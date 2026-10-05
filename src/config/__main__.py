from src.config.base import init_db, engine
from src.nlu_extractor import IntentExtractor
from src.calendar_backend import LocalJSONCalendar, DBCalendarBackend, QuotaEnforcingCalendar, QuotaExceededError
from src.models.user import User
from sqlmodel import Session
from pathlib import Path

from src.services.base import hash_password

# Reset local test storage so quota starts fresh
Path("data/test_quota.json").unlink(missing_ok=True)


init_db()

# Create one real test user directly (bypassing the API, just for this test)
with Session(engine) as session:
    existing = session.get(User, "test-user-1")
    if not existing:
        test_user = User(id="test-user-1", email="quota_test@example.com",
                         hashed_password=hash_password("testpass123"))
        session.add(test_user)
        session.commit()

extractor = IntentExtractor()
calendar = QuotaEnforcingCalendar(
    local_backend=LocalJSONCalendar(storage_path="data/test_quota.json"),
    db_backend=DBCalendarBackend(),
)

intent = extractor.extract("Schedule a meeting with Justin tomorrow at 3pm")

for i in range(5):
    try:
        event = calendar.book_event(
            intent, user_id="test-user-1", save_to_db=(i >= 3))
        print(f"Booking {i+1}: stored in {event['storage']}")
    except QuotaExceededError as e:
        print(f"Booking {i+1}: BLOCKED - {e}")
