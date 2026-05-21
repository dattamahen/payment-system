from fastapi import APIRouter, Request, Depends, HTTPException
from app.modules.payments.schemas import CreateOrderRequest
from app.modules.payments.service import PaymentService
from app.core.middleware import TenantContext

router = APIRouter()


@router.post("/create-order")
async def create_order(body: CreateOrderRequest, tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await PaymentService.create_order(tenant_id, body.event_id, body.registration_id)


@router.post("/webhook")
async def payment_webhook(request: Request):
    """Razorpay webhook - called when payment is captured."""
    body = await request.json()
    signature = request.headers.get("X-Razorpay-Signature")
    return await PaymentService.handle_webhook(body, signature)


@router.get("/{registration_id}")
async def get_payment_status(registration_id: str, tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await PaymentService.get_status(registration_id, tenant_id)
