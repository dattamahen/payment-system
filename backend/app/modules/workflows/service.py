import httpx
from app.config import get_settings

settings = get_settings()


class WorkflowService:
    @staticmethod
    async def list_workflows():
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.N8N_BASE_URL}/api/v1/workflows",
                headers={"X-N8N-API-KEY": settings.N8N_API_KEY}
            )
            return resp.json()

    @staticmethod
    async def trigger(workflow_id: str, payload: dict, tenant_id: str):
        payload["tenant_id"] = tenant_id
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.N8N_BASE_URL}/api/v1/workflows/{workflow_id}/activate",
                headers={"X-N8N-API-KEY": settings.N8N_API_KEY},
                json=payload
            )
            return resp.json()
