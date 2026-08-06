from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    field_validator,
)


class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def validate_mccain_email(cls, value: EmailStr):
        email = str(value).lower()

        if not email.endswith("@mccain.com"):
            raise ValueError(
                "Only @mccain.com email addresses are allowed."
            )

        return value


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    is_active: bool

    model_config = ConfigDict(from_attributes=True)