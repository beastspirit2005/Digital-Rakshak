"""add_v2_2_lifecycle_and_audit_tables

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c1d2
Create Date: 2026-11-08 22:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'e7f8a9b0c1d2'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create fraud_response_lifecycle_events table
    op.create_table(
        'fraud_response_lifecycle_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('correlation_id', sa.String(length=128), nullable=False, index=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('financial_transactions.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('escalation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bank_escalations.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('stage', sa.String(length=64), nullable=False, index=True),
        sa.Column('previous_stage', sa.String(length=64), nullable=True),
        sa.Column('actor_or_service', sa.String(length=128), nullable=False),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('transition_reason', sa.Text(), nullable=False),
        sa.Column('evidence_reference', sa.String(length=128), nullable=True),
        sa.Column('financial_snapshot', postgresql.JSONB(), nullable=True),
        sa.Column('metadata_payload', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('event_hash', sa.String(length=64), nullable=False, index=True),
        sa.Column('previous_event_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    )

    # 2. Create webhook_nonce_replay_cache table
    op.create_table(
        'webhook_nonce_replay_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('bank_code', sa.String(length=32), nullable=False, index=True),
        sa.Column('nonce', sa.String(length=128), nullable=False, unique=True, index=True),
        sa.Column('signature', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, index=True)
    )

    # 3. Create investigator_decision_audits table
    op.create_table(
        'investigator_decision_audits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('escalation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('bank_escalations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('investigator_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('decision', sa.String(length=32), nullable=False),
        sa.Column('reviewed_evidence_ids', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('statutory_powers_invoked', sa.String(length=64), nullable=False),
        sa.Column('decision_rationale', sa.Text(), nullable=False),
        sa.Column('authorization_token', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    )


def downgrade():
    op.drop_table('investigator_decision_audits')
    op.drop_table('webhook_nonce_replay_cache')
    op.drop_table('fraud_response_lifecycle_events')
