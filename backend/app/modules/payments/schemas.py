from pydantic import BaseModel


class CreateOrderRequest(BaseModel):
    registration_id: str
    event_id: str
