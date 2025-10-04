import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Force reload environment variables from .env
load_dotenv(override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, env_ignore_empty=True
    )

    # Application
    APP_NAME: str = "Admin API Backend"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str | None = os.getenv("REDIS_PASSWORD", None)
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes default

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000


settings = Settings()