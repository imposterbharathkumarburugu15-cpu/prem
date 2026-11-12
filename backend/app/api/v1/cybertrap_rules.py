import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Query, HTTPException, status, Response
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.cybertrap import CyberTrapRule
from backend.app.services.cybertrap.defense_service import DefenseService
from crypto.authority import sign_checkpoint

router = APIRouter(prefix="/cybertrap/rules", tags=["CyberTrap Defensive Rules"])


class RuleApprovalRequest(BaseModel):
    approved_by: str = Field(default="Platform/Cyber Administrator", description="Identity of approving human authority")


class RuleRejectionRequest(BaseModel):
    rejected_by: str = Field(default="Platform Administrator", description="Identity of rejecting authority")
    rejection_reason: str = Field(default="Administrative override", description="Reason for rejecting rule")


class StagingValidationRequest(BaseModel):
    rule_id: str = Field(..., description="ID of the rule to validate in staging sandbox")


def _format_rule(r: CyberTrapRule) -> Dict[str, Any]:
    params = {}
    staging = {}
    try:
        params = json.loads(r.parameters_json or "{}")
    except Exception:
        params = {}
    try:
        staging = json.loads(r.staging_validation_results or "{}")
    except Exception:
        staging = {}

    return {
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
        "staging_validation": staging,
        "version": r.version,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


@router.get("")
@router.get("/")
def list_defensive_rules(
    status: Optional[str] = None,
    rule_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Lists all adaptive defensive rules across their lifecycle stages."""
    query = db.query(CyberTrapRule)
    if status:
        query = query.filter(CyberTrapRule.status == status)
    if rule_type:
        query = query.filter(CyberTrapRule.rule_type == rule_type)

    total = query.count()
    rules = query.order_by(CyberTrapRule.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_format_rule(r) for r in rules],
    }


@router.post("/propose")
def propose_rules(db: Session = Depends(get_db)):
    """Generates defensive rule proposals from high-risk incidents."""
    rules = DefenseService.propose_rules_from_incidents(db)
    return {
        "status": "COMPLETED",
        "proposed_count": len(rules),
        "rules": [_format_rule(r) for r in rules],
    }


@router.post("/{rule_id}/approve")
def approve_rule(
    rule_id: str,
    payload: RuleApprovalRequest = RuleApprovalRequest(),
    db: Session = Depends(get_db),
):
    """Human authority approves a proposed rule (PROPOSED/STAGING_VALIDATED -> APPROVED/ACTIVE)."""
    try:
        rule = DefenseService.approve_rule(
            db=db,
            rule_id=rule_id,
            approved_by=payload.approved_by,
        )
        return {
            "status": "SUCCESS",
            "rule_id": rule.id,
            "new_status": rule.status,
            "version": rule.version,
            "approved_by": rule.approved_by,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{rule_id}/reject")
def reject_rule(
    rule_id: str,
    payload: RuleRejectionRequest = RuleRejectionRequest(),
    db: Session = Depends(get_db),
):
    """Rejects a rule proposal with explicit justification."""
    try:
        rule = DefenseService.reject_rule(
            db=db,
            rule_id=rule_id,
            rejected_by=payload.rejected_by,
            rejection_reason=payload.rejection_reason,
        )
        return {
            "status": "REJECTED",
            "rule_id": rule.id,
            "rejection_reason": rule.rejection_reason,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/validate-staging")
def validate_rule_staging(
    payload: StagingValidationRequest,
    db: Session = Depends(get_db),
):
    """Validates a rule inside the staging sandbox ensuring 0 false positives against legitimate farmers."""
    try:
        rule = DefenseService.validate_rule_in_staging(db=db, rule_id=payload.rule_id)
        return {
            "status": "STAGING_VALIDATED",
            "rule_id": rule.id,
            "staging_validation": json.loads(rule.staging_validation_results or "{}"),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/manifest")
def get_rules_manifest(
    response: Response,
    db: Session = Depends(get_db),
):
    """Returns an Authority NIST P-256 signed manifest of all active rules for edge caching and sync."""
    active_rules = DefenseService.get_active_rules(db)
    max_ver = max([r.version for r in active_rules], default=1)
    
    rules_payload = []
    for r in active_rules:
        params = {}
        try:
            params = json.loads(r.parameters_json or "{}")
        except Exception:
            params = {}
        rules_payload.append({
            "rule_id": r.id,
            "rule_type": r.rule_type,
            "target_value": r.target_value,
            "parameters": params,
            "version": r.version,
        })

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = {
        "manifest_version": max_ver,
        "timestamp": timestamp,
        "active_rule_count": len(rules_payload),
        "rules": rules_payload,
        "authority_id": "praman-root-authority-1",
    }

    # Sign manifest with NIST P-256 ECDSA over RFC 8785 canonical bytes
    signature = sign_checkpoint(manifest)
    manifest["signature"] = signature

    # Set version header for edge cache validation
    response.headers["X-Praman-Rule-Version"] = str(max_ver)
    return manifest
