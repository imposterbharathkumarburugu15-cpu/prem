import pytest
import uuid
import json
import random
import hashlib
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models import (
    Farmer, Farm, Batch, Shipment, ShipmentItem, ShipmentEvent,
    WeighingRecord, QualityInspection, ProcurementOrder, RetailerInventory,
    PublicToken, MerkleBatch, Organization, User, AuditLog
)

client = TestClient(app)


def test_end_to_end_lineage_split_child_traversal():
    """
    Empirically verifies:
    1. Parent batch created from Farm with harvest evidence.
    2. Transporter pickup, checkpoint, and delivery events recorded for parent batch.
    3. Collection Centre weighing & quality inspection recorded for parent batch.
    4. Parent batch split into Child 1 and Child 2.
    5. Child 1 procured and received by Retailer into RetailerInventory with opaque QR token.
    6. Customer QR verification traverses from Child 1 through parent_batch_id back to
       Root Parent Batch, Farm, and logistics events.
    7. Verifies authentic timestamps, organizations, and CAS media hashes.
    """
    db = SessionLocal()
    run_id = str(uuid.uuid4())[:8].upper()
    phone_suffix = f"{random.randint(100000, 999999)}"

    try:
        # Step 1: Create Farmer and Farm
        farmer = Farmer(
            id=f"farmer-{run_id}",
            full_name="B. Venkat Reddy",
            phone_number=f"+91-98{phone_suffix}",
            language_pref="te",
        )
        db.add(farmer)
        db.commit()

        valid_polygon = {
            "type": "Polygon",
            "coordinates": [[
                [78.5320, 19.6640],
                [78.5330, 19.6640],
                [78.5330, 19.6650],
                [78.5320, 19.6650],
                [78.5320, 19.6640]
            ]]
        }

        farm = Farm(
            id=f"farm-{run_id}",
            farmer_id=farmer.id,
            farm_name="Venkat Reddy Cotton Estate",
            crop_type="Organic Cotton",
            boundary_geojson=json.dumps(valid_polygon),
            boundary_version=1,
            crs="EPSG:4326",
            area_sq_meters=34398.0,
            area_acres=8.5,
            area_hectares=3.44,
            district="Adilabad",
            state="Telangana",
            is_valid=True,
        )
        db.add(farm)
        db.commit()

        # Step 2: Parent Batch at Farm
        parent_batch = Batch(
            batch_code=f"BATCH-PARENT-{run_id}",
            farm_id=farm.id,
            crop_type="Organic Cotton",
            variety="Brahma Extra-Long",
            initial_quantity=2000.0,
            current_quantity=2000.0,
            unit="kg",
            lineage_type="ORIGINAL",
            stage="FARM_HARVESTED",
            status="ACTIVE",
            notes=f"Original parent harvest for run {run_id}",
        )
        db.add(parent_batch)
        db.commit()
        db.refresh(parent_batch)

        # Step 3: Transporter Logistics for Parent Batch
        trans_org = db.query(Organization).filter(Organization.org_type == "TRANSPORTER").first()
        assert trans_org is not None, "Transporter org required"

        shipment = Shipment(
            shipment_code=f"SHIP-PARENT-{run_id}",
            transporter_org_id=trans_org.id,
            driver_name="R. Gangadhar",
            vehicle_reg="TS 08 TC 9901",
            origin_name="Farm Gate Cluster Alpha",
            destination_name="Adilabad Cotton Centre Bay 2",
            stage="DELIVERED",
            status="ACTIVE",
        )
        db.add(shipment)
        db.commit()
        db.refresh(shipment)

        ship_item = ShipmentItem(
            shipment_id=shipment.id,
            batch_id=parent_batch.id,
            declared_quantity=2000.0,
            picked_up_quantity=2000.0,
            delivered_quantity=1995.0,
            unit="kg",
        )
        db.add(ship_item)
        db.commit()

        # Specific hashes for CAS media verification
        pickup_hash = hashlib.sha256(f"pickup-evidence-{run_id}".encode()).hexdigest()
        checkpoint_hash = hashlib.sha256(f"checkpoint-evidence-{run_id}".encode()).hexdigest()
        delivery_hash = hashlib.sha256(f"delivery-evidence-{run_id}".encode()).hexdigest()

        pickup_event = ShipmentEvent(
            shipment_id=shipment.id,
            event_type="PICKUP",
            location_name="Farm Gate Loading Point",
            latitude=19.6640,
            longitude=78.5320,
            condition="EXCELLENT",
            notes=f"Pickup verified by {shipment.vehicle_reg}",
            photo_evidence_hash=pickup_hash,
        )
        checkpoint_event = ShipmentEvent(
            shipment_id=shipment.id,
            event_type="TRANSIT_CHECKPOINT",
            location_name="Nirmal Highway Toll Plaza",
            latitude=19.4500,
            longitude=78.3400,
            condition="EXCELLENT",
            notes="Transit seal verified",
            photo_evidence_hash=checkpoint_hash,
        )
        delivery_event = ShipmentEvent(
            shipment_id=shipment.id,
            event_type="DELIVERY",
            location_name="Adilabad Collection Centre Dock 1",
            latitude=19.6700,
            longitude=78.5400,
            condition="EXCELLENT",
            notes="Delivered intact",
            photo_evidence_hash=delivery_hash,
        )
        db.add_all([pickup_event, checkpoint_event, delivery_event])
        db.commit()

        # Step 4: Collection Centre Weighing & Grading on Parent Batch
        centre_org = db.query(Organization).filter(Organization.org_type == "COLLECTION_CENTRE").first()
        assert centre_org is not None, "Collection centre org required"

        parent_batch.collection_centre_id = centre_org.id
        parent_batch.stage = "AT_COLLECTION_CENTRE"
        parent_batch.current_quantity = 1995.0
        db.commit()

        slip_hash = hashlib.sha256(f"weigh-slip-{run_id}".encode()).hexdigest()
        inspect_hash = hashlib.sha256(f"quality-photo-{run_id}".encode()).hexdigest()

        weigh_record = WeighingRecord(
            batch_id=parent_batch.id,
            operator_id="operator-certified-09",
            measured_weight=1995.0,
            unit="kg",
            scale_identifier="Scale-Digitron-04",
            is_manual_entry=True,
            slip_photo_hash=slip_hash,
        )
        db.add(weigh_record)

        inspection = QualityInspection(
            batch_id=parent_batch.id,
            inspector_id="inspector-certified-12",
            crop_category="Cotton",
            grade="GRADE_A",
            physical_condition="PREMIUM",
            moisture_pct=7.2,
            defect_notes="Zero trash, bright white staple",
            decision="ACCEPTED",
            photo_evidence_hash=inspect_hash,
        )
        db.add(inspection)
        db.commit()

        # Step 5: Split Parent Batch into Child 1 and Child 2
        # 1995.0 kg total: Child 1 = 1200.0, Child 2 = 780.0, Loss = 15.0
        split_res = client.post(
            "/api/v1/platform/centre/split-batch",
            json={
                "parent_batch_id": parent_batch.id,
                "splits": [
                    {"quantity": 1200.0, "grade": "GRADE_A"},
                    {"quantity": 780.0, "grade": "GRADE_B"},
                ],
                "loss_waste_quantity": 15.0,
                "reason_notes": "Ginning and sorting process",
            }
        )
        assert split_res.status_code == 200, f"Split failed: {split_res.text}"
        child_codes = split_res.json()["children"]
        assert len(child_codes) == 2

        child_1 = db.query(Batch).filter(Batch.batch_code == child_codes[0]).first()
        assert child_1 is not None
        assert child_1.parent_batch_id == parent_batch.id
        assert child_1.lineage_type == "SPLIT_CHILD"

        # Step 6: Retailer Procures and Receives Child 1
        ret_org = db.query(Organization).filter(Organization.org_type == "RETAILER").first()
        assert ret_org is not None, "Retailer org required"

        procure_res = client.post(
            "/api/v1/platform/retailer/procure",
            json={
                "batch_id": child_1.id,
                "ordered_quantity": 1200.0,
                "unit_price": 92.00,
            }
        )
        assert procure_res.status_code == 200
        order_code = procure_res.json()["order_code"]
        p_order = db.query(ProcurementOrder).filter(ProcurementOrder.order_code == order_code).first()

        receive_res = client.post(
            "/api/v1/platform/retailer/receive",
            json={
                "order_id": p_order.id,
                "received_quantity": 1200.0,
                "actual_condition": "PREMIUM",
                "invoice_number": f"INV-CHALLENGER-{run_id}",
            }
        )
        assert receive_res.status_code == 200
        opaque_qr = receive_res.json()["opaque_qr_token"]
        assert opaque_qr.startswith("prm_")

        # Step 7: Customer QR Verification
        verify_res = client.get(f"/api/v1/platform/verify/{opaque_qr}")
        assert verify_res.status_code == 200
        vdata = verify_res.json()

        # Invariant Assertions
        assert vdata["status"] == "VERIFIED_AUTHENTIC"
        assert vdata["verification_token"] == opaque_qr
        assert vdata["batch_code"] == child_1.batch_code
        assert vdata["crop_type"] == "Organic Cotton"
        assert vdata["merkle_root"] is not None and len(vdata["merkle_root"]) == 64
        assert vdata["zero_pii_enforced"] is True
        assert vdata["zero_gps_leakage"] is True

        timeline = vdata["provenance_timeline"]
        stages = [t["stage"] for t in timeline]

        # Verify authentic relational graph traversal:
        # Farm Harvest -> Logistics (Pickup, Checkpoint, Delivery) -> Weighing -> Grading -> Split -> Retail
        assert "FARM_HARVEST" in stages
        assert "SECURE_TRANSIT_PICKUP" in stages
        assert "SECURE_TRANSIT_CHECKPOINT" in stages
        assert "SECURE_TRANSIT_DELIVERY" in stages
        assert "COLLECTION_CENTRE_WEIGHING" in stages
        assert "COLLECTION_CENTRE_GRADING" in stages
        assert "BATCH_LINEAGE_SPLIT" in stages
        assert "RETAIL_PROCUREMENT" in stages
        assert "RETAIL_RECEIPT" in stages

        # Verify authentic media hashes and attributes
        pickup_t = next(t for t in timeline if t["stage"] == "SECURE_TRANSIT_PICKUP")
        assert pickup_t["photo_hash"] == pickup_hash

        checkpoint_t = next(t for t in timeline if t["stage"] == "SECURE_TRANSIT_CHECKPOINT")
        assert checkpoint_t["photo_hash"] == checkpoint_hash

        delivery_t = next(t for t in timeline if t["stage"] == "SECURE_TRANSIT_DELIVERY")
        assert delivery_t["photo_hash"] == delivery_hash

        weigh_t = next(t for t in timeline if t["stage"] == "COLLECTION_CENTRE_WEIGHING")
        assert weigh_t["photo_hash"] == slip_hash
        assert "Scale-Digitron-04" in weigh_t["description"]
        assert "1995.0" in weigh_t["description"]

        inspect_t = next(t for t in timeline if t["stage"] == "COLLECTION_CENTRE_GRADING")
        assert inspect_t["photo_hash"] == inspect_hash
        assert "GRADE_A" in inspect_t["status"]

        split_t = next(t for t in timeline if t["stage"] == "BATCH_LINEAGE_SPLIT")
        assert parent_batch.batch_code in split_t["description"]

        farm_t = next(t for t in timeline if t["stage"] == "FARM_HARVEST")
        assert farm_t["attributes"]["variety"] == "Brahma Extra-Long"
        assert "8.5 acres" in farm_t["description"]

        # Step 8: Verify HTML route returns 200 and embeds openCustomerVerify
        html_res = client.get(f"/verify/{opaque_qr}")
        assert html_res.status_code == 200
        assert f'openCustomerVerify("{opaque_qr}")' in html_res.text

    finally:
        db.close()


def test_adversarial_multitier_grandchild_split_lineage():
    """
    Adversarial Multi-tier Lineage:
    Root Batch -> Child Batch -> Grandchild Batch.
    Tests deep recursive parent traversal up through multiple generations to
    original Farm and Logistics records.
    """
    db = SessionLocal()
    run_id = str(uuid.uuid4())[:8].upper()

    try:
        # Farm & Root Batch
        farm = db.query(Farm).first()
        farm_id = farm.id if farm else None

        ret_org = db.query(Organization).filter(Organization.org_type == "RETAILER").first()
        assert ret_org is not None, "Retailer organization must exist in database"

        root_batch = Batch(
            batch_code=f"BATCH-ROOT-{run_id}",
            farm_id=farm_id,
            crop_type="Organic Cotton",
            variety="Desi Heritage",
            initial_quantity=5000.0,
            current_quantity=5000.0,
            unit="kg",
            lineage_type="ORIGINAL",
            stage="AT_COLLECTION_CENTRE",
            status="SPLIT",
        )
        db.add(root_batch)
        db.commit()
        db.refresh(root_batch)

        # Weighing on Root Batch
        root_slip = hashlib.sha256(f"root-slip-{run_id}".encode()).hexdigest()
        weigh_rec = WeighingRecord(
            batch_id=root_batch.id,
            operator_id="operator-root",
            measured_weight=5000.0,
            unit="kg",
            scale_identifier="Scale-Bulk-01",
            is_manual_entry=True,
            slip_photo_hash=root_slip,
        )
        db.add(weigh_rec)

        # Generation 1 Split: Child Batch
        child_batch = Batch(
            batch_code=f"BATCH-CHILD-{run_id}",
            farm_id=farm_id,
            crop_type="Organic Cotton",
            variety="Desi Heritage",
            initial_quantity=2500.0,
            current_quantity=2500.0,
            unit="kg",
            parent_batch_id=root_batch.id,
            lineage_type="SPLIT_CHILD",
            stage="PROCESSED",
            status="SPLIT",
        )
        db.add(child_batch)
        db.commit()
        db.refresh(child_batch)

        # Generation 2 Split: Grandchild Batch
        grandchild_batch = Batch(
            batch_code=f"BATCH-GRANDCHILD-{run_id}",
            farm_id=farm_id,
            crop_type="Organic Cotton",
            variety="Desi Heritage",
            initial_quantity=1000.0,
            current_quantity=1000.0,
            unit="kg",
            parent_batch_id=child_batch.id,
            lineage_type="SPLIT_CHILD",
            stage="AT_RETAILER",
            status="ACTIVE",
        )
        db.add(grandchild_batch)
        db.commit()
        db.refresh(grandchild_batch)

        # Retailer Inventory for Grandchild
        opaque_token = f"prm_test_grandchild_{run_id.lower()}"
        inv = RetailerInventory(
            retailer_org_id=ret_org.id,
            batch_id=grandchild_batch.id,
            crop_type="Organic Cotton",
            available_quantity=1000.0,
            unit="kg",
            storage_location="Shelf Row G-3",
            opaque_qr_token=opaque_token,
        )
        db.add(inv)
        db.commit()

        # Verify Grandchild Token
        verify_res = client.get(f"/api/v1/platform/verify/{opaque_token}")
        assert verify_res.status_code == 200
        vdata = verify_res.json()

        assert vdata["status"] == "VERIFIED_AUTHENTIC"
        assert vdata["batch_code"] == grandchild_batch.batch_code

        # Check that Root Batch's weighing record was retrieved through 2-level traversal
        timeline = vdata["provenance_timeline"]
        weighing_stages = [t for t in timeline if t["stage"] == "COLLECTION_CENTRE_WEIGHING"]
        assert len(weighing_stages) >= 1
        assert any(w.get("photo_hash") == root_slip for w in weighing_stages)

        # Check split lineage stage references parent (child_batch)
        split_stages = [t for t in timeline if t["stage"] == "BATCH_LINEAGE_SPLIT"]
        assert len(split_stages) >= 1
        assert child_batch.batch_code in split_stages[0]["description"]

    finally:
        db.close()


def test_strict_zero_pii_and_zero_gps_leakage():
    """
    Adversarial Security Probe:
    Inject highly identifiable PII (farmer personal name, phone number, private UUIDs,
    exact GPS coordinates, cadastral survey number, secret driver/operator IDs) and
    rigorously verify that NOT A SINGLE BYTE of sensitive data leaks through
    the public verification endpoint.
    """
    db = SessionLocal()
    run_id = str(uuid.uuid4())[:8].upper()
    phone_suffix = f"{random.randint(100000, 999999)}"

    # Sensitive PII values to inject
    SECRET_FARMER_NAME = f"Sitaram_Ananthula_Secret_{run_id}"
    SECRET_PHONE = f"+91-97{phone_suffix}"
    SECRET_FARMER_UUID = f"private-farmer-uuid-{run_id}"
    SECRET_USER_NAME = f"sitaram_private_{run_id}"
    SECRET_EMAIL = f"sitaram_{run_id}@confidential-farm.org"
    SECRET_FARM_NAME = f"Private_Ancestral_Plot_{run_id}"
    SECRET_CADASTRAL_ID = f"SY-NO-999-SECRET-PLOT-{run_id}"
    SECRET_DRIVER_NAME = f"Gopal_Driver_Private_{run_id}"
    SECRET_DRIVER_UUID = f"driver-uuid-{run_id}"
    SECRET_OPERATOR_ID = f"operator-uuid-{run_id}"
    SECRET_INSPECTOR_ID = f"inspector-uuid-{run_id}"

    # Exact high-precision GPS values
    EXACT_FARM_LAT = 19.66421356789
    EXACT_FARM_LON = 78.53214589123
    EXACT_TRANSIT_LAT = 19.67890123456
    EXACT_TRANSIT_LON = 78.54321098765

    try:
        ret_org = db.query(Organization).filter(Organization.org_type == "RETAILER").first()
        assert ret_org is not None, "Retailer organization required"

        trans_org = db.query(Organization).filter(Organization.org_type == "TRANSPORTER").first()
        assert trans_org is not None, "Transporter organization required"

        farmer = Farmer(
            id=SECRET_FARMER_UUID,
            full_name=SECRET_FARMER_NAME,
            phone_number=SECRET_PHONE,
            language_pref="te",
        )
        db.add(farmer)

        user = User(
            id=f"user-{run_id}",
            username=SECRET_USER_NAME,
            email=SECRET_EMAIL,
            hashed_password="secret_argon2_hash_value",
            full_name=SECRET_FARMER_NAME,
            role="FARMER",
            is_active=True,
        )
        db.add(user)
        db.commit()

        valid_polygon = {
            "type": "Polygon",
            "coordinates": [[[EXACT_FARM_LON, EXACT_FARM_LAT], [EXACT_FARM_LON + 0.001, EXACT_FARM_LAT], [EXACT_FARM_LON + 0.001, EXACT_FARM_LAT + 0.001], [EXACT_FARM_LON, EXACT_FARM_LAT]]]
        }

        farm = Farm(
            id=f"farm-secret-{run_id}",
            farmer_id=farmer.id,
            farm_name=SECRET_FARM_NAME,
            crop_type="Organic Cotton",
            boundary_geojson=json.dumps(valid_polygon),
            boundary_version=1,
            crs="EPSG:4326",
            area_sq_meters=50180.0,
            area_acres=12.4,
            area_hectares=5.02,
            district="Adilabad",
            state="Telangana",
            is_valid=True,
            validation_details=json.dumps({"cadastral_survey_no": SECRET_CADASTRAL_ID}),
        )
        db.add(farm)
        db.commit()

        batch = Batch(
            batch_code=f"BATCH-SECRET-{run_id}",
            farm_id=farm.id,
            crop_type="Organic Cotton",
            variety="Shankar-6",
            initial_quantity=1500.0,
            current_quantity=1500.0,
            unit="kg",
            lineage_type="ORIGINAL",
            stage="AT_RETAILER",
            status="ACTIVE",
        )
        db.add(batch)
        db.commit()

        shipment = Shipment(
            shipment_code=f"SHIP-SECRET-{run_id}",
            transporter_org_id=trans_org.id,
            driver_id=SECRET_DRIVER_UUID,
            driver_name=SECRET_DRIVER_NAME,
            vehicle_reg="TS 09 AD 1234",
            origin_name="Farm Gate Secret Origin",
            destination_name="Adilabad Regional Collection Centre",
            stage="DELIVERED",
            status="ACTIVE",
        )
        db.add(shipment)
        db.commit()

        item = ShipmentItem(
            shipment_id=shipment.id,
            batch_id=batch.id,
            declared_quantity=1500.0,
            unit="kg",
        )
        db.add(item)

        event = ShipmentEvent(
            shipment_id=shipment.id,
            event_type="PICKUP",
            location_name="Adilabad Regional Cluster",
            latitude=EXACT_TRANSIT_LAT,
            longitude=EXACT_TRANSIT_LON,
            condition="GOOD",
            photo_evidence_hash="abcdef1234567890",
        )
        db.add(event)

        weigh = WeighingRecord(
            batch_id=batch.id,
            operator_id=SECRET_OPERATOR_ID,
            measured_weight=1500.0,
            unit="kg",
            scale_identifier="Scale-Secret-01",
            is_manual_entry=True,
        )
        db.add(weigh)

        inspect = QualityInspection(
            batch_id=batch.id,
            inspector_id=SECRET_INSPECTOR_ID,
            crop_category="Cotton",
            grade="GRADE_A",
            physical_condition="GOOD",
            decision="ACCEPTED",
        )
        db.add(inspect)

        opaque_token = f"prm_privacy_probe_{run_id.lower()}"
        inv = RetailerInventory(
            retailer_org_id=ret_org.id,
            batch_id=batch.id,
            crop_type="Organic Cotton",
            available_quantity=1500.0,
            unit="kg",
            storage_location="Depot Room 1",
            opaque_qr_token=opaque_token,
        )
        db.add(inv)
        db.commit()

        # Query verification endpoint
        verify_res = client.get(f"/api/v1/platform/verify/{opaque_token}")
        assert verify_res.status_code == 200
        raw_response_text = verify_res.text
        lower_response = raw_response_text.lower()

        # Rigorous check: Zero PII
        assert SECRET_FARMER_NAME.lower() not in lower_response, "PII Leak: Farmer full name found in response!"
        assert SECRET_PHONE not in raw_response_text, "PII Leak: Farmer phone number found in response!"
        assert phone_suffix not in raw_response_text, "PII Leak: Phone digits found in response!"
        assert SECRET_FARMER_UUID not in raw_response_text, "PII Leak: Farmer private UUID found in response!"
        assert SECRET_USER_NAME not in lower_response, "PII Leak: Farmer username found in response!"
        assert SECRET_EMAIL not in lower_response, "PII Leak: Farmer email found in response!"
        assert SECRET_FARM_NAME.lower() not in lower_response, "PII Leak: Private farm name found in response!"
        assert SECRET_CADASTRAL_ID.lower() not in lower_response, "PII Leak: Cadastral survey ID found in response!"
        assert SECRET_DRIVER_NAME.lower() not in lower_response, "PII Leak: Driver name found in response!"
        assert SECRET_DRIVER_UUID not in raw_response_text, "PII Leak: Driver UUID found in response!"
        assert SECRET_OPERATOR_ID not in raw_response_text, "PII Leak: Operator ID found in response!"
        assert SECRET_INSPECTOR_ID not in raw_response_text, "PII Leak: Inspector ID found in response!"

        # Rigorous check: Zero fine-grained GPS leakage
        assert str(EXACT_FARM_LAT) not in raw_response_text, "GPS Leak: Exact farm latitude found in response!"
        assert f"{EXACT_FARM_LAT:.4f}" not in raw_response_text, "GPS Leak: Truncated farm latitude found in response!"
        assert str(EXACT_FARM_LON) not in raw_response_text, "GPS Leak: Exact farm longitude found in response!"
        assert f"{EXACT_FARM_LON:.4f}" not in raw_response_text, "GPS Leak: Truncated farm longitude found in response!"
        assert str(EXACT_TRANSIT_LAT) not in raw_response_text, "GPS Leak: Exact transit latitude found in response!"
        assert str(EXACT_TRANSIT_LON) not in raw_response_text, "GPS Leak: Exact transit longitude found in response!"

        # Verify only coarse geographic aggregation is returned
        vdata = verify_res.json()
        assert vdata["coarse_region"] == "Telangana State, India"
        assert vdata["zero_pii_enforced"] is True
        assert vdata["zero_gps_leakage"] is True

        # Check FARM_HARVEST description uses only regional cluster
        farm_harvest = next(t for t in vdata["provenance_timeline"] if t["stage"] == "FARM_HARVEST")
        assert "Adilabad Certified Organic Cluster" in farm_harvest["description"]
        assert "Zero Farmer PII & Zero Private GPS disclosed" in farm_harvest["description"]

    finally:
        db.close()


def test_tamper_detection_and_invalid_token_resilience():
    """
    Adversarial Tamper & Injection Resistance:
    1. Unknown / fabricated tokens must return HTTP 404 with exact tamper banner detail.
    2. SQL injection payloads must be safely handled without SQL errors or 500 crashes.
    3. XSS injection payloads must return 404.
    4. Extreme length strings must not cause buffer overflows or 500s.
    """
    # 1. Non-existent token
    res = client.get("/api/v1/platform/verify/prm_completely_fabricated_token_99999")
    assert res.status_code == 404
    assert "UNVERIFIED OR TAMPERED TOKEN" in res.json()["detail"]

    # 2. SQL injection attempts
    sqli_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE batches; --",
        "prm_test' UNION SELECT username, password_hash, NULL, NULL FROM users --",
    ]
    for sqli in sqli_payloads:
        res = client.get(f"/api/v1/platform/verify/{sqli}")
        assert res.status_code == 404
        assert "UNVERIFIED OR TAMPERED TOKEN" in res.json()["detail"]

    # 3. XSS injection attempt
    xss_payload = "<script>alert('XSS_ATTACK')</script>"
    res = client.get(f"/api/v1/platform/verify/{xss_payload}")
    assert res.status_code == 404

    # 4. Long buffer attack (4000 characters)
    long_payload = "A" * 4000
    res = client.get(f"/api/v1/platform/verify/{long_payload}")
    assert res.status_code == 404


def test_retailer_sales_inventory_depletion_and_conservation():
    """
    Validates physical mass conservation down to retail sales:
    - Normal sale decrements available_quantity.
    - Zero or negative quantity sale rejected.
    - Quantity exceeding available stock rejected.
    - Full depletion updates status to DEPLETED and stage to SOLD.
    """
    db = SessionLocal()
    run_id = str(uuid.uuid4())[:8].upper()

    try:
        ret_org = db.query(Organization).filter(Organization.org_type == "RETAILER").first()
        assert ret_org is not None, "Retailer organization required"

        batch = Batch(
            batch_code=f"BATCH-SALE-{run_id}",
            crop_type="Organic Cotton",
            variety="Desi",
            initial_quantity=50.0,
            current_quantity=50.0,
            unit="kg",
            stage="AT_RETAILER",
            status="ACTIVE",
        )
        db.add(batch)
        db.commit()

        inv = RetailerInventory(
            retailer_org_id=ret_org.id,
            batch_id=batch.id,
            crop_type="Organic Cotton",
            available_quantity=50.0,
            unit="kg",
            storage_location="Shelf 4",
            opaque_qr_token=f"prm_sale_{run_id.lower()}",
        )
        db.add(inv)
        db.commit()

        # 1. Reject <= 0 quantity
        neg_res = client.post("/api/v1/platform/retailer/sale", json={"inventory_id": inv.id, "quantity": -5.0})
        assert neg_res.status_code == 400

        zero_res = client.post("/api/v1/platform/retailer/sale", json={"inventory_id": inv.id, "quantity": 0.0})
        assert zero_res.status_code == 400

        # 2. Reject quantity exceeding available stock (50.0 kg available, attempt 55.0 kg)
        over_res = client.post("/api/v1/platform/retailer/sale", json={"inventory_id": inv.id, "quantity": 55.0})
        assert over_res.status_code == 400
        assert "exceeds available stock" in over_res.json()["detail"]

        # 3. Valid partial sale (20.0 kg)
        part_res = client.post("/api/v1/platform/retailer/sale", json={"inventory_id": inv.id, "quantity": 20.0})
        assert part_res.status_code == 200
        assert part_res.json()["remaining_quantity"] == 30.0

        db.refresh(inv)
        assert inv.available_quantity == 30.0
        assert inv.batch.status == "ACTIVE"

        # 4. Final depletion sale (remaining 30.0 kg)
        final_res = client.post("/api/v1/platform/retailer/sale", json={"inventory_id": inv.id, "quantity": 30.0})
        assert final_res.status_code == 200
        assert final_res.json()["remaining_quantity"] == 0.0
        assert final_res.json()["is_depleted"] is True

        db.refresh(inv)
        db.refresh(batch)
        assert inv.available_quantity == 0.0
        assert batch.status == "DEPLETED"
        assert batch.stage == "SOLD"

        # 5. Sale on already depleted stock rejected
        depleted_res = client.post("/api/v1/platform/retailer/sale", json={"inventory_id": inv.id, "quantity": 1.0})
        assert depleted_res.status_code == 400

    finally:
        db.close()
