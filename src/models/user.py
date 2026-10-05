from datetime import datetime, timezone
import uuid

from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(
        default_factory=lambda: str(
            uuid.uuid4()),
        primary_key=True
    )
    email: str = Field(
        index=True,
        unique=True,
        nullable=False
    )
    hashed_password: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
