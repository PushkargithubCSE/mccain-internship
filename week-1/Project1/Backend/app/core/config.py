from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ==========================
    # Application
    # ==========================
    APP_NAME: str = "AI Customer Support Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ==========================
    # API
    # ==========================
    API_V1_PREFIX: str = "/api/v1"
    
    DATABASE_URL: str
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()