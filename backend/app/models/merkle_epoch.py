import uuid
from sqlalchemy import Column, String, Integer, DateTime, Text, func
from backend.app.core.database import Base


class MerkleEpoch(Base):
    __tablename__ = "merkle_epochs"

    id = Column(String, primary_key=True, default=lambda: f"epoch-{uuid.uuid4()}")
    epoch_index = Column(Integer, nullable=False, unique=True, index=True)
    epoch_number = Column(Integer, nullable=True, index=True)  # alias for epoch_index
    epoch_root = Column(String(64), nullable=False, index=True)
    batch_count = Column(Integer, nullable=False)
    total_items = Column(Integer, nullable=False, default=0)
    total_item_count = Column(Integer, nullable=True, default=0)  # alias for total_items
    batch_ids_json = Column(Text, nullable=False)  # JSON list of constituent batch IDs
    checkpoint_id = Column(String, nullable=True)
    checkpoint_signature = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="COMMITTED")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

