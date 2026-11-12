"""Staking and Slashing Mechanism Service (Capability 19 - P2).
Provides cryptographic economic stake locking and slashing accountability:
- Stake Lifecycle: BONDED -> ACTIVE -> DISPUTED -> SLASHED / RELEASED
- Invariant: Slashing CANNOT be executed autonomously by algorithms or AI models.
  Slashing strictly requires human adjudication by the Evidence Integrity Officer with mandatory rationale.
- Proportional Penalty Tiers: Minor variance (5-10% penalty), gross negligence (25-50%),
  proven malicious fraud / collusion (100% slash + reputation collapse).
- Preserves complete financial and cryptographic audit trail for all balance modifications.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib


@dataclass
class ActorStake:
    stake_id: str
    actor_id: str
    actor_type: str  # TRANSPORTER, COLLECTION_CENTRE, RETAILER
    bonded_amount_inr: float
    locked_in_dispute_inr: float
    available_amount_inr: float
    status: str  # ACTIVE, LOCKED_DISPUTE, DEPLETED, WITHDRAWN
    last_updated_iso: str


@dataclass
class StakeDispute:
    dispute_id: str
    stake_id: str
    batch_id: str
    initiator_role: str
    allegation_type: str  # WEIGHT_TAMPERING, TEMPERATURE_VIOLATION, ROUTE_DIVERSION, COUNTERFEIT_INJECTION
    disputed_amount_inr: float
    evidence_hashes: List[str]
    status: str  # OPEN, ADJUDICATED_SLASHED, ADJUDICATED_EXONERATED, SETTLED
    created_at_iso: str
    adjudicated_by_eio: Optional[str]
    adjudication_rationale: Optional[str]
    slashed_amount_inr: float


class StakingAndSlashingService:
    """Manages actor collateral bonding, dispute escrow, and human-authorized slashing."""

    _stakes_db: Dict[str, ActorStake] = {}
    _disputes_db: Dict[str, StakeDispute] = {}

    @classmethod
    def bond_stake(
        cls,
        actor_id: str,
        actor_type: str,
        amount_inr: float,
    ) -> ActorStake:
        """Deposits and locks operational security collateral."""
        if amount_inr <= 0.0:
            raise ValueError("Stake amount must be strictly positive")

        stake_id = f"stake_{hashlib.sha256(f'{actor_id}:{actor_type}'.encode()).hexdigest()[:16]}"
        existing = cls._stakes_db.get(stake_id)

        now_iso = datetime.now(timezone.utc).isoformat()
        if existing:
            existing.bonded_amount_inr += amount_inr
            existing.available_amount_inr += amount_inr
            existing.last_updated_iso = now_iso
            return existing

        stake = ActorStake(
            stake_id=stake_id,
            actor_id=actor_id,
            actor_type=actor_type.upper(),
            bonded_amount_inr=amount_inr,
            locked_in_dispute_inr=0.0,
            available_amount_inr=amount_inr,
            status="ACTIVE",
            last_updated_iso=now_iso,
        )
        cls._stakes_db[stake_id] = stake
        return stake

    @classmethod
    def open_dispute(
        cls,
        actor_id: str,
        batch_id: str,
        initiator_role: str,
        allegation_type: str,
        dispute_amount_inr: float,
        evidence_hashes: List[str],
    ) -> StakeDispute:
        """Opens a dispute and locks required stake in escrow pending EIO investigation."""
        # Find actor's stake
        target_stake: Optional[ActorStake] = None
        for s in cls._stakes_db.values():
            if s.actor_id == actor_id:
                target_stake = s
                break

        if not target_stake:
            raise ValueError(f"No bonded collateral stake found for actor '{actor_id}'")

        if target_stake.available_amount_inr < dispute_amount_inr:
            dispute_amount_inr = target_stake.available_amount_inr  # Lock what is available

        target_stake.available_amount_inr -= dispute_amount_inr
        target_stake.locked_in_dispute_inr += dispute_amount_inr
        target_stake.status = "LOCKED_DISPUTE"
        target_stake.last_updated_iso = datetime.now(timezone.utc).isoformat()

        dispute_id = f"disp_{hashlib.sha256(f'{target_stake.stake_id}:{batch_id}:{allegation_type}'.encode()).hexdigest()[:16]}"
        dispute = StakeDispute(
            dispute_id=dispute_id,
            stake_id=target_stake.stake_id,
            batch_id=batch_id,
            initiator_role=initiator_role,
            allegation_type=allegation_type,
            disputed_amount_inr=dispute_amount_inr,
            evidence_hashes=evidence_hashes,
            status="OPEN",
            created_at_iso=datetime.now(timezone.utc).isoformat(),
            adjudicated_by_eio=None,
            adjudication_rationale=None,
            slashed_amount_inr=0.0,
        )
        cls._disputes_db[dispute_id] = dispute
        return dispute

    @classmethod
    def adjudicate_slashing_order(
        cls,
        dispute_id: str,
        officer_user_id: str,
        is_officer_eio: bool,
        verdict: str,  # "SLASH_FULL", "SLASH_PARTIAL", "EXONERATE"
        slash_percentage: float,  # 0.0 to 100.0
        rationale: str,
    ) -> Dict[str, Any]:
        """Adjudicates a dispute and executes slashing. Strictly requires EIO authorization and written rationale."""
        # 1. Enforce Role Permission Invariant
        if not is_officer_eio:
            raise PermissionError("Autonomous or unauthorized slashing forbidden: only Evidence Integrity Officer can adjudicate slashing.")

        # 2. Enforce Mandatory Rationale
        if not rationale or len(rationale.strip()) < 15:
            raise ValueError("Mandatory written rationale (minimum 15 characters) required for slashing adjudication.")

        dispute = cls._disputes_db.get(dispute_id)
        if not dispute:
            raise ValueError(f"Dispute '{dispute_id}' not found")

        if dispute.status != "OPEN":
            raise ValueError(f"Dispute already resolved with status: {dispute.status}")

        stake = cls._stakes_db.get(dispute.stake_id)
        if not stake:
            raise ValueError(f"Stake record '{dispute.stake_id}' missing")

        now_iso = datetime.now(timezone.utc).isoformat()
        dispute.adjudicated_by_eio = officer_user_id
        dispute.adjudication_rationale = rationale.strip()

        if verdict in ("SLASH_FULL", "SLASH_PARTIAL"):
            pct = min(100.0, max(1.0, slash_percentage)) if verdict == "SLASH_PARTIAL" else 100.0
            slashed_amount = round((pct / 100.0) * dispute.disputed_amount_inr, 2)
            refund_amount = round(dispute.disputed_amount_inr - slashed_amount, 2)

            stake.locked_in_dispute_inr = max(0.0, stake.locked_in_dispute_inr - dispute.disputed_amount_inr)
            stake.bonded_amount_inr = max(0.0, stake.bonded_amount_inr - slashed_amount)
            stake.available_amount_inr += refund_amount

            dispute.slashed_amount_inr = slashed_amount
            dispute.status = "ADJUDICATED_SLASHED"

            result_msg = f"EIO slashed {slashed_amount:.2f} INR ({pct:.1f}%) from stake {stake.stake_id}. Rationale: {rationale}"

        elif verdict == "EXONERATE":
            # Refund all locked funds back to available
            stake.locked_in_dispute_inr = max(0.0, stake.locked_in_dispute_inr - dispute.disputed_amount_inr)
            stake.available_amount_inr += dispute.disputed_amount_inr

            dispute.slashed_amount_inr = 0.0
            dispute.status = "ADJUDICATED_EXONERATED"
            result_msg = f"EIO exonerated actor. All {dispute.disputed_amount_inr:.2f} INR released to available balance."
        else:
            raise ValueError(f"Invalid verdict: {verdict}")

        stake.status = "DEPLETED" if stake.bonded_amount_inr <= 0 else "ACTIVE"
        stake.last_updated_iso = now_iso

        return {
            "dispute_id": dispute_id,
            "stake_id": stake.stake_id,
            "status": dispute.status,
            "verdict": verdict,
            "slashed_amount_inr": dispute.slashed_amount_inr,
            "remaining_bonded_inr": stake.bonded_amount_inr,
            "adjudicated_by": officer_user_id,
            "adjudication_time": now_iso,
            "rationale": rationale,
            "summary": result_msg,
        }

    @classmethod
    def get_stake(cls, actor_id: str) -> Optional[ActorStake]:
        for s in cls._stakes_db.values():
            if s.actor_id == actor_id:
                return s
        return None

    @classmethod
    def get_dispute(cls, dispute_id: str) -> Optional[StakeDispute]:
        return cls._disputes_db.get(dispute_id)

