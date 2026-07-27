from fastapi import APIRouter, Depends

from app.core.dependencies import get_db
from app.core.exceptions import AppException
from app.schemas.base import ApiResponse

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


@router.get("/ping",response_model=ApiResponse[None])
async def ping(
    db=Depends(get_db),
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