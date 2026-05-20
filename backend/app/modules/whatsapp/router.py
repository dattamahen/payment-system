from fastapi import APIRouter, Request, Depends, HTTPException
import httpx
from app.config import get_settings
from app.modules.whatsapp.flow_engine import FlowEngine
from app.database import get_db

settings = get_settings()
router = APIRouter()


@router.get("/webhook")
async def verify_webhook(hub_mode: str = "", hub_verify_token: str = "", hub_challenge: str = ""):
    """WhatsApp webhook verification endpoint."""
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_message(request: Request):
    """Receive WhatsApp messages from Meta and forward to n8n for processing."""
    body = await request.json()
    db = await get_db()

    # Log webhook
    await db.webhook_logs.insert_one({"source": "whatsapp", "payload": body, "processed": False})

    # Forward full payload to n8n which handles the conversation + reply
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{settings.N8N_BASE_URL}/webhook/whatsapp-webhook",
                json=body,
                timeout=10.0
            )
    except Exception as e:
        import logging
        logging.error(f"Failed to forward to n8n: {e}")

    await db.webhook_logs.update_one({"payload.entry": body["entry"]}, {"$set": {"processed": True}})
    return {"status": "ok"}


class WhatsAppService:
    @staticmethod
    async def send_message(phone_number_id: str, to: str, text: str, tenant: dict):
        import httpx
        from app.core.security import decrypt_secret

        api_key = decrypt_secret(tenant["config"]["whatsapp_api_key"])
        url = f"{settings.WHATSAPP_API_URL}/{phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text}
        }
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, headers=headers)
