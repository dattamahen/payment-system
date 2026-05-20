from motor.motor_asyncio import AsyncIOMotorClient
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class InMemoryCache:
    """Fallback when Redis is unavailable."""
    def __init__(self):
        self._store = {}

    async def get(self, key):
        return self._store.get(key)

    async def set(self, key, value, ex=None):
        self._store[key] = value

    async def delete(self, key):
        self._store.pop(key, None)

    async def close(self):
        pass


class Database:
    client: AsyncIOMotorClient = None
    redis = None

    @classmethod
    async def connect(cls):
        cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
        cls.db = cls.client[settings.MONGODB_DB_NAME]
        logger.info(f"Connected to MongoDB: {settings.MONGODB_DB_NAME}")

        # Try Redis, fallback to in-memory
        if settings.REDIS_ENABLED:
            try:
                from redis.asyncio import Redis
                cls.redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
                await cls.redis.ping()
                logger.info("Connected to Redis")
            except Exception as e:
                logger.warning(f"Redis unavailable ({e}), using in-memory cache")
                cls.redis = InMemoryCache()
        else:
            cls.redis = InMemoryCache()
            logger.info("Redis disabled, using in-memory cache")

    @classmethod
    async def disconnect(cls):
        if cls.client:
            cls.client.close()
        if cls.redis:
            await cls.redis.close()

    @classmethod
    def get_db(cls):
        return cls.db

    @classmethod
    def get_tenant_db(cls, tenant_id: str):
        """Returns a namespace helper that prefixes collection names with tenant_id.
        All data stays in the same eventpay database."""
        return TenantCollections(cls.db, tenant_id)

    @classmethod
    def get_redis(cls):
        return cls.redis


class TenantCollections:
    """Provides tenant-scoped collections within the same database.
    e.g., tenant_abc123_events, tenant_abc123_registrations"""

    def __init__(self, db, tenant_id: str):
        self._db = db
        self._prefix = f"tenant_{tenant_id}"

    def __getattr__(self, name):
        return self._db[f"{self._prefix}_{name}"]


async def get_db():
    return Database.get_db()


async def get_tenant_db(tenant_id: str):
    return Database.get_tenant_db(tenant_id)


async def get_redis():
    return Database.get_redis()
