from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "McCain Smart Distribution"
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
   

@lru_cache
def get_settings():
    return Settings()


settings = get_settings()   