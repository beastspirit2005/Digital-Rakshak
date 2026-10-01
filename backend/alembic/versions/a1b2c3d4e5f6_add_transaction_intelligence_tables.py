"""add_transaction_intelligence_tables

Revision ID: a1b2c3d4e5f6
Revises: ec8e91f05a89
Create Date: 2026-10-01 20:23:00.000000

Creates 8 tables required by the Transaction Intelligence pipeline:
  - transactions
  - transaction_features
  - transaction_scores
  - transaction_decisions
  - device_profiles
  - beneficiary_profiles
  - transaction_feedback
  - policy_rules
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'ec8e91f05a89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- transactions ---
    op.create_table(
        'transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('transaction_id', sa.String(), nullable=False),
        sa.Column('account_id', sa.String(), nullable=False),
        sa.Column('beneficiary_id', sa.String(), nullable=False),
        sa.Column('device_id', sa.String(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(), nullable=False, server_default='INR'),
        sa.Column('transaction_type', sa.String(), nullable=False, server_default='UPI'),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('city', sa.String(), nullable=True),
        sa.Column('state', sa.String(), nullable=True),
        sa.Column('channel', sa.String(), nullable=False, server_default='MOBILE'),
        sa.Column('status', sa.String(), nullable=False, server_default='PENDING'),
        sa.Column('raw_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_transactions_id', 'transactions', ['id'], unique=False)
    op.create_index('ix_transactions_transaction_id', 'transactions', ['transaction_id'], unique=True)
    op.create_index('ix_transactions_account_id', 'transactions', ['account_id'], unique=False)
    op.create_index('ix_transactions_beneficiary_id', 'transactions', ['beneficiary_id'], unique=False)
    op.create_index('ix_transactions_device_id', 'transactions', ['device_id'], unique=False)
    op.create_index('ix_transactions_timestamp', 'transactions', ['timestamp'], unique=False)
    op.create_index('ix_transactions_status', 'transactions', ['status'], unique=False)

    # --- transaction_features ---
    op.create_table(
        'transaction_features',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('feature_name', sa.String(), nullable=False),
        sa.Column('feature_value', sa.Float(), nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_transaction_features_id', 'transaction_features', ['id'], unique=False)
    op.create_index('ix_transaction_features_transaction_id', 'transaction_features', ['transaction_id'], unique=False)
    op.create_index('ix_transaction_features_feature_name', 'transaction_features', ['feature_name'], unique=False)

    # --- transaction_scores ---
    op.create_table(
        'transaction_scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('risk_score', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('risk_band', sa.String(), nullable=False),
        sa.Column('sub_scores', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('model_version', sa.String(), nullable=False, server_default='v1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_transaction_scores_id', 'transaction_scores', ['id'], unique=False)
    op.create_index('ix_transaction_scores_transaction_id', 'transaction_scores', ['transaction_id'], unique=True)
    op.create_index('ix_transaction_scores_risk_score', 'transaction_scores', ['risk_score'], unique=False)
    op.create_index('ix_transaction_scores_risk_band', 'transaction_scores', ['risk_band'], unique=False)

    # --- transaction_decisions ---
    op.create_table(
        'transaction_decisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('decision', sa.String(), nullable=False),
        sa.Column('policy_version', sa.String(), nullable=False, server_default='v1.0'),
        sa.Column('reason_codes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('explanation_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_transaction_decisions_id', 'transaction_decisions', ['id'], unique=False)
    op.create_index('ix_transaction_decisions_transaction_id', 'transaction_decisions', ['transaction_id'], unique=True)
    op.create_index('ix_transaction_decisions_decision', 'transaction_decisions', ['decision'], unique=False)

    # --- device_profiles ---
    op.create_table(
        'device_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('device_id', sa.String(), nullable=False),
        sa.Column('first_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_transactions', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('associated_accounts', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('risk_score', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('is_emulator', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('ip_addresses', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_device_profiles_id', 'device_profiles', ['id'], unique=False)
    op.create_index('ix_device_profiles_device_id', 'device_profiles', ['device_id'], unique=True)

    # --- beneficiary_profiles ---
    op.create_table(
        'beneficiary_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('beneficiary_id', sa.String(), nullable=False),
        sa.Column('account_number', sa.String(), nullable=True),
        sa.Column('ifsc_or_vpa', sa.String(), nullable=True),
        sa.Column('first_received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_received_amount', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('total_transactions', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('is_flagged', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('risk_score', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_beneficiary_profiles_id', 'beneficiary_profiles', ['id'], unique=False)
    op.create_index('ix_beneficiary_profiles_beneficiary_id', 'beneficiary_profiles', ['beneficiary_id'], unique=True)
    op.create_index('ix_beneficiary_profiles_account_number', 'beneficiary_profiles', ['account_number'], unique=False)
    op.create_index('ix_beneficiary_profiles_is_flagged', 'beneficiary_profiles', ['is_flagged'], unique=False)

    # --- transaction_feedback ---
    op.create_table(
        'transaction_feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('investigator_id', sa.String(), nullable=True),
        sa.Column('ai_risk_score', sa.Float(), nullable=False),
        sa.Column('ai_decision', sa.String(), nullable=False),
        sa.Column('human_decision', sa.String(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_transaction_feedback_id', 'transaction_feedback', ['id'], unique=False)
    op.create_index('ix_transaction_feedback_transaction_id', 'transaction_feedback', ['transaction_id'], unique=False)

    # --- policy_rules ---
    op.create_table(
        'policy_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('rule_name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('condition_expression', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=True, server_default='100'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_policy_rules_id', 'policy_rules', ['id'], unique=False)
    op.create_index('ix_policy_rules_rule_name', 'policy_rules', ['rule_name'], unique=True)


def downgrade() -> None:
    op.drop_table('policy_rules')
    op.drop_table('transaction_feedback')
    op.drop_table('beneficiary_profiles')
    op.drop_table('device_profiles')
    op.drop_table('transaction_decisions')
    op.drop_table('transaction_scores')
    op.drop_table('transaction_features')
    op.drop_table('transactions')
