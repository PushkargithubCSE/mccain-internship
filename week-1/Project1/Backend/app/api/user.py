from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.base import ApiResponse
from app.schemas.user import UserRegister, UserResponse
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "/register",
    response_model=ApiResponse[UserResponse],
)
def register(
    payload: UserRegister,
    db: Session = Depends(get_db),
):
    service = UserService(db)

    user = service.register_user(payload)

    return ApiResponse(
        success=True,
        message="User registered successfully.",
        data=UserResponse.model_validate(user),
    )