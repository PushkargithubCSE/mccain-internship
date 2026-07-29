import json

from app.core.config import settings
from app.services.cache.redis_service import redis_service


class SessionService:

    async def create_session(
        self,
        user_id: int,
        token_id: str,
    ) -> None:
        key = f"session:{token_id}"

        data = {
            "user_id": user_id,
        }

        ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

        await redis_service.set(
            key=key,
            value=json.dumps(data),
            ttl=ttl,
        )

    async def get_session(self, token_id: str):
        value = await redis_service.get(
            f"session:{token_id}"
        )

        if value is None:
            return None

        return json.loads(value)

    async def revoke_session(self, token_id: str) -> bool:
        return await redis_service.delete(
            f"session:{token_id}"
        )


session_service = SessionService()