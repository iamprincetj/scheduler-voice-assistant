from abc import ABC, abstractmethod
import json
import uuid
from typing import List, Optional
from pathlib import Path
from datetime import datetime

from sqlmodel import Session, select

from src.models.base import SchedulingIntent, Event
from src.models.event_db import EventDB
from src.config.base import engine

DEFAULT_USER_ID = "local-default-user"
LOCAL_QUOTA = 3


class QuotaExceededError(Exception):
    """Raised when a user has hit their free local storage limit and
    hasn't opted into DB storage for this particular booking."""
    pass


class CalendarBackend(ABC):

    def __init__(self, storage_path: str = "unused"):
        self.storage_path = Path(storage_path)

    @abstractmethod
    def book_event(self, intent: SchedulingIntent, user_id: str = DEFAULT_USER_ID) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_all_events(self, user_id: Optional[str] = None) -> List[dict]:
        raise NotImplementedError

    @abstractmethod
    def mark_reminded(self, event_id: str) -> None:
        raise NotImplementedError


class LocalJSONCalendar(CalendarBackend):
    """
    MVP calendar backend: stores booked events in a local JSON file,
    scoped per user_id. Used for each user's first LOCAL_QUOTA events
    before QuotaEnforcingCalendar requires DB storage instead.
    """

    def __init__(self, storage_path: str = "data/events.json"):
        super().__init__(storage_path=storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.touch(exist_ok=True)

        if self.storage_path.stat().st_size == 0:
            self.storage_path.write_text(json.dumps([]))

    def book_event(self, intent: SchedulingIntent, user_id: str = DEFAULT_USER_ID) -> dict:
        event = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "person": intent.person,
            "when": intent.parsed_datetime,
            "raw_transcript": intent.raw_text,
            "booked_at": datetime.now().isoformat(),
            "reminded": False,
        }

        events = json.loads(self.storage_path.read_text())
        events.append(event)
        self.storage_path.write_text(json.dumps(events, indent=2))

        return event

    def get_all_events(self, user_id: Optional[str] = None) -> List[dict]:
        events = json.loads(self.storage_path.read_text())
        if user_id is None:
            return events
        return [e for e in events if e.get("user_id") == user_id]

    def mark_reminded(self, event_id: str) -> None:
        events = json.loads(self.storage_path.read_text())
        for event in events:
            if event["id"] == event_id:
                event["reminded"] = True
        self.storage_path.write_text(json.dumps(events, indent=2))


class DBCalendarBackend(CalendarBackend):
    """
    Postgres-backed calendar storage. Used once a user exceeds their free
    local quota (or explicitly opts into DB storage). Same interface as
    LocalJSONCalendar -- callers can't tell the difference.
    """

    def __init__(self):
        super().__init__()  # no file storage involved, base default is unused here

    def book_event(self, intent: SchedulingIntent, user_id: str = DEFAULT_USER_ID) -> dict:
        db_event = EventDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            person=intent.person,
            when=intent.parsed_datetime,
            raw_transcript=intent.raw_text,
        )
        with Session(engine) as session:
            session.add(db_event)
            session.commit()
            session.refresh(db_event)
            return db_event.model_dump()

    def get_all_events(self, user_id: Optional[str] = None) -> List[dict]:
        with Session(engine) as session:
            statement = select(EventDB)
            if user_id is not None:
                statement = statement.where(EventDB.user_id == user_id)
            results = session.exec(statement).all()
            return [e.model_dump() for e in results]

    def mark_reminded(self, event_id: str) -> None:
        with Session(engine) as session:
            event = session.get(EventDB, event_id)
            if event:
                event.reminded = True
                session.add(event)
                session.commit()


class QuotaEnforcingCalendar(CalendarBackend):
    """
    Decorator: routes bookings to LocalJSONCalendar for a user's first
    LOCAL_QUOTA events (free, no DB dependency), then requires the caller
    to explicitly opt into DB storage for anything beyond that. Neither
    the pipeline nor the API needs to know this rule exists internally --
    they just call book_event() as usual.
    """

    def __init__(self, local_backend: CalendarBackend, db_backend: CalendarBackend, quota: int = LOCAL_QUOTA):
        super().__init__()
        self.local_backend = local_backend
        self.db_backend = db_backend
        self.quota = quota

    def book_event(self, intent: SchedulingIntent, user_id: str = DEFAULT_USER_ID, save_to_db: bool = False) -> dict:
        local_count = len(self.local_backend.get_all_events(user_id))

        if local_count < self.quota:
            event = self.local_backend.book_event(intent, user_id)
            event["storage"] = "local"
            return event

        if not save_to_db:
            raise QuotaExceededError(
                f"You've reached your free local storage limit of {self.quota} events. "
                "Set save_to_db=True to continue saving this and future events to the database."
            )

        event = self.db_backend.book_event(intent, user_id)
        event["storage"] = "database"
        return event

    def get_all_events(self, user_id: Optional[str] = None) -> List[dict]:
        return self.local_backend.get_all_events(user_id) + self.db_backend.get_all_events(user_id)

    def mark_reminded(self, event_id: str) -> None:
        self.local_backend.mark_reminded(event_id)
        self.db_backend.mark_reminded(event_id)
