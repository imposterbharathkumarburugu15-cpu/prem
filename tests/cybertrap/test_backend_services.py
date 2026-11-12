import json
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.models.cybertrap import CyberTrapEvent, CyberTrapIncident, CyberTrapRule
from backend.app.models.farmer import Farmer
from backend.app.models.farm import Farm
from backend.app.models.supply_chain import Batch
from backend.app.models.audit_log import AuditLog
from backend.app.services.cybertrap.threat_engine import ThreatEngine
from backend.app.services.cybertrap.defense_service import DefenseService
from backend.app.services.cybertrap.ledger_anchor import LedgerAnchorService
from backend.app.core.cybertrap_middleware import CyberTrapDefensiveMiddleware
from crypto.authority import verify_checkpoint_signature


@pytest.fixture
def db_session():
    """Isolated in-memory SQLite database session for unit and integration testing."""
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
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    CyberTrapDefensiveMiddleware.invalidate_cache()
    CyberTrapDefensiveMiddleware._rate_limit_history.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    CyberTrapDefensiveMiddleware.invalidate_cache()
    CyberTrapDefensiveMiddleware._rate_limit_history.clear()


# ==============================================================================
# 1. Threat Engine Tests (Categorization, Risk Scoring, Isolation)
# ==============================================================================

def test_threat_engine_reconnaissance_categorization():
    event = CyberTrapEvent(
        id=str(uuid.uuid4()),
        decoy_id="decoy-admin-export",
        decoy_type="ADMIN_PORTAL",
        request_method="GET",
        request_path="/api/v1/cybertrap/decoys/admin/db_dump",
        source_ip="192.168.10.45",
        is_honeytoken_triggered=False,
    )
    analysis = ThreatEngine.evaluate_event(event)
    assert analysis["category"] == "RECONNAISSANCE"
    assert analysis["risk_level"] in ["LOW", "MEDIUM"]
    assert "explanation" in analysis
    assert analysis["explanation"]["primary_rule"] == "RECONNAISSANCE"
    assert analysis["explanation"]["source_ip"] == "192.168.10.45"


def test_threat_engine_brute_force_categorization():
    now = datetime.now(timezone.utc)
    ip = "198.51.100.30"
    # Create 3 prior auth events in context
    context = [
        CyberTrapEvent(
            id=str(uuid.uuid4()),
            decoy_id="decoy-auth-login",
            decoy_type="API_ENDPOINT",
            request_method="POST",
            request_path="/api/v1/cybertrap/decoys/auth/login",
            source_ip=ip,
            timestamp=now - timedelta(minutes=i),
            is_honeytoken_triggered=False,
        )
        for i in range(1, 4)
    ]
    current_event = CyberTrapEvent(
        id=str(uuid.uuid4()),
        decoy_id="decoy-auth-login",
        decoy_type="API_ENDPOINT",
        request_method="POST",
        request_path="/api/v1/cybertrap/decoys/auth/login",
        source_ip=ip,
        timestamp=now,
        is_honeytoken_triggered=False,
    )
    analysis = ThreatEngine.evaluate_event(current_event, recent_context=context)
    assert analysis["category"] == "BRUTE_FORCE"
    assert analysis["risk_level"] in ["HIGH", "CRITICAL"]
    assert any(r["rule"] == "BRUTE_FORCE" for r in analysis["rules_triggered"])


def test_threat_engine_data_exfiltration_categorization():
    event = CyberTrapEvent(
        id=str(uuid.uuid4()),
        decoy_id="decoy-batch-saffron",
        decoy_type="HONEY_BATCH",
        request_method="GET",
        request_path="/api/v1/cybertrap/decoys/batches/BATCH-HONEY-SAFFRON-001",
        source_ip="203.0.113.15",
        is_honeytoken_triggered=False,
    )
    analysis = ThreatEngine.evaluate_event(event)
    assert analysis["category"] == "DATA_EXFILTRATION"
    assert analysis["risk_level"] == "HIGH"
    assert "exfiltration" in analysis["explanation"]["rationale"].lower()


def test_threat_engine_canary_honeytoken_triggered_categorization():
    event = CyberTrapEvent(
        id=str(uuid.uuid4()),
        decoy_id="decoy-canary-token",
        decoy_type="HONEYTOKEN",
        request_method="GET",
        request_path="/api/v1/cybertrap/decoys/tokens/validate",
        source_ip="198.51.100.88",
        is_honeytoken_triggered=True,
        honeytoken_id="prm_trap_saff_9941a8e2b",
    )
    analysis = ThreatEngine.evaluate_event(event)
    assert analysis["category"] == "CANARY_HONEYTOKEN_TRIGGERED"
    assert analysis["risk_level"] == "CRITICAL"
    assert analysis["explanation"]["primary_rule"] == "CANARY_HONEYTOKEN_TRIGGERED"


def test_threat_engine_sqli_probe_categorization():
    event = CyberTrapEvent(
        id=str(uuid.uuid4()),
        decoy_id="decoy-login",
        decoy_type="API_ENDPOINT",
        request_method="POST",
        request_path="/api/v1/cybertrap/decoys/auth/login",
        source_ip="172.20.0.10",
        payload_json='{"username": "admin\' union select null, null --", "password": "x"}',
        is_honeytoken_triggered=False,
    )
    analysis = ThreatEngine.evaluate_event(event)
    assert analysis["category"] == "SQLI_PROBE"
    assert analysis["risk_level"] == "HIGH"
    assert any("SQL" in r["rationale"] for r in analysis["rules_triggered"])


def test_threat_engine_dos_burst_categorization():
    now = datetime.now(timezone.utc)
    ip = "10.0.1.50"
    context = [
        CyberTrapEvent(
            id=str(uuid.uuid4()),
            decoy_id="decoy-fast-scan",
            decoy_type="API_ENDPOINT",
            request_method="GET",
            request_path=f"/api/v1/cybertrap/decoys/item/{i}",
            source_ip=ip,
            timestamp=now - timedelta(seconds=i * 2),
            is_honeytoken_triggered=False,
        )
        for i in range(1, 6)
    ]
    current_event = CyberTrapEvent(
        id=str(uuid.uuid4()),
        decoy_id="decoy-fast-scan",
        decoy_type="API_ENDPOINT",
        request_method="GET",
        request_path="/api/v1/cybertrap/decoys/item/0",
        source_ip=ip,
        timestamp=now,
        is_honeytoken_triggered=False,
    )
    analysis = ThreatEngine.evaluate_event(current_event, recent_context=context)
    assert analysis["category"] == "DOS_BURST"
    assert analysis["risk_level"] == "HIGH"


def test_threat_engine_strict_isolation_guarantee(db_session):
    """Guarantees ThreatEngine never modifies farmer or agricultural records."""
    # Seed genuine farmer and batch
    farmer = Farmer(
        farmer_id="FARMER-TEST-999",
        name="Ramesh Patel",
        phone="+919876543210",
        aadhaar_hash="sha256:abc12345",
        status="ACTIVE",
    )
    db_session.add(farmer)
    db_session.commit()

    # Create malicious honeypot event
    event = CyberTrapEvent(
        id=str(uuid.uuid4()),
        decoy_id="decoy-honeypot",
        decoy_type="API_ENDPOINT",
        request_method="POST",
        request_path="/api/v1/cybertrap/decoys/auth/login",
        source_ip="198.51.100.99",
        payload_json='{"username": "admin\' OR 1=1 --"}',
        is_honeytoken_triggered=True,
        honeytoken_id="prm_trap_test_123",
    )
    db_session.add(event)
    db_session.commit()

    # Process threat engine
    incident = ThreatEngine.process_event_to_incident(db_session, event)
    assert incident is not None
    assert incident.category in ["CANARY_HONEYTOKEN_TRIGGERED", "SQLI_PROBE"]

    # Verify farmer status is completely unchanged
    refreshed_farmer = db_session.query(Farmer).filter(Farmer.farmer_id == "FARMER-TEST-999").first()
    assert refreshed_farmer.status == "ACTIVE"


def test_threat_engine_incident_aggregation_and_rfc8785_hash(db_session):
    ip = "203.0.113.77"
    ev1 = CyberTrapEvent(
        id=str(uuid.uuid4()),
        decoy_id="decoy-1",
        decoy_type="HONEY_BATCH",
        request_method="GET",
        request_path="/api/v1/cybertrap/decoys/batches/BATCH-HONEY-01",
        source_ip=ip,
        is_honeytoken_triggered=False,
    )
    db_session.add(ev1)
    db_session.commit()

    inc1 = ThreatEngine.process_event_to_incident(db_session, ev1)
    assert inc1.event_count == 1
    assert inc1.canonical_report_hash is not None

    ev2 = CyberTrapEvent(
        id=str(uuid.uuid4()),
        decoy_id="decoy-2",
        decoy_type="HONEY_BATCH",
        request_method="GET",
        request_path="/api/v1/cybertrap/decoys/batches/BATCH-HONEY-02",
        source_ip=ip,
        is_honeytoken_triggered=False,
    )
    db_session.add(ev2)
    db_session.commit()

    inc2 = ThreatEngine.process_event_to_incident(db_session, ev2)
    assert inc2.id == inc1.id
    assert inc2.event_count == 2


# ==============================================================================
# 2. Threat Intel APIs Tests
# ==============================================================================

def test_threat_intel_api_endpoints(client, db_session):
    # Seed an incident
    inc = CyberTrapIncident(
        id=str(uuid.uuid4()),
        category="BRUTE_FORCE",
        risk_level="CRITICAL",
        source_ip="198.51.100.101",
        event_count=5,
        description="Brute force auth probe",
        explanation_json=json.dumps({"primary_rule": "BRUTE_FORCE", "rationale": "High-frequency auth attempts"}),
        status="ACTIVE",
    )
    db_session.add(inc)
    db_session.commit()

    # 1. GET /api/v1/cybertrap/intelligence/incidents
    r = client.get("/api/v1/cybertrap/intelligence/incidents")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert any(i["id"] == inc.id for i in data["items"])

    # 2. GET /api/v1/cybertrap/intelligence/incidents/{id}
    r = client.get(f"/api/v1/cybertrap/intelligence/incidents/{inc.id}")
    assert r.status_code == 200
    assert r.json()["category"] == "BRUTE_FORCE"
    assert r.json()["risk_level"] == "CRITICAL"

    # 3. GET /api/v1/cybertrap/intelligence/overview
    r = client.get("/api/v1/cybertrap/intelligence/overview")
    assert r.status_code == 200
    overview = r.json()
    assert "total_incidents" in overview
    assert "risk_breakdown" in overview
    assert overview["risk_breakdown"]["CRITICAL"] >= 1


# ==============================================================================
# 3. Defense Service & Defensive Rules APIs Tests
# ==============================================================================

def test_defense_service_rule_proposals_and_lifecycle(db_session):
    inc = CyberTrapIncident(
        id=str(uuid.uuid4()),
        category="DOS_BURST",
        risk_level="HIGH",
        source_ip="192.0.2.80",
        event_count=10,
        description="DoS burst attack",
        explanation_json="{}",
        status="ACTIVE",
    )
    db_session.add(inc)
    db_session.commit()

    # Step 1: Propose Rules
    rules = DefenseService.propose_rules_from_incidents(db_session)
    assert len(rules) == 1
    rule = rules[0]
    assert rule.status == "PROPOSED"
    assert rule.rule_type == "RATE_LIMIT"
    assert rule.target_value == "192.0.2.80"

    # Step 2: Validate in Staging Sandbox
    validated_rule = DefenseService.validate_rule_in_staging(db_session, rule.id)
    assert validated_rule.status == "STAGING_VALIDATED"
    results = json.loads(validated_rule.staging_validation_results)
    assert results["sandbox_status"] == "PASSED"
    assert results["legitimate_farmer_traffic_interrupted"] == 0
    assert results["false_positive_rate"] == 0.0

    # Step 3: Approve Rule
    approved_rule = DefenseService.approve_rule(
        db=db_session,
        rule_id=rule.id,
        approved_by="Cybersecurity Administrator (Dr. K. Rao)",
    )
    assert approved_rule.status == "ACTIVE"
    assert approved_rule.version == 2
    assert approved_rule.approved_by == "Cybersecurity Administrator (Dr. K. Rao)"


def test_defense_service_rule_rejection(db_session):
    inc = CyberTrapIncident(
        id=str(uuid.uuid4()),
        category="RECONNAISSANCE",
        risk_level="HIGH",
        source_ip="192.0.2.81",
        event_count=2,
        description="Recon probe",
        explanation_json="{}",
        status="ACTIVE",
    )
    db_session.add(inc)
    db_session.commit()

    rule = DefenseService.propose_rules_from_incidents(db_session)[0]
    rejected_rule = DefenseService.reject_rule(
        db=db_session,
        rule_id=rule.id,
        rejected_by="Platform Admin",
        rejection_reason="Benign penetration testing IP",
    )
    assert rejected_rule.status == "REJECTED"
    assert "Benign penetration testing IP" in rejected_rule.rejection_reason


def test_defensive_rules_api_endpoints(client, db_session):
    inc = CyberTrapIncident(
        id=str(uuid.uuid4()),
        category="CANARY_HONEYTOKEN_TRIGGERED",
        risk_level="CRITICAL",
        source_ip="198.51.100.222",
        event_count=1,
        description="Canary token triggered",
        explanation_json="{}",
        status="ACTIVE",
    )
    db_session.add(inc)
    db_session.commit()

    # 1. Propose via API
    r_prop = client.post("/api/v1/cybertrap/rules/propose")
    assert r_prop.status_code == 200
    rule_id = r_prop.json()["rules"][0]["id"]

    # 2. List rules
    r_list = client.get("/api/v1/cybertrap/rules")
    assert r_list.status_code == 200
    assert any(rule["id"] == rule_id for rule in r_list.json()["items"])

    # 3. Validate Staging
    r_val = client.post(
        "/api/v1/cybertrap/rules/validate-staging",
        json={"rule_id": rule_id},
    )
    assert r_val.status_code == 200
    assert r_val.json()["status"] == "STAGING_VALIDATED"

    # 4. Approve
    r_app = client.post(
        f"/api/v1/cybertrap/rules/{rule_id}/approve",
        json={"approved_by": "Security Officer Jane"},
    )
    assert r_app.status_code == 200
    assert r_app.json()["new_status"] == "ACTIVE"

    # 5. Manifest (Signed with Authority NIST P-256 ECDSA)
    r_man = client.get("/api/v1/cybertrap/rules/manifest")
    assert r_man.status_code == 200
    manifest = r_man.json()
    assert "signature" in manifest
    assert "X-Praman-Rule-Version" in r_man.headers

    # Verify signature
    is_valid = verify_checkpoint_signature(manifest)
    assert is_valid is True


# ==============================================================================
# 4. Defensive Middleware Tests (HTTP 429 & HTTP 403 Enforcement)
# ==============================================================================

def test_defensive_middleware_quarantine_enforcement(client):
    quarantined_ip = "198.51.100.199"
    innocent_ip = "192.168.1.10"

    # Register active quarantine rule in middleware cache
    mock_rule = {
        "id": "rule-quarantine-test",
        "rule_type": "IP_QUARANTINE",
        "target_value": quarantined_ip,
        "parameters": {"action": "403"},
    }
    CyberTrapDefensiveMiddleware.reload_active_rules([mock_rule])

    # Request from quarantined IP -> 403 Forbidden
    resp = client.get("/api/v1/cybertrap/intelligence/overview", headers={"X-Forwarded-For": quarantined_ip})
    assert resp.status_code == 403
    assert "quarantined" in resp.json()["detail"].lower()

    # Request from innocent IP -> 200 OK
    resp_ok = client.get("/api/v1/cybertrap/intelligence/overview", headers={"X-Forwarded-For": innocent_ip})
    assert resp_ok.status_code == 200


def test_defensive_middleware_rate_limit_enforcement(client):
    rate_limited_ip = "203.0.113.66"

    mock_rule = {
        "id": "rule-ratelimit-test",
        "rule_type": "RATE_LIMIT",
        "target_value": rate_limited_ip,
        "parameters": {
            "max_requests_per_minute": 2,
            "window_seconds": 60,
            "action": "429",
        },
    }
    CyberTrapDefensiveMiddleware.reload_active_rules([mock_rule])
    CyberTrapDefensiveMiddleware._rate_limit_history.clear()

    # 1st request -> 200 OK
    r1 = client.get("/api/v1/cybertrap/intelligence/overview", headers={"X-Forwarded-For": rate_limited_ip})
    assert r1.status_code == 200

    # 2nd request -> 200 OK
    r2 = client.get("/api/v1/cybertrap/intelligence/overview", headers={"X-Forwarded-For": rate_limited_ip})
    assert r2.status_code == 200

    # 3rd request -> 429 Too Many Requests
    r3 = client.get("/api/v1/cybertrap/intelligence/overview", headers={"X-Forwarded-For": rate_limited_ip})
    assert r3.status_code == 429
    assert "Rate limit exceeded" in r3.json()["detail"]
    assert "Retry-After" in r3.headers


# ==============================================================================
# 5. Ledger Anchor & Audit APIs Tests (RFC 8785, Checkpoints, Verification)
# ==============================================================================

def test_ledger_anchor_incident_and_checkpoint_signing(db_session):
    inc = CyberTrapIncident(
        id=str(uuid.uuid4()),
        category="SQLI_PROBE",
        risk_level="HIGH",
        source_ip="192.168.50.12",
        event_count=3,
        description="SQL injection in search",
        explanation_json="{}",
        status="ACTIVE",
    )
    db_session.add(inc)
    db_session.commit()

    receipt = LedgerAnchorService.anchor_incident(db_session, inc.id)
    assert receipt["status"] == "ANCHORED"
    assert receipt["canonical_report_hash"] is not None
    assert receipt["signature"] is not None

    # Verify AuditLog entry was chained
    log_entry = db_session.query(AuditLog).filter(AuditLog.log_id == receipt["audit_log_id"]).first()
    assert log_entry is not None
    assert log_entry.event_type == "CYBERTRAP_INCIDENT"
    assert log_entry.entity_id == inc.id

    # Verify Checkpoint signature
    checkpoint = receipt["checkpoint"]
    assert verify_checkpoint_signature(checkpoint) is True


def test_ledger_anchor_integrity_verification_and_tamper_detection(db_session):
    inc = CyberTrapIncident(
        id=str(uuid.uuid4()),
        category="DATA_EXFILTRATION",
        risk_level="HIGH",
        source_ip="198.51.100.150",
        event_count=1,
        description="Honey-batch exfiltration probe",
        explanation_json="{}",
        status="ACTIVE",
    )
    db_session.add(inc)
    db_session.commit()

    # Anchor incident
    LedgerAnchorService.anchor_incident(db_session, inc.id)

    # 1. Verification of intact record
    verify_res = LedgerAnchorService.verify_incident(db_session, inc.id)
    assert verify_res["status"] == "VERIFIED_INTACT"
    assert verify_res["is_intact"] is True

    # 2. Tampering test: modify description in DB
    inc.description = "Tampered description by unauthorized party"
    db_session.commit()

    tamper_res = LedgerAnchorService.verify_incident(db_session, inc.id)
    assert tamper_res["status"] == "TAMPER_DETECTED"
    assert tamper_res["is_intact"] is False
    assert "mismatch" in tamper_res["reason"].lower()


def test_audit_api_endpoints(client, db_session):
    inc = CyberTrapIncident(
        id=str(uuid.uuid4()),
        category="BRUTE_FORCE",
        risk_level="CRITICAL",
        source_ip="203.0.113.200",
        event_count=4,
        description="Brute force auth attempt",
        explanation_json="{}",
        status="ACTIVE",
    )
    db_session.add(inc)
    db_session.commit()

    # 1. POST /api/v1/cybertrap/audit/anchor/{id}
    r_anchor = client.post(f"/api/v1/cybertrap/audit/anchor/{inc.id}")
    assert r_anchor.status_code == 200
    data_anchor = r_anchor.json()
    assert data_anchor["status"] == "ANCHORED"

    # 2. GET /api/v1/cybertrap/audit/verify/{id}
    r_verify = client.get(f"/api/v1/cybertrap/audit/verify/{inc.id}")
    assert r_verify.status_code == 200
    data_verify = r_verify.json()
    assert data_verify["status"] == "VERIFIED_INTACT"
    assert data_verify["is_intact"] is True

    # 3. GET /api/v1/cybertrap/audit/checkpoints
    r_checkpoints = client.get("/api/v1/cybertrap/audit/checkpoints")
    assert r_checkpoints.status_code == 200
    checkpoints = r_checkpoints.json()["items"]
    assert len(checkpoints) >= 1
    assert any(c["incident_id"] == inc.id for c in checkpoints)
