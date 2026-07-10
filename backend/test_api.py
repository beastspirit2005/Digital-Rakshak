import httpx

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjMiLCJyb2xlIjoiYWRtaW4iLCJleHAiOjE3ODM3OTUwNjJ9.5QZOOZlsqkPKD7Imzwpv3C0e2hLOtQV4V1Et5iqwK3M"
headers = {"Authorization": f"Bearer {token}"}
r = httpx.get("http://127.0.0.1:8000/api/v1/users/", headers=headers, timeout=30.0)
print(f"Status Code: {r.status_code}")
print(f"Response: {r.text}")
