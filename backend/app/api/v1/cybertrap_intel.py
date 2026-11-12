import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.database import get_db
from backend.app.models.cybertrap import CyberTrapEvent, CyberTrapIncident
from backend.app.services.cybertrap.threat_engine import ThreatEngine

router = APIRouter(tags=["CyberTrap Threat Intelligence"])


def _format_incident(inc: CyberTrapIncident) -> Dict[str, Any]:
    explanation = {}
    try:
        explanation = json.loads(inc.explanation_json or "{}")
    except Exception:
        explanation = {"raw": inc.explanation_json}

    return {
        "id": inc.id,
        "created_at": inc.created_at.isoformat() if inc.created_at else None,
        "category": inc.category,
        "risk_level": inc.risk_level,
        "source_ip": inc.source_ip,
        "event_count": inc.event_count,
        "description": inc.description,
        "explanation": explanation,
        "status": inc.status,
        "canonical_report_hash": inc.canonical_report_hash,
        "ledger_checkpoint_id": inc.ledger_checkpoint_id,
        "ledger_anchored_at": inc.ledger_anchored_at.isoformat() if inc.ledger_anchored_at else None,
    }


# Endpoints under /cybertrap/intelligence/
@router.get("/cybertrap/intelligence/incidents")
@router.get("/cybertrap/intel/incidents")
def list_threat_incidents(
    status: Optional[str] = None,
    risk_level: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Retrieve categorized threat intelligence incidents."""
    query = db.query(CyberTrapIncident)
    if status:
        query = query.filter(CyberTrapIncident.status == status)
    if risk_level:
        query = query.filter(CyberTrapIncident.risk_level == risk_level)
    if category:
        query = query.filter(CyberTrapIncident.category == category)

    total = query.count()
    incidents = query.order_by(CyberTrapIncident.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_format_incident(inc) for inc in incidents],
    }


@router.get("/cybertrap/intelligence/incidents/{incident_id}")
@router.get("/cybertrap/intel/incidents/{incident_id}")
def get_threat_incident(
    incident_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve details and explainable analysis for a single threat incident."""
    incident = db.query(CyberTrapIncident).filter(CyberTrapIncident.id == incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Threat incident '{incident_id}' not found.",
        )
    return _format_incident(incident)


@router.get("/cybertrap/intelligence/overview")
@router.get("/cybertrap/intel/overview")
def get_threat_overview(db: Session = Depends(get_db)):
    """Retrieve system threat metrics, totals, and risk/category distributions."""
    total_incidents = db.query(CyberTrapIncident).count()
    active_incidents = db.query(CyberTrapIncident).filter(CyberTrapIncident.status == "ACTIVE").count()
    mitigated_incidents = db.query(CyberTrapIncident).filter(CyberTrapIncident.status == "MITIGATED").count()
    investigating_incidents = db.query(CyberTrapIncident).filter(CyberTrapIncident.status == "INVESTIGATING").count()

    total_events = db.query(CyberTrapEvent).count()
    honeytoken_triggers = db.query(CyberTrapEvent).filter(CyberTrapEvent.is_honeytoken_triggered == True).count()

    # Risk breakdown
    risk_counts = (
        db.query(CyberTrapIncident.risk_level, func.count(CyberTrapIncident.id))
        .group_by(CyberTrapIncident.risk_level)
        .all()
    )
    risk_breakdown = {
        "CRITICAL": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
    }
    for level, count in risk_counts:
        if level in risk_breakdown:
            risk_breakdown[level] = count

    # Category breakdown
    category_counts = (
        db.query(CyberTrapIncident.category, func.count(CyberTrapIncident.id))
        .group_by(CyberTrapIncident.category)
        .all()
    )
    category_breakdown = {cat: count for cat, count in category_counts}

    recent_incidents = (
        db.query(CyberTrapIncident)
        .order_by(CyberTrapIncident.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "total_incidents": total_incidents,
        "active_incidents": active_incidents,
        "mitigated_incidents": mitigated_incidents,
        "investigating_incidents": investigating_incidents,
        "total_events_analyzed": total_events,
        "honeytoken_triggers": honeytoken_triggers,
        "risk_breakdown": risk_breakdown,
        "category_breakdown": category_breakdown,
        "recent_incidents": [_format_incident(inc) for inc in recent_incidents],
    }


# Backwards compatibility endpoints for existing tests / UI
@router.get("/cybertrap/intel/events")
def list_threat_events(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    decoy_type: Optional[str] = None,
    source_ip: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(CyberTrapEvent)
    if decoy_type:
        query = query.filter(CyberTrapEvent.decoy_type == decoy_type)
    if source_ip:
        query = query.filter(CyberTrapEvent.source_ip == source_ip)

    total = query.count()
    events = query.order_by(CyberTrapEvent.timestamp.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": ev.id,
                "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                "decoy_id": ev.decoy_id,
                "decoy_type": ev.decoy_type,
                "request_method": ev.request_method,
                "request_path": ev.request_path,
                "source_ip": ev.source_ip,
                "user_agent": ev.user_agent,
                "session_id": ev.session_id,
                "is_honeytoken_triggered": ev.is_honeytoken_triggered,
                "honeytoken_id": ev.honeytoken_id,
            }
            for ev in events
        ],
    }


@router.post("/cybertrap/intel/analyse")
def trigger_threat_analysis(
    lookback_minutes: int = Query(120, ge=5, le=1440),
    db: Session = Depends(get_db),
):
    incidents = ThreatEngine.evaluate_all_recent_events(db=db, lookback_minutes=lookback_minutes)
    return {
        "status": "COMPLETED",
        "incidents_generated": len(incidents),
        "incident_ids": [i.id for i in incidents],
    }


@router.get("/cybertrap/intel/patterns")
def get_threat_patterns(db: Session = Depends(get_db)):
    from backend.app.services.cybertrap.threat_intelligence import ThreatIntelligenceEngine
    return ThreatIntelligenceEngine.get_threat_patterns(db)


@router.get("/cybertrap/intel/metrics")
def get_detection_metrics(db: Session = Depends(get_db)):
    from backend.app.services.cybertrap.threat_intelligence import ThreatIntelligenceEngine
    return ThreatIntelligenceEngine.get_detection_metrics(db)
