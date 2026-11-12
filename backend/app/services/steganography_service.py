"""Steganographic Evidence Watermarking Service (Capability 15 - P1).
Provides imperceptible forensic provenance watermarking for exported evidence images:
- Raw Evidence Invariant: Original raw uploads stored in CAS under their SHA-256 hash
  are NEVER modified and retain their original device/camera signatures.
- Export Derivative Watermarking: When evidence images are exported, audited, or rendered
  for public/court review, an imperceptible forensic payload is embedded in the pixel LSBs.
- Forensic Payload: Magic bytes + Batch/Evidence ID + Org DID + ISO Timestamp + Cryptographic HMAC.
- Extraction & Verification: Extracts payload from exported derivative and verifies HMAC authentication tag.
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import io
import struct
import hmac
import hashlib

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


@dataclass
class WatermarkPayload:
    batch_id: str
    evidence_id: str
    org_did: str
    timestamp_iso: str
    hmac_signature: str


@dataclass
class WatermarkExtractionResult:
    has_watermark: bool
    is_hmac_valid: bool
    payload: Optional[WatermarkPayload]
    error_message: Optional[str]


class SteganographyService:
    """Forensic steganographic watermarking for derivative evidence exports."""

    MAGIC_HEADER = b"PRM_STEG_V1"
    HMAC_SECRET = b"PRAMAN-STEG-FORENSIC-SECRET-2026"

    @classmethod
    def compute_hmac(cls, data: bytes) -> bytes:
        """Calculates 16-byte HMAC tag for watermarked payload."""
        return hmac.new(cls.HMAC_SECRET, data, hashlib.sha256).digest()[:16]

    @classmethod
    def encode_payload(cls, batch_id: str, evidence_id: str, org_did: str, timestamp_iso: str) -> bytes:
        """Serializes watermark payload with magic header and cryptographic HMAC."""
        # Format: MAGIC(11 bytes) + len_b(1) + batch_id + len_e(1) + evidence_id + len_o(1) + org_did + len_t(1) + timestamp + HMAC(16)
        b_b = batch_id.encode("utf-8")[:64]
        b_e = evidence_id.encode("utf-8")[:64]
        b_o = org_did.encode("utf-8")[:64]
        b_t = timestamp_iso.encode("utf-8")[:32]

        content = (
            struct.pack(">B", len(b_b)) + b_b +
            struct.pack(">B", len(b_e)) + b_e +
            struct.pack(">B", len(b_o)) + b_o +
            struct.pack(">B", len(b_t)) + b_t
        )

        tag = cls.compute_hmac(content)
        return cls.MAGIC_HEADER + content + tag

    @classmethod
    def embed_watermark_in_image(
        cls,
        image_bytes: bytes,
        batch_id: str,
        evidence_id: str,
        org_did: str,
        timestamp_iso: Optional[str] = None,
    ) -> bytes:
        """Embeds imperceptible forensic watermark into derivative image (PNG/BMP) using LSB encoding.
        Original raw file in CAS remains unmodified.
        """
        if not HAS_PIL:
            # Fallback if PIL unavailable: append authenticated forensic trailer
            now_iso = timestamp_iso or datetime.now(timezone.utc).isoformat()
            raw_payload = cls.encode_payload(batch_id, evidence_id, org_did, now_iso)
            return image_bytes + b"\x00PRAMAN_TRAILER\x00" + raw_payload

        now_iso = timestamp_iso or datetime.now(timezone.utc).isoformat()
        payload_bytes = cls.encode_payload(batch_id, evidence_id, org_did, now_iso)
        
        # 4 bytes for total length prefix + payload bytes
        full_stream = struct.pack(">I", len(payload_bytes)) + payload_bytes
        bit_stream = []
        for byte_val in full_stream:
            for bit_idx in range(7, -1, -1):
                bit_stream.append((byte_val >> bit_idx) & 1)

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = img.size
        pixels = list(img.getdata())

        total_pixels = len(pixels)
        if len(bit_stream) > total_pixels * 3:
            raise ValueError(f"Image too small ({total_pixels} pixels) for watermark bitstream ({len(bit_stream)} bits)")

        modified_pixels = []
        bit_idx = 0
        total_bits = len(bit_stream)

        for r, g, b in pixels:
            channels = [r, g, b]
            for c_i in range(3):
                if bit_idx < total_bits:
                    # Clear least significant bit and set watermark bit
                    channels[c_i] = (channels[c_i] & ~1) | bit_stream[bit_idx]
                    bit_idx += 1
            modified_pixels.append(tuple(channels))

        watermarked_img = Image.new("RGB", (width, height))
        watermarked_img.putdata(modified_pixels)

        out_buffer = io.BytesIO()
        watermarked_img.save(out_buffer, format="PNG")
        return out_buffer.getvalue()

    @classmethod
    def extract_watermark_from_image(cls, image_bytes: bytes) -> WatermarkExtractionResult:
        """Extracts and cryptographically verifies forensic watermark from derivative image."""
        if not HAS_PIL:
            # Check trailer fallback
            trailer_tag = b"\x00PRAMAN_TRAILER\x00"
            idx = image_bytes.find(trailer_tag)
            if idx != -1:
                raw_payload = image_bytes[idx + len(trailer_tag):]
                return cls._parse_raw_payload(raw_payload)
            return WatermarkExtractionResult(
                has_watermark=False,
                is_hmac_valid=False,
                payload=None,
                error_message="No watermark found (PIL unavailable, trailer absent)",
            )

        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            pixels = list(img.getdata())

            # Read first 32 bits to get payload length
            len_bits = []
            bit_count = 0
            for r, g, b in pixels:
                for channel in (r, g, b):
                    if bit_count < 32:
                        len_bits.append(channel & 1)
                        bit_count += 1
                if bit_count >= 32:
                    break

            payload_len = 0
            for b in len_bits:
                payload_len = (payload_len << 1) | b

            if payload_len <= 0 or payload_len > 10000:
                # Trailer fallback check
                trailer_tag = b"\x00PRAMAN_TRAILER\x00"
                idx = image_bytes.find(trailer_tag)
                if idx != -1:
                    raw_payload = image_bytes[idx + len(trailer_tag):]
                    return cls._parse_raw_payload(raw_payload)
                return WatermarkExtractionResult(
                    has_watermark=False,
                    is_hmac_valid=False,
                    payload=None,
                    error_message=f"Invalid payload length: {payload_len}",
                )

            # Read payload bits
            total_payload_bits = payload_len * 8
            payload_bits = []
            bit_count = 0
            target_bits = 32 + total_payload_bits

            for r, g, b in pixels:
                for channel in (r, g, b):
                    if bit_count >= 32 and bit_count < target_bits:
                        payload_bits.append(channel & 1)
                    bit_count += 1
                if bit_count >= target_bits:
                    break

            # Convert bits to bytes
            payload_bytes = bytearray()
            for byte_i in range(0, len(payload_bits), 8):
                byte_val = 0
                for bit_i in range(8):
                    if byte_i + bit_i < len(payload_bits):
                        byte_val = (byte_val << 1) | payload_bits[byte_i + bit_i]
                payload_bytes.append(byte_val)

            return cls._parse_raw_payload(bytes(payload_bytes))

        except Exception as e:
            return WatermarkExtractionResult(
                has_watermark=False,
                is_hmac_valid=False,
                payload=None,
                error_message=f"Steganographic extraction error: {str(e)}",
            )

    @classmethod
    def _parse_raw_payload(cls, raw: bytes) -> WatermarkExtractionResult:
        """Validates magic header, unpacks fields, and verifies HMAC tag."""
        if len(raw) < len(cls.MAGIC_HEADER) + 20:
            return WatermarkExtractionResult(
                has_watermark=False,
                is_hmac_valid=False,
                payload=None,
                error_message="Payload too short",
            )

        magic = raw[:len(cls.MAGIC_HEADER)]
        if magic != cls.MAGIC_HEADER:
            return WatermarkExtractionResult(
                has_watermark=False,
                is_hmac_valid=False,
                payload=None,
                error_message="Magic header mismatch",
            )

        offset = len(cls.MAGIC_HEADER)
        try:
            # 1. Batch ID
            len_b = raw[offset]
            offset += 1
            batch_id = raw[offset : offset + len_b].decode("utf-8")
            offset += len_b

            # 2. Evidence ID
            len_e = raw[offset]
            offset += 1
            evidence_id = raw[offset : offset + len_e].decode("utf-8")
            offset += len_e

            # 3. Org DID
            len_o = raw[offset]
            offset += 1
            org_did = raw[offset : offset + len_o].decode("utf-8")
            offset += len_o

            # 4. Timestamp
            len_t = raw[offset]
            offset += 1
            timestamp_iso = raw[offset : offset + len_t].decode("utf-8")
            offset += len_t

            # Verify HMAC tag (last 16 bytes)
            content_bytes = raw[len(cls.MAGIC_HEADER) : offset]
            received_tag = raw[offset : offset + 16]
            expected_tag = cls.compute_hmac(content_bytes)

            is_valid_hmac = hmac.compare_digest(received_tag, expected_tag)

            payload = WatermarkPayload(
                batch_id=batch_id,
                evidence_id=evidence_id,
                org_did=org_did,
                timestamp_iso=timestamp_iso,
                hmac_signature=received_tag.hex(),
            )

            return WatermarkExtractionResult(
                has_watermark=True,
                is_hmac_valid=is_valid_hmac,
                payload=payload,
                error_message=None if is_valid_hmac else "HMAC authentication failed: payload tampered",
            )
        except Exception as e:
            return WatermarkExtractionResult(
                has_watermark=False,
                is_hmac_valid=False,
                payload=None,
                error_message=f"Payload unpack failed: {str(e)}",
            )

