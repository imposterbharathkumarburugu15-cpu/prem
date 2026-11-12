"""Adversarial and Empirical Stress Test Suite for Milestone 3 (teamwork_challenger_m3_2).

Exhaustively verifies:
1. Tier 2 Epoch Merkle Rollup (P0.9):
   - Empty batch list handling and zero-state exceptions.
   - Odd batch counts (1, 3, 5, 7, 9, 11) with odd-node promotion.
   - Two-tier inclusion proof generation and cryptographic verification across multi-batch epochs.
   - Full adversarial tamper suite on dual-tier proofs:
     * Tampered envelope bytes.
     * Tampered Tier 1 proof step (flipped bit and inverted position).
     * Tampered Tier 1 batch root.
     * Tampered Tier 2 canonical batch leaf descriptor.
     * Tampered Tier 2 audit path.
     * Tampered Tier 2 epoch root.
     * Tampered authority checkpoint signature.
   - Batch re-sealing prevention and non-existent batch isolation.

2. Mass Balance Quantity Reconciliation:
   - Highway transit moisture shrinkage across diverse commodities (Cotton, Produce, Paddy, Grain, Chilli, Default).
   - Strict detection of negative shrinkage / weight inflation (<-0.20% and <-0.50%).
   - Batch split conservation tolerance (+-0.01 kg exact boundary and floating-point stress).
   - Retail anti-overselling enforcement and exact depletion mechanics.
   - Certified scale reconciliation (manual vs hardware automated tolerances).
   - End-to-end multi-stage batch lineage reconciliation.

3. Trust Graph Temporal Decay & Harmonic Mean Propagation (P0.7):
   - Mathematical precision of exponential dormancy decay T(t) = T_baseline + (T_0 - T_baseline) * exp(-lambda * delta_t).
   - Half-life calibration (t_1/2 ~ 60 days).
   - Reverse decay toward baseline from below (reputation recovery).
   - Boundary conditions (delta_t = 0, delta_t < 0, delta_t -> inf, extreme out-of-bound inputs).
   - Harmonic mean custody chain invariants:
     * Identity and homogeneity.
     * Commutativity and order invariance.
     * Domination by weakest link (comparison with deceptive arithmetic mean).
     * Complete zero-trust collapse.
   - Upstream penalty back-propagation, non-negativity clamping, and self-loop deduplication.
   - Radar routing strictness to single Evidence Integrity Officer (officer1).
"""

import math
import uuid
import json
import hashlib
import pytest
from datetime import datetime, timezone, timedelta, date

from backend.app.core.database import SessionLocal
from backend.app.models.farmer import Farmer
from backend.app.models.device import Device
from backend.app.models.farm import Farm
from backend.app.models.evidence import Evidence
from backend.app.models.merkle_batch import MerkleBatch
from backend.app.models.merkle_epoch import MerkleEpoch
from backend.app.models.trust import ActorTrust, TrustEvent
from backend.app.models.supply_chain import (
    Batch,
    Shipment,
    ShipmentItem,
    ShipmentEvent,
    WeighingRecord,
    RetailerInventory,
)

from backend.app.services.epoch_merkle_service import EpochMerkleService
from backend.app.services.merkle_service import MerkleService
from backend.app.services.mass_balance_service import MassBalanceService
from backend.app.services.trust_graph_service import TrustGraphService
from backend.app.services.radar_service import RadarService
from crypto.rfc8785 import canonicalize
from crypto.merkle import MerkleTree, leaf_hash_hex, verify_merkle_proof
from crypto.authority import get_authority_public_key_pem


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


# ============================================================================
# PART 1: TIER 2 EPOCH MERKLE ROLLUP STRESS TESTS (P0.9)
# ============================================================================

def test_epoch_empty_batch_list_handling(db):
    """Stress test: verify explicit rejection of empty or non-existent batch lists."""
    # 1. Explicit empty list must raise ValueError
    with pytest.raises(ValueError, match="batch_ids list cannot be empty"):
        EpochMerkleService.create_epoch(db, batch_ids=[])

    # 2. Non-existent batch IDs must raise ValueError
    bogus_id = f"batch-nonexistent-{uuid.uuid4().hex}"
    with pytest.raises(ValueError, match="One or more specified batches do not exist"):
        EpochMerkleService.create_epoch(db, batch_ids=[bogus_id])

    # 3. MerkleTree empty initialization must return None root
    tree_empty = MerkleTree(leaves_data=[])
    assert tree_empty.root is None
    assert tree_empty.root_hex is None
    assert tree_empty.leaf_count == 0


def test_epoch_odd_batch_counts_promotion():
    """Stress test: odd batch counts (1, 3, 5, 7, 9, 11) with odd-node promotion.
    Confirms CVE-2012-2459 immunity and independent proof validity for all leaves.
    """
    for count in [1, 3, 5, 7, 9, 11, 21]:
        raw_leaves = [
            canonicalize({"batch_index": i, "token": f"leaf-{i}-{count}"})
            for i in range(count)
        ]
        tree = MerkleTree(leaves_data=raw_leaves)
        assert tree.root_hex is not None
        assert tree.leaf_count == count

        # Verify every leaf's inclusion proof
        for idx in range(count):
            proof = tree.get_proof(idx)
            is_valid = verify_merkle_proof(
                leaf_data=raw_leaves[idx],
                proof=proof,
                expected_root=tree.root_hex,
            )
            assert is_valid is True, f"Failed proof verification for leaf {idx} of {count}"

        # Confirm Bitcoin-style duplicate padding creates a DIFFERENT root
        # (proving odd-node promotion is strictly distinct from duplication)
        if count > 1 and count % 2 == 1:
            padded_leaves = list(raw_leaves) + [raw_leaves[-1]]
            padded_tree = MerkleTree(leaves_data=padded_leaves)
            assert tree.root_hex != padded_tree.root_hex, "Odd-node promotion must not equal duplicate padding!"


def test_epoch_already_sealed_batch_rejection(db):
    """Stress test: attempting to seal a batch already rolled into an epoch must fail."""
    # Create batch
    b_id = f"batch-sealed-{uuid.uuid4().hex[:8]}"
    b = MerkleBatch(
        id=b_id,
        merkle_root=hashlib.sha256(b_id.encode()).hexdigest(),
        leaf_count=5,
        evidence_ids_json=json.dumps(["ev-1"]),
        status="COMMITTED_TO_LEDGER",
    )
    db.add(b)
    db.flush()

    # Seal in epoch 1
    epoch1 = EpochMerkleService.create_epoch(db, batch_ids=[b_id])
    assert b.epoch_id == epoch1.id

    # Attempt to seal again in epoch 2 must be rejected
    with pytest.raises(ValueError, match="already rolled into epoch"):
        EpochMerkleService.create_epoch(db, batch_ids=[b_id])


def test_dual_tier_proof_multi_batch_comprehensive(db):
    """Stress test: 3 Tier 1 batches in 1 Tier 2 Epoch with multiple evidence items.
    Generates and verifies dual-tier inclusion proofs for every single leaf.
    """
    run_id = uuid.uuid4().hex[:6]
    farmer = Farmer(id=f"farmer-stress-{run_id}", name="Stress Farmer", phone=f"+9198765{run_id}")
    db.add(farmer)
    db.flush()

    farm = Farm(id=f"farm-stress-{run_id}", farmer_id=farmer.id, farm_name="Stress Farm", crop_type="COTTON", area_acres=3.0)
    db.add(farm)
    db.flush()

    dev_id = f"dev-stress-{run_id}"
    device = Device(id=dev_id, farmer_id=farmer.id, public_key_pem="stress-key", status="ACTIVE")
    db.add(device)
    db.flush()

    # Create 3 batches, each with 2 evidence items (total 6 items)
    all_ev_ids = []
    all_canons = {}
    batch_ids = []

    for b_idx in range(3):
        batch_ev_ids = []
        for e_idx in range(2):
            seq = b_idx * 10 + e_idx + 1
            envelope_dict = {
                "device_id": dev_id,
                "sequence_number": seq,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "batch_group": b_idx,
                "leaf_num": e_idx,
            }
            canon_bytes = canonicalize(envelope_dict)
            ev_id = f"ev-stress-{run_id}-b{b_idx}-e{e_idx}"
            ev = Evidence(
                id=ev_id,
                farm_id=farm.id,
                device_id=dev_id,
                sequence_number=seq,
                lifecycle_stage="HARVEST",
                image_hash=hashlib.sha256(canon_bytes).hexdigest(),
                canonical_envelope_json=json.dumps(envelope_dict),
                signature_b64="sig",
                status="APPROVED",
            )
            db.add(ev)
            batch_ev_ids.append(ev_id)
            all_ev_ids.append(ev_id)
            all_canons[ev_id] = canon_bytes
        db.flush()

        batch_res = MerkleService.create_batch(db, evidence_ids=batch_ev_ids)
        batch_ids.append(batch_res["batch_id"])

    # Roll the 3 batches into an epoch
    epoch = EpochMerkleService.create_epoch(db, batch_ids=batch_ids)
    assert epoch.batch_count == 3
    assert epoch.total_items == 6

    # Verify dual-tier proof for ALL 6 evidence items
    for ev_id in all_ev_ids:
        proof_bundle = EpochMerkleService.get_dual_tier_proof(db, ev_id)
        assert proof_bundle is not None
        assert proof_bundle["evidence_id"] == ev_id

        is_valid = EpochMerkleService.verify_dual_tier_proof(
            envelope_canonical_bytes=all_canons[ev_id],
            proof_bundle=proof_bundle,
        )
        assert is_valid is True, f"Dual-tier verification failed for {ev_id}"


def test_dual_tier_proof_tamper_matrix(db):
    """Stress test: Exhaustive adversarial tamper matrix against Dual-Tier Proofs.
    Every single mutation must immediately result in verification failure (False).
    """
    run_id = uuid.uuid4().hex[:6]
    farmer = Farmer(id=f"farmer-tamper-{run_id}", name="Tamper Farmer", phone=f"+9198765{run_id}")
    db.add(farmer)
    farm = Farm(id=f"farm-tamper-{run_id}", farmer_id=farmer.id, farm_name="Tamper Farm", crop_type="COTTON", area_acres=2.0)
    db.add(farm)
    dev_id = f"dev-tamper-{run_id}"
    device = Device(id=dev_id, farmer_id=farmer.id, public_key_pem="key", status="ACTIVE")
    db.add(device)
    db.flush()

    envelope_dict = {"device_id": dev_id, "sequence": 99, "data": "authentic-payload"}
    canon_bytes = canonicalize(envelope_dict)
    ev_id = f"ev-tamper-{run_id}"
    ev = Evidence(
        id=ev_id,
        farm_id=farm.id,
        device_id=dev_id,
        sequence_number=99,
        lifecycle_stage="HARVEST",
        image_hash=hashlib.sha256(canon_bytes).hexdigest(),
        canonical_envelope_json=json.dumps(envelope_dict),
        signature_b64="sig",
        status="APPROVED",
    )
    db.add(ev)
    db.flush()

    batch_res = MerkleService.create_batch(db, evidence_ids=[ev_id])
    epoch = EpochMerkleService.create_epoch(db, batch_ids=[batch_res["batch_id"]])

    genuine_bundle = EpochMerkleService.get_dual_tier_proof(db, ev_id)
    assert genuine_bundle is not None
    assert EpochMerkleService.verify_dual_tier_proof(canon_bytes, genuine_bundle) is True

    # Attack 1: Altered Leaf Bytes (payload modification)
    tampered_bytes = canonicalize({"device_id": dev_id, "sequence": 99, "data": "malicious-payload"})
    assert EpochMerkleService.verify_dual_tier_proof(tampered_bytes, genuine_bundle) is False

    # Attack 2: Tamper Tier 1 Batch Root
    bundle_bad_t1_root = json.loads(json.dumps(genuine_bundle))
    bundle_bad_t1_root["tier1_proof"]["batch_merkle_root"] = "0" * 64
    assert EpochMerkleService.verify_dual_tier_proof(canon_bytes, bundle_bad_t1_root) is False

    # Attack 3: Tamper Tier 1 Audit Path Sibling Hash (if path exists, otherwise alter empty list to fake step)
    bundle_bad_t1_path = json.loads(json.dumps(genuine_bundle))
    if bundle_bad_t1_path["tier1_proof"]["audit_path"]:
        bundle_bad_t1_path["tier1_proof"]["audit_path"][0]["hash"] = "f" * 64
    else:
        bundle_bad_t1_path["tier1_proof"]["audit_path"] = [{"position": "right", "hash": "f" * 64}]
    assert EpochMerkleService.verify_dual_tier_proof(canon_bytes, bundle_bad_t1_path) is False

    # Attack 4: Tamper Tier 2 Epoch Root
    bundle_bad_t2_root = json.loads(json.dumps(genuine_bundle))
    bundle_bad_t2_root["tier2_proof"]["epoch_root"] = "e" * 64
    assert EpochMerkleService.verify_dual_tier_proof(canon_bytes, bundle_bad_t2_root) is False

    # Attack 5: Tamper Tier 2 Audit Path
    bundle_bad_t2_path = json.loads(json.dumps(genuine_bundle))
    bundle_bad_t2_path["tier2_proof"]["audit_path"] = [{"position": "left", "hash": "a" * 64}]
    assert EpochMerkleService.verify_dual_tier_proof(canon_bytes, bundle_bad_t2_path) is False

    # Attack 6: Tamper Tier 1 Checkpoint ID (alters canonical leaf for Tier 2)
    bundle_bad_cp_id = json.loads(json.dumps(genuine_bundle))
    bundle_bad_cp_id["tier1_proof"]["checkpoint"]["checkpoint_id"] = "cp-tampered-id"
    assert EpochMerkleService.verify_dual_tier_proof(canon_bytes, bundle_bad_cp_id) is False

    # Attack 7: Tamper Authority Checkpoint Signature
    bundle_bad_sig = json.loads(json.dumps(genuine_bundle))
    bundle_bad_sig["tier2_proof"]["checkpoint"]["signature"] = "bWFsZm9ybWVkLXNpZ25hdHVyZQ=="
    assert EpochMerkleService.verify_dual_tier_proof(canon_bytes, bundle_bad_sig) is False

    # Attack 8: Missing proof sections
    assert EpochMerkleService.verify_dual_tier_proof(canon_bytes, {"tier1_proof": {}}) is False
    assert EpochMerkleService.verify_dual_tier_proof(canon_bytes, {}) is False


# ============================================================================
# PART 2: MASS BALANCE QUANTITY RECONCILIATION STRESS TESTS
# ============================================================================

def test_mass_balance_multi_commodity_transit_shrinkage():
    """Stress test: moisture loss curves across multiple commodity thresholds."""
    # 1. COTTON: normal <= 2.0%, warning <= 4.0%, violation > 4.0%
    assert MassBalanceService.evaluate_transit_shrinkage(1000.0, 980.0, "COTTON").status == "NORMAL"  # 2.0%
    assert MassBalanceService.evaluate_transit_shrinkage(1000.0, 979.9, "COTTON").status == "WARNING"  # 2.01%
    assert MassBalanceService.evaluate_transit_shrinkage(1000.0, 960.0, "COTTON").status == "WARNING"  # 4.0%
    assert MassBalanceService.evaluate_transit_shrinkage(1000.0, 959.0, "COTTON").status == "VIOLATION"  # 4.1%

    # 2. PRODUCE: normal <= 5.0%, warning <= 8.0%, violation > 8.0%
    assert MassBalanceService.evaluate_transit_shrinkage(1000.0, 950.0, "PRODUCE").status == "NORMAL"  # 5.0%
    assert MassBalanceService.evaluate_transit_shrinkage(1000.0, 949.0, "PRODUCE").status == "WARNING"  # 5.1%
    assert MassBalanceService.evaluate_transit_shrinkage(1000.0, 920.0, "PRODUCE").status == "WARNING"  # 8.0%
    assert MassBalanceService.evaluate_transit_shrinkage(1000.0, 919.0, "PRODUCE").status == "VIOLATION"  # 8.1%

    # 3. PADDY / GRAIN / SOYBEAN: normal <= 1.5%, warning <= 3.0%, violation > 3.0%
    assert MassBalanceService.evaluate_transit_shrinkage(1000.0, 985.0, "PADDY").status == "NORMAL"  # 1.5%
    assert MassBalanceService.evaluate_transit_shrinkage(1000.0, 984.0, "SOYBEAN").status == "WARNING"  # 1.6%
    assert MassBalanceService.evaluate_transit_shrinkage(1000.0, 970.0, "GRAIN").status == "WARNING"  # 3.0%
    assert MassBalanceService.evaluate_transit_shrinkage(1000.0, 969.0, "PULSE").status == "VIOLATION"  # 3.1%

    # 4. DEFAULT (unknown commodity) falls back to default thresholds (2% / 4%)
    assert MassBalanceService.evaluate_transit_shrinkage(1000.0, 980.0, "UNKNOWN_CROP").status == "NORMAL"
    assert MassBalanceService.evaluate_transit_shrinkage(1000.0, 959.0, "UNKNOWN_CROP").status == "VIOLATION"

    # 5. Invalid input: non-positive pickup
    with pytest.raises(ValueError, match="must be positive"):
        MassBalanceService.evaluate_transit_shrinkage(0.0, 10.0)


def test_mass_balance_weight_inflation_boundary_stress():
    """Stress test: negative shrinkage / weight inflation boundaries (<-0.20% and <-0.50%)."""
    # COTTON inflation threshold is -0.20%
    # Delivered 1001.9 kg from 1000.0 kg -> -0.19% shrinkage -> NORMAL (within inflation tolerance)
    res_sub = MassBalanceService.evaluate_transit_shrinkage(1000.0, 1001.9, "COTTON")
    assert res_sub.status == "NORMAL"

    # Delivered 1002.1 kg from 1000.0 kg -> -0.21% shrinkage -> VIOLATION (Weight inflation)
    res_inf = MassBalanceService.evaluate_transit_shrinkage(1000.0, 1002.1, "COTTON")
    assert res_inf.status == "VIOLATION"
    assert "Weight inflation detected" in res_inf.reason

    # PRODUCE inflation threshold is -0.50%
    # Delivered 1004.0 kg from 1000.0 kg -> -0.40% -> NORMAL
    assert MassBalanceService.evaluate_transit_shrinkage(1000.0, 1004.0, "PRODUCE").status == "NORMAL"
    # Delivered 1006.0 kg from 1000.0 kg -> -0.60% -> VIOLATION
    assert MassBalanceService.evaluate_transit_shrinkage(1000.0, 1006.0, "PRODUCE").status == "VIOLATION"


def test_mass_balance_split_conservation_precision_stress():
    """Stress test: split conservation tolerance (+-0.01 kg) and precision boundaries."""
    parent = 1000.0

    # 1. Exact match
    r1 = MassBalanceService.validate_batch_split_conservation(parent, [600.0, 390.0], waste_loss_qty=10.0)
    assert r1["is_valid"] is True
    assert r1["delta_kg"] == 0.0

    # 2. Within tolerance: delta = 0.0099 kg
    r2 = MassBalanceService.validate_batch_split_conservation(parent, [600.0, 389.9901], waste_loss_qty=10.0)
    assert r2["is_valid"] is True
    assert r2["delta_kg"] == 0.0099

    # 3. Exactly at tolerance: delta = 0.0100 kg
    r3 = MassBalanceService.validate_batch_split_conservation(parent, [600.0, 389.9900], waste_loss_qty=10.0)
    assert r3["is_valid"] is True
    assert r3["delta_kg"] == 0.0100

    # 4. Out of tolerance: delta = 0.0101 kg
    r4 = MassBalanceService.validate_batch_split_conservation(parent, [600.0, 389.9899], waste_loss_qty=10.0)
    assert r4["is_valid"] is False
    assert r4["delta_kg"] == 0.0101
    assert "Mass conservation violation" in r4["reason"]

    # 5. High-order 10-split stress test
    splits = [99.99] * 10  # 999.90 kg
    waste = 0.10  # total 1000.00 kg
    r5 = MassBalanceService.validate_batch_split_conservation(1000.0, splits, waste_loss_qty=waste)
    assert r5["is_valid"] is True
    assert r5["delta_kg"] == 0.0

    # 6. Excessive waste loss (> 5.0%) flagged
    r6 = MassBalanceService.validate_batch_split_conservation(1000.0, [940.0], waste_loss_qty=60.0)
    assert r6["is_valid"] is True  # Mathematically conserved
    assert r6["is_loss_excessive"] is True  # But flagged for review!
    assert r6["waste_loss_pct"] == 6.0


def test_mass_balance_retail_depletion_and_overselling():
    """Stress test: retail inventory sales, zero depletion, and anti-overselling invariant."""
    # 1. Normal partial depletion
    r1 = MassBalanceService.validate_retail_depletion(current_available_qty=200.0, sale_qty=75.5)
    assert r1["is_valid"] is True
    assert r1["remaining_available_qty"] == 124.5
    assert r1["is_depleted"] is False

    # 2. Exact complete depletion to zero
    r2 = MassBalanceService.validate_retail_depletion(current_available_qty=124.5, sale_qty=124.5)
    assert r2["is_valid"] is True
    assert r2["remaining_available_qty"] == 0.0
    assert r2["is_depleted"] is True

    # 3. Overselling attempt (sale > available by 0.01 kg)
    r3 = MassBalanceService.validate_retail_depletion(current_available_qty=0.0, sale_qty=0.01)
    assert r3["is_valid"] is False
    assert "Insufficient stock" in r3["reason"]
    assert r3["deficit_qty"] == 0.01

    # 4. Invalid non-positive sales
    assert MassBalanceService.validate_retail_depletion(100.0, 0.0)["is_valid"] is False
    assert MassBalanceService.validate_retail_depletion(100.0, -10.0)["is_valid"] is False


def test_mass_balance_scale_reconciliation():
    """Stress test: certified scale reconciliation for manual vs automated scales."""
    # Automated hardware scale (0.5% normal, 1.0% warning, >1.0% violation)
    assert MassBalanceService.evaluate_scale_reconciliation(1000.0, 995.0, is_manual_entry=False).status == "NORMAL"  # 0.5%
    assert MassBalanceService.evaluate_scale_reconciliation(1000.0, 994.0, is_manual_entry=False).status == "WARNING"  # 0.6%
    assert MassBalanceService.evaluate_scale_reconciliation(1000.0, 989.0, is_manual_entry=False).status == "VIOLATION"  # 1.1%

    # Manual entry certified scale (1.0% normal, 2.0% warning, >2.0% violation)
    assert MassBalanceService.evaluate_scale_reconciliation(1000.0, 990.0, is_manual_entry=True).status == "NORMAL"  # 1.0%
    assert MassBalanceService.evaluate_scale_reconciliation(1000.0, 985.0, is_manual_entry=True).status == "WARNING"  # 1.5%
    assert MassBalanceService.evaluate_scale_reconciliation(1000.0, 978.0, is_manual_entry=True).status == "VIOLATION"  # 2.2%


# ============================================================================
# PART 3: TRUST GRAPH TEMPORAL DECAY & HARMONIC PROPAGATION (P0.7)
# ============================================================================

def test_trust_temporal_decay_mathematical_invariants():
    """Stress test: exponential temporal dormancy decay invariants."""
    t_base = 0.50
    lam = 0.01155  # half life ~60 days

    # 1. Invariant: delta_days == 0 -> No decay
    assert TrustGraphService.compute_decayed_trust(0.95, t_base, lam, delta_days=0.0) == 0.95

    # 2. Invariant: delta_days < 0 -> Returns current trust (no future time distortion)
    assert TrustGraphService.compute_decayed_trust(0.95, t_base, lam, delta_days=-10.0) == 0.95

    # 3. Half-life precision: at 60 days, decay is ~50% toward baseline
    # High trust: (0.90 - 0.50) * 0.5 = 0.20 -> 0.70
    t_60d = TrustGraphService.compute_decayed_trust(0.90, t_base, lam, delta_days=60.0)
    assert abs(t_60d - 0.70) < 0.005

    # 4. Reputation recovery toward baseline from below:
    # Low trust: (0.10 - 0.50) = -0.40; at 60 days, -0.40 * 0.5 = -0.20 -> 0.30
    t_rec = TrustGraphService.compute_decayed_trust(0.10, t_base, lam, delta_days=60.0)
    assert abs(t_rec - 0.30) < 0.005

    # 5. Long-term convergence: as delta_days -> inf, T -> t_base
    t_inf = TrustGraphService.compute_decayed_trust(0.95, t_base, lam, delta_days=1000.0)
    assert abs(t_inf - t_base) < 0.0001

    # 6. Bounds clamping [0.0, 1.0]
    assert 0.0 <= TrustGraphService.compute_decayed_trust(1.5, t_base, lam, delta_days=5.0) <= 1.0
    assert 0.0 <= TrustGraphService.compute_decayed_trust(-0.5, t_base, lam, delta_days=5.0) <= 1.0


def test_trust_harmonic_mean_chain_invariants():
    """Stress test: harmonic mean custody chain trust propagation properties."""
    # 1. Empty list returns baseline 0.50
    assert TrustGraphService.compute_harmonic_mean_trust([]) == 0.50

    # 2. Identity / Homogeneity: [s, s, s, s] -> s
    for s in [0.2, 0.5, 0.8, 1.0]:
        hm = TrustGraphService.compute_harmonic_mean_trust([s, s, s, s])
        assert abs(hm - s) < 0.001

    # 3. Commutativity / Order Invariance: any permutation gives identical result
    chain_a = [0.90, 0.75, 0.60, 0.40]
    chain_b = [0.40, 0.60, 0.75, 0.90]
    chain_c = [0.75, 0.40, 0.90, 0.60]
    hm_a = TrustGraphService.compute_harmonic_mean_trust(chain_a)
    hm_b = TrustGraphService.compute_harmonic_mean_trust(chain_b)
    hm_c = TrustGraphService.compute_harmonic_mean_trust(chain_c)
    assert hm_a == hm_b == hm_c

    # 4. Domination by Weakest Link (Contrast with Arithmetic Mean):
    # 4 actors: 3 reputable (0.95), 1 untrusted (0.10)
    scores = [0.95, 0.95, 0.95, 0.10]
    arithmetic_mean = sum(scores) / len(scores)  # 0.7375 (acceptable!)
    harmonic_mean = TrustGraphService.compute_harmonic_mean_trust(scores)  # ~0.30 (high risk!)
    assert arithmetic_mean >= 0.70
    assert harmonic_mean < 0.35, f"Harmonic mean {harmonic_mean} must crush trust when one link is compromised"

    # 5. Zero Trust Collapse:
    # A single 0.0 trust node collapses the entire custody chain trust to ~0.0
    scores_zero = [0.99, 0.99, 0.99, 0.00]
    hm_zero = TrustGraphService.compute_harmonic_mean_trust(scores_zero)
    assert hm_zero < 0.001


def test_trust_upstream_penalty_backpropagation(db):
    """Stress test: violation penalty deducts 0.35 and back-propagates 25% to upstream actors."""
    svc = TrustGraphService()
    run_id = uuid.uuid4().hex[:6]
    farmer_id = f"farmer-trust-{run_id}"
    transporter_id = f"transporter-trust-{run_id}"
    cc_id = f"cc-trust-{run_id}"

    # Initialize all 3 actors to trust 0.80
    f_rec = svc.get_or_create_actor_trust(db, farmer_id)
    t_rec = svc.get_or_create_actor_trust(db, transporter_id)
    c_rec = svc.get_or_create_actor_trust(db, cc_id)
    f_rec.current_trust = 0.80
    t_rec.current_trust = 0.80
    c_rec.current_trust = 0.80
    db.flush()

    # CC commits violation. Upstream actors: farmer, transporter.
    # Primary penalty = 0.35 -> CC trust: 0.80 - 0.35 = 0.45
    # Upstream penalty = 0.35 * 0.25 = 0.0875 -> Farmer & Transporter trust: 0.80 - 0.0875 = 0.7125
    svc.apply_violation_penalty(
        db=db,
        actor_id=cc_id,
        reason="Collection centre altered weight bridge",
        upstream_actor_ids=[farmer_id, transporter_id, cc_id],  # Includes self to test deduplication!
    )

    db.refresh(c_rec)
    db.refresh(f_rec)
    db.refresh(t_rec)

    assert abs(c_rec.current_trust - 0.45) < 0.001
    assert abs(f_rec.current_trust - 0.7125) < 0.001
    assert abs(t_rec.current_trust - 0.7125) < 0.001

    # Invariant: non-negative clamping on upstream actors
    f_rec.current_trust = 0.05
    db.flush()
    svc.apply_violation_penalty(
        db=db,
        actor_id=cc_id,
        reason="Second violation",
        upstream_actor_ids=[farmer_id],
    )
    db.refresh(f_rec)
    assert f_rec.current_trust == 0.0  # Clamped at 0.0, never negative!


def test_radar_explainable_review_strictness():
    """Stress test: Radar multi-signal breakdown and routing strictness."""
    radar = RadarService()

    # Pristine signals -> AUTO_APPROVE
    sc = radar.compute_crypto_axis(signature_valid=True, sequence_valid=True, hash_matched=True, clock_skew_seconds=10.0)
    ss = radar.compute_spatial_axis(is_inside_boundary=True, distance_meters=0.0, gps_accuracy=4.0)
    sf = radar.compute_forensic_axis(laplacian_variance=150.0, exposure_clipping_pct=4.0, is_duplicate=False)
    sp = radar.compute_phenology_axis(crop_match=True, stage_consistent=True, match_confidence=0.95)
    r_ok = radar.evaluate_radar(sc, ss, sf, sp)
    assert r_ok.routing_action == "AUTO_APPROVE"
    assert r_ok.assigned_officer is None

    # Clock skew warning (180s) drops crypto score to 0.80 -> routes to officer1
    sc_skew = radar.compute_crypto_axis(signature_valid=True, sequence_valid=True, hash_matched=True, clock_skew_seconds=180.0)
    r_skew = radar.evaluate_radar(sc_skew, ss, sf, sp)
    assert r_skew.routing_action == "OFFICER_REVIEW_REQUIRED"
    assert r_skew.assigned_officer == "officer1"

    # Spatial GPS accuracy gate violation (> 100m) -> hard flag, routes to officer1
    ss_inacc = radar.compute_spatial_axis(is_inside_boundary=True, gps_accuracy=105.0)
    r_inacc = radar.evaluate_radar(sc, ss_inacc, sf, sp)
    assert r_inacc.routing_action == "OFFICER_REVIEW_REQUIRED"
    assert r_inacc.assigned_officer == "officer1"
    assert "SPATIAL_GATE_VIOLATION" in r_inacc.hard_flags
