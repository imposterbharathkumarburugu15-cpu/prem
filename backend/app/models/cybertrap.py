import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class CyberTrapEvent(Base):
    """Raw decoy interaction event logged by honeypots."""
    __tablename__ = "cybertrap_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    decoy_id = Column(String(64), nullable=False, index=True)
    decoy_type = Column(String(32), nullable=False)  # API_ENDPOINT, HONEY_BATCH, HONEYTOKEN, ADMIN_PORTAL
    request_method = Column(String(10), nullable=False)
    request_path = Column(String(255), nullable=False)
    source_ip = Column(String(45), nullable=False, index=True)
    user_agent = Column(Text, nullable=True)
    session_id = Column(String(64), nullable=True)
    headers_json = Column(Text, nullable=True)
    payload_json = Column(Text, nullable=True)
    query_params_json = Column(Text, nullable=True)
    is_honeytoken_triggered = Column(Boolean, default=False, nullable=False)
    honeytoken_id = Column(String(64), nullable=True)


class CyberTrapIncident(Base):
    """Aggregated threat intelligence incident."""
    __tablename__ = "cybertrap_incidents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    category = Column(String(64), nullable=False)  # RECONNAISSANCE, BRUTE_FORCE, CREDENTIAL_STUFFING, DATA_EXFILTRATION, ANOMALOUS_REPLAY, SQLI_PROBE
    risk_level = Column(String(20), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    source_ip = Column(String(45), nullable=False, index=True)
    event_count = Column(Integer, default=1, nullable=False)
    description = Column(Text, nullable=False)
    explanation_json = Column(Text, nullable=False)  # Explainable breakdown of why flagged
    status = Column(String(32), default="ACTIVE", nullable=False)  # ACTIVE, INVESTIGATING, MITIGATED, ARCHIVED
    canonical_report_hash = Column(String(64), nullable=True)  # SHA-256 digest
    ledger_checkpoint_id = Column(String(64), nullable=True)
    ledger_anchored_at = Column(DateTime, nullable=True)

    rules = relationship("CyberTrapRule", back_populates="incident", cascade="all, delete-orphan")


class CyberTrapRule(Base):
    """Adaptive defensive rule proposal and enforcement."""
    __tablename__ = "cybertrap_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("cybertrap_incidents.id"), nullable=True)
    rule_type = Column(String(32), nullable=False)  # RATE_LIMIT, IP_QUARANTINE, HEADER_BLOCK, CAPTCHA_CHALLENGE
    target_value = Column(String(255), nullable=False)  # IP address, User-Agent substring, CIDR
    parameters_json = Column(Text, nullable=True)  # e.g. {"rate_limit": "5/min", "duration_seconds": 3600}
    status = Column(String(32), default="PROPOSED", nullable=False)  # PROPOSED, STAGING_VALIDATED, APPROVED, ACTIVE, REJECTED, EXPIRED
    proposed_by = Column(String(64), default="THREAT_INTELLIGENCE_ENGINE", nullable=False)
    approved_by = Column(String(64), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    staging_validation_results = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    incident = relationship("CyberTrapIncident", back_populates="rules")


class CyberTrapDecoyBatch(Base):
    """Synthetic honey-batch definitions completely isolated from real batches."""
    __tablename__ = "cybertrap_decoy_batches"

    id = Column(String(64), primary_key=True)  # e.g. BATCH-HONEY-SAFFRON-001
    crop_type = Column(String(64), nullable=False)
    variety = Column(String(64), nullable=True, default="Super Negin Grade 1")
    declared_quantity = Column(Float, default=500.0, nullable=False)
    unit = Column(String(20), default="kg", nullable=False)
    honeytoken_secret = Column(String(64), nullable=False)
    synthetic_location = Column(String(128), default="Kashmir High Altitude Research Station")
    quality_grade = Column(String(32), default="GRADE_AAA_RESERVE")
    estimated_value_inr = Column(Float, default=1250000.0)
    custodian_org = Column(String(128), default="Synthetic Central Reserve Warehouse")
    access_count = Column(Integer, default=0, nullable=False)
    status = Column(String(32), default="ACTIVE", nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
