from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.services.cybertrap.cybertrap_audit import CyberTrapLedgerAuditor

router = APIRouter(prefix="/cybertrap/audit", tags=["CyberTrap Blockchain & Ledger Audit"])


@router.post("/incidents/{incident_id}/anchor")
def anchor_incident_report(
    incident_id: str,
    db: Session = Depends(get_db),
):
    """Anchors incident cryptographic SHA-256 hash to the tamper-evident ledger."""
    try:
        receipt = CyberTrapLedgerAuditor.anchor_incident_to_ledger(db=db, incident_id=incident_id)
        return receipt
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/incidents/{incident_id}/verify")
def verify_incident_report(
    incident_id: str,
    db: Session = Depends(get_db),
):
    """Verifies cryptographic integrity of an incident report against the ledger."""
    try:
        verification = CyberTrapLedgerAuditor.verify_incident_integrity(db=db, incident_id=incident_id)
        return verification
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/trail")
def get_security_audit_trail(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retrieves immutable audit chain entries for cybersecurity intelligence."""
    items = CyberTrapLedgerAuditor.get_security_audit_trail(db=db, limit=limit)
    return {"total": len(items), "items": items}

