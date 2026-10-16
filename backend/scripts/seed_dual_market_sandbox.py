"""
Seed Sandbox Data for Digital Rakshak Dual-Market Architecture
=============================================================
Creates:
1. Demo Enterprise Organization ("Apex Nodal Cyber Cell & FinTech Labs").
2. Two pre-configured B2B machine API keys.
3. Realistic monthly usage quota metrics.
4. Pre-populated sample threat patterns.

Usage::

    python backend/scripts/seed_dual_market_sandbox.py
"""
import sys
import os
import asyncio
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from infrastructure.db.session import AsyncSessionLocal
from domain.models.organization import (
    Organization,
    ApiKey,
    UsageQuota,
    OrgTier,
    Subscription,
    SubscriptionStatus,
    PlanCode,
    MarketSegment,
)


DEMO_ORG_SLUG = "apex-nodal-labs"
DEMO_API_KEY_PLAINTEXT = "dr_test_demo_siem_forwarder"
DEMO_BANK_KEY_PLAINTEXT = "dr_demo_bank_switch_hook"


async def seed_sandbox():
    print("=" * 60)
    print("[*] Digital Rakshak — Seeding Dual-Market Sandbox Data")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        # 1. Organization Check or Create
        result = await session.execute(
            select(Organization).where(Organization.slug == DEMO_ORG_SLUG)
        )
        org = result.scalar_one_or_none()

        if not org:
            org = Organization(
                name="Apex Nodal Cyber Cell & FinTech Labs",
                slug=DEMO_ORG_SLUG,
                tier=OrgTier.BUSINESS.value,
                domain="apexsec.io",
                is_active=True,
            )
            session.add(org)
            await session.commit()
            await session.refresh(org)
            print(f"[+] Created Organization: {org.name} (id: {org.id})")
        else:
            print(f"[*] Organization already exists: {org.name} (id: {org.id})")

        # 2. Seed Primary API Key
        key1_hash = ApiKey.hash_key(DEMO_API_KEY_PLAINTEXT)
        key1_prefix = DEMO_API_KEY_PLAINTEXT[:12]

        k1_res = await session.execute(
            select(ApiKey).where(ApiKey.key_hash == key1_hash)
        )
        if not k1_res.scalar_one_or_none():
            key1 = ApiKey(
                org_id=org.id,
                name="Primary SIEM Forwarder",
                key_prefix=key1_prefix,
                key_hash=key1_hash,
                scopes=["events:write", "alerts:read", "keys:manage"],
                is_active=True,
                last_used_at=datetime.now(timezone.utc),
            )
            session.add(key1)
            print(f"[+] Created API Key: Primary SIEM Forwarder ({key1_prefix}...)")

        # 3. Seed Secondary Bank Key
        key2_hash = ApiKey.hash_key(DEMO_BANK_KEY_PLAINTEXT)
        key2_prefix = DEMO_BANK_KEY_PLAINTEXT[:12]

        k2_res = await session.execute(
            select(ApiKey).where(ApiKey.key_hash == key2_hash)
        )
        if not k2_res.scalar_one_or_none():
            key2 = ApiKey(
                org_id=org.id,
                name="Banking Switch Telemetry Hook",
                key_prefix=key2_prefix,
                key_hash=key2_hash,
                scopes=["events:write"],
                is_active=True,
            )
            session.add(key2)
            print(f"[+] Created API Key: Banking Switch Hook ({key2_prefix}...)")

        # 4. Seed / Update Monthly Usage Quota
        current_period = datetime.now(timezone.utc).strftime("%Y-%m")
        q_res = await session.execute(
            select(UsageQuota).where(
                UsageQuota.org_id == org.id,
                UsageQuota.period == current_period,
            )
        )
        quota = q_res.scalar_one_or_none()

        if not quota:
            quota = UsageQuota(
                org_id=org.id,
                period=current_period,
                events_processed=14_250,
                monthly_limit=100_000,
                overage_count=0,
            )
            session.add(quota)
            print(f"[+] Initialized Usage Quota: 14,250 / 100,000 events ({current_period})")
        else:
            quota.events_processed = max(quota.events_processed, 14_250)
            print(f"[*] Usage Quota active: {quota.events_processed:,} / {quota.monthly_limit:,} events ({current_period})")

        # 5. Seed B2B Active Subscription Record
        sub_res = await session.execute(
            select(Subscription).where(Subscription.org_id == org.id)
        )
        if not sub_res.scalar_one_or_none():
            sub = Subscription(
                org_id=org.id,
                market=MarketSegment.B2B.value,
                plan_code=PlanCode.B2B_BUSINESS.value,
                status=SubscriptionStatus.ACTIVE.value,
                current_period_start=datetime.now(timezone.utc),
                current_period_end=datetime.now(timezone.utc),
            )
            session.add(sub)
            print("[+] Seeded active B2B Business subscription record")

        await session.commit()

    print("\n" + "=" * 60)
    print("[SUCCESS] SANDBOX SEEDING COMPLETE!")
    print("=" * 60)
    print("\nCopy this API Key to connect in the /business portal:")
    print(f"\n>>  {DEMO_API_KEY_PLAINTEXT}\n")
    print("Instructions:")
    print("1. Open http://localhost:3000/business in your browser.")
    print("2. Paste the API key above into the top-right 'Enter B2B API Key' field and click 'Connect'.")
    print("3. You will immediately see live quota meters, 2 active machine keys, and the code guides.")
    print("=" * 60)



if __name__ == "__main__":
    asyncio.run(seed_sandbox())
