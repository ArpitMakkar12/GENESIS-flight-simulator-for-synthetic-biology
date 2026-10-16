"""Settings: one hosted-database address must become two correct driver URLs.

A wrong translation would only show up after deploying (the app cannot
reach its database), so it is checked here instead.
"""

from app.config import Settings, split_database_url

NEON = "postgresql://user:secret@ep-cool-1.ap-southeast-1.aws.neon.tech/genesis?sslmode=require&channel_binding=require"


def test_async_url_uses_asyncpg_spelling_of_ssl():
    async_url, _ = split_database_url(NEON)
    assert async_url.startswith("postgresql+asyncpg://user:secret@ep-cool-1")
    assert async_url.endswith("/genesis?ssl=require")   # asyncpg rejects sslmode and channel_binding


def test_sync_url_keeps_the_address_as_given():
    _, sync_url = split_database_url(NEON)
    assert sync_url == NEON                               # psycopg2 understands both parameters


def test_postgres_scheme_and_no_ssl():
    async_url, sync_url = split_database_url("postgres://u:p@localhost:5432/db")
    assert async_url == "postgresql+asyncpg://u:p@localhost:5432/db"
    assert sync_url == "postgresql://u:p@localhost:5432/db"


def test_plain_database_url_sets_both(monkeypatch):
    monkeypatch.setenv("DATABASE_URL_SYNC", "placeholder")   # restored after the test
    s = Settings(DATABASE_URL=NEON)
    assert s.DATABASE_URL.startswith("postgresql+asyncpg://")
    assert s.DATABASE_URL_SYNC == NEON


def test_explicit_urls_are_left_alone():
    local = "postgresql+asyncpg://biosandbox:biosandbox@db:5432/biosandbox"
    s = Settings(DATABASE_URL=local, DATABASE_URL_SYNC="postgresql://biosandbox:biosandbox@db:5432/biosandbox")
    assert s.DATABASE_URL == local


def test_allowed_origins_forgive_spaces_and_trailing_slash():
    s = Settings(ALLOWED_ORIGINS="https://genesis.vercel.app/ , http://localhost:3000")
    assert s.allowed_origins == ["https://genesis.vercel.app", "http://localhost:3000"]