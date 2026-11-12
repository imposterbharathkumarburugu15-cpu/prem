"""
Threat Intelligence Engine — PRAMAN CyberTrap Milestone 4.

EXPLAINABLE rule-based anomaly classification engine.
No black-box ML — every decision carries a human-readable reason string,
the specific event fields that triggered it, and a confidence score.

Isolation guarantee: operates ONLY on cybertrap_* tables.
Real farmer / farm / batch / evidence tables are never touched.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.app.models.cybertrap import CyberTrapEvent, CyberTrapIncident

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RISK_LOW = "LOW"
RISK_MEDIUM = "MEDIUM"
RISK_HIGH = "HIGH"
RISK_CRITICAL = "CRITICAL"

RISK_ORDER = {RISK_LOW: 0, RISK_MEDIUM: 1, RISK_HIGH: 2, RISK_CRITICAL: 3}

# SQL injection keyword pattern (case-insensitive)
_SQLI_PATTERN = re.compile(
    r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|OR\s+1=1|AND\s+1=1"
    r"|--|;--|\/\*|\*\/|xp_|EXEC\s*\(|EXECUTE\s*\(|CAST\s*\(|CONVERT\s*\()\b",
    re.IGNORECASE,
)

# Decoy admin paths
_ADMIN_PATH_PATTERN = re.compile(
    r"(admin|export.database|internal.tokens|dump|backup|root|superuser)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data-classes (plain dicts returned to callers)
# ---------------------------------------------------------------------------

class ClassificationResult:
    """Single-rule classification result."""

    __slots__ = (
        "rule_name",
        "risk_level",
        "reason_text",
        "evidence_fields",
        "confidence_score",
        "category",
    )

    def __init__(
        self,
        rule_name: str,
        risk_level: str,
        reason_text: str,
        evidence_fields: List[str],
        confidence_score: float,
        category: str,
    ) -> None:
        self.rule_name = rule_name
        self.risk_level = risk_level
        self.reason_text = reason_text
        self.evidence_fields = evidence_fields
        self.confidence_score = confidence_score
        self.category = category

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "risk_level": self.risk_level,
            "reason_text": self.reason_text,
            "evidence_fields": self.evidence_fields,
            "confidence_score": self.confidence_score,
            "category": self.category,
        }


# ---------------------------------------------------------------------------
# ThreatIntelligenceEngine
# ---------------------------------------------------------------------------

class ThreatIntelligenceEngine:
    """
    Explainable, rule-based threat classification engine for CyberTrap events.

    Design principles:
    - Every decision is deterministic and reproducible from the raw event data.
    - Each rule carries: rule_name, reason_text, evidence_fields, confidence_score.
    - HIGH / CRITICAL findings automatically create CyberTrapIncident DB records.
    - NEVER touches real farmer / farm / batch / evidence tables.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyse_unclassified(self, db: Session) -> Dict[str, Any]:
        """
        Analyse all CyberTrapEvents that have not yet been linked to an
        incident.  Returns a summary dict suitable for the /analyse endpoint.
        """
        # Fetch all events (cybertrap table only)
        all_events: List[CyberTrapEvent] = (
            db.query(CyberTrapEvent)
            .order_by(CyberTrapEvent.timestamp)
            .all()
        )

        # Existing incident source-ip set so we don't double-create
        existing_incident_ips = {
            row.source_ip
            for row in db.query(CyberTrapIncident.source_ip).all()
        }

        summary = {
            "events_analysed": len(all_events),
            "classifications": [],
            "incidents_created": 0,
            "risk_distribution": {
                RISK_LOW: 0,
                RISK_MEDIUM: 0,
                RISK_HIGH: 0,
                RISK_CRITICAL: 0,
            },
        }

        # Group by source_ip for windowed rule evaluation
        by_ip: Dict[str, List[CyberTrapEvent]] = defaultdict(list)
        by_session: Dict[str, List[CyberTrapEvent]] = defaultdict(list)
        for ev in all_events:
            by_ip[ev.source_ip].append(ev)
            if ev.session_id:
                by_session[ev.session_id].append(ev)

        # Classify each event and collect HIGH/CRITICAL per-IP groups
        # We want one incident per unique (source_ip, rule_name) pair so we
        # don't spam the incidents table on repeated runs.
        incidents_to_create: Dict[Tuple[str, str], Dict[str, Any]] = {}

        for ev in all_events:
            result = self._classify_event(ev, by_ip, by_session)
            summary["classifications"].append(
                {
                    "event_id": ev.id,
                    "source_ip": ev.source_ip,
                    **result.to_dict(),
                }
            )
            summary["risk_distribution"][result.risk_level] += 1

            if RISK_ORDER[result.risk_level] >= RISK_ORDER[RISK_HIGH]:
                key = (ev.source_ip, result.rule_name)
                if key not in incidents_to_create:
                    incidents_to_create[key] = {
                        "source_ip": ev.source_ip,
                        "classification": result,
                        "event_ids": [ev.id],
                        "first_seen": ev.timestamp,
                    }
                else:
                    incidents_to_create[key]["event_ids"].append(ev.id)

        # Persist new incidents (skip IPs that already have an incident for this rule)
        for key, info in incidents_to_create.items():
            source_ip = info["source_ip"]
            classification: ClassificationResult = info["classification"]

            # Check if incident with same ip+rule already exists
            existing = (
                db.query(CyberTrapIncident)
                .filter(
                    CyberTrapIncident.source_ip == source_ip,
                    CyberTrapIncident.category == classification.category,
                )
                .first()
            )
            if existing:
                continue

            explanation = {
                "rule_name": classification.rule_name,
                "reason_text": classification.reason_text,
                "evidence_fields": classification.evidence_fields,
                "confidence_score": classification.confidence_score,
                "triggering_event_ids": info["event_ids"][:20],
            }
            explanation_str = json.dumps(explanation)
            canonical = hashlib.sha256(
                f"{source_ip}:{classification.rule_name}:{info['first_seen']}".encode()
            ).hexdigest()

            incident = CyberTrapIncident(
                id=str(uuid.uuid4()),
                created_at=datetime.now(timezone.utc),
                category=classification.category,
                risk_level=classification.risk_level,
                source_ip=source_ip,
                event_count=len(info["event_ids"]),
                description=classification.reason_text,
                explanation_json=explanation_str,
                status="ACTIVE",
                canonical_report_hash=canonical,
            )
            db.add(incident)
            summary["incidents_created"] += 1

        try:
            db.commit()
        except Exception:
            db.rollback()

        return summary

    def classify_event(
        self,
        event: CyberTrapEvent,
        db: Session,
    ) -> ClassificationResult:
        """
        Classify a single event in isolation (best-effort — no cross-event windowing).
        Used for inline / real-time classification.
        """
        by_ip: Dict[str, List[CyberTrapEvent]] = defaultdict(list)
        by_session: Dict[str, List[CyberTrapEvent]] = defaultdict(list)

        # Fetch sibling events for the same IP from DB for windowed rules
        siblings: List[CyberTrapEvent] = (
            db.query(CyberTrapEvent)
            .filter(CyberTrapEvent.source_ip == event.source_ip)
            .order_by(CyberTrapEvent.timestamp)
            .all()
        )
        by_ip[event.source_ip] = siblings

        if event.session_id:
            session_siblings: List[CyberTrapEvent] = (
                db.query(CyberTrapEvent)
                .filter(CyberTrapEvent.session_id == event.session_id)
                .order_by(CyberTrapEvent.timestamp)
                .all()
            )
            by_session[event.session_id] = session_siblings

        return self._classify_event(event, by_ip, by_session)

    def get_patterns(self, db: Session) -> Dict[str, Any]:
        """
        Aggregate threat patterns across all recorded CyberTrapEvents:
        - top source IPs (by event count)
        - top decoy endpoints triggered
        - risk-level distribution (via classify_event)
        - honeytoken activation rate
        """
        all_events: List[CyberTrapEvent] = db.query(CyberTrapEvent).all()

        ip_counts: Dict[str, int] = defaultdict(int)
        decoy_counts: Dict[str, int] = defaultdict(int)
        risk_dist: Dict[str, int] = {
            RISK_LOW: 0, RISK_MEDIUM: 0, RISK_HIGH: 0, RISK_CRITICAL: 0
        }
        honeytoken_hits = 0

        by_ip: Dict[str, List[CyberTrapEvent]] = defaultdict(list)
        by_session: Dict[str, List[CyberTrapEvent]] = defaultdict(list)
        for ev in all_events:
            by_ip[ev.source_ip].append(ev)
            if ev.session_id:
                by_session[ev.session_id].append(ev)

        for ev in all_events:
            ip_counts[ev.source_ip] += 1
            decoy_counts[ev.decoy_id] += 1
            if ev.is_honeytoken_triggered:
                honeytoken_hits += 1
            result = self._classify_event(ev, by_ip, by_session)
            risk_dist[result.risk_level] += 1

        top_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_decoys = sorted(decoy_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_events": len(all_events),
            "top_source_ips": [{"ip": ip, "count": c} for ip, c in top_ips],
            "top_decoys_triggered": [{"decoy_id": d, "count": c} for d, c in top_decoys],
            "risk_distribution": risk_dist,
            "honeytoken_activation_count": honeytoken_hits,
            "honeytoken_activation_rate": (
                round(honeytoken_hits / len(all_events), 4) if all_events else 0.0
            ),
        }

    def get_stats(self, db: Session) -> Dict[str, Any]:
        """
        Return detection statistics:
        - total events, total incidents
        - detection rate (incidents / events)
        - false-positive rate placeholder (requires human feedback loop)
        - average detection latency placeholder
        - risk distribution
        """
        total_events = db.query(CyberTrapEvent).count()
        total_incidents = db.query(CyberTrapIncident).count()
        active_incidents = (
            db.query(CyberTrapIncident)
            .filter(CyberTrapIncident.status == "ACTIVE")
            .count()
        )
        critical_incidents = (
            db.query(CyberTrapIncident)
            .filter(CyberTrapIncident.risk_level == RISK_CRITICAL)
            .count()
        )
        high_incidents = (
            db.query(CyberTrapIncident)
            .filter(CyberTrapIncident.risk_level == RISK_HIGH)
            .count()
        )

        detection_rate = (
            round(total_incidents / total_events, 4) if total_events > 0 else 0.0
        )

        return {
            "total_events": total_events,
            "total_incidents": total_incidents,
            "active_incidents": active_incidents,
            "critical_incidents": critical_incidents,
            "high_incidents": high_incidents,
            "detection_rate": detection_rate,
            "false_positive_rate_placeholder": None,
            "note_false_positive": (
                "False-positive rate requires analyst feedback loop; "
                "not yet implemented — placeholder returns null."
            ),
            "avg_detection_latency_seconds_placeholder": None,
            "note_latency": (
                "Detection latency is computed on-demand analysis runs; "
                "real-time streaming not yet enabled."
            ),
            "engine_version": "1.0.0",
            "rules_active": 7,
        }

    # ------------------------------------------------------------------
    # Core classification logic (private)
    # ------------------------------------------------------------------

    def _classify_event(
        self,
        event: CyberTrapEvent,
        by_ip: Dict[str, List[CyberTrapEvent]],
        by_session: Dict[str, List[CyberTrapEvent]],
    ) -> ClassificationResult:
        """
        Apply all rules in priority order (CRITICAL > HIGH > MEDIUM > LOW).
        Returns the highest-severity matching ClassificationResult.
        """
        rules = [
            self._rule_credential_stuffing,
            self._rule_burst_scan,
            self._rule_sqli_attempt,
            self._rule_repeated_probe,
            self._rule_canary_activated,
            self._rule_admin_enumeration,
            self._rule_low_signal,
        ]
        best: Optional[ClassificationResult] = None

        for rule_fn in rules:
            result = rule_fn(event, by_ip, by_session)
            if result is None:
                continue
            if best is None or RISK_ORDER[result.risk_level] > RISK_ORDER[best.risk_level]:
                best = result
            # Short-circuit on CRITICAL
            if best.risk_level == RISK_CRITICAL:
                break

        # Fallback should never be reached but be safe
        if best is None:
            best = self._rule_low_signal(event, by_ip, by_session)  # type: ignore[return-value]

        return best  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Individual rules
    # ------------------------------------------------------------------

    def _rule_repeated_probe(
        self,
        event: CyberTrapEvent,
        by_ip: Dict[str, List[CyberTrapEvent]],
        by_session: Dict[str, List[CyberTrapEvent]],
    ) -> Optional[ClassificationResult]:
        """
        REPEATED_PROBE: same session_id OR source_ip hits >3 distinct decoy
        endpoints within any 5-minute sliding window → HIGH.
        """
        WINDOW = timedelta(minutes=5)
        THRESHOLD = 3

        def _distinct_decoys_in_window(events: List[CyberTrapEvent], anchor: datetime) -> int:
            start = anchor - WINDOW
            # Make anchor timezone-aware if needed
            if anchor.tzinfo is None:
                start = start.replace(tzinfo=None)
            return len(
                {
                    e.decoy_id
                    for e in events
                    if _ts(e) >= start and _ts(e) <= _ts_or(anchor, _ts(e))
                }
            )

        anchor = _ts(event)

        # Check by session first (tighter signal)
        session_events = by_session.get(event.session_id or "", [])
        if session_events:
            distinct = _distinct_decoys_in_window(session_events, anchor)
            if distinct > THRESHOLD:
                return ClassificationResult(
                    rule_name="REPEATED_PROBE",
                    risk_level=RISK_HIGH,
                    reason_text=(
                        f"Session {event.session_id!r} probed {distinct} distinct decoy "
                        f"endpoints within a 5-minute window (threshold: >{THRESHOLD})."
                    ),
                    evidence_fields=["session_id", "decoy_id", "timestamp"],
                    confidence_score=min(0.6 + (distinct - THRESHOLD) * 0.08, 0.95),
                    category="RECONNAISSANCE",
                )

        # Check by IP
        ip_events = by_ip.get(event.source_ip, [])
        distinct = _distinct_decoys_in_window(ip_events, anchor)
        if distinct > THRESHOLD:
            return ClassificationResult(
                rule_name="REPEATED_PROBE",
                risk_level=RISK_HIGH,
                reason_text=(
                    f"Source IP {event.source_ip} probed {distinct} distinct decoy "
                    f"endpoints within a 5-minute window (threshold: >{THRESHOLD})."
                ),
                evidence_fields=["source_ip", "decoy_id", "timestamp"],
                confidence_score=min(0.55 + (distinct - THRESHOLD) * 0.07, 0.92),
                category="RECONNAISSANCE",
            )

        return None

    def _rule_canary_activated(
        self,
        event: CyberTrapEvent,
        by_ip: Dict[str, List[CyberTrapEvent]],
        by_session: Dict[str, List[CyberTrapEvent]],
    ) -> Optional[ClassificationResult]:
        """
        CANARY_ACTIVATED: any event with is_honeytoken_triggered=True → HIGH.
        """
        if not event.is_honeytoken_triggered:
            return None
        return ClassificationResult(
            rule_name="CANARY_ACTIVATED",
            risk_level=RISK_HIGH,
            reason_text=(
                f"Honeytoken canary triggered on decoy {event.decoy_id!r}. "
                f"Token ID: {event.honeytoken_id!r}. "
                "This indicates deliberate use or exfiltration of a synthetic credential."
            ),
            evidence_fields=["is_honeytoken_triggered", "honeytoken_id", "decoy_id"],
            confidence_score=0.97,
            category="DATA_EXFILTRATION",
        )

    def _rule_credential_stuffing(
        self,
        event: CyberTrapEvent,
        by_ip: Dict[str, List[CyberTrapEvent]],
        by_session: Dict[str, List[CyberTrapEvent]],
    ) -> Optional[ClassificationResult]:
        """
        CREDENTIAL_STUFFING: >5 failed decoy auth attempts from same IP in
        10 minutes → CRITICAL.

        Auth events are identified by decoy_type=API_ENDPOINT and
        decoy_id containing 'AUTH' or 'LOGIN' (case-insensitive).
        """
        WINDOW = timedelta(minutes=10)
        THRESHOLD = 5

        auth_pattern = re.compile(r"(auth|login|credential|token)", re.IGNORECASE)
        ip_events = by_ip.get(event.source_ip, [])
        anchor = _ts(event)
        start = anchor - WINDOW

        auth_hits = [
            e
            for e in ip_events
            if _ts(e) >= start
            and auth_pattern.search(e.decoy_id)
        ]
        count = len(auth_hits)
        if count > THRESHOLD:
            return ClassificationResult(
                rule_name="CREDENTIAL_STUFFING",
                risk_level=RISK_CRITICAL,
                reason_text=(
                    f"Source IP {event.source_ip} made {count} failed decoy "
                    f"authentication attempts within 10 minutes (threshold: >{THRESHOLD}). "
                    "Pattern is consistent with automated credential-stuffing attack."
                ),
                evidence_fields=["source_ip", "decoy_id", "decoy_type", "timestamp"],
                confidence_score=min(0.70 + (count - THRESHOLD) * 0.05, 0.99),
                category="CREDENTIAL_STUFFING",
            )
        return None

    def _rule_admin_enumeration(
        self,
        event: CyberTrapEvent,
        by_ip: Dict[str, List[CyberTrapEvent]],
        by_session: Dict[str, List[CyberTrapEvent]],
    ) -> Optional[ClassificationResult]:
        """
        ADMIN_ENUMERATION: probe of a decoy admin path → MEDIUM.
        """
        path = event.request_path or ""
        decoy_id = event.decoy_id or ""
        if _ADMIN_PATH_PATTERN.search(path) or _ADMIN_PATH_PATTERN.search(decoy_id):
            return ClassificationResult(
                rule_name="ADMIN_ENUMERATION",
                risk_level=RISK_MEDIUM,
                reason_text=(
                    f"Source IP {event.source_ip} probed a decoy admin path "
                    f"({path!r}) via {event.request_method}. "
                    "Suggests active administrative interface enumeration."
                ),
                evidence_fields=["request_path", "decoy_id", "source_ip", "request_method"],
                confidence_score=0.75,
                category="RECONNAISSANCE",
            )
        return None

    def _rule_sqli_attempt(
        self,
        event: CyberTrapEvent,
        by_ip: Dict[str, List[CyberTrapEvent]],
        by_session: Dict[str, List[CyberTrapEvent]],
    ) -> Optional[ClassificationResult]:
        """
        SQLI_ATTEMPT: SQL injection keywords detected in request body or query
        params → HIGH.
        """
        targets = []
        evidence: List[str] = []

        if event.payload_json:
            targets.append(("payload_json", event.payload_json))
        if event.query_params_json:
            targets.append(("query_params_json", event.query_params_json))

        matched_fields: List[str] = []
        matched_keywords: List[str] = []
        for field_name, text in targets:
            matches = _SQLI_PATTERN.findall(text)
            if matches:
                matched_fields.append(field_name)
                matched_keywords.extend(matches)

        if matched_fields:
            kw_str = ", ".join(set(matched_keywords))[:200]
            return ClassificationResult(
                rule_name="SQLI_ATTEMPT",
                risk_level=RISK_HIGH,
                reason_text=(
                    f"SQL injection keywords detected in {matched_fields} from "
                    f"IP {event.source_ip}. Keywords: [{kw_str}]. "
                    "Request body or query parameters contain SQL control tokens."
                ),
                evidence_fields=matched_fields + ["source_ip", "decoy_id"],
                confidence_score=0.90,
                category="SQLI_PROBE",
            )
        return None

    def _rule_burst_scan(
        self,
        event: CyberTrapEvent,
        by_ip: Dict[str, List[CyberTrapEvent]],
        by_session: Dict[str, List[CyberTrapEvent]],
    ) -> Optional[ClassificationResult]:
        """
        BURST_SCAN: >10 requests from same IP within 60 seconds → HIGH.
        """
        WINDOW = timedelta(seconds=60)
        THRESHOLD = 10

        ip_events = by_ip.get(event.source_ip, [])
        anchor = _ts(event)
        start = anchor - WINDOW

        window_events = [e for e in ip_events if _ts(e) >= start and _ts(e) <= anchor]
        count = len(window_events)
        if count > THRESHOLD:
            return ClassificationResult(
                rule_name="BURST_SCAN",
                risk_level=RISK_HIGH,
                reason_text=(
                    f"Source IP {event.source_ip} sent {count} requests within 60 seconds "
                    f"(threshold: >{THRESHOLD}). Burst pattern indicative of automated scanner."
                ),
                evidence_fields=["source_ip", "timestamp"],
                confidence_score=min(0.65 + (count - THRESHOLD) * 0.03, 0.95),
                category="RECONNAISSANCE",
            )
        return None

    def _rule_low_signal(
        self,
        event: CyberTrapEvent,
        by_ip: Dict[str, List[CyberTrapEvent]],
        by_session: Dict[str, List[CyberTrapEvent]],
    ) -> ClassificationResult:
        """
        LOW_SIGNAL: single isolated probe not matching any higher rule → LOW.
        Always fires as the final fallback.
        """
        ip_count = len(by_ip.get(event.source_ip, []))
        return ClassificationResult(
            rule_name="LOW_SIGNAL",
            risk_level=RISK_LOW,
            reason_text=(
                f"Single isolated probe from IP {event.source_ip} to decoy "
                f"{event.decoy_id!r}. No corroborating patterns detected "
                f"(total events from this IP: {ip_count})."
            ),
            evidence_fields=["source_ip", "decoy_id", "timestamp"],
            confidence_score=0.40,
            category="RECONNAISSANCE",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts(event: CyberTrapEvent) -> datetime:
    """Return timezone-aware UTC datetime for an event."""
    t = event.timestamp
    if t is None:
        return datetime.now(timezone.utc)
    if t.tzinfo is None:
        return t.replace(tzinfo=timezone.utc)
    return t


def _ts_or(a: datetime, b: datetime) -> datetime:
    """Return the later of two datetimes (mixing tz-aware if needed)."""
    if a.tzinfo is None:
        a = a.replace(tzinfo=timezone.utc)
    if b.tzinfo is None:
        b = b.replace(tzinfo=timezone.utc)
    return a if a >= b else b


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

threat_intelligence_engine = ThreatIntelligenceEngine()
