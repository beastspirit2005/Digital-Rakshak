import httpx
import asyncio

async def test_flow():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=30.0) as client:
        # Login
        login_data = {
            "email": "testadmin2@example.com",
            "password": "Password1!"
        }
        r = await client.post("/api/v1/auth/login-password", json=login_data)
        print("Login:", r.status_code)
        if r.status_code != 200:
            print(r.text)
            return
        
        token = r.json()["access_token"]
        print("Got token:", token[:10] + "...")

        # Fetch users
        headers = {"Authorization": f"Bearer {token}"}
        r = await client.get("/api/v1/users/", headers=headers)
        print("Get users:", r.status_code)
        if r.status_code != 200:
            print(r.text)
        else:
            print("Successfully fetched users!")

if __name__ == "__main__":
    asyncio.run(test_flow())
