from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Tuple
import re
from dateparser.search import search_dates

from src.models.scheduling_intent import SchedulingIntent


class IntentExtractor:
    """
    Rule-based extractor: transcript -> structured scheduling intent.
    """

    PERSON_PATTERN = re.compile(r"with ([A-Z][a-zA-Z]+)")
    TIME_HINT_PATTERN = re.compile(
        r"\b\d{1,2}(?:[:.]\d{2})?\s*(?:am|pm)\b|o'?clock",
        re.IGNORECASE,
    )

    # Whisper may produce:
    #   6.10 pm
    #   6-10 pm
    # for spoken "6:10 pm".
    TIME_PERIOD_PATTERN = re.compile(
        r"\b(\d{1,2})[.-](\d{2})(\s*(?:am|pm))\b",
        re.IGNORECASE,
    )

    COMMAND_WORD_PATTERN = re.compile(
        r"\b(?:set|schedule|book|create|make)\b",
        re.IGNORECASE,
    )

    # Whisper may produce compact times: # 530 pm -> 5:30 pm # 544 pm -> 5:44 pm # 1655 -> 16:55 # # We only normalize these when the surrounding context makes # them look like a clock time.
    COMPACT_12H_TIME_PATTERN = re.compile(
        r"\b([1-9])(\d{2})\s*(am|pm)\b", re.IGNORECASE, )
    COMPACT_24H_TIME_PATTERN = re.compile(r"\b([01]\d|2[0-3])([0-5]\d)\b")

    def _clean_for_dateparser(self, text: str) -> str:
        return self.COMMAND_WORD_PATTERN.sub("", text)

    def extract(self, transcript: str) -> SchedulingIntent:
        normalized = self._normalize_times(transcript)
        cleaned = self._clean_for_dateparser(normalized)
        action = "schedule" if "schedule" in transcript.lower() else "unknown"

        person_match = self.PERSON_PATTERN.search(transcript)
        person = person_match.group(1) if person_match else "John Doe"

        matches = search_dates(
            cleaned, settings={"PREFER_DATES_FROM": "future"}) or []

        candidates = [(text, dt.isoformat()) for text, dt in matches]

        chosen_text, chosen_dt = self._resolve_best_matches(matches)

        ambiguous = len({c[1] for c in candidates}) > 1

        return SchedulingIntent(
            raw_text=transcript,
            action=action,
            person=person,
            datetime_text=chosen_text,
            parsed_datetime=(chosen_dt.isoformat() if chosen_dt else None),
            ambiguous=ambiguous,
            all_date_candidates=candidates
        )

    def _normalize_times(self, text: str) -> str:
        """
        Normalize common Whisper representations of clock times. Examples: 6.10 pm -> 6:10 pm 6-10 pm -> 6:10 pm 530 pm -> 5:30 pm 544 pm -> 5:44 pm 1655 -> 16:55
        """

        # 5.30 pm / 5-30 pm -> 5:30 pm

        text = self.TIME_PERIOD_PATTERN.sub(
            r"\1:\2\3",
            text,
        )

        # 530 pm / 544 pm -> 5:30 pm / 5:44 pm
        text = self.COMPACT_12H_TIME_PATTERN.sub(
            r"\1:\2 \3",
            text,
        )

        # This is intentionally done last. # It only accepts valid 24-hour hour/minute combinations.
        text = self.COMPACT_24H_TIME_PATTERN.sub(
            r"\1:\2",
            text,
        )

        return text

    def _resolve_best_matches(self, matches):
        """
        Decouples date from time so corrections that only restate one of
        them (e.g. 'no I meant tomorrow') still merge correctly with the
        most recently stated value of the other.
        """

        if not matches:
            return None, None

        with_time = [
            m
            for m in matches
            if self.TIME_HINT_PATTERN.search(m[0])
        ]

        # Date comes from the LAST date/time phrase mentioned, period.

        date_text, date_dt = matches[-1]
        date_component = date_dt.date()

        # Time comes from the last phrase that explicitly stated a clock time

        if with_time:
            time_text, time_dt = with_time[-1]

            combined = datetime.combine(
                date_component,
                time_dt.time(),
            )

            chosen_text = f"{date_text} / {time_text}"

        else:
            combined = date_dt
            chosen_text = date_text

        return chosen_text, combined
