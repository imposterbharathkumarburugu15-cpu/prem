import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.cybertrap import CyberTrapEvent, CyberTrapIncident
from crypto.rfc8785 import canonicalize

logger = logging.getLogger("praman.cybertrap.threat_engine")


class ThreatEngine:
    """Explainable rule-based threat categorization and risk scoring engine for CyberTrap.
    
    STRICT ISOLATION INVARIANT:
    This engine operates strictly on CyberTrap events and incidents (`cybertrap_*` tables).
    It NEVER queries, modifies, or adjusts trust scores for farmers, farms, devices,
    or crop evidence records.
    """

    SQLI_PATTERNS = [
        "union select", "select *", "drop table", "1=1", "or 1=1",
        "--", "/*", "sleep(", "benchmark(", "' or '", "';--", "exec(",
        "information_schema", "xp_cmdshell", "waitfor delay"
    ]

    RISK_LEVEL_WEIGHTS = {
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4,
    }

    @classmethod
    def evaluate_event(
        cls,
        event: CyberTrapEvent,
        recent_context: Optional[List[CyberTrapEvent]] = None,
    ) -> Dict[str, Any]:
        """Evaluates a CyberTrapEvent and determines its threat category, risk score, and rationale.
        
        Supported categories:
        - CANARY_HONEYTOKEN_TRIGGERED: Honeytoken secret detected in request/payload
        - DATA_EXFILTRATION: Honey-batch record access or unauthorized export
        - SQLI_PROBE: SQL injection probe detected in query, path, or payload
        - BRUTE_FORCE: Rapid repetitive authentication attempts
        - DOS_BURST: High-frequency burst of requests from the same source
        - RECONNAISSANCE: Multi-endpoint probing or admin resource discovery
        """
        context = recent_context or []
        rules_triggered = []
        highest_risk = "LOW"

        def trigger_rule(level: str, rule_name: str, rationale: str, evidence: List[str], confidence: float):
            nonlocal highest_risk
            if cls.RISK_LEVEL_WEIGHTS[level] > cls.RISK_LEVEL_WEIGHTS[highest_risk]:
                highest_risk = level
            rules_triggered.append({
                "rule": rule_name,
                "risk_level": level,
                "rationale": rationale,
                "evidence_fields": evidence,
                "confidence": confidence,
            })

        # 1. Honeytoken and Canary Trigger
        if event.is_honeytoken_triggered:
            trigger_rule(
                "CRITICAL" if event.honeytoken_id else "HIGH",
                "CANARY_HONEYTOKEN_TRIGGERED",
                f"Synthetic canary honeytoken '{event.honeytoken_id or 'unknown'}' was activated in honeypot interaction.",
                ["is_honeytoken_triggered", "honeytoken_id", "request_path"],
                1.0,
            )

        # 2. SQL Injection Inspection
        payload_text = (event.payload_json or "").lower()
        query_text = (event.query_params_json or "").lower()
        path_text = (event.request_path or "").lower()
        combined_text = f"{payload_text} {query_text} {path_text}"

        for sqli_kw in cls.SQLI_PATTERNS:
            if sqli_kw in combined_text:
                trigger_rule(
                    "HIGH",
                    "SQLI_PROBE",
                    f"SQL injection syntax pattern '{sqli_kw}' identified in probe.",
                    ["payload_json", "query_params_json", "request_path"],
                    0.96,
                )
                break

        # 3. Contextual Temporal Patterns
        now = event.timestamp or datetime.now(timezone.utc)
        peer_events = [
            e for e in context
            if e.source_ip == event.source_ip and e.id != event.id
        ]

        # Brute Force / Credential Stuffing
        ten_mins_ago = now - timedelta(minutes=10)
        recent_auth_events = [
            e for e in peer_events
            if "auth" in e.request_path.lower() and e.timestamp and e.timestamp >= ten_mins_ago
        ]
        if len(recent_auth_events) >= 3 or ("auth" in event.request_path.lower() and len(recent_auth_events) >= 2):
            trigger_rule(
                "CRITICAL" if len(recent_auth_events) >= 4 else "HIGH",
                "BRUTE_FORCE",
                f"Repetitive authentication attempts detected ({len(recent_auth_events) + 1} requests within 10 minutes) from {event.source_ip}.",
                ["source_ip", "request_path", "timestamp"],
                0.95,
            )

        # DoS Burst
        sixty_secs_ago = now - timedelta(seconds=60)
        recent_burst_events = [
            e for e in peer_events
            if e.timestamp and e.timestamp >= sixty_secs_ago
        ]
        if len(recent_burst_events) >= 5:
            trigger_rule(
                "HIGH",
                "DOS_BURST",
                f"High-frequency request burst: {len(recent_burst_events) + 1} requests within 60s from {event.source_ip}.",
                ["source_ip", "timestamp"],
                0.90,
            )

        # Data Exfiltration / Honey Batch Temptation
        if "batches" in path_text or "export" in path_text or event.decoy_type in ["HONEY_BATCH", "ADMIN_PORTAL"]:
            if event.decoy_type == "HONEY_BATCH" or "batches" in path_text:
                trigger_rule(
                    "HIGH",
                    "DATA_EXFILTRATION",
                    f"Direct exfiltration probe on synthetic honey-batch resource: '{event.request_path}'.",
                    ["request_path", "decoy_type", "decoy_id"],
                    0.92,
                )

        # Reconnaissance / Directory Discovery
        if any(term in path_text for term in ["admin", "internal", "root", "dump", "export", "config"]):
            trigger_rule(
                "MEDIUM",
                "RECONNAISSANCE",
                f"Unauthorized enumeration of administrative decoy paths: '{event.request_path}'.",
                ["request_path", "decoy_type"],
                0.85,
            )

        # Multi-endpoint Reconnaissance
        five_mins_ago = now - timedelta(minutes=5)
        distinct_paths = set(
            e.request_path for e in peer_events
            if e.timestamp and e.timestamp >= five_mins_ago
        )
        distinct_paths.add(event.request_path)
        if len(distinct_paths) >= 3:
            trigger_rule(
                "MEDIUM" if highest_risk == "LOW" else highest_risk,
                "RECONNAISSANCE",
                f"Broad reconnaissance probing {len(distinct_paths)} separate decoy endpoints within 5 minutes.",
                ["request_path", "source_ip"],
                0.88,
            )

        # Fallback if no specific rule matched
        if not rules_triggered:
            trigger_rule(
                "LOW",
                "RECONNAISSANCE",
                f"Isolated interaction with decoy honeypot endpoint: '{event.request_path}'.",
                ["request_path", "source_ip"],
                0.50,
            )

        # Determine Primary Category
        primary_category = "RECONNAISSANCE"
        rule_priority = [
            ("CANARY_HONEYTOKEN_TRIGGERED", "CANARY_HONEYTOKEN_TRIGGERED"),
            ("BRUTE_FORCE", "BRUTE_FORCE"),
            ("SQLI_PROBE", "SQLI_PROBE"),
            ("DOS_BURST", "DOS_BURST"),
            ("DATA_EXFILTRATION", "DATA_EXFILTRATION"),
            ("RECONNAISSANCE", "RECONNAISSANCE"),
        ]

        for rule_key, cat_name in rule_priority:
            if any(r["rule"] == rule_key for r in rules_triggered):
                primary_category = cat_name
                break

        explanation_dict = {
            "primary_rule": rules_triggered[0]["rule"],
            "category": primary_category,
            "risk_level": highest_risk,
            "rationale": rules_triggered[0]["rationale"],
            "rules_triggered": rules_triggered,
            "source_ip": event.source_ip,
            "timestamp": now.isoformat() if isinstance(now, datetime) else str(now),
            "decoy_id": event.decoy_id,
            "decoy_type": event.decoy_type,
            "request_path": event.request_path,
        }

        return {
            "category": primary_category,
            "risk_level": highest_risk,
            "explanation": explanation_dict,
            "rules_triggered": rules_triggered,
        }

    @classmethod
    def compute_canonical_incident_hash(cls, incident_payload: Dict[str, Any]) -> str:
        """Deterministic RFC 8785 canonical JSON SHA-256 digest calculation.
        
        Conforms strictly to RFC 8785:
        - Sorted keys
        - Canonical whitespace formatting
        - Cryptographic SHA-256 hash
        """
        canonical_bytes = canonicalize(incident_payload)
        return hashlib.sha256(canonical_bytes).hexdigest()

    @classmethod
    def process_event_to_incident(
        cls,
        db: Session,
        event: CyberTrapEvent,
    ) -> CyberTrapIncident:
        """Processes an individual CyberTrapEvent, performs evaluation, and creates or updates a CyberTrapIncident."""
        # Find recent context events from this IP
        now = event.timestamp or datetime.now(timezone.utc)
        lookback_window = now - timedelta(hours=2)
        recent_events = (
            db.query(CyberTrapEvent)
            .filter(
                CyberTrapEvent.source_ip == event.source_ip,
                CyberTrapEvent.timestamp >= lookback_window,
            )
            .order_by(CyberTrapEvent.timestamp.asc())
            .all()
        )

        evaluation = cls.evaluate_event(event, recent_events)
        category = evaluation["category"]
        risk_level = evaluation["risk_level"]
        explanation = evaluation["explanation"]

        # Check if an active incident exists for this source_ip and category within 24 hours
        cutoff = now - timedelta(hours=24)
        incident = (
            db.query(CyberTrapIncident)
            .filter(
                CyberTrapIncident.source_ip == event.source_ip,
                CyberTrapIncident.category == category,
                CyberTrapIncident.status.in_(["ACTIVE", "INVESTIGATING"]),
                CyberTrapIncident.created_at >= cutoff,
            )
            .first()
        )

        if incident:
            # Update existing incident
            incident.event_count += 1
            # Escalate risk level if current evaluation is higher
            if cls.RISK_LEVEL_WEIGHTS[risk_level] > cls.RISK_LEVEL_WEIGHTS[incident.risk_level]:
                incident.risk_level = risk_level
            incident.explanation_json = json.dumps(explanation)
            incident.description = f"Aggregated {incident.event_count} events from {event.source_ip}: {explanation['rationale']}"
        else:
            # Create new incident
            incident = CyberTrapIncident(
                category=category,
                risk_level=risk_level,
                source_ip=event.source_ip,
                event_count=1,
                description=f"Initial detection on {event.request_path}: {explanation['rationale']}",
                explanation_json=json.dumps(explanation),
                status="ACTIVE",
            )
            db.add(incident)

        db.flush()

        # Update canonical hash using RFC 8785
        canonical_payload = {
            "incident_id": incident.id,
            "category": incident.category,
            "risk_level": incident.risk_level,
            "source_ip": incident.source_ip,
            "event_count": incident.event_count,
            "description": incident.description,
        }
        incident.canonical_report_hash = cls.compute_canonical_incident_hash(canonical_payload)
        db.commit()
        db.refresh(incident)

        return incident

    @classmethod
    def evaluate_all_recent_events(
        cls,
        db: Session,
        lookback_minutes: int = 120,
    ) -> List[CyberTrapIncident]:
        """Scans recent events and ensures all events are promoted to incidents."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
        events = (
            db.query(CyberTrapEvent)
            .filter(CyberTrapEvent.timestamp >= cutoff)
            .order_by(CyberTrapEvent.timestamp.asc())
            .all()
        )

        incidents_created = []
        for ev in events:
            inc = cls.process_event_to_incident(db, ev)
            if inc not in incidents_created:
                incidents_created.append(inc)

        return incidents_created
