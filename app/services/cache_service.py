import json
import redis.asyncio as redis
from typing import Optional, Any
from app.database import settings
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """Сервис для работы с Redis кешем"""
    
    def __init__(self):
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """Устанавливает соединение с Redis"""
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5
            )
            logger.info("Connected to Redis")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    async def get(self, key: str) -> Optional[Any]:
        """Получить значение из кеша"""
        if not self.redis_client:
            return None
        try:
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Сохранить значение в кеш с TTL"""
        if not self.redis_client:
            return False
        try:
            data = json.dumps(value, default=str)
            if ttl:
                await self.redis_client.setex(key, ttl, data)
            else:
                await self.redis_client.set(key, data)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Удалить ключ из кеша"""
        if not self.redis_client:
            return False
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Удалить все ключи по шаблону"""
        if not self.redis_client:
            return 0
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                await self.redis_client.delete(*keys)
                return len(keys)
            return 0
        except Exception as e:
            logger.error(f"Redis delete_pattern error: {e}")
            return 0


# Создаём глобальный экземпляр
cache_service = CacheService()


async def get_cache_service() -> CacheService:
    """Dependency для внедрения кеш-сервиса"""
    return cache_service