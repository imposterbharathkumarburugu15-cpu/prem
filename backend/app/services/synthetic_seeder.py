import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from backend.app.core.database import SessionLocal
from backend.app.models.farmer import Farmer
from backend.app.models.farm import Farm
from backend.app.models.device import Device
from backend.app.models.evidence import Evidence
from backend.app.models.ai_assessment import AIAssessment
from backend.app.models.review_decision import ReviewDecision
from backend.app.models.public_token import PublicToken
from backend.app.models.user_org import Organization, User
from backend.app.models.supply_chain import (
    Batch,
    Shipment,
    ShipmentItem,
    ShipmentEvent,
    WeighingRecord,
    QualityInspection,
    ProcurementOrder,
    RetailerInventory,
    ChallengeResponse,
)


def seed_synthetic_development_data():
    """
    Populates a completely connected, repeatable synthetic dataset for local development.
    Strictly isolated and clearly tagged with [SYNTHETIC-DEV].
    Zero loss or modification of existing operational records.
    """
    db = SessionLocal()
    print("[INFO] Starting synthetic development dataset population...")

    pw_hash = hashlib.sha256("Praman@2026".encode("utf-8")).hexdigest()

    # 1. ORGANIZATIONS (Clearly marked as SYNTHETIC-DEV)
    org_specs = [
        ("Kisan Logistics Telangana [SYNTHETIC-DEV]", "TRANSPORTER", "Telangana", "Adilabad"),
        ("Deccan Agri Freight Lines [SYNTHETIC-DEV]", "TRANSPORTER", "Telangana", "Warangal"),
        ("Adilabad Cotton Collection Centre [SYNTHETIC-DEV]", "COLLECTION_CENTRE", "Telangana", "Adilabad"),
        ("Warangal Grain Processing Depot [SYNTHETIC-DEV]", "COLLECTION_CENTRE", "Telangana", "Warangal"),
        ("Nature Organics Retail Ltd [SYNTHETIC-DEV]", "RETAILER", "Telangana", "Hyderabad"),
        ("FreshKart Hypermarket [SYNTHETIC-DEV]", "RETAILER", "Telangana", "Secunderabad"),
        ("PRAMAN Integrity Bureau [SYNTHETIC-DEV]", "AUTHORITY", "Telangana", "Hyderabad"),
        ("PRAMAN Platform Governance [SYNTHETIC-DEV]", "ADMIN", "Telangana", "Hyderabad"),
    ]

    org_map = {}
    for name, org_type, state, dist in org_specs:
        org = db.query(Organization).filter(Organization.name == name).first()
        if not org:
            org = Organization(name=name, org_type=org_type, state=state, district=dist, is_active=True)
            db.add(org)
            db.flush()
        org_map[name] = org

    # 2. USERS (Roles with [SYNTHETIC-DEV] tagged affiliations)
    user_specs = [
        ("dev_transporter_adilabad", "trans_adl@praman-dev.org", "TRANSPORTER", "Kisan Logistics Telangana [SYNTHETIC-DEV]", "K. Mallesh (Transporter) [SYNTHETIC]"),
        ("dev_transporter_warangal", "trans_wgl@praman-dev.org", "TRANSPORTER", "Deccan Agri Freight Lines [SYNTHETIC-DEV]", "B. Venkatesh (Transporter) [SYNTHETIC]"),
        ("dev_centre_adilabad", "centre_adl@praman-dev.org", "COLLECTION_CENTRE", "Adilabad Cotton Collection Centre [SYNTHETIC-DEV]", "Suresh Reddy (Centre Manager) [SYNTHETIC]"),
        ("dev_centre_warangal", "centre_wgl@praman-dev.org", "COLLECTION_CENTRE", "Warangal Grain Processing Depot [SYNTHETIC-DEV]", "K. Srinivas (Centre Manager) [SYNTHETIC]"),
        ("dev_retailer_nature", "retail_nature@praman-dev.org", "RETAILER", "Nature Organics Retail Ltd [SYNTHETIC-DEV]", "Priya Sharma (Procurement Head) [SYNTHETIC]"),
        ("dev_retailer_freshkart", "retail_fresh@praman-dev.org", "RETAILER", "FreshKart Hypermarket [SYNTHETIC-DEV]", "Amit Patel (Category Manager) [SYNTHETIC]"),
        ("dev_officer_integrity", "officer@praman-dev.org", "EVIDENCE_INTEGRITY_OFFICER", "PRAMAN Integrity Bureau [SYNTHETIC-DEV]", "Dr. K. Rao (Evidence Integrity Officer) [SYNTHETIC]"),
        ("dev_admin_governance", "admin@praman-dev.org", "ADMIN", "PRAMAN Platform Governance [SYNTHETIC-DEV]", "System Administrator [SYNTHETIC]"),
    ]

    for uname, email, role, org_name, fname in user_specs:
        u = db.query(User).filter(User.username == uname).first()
        if not u:
            u = User(
                username=uname,
                email=email,
                hashed_password=pw_hash,
                full_name=fname,
                role=role,
                organization_id=org_map[org_name].id,
                is_active=True,
            )
            db.add(u)
            db.flush()

    # 3. SYNTHETIC FARMERS & FARMS
    farmers_data = [
        ("FRM-DEV-001", "G. Lakshmi Narayana [SYNTHETIC]", "+919848011221", "Cotton", "Adilabad Regional Farm [SYNTHETIC]"),
        ("FRM-DEV-002", "P. Anjaiah Naidu [SYNTHETIC]", "+919848033443", "Paddy", "Warangal Paddy Basin Farm [SYNTHETIC]"),
        ("FRM-DEV-003", "Ch. Rajeshwar Rao [SYNTHETIC]", "+919848055665", "Chilli", "Khammam Teja Chilli Farm [SYNTHETIC]"),
    ]

    farm_map = {}
    for fcode, name, phone, crop, farm_name in farmers_data:
        farmer = db.query(Farmer).filter(Farmer.phone_number == phone).first()
        if not farmer:
            farmer = Farmer(
                id=str(uuid.uuid4()),
                full_name=name,
                phone_number=phone,
                language_pref="te",
            )
            db.add(farmer)
            db.flush()

        farm = db.query(Farm).filter(Farm.farm_name == farm_name).first()
        if not farm:
            farm = Farm(
                id=str(uuid.uuid4()),
                farmer_id=farmer.id,
                farm_name=farm_name,
                crop_type=crop,
                state="Telangana",
                district=farm_name.split()[0],
                area_acres=4.5,
                area_sq_meters=18210.85,
                boundary_geojson='{"type":"Polygon","coordinates":[[[78.5,19.6],[78.51,19.6],[78.51,19.61],[78.5,19.61],[78.5,19.6]]]}',
            )
            db.add(farm)
            db.flush()
        farm_map[crop] = farm

    # 4. WORKFLOW 1: FULL CERTIFIED COTTON SUPPLY CHAIN (Harvested -> In Transit -> Graded -> Split -> Procured -> Stocked -> QR)
    # Quantities: 1200 kg Harvest -> 1200 kg Pickup -> 1195 kg Received (5 kg transit moisture loss)
    # Split: Child A (700 kg Grade A) + Child B (480 kg Grade B) + 15 kg processing loss (700+480+15 = 1195 kg)
    # Retail Procure Child A: 700 kg -> Stocked -> Customer QR
    farm_cotton = farm_map["Cotton"]
    b_code_1 = "BATCH-SYNTH-COTTON-2026-001"
    b1 = db.query(Batch).filter(Batch.batch_code == b_code_1).first()
    if not b1:
        b1 = Batch(
            batch_code=b_code_1,
            farm_id=farm_cotton.id,
            crop_type="Organic Cotton",
            variety="Suvin Long-Staple [SYNTHETIC-DEV]",
            harvest_date=datetime.now(timezone.utc) - timedelta(days=5),
            initial_quantity=1200.0,
            current_quantity=1200.0,
            unit="kg",
            stage="PROCESSED",
            status="SPLIT",
            collection_centre_id=org_map["Adilabad Cotton Collection Centre [SYNTHETIC-DEV]"].id,
            quality_grade="GRADE_A",
            notes="[SYNTHETIC-DEV] Full supply chain certified harvest demonstration",
        )
        db.add(b1)
        db.flush()

        # Shipment
        s1 = Shipment(
            shipment_code="SHIP-SYNTH-COTTON-001",
            transporter_org_id=org_map["Kisan Logistics Telangana [SYNTHETIC-DEV]"].id,
            driver_name="K. Mallesh [SYNTHETIC]",
            vehicle_reg="TS 01 AB 4021",
            origin_name="Adilabad Regional Farm [SYNTHETIC]",
            destination_name="Adilabad Cotton Collection Centre [SYNTHETIC-DEV]",
            stage="DELIVERED",
            status="COMPLETED",
            pickup_timestamp=datetime.now(timezone.utc) - timedelta(days=4),
            delivery_timestamp=datetime.now(timezone.utc) - timedelta(days=3),
            notes="[SYNTHETIC-DEV] Completed transport via NH 44 corridor",
        )
        db.add(s1)
        db.flush()

        db.add(ShipmentItem(shipment_id=s1.id, batch_id=b1.id, declared_quantity=1200.0, picked_up_quantity=1200.0, delivered_quantity=1195.0, unit="kg", condition="EXCELLENT"))
        db.add(ShipmentEvent(shipment_id=s1.id, event_type="PICKUP", location_name="Farm Gate", condition="EXCELLENT", notes="Seals verified"))
        db.add(ShipmentEvent(shipment_id=s1.id, event_type="TRANSIT_CHECKPOINT", location_name="Gudihathnoor Toll Plaza", condition="GOOD", notes="En route, tarpaulin intact"))
        db.add(ShipmentEvent(shipment_id=s1.id, event_type="DELIVERY", location_name="Adilabad Collection Centre", condition="EXCELLENT", notes="Delivered 1195 kg (5kg transit moisture loss)"))

        # Weighing & Inspection at Centre
        db.add(WeighingRecord(batch_id=b1.id, operator_id="dev_centre_adilabad", measured_weight=1195.0, unit="kg", is_manual_entry=True, scale_identifier="Scale-Elec-01"))
        db.add(QualityInspection(batch_id=b1.id, inspector_id="dev_centre_adilabad", crop_category="Cotton", grade="GRADE_A", physical_condition="EXCELLENT", moisture_pct=7.6, decision="ACCEPTED"))

        # Batch Split: Child A (700 kg Grade A) & Child B (480 kg Grade B)
        b1_child_a = Batch(
            batch_code=f"{b_code_1}-A",
            farm_id=farm_cotton.id,
            crop_type="Organic Cotton",
            variety="Suvin Long-Staple [SYNTHETIC-DEV]",
            initial_quantity=700.0,
            current_quantity=700.0,
            unit="kg",
            parent_batch_id=b1.id,
            lineage_type="SPLIT_CHILD",
            stage="AT_RETAILER",
            status="ACTIVE",
            collection_centre_id=org_map["Adilabad Cotton Collection Centre [SYNTHETIC-DEV]"].id,
            retailer_id=org_map["Nature Organics Retail Ltd [SYNTHETIC-DEV]"].id,
            quality_grade="GRADE_A",
            notes="[SYNTHETIC-DEV] Premium lint cotton child batch A",
        )
        b1_child_b = Batch(
            batch_code=f"{b_code_1}-B",
            farm_id=farm_cotton.id,
            crop_type="Organic Cotton",
            variety="Suvin Standard [SYNTHETIC-DEV]",
            initial_quantity=480.0,
            current_quantity=480.0,
            unit="kg",
            parent_batch_id=b1.id,
            lineage_type="SPLIT_CHILD",
            stage="PROCESSED",
            status="ACTIVE",
            collection_centre_id=org_map["Adilabad Cotton Collection Centre [SYNTHETIC-DEV]"].id,
            quality_grade="GRADE_B",
            notes="[SYNTHETIC-DEV] Standard grade child batch B remaining in centre inventory",
        )
        db.add(b1_child_a)
        db.add(b1_child_b)
        db.flush()

        # Retailer Procurement for Child A
        po_1 = ProcurementOrder(
            order_code="PO-SYNTH-2026-COTTON-001",
            retailer_org_id=org_map["Nature Organics Retail Ltd [SYNTHETIC-DEV]"].id,
            supplier_org_id=org_map["Adilabad Cotton Collection Centre [SYNTHETIC-DEV]"].id,
            batch_id=b1_child_a.id,
            ordered_quantity=700.0,
            unit_price=85.0,
            status="RECEIVED",
            invoice_number="INV-SYNTH-88210",
            received_quantity=700.0,
            receiving_condition="EXCELLENT",
        )
        db.add(po_1)
        db.flush()

        # Retailer Inventory and Customer Opaque QR Token
        qr_token_cotton = "prm_synth_organic_cotton_7810ad"
        inv_cotton = RetailerInventory(
            retailer_org_id=org_map["Nature Organics Retail Ltd [SYNTHETIC-DEV]"].id,
            batch_id=b1_child_a.id,
            crop_type="Organic Cotton",
            available_quantity=700.0,
            unit="kg",
            storage_location="Hyderabad Nature Hub Bay 2",
            opaque_qr_token=qr_token_cotton,
        )
        db.add(inv_cotton)

    # 5. WORKFLOW 2: ACTIVE TRANSIT SHIPMENT (Paddy from Warangal to Warangal Centre)
    farm_paddy = farm_map["Paddy"]
    b_code_2 = "BATCH-SYNTH-PADDY-2026-002"
    b2 = db.query(Batch).filter(Batch.batch_code == b_code_2).first()
    if not b2:
        b2 = Batch(
            batch_code=b_code_2,
            farm_id=farm_paddy.id,
            crop_type="Sona Masoori Paddy",
            variety="BPT 5204 [SYNTHETIC-DEV]",
            harvest_date=datetime.now(timezone.utc) - timedelta(days=1),
            initial_quantity=2500.0,
            current_quantity=2500.0,
            unit="kg",
            stage="IN_TRANSIT_TO_CENTRE",
            status="ACTIVE",
            notes="[SYNTHETIC-DEV] Active transit consignment en route to Warangal Depot",
        )
        db.add(b2)
        db.flush()

        s2 = Shipment(
            shipment_code="SHIP-SYNTH-PADDY-002",
            transporter_org_id=org_map["Deccan Agri Freight Lines [SYNTHETIC-DEV]"].id,
            driver_name="B. Venkatesh [SYNTHETIC]",
            vehicle_reg="TS 03 CD 9112",
            origin_name="Warangal Paddy Basin Farm [SYNTHETIC]",
            destination_name="Warangal Grain Processing Depot [SYNTHETIC-DEV]",
            stage="IN_TRANSIT",
            status="ACTIVE",
            pickup_timestamp=datetime.now(timezone.utc) - timedelta(hours=3),
            notes="[SYNTHETIC-DEV] Active logistics movement across Warangal outer ring road",
        )
        db.add(s2)
        db.flush()

        db.add(ShipmentItem(shipment_id=s2.id, batch_id=b2.id, declared_quantity=2500.0, picked_up_quantity=2500.0, unit="kg", condition="GOOD"))
        db.add(ShipmentEvent(shipment_id=s2.id, event_type="PICKUP", location_name="Paddy Basin Gate", condition="GOOD", notes="Loaded 2500 kg sacks"))
        db.add(ShipmentEvent(shipment_id=s2.id, event_type="TRANSIT_CHECKPOINT", location_name="Kazipet Bypass", condition="GOOD", notes="En route, on schedule"))

    # 6. WORKFLOW 3: SUSPICIOUS EVIDENCE SCENARIO FOR EVIDENCE INTEGRITY OFFICER
    # Synthetic suspicious case clearly flagged: Near-Duplicate / Tamper test scenario
    synth_device = db.query(Device).first()
    ev_synth_id = "ev_synth_tamper_flagged_case_99"
    ev_suspicious = db.query(Evidence).filter(Evidence.id == ev_synth_id).first()
    if not ev_suspicious and synth_device and farm_cotton:
        ev_suspicious = Evidence(
            id=ev_synth_id,
            farm_id=farm_cotton.id,
            device_id=synth_device.id,
            sequence_number=999,
            lifecycle_stage="HARVEST",
            image_hash="7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
            phash="ff88c3a1b0294e11",
            dhash="0011ee44aa77bb22",
            canonical_envelope_json='{"device_id":"synth-dev","metadata":{"scenario":"[SYNTHETIC-DEV] AI Invariant Check Simulation"}}',
            signature_b64="MEQCIDKj/synthSigP256MockForTestVerificationOnly==",
            status="PENDING_REVIEW",
        )
        db.add(ev_suspicious)
        db.flush()

        # Add AI assessment with flagged ELA variance and blur warning
        ai_assess = AIAssessment(
            id=str(uuid.uuid4()),
            evidence_id=ev_suspicious.id,
            blur_score=142.5,
            is_blurry=False,
            is_duplicate=True,
            nearest_phash_distance=2,  # Close to another image (suspicious near-duplicate)
            is_tamper_suspected=True,
            ela_variance=0.082,
            recommendation="FLAG_FOR_HUMAN_REVIEW",
            assessment_json='{"rule_version":"PRAMAN-AI-V2.1","reason_codes":["ERR_NEAR_DUPLICATE_PHASH","WARN_ELA_HIGH_VARIANCE"],"scenario":"SYNTHETIC_TEST_SCENARIO"}',
            sha256=ev_suspicious.image_hash,
            phash=ev_suspicious.phash,
        )
        db.add(ai_assess)

        # Dispatch an active challenge bound to this suspicious case
        chal = ChallengeResponse(
            challenge_id="CHAL-SYNTH-CASE-99",
            evidence_id=ev_suspicious.id,
            officer_id="dev_officer_integrity",
            challenge_type="FRESH_PHOTO_REQUEST",
            reason_code="ERR_NEAR_DUPLICATE_PHASH",
            instructions="[SYNTHETIC-DEV] Capture fresh wide-angle photograph of the harvesting swath with real-time GPS locked.",
            status="PENDING",
        )
        db.add(chal)

    db.commit()
    db.close()
    print("[SUCCESS] Fully connected synthetic development dataset successfully populated.")


if __name__ == "__main__":
    seed_synthetic_development_data()
