"""0005_add_merkle_epochs_and_trust_tables

Revision ID: 0005_merkle_epoch_trust
Revises: 0004_supply_chain_and_user_org_tables
Create Date: 2026-11-11 19:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision: str = '0005_merkle_epoch_trust'
down_revision: Union[str, None] = '0004_supply_chain_and_user_org_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = Inspector.from_engine(bind)
    existing_tables = set(insp.get_table_names())

    # 1. merkle_epochs
    if 'merkle_epochs' not in existing_tables:
        op.create_table(
            'merkle_epochs',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('epoch_index', sa.Integer(), nullable=False),
            sa.Column('epoch_number', sa.Integer(), nullable=True),
            sa.Column('epoch_root', sa.String(length=64), nullable=False),
            sa.Column('batch_count', sa.Integer(), nullable=False),
            sa.Column('total_items', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('total_item_count', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('batch_ids_json', sa.Text(), nullable=False),
            sa.Column('checkpoint_id', sa.String(), nullable=True),
            sa.Column('checkpoint_signature', sa.Text(), nullable=True),
            sa.Column('status', sa.String(), nullable=False, server_default='COMMITTED'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        )
        op.create_index('ix_merkle_epochs_epoch_index', 'merkle_epochs', ['epoch_index'], unique=True)
        op.create_index('ix_merkle_epochs_epoch_number', 'merkle_epochs', ['epoch_number'], unique=False)
        op.create_index('ix_merkle_epochs_epoch_root', 'merkle_epochs', ['epoch_root'], unique=False)

    # 2. Add epoch_id column to merkle_batches if not present
    existing_columns = [col['name'] for col in insp.get_columns('merkle_batches')] if 'merkle_batches' in existing_tables else []
    if 'epoch_id' not in existing_columns and 'merkle_batches' in existing_tables:
        op.add_column('merkle_batches', sa.Column('epoch_id', sa.String(), nullable=True))
        op.create_index('ix_merkle_batches_epoch_id', 'merkle_batches', ['epoch_id'], unique=False)

    # 3. actor_trust_scores
    if 'actor_trust_scores' not in existing_tables:
        op.create_table(
            'actor_trust_scores',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('actor_id', sa.String(), nullable=False),
            sa.Column('actor_type', sa.String(), nullable=False),
            sa.Column('current_trust', sa.Float(), nullable=False, server_default='0.50'),
            sa.Column('baseline_trust', sa.Float(), nullable=False, server_default='0.50'),
            sa.Column('decay_lambda', sa.Float(), nullable=False, server_default='0.01155'),
            sa.Column('total_submissions', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('successful_submissions', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('violation_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('last_activity_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        )
        op.create_index('ix_actor_trust_scores_actor_id', 'actor_trust_scores', ['actor_id'], unique=True)
        op.create_index('ix_actor_trust_scores_actor_type', 'actor_trust_scores', ['actor_type'], unique=False)

    # 4. trust_events
    if 'trust_events' not in existing_tables:
        op.create_table(
            'trust_events',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('actor_id', sa.String(), sa.ForeignKey('actor_trust_scores.actor_id'), nullable=False),
            sa.Column('event_type', sa.String(), nullable=False),
            sa.Column('score_before', sa.Float(), nullable=False),
            sa.Column('score_after', sa.Float(), nullable=False),
            sa.Column('delta', sa.Float(), nullable=False),
            sa.Column('reference_id', sa.String(), nullable=True),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        )
        op.create_index('ix_trust_events_actor_id', 'trust_events', ['actor_id'], unique=False)
        op.create_index('ix_trust_events_reference_id', 'trust_events', ['reference_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = Inspector.from_engine(bind)
    existing_tables = set(insp.get_table_names())

    if 'trust_events' in existing_tables:
        op.drop_table('trust_events')
    if 'actor_trust_scores' in existing_tables:
        op.drop_table('actor_trust_scores')
    if 'merkle_batches' in existing_tables:
        cols = [col['name'] for col in insp.get_columns('merkle_batches')]
        if 'epoch_id' in cols:
            indices = [idx['name'] for idx in insp.get_indexes('merkle_batches')]
            if 'ix_merkle_batches_epoch_id' in indices:
                op.drop_index('ix_merkle_batches_epoch_id', table_name='merkle_batches')
            op.drop_column('merkle_batches', 'epoch_id')
    if 'merkle_epochs' in existing_tables:
        op.drop_table('merkle_epochs')
