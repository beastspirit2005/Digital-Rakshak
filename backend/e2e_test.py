import requests
import json
import os

BASE_URL = "http://127.0.0.1:8000/api/v1"

def print_result(title, res):
    print(f"\n{'='*50}\n[TEST] {title}")
    print(f"Status: {res.status_code}")
    try:
        print(json.dumps(res.json(), indent=2))
    except:
        print(res.text)

def run_tests():
    print("Starting End-to-End Tests for Digital Rakshak")

    # 1. Test Text Scan (Should hit the newly trained ML model)
    payload = {"text": "I am a CBI officer calling about a money laundering case. Send Rs 50000 to avoid digital arrest immediately."}
    res = requests.get(f"{BASE_URL}/scan", params=payload)
    print_result("Native AI Text Scan (Digital Arrest)", res)
    
    # 2. Test Safe Text Scan
    payload = {"text": "Hi Mom, I am coming home for dinner tonight."}
    res = requests.get(f"{BASE_URL}/scan", params=payload)
    print_result("Native AI Text Scan (Safe Message)", res)

    # 3. Test Graph URL Scan (OSINT / Graph DB integration)
    payload = {"url": "http://evil-phishing.com/login"}
    res = requests.get(f"{BASE_URL}/scan", params=payload)
    print_result("OSINT URL Scan", res)
    
    print("\nAPI tests completed.")

if __name__ == "__main__":
    run_tests()
