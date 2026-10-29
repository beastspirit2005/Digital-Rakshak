import asyncio
from core.security import create_access_token, decode_access_token
from core.config import settings

def test_jwt():
    print(f"SECRET_KEY: {settings.SECRET_KEY}")
    
    # 1. Create token
    data = {"sub": "123", "role": "admin"}
    token = create_access_token(data)
    print(f"Created token: {token}")
    
    # 2. Decode token
    try:
        decoded = decode_access_token(token)
        print(f"Decoded token: {decoded}")
    except Exception as e:
        print(f"Failed to decode token: {e}")

if __name__ == "__main__":
    test_jwt()
