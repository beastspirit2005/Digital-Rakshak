import urllib.request
import json
import time

time.sleep(3)  # Wait for server to be ready

url = "http://127.0.0.1:8000/api/v1/auth/request-otp"
data = json.dumps({"email": "harshit2500sharma@gmail.com"}).encode()
headers = {"Content-Type": "application/json"}

req = urllib.request.Request(url, data=data, headers=headers)
try:
    resp = urllib.request.urlopen(req)
    print(f"SUCCESS! Status: {resp.status}")
    print(f"Response: {resp.read().decode()}")
except urllib.error.HTTPError as e:
    print(f"FAILED! Status: {e.code}")
    print(f"Error: {e.read().decode()}")
