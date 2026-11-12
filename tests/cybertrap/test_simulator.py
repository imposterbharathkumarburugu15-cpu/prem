"""Automated Test Suite for CyberTrap Attacker Simulator CLI & Testing Engine.

Verifies:
1. Strict Safety Guard: Rejection of external domains, public IPs, and non-local targets.
2. Unit & Integration tests for all 6 scenarios (recon, credential_stuffing, honey_batch, sqli, dos_burst, all).
3. Performance Metrics module (mean latency, min/max, percentiles, event capture rate, canary detection).
4. Forensic event verification in database (CyberTrapEvent logging and metadata).
5. Standalone CLI execution via subprocess.
6. Strict Agricultural Isolation Guarantee: Verification that genuine farmers, batches, and trust scores
   remain 100% unaltered during aggressive attack simulations.
"""

import json
import os
import subprocess
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.core.database import Base, get_db
from backend.app.models.cybertrap import CyberTrapEvent, CyberTrapDecoyBatch
from backend.app.models.farmer import Farmer
from backend.app.models.supply_chain import Batch
from backend.app.models.trust import ActorTrust

from scripts.cybertrap_simulator import (
    CyberTrapSimulator,
    PerformanceMetrics,
    SafetyCheckError,
    SimulatorClient,
    SimulatorResponse,
    validate_target_url,
)


@pytest.fixture(scope="function")
def simulator_test_env(tmp_path):
    """Create isolated SQLite database with pre-seeded genuine agricultural data."""
    test_db_path = str(tmp_path / "test_simulator_db.db")
    test_engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    # Pre-seed real production data to guarantee strict isolation
    seed_db = TestingSessionLocal()
    try:
        real_farmer = Farmer(
            id="farmer-genuine-sim-001",
            full_name="Anil Kumar",
            phone_number="+919876543299",
            language_pref="hi",
        )
        real_batch = Batch(
            id="batch-genuine-sim-001",
            batch_code="BATCH-GENUINE-SOY-001",
            crop_type="Soybean",
            initial_quantity=5000.0,
            current_quantity=5000.0,
            unit="kg",
            stage="FARM_HARVESTED",
            status="ACTIVE",
        )
        real_trust = ActorTrust(
            actor_id="farmer-genuine-sim-001",
            actor_type="FARMER",
            current_trust=0.98,
            baseline_trust=0.98,
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
    test_client = TestClient(app)

    yield test_client, TestingSessionLocal

    app.dependency_overrides.clear()


# =========================================================================
# TIER 1: SAFETY GUARD UNIT TESTS
# =========================================================================

def test_safety_guard_rejects_external_domains():
    """Verify simulator immediately rejects external domains and hostnames."""
    external_targets = [
        "http://attacker.com",
        "https://evil-site.org:8080",
        "http://praman-cloud.internal.aws:10000",
        "http://subdomain.google.com",
        "http://phishing-portal.xyz/api",
    ]
    for target in external_targets:
        with pytest.raises(SafetyCheckError) as exc_info:
            validate_target_url(target)
        assert "Safety Violation" in str(exc_info.value)
        assert "Rejected external target" in str(exc_info.value)


def test_safety_guard_rejects_external_ips():
    """Verify simulator immediately rejects public or non-loopback IP addresses."""
    external_ips = [
        "http://8.8.8.8:8080",
        "http://192.168.1.105:10000",
        "http://10.0.0.1:8000",
        "http://172.16.20.1",
        "http://1.1.1.1",
    ]
    for target in external_ips:
        with pytest.raises(SafetyCheckError) as exc_info:
            validate_target_url(target)
        assert "Safety Violation" in str(exc_info.value)
        assert "Rejected external target" in str(exc_info.value)


def test_safety_guard_accepts_valid_local_targets():
    """Verify simulator accepts authorized local test targets."""
    valid_targets = [
        ("http://127.0.0.1:10000", "http://127.0.0.1:10000"),
        ("http://localhost:8000/", "http://localhost:8000"),
        ("http://[::1]:10000", "http://[::1]:10000"),
        ("http://testserver", "http://testserver"),
        ("127.0.0.1:10000", "http://127.0.0.1:10000"),
        ("http://0.0.0.0:10000", "http://0.0.0.0:10000"),
    ]
    for raw_target, expected in valid_targets:
        validated = validate_target_url(raw_target)
        assert validated == expected


def test_safety_guard_rejects_empty_or_malformed():
    """Verify simulator rejects empty or non-string inputs."""
    with pytest.raises(SafetyCheckError):
        validate_target_url("")
    with pytest.raises(SafetyCheckError):
        validate_target_url(None)


def test_performance_metrics_calculator_unit():
    """Verify unit-level statistics calculation in PerformanceMetrics."""
    responses = [
        SimulatorResponse(status_code=200, text="ok", latency_ms=10.0, endpoint="/api/1"),
        SimulatorResponse(status_code=200, text="ok", latency_ms=20.0, endpoint="/api/2"),
        SimulatorResponse(status_code=401, text="unauthorized", latency_ms=30.0, endpoint="/api/auth"),
        SimulatorResponse(
            status_code=200,
            text='{"valid": true, "token_type": "INTERNAL_CANARY"}',
            json_data={"valid": True, "token_type": "INTERNAL_CANARY"},
            latency_ms=15.0,
            endpoint="/api/v1/cybertrap/decoys/tokens/validate",
        ),
    ]

    metrics = PerformanceMetrics.calculate(
        responses=responses,
        canary_tokens_tested=["prm_trap_test_1"],
        db_events_count=4,
    )

    assert metrics["total_requests"] == 4
    assert metrics["successful_requests"] == 4
    assert metrics["failed_requests"] == 0
    assert metrics["status_codes"] == {200: 3, 401: 1}
    assert metrics["mean_latency_ms"] == 18.75
    assert metrics["min_latency_ms"] == 10.0
    assert metrics["max_latency_ms"] == 30.0
    assert metrics["canary_detection_accuracy"] == 1.0
    assert metrics["event_capture_rate"] == 1.0


# =========================================================================
# TIER 2: SCENARIOS & FORENSIC EVENT VERIFICATION
# =========================================================================

def test_scenario_recon_execution_and_forensics(simulator_test_env):
    """Verify Recon scenario: probes secret endpoints and records forensic events."""
    test_client, SessionLocal = simulator_test_env
    db = SessionLocal()

    simulator = CyberTrapSimulator(
        target_url="http://127.0.0.1:10000",
        intensity="low",
        client_mode="testclient",
        test_client=test_client,
        db_session=db,
    )

    result = simulator.run_recon(intensity="low")

    assert result.scenario_name == "recon"
    assert result.total_requests == 4
    assert result.successful_requests == 4
    assert result.failed_requests == 0
    assert result.status_codes == {200: 4}
    assert result.mean_latency_ms > 0
    assert len(result.canary_tokens_triggered) >= 3

    # Check database forensic events
    events = db.query(CyberTrapEvent).all()
    assert len(events) == 4
    decoy_ids = [e.decoy_id for e in events]
    assert "PROBE-ADMIN-EXPORT-DB" in decoy_ids
    assert "PROBE-AUTH-INTERNAL-TOKENS" in decoy_ids
    assert "PROBE-EVIDENCE-CAS-DUMP" in decoy_ids
    assert "DECOY-ADMIN-EXPORT" in decoy_ids

    # Confirm honeytokens flagged
    assert any(e.is_honeytoken_triggered for e in events)
    db.close()


def test_scenario_credential_stuffing_execution_and_forensics(simulator_test_env):
    """Verify Credential Stuffing scenario: executes brute-force login attacks."""
    test_client, SessionLocal = simulator_test_env
    db = SessionLocal()

    simulator = CyberTrapSimulator(
        target_url="http://127.0.0.1:10000",
        intensity="low",
        client_mode="testclient",
        test_client=test_client,
        db_session=db,
    )

    result = simulator.run_credential_stuffing(intensity="low")

    assert result.scenario_name == "credential_stuffing"
    assert result.total_requests == 4
    assert result.status_codes == {401: 4}
    assert result.mean_latency_ms > 0

    # Check database forensic events
    events = db.query(CyberTrapEvent).filter(CyberTrapEvent.decoy_id == "DECOY-AUTH-LOGIN").all()
    assert len(events) == 4
    for ev in events:
        assert ev.decoy_type == "API_ENDPOINT"
        assert ev.request_method == "POST"
        assert "Hydra" in (ev.user_agent or "")
        assert ev.payload_json is not None
        assert "password" in ev.payload_json

    db.close()


def test_scenario_honey_batch_execution_and_forensics(simulator_test_env):
    """Verify Honey Batch scenario: catalog -> batch exfiltration -> canary validation."""
    test_client, SessionLocal = simulator_test_env
    db = SessionLocal()

    simulator = CyberTrapSimulator(
        target_url="http://127.0.0.1:10000",
        intensity="low",
        client_mode="testclient",
        test_client=test_client,
        db_session=db,
    )

    result = simulator.run_honey_batch(intensity="low")

    assert result.scenario_name == "honey_batch"
    assert result.total_requests == 3
    assert result.status_codes == {200: 3}
    assert len(result.canary_tokens_triggered) >= 1
    assert any(tok.startswith("prm_trap_saff_") for tok in result.canary_tokens_triggered)
    assert result.canary_detection_accuracy == 1.0

    # Check database forensic events
    events = db.query(CyberTrapEvent).all()
    assert len(events) == 3
    decoy_ids = [e.decoy_id for e in events]
    assert "DECOY-BATCHES-CATALOG" in decoy_ids
    assert "DECOY-BATCH-BATCH-HONEY-SAFFRON-001" in decoy_ids
    assert "DECOY-TOKEN-VALIDATE" in decoy_ids

    # Confirm canary validation event has honeytoken flag True
    token_event = next(e for e in events if e.decoy_id == "DECOY-TOKEN-VALIDATE")
    assert token_event.is_honeytoken_triggered is True
    assert token_event.honeytoken_id.startswith("prm_trap_saff_")

    db.close()


def test_scenario_sqli_execution_and_forensics(simulator_test_env):
    """Verify SQLi scenario: injects SQL injection payloads across decoys without crashing."""
    test_client, SessionLocal = simulator_test_env
    db = SessionLocal()

    simulator = CyberTrapSimulator(
        target_url="http://127.0.0.1:10000",
        intensity="low",
        client_mode="testclient",
        test_client=test_client,
        db_session=db,
    )

    result = simulator.run_sqli(intensity="low")

    assert result.scenario_name == "sqli"
    assert result.total_requests == 4
    # All requests should return valid client errors (401, 404, or 200) - NEVER 500
    assert result.failed_requests == 0
    assert all(code in (200, 401, 404) for code in result.status_codes.keys())

    # Check database forensic events: SQLi strings preserved in payloads
    events = db.query(CyberTrapEvent).all()
    assert len(events) == 4
    assert any("OR" in (e.payload_json or "") or "UNION" in (e.payload_json or "") for e in events)

    db.close()


def test_scenario_dos_burst_execution_and_forensics(simulator_test_env):
    """Verify DoS Burst scenario: high-velocity request burst against decoys."""
    test_client, SessionLocal = simulator_test_env
    db = SessionLocal()

    simulator = CyberTrapSimulator(
        target_url="http://127.0.0.1:10000",
        intensity="low",
        client_mode="testclient",
        test_client=test_client,
        db_session=db,
    )

    result = simulator.run_dos_burst(intensity="low")

    assert result.scenario_name == "dos_burst"
    assert result.total_requests == 20
    assert result.failed_requests == 0
    assert result.mean_latency_ms > 0
    assert result.min_latency_ms <= result.max_latency_ms

    # Check throughput details
    assert "requests_per_second" in result.details[0]
    assert result.details[0]["burst_total_requests"] == 20

    # Check database forensic events
    events = db.query(CyberTrapEvent).all()
    assert len(events) == 20

    db.close()


def test_scenario_all_comprehensive_report(simulator_test_env):
    """Verify Scenario 'all': runs all 5 scenarios sequentially and builds complete JSON report."""
    test_client, SessionLocal = simulator_test_env
    db = SessionLocal()

    simulator = CyberTrapSimulator(
        target_url="http://127.0.0.1:10000",
        intensity="low",
        client_mode="testclient",
        test_client=test_client,
        db_session=db,
    )

    report = simulator.run_scenario("all")

    assert report["scenario"] == "all"
    assert report["intensity"] == "low"
    assert report["client_mode"] == "testclient"

    summary = report["summary"]
    assert summary["total_requests"] == 35  # 4 + 4 + 3 + 4 + 20
    assert summary["successful_requests"] == 35
    assert summary["failed_requests"] == 0
    assert summary["mean_latency_ms"] > 0
    assert len(summary["canary_tokens_triggered"]) >= 5
    assert summary["forensic_events_captured"] == 35
    assert summary["event_capture_rate"] == 1.0

    # Verify all scenario sections are populated
    scenarios = report["scenarios"]
    assert "recon" in scenarios
    assert "credential_stuffing" in scenarios
    assert "honey_batch" in scenarios
    assert "sqli" in scenarios
    assert "dos_burst" in scenarios

    db.close()


# =========================================================================
# TIER 3: INTENSITY SCALING & ERROR HANDLING
# =========================================================================

def test_simulator_intensity_scaling(simulator_test_env):
    """Verify intensity levels scale request volumes deterministically."""
    test_client, SessionLocal = simulator_test_env
    db = SessionLocal()

    simulator = CyberTrapSimulator(
        target_url="http://127.0.0.1:10000",
        intensity="medium",
        client_mode="testclient",
        test_client=test_client,
        db_session=db,
    )

    recon_res = simulator.run_recon(intensity="medium")
    assert recon_res.total_requests == 12  # 3 cycles * 4 endpoints

    stuff_res = simulator.run_credential_stuffing(intensity="medium")
    assert stuff_res.total_requests == 10

    db.close()


def test_simulator_invalid_scenario_rejection(simulator_test_env):
    """Verify simulator rejects unrecognized attack scenarios."""
    test_client, SessionLocal = simulator_test_env
    simulator = CyberTrapSimulator(
        target_url="http://127.0.0.1:10000",
        client_mode="testclient",
        test_client=test_client,
    )

    with pytest.raises(ValueError) as exc:
        simulator.run_scenario("remote_code_execution")
    assert "Invalid scenario" in str(exc.value)


# =========================================================================
# TIER 4: CLI SUBPROCESS & AGRICULTURAL ISOLATION
# =========================================================================

def test_cli_standalone_execution_subprocess():
    """Verify standalone CLI execution runs with exit code 0 and valid JSON report."""
    cmd = [
        sys.executable,
        "scripts/cybertrap_simulator.py",
        "--scenario", "recon",
        "--intensity", "low",
        "--json-output",
        "--quiet",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, f"CLI exited with error: {proc.stderr}"

    # Verify output is valid JSON
    # Strip any possible warning lines before parsing
    raw_out = proc.stdout.strip()
    json_start = raw_out.find("{")
    assert json_start != -1, f"No JSON start found in output: {raw_out}"
    parsed_report = json.loads(raw_out[json_start:])

    assert parsed_report["scenario"] == "recon"
    assert parsed_report["summary"]["total_requests"] == 4
    assert parsed_report["summary"]["successful_requests"] == 4
    assert len(parsed_report["summary"]["canary_tokens_triggered"]) >= 3


def test_cli_safety_violation_subprocess():
    """Verify standalone CLI immediately rejects external target with exit code 1."""
    cmd = [
        sys.executable,
        "scripts/cybertrap_simulator.py",
        "--target-url", "http://external-hacker-site.org",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    assert proc.returncode == 1
    assert "Safety Violation" in proc.stderr or "Safety Violation" in proc.stdout


def test_simulator_strict_agricultural_isolation(simulator_test_env):
    """Verify aggressive attack simulation NEVER touches genuine agricultural tables.
    
    Ensures zero false positives or score degradation against legitimate farmers and batches.
    """
    test_client, SessionLocal = simulator_test_env
    db = SessionLocal()

    simulator = CyberTrapSimulator(
        target_url="http://127.0.0.1:10000",
        intensity="low",
        client_mode="testclient",
        test_client=test_client,
        db_session=db,
    )

    # Execute full attack suite
    simulator.run_scenario("all")

    # 1. Verify Genuine Farmer is intact
    farmer = db.query(Farmer).filter(Farmer.id == "farmer-genuine-sim-001").first()
    assert farmer is not None
    assert farmer.full_name == "Anil Kumar"
    assert farmer.phone_number == "+919876543299"

    # 2. Verify Genuine Batch is intact
    batch = db.query(Batch).filter(Batch.id == "batch-genuine-sim-001").first()
    assert batch is not None
    assert batch.crop_type == "Soybean"
    assert batch.initial_quantity == 5000.0
    assert batch.status == "ACTIVE"

    # 3. Verify Genuine Trust Score is 100% UNTOUCHED
    trust = db.query(ActorTrust).filter(ActorTrust.actor_id == "farmer-genuine-sim-001").first()
    assert trust is not None
    assert trust.current_trust == 0.98

    # 4. Verify table isolation
    assert db.query(Farmer).count() == 1
    assert db.query(Batch).count() == 1
    assert db.query(CyberTrapEvent).count() == 35

    db.close()
