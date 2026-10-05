from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field


class EventDB(SQLModel, table=True):
    """SQL representation of a booked event, used once a user's local
    quota is exceeded. Mirrors the fields in models/event.py's Event
    dataclass, but as an actual database table."""

    __tablename__ = "events"

    id: str = Field(primary_key=True)
    user_id: str = Field(index=True, foreign_key="users.id")
    person: Optional[str] = None
    when: Optional[str] = None
    raw_transcript: str
    booked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    reminded: bool = False
