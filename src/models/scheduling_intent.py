from dataclasses import dataclass, field
from typing import Optional, Tuple, List


@dataclass
class SchedulingIntent:
    raw_text: str
    action: str
    person: Optional[str]
    datetime_text: Optional[str]
    parsed_datetime: Optional[str]
    ambiguous: bool = False
    all_date_candidates: List[Tuple[str, str]] = field(default_factory=list)
