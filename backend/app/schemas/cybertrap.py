from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class DecoyLoginRequest(BaseModel):
    """Payload submitted to the decoy login honeypot."""
    model_config = ConfigDict(extra="allow")

    username: Optional[str] = Field(default=None, description="Username or email probe")
    password: Optional[str] = Field(default=None, description="Password probe")
    token: Optional[str] = Field(default=None, description="Canary or stolen token probe")
    client_id: Optional[str] = Field(default=None, description="OAuth client ID")
    grant_type: Optional[str] = Field(default="password", description="Authentication grant type")
    extra: Optional[Dict[str, Any]] = Field(default=None, description="Additional arbitrary payload fields")


class DecoyLoginResponse(BaseModel):
    """Realistic-looking error response returned by the decoy login honeypot."""
    status: str = Field(default="error")
    error_code: str = Field(default="INVALID_CREDENTIALS")
    message: str = Field(default="Authentication failed for identity provider: LDAP_PRM_SECURE")
    retry_remaining: int = Field(default=2)
    request_id: str = Field(default="req_sec_unknown")


class HoneyBatchItem(BaseModel):
    """Public representation of a synthetic honey-batch record."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Batch code e.g. BATCH-HONEY-SAFFRON-001")
    crop_type: str = Field(..., description="Tempting crop type e.g. Saffron")
    variety: Optional[str] = Field(default=None)
    declared_quantity: float = Field(...)
    unit: str = Field(default="kg")
    canary_token: str = Field(..., description="Embedded honeytoken canary secret")
    synthetic_location: str = Field(...)
    quality_grade: str = Field(...)
    estimated_value_inr: float = Field(...)
    custodian_org: str = Field(...)
    access_count: int = Field(default=0)
    status: str = Field(default="ACTIVE")
    created_at: Optional[datetime] = None


class HoneyBatchListResponse(BaseModel):
    """Response containing list of synthetic honey-batches."""
    batches: List[HoneyBatchItem]
    total: int
    system_status: str = Field(default="ONLINE")
    disclaimer: str = Field(default="PRAMAN Provenance System - Verified Records Catalog")


class DecoyAdminExportRequest(BaseModel):
    """Payload probe submitted to the decoy admin export honeypot."""
    model_config = ConfigDict(extra="allow")

    format: str = Field(default="json", description="Export format: json, csv, sql")
    tables: List[str] = Field(default=["batches", "audit_logs", "users"])
    include_credentials: bool = Field(default=False)
    session_token: Optional[str] = Field(default=None)


class DecoyAdminExportResponse(BaseModel):
    """Simulated database export payload containing canary tokens."""
    status: str = Field(default="completed")
    export_job_id: str
    exported_tables: List[str]
    record_count: int
    download_url: str
    archive_checksum: str
    internal_access_token: str  # Canary honeytoken


class CanaryTokenValidateRequest(BaseModel):
    """Canary token validation probe."""
    token: str = Field(..., description="Token to validate")


class CanaryTokenValidateResponse(BaseModel):
    """Response for canary token validation."""
    valid: bool
    token: str
    token_type: str = Field(default="INTERNAL_CANARY")
    scope: List[str] = Field(default=["praman:internal:readonly"])
    status: str = Field(default="ACTIVE")
    message: str = Field(default="Token is active within PRAMAN internal federation")


class CyberTrapEventResponse(BaseModel):
    """Response model for a recorded honeypot interaction event."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    timestamp: datetime
    decoy_id: str
    decoy_type: str
    request_method: str
    request_path: str
    source_ip: str
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    is_honeytoken_triggered: bool
    honeytoken_id: Optional[str] = None
    headers_json: Optional[str] = None
    payload_json: Optional[str] = None
    query_params_json: Optional[str] = None


class CyberTrapEventListResponse(BaseModel):
    """Paginated list of honeypot interaction events."""
    events: List[CyberTrapEventResponse]
    total: int
    limit: int
    offset: int


class DecoyInteractionReceipt(BaseModel):
    """Internal receipt confirming an interaction was captured."""
    logged: bool = True
    event_id: str
    decoy_id: str
    source_ip: str
    timestamp: datetime
