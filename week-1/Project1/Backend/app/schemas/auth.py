from pydantic import BaseModel, EmailStr, field_validator


class LoginRequest(BaseModel):
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


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"