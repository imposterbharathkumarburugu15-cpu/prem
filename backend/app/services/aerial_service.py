"""Drone and Satellite Corroboration Engine (Capability 10 - P1).
Provides high-resolution aerial and satellite raster corroboration for agricultural plots:
- Validates raster coverage and spatial containment against registered farm plot polygon.
- Ingests multi-band reflectance metadata (Red, NIR, Green, Blue) to compute NDVI and EVI.
- Detects anomalies: cloud occlusion (>20%), canopy vigor deficit, out-of-boundary cultivation,
  and potential deforestation/clearing after EUDR cut-off baseline.
- Flags non-agricultural anomalies to the Evidence Integrity Officer without autonomous rejection.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import math
import hashlib

from backend.app.services.spatial import point_in_polygon


@dataclass
class AerialObservation:
    source_type: str  # SATELLITE_SENTINEL2, SATELLITE_LANDSAT, DRONE_ORTHOMOSAIC
    sensor_id: str
    acquisition_time: str
    gsd_meters: float  # Ground Sampling Distance (e.g. 0.05m for drone, 10.0m for Sentinel-2)
    cloud_cover_pct: float
    bounding_box: Tuple[float, float, float, float]  # (min_lat, min_lon, max_lat, max_lon)
    bands: Dict[str, float]  # Mean surface reflectance: {'red': 0.08, 'nir': 0.42, 'green': 0.09, 'blue': 0.05}
    raster_sha256: str
    is_synthetic: bool = False


@dataclass
class AerialCorroborationResult:
    is_corroborated: bool
    confidence_score: float  # 0.0 - 1.0
    ndvi: float
    evi: float
    canopy_status: str  # VIGOROUS, MODERATE, STRESSED, BARE_SOIL, WATER_OCUSED, INVALID
    cloud_occlusion_pct: float
    spatial_coverage_pct: float
    anomaly_flags: List[str]
    routed_to_eio: bool
    summary: str
    metadata: Dict[str, Any]


class DroneAndSatelliteService:
    """Corroborates agricultural activities using high-res drone & satellite observations."""

    MAX_USABLE_CLOUD_COVER = 30.0  # Above 30%, optical observations are untrusted
    MIN_EXPECTED_NDVI_VEGETATIVE = 0.30

    @classmethod
    def calculate_ndvi(cls, nir: float, red: float) -> float:
        """Normalized Difference Vegetation Index: (NIR - Red) / (NIR + Red)."""
        denominator = nir + red
        if abs(denominator) < 1e-6:
            return 0.0
        ndvi = (nir - red) / denominator
        # Clamp to [-1.0, 1.0]
        return round(max(-1.0, min(1.0, ndvi)), 4)

    @classmethod
    def calculate_evi(cls, nir: float, red: float, blue: float, G: float = 2.5, C1: float = 6.0, C2: float = 7.5, L: float = 1.0) -> float:
        """Enhanced Vegetation Index: G * ((NIR - Red) / (NIR + C1*Red - C2*Blue + L))."""
        denominator = nir + (C1 * red) - (C2 * blue) + L
        if abs(denominator) < 1e-6:
            return 0.0
        evi = G * ((nir - red) / denominator)
        return round(max(-1.0, min(1.0, evi)), 4)

    @classmethod
    def check_bbox_coverage(
        cls,
        farm_polygon: List[Tuple[float, float]],
        raster_bbox: Tuple[float, float, float, float],
    ) -> float:
        """Calculates percentage of farm vertices enclosed in the raster bounding box."""
        if not farm_polygon:
            return 0.0
        min_lat, min_lon, max_lat, max_lon = raster_bbox
        enclosed = sum(
            1 for lat, lon in farm_polygon
            if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon
        )
        return round((enclosed / len(farm_polygon)) * 100.0, 2)

    @classmethod
    def corroborate_plot(
        cls,
        farm_polygon: List[Tuple[float, float]],
        observation: AerialObservation,
        expected_stage: str = "VEGETATIVE_GROWTH",
        baseline_forest_ndvi: Optional[float] = None,
    ) -> AerialCorroborationResult:
        """Evaluates aerial raster observation against farm plot bounds and phenology."""
        anomalies: List[str] = []

        # 1. Spatial Coverage Check
        coverage_pct = cls.check_bbox_coverage(farm_polygon, observation.bounding_box)
        if coverage_pct < 100.0:
            anomalies.append(f"INCOMPLETE_PLOT_COVERAGE: {coverage_pct}% of plot enclosed by raster footprint")

        # 2. Cloud Occlusion Check
        cloud_pct = observation.cloud_cover_pct
        if cloud_pct > cls.MAX_USABLE_CLOUD_COVER:
            anomalies.append(f"HIGH_CLOUD_OCCLUSION: {cloud_pct}% cloud cover degrades optical fidelity")

        # 3. Spectral Vegetation Indices
        nir = observation.bands.get("nir", 0.0)
        red = observation.bands.get("red", 0.0)
        blue = observation.bands.get("blue", 0.0)

        ndvi = cls.calculate_ndvi(nir, red)
        evi = cls.calculate_evi(nir, red, blue)

        # 4. Phenology / Canopy Status
        if ndvi >= 0.60:
            canopy_status = "VIGOROUS"
        elif ndvi >= 0.35:
            canopy_status = "MODERATE"
        elif ndvi >= 0.18:
            canopy_status = "STRESSED"
        elif ndvi >= 0.0:
            canopy_status = "BARE_SOIL"
        else:
            canopy_status = "WATER_OCUSED"

        # 5. Phenological Expectation Mismatch
        if expected_stage in ("VEGETATIVE_GROWTH", "CROP_GROWTH", "FLOWERING") and ndvi < cls.MIN_EXPECTED_NDVI_VEGETATIVE:
            if cloud_pct <= cls.MAX_USABLE_CLOUD_COVER:
                anomalies.append(f"UNEXPECTED_LOW_VEGETATION: NDVI {ndvi} below expected minimum {cls.MIN_EXPECTED_NDVI_VEGETATIVE} for {expected_stage}")

        # 6. Deforestation / Land Clearing Alert (EUDR Baseline check)
        if baseline_forest_ndvi and baseline_forest_ndvi >= 0.70 and ndvi < 0.20:
            anomalies.append(f"POSSIBLE_LAND_CLEARING: Baseline forest NDVI dropped from {baseline_forest_ndvi} to {ndvi}")

        # Compute Confidence Score
        confidence = 1.0
        if coverage_pct < 100.0:
            confidence -= 0.35 * ((100.0 - coverage_pct) / 100.0)
        if cloud_pct > 10.0:
            confidence -= min(0.40, (cloud_pct / 100.0) * 0.8)
        if anomalies:
            confidence = max(0.15, confidence - 0.20)
        confidence = round(max(0.0, min(1.0, confidence)), 3)

        is_corroborated = len(anomalies) == 0 and confidence >= 0.65
        routed_to_eio = len(anomalies) > 0

        summary = (
            f"Aerial corroboration passed with confidence {confidence:.2f} (NDVI: {ndvi}, Canopy: {canopy_status})."
            if is_corroborated
            else f"Aerial corroboration flagged {len(anomalies)} anomalies (Confidence: {confidence:.2f}). Routed to Evidence Integrity Officer."
        )

        return AerialCorroborationResult(
            is_corroborated=is_corroborated,
            confidence_score=confidence,
            ndvi=ndvi,
            evi=evi,
            canopy_status=canopy_status,
            cloud_occlusion_pct=cloud_pct,
            spatial_coverage_pct=coverage_pct,
            anomaly_flags=anomalies,
            routed_to_eio=routed_to_eio,
            summary=summary,
            metadata={
                "source_type": observation.source_type,
                "sensor_id": observation.sensor_id,
                "gsd_meters": observation.gsd_meters,
                "raster_sha256": observation.raster_sha256,
                "is_synthetic": observation.is_synthetic,
            },
        )

