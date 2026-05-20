from fastapi import APIRouter, Depends
from app.core.middleware import TenantContext
from app.modules.workflows.service import WorkflowService

router = APIRouter()


@router.get("/")
async def list_workflows(tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await WorkflowService.list_workflows()


@router.post("/trigger/{workflow_id}")
async def trigger_workflow(workflow_id: str, payload: dict = {}, tenant_id: str = Depends(TenantContext.get_tenant_id)):
    return await WorkflowService.trigger(workflow_id, payload, tenant_id)
