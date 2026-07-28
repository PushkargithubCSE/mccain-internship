from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.base import ApiResponse
from app.services.auth import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)

    token = auth_service.login(payload)

    return ApiResponse(
        success=True,
        message="Login successful.",
        data=TokenResponse(**token),
    )