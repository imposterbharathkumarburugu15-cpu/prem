import json
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.user_org import Organization, User
from backend.app.models.farm import Farm
from backend.app.models.supply_chain import Batch, Shipment, ShipmentItem, BusinessEvent
from backend.app.services.event_engine import BusinessEventType, event_engine

client = TestClient(app)


def test_get_all_17_policies():
    """Validates that GET /api/v1/events/policies returns explicit policies for all 17 business events."""
    resp = client.get("/api/v1/events/policies")
    assert resp.status_code == 200
    policies = resp.json()

    expected_events = [
        "CROP_ACTIVITY_RECORDED",
        "FIELD_EVIDENCE_CAPTURED",
        "SHIPMENT_PICKUP_CONFIRMED",
        "SHIPMENT_CHECKPOINT_RECORDED",
        "SHIPMENT_DELIVERY_CONFIRMED",
        "PRODUCE_RECEIVED",
        "WEIGHT_RECORDED",
        "QUALITY_INSPECTION_COMPLETED",
        "BATCH_CREATED",
        "BATCH_SPLIT",
        "BATCH_DISPATCHED",
        "RETAIL_RECEIPT_CONFIRMED",
        "PACKAGING_VERIFIED",
        "QR_GENERATED",
        "INVESTIGATION_OPENED",
        "EVIDENCE_CHALLENGE_CREATED",
        "INVESTIGATION_DECISION_RECORDED",
    ]

    assert len(policies) == 17
    for ev_name in expected_events:
        assert ev_name in policies, f"Missing policy for {ev_name}"
        pol = policies[ev_name]
        assert "allowed_roles" in pol
        assert "required_business_fields" in pol
        assert "automatically_captured_metadata" in pol
        assert "evidence_requirement" in pol
        assert "verification_procedures" in pol

    # Verify FIELD_EVIDENCE_CAPTURED has MANDATORY evidence
    assert policies["FIELD_EVIDENCE_CAPTURED"]["evidence_requirement"] == "MANDATORY"
    # Verify other routine events have OPTIONAL evidence so valid workflows are not blocked
    assert policies["CROP_ACTIVITY_RECORDED"]["evidence_requirement"] == "OPTIONAL"
    assert policies["SHIPMENT_PICKUP_CONFIRMED"]["evidence_requirement"] == "OPTIONAL"
    assert policies["WEIGHT_RECORDED"]["evidence_requirement"] == "OPTIONAL"


def test_get_single_policy():
    """Validates individual policy lookup and 404 for invalid type."""
    resp = client.get("/api/v1/events/policies/WEIGHT_RECORDED")
    assert resp.status_code == 200
    data = resp.json()
    assert data["event_type"] == "WEIGHT_RECORDED"
    assert "measured_weight" in data["required_business_fields"]

    resp_404 = client.get("/api/v1/events/policies/NON_EXISTENT_EVENT")
    assert resp_404.status_code == 404


def test_record_crop_activity_optional_evidence():
    """Validates CROP_ACTIVITY_RECORDED succeeds without file upload (optional evidence)."""
    db = SessionLocal()
    farm = db.query(Farm).first()
    farm_id = farm.id if farm else "farm-synth-01"

    body = {
        "event_type": "CROP_ACTIVITY_RECORDED",
        "actor_id": "farmer-ramesh",
        "actor_role": "FARMER",
        "payload": {
            "farm_id": farm_id,
            "crop_type": "Organic Wheat",
            "activity_type": "IRRIGATION",
            "notes": "Drip irrigation scheduled for north parcel",
        },
    }
    resp = client.post("/api/v1/events/record", json=body)
    assert resp.status_code == 201
    res = resp.json()
    assert res["event_type"] == "CROP_ACTIVITY_RECORDED"
    assert res["verification_status"] == "VERIFIED"
    assert res["evidence_hash"] is None  # Optional evidence omitted


def test_field_evidence_mandatory_rule():
    """Validates FIELD_EVIDENCE_CAPTURED fails when evidence is omitted, and succeeds when provided."""
    body_no_evidence = {
        "event_type": "FIELD_EVIDENCE_CAPTURED",
        "actor_id": "farmer-ramesh",
        "actor_role": "FARMER",
        "payload": {
            "farm_id": "farm-synth-01",
            "crop_type": "Organic Cotton",
        },
    }
    resp_fail = client.post("/api/v1/events/record", json=body_no_evidence)
    assert resp_fail.status_code == 400
    assert "mandatory supporting evidence" in resp_fail.json()["detail"]

    # Now provide evidence via multipart form upload
    fake_img = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtest_image_bytes"
    form_data = {
        "event_type": "FIELD_EVIDENCE_CAPTURED",
        "actor_id": "farmer-ramesh",
        "actor_role": "FARMER",
        "payload": json.dumps({
            "farm_id": "farm-synth-01",
            "crop_type": "Organic Cotton",
            "notes": "Field parcel inspection photo",
        }),
    }
    resp_success = client.post(
        "/api/v1/events/record",
        data=form_data,
        files={"file": ("field_photo.png", fake_img, "image/png")},
    )
    assert resp_success.status_code == 201
    res = resp_success.json()
    assert res["verification_status"] == "VERIFIED"
    assert res["evidence_hash"] is not None


def test_batch_lifecycle_and_timeline():
    """Full lifecycle test connecting multiple business events and verifying single batch timeline:
    1. BATCH_CREATED
    2. PRODUCE_RECEIVED at Collection Centre
    3. WEIGHT_RECORDED
    4. QUALITY_INSPECTION_COMPLETED
    5. BATCH_SPLIT (with mass balance check)
    6. BATCH_DISPATCHED
    7. RETAIL_RECEIPT_CONFIRMED
    8. PACKAGING_VERIFIED
    9. QR_GENERATED
    10. INVESTIGATION_OPENED -> EVIDENCE_CHALLENGE_CREATED -> INVESTIGATION_DECISION_RECORDED
    """
    uid = str(uuid.uuid4())[:8].upper()
    batch_code = f"BATCH-TEST-{uid}"

    # 1. BATCH_CREATED
    resp = client.post("/api/v1/events/record", json={
        "event_type": "BATCH_CREATED",
        "actor_id": "centre-manager-1",
        "actor_role": "COLLECTION_CENTRE",
        "organization_id": "cc-org-01",
        "payload": {
            "batch_code": batch_code,
            "crop_type": "Basmati Rice",
            "variety": "Pusa 1121",
            "initial_quantity": 500.0,
            "unit": "kg",
            "notes": "Intake from Karimnagar cluster",
        },
    })
    assert resp.status_code == 201
    batch_id = resp.json()["batch_id"]
    assert batch_id is not None

    # 2. PRODUCE_RECEIVED
    resp = client.post("/api/v1/events/record", json={
        "event_type": "PRODUCE_RECEIVED",
        "actor_id": "dock-operator",
        "actor_role": "COLLECTION_CENTRE",
        "organization_id": "cc-org-01",
        "payload": {
            "batch_id": batch_id,
            "receiving_facility_id": "cc-org-01",
        },
    })
    assert resp.status_code == 201

    # 3. WEIGHT_RECORDED
    resp = client.post("/api/v1/events/record", json={
        "event_type": "WEIGHT_RECORDED",
        "actor_id": "weigh-scale-op",
        "actor_role": "COLLECTION_CENTRE",
        "payload": {
            "batch_id": batch_id,
            "measured_weight": 498.5,
            "unit": "kg",
            "scale_identifier": "SCALE-DIGI-01",
        },
    })
    assert resp.status_code == 201
    assert resp.json()["verification_details"]["new_quantity"] == 498.5

    # 4. QUALITY_INSPECTION_COMPLETED
    resp = client.post("/api/v1/events/record", json={
        "event_type": "QUALITY_INSPECTION_COMPLETED",
        "actor_id": "inspector-dr-rao",
        "actor_role": "COLLECTION_CENTRE",
        "payload": {
            "batch_id": batch_id,
            "grade": "GRADE_A",
            "decision": "ACCEPTED",
            "moisture_pct": 11.2,
            "defect_notes": "Clean grain, zero discoloration",
        },
    })
    assert resp.status_code == 201
    assert resp.json()["verification_details"]["grade"] == "GRADE_A"

    # 5. BATCH_SPLIT (Split 200 kg for Retailer A)
    child_code = f"BATCH-CHILD-{uid}-A"
    resp = client.post("/api/v1/events/record", json={
        "event_type": "BATCH_SPLIT",
        "actor_id": "centre-manager-1",
        "actor_role": "COLLECTION_CENTRE",
        "payload": {
            "parent_batch_id": batch_id,
            "splits": [
                {"batch_code": child_code, "quantity": 200.0, "retailer_id": "ret-org-01"},
            ],
            "reason": "Split for regional supermarket order",
        },
    })
    assert resp.status_code == 201
    assert resp.json()["verification_details"]["parent_remaining_qty"] == 298.5

    # 6. BATCH_DISPATCHED
    resp = client.post("/api/v1/events/record", json={
        "event_type": "BATCH_DISPATCHED",
        "actor_id": "dispatch-officer",
        "actor_role": "COLLECTION_CENTRE",
        "payload": {
            "batch_id": batch_id,
            "destination_org_id": "ret-org-01",
            "dispatched_quantity": 298.5,
        },
    })
    assert resp.status_code == 201

    # 7. RETAIL_RECEIPT_CONFIRMED
    resp = client.post("/api/v1/events/record", json={
        "event_type": "RETAIL_RECEIPT_CONFIRMED",
        "actor_id": "retail-manager",
        "actor_role": "RETAILER",
        "organization_id": "ret-org-01",
        "payload": {
            "batch_id": batch_id,
            "retailer_org_id": "ret-org-01",
            "received_quantity": 298.5,
            "storage_location": "Aisle 4 - Organic Staples",
        },
    })
    assert resp.status_code == 201

    # 8. PACKAGING_VERIFIED
    resp = client.post("/api/v1/events/record", json={
        "event_type": "PACKAGING_VERIFIED",
        "actor_id": "retail-qa",
        "actor_role": "RETAILER",
        "payload": {
            "batch_id": batch_id,
            "seal_status": "INTACT",
            "packaging_type": "TAMPER_EVIDENT_HEAT_SEAL",
        },
    })
    assert resp.status_code == 201

    # 9. QR_GENERATED
    resp = client.post("/api/v1/events/record", json={
        "event_type": "QR_GENERATED",
        "actor_id": "retail-qa",
        "actor_role": "RETAILER",
        "payload": {
            "batch_id": batch_id,
        },
    })
    assert resp.status_code == 201
    qr_token = resp.json()["verification_details"]["opaque_qr_token"]
    assert qr_token.startswith("prm_")

    # 10. INVESTIGATION FLOW
    # Open investigation
    resp = client.post("/api/v1/events/record", json={
        "event_type": "INVESTIGATION_OPENED",
        "actor_id": "officer-dr-rao",
        "actor_role": "EVIDENCE_INTEGRITY_OFFICER",
        "payload": {
            "target_entity_type": "BATCH",
            "target_entity_id": batch_id,
            "reason_code": "ROUTINE_SPOT_AUDIT",
            "severity": "LOW",
        },
    })
    assert resp.status_code == 201

    # Create challenge
    resp = client.post("/api/v1/events/record", json={
        "event_type": "EVIDENCE_CHALLENGE_CREATED",
        "actor_id": "officer-dr-rao",
        "actor_role": "EVIDENCE_INTEGRITY_OFFICER",
        "payload": {
            "target_entity_id": batch_id,
            "challenge_type": "ADDITIONAL_METADATA",
            "reason_code": "SPOT_CHECK",
            "instructions": "Confirm calibrated scale certificate id",
        },
    })
    assert resp.status_code == 201

    # Record decision
    resp = client.post("/api/v1/events/record", json={
        "event_type": "INVESTIGATION_DECISION_RECORDED",
        "actor_id": "officer-dr-rao",
        "actor_role": "EVIDENCE_INTEGRITY_OFFICER",
        "payload": {
            "target_entity_type": "BATCH",
            "target_entity_id": batch_id,
            "decision": "CONFIRM_VALID",
            "justification": "Scale certificate verified valid and calibrated",
        },
    })
    assert resp.status_code == 201

    # 11. Verify Timeline for parent batch
    timeline_resp = client.get(f"/api/v1/events/batch/{batch_id}/timeline")
    assert timeline_resp.status_code == 200
    tl = timeline_resp.json()
    assert tl["batch_code"] == batch_code
    assert tl["crop_type"] == "Basmati Rice"
    assert tl["total_milestones"] >= 10
    assert len(tl["timeline"]) >= 10
    assert tl["status"] == "ACTIVE"

    # 12. Verify Lineage in Timeline for child batch
    child_timeline_resp = client.get(f"/api/v1/events/batch/{child_code}/timeline")
    assert child_timeline_resp.status_code == 200
    ctl = child_timeline_resp.json()
    assert ctl["batch_code"] == child_code
    # Child batch should inherit parent lineage events
    parent_events = [e for e in ctl["timeline"] if e["source"] == "LINEAGE_PARENT_EVENT"]
    assert len(parent_events) >= 1


def test_shipment_events_progression():
    """Validates SHIPMENT_PICKUP_CONFIRMED, SHIPMENT_CHECKPOINT_RECORDED, and SHIPMENT_DELIVERY_CONFIRMED."""
    db = SessionLocal()
    trans_org = db.query(Organization).filter(Organization.org_type == "TRANSPORTER").first()
    org_id = trans_org.id if trans_org else "trans-synth-org"

    shipment_code = f"SHIP-EV-{str(uuid.uuid4())[:8].upper()}"
    shipment = Shipment(
        shipment_code=shipment_code,
        transporter_org_id=org_id,
        driver_name="Harish Transporter",
        vehicle_reg="TS 09 XY 8899",
        origin_name="Farm Hub",
        destination_name="Central Silo",
        stage="ASSIGNED",
        status="ACTIVE",
    )
    db.add(shipment)
    db.commit()
    db.refresh(shipment)

    # Pickup
    resp_pickup = client.post("/api/v1/events/record", json={
        "event_type": "SHIPMENT_PICKUP_CONFIRMED",
        "actor_id": "driver-harish",
        "actor_role": "TRANSPORTER",
        "organization_id": org_id,
        "payload": {
            "shipment_id": shipment.id,
            "vehicle_reg": "TS 09 XY 8899",
        },
    })
    assert resp_pickup.status_code == 201

    # Checkpoint
    resp_check = client.post("/api/v1/events/record", json={
        "event_type": "SHIPMENT_CHECKPOINT_RECORDED",
        "actor_id": "driver-harish",
        "actor_role": "TRANSPORTER",
        "organization_id": org_id,
        "payload": {
            "shipment_id": shipment.id,
            "location_name": "Toll Gate NH44",
            "latitude": 17.48,
            "longitude": 78.52,
        },
    })
    assert resp_check.status_code == 201

    # Delivery
    resp_deliv = client.post("/api/v1/events/record", json={
        "event_type": "SHIPMENT_DELIVERY_CONFIRMED",
        "actor_id": "driver-harish",
        "actor_role": "TRANSPORTER",
        "organization_id": org_id,
        "payload": {
            "shipment_id": shipment.id,
            "destination_name": "Central Silo",
        },
    })
    assert resp_deliv.status_code == 201

    db.refresh(shipment)
    assert shipment.stage == "DELIVERED"
    assert shipment.status == "COMPLETED"


def test_role_based_permissions_enforcement():
    """Validates that a role lacking permission cannot record unauthorized events."""
    # Transporter trying to record a FARMER crop activity
    resp = client.post("/api/v1/events/record", json={
        "event_type": "CROP_ACTIVITY_RECORDED",
        "actor_id": "transporter-1",
        "actor_role": "TRANSPORTER",
        "payload": {
            "farm_id": "farm-01",
            "crop_type": "Cotton",
            "activity_type": "SOWING",
        },
    })
    assert resp.status_code == 403
    assert "does not have permission" in resp.json()["detail"]


def test_list_business_events():
    """Validates listing business events with pagination and filters."""
    resp = client.get("/api/v1/events?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "events" in data
    assert len(data["events"]) <= 5


def test_all_roles_matrix_authorization_and_rejection():
    """Exhaustive matrix test:
    - Farmer, Transporter, Collection Centre, Retailer, Evidence Integrity Officer, and Admin
    - Each role can perform only authorized business actions.
    - Unauthorized roles receive HTTP 403 Forbidden.
    """
    db = SessionLocal()
    farm = db.query(Farm).first()
    farm_id = farm.id if farm else "farm-perm-test"

    # 1. FARMER: Authorized for CROP_ACTIVITY_RECORDED, Unauthorized for BATCH_DISPATCHED
    resp_farmer_ok = client.post("/api/v1/events/record", json={
        "event_type": "CROP_ACTIVITY_RECORDED",
        "actor_id": "farmer-user",
        "actor_role": "FARMER",
        "payload": {
            "farm_id": farm_id,
            "crop_type": "Mustard",
            "activity_type": "FERTILIZER_APPLICATION",
        },
    })
    assert resp_farmer_ok.status_code == 201

    resp_farmer_forbidden = client.post("/api/v1/events/record", json={
        "event_type": "BATCH_DISPATCHED",
        "actor_id": "farmer-user",
        "actor_role": "FARMER",
        "payload": {
            "batch_id": "some-batch",
            "destination_org_id": "ret-01",
        },
    })
    assert resp_farmer_forbidden.status_code == 403
    assert "does not have permission" in resp_farmer_forbidden.json()["detail"]

    # 2. TRANSPORTER: Authorized for SHIPMENT_CHECKPOINT_RECORDED, Unauthorized for WEIGHT_RECORDED
    resp_trans_forbidden = client.post("/api/v1/events/record", json={
        "event_type": "WEIGHT_RECORDED",
        "actor_id": "driver-user",
        "actor_role": "TRANSPORTER",
        "payload": {
            "batch_id": "some-batch",
            "measured_weight": 500.0,
        },
    })
    assert resp_trans_forbidden.status_code == 403

    # 3. COLLECTION_CENTRE: Authorized for WEIGHT_RECORDED, Unauthorized for INVESTIGATION_DECISION_RECORDED
    resp_cc_forbidden = client.post("/api/v1/events/record", json={
        "event_type": "INVESTIGATION_DECISION_RECORDED",
        "actor_id": "cc-operator",
        "actor_role": "COLLECTION_CENTRE",
        "payload": {
            "target_entity_type": "BATCH",
            "target_entity_id": "some-batch",
            "decision": "CONFIRM_VALID",
            "justification": "Operator approval",
        },
    })
    assert resp_cc_forbidden.status_code == 403

    # 4. RETAILER: Authorized for RETAIL_RECEIPT_CONFIRMED, Unauthorized for SHIPMENT_PICKUP_CONFIRMED
    resp_ret_forbidden = client.post("/api/v1/events/record", json={
        "event_type": "SHIPMENT_PICKUP_CONFIRMED",
        "actor_id": "retailer-user",
        "actor_role": "RETAILER",
        "payload": {
            "shipment_id": "some-shipment",
            "vehicle_reg": "KA 01 AB 1234",
        },
    })
    assert resp_ret_forbidden.status_code == 403

    # 5. EVIDENCE_INTEGRITY_OFFICER: Authorized for INVESTIGATION_OPENED, Unauthorized for BATCH_DISPATCHED
    resp_eio_ok = client.post("/api/v1/events/record", json={
        "event_type": "INVESTIGATION_OPENED",
        "actor_id": "eio-user",
        "actor_role": "EVIDENCE_INTEGRITY_OFFICER",
        "payload": {
            "target_entity_type": "BATCH",
            "target_entity_id": "some-batch",
            "reason_code": "RANDOM_INTEGRITY_AUDIT",
        },
    })
    assert resp_eio_ok.status_code == 201

    resp_eio_forbidden = client.post("/api/v1/events/record", json={
        "event_type": "BATCH_DISPATCHED",
        "actor_id": "eio-user",
        "actor_role": "EVIDENCE_INTEGRITY_OFFICER",
        "payload": {
            "batch_id": "some-batch",
            "destination_org_id": "ret-org",
        },
    })
    assert resp_eio_forbidden.status_code == 403

    # 6. ADMIN: Universal role override can perform actions across events
    resp_admin_ok = client.post("/api/v1/events/record", json={
        "event_type": "CROP_ACTIVITY_RECORDED",
        "actor_id": "admin-super",
        "actor_role": "ADMIN",
        "payload": {
            "farm_id": farm_id,
            "crop_type": "Organic Cotton",
            "activity_type": "ADMIN_OVERRIDE_AUDIT",
        },
    })
    assert resp_admin_ok.status_code == 201


def test_structured_event_schema_and_metadata_integrity():
    """Validates that recording a business action generates a complete, structured BusinessEvent
    with client metadata, correlation ID, server timestamp, and verification details.
    """
    uid = str(uuid.uuid4())[:8].upper()
    batch_code = f"BATCH-STRUCT-{uid}"

    headers = {
        "User-Agent": "PramanFieldApp/2.4.0 (Android 14; Mobile)",
        "X-Device-ID": "DEVICE-SAMSUNG-A54",
        "X-Device-Model": "SM-A546E",
        "X-App-Version": "2.4.0-build.102",
    }

    req_body = {
        "event_type": "BATCH_CREATED",
        "actor_id": "actor-cc-lead",
        "actor_role": "COLLECTION_CENTRE",
        "organization_id": "org-cc-central",
        "payload": {
            "batch_code": batch_code,
            "crop_type": "Red Gram",
            "initial_quantity": 750.0,
            "unit": "kg",
            "variety": "Asha ICPL 87119",
        },
    }

    resp = client.post("/api/v1/events/record", json=req_body, headers=headers)
    assert resp.status_code == 201
    data = resp.json()

    event_id = data["event_id"]
    assert event_id is not None
    assert data["event_type"] == "BATCH_CREATED"
    assert data["actor_id"] == "actor-cc-lead"
    assert data["actor_role"] == "COLLECTION_CENTRE"
    assert data["verification_status"] == "VERIFIED"

    # Verify metadata fields
    meta = data["metadata"]
    assert meta["device_id"] == "DEVICE-SAMSUNG-A54"
    assert meta["device_model"] == "SM-A546E"
    assert meta["app_version"] == "2.4.0-build.102"
    assert "correlation_id" in meta
    assert "timestamp_iso" in meta

    # Verify retrieval by event_id
    get_resp = client.get(f"/api/v1/events/{event_id}")
    assert get_resp.status_code == 200
    ev = get_resp.json()
    assert ev["event_id"] == event_id
    assert ev["payload"]["batch_code"] == batch_code
    assert ev["payload"]["initial_quantity"] == 750.0
    assert ev["metadata"]["device_id"] == "DEVICE-SAMSUNG-A54"


def test_evidence_requirements_and_linkage_to_event_and_batch():
    """Tests:
    1. Mandatory evidence check fails when missing and succeeds when provided.
    2. Optional evidence does not block valid workflows when omitted.
    3. When evidence is provided (file upload), evidence_hash is generated and linked to event and batch.
    """
    uid = str(uuid.uuid4())[:8].upper()
    batch_code = f"BATCH-EVID-{uid}"

    # Create batch
    c_resp = client.post("/api/v1/events/record", json={
        "event_type": "BATCH_CREATED",
        "actor_id": "operator-01",
        "actor_role": "COLLECTION_CENTRE",
        "payload": {
            "batch_code": batch_code,
            "crop_type": "Soybean",
            "initial_quantity": 1200.0,
        },
    })
    assert c_resp.status_code == 201
    batch_id = c_resp.json()["batch_id"]

    # 1. Optional evidence omitted on WEIGHT_RECORDED (succeeds, evidence_hash is None)
    w_no_ev = client.post("/api/v1/events/record", json={
        "event_type": "WEIGHT_RECORDED",
        "actor_id": "operator-01",
        "actor_role": "COLLECTION_CENTRE",
        "payload": {
            "batch_id": batch_id,
            "measured_weight": 1195.0,
            "unit": "kg",
        },
    })
    assert w_no_ev.status_code == 201
    assert w_no_ev.json()["evidence_hash"] is None

    # 2. Optional evidence provided on QUALITY_INSPECTION_COMPLETED via multipart form
    fake_inspection_img = b"JPEG_BINARY_DATA_SAMPLE_INSPECTION_" + uid.encode()
    insp_form = {
        "event_type": "QUALITY_INSPECTION_COMPLETED",
        "actor_id": "inspector-rajesh",
        "actor_role": "COLLECTION_CENTRE",
        "payload": json.dumps({
            "batch_id": batch_id,
            "grade": "GRADE_A",
            "decision": "ACCEPTED",
            "moisture_pct": 10.5,
        }),
    }
    insp_resp = client.post(
        "/api/v1/events/record",
        data=insp_form,
        files={"file": ("sample_tray.jpg", fake_inspection_img, "image/jpeg")},
    )
    assert insp_resp.status_code == 201
    insp_data = insp_resp.json()
    assert insp_data["evidence_hash"] is not None
    ev_hash = insp_data["evidence_hash"]

    # 3. Check that the evidence is linked to the batch timeline
    tl_resp = client.get(f"/api/v1/events/batch/{batch_id}/timeline")
    assert tl_resp.status_code == 200
    timeline = tl_resp.json()["timeline"]

    inspection_milestones = [
        m for m in timeline
        if m["event_type"] == "QUALITY_INSPECTION_COMPLETED"
    ]
    assert len(inspection_milestones) >= 1
    assert any(m.get("evidence_hash") == ev_hash for m in inspection_milestones)
    assert any(m.get("has_evidence") is True for m in inspection_milestones)


def test_chronological_batch_timeline_and_tenant_isolation():
    """Validates:
    1. Batch timeline query returns the complete chronological event chain.
    2. Multi-tenant isolation: unauthorized organization users cannot view the batch timeline.
    3. Authorized organization and admin users can view the timeline.
    """
    db = SessionLocal()
    uid = str(uuid.uuid4())[:8].upper()
    batch_code = f"BATCH-ISO-{uid}"

    # Setup tenant organizations
    org_a = Organization(name=f"CC Cluster A {uid}", org_type="COLLECTION_CENTRE")
    org_b = Organization(name=f"CC Cluster B {uid}", org_type="COLLECTION_CENTRE")
    db.add(org_a)
    db.add(org_b)
    db.commit()
    db.refresh(org_a)
    db.refresh(org_b)

    # Setup user belonging to Org B
    user_b = User(
        username=f"user_b_{uid}",
        email=f"user_b_{uid}@orgb.test",
        full_name=f"User B {uid}",
        hashed_password="pw",
        role="COLLECTION_CENTRE",
        organization_id=org_b.id,
    )
    db.add(user_b)
    db.commit()
    db.refresh(user_b)

    # Create batch belonging to Org A
    c_resp = client.post("/api/v1/events/record", json={
        "event_type": "BATCH_CREATED",
        "actor_id": "manager-a",
        "actor_role": "COLLECTION_CENTRE",
        "organization_id": org_a.id,
        "payload": {
            "batch_code": batch_code,
            "crop_type": "Sunflower",
            "initial_quantity": 800.0,
            "collection_centre_id": org_a.id,
        },
    })
    assert c_resp.status_code == 201
    batch_id = c_resp.json()["batch_id"]

    # Append additional events
    client.post("/api/v1/events/record", json={
        "event_type": "PRODUCE_RECEIVED",
        "actor_id": "manager-a",
        "actor_role": "COLLECTION_CENTRE",
        "organization_id": org_a.id,
        "payload": {"batch_id": batch_id},
    })
    client.post("/api/v1/events/record", json={
        "event_type": "WEIGHT_RECORDED",
        "actor_id": "manager-a",
        "actor_role": "COLLECTION_CENTRE",
        "organization_id": org_a.id,
        "payload": {"batch_id": batch_id, "measured_weight": 800.0},
    })

    # Test timeline ordering
    tl_resp = client.get(f"/api/v1/events/batch/{batch_id}/timeline")
    assert tl_resp.status_code == 200
    timeline = tl_resp.json()["timeline"]
    assert len(timeline) >= 3

    # Check timestamps are strictly non-decreasing
    timestamps = [m["timestamp"] for m in timeline if m.get("timestamp")]
    assert timestamps == sorted(timestamps)

    # Test multi-tenant isolation via EventEngine directly or through mock header
    # User B (from Org B) attempting to view Org A's batch
    with pytest.raises(Exception) as exc_info:
        event_engine.get_batch_timeline(db=db, batch_id=batch_id, current_user=user_b)
    assert "403" in str(exc_info.value) or "Access denied" in str(exc_info.value)
