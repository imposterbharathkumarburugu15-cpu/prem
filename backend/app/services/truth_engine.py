"""Decoupled Evidence Truth Engine (P0.3).
Evaluates 6 independent truth dimensions (Crypto, Spatial, Forensic, Crop, Corroboration, Trust),
computes weighted composite truth score, generates structured Anomaly Vector,
and enforces Never-Autonomous-Reject governance.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class AnomalyDimension:
    score: float
    weight: float
    weighted_score: float
    is_flagged: bool
    severity: float  # 0.0 (clean) to 1.0 (fatal)
    code: str
    explanation: str


@dataclass
class TruthEvaluationResult:
    composite_truth_score: float  # 0.0 - 1.0
    signals: Dict[str, Dict[str, Any]]
    has_critical_anomaly: bool
    has_warning_anomaly: bool
    flagged_codes: List[str]
    recommendation: str  # AUTO_APPROVE, FLAG_FOR_REVIEW, CHALLENGE_RECOMMENDED
    suggested_state: str  # PENDING_BATCH, PENDING_REVIEW
    governance_notes: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "composite_truth_score": self.composite_truth_score,
            "signals": self.signals,
            "has_critical_anomaly": self.has_critical_anomaly,
            "has_warning_anomaly": self.has_warning_anomaly,
            "flagged_codes": self.flagged_codes,
            "recommendation": self.recommendation,
            "suggested_state": self.suggested_state,
            "governance_notes": self.governance_notes,
        }


class DecoupledEvidenceTruthEngine:
    """Computes multi-dimensional truth score and enforces governance invariants."""

    WEIGHTS = {
        "crypto": 0.25,
        "spatial": 0.20,
        "forensic": 0.20,
        "crop": 0.15,
        "corrob": 0.10,
        "trust": 0.10,
    }

    def evaluate(
        self,
        crypto_valid: bool = True,
        sequence_valid: bool = True,
        spatial_data: Optional[Dict[str, Any]] = None,
        forensic_data: Optional[Dict[str, Any]] = None,
        crop_data: Optional[Dict[str, Any]] = None,
        corroboration_data: Optional[Dict[str, Any]] = None,
        actor_trust_score: float = 0.50,
        kinematic_data: Optional[Dict[str, Any]] = None,
    ) -> TruthEvaluationResult:
        """Evaluates all 6 dimensions and computes composite truth score."""
        signals: Dict[str, Dict[str, Any]] = {}
        flagged_codes: List[str] = []
        has_critical = False
        has_warning = False

        # 1. Cryptographic Envelope (0.25)
        crypto_score = 1.0
        crypto_code = "CRYPTO_CLEAN"
        crypto_desc = "P-256 signature and monotonic sequence verified"
        crypto_severity = 0.0

        if not crypto_valid:
            crypto_score = 0.0
            crypto_code = "CRYPTO_SIGNATURE_INVALID"
            crypto_desc = "Cryptographic signature failed verification"
            crypto_severity = 1.0
            has_critical = True
            flagged_codes.append(crypto_code)
        elif not sequence_valid:
            crypto_score = 0.0
            crypto_code = "CRYPTO_SEQUENCE_REPLAY"
            crypto_desc = "Device monotonic sequence out-of-order or replayed"
            crypto_severity = 1.0
            has_critical = True
            flagged_codes.append(crypto_code)

        signals["crypto"] = asdict(
            AnomalyDimension(
                score=crypto_score,
                weight=self.WEIGHTS["crypto"],
                weighted_score=round(crypto_score * self.WEIGHTS["crypto"], 4),
                is_flagged=crypto_score < 1.0,
                severity=crypto_severity,
                code=crypto_code,
                explanation=crypto_desc,
            )
        )

        # 2. Spatial Dimension (0.20)
        spatial_data = spatial_data or {}
        kinematic_data = kinematic_data or {}
        is_inside = spatial_data.get("is_inside_boundary", True)
        dist_m = spatial_data.get("distance_meters", 0.0)
        acc_m = spatial_data.get("horizontal_accuracy", 5.0)

        is_mock = kinematic_data.get("is_mock_detected", False)
        is_teleport = kinematic_data.get("is_teleportation", False)
        is_speed_bad = kinematic_data.get("is_anomalous", False)

        spatial_score = 1.0
        spatial_code = "SPATIAL_CLEAN"
        spatial_desc = "Within cadastral farm boundary"
        spatial_severity = 0.0

        if acc_m > 100.0 or is_mock or is_teleport:
            spatial_score = 0.0
            spatial_code = "SPATIAL_SPOOFING_DETECTED"
            spatial_desc = f"Mock GNSS ({is_mock}), teleportation ({is_teleport}), or accuracy ({acc_m}m > 100m)"
            spatial_severity = 0.95
            has_critical = True
            flagged_codes.append(spatial_code)
        elif is_speed_bad:
            spatial_score = 0.30
            spatial_code = "KINEMATIC_SPEED_ANOMALY"
            spatial_desc = "Velocity exceeds agricultural threshold (>50 m/s)"
            spatial_severity = 0.70
            has_warning = True
            flagged_codes.append(spatial_code)
        elif not is_inside:
            if dist_m <= 150.0:
                spatial_score = 0.75
                spatial_code = "PROXIMATE_BORDER"
                spatial_desc = f"{dist_m:.1f}m from perimeter (within drift margin)"
                spatial_severity = 0.25
                has_warning = True
            else:
                spatial_score = max(0.0, 1.0 - (dist_m / 1000.0))
                spatial_code = "OUTSIDE_FARMLAND_BOUNDARY"
                spatial_desc = f"{dist_m:.1f}m outside registered boundary"
                spatial_severity = 0.75
                has_warning = True
                flagged_codes.append(spatial_code)

        signals["spatial"] = asdict(
            AnomalyDimension(
                score=round(spatial_score, 3),
                weight=self.WEIGHTS["spatial"],
                weighted_score=round(spatial_score * self.WEIGHTS["spatial"], 4),
                is_flagged=spatial_score < 0.85,
                severity=spatial_severity,
                code=spatial_code,
                explanation=spatial_desc,
            )
        )

        # 3. AI Forensics Dimension (0.20)
        forensic_data = forensic_data or {}
        is_tamper = forensic_data.get("is_tamper_suspected", False)
        is_ai_gen = forensic_data.get("is_ai_generated_suspected", False)
        is_dup = forensic_data.get("is_duplicate", False)
        is_blurry = forensic_data.get("is_blurry", False)

        forensic_score = 1.0
        forensic_code = "FORENSIC_CLEAN"
        forensic_desc = "Natural sensor noise, sharp focus, no tampering"
        forensic_severity = 0.0

        if is_dup:
            forensic_score = 0.0
            forensic_code = "DUPLICATE_IMAGE_REUSED"
            forensic_desc = "Image perceptual hash matches previously ingested submission"
            forensic_severity = 1.0
            has_critical = True
            flagged_codes.append(forensic_code)
        elif is_tamper or is_ai_gen:
            forensic_score = 0.15
            forensic_code = "IMAGE_MANIPULATION_DETECTED"
            forensic_desc = "Error Level Analysis or spectral frequency anomaly detected"
            forensic_severity = 0.90
            has_critical = True
            flagged_codes.append(forensic_code)
        elif is_blurry:
            forensic_score = 0.50
            forensic_code = "BLURRY_CAPTURE"
            forensic_desc = "Laplacian focus score below threshold (< 50.0)"
            forensic_severity = 0.40
            has_warning = True
            flagged_codes.append(forensic_code)

        signals["forensic"] = asdict(
            AnomalyDimension(
                score=round(forensic_score, 3),
                weight=self.WEIGHTS["forensic"],
                weighted_score=round(forensic_score * self.WEIGHTS["forensic"], 4),
                is_flagged=forensic_score < 0.80,
                severity=forensic_severity,
                code=forensic_code,
                explanation=forensic_desc,
            )
        )

        # 4. Crop & Phenology Consistency (0.15)
        crop_data = crop_data or {}
        is_crop_match = crop_data.get("is_crop_match", True)
        crop_conf = crop_data.get("confidence", 0.90)

        crop_score = round(crop_conf, 3) if is_crop_match else 0.20
        crop_code = "CROP_STAGE_CONSISTENT" if is_crop_match else "CROP_CATEGORY_MISMATCH"
        crop_desc = "Visual classification matches registered crop" if is_crop_match else "Visual crop differs from registration"
        crop_sev = 0.0 if is_crop_match else 0.70
        if not is_crop_match:
            has_warning = True
            flagged_codes.append(crop_code)

        signals["crop"] = asdict(
            AnomalyDimension(
                score=crop_score,
                weight=self.WEIGHTS["crop"],
                weighted_score=round(crop_score * self.WEIGHTS["crop"], 4),
                is_flagged=not is_crop_match,
                severity=crop_sev,
                code=crop_code,
                explanation=crop_desc,
            )
        )

        # 5. External Corroboration (0.10)
        corroboration_data = corroboration_data or {}
        corrob_score = corroboration_data.get("composite_corroboration_score", 0.85)
        corrob_score = max(0.0, min(1.0, float(corrob_score)))

        corrob_code = "CORROBORATION_CONFIRMED" if corrob_score >= 0.70 else "CORROBORATION_DISCREPANCY"
        corrob_desc = "NDVI and weather corroborate observation" if corrob_score >= 0.70 else "NDVI or weather diverges from expectation"
        corrob_sev = 0.0 if corrob_score >= 0.70 else 0.50
        if corrob_score < 0.70:
            has_warning = True
            flagged_codes.append(corrob_code)

        signals["corrob"] = asdict(
            AnomalyDimension(
                score=round(corrob_score, 3),
                weight=self.WEIGHTS["corrob"],
                weighted_score=round(corrob_score * self.WEIGHTS["corrob"], 4),
                is_flagged=corrob_score < 0.70,
                severity=corrob_sev,
                code=corrob_code,
                explanation=corrob_desc,
            )
        )

        # 6. Actor Historical Trust (0.10)
        actor_trust = max(0.0, min(1.0, float(actor_trust_score)))
        trust_code = "TRUSTED_ACTOR" if actor_trust >= 0.60 else ("UNPROVEN_ACTOR" if actor_trust >= 0.40 else "DEGRADED_TRUST_ACTOR")
        trust_desc = f"Actor decayed trust score: {actor_trust:.2f}"
        trust_sev = 0.0 if actor_trust >= 0.40 else 0.60
        if actor_trust < 0.40:
            has_warning = True
            flagged_codes.append(trust_code)

        signals["trust"] = asdict(
            AnomalyDimension(
                score=round(actor_trust, 3),
                weight=self.WEIGHTS["trust"],
                weighted_score=round(actor_trust * self.WEIGHTS["trust"], 4),
                is_flagged=actor_trust < 0.40,
                severity=trust_sev,
                code=trust_code,
                explanation=trust_desc,
            )
        )

        # Composite Score Calculation
        composite_score = sum(d["weighted_score"] for d in signals.values())
        composite_score = round(max(0.0, min(1.0, composite_score)), 3)

        # Decision Governance (F-28 Invariant: Never Autonomous Reject)
        if composite_score >= 0.85 and not has_critical and not has_warning:
            recommendation = "AUTO_APPROVE"
            suggested_state = "PENDING_BATCH"
            gov_note = "Composite truth exceeds 0.85 with zero anomalies. Auto-approval eligible."
        elif has_critical:
            recommendation = "FLAG_FOR_REVIEW"
            suggested_state = "PENDING_REVIEW"
            gov_note = "Critical anomaly flagged. Routed to Evidence Integrity Officer (Never-Autonomous-Reject policy)."
        elif composite_score < 0.50:
            recommendation = "CHALLENGE_RECOMMENDED"
            suggested_state = "PENDING_REVIEW"
            gov_note = "Low composite truth score. Routed to Evidence Integrity Officer for challenge issuance."
        else:
            recommendation = "FLAG_FOR_REVIEW"
            suggested_state = "PENDING_REVIEW"
            gov_note = "Sub-threshold or warning anomaly. Routed to Evidence Integrity Officer for adjudication."

        return TruthEvaluationResult(
            composite_truth_score=composite_score,
            signals=signals,
            has_critical_anomaly=has_critical,
            has_warning_anomaly=has_warning,
            flagged_codes=flagged_codes,
            recommendation=recommendation,
            suggested_state=suggested_state,
            governance_notes=gov_note,
        )

