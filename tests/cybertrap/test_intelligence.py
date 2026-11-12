import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.models.cybertrap import CyberTrapEvent, CyberTrapIncident
from backend.app.models.farmer import Farmer
from backend.app.models.supply_chain import Batch
from backend.app.services.cybertrap.threat_intelligence import ThreatIntelligenceEngine


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


def test_rule_canary_activated():
    event = CyberTrapEvent(
        id=str(uuid.uuid4()),
        decoy_id="decoy-batch-001",
        decoy_type="HONEYTOKEN",
        request_method="GET",
        request_path="/api/v1/cybertrap/decoys/batches/BATCH-HONEY-01",
        source_ip="192.168.1.100",
        is_honeytoken_triggered=True,
        honeytoken_id="honey-saffron-key",
    )
    analysis = ThreatIntelligenceEngine.evaluate_event_rules(event)
    assert analysis["risk_level"] == "HIGH"
    assert analysis["category"] == "DATA_EXFILTRATION"
    assert any(r["rule"] == "CANARY_ACTIVATED" for r in analysis["rules_triggered"])


def test_rule_sqli_attempt():
    event = CyberTrapEvent(
        id=str(uuid.uuid4()),
        decoy_id="decoy-auth-login",
        decoy_type="API_ENDPOINT",
        request_method="POST",
        request_path="/api/v1/cybertrap/decoys/auth/login",
        source_ip="10.0.0.5",
        payload_json='{"username": "admin\' OR 1=1 --", "password": "x"}',
        is_honeytoken_triggered=False,
    )
    analysis = ThreatIntelligenceEngine.evaluate_event_rules(event)
    assert analysis["risk_level"] == "HIGH"
    assert analysis["category"] == "SQLI_PROBE"
    assert any(r["rule"] == "SQLI_ATTEMPT" for r in analysis["rules_triggered"])


def test_rule_admin_enumeration():
    event = CyberTrapEvent(
        id=str(uuid.uuid4()),
        decoy_id="decoy-admin-export",
        decoy_type="ADMIN_PORTAL",
        request_method="GET",
        request_path="/api/v1/cybertrap/decoys/admin/db_dump",
        source_ip="172.16.0.42",
        is_honeytoken_triggered=False,
    )
    analysis = ThreatIntelligenceEngine.evaluate_event_rules(event)
    assert analysis["risk_level"] == "MEDIUM"
    assert analysis["category"] == "ADMIN_ENUMERATION"


def test_rule_credential_stuffing_detection():
    now = datetime.now(timezone.utc)
    ip = "198.51.100.22"
    # Create 5 historical auth attempts within 10 minutes
    context = [
        CyberTrapEvent(
            id=str(uuid.uuid4()),
            decoy_id="decoy-auth",
            decoy_type="API_ENDPOINT",
            request_method="POST",
            request_path="/api/v1/cybertrap/decoys/auth/login",
            source_ip=ip,
            timestamp=now - timedelta(minutes=i),
            is_honeytoken_triggered=False,
        )
        for i in range(1, 5)
    ]
    current = CyberTrapEvent(
        id=str(uuid.uuid4()),
        decoy_id="decoy-auth",
        decoy_type="API_ENDPOINT",
        request_method="POST",
        request_path="/api/v1/cybertrap/decoys/auth/login",
        source_ip=ip,
        timestamp=now,
        is_honeytoken_triggered=False,
    )
    analysis = ThreatIntelligenceEngine.evaluate_event_rules(current, context)
    assert analysis["risk_level"] == "CRITICAL"
    assert analysis["category"] == "CREDENTIAL_STUFFING"


def test_rule_burst_scan_detection():
    now = datetime.now(timezone.utc)
    ip = "203.0.113.88"
    # 10 requests within 60 seconds
    context = [
        CyberTrapEvent(
            id=str(uuid.uuid4()),
            decoy_id="decoy-probe",
            decoy_type="API_ENDPOINT",
            request_method="GET",
            request_path="/api/v1/cybertrap/decoys/probe",
            source_ip=ip,
            timestamp=now - timedelta(seconds=i * 5),
            is_honeytoken_triggered=False,
        )
        for i in range(1, 10)
    ]
    current = CyberTrapEvent(
        id=str(uuid.uuid4()),
        decoy_id="decoy-probe",
        decoy_type="API_ENDPOINT",
        request_method="GET",
        request_path="/api/v1/cybertrap/decoys/probe",
        source_ip=ip,
        timestamp=now,
        is_honeytoken_triggered=False,
    )
    analysis = ThreatIntelligenceEngine.evaluate_event_rules(current, context)
    assert analysis["risk_level"] == "HIGH"
    assert any(r["rule"] == "BURST_SCAN" for r in analysis["rules_triggered"])


def test_rule_low_signal_isolated():
    event = CyberTrapEvent(
        id=str(uuid.uuid4()),
        decoy_id="decoy-simple",
        decoy_type="API_ENDPOINT",
        request_method="GET",
        request_path="/api/v1/cybertrap/decoys/public_ping",
        source_ip="192.0.2.1",
        is_honeytoken_triggered=False,
    )
    analysis = ThreatIntelligenceEngine.evaluate_event_rules(event)
    assert analysis["risk_level"] == "LOW"
    assert analysis["category"] == "RECONNAISSANCE"


def test_analyse_events_and_generate_incidents(db_session):
    ip = "192.168.10.99"
    ev1 = CyberTrapEvent(
        id=str(uuid.uuid4()),
        decoy_id="decoy-sqli",
        decoy_type="API_ENDPOINT",
        request_method="POST",
        request_path="/api/v1/cybertrap/decoys/search",
        source_ip=ip,
        payload_json='{"query": "UNION SELECT 1,2,3"}',
        is_honeytoken_triggered=False,
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(ev1)
    db_session.commit()

    result = ThreatIntelligenceEngine.analyse_events_and_generate_incidents(db_session)
    assert result["events_analyzed"] >= 1
    assert result["incidents_created"] >= 1

    inc = db_session.query(CyberTrapIncident).filter(CyberTrapIncident.source_ip == ip).first()
    assert inc is not None
    assert inc.risk_level == "HIGH"
    assert inc.canonical_report_hash is not None


def test_canonical_incident_hash_deterministic():
    data1 = {"category": "SQLI_PROBE", "risk": "HIGH", "source_ip": "1.2.3.4"}
    data2 = {"risk": "HIGH", "source_ip": "1.2.3.4", "category": "SQLI_PROBE"}
    hash1 = ThreatIntelligenceEngine.compute_canonical_incident_hash(data1)
    hash2 = ThreatIntelligenceEngine.compute_canonical_incident_hash(data2)
    assert hash1 == hash2


def test_zero_agricultural_cross_contamination(db_session):
    farmer = Farmer(id=str(uuid.uuid4()), full_name="Somaiah", phone_number="+919988776655")
    batch = Batch(
        id=str(uuid.uuid4()),
        batch_code="BATCH-LEGIT-001",
        farm_id="farm-001",
        crop_type="Organic Cotton",
        initial_quantity=500.0,
        current_quantity=500.0,
        unit="kg",
        stage="FARM_HARVESTED",
        status="ACTIVE",
    )
    db_session.add(farmer)
    db_session.add(batch)
    db_session.commit()

    ThreatIntelligenceEngine.analyse_events_and_generate_incidents(db_session)

    # Real farmer and batch must remain completely unflagged, pristine and active
    f = db_session.query(Farmer).filter(Farmer.id == farmer.id).first()
    b = db_session.query(Batch).filter(Batch.id == batch.id).first()
    assert f.full_name == "Somaiah"
    assert b.status == "ACTIVE"


def test_api_intel_endpoints(client, db_session):
    ev = CyberTrapEvent(
        id=str(uuid.uuid4()),
        decoy_id="decoy-batch-test",
        decoy_type="HONEY_BATCH",
        request_method="GET",
        request_path="/api/v1/cybertrap/decoys/batches/BATCH-TEST",
        source_ip="10.10.10.10",
        is_honeytoken_triggered=True,
        honeytoken_id="test-token",
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(ev)
    db_session.commit()

    # Trigger analysis
    r_analyse = client.post("/api/v1/cybertrap/intel/analyse")
    assert r_analyse.status_code == 200

    # List events
    r_events = client.get("/api/v1/cybertrap/intel/events")
    assert r_events.status_code == 200
    assert r_events.json()["total"] >= 1

    # List incidents
    r_inc = client.get("/api/v1/cybertrap/intel/incidents")
    assert r_inc.status_code == 200
    assert len(r_inc.json()["items"]) >= 1

    # Patterns
    r_patterns = client.get("/api/v1/cybertrap/intel/patterns")
    assert r_patterns.status_code == 200
    assert "risk_distribution" in r_patterns.json()

    # Metrics
    r_metrics = client.get("/api/v1/cybertrap/intel/metrics")
    assert r_metrics.status_code == 200
    assert r_metrics.json()["false_positive_rate_pct"] == 0.0

