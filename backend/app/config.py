from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://biosandbox:biosandbox@localhost:5432/biosandbox"
    DATABASE_URL_SYNC: str = "postgresql://biosandbox:biosandbox@localhost:5432/biosandbox"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # App
    SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = True
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # AI Model paths
    MODEL_DIR: str = "./data/models"
    HYENADNA_MODEL_PATH: Optional[str] = None
    EXPRESSION_MODEL_PATH: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
