from dataclasses import dataclass, field
from typing import Optional



@dataclass(frozen=True)
class Event:
    id: str
    person: Optional[str]
    when: Optional[str]
    raw_transcript: str
    booked_at: str
    reminded: bool = False