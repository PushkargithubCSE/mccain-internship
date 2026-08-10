"""
Redis-backed sliding-window rate limiter.

Algorithm: sliding window log implemented with a Redis sorted set.
  - Key: rate_limit:{scope}:{identifier}
  - Member: unique request id (uuid), Score: request timestamp (ms)
  - On each call: atomically (via Lua script, so it's race-free under
    concurrent requests) trim entries older than `window_seconds`,
    count remaining entries, and either add the new entry (allowed)
    or reject.

This is more accurate than a fixed-window counter (no burst-at-boundary
problem) while staying O(log N) per request and self-expiring via TTL,
so it needs no background cleanup job.
"""
import time
import uuid
from dataclasses import dataclass

from redis.asyncio import Redis

# KEYS[1] = redis key
# ARGV[1] = current timestamp in ms
# ARGV[2] = window size in ms
# ARGV[3] = max requests allowed in window
# ARGV[4] = unique member id for this request
# ARGV[5] = key TTL in seconds (safety net so keys don't linger forever)
_SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
local ttl = tonumber(ARGV[5])

local window_start = now - window

redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
local current = redis.call('ZCARD', key)

if current < limit then
    redis.call('ZADD', key, now, member)
    redis.call('EXPIRE', key, ttl)
    local remaining = limit - current - 1
    return {1, remaining}
else
    -- compute retry_after from the oldest entry still in window
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after_ms = window
    if oldest[2] ~= nil then
        retry_after_ms = (tonumber(oldest[2]) + window) - now
    end
    return {0, 0, retry_after_ms}
end
"""


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    limit: int
    retry_after_seconds: float = 0.0


class RedisSlidingWindowRateLimiter:
    def __init__(self, redis: Redis):
        self._redis = redis
        self._script = redis.register_script(_SLIDING_WINDOW_LUA)

    async def check(
        self,
        scope: str,
        identifier: str,
        max_requests: int,
        window_seconds: int,
    ) -> RateLimitResult:
        """
        scope: logical bucket, e.g. 'login', 'register', 'global'
        identifier: e.g. client IP, user id, or "ip:route"
        """
        key = f"rate_limit:{scope}:{identifier}"
        now_ms = int(time.time() * 1000)
        window_ms = window_seconds * 1000
        member = uuid.uuid4().hex
        ttl = window_seconds + 5  # small safety buffer

        result = await self._script(
            keys=[key],
            args=[now_ms, window_ms, max_requests, member, ttl],
        )
        allowed = bool(int(result[0]))
        if allowed:
            return RateLimitResult(allowed=True, remaining=int(result[1]), limit=max_requests)
        retry_after_ms = int(result[2]) if len(result) > 2 else window_ms
        return RateLimitResult(
            allowed=False,
            remaining=0,
            limit=max_requests,
            retry_after_seconds=max(retry_after_ms, 0) / 1000,
        )
