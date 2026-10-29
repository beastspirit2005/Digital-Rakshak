import httpx

import os
token = os.environ.get("TEST_JWT_TOKEN", "dummy_test_token")
headers = {"Authorization": f"Bearer {token}"}
r = httpx.get("http://127.0.0.1:8000/api/v1/users/", headers=headers, timeout=30.0)
print(f"Status Code: {r.status_code}")
print(f"Response: {r.text}")
