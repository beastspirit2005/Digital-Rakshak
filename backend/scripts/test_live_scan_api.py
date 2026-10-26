import urllib.request
import json

cases = [
    ("Legitimate SBI UPI Alert", {"text": "Dear Customer, INR 450.00 debited from A/C XX9012 on 18-Oct-26 via UPI. Ref No 428912389123. If not done by you, forward to 9223008333 or SMS BLOCK to 56767."}),
    ("Digital Arrest Lure", {"text": "Mumbai Cyber Police: Your Aadhaar was found in confiscated courier with MDMA. Interrogation on Skype now."}),
    ("Electricity Bill Fraud", {"text": "Electricity Alert: Dear consumer, your electricity power will be disconnected tonight at 9:30 PM from electricity office. Call officer at +919876543210."}),
    ("Swiggy Delivery Alert", {"text": "Your Swiggy order from Biryani Blues has been picked up by Vikram. Track live on https://swiggy.com/order/track"}),
    ("Obfuscated Scam Message", {"text": "URGENT!! p@y now to stop c-b-i arrest warrant at http://fake-cbi-fine.in"})
]

print("=== TESTING LIVE /v1/scan ENDPOINT ===")
for name, payload in cases:
    req = urllib.request.Request(
        "http://127.0.0.1:8000/v1/scan",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
        print(f"[{name}]")
        print(f"  -> is_safe: {res.get('is_safe')} | Risk: {res.get('risk_level')}")
        print(f"  -> Reasons: {res.get('reasons')}")
        print(f"  -> Guidance: {res.get('guidance')[:1]}\n")
