import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.core.database import Base, get_db
from backend.app.models.cybertrap import (
    CyberTrapEvent,
    CyberTrapDecoyBatch,
    CyberTrapIncident,
    CyberTrapRule,
)
from backend.app.models.farmer import Farmer
from backend.app.models.supply_chain import Batch
from backend.app.models.trust import ActorTrust
from backend.app.services.cybertrap.honeypot_service import honeypot_service


@pytest.fixture(scope="function")
def isolated_db(tmp_path):
    """Create an isolated temporary SQLite database for testing."""
    test_db_path = str(tmp_path / "test_cybertrap.db")
    test_engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    # Pre-seed real production data to verify strict isolation
    seed_db = TestingSessionLocal()
    try:
        real_farmer = Farmer(
            id="farmer-genuine-001",
            full_name="Ramesh Patel",
            phone_number="+919876543210",
            language_pref="te",
        )
        real_batch = Batch(
            id="batch-genuine-001",
            batch_code="BATCH-GENUINE-COTTON-001",
            crop_type="Organic Cotton",
            initial_quantity=1200.0,
            current_quantity=1200.0,
            unit="kg",
            stage="FARM_HARVESTED",
            status="ACTIVE",
        )
        real_trust = ActorTrust(
            actor_id="farmer-genuine-001",
            actor_type="FARMER",
            current_trust=0.95,
            baseline_trust=0.95,
        )
        seed_db.add_all([real_farmer, real_batch, real_trust])
        seed_db.commit()
    finally:
        seed_db.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client, TestingSessionLocal
    app.dependency_overrides.clear()


# =========================================================================
# TIER 1: FEATURE COVERAGE TESTS
# =========================================================================

def test_decoy_auth_login_captures_event(isolated_db):
    """Test 1: Decoy login endpoint returns realistic 401 and logs interaction."""
    client, SessionLocal = isolated_db
    login_payload = {
        "username": "admin@praman.internal",
        "password": "Password123!@#",
        "client_id": "probe_scanner_v1",
    }

    res = client.post(
        "/api/v1/cybertrap/decoys/auth/login",
        json=login_payload,
        headers={"User-Agent": "SecurityProbe/2.0"},
    )
    assert res.status_code == 401
    data = res.json()
    assert data["status"] == "error"
    assert data["error_code"] == "INVALID_CREDENTIALS"
    assert "LDAP_PRM_SECURE" in data["message"]
    assert "request_id" in data

    # Verify event logged in cybertrap_events table
    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(CyberTrapEvent.decoy_id == "DECOY-AUTH-LOGIN").first()
        assert event is not None
        assert event.decoy_type == "API_ENDPOINT"
        assert event.request_method == "POST"
        assert event.request_path == "/api/v1/cybertrap/decoys/auth/login"
        assert event.user_agent == "SecurityProbe/2.0"
        assert "admin@praman.internal" in (event.payload_json or "")
    finally:
        db.close()


def test_decoy_batches_catalog_returns_synthetic_records(isolated_db):
    """Test 2: Decoy honey-batches catalog returns high-value synthetic items."""
    client, SessionLocal = isolated_db
    res = client.get("/api/v1/cybertrap/decoys/batches")
    assert res.status_code == 200
    data = res.json()
    assert data["system_status"] == "ONLINE"
    assert data["total"] >= 3
    batch_ids = [b["id"] for b in data["batches"]]
    assert "BATCH-HONEY-SAFFRON-001" in batch_ids
    assert "BATCH-HONEY-CARDAMOM-002" in batch_ids
    assert "BATCH-HONEY-VANILLA-003" in batch_ids

    # Check canary secret is included
    saffron = next(b for b in data["batches"] if b["id"] == "BATCH-HONEY-SAFFRON-001")
    assert saffron["canary_token"].startswith("prm_trap_saff_")
    assert saffron["estimated_value_inr"] > 1000000.0

    # Verify logging
    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(CyberTrapEvent.decoy_id == "DECOY-BATCHES-CATALOG").first()
        assert event is not None
        assert event.decoy_type == "HONEY_BATCH"
    finally:
        db.close()


def test_decoy_batch_detail_access_and_honeytoken_trigger(isolated_db):
    """Test 3: Querying a specific honey-batch increments access and triggers honeytoken."""
    client, SessionLocal = isolated_db
    batch_id = "BATCH-HONEY-SAFFRON-001"

    res = client.get(f"/api/v1/cybertrap/decoys/batches/{batch_id}")
    assert res.status_code == 200
    batch_data = res.json()
    assert batch_data["id"] == batch_id
    assert batch_data["access_count"] >= 1
    assert batch_data["canary_token"] == "prm_trap_saff_9941a8e2b"

    # Verify event logged with honeytoken flag
    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(CyberTrapEvent.decoy_id == f"DECOY-BATCH-{batch_id}").first()
        assert event is not None
        assert event.is_honeytoken_triggered is True
        assert event.honeytoken_id == "prm_trap_saff_9941a8e2b"
    finally:
        db.close()


def test_decoy_admin_export_honeypot(isolated_db):
    """Test 4: Admin export honeypot returns simulated archive with canary token."""
    client, SessionLocal = isolated_db
    export_payload = {
        "format": "json",
        "tables": ["users", "batches", "audit_logs"],
        "include_credentials": True,
    }

    res = client.post("/api/v1/cybertrap/decoys/admin/export", json=export_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert "job_exp_" in data["export_job_id"]
    assert data["internal_access_token"].startswith("prm_trap_exp_admin_")
    assert data["record_count"] == 1420

    # Verify event logged as ADMIN_PORTAL
    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(CyberTrapEvent.decoy_id == "DECOY-ADMIN-EXPORT").first()
        assert event is not None
        assert event.decoy_type == "ADMIN_PORTAL"
        assert event.is_honeytoken_triggered is True
        assert event.honeytoken_id == data["internal_access_token"]
    finally:
        db.close()


def test_canary_token_validation_triggers_alert(isolated_db):
    """Test 5: Validating a canary token triggers honeytoken alerts in event logs."""
    client, SessionLocal = isolated_db
    canary_token = "prm_trap_saff_9941a8e2b"

    res = client.get(f"/api/v1/cybertrap/decoys/tokens/validate?token={canary_token}")
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["token"] == canary_token
    assert data["token_type"] == "INTERNAL_CANARY"

    # Verify event logged
    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(CyberTrapEvent.decoy_id == "DECOY-TOKEN-VALIDATE").first()
        assert event is not None
        assert event.is_honeytoken_triggered is True
        assert event.honeytoken_id == canary_token
    finally:
        db.close()


# =========================================================================
# TIER 1: INTUITIVE PROBE ALIAS TESTS
# =========================================================================

def test_probe_admin_export_database(isolated_db):
    """Test 6: Probe alias /api/v1/admin/export-database captures reconnaissance."""
    client, SessionLocal = isolated_db
    res = client.get("/api/v1/admin/export-database")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert "internal_access_token" in data
    assert data["internal_access_token"].startswith("prm_trap_db_admin_")

    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(CyberTrapEvent.decoy_id == "PROBE-ADMIN-EXPORT-DB").first()
        assert event is not None
        assert event.decoy_type == "ADMIN_PORTAL"
        assert event.is_honeytoken_triggered is True
    finally:
        db.close()


def test_probe_auth_internal_tokens(isolated_db):
    """Test 7: Probe alias /api/v1/auth/internal-tokens provides canary service tokens."""
    client, SessionLocal = isolated_db
    res = client.post("/api/v1/auth/internal-tokens")
    assert res.status_code == 200
    data = res.json()
    assert data["federation"] == "PRAMAN_INTERNAL_KMS"
    tokens = [t["token"] for t in data["active_tokens"]]
    assert len(tokens) >= 2
    assert all(t.startswith("prm_trap_") for t in tokens)

    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(CyberTrapEvent.decoy_id == "PROBE-AUTH-INTERNAL-TOKENS").first()
        assert event is not None
        assert event.decoy_type == "HONEYTOKEN"
        assert event.is_honeytoken_triggered is True
    finally:
        db.close()


def test_probe_evidence_raw_cas_dump(isolated_db):
    """Test 8: Probe alias /api/v1/evidence/raw-cas-dump captures data exfiltration probes."""
    client, SessionLocal = isolated_db
    res = client.get("/api/v1/evidence/raw-cas-dump")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ONLINE"
    assert len(data["sample_artifacts"]) >= 2
    assert any(a["canary_token"].startswith("prm_trap_") for a in data["sample_artifacts"])

    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(CyberTrapEvent.decoy_id == "PROBE-EVIDENCE-CAS-DUMP").first()
        assert event is not None
        assert event.is_honeytoken_triggered is True
    finally:
        db.close()


# =========================================================================
# TIER 1: EVENTS QUERY API
# =========================================================================

def test_list_events_admin_endpoint(isolated_db):
    """Test 9: Admin events query endpoint returns paginated interaction events."""
    client, _ = isolated_db
    # Trigger 3 interactions
    client.post("/api/v1/cybertrap/decoys/auth/login", json={"username": "scanner_user"})
    client.get("/api/v1/cybertrap/decoys/batches")
    client.get("/api/v1/admin/export-database")

    res = client.get("/api/v1/cybertrap/events?limit=10&offset=0")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 3
    assert len(data["events"]) >= 3

    # Test filtering by decoy_id
    filtered_res = client.get("/api/v1/cybertrap/events?decoy_id=DECOY-AUTH-LOGIN")
    assert filtered_res.status_code == 200
    f_data = filtered_res.json()
    assert f_data["total"] >= 1
    assert all(e["decoy_id"] == "DECOY-AUTH-LOGIN" for e in f_data["events"])


# =========================================================================
# TIER 2: BOUNDARY & CORNER CASES
# =========================================================================

def test_decoy_batch_detail_not_found_boundary(isolated_db):
    """Test 10: Non-existent honey-batch returns 404 but still logs the probe."""
    client, SessionLocal = isolated_db
    missing_id = "BATCH-HONEY-DOES-NOT-EXIST-999"

    res = client.get(f"/api/v1/cybertrap/decoys/batches/{missing_id}")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(
            CyberTrapEvent.decoy_id == f"DECOY-BATCH-NOT-FOUND-{missing_id}"
        ).first()
        assert event is not None
        assert event.decoy_type == "HONEY_BATCH"
    finally:
        db.close()


def test_decoy_auth_login_malformed_empty_payload(isolated_db):
    """Test 11: Empty or malformed login requests do not crash honeypot."""
    client, SessionLocal = isolated_db
    res = client.post("/api/v1/cybertrap/decoys/auth/login", json={})
    assert res.status_code == 401
    assert res.json()["status"] == "error"

    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(CyberTrapEvent.decoy_id == "DECOY-AUTH-LOGIN").order_by(
            CyberTrapEvent.timestamp.desc()
        ).first()
        assert event is not None
    finally:
        db.close()


def test_decoy_login_sqli_payload_preservation(isolated_db):
    """Test 12: SQL injection payloads are captured verbatim in payload_json."""
    client, SessionLocal = isolated_db
    sqli_attack = {
        "username": "admin' OR 1=1 --",
        "password": "' UNION SELECT * FROM farmers --",
    }
    res = client.post("/api/v1/cybertrap/decoys/auth/login", json=sqli_attack)
    assert res.status_code == 401

    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(CyberTrapEvent.decoy_id == "DECOY-AUTH-LOGIN").order_by(
            CyberTrapEvent.timestamp.desc()
        ).first()
        assert event is not None
        assert "UNION SELECT" in (event.payload_json or "")
        assert "OR 1=1" in (event.payload_json or "")
    finally:
        db.close()


def test_proxy_forwarded_for_ip_extraction(isolated_db):
    """Test 13: X-Forwarded-For client IP is accurately extracted and stored."""
    client, SessionLocal = isolated_db
    res = client.get(
        "/api/v1/cybertrap/decoys/batches",
        headers={
            "X-Forwarded-For": "198.51.100.42, 203.0.113.1",
            "User-Agent": "Masscan/1.3.2",
        },
    )
    assert res.status_code == 200

    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(CyberTrapEvent.source_ip == "198.51.100.42").first()
        assert event is not None
        assert event.user_agent == "Masscan/1.3.2"
    finally:
        db.close()


def test_canary_token_validation_benign_token(isolated_db):
    """Test 14: Validating a non-honeytoken does not flag honeytoken alert."""
    client, SessionLocal = isolated_db
    benign_token = "standard_bearer_auth_token_991823"
    res = client.get(f"/api/v1/cybertrap/decoys/tokens/validate?token={benign_token}")
    assert res.status_code == 200
    data = res.json()
    assert data["token_type"] == "STANDARD_BEARER"

    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(CyberTrapEvent.decoy_id == "DECOY-TOKEN-VALIDATE").order_by(
            CyberTrapEvent.timestamp.desc()
        ).first()
        assert event is not None
        assert event.is_honeytoken_triggered is False
        assert event.honeytoken_id is None
    finally:
        db.close()


# =========================================================================
# STRICT AGRICULTURAL ISOLATION GUARANTEE
# =========================================================================

def test_honeypot_strict_isolation_guarantee(isolated_db):
    """Test 15: Honeypot interactions NEVER query, modify, or expose genuine production tables.
    
    Verifies that real farmer records, genuine batches, and trust scores remain completely
    unaltered regardless of attacks on CyberTrap honeypots.
    """
    client, SessionLocal = isolated_db

    # 1. Execute multiple diverse attacker probes against CyberTrap decoys
    client.post("/api/v1/cybertrap/decoys/auth/login", json={"username": "malicious_actor", "password": "attack"})
    client.get("/api/v1/cybertrap/decoys/batches")
    client.get("/api/v1/cybertrap/decoys/batches/BATCH-HONEY-SAFFRON-001")
    client.post("/api/v1/cybertrap/decoys/admin/export", json={"tables": ["farmers", "batches"]})
    client.get("/api/v1/admin/export-database")
    client.get("/api/v1/auth/internal-tokens")
    client.get("/api/v1/evidence/raw-cas-dump")

    # 2. Inspect real production tables in database
    db = SessionLocal()
    try:
        # Genuine farmer check
        farmer = db.query(Farmer).filter(Farmer.id == "farmer-genuine-001").first()
        assert farmer is not None
        assert farmer.full_name == "Ramesh Patel"
        assert farmer.phone_number == "+919876543210"

        # Genuine batch check
        batch = db.query(Batch).filter(Batch.id == "batch-genuine-001").first()
        assert batch is not None
        assert batch.batch_code == "BATCH-GENUINE-COTTON-001"
        assert batch.initial_quantity == 1200.0
        assert batch.current_quantity == 1200.0
        assert batch.status == "ACTIVE"

        # Genuine trust score check: Honeypot events MUST NOT penalize farmers
        trust = db.query(ActorTrust).filter(ActorTrust.actor_id == "farmer-genuine-001").first()
        assert trust is not None
        assert trust.current_trust == 0.95

        # Check total production records counts
        assert db.query(Farmer).count() == 1
        assert db.query(Batch).count() == 1

        # Check CyberTrap records are cleanly isolated
        assert db.query(CyberTrapDecoyBatch).count() >= 3
        assert db.query(CyberTrapEvent).count() >= 7
    finally:
        db.close()


# =========================================================================
# TIER 3: REMEDIATION & ROBUSTNESS TESTS (ITERATION 2)
# =========================================================================

def test_decoy_raw_binary_and_malformed_payload_handling(isolated_db):
    """Test 16: Raw binary and non-JSON payloads are handled gracefully without 500 errors."""
    client, SessionLocal = isolated_db
    binary_payload = b"\x00\xff\xe7\x81\x9b\xa3\x00\x01\x02\xfe\xca\xfe\xba\xbe"

    # 1. Test binary payload on decoy auth login
    res_login = client.post(
        "/api/v1/cybertrap/decoys/auth/login",
        content=binary_payload,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert res_login.status_code == 401
    login_data = res_login.json()
    assert login_data["status"] == "error"
    assert login_data["error_code"] == "INVALID_CREDENTIALS"

    # 2. Test binary payload on decoy admin export
    res_export = client.post(
        "/api/v1/cybertrap/decoys/admin/export",
        content=binary_payload,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert res_export.status_code == 200
    export_data = res_export.json()
    assert export_data["status"] == "completed"
    assert "internal_access_token" in export_data

    # 3. Verify both interactions were logged in cybertrap_events
    db = SessionLocal()
    try:
        login_event = db.query(CyberTrapEvent).filter(
            CyberTrapEvent.decoy_id == "DECOY-AUTH-LOGIN"
        ).order_by(CyberTrapEvent.timestamp.desc()).first()
        assert login_event is not None
        assert login_event.payload_json is not None

        export_event = db.query(CyberTrapEvent).filter(
            CyberTrapEvent.decoy_id == "DECOY-ADMIN-EXPORT"
        ).order_by(CyberTrapEvent.timestamp.desc()).first()
        assert export_event is not None
        assert export_event.is_honeytoken_triggered is True
    finally:
        db.close()


def test_canary_token_url_encoded_extraction(isolated_db):
    """Test 17: URL-encoded canary honeytokens are unquoted and detected across payloads and headers."""
    client, SessionLocal = isolated_db
    raw_token = "prm_trap_saff_urlenc_9941a"
    encoded_token = "prm%5Ftrap%5Fsaff%5Furlenc%5F9941a"

    # 1. Test URL-encoded token in custom login payload
    res = client.post(
        "/api/v1/cybertrap/decoys/auth/login",
        json={"stolen_secret": encoded_token, "client": "scanner"},
    )
    assert res.status_code == 401

    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(
            CyberTrapEvent.decoy_id == "DECOY-AUTH-LOGIN"
        ).order_by(CyberTrapEvent.timestamp.desc()).first()
        assert event is not None
        assert event.is_honeytoken_triggered is True
        assert event.honeytoken_id == raw_token
    finally:
        db.close()

    # 2. Test URL-encoded token in custom HTTP header
    res_header = client.get(
        "/api/v1/cybertrap/decoys/batches",
        headers={"X-Canary-Probe": "prm%5Ftrap%5Fheader%5Ftest888"},
    )
    assert res_header.status_code == 200

    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(
            CyberTrapEvent.decoy_id == "DECOY-BATCHES-CATALOG"
        ).order_by(CyberTrapEvent.timestamp.desc()).first()
        assert event is not None
        assert event.is_honeytoken_triggered is True
        assert event.honeytoken_id == "prm_trap_header_test888"
    finally:
        db.close()


def test_proxy_ip_long_and_nul_byte_sanitization(isolated_db):
    """Test 18: Oversized proxy IPs (>45 chars) and NUL bytes are sanitized and truncated."""
    client, SessionLocal = isolated_db

    # 1. Oversized XFF string (>100 characters)
    oversized_ip = "192.168.1.50" + "A" * 100
    res = client.get("/api/v1/cybertrap/decoys/batches", headers={"X-Forwarded-For": oversized_ip})
    assert res.status_code == 200

    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(
            CyberTrapEvent.decoy_id == "DECOY-BATCHES-CATALOG"
        ).order_by(CyberTrapEvent.timestamp.desc()).first()
        assert event is not None
        assert len(event.source_ip) <= 45
        assert event.source_ip == oversized_ip[:45]
    finally:
        db.close()

    # 2. XFF string containing NUL bytes and comma-separated IPs
    nul_byte_ip = "10.0.0.1\x00evil_injection, 172.16.0.2"
    res2 = client.get("/api/v1/cybertrap/decoys/batches", headers={"X-Forwarded-For": nul_byte_ip})
    assert res2.status_code == 200

    db = SessionLocal()
    try:
        event2 = db.query(CyberTrapEvent).filter(
            CyberTrapEvent.decoy_id == "DECOY-BATCHES-CATALOG"
        ).order_by(CyberTrapEvent.timestamp.desc()).first()
        assert event2 is not None
        assert "\x00" not in event2.source_ip
        assert event2.source_ip == "10.0.0.1evil_injection"[:45]
    finally:
        db.close()


def test_decoy_batch_not_found_long_id_truncation(isolated_db):
    """Test 19: Long batch IDs in not-found queries are truncated to keep decoy_id <= 64 chars."""
    client, SessionLocal = isolated_db
    long_batch_id = "BATCH-NONEXISTENT-" + "X" * 100

    res = client.get(f"/api/v1/cybertrap/decoys/batches/{long_batch_id}")
    assert res.status_code == 404

    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(
            CyberTrapEvent.decoy_type == "HONEY_BATCH"
        ).order_by(CyberTrapEvent.timestamp.desc()).first()
        assert event is not None
        assert len(event.decoy_id) <= 64
        assert event.decoy_id == f"DECOY-BATCH-NOT-FOUND-{long_batch_id[:40]}"
    finally:
        db.close()
