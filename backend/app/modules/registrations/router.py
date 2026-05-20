from fastapi import APIRouter, Depends
from typing import List
from app.core.middleware import TenantContext
from app.modules.registrations.service import RegistrationService

router = APIRouter()


@router.get("/")
async def list_registrations(event_id: str = None, tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await RegistrationService.list_by_tenant(tenant_id, event_id)


@router.get("/{registration_id}")
async def get_registration(registration_id: str, tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await RegistrationService.get(registration_id, tenant_id)
