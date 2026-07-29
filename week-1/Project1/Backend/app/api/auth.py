from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
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
async def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)

    # IMPORTANT: await because AuthService.login() is async
    token = await auth_service.login(payload)

    return ApiResponse(
        success=True,
        message="Login successful.",
        data=TokenResponse(**token),
    )


@router.post(
    "/refresh",
    response_model=ApiResponse[TokenResponse],
)
async def refresh(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)

    tokens = await auth_service.refresh(
        payload.refresh_token
    )

    return ApiResponse(
        success=True,
        message="Token refreshed successfully.",
        data=TokenResponse(**tokens),
    )


@router.post("/logout")
async def logout(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)

    await auth_service.logout(
        payload.refresh_token
    )

    return ApiResponse(
        success=True,
        message="Logged out successfully.",
        data=None,
    )