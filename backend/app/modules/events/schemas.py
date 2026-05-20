from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class Pricing(BaseModel):
    type: str = "free"  # free | paid | tiered
    amount: Optional[int] = None
    currency: str = "INR"
    tiers: Optional[List[Dict[str, Any]]] = None


class Venue(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    map_url: Optional[str] = None


class FormFieldInline(BaseModel):
    label: str
    type: str = "text"  # text, number, email, phone, select, multi_select, file
    required: bool = True
    options: Optional[List[str]] = None


class SheetsConfig(BaseModel):
    spreadsheet_id: str
    sheet_name: str = "Registrations"
    column_mapping: Dict[str, str] = {}


class EventCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    event_date: datetime
    registration_deadline: Optional[datetime] = None
    max_participants: int = 500
    pricing: Pricing = Pricing()
    venue: Optional[Venue] = None
    form_fields: Optional[List[FormFieldInline]] = None
    form_id: Optional[str] = None
    flow_id: Optional[str] = None
    sheets_config: Optional[SheetsConfig] = None


class EventUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[datetime] = None
    max_participants: Optional[int] = None
    pricing: Optional[Pricing] = None
    form_id: Optional[str] = None
    flow_id: Optional[str] = None
    sheets_config: Optional[SheetsConfig] = None
    status: Optional[str] = None


class EventResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    slug: str
    status: str
    pricing: Pricing
    venue: Optional[Venue] = None
    form_fields: Optional[List[FormFieldInline]] = None
    registrations_count: int = 0
    qr_code_url: Optional[str] = None
    created_at: Optional[datetime] = None
