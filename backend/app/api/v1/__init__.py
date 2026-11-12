from fastapi import APIRouter
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.farmers import router as farmers_router
from backend.app.api.v1.devices import router as devices_router
from backend.app.api.v1.farms import router as farms_router
from backend.app.api.v1.evidence import router as evidence_router
from backend.app.api.v1.audit import router as audit_router
from backend.app.api.v1.reviewer import router as reviewer_router
from backend.app.api.v1.verify import router as verify_router
from backend.app.api.v1.merkle import router as merkle_router
from backend.app.api.v1.platform import router as platform_router
from backend.app.api.v1.events import router as events_router
from backend.app.api.v1.cybertrap_decoys import router as cybertrap_decoys_router
from backend.app.api.v1.cybertrap_intel import router as cybertrap_intel_router
from backend.app.api.v1.cybertrap_rules import router as cybertrap_rules_router
from backend.app.api.v1.cybertrap_feedback import router as cybertrap_feedback_router
from backend.app.api.v1.cybertrap_audit import router as cybertrap_audit_router

api_router = APIRouter()
# CyberTrap decoys included first so specific decoy probe routes (e.g. /evidence/raw-cas-dump)
# take precedence over generic parameterized routes (e.g. /evidence/{evidence_id})
api_router.include_router(cybertrap_decoys_router)
api_router.include_router(cybertrap_intel_router)
api_router.include_router(cybertrap_rules_router)
api_router.include_router(cybertrap_feedback_router)
api_router.include_router(cybertrap_audit_router)
api_router.include_router(health_router)
api_router.include_router(farmers_router)
api_router.include_router(devices_router)
api_router.include_router(farms_router)
api_router.include_router(evidence_router)
api_router.include_router(audit_router)
api_router.include_router(reviewer_router)
api_router.include_router(verify_router)
api_router.include_router(merkle_router)
api_router.include_router(platform_router)
api_router.include_router(events_router)
