from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "EventPay SaaS"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "eventpay"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_ENABLED: bool = False

    # CORS
    ALLOWED_ORIGINS: list = ["http://localhost:4200"]

    # JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # WhatsApp Business API
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v18.0"
    WHATSAPP_VERIFY_TOKEN: str = "verify-token"

    # Razorpay (per-tenant override via DB)
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    # n8n
    N8N_BASE_URL: str = "http://localhost:5678"
    N8N_API_KEY: str = ""

    # Encryption key for tenant secrets
    ENCRYPTION_KEY: str = "32-byte-key-for-fernet-encryption"

    # Admin (first boot)
    ADMIN_EMAIL: str = "admin@eventpay.com"
    ADMIN_PASSWORD: str = "admin123"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
