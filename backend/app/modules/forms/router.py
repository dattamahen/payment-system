from fastapi import APIRouter, Depends
from typing import List
from app.core.middleware import require_tenant_admin, TenantContext
from app.modules.forms.schemas import FormCreate, FormUpdate, FormResponse
from app.modules.forms.service import FormService

router = APIRouter()


@router.post("/", response_model=FormResponse)
async def create_form(body: FormCreate, tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await FormService.create(tenant_id, body)


@router.get("/", response_model=List[FormResponse])
async def list_forms(tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await FormService.list_by_tenant(tenant_id)


@router.get("/{form_id}", response_model=FormResponse)
async def get_form(form_id: str, tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await FormService.get(form_id, tenant_id)


@router.patch("/{form_id}", response_model=FormResponse)
async def update_form(form_id: str, body: FormUpdate, tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await FormService.update(form_id, tenant_id, body)


@router.delete("/{form_id}")
async def delete_form(form_id: str, tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await FormService.delete(form_id, tenant_id)
