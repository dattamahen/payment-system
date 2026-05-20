"""
n8n Integration API - Public endpoints for n8n workflows.
n8n uses these to:
1. Get event registration questions
2. Submit user responses collected via WhatsApp
3. Sync responses to tenant's Google Sheet
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, Dict
from app.config import get_settings
from app.modules.n8n.service import N8nService

settings = get_settings()
router = APIRouter()


def verify_n8n_key(x_api_key: str = Header(...)):
    if x_api_key != settings.N8N_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


class SubmitResponseRequest(BaseModel):
    phone: str
    responses: Dict[str, str]
    payment_status: Optional[str] = "pending"


class CreatePaymentRequest(BaseModel):
    registration_id: str
    phone: str


@router.get("/{tenant_id}/events/{event_id}/questions")
async def get_event_questions(tenant_id: str, event_id: str, x_api_key: str = Header(...)):
    """n8n calls this to get the registration questions for an event."""
    verify_n8n_key(x_api_key)
    return await N8nService.get_questions(tenant_id, event_id)


@router.post("/{tenant_id}/events/{event_id}/responses")
async def submit_response(tenant_id: str, event_id: str, body: SubmitResponseRequest, x_api_key: str = Header(...)):
    """n8n calls this after collecting all answers from a user via WhatsApp."""
    verify_n8n_key(x_api_key)
    return await N8nService.submit_response(tenant_id, event_id, body.phone, body.responses, body.payment_status)


@router.post("/{tenant_id}/events/{event_id}/sync-sheet")
async def sync_to_sheet(tenant_id: str, event_id: str, x_api_key: str = Header(...)):
    """n8n calls this to push new registrations to the tenant's Google Sheet."""
    verify_n8n_key(x_api_key)
    return await N8nService.sync_to_sheet(tenant_id, event_id)


@router.post("/{tenant_id}/events/{event_id}/create-payment")
async def create_payment_link(tenant_id: str, event_id: str, body: CreatePaymentRequest, x_api_key: str = Header(...)):
    """n8n calls this to generate a Razorpay payment link for a registration."""
    verify_n8n_key(x_api_key)
    return await N8nService.create_payment_link(tenant_id, event_id, body.registration_id, body.phone)


@router.get("/resolve/{wa_number}")
async def resolve_tenant_by_whatsapp(wa_number: str, x_api_key: str = Header(...)):
    """n8n calls this to find which tenant owns a WhatsApp number and their active events."""
    verify_n8n_key(x_api_key)
    return await N8nService.resolve_by_whatsapp(wa_number)


class StartSessionRequest(BaseModel):
    phone: str
    tenant_id: str
    event_id: str


@router.post("/session/start")
async def start_session(body: StartSessionRequest, x_api_key: str = Header(...)):
    """n8n calls this to start a registration session for a user."""
    verify_n8n_key(x_api_key)
    return await N8nService.get_questions(body.tenant_id, body.event_id)


class ConfirmPaymentRequest(BaseModel):
    registration_id: str
    phone: str
    amount: float
    status: str


@router.post("/{tenant_id}/events/{event_id}/payment-confirmed")
async def confirm_payment(tenant_id: str, event_id: str, body: ConfirmPaymentRequest, x_api_key: str = Header(...)):
    """n8n calls this when Razorpay payment is confirmed. Updates registration and sends WhatsApp confirmation."""
    verify_n8n_key(x_api_key)
    from app.database import get_db, get_tenant_db
    from app.core.security import decrypt_secret
    import httpx

    db = await get_db()
    tenant_db = await get_tenant_db(tenant_id)

    # Update registration status
    from bson import ObjectId
    await tenant_db.registrations.update_one(
        {"_id": ObjectId(body.registration_id)},
        {"$set": {"payment.status": "paid", "status": "completed"}}
    )

    # Sync to sheet
    try:
        await N8nService.sync_to_sheet(tenant_id, event_id)
    except Exception:
        pass

    # Send WhatsApp confirmation using tenant's token
    tenant = await db.tenants.find_one({"_id": ObjectId(tenant_id)})
    if tenant and tenant.get("config", {}).get("whatsapp_api_key"):
        phone_number_id = tenant["config"].get("whatsapp_phone_number_id") or tenant["config"].get("whatsapp_number_id", "")
        api_key = decrypt_secret(tenant["config"]["whatsapp_api_key"])
        url = f"{settings.WHATSAPP_API_URL}/{phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "messaging_product": "whatsapp",
            "to": body.phone,
            "type": "text",
            "text": {"body": f"\u2705 Payment of \u20b9{body.amount} received! Your registration is confirmed. Thank you!"}
        }
        try:
            async with httpx.AsyncClient() as client:
                await client.post(url, json=payload, headers=headers)
        except Exception:
            pass

    return {"status": "confirmed", "registration_id": body.registration_id}


class SessionMessageRequest(BaseModel):
    phone: str
    text: str
    wa_number: str


@router.post("/session/message")
async def handle_message(body: SessionMessageRequest, x_api_key: str = Header(...)):
    """n8n calls this for each incoming message. Handles full conversation state and sends reply."""
    verify_n8n_key(x_api_key)
    result = await N8nService.handle_conversation(body.phone, body.text, body.wa_number)

    # Send WhatsApp reply directly from backend using tenant's stored token
    if result.get("action") == "reply" and result.get("message"):
        from app.database import get_db
        from app.core.security import decrypt_secret
        import httpx

        db = await get_db()
        tenant = await db.tenants.find_one({
            "$or": [
                {"config.whatsapp_number": body.wa_number},
                {"config.whatsapp_phone_number_id": body.wa_number},
                {"config.whatsapp_number_id": body.wa_number},
            ],
            "config.whatsapp_api_key": {"$exists": True},
            "status": "active"
        })
        if tenant and tenant.get("config", {}).get("whatsapp_api_key"):
            phone_number_id = tenant["config"].get("whatsapp_phone_number_id") or tenant["config"].get("whatsapp_number_id") or body.wa_number
            api_key = decrypt_secret(tenant["config"]["whatsapp_api_key"])
            url = f"{settings.WHATSAPP_API_URL}/{phone_number_id}/messages"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "messaging_product": "whatsapp",
                "to": body.phone,
                "type": "text",
                "text": {"body": result["message"]}
            }
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(url, json=payload, headers=headers)
                result["reply_sent"] = True
            except Exception:
                result["reply_sent"] = False

    return result
