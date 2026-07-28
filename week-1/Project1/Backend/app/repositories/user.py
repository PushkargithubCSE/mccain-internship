from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):

    def __init__(self, db: Session):
        super().__init__(db)

    def get_by_id(self, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id)

        return self.db.scalar(stmt)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)

        return self.db.scalar(stmt)

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def list_all(self) -> list[User]:
        stmt = select(User)

        return list(self.db.scalars(stmt).all())

    def delete(self, user: User) -> None:
        self.db.delete(user)
        self.db.commit()