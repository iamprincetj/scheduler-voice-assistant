"""
Database engine and session management.

Uses SQLModel (Pydantic + SQLAlchemy combined) so our DB tables
doubles as validated data models - matching the project's existing convention of keeping domain objects in models/.
"""

from sqlmodel import SQLModel, create_engine, Session
from src.config.base import DATABASE_URL


if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. check your .env file")

engine = create_engine(DATABASE_URL, echo=False)


def init_db() -> None:
    """
    Creates all tables that don't exists yet. Safe to call on every startup.
    """

    SQLModel.metadata.create_all(engine)


def get_session():
    """
    FastAPI dependency: yields a DB session, closes it after the request.
    """
    with Session(engine) as session:
        yield session
