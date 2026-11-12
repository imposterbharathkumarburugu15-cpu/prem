"""Empirical Challenger 2: Adversarial Canary & Evasion Verification Suite.

Tests and verifies:
1. Honeytoken extraction and regex boundary conditions.
2. Evasion attempts: nested JSON, query parameter embedding, URL-encoded tokens, header embedding, non-serializable objects.
3. Proxy IP extraction robustness: XFF spoofing, SQLi in XFF, oversized XFF, empty/malformed XFF.
"""

import json
import urllib.parse
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.core.database import Base, get_db
from backend.app.models.cybertrap import CyberTrapEvent, CyberTrapDecoyBatch
from backend.app.services.cybertrap.honeypot_service import HoneypotService, honeypot_service


@pytest.fixture(scope="function")
def challenger_db(tmp_path):
    """Isolated temporary SQLite database for challenger tests."""
    test_db_path = str(tmp_path / "challenger_test.db")
    test_engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

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
# 1. HONEYTOKEN EXTRACTION & REGEX BOUNDARY TESTS
# =========================================================================

def test_honeytoken_extraction_direct_unit():
    """Verify unit-level honeytoken matching and extraction."""
    # Standard format
    assert HoneypotService.is_honeytoken("prm_trap_saff_9941a8e2b") is True
    assert HoneypotService.is_honeytoken("prm_trap_12345") is True
    assert HoneypotService.is_honeytoken("prm_trap_a-b_c") is True

    # Negative / boundary cases
    assert HoneypotService.is_honeytoken(None) is False
    assert HoneypotService.is_honeytoken("") is False
    assert HoneypotService.is_honeytoken("prm_trap_") is False  # Incomplete
    assert HoneypotService.is_honeytoken("prm_trapped_animal") is False  # Missing required underscore after trap_
    assert HoneypotService.is_honeytoken("standard_user_token") is False

    # Extract from dict
    data = {
        "user": "attacker",
        "auth": {"nested": "prm_trap_secret_abc123"},
        "tags": ["alpha", "prm_trap_tag_456", "prm_trap_secret_abc123"],
    }
    extracted = HoneypotService.extract_honeytokens(data)
    assert len(extracted) == 2
    assert "prm_trap_secret_abc123" in extracted
    assert "prm_trap_tag_456" in extracted

    # Extract None or empty
    assert HoneypotService.extract_honeytokens(None) == []
    assert HoneypotService.extract_honeytokens("") == []
    assert HoneypotService.extract_honeytokens({}) == []
    assert HoneypotService.extract_honeytokens([]) == []


def test_honeytoken_extraction_type_error_on_sets():
    """REMEDIATED: extract_honeytokens safely handles non-JSON serializable objects (e.g. sets) without TypeError."""
    tokens = HoneypotService.extract_honeytokens({"tokens": {"prm_trap_in_set"}})
    assert "prm_trap_in_set" in tokens


# =========================================================================
# 2. EVASION ATTEMPTS: NESTED JSON & PYDANTIC SCHEMA EVASION
# =========================================================================

def test_evasion_nested_json_dropped_by_pydantic_schema(challenger_db):
    """REMEDIATED: Non-standard nested JSON fields in login requests are preserved and honeytokens are detected."""
    client, SessionLocal = challenger_db

    # Payload with honeytoken in a nested custom field
    nested_payload = {
        "client_session": {
            "credentials": {
                "api_key": "prm_trap_evasion_nested_001"
            }
        }
    }

    res = client.post("/api/v1/cybertrap/decoys/auth/login", json=nested_payload)
    assert res.status_code == 401

    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(
            CyberTrapEvent.decoy_id == "DECOY-AUTH-LOGIN"
        ).order_by(CyberTrapEvent.timestamp.desc()).first()
        assert event is not None
        # VERIFIED: Arbitrary nested fields are preserved and honeytoken alert is triggered
        assert event.is_honeytoken_triggered is True
        assert event.honeytoken_id == "prm_trap_evasion_nested_001"
        assert "prm_trap_evasion_nested_001" in (event.payload_json or "")
    finally:
        db.close()


def test_evasion_nested_json_preserved_when_under_extra(challenger_db):
    """Verify that if nested data is placed under the explicit 'extra' field, it is detected."""
    client, SessionLocal = challenger_db

    nested_payload = {
        "extra": {
            "session_dump": {
                "secret": "prm_trap_extra_field_002"
            }
        }
    }

    res = client.post("/api/v1/cybertrap/decoys/auth/login", json=nested_payload)
    assert res.status_code == 401

    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(
            CyberTrapEvent.honeytoken_id == "prm_trap_extra_field_002"
        ).first()
        assert event is not None
        assert event.is_honeytoken_triggered is True
    finally:
        db.close()


def test_evasion_query_parameter_embedding(challenger_db):
    """Verify honeytoken passed in arbitrary query parameters is detected."""
    client, SessionLocal = challenger_db

    res = client.get("/api/v1/cybertrap/decoys/batches?debug_token=prm_trap_query_param_001&filter=all")
    assert res.status_code == 200

    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(
            CyberTrapEvent.honeytoken_id == "prm_trap_query_param_001"
        ).first()
        assert event is not None
        assert event.is_honeytoken_triggered is True
    finally:
        db.close()


def test_evasion_header_embedding(challenger_db):
    """Verify honeytoken embedded in HTTP request headers is detected."""
    client, SessionLocal = challenger_db

    headers = {
        "X-Custom-Canary": "prm_trap_header_custom_555",
        "Authorization": "Bearer prm_trap_auth_header_777",
    }
    res = client.get("/api/v1/cybertrap/decoys/batches", headers=headers)
    assert res.status_code == 200

    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(
            CyberTrapEvent.is_honeytoken_triggered.is_(True)
        ).first()
        assert event is not None
        assert event.honeytoken_id in ["prm_trap_header_custom_555", "prm_trap_auth_header_777"]
    finally:
        db.close()


def test_evasion_url_encoded_token_in_query(challenger_db):
    """Verify URL-encoded honeytoken in query parameters is decoded by Starlette."""
    client, SessionLocal = challenger_db

    raw_token = "prm_trap_saff_9941a8e2b"
    # %5F is underscore
    encoded_token = "prm%5Ftrap%5Fsaff%5F9941a8e2b"

    res = client.get(f"/api/v1/cybertrap/decoys/tokens/validate?token={encoded_token}")
    assert res.status_code == 200
    data = res.json()
    assert data["token_type"] == "INTERNAL_CANARY"

    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(
            CyberTrapEvent.decoy_id == "DECOY-TOKEN-VALIDATE"
        ).first()
        assert event is not None
        assert event.is_honeytoken_triggered is True
        assert event.honeytoken_id == raw_token
    finally:
        db.close()


def test_evasion_url_encoded_token_in_json_payload_evades_detection():
    """REMEDIATED: Honeytoken URL-encoded inside a JSON payload is decoded and detected."""
    token_url_encoded = "prm%5Ftrap%5Fsaff_payload_urlenc"
    res = HoneypotService.extract_honeytokens({"stolen_canary": token_url_encoded})
    assert "prm_trap_saff_payload_urlenc" in res


def test_evasion_url_encoded_token_in_headers_evades_detection(challenger_db):
    """REMEDIATED: Honeytoken URL-encoded in custom header is unquoted and detected."""
    client, SessionLocal = challenger_db

    headers = {"X-Canary-Probe": "prm%5Ftrap%5Fheader_evaded"}
    res = client.get("/api/v1/cybertrap/decoys/batches", headers=headers)
    assert res.status_code == 200

    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(
            CyberTrapEvent.decoy_id == "DECOY-BATCHES-CATALOG"
        ).order_by(CyberTrapEvent.timestamp.desc()).first()
        assert event is not None
        assert event.is_honeytoken_triggered is True
        assert event.honeytoken_id == "prm_trap_header_evaded"
    finally:
        db.close()


# =========================================================================
# 3. PROXY IP EXTRACTION & SPOOFING ROBUSTNESS
# =========================================================================

def test_proxy_ip_empty_or_whitespace_xff(challenger_db):
    """Verify empty or whitespace-only X-Forwarded-For handling."""
    client, SessionLocal = challenger_db

    # Test 1: Empty string (falls back to client host)
    res = client.get("/api/v1/cybertrap/decoys/batches", headers={"X-Forwarded-For": ""})
    assert res.status_code == 200

    # Test 2: Whitespace only -> results in client_ip = ""
    res = client.get("/api/v1/cybertrap/decoys/batches", headers={"X-Forwarded-For": "   "})
    assert res.status_code == 200

    db = SessionLocal()
    try:
        events = db.query(CyberTrapEvent).all()
        assert len(events) >= 2
    finally:
        db.close()


def test_proxy_ip_sqli_in_xff(challenger_db):
    """Verify SQL injection payloads in X-Forwarded-For are safely parameterized."""
    client, SessionLocal = challenger_db

    sqli_xff = "' OR 1=1; DROP TABLE cybertrap_events; --"
    res = client.get("/api/v1/cybertrap/decoys/batches", headers={"X-Forwarded-For": sqli_xff})
    assert res.status_code == 200

    db = SessionLocal()
    try:
        # Table was not dropped; query succeeds
        assert db.query(CyberTrapEvent).count() >= 1
    finally:
        db.close()


def test_proxy_ip_oversized_xff_vulnerability_on_postgres():
    """FINDING: Oversized XFF string (>45 chars) crashes PostgreSQL with StringDataRightTruncation."""
    from backend.app.core.database import SessionLocal, Base, engine
    import datetime

    # Only test against PostgreSQL engine if connected
    if engine.dialect.name == "postgresql":
        db = SessionLocal()
        try:
            oversized_event = CyberTrapEvent(
                id="test-oversized-check",
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                decoy_id="test",
                decoy_type="test",
                request_method="GET",
                request_path="/",
                source_ip="192.168.1.1" + "A" * 100,
            )
            db.add(oversized_event)
            with pytest.raises(Exception) as excinfo:
                db.commit()
            assert "value too long for type character varying(45)" in str(excinfo.value)
        finally:
            db.close()


def test_proxy_ip_ipv6_with_port(challenger_db):
    """Verify standard IPv6 address extraction."""
    client, SessionLocal = challenger_db

    ipv6_addr = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
    res = client.get("/api/v1/cybertrap/decoys/batches", headers={"X-Forwarded-For": f"{ipv6_addr}, 10.0.0.1"})
    assert res.status_code == 200

    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(CyberTrapEvent.source_ip == ipv6_addr).first()
        assert event is not None
        assert event.source_ip == ipv6_addr
    finally:
        db.close()


def test_proxy_ip_x_real_ip_precedence(challenger_db):
    """Verify X-Real-IP is used as fallback when X-Forwarded-For is missing."""
    client, SessionLocal = challenger_db

    real_ip = "198.51.100.99"
    res = client.get("/api/v1/cybertrap/decoys/batches", headers={"X-Real-IP": real_ip})
    assert res.status_code == 200

    db = SessionLocal()
    try:
        event = db.query(CyberTrapEvent).filter(CyberTrapEvent.source_ip == real_ip).first()
        assert event is not None
        assert event.source_ip == real_ip
    finally:
        db.close()
