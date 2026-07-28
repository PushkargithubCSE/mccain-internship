from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.security import create_access_token, verify_password
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest


class AuthService:

    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)

    def login(self, data: LoginRequest):

        user = self.user_repo.get_by_email(data.email)

        if not user:
            raise AppException(
                status_code=401,
                message="Invalid email or password.",
                error_code="INVALID_CREDENTIALS",
            )

        if not verify_password(data.password, user.hashed_password):
            raise AppException(
                status_code=401,
                message="Invalid email or password.",
                error_code="INVALID_CREDENTIALS",
            )

        token = create_access_token(str(user.id))

        return {
            "access_token": token,
            "token_type": "bearer",
        }