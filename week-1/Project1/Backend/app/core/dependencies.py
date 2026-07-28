from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.security import decode_access_token
from app.db.database import SessionLocal
from app.repositories.user import UserRepository

security = HTTPBearer()


def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    try:
        payload = decode_access_token(credentials.credentials)
    except Exception:
        raise AppException(
            status_code=401,
            message="Invalid token.",
            error_code="INVALID_TOKEN",
        )

    user = UserRepository(db).get_by_id(int(payload["sub"]))

    if not user:
        raise AppException(
            status_code=401,
            message="User not found.",
            error_code="USER_NOT_FOUND",
        )

    return user