"""harden_bank_v2_1_precision_and_legal

Revision ID: e7f8a9b0c1d2
Revises: f9a0b1c2d3e4
Create Date: 2026-11-08 22:38:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e7f8a9b0c1d2'
down_revision = 'f9a0b1c2d3e4'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Update financial_transactions with Numeric precision and multi-tier reconciliation columns
    op.alter_column('financial_transactions', 'amount',
                    existing_type=sa.Float(),
                    type_=sa.Numeric(precision=14, scale=2),
                    existing_nullable=False)
    
    op.add_column('financial_transactions', sa.Column('reported_loss_amount', sa.Numeric(precision=14, scale=2), nullable=True))
    op.add_column('financial_transactions', sa.Column('amount_under_lien', sa.Numeric(precision=14, scale=2), server_default='0.00', nullable=False))
    op.add_column('financial_transactions', sa.Column('amount_frozen', sa.Numeric(precision=14, scale=2), server_default='0.00', nullable=False))
    op.add_column('financial_transactions', sa.Column('amount_recovered', sa.Numeric(precision=14, scale=2), server_default='0.00', nullable=False))
    op.add_column('financial_transactions', sa.Column('beneficiary_bank_confidence', sa.String(length=32), server_default='CANDIDATE_PSP_ROUTING', nullable=False))

    # 2. Update bank_escalations with instruction categories and statutory basis
    op.add_column('bank_escalations', sa.Column('instruction_category', sa.String(length=32), server_default='INFORMATIONAL_ALERT', nullable=False))
    op.add_column('bank_escalations', sa.Column('statutory_basis', sa.String(length=64), server_default='RBI_CUSTOMER_PROTECTION_2017', nullable=False))
    op.add_column('bank_escalations', sa.Column('beneficiary_bank_confidence', sa.String(length=32), server_default='CANDIDATE_PSP_ROUTING', nullable=False))

    # 3. Update bank_responses with Numeric precision
    op.add_column('bank_responses', sa.Column('funds_frozen_amount', sa.Numeric(precision=14, scale=2), nullable=True))
    op.add_column('bank_responses', sa.Column('funds_actioned_amount', sa.Numeric(precision=14, scale=2), nullable=True))


def downgrade():
    op.drop_column('bank_responses', 'funds_actioned_amount')
    op.drop_column('bank_responses', 'funds_frozen_amount')

    op.drop_column('bank_escalations', 'beneficiary_bank_confidence')
    op.drop_column('bank_escalations', 'statutory_basis')
    op.drop_column('bank_escalations', 'instruction_category')

    op.drop_column('financial_transactions', 'beneficiary_bank_confidence')
    op.drop_column('financial_transactions', 'amount_recovered')
    op.drop_column('financial_transactions', 'amount_frozen')
    op.drop_column('financial_transactions', 'amount_under_lien')
    op.drop_column('financial_transactions', 'reported_loss_amount')

    op.alter_column('financial_transactions', 'amount',
                    existing_type=sa.Numeric(precision=14, scale=2),
                    type_=sa.Float(),
                    existing_nullable=False)
