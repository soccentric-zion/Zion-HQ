from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str | None = None):
    settings = get_settings()
    return create_async_engine(database_url or settings.database_url, pool_pre_ping=True)


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = make_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


def configure_for_tests(database_url: str) -> None:
    """Point the module-level engine/session factory at a test database.

    Must be called before any request touches get_db(); tests do this in a
    fixture before the app is exercised.
    """
    global _engine, _session_factory
    _engine = make_engine(database_url)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
