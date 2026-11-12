"""Explainable Human Review Radar Service (P0.8).
Computes 4-axis radar scores (Crypto, Spatial, Forensic, Phenology),
calculates composite confidence C = 0.35 Scrypto + 0.25 Sspatial + 0.20 Sforensic + 0.20 Sphenology,
and routes sub-threshold or anomalous submissions to Evidence Integrity Officer (officer1).
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class RadarDimensionScore:
    name: str
    score: float  # 0.0 to 1.0
    weight: float
    weighted_score: float
    status: str  # PASS, WARNING, FAIL
    details: Dict[str, Any]


@dataclass
class RadarEvaluationResult:
    composite_confidence: float
    axes: Dict[str, Dict[str, Any]]
    routing_action: str  # AUTO_APPROVE, OFFICER_REVIEW_REQUIRED
    assigned_queue: str
    assigned_officer: Optional[str]
    hard_flags: List[str]
    governance_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "composite_confidence": self.composite_confidence,
            "axes": self.axes,
            "routing_action": self.routing_action,
            "assigned_queue": self.assigned_queue,
            "assigned_officer": self.assigned_officer,
            "hard_flags": self.hard_flags,
            "governance_note": self.governance_note,
        }


class RadarService:
    """Computes explainable review radar and routes evidence."""

    WEIGHT_CRYPTO = 0.35
    WEIGHT_SPATIAL = 0.25
    WEIGHT_FORENSIC = 0.20
    WEIGHT_PHENOLOGY = 0.20

    AUTO_APPROVE_THRESHOLD = 0.85
    DEFAULT_OFFICER = "officer1"

    def compute_crypto_axis(
        self,
        signature_valid: bool = True,
        sequence_valid: bool = True,
        hash_matched: bool = True,
        clock_skew_seconds: float = 0.0,
    ) -> RadarDimensionScore:
        """Evaluates cryptographic envelope integrity."""
        if not signature_valid or not sequence_valid or not hash_matched:
            score = 0.0
            status = "FAIL"
            details = {
                "signature_valid": signature_valid,
                "sequence_valid": sequence_valid,
                "hash_matched": hash_matched,
                "clock_skew_seconds": clock_skew_seconds,
            }
        elif 120.0 < clock_skew_seconds <= 300.0:
            score = 0.80
            status = "WARNING"
            details = {"clock_skew_warning": True, "skew_seconds": clock_skew_seconds}
        else:
            score = 1.0
            status = "PASS"
            details = {"crypto_pristine": True}

        return RadarDimensionScore(
            name="Cryptographic Envelope",
            score=score,
            weight=self.WEIGHT_CRYPTO,
            weighted_score=round(score * self.WEIGHT_CRYPTO, 4),
            status=status,
            details=details,
        )

    def compute_spatial_axis(
        self,
        is_inside_boundary: bool = True,
        distance_meters: float = 0.0,
        gps_accuracy: float = 5.0,
        is_mock: bool = False,
        velocity_mps: float = 0.0,
    ) -> RadarDimensionScore:
        """Evaluates spatial proximity and kinematic plausibility."""
        hard_flag = False
        details = {
            "is_inside_boundary": is_inside_boundary,
            "distance_meters": distance_meters,
            "gps_accuracy": gps_accuracy,
            "is_mock": is_mock,
            "velocity_mps": velocity_mps,
        }

        if gps_accuracy > 100.0 or is_mock:
            score = 0.0
            status = "FAIL"
            details["flag"] = "EXCESSIVE_INACCURACY_OR_MOCK"
            hard_flag = True
        elif velocity_mps > 50.0:
            score = 0.0
            status = "FAIL"
            details["flag"] = "KINEMATIC_VELOCITY_ANOMALY"
            hard_flag = True
        else:
            if is_inside_boundary:
                containment = 1.0
            elif distance_meters <= 50.0:
                containment = 0.85
            elif distance_meters <= 150.0:
                containment = 0.50
            else:
                containment = max(0.0, 1.0 - (distance_meters / 500.0))

            # Accuracy multiplier
            if gps_accuracy <= 10.0:
                acc_mult = 1.0
            elif gps_accuracy <= 50.0:
                acc_mult = 0.90
            else:
                acc_mult = 0.70

            score = round(containment * acc_mult, 3)
            status = "PASS" if score >= 0.70 else "WARNING"

        return RadarDimensionScore(
            name="Spatial Proximity",
            score=score,
            weight=self.WEIGHT_SPATIAL,
            weighted_score=round(score * self.WEIGHT_SPATIAL, 4),
            status=status,
            details=details,
        )

    def compute_forensic_axis(
        self,
        laplacian_variance: float = 120.0,
        exposure_clipping_pct: float = 5.0,
        ela_variance: float = 0.02,
        noise_disparity: float = 0.01,
        is_duplicate: bool = False,
        has_exif: bool = True,
    ) -> RadarDimensionScore:
        """Evaluates AI image forensics, blur, and deduplication."""
        details = {
            "laplacian_variance": laplacian_variance,
            "exposure_clipping_pct": exposure_clipping_pct,
            "ela_variance": ela_variance,
            "noise_disparity": noise_disparity,
            "is_duplicate": is_duplicate,
            "has_exif": has_exif,
        }

        if is_duplicate:
            score = 0.0
            status = "FAIL"
            details["flag"] = "DUPLICATE_IMAGE_DETECTED"
        else:
            # Blur subscore
            s_blur = 1.0 if laplacian_variance >= 100.0 else (0.70 if laplacian_variance >= 50.0 else 0.30)
            # Exposure subscore
            s_exp = 1.0 if exposure_clipping_pct <= 15.0 else (0.70 if exposure_clipping_pct <= 35.0 else 0.30)
            # Tamper subscore (exempt if genuine EXIF camera image)
            is_tamper = (ela_variance > 0.05 or noise_disparity > 0.04) and not has_exif
            s_tamper = 0.20 if is_tamper else 1.0
            s_dedup = 1.0

            score = round(0.25 * s_blur + 0.20 * s_exp + 0.30 * s_dedup + 0.25 * s_tamper, 3)
            status = "PASS" if score >= 0.70 else "WARNING"

        return RadarDimensionScore(
            name="AI Forensics",
            score=score,
            weight=self.WEIGHT_FORENSIC,
            weighted_score=round(score * self.WEIGHT_FORENSIC, 4),
            status=status,
            details=details,
        )

    def compute_phenology_axis(
        self,
        crop_match: bool = True,
        stage_consistent: bool = True,
        match_confidence: float = 0.90,
    ) -> RadarDimensionScore:
        """Evaluates crop classification and agricultural stage progression."""
        s_crop = round(match_confidence, 3) if crop_match else 0.20
        s_stage = 1.0 if stage_consistent else 0.40
        score = round(0.65 * s_crop + 0.35 * s_stage, 3)
        status = "PASS" if score >= 0.70 else ("WARNING" if score >= 0.40 else "FAIL")

        return RadarDimensionScore(
            name="Crop Phenology",
            score=score,
            weight=self.WEIGHT_PHENOLOGY,
            weighted_score=round(score * self.WEIGHT_PHENOLOGY, 4),
            status=status,
            details={
                "crop_match": crop_match,
                "stage_consistent": stage_consistent,
                "match_confidence": match_confidence,
            },
        )

    def evaluate_radar(
        self,
        crypto_score: RadarDimensionScore,
        spatial_score: RadarDimensionScore,
        forensic_score: RadarDimensionScore,
        phenology_score: RadarDimensionScore,
    ) -> RadarEvaluationResult:
        """Computes composite confidence and executes human review routing."""
        c = (
            crypto_score.weighted_score
            + spatial_score.weighted_score
            + forensic_score.weighted_score
            + phenology_score.weighted_score
        )
        composite_confidence = round(c, 3)

        hard_flags: List[str] = []
        if crypto_score.score < 1.0:
            hard_flags.append("CRYPTO_INTEGRITY_COMPROMISED")
        if spatial_score.status == "FAIL":
            hard_flags.append("SPATIAL_GATE_VIOLATION")
        if forensic_score.status == "FAIL":
            hard_flags.append("FORENSIC_TAMPER_OR_DUPLICATE")
        if phenology_score.status == "FAIL":
            hard_flags.append("CROP_CATEGORY_MISMATCH")

        can_auto_approve = (
            composite_confidence >= self.AUTO_APPROVE_THRESHOLD
            and crypto_score.score == 1.0
            and spatial_score.score >= 0.70
            and forensic_score.score >= 0.70
            and not hard_flags
        )

        if can_auto_approve:
            routing = "AUTO_APPROVE"
            queue = "BATCH_LEDGER_QUEUE"
            officer = None
            note = f"Composite confidence {composite_confidence:.2f} >= {self.AUTO_APPROVE_THRESHOLD}. Approved for ledger batching."
        else:
            routing = "OFFICER_REVIEW_REQUIRED"
            queue = "EVIDENCE_INTEGRITY_OFFICER_QUEUE"
            officer = self.DEFAULT_OFFICER
            if hard_flags:
                note = f"Hard flags present: {', '.join(hard_flags)}. Routed to {self.DEFAULT_OFFICER}."
            else:
                note = f"Composite confidence {composite_confidence:.2f} < {self.AUTO_APPROVE_THRESHOLD}. Routed to {self.DEFAULT_OFFICER}."

        axes = {
            "crypto": asdict(crypto_score),
            "spatial": asdict(spatial_score),
            "forensic": asdict(forensic_score),
            "phenology": asdict(phenology_score),
        }

        return RadarEvaluationResult(
            composite_confidence=composite_confidence,
            axes=axes,
            routing_action=routing,
            assigned_queue=queue,
            assigned_officer=officer,
            hard_flags=hard_flags,
            governance_note=note,
        )

