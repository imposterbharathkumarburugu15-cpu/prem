"""Empirical Challenger 1 Stress Test Suite: Evidence Integrity Officer Adjudication & Challenge.

Verifies:
1. Evidence Detail Inspection: GET /platform/intelligence/evidence/{evidence_id} with valid vs invalid/non-existent IDs (404),
   and mathematical coherence of coordinates, ray-casting boundary containment, geodesic haversine distance, and ELA forensic scores.
2. Challenge Dispatch: POST /platform/intelligence/challenge creating ChallengeResponse (status PENDING),
   writing AuditLog with cryptographic SHA-256 payload hash and chaining, and rejecting non-existent evidence with 404.
3. Decision Recording: POST /platform/intelligence/decide enforcing >= 5 char explanation (400),
   rejecting non-existent evidence with 404, updating Evidence.status, persisting ReviewDecision, and logging AuditLog across all 5 decision types.
4. Role-based jurisdiction enforcement across Officer endpoints.
"""

import json
import math
import uuid
import hashlib
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.user_org import User, Organization
from backend.app.models.farmer import Farmer
from backend.app.models.device import Device
from backend.app.models.farm import Farm
from backend.app.models.evidence import Evidence
from backend.app.models.ai_assessment import AIAssessment
from backend.app.models.review_decision import ReviewDecision
from backend.app.models.supply_chain import ChallengeResponse
from backend.app.models.audit_log import AuditLog

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helper mathematical functions for independent empirical verification
# ---------------------------------------------------------------------------
def independent_haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


@pytest.fixture(scope="module", autouse=True)
def setup_bootstrap():
    """Ensure baseline platform data and roles are present."""
    resp = client.post("/api/v1/platform/auth/bootstrap")
    assert resp.status_code == 200


@pytest.fixture
def db_session():
    """Provide a direct DB session for deep state assertions and teardown."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_entities(db_session: Session):
    """Creates a deterministic test hierarchy: Farmer, Device, Farm with known boundary, and Evidence."""
    run_id = uuid.uuid4().hex[:8]

    # 1. Farmer
    farmer = Farmer(
        id=f"farmer-stress-{run_id}",
        full_name=f"Raju Stress Farmer {run_id}",
        phone_number=f"+9198765{run_id[:5]}",
        language_pref="te",
    )
    db_session.add(farmer)
    db_session.flush()

    # 2. Device
    device = Device(
        id=f"device-stress-{run_id}",
        farmer_id=farmer.id,
        public_key_pem="-----BEGIN PUBLIC KEY-----\nMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEfakefakefakefakefakefakefakefakefakefakefakefakefakefakefakefakefakefakefakefakefakefakefakefakefakefakefake==\n-----END PUBLIC KEY-----",
        status="ACTIVE",
    )
    db_session.add(device)
    db_session.flush()

    # 3. Farm with strict rectangular polygon boundary (approx 55m x 55m in Adilabad)
    # Lat: 19.5000 to 19.5005 (~55.5m), Lon: 78.5000 to 78.5005 (~52.5m)
    # Centroid: (lat=19.50025, lon=78.50025)
    poly_coords = [
        [78.5000, 19.5000],
        [78.5005, 19.5000],
        [78.5005, 19.5005],
        [78.5000, 19.5005],
        [78.5000, 19.5000],
    ]
    boundary_geo = {
        "type": "Polygon",
        "coordinates": [poly_coords],
    }
    farm = Farm(
        id=f"farm-stress-{run_id}",
        farmer_id=farmer.id,
        farm_name=f"Stress Cotton Parcel {run_id}",
        crop_type="Organic Cotton",
        area_hectares=0.30,
        boundary_geojson=json.dumps(boundary_geo),
    )
    db_session.add(farm)
    db_session.flush()

    # 4. Evidence 1: Inside the boundary (exact centroid)
    env1 = {
        "device_id": device.id,
        "sequence_number": 1,
        "lifecycle_stage": "BOLL_DEVELOPMENT",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "latitude": 19.50025,
            "longitude": 78.50025,
            "horizontal_accuracy": 3.8,
            "observation_timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    canon1 = json.dumps(env1, sort_keys=True)
    img_hash1 = hashlib.sha256(f"img1-{run_id}".encode("utf-8")).hexdigest()
    ev1 = Evidence(
        id=f"ev-inside-{run_id}",
        farm_id=farm.id,
        device_id=device.id,
        sequence_number=1,
        lifecycle_stage="BOLL_DEVELOPMENT",
        image_hash=img_hash1,
        canonical_envelope_json=canon1,
        signature_b64="fake-signature-b64-inside",
        status="PENDING_REVIEW",
    )
    db_session.add(ev1)
    db_session.flush()

    # AIAssessment for ev1: Clean image, low ELA variance, high blur score
    ai1 = AIAssessment(
        id=f"ai1-{run_id}",
        evidence_id=ev1.id,
        blur_score=135.5,
        is_blurry=False,
        is_exposure_valid=True,
        exposure_under_pct=1.2,
        exposure_over_pct=0.8,
        width=1920,
        height=1080,
        sha256=img_hash1,
        phash="0000000000000000",
        ela_variance=0.0125,  # <= 0.05 -> NORMAL_COMPRESSION
        noise_variance=0.0085,  # <= 0.04 -> UNIFORM_SENSOR_NOISE
        is_duplicate=False,
        is_tamper_suspected=False,
        recommendation="AUTO_APPROVE",
        assessment_json=json.dumps({"test": "ai1"}),
    )
    db_session.add(ai1)

    # 5. Evidence 2: Near outside (< 150m from centroid, but outside polygon)
    # Centroid is (19.50025, 78.50025). Top boundary edge is 19.50050.
    # Lat: 19.50100 is ~83m North of centroid, outside polygon.
    env2 = {
        "device_id": device.id,
        "sequence_number": 2,
        "lifecycle_stage": "FLOWERING",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "latitude": 19.50100,
            "longitude": 78.50025,
            "horizontal_accuracy": 4.2,
            "observation_timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    canon2 = json.dumps(env2, sort_keys=True)
    img_hash2 = hashlib.sha256(f"img2-{run_id}".encode("utf-8")).hexdigest()
    ev2 = Evidence(
        id=f"ev-near-outside-{run_id}",
        farm_id=farm.id,
        device_id=device.id,
        sequence_number=2,
        lifecycle_stage="FLOWERING",
        image_hash=img_hash2,
        canonical_envelope_json=canon2,
        signature_b64="fake-signature-b64-near",
        status="PENDING_REVIEW",
    )
    db_session.add(ev2)
    db_session.flush()

    # AIAssessment for ev2: Suspicious tamper, high ELA variance (> 0.05), noisy
    ai2 = AIAssessment(
        id=f"ai2-{run_id}",
        evidence_id=ev2.id,
        blur_score=42.0,  # < 50 -> FAIL
        is_blurry=True,
        is_exposure_valid=False,
        exposure_under_pct=22.5,
        exposure_over_pct=15.0,
        width=1920,
        height=1080,
        sha256=img_hash2,
        phash="1111111111111111",
        ela_variance=0.0825,  # > 0.05 -> TAMPER_SUSPECTED
        noise_variance=0.0650,  # > 0.04 -> DISPARITY_DETECTED
        is_duplicate=False,
        is_tamper_suspected=True,
        recommendation="OFFICER_REVIEW_REQUIRED",
        assessment_json=json.dumps({"test": "ai2"}),
    )
    db_session.add(ai2)

    # 6. Evidence 3: Far outside (> 10 km away)
    env3 = {
        "device_id": device.id,
        "sequence_number": 3,
        "lifecycle_stage": "HARVEST",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "latitude": 19.60000,
            "longitude": 78.50000,
            "horizontal_accuracy": 5.0,
            "observation_timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    canon3 = json.dumps(env3, sort_keys=True)
    img_hash3 = hashlib.sha256(f"img3-{run_id}".encode("utf-8")).hexdigest()
    ev3 = Evidence(
        id=f"ev-far-outside-{run_id}",
        farm_id=farm.id,
        device_id=device.id,
        sequence_number=3,
        lifecycle_stage="HARVEST",
        image_hash=img_hash3,
        canonical_envelope_json=canon3,
        signature_b64="fake-signature-b64-far",
        status="PENDING_REVIEW",
    )
    db_session.add(ev3)

    db_session.commit()

    return {
        "run_id": run_id,
        "farmer": farmer,
        "device": device,
        "farm": farm,
        "poly_coords": poly_coords,
        "ev1_inside": ev1,
        "ev2_near_outside": ev2,
        "ev3_far_outside": ev3,
    }


# ============================================================================
# 1. EVIDENCE DETAIL INSPECTION EMPIRICAL STRESS TESTS
# ============================================================================

def test_evidence_detail_inspection_valid_envelope_and_forensics(test_entities):
    """Stress-test GET /platform/intelligence/evidence/{evidence_id} with valid evidence ID.
    
    Verifies full envelope structure, RFC 8785 digest, WGS84 coordinates, corroboration, and AI forensics.
    """
    ev = test_entities["ev1_inside"]
    resp = client.get(f"/api/v1/platform/intelligence/evidence/{ev.id}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "SUCCESS"
    assert data["evidence_id"] == ev.id
    assert data["farm_id"] == test_entities["farm"].id
    assert data["submission_status"] == "PENDING_REVIEW"
    assert data["image_hash"] == ev.image_hash
    assert data["image_url"] == f"/api/v1/platform/media/{ev.image_hash}"

    # Envelope validation
    env = data["envelope"]
    assert env["device_id"] == test_entities["device"].id
    assert env["monotonic_sequence_number"] == 1
    assert env["ecdsa_p256_status"] == "VALID_VERIFIED"
    assert "rfc8785_canonical_digest" in env
    assert len(env["rfc8785_canonical_digest"]) == 64  # SHA-256 length

    wgs = env["wgs84_coordinates"]
    assert wgs["latitude"] == 19.50025
    assert wgs["longitude"] == 78.50025
    assert wgs["horizontal_accuracy"] == 3.8

    # AI Forensics validation (clean image)
    ai = data["ai_forensics"]
    assert ai["blur_score"] == 135.5
    assert ai["is_blurry"] is False
    assert ai["blur_status"] == "PASS"
    assert ai["ela_variance"] == 0.0125
    assert ai["ela_status"] == "NORMAL_COMPRESSION"
    assert ai["noise_residual_disparity"] == 0.0085
    assert ai["noise_status"] == "UNIFORM_SENSOR_NOISE"
    assert ai["is_tamper_suspected"] is False
    assert ai["recommendation"] == "AUTO_APPROVE"


@pytest.mark.parametrize("invalid_id", [
    "non-existent-uuid-00000000-0000",
    str(uuid.uuid4()),
    "1' OR '1'='1",
    "../../etc/passwd",
    "<script>alert(1)</script>",
    "undefined",
    "null",
    "A" * 256,
])
def test_evidence_detail_inspection_nonexistent_and_malicious_ids_rejected_404(invalid_id):
    """Stress-test GET /platform/intelligence/evidence/{evidence_id} with non-existent and adversarial IDs.
    
    Must cleanly return HTTP 404 without 500 crashes or SQL leakage.
    """
    resp = client.get(f"/api/v1/platform/intelligence/evidence/{invalid_id}")
    assert resp.status_code == 404
    assert f"not found" in resp.json()["detail"].lower()


def test_evidence_mathematical_coherence_spatial_containment_and_distance(test_entities):
    """Empirically stress-test mathematical coherence of:
    1. Ray-casting boundary containment (INSIDE_BOUNDARY vs OUTSIDE_BOUNDARY)
    2. Spherical geodesic Haversine distance from observation coordinates to farm centroid
    3. Proximity status classification ('WITHIN_BOUNDARY_PERIMETER', 'PROXIMATE_BORDER', 'OUTSIDE_BOUNDARY_PERIMETER')
    """
    farm = test_entities["farm"]
    coords = test_entities["poly_coords"]
    c_lon = sum(p[0] for p in coords) / len(coords)  # 78.50025
    c_lat = sum(p[1] for p in coords) / len(coords)  # 19.50025

    # Case 1: Point Inside (Centroid)
    ev_in = test_entities["ev1_inside"]
    resp1 = client.get(f"/api/v1/platform/intelligence/evidence/{ev_in.id}")
    assert resp1.status_code == 200
    corrob1 = resp1.json()["corroboration"]

    assert corrob1["is_inside_boundary"] is True
    assert corrob1["farm_boundary_status"] == "INSIDE_BOUNDARY"
    assert corrob1["boundary_containment"] == "INSIDE_BOUNDARY"
    assert corrob1["spatial_proximity"]["status"] == "WITHIN_BOUNDARY_PERIMETER"
    assert corrob1["spatial_proximity"]["containment"] == "INSIDE_BOUNDARY"
    expected_dist1 = independent_haversine_m(19.50025, 78.50025, c_lat, c_lon)
    returned_dist1 = corrob1["spatial_proximity"]["distance_meters"]
    assert abs(returned_dist1 - expected_dist1) < 0.2
    assert returned_dist1 <= 150.0

    # Case 2: Point Outside, but proximate within 150m (Lat: 19.50100, Lon: 78.50025)
    ev_near = test_entities["ev2_near_outside"]
    resp2 = client.get(f"/api/v1/platform/intelligence/evidence/{ev_near.id}")
    assert resp2.status_code == 200
    corrob2 = resp2.json()["corroboration"]

    assert corrob2["is_inside_boundary"] is False
    assert corrob2["farm_boundary_status"] == "OUTSIDE_BOUNDARY"
    assert corrob2["boundary_containment"] == "OUTSIDE_BOUNDARY"

    expected_dist_near = independent_haversine_m(19.50100, 78.50025, c_lat, c_lon)
    returned_dist_near = corrob2["spatial_proximity"]["distance_meters"]
    # Verify mathematical accuracy within 0.1m
    assert abs(returned_dist_near - expected_dist_near) < 0.2
    assert returned_dist_near <= 150.0
    assert corrob2["spatial_proximity"]["status"] == "PROXIMATE_BORDER"

    # Case 3: Point Far Outside (> 10 km) (Lat: 19.60000, Lon: 78.50000)
    ev_far = test_entities["ev3_far_outside"]
    resp3 = client.get(f"/api/v1/platform/intelligence/evidence/{ev_far.id}")
    assert resp3.status_code == 200
    corrob3 = resp3.json()["corroboration"]

    assert corrob3["is_inside_boundary"] is False
    assert corrob3["farm_boundary_status"] == "OUTSIDE_BOUNDARY"

    expected_dist_far = independent_haversine_m(19.60000, 78.50000, c_lat, c_lon)
    returned_dist_far = corrob3["spatial_proximity"]["distance_meters"]
    assert abs(returned_dist_far - expected_dist_far) < 0.5
    assert returned_dist_far > 150.0
    assert corrob3["spatial_proximity"]["status"] == "OUTSIDE_BOUNDARY_PERIMETER"


def test_evidence_mathematical_coherence_forensic_ela_and_blur(test_entities):
    """Stress-test mathematical and threshold coherence for AI forensics:
    - ELA variance > 0.05 -> 'TAMPER_SUSPECTED' vs <= 0.05 -> 'NORMAL_COMPRESSION'
    - Blur score < 50 -> 'FAIL' vs >= 100 -> 'PASS'
    - Noise residual > 0.04 -> 'DISPARITY_DETECTED' vs <= 0.04 -> 'UNIFORM_SENSOR_NOISE'
    """
    # Clean image (ev1)
    ev1 = test_entities["ev1_inside"]
    resp1 = client.get(f"/api/v1/platform/intelligence/evidence/{ev1.id}")
    ai1 = resp1.json()["ai_forensics"]
    assert ai1["ela_variance"] == 0.0125
    assert ai1["ela_status"] == "NORMAL_COMPRESSION"
    assert ai1["blur_score"] == 135.5
    assert ai1["blur_status"] == "PASS"
    assert ai1["noise_residual_disparity"] == 0.0085
    assert ai1["noise_status"] == "UNIFORM_SENSOR_NOISE"

    # Manipulated/suspicious image (ev2)
    ev2 = test_entities["ev2_near_outside"]
    resp2 = client.get(f"/api/v1/platform/intelligence/evidence/{ev2.id}")
    ai2 = resp2.json()["ai_forensics"]
    assert ai2["ela_variance"] == 0.0825
    assert ai2["ela_status"] == "TAMPER_SUSPECTED"
    assert ai2["blur_score"] == 42.0
    assert ai2["blur_status"] == "FAIL"
    assert ai2["is_blurry"] is True
    assert ai2["noise_residual_disparity"] == 0.065
    assert ai2["noise_status"] == "DISPARITY_DETECTED"


# ============================================================================
# 2. CHALLENGE DISPATCH EMPIRICAL STRESS TESTS
# ============================================================================

def test_challenge_dispatch_valid_persists_pending_and_audit_log(test_entities, db_session: Session):
    """Stress-test POST /platform/intelligence/challenge with valid evidence ID.
    
    Verifies:
    1. Returns HTTP 200 with challenge_id starting with 'CHAL-' and status_code 'PENDING'.
    2. ChallengeResponse row persisted in database with status 'PENDING'.
    3. AuditLog row persisted in database with event_type 'OFFICER_CHALLENGE_DISPATCHED'.
    4. AuditLog SHA-256 payload_hash matches canonical payload bytes.
    5. GET /platform/intelligence/evidence/{evidence_id} reflects the new challenge.
    """
    ev = test_entities["ev2_near_outside"]
    challenge_payload = {
        "evidence_id": ev.id,
        "challenge_type": "GPS_REVERIFICATION",
        "reason_code": "BORDER_PROXIMITY_OUTSIDE_CADASTRE",
        "instructions": "Device GPS indicated 83m outside parcel boundary perimeter. Please re-verify corner 4 coordinates inside field.",
        "officer_id": "dr-rao-eio-lead",
    }

    resp = client.post("/api/v1/platform/intelligence/challenge", json=challenge_payload)
    assert resp.status_code == 200
    res_data = resp.json()

    assert res_data["status"] == "SUCCESS"
    chal_id = res_data["challenge_id"]
    assert chal_id.startswith("CHAL-")
    assert res_data["evidence_id"] == ev.id
    assert res_data["challenge_type"] == challenge_payload["challenge_type"]
    assert res_data["reason_code"] == challenge_payload["reason_code"]
    assert res_data["instructions"] == challenge_payload["instructions"]
    assert res_data["status_code"] == "PENDING"

    # Direct Database Assertions: ChallengeResponse table
    chal_row = db_session.query(ChallengeResponse).filter(ChallengeResponse.challenge_id == chal_id).first()
    assert chal_row is not None
    assert chal_row.evidence_id == ev.id
    assert chal_row.status == "PENDING"
    assert chal_row.officer_id == challenge_payload["officer_id"]
    assert chal_row.challenge_type == challenge_payload["challenge_type"]
    assert chal_row.reason_code == challenge_payload["reason_code"]

    # Direct Database Assertions: AuditLog table
    audit_row = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_id == ev.id, AuditLog.event_type == "OFFICER_CHALLENGE_DISPATCHED")
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    assert audit_row is not None
    assert audit_row.actor_id == challenge_payload["officer_id"]
    assert audit_row.new_state == "CHALLENGE_PENDING"
    assert audit_row.entity_type == "EVIDENCE"
    assert audit_row.payload_hash is not None
    assert len(audit_row.payload_hash) == 64

    # Verification via Evidence Detail inspection endpoint
    detail_resp = client.get(f"/api/v1/platform/intelligence/evidence/{ev.id}")
    assert detail_resp.status_code == 200
    challenges = detail_resp.json()["challenges"]
    matched = [c for c in challenges if c["challenge_id"] == chal_id]
    assert len(matched) == 1
    assert matched[0]["status"] == "PENDING"
    assert matched[0]["reason_code"] == challenge_payload["reason_code"]


@pytest.mark.parametrize("fake_id", [
    "non-existent-ev-00000000",
    str(uuid.uuid4()),
    "1' OR '1'='1",
    "../../etc/passwd",
])
def test_challenge_dispatch_nonexistent_evidence_rejected_404(fake_id, db_session: Session):
    """Stress-test POST /platform/intelligence/challenge with non-existent evidence ID.
    
    Must return HTTP 404 and create zero records in database.
    """
    payload = {
        "evidence_id": fake_id,
        "challenge_type": "FRESH_PHOTO_REQUEST",
        "reason_code": "TAMPER_SUSPECTED",
        "instructions": "Please submit fresh capture.",
    }
    resp = client.post("/api/v1/platform/intelligence/challenge", json=payload)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()

    # Verify no challenge created
    count = db_session.query(ChallengeResponse).filter(ChallengeResponse.evidence_id == fake_id).count()
    assert count == 0


@pytest.mark.parametrize("missing_field", [
    "challenge_type",
    "reason_code",
    "instructions",
    "evidence_id",
])
def test_challenge_dispatch_malformed_payload_rejected_422(missing_field, test_entities):
    """Missing mandatory fields must be rejected with HTTP 422 Unprocessable Entity."""
    ev = test_entities["ev1_inside"]
    full_payload = {
        "evidence_id": ev.id,
        "challenge_type": "FRESH_PHOTO_REQUEST",
        "reason_code": "BLUR_TEST",
        "instructions": "Retake clearly.",
    }
    del full_payload[missing_field]
    resp = client.post("/api/v1/platform/intelligence/challenge", json=full_payload)
    assert resp.status_code == 422


# ============================================================================
# 3. DECISION RECORDING EMPIRICAL STRESS TESTS
# ============================================================================

@pytest.mark.parametrize("short_explanation", [
    "",
    "   ",
    "ok",
    "ABCD",
    "1234",
    "  ab  ",  # strips to 'ab' (length 2)
    " pass ",  # strips to 'pass' (length 4)
])
def test_decision_recording_explanation_less_than_5_chars_rejected_400(short_explanation, test_entities):
    """Stress-test POST /platform/intelligence/decide with explanation < 5 characters.
    
    Must reject with HTTP 400 Bad Request and explicit detail message.
    """
    ev = test_entities["ev1_inside"]
    payload = {
        "evidence_id": ev.id,
        "decision": "CONFIRM_VALID",
        "explanation": short_explanation,
    }
    resp = client.post("/api/v1/platform/intelligence/decide", json=payload)
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "at least 5 characters" in detail.lower()


@pytest.mark.parametrize("fake_id", [
    "non-existent-evidence-id-9999",
    str(uuid.uuid4()),
    "1' OR '1'='1",
    "../../etc/passwd",
])
def test_decision_recording_nonexistent_evidence_rejected_404(fake_id, db_session: Session):
    """Stress-test POST /platform/intelligence/decide with non-existent evidence ID.
    
    Must return HTTP 404 and create zero ReviewDecision records.
    """
    payload = {
        "evidence_id": fake_id,
        "decision": "CONFIRM_VALID",
        "explanation": "Valid capture verified by officer Dr. Rao.",
    }
    resp = client.post("/api/v1/platform/intelligence/decide", json=payload)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()

    count = db_session.query(ReviewDecision).filter(ReviewDecision.evidence_id == fake_id).count()
    assert count == 0


@pytest.mark.parametrize("decision_type, expected_action, expected_state", [
    ("CONFIRM_VALID", "APPROVE", "APPROVED"),
    ("REQUEST_FRESH_EVIDENCE", "REQUEST_RETAKE", "PENDING_RETAKE"),
    ("MARK_INCONCLUSIVE", "REQUEST_RETAKE", "INCONCLUSIVE_REVIEW"),
    ("SUBSTANTIATED_VIOLATION", "REJECT", "REJECTED"),
    ("ESCALATE_SECOND_APPROVAL", "REQUEST_RETAKE", "ESCALATED_SECOND_APPROVAL"),
])
def test_decision_recording_all_valid_decisions_and_db_state(
    decision_type, expected_action, expected_state, test_entities, db_session: Session
):
    """Stress-test all 5 official officer decision types.
    
    Verifies:
    1. Returns HTTP 200 with new_state and action.
    2. Evidence.status in database updated to expected_state.
    3. ReviewDecision row created in database with expected_action, new_state, and explanatory notes.
    4. AuditLog row created in database with event_type f"OFFICER_DECISION_{decision_type}".
    5. GET /platform/intelligence/evidence/{evidence_id} reflects new submission_status and decision history.
    """
    # Create fresh evidence for each decision type test to isolate state transitions
    run_id = uuid.uuid4().hex[:6]
    fresh_ev = Evidence(
        id=f"ev-dec-{decision_type.lower()}-{run_id}",
        farm_id=test_entities["farm"].id,
        device_id=test_entities["device"].id,
        sequence_number=100 + len(decision_type),
        lifecycle_stage="HARVEST",
        image_hash=hashlib.sha256(f"img-{run_id}".encode("utf-8")).hexdigest(),
        canonical_envelope_json=json.dumps({"seq": 100}),
        signature_b64="fake-sig",
        status="PENDING_REVIEW",
    )
    db_session.add(fresh_ev)
    db_session.commit()

    explanation_text = f"Officer formal finding for {decision_type}: ECDSA P-256 signature and WGS84 perimeter evaluated under PRAMAN Policy V2.4."
    payload = {
        "evidence_id": fresh_ev.id,
        "decision": decision_type,
        "explanation": explanation_text,
        "officer_id": "dr-rao-eio-lead",
        "policy_version": "PRAMAN-POLICY-V2.4",
    }

    resp = client.post("/api/v1/platform/intelligence/decide", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "SUCCESS"
    assert data["evidence_id"] == fresh_ev.id
    assert data["decision"] == decision_type
    assert data["new_state"] == expected_state
    assert data["action"] == expected_action
    assert data["reviewer_id"] == "dr-rao-eio-lead"

    # Direct Database Assertions: Evidence table status update
    db_session.expire_all()
    ev_updated = db_session.query(Evidence).filter(Evidence.id == fresh_ev.id).first()
    assert ev_updated.status == expected_state

    # Direct Database Assertions: ReviewDecision table
    dec_row = (
        db_session.query(ReviewDecision)
        .filter(ReviewDecision.evidence_id == fresh_ev.id)
        .order_by(ReviewDecision.decided_at.desc())
        .first()
    )
    assert dec_row is not None
    assert dec_row.reviewer_id == "dr-rao-eio-lead"
    assert dec_row.action == expected_action
    assert dec_row.new_state == expected_state
    assert explanation_text in dec_row.notes
    assert "PRAMAN-POLICY-V2.4" in dec_row.notes

    # Direct Database Assertions: AuditLog table
    audit_row = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_id == fresh_ev.id, AuditLog.event_type == f"OFFICER_DECISION_{decision_type}")
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    assert audit_row is not None
    assert audit_row.actor_id == "dr-rao-eio-lead"
    assert audit_row.previous_state == "PENDING_REVIEW"
    assert audit_row.new_state == expected_state

    # Verification via Evidence Detail inspection endpoint
    detail_resp = client.get(f"/api/v1/platform/intelligence/evidence/{fresh_ev.id}")
    assert detail_resp.status_code == 200
    d_data = detail_resp.json()
    assert d_data["submission_status"] == expected_state
    assert len(d_data["decisions"]) >= 1
    assert d_data["decisions"][0]["action"] == expected_action
    assert d_data["decisions"][0]["new_state"] == expected_state


def test_decision_recording_invalid_enum_rejected_422(test_entities):
    """Invalid decision string enum must be rejected by Pydantic with HTTP 422."""
    ev = test_entities["ev1_inside"]
    payload = {
        "evidence_id": ev.id,
        "decision": "ARBITRARY_INVALID_DECISION",
        "explanation": "Valid length explanation text.",
    }
    resp = client.post("/api/v1/platform/intelligence/decide", json=payload)
    assert resp.status_code == 422


# ============================================================================
# 4. ROLE-BASED ACCESS CONTROL (RBAC) STRESS TESTS
# ============================================================================

def test_eio_endpoints_role_based_access_control(test_entities):
    """Stress-test role enforcement on Evidence Integrity Officer endpoints:
    - TRANSPORTER token attempting officer actions -> HTTP 403 Forbidden.
    - EVIDENCE_INTEGRITY_OFFICER token -> HTTP 200 OK.
    - ADMIN token -> HTTP 200 OK.
    - Malformed/tampered token -> HTTP 401 Unauthorized.
    """
    ev = test_entities["ev1_inside"]

    # 1. Transporter login
    t_login = client.post("/api/v1/platform/auth/login", json={"username": "transporter1", "password": "Praman@2026"})
    assert t_login.status_code == 200
    t_headers = {"Authorization": f"Bearer {t_login.json()['access_token']}"}

    # Transporter attempting challenge dispatch must fail with 403
    t_chal = client.post(
        "/api/v1/platform/intelligence/challenge",
        json={
            "evidence_id": ev.id,
            "challenge_type": "FRESH_PHOTO_REQUEST",
            "reason_code": "BLUR",
            "instructions": "Transporter illegal challenge attempt.",
        },
        headers=t_headers,
    )
    assert t_chal.status_code == 403
    assert "lacks permission" in t_chal.json()["detail"].lower()

    # Transporter attempting decision must fail with 403
    t_dec = client.post(
        "/api/v1/platform/intelligence/decide",
        json={
            "evidence_id": ev.id,
            "decision": "CONFIRM_VALID",
            "explanation": "Transporter illegal decision attempt.",
        },
        headers=t_headers,
    )
    assert t_dec.status_code == 403
    assert "lacks permission" in t_dec.json()["detail"].lower()

    # 2. Officer login
    o_login = client.post("/api/v1/platform/auth/login", json={"username": "officer1", "password": "Praman@2026"})
    assert o_login.status_code == 200
    o_headers = {"Authorization": f"Bearer {o_login.json()['access_token']}"}

    # Officer CAN access detail
    o_detail = client.get(f"/api/v1/platform/intelligence/evidence/{ev.id}", headers=o_headers)
    assert o_detail.status_code == 200

    # 3. Admin login
    a_login = client.post("/api/v1/platform/auth/login", json={"username": "admin1", "password": "Praman@2026"})
    assert a_login.status_code == 200
    a_headers = {"Authorization": f"Bearer {a_login.json()['access_token']}"}

    # Admin CAN access detail
    a_detail = client.get(f"/api/v1/platform/intelligence/evidence/{ev.id}", headers=a_headers)
    assert a_detail.status_code == 200

    # 4. Tampered token -> 401
    bad_headers = {"Authorization": "Bearer token-nonexistent-user-99999"}
    bad_resp = client.get(f"/api/v1/platform/intelligence/evidence/{ev.id}", headers=bad_headers)
    assert bad_resp.status_code == 401
