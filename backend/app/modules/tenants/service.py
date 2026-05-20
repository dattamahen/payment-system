from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException
from app.database import get_db, get_tenant_db
from app.core.security import hash_password, encrypt_secret
from app.modules.tenants.schemas import TenantCreate, TenantUpdate, TenantUserCreate


class TenantService:
    @staticmethod
    async def create(body: TenantCreate):
        db = await get_db()
        if await db.tenants.find_one({"slug": body.slug}):
            raise HTTPException(status_code=409, detail="Slug already exists")

        tenant_doc = {
            "name": body.name,
            "slug": body.slug,
            "plan": body.plan,
            "config": {},
            "limits": {"max_events": 10 if body.plan == "free" else 50, "max_registrations_per_event": 500},
            "status": "active",
            "created_at": datetime.utcnow(),
        }

        if body.config:
            config = body.config.model_dump(exclude_none=True)
            for key in ("whatsapp_api_key", "razorpay_key_id", "razorpay_key_secret", "google_sheets_credentials"):
                if key in config and config[key]:
                    config[key] = encrypt_secret(config[key])
            tenant_doc["config"] = config

        result = await db.tenants.insert_one(tenant_doc)
        tenant_id = str(result.inserted_id)

        # Create owner user
        await db.users.insert_one({
            "email": body.owner_email,
            "password_hash": hash_password(body.owner_password),
            "name": body.name,
            "role": "tenant_admin",
            "tenant_id": tenant_id,
            "status": "active",
            "created_at": datetime.utcnow(),
        })

        return {"id": tenant_id, "name": body.name, "slug": body.slug, "plan": body.plan, "status": "active", "created_at": tenant_doc["created_at"]}

    @staticmethod
    async def list_all():
        db = await get_db()
        tenants = await db.tenants.find().to_list(100)
        return [{"id": str(t["_id"]), "name": t["name"], "slug": t["slug"], "plan": t["plan"], "status": t["status"], "created_at": t.get("created_at")} for t in tenants]

    @staticmethod
    async def update(tenant_id: str, body: TenantUpdate):
        db = await get_db()
        update_data = body.model_dump(exclude_none=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        # Encrypt sensitive config fields
        if "config" in update_data:
            config = update_data["config"]
            for key in ("whatsapp_api_key", "razorpay_key_id", "razorpay_key_secret", "google_sheets_credentials"):
                if key in config and config[key]:
                    config[key] = encrypt_secret(config[key])
            # Merge with existing config instead of replacing
            tenant = await db.tenants.find_one({"_id": ObjectId(tenant_id)})
            existing_config = tenant.get("config", {}) if tenant else {}
            existing_config.update(config)
            update_data["config"] = existing_config
        update_data["updated_at"] = datetime.utcnow()
        await db.tenants.update_one({"_id": ObjectId(tenant_id)}, {"$set": update_data})
        tenant = await db.tenants.find_one({"_id": ObjectId(tenant_id)})
        return {"id": str(tenant["_id"]), "name": tenant["name"], "slug": tenant["slug"], "plan": tenant["plan"], "status": tenant["status"], "created_at": tenant.get("created_at")}

    @staticmethod
    async def deactivate(tenant_id: str):
        db = await get_db()
        await db.tenants.update_one({"_id": ObjectId(tenant_id)}, {"$set": {"status": "inactive"}})
        return {"message": "Tenant deactivated"}

    @staticmethod
    async def create_tenant_user(tenant_id: str, body: TenantUserCreate):
        db = await get_db()
        if not await db.tenants.find_one({"_id": ObjectId(tenant_id)}):
            raise HTTPException(status_code=404, detail="Tenant not found")
        if await db.users.find_one({"email": body.email}):
            raise HTTPException(status_code=409, detail="Email already exists")
        user_doc = {
            "email": body.email,
            "password_hash": hash_password(body.password),
            "name": body.name,
            "role": body.role,
            "tenant_id": tenant_id,
            "status": "active",
            "created_at": datetime.utcnow(),
        }
        result = await db.users.insert_one(user_doc)
        return {"id": str(result.inserted_id), "email": body.email, "name": body.name, "role": body.role, "tenant_id": tenant_id}

    @staticmethod
    async def get_tenant_events(tenant_id: str):
        db = await get_tenant_db(tenant_id)
        events = await db.events.find().to_list(100)
        result = []
        for e in events:
            event_id = str(e["_id"])
            reg_count = await db.registrations.count_documents({"event_id": event_id})
            result.append({
                "id": event_id, "name": e["name"], "slug": e["slug"],
                "status": e["status"], "pricing": e["pricing"],
                "venue": e.get("venue"), "registrations_count": reg_count,
                "created_at": e.get("created_at"),
            })
        return result

    @staticmethod
    async def get_tenant_event_detail(tenant_id: str, event_id: str):
        db = await get_tenant_db(tenant_id)
        event = await db.events.find_one({"_id": ObjectId(event_id)})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        reg_count = await db.registrations.count_documents({"event_id": event_id})
        registrations = await db.registrations.find({"event_id": event_id}).sort("created_at", -1).to_list(500)
        regs = [{"id": str(r["_id"]), "phone": r.get("phone"), "responses": r.get("responses", {}), "payment": r.get("payment", {}), "status": r.get("status"), "created_at": r.get("created_at")} for r in registrations]
        return {
            "id": event_id, "name": event["name"], "slug": event["slug"],
            "description": event.get("description"), "event_date": event.get("event_date"),
            "registration_deadline": event.get("registration_deadline"),
            "max_participants": event.get("max_participants"),
            "status": event["status"], "pricing": event["pricing"],
            "venue": event.get("venue"), "form_fields": event.get("form_fields"),
            "registrations_count": reg_count, "registrations": regs,
            "qr_code_url": event.get("qr_code_url"), "created_at": event.get("created_at"),
        }
