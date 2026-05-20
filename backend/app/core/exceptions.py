from fastapi import HTTPException


class TenantNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="Tenant not found")


class EventNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="Event not found")


class PaymentFailed(HTTPException):
    def __init__(self, detail: str = "Payment processing failed"):
        super().__init__(status_code=402, detail=detail)


class RateLimitExceeded(HTTPException):
    def __init__(self):
        super().__init__(status_code=429, detail="Rate limit exceeded")
