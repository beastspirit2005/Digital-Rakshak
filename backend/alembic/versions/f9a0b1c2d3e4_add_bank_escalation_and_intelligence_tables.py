"""add_bank_escalation_and_intelligence_tables

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-11-05 20:30:00.000000

Adds Bank Intelligence & Escalation tables:
  - bank_registry
  - financial_transactions
  - bank_escalations
  - bank_delivery_attempts
  - bank_responses
"""
from typing import Sequence, Union
from alembic import op

# revision identifiers
revision: str = 'f9a0b1c2d3e4'
down_revision: Union[str, Sequence[str], None] = 'e8f9a0b1c2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. bank_registry
    op.execute("""
    CREATE TABLE IF NOT EXISTS bank_registry (
        id UUID PRIMARY KEY,
        bank_code VARCHAR(32) UNIQUE NOT NULL,
        bank_name VARCHAR(255) NOT NULL,
        rbi_code VARCHAR(32),
        ifsc_prefix VARCHAR(10) NOT NULL,
        supported_rails JSONB DEFAULT '["UPI", "IMPS", "NEFT", "RTGS"]'::jsonb NOT NULL,
        escalation_channels JSONB DEFAULT '{"api": true, "nodal_email": true}'::jsonb NOT NULL,
        integration_type VARCHAR(32) DEFAULT 'SANDBOX_API' NOT NULL,
        api_endpoint VARCHAR(500),
        nodal_email VARCHAR(255),
        is_active BOOLEAN DEFAULT TRUE NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_bank_registry_code ON bank_registry(bank_code)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bank_registry_ifsc_prefix ON bank_registry(ifsc_prefix)")

    # 2. financial_transactions
    op.execute("""
    CREATE TABLE IF NOT EXISTS financial_transactions (
        id UUID PRIMARY KEY,
        case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
        transaction_reference VARCHAR(64),
        amount DOUBLE PRECISION NOT NULL,
        currency VARCHAR(10) DEFAULT 'INR' NOT NULL,
        payment_rail VARCHAR(32) DEFAULT 'UPI' NOT NULL,
        transaction_time TIMESTAMP WITH TIME ZONE,
        remitter_bank_id UUID REFERENCES bank_registry(id) ON DELETE SET NULL,
        remitter_account_masked VARCHAR(64),
        remitter_vpa VARCHAR(255),
        beneficiary_bank_id UUID REFERENCES bank_registry(id) ON DELETE SET NULL,
        beneficiary_account_masked VARCHAR(64),
        beneficiary_vpa VARCHAR(255),
        verification_status VARCHAR(32) DEFAULT 'EXTRACTED_UNVERIFIED' NOT NULL,
        raw_extraction JSONB DEFAULT '{}'::jsonb NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_fin_txns_case_id ON financial_transactions(case_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fin_txns_ref ON financial_transactions(transaction_reference)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fin_txns_remitter_bank ON financial_transactions(remitter_bank_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fin_txns_beneficiary_bank ON financial_transactions(beneficiary_bank_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fin_txns_status ON financial_transactions(verification_status)")

    # 3. bank_escalations
    op.execute("""
    CREATE TABLE IF NOT EXISTS bank_escalations (
        id UUID PRIMARY KEY,
        case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
        transaction_id UUID REFERENCES financial_transactions(id) ON DELETE SET NULL,
        alert_reference VARCHAR(64) UNIQUE NOT NULL,
        target_bank_id UUID NOT NULL REFERENCES bank_registry(id) ON DELETE CASCADE,
        escalation_role VARCHAR(32) NOT NULL,
        approval_tier VARCHAR(32) DEFAULT 'INVESTIGATOR_APPROVED' NOT NULL,
        status VARCHAR(32) DEFAULT 'DRAFT' NOT NULL,
        priority VARCHAR(16) DEFAULT 'MEDIUM' NOT NULL,
        alert_payload JSONB NOT NULL,
        approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
        approved_at TIMESTAMP WITH TIME ZONE,
        idempotency_key VARCHAR(128) UNIQUE NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_bank_escalations_case ON bank_escalations(case_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bank_escalations_alert_ref ON bank_escalations(alert_reference)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bank_escalations_target_bank ON bank_escalations(target_bank_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bank_escalations_status ON bank_escalations(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bank_escalations_idempotency ON bank_escalations(idempotency_key)")

    # 4. bank_delivery_attempts
    op.execute("""
    CREATE TABLE IF NOT EXISTS bank_delivery_attempts (
        id UUID PRIMARY KEY,
        escalation_id UUID NOT NULL REFERENCES bank_escalations(id) ON DELETE CASCADE,
        attempt_number INT DEFAULT 1 NOT NULL,
        channel VARCHAR(32) DEFAULT 'API' NOT NULL,
        http_status_code INT,
        response_body JSONB,
        delivery_status VARCHAR(32) NOT NULL,
        error_message TEXT,
        attempted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_bank_delivery_escalation ON bank_delivery_attempts(escalation_id)")

    # 5. bank_responses
    op.execute("""
    CREATE TABLE IF NOT EXISTS bank_responses (
        id UUID PRIMARY KEY,
        escalation_id UUID NOT NULL REFERENCES bank_escalations(id) ON DELETE CASCADE,
        bank_reference_number VARCHAR(128),
        response_type VARCHAR(64) NOT NULL,
        status_summary VARCHAR(128) NOT NULL,
        details JSONB DEFAULT '{}'::jsonb NOT NULL,
        received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_bank_responses_escalation ON bank_responses(escalation_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bank_responses_ref ON bank_responses(bank_reference_number)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS bank_responses CASCADE")
    op.execute("DROP TABLE IF EXISTS bank_delivery_attempts CASCADE")
    op.execute("DROP TABLE IF EXISTS bank_escalations CASCADE")
    op.execute("DROP TABLE IF EXISTS financial_transactions CASCADE")
    op.execute("DROP TABLE IF EXISTS bank_registry CASCADE")
