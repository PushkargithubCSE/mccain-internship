import asyncio

from app.db.redis import redis_client


async def main():
    try:
        # 1. Check connection
        pong = await redis_client.ping()
        print("PING:", pong)

        # 2. SET with 60-second TTL
        await redis_client.set(
            "test:user:1",
            "Pushkar",
            ex=60,
        )

        print("SET successful")

        # 3. GET
        value = await redis_client.get("test:user:1")
        print("GET:", value)

        # 4. Check remaining TTL
        ttl = await redis_client.ttl("test:user:1")
        print("TTL:", ttl)

        # 5. DELETE
        deleted = await redis_client.delete("test:user:1")
        print("DELETE:", deleted)

        # 6. Verify deletion
        value = await redis_client.get("test:user:1")
        print("After DELETE:", value)

    finally:
        await redis_client.aclose()


asyncio.run(main())