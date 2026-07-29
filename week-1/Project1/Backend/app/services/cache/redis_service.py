from app.db.redis import redis_client


class RedisService:
    def __init__(self):
        self.client = redis_client

    async def set(
        self,
        key: str,
        value: str,
        ttl: int | None = None,
    ) -> None:
        await self.client.set(
            name=key,
            value=value,
            ex=ttl,
        )

    async def get(self, key: str) -> str | None:
        return await self.client.get(key)

    async def delete(self, key: str) -> bool:
        deleted_count = await self.client.delete(key)
        return deleted_count > 0

    async def exists(self, key: str) -> bool:
        return bool(await self.client.exists(key))

    async def ttl(self, key: str) -> int:
        return await self.client.ttl(key)


redis_service = RedisService()