import os
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings


def split_database_url(url: str) -> tuple[str, str]:
    """One plain Postgres address -> (async URL for asyncpg, sync URL for psycopg2).

    The two database drivers spell encryption differently:
        psycopg2 (sync)  understands  ?sslmode=require   (and channel_binding)
        asyncpg  (async) understands  ?ssl=require        (and nothing else)
    So a hosted database's address, e.g. Neon's
        postgresql://user:pass@ep-x.aws.neon.tech/genesis?sslmode=require&channel_binding=require
    is kept as-is for psycopg2 and translated for asyncpg.
    """
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))

    sync_url = urlunsplit(parts._replace(scheme="postgresql"))

    async_query = {k: v for k, v in query.items() if k not in ("sslmode", "channel_binding")}
    if query.get("sslmode", "disable") != "disable":
        async_query["ssl"] = query["sslmode"]
    async_url = urlunsplit(parts._replace(scheme="postgresql+asyncpg", query=urlencode(async_query)))

    return async_url, sync_url


def is_plain_postgres_url(url: str) -> bool:
    """True for postgresql://... or postgres://..., False when a driver is named (+asyncpg)."""
    return url.split("://", 1)[0] in ("postgres", "postgresql")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database. Locally (Docker) both are set explicitly. Online, set only
    # DATABASE_URL to the plain address your database host gives you
    # (postgresql://...); both URLs are then derived from it, see below.
    DATABASE_URL: str = "postgresql+asyncpg://biosandbox:biosandbox@localhost:5432/biosandbox"
    DATABASE_URL_SYNC: str = "postgresql://biosandbox:biosandbox@localhost:5432/biosandbox"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # App
    SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = True
    ALLOWED_ORIGINS: str = "http://localhost:3000"   # comma-separated

    # AI Model paths
    MODEL_DIR: str = "./data/models"
    HYENADNA_MODEL_PATH: Optional[str] = None
    EXPRESSION_MODEL_PATH: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True

    @model_validator(mode="after")
    def _one_database_url_is_enough(self) -> "Settings":
        """A plain postgresql:// DATABASE_URL (no +asyncpg) is the only database setting."""
        if is_plain_postgres_url(self.DATABASE_URL):
            self.DATABASE_URL, self.DATABASE_URL_SYNC = split_database_url(self.DATABASE_URL)
            # The AI layer and Alembic read the sync address from the environment
            os.environ["DATABASE_URL_SYNC"] = self.DATABASE_URL_SYNC
        return self

    @property
    def allowed_origins(self) -> list[str]:
        """ALLOWED_ORIGINS as a list; spaces and a trailing / are forgiven."""
        return [o.strip().rstrip("/") for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()