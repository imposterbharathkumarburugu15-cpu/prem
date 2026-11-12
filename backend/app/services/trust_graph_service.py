"""Cross-Batch Trust Graph Service with Temporal Decay (P0.7).
Implements exponential temporal trust decay, positive reinforcement,
violation penalty deduction, harmonic mean custody chain trust propagation,
and downstream penalty back-propagation.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import math
from sqlalchemy.orm import Session

from backend.app.models.trust import ActorTrust, TrustEvent


class TrustGraphService:
    """Manages actor trust scores, temporal decay, and custody chain propagation."""

    DEFAULT_BASELINE = 0.50
    DEFAULT_LAMBDA = 0.01155  # half-life ~60 days (ln(2) / 60)
    POSITIVE_DELTA_FACTOR = 0.05
    VIOLATION_PENALTY = 0.35
    UPSTREAM_BACKPROP_FACTOR = 0.25  # Upstream receives 25% of violation penalty

    @classmethod
    def compute_decayed_trust(
        cls,
        current_trust: float,
        baseline_trust: float,
        decay_lambda: float,
        delta_days: float,
    ) -> float:
        """Calculates exponential temporal trust decay toward baseline:
        T(t) = T_baseline + (T_0 - T_baseline) * exp(-lambda * delta_t)
        """
        if delta_days <= 0.0:
            return current_trust
        decayed = baseline_trust + (current_trust - baseline_trust) * math.exp(-decay_lambda * delta_days)
        return round(max(0.0, min(1.0, decayed)), 4)

    @classmethod
    def compute_harmonic_mean_trust(cls, trust_scores: List[float]) -> float:
        """Computes harmonic mean trust of actors along a custody chain.
        T_batch = n / sum(1 / (T_i + epsilon))
        """
        if not trust_scores:
            return cls.DEFAULT_BASELINE
        epsilon = 1e-6
        reciprocal_sum = sum(1.0 / (max(0.0, s) + epsilon) for s in trust_scores)
        harmonic_mean = len(trust_scores) / reciprocal_sum
        return round(max(0.0, min(1.0, harmonic_mean)), 4)

    def get_or_create_actor_trust(
        self,
        db: Session,
        actor_id: str,
        actor_type: str = "FARMER",
    ) -> ActorTrust:
        """Retrieves or initializes an ActorTrust record."""
        record = db.query(ActorTrust).filter(ActorTrust.actor_id == actor_id).first()
        if not record:
            record = ActorTrust(
                actor_id=actor_id,
                actor_type=actor_type,
                current_trust=self.DEFAULT_BASELINE,
                baseline_trust=self.DEFAULT_BASELINE,
                decay_lambda=self.DEFAULT_LAMBDA,
                total_submissions=0,
                successful_submissions=0,
                violation_count=0,
            )
            db.add(record)
            db.flush()
        return record

    def evaluate_and_decay_trust(
        self,
        db: Session,
        actor_id: str,
        evaluation_time: Optional[datetime] = None,
    ) -> ActorTrust:
        """Applies exponential temporal decay to actor trust based on elapsed time."""
        record = self.get_or_create_actor_trust(db, actor_id)
        now = evaluation_time or datetime.now(timezone.utc)

        last_active = record.last_activity_at
        if last_active.tzinfo is None:
            last_active = last_active.replace(tzinfo=timezone.utc)

        delta_days = max(0.0, (now - last_active).total_seconds() / 86400.0)
        decayed_score = self.compute_decayed_trust(
            current_trust=record.current_trust,
            baseline_trust=record.baseline_trust,
            decay_lambda=record.decay_lambda,
            delta_days=delta_days,
        )

        if abs(decayed_score - record.current_trust) >= 0.001 and delta_days > 0.1:
            event = TrustEvent(
                actor_id=actor_id,
                event_type="DECAY_EVALUATION",
                score_before=record.current_trust,
                score_after=decayed_score,
                delta=round(decayed_score - record.current_trust, 4),
                reason=f"Temporal dormancy decay over {delta_days:.1f} days",
            )
            db.add(event)
            record.current_trust = decayed_score
            db.flush()

        return record

    def record_positive_event(
        self,
        db: Session,
        actor_id: str,
        reference_id: Optional[str] = None,
        reason: str = "Verified authentic evidence submission",
    ) -> ActorTrust:
        """Applies positive reinforcement: T_new = min(1.0, T_decayed + 0.05 * (1.0 - T_decayed))."""
        record = self.evaluate_and_decay_trust(db, actor_id)
        before = record.current_trust
        delta = self.POSITIVE_DELTA_FACTOR * (1.0 - before)
        after = round(min(1.0, before + delta), 4)

        record.current_trust = after
        record.total_submissions += 1
        record.successful_submissions += 1
        record.last_activity_at = datetime.now(timezone.utc)

        event = TrustEvent(
            actor_id=actor_id,
            event_type="POSITIVE_VERIFICATION",
            score_before=before,
            score_after=after,
            delta=round(after - before, 4),
            reference_id=reference_id,
            reason=reason,
        )
        db.add(event)
        db.flush()
        return record

    def apply_violation_penalty(
        self,
        db: Session,
        actor_id: str,
        reference_id: Optional[str] = None,
        reason: str = "Substantiated tampering or spatial violation",
        upstream_actor_ids: Optional[List[str]] = None,
    ) -> ActorTrust:
        """Applies violation penalty: T_new = max(0.0, T_decayed - 0.35)
        and back-propagates penalty to upstream custody chain actors.
        """
        record = self.evaluate_and_decay_trust(db, actor_id)
        before = record.current_trust
        after = round(max(0.0, before - self.VIOLATION_PENALTY), 4)

        record.current_trust = after
        record.total_submissions += 1
        record.violation_count += 1
        record.last_activity_at = datetime.now(timezone.utc)

        event = TrustEvent(
            actor_id=actor_id,
            event_type="SUBSTANTIATED_VIOLATION",
            score_before=before,
            score_after=after,
            delta=round(after - before, 4),
            reference_id=reference_id,
            reason=reason,
        )
        db.add(event)

        # Back-propagate to upstream actors
        if upstream_actor_ids:
            upstream_penalty = self.VIOLATION_PENALTY * self.UPSTREAM_BACKPROP_FACTOR
            for up_id in upstream_actor_ids:
                if up_id == actor_id:
                    continue
                up_record = self.evaluate_and_decay_trust(db, up_id)
                up_before = up_record.current_trust
                up_after = round(max(0.0, up_before - upstream_penalty), 4)
                up_record.current_trust = up_after
                up_event = TrustEvent(
                    actor_id=up_id,
                    event_type="TRANSITIVE_PENALTY",
                    score_before=up_before,
                    score_after=up_after,
                    delta=round(up_after - up_before, 4),
                    reference_id=reference_id,
                    reason=f"Transitive penalty back-propagated from violation by {actor_id}",
                )
                db.add(up_event)

        db.flush()
        return record

    def compute_custody_chain_batch_trust(
        self,
        db: Session,
        actor_ids: List[str],
    ) -> Dict[str, Any]:
        """Calculates harmonic mean custody chain trust across all participating actors."""
        individual_scores: Dict[str, float] = {}
        for aid in actor_ids:
            record = self.evaluate_and_decay_trust(db, aid)
            individual_scores[aid] = record.current_trust

        scores_list = list(individual_scores.values())
        batch_trust = self.compute_harmonic_mean_trust(scores_list)

        return {
            "batch_trust_score": batch_trust,
            "individual_actor_scores": individual_scores,
            "chain_length": len(actor_ids),
            "weakest_link_trust": min(scores_list) if scores_list else self.DEFAULT_BASELINE,
            "governance_status": "HIGH_CONFIDENCE" if batch_trust >= 0.70 else ("ACCEPTABLE" if batch_trust >= 0.40 else "HIGH_RISK_CHAIN"),
        }

