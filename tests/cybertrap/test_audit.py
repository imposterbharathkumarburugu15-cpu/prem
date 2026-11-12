import uuid
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.models.cybertrap import CyberTrapIncident, CyberTrapRule
from backend.app.models.audit_log import AuditLog
from backend.app.services.cybertrap.cybertrap_audit import CyberTrapLedgerAuditor


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_anchor_incident_creates_audit_entry(db_session):
    inc = CyberTrapIncident(
        id=str(uuid.uuid4()),
        category="CREDENTIAL_STUFFING",
        risk_level="CRITICAL",
        source_ip="198.51.100.12",
        description="Auth attack on decoy endpoints",
        explanation_json='{"rule": "CREDENTIAL_STUFFING"}',
        status="ACTIVE",
        canonical_report_hash=hashlib.sha256(b"canonical_test_payload").hexdigest(),
    )
    db_session.add(inc)
    db_session.commit()

    receipt = CyberTrapLedgerAuditor.anchor_incident_to_ledger(db_session, inc.id)
    assert receipt["status"] == "ANCHORED"
    assert receipt["ledger_checkpoint_id"] is not None

    # Verify audit entry exists in db
    entry = db_session.query(AuditLog).filter(AuditLog.log_id == receipt["ledger_checkpoint_id"]).first()
    assert entry is not None
    assert entry.event_type == "CYBERTRAP_INCIDENT_ANCHOR"
    assert entry.entity_id == inc.id


def test_verify_intact_incident(db_session):
    inc = CyberTrapIncident(
        id=str(uuid.uuid4()),
        category="SQLI_PROBE",
        risk_level="HIGH",
        source_ip="10.0.0.99",
        description="SQL injection in decoy search",
        explanation_json="{}",
        status="ACTIVE",
    )
    db_session.add(inc)
    db_session.commit()

    CyberTrapLedgerAuditor.anchor_incident_to_ledger(db_session, inc.id)

    verify_res = CyberTrapLedgerAuditor.verify_incident_integrity(db_session, inc.id)
    assert verify_res["status"] == "VERIFIED_INTACT"
    assert verify_res["is_intact"] is True
    assert verify_res["hash_chain_verified"] is True


def test_tamper_detection(db_session):
    inc = CyberTrapIncident(
        id=str(uuid.uuid4()),
        category="DATA_EXFILTRATION",
        risk_level="HIGH",
        source_ip="192.168.1.55",
        description="Canary token triggered",
        explanation_json="{}",
        status="ACTIVE",
    )
    db_session.add(inc)
    db_session.commit()

    CyberTrapLedgerAuditor.anchor_incident_to_ledger(db_session, inc.id)

    # Maliciously mutate the canonical_report_hash on the incident
    inc.canonical_report_hash = "0000000000000000000000000000000000000000000000000000000000000000"
    db_session.commit()

    # Verification must flag TAMPER_DETECTED!
    verify_res = CyberTrapLedgerAuditor.verify_incident_integrity(db_session, inc.id)
    assert verify_res["status"] == "TAMPER_DETECTED"
    assert verify_res["is_intact"] is False


def test_anchor_rule_transition(db_session):
    inc = CyberTrapIncident(
        id=str(uuid.uuid4()),
        category="SQLI_PROBE",
        risk_level="HIGH",
        source_ip="10.0.0.99",
        description="SQL injection test",
        explanation_json="{}",
        status="ACTIVE",
    )
    db_session.add(inc)
    db_session.commit()

    rule = CyberTrapRule(
        id=str(uuid.uuid4()),
        incident_id=inc.id,
        rule_type="RATE_LIMIT",
        target_value="10.0.0.99",
        status="APPROVED",
    )
    db_session.add(rule)
    db_session.commit()

    audit_entry = CyberTrapLedgerAuditor.anchor_rule_transition(
        db_session, rule.id, "RULE_APPROVED", "Admin Dr. Rao"
    )
    assert audit_entry.event_type == "CYBERTRAP_RULE_AUDIT"
    assert audit_entry.actor_id == "Admin Dr. Rao"


def test_api_audit_endpoints(client, db_session):
    inc = CyberTrapIncident(
        id=str(uuid.uuid4()),
        category="CREDENTIAL_STUFFING",
        risk_level="CRITICAL",
        source_ip="172.16.1.1",
        description="API audit test",
        explanation_json="{}",
        status="ACTIVE",
    )
    db_session.add(inc)
    db_session.commit()

    # Anchor via API
    r_anchor = client.post(f"/api/v1/cybertrap/audit/incidents/{inc.id}/anchor")
    assert r_anchor.status_code == 200
    assert r_anchor.json()["status"] == "ANCHORED"

    # Verify via API
    r_verify = client.get(f"/api/v1/cybertrap/audit/incidents/{inc.id}/verify")
    assert r_verify.status_code == 200
    assert r_verify.json()["status"] == "VERIFIED_INTACT"

    # Trail via API
    r_trail = client.get("/api/v1/cybertrap/audit/trail")
    assert r_trail.status_code == 200
    assert r_trail.json()["total"] >= 1

