from datetime import datetime, timedelta

from .calendar_backend import CalendarBackend
from .notifier import Notifier, GoogleCalendarNotifier


class ReminderService:
    """
    Scans booked events and notifies for any that are due soon.
    Tracks 'reminded' state per event to avoid duplicate notifications
    """

    def __init__(self, calendar: CalendarBackend, notifier: Notifier, lookahead_minutes: int = 15):
        self.calendar = calendar
        self.notifier = notifier
        self.lookahead_minutes = lookahead_minutes

    def check_and_notify(self):

        now = datetime.now() - timedelta(minutes=3)

        window_end = now + timedelta(minutes=self.lookahead_minutes)

        print(f"{now} -------- {window_end}")

        for event in self.calendar.get_all_events():
            if event.get("reminded"):
                continue

            when_str = event.get('when')

            if not when_str:
                continue

            when_dt = datetime.fromisoformat(when_str)
            if now <= when_dt <= window_end:
                print(self.notifier.notify(event))
                self.calendar.mark_reminded(event['id'])
