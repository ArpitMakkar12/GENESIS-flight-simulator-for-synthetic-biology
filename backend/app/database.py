from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# pool_pre_ping: test a pooled connection before using it. A hosted database
# that sleeps when idle (Neon, after 5 min) closes every open connection, and
# without the check the first request after a pause would fail.
# pool_recycle: replace connections older than 5 min for the same reason.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
)

# One shared engine for the synchronous code (regulator rules, gene lists).
# Creating an engine per request opened a new connection every time, and
# online every new connection costs an encrypted handshake with the database.
sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    pool_size=2,
    max_overflow=3,
    pool_pre_ping=True,
    pool_recycle=300,
)



async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


async def get_db() -> AsyncSession:
    """Dependency that provides an async database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
