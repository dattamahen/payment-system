import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["eventpay"]
    result = await db.tenants.update_many({}, {"$set": {"config.whatsapp_number": "15556747543", "config.whatsapp_phone_number_id": "1073260732545641"}})
    print(f"Updated {result.modified_count} tenants")
    client.close()

asyncio.run(main())
