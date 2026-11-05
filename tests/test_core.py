import unittest
import os
from datetime import datetime, time
import pytz

from src.services.parser import parse_task_input
from src.config import Settings, settings
from src.database.db import init_db, get_db_connection
from src.database.models import (
    upsert_user,
    create_task,
    set_task_priority,
    get_task_by_id,
    get_pending_tasks_for_user,
    get_tasks_needing_priority,
    mark_task_completed,
    mark_task_dropped,
    clear_user_tasks
)
from src.services.scheduler import calculate_next_reminder_time

class TestParser(unittest.TestCase):
    def test_newline_separated(self):
        text = "Task 1\nTask 2\nTask 3"
        self.assertEqual(parse_task_input(text), ["Task 1", "Task 2", "Task 3"])

    def test_comma_separated(self):
        text = "Write code, Review PR, Send email"
        self.assertEqual(parse_task_input(text), ["Write code", "Review PR", "Send email"])

    def test_bullets_and_numbers(self):
        text = "1. First item\n2) Second item\n- Third item\n* Fourth item\n• Fifth item"
        self.assertEqual(
            parse_task_input(text),
            ["First item", "Second item", "Third item", "Fourth item", "Fifth item"]
        )

    def test_empty_input(self):
        self.assertEqual(parse_task_input(""), [])
        self.assertEqual(parse_task_input("   \n\n  "), [])

    def test_mixed_commas_and_whitespace(self):
        text = "  Task A,  , Task B , , Task C  "
        self.assertEqual(parse_task_input(text), ["Task A", "Task B", "Task C"])

class TestConfigAndQuietHours(unittest.TestCase):
    def test_quiet_hours_over_midnight(self):
        cfg = Settings(
            bot_token="dummy",
            quiet_hours_start="00:00",
            quiet_hours_end="07:00",
            timezone="UTC"
        )
        utc = pytz.UTC
        # Inside quiet hours (03:00)
        dt_quiet = datetime(2026, 1, 1, 3, 0, 0, tzinfo=utc)
        self.assertTrue(cfg.is_in_quiet_hours(dt_quiet))

        # Outside quiet hours (14:00)
        dt_active = datetime(2026, 1, 1, 14, 0, 0, tzinfo=utc)
        self.assertFalse(cfg.is_in_quiet_hours(dt_active))

        # Exactly at start (00:00) -> inside
        dt_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=utc)
        self.assertTrue(cfg.is_in_quiet_hours(dt_start))

        # Exactly at end (07:00) -> outside
        dt_end = datetime(2026, 1, 1, 7, 0, 0, tzinfo=utc)
        self.assertFalse(cfg.is_in_quiet_hours(dt_end))

    def test_calculate_next_reminder_quiet_hour_adjustment(self):
        # 11:45 PM (23:45) with 45 min interval -> 00:30 AM (in quiet hours 00:00 - 07:00)
        # Should be pushed to 07:00 AM!
        utc = pytz.UTC
        from_dt = datetime(2026, 1, 1, 23, 45, 0, tzinfo=utc)
        settings.quiet_hours_start = "00:00"
        settings.quiet_hours_end = "07:00"
        next_dt = calculate_next_reminder_time(interval_minutes=45, from_time=from_dt)
        self.assertEqual(next_dt.hour, 7)
        self.assertEqual(next_dt.minute, 0)

class TestDatabase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Use a test DB
        settings.db_path = "data/test_relentless.db"
        await init_db()

    async def asyncTearDown(self):
        test_db = "data/test_relentless.db"
        if os.path.exists(test_db):
            try:
                os.remove(test_db)
            except Exception:
                pass

    async def test_user_and_task_lifecycle(self):
        # 1. Upsert user
        await upsert_user(user_id=12345, chat_id=12345, username="tester", first_name="Test")
        
        # 2. Create tasks
        t1_id = await create_task(user_id=12345, chat_id=12345, title="Write unit tests")
        t2_id = await create_task(user_id=12345, chat_id=12345, title="Review code")

        # 3. Check tasks needing priority
        needing = await get_tasks_needing_priority(12345)
        self.assertEqual(len(needing), 2)
        self.assertEqual(needing[0]["id"], t1_id)

        # 4. Set priority
        await set_task_priority(t1_id, "high", datetime.now().isoformat())
        await set_task_priority(t2_id, "low", datetime.now().isoformat())

        needing_after = await get_tasks_needing_priority(12345)
        self.assertEqual(len(needing_after), 0)

        # 5. List pending tasks
        pending = await get_pending_tasks_for_user(12345)
        self.assertEqual(len(pending), 2)
        self.assertEqual(pending[0]["priority"], "high")  # Ordered high first

        # 6. Complete task
        await mark_task_completed(t1_id)
        pending_after_complete = await get_pending_tasks_for_user(12345)
        self.assertEqual(len(pending_after_complete), 1)
        self.assertEqual(pending_after_complete[0]["id"], t2_id)

        # 7. Drop remaining task
        await mark_task_dropped(t2_id)
        pending_final = await get_pending_tasks_for_user(12345)
        self.assertEqual(len(pending_final), 0)

        # 8. Clear user tasks
        await clear_user_tasks(12345)

if __name__ == "__main__":
    unittest.main()
