import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut], dependencies=[Depends(require_role(UserRole.ADMIN))])
async def list_users(db: AsyncSession = Depends(get_db), skip: int = 0, limit: int = 50):
    result = await db.execute(select(User).offset(skip).limit(min(limit, 200)))
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserOut, dependencies=[Depends(require_role(UserRole.ADMIN))])
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}/deactivate", response_model=UserOut, dependencies=[Depends(require_role(UserRole.ADMIN))])
async def deactivate_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return user
