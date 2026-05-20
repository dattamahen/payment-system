from pydantic import BaseModel
from typing import Optional


class CreateOrderRequest(BaseModel):
    registration_id: str
    event_id: str


class PaymentWebhook(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
