"""
Idempotent Database Migration Script for Multi-Tenant B2B & Billing
===================================================================
Applies table definitions and column additions directly using SQLAlchemy.
Safe to run multiple times against Neon/PostgreSQL.

Usage::

    python backend/scripts/patch_multitenant_db.py
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from infrastructure.db.session import engine, Base
import domain.models  # Registers all models including Organization, ApiKey, etc.


async def patch_multitenant_db():
    print("[*] Connecting to database...")
    async with engine.begin() as conn:
        print("[*] Creating all registered tables (organizations, api_keys, subscriptions, etc.)...")
        await conn.run_sync(Base.metadata.create_all)
        print("[+] Base.metadata.create_all completed.")

        print("[*] Checking and adding tenant_id column to cases if missing...")
        try:
            await conn.execute(text("""
                ALTER TABLE cases 
                ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES organizations(id);
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_cases_tenant_id ON cases (tenant_id);
            """))
            print("[+] cases.tenant_id column verified.")
        except Exception as e:
            print("[-] cases.tenant_id notice:", e)

        print("[*] Checking and adding B2C subscription columns to users if missing...")
        try:
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS b2c_plan_code VARCHAR DEFAULT 'b2c_free';
            """))
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS b2c_subscription_status VARCHAR DEFAULT 'active';
            """))
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS razorpay_customer_id VARCHAR;
            """))
            print("[+] users subscription columns verified.")
        except Exception as e:
            print("[-] users columns notice:", e)

    print("\n[SUCCESS] Multi-tenant and Razorpay billing schema patch complete!")


if __name__ == "__main__":
    asyncio.run(patch_multitenant_db())
