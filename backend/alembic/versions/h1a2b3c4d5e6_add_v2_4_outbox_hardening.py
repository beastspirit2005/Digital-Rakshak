"""add_v2_4_outbox_hardening

Revision ID: h1a2b3c4d5e6
Revises: g1a2b3c4d5e6
Create Date: 2026-11-09 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'h1a2b3c4d5e6'
down_revision = 'g1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add lease recovery and error categorization columns to institutional_outbox_events
    op.add_column(
        'institutional_outbox_events',
        sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'institutional_outbox_events',
        sa.Column('last_error_code', sa.String(length=64), nullable=True)
    )

    # 2. Add composite indexes to optimize SKIP LOCKED sweep and lease recovery queries
    op.create_index(
        'ix_outbox_status_available',
        'institutional_outbox_events',
        ['status', 'available_at']
    )
    op.create_index(
        'ix_outbox_status_lease',
        'institutional_outbox_events',
        ['status', 'lease_expires_at']
    )

    # 3. Create outbox_worker_runs execution history and heartbeat audit table
    op.create_table(
        'outbox_worker_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('worker_id', sa.String(length=128), nullable=False, index=True),
        sa.Column('trigger_type', sa.String(length=32), nullable=False, server_default='CRON'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('events_claimed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('events_processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('events_retry_scheduled', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('events_dead_lettered', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='RUNNING', index=True),
        sa.Column('error_summary', sa.Text(), nullable=True)
    )


def downgrade():
    op.drop_table('outbox_worker_runs')
    op.drop_index('ix_outbox_status_lease', table_name='institutional_outbox_events')
    op.drop_index('ix_outbox_status_available', table_name='institutional_outbox_events')
    op.drop_column('institutional_outbox_events', 'last_error_code')
    op.drop_column('institutional_outbox_events', 'lease_expires_at')
