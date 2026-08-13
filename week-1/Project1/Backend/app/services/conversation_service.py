from uuid import UUID

from app.db.redis import redis_client


class ConversationService:
    """
    Manages short-lived conversation history in Redis.

    Redis structure:

    conversation:{conversation_id}
        [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."},
            ...
        ]
    """

    CONVERSATION_TTL = 60 * 60 * 24  # 24 hours
    MAX_MESSAGES = 20

    def _key(self, conversation_id: UUID) -> str:
        return f"conversation:{conversation_id}"

    async def get_history(
        self,
        conversation_id: UUID,
    ) -> list[dict]:
        key = self._key(conversation_id)

        history = await redis_client.lrange(
            key,
            0,
            -1,
        )

        return history

    async def add_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
    ) -> None:
        key = self._key(conversation_id)

        message = {
            "role": role,
            "content": content,
        }

        await redis_client.rpush(
            key,
            message,
        )

        # Keep only the latest messages.
        await redis_client.ltrim(
            key,
            -self.MAX_MESSAGES,
            -1,
        )

        # Refresh conversation expiry.
        await redis_client.expire(
            key,
            self.CONVERSATION_TTL,
        )

    async def clear_history(
        self,
        conversation_id: UUID,
    ) -> None:
        key = self._key(conversation_id)

        await redis_client.delete(key)


conversation_service = ConversationService()