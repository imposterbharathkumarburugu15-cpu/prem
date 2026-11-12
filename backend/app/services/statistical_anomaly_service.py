"""Statistical Anomaly Detection Engine (Capability 13 - P1).
Provides rigorous mathematical and statistical fraud detection across supply-chain data:
1. Yield Density Outliers: Evaluates yield/hectare (kg/ha) against regional cohort using
   parametric (Z-Score) and non-parametric (IQR Tukey fence) methods.
2. Benford's Law Analysis: Validates natural distribution of leading digits across transaction
   weights and financial records using Pearson's Chi-Square (χ²) test to detect fabricated data.
3. Transaction Velocity / Burst Spikes: Detects abnormal volume spikes from individual actors.
4. All anomalies generate structured evidence reports routed to the Evidence Integrity Officer.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import math
from collections import Counter


@dataclass
class YieldAnomalyResult:
    is_outlier: bool
    yield_kg_per_ha: float
    cohort_mean: float
    cohort_std: float
    z_score: float
    iqr_q1: float
    iqr_q3: float
    tukey_upper_bound: float
    anomaly_severity: str  # NONE, MILD_OUTLIER, SEVERE_INFLATION, DEFICIT
    routed_to_eio: bool
    explanation: str


@dataclass
class BenfordsLawResult:
    sample_size: int
    digit_counts: Dict[int, int]
    observed_frequencies: Dict[int, float]
    expected_frequencies: Dict[int, float]
    chi_square_statistic: float
    critical_value_p05: float  # 15.507 for df=8 at alpha=0.05
    is_conforming: bool
    anomaly_flag: str  # NATURAL_DISTRIBUTION, SUSPICIOUS_MANIPULATION, FABRICATED_WEIGHTS
    routed_to_eio: bool
    explanation: str


@dataclass
class VelocitySpikeResult:
    is_spike: bool
    current_interval_volume: float
    historical_baseline_mean: float
    spike_ratio: float
    threshold_ratio: float
    routed_to_eio: bool
    explanation: str


class StatisticalAnomalyService:
    """Detects data anomalies using statistical and mathematical tests."""

    # Benford's Law theoretical frequencies for digits 1..9: log10(1 + 1/d)
    BENFORD_THEORETICAL: Dict[int, float] = {
        d: math.log10(1.0 + 1.0 / d) for d in range(1, 10)
    }
    # Critical value for Chi-Square with 8 degrees of freedom at alpha=0.05
    CHI_SQUARE_CRITICAL_DF8_ALPHA05 = 15.507
    CHI_SQUARE_CRITICAL_DF8_ALPHA01 = 20.090

    @classmethod
    def evaluate_yield_anomaly(
        cls,
        farm_yield_kg: float,
        farm_area_ha: float,
        cohort_yields_kg_per_ha: List[float],
    ) -> YieldAnomalyResult:
        """Evaluates farm productivity (kg/ha) against peer cohort in the same region and season."""
        if farm_area_ha <= 0.0 or farm_yield_kg < 0.0:
            raise ValueError("Farm area must be positive and yield cannot be negative")

        observed_yield_per_ha = round(farm_yield_kg / farm_area_ha, 2)

        if not cohort_yields_kg_per_ha or len(cohort_yields_kg_per_ha) < 3:
            # Insufficient peer data for statistical bounds
            return YieldAnomalyResult(
                is_outlier=False,
                yield_kg_per_ha=observed_yield_per_ha,
                cohort_mean=observed_yield_per_ha,
                cohort_std=0.0,
                z_score=0.0,
                iqr_q1=observed_yield_per_ha,
                iqr_q3=observed_yield_per_ha,
                tukey_upper_bound=observed_yield_per_ha * 2.0,
                anomaly_severity="NONE",
                routed_to_eio=False,
                explanation="Insufficient cohort data (n < 3) to establish statistical boundaries.",
            )

        n = len(cohort_yields_kg_per_ha)
        mean_val = sum(cohort_yields_kg_per_ha) / n
        variance = sum((x - mean_val) ** 2 for x in cohort_yields_kg_per_ha) / max(1, n - 1)
        std_dev = math.sqrt(variance)

        # Z-Score
        z_score = (observed_yield_per_ha - mean_val) / std_dev if std_dev > 1e-4 else 0.0
        z_score = round(z_score, 2)

        # Quartiles & IQR
        sorted_cohort = sorted(cohort_yields_kg_per_ha)
        q1_idx = int(n * 0.25)
        q3_idx = int(n * 0.75)
        q1 = sorted_cohort[q1_idx]
        q3 = sorted_cohort[q3_idx]
        iqr = q3 - q1
        tukey_upper = round(q3 + 1.5 * iqr, 2)
        tukey_extreme = round(q3 + 3.0 * iqr, 2)

        # Classify Severity
        if observed_yield_per_ha > tukey_extreme or z_score >= 3.0:
            severity = "SEVERE_INFLATION"
            is_outlier = True
            routed = True
            exp = f"Severe yield inflation: {observed_yield_per_ha} kg/ha (Z={z_score:+.2f}, Tukey bound {tukey_upper} kg/ha). Potential ghost harvest laundering."
        elif observed_yield_per_ha > tukey_upper or z_score >= 2.0:
            severity = "MILD_OUTLIER"
            is_outlier = True
            routed = True
            exp = f"Yield exceeds upper quartile bounds: {observed_yield_per_ha} kg/ha (Z={z_score:+.2f}). Requires harvest inspection."
        elif z_score <= -2.5:
            severity = "DEFICIT"
            is_outlier = True
            routed = False  # Deficit alone is crop loss, not fraud
            exp = f"Significant crop deficit: {observed_yield_per_ha} kg/ha (Z={z_score:+.2f}). Crop failure/pest loss indicated."
        else:
            severity = "NONE"
            is_outlier = False
            routed = False
            exp = f"Yield {observed_yield_per_ha} kg/ha conforms to regional cohort (Mean: {mean_val:.1f}, Z: {z_score:+.2f})."

        return YieldAnomalyResult(
            is_outlier=is_outlier,
            yield_kg_per_ha=observed_yield_per_ha,
            cohort_mean=round(mean_val, 2),
            cohort_std=round(std_dev, 2),
            z_score=z_score,
            iqr_q1=round(q1, 2),
            iqr_q3=round(q3, 2),
            tukey_upper_bound=tukey_upper,
            anomaly_severity=severity,
            routed_to_eio=routed,
            explanation=exp,
        )

    @classmethod
    def test_benfords_law(cls, numbers: List[float]) -> BenfordsLawResult:
        """Applies Pearson's Chi-Square test against Benford's Law on leading digits."""
        leading_digits: List[int] = []
        for num in numbers:
            val = abs(num)
            if val < 1e-6:
                continue
            # Extract first significant digit
            s = f"{val:.10f}".lstrip("0.")
            if s and s[0].isdigit():
                d = int(s[0])
                if 1 <= d <= 9:
                    leading_digits.append(d)

        sample_size = len(leading_digits)
        if sample_size < 30:
            # Need minimum sample size for reliable chi-square test
            return BenfordsLawResult(
                sample_size=sample_size,
                digit_counts={},
                observed_frequencies={},
                expected_frequencies=cls.BENFORD_THEORETICAL,
                chi_square_statistic=0.0,
                critical_value_p05=cls.CHI_SQUARE_CRITICAL_DF8_ALPHA05,
                is_conforming=True,
                anomaly_flag="NATURAL_DISTRIBUTION",
                routed_to_eio=False,
                explanation=f"Sample size (n={sample_size}) too small for Benford Chi-Square test (minimum 30 required).",
            )

        counts = Counter(leading_digits)
        observed_freq: Dict[int, float] = {}
        chi_sq = 0.0

        for d in range(1, 10):
            obs_count = counts.get(d, 0)
            obs_freq = obs_count / sample_size
            observed_freq[d] = round(obs_freq, 4)
            exp_count = cls.BENFORD_THEORETICAL[d] * sample_size
            chi_sq += ((obs_count - exp_count) ** 2) / exp_count

        chi_sq = round(chi_sq, 3)
        is_conforming = chi_sq <= cls.CHI_SQUARE_CRITICAL_DF8_ALPHA05

        if chi_sq > cls.CHI_SQUARE_CRITICAL_DF8_ALPHA01:
            flag = "FABRICATED_WEIGHTS"
            routed = True
            exp = f"Severe Benford deviation (χ²={chi_sq} > critical {cls.CHI_SQUARE_CRITICAL_DF8_ALPHA01}). Highly unnatural digit distribution, indicative of manual fabrication."
        elif chi_sq > cls.CHI_SQUARE_CRITICAL_DF8_ALPHA05:
            flag = "SUSPICIOUS_MANIPULATION"
            routed = True
            exp = f"Moderate Benford anomaly (χ²={chi_sq} > critical {cls.CHI_SQUARE_CRITICAL_DF8_ALPHA05}). Discrepancy flagged for human review."
        else:
            flag = "NATURAL_DISTRIBUTION"
            routed = False
            exp = f"Leading digit distribution conforms naturally to Benford's Law (χ²={chi_sq} <= {cls.CHI_SQUARE_CRITICAL_DF8_ALPHA05})."

        return BenfordsLawResult(
            sample_size=sample_size,
            digit_counts=dict(counts),
            observed_frequencies=observed_freq,
            expected_frequencies={d: round(v, 4) for d, v in cls.BENFORD_THEORETICAL.items()},
            chi_square_statistic=chi_sq,
            critical_value_p05=cls.CHI_SQUARE_CRITICAL_DF8_ALPHA05,
            is_conforming=is_conforming,
            anomaly_flag=flag,
            routed_to_eio=routed,
            explanation=exp,
        )

    @classmethod
    def evaluate_velocity_spike(
        cls,
        current_volume: float,
        historical_volumes: List[float],
        threshold_ratio: float = 3.0,
    ) -> VelocitySpikeResult:
        """Detects sudden volume spikes compared to entity's rolling average."""
        if not historical_volumes:
            return VelocitySpikeResult(
                is_spike=False,
                current_interval_volume=current_volume,
                historical_baseline_mean=current_volume,
                spike_ratio=1.0,
                threshold_ratio=threshold_ratio,
                routed_to_eio=False,
                explanation="No historical baseline available; transaction registered as initial datum.",
            )

        mean_baseline = sum(historical_volumes) / len(historical_volumes)
        if mean_baseline <= 0:
            ratio = float("inf") if current_volume > 0 else 1.0
        else:
            ratio = round(current_volume / mean_baseline, 2)

        is_spike = ratio >= threshold_ratio and current_volume > 500.0  # Only trigger on substantive absolute volume

        exp = (
            f"Volume spike detected: current {current_volume} kg is {ratio:.1f}x historical baseline {mean_baseline:.1f} kg (Threshold: {threshold_ratio}x)."
            if is_spike
            else f"Transaction volume {current_volume} kg within normal operational baseline ({ratio:.1f}x baseline)."
        )

        return VelocitySpikeResult(
            is_spike=is_spike,
            current_interval_volume=current_volume,
            historical_baseline_mean=round(mean_baseline, 2),
            spike_ratio=ratio,
            threshold_ratio=threshold_ratio,
            routed_to_eio=is_spike,
            explanation=exp,
        )

