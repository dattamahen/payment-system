from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime


class BrandingConfig(BaseModel):
    logo_url: Optional[str] = None
    primary_color: Optional[str] = "#1976d2"
    welcome_message: Optional[str] = "Welcome!"


class TenantConfig(BaseModel):
    whatsapp_number: Optional[str] = None
    whatsapp_api_key: Optional[str] = None
    razorpay_key_id: Optional[str] = None
    razorpay_key_secret: Optional[str] = None
    google_sheets_credentials: Optional[str] = None
    branding: Optional[BrandingConfig] = None


class TenantCreate(BaseModel):
    name: str
    slug: str
    owner_email: str
    owner_password: str
    plan: str = "free"
    config: Optional[TenantConfig] = None


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    plan: Optional[str] = None
    config: Optional[TenantConfig] = None
    status: Optional[str] = None


class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    status: str
    created_at: Optional[datetime] = None


class TenantUserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: str = "tenant_admin"


class TenantUserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    tenant_id: str
