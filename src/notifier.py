from abc import ABC, abstractmethod
from src.models.base import Event
from src.calendar_service import create_calendar_event

class Notifier(ABC):
    """
    Base Interface for delivering a reminder. Swap ConsoleNotifier for an email, SMS, or push notification implementation later -
    nothing else in the app needs to change.
    """

    @abstractmethod
    def notify(self, event: Event):
        raise NotImplementedError


class ConsoleNotifier(Notifier):
    """
    MVP notifier: prints a reminder to the terminal.
    """

    def notify(self, event: Event) -> None:
        print(f"\n 🔔REMINDER: Meeting with {event.get('person', '')} at {event.get('when')}\n")


class GoogleCalendarNotifier(Notifier):
    """
    Uses Google Calendar to notify the user
    """

    def notify(self, event: Event):
        
        created_event = create_calendar_event(event.person, event.when)
        
        return created_event