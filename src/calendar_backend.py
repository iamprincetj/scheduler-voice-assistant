from abc import ABC, abstractmethod
import json
from typing import List
import uuid
from pathlib import Path
from datetime import datetime
from src.models.base import SchedulingIntent, Event

class CalendarBackend(ABC):

    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
    
    @abstractmethod
    def book_event(self, intent: SchedulingIntent) -> Event:
        raise NotImplementedError

    @abstractmethod
    def get_all_events(self) -> List[Event]:
        raise NotImplementedError

    @abstractmethod
    def mark_reminded(self, event_id: str) -> None:
        raise NotImplementedError



class LocalJSONCalendar(CalendarBackend):
    """
    MVP calendar backend: stores booked events in a local JSOn file.
    """

    def __init__(self, storage_path: str= "data/events.json"):
        super().__init__(storage_path=storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.touch(exist_ok=True)

        if self.storage_path.stat().st_size == 0:
            self.storage_path.write_text(json.dumps([]))


    def book_event(self, intent: SchedulingIntent) -> Event:
        event = {
            "id": str(uuid.uuid4()),
            "person": intent.person,
            "when": intent.parsed_datetime,
            "raw_transcript": intent.raw_text,
            "booked_at": datetime.now().isoformat(),
            "reminded": False
        }

        events = json.loads(self.storage_path.read_text())
        events.append(event)
        self.storage_path.write_text(json.dumps(events, indent=2))


        return event

    def get_all_events(self) -> List[Event]:
        return json.loads(self.storage_path.read_text())

    def mark_reminded(self, event_id) -> None:
        events = json.loads(self.storage_path.read_text())

        for event in events:
            if event['id'] == event_id:
                event["reminded"] = True
        self.storage_path.write_text(json.dumps(events, indent=2))
        