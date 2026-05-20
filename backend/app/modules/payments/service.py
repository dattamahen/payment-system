import hmac
import hashlib
from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException
from app.database import get_db, get_tenant_db
from app.core.security import decrypt_secret


class PaymentService:
    @staticmethod
    async def create_order(tenant_id: str, event_id: str, registration_id: str):
        import razorpay
        db = await get_db()
        tenant_db = await get_tenant_db(tenant_id)

        tenant = await db.tenants.find_one({"_id": ObjectId(tenant_id)})
        event = await tenant_db.events.find_one({"_id": ObjectId(event_id)})
        if not tenant or not event:
            raise HTTPException(status_code=404, detail="Tenant or event not found")

        key_id = decrypt_secret(tenant["config"]["razorpay_key_id"])
        key_secret = decrypt_secret(tenant["config"]["razorpay_key_secret"])
        client = razorpay.Client(auth=(key_id, key_secret))

        amount = event["pricing"]["amount"]
        order = client.order.create({
            "amount": amount,
            "currency": event["pricing"].get("currency", "INR"),
            "receipt": registration_id,
            "notes": {"event_id": event_id, "tenant_id": tenant_id},
        })

        await tenant_db.registrations.update_one(
            {"_id": ObjectId(registration_id)},
            {"$set": {"payment.razorpay_order_id": order["id"], "payment.amount": amount}}
        )

        return {"order_id": order["id"], "amount": amount, "currency": event["pricing"].get("currency", "INR"), "key_id": key_id}

    @staticmethod
    async def handle_webhook(payload: dict):
        db = await get_db()
        await db.webhook_logs.insert_one({"source": "razorpay", "payload": payload, "processed": False, "created_at": datetime.utcnow()})

        event_type = payload.get("event")

        # Handle both payment.captured and payment_link.paid
        if event_type in ("payment.captured", "payment_link.paid"):
            if event_type == "payment_link.paid":
                payment_link_entity = payload["payload"]["payment_link"]["entity"]
                notes = payment_link_entity.get("notes", {})
                payment_id = payment_link_entity.get("id", "")
            else:
                payment_entity = payload["payload"]["payment"]["entity"]
                notes = payment_entity.get("notes", {})
                payment_id = payment_entity.get("id", "")

            tenant_id = notes.get("tenant_id")
            registration_id = notes.get("registration_id")

            if tenant_id and registration_id:
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
        return {"status": "ok"}

    @staticmethod
    async def get_status(registration_id: str, tenant_id: str):
        db = await get_tenant_db(tenant_id)
        reg = await db.registrations.find_one({"_id": ObjectId(registration_id)})
        if not reg:
            raise HTTPException(status_code=404, detail="Registration not found")
        return reg.get("payment", {})

    @staticmethod
    def verify_signature(order_id: str, payment_id: str, signature: str, secret: str) -> bool:
        msg = f"{order_id}|{payment_id}"
        generated = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(generated, signature)
