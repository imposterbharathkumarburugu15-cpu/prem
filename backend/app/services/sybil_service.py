"""Collusion and Sybil Detection Service (P0.6).
Implements Herfindahl-Hirschman Index (HHI) for witness concentration,
DFS directed cycle detection for circular endorsements,
phantom yield-to-acreage ratio checks, and shared hardware device detection.
"""

from typing import Dict, Any, List, Set, Tuple, Optional
from collections import defaultdict
from sqlalchemy.orm import Session

from backend.app.models.farmer import Farmer
from backend.app.models.farm import Farm
from backend.app.models.device import Device
from backend.app.models.supply_chain import Batch, Shipment, ShipmentItem, ShipmentEvent


class CollusionAndSybilDetectionService:
    """Detects collusion rings, circular supply-chain loops, and sybil identities."""

    # Agro-climatic maximum sustainable yield (kg per hectare) for cotton/pulses
    REGIONAL_MAX_YIELD_KG_PER_HA = 3500.0
    PHANTOM_YIELD_MULTIPLIER = 3.5  # > 12,250 kg/ha is physically impossible
    HHI_COLLUSION_THRESHOLD = 0.80
    MIN_INTERACTIONS_FOR_HHI = 3

    @staticmethod
    def calculate_hhi(interaction_counts: Dict[str, int]) -> float:
        """Computes Herfindahl-Hirschman Index (normalized to [0.0, 1.0]).
        HHI = sum((count_i / total)^2).
        """
        total = sum(interaction_counts.values())
        if total <= 0:
            return 0.0
        return round(sum((count / total) ** 2 for count in interaction_counts.values()), 4)

    @staticmethod
    def detect_directed_cycles(edges: List[Tuple[str, str]]) -> List[List[str]]:
        """Detects directed cycles in a directed graph using DFS with active recursion stack."""
        graph: Dict[str, List[str]] = defaultdict(list)
        for u, v in edges:
            graph[u].append(v)

        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        current_path: List[str] = []
        cycles: List[List[str]] = []

        def dfs(node: str):
            visited.add(node)
            rec_stack.add(node)
            current_path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Cycle found: extract cycle subpath
                    try:
                        idx = current_path.index(neighbor)
                        cycle = current_path[idx:] + [neighbor]
                        if len(cycle) >= 3:  # node -> other -> node
                            cycles.append(cycle)
                    except ValueError:
                        pass

            current_path.pop()
            rec_stack.remove(node)

        for node in list(graph.keys()):
            if node not in visited:
                dfs(node)

        return cycles

    @staticmethod
    def evaluate_yield_capacity(
        total_delivered_kg: float,
        land_area_hectares: float,
        max_sustainable_yield_kg_ha: float = 3500.0,
        multiplier: float = 3.5,
    ) -> Dict[str, Any]:
        """Evaluates whether delivered quantity exceeds physical land capacity."""
        if land_area_hectares <= 0:
            return {
                "yield_kg_per_ha": None,
                "is_phantom_yield": True,
                "reason": "Invalid or zero registered land area",
            }

        yield_kg_ha = total_delivered_kg / land_area_hectares
        max_allowed = max_sustainable_yield_kg_ha * multiplier
        is_phantom = yield_kg_ha > max_allowed

        return {
            "yield_kg_per_ha": round(yield_kg_ha, 2),
            "max_allowed_kg_per_ha": round(max_allowed, 2),
            "ratio_to_baseline": round(yield_kg_ha / max_sustainable_yield_kg_ha, 2),
            "is_phantom_yield": is_phantom,
            "reason": (
                f"Yield of {yield_kg_ha:.1f} kg/ha exceeds physical capacity {max_allowed:.1f} kg/ha ({multiplier}x limit)"
                if is_phantom
                else "Yield is within agro-climatic land capacity bounds"
            ),
        }

    def analyze_actor_collusion_risk(
        self,
        actor_id: str,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Performs full collusion, Sybil, and circular endorsement analysis for an actor."""
        flags: List[str] = []
        hhi_score = 0.0
        is_hhi_suspected = False
        cycles: List[List[str]] = []
        has_cycles = False
        yield_eval: Dict[str, Any] = {"yield_kg_per_ha": None, "is_phantom_yield": False}
        shared_devices_count = 0
        is_sybil_device = False

        if db is not None:
            # 1. HHI Counterparty concentration
            # Query shipments where actor is sender, transporter, or receiver
            shipments = db.query(Shipment).all()
            counterparty_counts: Dict[str, int] = defaultdict(int)
            graph_edges: List[Tuple[str, str]] = []

            for s in shipments:
                sender = s.origin_name or "ORIGIN"
                transporter = s.transporter_org_id or s.driver_id or "TRANSPORTER"
                receiver = s.destination_name or "DESTINATION"
                graph_edges.append((sender, transporter))
                graph_edges.append((transporter, receiver))

                if transporter == actor_id or getattr(s, "driver_id", None) == actor_id:
                    counterparty_counts[sender] += 1
                    counterparty_counts[receiver] += 1
                elif sender == actor_id:
                    counterparty_counts[transporter] += 1
                elif receiver == actor_id:
                    counterparty_counts[transporter] += 1

            total_interactions = sum(counterparty_counts.values())
            if total_interactions >= self.MIN_INTERACTIONS_FOR_HHI:
                hhi_score = self.calculate_hhi(counterparty_counts)
                if hhi_score > self.HHI_COLLUSION_THRESHOLD:
                    is_hhi_suspected = True
                    flags.append("REPETITIVE_WITNESS_COLLUSION")

            # 2. Directed Cycle Detection
            cycles = self.detect_directed_cycles(graph_edges)
            has_cycles = any(actor_id in c for c in cycles) if cycles else False
            if has_cycles:
                flags.append("CIRCULAR_ENDORSEMENT_DETECTED")

            # 3. Yield to Acreage
            farmer = db.query(Farmer).filter(Farmer.id == actor_id).first()
            if farmer:
                farms = db.query(Farm).filter(Farm.farmer_id == actor_id).all()
                total_ha = sum(f.area_acres * 0.404686 for f in farms if f.area_acres)
                farm_ids = [f.id for f in farms]
                batches = db.query(Batch).filter(Batch.farm_id.in_(farm_ids)).all() if farm_ids else []
                total_kg = sum(b.initial_quantity for b in batches if b.initial_quantity)
                if total_ha > 0 and total_kg > 0:
                    yield_eval = self.evaluate_yield_capacity(
                        total_delivered_kg=total_kg,
                        land_area_hectares=total_ha,
                    )
                    if yield_eval.get("is_phantom_yield"):
                        flags.append("PHANTOM_ACREAGE_OVERPRODUCTION")

            # 4. Sybil Hardware Sharing
            devices = db.query(Device).filter(Device.farmer_id == actor_id).all()
            for d in devices:
                if d.public_key:
                    other = (
                        db.query(Device)
                        .filter(
                            Device.public_key == d.public_key,
                            Device.farmer_id != actor_id,
                        )
                        .count()
                    )
                    if other > 0:
                        shared_devices_count += other
                        is_sybil_device = True
                        flags.append("SHARED_DEVICE_SYBIL_RISK")
                        break

        # Calculate risk level
        if "CIRCULAR_ENDORSEMENT_DETECTED" in flags or "PHANTOM_ACREAGE_OVERPRODUCTION" in flags:
            risk_level = "CRITICAL"
        elif "REPETITIVE_WITNESS_COLLUSION" in flags or "SHARED_DEVICE_SYBIL_RISK" in flags:
            risk_level = "HIGH"
        elif len(flags) > 0:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "actor_id": actor_id,
            "hhi_score": hhi_score,
            "is_hhi_collusion_suspected": is_hhi_suspected,
            "has_circular_endorsements": has_cycles,
            "detected_cycles": cycles,
            "yield_to_acreage": yield_eval,
            "is_phantom_yield": yield_eval.get("is_phantom_yield", False),
            "shared_devices_count": shared_devices_count,
            "is_sybil_device_suspected": is_sybil_device,
            "risk_level": risk_level,
            "flagged_indicators": flags,
        }
