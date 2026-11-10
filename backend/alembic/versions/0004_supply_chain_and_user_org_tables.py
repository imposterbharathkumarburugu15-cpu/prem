"""0004_supply_chain_and_user_org_tables

Revision ID: 0004_supply_chain_and_user_org_tables
Revises: 0003_boundary_tables_and_versioning
Create Date: 2026-11-10 16:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision: str = '0004_supply_chain_and_user_org_tables'
down_revision: Union[str, None] = '0003_boundary_tables_and_versioning'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = Inspector.from_engine(bind)
    existing_tables = set(insp.get_table_names())

    # 1. organizations
    if 'organizations' not in existing_tables:
        op.create_table(
            'organizations',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('name', sa.String(), nullable=False, unique=True),
            sa.Column('org_type', sa.String(), nullable=False),
            sa.Column('registration_number', sa.String(), nullable=True),
            sa.Column('contact_phone', sa.String(), nullable=True),
            sa.Column('contact_email', sa.String(), nullable=True),
            sa.Column('address', sa.String(), nullable=True),
            sa.Column('district', sa.String(), nullable=True),
            sa.Column('state', sa.String(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        )

    # 2. users
    if 'users' not in existing_tables:
        op.create_table(
            'users',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('username', sa.String(), nullable=False, unique=True),
            sa.Column('email', sa.String(), nullable=False, unique=True),
            sa.Column('hashed_password', sa.String(), nullable=False),
            sa.Column('full_name', sa.String(), nullable=False),
            sa.Column('role', sa.String(), nullable=False),
            sa.Column('organization_id', sa.String(), sa.ForeignKey('organizations.id'), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        )

    # 3. batches
    if 'batches' not in existing_tables:
        op.create_table(
            'batches',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('batch_code', sa.String(), nullable=False, unique=True),
            sa.Column('farm_id', sa.String(), sa.ForeignKey('farms.id'), nullable=True),
            sa.Column('crop_type', sa.String(), nullable=False),
            sa.Column('variety', sa.String(), nullable=True),
            sa.Column('harvest_date', sa.DateTime(), nullable=True),
            sa.Column('initial_quantity', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('current_quantity', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('unit', sa.String(), nullable=False, server_default='kg'),
            sa.Column('parent_batch_id', sa.String(), sa.ForeignKey('batches.id'), nullable=True),
            sa.Column('lineage_type', sa.String(), nullable=True),
            sa.Column('stage', sa.String(), nullable=False, server_default='FARM_HARVESTED'),
            sa.Column('status', sa.String(), nullable=False, server_default='ACTIVE'),
            sa.Column('collection_centre_id', sa.String(), sa.ForeignKey('organizations.id'), nullable=True),
            sa.Column('retailer_id', sa.String(), sa.ForeignKey('organizations.id'), nullable=True),
            sa.Column('quality_grade', sa.String(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        )

    # 4. shipments
    if 'shipments' not in existing_tables:
        op.create_table(
            'shipments',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('shipment_code', sa.String(), nullable=False, unique=True),
            sa.Column('transporter_org_id', sa.String(), sa.ForeignKey('organizations.id'), nullable=False),
            sa.Column('driver_id', sa.String(), nullable=True),
            sa.Column('driver_name', sa.String(), nullable=True),
            sa.Column('vehicle_reg', sa.String(), nullable=True),
            sa.Column('origin_name', sa.String(), nullable=False),
            sa.Column('origin_address', sa.String(), nullable=True),
            sa.Column('destination_name', sa.String(), nullable=False),
            sa.Column('destination_address', sa.String(), nullable=True),
            sa.Column('stage', sa.String(), nullable=False, server_default='ASSIGNED'),
            sa.Column('status', sa.String(), nullable=False, server_default='ACTIVE'),
            sa.Column('pickup_timestamp', sa.DateTime(), nullable=True),
            sa.Column('delivery_timestamp', sa.DateTime(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        )

    # 5. shipment_items
    if 'shipment_items' not in existing_tables:
        op.create_table(
            'shipment_items',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('shipment_id', sa.String(), sa.ForeignKey('shipments.id'), nullable=False),
            sa.Column('batch_id', sa.String(), sa.ForeignKey('batches.id'), nullable=False),
            sa.Column('declared_quantity', sa.Float(), nullable=False),
            sa.Column('picked_up_quantity', sa.Float(), nullable=True),
            sa.Column('delivered_quantity', sa.Float(), nullable=True),
            sa.Column('unit', sa.String(), nullable=False, server_default='kg'),
            sa.Column('condition', sa.String(), nullable=True, server_default='GOOD'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        )

    # 6. shipment_events
    if 'shipment_events' not in existing_tables:
        op.create_table(
            'shipment_events',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('shipment_id', sa.String(), sa.ForeignKey('shipments.id'), nullable=False),
            sa.Column('event_type', sa.String(), nullable=False),
            sa.Column('location_name', sa.String(), nullable=True),
            sa.Column('latitude', sa.Float(), nullable=True),
            sa.Column('longitude', sa.Float(), nullable=True),
            sa.Column('condition', sa.String(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('photo_evidence_hash', sa.String(64), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        )

    # 7. weighing_records
    if 'weighing_records' not in existing_tables:
        op.create_table(
            'weighing_records',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('batch_id', sa.String(), sa.ForeignKey('batches.id'), nullable=False),
            sa.Column('operator_id', sa.String(), nullable=False),
            sa.Column('measured_weight', sa.Float(), nullable=False),
            sa.Column('unit', sa.String(), nullable=False, server_default='kg'),
            sa.Column('is_manual_entry', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('scale_identifier', sa.String(), nullable=True),
            sa.Column('slip_photo_hash', sa.String(64), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        )

    # 8. quality_inspections
    if 'quality_inspections' not in existing_tables:
        op.create_table(
            'quality_inspections',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('batch_id', sa.String(), sa.ForeignKey('batches.id'), nullable=False),
            sa.Column('inspector_id', sa.String(), nullable=False),
            sa.Column('crop_category', sa.String(), nullable=False),
            sa.Column('grade', sa.String(), nullable=False),
            sa.Column('physical_condition', sa.String(), nullable=False),
            sa.Column('moisture_pct', sa.Float(), nullable=True),
            sa.Column('defect_notes', sa.Text(), nullable=True),
            sa.Column('decision', sa.String(), nullable=False),
            sa.Column('photo_evidence_hash', sa.String(64), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        )

    # 9. procurement_orders
    if 'procurement_orders' not in existing_tables:
        op.create_table(
            'procurement_orders',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('order_code', sa.String(), nullable=False, unique=True),
            sa.Column('retailer_org_id', sa.String(), sa.ForeignKey('organizations.id'), nullable=False),
            sa.Column('supplier_org_id', sa.String(), sa.ForeignKey('organizations.id'), nullable=False),
            sa.Column('batch_id', sa.String(), sa.ForeignKey('batches.id'), nullable=False),
            sa.Column('ordered_quantity', sa.Float(), nullable=False),
            sa.Column('unit_price', sa.Float(), nullable=True),
            sa.Column('currency', sa.String(), nullable=False, server_default='INR'),
            sa.Column('status', sa.String(), nullable=False, server_default='ORDERED'),
            sa.Column('invoice_number', sa.String(), nullable=True),
            sa.Column('received_quantity', sa.Float(), nullable=True),
            sa.Column('receiving_condition', sa.String(), nullable=True),
            sa.Column('receiving_photo_hash', sa.String(64), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('delivered_at', sa.DateTime(), nullable=True),
        )

    # 10. retailer_inventory
    if 'retailer_inventory' not in existing_tables:
        op.create_table(
            'retailer_inventory',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('retailer_org_id', sa.String(), sa.ForeignKey('organizations.id'), nullable=False),
            sa.Column('batch_id', sa.String(), sa.ForeignKey('batches.id'), nullable=False),
            sa.Column('crop_type', sa.String(), nullable=False),
            sa.Column('available_quantity', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('unit', sa.String(), nullable=False, server_default='kg'),
            sa.Column('storage_location', sa.String(), nullable=True),
            sa.Column('opaque_qr_token', sa.String(128), nullable=True, unique=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        )

    # 11. challenge_responses
    if 'challenge_responses' not in existing_tables:
        op.create_table(
            'challenge_responses',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('challenge_id', sa.String(), nullable=False),
            sa.Column('evidence_id', sa.String(), sa.ForeignKey('evidence.id'), nullable=True),
            sa.Column('officer_id', sa.String(), nullable=False),
            sa.Column('challenge_type', sa.String(), nullable=False),
            sa.Column('reason_code', sa.String(), nullable=False),
            sa.Column('instructions', sa.Text(), nullable=False),
            sa.Column('status', sa.String(), nullable=False, server_default='PENDING'),
            sa.Column('response_notes', sa.Text(), nullable=True),
            sa.Column('response_evidence_id', sa.String(), sa.ForeignKey('evidence.id'), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('responded_at', sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table('challenge_responses')
    op.drop_table('retailer_inventory')
    op.drop_table('procurement_orders')
    op.drop_table('quality_inspections')
    op.drop_table('weighing_records')
    op.drop_table('shipment_events')
    op.drop_table('shipment_items')
    op.drop_table('shipments')
    op.drop_table('batches')
    op.drop_table('users')
    op.drop_table('organizations')

