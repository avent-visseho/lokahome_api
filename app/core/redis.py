"""
Redis configuration for caching and pub/sub.
"""
import json
from collections.abc import AsyncGenerator
from typing import Any

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.core.config import settings


class RedisManager:
    """Manages Redis connections and operations."""

    def __init__(self):
        self._client: Redis | None = None

    async def connect(self) -> None:
        """Establish Redis connection."""
        self._client = await aioredis.from_url(
            str(settings.REDIS_URL),
            encoding="utf-8",
            decode_responses=True,
        )

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()

    @property
    def client(self) -> Redis:
        """Get Redis client."""
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client

    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        value = await self.client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def set(
        self,
        key: str,
        value: Any,
        expire: int | None = None,
    ) -> None:
        """Set value in cache."""
        expire = expire or settings.REDIS_CACHE_EXPIRE
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self.client.set(key, value, ex=expire)

    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        await self.client.delete(key)

    async def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching pattern."""
        async for key in self.client.scan_iter(match=pattern):
            await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return bool(await self.client.exists(key))

    async def incr(self, key: str) -> int:
        """Increment counter."""
        return await self.client.incr(key)

    async def expire(self, key: str, seconds: int) -> None:
        """Set expiration on key."""
        await self.client.expire(key, seconds)


# Global instance
redis_manager = RedisManager()


async def get_redis() -> AsyncGenerator[Redis, None]:
    """Dependency for Redis client."""
    yield redis_manager.client
