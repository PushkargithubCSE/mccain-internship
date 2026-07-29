from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.core.exceptions import AppException
from app.models.user import User
from app.schemas.base import ApiResponse
from app.services.rate_limiter import rate_limiter


router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


@router.get(
    "/ping",
    response_model=ApiResponse[None],
)
async def ping(
    db: Session = Depends(get_db),
):
    return ApiResponse(
        success=True,
        message="Dependency Injection Working",
        data=None,
    )


@router.get("/error")
async def error():
    raise AppException(
        status_code=400,
        message="Invalid Request",
        error_code="INVALID_REQUEST",
    )


@router.get(
    "/test-rate-limit",
    response_model=ApiResponse[None],
)
async def test_rate_limit(
    current_user: User = Depends(get_current_user),
):
    key = f"rate_limit:user:{current_user.id}:chat"

    allowed, count = await rate_limiter.is_allowed(
        key=key,
        limit=20,
        window_seconds=60,
    )

    if not allowed:
        raise AppException(
            status_code=429,
            message="Too many requests. Try again later.",
            error_code="RATE_LIMIT_EXCEEDED",
        )

    return ApiResponse(
        success=True,
        message=f"Request allowed. Request count: {count}/20",
        data=None,
    )