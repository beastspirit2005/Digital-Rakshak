import requests
import json

base_url = "http://127.0.0.1:8000/v1"

# Login as admin to get token
acc = {"email": "harshit2500sharma@gmail.com", "password": "Admin@123"}
resp = requests.post(f"{base_url}/auth/login-password", json=acc)
if resp.status_code != 200:
    print(f"Login failed: {resp.text}")
    exit(1)

data = resp.json()
print("Login response:", data)
token = data["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("Successfully logged in. Submitting a test case...")

scam_text = "I received a call from +919876543210 claiming my FedEx package was seized by customs. They asked for money urgently. Also check upi id scammer@ybl."

submit_resp = requests.post(
    f"{base_url}/cases/submit",
    headers=headers,
    data={
        "scam_text": scam_text,
        "ai_mode": "mock", # Using mock mode to test pipeline logic without slow local inference
        "city": "Mumbai",
        "state": "Maharashtra",
        "latitude": 19.0760,
        "longitude": 72.8777
    }
)

print(f"Status Code: {submit_resp.status_code}")
try:
    print(json.dumps(submit_resp.json(), indent=2))
except:
    print(submit_resp.text)
