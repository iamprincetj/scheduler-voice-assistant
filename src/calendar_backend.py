from abc import ABC, abstractmethod
import json
from pathlib import Path
from datetime import datetime

from .nlu_extractor import SchedulingIntent



class CalendarBackend(ABC):
    @abstractmethod
    def book_event(self, intent: SchedulingIntent) -> dict:
        raise NotImplementedError



class LocalJSONCalendar(CalendarBackend):
    """
    MVP calendar backend: stores booked events in a local JSOn file.
    """

    def __init__(self, storage_path: str= "data/events.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(exist_ok=True)
        self.storage_path.touch(exist_ok=True)

        if self.storage_path.stat().st_size == 0:
            self.storage_path.write_text(json.dumps([]))


    def book_event(self, intent: SchedulingIntent) -> dict:
        event = {
            "person": intent.person,
            "when": intent.parsed_datetime,
            "raw_transcript": intent.raw_text,
            "booked_at": datetime.now().isoformat()
        }

        events = json.loads(self.storage_path.read_text())
        events.append(event)
        self.storage_path.write_text(json.dumps(events, indent=2))


        return event
        