from sqlalchemy.orm import Session
from jwt import InvalidTokenError

from app.core.exceptions import AppException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest
from app.services.session_service import session_service

class AuthService:

    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)

    async def login(self, data: LoginRequest):
        email = data.email.lower()

        if not email.endswith("@mccain.com"):
            raise AppException(status_code=403,message="Only McCain employees can access this application.",error_code="INVALID_EMAIL_DOMAIN",)
        user = self.user_repo.get_by_email(data.email)

        if not user or not verify_password(
            data.password,
            user.hashed_password,
        ):
            raise AppException(
                status_code=401,
                message="Invalid email or password.",
                error_code="INVALID_CREDENTIALS",
            )

        access_token = create_access_token(str(user.id))

        refresh_token, token_id = create_refresh_token(
            str(user.id)
        )

        await session_service.create_session(
            user_id=user.id,
            token_id=token_id,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def refresh(self, refresh_token: str):
        try:
            payload = decode_token(refresh_token)
        except InvalidTokenError:
            raise AppException(
                status_code=401,
                message="Invalid refresh token.",
                error_code="INVALID_REFRESH_TOKEN",
            )

        if payload.get("type") != "refresh":
            raise AppException(
                status_code=401,
                message="Invalid token type.",
                error_code="INVALID_TOKEN_TYPE",
            )

        user_id = payload.get("sub")
        old_token_id = payload.get("jti")

        if not user_id or not old_token_id:
            raise AppException(
                status_code=401,
                message="Invalid refresh token.",
                error_code="INVALID_REFRESH_TOKEN",
            )

        session = await session_service.get_session(old_token_id)

        if not session:
            raise AppException(
                status_code=401,
                message="Session expired or revoked.",
                error_code="SESSION_NOT_FOUND",
            )

        # Rotate refresh token:
        # old session becomes unusable
        await session_service.revoke_session(old_token_id)

        access_token = create_access_token(user_id)

        new_refresh_token, new_token_id = create_refresh_token(
            user_id
        )

        await session_service.create_session(
            user_id=int(user_id),
            token_id=new_token_id,
        )

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }

    async def logout(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token)
        except InvalidTokenError:
            raise AppException(
                status_code=401,
                message="Invalid refresh token.",
                error_code="INVALID_REFRESH_TOKEN",
            )

        if payload.get("type") != "refresh":
            raise AppException(
                status_code=401,
                message="Invalid token type.",
                error_code="INVALID_TOKEN_TYPE",
            )

        token_id = payload.get("jti")

        if not token_id:
            raise AppException(
                status_code=401,
                message="Invalid refresh token.",
                error_code="INVALID_REFRESH_TOKEN",
            )

        await session_service.revoke_session(token_id)