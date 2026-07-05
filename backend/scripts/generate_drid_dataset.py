import random
import csv
import os
import uuid
from typing import List, Dict

# Set up templates
SCAM_TEMPLATES = [
    # UPI Fraud - Request Money
    {"text": "Dear customer, you have received Rs. {amount} from {name}. Please click the link to claim your money immediately: {url}", "lang": "en", "threat": "UPI Fraud", "behaviors": ["Urgency", "Impersonation"]},
    {"text": "Aapke account me Rs {amount} credit hone wale hain. Approve karne ke liye is UPI ID par click kare: {upi}", "lang": "hi", "threat": "UPI Fraud", "behaviors": ["Urgency"]},
    {"text": "Sir mene galti se aapko {amount} bhej diya hai, plz wapas kar do {upi} pe, meri beti bimar hai.", "lang": "hinglish", "threat": "UPI Fraud", "behaviors": ["Fear", "Urgency"]},
    
    # Banking Fraud - OTP Harvesting
    {"text": "SBI Alert: Your account {pan} will be blocked in 24 hrs due to pending KYC. Update PAN via {url} or call {phone}", "lang": "en", "threat": "Banking Fraud", "behaviors": ["Fear", "Urgency", "Impersonation", "OTP Harvesting"]},
    {"text": "Aapka HDFC bank account suspend ho gaya hai. Abhi {phone} par call kare ya apna OTP share na kare.", "lang": "hi", "threat": "Banking Fraud", "behaviors": ["Fear", "Impersonation"]},
    {"text": "Your debit card is blocked. Send OTP received on your mobile to {phone} to unblock.", "lang": "en", "threat": "Banking Fraud", "behaviors": ["Urgency", "OTP Harvesting"]},
    
    # Digital Arrest
    {"text": "This is Mumbai Cyber Police. A parcel containing illegal items under your Aadhaar {aadhaar} was seized. Pay fine to {upi} or face imminent arrest.", "lang": "en", "threat": "Digital Arrest", "behaviors": ["Fear", "Impersonation", "Urgency"]},
    {"text": "CBI Officer calling. Aapke naam pe money laundering ka case mila hai. Agar aap chahte hain ki arrest na ho, toh {amount} is account IFSC: {ifsc} me bheje.", "lang": "hi", "threat": "Digital Arrest", "behaviors": ["Fear", "Impersonation"]},
    
    # Courier Scam
    {"text": "FedEx Alert: Your international package is stuck at customs. Pay customs duty Rs {amount} at {url} to release.", "lang": "en", "threat": "Courier Scam", "behaviors": ["Impersonation", "Urgency"]},
    {"text": "Sir aapka parcel India Post me fasa hai. Clearance charge {amount} jama kare is UPI pe {upi}", "lang": "hinglish", "threat": "Courier Scam", "behaviors": ["Impersonation"]},
    
    # Remote Access
    {"text": "Jio Customer Support: Your SIM will be deactivated today. Download AnyDesk from {url} and share the 9-digit code with {phone}.", "lang": "en", "threat": "Banking Fraud", "behaviors": ["Urgency", "Remote Access", "Impersonation"]},
]

SAFE_TEMPLATES = [
    {"text": "Your salary of Rs {amount} has been credited to your account ending in 1234. IFSC: {ifsc}", "lang": "en", "threat": "Safe", "behaviors": []},
    {"text": "Hey {name}, are we still meeting for lunch tomorrow? Call me at {phone} if plans change.", "lang": "en", "threat": "Safe", "behaviors": []},
    {"text": "Aapka order deliver ho gaya hai. Aap receipt {url} se download kar sakte hain.", "lang": "hi", "threat": "Safe", "behaviors": []},
    {"text": "Happy Diwali! Enjoy 50% off on all clothes. Visit our store or shop at {url}", "lang": "hinglish", "threat": "Safe", "behaviors": []},
]

def random_phone(): return f"+91{random.randint(7000000000, 9999999999)}"
def random_upi(): return f"{random.randint(7000000000, 9999999999)}@{random.choice(['ybl','sbi','okhdfcbank','icici'])}"
def random_url(): return f"http://{random.choice(['kyc-update-sbi','fedex-customs-pay','india-post-track','jio-sim-active'])}.com/{random.randint(100,999)}"
def random_ifsc(): return f"{random.choice(['SBIN','HDFC','ICIC','PUNB'])}0{random.randint(100000, 999999)}"
def random_amount(): return str(random.choice([499, 1000, 25000, 99999, 150000]))
def random_name(): return random.choice(["Rahul", "Priya", "Amit", "Sneha", "Vikram"])
def random_pan(): return f"ABCDE{random.randint(1000,9999)}F"
def random_aadhaar(): return f"{random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)}"

def generate_data(num_samples: int = 15000) -> List[Dict]:
    dataset = []
    
    for _ in range(num_samples):
        is_scam = random.random() < 0.7  # 70% scams, 30% safe
        template_pool = SCAM_TEMPLATES if is_scam else SAFE_TEMPLATES
        template = random.choice(template_pool)
        
        text = template["text"].format(
            amount=random_amount(),
            name=random_name(),
            url=random_url(),
            upi=random_upi(),
            phone=random_phone(),
            ifsc=random_ifsc(),
            pan=random_pan(),
            aadhaar=random_aadhaar()
        )
        
        # Binary flags for multi-label behavior
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
    
    print("Generating DRID dataset with 15000 samples...")
    data = generate_data(15000)
    
    keys = data[0].keys()
    with open(out_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
        
    print(f"Successfully generated DRID dataset at {out_file}")
