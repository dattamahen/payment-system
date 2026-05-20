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
    """Razorpay webhook - verifies signature and updates registration."""
    body = await request.json()
    return await PaymentService.handle_webhook(body)


@router.get("/{registration_id}")
async def get_payment_status(registration_id: str, tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await PaymentService.get_status(registration_id, tenant_id)
