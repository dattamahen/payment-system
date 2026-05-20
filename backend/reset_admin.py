"""Run this script to reset the admin user: py reset_admin.py"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["eventpay"]
    
    # Delete existing admin
    result = await db.users.delete_many({"email": "admin@eventpay.com"})
    print(f"Deleted {result.deleted_count} existing admin records")
    
    # Create fresh admin with bcrypt hash
    password_hash = bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    print(f"Generated hash: {password_hash}")
    
    await db.users.insert_one({
        "email": "admin@eventpay.com",
        "password_hash": password_hash,
        "name": "Super Admin",
        "role": "super_admin",
        "tenant_id": None,
        "status": "active",
    })
    print("Admin user created successfully!")
    
    # Verify
    user = await db.users.find_one({"email": "admin@eventpay.com"})
    print(f"Verify: {bcrypt.checkpw('admin123'.encode('utf-8'), user['password_hash'].encode('utf-8'))}")
    
    client.close()

asyncio.run(main())
