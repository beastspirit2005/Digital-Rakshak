import asyncio
import sys
import os
import uuid
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from infrastructure.db.session import AsyncSessionLocal
from domain.models.case import Case
from sqlalchemy import select, update, text
from infrastructure.graph.neo4j_client import IntelligenceGraph

async def main():
    async with AsyncSessionLocal() as db:
        # 1. Fix existing CAS-* cases that have scam type in ai_decision but not in scam_type_code
        result = await db.execute(select(Case).where(Case.scam_type_code.is_(None)))
        null_cases = result.scalars().all()
        print(f"Found {len(null_cases)} cases with NULL scam_type_code")
        
        for c in null_cases:
            if c.ai_decision and isinstance(c.ai_decision, dict):
                scam_type = c.ai_decision.get("scam_type_classification")
                if scam_type:
                    c.scam_type_code = scam_type
                    print(f"  Fixed {c.case_number}: scam_type_code = '{scam_type}'")
                else:
                    # Infer from scam_text
                    text_lower = (c.scam_text or "").lower()
                    if "upi" in text_lower or "gpay" in text_lower:
                        c.scam_type_code = "UPI Fraud"
                    elif "loan" in text_lower or "emi" in text_lower:
                        c.scam_type_code = "Loan Fraud"
                    elif "phishing" in text_lower or "link" in text_lower:
                        c.scam_type_code = "Phishing"
                    else:
                        c.scam_type_code = "Cyber Fraud"
                    print(f"  Inferred {c.case_number}: scam_type_code = '{c.scam_type_code}'")
        
        await db.commit()
        print("\n--- Phase 1 Complete: Fixed NULL scam_type_codes ---\n")
        
        # 2. Now seed MORE diverse cases to balance the 30 counterfeit ones
        from domain.models.user import User
        user_result = await db.execute(select(User).limit(1))
        user = user_result.scalar_one_or_none()
        mock_user_id = str(user.id) if user else "00000000-0000-0000-0000-000000000000"
        
        NEW_CASES = [
            # UPI Fraud cases
            {"city": "Mumbai", "state": "Maharashtra", "lat": 19.0760, "lng": 72.8777,
             "scam_type": "UPI Fraud", "priority": "critical",
             "text": "Someone called posing as SBI bank officer. They sent a UPI collect request for Rs 49,999 from fraud.refund@ybl claiming it was a refund. Money was debited instead.",
             "phone": "+919988776655", "upi": "fraud.refund@ybl"},
            {"city": "Delhi", "state": "Delhi", "lat": 28.6139, "lng": 77.2090,
             "scam_type": "UPI Fraud", "priority": "high",
             "text": "Received WhatsApp message about KYC expiry. Link redirected to fake PhonePe page. Lost Rs 25,000 through unauthorized UPI transaction to scammer.pay@paytm.",
             "phone": "+919112233445", "upi": "scammer.pay@paytm"},
            {"city": "Lucknow", "state": "Uttar Pradesh", "lat": 26.8467, "lng": 80.9462,
             "scam_type": "UPI Fraud", "priority": "medium",
             "text": "OLX seller asked me to scan QR code to 'receive' payment for my old laptop. Instead Rs 15,000 was debited from my account via UPI.",
             "upi": "olxseller99@oksbi"},
            {"city": "Indore", "state": "Madhya Pradesh", "lat": 22.7196, "lng": 75.8577,
             "scam_type": "UPI Fraud", "priority": "high",
             "text": "Fake GPay cashback offer link circulated on WhatsApp. Entered UPI PIN and lost Rs 32,000 to quickpay.deals@axl.",
             "upi": "quickpay.deals@axl"},
             
            # Phishing cases
            {"city": "Hyderabad", "state": "Telangana", "lat": 17.3850, "lng": 78.4867,
             "scam_type": "Phishing", "priority": "high",
             "text": "Got SMS: 'Your HDFC account is blocked. Click hdfc-secure-verify.in to reactivate.' Entered card details. Rs 89,000 stolen in 3 transactions.",
             "url": "hdfc-secure-verify.in"},
            {"city": "Chandigarh", "state": "Punjab", "lat": 30.7333, "lng": 76.7794,
             "scam_type": "Phishing", "priority": "critical",
             "text": "Email from support@icici-alerts.co asking to update PAN. Website looked identical to ICICI. Lost Rs 2,40,000 after entering net banking credentials.",
             "url": "icici-alerts.co"},
            {"city": "Bhopal", "state": "Madhya Pradesh", "lat": 23.2599, "lng": 77.4126,
             "scam_type": "Phishing", "priority": "medium",
             "text": "Instagram DM with link to 'win iPhone 15'. Site amazon-diwali-sale.com asked for debit card. Unauthorized charge of Rs 12,500.",
             "url": "amazon-diwali-sale.com"},
             
            # Investment/Trading Fraud
            {"city": "Bangalore", "state": "Karnataka", "lat": 12.9716, "lng": 77.5946,
             "scam_type": "Investment Fraud", "priority": "critical",
             "text": "Telegram group 'Stock Market Millionaires' convinced me to install fake trading app. Deposited 5 lakh. App shows profits but withdrawals blocked.",
             "phone": "+918855443322"},
            {"city": "Pune", "state": "Maharashtra", "lat": 18.5204, "lng": 73.8567,
             "scam_type": "Investment Fraud", "priority": "high",
             "text": "WhatsApp group added me. Showed crypto trading profits on fake binance-pro-trade.com. Invested 3 lakh. Cannot withdraw funds.",
             "url": "binance-pro-trade.com", "phone": "+916677889900"},
            {"city": "Noida", "state": "Uttar Pradesh", "lat": 28.5355, "lng": 77.3910,
             "scam_type": "Investment Fraud", "priority": "high",
             "text": "YouTube ad about doubling money in 30 days. Signed up on invest-sure-returns.in. Paid 1.5 lakh. Website now offline.",
             "url": "invest-sure-returns.in"},
             
            # Loan Fraud
            {"city": "Chennai", "state": "Tamil Nadu", "lat": 13.0827, "lng": 80.2707,
             "scam_type": "Loan Fraud", "priority": "high",
             "text": "Instant loan app 'QuickCash Pro' approved Rs 50,000 loan. After download, app accessed all contacts. Now receiving threats and morphed photos for Rs 1,50,000.",
             "phone": "+917744556688"},
            {"city": "Kochi", "state": "Kerala", "lat": 9.9312, "lng": 76.2673,
             "scam_type": "Loan Fraud", "priority": "critical",
             "text": "Downloaded 'EasyLoan' app. Gave small loan of 5000. Now demanding 50,000 with threats. Sending morphed photos to all my contacts.",
             "phone": "+919900112233"},
             
            # Sextortion
            {"city": "Jaipur", "state": "Rajasthan", "lat": 26.9124, "lng": 75.7873,
             "scam_type": "Sextortion", "priority": "critical",
             "text": "Random video call on WhatsApp from unknown number. They recorded screen and now demanding Rs 5 lakh or they'll share the video.",
             "phone": "+918822334455"},
            {"city": "Nagpur", "state": "Maharashtra", "lat": 21.1458, "lng": 79.0882,
             "scam_type": "Sextortion", "priority": "high",
             "text": "Facebook friend request from fake profile. Video call turned into blackmail. Demanding Rs 2 lakh via UPI to stop.leaking@ybl.",
             "upi": "stop.leaking@ybl", "phone": "+917766001122"},
             
            # Job Fraud
            {"city": "Gurgaon", "state": "Haryana", "lat": 28.4595, "lng": 77.0266,
             "scam_type": "Job Fraud", "priority": "high",
             "text": "Got offer letter from 'Google India HR' via email. Asked to pay Rs 35,000 registration fee to google.hr.india@kotak. Turned out to be fake.",
             "upi": "google.hr.india@kotak"},
            {"city": "Vizag", "state": "Andhra Pradesh", "lat": 17.6868, "lng": 83.2185,
             "scam_type": "Job Fraud", "priority": "medium",
             "text": "Work from home data entry job posting. Paid Rs 8,000 joining fee. After payment, WhatsApp group admin blocked everyone.",
             "phone": "+919876001234"},
             
            # Matrimonial Fraud
            {"city": "Kolkata", "state": "West Bengal", "lat": 22.5726, "lng": 88.3639,
             "scam_type": "Matrimonial Fraud", "priority": "high",
             "text": "Met person on Shaadi.com claiming to be NRI doctor. After 2 months of chatting, asked for Rs 3 lakh for 'customs clearance of gifts'. Disappeared after transfer.",
             "upi": "nri.doctor@sbi"},
             
            # SIM Swap
            {"city": "Ahmedabad", "state": "Gujarat", "lat": 23.0225, "lng": 72.5714,
             "scam_type": "SIM Swap", "priority": "critical",
             "text": "Phone suddenly lost network. Someone got duplicate SIM of my number from Airtel store using fake ID. Rs 4.5 lakh transferred from my bank account.",
             "phone": "+919998887776"},
             
            # Tech Support Scam  
            {"city": "Coimbatore", "state": "Tamil Nadu", "lat": 11.0168, "lng": 76.9558,
             "scam_type": "Tech Support Scam", "priority": "medium",
             "text": "Pop-up on laptop saying 'Windows infected with virus. Call Microsoft: +918800990077'. Called and they installed AnyDesk. Took Rs 22,000.",
             "phone": "+918800990077"},
             
            # KYC Fraud
            {"city": "Patna", "state": "Bihar", "lat": 25.6093, "lng": 85.1376,
             "scam_type": "KYC Fraud", "priority": "high",
             "text": "Call from 'Paytm KYC department' saying account will be blocked. Shared OTP over phone. Rs 67,000 debited in 5 minutes.",
             "phone": "+917700889966"},
        ]
        
        graph = IntelligenceGraph()
        
        for c in NEW_CASES:
            case_id = f"CAS-{uuid.uuid4().hex[:8].upper()}"
            
            ai_decision = {
                "decision": "Fraudulent",
                "confidence": round(0.85 + (hash(c["text"]) % 15) / 100, 2),
                "reasoning": f"AI analysis identified {c['scam_type']} pattern. Multiple behavioral and textual indicators match known fraud templates from national cybercrime intelligence databases.",
                "scam_type_classification": c["scam_type"],
                "extracted_entities": {
                    "phone_numbers": [c["phone"]] if c.get("phone") else [],
                    "urls": [c["url"]] if c.get("url") else [],
                    "upi_ids": [c["upi"]] if c.get("upi") else [],
                },
                "evidence": [
                    {"relevance": f"Primary indicator: {c['scam_type']} modus operandi detected"},
                    {"relevance": f"Geographic correlation with known {c['scam_type']} hotspot in {c['city']}"}
                ],
                "raw_explanation": f"This case matches the {c['scam_type']} pattern. The victim was targeted through social engineering techniques commonly associated with organized cybercrime syndicates operating in India.",
                "ztivf_metrics": {
                    "trust_score": round(0.1 + (hash(c["city"]) % 30) / 100, 2),
                    "identity_verification": round(0.2 + (hash(c["state"]) % 20) / 100, 2),
                    "validation_score": round(0.85 + (hash(c["text"][:20]) % 15) / 100, 2),
                    "fraud_probability": round(0.80 + (hash(c["scam_type"]) % 20) / 100, 2),
                },
                "models_used": ["llama-3.3-70b", "threat-classifier-v2"],
                "inference_time_ms": 450 + hash(c["city"]) % 800
            }
            
            new_case = Case(
                case_number=case_id,
                submitted_by=mock_user_id,
                scam_text=c["text"],
                scam_type_code=c["scam_type"],
                city=c["city"],
                state=c["state"],
                latitude=c["lat"],
                longitude=c["lng"],
                threat_confidence_score=ai_decision["confidence"],
                ai_decision=ai_decision,
                priority=c["priority"],
                status="under_review"
            )
            db.add(new_case)
            
            # Add to Neo4j graph
            if c.get("phone"):
                await graph.add_case_entity_link(case_id, "PhoneNumber", c["phone"])
            if c.get("upi"):
                await graph.add_case_entity_link(case_id, "UPI_ID", c["upi"])
            if c.get("url"):
                await graph.add_case_entity_link(case_id, "URL", c["url"])
            
            print(f"  Created {case_id} | {c['scam_type']:20s} | {c['city']}")
        
        await db.commit()
        await graph.close()
        
        # 3. Final count
        total = await db.execute(select(Case.scam_type_code))
        all_types = [r[0] for r in total.all()]
        from collections import Counter
        print("\n--- Final Case Distribution ---")
        for t, count in Counter(all_types).most_common():
            print(f"  {t or 'NULL':25s}: {count}")
        print(f"  {'TOTAL':25s}: {len(all_types)}")

asyncio.run(main())
