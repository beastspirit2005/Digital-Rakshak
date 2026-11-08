"""add_v2_3_outbox_and_fund_positions

Revision ID: g1a2b3c4d5e6
Revises: f1a2b3c4d5e6
Create Date: 2026-11-08 23:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'g1a2b3c4d5e6'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create institutional_outbox_events table
    op.create_table(
        'institutional_outbox_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_type', sa.String(length=64), nullable=False, index=True),
        sa.Column('aggregate_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('correlation_id', sa.String(length=128), nullable=False, index=True),
        sa.Column('payload', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='PENDING', index=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('available_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('locked_by', sa.String(length=128), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('aggregate_id', 'event_type', name='uq_outbox_aggregate_event')
    )

    # 2. Create financial_fund_positions table
    op.create_table(
        'financial_fund_positions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('financial_transactions.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('account_reference_masked', sa.String(length=64), nullable=False),
        sa.Column('bank_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bank_registry.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('original_amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('lien_amount', sa.Numeric(14, 2), nullable=False, server_default='0.00'),
        sa.Column('frozen_amount', sa.Numeric(14, 2), nullable=False, server_default='0.00'),
        sa.Column('recovered_amount', sa.Numeric(14, 2), nullable=False, server_default='0.00'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='ACTIVE', index=True),
        sa.Column('source_reference', sa.String(length=128), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    )

    # 3. Create evidence_checkpoints table
    op.create_table(
        'evidence_checkpoints',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('sequence_start', sa.Integer(), nullable=False),
        sa.Column('sequence_end', sa.Integer(), nullable=False),
        sa.Column('merkle_root_hash', sa.String(length=64), nullable=False, index=True),
        sa.Column('signature', sa.String(length=256), nullable=False),
        sa.Column('signing_key_id', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    )

    # 4. Create evidence_access_events table
    op.create_table(
        'evidence_access_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('actor_role', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False, index=True),
        sa.Column('evidence_reference', sa.String(length=128), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    )

    # 5. Add version column to bank_escalations for optimistic concurrency
    op.add_column('bank_escalations', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))


def downgrade():
    op.drop_column('bank_escalations', 'version')
    op.drop_table('evidence_access_events')
    op.drop_table('evidence_checkpoints')
    op.drop_table('financial_fund_positions')
    op.drop_table('institutional_outbox_events')
