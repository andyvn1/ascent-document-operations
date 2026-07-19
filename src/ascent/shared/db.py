"""Database connection setup.

One engine and session factory for the whole application, built from
Settings rather than a hardcoded connection string, so tests and
different environments (dev/staging/prod) can point at different
databases without changing any application code.
"""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ascent.shared.config import Settings, get_settings


class Base(DeclarativeBase):
    """Base class every ORM model inherits from. Alembic's env.py points
    at Base.metadata to autogenerate migrations from model changes.
    """


def make_engine(settings: Settings | None = None) -> Engine:
    settings = settings or get_settings()
    return create_engine(settings.database_url)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a session, always closed after the
    request, even if a handler raises.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()