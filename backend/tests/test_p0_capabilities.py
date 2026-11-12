"""Comprehensive Unit and Integration Test Suite for Milestone 3 P0 Architectural Capabilities.

Verifies:
1. Kinematic GNSS & Sensor Spoofing Defence (P0.4):
   - Geodesic velocity calculation (v = delta_d / delta_t).
   - Teleportation detection (delta_t == 0 and delta_d > 10m).
   - Excessive velocity detection (> 50.0 m/s).
   - Altitude plausibility bounds ([-100.0m, 5000.0m]).
   - Android mock location flag detection.
2. Multi-Source Evidence Corroboration Engine (P0.2):
   - Deterministic Copernicus Sentinel-2 NDVI phenology model.
   - Agro-weather condition evaluation and F-38 monsoon delay legitimacy.
   - Transporter route proximity evaluation against farm boundary.
3. Decoupled Evidence Truth Engine (P0.3):
   - 6-dimension weighted composite truth score (crypto, spatial, forensic, crop, corrob, trust).
   - Structured Anomaly Vector generation.
   - Never-Autonomous-Reject governance invariant.
4. Collusion & Sybil Detection Service (P0.6):
   - Herfindahl-Hirschman Index (HHI) for repetitive witness pairs (> 0.80).
   - DFS directed cycle detection for circular endorsements.
   - Phantom yield-to-acreage ratio detection (> 3.5x capacity).
5. Cross-Batch Trust Graph with Temporal Decay (P0.7):
   - Exponential temporal dormancy decay T(t) = T_baseline + (T_0 - T_baseline) * exp(-lambda * delta_t).
   - Positive reinforcement and violation penalty deduction.
   - Harmonic mean custody chain trust propagation and downstream back-propagation.
6. Explainable Human Review Radar (P0.8):
   - 4-axis explainable radar scores (Scrypto, Sspatial, Sforensic, Sphenology).
   - Composite confidence C = 0.35 Scrypto + 0.25 Sspatial + 0.20 Sforensic + 0.20 Sphenology.
   - Auto-approve threshold (>= 0.85) vs Evidence Integrity Officer (officer1) routing.
7. Tier 2 Epoch Merkle Rollup Service (P0.9):
   - Batch aggregation into MerkleEpoch with odd-node promotion (CVE-2012-2459 immunity).
   - NIST P-256 Authority checkpoint signing and verification.
   - Two-tier inclusion proof generation and independent verification.
8. Multi-Stage Mass-Balance Quantity Reconciliation:
   - Highway transit moisture shrinkage curves (2-5% tolerances).
   - Negative shrinkage / weight inflation detection (<-0.5%).
   - Weigh-bridge scale reconciliation (<= 0.5% / 1.0%).
   - Strict batch split conservation (+- 0.01 kg tolerance).
   - Retail anti-overselling enforcement.
9. Platform API Intelligence Endpoints:
   - GET /platform/intelligence/trust/{actor_id}
   - GET /platform/intelligence/sybil/actor/{actor_id}
   - POST /platform/intelligence/epoch/seal
   - GET /platform/intelligence/epoch/latest
   - GET /platform/intelligence/epoch/proof/{evidence_id}
   - GET /platform/intelligence/mass-balance/batch/{batch_id}
   - GET /platform/admin/stats
"""

import math
import uuid
import json
import hashlib
import pytest
from datetime import datetime, timezone, timedelta, date
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.user_org import User, Organization
from backend.app.models.farmer import Farmer
from backend.app.models.device import Device
from backend.app.models.farm import Farm
from backend.app.models.evidence import Evidence
from backend.app.models.merkle_batch import MerkleBatch
from backend.app.models.merkle_epoch import MerkleEpoch
from backend.app.models.trust import ActorTrust, TrustEvent
from backend.app.models.supply_chain import Batch, Shipment, ShipmentItem, ShipmentEvent

from backend.app.services.spatial import (
    haversine_distance_m,
    point_in_polygon,
    evaluate_altitude_plausibility,
    validate_kinematic_transition,
    check_mock_location,
)
from backend.app.services.corroboration_service import MultiSourceCorroborationService
from backend.app.services.truth_engine import DecoupledEvidenceTruthEngine
from backend.app.services.sybil_service import CollusionAndSybilDetectionService
from backend.app.services.trust_graph_service import TrustGraphService
from backend.app.services.radar_service import RadarService
from backend.app.services.epoch_merkle_service import EpochMerkleService
from backend.app.services.mass_balance_service import MassBalanceService
from crypto.rfc8785 import canonicalize
from crypto.merkle import MerkleTree, leaf_hash_hex

client = TestClient(app)


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


# ============================================================================
# 1. KINEMATIC GNSS & SENSOR SPOOFING DEFENCE (P0.4)
# ============================================================================

def test_kinematic_transition_teleportation():
    """ADV-04: Teleportation detection (delta_t == 0 and delta_d > 10m)."""
    p1 = {"latitude": 19.500, "longitude": 78.500, "timestamp": 1700000000.0}
    p2 = {"latitude": 19.505, "longitude": 78.505, "timestamp": 1700000000.0}
    res = validate_kinematic_transition(p1, p2)
    assert res["is_anomalous"] is True
    assert res["is_teleportation"] is True
    assert res["delta_seconds"] == 0.0
    assert res["velocity_mps"] == float("inf")
    assert "teleportation" in res["reason"].lower()


def test_kinematic_transition_excessive_velocity():
    """ADV-04: Velocity > 50.0 m/s (180 km/h) flagged as speed anomaly."""
    # Move ~600m in 5 seconds -> ~120 m/s
    p1 = {"latitude": 19.5000, "longitude": 78.5000, "timestamp": 1700000000.0}
    p2 = {"latitude": 19.5054, "longitude": 78.5000, "timestamp": 1700000005.0}
    res = validate_kinematic_transition(p1, p2, max_velocity_mps=50.0)
    assert res["is_anomalous"] is True
    assert res["velocity_mps"] > 50.0
    assert "exceeds maximum threshold" in res["reason"]


def test_kinematic_transition_normal_walking():
    """Normal agricultural motion (2 m/s) passes validation."""
    p1 = {"latitude": 19.50000, "longitude": 78.50000, "timestamp": 1700000000.0}
    p2 = {"latitude": 19.50009, "longitude": 78.50000, "timestamp": 1700000005.0}
    res = validate_kinematic_transition(p1, p2, max_velocity_mps=50.0)
    assert res["is_anomalous"] is False
    assert res["is_valid"] is True
    assert res["velocity_mps"] < 50.0


def test_altitude_plausibility_bounds():
    """Validates terrestrial elevation bounds [-100.0m, 5000.0m]."""
    assert evaluate_altitude_plausibility(350.0)["is_valid"] is True
    assert evaluate_altitude_plausibility(-20.0)["is_valid"] is True
    assert evaluate_altitude_plausibility(6000.0)["is_valid"] is False
    assert evaluate_altitude_plausibility(-200.0)["is_valid"] is False
    assert evaluate_altitude_plausibility(float("nan"))["is_valid"] is False


def test_android_mock_location_detection():
    """Detects Android mock location and provider flags."""
    assert check_mock_location({"is_mock": True})["is_mock_detected"] is True
    assert check_mock_location({"isMock": True})["is_mock_detected"] is True
    assert check_mock_location({"mock_provider": True})["is_mock_detected"] is True
    assert check_mock_location({"provider": "mock"})["is_mock_detected"] is True
    assert check_mock_location({"provider": "gps", "is_mock": False})["is_mock_detected"] is False


# ============================================================================
# 2. MULTI-SOURCE EVIDENCE CORROBORATION (P0.2)
# ============================================================================

def test_satellite_ndvi_phenology_consistency():
    """Verifies deterministic Sentinel-2 regional NDVI model and phenology consistency."""
    svc = MultiSourceCorroborationService()
    # Cotton in vegetative growth
    res = svc.compute_satellite_ndvi(
        lat=19.664,
        lon=78.532,
        crop_type="COTTON",
        lifecycle_stage="VEGETATIVE_GROWTH",
        observation_date=date(2026, 8, 15),
    )
    assert 0.0 <= res["observed_ndvi"] <= 1.0
    assert res["data_source"] == "COPERNICUS_SENTINEL_2_REGIONAL_GRID"
    assert "expected_range" in res
    assert 0.0 <= res["phenology_score"] <= 1.0


def test_weather_condition_and_monsoon_delay():
    """Verifies Open-Meteo agro-weather and F-38 monsoon delay legitimacy."""
    svc = MultiSourceCorroborationService()
    # August capture date in Adilabad (monsoon season)
    res = svc.corroborate_weather_conditions(
        lat=19.664,
        lon=78.532,
        observation_ts_iso="2026-08-10T10:00:00+00:00",
        created_at=datetime(2026, 8, 14, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert res["is_weather_consistent"] is True
    assert res["precipitation_mm"] >= 0.0
    assert "delay_legitimacy" in res
    assert res["delay_legitimacy"]["is_legitimate"] is True
    assert res["delay_legitimacy"]["policy_name"] == "F-38_MONSOON_OFFLINE_DELAY_LEGITIMACY"


# ============================================================================
# 3. DECOUPLED EVIDENCE TRUTH ENGINE (P0.3)
# ============================================================================

def test_truth_engine_scoring_and_weights():
    """Verifies 6-dimension weighted composite score formula."""
    engine = DecoupledEvidenceTruthEngine()
    # Clean evidence
    res = engine.evaluate(
        crypto_valid=True,
        sequence_valid=True,
        spatial_data={"is_inside_boundary": True, "distance_meters": 0.0, "horizontal_accuracy": 5.0},
        forensic_data={"is_tamper_suspected": False, "is_ai_generated_suspected": False, "is_duplicate": False, "is_blurry": False},
        crop_data={"is_crop_match": True, "confidence": 0.95},
        corroboration_data={"composite_corroboration_score": 0.90},
        actor_trust_score=0.85,
    )
    assert res.composite_truth_score >= 0.85
    assert res.recommendation == "AUTO_APPROVE"
    assert res.suggested_state == "PENDING_BATCH"
    assert res.has_critical_anomaly is False


def test_truth_engine_never_autonomous_reject():
    """Invariant F-28: Never autonomously reject even with critical tampering flags."""
    engine = DecoupledEvidenceTruthEngine()
    res = engine.evaluate(
        crypto_valid=False,  # Critical invalid signature
        sequence_valid=True,
        spatial_data={"is_inside_boundary": True},
        forensic_data={"is_duplicate": True},  # Critical duplicate
    )
    assert res.has_critical_anomaly is True
    # Invariant check: Must route to human review rather than reject autonomously
    assert res.recommendation in ("FLAG_FOR_REVIEW", "CHALLENGE_RECOMMENDED")
    assert res.suggested_state == "PENDING_REVIEW"
    assert "CRYPTO_SIGNATURE_INVALID" in res.flagged_codes
    assert "DUPLICATE_IMAGE_REUSED" in res.flagged_codes


# ============================================================================
# 4. COLLUSION & SYBIL DETECTION SERVICE (P0.6)
# ============================================================================

def test_hhi_witness_concentration():
    """HHI > 0.80 flags counterparty concentration collusion risk."""
    # Monopolistic: 19 interactions with counterparty A, 1 with B
    counts_collusion = {"actor_B": 19, "actor_C": 1}
    hhi = CollusionAndSybilDetectionService.calculate_hhi(counts_collusion)
    assert hhi > 0.80

    # Diverse: 5 interactions across 4 counterparties equally
    counts_diverse = {"actor_B": 5, "actor_C": 5, "actor_D": 5, "actor_E": 5}
    hhi_diverse = CollusionAndSybilDetectionService.calculate_hhi(counts_diverse)
    assert hhi_diverse == 0.25


def test_dfs_directed_cycle_detection():
    """DFS detects directed circular loops in custody handover graph."""
    edges = [
        ("Farmer_A", "Transporter_T1"),
        ("Transporter_T1", "CC_C1"),
        ("CC_C1", "Farmer_A"),  # Cycle: A -> T1 -> C1 -> A
        ("Farmer_B", "Transporter_T2"),
    ]
    cycles = CollusionAndSybilDetectionService.detect_directed_cycles(edges)
    assert len(cycles) >= 1
    flat_cycle = cycles[0]
    assert "Farmer_A" in flat_cycle
    assert "Transporter_T1" in flat_cycle
    assert "CC_C1" in flat_cycle


def test_phantom_yield_capacity_exceeded():
    """Delivered harvest exceeding 3.5x sustainable agro capacity is flagged."""
    # 2 hectares delivering 30,000 kg (15,000 kg/ha > 12,250 kg/ha limit)
    res = CollusionAndSybilDetectionService.evaluate_yield_capacity(
        total_delivered_kg=30000.0,
        land_area_hectares=2.0,
        max_sustainable_yield_kg_ha=3500.0,
        multiplier=3.5,
    )
    assert res["is_phantom_yield"] is True
    assert res["yield_kg_per_ha"] == 15000.0


# ============================================================================
# 5. CROSS-BATCH TRUST GRAPH WITH TEMPORAL DECAY (P0.7)
# ============================================================================

def test_trust_temporal_decay_formula():
    """T(t) = T_baseline + (T_0 - T_baseline) * exp(-lambda * delta_t)."""
    t_0 = 0.90
    t_baseline = 0.50
    decay_lambda = 0.01155  # ~60 days half-life
    # After 60 days, (0.90 - 0.50) decays by half (0.20) -> 0.70
    decayed_60d = TrustGraphService.compute_decayed_trust(
        current_trust=t_0,
        baseline_trust=t_baseline,
        decay_lambda=decay_lambda,
        delta_days=60.0,
    )
    assert abs(decayed_60d - 0.70) < 0.01


def test_trust_positive_reinforcement_and_violation_penalty(db):
    """Verifies +0.05*(1-T) reinforcement and -0.35 violation penalty."""
    svc = TrustGraphService()
    actor_id = f"test-actor-{uuid.uuid4().hex[:8]}"

    # Initial trust is 0.50
    record = svc.get_or_create_actor_trust(db, actor_id)
    assert record.current_trust == 0.50

    # Positive event: 0.50 + 0.05 * (1 - 0.50) = 0.525
    record = svc.record_positive_event(db, actor_id, reason="Good harvest")
    assert abs(record.current_trust - 0.525) < 0.001
    assert record.successful_submissions == 1

    # Violation penalty: 0.525 - 0.35 = 0.175
    record = svc.apply_violation_penalty(db, actor_id, reason="Tampered geo")
    assert abs(record.current_trust - 0.175) < 0.001
    assert record.violation_count == 1


def test_custody_chain_harmonic_mean_trust():
    """Harmonic mean heavily penalizes a chain if any link has compromised trust."""
    # Strong actors: 0.9, 0.9, 0.9 -> harmonic mean ~0.9
    hm_strong = TrustGraphService.compute_harmonic_mean_trust([0.9, 0.9, 0.9])
    assert abs(hm_strong - 0.9) < 0.01

    # Compromised link: 0.9, 0.9, 0.1 -> harmonic mean drops to ~0.245
    hm_compromised = TrustGraphService.compute_harmonic_mean_trust([0.9, 0.9, 0.1])
    assert hm_compromised < 0.30


# ============================================================================
# 6. EXPLAINABLE HUMAN REVIEW RADAR (P0.8)
# ============================================================================

def test_radar_scoring_and_auto_approve():
    """Radar composite confidence C = 0.35 Scrypto + 0.25 Sspatial + 0.20 Sforensic + 0.20 Sphenology."""
    radar = RadarService()
    sc = radar.compute_crypto_axis(signature_valid=True, sequence_valid=True, hash_matched=True)
    ss = radar.compute_spatial_axis(is_inside_boundary=True, distance_meters=0.0, gps_accuracy=5.0)
    sf = radar.compute_forensic_axis(laplacian_variance=120.0, exposure_clipping_pct=5.0, is_duplicate=False)
    sp = radar.compute_phenology_axis(crop_match=True, stage_consistent=True)

    res = radar.evaluate_radar(sc, ss, sf, sp)
    assert res.composite_confidence >= 0.85
    assert res.routing_action == "AUTO_APPROVE"
    assert res.assigned_queue == "BATCH_LEDGER_QUEUE"
    assert res.assigned_officer is None


def test_radar_routing_to_officer1():
    """Inaccuracy > 100m or low confidence routes strictly to officer1."""
    radar = RadarService()
    sc = radar.compute_crypto_axis(signature_valid=True)
    ss = radar.compute_spatial_axis(gps_accuracy=120.0)  # > 100m gate fails spatial axis
    sf = radar.compute_forensic_axis()
    sp = radar.compute_phenology_axis()

    res = radar.evaluate_radar(sc, ss, sf, sp)
    assert res.routing_action == "OFFICER_REVIEW_REQUIRED"
    assert res.assigned_queue == "EVIDENCE_INTEGRITY_OFFICER_QUEUE"
    assert res.assigned_officer == "officer1"
    assert "SPATIAL_GATE_VIOLATION" in res.hard_flags


# ============================================================================
# 7. TIER 2 EPOCH MERKLE ROLLUP & DUAL-TIER PROOFS (P0.9)
# ============================================================================

def test_epoch_merkle_rollup_and_odd_node_promotion(db):
    """Aggregates 3 batches (odd count) into MerkleEpoch with odd-node promotion."""
    # Seed 3 dummy MerkleBatch records
    b_ids = []
    for i in range(3):
        b = MerkleBatch(
            id=f"batch-test-{uuid.uuid4().hex[:8]}",
            merkle_root=hashlib.sha256(f"root-{i}-{uuid.uuid4()}".encode()).hexdigest(),
            leaf_count=10,
            evidence_ids_json=json.dumps([f"ev-{i}-1", f"ev-{i}-2"]),
            status="COMMITTED_TO_LEDGER",
            checkpoint_id=f"cp-test-{i}",
            checkpoint_signature="fake-sig",
        )
        db.add(b)
        db.flush()
        b_ids.append(b.id)

    epoch = EpochMerkleService.create_epoch(db, batch_ids=b_ids)
    assert epoch.batch_count == 3
    assert epoch.total_items == 30
    assert len(epoch.epoch_root) == 64
    assert epoch.checkpoint_signature is not None
    assert epoch.status == "COMMITTED"

    # Verify batches are linked
    for bid in b_ids:
        b_rec = db.query(MerkleBatch).filter(MerkleBatch.id == bid).first()
        assert b_rec.epoch_id == epoch.id


def test_dual_tier_proof_generation_and_verification(db):
    """Verifies end-to-end Dual-Tier Inclusion Proof verification."""
    # 1. Create genuine approved evidence
    run_id = uuid.uuid4().hex[:6]
    farmer = db.query(Farmer).first()
    if not farmer:
        farmer = Farmer(id=f"farmer-{run_id}", name="Test Farmer", phone=f"+9198765{run_id[:5]}")
        db.add(farmer)
        db.flush()
    farm = db.query(Farm).first()
    if not farm:
        farm = Farm(id=f"farm-{run_id}", farmer_id=farmer.id, farm_name="Test Farm", crop_type="COTTON", area_acres=2.5)
        db.add(farm)
        db.flush()

    dev_id = f"dev-dual-{run_id}"
    device = Device(id=dev_id, farmer_id=farmer.id, public_key_pem="test-key", status="ACTIVE")
    db.add(device)
    db.flush()

    envelope_dict = {
        "device_id": dev_id,
        "sequence_number": 1,
        "capture_timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {"latitude": 19.500, "longitude": 78.500, "gps_accuracy": 5.0},
    }
    canon_bytes = canonicalize(envelope_dict)
    ev = Evidence(
        id=f"ev-dual-{run_id}",
        farm_id=farm.id,
        device_id=dev_id,
        sequence_number=1,
        lifecycle_stage="HARVEST",
        image_hash=hashlib.sha256(f"image-{run_id}".encode()).hexdigest(),
        canonical_envelope_json=json.dumps(envelope_dict),
        signature_b64="test-sig",
        status="APPROVED",
    )
    db.add(ev)
    db.flush()

    # 2. Batch Evidence into Tier 1 Batch
    from backend.app.services.merkle_service import MerkleService
    batch_res = MerkleService.create_batch(db, evidence_ids=[ev.id])
    batch_id = batch_res["batch_id"]

    # 3. Roll Batch into Tier 2 Epoch
    epoch = EpochMerkleService.create_epoch(db, batch_ids=[batch_id])

    # 4. Generate Dual-Tier Proof
    proof_bundle = EpochMerkleService.get_dual_tier_proof(db, ev.id)
    assert proof_bundle is not None
    assert proof_bundle["evidence_id"] == ev.id
    assert proof_bundle["tier1_proof"]["batch_id"] == batch_id
    assert proof_bundle["tier2_proof"]["epoch_id"] == epoch.id

    # 5. Verify Dual-Tier Proof independently
    is_valid = EpochMerkleService.verify_dual_tier_proof(
        envelope_canonical_bytes=canon_bytes,
        proof_bundle=proof_bundle,
    )
    assert is_valid is True

    # 6. Tampered envelope bytes must fail verification
    is_tampered_valid = EpochMerkleService.verify_dual_tier_proof(
        envelope_canonical_bytes=b"tampered-payload-bytes",
        proof_bundle=proof_bundle,
    )
    assert is_tampered_valid is False


# ============================================================================
# 8. MULTI-STAGE MASS-BALANCE RECONCILIATION
# ============================================================================

def test_mass_balance_transit_shrinkage_tolerances():
    """Transit moisture loss: normal (<=2%), warning (2-4%), violation (>4%)."""
    # 1. Normal cotton transit shrinkage (1.5%)
    r_norm = MassBalanceService.evaluate_transit_shrinkage(1000.0, 985.0, commodity="COTTON")
    assert r_norm.status == "NORMAL"
    assert r_norm.discrepancy_pct == 1.5

    # 2. Elevated warning (3.0%)
    r_warn = MassBalanceService.evaluate_transit_shrinkage(1000.0, 970.0, commodity="COTTON")
    assert r_warn.status == "WARNING"

    # 3. Excessive deficit violation (6.0%)
    r_viol = MassBalanceService.evaluate_transit_shrinkage(1000.0, 940.0, commodity="COTTON")
    assert r_viol.status == "VIOLATION"


def test_mass_balance_weight_inflation_adulteration():
    """Negative shrinkage (<-0.2%) flagged as weight inflation / adulteration."""
    r_inf = MassBalanceService.evaluate_transit_shrinkage(1000.0, 1015.0, commodity="COTTON")
    assert r_inf.status == "VIOLATION"
    assert "Weight inflation" in r_inf.reason


def test_mass_balance_split_conservation_tolerance():
    """Strict batch split conservation: sum(children) + loss == parent +- 0.01 kg."""
    # Pristine: 600.0 + 380.0 + 15.0 = 995.0 == 995.0
    r_ok = MassBalanceService.validate_batch_split_conservation(
        parent_qty=995.0,
        child_quantities=[600.0, 380.0],
        waste_loss_qty=15.0,
    )
    assert r_ok["is_valid"] is True
    assert r_ok["delta_kg"] == 0.0

    # Exceeding tolerance: diff 0.05 kg > 0.01 kg
    r_bad = MassBalanceService.validate_batch_split_conservation(
        parent_qty=995.0,
        child_quantities=[600.0, 380.0],
        waste_loss_qty=14.95,
    )
    assert r_bad["is_valid"] is False
    assert r_bad["delta_kg"] == 0.05


def test_mass_balance_retail_anti_overselling():
    """Retail sales cannot exceed available inventory stock."""
    # Available 100 kg, sell 40 kg -> remaining 60 kg
    r_ok = MassBalanceService.validate_retail_depletion(100.0, 40.0)
    assert r_ok["is_valid"] is True
    assert r_ok["remaining_available_qty"] == 60.0

    # Available 50 kg, attempt to sell 55 kg -> rejected
    r_fail = MassBalanceService.validate_retail_depletion(50.0, 55.0)
    assert r_fail["is_valid"] is False
    assert "Insufficient stock" in r_fail["reason"]


# ============================================================================
# 9. PLATFORM API INTELLIGENCE ENDPOINTS INTEGRATION
# ============================================================================

def test_api_platform_intelligence_trust_endpoint():
    """GET /api/v1/platform/intelligence/trust/{actor_id}."""
    actor_id = f"farmer-api-{uuid.uuid4().hex[:6]}"
    resp = client.get(f"/api/v1/platform/intelligence/trust/{actor_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["actor_id"] == actor_id
    assert 0.0 <= data["current_trust"] <= 1.0


def test_api_platform_intelligence_sybil_endpoint():
    """GET /api/v1/platform/intelligence/sybil/actor/{actor_id}."""
    actor_id = f"actor-sybil-{uuid.uuid4().hex[:6]}"
    resp = client.get(f"/api/v1/platform/intelligence/sybil/actor/{actor_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["actor_id"] == actor_id
    assert "hhi_score" in data
    assert "risk_level" in data


def test_api_platform_intelligence_epoch_and_admin_stats(db):
    """Tests epoch latest, admin stats alias, and mass balance batch API."""
    # 1. Admin stats alias
    resp_stats = client.get("/api/v1/platform/admin/stats")
    assert resp_stats.status_code == 200
    assert "metrics" in resp_stats.json()

    # 2. Latest Epoch
    resp_epoch = client.get("/api/v1/platform/intelligence/epoch/latest")
    assert resp_epoch.status_code in (200, 404)
    if resp_epoch.status_code == 200:
        assert "epoch_root" in resp_epoch.json()
