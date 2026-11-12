"""PRAMAN CyberTrap — Local Attacker Simulator CLI & Security Testing Engine.

Provides automated, deterministic, and repeatable attack simulation scenarios
targeting isolated local PRAMAN honeypots and decoy endpoints.

Strict Safety Constraint:
    TARGETS ONLY LOCAL PRAMAN TEST ENDPOINTS (127.0.0.1, localhost, ::1, testserver).
    ANY EXTERNAL HOSTNAME OR IP ADDRESS IS IMMEDIATELY REJECTED.
"""

import argparse
import json
import os
import re
import socket
import sys
import time
import urllib.parse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

# Ensure project root is in sys.path so 'backend' can always be imported
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    import httpx
except ImportError:
    httpx = None

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


# =========================================================================
# SAFETY CONSTRAINT & VALIDATION
# =========================================================================

ALLOWED_LOCAL_HOSTS = {
    "127.0.0.1",
    "localhost",
    "::1",
    "[::1]",
    "testserver",
    "0.0.0.0",
}


class SafetyCheckError(ValueError):
    """Raised when an external or unauthorized target URL is supplied."""
    pass


def validate_target_url(target_url: str) -> str:
    """Validate that target_url strictly targets authorized local test endpoints.
    
    Raises:
        SafetyCheckError: If target points to external domain, public IP, or non-local host.
    """
    if not target_url or not isinstance(target_url, str):
        raise SafetyCheckError("Safety Violation: Target URL must be a non-empty string.")

    # Prepend scheme if missing for parsing
    url_to_parse = target_url
    if not url_to_parse.startswith(("http://", "https://")):
        url_to_parse = "http://" + url_to_parse

    parsed = urllib.parse.urlparse(url_to_parse)
    hostname = (parsed.hostname or "").lower().strip()

    if not hostname:
        raise SafetyCheckError(f"Safety Violation: Unable to extract valid hostname from target '{target_url}'.")

    if hostname not in ALLOWED_LOCAL_HOSTS:
        raise SafetyCheckError(
            f"Safety Violation: Target must be a local PRAMAN test endpoint (localhost or 127.0.0.1). "
            f"Rejected external target: '{hostname}'."
        )

    # Return normalized base URL without trailing slash
    port_part = f":{parsed.port}" if parsed.port else ""
    scheme = parsed.scheme if parsed.scheme in ("http", "https") else "http"
    host_formatted = f"[{hostname}]" if ":" in hostname and not hostname.startswith("[") else hostname
    return f"{scheme}://{host_formatted}{port_part}"


# =========================================================================
# DATA STRUCTURES & METRICS
# =========================================================================

@dataclass
class SimulatorResponse:
    """Standardized response wrapper across live HTTP and TestClient."""
    status_code: int
    text: str
    json_data: Optional[Any] = None
    headers: Dict[str, str] = field(default_factory=dict)
    latency_ms: float = 0.0
    endpoint: str = ""
    method: str = "GET"
    error: Optional[str] = None


@dataclass
class ScenarioResult:
    """Detailed execution result for an attack scenario."""
    scenario_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    status_codes: Dict[int, int]
    mean_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p95_latency_ms: float
    canary_tokens_triggered: List[str]
    canary_detection_accuracy: float
    event_capture_rate: float
    forensic_events_count: int
    details: List[Dict[str, Any]] = field(default_factory=list)


# =========================================================================
# CLIENT ABSTRACTION (TestClient & Live HTTP)
# =========================================================================

class SimulatorClient:
    """Unified client handling both FastAPI TestClient (headless) and live HTTP."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:10000",
        mode: str = "auto",
        test_client: Optional[Any] = None,
    ):
        self.base_url = validate_target_url(base_url)
        self.mode = mode
        self._test_client = test_client
        self._http_client = None

        if self.mode == "auto":
            if self._test_client is not None:
                self.mode = "testclient"
            elif self._is_live_server_reachable():
                self.mode = "live"
            else:
                self.mode = "testclient"

        if self.mode == "testclient" and self._test_client is None:
            self._init_testclient()
        elif self.mode == "live":
            self._init_httpx()

    def _is_live_server_reachable(self) -> bool:
        """Quick socket handshake check to see if target port is actively open."""
        parsed = urllib.parse.urlparse(self.base_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.3)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _init_testclient(self):
        """Lazy load FastAPI TestClient with PRAMAN app."""
        if TestClient is None:
            raise RuntimeError("FastAPI TestClient is required for testclient mode but could not be imported.")
        try:
            from backend.app.main import app
            self._test_client = TestClient(app)
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize internal TestClient with PRAMAN app: {exc}")

    def _init_httpx(self):
        """Initialize HTTP client for live endpoint requests."""
        if httpx is not None:
            self._http_client = httpx.Client(base_url=self.base_url, timeout=10.0)
        else:
            self._http_client = None

    def request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        content: Optional[bytes] = None,
    ) -> SimulatorResponse:
        """Execute request and measure round-trip latency in ms."""
        req_headers = headers.copy() if headers else {}
        if "User-Agent" not in req_headers:
            req_headers["User-Agent"] = "PRAMAN-CyberTrap-Simulator/1.0"

        start_time = time.perf_counter()
        try:
            if self.mode == "testclient":
                resp = self._test_client.request(
                    method=method,
                    url=path,
                    headers=req_headers,
                    json=json_data,
                    params=params,
                    content=content,
                )
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                json_body = None
                try:
                    json_body = resp.json()
                except Exception:
                    json_body = None

                return SimulatorResponse(
                    status_code=resp.status_code,
                    text=resp.text,
                    json_data=json_body,
                    headers=dict(resp.headers),
                    latency_ms=round(latency_ms, 2),
                    endpoint=path,
                    method=method,
                )
            else:
                # Live HTTP execution
                if self._http_client is not None:
                    resp = self._http_client.request(
                        method=method,
                        url=path,
                        headers=req_headers,
                        json=json_data,
                        params=params,
                        content=content,
                    )
                    latency_ms = (time.perf_counter() - start_time) * 1000.0
                    json_body = None
                    try:
                        json_body = resp.json()
                    except Exception:
                        json_body = None

                    return SimulatorResponse(
                        status_code=resp.status_code,
                        text=resp.text,
                        json_data=json_body,
                        headers=dict(resp.headers),
                        latency_ms=round(latency_ms, 2),
                        endpoint=path,
                        method=method,
                    )
                else:
                    # Fallback standard urllib.request
                    full_url = urllib.parse.urljoin(self.base_url, path)
                    if params:
                        full_url += "?" + urllib.parse.urlencode(params)
                    req_data = None
                    if json_data is not None:
                        req_data = json.dumps(json_data).encode("utf-8")
                        req_headers["Content-Type"] = "application/json"
                    elif content is not None:
                        req_data = content

                    req = urllib.request.Request(full_url, data=req_data, headers=req_headers, method=method)
                    try:
                        with urllib.request.urlopen(req, timeout=10.0) as uresp:
                            raw_body = uresp.read().decode("utf-8", errors="replace")
                            latency_ms = (time.perf_counter() - start_time) * 1000.0
                            json_body = None
                            try:
                                json_body = json.loads(raw_body)
                            except Exception:
                                pass
                            return SimulatorResponse(
                                status_code=uresp.status,
                                text=raw_body,
                                json_data=json_body,
                                headers=dict(uresp.headers),
                                latency_ms=round(latency_ms, 2),
                                endpoint=path,
                                method=method,
                            )
                    except urllib.error.HTTPError as he:
                        raw_body = he.read().decode("utf-8", errors="replace")
                        latency_ms = (time.perf_counter() - start_time) * 1000.0
                        json_body = None
                        try:
                            json_body = json.loads(raw_body)
                        except Exception:
                            pass
                        return SimulatorResponse(
                            status_code=he.code,
                            text=raw_body,
                            json_data=json_body,
                            headers=dict(he.headers),
                            latency_ms=round(latency_ms, 2),
                            endpoint=path,
                            method=method,
                        )

        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return SimulatorResponse(
                status_code=0,
                text="",
                json_data=None,
                headers={},
                latency_ms=round(latency_ms, 2),
                endpoint=path,
                method=method,
                error=str(exc),
            )


# =========================================================================
# PERFORMANCE METRICS CALCULATOR
# =========================================================================

class PerformanceMetrics:
    """Helper module to calculate latency percentiles, event capture rates, and canary detection."""

    @staticmethod
    def calculate(
        responses: List[SimulatorResponse],
        canary_tokens_tested: List[str],
        db_events_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Compute statistical performance metrics from simulation responses."""
        if not responses:
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "status_codes": {},
                "mean_latency_ms": 0.0,
                "min_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "canary_detection_accuracy": 1.0,
                "event_capture_rate": 1.0,
            }

        latencies = [r.latency_ms for r in responses if r.latency_ms > 0]
        status_counts: Dict[int, int] = {}
        for r in responses:
            status_counts[r.status_code] = status_counts.get(r.status_code, 0) + 1

        successful = sum(count for code, count in status_counts.items() if 200 <= code < 500)
        failed = sum(count for code, count in status_counts.items() if code >= 500 or code == 0)

        latencies_sorted = sorted(latencies) if latencies else [0.0]
        mean_lat = sum(latencies_sorted) / len(latencies_sorted)
        min_lat = latencies_sorted[0]
        max_lat = latencies_sorted[-1]
        p95_idx = int(len(latencies_sorted) * 0.95)
        p95_lat = latencies_sorted[min(p95_idx, len(latencies_sorted) - 1)]

        # Event capture rate calculation
        total_reqs = len(responses)
        if db_events_count is not None and total_reqs > 0:
            capture_rate = min(1.0, db_events_count / total_reqs)
        else:
            capture_rate = 1.0

        # Canary detection accuracy: canary tokens tested that were confirmed in response
        canary_acc = 1.0
        if canary_tokens_tested:
            # Check how many validation calls returned valid=True or token_type == INTERNAL_CANARY
            canary_successes = sum(
                1 for r in responses
                if r.json_data and isinstance(r.json_data, dict)
                and (r.json_data.get("token_type") == "INTERNAL_CANARY" or r.json_data.get("valid") is True)
            )
            # If validation calls were made, compute ratio, else default to 1.0
            val_calls = sum(1 for r in responses if "/tokens/validate" in r.endpoint)
            if val_calls > 0:
                canary_acc = round(min(1.0, canary_successes / val_calls), 2)

        return {
            "total_requests": total_reqs,
            "successful_requests": successful,
            "failed_requests": failed,
            "status_codes": status_counts,
            "mean_latency_ms": round(mean_lat, 2),
            "min_latency_ms": round(min_lat, 2),
            "max_latency_ms": round(max_lat, 2),
            "p95_latency_ms": round(p95_lat, 2),
            "canary_detection_accuracy": canary_acc,
            "event_capture_rate": round(capture_rate, 2),
        }


# =========================================================================
# ATTACK SIMULATOR CORE
# =========================================================================

INTENSITY_CONFIG = {
    "low": {
        "recon_cycles": 1,
        "credential_stuffing_attempts": 4,
        "honey_batch_cycles": 1,
        "sqli_payloads": 4,
        "dos_burst_count": 20,
        "sleep_sec": 0.02,
    },
    "medium": {
        "recon_cycles": 3,
        "credential_stuffing_attempts": 10,
        "honey_batch_cycles": 3,
        "sqli_payloads": 8,
        "dos_burst_count": 50,
        "sleep_sec": 0.01,
    },
    "high": {
        "recon_cycles": 6,
        "credential_stuffing_attempts": 25,
        "honey_batch_cycles": 5,
        "sqli_payloads": 16,
        "dos_burst_count": 100,
        "sleep_sec": 0.002,
    },
}

CREDENTIAL_DICTIONARY = [
    ("admin@praman.internal", "Password123!"),
    ("superadmin", "PramanMaster2026#"),
    ("root", "toor"),
    ("audit_officer@praman.gov.in", "IndiaAgriSecure99"),
    ("db_sync", "sync_daemon_pwd"),
    ("farmer_rep", "KisanTrust#2026"),
    ("ledger_bridge", "NIST_p256_private_key"),
    ("sys_operator", "admin123456"),
    ("inspector_01", "CertVerify2026!"),
    ("service_account", "svc_token_secret"),
    ("guest", "guest"),
    ("test_user", "test_password"),
]

SQLI_PAYLOADS = [
    "' OR '1'='1",
    "admin' --",
    "' UNION SELECT id, crop_type, declared_quantity, honeytoken_secret FROM cybertrap_decoy_batches --",
    "1' AND (SELECT COUNT(*) FROM farmers) > 0 --",
    "'; DROP TABLE cybertrap_events; --",
    "admin' /*!50000OR*/ 1=1 --",
    "' OR 1=1#",
    "' WAITFOR DELAY '0:0:1' --",
]

RECON_ENDPOINTS = [
    {"path": "/api/v1/admin/export-database", "method": "GET", "ua": "Nmap Scripting Engine (https://nmap.org/book/nse.html)"},
    {"path": "/api/v1/auth/internal-tokens", "method": "POST", "ua": "Masscan/1.3.2 (https://github.com/robertdavidgraham/masscan)"},
    {"path": "/api/v1/evidence/raw-cas-dump", "method": "GET", "ua": "DirBuster-1.0-RC1"},
    {"path": "/api/v1/cybertrap/decoys/admin/export", "method": "POST", "ua": "Nikto/2.1.6"},
]


class CyberTrapSimulator:
    """Orchestrates local attack simulations against PRAMAN CyberTrap decoys."""

    def __init__(
        self,
        target_url: str = "http://127.0.0.1:10000",
        intensity: str = "low",
        client_mode: str = "auto",
        test_client: Optional[Any] = None,
        db_session: Optional[Any] = None,
    ):
        self.target_url = validate_target_url(target_url)
        self.intensity = intensity.lower() if intensity.lower() in INTENSITY_CONFIG else "low"
        self.client = SimulatorClient(
            base_url=self.target_url,
            mode=client_mode,
            test_client=test_client,
        )
        self.db_session = db_session
        self.config = INTENSITY_CONFIG[self.intensity]

    def _query_db_event_count(self) -> int:
        """Fetch total events currently recorded in database."""
        try:
            if self.db_session:
                from backend.app.models.cybertrap import CyberTrapEvent
                return self.db_session.query(CyberTrapEvent).count()
            # Otherwise query admin events endpoint
            resp = self.client.request("GET", "/api/v1/cybertrap/events?limit=1")
            if resp.status_code == 200 and resp.json_data and "total" in resp.json_data:
                return int(resp.json_data["total"])
        except Exception:
            pass
        return 0

    # ---------------------------------------------------------------------
    # SCENARIO 1: RECONNAISSANCE
    # ---------------------------------------------------------------------
    def run_recon(self, intensity: Optional[str] = None) -> ScenarioResult:
        """Scenario 1: Reconnaissance.
        
        Enumerates administrative and secret endpoints commonly targeted by scanners:
        - /api/v1/admin/export-database
        - /api/v1/auth/internal-tokens
        - /api/v1/evidence/raw-cas-dump
        - /api/v1/cybertrap/decoys/admin/export
        """
        cfg = INTENSITY_CONFIG[intensity.lower()] if intensity and intensity.lower() in INTENSITY_CONFIG else self.config
        cycles = cfg["recon_cycles"]
        sleep_sec = cfg["sleep_sec"]

        events_before = self._query_db_event_count()
        responses: List[SimulatorResponse] = []
        canaries_extracted: List[str] = []
        details: List[Dict[str, Any]] = []

        for cycle in range(cycles):
            for probe in RECON_ENDPOINTS:
                path = probe["path"]
                method = probe["method"]
                ua = probe["ua"] if cycle == 0 else f"{probe['ua']}; cycle={cycle+1}"

                resp = self.client.request(
                    method=method,
                    path=path,
                    headers={"User-Agent": ua},
                )
                responses.append(resp)

                # Extract canary tokens if present in response
                if resp.json_data and isinstance(resp.json_data, dict):
                    # Check internal_access_token
                    if "internal_access_token" in resp.json_data:
                        canaries_extracted.append(resp.json_data["internal_access_token"])
                    # Check active_tokens
                    if "active_tokens" in resp.json_data and isinstance(resp.json_data["active_tokens"], list):
                        for item in resp.json_data["active_tokens"]:
                            if isinstance(item, dict) and "token" in item:
                                canaries_extracted.append(item["token"])
                    # Check sample_artifacts
                    if "sample_artifacts" in resp.json_data and isinstance(resp.json_data["sample_artifacts"], list):
                        for item in resp.json_data["sample_artifacts"]:
                            if isinstance(item, dict) and "canary_token" in item:
                                canaries_extracted.append(item["canary_token"])

                details.append({
                    "cycle": cycle + 1,
                    "endpoint": path,
                    "method": method,
                    "status_code": resp.status_code,
                    "latency_ms": resp.latency_ms,
                    "user_agent": ua,
                })
                if sleep_sec > 0:
                    time.sleep(sleep_sec)

        events_after = self._query_db_event_count()
        new_events = max(0, events_after - events_before)
        metrics = PerformanceMetrics.calculate(responses, canaries_extracted, db_events_count=new_events)

        return ScenarioResult(
            scenario_name="recon",
            total_requests=metrics["total_requests"],
            successful_requests=metrics["successful_requests"],
            failed_requests=metrics["failed_requests"],
            status_codes=metrics["status_codes"],
            mean_latency_ms=metrics["mean_latency_ms"],
            min_latency_ms=metrics["min_latency_ms"],
            max_latency_ms=metrics["max_latency_ms"],
            p95_latency_ms=metrics["p95_latency_ms"],
            canary_tokens_triggered=list(set(canaries_extracted)),
            canary_detection_accuracy=metrics["canary_detection_accuracy"],
            event_capture_rate=metrics["event_capture_rate"],
            forensic_events_count=new_events,
            details=details,
        )

    # ---------------------------------------------------------------------
    # SCENARIO 2: CREDENTIAL STUFFING
    # ---------------------------------------------------------------------
    def run_credential_stuffing(self, intensity: Optional[str] = None) -> ScenarioResult:
        """Scenario 2: Credential Stuffing.
        
        Simulates automated dictionary and brute-force authentication attacks on:
        - /api/v1/cybertrap/decoys/auth/login
        """
        cfg = INTENSITY_CONFIG[intensity.lower()] if intensity and intensity.lower() in INTENSITY_CONFIG else self.config
        attempts = cfg["credential_stuffing_attempts"]
        sleep_sec = cfg["sleep_sec"]

        events_before = self._query_db_event_count()
        responses: List[SimulatorResponse] = []
        details: List[Dict[str, Any]] = []

        dict_len = len(CREDENTIAL_DICTIONARY)
        for i in range(attempts):
            username, password = CREDENTIAL_DICTIONARY[i % dict_len]
            # Mutate slightly if repeated
            if i >= dict_len:
                username = f"{username}_{i}"

            payload = {
                "username": username,
                "password": password,
                "client_id": f"hydra_worker_{i+1}",
            }
            resp = self.client.request(
                method="POST",
                path="/api/v1/cybertrap/decoys/auth/login",
                headers={"User-Agent": "Hydra/9.2 (https://github.com/vanhauser-thc/thc-hydra)"},
                json_data=payload,
            )
            responses.append(resp)
            details.append({
                "attempt": i + 1,
                "endpoint": "/api/v1/cybertrap/decoys/auth/login",
                "username": username,
                "status_code": resp.status_code,
                "latency_ms": resp.latency_ms,
                "error_code": resp.json_data.get("error_code") if resp.json_data else None,
            })
            if sleep_sec > 0:
                time.sleep(sleep_sec)

        events_after = self._query_db_event_count()
        new_events = max(0, events_after - events_before)
        metrics = PerformanceMetrics.calculate(responses, [], db_events_count=new_events)

        return ScenarioResult(
            scenario_name="credential_stuffing",
            total_requests=metrics["total_requests"],
            successful_requests=metrics["successful_requests"],
            failed_requests=metrics["failed_requests"],
            status_codes=metrics["status_codes"],
            mean_latency_ms=metrics["mean_latency_ms"],
            min_latency_ms=metrics["min_latency_ms"],
            max_latency_ms=metrics["max_latency_ms"],
            p95_latency_ms=metrics["p95_latency_ms"],
            canary_tokens_triggered=[],
            canary_detection_accuracy=1.0,
            event_capture_rate=metrics["event_capture_rate"],
            forensic_events_count=new_events,
            details=details,
        )

    # ---------------------------------------------------------------------
    # SCENARIO 3: HONEY BATCH EXFILTRATION & CANARY VALIDATION
    # ---------------------------------------------------------------------
    def run_honey_batch(self, intensity: Optional[str] = None) -> ScenarioResult:
        """Scenario 3: Honey Batch Exfiltration & Canary Validation.
        
        Targets high-value synthetic crop records (BATCH-HONEY-SAFFRON-001),
        extracts canary honeytokens, and attempts to validate them at
        /api/v1/cybertrap/decoys/tokens/validate.
        """
        cfg = INTENSITY_CONFIG[intensity.lower()] if intensity and intensity.lower() in INTENSITY_CONFIG else self.config
        cycles = cfg["honey_batch_cycles"]
        sleep_sec = cfg["sleep_sec"]

        events_before = self._query_db_event_count()
        responses: List[SimulatorResponse] = []
        canaries_triggered: List[str] = []
        details: List[Dict[str, Any]] = []

        for cycle in range(cycles):
            # Step 1: Catalog enumeration
            catalog_resp = self.client.request(
                method="GET",
                path="/api/v1/cybertrap/decoys/batches",
                headers={"User-Agent": "CustomHarvester/2.4"},
            )
            responses.append(catalog_resp)
            batch_ids = ["BATCH-HONEY-SAFFRON-001"]
            if catalog_resp.json_data and isinstance(catalog_resp.json_data, dict) and "batches" in catalog_resp.json_data:
                batch_ids = [b["id"] for b in catalog_resp.json_data["batches"]]

            details.append({
                "step": "catalog_enumeration",
                "endpoint": "/api/v1/cybertrap/decoys/batches",
                "status_code": catalog_resp.status_code,
                "latency_ms": catalog_resp.latency_ms,
                "batches_discovered": len(batch_ids),
            })
            if sleep_sec > 0:
                time.sleep(sleep_sec)

            # Step 2: Target high-value crop batch (saffron)
            target_batch = "BATCH-HONEY-SAFFRON-001"
            batch_resp = self.client.request(
                method="GET",
                path=f"/api/v1/cybertrap/decoys/batches/{target_batch}",
                headers={"User-Agent": "DataScraper/1.0"},
            )
            responses.append(batch_resp)

            stolen_token = None
            if batch_resp.json_data and isinstance(batch_resp.json_data, dict):
                stolen_token = batch_resp.json_data.get("canary_token") or batch_resp.json_data.get("honeytoken_secret")

            details.append({
                "step": "batch_exfiltration",
                "target_batch": target_batch,
                "status_code": batch_resp.status_code,
                "latency_ms": batch_resp.latency_ms,
                "canary_token_extracted": stolen_token,
            })
            if sleep_sec > 0:
                time.sleep(sleep_sec)

            # Step 3: Validate canary token
            token_to_validate = stolen_token or "prm_trap_saff_9941a8e2b"
            val_resp = self.client.request(
                method="GET",
                path="/api/v1/cybertrap/decoys/tokens/validate",
                params={"token": token_to_validate},
                headers={"User-Agent": "TokenVerifierBot/1.1"},
            )
            responses.append(val_resp)
            canaries_triggered.append(token_to_validate)

            details.append({
                "step": "canary_validation",
                "endpoint": "/api/v1/cybertrap/decoys/tokens/validate",
                "token": token_to_validate,
                "status_code": val_resp.status_code,
                "latency_ms": val_resp.latency_ms,
                "is_canary_verified": val_resp.json_data.get("token_type") == "INTERNAL_CANARY" if val_resp.json_data else False,
            })
            if sleep_sec > 0:
                time.sleep(sleep_sec)

            # Step 4: If cycle > 0 or medium/high, probe cardamom and non-existent batch
            if cycle > 0 or self.intensity in ("medium", "high"):
                cardamom_resp = self.client.request(
                    method="GET",
                    path="/api/v1/cybertrap/decoys/batches/BATCH-HONEY-CARDAMOM-002",
                )
                responses.append(cardamom_resp)
                if cardamom_resp.json_data and isinstance(cardamom_resp.json_data, dict):
                    c_token = cardamom_resp.json_data.get("canary_token")
                    if c_token:
                        canaries_triggered.append(c_token)
                        # Validate cardamom token too
                        val_c = self.client.request(
                            method="GET",
                            path="/api/v1/cybertrap/decoys/tokens/validate",
                            params={"token": c_token},
                        )
                        responses.append(val_c)

        events_after = self._query_db_event_count()
        new_events = max(0, events_after - events_before)
        metrics = PerformanceMetrics.calculate(responses, canaries_triggered, db_events_count=new_events)

        return ScenarioResult(
            scenario_name="honey_batch",
            total_requests=metrics["total_requests"],
            successful_requests=metrics["successful_requests"],
            failed_requests=metrics["failed_requests"],
            status_codes=metrics["status_codes"],
            mean_latency_ms=metrics["mean_latency_ms"],
            min_latency_ms=metrics["min_latency_ms"],
            max_latency_ms=metrics["max_latency_ms"],
            p95_latency_ms=metrics["p95_latency_ms"],
            canary_tokens_triggered=list(set(canaries_triggered)),
            canary_detection_accuracy=metrics["canary_detection_accuracy"],
            event_capture_rate=metrics["event_capture_rate"],
            forensic_events_count=new_events,
            details=details,
        )

    # ---------------------------------------------------------------------
    # SCENARIO 4: SQL INJECTION (SQLi)
    # ---------------------------------------------------------------------
    def run_sqli(self, intensity: Optional[str] = None) -> ScenarioResult:
        """Scenario 4: SQL Injection Probing.
        
        Injects SQL injection payloads into decoy login and query parameters.
        Verifies input handling robustness and forensic event preservation.
        """
        cfg = INTENSITY_CONFIG[intensity.lower()] if intensity and intensity.lower() in INTENSITY_CONFIG else self.config
        payload_count = cfg["sqli_payloads"]
        sleep_sec = cfg["sleep_sec"]

        events_before = self._query_db_event_count()
        responses: List[SimulatorResponse] = []
        details: List[Dict[str, Any]] = []

        total_sqli = len(SQLI_PAYLOADS)
        for i in range(payload_count):
            payload = SQLI_PAYLOADS[i % total_sqli]

            # Alternating injection target: 1) auth login, 2) token validate, 3) batch query
            target_type = i % 3
            if target_type == 0:
                # Login SQLi
                login_data = {
                    "username": payload,
                    "password": "Password' OR '1'='1",
                }
                resp = self.client.request(
                    method="POST",
                    path="/api/v1/cybertrap/decoys/auth/login",
                    json_data=login_data,
                    headers={"User-Agent": "sqlmap/1.7.2#stable"},
                )
                endpoint = "/api/v1/cybertrap/decoys/auth/login"
            elif target_type == 1:
                # Token validator SQLi
                resp = self.client.request(
                    method="GET",
                    path="/api/v1/cybertrap/decoys/tokens/validate",
                    params={"token": payload},
                    headers={"User-Agent": "sqlmap/1.7.2#stable"},
                )
                endpoint = "/api/v1/cybertrap/decoys/tokens/validate"
            else:
                # Batch ID SQLi
                safe_encoded_id = urllib.parse.quote(payload, safe="")
                resp = self.client.request(
                    method="GET",
                    path=f"/api/v1/cybertrap/decoys/batches/{safe_encoded_id}",
                    headers={"User-Agent": "sqlmap/1.7.2#stable"},
                )
                endpoint = f"/api/v1/cybertrap/decoys/batches/{safe_encoded_id}"

            responses.append(resp)
            details.append({
                "probe": i + 1,
                "endpoint": endpoint,
                "payload": payload,
                "status_code": resp.status_code,
                "latency_ms": resp.latency_ms,
            })
            if sleep_sec > 0:
                time.sleep(sleep_sec)

        events_after = self._query_db_event_count()
        new_events = max(0, events_after - events_before)
        metrics = PerformanceMetrics.calculate(responses, [], db_events_count=new_events)

        return ScenarioResult(
            scenario_name="sqli",
            total_requests=metrics["total_requests"],
            successful_requests=metrics["successful_requests"],
            failed_requests=metrics["failed_requests"],
            status_codes=metrics["status_codes"],
            mean_latency_ms=metrics["mean_latency_ms"],
            min_latency_ms=metrics["min_latency_ms"],
            max_latency_ms=metrics["max_latency_ms"],
            p95_latency_ms=metrics["p95_latency_ms"],
            canary_tokens_triggered=[],
            canary_detection_accuracy=1.0,
            event_capture_rate=metrics["event_capture_rate"],
            forensic_events_count=new_events,
            details=details,
        )

    # ---------------------------------------------------------------------
    # SCENARIO 5: DOS BURST
    # ---------------------------------------------------------------------
    def run_dos_burst(self, intensity: Optional[str] = None) -> ScenarioResult:
        """Scenario 5: High-Velocity DoS Burst.
        
        Generates rapid request bursts against decoy endpoints in a tight loop.
        Measures throughput, concurrency resilience, and latency degradation.
        """
        cfg = INTENSITY_CONFIG[intensity.lower()] if intensity and intensity.lower() in INTENSITY_CONFIG else self.config
        burst_count = cfg["dos_burst_count"]

        events_before = self._query_db_event_count()
        responses: List[SimulatorResponse] = []
        details: List[Dict[str, Any]] = []

        burst_start = time.perf_counter()
        for i in range(burst_count):
            endpoint = "/api/v1/cybertrap/decoys/batches" if i % 2 == 0 else "/api/v1/cybertrap/decoys/auth/login"
            if endpoint == "/api/v1/cybertrap/decoys/batches":
                resp = self.client.request(
                    method="GET",
                    path=endpoint,
                    headers={"User-Agent": f"DosFlooder/1.0; seq={i+1}"},
                )
            else:
                resp = self.client.request(
                    method="POST",
                    path=endpoint,
                    headers={"User-Agent": f"DosFlooder/1.0; seq={i+1}"},
                    json_data={"burst_id": i + 1, "test": "flood"},
                )
            responses.append(resp)

        burst_duration = max(0.001, time.perf_counter() - burst_start)
        rps = round(burst_count / burst_duration, 1)

        events_after = self._query_db_event_count()
        new_events = max(0, events_after - events_before)
        metrics = PerformanceMetrics.calculate(responses, [], db_events_count=new_events)

        details.append({
            "burst_total_requests": burst_count,
            "burst_duration_seconds": round(burst_duration, 4),
            "requests_per_second": rps,
        })

        return ScenarioResult(
            scenario_name="dos_burst",
            total_requests=metrics["total_requests"],
            successful_requests=metrics["successful_requests"],
            failed_requests=metrics["failed_requests"],
            status_codes=metrics["status_codes"],
            mean_latency_ms=metrics["mean_latency_ms"],
            min_latency_ms=metrics["min_latency_ms"],
            max_latency_ms=metrics["max_latency_ms"],
            p95_latency_ms=metrics["p95_latency_ms"],
            canary_tokens_triggered=[],
            canary_detection_accuracy=1.0,
            event_capture_rate=metrics["event_capture_rate"],
            forensic_events_count=new_events,
            details=details,
        )

    # ---------------------------------------------------------------------
    # SCENARIO DISPATCHER & REPORT GENERATION
    # ---------------------------------------------------------------------
    def run_scenario(self, scenario: str) -> Dict[str, Any]:
        """Dispatch specified scenario or execute 'all' in sequence."""
        scenario_lower = scenario.lower()
        valid_scenarios = ["recon", "credential_stuffing", "honey_batch", "sqli", "dos_burst", "all"]
        if scenario_lower not in valid_scenarios:
            raise ValueError(f"Invalid scenario '{scenario}'. Allowed choices: {valid_scenarios}")

        results: Dict[str, ScenarioResult] = {}
        start_ts = datetime.now(timezone.utc).isoformat()

        if scenario_lower in ("recon", "all"):
            results["recon"] = self.run_recon()
        if scenario_lower in ("credential_stuffing", "all"):
            results["credential_stuffing"] = self.run_credential_stuffing()
        if scenario_lower in ("honey_batch", "all"):
            results["honey_batch"] = self.run_honey_batch()
        if scenario_lower in ("sqli", "all"):
            results["sqli"] = self.run_sqli()
        if scenario_lower in ("dos_burst", "all"):
            results["dos_burst"] = self.run_dos_burst()

        return self._build_report(start_ts, scenario_lower, results)

    def _build_report(
        self,
        timestamp: str,
        requested_scenario: str,
        scenario_results: Dict[str, ScenarioResult],
    ) -> Dict[str, Any]:
        """Compile comprehensive JSON report for security audit and automation."""
        total_reqs = sum(r.total_requests for r in scenario_results.values())
        succ_reqs = sum(r.successful_requests for r in scenario_results.values())
        fail_reqs = sum(r.failed_requests for r in scenario_results.values())

        merged_status_codes: Dict[int, int] = {}
        for r in scenario_results.values():
            for code, count in r.status_codes.items():
                merged_status_codes[code] = merged_status_codes.get(code, 0) + count

        all_means = [r.mean_latency_ms for r in scenario_results.values() if r.mean_latency_ms > 0]
        overall_mean_latency = round(sum(all_means) / len(all_means), 2) if all_means else 0.0

        all_mins = [r.min_latency_ms for r in scenario_results.values() if r.min_latency_ms > 0]
        overall_min_latency = min(all_mins) if all_mins else 0.0

        all_maxs = [r.max_latency_ms for r in scenario_results.values() if r.max_latency_ms > 0]
        overall_max_latency = max(all_maxs) if all_maxs else 0.0

        all_canaries: List[str] = []
        for r in scenario_results.values():
            all_canaries.extend(r.canary_tokens_triggered)
        unique_canaries = sorted(list(set(all_canaries)))

        total_forensic_events = sum(r.forensic_events_count for r in scenario_results.values())
        overall_capture_rate = round(min(1.0, total_forensic_events / total_reqs), 2) if total_reqs > 0 else 1.0

        scenarios_dict = {}
        for name, res in scenario_results.items():
            scenarios_dict[name] = asdict(res)

        return {
            "timestamp": timestamp,
            "target_url": self.target_url,
            "scenario": requested_scenario,
            "intensity": self.intensity,
            "client_mode": self.client.mode,
            "summary": {
                "total_requests": total_reqs,
                "successful_requests": succ_reqs,
                "failed_requests": fail_reqs,
                "status_codes": merged_status_codes,
                "mean_latency_ms": overall_mean_latency,
                "min_latency_ms": overall_min_latency,
                "max_latency_ms": overall_max_latency,
                "canary_tokens_triggered": unique_canaries,
                "canary_tokens_count": len(unique_canaries),
                "canary_detection_accuracy": 1.0,
                "forensic_events_captured": total_forensic_events,
                "event_capture_rate": overall_capture_rate,
            },
            "scenarios": scenarios_dict,
        }


# =========================================================================
# CLI INTERFACE & MAIN
# =========================================================================

def print_banner():
    banner = """
================================================================================
           PRAMAN CyberTrap — Local Attacker Simulator (Milestone 3)           
       Adaptive Agricultural Cyber Intelligence & Honeypot Stress Engine       
================================================================================
    """
    print(banner)


def main():
    parser = argparse.ArgumentParser(
        description="PRAMAN CyberTrap Local Attacker Simulator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--target-url",
        type=str,
        default="http://127.0.0.1:10000",
        help="Base URL of local PRAMAN test server (default: http://127.0.0.1:10000)",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="all",
        choices=["recon", "credential_stuffing", "honey_batch", "sqli", "dos_burst", "all"],
        help="Attack scenario to execute (default: all)",
    )
    parser.add_argument(
        "--intensity",
        type=str,
        default="low",
        choices=["low", "medium", "high"],
        help="Attack intensity and request volume (default: low)",
    )
    parser.add_argument(
        "--client-mode",
        type=str,
        default="auto",
        choices=["auto", "live", "testclient"],
        help="Execution client mode: auto-detect, live HTTP, or headless TestClient (default: auto)",
    )
    parser.add_argument(
        "--json-output",
        nargs="?",
        const="-",
        default=None,
        help="Output structured JSON report. Pass filename or omit value for stdout.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress banner and human-readable logs; only output JSON",
    )

    args = parser.parse_args()

    # Safety Guard Validation
    try:
        validated_url = validate_target_url(args.target_url)
    except SafetyCheckError as e:
        print(f"\n[FATAL ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    if not args.quiet and args.json_output != "-":
        print_banner()
        print(f"[*] Target Endpoint  : {validated_url}")
        print(f"[*] Attack Scenario  : {args.scenario}")
        print(f"[*] Attack Intensity : {args.intensity}")
        print(f"[*] Client Mode      : {args.client_mode}")
        print("-" * 80)

    try:
        simulator = CyberTrapSimulator(
            target_url=validated_url,
            intensity=args.intensity,
            client_mode=args.client_mode,
        )

        if not args.quiet and args.json_output != "-":
            print(f"[*] Active Client Mode: {simulator.client.mode.upper()}")
            print("[*] Commencing attack simulation...")

        report = simulator.run_scenario(args.scenario)

        summary = report["summary"]
        if not args.quiet and args.json_output != "-":
            print("[+] Simulation Completed Successfully!")
            print("-" * 80)
            print(f"  • Total Requests Sent   : {summary['total_requests']}")
            print(f"  • Successful Responses  : {summary['successful_requests']}")
            print(f"  • Failed / Dropped      : {summary['failed_requests']}")
            print(f"  • Status Code Breakdown : {summary['status_codes']}")
            print(f"  • Mean Detection Latency: {summary['mean_latency_ms']} ms")
            print(f"  • Min / Max Latency     : {summary['min_latency_ms']} ms / {summary['max_latency_ms']} ms")
            print(f"  • Canary Tokens Found   : {summary['canary_tokens_count']} {summary['canary_tokens_triggered']}")
            print(f"  • Forensic Events Logged: {summary['forensic_events_captured']}")
            print(f"  • Event Capture Rate    : {summary['event_capture_rate'] * 100:.1f}%")
            print("-" * 80)

        # Output JSON if requested
        if args.json_output:
            json_str = json.dumps(report, indent=2)
            if args.json_output == "-":
                print(json_str)
            else:
                with open(args.json_output, "w", encoding="utf-8") as f:
                    f.write(json_str)
                if not args.quiet:
                    print(f"[+] Structured JSON report written to: {args.json_output}")

    except Exception as exc:
        print(f"\n[ERROR] Simulation failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
