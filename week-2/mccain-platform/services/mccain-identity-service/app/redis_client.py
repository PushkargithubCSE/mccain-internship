"""
Shared async Redis client. Used for:
  - Rate limiting (sliding window counters)
  - Refresh token allow-list / access token blacklist
  - Account lockout counters
"""
from redis import asyncio as aioredis

from app.config import settings

redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=50,
)


def get_redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=redis_pool)


async def close_redis() -> None:
    await redis_pool.disconnect()
