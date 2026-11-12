import json
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.cybertrap import CyberTrapRule
from backend.app.services.cybertrap.adaptive_feedback import AdaptiveFeedbackEngine

router = APIRouter(prefix="/cybertrap/feedback", tags=["CyberTrap Adaptive Feedback"])


class ApproveRuleRequest(BaseModel):
    approved_by: str = Field("Cybersecurity Administrator (Dr. K. Rao)", description="Name/Role of approving human authority")


class RejectRuleRequest(BaseModel):
    rejected_by: str = Field("Cybersecurity Administrator", description="Name/Role of rejecting authority")
    rejection_reason: str = Field("Requires manual network inspection", description="Justification for rejecting rule")


class CheckRequestPayload(BaseModel):
    source_ip: str
    path: str = "/api/v1/cybertrap/decoys/auth/login"


@router.get("/rules")
def list_defensive_rules(
    status: Optional[str] = None,
    rule_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Lists all adaptive defensive rules across their lifecycle stages."""
    query = db.query(CyberTrapRule)
    if status:
        query = query.filter(CyberTrapRule.status == status)
    if rule_type:
        query = query.filter(CyberTrapRule.rule_type == rule_type)

    rules = query.order_by(CyberTrapRule.created_at.desc()).all()
    res = []
    for r in rules:
        params = {}
        staging_res = {}
        try:
            params = json.loads(r.parameters_json or "{}")
        except Exception:
            params = {}
        try:
            staging_res = json.loads(r.staging_validation_results or "{}")
        except Exception:
            staging_res = {}

        res.append({
            "id": r.id,
            "incident_id": r.incident_id,
            "rule_type": r.rule_type,
            "target_value": r.target_value,
            "parameters": params,
            "status": r.status,
            "proposed_by": r.proposed_by,
            "approved_by": r.approved_by,
            "approved_at": r.approved_at.isoformat() if r.approved_at else None,
            "rejection_reason": r.rejection_reason,
            "staging_validation": staging_res,
            "version": r.version,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        })
    return {"total": len(res), "items": res}


@router.post("/rules/generate")
def generate_rule_proposals(db: Session = Depends(get_db)):
    """Generates defensive rule proposals from actionable threat incidents."""
    rules = AdaptiveFeedbackEngine.generate_defensive_proposals(db)
    return {
        "status": "COMPLETED",
        "generated_count": len(rules),
        "rule_ids": [r.id for r in rules],
    }


@router.post("/rules/{rule_id}/approve")
def approve_rule(
    rule_id: str,
    payload: ApproveRuleRequest = ApproveRuleRequest(),
    db: Session = Depends(get_db),
):
    """Human authority approves a proposed rule (PROPOSED -> APPROVED)."""
    try:
        rule = AdaptiveFeedbackEngine.approve_rule(
            db=db,
            rule_id=rule_id,
            approved_by=payload.approved_by,
        )
        return {"status": "SUCCESS", "rule_id": rule.id, "new_status": rule.status}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/rules/{rule_id}/validate-staging")
def validate_staging_rule(
    rule_id: str,
    db: Session = Depends(get_db),
):
    """Executes staging dry-run validation (APPROVED -> STAGING_VALIDATED)."""
    try:
        rule = AdaptiveFeedbackEngine.validate_staging(
            db=db,
            rule_id=rule_id,
        )
        return {
            "status": "SUCCESS",
            "rule_id": rule.id,
            "new_status": rule.status,
            "validation_results": json.loads(rule.staging_validation_results or "{}"),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/rules/{rule_id}/deploy")
def deploy_rule(
    rule_id: str,
    deployed_by: str = Query("Platform Administrator"),
    db: Session = Depends(get_db),
):
    """Activates validated rule into production enforcement (STAGING_VALIDATED -> ACTIVE)."""
    try:
        rule = AdaptiveFeedbackEngine.deploy_rule(
            db=db,
            rule_id=rule_id,
            deployed_by=deployed_by,
        )
        return {"status": "SUCCESS", "rule_id": rule.id, "new_status": rule.status, "version": rule.version}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/rules/{rule_id}/reject")
def reject_rule(
    rule_id: str,
    payload: RejectRuleRequest = RejectRuleRequest(),
    db: Session = Depends(get_db),
):
    """Explicitly rejects a defensive rule with logged justification."""
    try:
        rule = AdaptiveFeedbackEngine.reject_rule(
            db=db,
            rule_id=rule_id,
            rejected_by=payload.rejected_by,
            rejection_reason=payload.rejection_reason,
        )
        return {"status": "SUCCESS", "rule_id": rule.id, "new_status": rule.status}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/check")
def check_request(
    payload: CheckRequestPayload,
    db: Session = Depends(get_db),
):
    """Evaluates whether an IP/path is blocked or throttled by an active defense rule."""
    match = AdaptiveFeedbackEngine.check_request_against_active_rules(
        db=db,
        source_ip=payload.source_ip,
        path=payload.path,
    )
    if match:
        return {"allowed": False, "enforcement": match}
    return {"allowed": True, "enforcement": None}

