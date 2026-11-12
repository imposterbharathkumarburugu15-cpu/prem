"""Multi-Stage Mass-Balance Quantity Reconciliation Service.
Tracks mass conservation and physical shrinkage across 7 supply-chain stages:
Harvest -> Pickup -> Transit -> Weigh-Bridge -> Batch Split -> Retail Depot -> Sales.
Enforces crop-specific shrinkage tolerances (2-5%), detects weight inflation (<-0.5%),
enforces batch split conservation (tolerance +-0.01 kg), and prevents retail overselling.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session

from backend.app.models.supply_chain import (
    Batch,
    Shipment,
    ShipmentItem,
    ShipmentEvent,
    WeighingRecord,
    ProcurementOrder,
    RetailerInventory,
)


@dataclass
class StageReconciliation:
    stage_name: str
    expected_qty: float
    actual_qty: float
    discrepancy_qty: float
    discrepancy_pct: float
    allowable_pct: float
    status: str  # NORMAL, WARNING, VIOLATION
    reason: str


class MassBalanceService:
    """Evaluates multi-stage commodity mass balance and shrinkage tolerances."""

    # Crop tolerance thresholds: (allowable_normal_pct, warning_upper_pct, max_inflation_pct)
    CROP_TOLERANCES: Dict[str, Dict[str, float]] = {
        "COTTON": {"normal": 2.0, "warning": 4.0, "inflation": -0.20},
        "GRAIN": {"normal": 1.5, "warning": 3.0, "inflation": -0.20},
        "PADDY": {"normal": 1.5, "warning": 3.0, "inflation": -0.20},
        "SOYBEAN": {"normal": 1.5, "warning": 3.0, "inflation": -0.20},
        "PULSE": {"normal": 1.5, "warning": 3.0, "inflation": -0.20},
        "CHILLI": {"normal": 2.0, "warning": 3.5, "inflation": -0.20},
        "PRODUCE": {"normal": 5.0, "warning": 8.0, "inflation": -0.50},
        "DEFAULT": {"normal": 2.0, "warning": 4.0, "inflation": -0.20},
    }

    SPLIT_CONSERVATION_TOLERANCE_KG = 0.01

    @classmethod
    def get_crop_tolerance(cls, commodity: Optional[str]) -> Dict[str, float]:
        """Returns tolerance thresholds for a commodity."""
        if not commodity:
            return cls.CROP_TOLERANCES["DEFAULT"]
        comm_upper = commodity.strip().upper()
        for key in cls.CROP_TOLERANCES:
            if key in comm_upper:
                return cls.CROP_TOLERANCES[key]
        return cls.CROP_TOLERANCES["DEFAULT"]

    @classmethod
    def evaluate_transit_shrinkage(
        cls,
        picked_up_qty: float,
        delivered_qty: float,
        commodity: Optional[str] = "COTTON",
    ) -> StageReconciliation:
        """Evaluates highway transit moisture loss between origin pickup and delivery."""
        if picked_up_qty <= 0:
            raise ValueError("Picked up quantity must be positive")

        delta = round(picked_up_qty - delivered_qty, 3)
        shrinkage_pct = round((delta / picked_up_qty) * 100.0, 3)
        tol = cls.get_crop_tolerance(commodity)

        if shrinkage_pct < tol["inflation"]:
            # Negative shrinkage: delivered weight exceeds pickup weight
            status = "VIOLATION"
            reason = f"Weight inflation detected ({shrinkage_pct:+.2f}%). Potential physical adulteration."
        elif shrinkage_pct <= tol["normal"]:
            status = "NORMAL"
            reason = f"Transit moisture loss {shrinkage_pct:.2f}% within normal bounds (<= {tol['normal']}%)"
        elif shrinkage_pct <= tol["warning"]:
            status = "WARNING"
            reason = f"Elevated transit moisture loss {shrinkage_pct:.2f}% (exceeds {tol['normal']}%, <= {tol['warning']}%)"
        else:
            status = "VIOLATION"
            reason = f"Excessive cargo deficit {shrinkage_pct:.2f}% exceeds maximum allowable {tol['warning']}%"

        return StageReconciliation(
            stage_name="TRANSIT_SHRINKAGE",
            expected_qty=picked_up_qty,
            actual_qty=delivered_qty,
            discrepancy_qty=delta,
            discrepancy_pct=shrinkage_pct,
            allowable_pct=tol["normal"],
            status=status,
            reason=reason,
        )

    @classmethod
    def evaluate_scale_reconciliation(
        cls,
        transporter_delivered_qty: float,
        certified_intake_qty: float,
        is_manual_entry: bool = False,
    ) -> StageReconciliation:
        """Reconciles transporter dock delivery weight against certified weigh-bridge intake."""
        if transporter_delivered_qty <= 0:
            raise ValueError("Delivered quantity must be positive")

        delta = round(abs(transporter_delivered_qty - certified_intake_qty), 3)
        pct_diff = round((delta / transporter_delivered_qty) * 100.0, 3)
        allowable_pct = 1.0 if is_manual_entry else 0.5
        violation_pct = 2.0 if is_manual_entry else 1.0

        if pct_diff <= allowable_pct:
            status = "NORMAL"
            reason = f"Scale discrepancy {pct_diff:.2f}% within certified calibration limit (<= {allowable_pct}%)"
        elif pct_diff <= violation_pct:
            status = "WARNING"
            reason = f"Scale reading difference {pct_diff:.2f}% exceeds regular tolerance {allowable_pct}%"
        else:
            status = "VIOLATION"
            reason = f"Significant scale variance {pct_diff:.2f}% exceeds maximum allowable {violation_pct}%"

        return StageReconciliation(
            stage_name="SCALE_RECONCILIATION",
            expected_qty=transporter_delivered_qty,
            actual_qty=certified_intake_qty,
            discrepancy_qty=delta,
            discrepancy_pct=pct_diff,
            allowable_pct=allowable_pct,
            status=status,
            reason=reason,
        )

    @classmethod
    def validate_batch_split_conservation(
        cls,
        parent_qty: float,
        child_quantities: List[float],
        waste_loss_qty: float = 0.0,
    ) -> Dict[str, Any]:
        """Validates mathematical mass conservation during batch division:
        sum(child_quantities) + waste_loss_qty == parent_qty +- 0.01 kg.
        """
        if parent_qty <= 0:
            return {"is_valid": False, "delta_kg": parent_qty, "reason": "Parent batch quantity must be positive"}

        sum_children = sum(child_quantities)
        total_accounted = sum_children + waste_loss_qty
        delta = round(abs(parent_qty - total_accounted), 4)

        is_valid = delta <= cls.SPLIT_CONSERVATION_TOLERANCE_KG
        loss_pct = round((waste_loss_qty / parent_qty) * 100.0, 2) if parent_qty > 0 else 0.0
        is_loss_excessive = loss_pct > 5.0

        return {
            "is_valid": is_valid,
            "parent_qty": parent_qty,
            "sum_children_qty": round(sum_children, 3),
            "waste_loss_qty": waste_loss_qty,
            "waste_loss_pct": loss_pct,
            "total_accounted_qty": total_accounted,
            "delta_kg": delta,
            "tolerance_kg": cls.SPLIT_CONSERVATION_TOLERANCE_KG,
            "is_loss_excessive": is_loss_excessive,
            "reason": (
                f"Conservation verified: delta {delta:.4f} kg <= {cls.SPLIT_CONSERVATION_TOLERANCE_KG} kg"
                if is_valid
                else f"Mass conservation violation: sum {total_accounted} kg differs from parent {parent_qty} kg by {delta:.4f} kg"
            ),
        }

    @classmethod
    def validate_retail_depletion(
        cls,
        current_available_qty: float,
        sale_qty: float,
    ) -> Dict[str, Any]:
        """Enforces anti-overselling invariant: sale_qty <= current_available_qty."""
        if sale_qty <= 0:
            return {"is_valid": False, "reason": "Sale quantity must be positive"}

        if sale_qty > current_available_qty:
            return {
                "is_valid": False,
                "current_available_qty": current_available_qty,
                "requested_sale_qty": sale_qty,
                "deficit_qty": round(sale_qty - current_available_qty, 3),
                "reason": f"Insufficient stock: requested {sale_qty} kg exceeds available {current_available_qty} kg",
            }

        remaining = round(current_available_qty - sale_qty, 3)
        return {
            "is_valid": True,
            "current_available_qty": current_available_qty,
            "requested_sale_qty": sale_qty,
            "remaining_available_qty": remaining,
            "is_depleted": remaining == 0.0,
            "reason": f"Sale verified. Remaining shelf stock: {remaining} kg",
        }

    def reconcile_batch_lineage(
        self,
        db: Session,
        batch_id: str,
    ) -> Dict[str, Any]:
        """Constructs an end-to-end mass balance reconciliation report for a batch."""
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            return {"error": f"Batch {batch_id} not found"}

        stages: List[Dict[str, Any]] = []
        overall_status = "NORMAL"

        # 1. Harvest -> Pickup
        shipment_items = db.query(ShipmentItem).filter(ShipmentItem.batch_id == batch_id).all()
        total_picked_up = sum(si.picked_up_quantity for si in shipment_items if si.picked_up_quantity)
        total_delivered = sum(si.delivered_quantity for si in shipment_items if si.delivered_quantity)

        if total_picked_up > 0 and batch.initial_quantity:
            pickup_delta = round(batch.initial_quantity - total_picked_up, 2)
            pickup_pct = round((abs(pickup_delta) / batch.initial_quantity) * 100.0, 2)
            st1_status = "NORMAL" if pickup_pct <= 2.0 else "WARNING"
            if st1_status == "WARNING" and overall_status == "NORMAL":
                overall_status = "WARNING"
            stages.append({
                "stage": "HARVEST_TO_PICKUP",
                "declared_harvest_kg": batch.initial_quantity,
                "picked_up_kg": total_picked_up,
                "discrepancy_kg": pickup_delta,
                "discrepancy_pct": pickup_pct,
                "status": st1_status,
            })

        # 2. Transit Shrinkage
        if total_picked_up > 0 and total_delivered > 0:
            comm = batch.commodity_type or "COTTON"
            transit_eval = self.evaluate_transit_shrinkage(
                picked_up_qty=total_picked_up,
                delivered_qty=total_delivered,
                commodity=comm,
            )
            if transit_eval.status == "VIOLATION":
                overall_status = "VIOLATION"
            elif transit_eval.status == "WARNING" and overall_status == "NORMAL":
                overall_status = "WARNING"
            stages.append({
                "stage": transit_eval.stage_name,
                "picked_up_kg": total_picked_up,
                "delivered_kg": total_delivered,
                "discrepancy_kg": transit_eval.discrepancy_qty,
                "shrinkage_pct": transit_eval.discrepancy_pct,
                "allowable_pct": transit_eval.allowable_pct,
                "status": transit_eval.status,
                "reason": transit_eval.reason,
            })

        # 3. Weigh-Bridge Intake
        weigh_records = db.query(WeighingRecord).filter(WeighingRecord.batch_id == batch_id).all()
        total_weighed = sum(wr.measured_weight for wr in weigh_records if wr.measured_weight)
        if total_delivered > 0 and total_weighed > 0:
            scale_eval = self.evaluate_scale_reconciliation(
                transporter_delivered_qty=total_delivered,
                certified_intake_qty=total_weighed,
            )
            if scale_eval.status == "VIOLATION":
                overall_status = "VIOLATION"
            elif scale_eval.status == "WARNING" and overall_status == "NORMAL":
                overall_status = "WARNING"
            stages.append({
                "stage": scale_eval.stage_name,
                "delivered_kg": total_delivered,
                "weighed_kg": total_weighed,
                "discrepancy_kg": scale_eval.discrepancy_qty,
                "discrepancy_pct": scale_eval.discrepancy_pct,
                "status": scale_eval.status,
                "reason": scale_eval.reason,
            })

        # 4. Child Splits
        child_batches = db.query(Batch).filter(Batch.parent_batch_id == batch_id).all()
        if child_batches:
            child_qtys = [cb.initial_quantity for cb in child_batches if cb.initial_quantity]
            split_eval = self.validate_batch_split_conservation(
                parent_qty=batch.current_quantity or batch.initial_quantity,
                child_quantities=child_qtys,
            )
            stages.append({
                "stage": "SPLIT_CONSERVATION",
                "parent_qty": split_eval["parent_qty"],
                "sum_children_qty": split_eval["sum_children_qty"],
                "delta_kg": split_eval["delta_kg"],
                "is_valid": split_eval["is_valid"],
                "status": "NORMAL" if split_eval["is_valid"] else "VIOLATION",
                "reason": split_eval["reason"],
            })

        # 5. Retail Inventory & Sales
        inventories = db.query(RetailerInventory).filter(RetailerInventory.batch_id == batch_id).all()
        total_initial_retail = sum(ri.initial_quantity for ri in inventories if ri.initial_quantity)
        total_avail_retail = sum(ri.available_quantity for ri in inventories if ri.available_quantity is not None)
        total_sold = round(total_initial_retail - total_avail_retail, 3) if total_initial_retail >= total_avail_retail else 0.0

        if inventories:
            stages.append({
                "stage": "RETAIL_DEPLETION",
                "total_retail_stock_kg": total_initial_retail,
                "available_stock_kg": total_avail_retail,
                "cumulative_sales_kg": total_sold,
                "is_depleted": total_avail_retail == 0.0,
                "status": "NORMAL",
            })

        return {
            "batch_id": batch_id,
            "commodity_type": batch.commodity_type,
            "overall_reconciliation_status": overall_status,
            "requires_officer_review": overall_status == "VIOLATION",
            "stages_evaluated": stages,
        }

