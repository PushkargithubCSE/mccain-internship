"""
Global rate-limiting middleware. Applies a baseline per-IP limit to every
request. Tighter, endpoint-specific limits (login, register) are enforced
separately via the `rate_limit_dependency` in api/deps.py, so sensitive
endpoints get double protection: the global ceiling here, plus a stricter
bucket at the route level.
"""
import structlog
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.core.rate_limiter import RedisSlidingWindowRateLimiter
from app.redis_client import get_redis

logger = structlog.get_logger(__name__)


def _client_ip(request: Request) -> str:
    # Trust X-Forwarded-For only if you're behind a trusted proxy/load balancer.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    EXEMPT_PATHS = {"/health", "/health/live", "/health/ready", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.RATE_LIMIT_ENABLED or request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        redis = get_redis()
        limiter = RedisSlidingWindowRateLimiter(redis)
        identifier = _client_ip(request)

        result = await limiter.check(
            scope="global",
            identifier=identifier,
            max_requests=settings.RATE_LIMIT_DEFAULT_MAX_REQUESTS,
            window_seconds=settings.RATE_LIMIT_DEFAULT_WINDOW_SECONDS,
        )

        if not result.allowed:
            logger.warning("rate_limit_exceeded", scope="global", identifier=identifier, path=request.url.path)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please slow down."},
                headers={
                    "Retry-After": str(int(result.retry_after_seconds) + 1),
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        return response
