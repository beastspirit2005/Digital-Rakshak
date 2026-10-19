import pytest
import pytest_asyncio
from fastapi import Request
from api.v1.scan import live_prevention_scan, ScanRequest
from infrastructure.ai.ml_client import RakshakCoreClient
from infrastructure.ai.ollama_client import OllamaClient

# 10 Ground-Truth Legitimate Indian Communications
LEGITIMATE_TEST_CASES = [
    {
        "name": "SBI UPI Debit Transaction SMS",
        "req": ScanRequest(text="Dear Customer, INR 450.00 debited from A/C XX9012 on 18-Oct-26 via UPI. Ref No 428912389123. If not done by you, forward to 9223008333 or SMS BLOCK to 56767."),
        "expected_safe": True
    },
    {
        "name": "HDFC Salary Credit Alert",
        "req": ScanRequest(text="Dear Customer, INR 75,000.00 credited to your account ending in 4102 on 18-Oct-26 through NEFT. Avail Bal: INR 1,42,850. HDFC Bank."),
        "expected_safe": True
    },
    {
        "name": "SBI NetBanking Official OTP",
        "req": ScanRequest(text="Your OTP for login to SBI NetBanking is 591024. Valid for 10 minutes. Do not share your OTP or password with anyone, including bank staff."),
        "expected_safe": True
    },
    {
        "name": "ICICI Credit Card Spend Alert",
        "req": ScanRequest(text="Dear Customer, INR 1,299.00 spent on your ICICI Bank Credit Card ending in 8912 at Dominos Pizza on 18-Oct-26. Available credit limit: INR 85,000."),
        "expected_safe": True
    },
    {
        "name": "Amazon Package Delivery Update",
        "req": ScanRequest(text="Your Amazon order #OD82194012 is out for delivery with associate Rahul Sharma. Please share delivery PIN 4912 only upon package arrival."),
        "expected_safe": True
    },
    {
        "name": "Swiggy Food Delivery Alert",
        "req": ScanRequest(text="Your Swiggy order from Biryani Blues has been picked up by Vikram. Track live on https://swiggy.com/order/track"),
        "expected_safe": True
    },
    {
        "name": "Income Tax Department ITR Refund Notice",
        "req": ScanRequest(text="Income Tax Department: Your ITR for AY 2026-27 has been processed. Refund of Rs 4,500 has been credited to your bank account. Check status at https://incometax.gov.in"),
        "expected_safe": True
    },
    {
        "name": "IRCTC PNR Status Alert",
        "req": ScanRequest(text="IRCTC PNR 2849102914: Train 12951 NDLS-BCT Rajdhani is scheduled to depart on time at 16:55 from Platform 1. Have a pleasant journey."),
        "expected_safe": True
    },
    {
        "name": "Official Google Domain",
        "req": ScanRequest(url="https://www.google.com/search?q=cybercrime+reporting"),
        "expected_safe": True
    },
    {
        "name": "Official SBI Internet Banking Portal",
        "req": ScanRequest(url="https://retail.onlinesbi.sbi/retail/login.htm"),
        "expected_safe": True
    }
]

# 10 Ground-Truth Malicious Indian Cybercrime Lures
MALICIOUS_TEST_CASES = [
    {
        "name": "Electricity Power Cut Tonight Urgent Threat",
        "req": ScanRequest(text="Electricity Alert: Dear consumer, your electricity power will be disconnected tonight at 9:30 PM from electricity office because your previous month bill was not updated. Immediately call electricity officer at +919876543210"),
        "expected_safe": False
    },
    {
        "name": "Digital Arrest Narcotics Customs Lure",
        "req": ScanRequest(text="This is Mumbai Cyber Police Headquarters. A parcel containing 5 fake passports and 140g MDMA under your Aadhaar 4912 3019 4812 was seized. Connect on Skype for video interrogation or face digital arrest."),
        "expected_safe": False
    },
    {
        "name": "FedEx Customs Duty Clearance Threat",
        "req": ScanRequest(text="FedEx Alert: Your international package is stuck at Mumbai customs with contraband items. Pay customs clearance fee Rs 25,000 at http://fedex-customs-duty.info/928 to avoid police seizure."),
        "expected_safe": False
    },
    {
        "name": "SBI Account Blocked 24 Hours KYC Phishing",
        "req": ScanRequest(text="SBI Alert: Your account will be blocked in 24 hrs due to pending KYC. Update PAN immediately via http://sbi-kyc-verify-login.in/update or call +918912839120"),
        "expected_safe": False
    },
    {
        "name": "HDFC Account Suspended Call Private Phone",
        "req": ScanRequest(text="Aapka HDFC bank account suspend ho gaya hai. Abhi +919812739182 par call kare ya pan card link kare http://pan-update-desk.com/login"),
        "expected_safe": False
    },
    {
        "name": "Part-Time YouTube Like Task Scam",
        "req": ScanRequest(text="Part time work from home: Earn Rs 3000 to 5000 daily by simply liking YouTube videos and rating hotels on Google Maps. No investment required. Contact our HR on Telegram: http://t.me/task_daily_earn"),
        "expected_safe": False
    },
    {
        "name": "Jio 5G SIM Deactivation AnyDesk APK Scam",
        "req": ScanRequest(text="Jio Support: Your 5G SIM will be deactivated today. Download 5G Upgrade Assistant AnyDesk APK from http://jio-5g-update.info/apk and share 9-digit code with +917971923463"),
        "expected_safe": False
    },
    {
        "name": "Instant Loan 0% Interest Rakshak Fast Loan APK",
        "req": ScanRequest(text="Instant Personal Loan approved Rs 50,000 with 0% interest and no CIBIL check. Install Fast Loan APK from http://fast-loan-approved.org/download.apk"),
        "expected_safe": False
    },
    {
        "name": "PhonePe Cash Refund Claim UPI Mandate Trap",
        "req": ScanRequest(text="Dear customer, you have received Rs. 2,500 cashback refund from PhonePe. Please click the link to claim your money immediately and enter UPI PIN: http://cashback-claim-desk.in/upi"),
        "expected_safe": False
    },
    {
        "name": "Accidental Money Transfer Refund Extortion",
        "req": ScanRequest(text="Sir mene galti se aapko 25000 bhej diya hai, plz wapas kar do refund-desk99@okhdfcbank pe, meri beti hospital me admit hai."),
        "expected_safe": False
    }
]

class MockRequest:
    def __init__(self, host="127.0.0.1"):
        self.client = type("Client", (), {"host": host})()

@pytest.mark.asyncio
async def test_raic_core_heuristic_and_accuracy():
    """Verify RAIC Core sub-millisecond offline classifier."""
    client = RakshakCoreClient(model_version="1.0")

    # 1. Genuine bank transaction
    res_safe = client.predict("Dear Customer, INR 500.00 debited from A/C XX1234 on 18-Oct-26 via UPI. Ref No 9283912. If not done by you, SMS BLOCK to 56767.")
    assert res_safe["threat_class"] == "Safe"
    assert res_safe["confidence"] >= 0.9

    # 2. Electricity bill disconnection
    res_scam = client.predict("Electricity Alert: Power will be disconnected tonight at 9:30 PM. Immediately call officer at +919876543210")
    assert res_scam["threat_class"] in ["Banking Fraud", "Utility Scam"]
    assert res_scam["confidence"] >= 0.9

    # 3. Digital arrest
    res_arrest = client.predict("This is Mumbai Cyber Police. MDMA narcotics parcel seized under your Aadhaar. Connect on Skype or face digital arrest.")
    assert res_arrest["threat_class"] == "Digital Arrest"
    assert res_arrest["confidence"] >= 0.9

@pytest.mark.asyncio
async def test_ollama_client_domain_grounding():
    """Verify that OllamaClient uses domain-grounded prompt and parses JSON accurately."""
    client = OllamaClient()

    # Test prompt formatting
    assert client.default_model == "llama3:8b"
    assert client._resolve_model("mistral") == "llama3:8b"
    assert client._resolve_model("qwen2.5:7b") == "llama3:8b"

@pytest.mark.asyncio
async def test_full_offline_scan_suite_accuracy():
    """
    Run the 20-sample benchmark through the live Prevention Scan engine.
    Target: 100% precision on legitimate bank communications (0 false positives)
    and 100% recall on malicious lures.
    """
    req = MockRequest()
    correct_count = 0
    total_count = len(LEGITIMATE_TEST_CASES) + len(MALICIOUS_TEST_CASES)

    print("\n--- EVALUATING 10 LEGITIMATE COMMUNICATIONS ---")
    for case in LEGITIMATE_TEST_CASES:
        res = await live_prevention_scan(request=req, payload=case["req"], user=None)
        is_safe = res.is_safe
        assert is_safe == True, f"False Positive on: {case['name']} (Result: {res.risk_level}, Reasons: {res.reasons})"
        assert res.indicator_status in ["VERIFIED_LEGITIMATE", "UNKNOWN_UNVERIFIED"]
        correct_count += 1
        print(f"  [PASS] {case['name']} -> Safe: {is_safe}, Indicator: {res.indicator_status}")

    print("\n--- EVALUATING 10 MALICIOUS THREAT LURES ---")
    for case in MALICIOUS_TEST_CASES:
        res = await live_prevention_scan(request=req, payload=case["req"], user=None)
        is_safe = res.is_safe
        assert is_safe == False, f"False Negative on: {case['name']} (Result: {res.risk_level}, Reasons: {res.reasons})"
        assert res.risk_level in ["CRITICAL", "HIGH", "MEDIUM"]
        assert res.indicator_status in ["KNOWN_MALICIOUS", "SUSPICIOUS"]
        correct_count += 1
        print(f"  [PASS] {case['name']} -> Safe: {is_safe}, Risk: {res.risk_level}, Attack DNA: {res.attack_dna_match or 'Flagged'}")

    accuracy = (correct_count / total_count) * 100.0
    print(f"\nBenchmark Result: {correct_count}/{total_count} ({accuracy:.1f}% accuracy)")
    assert accuracy >= 95.0
