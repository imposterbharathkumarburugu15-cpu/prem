import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class Batch(Base):
    __tablename__ = "batches"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_code = Column(String, nullable=False, unique=True, index=True)
    farm_id = Column(String, ForeignKey("farms.id"), nullable=True, index=True)
    crop_type = Column(String, nullable=False)
    variety = Column(String, nullable=True)
    harvest_date = Column(DateTime, nullable=True)
    initial_quantity = Column(Float, nullable=False, default=0.0)
    current_quantity = Column(Float, nullable=False, default=0.0)
    unit = Column(String, nullable=False, default="kg")
    
    # Lineage tracking
    parent_batch_id = Column(String, ForeignKey("batches.id"), nullable=True, index=True)
    lineage_type = Column(String, nullable=True)  # ORIGINAL, SPLIT_CHILD, MERGED_PRODUCT
    
    # State tracking
    stage = Column(String, nullable=False, default="FARM_HARVESTED")
    # Stages: FARM_HARVESTED, IN_TRANSIT_TO_CENTRE, AT_COLLECTION_CENTRE, GRADING, PROCESSED, IN_TRANSIT_TO_RETAIL, AT_RETAILER, SOLD
    status = Column(String, nullable=False, default="ACTIVE")  # ACTIVE, SPLIT, MERGED, DISPATCHED, DEPLETED, HOLD
    
    collection_centre_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)
    retailer_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)
    
    quality_grade = Column(String, nullable=True)  # GRADE_A, GRADE_B, GRADE_C, REJECTED
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    farm = relationship("Farm")
    centre_org = relationship("Organization", foreign_keys=[collection_centre_id], back_populates="batches_at_centre")
    parent_batch = relationship("Batch", remote_side=[id], backref="child_batches")
    shipment_items = relationship("ShipmentItem", back_populates="batch")
    inspections = relationship("QualityInspection", back_populates="batch")
    weighing_records = relationship("WeighingRecord", back_populates="batch")
    inventory_items = relationship("RetailerInventory", back_populates="batch")
    business_events = relationship("BusinessEvent", back_populates="batch", cascade="all, delete-orphan")


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    shipment_code = Column(String, nullable=False, unique=True, index=True)
    transporter_org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    driver_id = Column(String, nullable=True)
    driver_name = Column(String, nullable=True)
    vehicle_reg = Column(String, nullable=True)
    
    origin_name = Column(String, nullable=False)
    origin_address = Column(String, nullable=True)
    destination_name = Column(String, nullable=False)
    destination_address = Column(String, nullable=True)
    
    stage = Column(String, nullable=False, default="ASSIGNED")  # ASSIGNED, PICKED_UP, IN_TRANSIT, DELIVERED, INCIDENT_FLAGGED
    status = Column(String, nullable=False, default="ACTIVE")
    
    pickup_timestamp = Column(DateTime, nullable=True)
    delivery_timestamp = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    transporter_org = relationship("Organization", foreign_keys=[transporter_org_id], back_populates="shipments_as_transporter")
    items = relationship("ShipmentItem", back_populates="shipment", cascade="all, delete-orphan")
    events = relationship("ShipmentEvent", back_populates="shipment", cascade="all, delete-orphan")
    business_events = relationship("BusinessEvent", back_populates="shipment", cascade="all, delete-orphan")


class ShipmentItem(Base):
    __tablename__ = "shipment_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    shipment_id = Column(String, ForeignKey("shipments.id"), nullable=False, index=True)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=False, index=True)
    declared_quantity = Column(Float, nullable=False)
    picked_up_quantity = Column(Float, nullable=True)
    delivered_quantity = Column(Float, nullable=True)
    unit = Column(String, nullable=False, default="kg")
    condition = Column(String, nullable=True, default="GOOD")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    shipment = relationship("Shipment", back_populates="items")
    batch = relationship("Batch", back_populates="shipment_items")


class ShipmentEvent(Base):
    __tablename__ = "shipment_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    shipment_id = Column(String, ForeignKey("shipments.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)  # PICKUP, TRANSIT_CHECKPOINT, DELIVERY, INCIDENT
    location_name = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    condition = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    photo_evidence_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    shipment = relationship("Shipment", back_populates="events")


class WeighingRecord(Base):
    __tablename__ = "weighing_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id = Column(String, ForeignKey("batches.id"), nullable=False, index=True)
    operator_id = Column(String, nullable=False)
    measured_weight = Column(Float, nullable=False)
    unit = Column(String, nullable=False, default="kg")
    is_manual_entry = Column(Boolean, nullable=False, default=True)
    scale_identifier = Column(String, nullable=True)
    slip_photo_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    batch = relationship("Batch", back_populates="weighing_records")


class QualityInspection(Base):
    __tablename__ = "quality_inspections"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id = Column(String, ForeignKey("batches.id"), nullable=False, index=True)
    inspector_id = Column(String, nullable=False)
    crop_category = Column(String, nullable=False)
    grade = Column(String, nullable=False)  # GRADE_A, GRADE_B, GRADE_C, REJECTED
    physical_condition = Column(String, nullable=False)  # EXCELLENT, ACCEPTABLE, DAMAGED, CONTAMINATED
    moisture_pct = Column(Float, nullable=True)
    defect_notes = Column(Text, nullable=True)
    decision = Column(String, nullable=False)  # ACCEPTED, REJECTED, HOLD
    photo_evidence_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    batch = relationship("Batch", back_populates="inspections")


class ProcurementOrder(Base):
    __tablename__ = "procurement_orders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_code = Column(String, nullable=False, unique=True, index=True)
    retailer_org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    supplier_org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=False, index=True)
    ordered_quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=True)
    currency = Column(String, nullable=False, default="INR")
    status = Column(String, nullable=False, default="ORDERED")  # ORDERED, DISPATCHED, RECEIVED, REJECTED
    invoice_number = Column(String, nullable=True)
    received_quantity = Column(Float, nullable=True)
    receiving_condition = Column(String, nullable=True)
    receiving_photo_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    delivered_at = Column(DateTime, nullable=True)

    batch = relationship("Batch")


class RetailerInventory(Base):
    __tablename__ = "retailer_inventory"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    retailer_org_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=False, index=True)
    crop_type = Column(String, nullable=False)
    available_quantity = Column(Float, nullable=False, default=0.0)
    unit = Column(String, nullable=False, default="kg")
    storage_location = Column(String, nullable=True)
    opaque_qr_token = Column(String(128), nullable=True, unique=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    batch = relationship("Batch", back_populates="inventory_items")


class ChallengeResponse(Base):
    __tablename__ = "challenge_responses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    challenge_id = Column(String, nullable=False, index=True)
    evidence_id = Column(String, ForeignKey("evidence.id"), nullable=True, index=True)
    officer_id = Column(String, nullable=False)
    challenge_type = Column(String, nullable=False)  # FRESH_PHOTO_REQUEST, ADDITIONAL_METADATA, GPS_REVERIFICATION
    reason_code = Column(String, nullable=False)
    instructions = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="PENDING")  # PENDING, RESPONDED, EXPIRED, RESOLVED
    response_notes = Column(Text, nullable=True)
    response_evidence_id = Column(String, ForeignKey("evidence.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    responded_at = Column(DateTime, nullable=True)


class BusinessEvent(Base):
    __tablename__ = "business_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String, nullable=False, index=True)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=True, index=True)
    shipment_id = Column(String, ForeignKey("shipments.id"), nullable=True, index=True)
    farm_id = Column(String, ForeignKey("farms.id"), nullable=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)
    actor_id = Column(String, nullable=False, index=True)
    actor_role = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True, default=lambda: datetime.now(timezone.utc))
    payload_json = Column(Text, nullable=False, default="{}")
    metadata_json = Column(Text, nullable=False, default="{}")
    evidence_id = Column(String, ForeignKey("evidence.id"), nullable=True, index=True)
    evidence_hash = Column(String(64), nullable=True, index=True)
    verification_status = Column(String, nullable=False, default="VERIFIED")  # VERIFIED, FLAGGED, PENDING, FAILED
    verification_details_json = Column(Text, nullable=True, default="{}")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    batch = relationship("Batch", back_populates="business_events")
    shipment = relationship("Shipment", back_populates="business_events")
    farm = relationship("Farm")
    organization = relationship("Organization")
    evidence = relationship("Evidence")


