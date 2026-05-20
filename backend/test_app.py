"""Run: venv\Scripts\python.exe -m uvicorn test_app:app --port 8001"""
from fastapi import FastAPI
from pydantic import BaseModel
from app.database import Database
from app.core.security import verify_password, create_access_token, create_refresh_token
import traceback

app = FastAPI()


class LoginReq(BaseModel):
    email: str
    password: str


@app.on_event("startup")
async def startup():
    await Database.connect()


@app.post("/login")
async def login(body: LoginReq):
    try:
        db = Database.get_db()
        user = await db.users.find_one({"email": body.email})
        if not user:
            return {"error": "User not found"}
        
        valid = verify_password(body.password, user["password_hash"])
        if not valid:
            return {"error": "Invalid password"}
        
        token_data = {"sub": str(user["_id"]), "role": user["role"], "tenant_id": str(user.get("tenant_id") or "")}
        return {
            "access_token": create_access_token(token_data),
            "refresh_token": create_refresh_token(token_data),
            "token_type": "bearer"
        }
    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()}
