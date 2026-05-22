from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.core.middleware import require_tenant_admin, TenantContext
from app.modules.events.schemas import EventCreate, EventUpdate, EventResponse
from app.modules.events.service import EventService

router = APIRouter()


@router.post("/", response_model=EventResponse)
async def create_event(body: EventCreate, tenant_id: str = Depends(TenantContext.get_active_tenant_id)):
    return await EventService.create(tenant_id, body)


@router.get("/", response_model=List[EventResponse])
async def list_events(tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await EventService.list_by_tenant(tenant_id)


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: str, tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await EventService.get(event_id, tenant_id)


@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(event_id: str, body: EventUpdate, tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await EventService.update(event_id, tenant_id, body)


@router.post("/{event_id}/generate-qr")
async def generate_qr(event_id: str, tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await EventService.generate_qr(event_id, tenant_id)


@router.patch("/{event_id}/status")
async def change_event_status(event_id: str, status: str, tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await EventService.change_status(event_id, tenant_id, status)


@router.get("/{event_id}/registrations")
async def get_event_registrations(event_id: str, tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await EventService.get_registrations(event_id, tenant_id)


@router.get("/{event_id}/registrations/pdf")
async def download_registrations_pdf(event_id: str, tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await EventService.generate_pdf(event_id, tenant_id)


@router.get("/{event_id}/registrations/download")
async def download_pdf_public(event_id: str, token: str):
    """PDF download via query token (for browser new tab)."""
    from app.core.security import decode_token
    from bson import ObjectId
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    tenant_id = payload.get("tenant_id", "")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="No tenant")
    return await EventService.generate_pdf(event_id, tenant_id)


@router.get("/{event_id}/registrations/excel")
async def download_excel(event_id: str, tenant_id: str = None, user=Depends(require_tenant_admin)):
    tid = tenant_id or user.get("tenant_id")
    if not tid:
        raise HTTPException(status_code=400, detail="tenant_id required")
    return await EventService.generate_excel(event_id, tid)
