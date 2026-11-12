"""Comprehensive Test Suite for PRAMAN P1, P2, and P3 Capabilities (10 to 21).
Covers:
- Capability 10: Drone and Satellite Corroboration (AerialService)
- Capability 11: Weather Cross-Verification (WeatherCrossVerificationService)
- Capability 12: Acoustic Evidence Fingerprinting (AcousticFingerprintService)
- Capability 13: Statistical Anomaly Detection (StatisticalAnomalyService)
- Capability 14: Decentralized Identity (DID) Lifecycle (DecentralizedIdentityService)
- Capability 15: Steganographic Evidence Watermarking (SteganographyService)
- Capability 16: Packaging Physical Unclonable Features (PackagingPUFService)
- Capability 17: Supply-Chain Mass-Balance Invariants (MassBalanceService)
- Capability 18: Zero-Knowledge Compliance Verification (ZKComplianceService)
- Capability 19: Staking and Slashing Mechanisms (StakingAndSlashingService)
- Capability 20: Blind Margin Obfuscation (BlindMarginObfuscationService)
- Capability 21: Autonomous EUDR / FSMA Compliance Intelligence (RegulatoryComplianceService)
"""

import pytest
import io
import struct
import math
import hashlib
from datetime import date

# Import P1, P2, P3 services
from backend.app.services.aerial_service import DroneAndSatelliteService, AerialObservation
from backend.app.services.weather_service import WeatherCrossVerificationService, DailyWeatherRecord
from backend.app.services.acoustic_service import AcousticFingerprintService, AcousticFingerprint
from backend.app.services.statistical_anomaly_service import StatisticalAnomalyService
from backend.app.services.did_service import DecentralizedIdentityService
from backend.app.services.steganography_service import SteganographyService
from backend.app.services.puf_service import PackagingPUFService
from backend.app.services.mass_balance_service import MassBalanceService
from backend.app.services.zk_compliance_service import ZKComplianceService
from backend.app.services.staking_service import StakingAndSlashingService
from backend.app.services.margin_obfuscation_service import BlindMarginObfuscationService
from backend.app.services.regulatory_service import RegulatoryComplianceService


# ==============================================================================
# Capability 10: Drone and Satellite Corroboration Tests
# ==============================================================================
class TestCapability10AerialCorroboration:
    @pytest.fixture
    def sample_polygon(self):
        # 4 vertices in Warangal, Telangana
        return [
            (17.9689, 79.5941),
            (17.9710, 79.5945),
            (17.9712, 79.5980),
            (17.9688, 79.5978),
        ]

    def test_ndvi_and_evi_calculation(self):
        # NIR=0.50, Red=0.10 -> NDVI = (0.5 - 0.1) / (0.5 + 0.1) = 0.4 / 0.6 = 0.6667
        ndvi = DroneAndSatelliteService.calculate_ndvi(0.50, 0.10)
        assert abs(ndvi - 0.6667) < 0.001

        # Bare soil: NIR=0.20, Red=0.18 -> NDVI = 0.02 / 0.38 = 0.0526
        ndvi_soil = DroneAndSatelliteService.calculate_ndvi(0.20, 0.18)
        assert 0.0 < ndvi_soil < 0.15

        evi = DroneAndSatelliteService.calculate_evi(0.50, 0.10, 0.05)
        assert evi > 0.0

    def test_aerial_corroboration_vigorous_crop(self, sample_polygon):
        obs = AerialObservation(
            source_type="DRONE_ORTHOMOSAIC",
            sensor_id="DJI_MAVIC_M3M",
            acquisition_time="2026-11-10T10:00:00Z",
            gsd_meters=0.05,
            cloud_cover_pct=2.0,
            bounding_box=(17.9680, 79.5930, 17.9720, 79.5990),
            bands={"red": 0.08, "nir": 0.52, "green": 0.12, "blue": 0.04},
            raster_sha256="abcdef1234567890",
            is_synthetic=True,
        )
        res = DroneAndSatelliteService.corroborate_plot(sample_polygon, obs, expected_stage="VEGETATIVE_GROWTH")
        assert res.is_corroborated is True
        assert res.confidence_score >= 0.85
        assert res.canopy_status == "VIGOROUS"
        assert res.routed_to_eio is False
        assert len(res.anomaly_flags) == 0

    def test_aerial_corroboration_cloud_and_phenology_anomaly(self, sample_polygon):
        # High cloud cover + low vegetation during vegetative growth stage
        obs = AerialObservation(
            source_type="SATELLITE_SENTINEL2",
            sensor_id="SENTINEL2_MSI",
            acquisition_time="2026-11-10T10:00:00Z",
            gsd_meters=10.0,
            cloud_cover_pct=45.0,  # > 30% cloud
            bounding_box=(17.9680, 79.5930, 17.9720, 79.5990),
            bands={"red": 0.20, "nir": 0.22, "green": 0.15, "blue": 0.12},
            raster_sha256="9876543210fedcba",
            is_synthetic=True,
        )
        res = DroneAndSatelliteService.corroborate_plot(sample_polygon, obs, expected_stage="VEGETATIVE_GROWTH")
        assert res.is_corroborated is False
        assert res.routed_to_eio is True
        assert any("HIGH_CLOUD_OCCLUSION" in flag for flag in res.anomaly_flags)


# ==============================================================================
# Capability 11: Weather Cross-Verification Tests
# ==============================================================================
class TestCapability11WeatherVerification:
    def test_weather_delay_claim_confirmed(self):
        records = [
            DailyWeatherRecord(
                obs_date="2026-11-01",
                lat=17.97,
                lon=79.59,
                station_or_grid_id="STN_WGL_01",
                precipitation_mm=42.5,
                temp_max_c=28.0,
                temp_min_c=21.0,
                avg_humidity_pct=92.0,
                soil_moisture_m3m3=0.38,
                wind_max_kmh=45.0,
            ),
            DailyWeatherRecord(
                obs_date="2026-11-02",
                lat=17.97,
                lon=79.59,
                station_or_grid_id="STN_WGL_01",
                precipitation_mm=38.0,
                temp_max_c=26.5,
                temp_min_c=20.5,
                avg_humidity_pct=95.0,
                soil_moisture_m3m3=0.42,
                wind_max_kmh=52.0,
            ),
        ]
        res = WeatherCrossVerificationService.evaluate_delay_claim(
            claim_type="HEAVY_RAIN",
            records=records,
            claim_start_date="2026-11-01",
            claim_end_date="2026-11-02",
        )
        assert res.is_valid is True
        assert res.status == "CONFIRMED"
        assert res.recorded_precipitation_mm == 80.5
        assert res.routed_to_eio is False

    def test_weather_physical_impossibility_detected(self):
        # Claiming heavy rain when 0.0 mm rain recorded
        records = [
            DailyWeatherRecord(
                obs_date="2026-11-01",
                lat=17.97,
                lon=79.59,
                station_or_grid_id="STN_WGL_01",
                precipitation_mm=0.0,
                temp_max_c=36.0,
                temp_min_c=24.0,
                avg_humidity_pct=35.0,
                soil_moisture_m3m3=0.12,
                wind_max_kmh=12.0,
            ),
        ]
        res = WeatherCrossVerificationService.evaluate_delay_claim(
            claim_type="HEAVY_RAIN",
            records=records,
            claim_start_date="2026-11-01",
            claim_end_date="2026-11-01",
        )
        assert res.is_valid is False
        assert res.status == "PHYSICAL_IMPOSSIBILITY"
        assert res.routed_to_eio is True
        assert any("Physical discrepancy" in d for d in res.discrepancy_reasons)


# ==============================================================================
# Capability 12: Acoustic Evidence Fingerprinting Tests
# ==============================================================================
class TestCapability12AcousticFingerprinting:
    def _create_synthetic_wav(self, duration_sec: float = 1.0, freq_hz: float = 440.0) -> bytes:
        sample_rate = 16000
        n_samples = int(sample_rate * duration_sec)
        samples = []
        for i in range(n_samples):
            t = i / sample_rate
            sample_val = int(math.sin(2 * math.pi * freq_hz * t) * 16000)
            samples.append(sample_val)

        raw_pcm = struct.pack(f"<{n_samples}h", *samples)
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + len(raw_pcm),
            b"WAVE",
            b"fmt ",
            16,
            1,  # PCM
            1,  # Mono
            sample_rate,
            sample_rate * 2,
            2,
            16,
            b"data",
            len(raw_pcm),
        )
        return header + raw_pcm

    def test_fingerprint_extraction(self):
        wav_bytes = self._create_synthetic_wav(duration_sec=0.5, freq_hz=500.0)
        fp = AcousticFingerprintService.extract_fingerprint(wav_bytes)

        assert fp.duration_seconds >= 0.49
        assert fp.rms_energy > 0.05
        assert len(fp.perceptual_hash) == 16  # 64-bit hex
        assert fp.is_synthetic_or_silent is False

    def test_replay_detection_exact_and_near_duplicate(self):
        wav1 = self._create_synthetic_wav(duration_sec=0.5, freq_hz=440.0)
        wav2 = self._create_synthetic_wav(duration_sec=0.5, freq_hz=440.0)
        wav_diff = self._create_synthetic_wav(duration_sec=0.5, freq_hz=2500.0)

        fp1 = AcousticFingerprintService.extract_fingerprint(wav1)
        fp2 = AcousticFingerprintService.extract_fingerprint(wav2)
        fp_diff = AcousticFingerprintService.extract_fingerprint(wav_diff)

        # Exact duplicate
        res_exact = AcousticFingerprintService.compare_fingerprints(fp1, fp2)
        assert res_exact.is_duplicate_replay is True
        assert res_exact.is_identical_hash is True
        assert res_exact.similarity_score == 1.0

        # Different acoustic frequency
        res_diff = AcousticFingerprintService.compare_fingerprints(fp1, fp_diff)
        assert res_diff.is_identical_hash is False


# ==============================================================================
# Capability 13: Statistical Anomaly Detection Tests
# ==============================================================================
class TestCapability13StatisticalAnomalyDetection:
    def test_yield_anomaly_severe_inflation(self):
        # Peer cohort averages ~2000 kg/ha with standard deviation ~200
        cohort = [1850.0, 1920.0, 2050.0, 2100.0, 1980.0, 2010.0, 1890.0, 2150.0, 2020.0]
        # Claiming 8,500 kg/ha on a 1.0 ha farm
        res = StatisticalAnomalyService.evaluate_yield_anomaly(
            farm_yield_kg=8500.0,
            farm_area_ha=1.0,
            cohort_yields_kg_per_ha=cohort,
        )
        assert res.is_outlier is True
        assert res.anomaly_severity == "SEVERE_INFLATION"
        assert res.z_score > 3.0
        assert res.routed_to_eio is True

    def test_benfords_law_chi_square_natural_vs_fabricated(self):
        # Natural dataset conforming to Benford's law
        natural_data = []
        for d, prob in StatisticalAnomalyService.BENFORD_THEORETICAL.items():
            count = int(prob * 1000)
            natural_data.extend([d * 1000.0 + float(i % 100) for i in range(count)])

        res_natural = StatisticalAnomalyService.test_benfords_law(natural_data)
        assert res_natural.is_conforming is True
        assert res_natural.anomaly_flag == "NATURAL_DISTRIBUTION"
        assert res_natural.routed_to_eio is False

        # Fabricated dataset: uniform random / constant leading digit (e.g. all 7s and 8s)
        fabricated_data = [7500.0 + float(i % 100) for i in range(100)] + [8200.0 + float(i % 100) for i in range(100)]
        res_fab = StatisticalAnomalyService.test_benfords_law(fabricated_data)
        assert res_fab.is_conforming is False
        assert res_fab.anomaly_flag in ("FABRICATED_WEIGHTS", "SUSPICIOUS_MANIPULATION")
        assert res_fab.routed_to_eio is True

    def test_velocity_volume_spike(self):
        history = [120.0, 150.0, 130.0, 140.0, 125.0]
        # Sudden 1500 kg transaction (over 10x baseline)
        res = StatisticalAnomalyService.evaluate_velocity_spike(1500.0, history, threshold_ratio=3.0)
        assert res.is_spike is True
        assert res.spike_ratio > 5.0
        assert res.routed_to_eio is True


# ==============================================================================
# Capability 14: Decentralized Identity (DID) Lifecycle Tests
# ==============================================================================
class TestCapability14DecentralizedIdentity:
    def test_did_generation_and_document_resolution(self):
        did = DecentralizedIdentityService.generate_did("farmer", "f1092-telangana")
        assert did == "did:praman:farmer:f1092-telangana"

        doc = DecentralizedIdentityService.resolve_did_document(did)
        assert doc.did == did
        assert doc.actor_type == "farmer"
        assert doc.actor_id == "f1092-telangana"
        assert len(doc.document_json["verificationMethod"]) == 1
        assert doc.verification_method_id == f"{did}#keys-1"

    def test_verifiable_credential_issuance_and_verification(self):
        issuer_did = "did:praman:authority:telangana-agri-board"
        subject_did = "did:praman:farmer:f1092-telangana"
        claims = {
            "farmId": "farm-001",
            "organicStatus": "CERTIFIED_NPOP_ORGANIC",
            "crop": "COTTON",
            "maxCertifiedHa": 4.5,
        }

        vc = DecentralizedIdentityService.issue_verifiable_credential(
            issuer_did=issuer_did,
            subject_did=subject_did,
            credential_type="OrganicInspectionCredential",
            claims=claims,
            validity_days=180,
        )

        assert "OrganicInspectionCredential" in vc.credential_type
        assert vc.revocation_index > 0
        assert "proof" in vc.raw_vc_json

        # Verify credential
        import json
        vc_dict = json.loads(vc.raw_vc_json)
        verification = DecentralizedIdentityService.verify_credential(vc_dict)
        assert verification["is_valid"] is True
        assert verification["subject"] == subject_did

    def test_credential_revocation(self):
        issuer_did = "did:praman:authority:telangana-agri-board"
        subject_did = "did:praman:farmer:f-compromised"
        vc = DecentralizedIdentityService.issue_verifiable_credential(
            issuer_did=issuer_did,
            subject_did=subject_did,
            credential_type="FarmerIdentityCredential",
            claims={"status": "SUSPICIOUS"},
        )
        import json
        vc_dict = json.loads(vc.raw_vc_json)

        # Before revocation
        assert DecentralizedIdentityService.verify_credential(vc_dict)["is_valid"] is True

        # Officer revokes credential
        DecentralizedIdentityService.revoke_credential(
            revocation_index=vc.revocation_index,
            reason="Identity spoofing detected by Evidence Integrity Officer",
            officer_did="did:praman:officer:eio-01",
        )

        # After revocation
        rev_check = DecentralizedIdentityService.verify_credential(vc_dict)
        assert rev_check["is_valid"] is False
        assert "REVOKED_CREDENTIAL" in rev_check["reason"]


# ==============================================================================
# Capability 15: Steganographic Evidence Watermarking Tests
# ==============================================================================
class TestCapability15Steganography:
    def _create_test_image_bytes(self, width: int = 100, height: int = 100) -> bytes:
        from PIL import Image
        img = Image.new("RGB", (width, height), color=(128, 128, 128))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_embed_and_extract_watermark(self):
        raw_img = self._create_test_image_bytes(120, 120)
        raw_hash = hashlib.sha256(raw_img).hexdigest()

        # Embed into exported derivative
        derivative_img = SteganographyService.embed_watermark_in_image(
            image_bytes=raw_img,
            batch_id="BATCH-TEL-2026-X1",
            evidence_id="EVID-1092",
            org_did="did:praman:org:apmc-warangal",
            timestamp_iso="2026-11-10T12:00:00Z",
        )

        # Invariant check: Raw bytes remain intact
        assert hashlib.sha256(raw_img).hexdigest() == raw_hash
        assert derivative_img != raw_img

        # Extract from derivative
        result = SteganographyService.extract_watermark_from_image(derivative_img)
        assert result.has_watermark is True
        assert result.is_hmac_valid is True
        assert result.payload.batch_id == "BATCH-TEL-2026-X1"
        assert result.payload.evidence_id == "EVID-1092"
        assert result.payload.org_did == "did:praman:org:apmc-warangal"

    def test_tampered_payload_rejected(self):
        raw_img = self._create_test_image_bytes(100, 100)
        derivative_img = SteganographyService.embed_watermark_in_image(
            image_bytes=raw_img,
            batch_id="BATCH-01",
            evidence_id="EVID-01",
            org_did="did:praman:org:test",
        )

        # Alter random bytes in derivative image
        corrupted = bytearray(derivative_img)
        corrupted[150] ^= 0xFF

        result = SteganographyService.extract_watermark_from_image(bytes(corrupted))
        # If payload was altered, HMAC must fail or decode fails
        if result.has_watermark:
            assert result.is_hmac_valid is False


# ==============================================================================
# Capability 16: Packaging Physical Unclonable Features (PUF) Tests
# ==============================================================================
class TestCapability16PackagingPUF:
    def test_puf_enrollment_and_authentic_verification(self):
        enrolled_puf = "a1b2c3d4e5f60718" * 4  # 64 hex chars = 256 bits
        PackagingPUFService.enroll_seal(
            seal_id="SEAL-TAMPER-001",
            batch_id="BATCH-COTTON-01",
            feature_vector_hex=enrolled_puf,
            user_id="user_cc_operator_1",
            is_synthetic=True,
        )

        # Authentic scan with 1 bit difference (sensor noise)
        scanned_puf = "a1b2c3d4e5f60719" + ("a1b2c3d4e5f60718" * 3)
        res = PackagingPUFService.verify_seal(
            seal_id="SEAL-TAMPER-001",
            scanned_feature_hex=scanned_puf,
            hardware_connected=True,
        )
        assert res.is_authentic is True
        assert res.status == "VERIFIED_AUTHENTIC"
        assert res.hamming_distance_ratio <= 0.05
        assert res.routed_to_eio is False

    def test_puf_counterfeit_tamper_detection(self):
        enrolled_puf = "ffff0000ffff0000" * 4
        PackagingPUFService.enroll_seal(
            seal_id="SEAL-TAMPER-002",
            batch_id="BATCH-COTTON-02",
            feature_vector_hex=enrolled_puf,
            user_id="user_cc_operator_1",
        )

        # Counterfeit scan (divergent microstructure)
        fake_scan = "0000ffff0000ffff" * 4
        res = PackagingPUFService.verify_seal(
            seal_id="SEAL-TAMPER-002",
            scanned_feature_hex=fake_scan,
            hardware_connected=True,
        )
        assert res.is_authentic is False
        assert res.status == "CLONE_DETECTED"
        assert res.hamming_distance_ratio >= 0.80
        assert res.routed_to_eio is True

    def test_puf_hardware_disconnected_honesty(self):
        # Strict hardware truthfulness: reporting disconnected hardware
        res = PackagingPUFService.verify_seal(
            seal_id="SEAL-TAMPER-001",
            scanned_feature_hex=None,
            hardware_connected=False,
        )
        assert res.is_authentic is False
        assert res.status == "HARDWARE_DISCONNECTED"
        assert res.hardware_status == "DISCONNECTED"


# ==============================================================================
# Capability 17: Supply-Chain Mass-Balance Invariants Tests
# ==============================================================================
class TestCapability17MassBalance:
    def test_transit_shrinkage_normal_and_violation(self):
        # 1000 kg picked up -> 985 kg delivered = 1.5% shrinkage (normal for cotton)
        recon_norm = MassBalanceService.evaluate_transit_shrinkage(1000.0, 985.0, commodity="COTTON")
        assert recon_norm.status == "NORMAL"

        # Weight inflation: 1000 kg picked up -> 1010 kg delivered = negative shrinkage / adulteration
        recon_inf = MassBalanceService.evaluate_transit_shrinkage(1000.0, 1010.0, commodity="COTTON")
        assert recon_inf.status == "VIOLATION"
        assert "inflation" in recon_inf.reason.lower()

    def test_batch_split_conservation(self):
        # 1000 kg parent split into 400 + 350 + 240 + 10 kg waste = 1000 kg (exact)
        res_valid = MassBalanceService.validate_batch_split_conservation(
            parent_qty=1000.0,
            child_quantities=[400.0, 350.0, 240.0],
            waste_loss_qty=10.0,
        )
        assert res_valid["is_valid"] is True
        assert res_valid["delta_kg"] == 0.0

        # Unbalanced split: child quantities sum to 1050 kg (phantom mass insertion)
        res_invalid = MassBalanceService.validate_batch_split_conservation(
            parent_qty=1000.0,
            child_quantities=[600.0, 450.0],
            waste_loss_qty=0.0,
        )
        assert res_invalid["is_valid"] is False

    def test_retail_depletion_anti_overselling(self):
        # Available 50 kg, selling 20 kg -> OK
        res_ok = MassBalanceService.validate_retail_depletion(50.0, 20.0)
        assert res_ok["is_valid"] is True
        assert res_ok["remaining_available_qty"] == 30.0

        # Available 50 kg, selling 60 kg -> Overselling violation
        res_viol = MassBalanceService.validate_retail_depletion(50.0, 60.0)
        assert res_viol["is_valid"] is False
        assert res_viol["deficit_qty"] == 10.0


# ==============================================================================
# Capability 18: Zero-Knowledge Compliance Verification Tests
# ==============================================================================
class TestCapability18ZeroKnowledgeCompliance:
    def test_pedersen_commitment_homomorphic_binding(self):
        val = 1250  # 1250 kg
        comm, blinding = ZKComplianceService.commit(val)
        assert comm.commitment_int > 0
        assert len(comm.commitment_hex) > 60

    def test_zk_proof_generation_and_verification(self):
        actual_harvest_kg = 2450.0
        quota_min = 1000.0
        quota_max = 3000.0

        comm, proof, in_bounds = ZKComplianceService.prove_yield_in_quota(
            actual_harvest_kg, quota_min, quota_max
        )
        assert in_bounds is True

        # Verifier checks proof mathematically without knowing actual harvest kg
        verif = ZKComplianceService.verify_compliance_proof(comm.commitment_int, proof)
        assert verif.is_valid is True
        assert "succeeded" in verif.reason

    def test_zk_proof_fails_on_tampered_commitment(self):
        comm, proof, _ = ZKComplianceService.prove_yield_in_quota(1500.0, 1000.0, 2000.0)
        # Malicious prover alters commitment
        tampered_c = (comm.commitment_int + 1) % ZKComplianceService.P
        verif = ZKComplianceService.verify_compliance_proof(tampered_c, proof)
        assert verif.is_valid is False


# ==============================================================================
# Capability 19: Staking and Slashing Mechanisms Tests
# ==============================================================================
class TestCapability19StakingAndSlashing:
    def test_stake_bonding_and_dispute_lifecycle(self):
        actor_id = "transporter_logistics_corp"
        stake = StakingAndSlashingService.bond_stake(actor_id, "TRANSPORTER", 50000.0)
        assert stake.bonded_amount_inr == 50000.0
        assert stake.available_amount_inr == 50000.0

        # Open dispute for 10000 INR
        disp = StakingAndSlashingService.open_dispute(
            actor_id=actor_id,
            batch_id="BATCH-COTTON-09",
            initiator_role="COLLECTION_CENTRE",
            allegation_type="WEIGHT_TAMPERING",
            dispute_amount_inr=10000.0,
            evidence_hashes=["hash1", "hash2"],
        )
        assert disp.status == "OPEN"
        assert disp.disputed_amount_inr == 10000.0

        updated_stake = StakingAndSlashingService.get_stake(actor_id)
        assert updated_stake.available_amount_inr == 40000.0
        assert updated_stake.locked_in_dispute_inr == 10000.0

    def test_unauthorized_autonomous_slashing_rejected(self):
        actor_id = "transporter_unauth_test"
        StakingAndSlashingService.bond_stake(actor_id, "TRANSPORTER", 20000.0)
        disp = StakingAndSlashingService.open_dispute(
            actor_id=actor_id,
            batch_id="BATCH-01",
            initiator_role="AUTOMATED_ALGORITHM",
            allegation_type="TEMPERATURE_VIOLATION",
            dispute_amount_inr=5000.0,
            evidence_hashes=[],
        )

        # Autonomous slashing or non-EIO must be rejected
        with pytest.raises(PermissionError):
            StakingAndSlashingService.adjudicate_slashing_order(
                dispute_id=disp.dispute_id,
                officer_user_id="bot_engine",
                is_officer_eio=False,  # NOT EIO
                verdict="SLASH_FULL",
                slash_percentage=100.0,
                rationale="Automated rule triggered.",
            )

    def test_eio_adjudication_slashing_order(self):
        actor_id = "transporter_adjudicate_test"
        StakingAndSlashingService.bond_stake(actor_id, "TRANSPORTER", 30000.0)
        disp = StakingAndSlashingService.open_dispute(
            actor_id=actor_id,
            batch_id="BATCH-02",
            initiator_role="COLLECTION_CENTRE",
            allegation_type="ROUTE_DIVERSION",
            dispute_amount_inr=10000.0,
            evidence_hashes=[],
        )

        # EIO adjudicates partial 50% slash with mandatory written rationale
        res = StakingAndSlashingService.adjudicate_slashing_order(
            dispute_id=disp.dispute_id,
            officer_user_id="user_eio_official",
            is_officer_eio=True,
            verdict="SLASH_PARTIAL",
            slash_percentage=50.0,
            rationale="Transporter diverted 45km from geo-fenced highway corridor without technical breakdown justification.",
        )
        assert res["status"] == "ADJUDICATED_SLASHED"
        assert res["slashed_amount_inr"] == 5000.0

        stake = StakingAndSlashingService.get_stake(actor_id)
        assert stake.bonded_amount_inr == 25000.0
        assert stake.available_amount_inr == 25000.0


# ==============================================================================
# Capability 20: Blind Margin Obfuscation Tests
# ==============================================================================
class TestCapability20BlindMarginObfuscation:
    def test_role_based_sanitization(self):
        record = {
            "batch_id": "BATCH-PADDY-01",
            "quantity_kg": 500.0,
            "crop_grade": "A+",
            "procurement_price_inr": 22500.0,
            "trader_margin_inr": 3500.0,
            "wholesale_cost_per_kg": 45.0,
        }

        # Public QR / Consumer view
        public_view = BlindMarginObfuscationService.sanitize_for_role(record, requester_role="PUBLIC_QR")
        assert public_view.is_obfuscated is True
        assert public_view.sanitized_record["procurement_price_inr"] == "[CONFIDENTIAL_COMMERCIAL_RECORD]"
        assert public_view.sanitized_record["quantity_kg"] == 500.0
        assert "_commercial_integrity_proof" in public_view.sanitized_record

        # Evidence Integrity Officer view
        eio_view = BlindMarginObfuscationService.sanitize_for_role(record, requester_role="EVIDENCE_INTEGRITY_OFFICER")
        assert eio_view.is_obfuscated is False
        assert eio_view.sanitized_record["procurement_price_inr"] == 22500.0

    def test_pricing_commitment_audit_verification(self):
        record = {
            "procurement_price_inr": 50000.0,
            "trader_margin_inr": 8000.0,
        }
        commitment = BlindMarginObfuscationService.compute_pricing_commitment("BATCH-99", record)
        assert BlindMarginObfuscationService.verify_pricing_integrity("BATCH-99", record, commitment) is True
        assert BlindMarginObfuscationService.verify_pricing_integrity("BATCH-99", {"procurement_price_inr": 100.0}, commitment) is False


# ==============================================================================
# Capability 21: Autonomous EUDR / FSMA Compliance Intelligence Tests
# ==============================================================================
class TestCapability21RegulatoryCompliance:
    def test_eudr_compliance_valid_polygon(self):
        # 5.5 ha plot (> 4 ha threshold) with 4 closed polygon vertices
        polygon = [
            (17.9689, 79.5941),
            (17.9710, 79.5945),
            (17.9712, 79.5980),
            (17.9688, 79.5978),
        ]
        res = RegulatoryComplianceService.evaluate_eudr_compliance(
            farm_id="farm_eudr_01",
            area_ha=5.5,
            polygon_vertices=polygon,
            last_deforestation_event_date=date(2018, 5, 20),  # Prior to Dec 31, 2020 cutoff
            country_code="IN",
        )
        assert res.is_eudr_compliant is True
        assert res.due_diligence_reference_id is not None
        assert "EUDR-DDS-IN-2026-" in res.due_diligence_reference_id
        assert res.routed_to_eio is False

    def test_eudr_violation_missing_polygon_on_large_plot(self):
        # 8.0 ha plot but only 1 coordinate point provided (violates Art 9)
        single_point = [(17.9689, 79.5941)]
        res = RegulatoryComplianceService.evaluate_eudr_compliance(
            farm_id="farm_eudr_large_invalid",
            area_ha=8.0,
            polygon_vertices=single_point,
            last_deforestation_event_date=date(2019, 1, 1),
        )
        assert res.is_eudr_compliant is False
        assert any("EUDR Article 9 Violation" in flag for flag in res.discrepancy_flags)
        assert res.routed_to_eio is True

    def test_eudr_violation_post_2020_deforestation(self):
        # Deforestation event in 2022 violates Dec 31, 2020 cut-off date
        polygon = [(17.9, 79.5), (17.91, 79.5), (17.91, 79.51)]
        res = RegulatoryComplianceService.evaluate_eudr_compliance(
            farm_id="farm_eudr_deforest",
            area_ha=2.5,
            polygon_vertices=polygon,
            last_deforestation_event_date=date(2022, 6, 15),
        )
        assert res.is_eudr_compliant is False
        assert any("EUDR Article 3 Violation" in flag for flag in res.discrepancy_flags)
        assert res.routed_to_eio is True

    def test_fsma_204_traceability_compliance(self):
        events = [
            {
                "event_type": "HARVESTING",
                "timestamp": "2026-11-08T07:00:00Z",
                "location_id": "LOC_FARM_WARANGAL_01",
                "quantity_kg": 1200.0,
                "document_id": "DOC-HARVEST-2026-001",
            },
            {
                "event_type": "SHIPPING",
                "timestamp": "2026-11-08T14:00:00Z",
                "location_id": "LOC_TRANS_DEPOT_01",
                "quantity_kg": 1200.0,
                "document_id": "BOL-TRUCK-8899",
            },
            {
                "event_type": "RECEIVING",
                "timestamp": "2026-11-09T09:00:00Z",
                "location_id": "LOC_CC_WARANGAL_CENTRAL",
                "quantity_kg": 1185.0,
                "document_id": "GRN-CC-2026-091",
            },
        ]
        res = RegulatoryComplianceService.evaluate_fsma_204_compliance(
            batch_id="BATCH-CHILLI-FSMA-01",
            commodity="CHILLI",
            supply_chain_events=events,
        )
        assert res.is_fsma_compliant is True
        assert res.is_ftl_covered is True
        assert len(res.critical_tracking_events) == 3
        assert "export_json_24hr_ready" in dir(res)
        assert res.export_json_24hr_ready["compliance_status"] == "COMPLIANT"
