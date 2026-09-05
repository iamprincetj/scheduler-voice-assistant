from datetime import datetime

from src.calendar_service import create_calendar_event

event = create_calendar_event(
    person="Daniel",
    start_time=datetime(2026, 9, 4, 19, 0)
)

print("Event created!")
print("Event ID:", event["id"])
print("Event link:", event.get("htmlLink"))