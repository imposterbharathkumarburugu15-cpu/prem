import base64
import json
from typing import Any, Dict, List, Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Header,
    Request,
    Response,
    UploadFile,
    File,
    Form,
    Query,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.supply_chain import BusinessEvent, Batch
from backend.app.models.user_org import User
from backend.app.services.event_engine import event_engine, BusinessEventType, normalize_role
from backend.app.api.v1.platform import get_current_user_optional

router = APIRouter(prefix="/events", tags=["Business Events & Evidence Policies"])


class EventRecordRequest(BaseModel):
    event_type: str = Field(..., description="One of the 17 supply chain business event types")
    payload: Dict[str, Any] = Field(..., description="Business payload fields for the event")
    actor_id: Optional[str] = Field(None, description="Optional actor user ID (defaults to authenticated user)")
    actor_role: Optional[str] = Field(None, description="Optional actor role (defaults to authenticated user role)")
    organization_id: Optional[str] = Field(None, description="Optional tenant organization ID")
    image_b64: Optional[str] = Field(None, description="Optional base64-encoded supporting evidence file")
    filename: Optional[str] = Field(None, description="Optional file name")


@router.get("/policies", response_model=Dict[str, Any])
def get_all_policies():
    """Returns explicit evidence policies for all 17 supply chain business events.
    Includes required business fields, automatically captured metadata,
    optional vs mandatory supporting evidence rules, and verification procedures.
    """
    return event_engine.get_policies()


@router.get("/policies/{event_type}", response_model=Dict[str, Any])
def get_policy_by_type(event_type: str):
    """Returns the evidence policy for a specific supply chain business event."""
    policy = event_engine.get_policy(event_type)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence policy for event type '{event_type}' not found",
        )
    return policy


@router.post("/record", status_code=status.HTTP_201_CREATED)
async def record_business_event(
    request: Request,
    db: Session = Depends(get_db),
    # Multipart Form inputs
    event_type: Optional[str] = Form(None),
    payload: Optional[str] = Form(None),
    actor_id: Optional[str] = Form(None),
    actor_role: Optional[str] = Form(None),
    organization_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    # HTTP Headers
    authorization: Optional[str] = Header(None),
    x_actor_id: Optional[str] = Header(None, alias="X-Actor-ID"),
    x_actor_role: Optional[str] = Header(None, alias="X-Actor-Role"),
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-ID"),
):
    """Records a supply-chain business event with automatic evidence policy application,
    cryptographic envelope generation, verification procedures, and batch/shipment state updates.
    Supports both JSON and Multipart Form submissions.
    """
    # 1. Resolve Authenticated User if present
    current_user: Optional[User] = get_current_user_optional(authorization, db)

    parsed_event_type = event_type
    parsed_payload: Dict[str, Any] = {}
    parsed_actor_id = actor_id or x_actor_id
    parsed_actor_role = actor_role or x_actor_role
    parsed_org_id = organization_id or x_organization_id
    file_bytes: Optional[bytes] = None
    file_name: Optional[str] = None

    upload_file = file or image

    # 2. Handle Multipart Form Submission
    if parsed_event_type is not None:
        if payload:
            try:
                parsed_payload = json.loads(payload)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Payload field must be valid JSON: {e}",
                )
        if upload_file is not None:
            file_bytes = await upload_file.read()
            file_name = upload_file.filename

    # 3. Handle JSON Body Submission
    else:
        try:
            body = await request.json()
            parsed_event_type = body.get("event_type")
            parsed_payload = body.get("payload") or {}
            if not parsed_actor_id:
                parsed_actor_id = body.get("actor_id")
            if not parsed_actor_role:
                parsed_actor_role = body.get("actor_role")
            if not parsed_org_id:
                parsed_org_id = body.get("organization_id")
            raw_b64 = body.get("image_b64") or body.get("file_b64")
            if raw_b64:
                file_bytes = base64.b64decode(raw_b64)
                file_name = body.get("filename", "evidence_upload.bin")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid request body format: {e}",
            )

    if not parsed_event_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field 'event_type' is required",
        )

    # 4. Resolve Actor Identity & Role defaults
    if current_user:
        if not parsed_actor_id:
            parsed_actor_id = current_user.id
        if not parsed_actor_role:
            parsed_actor_role = current_user.role
        if not parsed_org_id:
            parsed_org_id = current_user.organization_id

    # Fallback default if not authenticated
    if not parsed_actor_id:
        parsed_actor_id = "actor-system"
    if not parsed_actor_role:
        # Default role according to event type policy if unspecified
        policy = event_engine.get_policy(parsed_event_type)
        if policy and policy.get("allowed_roles"):
            parsed_actor_role = policy["allowed_roles"][0]
        else:
            parsed_actor_role = "ADMIN"

    # 5. Capture Automated Metadata from Client Headers
    client_meta = {
        "client_ip": request.client.host if request.client else "127.0.0.1",
        "user_agent": request.headers.get("user-agent", "Unknown-Client"),
        "device_id": request.headers.get("x-device-id"),
        "device_model": request.headers.get("x-device-model"),
        "app_version": request.headers.get("x-app-version"),
    }

    # 6. Execute Event Engine
    result = event_engine.record_event(
        db=db,
        event_type=parsed_event_type,
        payload=parsed_payload,
        actor_id=parsed_actor_id,
        actor_role=parsed_actor_role,
        organization_id=parsed_org_id,
        file_bytes=file_bytes,
        file_filename=file_name,
        client_metadata=client_meta,
    )

    return result


@router.get("/batch/{batch_id}/timeline")
def get_batch_timeline(
    batch_id: str,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    """Returns the single chronological supply chain timeline for a batch.
    Includes all business events, linked shipments, inspections, weighings,
    and cryptographic evidence with multi-tenant access control.
    """
    current_user: Optional[User] = get_current_user_optional(authorization, db)
    return event_engine.get_batch_timeline(
        db=db,
        batch_id=batch_id,
        current_user=current_user,
    )


@router.get("/{event_id}")
def get_event_by_id(
    event_id: str,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    """Retrieves a single business event by ID."""
    ev = db.query(BusinessEvent).filter(BusinessEvent.id == event_id).first()
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business event '{event_id}' not found",
        )
    return {
        "event_id": ev.id,
        "event_type": ev.event_type,
        "batch_id": ev.batch_id,
        "shipment_id": ev.shipment_id,
        "farm_id": ev.farm_id,
        "organization_id": ev.organization_id,
        "actor_id": ev.actor_id,
        "actor_role": ev.actor_role,
        "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
        "payload": json.loads(ev.payload_json or "{}"),
        "metadata": json.loads(ev.metadata_json or "{}"),
        "evidence_id": ev.evidence_id,
        "evidence_hash": ev.evidence_hash,
        "verification_status": ev.verification_status,
        "verification_details": json.loads(ev.verification_details_json or "{}"),
        "created_at": ev.created_at.isoformat() if ev.created_at else None,
    }


@router.get("")
def list_business_events(
    batch_id: Optional[str] = Query(None),
    shipment_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    """Lists business events with optional filters and multi-tenant scoping."""
    current_user: Optional[User] = get_current_user_optional(authorization, db)
    query = db.query(BusinessEvent)

    # Multi-tenant scoping if user is tenant-restricted
    if current_user and current_user.role not in ("ADMIN", "EVIDENCE_INTEGRITY_OFFICER"):
        if current_user.organization_id:
            query = query.filter(
                (BusinessEvent.organization_id == current_user.organization_id)
                | (BusinessEvent.actor_id == current_user.id)
            )

    if batch_id:
        query = query.filter(BusinessEvent.batch_id == batch_id)
    if shipment_id:
        query = query.filter(BusinessEvent.shipment_id == shipment_id)
    if event_type:
        query = query.filter(BusinessEvent.event_type == event_type)

    total = query.count()
    events = query.order_by(BusinessEvent.timestamp.desc()).offset(offset).limit(limit).all()

    items = []
    for ev in events:
        items.append({
            "event_id": ev.id,
            "event_type": ev.event_type,
            "batch_id": ev.batch_id,
            "shipment_id": ev.shipment_id,
            "farm_id": ev.farm_id,
            "organization_id": ev.organization_id,
            "actor_id": ev.actor_id,
            "actor_role": ev.actor_role,
            "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
            "payload": json.loads(ev.payload_json or "{}"),
            "evidence_hash": ev.evidence_hash,
            "verification_status": ev.verification_status,
        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "events": items,
    }
