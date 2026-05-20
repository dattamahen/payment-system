from bson import ObjectId
from fastapi import HTTPException
from app.database import get_tenant_db


class RegistrationService:
    @staticmethod
    async def list_by_tenant(tenant_id: str, event_id: str = None):
        db = await get_tenant_db(tenant_id)
        query = {}
        if event_id:
            query["event_id"] = event_id
        regs = await db.registrations.find(query).sort("created_at", -1).to_list(500)
        return [{"id": str(r["_id"]), "phone": r["phone"], "event_id": r["event_id"], "responses": r.get("responses", {}), "payment": r.get("payment", {}), "status": r["status"]} for r in regs]

    @staticmethod
    async def get(registration_id: str, tenant_id: str):
        db = await get_tenant_db(tenant_id)
        reg = await db.registrations.find_one({"_id": ObjectId(registration_id)})
        if not reg:
            raise HTTPException(status_code=404, detail="Registration not found")
        return {"id": str(reg["_id"]), "phone": reg["phone"], "event_id": reg["event_id"], "responses": reg.get("responses", {}), "payment": reg.get("payment", {}), "status": reg["status"]}
