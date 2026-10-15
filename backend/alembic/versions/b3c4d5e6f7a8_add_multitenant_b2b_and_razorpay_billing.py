"""add_multitenant_b2b_and_razorpay_billing

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-10-15 19:40:00.000000

Creates multi-tenant B2B and Razorpay billing tables:
  - organizations
  - organization_members
  - api_keys
  - subscriptions
  - usage_quotas

Adds columns:
  - cases.tenant_id
  - users.b2c_plan_code
  - users.b2c_subscription_status
  - users.razorpay_customer_id
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers
revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. organizations ──────────────────────────────────────────────────
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), unique=True, nullable=False),
        sa.Column('tier', sa.String(length=50), server_default='starter', nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index('ix_organizations_id', 'organizations', ['id'])
    op.create_index('ix_organizations_slug', 'organizations', ['slug'])

    # ── 2. organization_members ───────────────────────────────────────────
    op.create_table(
        'organization_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(length=50), server_default='analyst', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=True),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.UniqueConstraint('org_id', 'user_id', name='uq_org_user'),
    )
    op.create_index('ix_organization_members_org_id', 'organization_members', ['org_id'])
    op.create_index('ix_organization_members_user_id', 'organization_members', ['user_id'])

    # ── 3. api_keys ───────────────────────────────────────────────────────
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('key_prefix', sa.String(length=12), nullable=False),
        sa.Column('key_hash', sa.String(length=64), unique=True, nullable=False),
        sa.Column('scopes', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
    )
    op.create_index('ix_api_keys_org_id', 'api_keys', ['org_id'])
    op.create_index('ix_api_keys_key_prefix', 'api_keys', ['key_prefix'])

    # ── 4. subscriptions ──────────────────────────────────────────────────
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('market', sa.String(length=10), nullable=False),
        sa.Column('plan_code', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='trialing', nullable=False),
        sa.Column('razorpay_customer_id', sa.String(length=100), nullable=True),
        sa.Column('razorpay_subscription_id', sa.String(length=100), nullable=True),
        sa.Column('razorpay_plan_id', sa.String(length=100), nullable=True),
        sa.Column('razorpay_order_id', sa.String(length=100), nullable=True),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'])
    op.create_index('ix_subscriptions_org_id', 'subscriptions', ['org_id'])
    op.create_index('ix_subscriptions_razorpay_subscription_id', 'subscriptions', ['razorpay_subscription_id'])

    # ── 5. usage_quotas ───────────────────────────────────────────────────
    op.create_table(
        'usage_quotas',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('period', sa.String(length=7), nullable=False),
        sa.Column('events_processed', sa.Integer(), server_default='0', nullable=False),
        sa.Column('monthly_limit', sa.Integer(), server_default='50000', nullable=False),
        sa.Column('overage_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_warned_pct', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.UniqueConstraint('org_id', 'period', name='uq_org_period'),
    )
    op.create_index('ix_usage_quotas_org_id', 'usage_quotas', ['org_id'])

    # ── 6. Add tenant_id to cases ─────────────────────────────────────────
    op.add_column('cases', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=True))
    op.create_index('ix_cases_tenant_id', 'cases', ['tenant_id'])

    # ── 7. Add subscription fields to users ───────────────────────────────
    op.add_column('users', sa.Column('b2c_plan_code', sa.String(), server_default='b2c_free', nullable=False))
    op.add_column('users', sa.Column('b2c_subscription_status', sa.String(), server_default='active', nullable=False))
    op.add_column('users', sa.Column('razorpay_customer_id', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'razorpay_customer_id')
    op.drop_column('users', 'b2c_subscription_status')
    op.drop_column('users', 'b2c_plan_code')
    op.drop_index('ix_cases_tenant_id', table_name='cases')
    op.drop_column('cases', 'tenant_id')
    op.drop_table('usage_quotas')
    op.drop_table('subscriptions')
    op.drop_table('api_keys')
    op.drop_table('organization_members')
    op.drop_table('organizations')
