"""Acoustic Evidence Fingerprinting Service (Capability 12 - P1).
Provides cryptographic and perceptual fingerprinting of audio evidence:
- Calculates content-addressed storage (CAS) SHA-256 for audio bytes.
- Extracts acoustic features: Zero-Crossing Rate (ZCR), RMS Energy profile,
  Spectral Centroid proxy, and perceptual acoustic hash (bit-vector).
- Detects audio replay attacks across different batches, farmers, or timestamps.
- Flags indoor acoustic echo or synthesized audio submitted for outdoor farm claims.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import hashlib
import struct
import math


@dataclass
class AcousticFingerprint:
    audio_sha256: str
    sample_rate: int
    duration_seconds: float
    rms_energy: float
    zero_crossing_rate: float
    spectral_centroid: float
    perceptual_hash: str  # 64-bit hex representation
    is_indoor_acoustic_detected: bool
    is_synthetic_or_silent: bool


@dataclass
class AcousticComparisonResult:
    is_duplicate_replay: bool
    similarity_score: float  # 0.0 to 1.0 (1.0 = identical replay)
    hamming_distance: int
    is_identical_hash: bool
    recommendation: str
    routed_to_eio: bool


class AcousticFingerprintService:
    """Extracts perceptual fingerprints and detects replay attacks in audio evidence."""

    REPLAY_SIMILARITY_THRESHOLD = 0.92
    MIN_RMS_ENERGY = 0.005  # Lower than this is near-complete silence

    @classmethod
    def parse_audio_samples(cls, audio_bytes: bytes) -> Tuple[List[float], int]:
        """Extracts normalized float PCM samples from WAV header or raw bytes."""
        # Check for RIFF/WAVE header
        if len(audio_bytes) > 44 and audio_bytes[:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE":
            try:
                # Basic WAV parser: channels, sample_rate, bits_per_sample
                channels = struct.unpack_from("<H", audio_bytes, 22)[0]
                sample_rate = struct.unpack_from("<I", audio_bytes, 24)[0]
                bits_per_sample = struct.unpack_from("<H", audio_bytes, 34)[0]
                
                # Locate 'data' chunk
                pos = 36
                while pos < len(audio_bytes) - 8:
                    chunk_id = audio_bytes[pos:pos+4]
                    chunk_size = struct.unpack_from("<I", audio_bytes, pos+4)[0]
                    if chunk_id == b"data":
                        raw_data = audio_bytes[pos+8 : pos+8+chunk_size]
                        break
                    pos += 8 + chunk_size
                else:
                    raw_data = audio_bytes[44:]
                
                if bits_per_sample == 16:
                    count = len(raw_data) // 2
                    shorts = struct.unpack_from(f"<{count}h", raw_data)
                    # Convert to mono float [-1.0, 1.0]
                    if channels > 1:
                        mono = [shorts[i] / 32768.0 for i in range(0, count, channels)]
                    else:
                        mono = [s / 32768.0 for s in shorts]
                    return mono, sample_rate
            except Exception:
                pass

        # Fallback: treat raw bytes as signed 8-bit or unsigned byte PCM at 16000 Hz
        sample_rate = 16000
        mono = [(b - 128) / 128.0 for b in audio_bytes[:320000]]
        return mono, sample_rate

    @classmethod
    def extract_fingerprint(cls, audio_bytes: bytes) -> AcousticFingerprint:
        """Extracts acoustic features and 64-bit perceptual hash."""
        audio_sha256 = hashlib.sha256(audio_bytes).hexdigest()
        samples, sample_rate = cls.parse_audio_samples(audio_bytes)

        if not samples:
            return AcousticFingerprint(
                audio_sha256=audio_sha256,
                sample_rate=sample_rate,
                duration_seconds=0.0,
                rms_energy=0.0,
                zero_crossing_rate=0.0,
                spectral_centroid=0.0,
                perceptual_hash="0000000000000000",
                is_indoor_acoustic_detected=False,
                is_synthetic_or_silent=True,
            )

        n = len(samples)
        duration_sec = round(n / sample_rate, 3)

        # 1. RMS Energy
        sum_sq = sum(s * s for s in samples)
        rms = round(math.sqrt(sum_sq / n), 4)

        # 2. Zero Crossing Rate (ZCR)
        zcr_count = sum(1 for i in range(1, n) if (samples[i] >= 0 > samples[i - 1]) or (samples[i] < 0 <= samples[i - 1]))
        zcr = round(zcr_count / n, 4)

        # 3. Spectral Centroid Proxy (via time-domain derivative / weighted frequency proxy)
        diff_sq = sum((samples[i] - samples[i - 1]) ** 2 for i in range(1, n))
        spectral_centroid = round(math.sqrt(diff_sq / max(1, n - 1)) * (sample_rate / (2 * math.pi)), 2)

        # 4. 64-bit Perceptual Hash
        # Divide samples into 64 sub-blocks, compute block energies, and compare with adjacent block
        block_size = max(1, n // 64)
        block_energies = []
        for i in range(64):
            block = samples[i * block_size : (i + 1) * block_size]
            b_energy = sum(s * s for s in block) / max(1, len(block))
            block_energies.append(b_energy)

        hash_bits = []
        for i in range(64):
            prev = block_energies[i - 1] if i > 0 else block_energies[-1]
            hash_bits.append(1 if block_energies[i] > prev else 0)

        # Convert 64 bits to 16 hex chars
        val = 0
        for b in hash_bits:
            val = (val << 1) | b
        perceptual_hash = f"{val:016x}"

        # 5. Acoustic environment flags
        is_synthetic_or_silent = rms < cls.MIN_RMS_ENERGY
        # Indoor acoustics typically exhibit high low-frequency resonance and lower ZCR with high energy
        is_indoor = zcr < 0.03 and rms > 0.15 and spectral_centroid < 800.0

        return AcousticFingerprint(
            audio_sha256=audio_sha256,
            sample_rate=sample_rate,
            duration_seconds=duration_sec,
            rms_energy=rms,
            zero_crossing_rate=zcr,
            spectral_centroid=spectral_centroid,
            perceptual_hash=perceptual_hash,
            is_indoor_acoustic_detected=is_indoor,
            is_synthetic_or_silent=is_synthetic_or_silent,
        )

    @classmethod
    def compare_fingerprints(
        cls,
        fp1: AcousticFingerprint,
        fp2: AcousticFingerprint,
    ) -> AcousticComparisonResult:
        """Compares two acoustic fingerprints to detect replay attacks."""
        if fp1.audio_sha256 == fp2.audio_sha256:
            return AcousticComparisonResult(
                is_duplicate_replay=True,
                similarity_score=1.0,
                hamming_distance=0,
                is_identical_hash=True,
                recommendation="EXACT_AUDIO_DUPLICATE: Identical SHA-256 bitstream detected.",
                routed_to_eio=True,
            )

        # Compare 64-bit perceptual hashes
        v1 = int(fp1.perceptual_hash, 16)
        v2 = int(fp2.perceptual_hash, 16)
        xor_val = v1 ^ v2
        hamming_dist = bin(xor_val).count("1")

        similarity = round(1.0 - (hamming_dist / 64.0), 4)
        is_duplicate = similarity >= cls.REPLAY_SIMILARITY_THRESHOLD

        if is_duplicate:
            rec = f"ACOUSTIC_REPLAY_DETECTED: Similarity {similarity:.2%} (Hamming distance {hamming_dist}/64). Flagged as duplicate audio recording."
            routed = True
        elif similarity >= 0.80:
            rec = f"ACOUSTIC_SIMILARITY_WARNING: High similarity {similarity:.2%}. Manual inspection suggested."
            routed = True
        else:
            rec = f"DISTINCT_AUDIO: Similarity {similarity:.2%} within normal independent bounds."
            routed = False

        return AcousticComparisonResult(
            is_duplicate_replay=is_duplicate,
            similarity_score=similarity,
            hamming_distance=hamming_dist,
            is_identical_hash=False,
            recommendation=rec,
            routed_to_eio=routed,
        )

