import hashlib
import io
import os
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.user_org import Organization
from backend.app.models.supply_chain import Batch, RetailerInventory
from backend.app.models.farm import Farm
from backend.app.models.farmer import Farmer

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def ensure_bootstrap():
    """Ensure baseline platform data and demo batches are seeded."""
    resp = client.post("/api/v1/platform/auth/bootstrap")
    assert resp.status_code == 200


# ============================================================================
# 1. MEDIA UPLOAD & CAS PRESERVATION STRESS TESTS
# ============================================================================

def test_media_upload_diverse_byte_streams_preserves_sha256():
    """Stress-test POST /media/upload and GET /media/{photo_hash} across diverse byte streams.
    
    Verifies exact byte-for-byte preservation and SHA-256 integrity in CAS.
    """
    # 1. Simulated JPEG (with standard SOI and EOI markers)
    jpeg_stream = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + os.urandom(2048) + b"\xff\xd9"

    # 2. Simulated PNG (with 8-byte PNG signature and IHDR)
    png_stream = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + os.urandom(1024) + b"\x00\x00\x00\x00IEND\xaeB`\x82"

    # 3. Simulated WebP (RIFF + WEBP header)
    webp_stream = b"RIFF\x24\x08\x00\x00WEBPVP8 " + os.urandom(512)

    # 4. High-entropy pseudo-random binary stream (16 KB)
    binary_stream = os.urandom(16384)

    # 5. Deterministic repetitive pattern (64 KB)
    pattern_stream = (b"PRAMAN-SUPPLY-CHAIN-EVIDENCE-BLOCK-2026-" * 1600)[:65536]

    # 6. Structured ASCII log stream
    text_stream = b"TRANSIT_CHECKPOINT:LAT=19.6641:LON=78.5320:SEAL=VERIFIED:TIMESTAMP=2026-11-10T12:00:00Z\n" * 50

    test_streams = [
        ("cargo_photo.jpg", jpeg_stream, "image/jpeg", "CARGO_CONDITION"),
        ("ticket_slip.png", png_stream, "image/png", "SCALE_SLIP"),
        ("package.webp", webp_stream, "image/webp", "PACKAGE_LABEL"),
        ("firmware_dump.bin", binary_stream, "application/octet-stream", "SENSOR_RAW"),
        ("pattern_block.dat", pattern_stream, "application/octet-stream", "BULK_PAYLOAD"),
        ("route_log.txt", text_stream, "text/plain", "TRANSIT_LOG"),
        ("filename.with.many.dots.scan.jpeg", jpeg_stream[:1000] + b"\xff\xd9", "image/jpeg", "MULTI_DOT"),
        ("no_extension_file", binary_stream[:500], "application/octet-stream", "NO_EXT"),
    ]

    for filename, raw_bytes, content_type, category in test_streams:
        expected_hash = hashlib.sha256(raw_bytes).hexdigest()
        expected_size = len(raw_bytes)

        # Upload to CAS
        upload_resp = client.post(
            "/api/v1/platform/media/upload",
            files={"file": (filename, io.BytesIO(raw_bytes), content_type)},
            data={"category": category},
        )

        assert upload_resp.status_code == 200, f"Upload failed for {filename}: {upload_resp.text}"
        data = upload_resp.json()

        assert data["status"] == "SUCCESS"
        assert data["photo_hash"] == expected_hash, f"Hash mismatch for {filename}"
        assert data["size_bytes"] == expected_size
        assert data["category"] == category
        assert data["url"] == f"/api/v1/platform/media/{expected_hash}"

        # Retrieve raw bytes from CAS via GET /api/v1/platform/media/{photo_hash}
        get_resp = client.get(f"/api/v1/platform/media/{expected_hash}")
        assert get_resp.status_code == 200, f"Retrieval failed for hash {expected_hash}"

        retrieved_bytes = get_resp.content
        assert len(retrieved_bytes) == expected_size, f"Size mismatch for {filename}"
        assert retrieved_bytes == raw_bytes, f"Byte-for-byte corruption detected for {filename}"
        assert hashlib.sha256(retrieved_bytes).hexdigest() == expected_hash


def test_media_upload_idempotent_duplicate_storage():
    """Verify that uploading identical bytes repeatedly is idempotent in CAS."""
    sample_bytes = b"IMMUTABLE_EVIDENCE_REPRESENTATION_" + b"X" * 256
    expected_hash = hashlib.sha256(sample_bytes).hexdigest()

    # Upload first time
    r1 = client.post(
        "/api/v1/platform/media/upload",
        files={"file": ("first_run.jpg", io.BytesIO(sample_bytes), "image/jpeg")},
    )
    assert r1.status_code == 200
    assert r1.json()["photo_hash"] == expected_hash

    # Upload second time with different filename
    r2 = client.post(
        "/api/v1/platform/media/upload",
        files={"file": ("second_run_renamed.jpg", io.BytesIO(sample_bytes), "image/jpeg")},
    )
    assert r2.status_code == 200
    assert r2.json()["photo_hash"] == expected_hash

    # Content remains intact and retrievable
    get_resp = client.get(f"/api/v1/platform/media/{expected_hash}")
    assert get_resp.status_code == 200
    assert get_resp.content == sample_bytes


def test_media_upload_empty_stream_rejected():
    """Verify that an empty file upload is rejected with HTTP 400."""
    empty_resp = client.post(
        "/api/v1/platform/media/upload",
        files={"file": ("empty.jpg", io.BytesIO(b""), "image/jpeg")},
    )
    assert empty_resp.status_code == 400
    assert "Empty file upload" in empty_resp.json()["detail"]


def test_media_retrieval_nonexistent_hash_returns_404():
    """Verify that requesting a nonexistent media hash returns HTTP 404."""
    fake_hash = "a" * 64
    get_resp = client.get(f"/api/v1/platform/media/{fake_hash}")
    assert get_resp.status_code == 404
    assert "Media not found" in get_resp.json()["detail"]


# ============================================================================
# 2. RETAILER SALES WORKFLOW & INVENTORY DEPLETION STRESS TESTS
# ============================================================================

@pytest.fixture
def test_retail_inventory():
    """Creates a fresh isolated Batch and RetailerInventory item with exactly 100.0 kg."""
    db = SessionLocal()
    try:
        ret_org = db.query(Organization).filter(Organization.org_type == "RETAILER").first()
        unique_id = uuid.uuid4().hex[:8]

        batch = Batch(
            batch_code=f"BATCH-STRESS-{unique_id}",
            crop_type="Organic Soybeans",
            variety="Hardy Seed",
            initial_quantity=100.0,
            current_quantity=100.0,
            unit="kg",
            stage="AT_RETAILER",
            status="ACTIVE",
            quality_grade="GRADE_A",
        )
        db.add(batch)
        db.flush()

        opaque_token = f"prm_stress_{unique_id}"
        inv = RetailerInventory(
            retailer_org_id=ret_org.id if ret_org else "retailer-org-test",
            batch_id=batch.id,
            crop_type="Organic Soybeans",
            available_quantity=100.0,
            unit="kg",
            storage_location="Stress Test Shelf B-2",
            opaque_qr_token=opaque_token,
        )
        db.add(inv)
        db.commit()
        db.refresh(inv)
        db.refresh(batch)
        return {"inventory_id": inv.id, "batch_id": batch.id, "token": opaque_token}
    finally:
        db.close()


def test_retailer_sale_valid_partial_decrement(test_retail_inventory):
    """Stress-test valid partial sale: decrements available quantity accurately."""
    inv_id = test_retail_inventory["inventory_id"]

    # Sell 35.5 kg from 100.0 kg
    resp = client.post(
        "/api/v1/platform/retailer/sale",
        json={
            "inventory_id": inv_id,
            "quantity": 35.5,
            "receipt_number": "RCPT-PARTIAL-001",
            "customer_notes": "Bulk consumer purchase",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["quantity_sold"] == 35.5
    assert data["remaining_quantity"] == 64.5
    assert data["is_depleted"] is False

    # Verify directly in database
    db = SessionLocal()
    try:
        inv = db.query(RetailerInventory).filter(RetailerInventory.id == inv_id).first()
        assert inv.available_quantity == 64.5
        assert inv.batch.status == "ACTIVE"
    finally:
        db.close()


def test_retailer_sale_excessive_quantity_rejected(test_retail_inventory):
    """Stress-test excessive sale (Q > Q_avail): must reject with HTTP 400."""
    inv_id = test_retail_inventory["inventory_id"]

    # Available is 100.0 kg; attempt to sell 150.0 kg
    resp = client.post(
        "/api/v1/platform/retailer/sale",
        json={"inventory_id": inv_id, "quantity": 150.0},
    )
    assert resp.status_code == 400
    assert "exceeds available stock" in resp.json()["detail"]

    # Verify stock was untouched
    db = SessionLocal()
    try:
        inv = db.query(RetailerInventory).filter(RetailerInventory.id == inv_id).first()
        assert inv.available_quantity == 100.0
    finally:
        db.close()


def test_retailer_sale_zero_and_negative_quantities_rejected(test_retail_inventory):
    """Stress-test non-positive quantities (Q <= 0): must reject with HTTP 400."""
    inv_id = test_retail_inventory["inventory_id"]

    # 1. Zero quantity
    r_zero = client.post(
        "/api/v1/platform/retailer/sale",
        json={"inventory_id": inv_id, "quantity": 0.0},
    )
    assert r_zero.status_code == 400
    assert "Sale quantity must be positive" in r_zero.json()["detail"]

    # 2. Negative quantity
    r_neg = client.post(
        "/api/v1/platform/retailer/sale",
        json={"inventory_id": inv_id, "quantity": -12.5},
    )
    assert r_neg.status_code == 400
    assert "Sale quantity must be positive" in r_neg.json()["detail"]

    # 3. Micro-negative quantity
    r_micro_neg = client.post(
        "/api/v1/platform/retailer/sale",
        json={"inventory_id": inv_id, "quantity": -0.0001},
    )
    assert r_micro_neg.status_code == 400
    assert "Sale quantity must be positive" in r_micro_neg.json()["detail"]

    # Verify stock remained 100.0 kg
    db = SessionLocal()
    try:
        inv = db.query(RetailerInventory).filter(RetailerInventory.id == inv_id).first()
        assert inv.available_quantity == 100.0
    finally:
        db.close()


def test_retailer_sale_exact_full_sale_marks_depleted(test_retail_inventory):
    """Stress-test exact full sale (Q == Q_avail): must update batch status to DEPLETED and stage to SOLD."""
    inv_id = test_retail_inventory["inventory_id"]
    batch_id = test_retail_inventory["batch_id"]

    # Sell exactly 100.0 kg
    resp = client.post(
        "/api/v1/platform/retailer/sale",
        json={
            "inventory_id": inv_id,
            "quantity": 100.0,
            "receipt_number": "RCPT-FULL-DEPLETION-001",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["quantity_sold"] == 100.0
    assert data["remaining_quantity"] == 0.0
    assert data["is_depleted"] is True

    # Verify directly in database
    db = SessionLocal()
    try:
        inv = db.query(RetailerInventory).filter(RetailerInventory.id == inv_id).first()
        assert inv.available_quantity == 0.0
        assert inv.batch.status == "DEPLETED"
        assert inv.batch.stage == "SOLD"
    finally:
        db.close()

    # Attempting to sell anything more from depleted stock must reject with HTTP 400
    resp_after = client.post(
        "/api/v1/platform/retailer/sale",
        json={"inventory_id": inv_id, "quantity": 0.5},
    )
    assert resp_after.status_code == 400
    assert "exceeds available stock" in resp_after.json()["detail"]


def test_retailer_sale_by_batch_id_lookup(test_retail_inventory):
    """Verify endpoint supports lookup by batch_id as well as inventory_id."""
    batch_id = test_retail_inventory["batch_id"]

    resp = client.post(
        "/api/v1/platform/retailer/sale",
        json={"inventory_id": batch_id, "quantity": 10.0},
    )
    assert resp.status_code == 200
    assert resp.json()["remaining_quantity"] == 90.0


def test_retailer_sale_nonexistent_inventory_404():
    """Verify selling from non-existent inventory item returns HTTP 404."""
    resp = client.post(
        "/api/v1/platform/retailer/sale",
        json={"inventory_id": "non-existent-inventory-id-9999", "quantity": 10.0},
    )
    assert resp.status_code == 404
    assert "Retail inventory item not found" in resp.json()["detail"]


# ============================================================================
# 3. CUSTOMER QR VERIFICATION & TAMPER REJECTION STRESS TESTS
# ============================================================================

def test_customer_qr_verification_valid_token(test_retail_inventory):
    """Stress-test GET /verify/{opaque_token} with an authentic active token."""
    token = test_retail_inventory["token"]

    resp = client.get(f"/api/v1/platform/verify/{token}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "VERIFIED_AUTHENTIC"
    assert data["verification_token"] == token
    assert "merkle_root" in data and len(data["merkle_root"]) == 64
    assert data["ledger_commitment"] == "COMMITTED_TO_MERKLE_ROOT"
    assert data["cryptographic_integrity"] == "VALID_NIST_P256_SECP256R1"
    assert data["zero_pii_enforced"] is True
    assert data["zero_gps_leakage"] is True

    # Provenance timeline validation
    timeline = data["provenance_timeline"]
    assert isinstance(timeline, list)
    assert len(timeline) > 0

    # Ensure required audit timeline fields exist on all stages
    for stage in timeline:
        assert "stage" in stage
        assert "title" in stage
        assert "status" in stage
        assert "actor" in stage
        assert "timestamp" in stage


def test_customer_qr_verification_tampered_token_returns_404(test_retail_inventory):
    """Stress-test GET /verify/{opaque_token} with single-character tampered tokens.
    
    Any bit-flip, truncated token, or mutated character must return HTTP 404.
    """
    valid_token = test_retail_inventory["token"]

    # 1. Mutate last character
    last_char = valid_token[-1]
    mutated_last = "0" if last_char != "0" else "1"
    tampered_token_1 = valid_token[:-1] + mutated_last

    r1 = client.get(f"/api/v1/platform/verify/{tampered_token_1}")
    assert r1.status_code == 404
    assert "UNVERIFIED OR TAMPERED TOKEN" in r1.json()["detail"]

    # 2. Mutate middle character
    mid_idx = len(valid_token) // 2
    mid_char = valid_token[mid_idx]
    mutated_mid = "x" if mid_char != "x" else "y"
    tampered_token_2 = valid_token[:mid_idx] + mutated_mid + valid_token[mid_idx + 1:]

    r2 = client.get(f"/api/v1/platform/verify/{tampered_token_2}")
    assert r2.status_code == 404
    assert "UNVERIFIED OR TAMPERED TOKEN" in r2.json()["detail"]

    # 3. Truncated token
    tampered_token_3 = valid_token[:8]
    r3 = client.get(f"/api/v1/platform/verify/{tampered_token_3}")
    assert r3.status_code == 404
    assert "UNVERIFIED OR TAMPERED TOKEN" in r3.json()["detail"]


def test_customer_qr_verification_adversarial_inputs_returns_404():
    """Verify that SQL injection, XSS, and arbitrary strings do not bypass verification."""
    adversarial_inputs = [
        "random_bogus_token_12345678",
        "' OR '1'='1",
        "prm_admin'--",
        "<script>alert(1)</script>",
        "prm_00000000000000000000000000000000",
        "..%2F..%2Fetc%2Fpasswd",
        "../../etc/passwd",
    ]

    for attack_str in adversarial_inputs:
        resp = client.get(f"/api/v1/platform/verify/{attack_str}")
        assert resp.status_code == 404, f"Adversarial input {attack_str} did not return 404: {resp.status_code}"
        detail = resp.json()["detail"]
        assert "UNVERIFIED OR TAMPERED TOKEN" in detail or detail == "Not Found"
