from fastapi import APIRouter, Depends
from app.core.middleware import TenantContext
from app.modules.sheets.service import SheetsService

router = APIRouter()


@router.post("/{event_id}/sync")
async def sync_to_sheets(event_id: str, tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await SheetsService.sync_registrations(tenant_id, event_id)


@router.get("/{event_id}/mapping")
async def get_mapping(event_id: str, tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await SheetsService.get_mapping(tenant_id, event_id)


@router.patch("/{event_id}/mapping")
async def update_mapping(event_id: str, mapping: dict, tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await SheetsService.update_mapping(tenant_id, event_id, mapping)
