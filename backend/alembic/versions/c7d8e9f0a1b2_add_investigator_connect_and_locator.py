"""add_investigator_connect_and_locator

Revision ID: c7d8e9f0a1b2
Revises: b3c4d5e6f7a8
Create Date: 2026-10-26 19:15:00.000000

Creates Investigator Connect, Official Locator, and Chat Safety tables:
  - case_assignments
  - case_events
  - audit_events
  - official_locations
  - case_messages
  - safety_reports
  - preserved_evidence_packages

Adds columns to cases:
  - urgency_level
  - assistance_reference
  - is_ongoing_fraud
  - estimated_loss_inr
  - triage_notes

Adds columns to users:
  - chat_safety_policy_version
  - chat_safety_accepted_at
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers
revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, Sequence[str], None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add columns to cases
    op.add_column('cases', sa.Column('urgency_level', sa.String(length=50), server_default='standard', nullable=False))
    op.add_column('cases', sa.Column('assistance_reference', sa.String(length=64), nullable=True))
    op.add_column('cases', sa.Column('is_ongoing_fraud', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('cases', sa.Column('estimated_loss_inr', sa.Float(), nullable=True))
    op.add_column('cases', sa.Column('triage_notes', sa.Text(), nullable=True))
    op.create_index(op.f('ix_cases_assistance_reference'), 'cases', ['assistance_reference'], unique=True)
    op.create_index(op.f('ix_cases_urgency_level'), 'cases', ['urgency_level'], unique=False)

    # 2. Add columns to users
    op.add_column('users', sa.Column('chat_safety_policy_version', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('chat_safety_accepted_at', sa.DateTime(timezone=True), nullable=True))

    # 3. Create case_assignments
    op.create_table(
        'case_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('assignee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='offered', nullable=False),
        sa.Column('decline_reason', sa.Text(), nullable=True),
        sa.Column('offered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_case_assignments_id'), 'case_assignments', ['id'], unique=False)
    op.create_index(op.f('ix_case_assignments_case_id'), 'case_assignments', ['case_id'], unique=False)
    op.create_index(op.f('ix_case_assignments_assignee_id'), 'case_assignments', ['assignee_id'], unique=False)
    op.create_index(op.f('ix_case_assignments_status'), 'case_assignments', ['status'], unique=False)

    # 4. Create case_events
    op.create_table(
        'case_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('actor_role', sa.String(length=50), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('old_value', sa.String(length=255), nullable=True),
        sa.Column('new_value', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_case_events_id'), 'case_events', ['id'], unique=False)
    op.create_index(op.f('ix_case_events_case_id'), 'case_events', ['case_id'], unique=False)
    op.create_index(op.f('ix_case_events_event_type'), 'case_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_case_events_created_at'), 'case_events', ['created_at'], unique=False)

    # 5. Create audit_events
    op.create_table(
        'audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('actor_role', sa.String(length=50), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=255), nullable=False),
        sa.Column('ip_address', sa.String(length=100), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index(op.f('ix_audit_events_id'), 'audit_events', ['id'], unique=False)
    op.create_index(op.f('ix_audit_events_actor_id'), 'audit_events', ['actor_id'], unique=False)
    op.create_index(op.f('ix_audit_events_action'), 'audit_events', ['action'], unique=False)
    op.create_index(op.f('ix_audit_events_resource_type'), 'audit_events', ['resource_type'], unique=False)
    op.create_index(op.f('ix_audit_events_resource_id'), 'audit_events', ['resource_id'], unique=False)

    # 6. Create official_locations
    op.create_table(
        'official_locations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('jurisdiction_level', sa.String(length=50), server_default='district', nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('district', sa.String(length=100), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('pincode', sa.String(length=10), nullable=True),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('helpline_number', sa.String(length=50), nullable=True),
        sa.Column('landline_number', sa.String(length=50), nullable=True),
        sa.Column('official_email', sa.String(length=120), nullable=True),
        sa.Column('nodal_officer_designation', sa.String(length=120), nullable=True),
        sa.Column('source_url', sa.String(length=500), nullable=False),
        sa.Column('source_authority', sa.String(length=200), nullable=False),
        sa.Column('verification_status', sa.String(length=50), server_default='officially_listed', nullable=False),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('review_due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_official_locations_id'), 'official_locations', ['id'], unique=False)
    op.create_index(op.f('ix_official_locations_state'), 'official_locations', ['state'], unique=False)
    op.create_index(op.f('ix_official_locations_district'), 'official_locations', ['district'], unique=False)
    op.create_index(op.f('ix_official_locations_city'), 'official_locations', ['city'], unique=False)
    op.create_index(op.f('ix_official_locations_pincode'), 'official_locations', ['pincode'], unique=False)
    op.create_index('idx_official_locations_state_dist', 'official_locations', ['state', 'district'], unique=False)
    op.create_index('idx_official_locations_lat_lng', 'official_locations', ['latitude', 'longitude'], unique=False)

    # 7. Create case_messages
    op.create_table(
        'case_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('attachments', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('moderation_flag', sa.String(length=50), server_default='clean', nullable=False),
        sa.Column('scanner_rule', sa.String(length=100), nullable=True),
        sa.Column('is_redacted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_case_messages_id'), 'case_messages', ['id'], unique=False)
    op.create_index(op.f('ix_case_messages_case_id'), 'case_messages', ['case_id'], unique=False)
    op.create_index(op.f('ix_case_messages_sender_id'), 'case_messages', ['sender_id'], unique=False)
    op.create_index(op.f('ix_case_messages_moderation_flag'), 'case_messages', ['moderation_flag'], unique=False)
    op.create_index(op.f('ix_case_messages_created_at'), 'case_messages', ['created_at'], unique=False)

    # 8. Create safety_reports
    op.create_table(
        'safety_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cases.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reported_message_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('case_messages.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reporter_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reported_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('reason_narrative', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='pending_review', nullable=False),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('decision', sa.String(length=64), nullable=True),
        sa.Column('decision_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_safety_reports_id'), 'safety_reports', ['id'], unique=False)
    op.create_index(op.f('ix_safety_reports_case_id'), 'safety_reports', ['case_id'], unique=False)
    op.create_index(op.f('ix_safety_reports_reported_message_id'), 'safety_reports', ['reported_message_id'], unique=False)
    op.create_index(op.f('ix_safety_reports_reporter_id'), 'safety_reports', ['reporter_id'], unique=False)
    op.create_index(op.f('ix_safety_reports_reported_user_id'), 'safety_reports', ['reported_user_id'], unique=False)
    op.create_index(op.f('ix_safety_reports_category'), 'safety_reports', ['category'], unique=False)
    op.create_index(op.f('ix_safety_reports_status'), 'safety_reports', ['status'], unique=False)
    op.create_index(op.f('ix_safety_reports_reviewer_id'), 'safety_reports', ['reviewer_id'], unique=False)
    op.create_index(op.f('ix_safety_reports_created_at'), 'safety_reports', ['created_at'], unique=False)

    # 9. Create preserved_evidence_packages
    op.create_table(
        'preserved_evidence_packages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('safety_reports.id', ondelete='CASCADE'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cases.id', ondelete='SET NULL'), nullable=True),
        sa.Column('context_window_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('package_sha256', sa.String(length=64), nullable=False),
        sa.Column('retention_until', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_legal_hold', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('access_log', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_preserved_evidence_packages_id'), 'preserved_evidence_packages', ['id'], unique=False)
    op.create_index(op.f('ix_preserved_evidence_packages_report_id'), 'preserved_evidence_packages', ['report_id'], unique=True)
    op.create_index(op.f('ix_preserved_evidence_packages_case_id'), 'preserved_evidence_packages', ['case_id'], unique=False)
    op.create_index(op.f('ix_preserved_evidence_packages_package_sha256'), 'preserved_evidence_packages', ['package_sha256'], unique=False)
    op.create_index(op.f('ix_preserved_evidence_packages_is_legal_hold'), 'preserved_evidence_packages', ['is_legal_hold'], unique=False)


def downgrade() -> None:
    op.drop_table('preserved_evidence_packages')
    op.drop_table('safety_reports')
    op.drop_table('case_messages')
    op.drop_table('official_locations')
    op.drop_table('audit_events')
    op.drop_table('case_events')
    op.drop_table('case_assignments')
    op.drop_column('users', 'chat_safety_accepted_at')
    op.drop_column('users', 'chat_safety_policy_version')
    op.drop_index(op.f('ix_cases_urgency_level'), table_name='cases')
    op.drop_index(op.f('ix_cases_assistance_reference'), table_name='cases')
    op.drop_column('cases', 'triage_notes')
    op.drop_column('cases', 'estimated_loss_inr')
    op.drop_column('cases', 'is_ongoing_fraud')
    op.drop_column('cases', 'assistance_reference')
    op.drop_column('cases', 'urgency_level')
