"""Tier 2 Epoch Merkle Rollup Service (P0.9).
Aggregates multiple Tier 1 batch roots into an Epoch Merkle Tree,
creates signed NIST P-256 Authority Checkpoints with odd-node promotion,
and generates and verifies two-tier inclusion proofs.
"""

from typing import Dict, Any, List, Optional, Union
import uuid
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.merkle_batch import MerkleBatch
from backend.app.models.merkle_epoch import MerkleEpoch
from backend.app.models.evidence import Evidence
from backend.app.services.merkle_service import MerkleService
from crypto.merkle import MerkleTree, leaf_hash, leaf_hash_hex, verify_merkle_proof
from crypto.authority import (
    create_signed_checkpoint,
    verify_checkpoint_signature,
    get_authority_public_key_pem,
)
from crypto.rfc8785 import canonicalize


class EpochMerkleService:
    """Aggregates Tier 1 batch roots into Epoch Merkle Trees with two-tier proofs."""

    DEFAULT_AUTHORITY_ID = "praman-root-authority-1"

    @classmethod
    def create_epoch(
        cls,
        db: Session,
        batch_ids: Optional[List[str]] = None,
        authority_id: str = DEFAULT_AUTHORITY_ID,
    ) -> MerkleEpoch:
        """Aggregates unsealed or specified committed Merkle batches into a new MerkleEpoch.
        
        Args:
            db: SQLAlchemy session.
            batch_ids: Optional explicit list of batch IDs to include.
            authority_id: Authority identifier signing the epoch checkpoint.
            
        Returns:
            Created MerkleEpoch instance.
            
        Raises:
            ValueError: If no eligible unsealed batches exist or batch is already sealed.
        """
        if batch_ids is not None:
            if not batch_ids:
                raise ValueError("batch_ids list cannot be empty")
            batches = (
                db.query(MerkleBatch)
                .filter(MerkleBatch.id.in_(batch_ids))
                .order_by(MerkleBatch.created_at.asc(), MerkleBatch.id.asc())
                .all()
            )
            if len(batches) != len(batch_ids):
                raise ValueError("One or more specified batches do not exist")
            for b in batches:
                if b.epoch_id is not None:
                    raise ValueError(f"Batch {b.id} is already rolled into epoch {b.epoch_id}")
        else:
            batches = (
                db.query(MerkleBatch)
                .filter(MerkleBatch.epoch_id.is_(None))
                .order_by(MerkleBatch.created_at.asc(), MerkleBatch.id.asc())
                .all()
            )

        if not batches:
            raise ValueError("No eligible unsealed batches found for epoch creation")

        # Build Tier 2 Canonical Batch Leaf Descriptors
        raw_leaves: List[bytes] = []
        ordered_batch_ids = [b.id for b in batches]
        for b in batches:
            batch_leaf = {
                "batch_id": b.id,
                "checkpoint_id": b.checkpoint_id or f"cp-{b.id}",
                "leaf_count": b.leaf_count,
                "merkle_root": b.merkle_root,
            }
            raw_leaves.append(canonicalize(batch_leaf))

        # Build MerkleTree with odd-node promotion
        tree = MerkleTree(leaves_data=raw_leaves)
        epoch_root = tree.root_hex
        if not epoch_root:
            raise ValueError("Failed to compute epoch Merkle root")

        # Monotonic Epoch Number
        max_idx = db.query(func.max(MerkleEpoch.epoch_index)).scalar()
        epoch_index = (max_idx or 0) + 1

        # Checkpoint Signing
        timestamp_now = datetime.now(timezone.utc)
        ts_str = timestamp_now.strftime("%Y%m%d%H%M%S")
        checkpoint_id = f"cp-{ts_str}-epoch-{epoch_index:04d}-{uuid.uuid4().hex[:8]}"
        iso_timestamp = MerkleService.checkpoint_id_to_iso_timestamp(checkpoint_id)
        checkpoint_dict = create_signed_checkpoint(
            checkpoint_id=checkpoint_id,
            merkle_root=epoch_root,
            leaf_count=len(batches),
            timestamp=iso_timestamp,
            authority_id=authority_id,
        )

        total_items = sum(b.leaf_count for b in batches)

        epoch_record = MerkleEpoch(
            id=f"epoch-{uuid.uuid4()}",
            epoch_index=epoch_index,
            epoch_number=epoch_index,
            epoch_root=epoch_root,
            batch_count=len(batches),
            total_items=total_items,
            total_item_count=total_items,
            batch_ids_json=json.dumps(ordered_batch_ids),
            checkpoint_id=checkpoint_dict["checkpoint_id"],
            checkpoint_signature=checkpoint_dict["signature"],
            status="COMMITTED",
        )
        db.add(epoch_record)
        db.flush()

        # Link batches to this epoch
        for b in batches:
            b.epoch_id = epoch_record.id

        db.flush()
        return epoch_record

    @staticmethod
    def get_latest_epoch(db: Session) -> Optional[MerkleEpoch]:
        """Returns the most recently sealed MerkleEpoch."""
        return (
            db.query(MerkleEpoch)
            .order_by(MerkleEpoch.epoch_index.desc())
            .first()
        )

    @staticmethod
    def get_epoch(db: Session, epoch_id: str) -> Optional[MerkleEpoch]:
        """Returns MerkleEpoch by ID or epoch index string."""
        if epoch_id.isdigit():
            return db.query(MerkleEpoch).filter(MerkleEpoch.epoch_index == int(epoch_id)).first()
        return db.query(MerkleEpoch).filter(MerkleEpoch.id == epoch_id).first()

    @classmethod
    def get_dual_tier_proof(
        cls,
        db: Session,
        evidence_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Generates dual-tier inclusion proof connecting Evidence to Epoch Root."""
        # Step 1: Tier 1 Proof (Evidence -> Batch Root)
        t1 = MerkleService.get_evidence_inclusion_proof(db, evidence_id)
        if not t1:
            return None

        batch = db.query(MerkleBatch).filter(MerkleBatch.id == t1["batch_id"]).first()
        if not batch or not batch.epoch_id:
            return None

        # Step 2: Retrieve Epoch
        epoch = db.query(MerkleEpoch).filter(MerkleEpoch.id == batch.epoch_id).first()
        if not epoch:
            return None

        batch_ids: List[str] = json.loads(epoch.batch_ids_json)
        if batch.id not in batch_ids:
            return None

        # Step 3: Rebuild Tier 2 tree from epoch constituent batches
        batches = (
            db.query(MerkleBatch)
            .filter(MerkleBatch.id.in_(batch_ids))
            .all()
        )
        batch_map = {b.id: b for b in batches}

        raw_leaves: List[bytes] = []
        for bid in batch_ids:
            b = batch_map[bid]
            batch_leaf = {
                "batch_id": b.id,
                "checkpoint_id": b.checkpoint_id or f"cp-{b.id}",
                "leaf_count": b.leaf_count,
                "merkle_root": b.merkle_root,
            }
            raw_leaves.append(canonicalize(batch_leaf))

        t2_tree = MerkleTree(leaves_data=raw_leaves)
        batch_index = batch_ids.index(batch.id)
        t2_proof_steps = t2_tree.get_inclusion_proof(batch_index)

        return {
            "evidence_id": evidence_id,
            "tier1_proof": {
                "batch_id": batch.id,
                "leaf_index": t1["leaf_index"],
                "leaf_hash": t1["leaf_hash"],
                "batch_merkle_root": batch.merkle_root,
                "audit_path": t1["inclusion_proof"],
                "checkpoint": t1["checkpoint"],
            },
            "tier2_proof": {
                "epoch_id": epoch.id,
                "epoch_index": epoch.epoch_index,
                "batch_leaf_index": batch_index,
                "batch_leaf_hash": leaf_hash_hex(raw_leaves[batch_index]),
                "epoch_root": epoch.epoch_root,
                "audit_path": [
                    step.to_dict() if hasattr(step, "to_dict") else step
                    for step in t2_proof_steps
                ],
                "checkpoint": {
                    "checkpoint_id": epoch.checkpoint_id,
                    "merkle_root": epoch.epoch_root,
                    "leaf_count": epoch.batch_count,
                    "timestamp": MerkleService.checkpoint_id_to_iso_timestamp(epoch.checkpoint_id),
                    "authority_id": cls.DEFAULT_AUTHORITY_ID,
                    "signature": epoch.checkpoint_signature,
                },
            },
        }

    @classmethod
    def verify_dual_tier_proof(
        cls,
        envelope_canonical_bytes: bytes,
        proof_bundle: Dict[str, Any],
        authority_pub_pem: Optional[str] = None,
    ) -> bool:
        """Independently verifies dual-tier inclusion proof and epoch checkpoint signature."""
        try:
            t1 = proof_bundle.get("tier1_proof")
            t2 = proof_bundle.get("tier2_proof")
            if not t1 or not t2:
                return False

            # 1. Verify Tier 1: Evidence -> Batch Merkle Root
            t1_valid = verify_merkle_proof(
                leaf_data=envelope_canonical_bytes,
                proof=t1["audit_path"],
                expected_root=t1["batch_merkle_root"],
            )
            if not t1_valid:
                return False

            # 2. Reconstruct Canonical Batch Leaf for Tier 2
            batch_leaf_dict = {
                "batch_id": t1["batch_id"],
                "checkpoint_id": t1["checkpoint"]["checkpoint_id"],
                "leaf_count": t1["checkpoint"].get("leaf_count", 1),
                "merkle_root": t1["batch_merkle_root"],
            }
            batch_canonical_bytes = canonicalize(batch_leaf_dict)

            # 3. Verify Tier 2: Batch Leaf -> Epoch Merkle Root
            t2_valid = verify_merkle_proof(
                leaf_data=batch_canonical_bytes,
                proof=t2["audit_path"],
                expected_root=t2["epoch_root"],
            )
            if not t2_valid:
                return False

            # 4. Verify Epoch Checkpoint Signature
            epoch_cp = t2["checkpoint"]
            sig_valid = verify_checkpoint_signature(
                checkpoint_dict=epoch_cp,
                signature_b64=epoch_cp["signature"],
                authority_pub_pem=authority_pub_pem,
            )
            return sig_valid
        except Exception:
            return False
