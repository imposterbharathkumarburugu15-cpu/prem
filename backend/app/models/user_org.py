import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    org_type = Column(String, nullable=False)  # TRANSPORTER, COLLECTION_CENTRE, RETAILER, AUTHORITY, ADMIN
    registration_number = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    address = Column(String, nullable=True)
    district = Column(String, nullable=True)
    state = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    users = relationship("User", back_populates="organization")
    shipments_as_transporter = relationship("Shipment", back_populates="transporter_org", foreign_keys="[Shipment.transporter_org_id]")
    batches_at_centre = relationship("Batch", back_populates="centre_org", foreign_keys="[Batch.collection_centre_id]")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False, index=True)  # TRANSPORTER, COLLECTION_CENTRE, RETAILER, EVIDENCE_INTEGRITY_OFFICER, ADMIN
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    organization = relationship("Organization", back_populates="users")

