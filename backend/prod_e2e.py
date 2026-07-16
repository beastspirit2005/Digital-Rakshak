import asyncio
import httpx
import uuid
from typing import Dict, Any

API_BASE = "https://frontend-chi-lemon-78.vercel.app/api/v1"

async def test_endpoint(client: httpx.AsyncClient, name: str, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    print(f"\n--- Testing {name} ({method} {endpoint}) ---")
    try:
        if method.upper() == "GET":
            response = await client.get(f"{API_BASE}{endpoint}", **kwargs)
        elif method.upper() == "POST":
            response = await client.post(f"{API_BASE}{endpoint}", **kwargs)
        else:
            raise ValueError("Unsupported method")
            
        print(f"Status Code: {response.status_code}")
        if response.status_code >= 400:
            print(f"Error Response: {response.text}")
            return {"success": False, "error": response.text, "status": response.status_code}
            
        data = response.json()
        print(f"Success! Keys in response: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        return {"success": True, "data": data, "status": response.status_code}
    except Exception as e:
        print(f"Exception during request: {e}")
        return {"success": False, "error": str(e)}

async def run_e2e():
    print("=== STARTING PRODUCTION END-TO-END VERIFICATION ===")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Test Health
        res = await test_endpoint(client, "Health Check", "GET", "/health")
        
        # 2. Test Registration
        unique_id = uuid.uuid4().hex[:8]
        test_email = f"e2etest_{unique_id}@example.com"
        password = "SecurePassword123!"
        
        register_data = {
            "email": test_email,
            "password": password,
            "full_name": "E2E Tester",
            "role": "citizen"
        }
        reg_res = await test_endpoint(client, "Registration", "POST", "/auth/register", json=register_data)
        
        # 3. Test Login
        login_data = {
            "email": test_email,
            "password": password
        }
        login_res = await test_endpoint(client, "Login", "POST", "/auth/login-password", json=login_data)
        
        token = None
        if login_res.get("success"):
            token = login_res["data"].get("access_token")
            
        if not token:
            print("Failed to get auth token. Cannot proceed with authenticated routes.")
            return
            
        headers = {"Authorization": f"Bearer {token}"}
        
        # 4. Fetch Cases
        await test_endpoint(client, "Fetch Cases", "GET", "/cases/", headers=headers)
        
        # 5. Fetch Dashboard Analytics
        await test_endpoint(client, "Analytics Dashboard", "GET", "/analytics/dashboard", headers=headers)
        
        # 6. Test Chat Copilot
        chat_data = {
            "message": "I lost 500 rupees to a fake UPI QR code scan.",
            "mode": "voice"
        }
        await test_endpoint(client, "Copilot Chat", "POST", "/chat/copilot", json=chat_data, headers=headers)

    print("\n=== E2E VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(run_e2e())
