import uuid
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class ActorTrust(Base):
    __tablename__ = "actor_trust_scores"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_id = Column(String, nullable=False, unique=True, index=True)
    actor_type = Column(String, nullable=False, index=True)  # FARMER, TRANSPORTER, COLLECTION_CENTRE, RETAILER, DEVICE
    current_trust = Column(Float, nullable=False, default=0.50)
    baseline_trust = Column(Float, nullable=False, default=0.50)
    decay_lambda = Column(Float, nullable=False, default=0.01155)  # half-life ~60 days
    total_submissions = Column(Integer, nullable=False, default=0)
    successful_submissions = Column(Integer, nullable=False, default=0)
    violation_count = Column(Integer, nullable=False, default=0)
    last_activity_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    events = relationship("TrustEvent", back_populates="actor", cascade="all, delete-orphan")


class TrustEvent(Base):
    __tablename__ = "trust_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_id = Column(String, ForeignKey("actor_trust_scores.actor_id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)  # POSITIVE_VERIFICATION, DECAY_EVALUATION, SUBSTANTIATED_VIOLATION, TRANSITIVE_PENALTY
    score_before = Column(Float, nullable=False)
    score_after = Column(Float, nullable=False)
    delta = Column(Float, nullable=False)
    reference_id = Column(String, nullable=True, index=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    actor = relationship("ActorTrust", back_populates="events")

