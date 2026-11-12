import json
import logging
import time
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("praman.cybertrap.middleware")


class CyberTrapDefensiveMiddleware(BaseHTTPMiddleware):
    """Adaptive defensive ASGI middleware for CyberTrap.
    
    Dynamically enforces active human-approved security rules:
    - IP Quarantine: HTTP 403 Forbidden for quarantined adversaries.
    - Rate Limiting: HTTP 429 Too Many Requests when request limits are exceeded.
    - Header Block: HTTP 403 Forbidden when malicious signatures or headers are present.
    
    Features high-performance in-memory caching of active rules refreshed
    on rule approvals/activations.
    """

    _cached_rules: Optional[List[Dict[str, Any]]] = None
    _last_cache_time: float = 0.0
    _cache_ttl_seconds: float = 30.0
    _rate_limit_history: Dict[str, List[float]] = defaultdict(list)
    _quarantined_ips: Set[str] = set()

    WHITELISTED_PATHS = {
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/health",
        "/health",
        "/favicon.ico",
    }

    @classmethod
    def invalidate_cache(cls):
        """Forces immediate invalidation of the cached active defensive rules."""
        cls._cached_rules = None
        cls._last_cache_time = 0.0
        cls._quarantined_ips.clear()

    @classmethod
    def reload_active_rules(cls, rules: Optional[List[Any]] = None):
        """Explicitly reloads active rules into memory cache."""
        if rules is None:
            try:
                from backend.app.core.database import SessionLocal
                from backend.app.models.cybertrap import CyberTrapRule
                db = SessionLocal()
                try:
                    db_rules = (
                        db.query(CyberTrapRule)
                        .filter(CyberTrapRule.status == "ACTIVE")
                        .all()
                    )
                    cached = []
                    cls._quarantined_ips.clear()
                    for r in db_rules:
                        params = {}
                        try:
                            params = json.loads(r.parameters_json or "{}")
                        except Exception:
                            params = {}
                        cached.append({
                            "id": r.id,
                            "rule_type": r.rule_type,
                            "target_value": r.target_value,
                            "parameters": params,
                        })
                        if r.rule_type == "IP_QUARANTINE":
                            cls._quarantined_ips.add(r.target_value)
                    cls._cached_rules = cached
                    cls._last_cache_time = time.time()
                finally:
                    db.close()
            except Exception as e:
                logger.warning(f"Could not reload active rules from DB: {e}")
                if cls._cached_rules is None:
                    cls._cached_rules = []
        else:
            cls._cached_rules = []
            cls._quarantined_ips.clear()
            for r in rules:
                params = getattr(r, "parameters_json", None)
                if isinstance(params, str):
                    try:
                        params = json.loads(params)
                    except Exception:
                        params = {}
                elif not isinstance(params, dict):
                    params = getattr(r, "parameters", {})

                rule_dict = {
                    "id": getattr(r, "id", "rule_temp"),
                    "rule_type": getattr(r, "rule_type", ""),
                    "target_value": getattr(r, "target_value", ""),
                    "parameters": params or {},
                }
                cls._cached_rules.append(rule_dict)
                if rule_dict["rule_type"] == "IP_QUARANTINE":
                    cls._quarantined_ips.add(rule_dict["target_value"])
            cls._last_cache_time = time.time()

    @classmethod
    def get_client_ip(cls, request: Request) -> str:
        """Extracts client IP address safely, checking X-Forwarded-For and X-Real-IP."""
        xff = request.headers.get("x-forwarded-for")
        if xff:
            client_ip = xff.split(",")[0].strip()
            if client_ip:
                return client_ip
        x_real_ip = request.headers.get("x-real-ip")
        if x_real_ip and x_real_ip.strip():
            return x_real_ip.strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Whitelist internal and documentation paths
        if path in self.WHITELISTED_PATHS or path.startswith("/static") or path.startswith("/assets"):
            return await call_next(request)

        # Refresh rules if cache is expired or missing
        now = time.time()
        if self._cached_rules is None or (now - self._last_cache_time) > self._cache_ttl_seconds:
            self.reload_active_rules()

        active_rules = self._cached_rules or []
        client_ip = self.get_client_ip(request)

        # 1. Enforcement Check: IP Quarantine
        if client_ip in self._quarantined_ips:
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Forbidden",
                    "detail": "Access denied: IP address is quarantined under active CyberTrap security policy.",
                    "client_ip": client_ip,
                },
            )

        for rule in active_rules:
            rule_type = rule["rule_type"]
            target = rule["target_value"]
            params = rule.get("parameters", {})

            # IP Quarantine match
            if rule_type == "IP_QUARANTINE" and target == client_ip:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Forbidden",
                        "detail": f"Access denied: IP {client_ip} is quarantined by CyberTrap rule {rule['id']}.",
                        "rule_id": rule["id"],
                    },
                )

            # Header Block match
            if rule_type == "HEADER_BLOCK":
                target_header = params.get("target_header", "X-Forwarded-For")
                pattern = params.get("pattern", target)
                header_val = request.headers.get(target_header.lower(), "")
                if pattern and pattern in header_val:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": "Forbidden",
                            "detail": f"Request blocked: suspicious header match for rule {rule['id']}.",
                            "rule_id": rule["id"],
                        },
                    )

            # Rate Limit match
            if rule_type == "RATE_LIMIT" and (target == client_ip or target == "*"):
                max_reqs = params.get("max_requests_per_minute", 10)
                window_sec = params.get("window_seconds", 60)

                history = self._rate_limit_history[client_ip]
                # Filter out timestamps older than window
                cutoff = now - window_sec
                recent = [ts for ts in history if ts >= cutoff]

                if len(recent) >= max_reqs:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "Too Many Requests",
                            "detail": f"Rate limit exceeded: maximum {max_reqs} requests per {window_sec}s allowed.",
                            "rule_id": rule["id"],
                            "retry_after_seconds": int(window_sec - (now - recent[0])) if recent else window_sec,
                        },
                        headers={"Retry-After": str(window_sec)},
                    )

                recent.append(now)
                self._rate_limit_history[client_ip] = recent

        # Proceed with request
        response = await call_next(request)
        return response
