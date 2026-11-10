import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_platform_bootstrap():
    resp = client.post("/api/v1/platform/auth/bootstrap")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"


def test_auth_login():
    resp = client.post(
        "/api/v1/platform/auth/login",
        json={"username": "transporter1", "password": "Praman@2026"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["role"] == "TRANSPORTER"


def test_transporter_dashboard_and_lifecycle():
    # 1. Fetch dashboard
    resp = client.get("/api/v1/platform/transporter/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "metrics" in data
    assert len(data["shipments"]) > 0
    shipment_id = data["shipments"][0]["id"]

    # 2. Confirm pickup
    pickup_resp = client.post(
        "/api/v1/platform/transporter/pickup",
        json={
            "shipment_id": shipment_id,
            "driver_name": "Ramesh Kumar",
            "vehicle_reg": "TS 01 AB 9999",
            "pickup_quantity": 1200.0,
            "condition": "GOOD",
            "notes": "Secure farm gate dispatch",
        },
    )
    assert pickup_resp.status_code == 200
    assert pickup_resp.json()["stage"] == "PICKED_UP"

    # 3. Transit checkpoint
    check_resp = client.post(
        "/api/v1/platform/transporter/checkpoint",
        json={
            "shipment_id": shipment_id,
            "location_name": "Toll Plaza NH 44",
            "condition": "GOOD",
            "notes": "Weather normal, seals intact",
        },
    )
    assert check_resp.status_code == 200

    # 4. Confirm delivery
    deliv_resp = client.post(
        "/api/v1/platform/transporter/delivery",
        json={
            "shipment_id": shipment_id,
            "destination_name": "Adilabad Cotton Collection Centre",
            "delivered_quantity": 1200.0,
            "condition": "GOOD",
            "receiver_notes": "Delivered intact with seal verified",
        },
    )
    assert deliv_resp.status_code == 200
    assert deliv_resp.json()["stage"] == "DELIVERED"


def test_collection_centre_inspection_and_split():
    # 1. Centre dashboard
    dash_resp = client.get("/api/v1/platform/centre/dashboard")
    assert dash_resp.status_code == 200
    batches = dash_resp.json()["batches"]
    assert len(batches) > 0
    batch_id = batches[0]["id"]

    # 2. Weighing
    weigh_resp = client.post(
        "/api/v1/platform/centre/weighing",
        json={"batch_id": batch_id, "measured_weight": 1200.0, "unit": "kg"},
    )
    assert weigh_resp.status_code == 200

    # 3. Quality inspection
    insp_resp = client.post(
        "/api/v1/platform/centre/inspection",
        json={
            "batch_id": batch_id,
            "crop_category": "Cotton",
            "grade": "GRADE_A",
            "physical_condition": "EXCELLENT",
            "moisture_pct": 8.5,
            "decision": "ACCEPTED",
        },
    )
    assert insp_resp.status_code == 200
    assert insp_resp.json()["decision"] == "ACCEPTED"

    # 4. Batch split with explicit reconciliation
    split_resp = client.post(
        "/api/v1/platform/centre/split-batch",
        json={
            "parent_batch_id": batch_id,
            "splits": [
                {"quantity": 700.0, "grade": "GRADE_A"},
                {"quantity": 480.0, "grade": "GRADE_B"},
            ],
            "loss_waste_quantity": 20.0,
            "reason_notes": "Moisture evaporation and sorting loss recorded",
        },
    )
    assert split_resp.status_code == 200
    assert len(split_resp.json()["children"]) == 2


def test_retailer_procure_and_receive_flow():
    # 1. Retailer dashboard
    dash_resp = client.get("/api/v1/platform/retailer/dashboard")
    assert dash_resp.status_code == 200
    avail = dash_resp.json()["available_batches"]
    assert len(avail) > 0
    batch_id = avail[0]["id"]

    # 2. Place procurement order
    procure_resp = client.post(
        "/api/v1/platform/retailer/procure",
        json={"batch_id": batch_id, "ordered_quantity": 500.0, "unit_price": 75.0},
    )
    assert procure_resp.status_code == 200
    order_code = procure_resp.json()["order_code"]

    # 3. Receive into retail inventory and generate opaque QR token
    # Query order id
    orders = client.get("/api/v1/platform/retailer/dashboard").json()["orders"]
    matching_order = next(o for o in orders if o["order_code"] == order_code)

    rec_resp = client.post(
        "/api/v1/platform/retailer/receive",
        json={
            "order_id": matching_order["id"],
            "received_quantity": 500.0,
            "actual_condition": "GOOD",
        },
    )
    assert rec_resp.status_code == 200
    qr_token = rec_resp.json()["opaque_qr_token"]
    assert qr_token.startswith("prm_")

    # 4. Verify consumer QR verification returns verified authentic provenance with zero PII/GPS
    verify_resp = client.get(f"/api/v1/platform/verify/{qr_token}")
    assert verify_resp.status_code == 200
    vdata = verify_resp.json()
    assert vdata["status"] == "VERIFIED_AUTHENTIC"
    assert vdata["zero_pii_enforced"] is True
    assert vdata["zero_gps_leakage"] is True


def test_evidence_integrity_officer_workflow():
    overview_resp = client.get("/api/v1/platform/intelligence/overview")
    assert overview_resp.status_code == 200
    cases = overview_resp.json()["cases"]
    assert len(cases) > 0
    target_ev_id = cases[0]["id"]

    # Officer records official adjudication
    dec_resp = client.post(
        "/api/v1/platform/intelligence/decide",
        json={
            "evidence_id": target_ev_id,
            "decision": "CONFIRM_VALID",
            "explanation": "RFC 8785 signature valid, image sensor forensics within standard baseline, GPS in verified boundary.",
            "officer_id": "officer-dr-rao",
        },
    )
    assert dec_resp.status_code == 200
    assert dec_resp.json()["new_state"] == "APPROVED"


def test_platform_admin_governance():
    dash_resp = client.get("/api/v1/platform/admin/dashboard")
    assert dash_resp.status_code == 200
    assert dash_resp.json()["metrics"]["total_users"] >= 5

    import uuid
    rand_suffix = str(uuid.uuid4())[:6]
    create_resp = client.post(
        "/api/v1/platform/admin/users",
        json={
            "username": f"officer_ts_{rand_suffix}",
            "email": f"officer_{rand_suffix}@praman.org",
            "password": "SecurePassword@2026",
            "full_name": "Adilabad Regional Officer",
            "role": "EVIDENCE_INTEGRITY_OFFICER",
        },
    )
    assert create_resp.status_code == 200
    assert f"officer_ts_{rand_suffix}" == create_resp.json()["username"]


def test_unified_web_routes():
    # Web root serving unified application
    web_resp = client.get("/")
    assert web_resp.status_code == 200
    assert "PRAMAN" in web_resp.text
    assert "Transporter" in web_resp.text
    assert "Evidence Integrity Officer" in web_resp.text

    # Customer QR verification route
    qr_web_resp = client.get("/verify/prm_demo_authentic_token")
    assert qr_web_resp.status_code == 200
    assert "PRAMAN Verified Provenance Certificate" in qr_web_resp.text

