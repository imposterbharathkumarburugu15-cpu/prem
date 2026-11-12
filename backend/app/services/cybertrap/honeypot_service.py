import json
import re
import secrets
import urllib.parse
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from fastapi import Request
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.cybertrap import CyberTrapEvent, CyberTrapDecoyBatch
from backend.app.schemas.cybertrap import HoneyBatchItem

# Honeytoken matching pattern (e.g., prm_trap_saff_9941a8e2b)
HONEYTOKEN_REGEX = re.compile(r"prm_trap_[a-zA-Z0-9_\-]+")

# Built-in synthetic honey-batch seeds
DEFAULT_DECOY_BATCHES: List[Dict[str, Any]] = [
    {
        "id": "BATCH-HONEY-SAFFRON-001",
        "crop_type": "Saffron",
        "variety": "Super Negin Grade 1",
        "declared_quantity": 250.0,
        "unit": "kg",
        "honeytoken_secret": "prm_trap_saff_9941a8e2b",
        "synthetic_location": "Pampore High Altitude Saffron Station, Jammu & Kashmir",
        "quality_grade": "GRADE_AAA_RESERVE",
        "estimated_value_inr": 12500000.0,
        "custodian_org": "State Agri-Reserve Vault",
        "status": "ACTIVE",
    },
    {
        "id": "BATCH-HONEY-CARDAMOM-002",
        "crop_type": "Green Cardamom",
        "variety": "Alleppey Extra Bold 8mm",
        "declared_quantity": 1500.0,
        "unit": "kg",
        "honeytoken_secret": "prm_trap_card_7718c3d9e",
        "synthetic_location": "Idukki High Ranges Bio-Reserve, Kerala",
        "quality_grade": "GRADE_AAA_EXPORT",
        "estimated_value_inr": 4500000.0,
        "custodian_org": "South Spice Export Federation",
        "status": "ACTIVE",
    },
    {
        "id": "BATCH-HONEY-VANILLA-003",
        "crop_type": "Bourbon Vanilla",
        "variety": "Grade A Gourmet Black Pods",
        "declared_quantity": 300.0,
        "unit": "kg",
        "honeytoken_secret": "prm_trap_vani_1284f6a0b",
        "synthetic_location": "Western Ghats Agroforestry Station, Karnataka",
        "quality_grade": "GRADE_AAA_RESERVE",
        "estimated_value_inr": 2100000.0,
        "custodian_org": "Spices Board India - Reserve Division",
        "status": "ACTIVE",
    },
]


class HoneypotService:
    """Isolated CyberTrap Honeypot Service.
    
    CRITICAL ISOLATION GUARANTEE:
    This service operates strictly on `cybertrap_*` tables and synthetic datasets.
    It NEVER accesses or modifies genuine agricultural tables:
    - farmers
    - farms
    - devices
    - evidence
    - batches
    - shipments
    - actor_trust_scores
    """

    @staticmethod
    def generate_honeytoken(prefix: str = "prm_trap", length: int = 12) -> str:
        """Generate a random canary honeytoken with the standard prefix."""
        random_suffix = secrets.token_hex(length // 2)
        return f"{prefix}_{random_suffix}"

    @staticmethod
    def is_honeytoken(token: Optional[str]) -> bool:
        """Check if a string matches the canary honeytoken format."""
        if not token:
            return False
        return bool(HONEYTOKEN_REGEX.search(token))

    @staticmethod
    def extract_honeytokens(target: Any) -> List[str]:
        """Recursively scan an object (str, dict, list, set, bytes) for canary honeytokens.
        
        Applies urllib.parse.unquote() before regex matching to detect URL-encoded tokens,
        and adds default=str to json.dumps() to safely handle non-serializable objects.
        """
        if target is None:
            return []
        try:
            text_repr = json.dumps(target, default=str) if not isinstance(target, str) else target
        except Exception:
            text_repr = str(target)

        matches = set(HONEYTOKEN_REGEX.findall(text_repr))
        try:
            unquoted = urllib.parse.unquote(text_repr)
            matches.update(HONEYTOKEN_REGEX.findall(unquoted))
        except Exception:
            pass

        return list(matches)

    def seed_default_decoy_batches(self, db: Session) -> List[CyberTrapDecoyBatch]:
        """Seed initial synthetic honey-batch records if none exist."""
        existing_count = db.query(CyberTrapDecoyBatch).count()
        if existing_count > 0:
            return db.query(CyberTrapDecoyBatch).all()

        seeded_records = []
        for item in DEFAULT_DECOY_BATCHES:
            batch = CyberTrapDecoyBatch(
                id=item["id"],
                crop_type=item["crop_type"],
                variety=item["variety"],
                declared_quantity=item["declared_quantity"],
                unit=item["unit"],
                honeytoken_secret=item["honeytoken_secret"],
                synthetic_location=item["synthetic_location"],
                quality_grade=item["quality_grade"],
                estimated_value_inr=item["estimated_value_inr"],
                custodian_org=item["custodian_org"],
                status=item["status"],
                access_count=0,
            )
            db.add(batch)
            seeded_records.append(batch)

        db.commit()
        for batch in seeded_records:
            db.refresh(batch)
        return seeded_records

    def get_decoy_batches(self, db: Session) -> List[CyberTrapDecoyBatch]:
        """Fetch all synthetic honey-batch records, auto-seeding if empty."""
        batches = db.query(CyberTrapDecoyBatch).all()
        if not batches:
            batches = self.seed_default_decoy_batches(db)
        return batches

    def get_decoy_batch_by_id(self, db: Session, batch_id: str) -> Optional[CyberTrapDecoyBatch]:
        """Retrieve a specific synthetic honey-batch by its ID."""
        # Ensure seeds exist
        self.get_decoy_batches(db)
        return db.query(CyberTrapDecoyBatch).filter(CyberTrapDecoyBatch.id == batch_id).first()

    def increment_batch_access(self, db: Session, batch: CyberTrapDecoyBatch) -> None:
        """Increment synthetic honey-batch interaction count."""
        batch.access_count += 1
        db.add(batch)
        db.commit()

    @staticmethod
    def to_honey_batch_item(batch: CyberTrapDecoyBatch) -> HoneyBatchItem:
        """Convert a database model to the public Pydantic schema."""
        return HoneyBatchItem(
            id=batch.id,
            crop_type=batch.crop_type,
            variety=batch.variety,
            declared_quantity=batch.declared_quantity,
            unit=batch.unit,
            canary_token=batch.honeytoken_secret,
            synthetic_location=batch.synthetic_location,
            quality_grade=batch.quality_grade,
            estimated_value_inr=batch.estimated_value_inr,
            custodian_org=batch.custodian_org,
            access_count=batch.access_count,
            status=batch.status,
            created_at=batch.created_at,
        )

    def log_interaction(
        self,
        db: Session,
        request: Request,
        decoy_id: str,
        decoy_type: str,
        session_id: Optional[str] = None,
        payload: Optional[Any] = None,
        is_honeytoken_triggered: bool = False,
        honeytoken_id: Optional[str] = None,
    ) -> CyberTrapEvent:
        """Record an attacker or scanner interaction on a decoy honeypot.
        
        Extracts source IP, User-Agent, method, path, headers, query params,
        and inspects all incoming data for canary honeytokens.
        """
        # 1. Resolve source IP
        client_ip = "127.0.0.1"
        if request:
            forwarded_for = request.headers.get("x-forwarded-for")
            real_ip = request.headers.get("x-real-ip")
            extracted_ip = None
            if forwarded_for:
                candidate = forwarded_for.split(",")[0].replace("\x00", "").strip()
                if candidate:
                    extracted_ip = candidate
            if not extracted_ip and real_ip:
                candidate = real_ip.replace("\x00", "").strip()
                if candidate:
                    extracted_ip = candidate
            if not extracted_ip and request.client and request.client.host:
                candidate = str(request.client.host).replace("\x00", "").strip()
                if candidate:
                    extracted_ip = candidate

            if extracted_ip:
                client_ip = extracted_ip

        # Truncate to max 45 characters to prevent PostgreSQL StringDataRightTruncation
        client_ip = client_ip[:45]

        # 2. Extract headers and query params safely
        headers_dict: Dict[str, str] = {}
        query_params_dict: Dict[str, str] = {}
        request_method = "UNKNOWN"
        request_path = "/unknown"
        user_agent: Optional[str] = None

        if request:
            try:
                headers_dict = dict(request.headers)
            except Exception:
                headers_dict = {}

            try:
                query_params_dict = dict(request.query_params)
            except Exception:
                query_params_dict = {}

            request_method = request.method
            request_path = request.url.path
            user_agent = headers_dict.get("user-agent")

        # 3. Resolve session ID if not passed
        if not session_id and headers_dict:
            session_id = (
                headers_dict.get("x-session-id")
                or headers_dict.get("x-praman-session")
                or headers_dict.get("session-id")
            )

        # 4. Honeytoken inspection across headers, query params, and payload
        found_tokens: List[str] = []
        if payload:
            found_tokens.extend(self.extract_honeytokens(payload))
        if query_params_dict:
            found_tokens.extend(self.extract_honeytokens(query_params_dict))
        if headers_dict:
            found_tokens.extend(self.extract_honeytokens(headers_dict))

        if found_tokens:
            is_honeytoken_triggered = True
            if not honeytoken_id:
                honeytoken_id = found_tokens[0]

        # 5. Serialize JSON fields safely
        headers_json = json.dumps(headers_dict) if headers_dict else None
        query_params_json = json.dumps(query_params_dict) if query_params_dict else None
        payload_json = None
        if payload is not None:
            try:
                payload_json = json.dumps(payload, default=str)
            except Exception:
                payload_json = str(payload)

        # 6. Create event record
        event = CyberTrapEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            decoy_id=decoy_id,
            decoy_type=decoy_type,
            request_method=request_method,
            request_path=request_path,
            source_ip=client_ip,
            user_agent=user_agent,
            session_id=session_id,
            headers_json=headers_json,
            payload_json=payload_json,
            query_params_json=query_params_json,
            is_honeytoken_triggered=is_honeytoken_triggered,
            honeytoken_id=honeytoken_id,
        )

        try:
            db.add(event)
            db.commit()
            db.refresh(event)
        except Exception:
            db.rollback()
        return event

    def get_events(
        self,
        db: Session,
        limit: int = 50,
        offset: int = 0,
        decoy_id: Optional[str] = None,
        source_ip: Optional[str] = None,
        is_honeytoken_triggered: Optional[bool] = None,
    ) -> Tuple[List[CyberTrapEvent], int]:
        """Query honeypot events with filtering and pagination."""
        query = db.query(CyberTrapEvent)
        if decoy_id:
            query = query.filter(CyberTrapEvent.decoy_id == decoy_id)
        if source_ip:
            query = query.filter(CyberTrapEvent.source_ip == source_ip)
        if is_honeytoken_triggered is not None:
            query = query.filter(CyberTrapEvent.is_honeytoken_triggered == is_honeytoken_triggered)

        total = query.count()
        events = query.order_by(desc(CyberTrapEvent.timestamp)).offset(offset).limit(limit).all()
        return events, total


honeypot_service = HoneypotService()
