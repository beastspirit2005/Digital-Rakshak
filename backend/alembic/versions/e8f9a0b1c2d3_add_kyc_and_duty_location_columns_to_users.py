"""add_kyc_and_duty_location_columns_to_users

Revision ID: e8f9a0b1c2d3
Revises: c7d8e9f0a1b2
Create Date: 2026-10-28 19:00:00.000000

Adds official duty location and KYC columns to users table:
  - is_verified
  - latitude, longitude, city, state
  - station_name, badge_number, designation
  - kyc_org_id_path, kyc_org_id_filename
  - kyc_aadhaar_path, kyc_aadhaar_filename
  - kyc_submitted_at, kyc_reviewed_by, kyc_review_notes
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers
revision: str = 'e8f9a0b1c2d3'
down_revision: Union[str, Sequence[str], None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Use execute with IF NOT EXISTS to be safe with existing columns
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS city VARCHAR(100);")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS state VARCHAR(100);")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS station_name VARCHAR(255);")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS badge_number VARCHAR(50);")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS designation VARCHAR(120);")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_org_id_path VARCHAR(500);")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_org_id_filename VARCHAR(255);")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_aadhaar_path VARCHAR(500);")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_aadhaar_filename VARCHAR(255);")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_submitted_at TIMESTAMPTZ;")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_reviewed_by UUID REFERENCES users(id);")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_review_notes TEXT;")
    op.execute("UPDATE users SET is_verified = TRUE WHERE is_approved = TRUE;")

def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_verified;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS latitude;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS longitude;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS city;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS state;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS station_name;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS badge_number;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS designation;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS kyc_org_id_path;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS kyc_org_id_filename;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS kyc_aadhaar_path;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS kyc_aadhaar_filename;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS kyc_submitted_at;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS kyc_reviewed_by;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS kyc_review_notes;")
