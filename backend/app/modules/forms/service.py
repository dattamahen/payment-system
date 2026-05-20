from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException
from app.database import get_tenant_db
from app.modules.forms.schemas import FormCreate, FormUpdate


class FormService:
    @staticmethod
    async def create(tenant_id: str, body: FormCreate):
        db = await get_tenant_db(tenant_id)
        doc = {
            "tenant_id": tenant_id,
            "name": body.name,
            "fields": [f.model_dump() for f in body.fields],
            "created_at": datetime.utcnow(),
        }
        result = await db.forms.insert_one(doc)
        return {"id": str(result.inserted_id), "tenant_id": tenant_id, "name": body.name, "fields": body.fields, "created_at": doc["created_at"]}

    @staticmethod
    async def list_by_tenant(tenant_id: str):
        db = await get_tenant_db(tenant_id)
        forms = await db.forms.find().to_list(100)
        return [{"id": str(f["_id"]), "tenant_id": tenant_id, "name": f["name"], "fields": f["fields"], "created_at": f.get("created_at")} for f in forms]

    @staticmethod
    async def get(form_id: str, tenant_id: str):
        db = await get_tenant_db(tenant_id)
        form = await db.forms.find_one({"_id": ObjectId(form_id)})
        if not form:
            raise HTTPException(status_code=404, detail="Form not found")
        return {"id": str(form["_id"]), "tenant_id": tenant_id, "name": form["name"], "fields": form["fields"], "created_at": form.get("created_at")}

    @staticmethod
    async def update(form_id: str, tenant_id: str, body: FormUpdate):
        db = await get_tenant_db(tenant_id)
        update_data = body.model_dump(exclude_none=True)
        if "fields" in update_data:
            update_data["fields"] = [f if isinstance(f, dict) else f.model_dump() for f in update_data["fields"]]
        await db.forms.update_one({"_id": ObjectId(form_id)}, {"$set": update_data})
        return await FormService.get(form_id, tenant_id)

    @staticmethod
    async def delete(form_id: str, tenant_id: str):
        db = await get_tenant_db(tenant_id)
        await db.forms.delete_one({"_id": ObjectId(form_id)})
        return {"message": "Form deleted"}
