from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import settings


password_hash = PasswordHash.recommended()


# =========================================================
# PASSWORD HASHING
# =========================================================

def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return password_hash.verify(
        plain_password,
        hashed_password,
    )


# =========================================================
# ACCESS TOKEN
# =========================================================

def create_access_token(subject: str) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": subject,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


# =========================================================
# REFRESH TOKEN
# =========================================================

def create_refresh_token(
    subject: str,
) -> tuple[str, str]:

    now = datetime.now(timezone.utc)

    token_id = str(uuid4())

    payload = {
        "sub": subject,
        "jti": token_id,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        ),
    }

    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    return token, token_id


# =========================================================
# GENERIC TOKEN DECODER
# =========================================================

def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )


# =========================================================
# ACCESS TOKEN DECODER
# =========================================================

def decode_access_token(token: str) -> dict:

    payload = decode_token(token)

    if payload.get("type") != "access":
        raise jwt.InvalidTokenError(
            "Expected access token."
        )

    return payload