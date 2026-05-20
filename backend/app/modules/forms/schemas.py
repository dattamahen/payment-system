from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class FormField(BaseModel):
    field_id: str
    label: str
    type: str  # text, number, email, phone, select, multi_select, file
    required: bool = True
    validation: Optional[Dict[str, Any]] = None
    options: Optional[List[str]] = None
    order: int


class FormCreate(BaseModel):
    name: str
    fields: List[FormField]


class FormUpdate(BaseModel):
    name: Optional[str] = None
    fields: Optional[List[FormField]] = None


class FormResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    fields: List[FormField]
    created_at: Optional[datetime] = None
