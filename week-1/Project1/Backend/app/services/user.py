from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserRegister
from app.core.exceptions import AppException

from app.core.security import hash_password

class UserService:

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def register_user(self, data: UserRegister) -> User:

        existing_user = self.user_repo.get_by_email(data.email)

        if existing_user:
            raise AppException(
                status_code=400,
                message="Email already registered.",
                error_code="EMAIL_ALREADY_EXISTS",
            )

        user = User(
            full_name=data.full_name,
            email=data.email,
            hashed_password=hash_password(data.password)        
            )

        self.user_repo.create(user)

        self.db.commit()
        self.db.refresh(user)

        return user

    def get_user(self, user_id: int):
        return self.user_repo.get_by_id(user_id)

    def list_users(self):
        return self.user_repo.list_all()