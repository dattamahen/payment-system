from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback
import logging

logging.basicConfig(level=logging.INFO)
from contextlib import asynccontextmanager
from app.config import get_settings
from app.database import Database, get_db
from app.core.security import hash_password
from app.modules.auth.router import router as auth_router
from app.modules.tenants.router import router as tenants_router
from app.modules.events.router import router as events_router
from app.modules.forms.router import router as forms_router
from app.modules.payments.router import router as payments_router
from app.modules.whatsapp.router import router as whatsapp_router
from app.modules.workflows.router import router as workflows_router
from app.modules.sheets.router import router as sheets_router
from app.modules.registrations.router import router as registrations_router
from app.modules.n8n.router import router as n8n_router

settings = get_settings()


async def seed_admin():
    db = Database.get_db()
    existing = await db.users.find_one({"email": "admin@eventpay.com", "role": "super_admin"})
    if not existing:
        await db.users.insert_one({
            "email": "admin@eventpay.com",
            "password_hash": hash_password("admin123"),
            "name": "Super Admin",
            "role": "super_admin",
            "tenant_id": None,
            "status": "active",
        })
        logging.info("Admin user seeded. CHANGE PASSWORD IMMEDIATELY.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await Database.connect()
    await seed_admin()
    yield
    await Database.disconnect()


from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logging.error(f"Unhandled: {traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"detail": str(exc)})

# Register routers
app.include_router(auth_router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Auth"])
app.include_router(tenants_router, prefix=f"{settings.API_V1_PREFIX}/admin/tenants", tags=["Tenants"])
app.include_router(events_router, prefix=f"{settings.API_V1_PREFIX}/events", tags=["Events"])
app.include_router(forms_router, prefix=f"{settings.API_V1_PREFIX}/forms", tags=["Forms"])
app.include_router(payments_router, prefix=f"{settings.API_V1_PREFIX}/payments", tags=["Payments"])
app.include_router(whatsapp_router, prefix=f"{settings.API_V1_PREFIX}/whatsapp", tags=["WhatsApp"])
app.include_router(workflows_router, prefix=f"{settings.API_V1_PREFIX}/workflows", tags=["Workflows"])
app.include_router(sheets_router, prefix=f"{settings.API_V1_PREFIX}/sheets", tags=["Sheets"])
app.include_router(registrations_router, prefix=f"{settings.API_V1_PREFIX}/registrations", tags=["Registrations"])
app.include_router(n8n_router, prefix=f"{settings.API_V1_PREFIX}/n8n", tags=["n8n Integration"])


# Direct webhook path for Meta WhatsApp - matches /webhook/whatsapp-webhook
from app.modules.whatsapp.router import verify_webhook, receive_message
app.get("/webhook/whatsapp-webhook")(verify_webhook)
app.post("/webhook/whatsapp-webhook")(receive_message)


@app.get("/health")
async def health():
    return {"status": "ok"}
