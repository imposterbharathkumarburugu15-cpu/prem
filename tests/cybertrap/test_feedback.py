import uuid
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.models.cybertrap import CyberTrapIncident, CyberTrapRule, CyberTrapEvent
from backend.app.services.cybertrap.adaptive_feedback import AdaptiveFeedbackEngine


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


def test_generate_proposals_from_incident(db_session):
    inc = CyberTrapIncident(
        id=str(uuid.uuid4()),
        category="CREDENTIAL_STUFFING",
        risk_level="CRITICAL",
        source_ip="198.51.100.44",
        description="Brute-force auth attack detected",
        explanation_json="{}",
        status="ACTIVE",
    )
    db_session.add(inc)
    db_session.commit()

    rules = AdaptiveFeedbackEngine.generate_defensive_proposals(db_session)
    assert len(rules) == 1
    assert rules[0].rule_type == "RATE_LIMIT"
    assert rules[0].status == "PROPOSED"
    assert rules[0].target_value == "198.51.100.44"


def test_rule_lifecycle_success_path(db_session):
    inc = CyberTrapIncident(
        id=str(uuid.uuid4()),
        category="DATA_EXFILTRATION",
        risk_level="HIGH",
        source_ip="203.0.113.50",
        description="Canary token triggered",
        explanation_json="{}",
        status="ACTIVE",
    )
    db_session.add(inc)
    db_session.commit()

    rule = AdaptiveFeedbackEngine.generate_defensive_proposals(db_session)[0]
    assert rule.status == "PROPOSED"

    # Step 1: Human Approval
    app_rule = AdaptiveFeedbackEngine.approve_rule(db_session, rule.id, "Security Officer Alice")
    assert app_rule.status == "APPROVED"
    assert app_rule.approved_by == "Security Officer Alice"

    # Step 2: Staging Validation
    val_rule = AdaptiveFeedbackEngine.validate_staging(db_session, rule.id)
    assert val_rule.status == "STAGING_VALIDATED"
    assert val_rule.staging_validation_results is not None
    assert "PASS" in val_rule.staging_validation_results

    # Step 3: Production Deployment
    dep_rule = AdaptiveFeedbackEngine.deploy_rule(db_session, rule.id, "Platform Admin Bob")
    assert dep_rule.status == "ACTIVE"
    assert dep_rule.version == 2

    # Step 4: Active Enforcement Check
    match = AdaptiveFeedbackEngine.check_request_against_active_rules(
        db_session, "203.0.113.50", "/api/v1/cybertrap/decoys/test"
    )
    assert match is not None
    assert match["blocked"] is True


def test_cannot_bypass_human_approval_to_deploy(db_session):
    inc = CyberTrapIncident(
        id=str(uuid.uuid4()),
        category="DOS_BURST",
        risk_level="HIGH",
        source_ip="192.0.2.99",
        description="Burst scan detected",
        explanation_json="{}",
        status="ACTIVE",
    )
    db_session.add(inc)
    db_session.commit()

    rule = AdaptiveFeedbackEngine.generate_defensive_proposals(db_session)[0]
    assert rule.status == "PROPOSED"

    # Invariant: Attempting to deploy directly without approval must fail!
    with pytest.raises(ValueError) as excinfo:
        AdaptiveFeedbackEngine.deploy_rule(db_session, rule.id, "Attacker")
    assert "must be 'STAGING_VALIDATED' before deployment" in str(excinfo.value)


def test_rule_rejection(db_session):
    inc = CyberTrapIncident(
        id=str(uuid.uuid4()),
        category="SQLI_PROBE",
        risk_level="HIGH",
        source_ip="10.20.30.40",
        description="SQL injection query",
        explanation_json="{}",
        status="ACTIVE",
    )
    db_session.add(inc)
    db_session.commit()

    rule = AdaptiveFeedbackEngine.generate_defensive_proposals(db_session)[0]
    rej_rule = AdaptiveFeedbackEngine.reject_rule(
        db_session, rule.id, "Admin Carol", "False positive test case"
    )
    assert rej_rule.status == "REJECTED"
    assert "False positive test case" in rej_rule.rejection_reason


def test_api_feedback_endpoints(client, db_session):
    inc = CyberTrapIncident(
        id=str(uuid.uuid4()),
        category="CREDENTIAL_STUFFING",
        risk_level="CRITICAL",
        source_ip="198.51.100.77",
        description="Auth stuffing test",
        explanation_json="{}",
        status="ACTIVE",
    )
    db_session.add(inc)
    db_session.commit()

    # Generate proposals via API
    r_gen = client.post("/api/v1/cybertrap/feedback/rules/generate")
    assert r_gen.status_code == 200
    rule_id = r_gen.json()["rule_ids"][0]

    # List rules
    r_list = client.get("/api/v1/cybertrap/feedback/rules")
    assert r_list.status_code == 200
    assert r_list.json()["total"] >= 1

    # Approve
    r_app = client.post(f"/api/v1/cybertrap/feedback/rules/{rule_id}/approve", json={"approved_by": "Dr. Rao"})
    assert r_app.status_code == 200
    assert r_app.json()["new_status"] == "APPROVED"

    # Validate Staging
    r_val = client.post(f"/api/v1/cybertrap/feedback/rules/{rule_id}/validate-staging")
    assert r_val.status_code == 200
    assert r_val.json()["new_status"] == "STAGING_VALIDATED"

    # Deploy
    r_dep = client.post(f"/api/v1/cybertrap/feedback/rules/{rule_id}/deploy")
    assert r_dep.status_code == 200
    assert r_dep.json()["new_status"] == "ACTIVE"

    # Check request
    r_chk = client.post("/api/v1/cybertrap/feedback/check", json={"source_ip": "198.51.100.77"})
    assert r_chk.status_code == 200
    assert r_chk.json()["allowed"] is False

