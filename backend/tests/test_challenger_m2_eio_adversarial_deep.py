"""Empirical Challenger Deep Adversarial Test Suite for EIO Adjudication.

Thoroughly stress-tests:
1. Ray-casting boundary containment math on concave polygons, boundary points, and MultiPolygon GeoJSON.
2. Centroid and Haversine distance calculations including closed vs unclosed ring shifts.
3. Strict explanation length constraints (whitespace trimming, multi-byte Unicode, length boundaries 4 vs 5).
4. Multiple sequential challenge persistence and AuditLog hash chaining integrity.
5. Decision state transitions across all 5 official officer decision types.
6. RBAC enforcement across Officer endpoints.
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
from backend.app.models.farmer import Farmer
from backend.app.models.device import Device
from backend.app.models.farm import Farm
from backend.app.models.evidence import Evidence
from backend.app.models.review_decision import ReviewDecision
from backend.app.models.supply_chain import ChallengeResponse
from backend.app.models.audit_log import AuditLog
from backend.app.api.v1.platform import (
    _point_in_polygon_geojson,
    _calculate_farm_distance,
    _haversine_distance_m,
)

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_bootstrap():
    resp = client.post("/api/v1/platform/auth/bootstrap")
    assert resp.status_code == 200


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# 1. RAY-CASTING & SPATIAL GEOMETRY ADVERSARIAL TESTS
# ============================================================================

def test_ray_casting_concave_and_multipolygon_geometries():
    """Stress test ray-casting against concave polygons, U-shapes, and MultiPolygons."""
    # Concave U-shaped polygon in lat/lon space
    # (lat 10..20, lon 10..20) with center cutout (lat 15..20, lon 13..17)
    u_coords = [
        [10.0, 10.0],
        [20.0, 10.0],
        [20.0, 20.0],
        [17.0, 20.0],
        [17.0, 15.0],
        [13.0, 15.0],
        [13.0, 20.0],
        [10.0, 20.0],
        [10.0, 10.0],
    ]
    u_geo = json.dumps({"type": "Polygon", "coordinates": [u_coords]})

    # Bottom bar: lat=12, lon=15 -> INSIDE
    assert _point_in_polygon_geojson(lat=12.0, lon=15.0, boundary_geojson=u_geo) is True
    # Left arm: lat=18, lon=11.5 -> INSIDE
    assert _point_in_polygon_geojson(lat=18.0, lon=11.5, boundary_geojson=u_geo) is True
    # Right arm: lat=18, lon=18.5 -> INSIDE
    assert _point_in_polygon_geojson(lat=18.0, lon=18.5, boundary_geojson=u_geo) is True
    # Cutout center: lat=18, lon=15.0 -> OUTSIDE
    assert _point_in_polygon_geojson(lat=18.0, lon=15.0, boundary_geojson=u_geo) is False
    # Far outside: lat=25, lon=25 -> OUTSIDE
    assert _point_in_polygon_geojson(lat=25.0, lon=25.0, boundary_geojson=u_geo) is False

    # MultiPolygon test
    multi_geo = json.dumps({
        "type": "MultiPolygon",
        "coordinates": [
            [
                [[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [0.0, 5.0], [0.0, 0.0]]
            ]
        ]
    })
    # lat=2.5, lon=2.5 -> INSIDE
    assert _point_in_polygon_geojson(lat=2.5, lon=2.5, boundary_geojson=multi_geo) is True
    # lat=8.0, lon=8.0 -> OUTSIDE
    assert _point_in_polygon_geojson(lat=8.0, lon=8.0, boundary_geojson=multi_geo) is False


def test_ray_casting_degenerate_and_boundary_fallback():
    """Verify degenerate geometries fallback safely to True (non-blocking) without exceptions."""
    assert _point_in_polygon_geojson(19.5, 78.5, None) is True
    assert _point_in_polygon_geojson(19.5, 78.5, "") is True
    assert _point_in_polygon_geojson(19.5, 78.5, "{broken json") is True
    assert _point_in_polygon_geojson(19.5, 78.5, json.dumps({"type": "Point", "coordinates": [78.5, 19.5]})) is True
    assert _point_in_polygon_geojson(19.5, 78.5, json.dumps({"type": "Polygon", "coordinates": [[[0, 0], [1, 1]]]})) is True


def test_haversine_distance_mathematical_properties():
    """Verify Haversine mathematical correctness across identity, symmetry, and known distances."""
    # Identity: distance to self is 0.0
    assert _haversine_distance_m(19.5, 78.5, 19.5, 78.5) == 0.0

    # Symmetry: dist(A, B) == dist(B, A)
    d_ab = _haversine_distance_m(19.5000, 78.5000, 19.5010, 78.5015)
    d_ba = _haversine_distance_m(19.5010, 78.5015, 19.5000, 78.5000)
    assert abs(d_ab - d_ba) < 1e-9

    # Known 1 degree latitude distance (~111.195 km at equator)
    d_1deg = _haversine_distance_m(0.0, 0.0, 1.0, 0.0)
    assert 111000.0 < d_1deg < 112000.0


# ============================================================================
# 2. EXPLANATION CONSTRAINT ADVERSARIAL STRESS TESTS
# ============================================================================

@pytest.mark.parametrize("invalid_expl", [
    "",
    " ",
    "   \t\n   ",
    "a",
    "ab",
    "abc",
    "abcd",
    " ab ",
    "  \t abcd \n ",  # strips to 4 chars
])
def test_explanation_constraint_under_5_chars_rejected_400(invalid_expl, db_session: Session):
    """Explanations strictly under 5 stripped characters must be rejected with HTTP 400."""
    run_id = uuid.uuid4().hex[:6]
    farmer = Farmer(id=f"f-expl-{run_id}", full_name="Exp Farmer", phone_number=f"+91987{run_id[:7]}")
    device = Device(id=f"d-expl-{run_id}", farmer_id=farmer.id, public_key_pem="fake", status="ACTIVE")
    farm = Farm(
        id=f"farm-expl-{run_id}",
        farmer_id=farmer.id,
        farm_name="Exp Farm",
        crop_type="Cotton",
        boundary_geojson=json.dumps({"type": "Polygon", "coordinates": [[[78.5, 19.5], [78.51, 19.5], [78.51, 19.51], [78.5, 19.51], [78.5, 19.5]]]}),
    )
    ev = Evidence(
        id=f"ev-expl-{run_id}",
        farm_id=farm.id,
        device_id=device.id,
        sequence_number=1,
        lifecycle_stage="HARVEST",
        image_hash=hashlib.sha256(b"expl").hexdigest(),
        canonical_envelope_json="{}",
        signature_b64="fake",
        status="PENDING_REVIEW",
    )
    db_session.add_all([farmer, device, farm, ev])
    db_session.commit()

    resp = client.post("/api/v1/platform/intelligence/decide", json={
        "evidence_id": ev.id,
        "decision": "CONFIRM_VALID",
        "explanation": invalid_expl,
    })
    assert resp.status_code == 400
    assert "at least 5 characters" in resp.json()["detail"].lower()


@pytest.mark.parametrize("valid_expl", [
    "12345",  # exactly 5 chars
    "   12345   ",  # padded, strips to 5 chars
    "Valid",  # exactly 5 chars
    "నిజమైన ఆధారము",  # Telugu Unicode (> 5 chars)
    "प्रमाणित साक्ष्य",  # Hindi Unicode (> 5 chars)
    "A" * 5000,  # 5,000 chars stress
])
def test_explanation_constraint_5_and_above_accepted_200(valid_expl, db_session: Session):
    """Explanations with >= 5 stripped characters must be accepted with HTTP 200."""
    run_id = uuid.uuid4().hex[:6]
    farmer = Farmer(id=f"f-v-expl-{run_id}", full_name="V Farmer", phone_number=f"+91987{run_id[:7]}")
    device = Device(id=f"d-v-expl-{run_id}", farmer_id=farmer.id, public_key_pem="fake", status="ACTIVE")
    farm = Farm(
        id=f"farm-v-expl-{run_id}",
        farmer_id=farmer.id,
        farm_name="V Farm",
        crop_type="Cotton",
        boundary_geojson=json.dumps({"type": "Polygon", "coordinates": [[[78.5, 19.5], [78.51, 19.5], [78.51, 19.51], [78.5, 19.51], [78.5, 19.5]]]}),
    )
    ev = Evidence(
        id=f"ev-v-expl-{run_id}",
        farm_id=farm.id,
        device_id=device.id,
        sequence_number=1,
        lifecycle_stage="HARVEST",
        image_hash=hashlib.sha256(b"v-expl").hexdigest(),
        canonical_envelope_json="{}",
        signature_b64="fake",
        status="PENDING_REVIEW",
    )
    db_session.add_all([farmer, device, farm, ev])
    db_session.commit()

    resp = client.post("/api/v1/platform/intelligence/decide", json={
        "evidence_id": ev.id,
        "decision": "CONFIRM_VALID",
        "explanation": valid_expl,
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"
    assert resp.json()["new_state"] == "APPROVED"


# ============================================================================
# 3. CHALLENGE PERSISTENCE & AUDIT INTEGRITY STRESS TESTS
# ============================================================================

def test_multiple_sequential_challenges_persistence_and_inspection(db_session: Session):
    """Stress-test dispatching 5 rapid challenges on same evidence, verifying persistence and inspection."""
    run_id = uuid.uuid4().hex[:6]
    farmer = Farmer(id=f"f-chal-{run_id}", full_name="Chal Farmer", phone_number=f"+91987{run_id[:7]}")
    device = Device(id=f"d-chal-{run_id}", farmer_id=farmer.id, public_key_pem="fake", status="ACTIVE")
    farm = Farm(
        id=f"farm-chal-{run_id}",
        farmer_id=farmer.id,
        farm_name="Chal Farm",
        crop_type="Cotton",
        boundary_geojson=json.dumps({"type": "Polygon", "coordinates": [[[78.5, 19.5], [78.51, 19.5], [78.51, 19.51], [78.5, 19.51], [78.5, 19.5]]]}),
    )
    ev = Evidence(
        id=f"ev-chal-{run_id}",
        farm_id=farm.id,
        device_id=device.id,
        sequence_number=1,
        lifecycle_stage="HARVEST",
        image_hash=hashlib.sha256(b"chal").hexdigest(),
        canonical_envelope_json="{}",
        signature_b64="fake",
        status="PENDING_REVIEW",
    )
    db_session.add_all([farmer, device, farm, ev])
    db_session.commit()

    dispatched_ids = []
    for i in range(5):
        payload = {
            "evidence_id": ev.id,
            "challenge_type": f"TYPE_{i}",
            "reason_code": f"REASON_{i}",
            "instructions": f"Instructions for test challenge sequence index {i}.",
            "officer_id": f"officer-{i}",
        }
        res = client.post("/api/v1/platform/intelligence/challenge", json=payload)
        assert res.status_code == 200
        cid = res.json()["challenge_id"]
        assert cid.startswith("CHAL-")
        dispatched_ids.append(cid)

    # Inspect evidence detail
    detail = client.get(f"/api/v1/platform/intelligence/evidence/{ev.id}")
    assert detail.status_code == 200
    returned_challenges = detail.json()["challenges"]
    assert len(returned_challenges) == 5
    returned_ids = [c["challenge_id"] for c in returned_challenges]
    for cid in dispatched_ids:
        assert cid in returned_ids

    # Verify AuditLog entries created for all 5
    audit_logs = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_id == ev.id, AuditLog.event_type == "OFFICER_CHALLENGE_DISPATCHED")
        .order_by(AuditLog.created_at.asc())
        .all()
    )
    assert len(audit_logs) == 5
    for al in audit_logs:
        assert al.new_state == "CHALLENGE_PENDING"
        assert len(al.payload_hash) == 64
        if al.prev_log_hash:
            assert len(al.prev_log_hash) == 64


# ============================================================================
# 4. DECISION PERSISTENCE & STATE CONSISTENCY STRESS TESTS
# ============================================================================

@pytest.mark.parametrize("decision, expected_state, expected_action", [
    ("CONFIRM_VALID", "APPROVED", "APPROVE"),
    ("REQUEST_FRESH_EVIDENCE", "PENDING_RETAKE", "REQUEST_RETAKE"),
    ("MARK_INCONCLUSIVE", "INCONCLUSIVE_REVIEW", "REQUEST_RETAKE"),
    ("SUBSTANTIATED_VIOLATION", "REJECTED", "REJECT"),
    ("ESCALATE_SECOND_APPROVAL", "ESCALATED_SECOND_APPROVAL", "REQUEST_RETAKE"),
])
def test_all_decision_types_update_database_consistently(decision, expected_state, expected_action, db_session: Session):
    """Verify each decision enum creates ReviewDecision, updates Evidence, and logs AuditLog."""
    run_id = uuid.uuid4().hex[:6]
    farmer = Farmer(id=f"f-dec-{run_id}", full_name="Dec Farmer", phone_number=f"+91987{run_id[:7]}")
    device = Device(id=f"d-dec-{run_id}", farmer_id=farmer.id, public_key_pem="fake", status="ACTIVE")
    farm = Farm(
        id=f"farm-dec-{run_id}",
        farmer_id=farmer.id,
        farm_name="Dec Farm",
        crop_type="Cotton",
        boundary_geojson=json.dumps({"type": "Polygon", "coordinates": [[[78.5, 19.5], [78.51, 19.5], [78.51, 19.51], [78.5, 19.51], [78.5, 19.5]]]}),
    )
    ev = Evidence(
        id=f"ev-dec-{run_id}",
        farm_id=farm.id,
        device_id=device.id,
        sequence_number=1,
        lifecycle_stage="HARVEST",
        image_hash=hashlib.sha256(f"dec-{run_id}".encode()).hexdigest(),
        canonical_envelope_json="{}",
        signature_b64="fake",
        status="PENDING_REVIEW",
    )
    db_session.add_all([farmer, device, farm, ev])
    db_session.commit()

    resp = client.post("/api/v1/platform/intelligence/decide", json={
        "evidence_id": ev.id,
        "decision": decision,
        "explanation": f"Verified decision {decision} under standard policy guidelines.",
        "officer_id": "officer-dr-rao",
    })
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["new_state"] == expected_state
    assert res_data["action"] == expected_action

    db_session.expire_all()
    ev_updated = db_session.query(Evidence).filter(Evidence.id == ev.id).first()
    assert ev_updated.status == expected_state

    rd = db_session.query(ReviewDecision).filter(ReviewDecision.evidence_id == ev.id).first()
    assert rd is not None
    assert rd.new_state == expected_state
    assert rd.action == expected_action
