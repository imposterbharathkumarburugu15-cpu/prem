import hashlib
import json
import uuid
from typing import Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.services.cybertrap.honeypot_service import honeypot_service
from backend.app.schemas.cybertrap import (
    DecoyLoginRequest,
    DecoyLoginResponse,
    HoneyBatchItem,
    HoneyBatchListResponse,
    DecoyAdminExportRequest,
    DecoyAdminExportResponse,
    CanaryTokenValidateResponse,
    CyberTrapEventResponse,
    CyberTrapEventListResponse,
)

router = APIRouter(tags=["CyberTrap Decoys"])


@router.post("/cybertrap/decoys/auth/login", response_model=DecoyLoginResponse, status_code=status.HTTP_401_UNAUTHORIZED)
async def decoy_login(
    request: Request,
    db: Session = Depends(get_db),
):
    """Decoy Login Honeypot.
    
    Mimics credential checking and captures unauthorized authentication attempts.
    Always returns a realistic 401 Unauthorized while silently recording forensics.
    Accepts arbitrary non-JSON, binary, or structured payloads safely.
    """
    raw_bytes = await request.body()
    decoded_str = raw_bytes.decode("utf-8", errors="replace")[:4000]
    payload_data = None
    if raw_bytes:
        try:
            payload_data = json.loads(decoded_str)
        except Exception:
            payload_data = decoded_str

    event = honeypot_service.log_interaction(
        db=db,
        request=request,
        decoy_id="DECOY-AUTH-LOGIN",
        decoy_type="API_ENDPOINT",
        payload=payload_data,
    )

    req_id = f"req_auth_{uuid.uuid4().hex[:8]}"
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=DecoyLoginResponse(
            status="error",
            error_code="INVALID_CREDENTIALS",
            message="Authentication failed for identity provider: LDAP_PRM_SECURE",
            retry_remaining=2,
            request_id=req_id,
        ).model_dump(),
        headers={"X-Praman-Request-ID": req_id},
    )


@router.get("/cybertrap/decoys/batches", response_model=HoneyBatchListResponse)
def get_decoy_batches(
    request: Request,
    db: Session = Depends(get_db),
):
    """Decoy Honey-Batches Catalog.
    
    Exposes high-value synthetic crop records embedded with canary honeytokens.
    Strictly isolated from genuine production batches.
    """
    honeypot_service.log_interaction(
        db=db,
        request=request,
        decoy_id="DECOY-BATCHES-CATALOG",
        decoy_type="HONEY_BATCH",
    )

    batches = honeypot_service.get_decoy_batches(db)
    items = [honeypot_service.to_honey_batch_item(b) for b in batches]

    return HoneyBatchListResponse(
        batches=items,
        total=len(items),
        system_status="ONLINE",
        disclaimer="PRAMAN Provenance System - Verified Records Catalog",
    )


@router.get("/cybertrap/decoys/batches/{batch_id}", response_model=HoneyBatchItem)
def get_decoy_batch_detail(
    batch_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Decoy Honey-Batch Access.
    
    Increments access count and triggers honeytoken alerts upon probe.
    """
    batch = honeypot_service.get_decoy_batch_by_id(db, batch_id)
    if not batch:
        honeypot_service.log_interaction(
            db=db,
            request=request,
            decoy_id=f"DECOY-BATCH-NOT-FOUND-{batch_id[:40]}",
            decoy_type="HONEY_BATCH",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch record '{batch_id}' not found in registry",
        )

    honeypot_service.increment_batch_access(db, batch)
    honeypot_service.log_interaction(
        db=db,
        request=request,
        decoy_id=f"DECOY-BATCH-{batch.id}",
        decoy_type="HONEY_BATCH",
        is_honeytoken_triggered=True,
        honeytoken_id=batch.honeytoken_secret,
    )

    return honeypot_service.to_honey_batch_item(batch)


@router.post("/cybertrap/decoys/admin/export", response_model=DecoyAdminExportResponse)
async def decoy_admin_export(
    request: Request,
    db: Session = Depends(get_db),
):
    """Decoy Admin Database Export Honeypot.
    
    Mimics database backup / export probe and returns simulated archives with canary tokens.
    Accepts arbitrary non-JSON, binary, or structured payloads safely.
    """
    raw_bytes = await request.body()
    decoded_str = raw_bytes.decode("utf-8", errors="replace")[:4000]
    payload_data = None
    tables = ["batches", "audit_logs", "users"]
    if raw_bytes:
        try:
            payload_data = json.loads(decoded_str)
            if isinstance(payload_data, dict) and "tables" in payload_data and isinstance(payload_data["tables"], list):
                tables = [str(t) for t in payload_data["tables"]]
        except Exception:
            payload_data = decoded_str

    canary_token = honeypot_service.generate_honeytoken("prm_trap_exp_admin")

    honeypot_service.log_interaction(
        db=db,
        request=request,
        decoy_id="DECOY-ADMIN-EXPORT",
        decoy_type="ADMIN_PORTAL",
        payload=payload_data,
        is_honeytoken_triggered=True,
        honeytoken_id=canary_token,
    )

    job_id = f"job_exp_{uuid.uuid4().hex[:8]}"

    return DecoyAdminExportResponse(
        status="completed",
        export_job_id=job_id,
        exported_tables=tables,
        record_count=1420,
        download_url=f"/api/v1/cybertrap/decoys/admin/export/download/{job_id}.tar.gz",
        archive_checksum=hashlib.sha256(f"praman_archive_{job_id}".encode()).hexdigest(),
        internal_access_token=canary_token,
    )


@router.get("/cybertrap/decoys/tokens/validate", response_model=CanaryTokenValidateResponse)
def validate_canary_token(
    token: str = Query(..., description="Token to validate"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Canary Token Validator Endpoint.
    
    Validates tokens and triggers canary alerts when decoy tokens are used.
    """
    is_canary = honeypot_service.is_honeytoken(token)

    honeypot_service.log_interaction(
        db=db,
        request=request,
        decoy_id="DECOY-TOKEN-VALIDATE",
        decoy_type="HONEYTOKEN",
        is_honeytoken_triggered=is_canary,
        honeytoken_id=token if is_canary else None,
    )

    return CanaryTokenValidateResponse(
        valid=True,
        token=token,
        token_type="INTERNAL_CANARY" if is_canary else "STANDARD_BEARER",
        scope=["praman:internal:readonly", "praman:telemetry:write"],
        status="ACTIVE",
        message="Token is active within PRAMAN internal federation",
    )


@router.get("/cybertrap/events", response_model=CyberTrapEventListResponse)
def list_interaction_events(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    decoy_id: Optional[str] = Query(None),
    source_ip: Optional[str] = Query(None),
    is_honeytoken_triggered: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """List raw interaction events logged by CyberTrap honeypots (Admin only)."""
    events, total = honeypot_service.get_events(
        db=db,
        limit=limit,
        offset=offset,
        decoy_id=decoy_id,
        source_ip=source_ip,
        is_honeytoken_triggered=is_honeytoken_triggered,
    )

    return CyberTrapEventListResponse(
        events=events,
        total=total,
        limit=limit,
        offset=offset,
    )


# =========================================================================
# INTUITIVE PROBE ALIASES
# Decoys mounted at intuitive attack probe paths commonly scanned by adversaries
# =========================================================================

@router.api_route("/admin/export-database", methods=["GET", "POST"])
async def probe_admin_export_database(
    request: Request,
    db: Session = Depends(get_db),
):
    """Probe Decoy: /api/v1/admin/export-database.
    
    Attracts reconnaissance scanners probing for administrative database exports.
    """
    payload_data = None
    try:
        payload_data = await request.json()
    except Exception:
        pass

    canary_token = honeypot_service.generate_honeytoken("prm_trap_db_admin")

    honeypot_service.log_interaction(
        db=db,
        request=request,
        decoy_id="PROBE-ADMIN-EXPORT-DB",
        decoy_type="ADMIN_PORTAL",
        payload=payload_data,
        is_honeytoken_triggered=True,
        honeytoken_id=canary_token,
    )

    return {
        "status": "ready",
        "archive": "praman_prod_backup_latest.sql.gz",
        "size_bytes": 104857600,
        "digest_sha256": hashlib.sha256(b"praman_db_dump").hexdigest(),
        "internal_access_token": canary_token,
        "schema_version": "3.4.1",
        "table_count": 26,
    }


@router.api_route("/auth/internal-tokens", methods=["GET", "POST"])
async def probe_auth_internal_tokens(
    request: Request,
    db: Session = Depends(get_db),
):
    """Probe Decoy: /api/v1/auth/internal-tokens.
    
    Attracts credential-harvesting tools probing for internal service tokens.
    """
    canary_1 = honeypot_service.generate_honeytoken("prm_trap_svc_master")
    canary_2 = honeypot_service.generate_honeytoken("prm_trap_svc_sync")

    honeypot_service.log_interaction(
        db=db,
        request=request,
        decoy_id="PROBE-AUTH-INTERNAL-TOKENS",
        decoy_type="HONEYTOKEN",
        is_honeytoken_triggered=True,
        honeytoken_id=canary_1,
    )

    return {
        "federation": "PRAMAN_INTERNAL_KMS",
        "active_tokens": [
            {
                "service": "ledger-bridge-service",
                "token": canary_1,
                "role": "SYSTEM_ADMIN",
                "expires_in_seconds": 86400,
            },
            {
                "service": "evidence-sync-agent",
                "token": canary_2,
                "role": "EVIDENCE_COLLECTOR",
                "expires_in_seconds": 86400,
            },
        ],
    }


@router.get("/evidence/raw-cas-dump")
def probe_evidence_raw_cas_dump(
    request: Request,
    db: Session = Depends(get_db),
):
    """Probe Decoy: /api/v1/evidence/raw-cas-dump.
    
    Attracts data-exfiltration tools probing for raw content-addressable storage.
    """
    canary_ref = honeypot_service.generate_honeytoken("prm_trap_cas_raw")

    honeypot_service.log_interaction(
        db=db,
        request=request,
        decoy_id="PROBE-EVIDENCE-CAS-DUMP",
        decoy_type="API_ENDPOINT",
        is_honeytoken_triggered=True,
        honeytoken_id=canary_ref,
    )

    return {
        "status": "ONLINE",
        "total_nodes": 1280,
        "storage_engine": "RFC-8785-CAS",
        "sample_artifacts": [
            {
                "sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
                "content_type": "image/jpeg",
                "canary_token": canary_ref,
            },
            {
                "sha256": "8a339911e2cc4ea50a5e773e37530c91a3c010c2ec217ba97a4420ebbbcaa97b",
                "content_type": "application/json",
                "canary_token": honeypot_service.generate_honeytoken("prm_trap_cas_node"),
            },
        ],
    }
