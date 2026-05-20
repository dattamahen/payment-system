"""Run: py test_login.py"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt
import sys

sys.path.insert(0, ".")

async def main():
    from app.core.security import verify_password, create_access_token, create_refresh_token
    
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["eventpay"]
    
    user = await db.users.find_one({"email": "admin@eventpay.com"})
    if not user:
        print("ERROR: No admin user found")
        return
    
    print(f"User found: {user['email']}, role: {user['role']}")
    print(f"Hash: {user['password_hash'][:20]}...")
    
    try:
        result = verify_password("admin123", user["password_hash"])
        print(f"Password verify: {result}")
    except Exception as e:
        print(f"Password verify ERROR: {e}")
        return
    
    try:
        token_data = {"sub": str(user["_id"]), "role": user["role"], "tenant_id": str(user.get("tenant_id") or "")}
        print(f"Token data: {token_data}")
        access = create_access_token(token_data)
        print(f"Access token: {access[:30]}...")
        refresh = create_refresh_token(token_data)
        print(f"Refresh token: {refresh[:30]}...")
    except Exception as e:
        print(f"Token creation ERROR: {e}")
    
    client.close()

asyncio.run(main())
