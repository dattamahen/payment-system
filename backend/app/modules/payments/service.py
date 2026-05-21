import hmac
import hashlib
import json
from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException
from app.database import get_db, get_tenant_db
from app.core.security import decrypt_secret


class PaymentService:
    @staticmethod
    async def create_order(tenant_id: str, event_id: str, registration_id: str):
        """Creates a Razorpay payment link (used by n8n flow via WhatsApp)."""
        import razorpay
        db = await get_db()
        tenant_db = await get_tenant_db(tenant_id)

        tenant = await db.tenants.find_one({"_id": ObjectId(tenant_id)})
        event = await tenant_db.events.find_one({"_id": ObjectId(event_id)})
        if not tenant or not event:
            raise HTTPException(status_code=404, detail="Tenant or event not found")

        config = tenant.get("config", {})
        if not config.get("razorpay_key_id") or not config.get("razorpay_key_secret"):
            raise HTTPException(status_code=400, detail="Razorpay not configured for this tenant")

        key_id = decrypt_secret(config["razorpay_key_id"])
        key_secret = decrypt_secret(config["razorpay_key_secret"])
        client = razorpay.Client(auth=(key_id, key_secret))

        amount = event["pricing"]["amount"]
        order = client.order.create({
            "amount": amount * 100,  # paise
            "currency": event["pricing"].get("currency", "INR"),
            "receipt": registration_id,
            "notes": {"event_id": event_id, "tenant_id": tenant_id, "registration_id": registration_id},
        })

        await tenant_db.registrations.update_one(
            {"_id": ObjectId(registration_id)},
            {"$set": {"payment.razorpay_order_id": order["id"], "payment.amount": amount, "payment.status": "created"}}
        )

        return {"order_id": order["id"], "amount": amount, "currency": event["pricing"].get("currency", "INR"), "key_id": key_id}

    @staticmethod
    async def handle_webhook(payload: dict, signature: str = None):
        """Handles Razorpay webhook (payment.captured / payment_link.paid)."""
        db = await get_db()
        await db.webhook_logs.insert_one({"source": "razorpay", "payload": payload, "processed": False, "created_at": datetime.utcnow()})

        event_type = payload.get("event")

        if event_type in ("payment.captured", "payment_link.paid"):
            if event_type == "payment_link.paid":
                entity = payload["payload"]["payment_link"]["entity"]
            else:
                entity = payload["payload"]["payment"]["entity"]

            notes = entity.get("notes", {})
            payment_id = entity.get("id", "")
            tenant_id = notes.get("tenant_id")
            registration_id = notes.get("registration_id")

            if not tenant_id or not registration_id:
                return {"status": "ok", "message": "Missing notes, skipped"}

            # Verify webhook signature
            if signature:
                tenant = await db.tenants.find_one({"_id": ObjectId(tenant_id)})
                if tenant and tenant.get("config", {}).get("razorpay_webhook_secret"):
                    webhook_secret = decrypt_secret(tenant["config"]["razorpay_webhook_secret"])
                elif tenant and tenant.get("config", {}).get("razorpay_key_secret"):
                    webhook_secret = decrypt_secret(tenant["config"]["razorpay_key_secret"])
                else:
                    webhook_secret = None

                if webhook_secret:
                    body_bytes = json.dumps(payload, separators=(',', ':')).encode()
                    expected = hmac.new(webhook_secret.encode(), body_bytes, hashlib.sha256).hexdigest()
                    if not hmac.compare_digest(expected, signature):
                        raise HTTPException(status_code=400, detail="Invalid webhook signature")

            tenant_db = await get_tenant_db(tenant_id)
            await tenant_db.registrations.update_one(
                {"_id": ObjectId(registration_id)},
                {"$set": {
                    "payment.status": "paid",
                    "payment.razorpay_payment_id": payment_id,
                    "payment.paid_at": datetime.utcnow(),
                    "status": "completed",
                }}
            )
            await db.webhook_logs.update_one(
                {"payload": payload, "processed": False},
                {"$set": {"processed": True}}
            )
        return {"status": "ok"}

    @staticmethod
    async def get_status(registration_id: str, tenant_id: str):
        db = await get_tenant_db(tenant_id)
        reg = await db.registrations.find_one({"_id": ObjectId(registration_id)})
        if not reg:
            raise HTTPException(status_code=404, detail="Registration not found")
        return reg.get("payment", {})
