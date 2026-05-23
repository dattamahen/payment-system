import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

async def main():
    c = AsyncIOMotorClient("mongodb://localhost:27017")
    db = c["eventpay"]
    t = await db.tenants.find_one({"_id": ObjectId("6a0c781636cb3af010a170ae")})
    cfg = t.get("config", {})
    print(f"whatsapp_number: {cfg.get('whatsapp_number')}")
    print(f"whatsapp_phone_number_id: {cfg.get('whatsapp_phone_number_id')}")
    print(f"whatsapp_number_id: {cfg.get('whatsapp_number_id')}")
    c.close()

asyncio.run(main())
