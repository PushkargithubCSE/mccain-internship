import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.rate_limiter import RedisSlidingWindowRateLimiter
from app.core.security import TokenType, decode_token
from app.database import get_db
from app.models.user import User, UserRole
from app.redis_client import get_redis

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False)


def redis_dependency() -> Redis:
    return get_redis()


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(redis_dependency),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception

    try:
        payload = decode_token(token)
    except JWTError:
        raise credentials_exception

    if payload.get("type") != TokenType.ACCESS.value:
        raise credentials_exception

    jti = payload.get("jti")
    if jti and await redis.sismember("blacklist:access_tokens", jti):
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception

    return user


async def get_current_active_verified_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account not verified")
    return user


def require_role(*allowed_roles: UserRole):
    async def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _checker


def rate_limit_dependency(scope: str, max_requests: int, window_seconds: int):
    """
    Route-level rate limit dependency factory, keyed by client IP.
    Use for sensitive endpoints (login, register) that need a stricter
    bucket than the global middleware limit.
    """

    async def _dependency(request: Request, redis: Redis = Depends(redis_dependency)) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        forwarded = request.headers.get("x-forwarded-for")
        ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")

        limiter = RedisSlidingWindowRateLimiter(redis)
        result = await limiter.check(scope=scope, identifier=ip, max_requests=max_requests, window_seconds=window_seconds)
        if not result.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many {scope} attempts. Try again in {int(result.retry_after_seconds) + 1}s.",
                headers={"Retry-After": str(int(result.retry_after_seconds) + 1)},
            )

    return _dependency
