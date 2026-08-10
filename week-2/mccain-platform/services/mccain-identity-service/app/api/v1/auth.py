import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, rate_limit_dependency, redis_dependency
from app.config import settings
from app.core.security import (
    TokenType,
    access_token_expires_in_seconds,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.events.kafka_producer import kafka_producer
from app.models.user import RefreshToken, User
from app.schemas.auth import (
    ChangePasswordRequest,
    LogoutRequest,
    RefreshRequest,
    TokenPair,
    UserLogin,
    UserOut,
    UserRegister,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _issue_token_pair(db: AsyncSession, user: User, request: Request) -> TokenPair:
    access_token = create_access_token(user_id=str(user.id), role=user.role.value)
    refresh_token, jti, expires_at = create_refresh_token(user_id=str(user.id))

    db.add(
        RefreshToken(
            jti=jti,
            user_id=user.id,
            device_info=request.headers.get("user-agent", "unknown")[:255],
            ip_address=_client_ip(request),
            expires_at=expires_at,
        )
    )
    await db.commit()

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=access_token_expires_in_seconds(),
    )


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            rate_limit_dependency(
                "register",
                settings.RATE_LIMIT_REGISTER_MAX_REQUESTS,
                settings.RATE_LIMIT_REGISTER_WINDOW_SECONDS,
            )
        )
    ],
)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        # Deliberately vague to avoid user-enumeration.
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unable to register with provided details")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await kafka_producer.publish("user.registered", {"user_id": str(user.id), "email": user.email})
    logger.info("user_registered", user_id=str(user.id))
    return user


@router.post(
    "/login",
    response_model=TokenPair,
    dependencies=[
        Depends(
            rate_limit_dependency(
                "login",
                settings.RATE_LIMIT_LOGIN_MAX_REQUESTS,
                settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS,
            )
        )
    ],
)
async def login(
    payload: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(redis_dependency),
):
    lockout_key = f"lockout:{payload.email.lower()}"
    failed_attempts = int(await redis.get(lockout_key) or 0)
    if failed_attempts >= settings.ACCOUNT_LOCKOUT_THRESHOLD:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked due to repeated failed login attempts. Try again later.",
        )

    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        await redis.incr(lockout_key)
        await redis.expire(lockout_key, settings.ACCOUNT_LOCKOUT_WINDOW_SECONDS)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    await redis.delete(lockout_key)

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    tokens = await _issue_token_pair(db, user, request)
    await kafka_producer.publish("user.login", {"user_id": str(user.id), "email": user.email})
    logger.info("user_login", user_id=str(user.id))
    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    invalid_exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    try:
        decoded = decode_token(payload.refresh_token)
    except JWTError:
        raise invalid_exc

    if decoded.get("type") != TokenType.REFRESH.value:
        raise invalid_exc

    jti = decoded.get("jti")
    user_id = decoded.get("sub")
    if not jti or not user_id:
        raise invalid_exc

    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    stored = result.scalar_one_or_none()

    if stored is None or stored.revoked or stored.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise invalid_exc

    user_result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise invalid_exc

    # Rotation: revoke the used refresh token, issue a brand new pair.
    stored.revoked = True
    await db.commit()

    tokens = await _issue_token_pair(db, user, request)
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(redis_dependency),
    current_user: User = Depends(get_current_user),
):
    if payload.all_devices:
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.user_id == current_user.id, RefreshToken.revoked.is_(False))
        )
        for token_row in result.scalars().all():
            token_row.revoked = True
        await db.commit()
        return

    try:
        decoded = decode_token(payload.refresh_token)
    except JWTError:
        return  # already invalid, nothing to revoke

    jti = decoded.get("jti")
    if jti:
        result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
        stored = result.scalar_one_or_none()
        if stored and stored.user_id == current_user.id:
            stored.revoked = True
            await db.commit()

    return


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")

    current_user.hashed_password = hash_password(payload.new_password)

    # Revoke all refresh tokens so other sessions are forced to re-auth.
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.user_id == current_user.id, RefreshToken.revoked.is_(False))
    )
    for token_row in result.scalars().all():
        token_row.revoked = True

    await db.commit()
    await kafka_producer.publish("user.password_changed", {"user_id": str(current_user.id)})
    return
