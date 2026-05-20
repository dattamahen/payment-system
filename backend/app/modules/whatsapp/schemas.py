from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class FlowCondition(BaseModel):
    field_id: str
    operator: str  # eq, neq, contains, gt, lt
    value: Any
    next: str


class FlowNode(BaseModel):
    node_id: str
    type: str  # message, question, condition, payment, confirmation
    content: str
    field_id: Optional[str] = None
    next: Optional[str] = None
    conditions: Optional[List[FlowCondition]] = None


class FlowCreate(BaseModel):
    name: str
    event_id: str
    nodes: List[FlowNode]
    fallback_message: str = "Sorry, I didn't understand. Please try again."


class FlowUpdate(BaseModel):
    name: Optional[str] = None
    nodes: Optional[List[FlowNode]] = None
    fallback_message: Optional[str] = None


class IncomingMessage(BaseModel):
    from_number: str  # sender phone
    message: str
    message_id: Optional[str] = None
    timestamp: Optional[str] = None
