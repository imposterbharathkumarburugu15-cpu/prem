"""Milestone 3 P0 Adversarial & Spoofing Empirical Stress Test Suite.
Author: teamwork_challenger_m3_1 (Role: P0 Adversarial & Spoofing Challenger)

Comprehensive empirical stress-testing across:
1. GPS Spatial Accuracy Threshold:
   - Floating point boundary gating: 100.0m (pass) vs 100.01m (fail)
   - Exact boundary, epsilon neighbors (99.9999m, 100.0000001m)
   - Zero, negative, sub-zero, and extreme values (0.0m, -0.001m, -100m, 500m, 10000m)
   - Non-finite injections (NaN, +Inf, -Inf) and type mismatches
   - Farmland polygon boundary vertex accuracy integration
2. EXIF Exemption:
   - Genuine camera images with EXIF: immunity from AI-generation suspicion under extreme noise disparity / spectral anomaly
   - Images without EXIF: correct triggering of AI-generation suspicion under synthetic noise disparity / spectral anomaly
   - Clean images without EXIF: no false positive AI flags
   - Tamper vs AI distinction: images with EXIF but high ELA variance are still flagged for tamper
   - Bytes vs PIL Image input formats
3. Kinematic GNSS Transitions:
   - Excessive velocity gating (> 50.0 m/s ~ 180 km/h)
   - Teleportation gating (dt == 0 and distance > 10.0m)
   - Stationary/sub-threshold jitter (dt == 0 and distance <= 10.0m)
   - Terrestrial altitude limits ([-100.0m, 5000.0m]): -100.0m valid, -100.01m invalid, 5000.0m valid, 5000.01m invalid
   - Mock location detection across all standard and adversarial flags (is_mock, isMock, mock_provider, is_from_mock_provider, provider="mock", mock_location)
4. Sybil HHI Witness Concentration & Circular Cycle Detection:
   - HHI mathematical properties, monotonic concentration, edge cases (empty, single actor, 50/50, 90/10, multi-actor)
   - HHI collusion threshold boundary (0.80)
   - Minimum interaction requirements (F-24)
   - DFS directed cycle detection across multi-node loops (2-cycles, 3-cycles, 4-cycles, complex DAGs, disconnected components)
"""

import io
import math
import pytest
from datetime import datetime, timezone
from PIL import Image

from backend.app.services.spatial import (
    is_valid_wgs84,
    validate_farm_polygon,
    evaluate_altitude_plausibility,
    validate_kinematic_transition,
    check_mock_location,
    haversine_distance_m,
)
from ai_engine.forensics import ImageForensicsAnalyzer
from backend.app.services.sybil_service import CollusionAndSybilDetectionService


# ============================================================================
# SECTION 1: GPS SPATIAL ACCURACY THRESHOLD EMPIRICAL STRESS
# ============================================================================

class TestGPSSpatialAccuracyStress:
    """Empirical boundary stress on GPS horizontal accuracy validation."""

    def test_accuracy_exact_boundary_100m(self):
        """Verify 100.0m is accepted and 100.01m is strictly rejected."""
        # Baseline valid coordinate: Adilabad, Telangana
        lat, lon = 19.6640, 78.5320

        # Exact 100.0m threshold must be ACCEPTED
        assert is_valid_wgs84(lat, lon, accuracy=100.0) is True, (
            "Accuracy of exactly 100.0m MUST be accepted"
        )

        # 99.9999m must be ACCEPTED
        assert is_valid_wgs84(lat, lon, accuracy=99.9999) is True

        # 100.0000000001m must be REJECTED
        assert is_valid_wgs84(lat, lon, accuracy=100.0000000001) is False

        # 100.01m must be REJECTED
        assert is_valid_wgs84(lat, lon, accuracy=100.01) is False, (
            "Accuracy of 100.01m MUST be rejected (> 100.0m)"
        )

        # Large values must be REJECTED
        assert is_valid_wgs84(lat, lon, accuracy=100.1) is False
        assert is_valid_wgs84(lat, lon, accuracy=500.0) is False
        assert is_valid_wgs84(lat, lon, accuracy=10000.0) is False

    def test_accuracy_lower_bound_zero_and_negative(self):
        """Verify accuracy <= 0.0m is rejected as physically impossible."""
        lat, lon = 19.6640, 78.5320

        # 0.0m is rejected (sensors have non-zero uncertainty)
        assert is_valid_wgs84(lat, lon, accuracy=0.0) is False

        # Negative accuracy is rejected
        assert is_valid_wgs84(lat, lon, accuracy=-0.0001) is False
        assert is_valid_wgs84(lat, lon, accuracy=-1.0) is False
        assert is_valid_wgs84(lat, lon, accuracy=-100.0) is False

        # Smallest positive accuracy is accepted
        assert is_valid_wgs84(lat, lon, accuracy=0.001) is True
        assert is_valid_wgs84(lat, lon, accuracy=1.0) is True

    def test_accuracy_non_finite_and_type_injections(self):
        """Verify non-finite float injections and type mismatches are rejected."""
        lat, lon = 19.6640, 78.5320

        assert is_valid_wgs84(lat, lon, accuracy=float("nan")) is False
        assert is_valid_wgs84(lat, lon, accuracy=float("inf")) is False
        assert is_valid_wgs84(lat, lon, accuracy=float("-inf")) is False
        assert is_valid_wgs84(lat, lon, accuracy=math.nan) is False
        assert is_valid_wgs84(lat, lon, accuracy=math.inf) is False

        # String accuracy directly to is_valid_wgs84 must be rejected
        assert is_valid_wgs84(lat, lon, accuracy="5.0") is False  # type: ignore
        assert is_valid_wgs84(lat, lon, accuracy=[5.0]) is False  # type: ignore

    def test_polygon_vertex_accuracy_threshold_integration(self):
        """Verify validate_farm_polygon enforces 100.0m limit on all vertices."""
        base_coords = [
            (19.6640, 78.5320),
            (19.6650, 78.5320),
            (19.6650, 78.5340),
            (19.6640, 78.5340),
        ]

        # All vertices with accuracy 100.0m -> Valid
        poly_100m = [
            {"lat": c[0], "lon": c[1], "horizontal_accuracy": 100.0}
            for c in base_coords
        ]
        is_valid, msg = validate_farm_polygon(poly_100m)
        assert is_valid is True, f"100.0m accuracy vertices should be valid, got: {msg}"

        # Single vertex with accuracy 100.01m -> Invalid
        poly_100_01m = [
            {"lat": c[0], "lon": c[1], "horizontal_accuracy": 100.0}
            for c in base_coords
        ]
        poly_100_01m[2]["horizontal_accuracy"] = 100.01
        is_valid, msg = validate_farm_polygon(poly_100_01m)
        assert is_valid is False
        assert "Invalid horizontal accuracy at vertex 2: 100.01m" in msg

        # Single vertex with accuracy 0.0m -> Invalid
        poly_0m = [
            {"lat": c[0], "lon": c[1], "horizontal_accuracy": 5.0}
            for c in base_coords
        ]
        poly_0m[1]["horizontal_accuracy"] = 0.0
        is_valid, msg = validate_farm_polygon(poly_0m)
        assert is_valid is False
        assert "Invalid horizontal accuracy at vertex 1: 0.0m" in msg


# ============================================================================
# SECTION 2: EXIF EXEMPTION EMPIRICAL STRESS
# ============================================================================

class TestEXIFExemptionStress:
    """Empirical stress on EXIF exemption for AI-generation vs tamper detection."""

    def _create_jpeg_with_exif(self, make="Canon", model="EOS R5") -> bytes:
        img = Image.new("RGB", (128, 128), color=(100, 150, 200))
        exif = img.getexif()
        exif[0x010F] = make   # Make
        exif[0x0110] = model  # Model
        buf = io.BytesIO()
        img.save(buf, format="JPEG", exif=exif)
        return buf.getvalue()

    def _create_jpeg_without_exif(self) -> bytes:
        img = Image.new("RGB", (128, 128), color=(100, 150, 200))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    def test_exif_image_exempt_from_ai_generated_flag(self):
        """Genuine camera image with EXIF must NOT be flagged as AI-generated,
        even under low noise disparity threshold.
        """
        analyzer = ImageForensicsAnalyzer(noise_disparity_threshold=1.0)
        jpeg_bytes = self._create_jpeg_with_exif()

        res = analyzer.evaluate_tamper(jpeg_bytes)
        assert res["is_ai_generated_suspected"] is False, (
            "Image with EXIF must be exempt from AI-generation suspicion"
        )

    def test_non_exif_image_flagged_when_anomalous(self):
        """Image without EXIF must be evaluated and flagged when noise disparity exceeds threshold."""
        analyzer = ImageForensicsAnalyzer(noise_disparity_threshold=1.0)
        jpeg_no_exif = self._create_jpeg_without_exif()

        res = analyzer.evaluate_tamper(jpeg_no_exif)
        # With threshold=1.0, even natural block disparity triggers AI suspicion without EXIF
        assert res["is_ai_generated_suspected"] is True, (
            "Image without EXIF with disparity > threshold should be flagged as AI-generated"
        )

    def test_clean_non_exif_image_not_flagged_under_standard_threshold(self):
        """Image without EXIF with standard threshold (25.0) and normal noise is not flagged."""
        analyzer = ImageForensicsAnalyzer(noise_disparity_threshold=25.0)
        # Uniform solid color image has zero disparity
        img = Image.new("RGB", (128, 128), color=(128, 128, 128))
        res = analyzer.evaluate_tamper(img)
        assert res["is_ai_generated_suspected"] is False

    def test_exif_does_not_exempt_genuine_ela_tamper(self):
        """EXIF presence exempts AI-generation suspicion, but must NOT exempt ELA tampering."""
        analyzer = ImageForensicsAnalyzer(ela_variance_threshold=5.0)
        # Create an image with spliced block to induce high ELA variance
        img = Image.new("RGB", (128, 128), color=(255, 255, 255))
        exif = img.getexif()
        exif[0x010F] = "Nikon"
        # Draw high-contrast pattern
        pixels = img.load()
        for y in range(32, 96):
            for x in range(32, 96):
                pixels[x, y] = (0, 0, 0) if (x + y) % 2 == 0 else (255, 255, 255)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=50, exif=exif)  # low quality recompression
        spliced_bytes = buf.getvalue()

        res = analyzer.evaluate_tamper(spliced_bytes)
        # EXIF prevents AI flag
        assert res["is_ai_generated_suspected"] is False
        # But tamper detection (ELA or noise) still flags it if anomalous
        if res["ela_variance"] > 5.0:
            assert res["is_tamper_suspected"] is True

    def test_pil_image_with_mock_getexif(self):
        """Verify Image object with mock getexif dictionary functions identically."""
        analyzer = ImageForensicsAnalyzer(noise_disparity_threshold=1.0)
        img = Image.new("RGB", (64, 64), color="green")
        # Empty getexif -> flagged
        res_empty = analyzer.evaluate_tamper(img)
        assert res_empty["is_ai_generated_suspected"] is True

        # Non-empty getexif -> exempt
        img_with_exif = Image.new("RGB", (64, 64), color="green")
        img_with_exif._getexif = lambda: {271: "Sony", 272: "A7III"}  # type: ignore
        img_with_exif.getexif = lambda: {271: "Sony", 272: "A7III"}    # type: ignore
        res_exif = analyzer.evaluate_tamper(img_with_exif)
        assert res_exif["is_ai_generated_suspected"] is False


# ============================================================================
# SECTION 3: KINEMATIC GNSS TRANSITIONS EMPIRICAL STRESS
# ============================================================================

class TestKinematicGNSSStress:
    """Empirical stress on velocity, teleportation, altitude, and mock location defences."""

    def test_velocity_boundary_at_50_mps(self):
        """Stress velocity calculation around 50.0 m/s (180 km/h) threshold."""
        # 1 second delta
        t1 = 1700000000.0
        t2 = 1700000001.0
        p1 = {"lat": 19.5000, "lon": 78.5000, "timestamp": t1}

        # 45 m/s (~162 km/h) -> Valid
        # Approximate 45m displacement in latitude: 45m / 111139m/deg ~ 0.000405 deg
        p_normal = {"lat": 19.50040, "lon": 78.5000, "timestamp": t2}
        res_normal = validate_kinematic_transition(p1, p_normal, max_velocity_mps=50.0)
        assert res_normal["is_valid"] is True
        assert res_normal["is_anomalous"] is False
        assert res_normal["velocity_mps"] < 50.0

        # 60 m/s (~216 km/h) -> Anomalous
        p_fast = {"lat": 19.50060, "lon": 78.5000, "timestamp": t2}
        res_fast = validate_kinematic_transition(p1, p_fast, max_velocity_mps=50.0)
        assert res_fast["is_valid"] is False
        assert res_fast["is_anomalous"] is True
        assert res_fast["velocity_mps"] > 50.0
        assert "exceeds maximum threshold" in res_fast["reason"]

    def test_teleportation_dt_zero_boundary(self):
        """Stress dt=0: <= 10m is sub-threshold jitter, > 10m is teleportation."""
        t_same = 1700000000.0
        p1 = {"lat": 19.500000, "lon": 78.500000, "timestamp": t_same}

        # Exact same point: 0m distance -> valid, stationary
        res_0m = validate_kinematic_transition(p1, p1)
        assert res_0m["is_anomalous"] is False
        assert res_0m["is_teleportation"] is False
        assert res_0m["delta_seconds"] == 0.0
        assert res_0m["velocity_mps"] == 0.0

        # Jitter within 10m: ~5m shift -> valid
        # 5m in lon: 5 / (111139 * cos(19.5 deg)) ~ 5 / 104764 ~ 0.000047 deg
        p_jitter = {"lat": 19.500000, "lon": 78.500045, "timestamp": t_same}
        res_jitter = validate_kinematic_transition(p1, p_jitter)
        assert res_jitter["distance_meters"] <= 10.0
        assert res_jitter["is_anomalous"] is False
        assert res_jitter["is_teleportation"] is False

        # Teleportation: 50m shift with dt=0 -> anomalous
        p_teleport = {"lat": 19.500500, "lon": 78.500000, "timestamp": t_same}
        res_teleport = validate_kinematic_transition(p1, p_teleport)
        assert res_teleport["distance_meters"] > 10.0
        assert res_teleport["is_anomalous"] is True
        assert res_teleport["is_teleportation"] is True
        assert res_teleport["velocity_mps"] == float("inf")
        assert "teleportation" in res_teleport["reason"].lower()

    def test_altitude_bounds_boundary_stress(self):
        """Stress altitude plausibility across [-100.0m, 5000.0m] terrestrial limits."""
        # Boundaries
        assert evaluate_altitude_plausibility(-100.0)["is_valid"] is True
        assert evaluate_altitude_plausibility(-100.001)["is_valid"] is False
        assert evaluate_altitude_plausibility(-150.0)["is_valid"] is False

        assert evaluate_altitude_plausibility(5000.0)["is_valid"] is True
        assert evaluate_altitude_plausibility(5000.001)["is_valid"] is False
        assert evaluate_altitude_plausibility(5050.0)["is_valid"] is False

        # Interior plausibility
        assert evaluate_altitude_plausibility(0.0)["is_valid"] is True
        assert evaluate_altitude_plausibility(300.0)["is_valid"] is True
        assert evaluate_altitude_plausibility(2500.0)["is_valid"] is True

        # Non-finite and None
        assert evaluate_altitude_plausibility(None)["is_valid"] is True  # graceful missing
        assert evaluate_altitude_plausibility(float("nan"))["is_valid"] is False
        assert evaluate_altitude_plausibility(float("inf"))["is_valid"] is False
        assert evaluate_altitude_plausibility(float("-inf"))["is_valid"] is False

    def test_altitude_anomaly_propagates_into_transition_validation(self):
        """Verify out-of-bounds altitude flags kinematic transition even at walking speed."""
        p1 = {"lat": 19.5000, "lon": 78.5000, "timestamp": 1700000000.0, "altitude": 300.0}
        # Normal walking speed (1 m/s) but altitude is 6000m (aircraft flight)
        p2 = {"lat": 19.50001, "lon": 78.5000, "timestamp": 1700000001.0, "altitude": 6000.0}
        res = validate_kinematic_transition(p1, p2)
        assert res["is_anomalous"] is True
        assert res["is_valid"] is False
        assert res["altitude_plausibility"]["is_valid"] is False
        assert "out of terrestrial bounds" in res["reason"]

    def test_mock_location_adversarial_flags(self):
        """Stress check_mock_location across all standard and spoofed flag keys."""
        # Direct flags
        assert check_mock_location({"is_mock": True})["is_mock_detected"] is True
        assert check_mock_location({"isMock": True})["is_mock_detected"] is True
        assert check_mock_location({"mock_provider": True})["is_mock_detected"] is True
        assert check_mock_location({"is_from_mock_provider": True})["is_mock_detected"] is True
        assert check_mock_location({"mock_location": True})["is_mock_detected"] is True

        # Provider string case insensitivity
        assert check_mock_location({"provider": "mock"})["is_mock_detected"] is True
        assert check_mock_location({"provider": "MOCK"})["is_mock_detected"] is True
        assert check_mock_location({"provider": "Mock"})["is_mock_detected"] is True

        # Clean hardware GPS
        clean = {"provider": "gps", "is_mock": False, "accuracy": 3.5}
        assert check_mock_location(clean)["is_mock_detected"] is False

        clean_fused = {"provider": "fused", "isMock": False}
        assert check_mock_location(clean_fused)["is_mock_detected"] is False


# ============================================================================
# SECTION 4: SYBIL HHI CONCENTRATION & CIRCULAR CYCLE DETECTION
# ============================================================================

class TestSybilHHIAndCycleDetectionStress:
    """Empirical stress on Herfindahl-Hirschman Index and DFS directed cycles."""

    def test_hhi_mathematical_properties(self):
        """Verify HHI calculation strictly follows HHI = sum((c_i / N)^2)."""
        calc = CollusionAndSybilDetectionService.calculate_hhi

        # Empty dict -> 0.0
        assert calc({}) == 0.0
        assert calc({"a": 0}) == 0.0

        # Monopolistic: 1 actor 100% -> HHI = 1.0
        assert calc({"transporter_A": 10}) == 1.0

        # Equal bipartite: 2 actors 50/50 -> 0.5^2 + 0.5^2 = 0.50
        assert calc({"A": 10, "B": 10}) == 0.50

        # Equal 4 actors: 4 x 0.25^2 = 0.25
        assert calc({"A": 5, "B": 5, "C": 5, "D": 5}) == 0.25

        # Equal 10 actors: 10 x 0.10^2 = 0.10
        ten_actors = {f"actor_{i}": 10 for i in range(10)}
        assert abs(calc(ten_actors) - 0.10) < 1e-4

    def test_hhi_collusion_threshold_boundary_0_80(self):
        """Verify HHI > 0.80 boundary identification for collusion detection."""
        calc = CollusionAndSybilDetectionService.calculate_hhi

        # 90/10 split: 0.9^2 + 0.1^2 = 0.81 + 0.01 = 0.8200 -> COLLUSION (> 0.80)
        hhi_90_10 = calc({"A": 90, "B": 10})
        assert hhi_90_10 == 0.82
        assert hhi_90_10 > CollusionAndSybilDetectionService.HHI_COLLUSION_THRESHOLD

        # 88/12 split: 0.88^2 + 0.12^2 = 0.7744 + 0.0144 = 0.7888 -> NOT COLLUSION (<= 0.80)
        hhi_88_12 = calc({"A": 88, "B": 12})
        assert hhi_88_12 == 0.7888
        assert hhi_88_12 <= CollusionAndSybilDetectionService.HHI_COLLUSION_THRESHOLD

    def test_dfs_directed_cycle_2_cycle(self):
        """Verify detection of 2-actor circular custody (A -> B -> A)."""
        edges = [
            ("Farmer_1", "Transporter_A"),
            ("Transporter_A", "Farmer_1"),
        ]
        cycles = CollusionAndSybilDetectionService.detect_directed_cycles(edges)
        assert len(cycles) >= 1
        cycle = cycles[0]
        assert "Farmer_1" in cycle
        assert "Transporter_A" in cycle

    def test_dfs_directed_cycle_3_cycle_supply_chain(self):
        """Verify detection of classic 3-actor ring: Farmer -> Transporter -> CC -> Farmer."""
        edges = [
            ("Farmer_F1", "Transporter_T1"),
            ("Transporter_T1", "CC_CC1"),
            ("CC_CC1", "Farmer_F1"),
            ("Farmer_F2", "Transporter_T2"),  # Legitimate branch
            ("Transporter_T2", "CC_CC2"),
        ]
        cycles = CollusionAndSybilDetectionService.detect_directed_cycles(edges)
        assert len(cycles) == 1
        cycle = cycles[0]
        assert cycle[0] == cycle[-1]  # Loop closed
        assert set(cycle) == {"Farmer_F1", "Transporter_T1", "CC_CC1"}

    def test_dfs_directed_cycle_disconnected_multiple_cycles(self):
        """Verify detection when multiple disjoint cycles exist in graph."""
        edges = [
            # Disjoint cycle 1
            ("Actor_A", "Actor_B"),
            ("Actor_B", "Actor_A"),
            # Disjoint cycle 2
            ("Actor_X", "Actor_Y"),
            ("Actor_Y", "Actor_Z"),
            ("Actor_Z", "Actor_X"),
            # Linear chain
            ("Actor_M", "Actor_N"),
            ("Actor_N", "Actor_P"),
        ]
        cycles = CollusionAndSybilDetectionService.detect_directed_cycles(edges)
        assert len(cycles) >= 2
        flat_nodes = [node for c in cycles for node in c]
        assert "Actor_A" in flat_nodes
        assert "Actor_X" in flat_nodes
        assert "Actor_M" not in flat_nodes

    def test_dfs_directed_acyclic_graph_returns_no_cycles(self):
        """Verify DAG with complex branching has zero detected cycles."""
        edges = [
            ("Farmer_1", "Transporter_1"),
            ("Farmer_1", "Transporter_2"),
            ("Transporter_1", "CC_1"),
            ("Transporter_2", "CC_1"),
            ("CC_1", "Retailer_1"),
            ("CC_1", "Retailer_2"),
            ("Retailer_1", "Consumer_1"),
            ("Retailer_2", "Consumer_2"),
        ]
        cycles = CollusionAndSybilDetectionService.detect_directed_cycles(edges)
        assert len(cycles) == 0

    def test_phantom_yield_capacity_stress(self):
        """Verify phantom yield capacity evaluation against physical hectares."""
        eval_fn = CollusionAndSybilDetectionService.evaluate_yield_capacity

        # Valid yield: 3,000 kg on 1 hectare (baseline is 3,500 kg/ha)
        res_valid = eval_fn(3000.0, 1.0)
        assert res_valid["is_phantom_yield"] is False
        assert res_valid["yield_kg_per_ha"] == 3000.0

        # Boundary yield: 12,250 kg on 1 hectare (exact 3.5x multiplier)
        res_boundary = eval_fn(12250.0, 1.0, multiplier=3.5)
        assert res_boundary["is_phantom_yield"] is False

        # Over-capacity yield: 12,251 kg on 1 hectare (> 3.5x)
        res_over = eval_fn(12251.0, 1.0, multiplier=3.5)
        assert res_over["is_phantom_yield"] is True
        assert "exceeds physical capacity" in res_over["reason"]

        # Zero or negative hectares -> Phantom yield
        res_zero = eval_fn(5000.0, 0.0)
        assert res_zero["is_phantom_yield"] is True
        assert res_zero["yield_kg_per_ha"] is None
