from datetime import datetime

from src.services.calendar_service import create_calendar_event

event = create_calendar_event(
    person="Daniel",
    start_time=datetime(2026, 10, 11, 21, 30).isoformat()
)

print("Event created!")
print("Event ID:", event["id"])
print("Event link:", event.get("htmlLink"))
