import random
import csv
import os
import uuid
from typing import List, Dict

# Set up templates
SCAM_TEMPLATES = [
    # UPI Fraud - Request Money & Refund Traps
    {"text": "Dear customer, you have received Rs. {amount} cashback from {name}. Please click the link to claim your money immediately: {phish_url}", "lang": "en", "threat": "UPI Fraud", "behaviors": ["Urgency", "Impersonation"]},
    {"text": "Aapke account me Rs {amount} credit hone wale hain. Approve karne ke liye is UPI ID par request accept kare: {phish_upi}", "lang": "hi", "threat": "UPI Fraud", "behaviors": ["Urgency"]},
    {"text": "Sir mene galti se aapko {amount} bhej diya hai, plz wapas kar do {phish_upi} pe, meri beti hospital me admit hai.", "lang": "hinglish", "threat": "UPI Fraud", "behaviors": ["Fear", "Urgency"]},
    {"text": "Instant Refund Alert: Rs {amount} pending from PhonePe. Click here to approve mandate and receive refund directly: {phish_url}", "lang": "en", "threat": "UPI Fraud", "behaviors": ["Urgency", "Impersonation"]},
    
    # Banking Fraud - KYC & OTP Harvesting
    {"text": "SBI Alert: Your account will be blocked in 24 hrs due to pending KYC. Update PAN immediately via {phish_url} or call {scam_phone}", "lang": "en", "threat": "Banking Fraud", "behaviors": ["Fear", "Urgency", "Impersonation", "OTP Harvesting"]},
    {"text": "Aapka HDFC bank account suspend ho gaya hai. Abhi {scam_phone} par call kare ya pan card link kare {phish_url}", "lang": "hi", "threat": "Banking Fraud", "behaviors": ["Fear", "Impersonation", "Urgency"]},
    {"text": "Dear Cardholder, your Credit Card reward points worth Rs {amount} are expiring today. Redeem cash to bank account by visiting {phish_url}", "lang": "en", "threat": "Banking Fraud", "behaviors": ["Urgency", "Impersonation"]},
    {"text": "Your debit card is blocked. Send OTP received on your mobile to {scam_phone} to unblock immediately.", "lang": "en", "threat": "Banking Fraud", "behaviors": ["Urgency", "OTP Harvesting"]},

    # Digital Arrest & Law Enforcement Impersonation
    {"text": "This is Mumbai Cyber Police Headquarters. A parcel containing 5 fake passports and 140g MDMA under your Aadhaar {aadhaar} was seized. Connect on Skype for video interrogation or face digital arrest.", "lang": "en", "threat": "Digital Arrest", "behaviors": ["Fear", "Impersonation", "Urgency"]},
    {"text": "CBI Officer calling. Aapke naam pe money laundering aur illegal trafficking ka case darj hua hai. Arrest warrant cancel karne ke liye Rs {amount} verification account me transfer kare.", "lang": "hi", "threat": "Digital Arrest", "behaviors": ["Fear", "Impersonation", "Urgency"]},
    {"text": "TRAI Notice: Your mobile number will be disconnected in 2 hours due to illegal advertisements and harassment complaints. Press 9 to speak with telecom authority officer.", "lang": "en", "threat": "Digital Arrest", "behaviors": ["Fear", "Impersonation", "Urgency"]},

    # Courier & Customs Scams
    {"text": "FedEx Alert: Your international package is stuck at Mumbai customs with contraband items. Pay customs clearance fee Rs {amount} at {phish_url} to avoid police seizure.", "lang": "en", "threat": "Courier Scam", "behaviors": ["Impersonation", "Urgency", "Fear"]},
    {"text": "India Post Tracking: Aapka parcel address incorrect hone ki wajah se return ho raha hai. Rs 48 re-delivery fee pay kare {phish_url}", "lang": "hinglish", "threat": "Courier Scam", "behaviors": ["Impersonation", "Urgency"]},

    # Utility & Power Disconnection Scams
    {"text": "Electricity Alert: Dear consumer, your electricity power will be disconnected tonight at 9:30 PM from electricity office because your previous month bill was not updated. Immediately call electricity officer at {scam_phone}", "lang": "en", "threat": "Banking Fraud", "behaviors": ["Urgency", "Fear", "Impersonation"]},
    {"text": "Bijli bill update nahi hua hai. Aaj raat 9 baje light kat di jayegi. Bill verify karne ke liye turant call kare {scam_phone}", "lang": "hi", "threat": "Banking Fraud", "behaviors": ["Urgency", "Fear", "Impersonation"]},

    # Task & Work-from-Home Scams
    {"text": "Part time work from home: Earn Rs 3000 to 5000 daily by simply liking YouTube videos and rating hotels on Google Maps. No investment required. Contact our HR on Telegram: {phish_url}", "lang": "en", "threat": "UPI Fraud", "behaviors": ["Urgency", "Impersonation"]},
    {"text": "Congratulations! You have been selected for Amazon VIP review assistant role. Daily payout Rs 4,000 to your UPI. Message coordinator on WhatsApp: {scam_phone}", "lang": "en", "threat": "UPI Fraud", "behaviors": ["Impersonation"]},

    # Remote Access & Fake APKs
    {"text": "Jio Support: Your 5G SIM will be deactivated today. Download 5G Upgrade Assistant APK from {phish_url} and share 9-digit code with {scam_phone}", "lang": "en", "threat": "Banking Fraud", "behaviors": ["Urgency", "Remote Access", "Impersonation"]},
    {"text": "Instant Personal Loan approved Rs {amount} with 0% interest and no CIBIL check. Install Rakshak Fast Loan APK from {phish_url}", "lang": "en", "threat": "Banking Fraud", "behaviors": ["Remote Access", "Impersonation"]},
]

SAFE_TEMPLATES = [
    # Legitimate Indian Bank Transaction Alerts
    {"text": "Dear Customer, INR {amount}.00 debited from A/C XX{last4} on {date} via UPI. Ref No {ref}. If not done by you, forward this SMS to 9223008333 or SMS BLOCK to 56767.", "lang": "en", "threat": "Safe", "behaviors": []},
    {"text": "Dear Customer, INR {amount}.00 credited to your account ending in {last4} on {date} through NEFT. Avail Bal: INR {bal}. HDFC Bank.", "lang": "en", "threat": "Safe", "behaviors": []},
    {"text": "Aapke SBI khate me Rs {amount} salary credit ho gaya hai. Balance check karne ke liye 9223766666 par miss call de.", "lang": "hi", "threat": "Safe", "behaviors": []},
    {"text": "Dear Customer, INR {amount}.00 spent on your ICICI Bank Credit Card ending in {last4} at {store} on {date}. Available credit limit: INR {bal}.", "lang": "en", "threat": "Safe", "behaviors": []},

    # Legitimate OTPs with Security Advisories
    {"text": "Your OTP for login to SBI NetBanking is {otp}. Valid for 10 minutes. Do not share your OTP or password with anyone, including bank staff.", "lang": "en", "threat": "Safe", "behaviors": []},
    {"text": "981240 is your secret OTP for authenticating transaction of INR {amount}.00 on Amazon. Never share OTP with anyone.", "lang": "en", "threat": "Safe", "behaviors": []},
    {"text": "HDFC Bank: Use OTP {otp} to verify your mobile number. Bank never calls asking for OTP or NetBanking password.", "lang": "en", "threat": "Safe", "behaviors": []},

    # Legitimate E-commerce & Food Delivery Notifications
    {"text": "Your Amazon order #{order_id} is out for delivery with associate {name}. Please share delivery PIN {otp} only upon package arrival.", "lang": "en", "threat": "Safe", "behaviors": []},
    {"text": "Your Swiggy order from {store} has been picked up by {name}. Track live on app: {safe_url}", "lang": "en", "threat": "Safe", "behaviors": []},
    {"text": "Aapka Zomato order deliver ho chuka hai. Khana enjoy kare aur delivery partner ko rate kare: {safe_url}", "lang": "hi", "threat": "Safe", "behaviors": []},

    # Legitimate Utility, Travel & Government Alerts
    {"text": "Income Tax Department: Your ITR for AY 2026-27 has been processed. Refund of Rs {amount} has been credited to your bank account. Check status at {safe_url}", "lang": "en", "threat": "Safe", "behaviors": []},
    {"text": "IRCTC PNR {pnr}: Train 12951 NDLS-BCT Rajdhani is scheduled to depart on time at 16:55 from Platform 1. Have a pleasant journey.", "lang": "en", "threat": "Safe", "behaviors": []},
    {"text": "Dear Consumer, payment of Rs {amount} towards electricity Consumer No {last4} received successfully. Download receipt at {safe_url}", "lang": "en", "threat": "Safe", "behaviors": []},
    
    # Conversational & Personal
    {"text": "Hey {name}, are we still meeting for lunch tomorrow? Call me at {safe_phone} if plans change.", "lang": "en", "threat": "Safe", "behaviors": []},
    {"text": "Happy Diwali to you and your family! May this festival bring prosperity and good health.", "lang": "en", "threat": "Safe", "behaviors": []},
]

def random_scam_phone(): return f"+91{random.randint(7000000000, 9999999999)}"
def random_safe_phone(): return f"+91{random.randint(7000000000, 9999999999)}"
def random_phish_upi(): return f"{random.choice(['refund-desk','cashback-claim','sbi-kyc','customs-fine'])}{random.randint(10,99)}@{random.choice(['ybl','icici','okhdfcbank'])}"
def random_phish_url(): return f"http://{random.choice(['sbi-kyc-verify-login.in','pan-update-desk.com','fedex-customs-duty.info','electricity-discom-bill.net','t.me/task_daily_earn'])}/{random.randint(100,999)}"
def random_safe_url(): return f"https://{random.choice(['onlinesbi.sbi','hdfcbank.com','incometax.gov.in','amazon.in/orders','swiggy.com/order','zomato.com'])}/track"
def random_amount(): return str(random.choice([250, 499, 1200, 4500, 25000, 95000, 150000]))
def random_bal(): return str(random.choice([14200, 58400, 129000, 345000]))
def random_name(): return random.choice(["Rahul Sharma", "Priya Patel", "Amit Kumar", "Sneha Rao", "Vikram Singh", "Sunil Verma"])
def random_store(): return random.choice(["Biryani Blues", "Dominos Pizza", "Haldirams", "Subway", "Bikanervala"])
def random_last4(): return str(random.randint(1000, 9999))
def random_otp(): return str(random.randint(100000, 999999))
def random_ref(): return str(random.randint(400000000000, 499999999999))
def random_pnr(): return str(random.randint(2000000000, 2999999999))
def random_order_id(): return f"OD{random.randint(10000000, 99999999)}"
def random_date(): return random.choice(["18-Oct-26", "17-Oct-26", "16-Oct-26", "15-Oct-26"])
def random_aadhaar(): return f"{random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)}"

def generate_data(num_samples: int = 15000) -> List[Dict]:
    dataset = []
    
    for _ in range(num_samples):
        is_scam = random.random() < 0.6  # 60% scams, 40% safe
        template_pool = SCAM_TEMPLATES if is_scam else SAFE_TEMPLATES
        template = random.choice(template_pool)
        
        text = template["text"].format(
            amount=random_amount(),
            bal=random_bal(),
            name=random_name(),
            store=random_store(),
            last4=random_last4(),
            otp=random_otp(),
            ref=random_ref(),
            pnr=random_pnr(),
            order_id=random_order_id(),
            date=random_date(),
            phish_url=random_phish_url(),
            safe_url=random_safe_url(),
            phish_upi=random_phish_upi(),
            scam_phone=random_scam_phone(),
            safe_phone=random_safe_phone(),
            aadhaar=random_aadhaar()
        )
        
        behaviors = template["behaviors"]
        bh_impersonation = 1 if "Impersonation" in behaviors else 0
        bh_urgency = 1 if "Urgency" in behaviors else 0
        bh_fear = 1 if "Fear" in behaviors else 0
        bh_otp = 1 if "OTP Harvesting" in behaviors else 0
        bh_remote = 1 if "Remote Access" in behaviors else 0
        
        dataset.append({
            "id": str(uuid.uuid4()),
            "text": text,
            "language": template["lang"],
            "threat_class": template["threat"],
            "bh_impersonation": bh_impersonation,
            "bh_urgency": bh_urgency,
            "bh_fear": bh_fear,
            "bh_otp": bh_otp,
            "bh_remote": bh_remote
        })
        
    return dataset

if __name__ == "__main__":
    output_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, "drid_train.csv")
    
    print("Generating clean DRID dataset with 15000 samples...")
    data = generate_data(15000)
    
    keys = data[0].keys()
    with open(out_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    print(f"Successfully generated {len(data)} clean training samples in {out_file}")
