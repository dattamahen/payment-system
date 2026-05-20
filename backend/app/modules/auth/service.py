from fastapi import HTTPException
from app.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.modules.auth.schemas import RegisterRequest


class AuthService:
    @staticmethod
    async def login(email: str, password: str):
        db = await get_db()
        user = await db.users.find_one({"email": email})
        if not user or not verify_password(password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token_data = {"sub": str(user["_id"]), "role": user["role"], "tenant_id": str(user.get("tenant_id") or "")}
        return {
            "access_token": create_access_token(token_data),
            "refresh_token": create_refresh_token(token_data),
        }

    @staticmethod
    async def register(body: RegisterRequest):
        db = await get_db()
        existing = await db.users.find_one({"email": body.email})
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        user_doc = {
            "email": body.email,
            "password_hash": hash_password(body.password),
            "name": body.name,
            "role": body.role,
            "tenant_id": body.tenant_id,
            "status": "active",
        }
        result = await db.users.insert_one(user_doc)
        token_data = {"sub": str(result.inserted_id), "role": body.role, "tenant_id": body.tenant_id or ""}
        return {
            "access_token": create_access_token(token_data),
            "refresh_token": create_refresh_token(token_data),
        }

    @staticmethod
    async def refresh_token(refresh_token: str):
        payload = decode_token(refresh_token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        return {
            "access_token": create_access_token({"sub": payload["sub"], "role": payload["role"], "tenant_id": payload["tenant_id"]}),
            "refresh_token": create_refresh_token({"sub": payload["sub"], "role": payload["role"], "tenant_id": payload["tenant_id"]}),
        }
