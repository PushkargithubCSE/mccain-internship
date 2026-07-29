from app.db.redis import redis_client


class RateLimiter:

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int]:

        current = await redis_client.incr(key)

        if current == 1:
            await redis_client.expire(
                key,
                window_seconds,
            )

        return current <= limit, current


rate_limiter = RateLimiter()