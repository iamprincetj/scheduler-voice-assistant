from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List,Tuple
import re
from dateparser.search import search_dates

@dataclass
class SchedulingIntent:
    raw_text: str
    action: str
    person: Optional[str]
    datetime_text: Optional[str]
    parsed_datetime: Optional[str]
    ambiguous: bool = False
    all_date_candidates: List[Tuple[str, str]] = field(default_factory=list)



class IntentExtractor:
    """
    Rule-based extractor: transcript -> structured scheduling intent.
    """

    PERSON_PATTERN = re.compile(r"with ([A-Z][a-zA-Z]+)")
    TIME_HINT_PATTERN = re.compile(r"\d{1,2}(:\d{2})?\s*(am|pm)|o'?clock", re.IGNORECASE)

    def extract(self, transcript: str) -> SchedulingIntent:
        action = "schedule" if "schedule" in transcript.lower() else "unknown"

        person_match = self.PERSON_PATTERN.search(transcript)
        person = person_match.group(1) if person_match else None

        matches = search_dates(transcript, settings={"PREFER_DATES_FROM": "future"}) or []

        candidates = [(text, dt.isoformat()) for text, dt in matches]

        chosen_text, chosen_iso = self._resolve_best_matches(matches)

        ambiguous = len({c[1] for c in candidates}) > 1

        return SchedulingIntent(
            raw_text=transcript,
            action=action,
            person=person,
            datetime_text=chosen_text,
            parsed_datetime=chosen_iso,
            ambiguous=ambiguous,
            all_date_candidates=candidates
        )


    def _resolve_best_matches(self, matches):
        """
        Decouples date from time so corrections that only restate one of
        them (e.g. 'no I meant tomorrow') still merge correctly with the
        most recently stated value of the other.
        """

        if not matches:
            return None, None

        with_time = [m for m in matches if self.TIME_HINT_PATTERN.search(m[0])]

        # Date comes from the LAST date/time phrase mentioned, period.

        date_text, date_dt = matches[-1]
        date_component = date_dt.date()


        # Time comes from the last phrase that explicitly stated a clock time

        if with_time:
            time_text, time_dt = with_time[-1]
            combined = datetime.combine(date_component,time_dt.time()).isoformat()
            chosen_text = f"{date_text} / {time_text}"

        else:
            combined = date_dt
            chosen_text = date_text

        return chosen_text, combined