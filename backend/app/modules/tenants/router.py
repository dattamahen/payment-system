from fastapi import APIRouter, Depends
from app.core.middleware import require_super_admin
from app.modules.tenants.schemas import TenantCreate, TenantUpdate, TenantResponse, TenantUserCreate, TenantUserResponse
from app.modules.tenants.service import TenantService
from typing import List

router = APIRouter()


@router.post("/", response_model=TenantResponse)
async def create_tenant(body: TenantCreate, user=Depends(require_super_admin)):
    return await TenantService.create(body)


@router.get("/", response_model=List[TenantResponse])
async def list_tenants(user=Depends(require_super_admin)):
    return await TenantService.list_all()


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(tenant_id: str, body: TenantUpdate, user=Depends(require_super_admin)):
    return await TenantService.update(tenant_id, body)


@router.delete("/{tenant_id}")
async def deactivate_tenant(tenant_id: str, user=Depends(require_super_admin)):
    return await TenantService.deactivate(tenant_id)


@router.post("/{tenant_id}/users", response_model=TenantUserResponse)
async def create_tenant_user(tenant_id: str, body: TenantUserCreate, user=Depends(require_super_admin)):
    return await TenantService.create_tenant_user(tenant_id, body)


@router.get("/{tenant_id}/events")
async def get_tenant_events(tenant_id: str, user=Depends(require_super_admin)):
    return await TenantService.get_tenant_events(tenant_id)


@router.get("/{tenant_id}/events/{event_id}")
async def get_tenant_event_detail(tenant_id: str, event_id: str, user=Depends(require_super_admin)):
    return await TenantService.get_tenant_event_detail(tenant_id, event_id)


@router.patch("/{tenant_id}/events/{event_id}/status")
async def change_tenant_event_status(tenant_id: str, event_id: str, status: str, user=Depends(require_super_admin)):
    from app.modules.events.service import EventService
    return await EventService.change_status(event_id, tenant_id, status)
