"""
Password hashing + JWT issuing/verification.

Token design:
  - Access token: short-lived (15 min default), carries `sub` (user id),
    `role`, `type=access`. Stateless — verified purely via signature + exp.
  - Refresh token: longer-lived (7 days default), carries `type=refresh`
    and a unique `jti`. The `jti` is persisted in Postgres (RefreshToken
    table) so it can be revoked/rotated. Every refresh issues a *new*
    refresh token and revokes the old one (rotation) to limit replay risk.
"""
import uuid
from datetime import datetime, timedelta, timezone
from enum import StrEnum

import bcrypt
from jose import JWTError, jwt

from app.config import settings


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


# NOTE: we use the `bcrypt` package directly rather than passlib's CryptContext.
# passlib 1.7.4 (latest PyPI release) probes `bcrypt.__about__.__version__` to
# detect the backend version, which was removed in bcrypt>=4.1 — this raises
# at runtime on any current bcrypt install. Calling bcrypt directly sidesteps
# that dead dependency entirely.
_BCRYPT_MAX_BYTES = 72  # bcrypt silently ignores bytes beyond this


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))
    except ValueError:
        return False


def _create_token(subject: str, token_type: TokenType, expires_delta: timedelta, extra_claims: dict | None = None) -> tuple[str, str]:
    """Returns (encoded_jwt, jti)."""
    now = datetime.now(timezone.utc)
    jti = uuid.uuid4().hex
    payload = {
        "sub": subject,
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
        "iss": settings.JWT_ISSUER,
        "jti": jti,
    }
    if extra_claims:
        payload.update(extra_claims)
    encoded = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded, jti


def create_access_token(user_id: str, role: str) -> str:
    token, _ = _create_token(
        subject=user_id,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims={"role": role},
    )
    return token


def create_refresh_token(user_id: str) -> tuple[str, str, datetime]:
    """Returns (token, jti, expires_at)."""
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    token, jti = _create_token(subject=user_id, token_type=TokenType.REFRESH, expires_delta=expires_delta)
    expires_at = datetime.now(timezone.utc) + expires_delta
    return token, jti, expires_at


def decode_token(token: str) -> dict:
    """Raises jose.JWTError on invalid/expired token."""
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        issuer=settings.JWT_ISSUER,
    )


def access_token_expires_in_seconds() -> int:
    return settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "access_token_expires_in_seconds",
    "TokenType",
    "JWTError",
]
