from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId
from app.core.security import decode_token
from app.database import get_db

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    db = await get_db()
    user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def require_super_admin(user=Depends(get_current_user)):
    if user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    return user


async def require_tenant_admin(user=Depends(get_current_user)):
    if user.get("role") not in ("tenant_admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Tenant admin access required")
    return user


class TenantContext:
    """Extracts tenant_id from authenticated user for multi-tenant isolation."""

    @staticmethod
    async def get_tenant_id(user=Depends(get_current_user)) -> str:
        tenant_id = user.get("tenant_id")
        if not tenant_id and user.get("role") != "super_admin":
            raise HTTPException(status_code=403, detail="No tenant associated")
        return tenant_id
