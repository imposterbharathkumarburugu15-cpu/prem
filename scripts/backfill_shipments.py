import uuid
from datetime import datetime, timezone
from backend.app.core.database import SessionLocal
from backend.app.models.evidence import Evidence
from backend.app.models.device import Device
from backend.app.models.farmer import Farmer
from backend.app.models.farm import Farm
from backend.app.models.supply_chain import Shipment, ShipmentItem, Batch
from backend.app.models.user_org import Organization

db = SessionLocal()
transporter_org = db.query(Organization).filter(Organization.org_type == 'TRANSPORTER').first()
org_id = transporter_org.id if transporter_org else 'org-transporter-01'

all_ev = db.query(Evidence).order_by(Evidence.created_at.desc()).all()
created_count = 0

for ev in all_ev:
    # Resolve device and farmer
    dev = db.query(Device).filter(Device.id == ev.device_id).first()
    farmer_id = dev.farmer_id if dev else None
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first() if farmer_id else None
    f_name = farmer.full_name if farmer else 'Bharathkumar Burugu'
    f_phone = farmer.phone_number if farmer else '+91 8978336017'

    # Check if shipment already created for this sequence/evidence
    s_prefix = f"SHIP-TEL-{ev.sequence_number:03d}"
    existing_s = db.query(Shipment).filter(Shipment.shipment_code.like(f"{s_prefix}%")).first()
    if existing_s:
        continue

    # Create Batch
    batch_suffix = f"{ev.sequence_number}_{uuid.uuid4().hex[:4].upper()}"
    b = Batch(
        id=str(uuid.uuid4()),
        batch_code=f"BATCH-TEL-{batch_suffix}",
        farm_id=ev.farm_id or "farm_default",
        crop_type="Organic Cotton" if "COTTON" in str(ev.lifecycle_stage).upper() else "Organic Harvest Produce",
        variety="Shankar-6 Long Staple",
        harvest_date=datetime.now(timezone.utc),
        initial_quantity=1000.0,
        current_quantity=1000.0,
        unit="kg",
        stage="FARM_HARVESTED",
        status="ACTIVE",
        quality_grade="GRADE_A",
    )
    db.add(b)
    db.flush()

    # Create Shipment
    s_code = f"SHIP-TEL-{ev.sequence_number:03d}-{uuid.uuid4().hex[:4].upper()}"
    shp = Shipment(
        id=str(uuid.uuid4()),
        shipment_code=s_code,
        transporter_org_id=org_id,
        driver_name="Ramesh Kumar",
        vehicle_reg="TS-08-UB-4912",
        origin_name=f"{f_name}'s Farm Gate ({f_phone})",
        destination_name="Adilabad Central Collection Dock",
        stage="ASSIGNED",
        status="ACTIVE",
    )
    db.add(shp)
    db.flush()

    item = ShipmentItem(
        id=str(uuid.uuid4()),
        shipment_id=shp.id,
        batch_id=b.id,
        declared_quantity=1000.0,
        unit="kg",
        condition="EXCELLENT",
    )
    db.add(item)
    created_count += 1

db.commit()
print(f"Successfully created {created_count} shipments for mobile evidence records!")
