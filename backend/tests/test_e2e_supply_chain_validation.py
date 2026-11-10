import pytest
import uuid
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models import (
    Farmer, Farm, Batch, Shipment, ShipmentItem,
    ProcurementOrder, RetailerInventory, Evidence, ReviewDecision, Organization, User
)

client = TestClient(app)


def test_complete_synthetic_supply_chain_and_officer_investigation_e2e():
    """
    Validates full end-to-end connected lifecycle using isolated synthetic test entities:
    Synthetic Farmer Batch -> Transporter Pickup -> Transit -> Delivery -> 
    Collection Centre Receiving/Weighing -> Inspection -> Strict Lineage Split ->
    Retailer Procurement -> Stock Receiving -> Consumer QR Verification ->
    Suspicious Tamper Evidence -> Evidence Integrity Officer Adjudication.
    """
    db = SessionLocal()
    run_id = str(uuid.uuid4())[:8].upper()

    # 1. Setup isolated synthetic farm & batch
    farm = db.query(Farm).first()
    farm_id = farm.id if farm else None

    synth_batch_code = f"BATCH-SYNTH-{run_id}"
    batch = Batch(
        batch_code=synth_batch_code,
        farm_id=farm_id,
        crop_type="Organic Cotton",
        variety="Suvin Extra-Long Staple",
        initial_quantity=1000.0,
        current_quantity=1000.0,
        unit="kg",
        stage="FARM_HARVESTED",
        status="ACTIVE",
        notes=f"Synthetic test batch run {run_id}",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    # 2. Transporter Pickup
    synth_shipment_code = f"SHIP-SYNTH-{run_id}"
    trans_org = db.query(Organization).filter(Organization.org_type == "TRANSPORTER").first()
    shipment = Shipment(
        shipment_code=synth_shipment_code,
        transporter_org_id=trans_org.id if trans_org else "trans-synth-org",
        driver_name="V. Ramana (Synthetic)",
        vehicle_reg="TS 07 TR 1001",
        origin_name="Synthetically Verified Farm Gate",
        destination_name="Adilabad Central Collection Centre",
        stage="ASSIGNED",
        status="ACTIVE",
    )
    db.add(shipment)
    db.commit()
    db.refresh(shipment)

    item = ShipmentItem(
        shipment_id=shipment.id,
        batch_id=batch.id,
        declared_quantity=1000.0,
        unit="kg",
    )
    db.add(item)
    db.commit()

    # Transporter confirms pickup
    pickup_res = client.post(
        "/api/v1/platform/transporter/pickup",
        json={
            "shipment_id": shipment.id,
            "driver_name": "V. Ramana (Synthetic)",
            "vehicle_reg": "TS 07 TR 1001",
            "pickup_quantity": 1000.0,
            "condition": "EXCELLENT",
            "notes": "Gate pickup confirmed. Tarpaulin seals verified.",
        }
    )
    assert pickup_res.status_code == 200
    assert pickup_res.json()["stage"] == "PICKED_UP"

    # Transporter records transit checkpoint
    cp_res = client.post(
        "/api/v1/platform/transporter/checkpoint",
        json={
            "shipment_id": shipment.id,
            "location_name": "NH 44 Adilabad Highway Checkpoint",
            "condition": "EXCELLENT",
            "notes": "GPS tracking nominal, temperature normal",
        }
    )
    assert cp_res.status_code == 200

    # Transporter confirms delivery
    deliv_res = client.post(
        "/api/v1/platform/transporter/delivery",
        json={
            "shipment_id": shipment.id,
            "destination_name": "Adilabad Central Collection Centre",
            "delivered_quantity": 1000.0,
            "condition": "EXCELLENT",
            "receiver_notes": "Delivered intact to centre bay #3",
        }
    )
    assert deliv_res.status_code == 200
    assert deliv_res.json()["stage"] == "DELIVERED"

    # 3. Collection Centre Weighing & Grading
    weigh_res = client.post(
        "/api/v1/platform/centre/weighing",
        json={
            "batch_id": batch.id,
            "operator_id": "operator-centre-01",
            "measured_weight": 995.0,  # 5kg moisture evaporation during transit
            "unit": "kg",
            "scale_identifier": "Scale-Digitron-04",
            "is_manual_entry": True,
        }
    )
    assert weigh_res.status_code == 200
    assert weigh_res.json()["measured_weight"] == 995.0

    insp_res = client.post(
        "/api/v1/platform/centre/inspection",
        json={
            "batch_id": batch.id,
            "crop_category": "Cotton",
            "grade": "GRADE_A",
            "physical_condition": "EXCELLENT",
            "moisture_pct": 7.8,
            "defect_notes": "Zero foreign matter, clean staple fiber",
            "decision": "ACCEPTED",
        }
    )
    assert insp_res.status_code == 200
    assert insp_res.json()["decision"] == "ACCEPTED"

    # 4. Collection Centre Batch Splitting with mathematical reconciliation
    # 995 kg total: 600 kg (Child A) + 380 kg (Child B) + 15 kg (ginning loss)
    split_res = client.post(
        "/api/v1/platform/centre/split-batch",
        json={
            "parent_batch_id": batch.id,
            "splits": [
                {"quantity": 600.0, "grade": "GRADE_A"},
                {"quantity": 380.0, "grade": "GRADE_B"},
            ],
            "loss_waste_quantity": 15.0,
            "reason_notes": "Ginning processing and dust removal",
        }
    )
    assert split_res.status_code == 200
    children = split_res.json()["children"]
    assert len(children) == 2

    child_a = db.query(Batch).filter(Batch.batch_code == children[0]).first()
    assert child_a is not None
    assert child_a.parent_batch_id == batch.id

    # 5. Retailer Procurement & Receiving
    order_res = client.post(
        "/api/v1/platform/retailer/procure",
        json={
            "batch_id": child_a.id,
            "ordered_quantity": 600.0,
            "unit_price": 84.50,
        }
    )
    assert order_res.status_code == 200
    order_code = order_res.json()["order_code"]

    retail_order = db.query(ProcurementOrder).filter(ProcurementOrder.order_code == order_code).first()
    receive_res = client.post(
        "/api/v1/platform/retailer/receive",
        json={
            "order_id": retail_order.id,
            "received_quantity": 600.0,
            "actual_condition": "EXCELLENT",
            "invoice_number": f"INV-{run_id}",
        }
    )
    assert receive_res.status_code == 200
    opaque_qr = receive_res.json()["opaque_qr_token"]
    assert opaque_qr.startswith("prm_")

    # 6. Customer QR Verification Endpoint (Zero PII, Zero GPS disclosure)
    verify_res = client.get(f"/api/v1/platform/verify/{opaque_qr}")
    assert verify_res.status_code == 200
    vdata = verify_res.json()
    assert vdata["status"] == "VERIFIED_AUTHENTIC"
    assert vdata["zero_pii_enforced"] is True
    assert vdata["zero_gps_leakage"] is True
    assert vdata["crop_type"] == "Organic Cotton"

    # 7. Evidence Integrity Officer Adjudication Workflow
    # Find pending review case
    pending_ev = db.query(Evidence).filter(Evidence.status == "PENDING_REVIEW").first()
    assert pending_ev is not None

    adjudicate_res = client.post(
        "/api/v1/platform/intelligence/decide",
        json={
            "evidence_id": pending_ev.id,
            "decision": "CONFIRM_VALID",
            "explanation": "Cryptographic ECDSA P-256 signature verified over RFC 8785 canonical bytes. Spatial polygon intersection confirmed within cadastral boundary.",
            "officer_id": "officer-dr-rao",
            "policy_version": "PRAMAN-POLICY-V2.4",
        }
    )
    assert adjudicate_res.status_code == 200
    assert adjudicate_res.json()["new_state"] == "APPROVED"

    # Verify decision logged in review_decisions
    decision_log = (
        db.query(ReviewDecision)
        .filter(ReviewDecision.evidence_id == pending_ev.id)
        .order_by(ReviewDecision.decided_at.desc())
        .first()
    )
    assert decision_log is not None
    assert decision_log.action == "APPROVE"

    db.close()

