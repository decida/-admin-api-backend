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

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000


settings = Settings()