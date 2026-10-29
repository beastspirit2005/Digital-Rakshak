"""
Digital Rakshak â€” Inject Realistic Interconnected Sample Scams
Clears old cases and creates 30 realistic cybercrime cases across Indian cities
with shared indicators (phones, UPIs, URLs) for spatial map & graph visualization.
"""
import asyncio
import uuid
import random
from datetime import datetime, timezone, timedelta

# â”€â”€â”€ Shared Bad-Actor Indicators (these create graph connections) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
BAD_PHONES = [
    "+919876543210", "+919988776655", "+918899001122",
    "+917766554433", "+916655443322",
]
BAD_UPIS = [
    "rakesh.fraud@ybl", "quick.loan.help@paytm", "govt.refund2024@oksbi",
    "invest.crypto99@axl",
]
BAD_URLS = [
    "http://kyc-update-sbi.in", "http://free-iphone-win.com",
    "http://loan-instant-approval.co.in", "http://customs-clearance-india.net",
    "http://job-portal-govt.in",
]
BAD_EMAILS = [
    "support@kyc-update-sbi.in", "hr@job-portal-govt.in",
    "customs.officer@clearance-india.net",
]

# â”€â”€â”€ City Coordinates â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
CITIES = [
    {"city": "Mumbai",     "state": "Maharashtra",    "lat": 19.0760, "lon": 72.8777},
    {"city": "Delhi",      "state": "Delhi",          "lat": 28.6139, "lon": 77.2090},
    {"city": "Bangalore",  "state": "Karnataka",      "lat": 12.9716, "lon": 77.5946},
    {"city": "Hyderabad",  "state": "Telangana",      "lat": 17.3850, "lon": 78.4867},
    {"city": "Chennai",    "state": "Tamil Nadu",     "lat": 13.0827, "lon": 80.2707},
    {"city": "Kolkata",    "state": "West Bengal",    "lat": 22.5726, "lon": 88.3639},
    {"city": "Pune",       "state": "Maharashtra",    "lat": 18.5204, "lon": 73.8567},
    {"city": "Jaipur",     "state": "Rajasthan",      "lat": 26.9124, "lon": 75.7873},
    {"city": "Lucknow",    "state": "Uttar Pradesh",  "lat": 26.8467, "lon": 80.9462},
    {"city": "Ahmedabad",  "state": "Gujarat",        "lat": 23.0225, "lon": 72.5714},
]

# â”€â”€â”€ 30 Realistic Scam Templates â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
SCAMS = [
    # --- UPI / Payment Fraud ---
    {
        "text": "Received a call from {phone} claiming to be from SBI. They said my account was being closed and I needed to verify via UPI. They made me send â‚¹49,999 to {upi}.",
        "type": "FIN-PAY-UPI", "priority": "critical", "amount": 49999,
        "phones": 1, "upis": 1, "urls": 0, "emails": 0,
    },
    {
        "text": "Someone called from {phone} posing as a Paytm executive, said I won a cashback of â‚¹15,000. Asked me to pay â‚¹999 processing fee to {upi}. Money debited instantly.",
        "type": "FIN-PAY-UPI", "priority": "high", "amount": 999,
        "phones": 1, "upis": 1, "urls": 0, "emails": 0,
    },
    {
        "text": "Got a WhatsApp message with a QR code from {phone}. They said scan to receive â‚¹5,000 refund from electricity board. Instead â‚¹25,000 was debited from my account to {upi}.",
        "type": "FIN-PAY-QR", "priority": "critical", "amount": 25000,
        "phones": 1, "upis": 1, "urls": 0, "emails": 0,
    },
    # --- Phishing / Fake KYC ---
    {
        "text": "Received an SMS from {phone}: 'Dear customer, your SBI account will be blocked. Update KYC immediately at {url}'. I entered my details and lost â‚¹1,50,000 from my savings.",
        "type": "ID-PHI-KYC", "priority": "critical", "amount": 150000,
        "phones": 1, "upis": 0, "urls": 1, "emails": 0,
    },
    {
        "text": "Got an email from {email} asking to update PAN card linked to my bank account via {url}. After filling the form, â‚¹75,000 was withdrawn in 3 transactions.",
        "type": "ID-PHI-KYC", "priority": "critical", "amount": 75000,
        "phones": 0, "upis": 0, "urls": 1, "emails": 1,
    },
    {
        "text": "A person called from {phone} claiming my Aadhaar was used for illegal activities. Directed me to {url} to 'verify identity'. They gained remote access to my phone.",
        "type": "ID-PHI-AADHAAR", "priority": "high", "amount": 0,
        "phones": 1, "upis": 0, "urls": 1, "emails": 0,
    },
    # --- Loan App Harassment ---
    {
        "text": "Downloaded a loan app advertised on {url}. Got â‚¹8,000 loan but they demanded â‚¹45,000 repayment. Now sending morphed photos to my contacts from {phone}.",
        "type": "FIN-LOAN-APP", "priority": "critical", "amount": 45000,
        "phones": 1, "upis": 0, "urls": 1, "emails": 0,
    },
    {
        "text": "Predatory lending app accessed my contacts and gallery. Received threatening calls from {phone} and {phone} demanding â‚¹30,000 or they'll share my photos.",
        "type": "FIN-LOAN-APP", "priority": "critical", "amount": 30000,
        "phones": 2, "upis": 0, "urls": 0, "emails": 0,
    },
    # --- Job / Employment Scam ---
    {
        "text": "Applied for a govt job on {url}. Got a call from {phone} saying I was selected, just need to pay â‚¹12,000 for training materials. After payment to {upi}, number switched off.",
        "type": "SOC-JOB-FAKE", "priority": "high", "amount": 12000,
        "phones": 1, "upis": 1, "urls": 1, "emails": 0,
    },
    {
        "text": "Received offer letter from {email} for Amazon work-from-home. Paid â‚¹5,000 registration fee to {upi}. The 'job' was reviewing products â€” classic task scam. Lost â‚¹2,00,000 total.",
        "type": "SOC-JOB-TASK", "priority": "critical", "amount": 200000,
        "phones": 0, "upis": 1, "urls": 0, "emails": 1,
    },
    # --- OLX / Marketplace Fraud ---
    {
        "text": "Listed my bike on OLX. Buyer called from {phone} claiming to be an Army officer. Sent a fake UPI payment screenshot and picked up the bike. Lost my â‚¹85,000 vehicle.",
        "type": "FIN-MARKET-OLX", "priority": "high", "amount": 85000,
        "phones": 1, "upis": 0, "urls": 0, "emails": 0,
    },
    {
        "text": "Tried to buy a second-hand laptop on OLX. Seller {phone} asked for advance payment of â‚¹15,000 to {upi}. After payment, blocked my number.",
        "type": "FIN-MARKET-OLX", "priority": "medium", "amount": 15000,
        "phones": 1, "upis": 1, "urls": 0, "emails": 0,
    },
    # --- Crypto / Investment Scam ---
    {
        "text": "Joined a WhatsApp group for crypto trading run by {phone}. Invested â‚¹3,00,000 via {upi}. Platform at {url} showed fake profits. When I tried to withdraw, account was locked.",
        "type": "FIN-INV-CRYPTO", "priority": "critical", "amount": 300000,
        "phones": 1, "upis": 1, "urls": 1, "emails": 0,
    },
    {
        "text": "Instagram ad led me to {url} promising 300% returns on crypto. Contacted on WhatsApp {phone}. Invested â‚¹50,000 to {upi}. Platform disappeared after 2 weeks.",
        "type": "FIN-INV-CRYPTO", "priority": "high", "amount": 50000,
        "phones": 1, "upis": 1, "urls": 1, "emails": 0,
    },
    {
        "text": "Received a Telegram message about a stock trading group. Mentor {phone} guided investments totaling â‚¹8,00,000 to {upi}. All fake â€” the 'trading platform' was a cloned website at {url}.",
        "type": "FIN-INV-STOCK", "priority": "critical", "amount": 800000,
        "phones": 1, "upis": 1, "urls": 1, "emails": 0,
    },
    # --- Sextortion ---
    {
        "text": "Received a video call on WhatsApp from an unknown number {phone}. They recorded a compromising video and are now demanding â‚¹1,00,000 to {upi} or they'll leak it.",
        "type": "SOC-SEXT", "priority": "critical", "amount": 100000,
        "phones": 1, "upis": 1, "urls": 0, "emails": 0,
    },
    {
        "text": "Got friend request on Facebook from {phone}. After video call, threatening to send morphed screenshots to family. Demanding â‚¹50,000 to {upi}.",
        "type": "SOC-SEXT", "priority": "high", "amount": 50000,
        "phones": 1, "upis": 1, "urls": 0, "emails": 0,
    },
    # --- Customs / Courier Scam ---
    {
        "text": "Call from {phone} saying a parcel in my name with drugs was seized at Mumbai customs. Transferred to fake 'CBI officer'. Paid â‚¹2,50,000 to {upi} for 'clearance'. Website: {url}.",
        "type": "SOC-IMP-CUSTOMS", "priority": "critical", "amount": 250000,
        "phones": 1, "upis": 1, "urls": 1, "emails": 0,
    },
    {
        "text": "FedEx automated call said parcel with contraband was intercepted. {phone} transferred me to 'narcotics bureau'. Under digital arrest for 6 hours. Lost â‚¹4,00,000.",
        "type": "SOC-IMP-FEDEX", "priority": "critical", "amount": 400000,
        "phones": 1, "upis": 0, "urls": 0, "emails": 0,
    },
    {
        "text": "Received call from {phone} claiming to be from DHL. My package had 'illegal items'. Asked to verify at {url}. They installed AnyDesk and drained â‚¹1,80,000.",
        "type": "SOC-IMP-CUSTOMS", "priority": "critical", "amount": 180000,
        "phones": 1, "upis": 0, "urls": 1, "emails": 0,
    },
    # --- Tech Support Scam ---
    {
        "text": "Pop-up appeared saying my computer was infected. Called {phone} (Microsoft support). They installed remote access and transferred â‚¹95,000 from my net banking.",
        "type": "SOC-TECH-SUPPORT", "priority": "high", "amount": 95000,
        "phones": 1, "upis": 0, "urls": 0, "emails": 0,
    },
    # --- Electricity / Utility Scam ---
    {
        "text": "SMS from {phone}: 'Your electricity will be disconnected tonight. Pay â‚¹1,200 immediately to {upi}.' Panicked and paid. Later found out it was fake.",
        "type": "SOC-IMP-UTILITY", "priority": "medium", "amount": 1200,
        "phones": 1, "upis": 1, "urls": 0, "emails": 0,
    },
    # --- Insurance Fraud ---
    {
        "text": "Call from {phone} offering LIC bonus of â‚¹3,00,000. Needed to pay â‚¹25,000 'tax' to {upi}. After payment, they kept demanding more. Total loss: â‚¹75,000.",
        "type": "FIN-INS-FAKE", "priority": "high", "amount": 75000,
        "phones": 1, "upis": 1, "urls": 0, "emails": 0,
    },
    # --- Romance Scam ---
    {
        "text": "Met someone on a dating app who claimed to be a US-based NRI. After 2 months, asked for â‚¹2,00,000 for 'customs clearance of gift parcel' to {upi}. Contact: {phone}.",
        "type": "SOC-ROMANCE", "priority": "high", "amount": 200000,
        "phones": 1, "upis": 1, "urls": 0, "emails": 0,
    },
    # --- Fake E-commerce ---
    {
        "text": "Ordered a phone from {url} advertised on Instagram. Paid â‚¹18,000 to {upi}. Received an empty box. Seller {phone} now unreachable.",
        "type": "FIN-ECOM-FAKE", "priority": "medium", "amount": 18000,
        "phones": 1, "upis": 1, "urls": 1, "emails": 0,
    },
    # --- Digital Arrest ---
    {
        "text": "Video call from {phone} â€” man in police uniform said arrest warrant issued against me for money laundering. Under 'digital arrest' for 12 hours. Transferred â‚¹6,00,000 to {upi}.",
        "type": "SOC-IMP-POLICE", "priority": "critical", "amount": 600000,
        "phones": 1, "upis": 1, "urls": 0, "emails": 0,
    },
    {
        "text": "Received a call from {phone} saying CBI has a case against my Aadhaar number. Kept on video call for 8 hours. Made me transfer â‚¹3,50,000 to 'safe RBI account' {upi}.",
        "type": "SOC-IMP-CBI", "priority": "critical", "amount": 350000,
        "phones": 1, "upis": 1, "urls": 0, "emails": 0,
    },
    # --- Reward / Lottery Scam ---
    {
        "text": "Email from {email}: 'Congratulations! You won â‚¹25,00,000 in Jio KBC lottery.' Pay â‚¹15,000 processing fee to {upi}. Paid and then blocked.",
        "type": "SOC-LOTTERY", "priority": "medium", "amount": 15000,
        "phones": 0, "upis": 1, "urls": 0, "emails": 1,
    },
    # --- Sim Swap ---
    {
        "text": "My phone lost network suddenly. Next day found â‚¹4,50,000 transferred from my bank. Attacker used {phone} to call Airtel and swap my SIM using Aadhaar details from {url}.",
        "type": "FIN-SIM-SWAP", "priority": "critical", "amount": 450000,
        "phones": 1, "upis": 0, "urls": 1, "emails": 0,
    },
    # --- Matrimonial Fraud ---
    {
        "text": "Met groom on Shaadi.com. After 3 months, {phone} asked for â‚¹5,00,000 for 'business emergency'. Sent to {upi}. Profile was fake, photos stolen.",
        "type": "SOC-MATRIMONY", "priority": "high", "amount": 500000,
        "phones": 1, "upis": 1, "urls": 0, "emails": 0,
    },
]

STATUSES = ["submitted", "under_review", "investigating", "escalated", "assigned"]

async def main():
    import sys
    sys.path.insert(0, ".")
    
    from infrastructure.db.session import AsyncSessionLocal, engine
    from domain.models.case import Case
    from domain.models.user import User
    from sqlalchemy import select, delete, text
    
    print("=" * 60)
    print("  Digital Rakshak â€” Scam Data Injector")
    print("=" * 60)
    
    # Step 1: Clear old cases
    async with AsyncSessionLocal() as db:
        # Delete evidence first (FK constraint)
        await db.execute(text("DELETE FROM evidence"))
        result = await db.execute(text("DELETE FROM cases"))
        deleted = result.rowcount
        await db.commit()
        print(f"\nâœ“ Cleared {deleted} old cases from PostgreSQL")
    
    # Step 2: Clear Neo4j graph
    try:
        from infrastructure.graph.neo4j_client import IntelligenceGraph
        graph = IntelligenceGraph()
        async with graph.driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
        print("âœ“ Cleared Neo4j graph")
    except Exception as e:
        print(f"âš  Neo4j clear failed (non-critical): {e}")
        graph = None
    
    # Step 3: Get admin user ID for submitted_by
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.role == "admin").limit(1))
        admin = result.scalar_one_or_none()
        if not admin:
            print("âœ— No admin user found! Create one first.")
            return
        admin_id = admin.id
        print(f"âœ“ Using admin: {admin.email} ({admin_id})")
    
    # Step 4: Inject 30 cases
    print(f"\nâ†’ Injecting {len(SCAMS)} interconnected cases...")
    
    created_cases = []
    async with AsyncSessionLocal() as db:
        for i, template in enumerate(SCAMS):
            city_info = CITIES[i % len(CITIES)]
            
            # Pick random indicators from shared pools
            phones_used = random.sample(BAD_PHONES, min(template["phones"], len(BAD_PHONES)))
            upis_used = random.sample(BAD_UPIS, min(template["upis"], len(BAD_UPIS)))
            urls_used = random.sample(BAD_URLS, min(template["urls"], len(BAD_URLS)))
            emails_used = random.sample(BAD_EMAILS, min(template["emails"], len(BAD_EMAILS)))
            
            # Fill in the text template
            text = template["text"]
            for p in phones_used:
                text = text.replace("{phone}", p, 1)
            for u in upis_used:
                text = text.replace("{upi}", u, 1)
            for url in urls_used:
                text = text.replace("{url}", url, 1)
            for em in emails_used:
                text = text.replace("{email}", em, 1)
            
            # Scatter coordinates slightly around city center
            lat = city_info["lat"] + random.uniform(-0.03, 0.03)
            lon = city_info["lon"] + random.uniform(-0.03, 0.03)
            
            case_number = f"CAS-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            confidence = round(random.uniform(0.75, 0.99), 2)
            
            # Build ai_decision JSONB
            ai_decision = {
                "decision": template["priority"].capitalize(),
                "confidence": confidence,
                "phone_numbers": phones_used,
                "upi_ids": upis_used,
                "urls": urls_used,
                "emails": emails_used,
                "scam_type_code": template["type"],
                "risk_factors": [
                    "Known fraud number" if phones_used else None,
                    "Suspicious URL pattern" if urls_used else None,
                    "High financial loss" if template["amount"] > 50000 else None,
                ],
            }
            ai_decision["risk_factors"] = [r for r in ai_decision["risk_factors"] if r]
            
            # Randomize created_at across last 30 days
            days_ago = random.randint(0, 30)
            created_at = datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23))
            
            case = Case(
                case_number=case_number,
                submitted_by=admin_id,
                scam_text=text,
                scam_type_code=template["type"],
                city=city_info["city"],
                state=city_info["state"],
                latitude=lat,
                longitude=lon,
                threat_confidence_score=confidence,
                ai_decision=ai_decision,
                status=random.choice(STATUSES),
                priority=template["priority"],
                estimated_amount=template["amount"] if template["amount"] > 0 else None,
                created_at=created_at,
                updated_at=created_at,
            )
            db.add(case)
            created_cases.append({
                "case_number": case_number,
                "phones": phones_used,
                "upis": upis_used,
                "urls": urls_used,
                "emails": emails_used,
            })
            
            city_name = city_info["city"]
            print(f"  [{i+1:02d}] {case_number} | {city_name:12s} | {template['type']:20s} | â‚¹{template['amount']:>10,}")
        
        await db.commit()
        print(f"\nâœ“ Injected {len(SCAMS)} cases into PostgreSQL")
    
    # Step 5: Build Neo4j graph connections
    if graph:
        print("\nâ†’ Building intelligence graph connections in Neo4j...")
        link_count = 0
        for case_info in created_cases:
            cn = case_info["case_number"]
            for phone in case_info["phones"]:
                await graph.add_case_entity_link(cn, "PhoneNumber", phone)
                link_count += 1
            for upi in case_info["upis"]:
                await graph.add_case_entity_link(cn, "UPI_ID", upi)
                link_count += 1
            for url in case_info["urls"]:
                await graph.add_case_entity_link(cn, "URL", url)
                link_count += 1
            for email in case_info["emails"]:
                await graph.add_case_entity_link(cn, "Email", email)
                link_count += 1
        print(f"âœ“ Created {link_count} graph links across {len(created_cases)} cases")
    
    # Summary
    print("\n" + "=" * 60)
    print("  INJECTION COMPLETE")
    print("=" * 60)
    print(f"  Cases created:    {len(created_cases)}")
    print(f"  Cities covered:   {len(CITIES)}")
    print(f"  Shared phones:    {len(BAD_PHONES)}")
    print(f"  Shared UPIs:      {len(BAD_UPIS)}")
    print(f"  Shared URLs:      {len(BAD_URLS)}")
    print(f"  Shared emails:    {len(BAD_EMAILS)}")
    total_amount = sum(t["amount"] for t in SCAMS)
    print(f"  Total â‚¹ at risk:  â‚¹{total_amount:,}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
