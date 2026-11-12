import json
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.cybertrap import CyberTrapEvent, CyberTrapIncident
from backend.app.services.cybertrap.threat_intelligence import ThreatIntelligenceEngine

router = APIRouter(prefix="/cybertrap/intel", tags=["CyberTrap Threat Intelligence"])


@router.get("/events")
def list_threat_events(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    decoy_type: Optional[str] = None,
    source_ip: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Retrieve raw logged honeypot interaction events."""
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


@router.get("/incidents")
def list_threat_incidents(
    status: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Retrieve categorized threat intelligence incidents."""
    query = db.query(CyberTrapIncident)
    if status:
        query = query.filter(CyberTrapIncident.status == status)
    if risk_level:
        query = query.filter(CyberTrapIncident.risk_level == risk_level)

    incidents = query.order_by(CyberTrapIncident.created_at.desc()).limit(limit).all()

    res = []
    for inc in incidents:
        explanation = {}
        try:
            explanation = json.loads(inc.explanation_json)
        except Exception:
            explanation = {"raw": inc.explanation_json}

        res.append({
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
        })
    return {"total": len(res), "items": res}


@router.post("/analyse")
def trigger_threat_analysis(
    lookback_minutes: int = Query(120, ge=5, le=1440),
    db: Session = Depends(get_db),
):
    """Triggers deterministic threat classification across recent events to update incidents."""
    result = ThreatIntelligenceEngine.analyse_events_and_generate_incidents(
        db=db,
        lookback_minutes=lookback_minutes,
    )
    return {
        "status": "COMPLETED",
        "analysis": result,
    }


@router.get("/patterns")
def get_threat_patterns(db: Session = Depends(get_db)):
    """Retrieve multi-dimensional pattern summaries and distributions."""
    return ThreatIntelligenceEngine.get_threat_patterns(db)


@router.get("/metrics")
def get_detection_metrics(db: Session = Depends(get_db)):
    """Quantitative detection performance and latency benchmarks."""
    return ThreatIntelligenceEngine.get_detection_metrics(db)

