import time
import unittest
import importlib.util
from pathlib import Path


# Import the schedule view module by file path to avoid importing the top-level
# App package (App.__init__ pulls in many modules and can cause circular
# imports during test collection). This loads the module in isolation.
ROOT = Path(__file__).resolve().parents[1]
schedule_path = ROOT / 'views' / 'schedule.py'
spec = importlib.util.spec_from_file_location('app_views_schedule', schedule_path)
schedule_view = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schedule_view)


class AvailabilityCacheTests(unittest.TestCase):
    def test_cache_set_and_get(self):
        schedule_type = 'helpdesk'
        staff_id = 'test_staff'
        day = 'monday'
        time_slot = '9:00 am'
        value = {'status': 'success', 'is_available': True}

        # Ensure cache empty for key
        schedule_view._availability_cache.clear()

        self.assertIsNone(schedule_view._get_cached_availability(schedule_type, staff_id, day, time_slot))

        # Set and retrieve
        schedule_view._set_cached_availability(schedule_type, staff_id, day, time_slot, value)
        cached = schedule_view._get_cached_availability(schedule_type, staff_id, day, time_slot)
        self.assertIsNotNone(cached)
        self.assertEqual(cached, value)

    def test_cache_expiry(self):
        schedule_type = 'helpdesk'
        staff_id = 'test_staff_2'
        day = 'tuesday'
        time_slot = '10:00 am'
        value = {'status': 'success', 'is_available': False}

        # Use a very small TTL for this test
        original_ttl = schedule_view._AVAILABILITY_CACHE_TTL
        schedule_view._AVAILABILITY_CACHE_TTL = 0.01
        try:
            schedule_view._availability_cache.clear()
            schedule_view._set_cached_availability(schedule_type, staff_id, day, time_slot, value)
            # Immediately available
            self.assertIsNotNone(schedule_view._get_cached_availability(schedule_type, staff_id, day, time_slot))
            # Wait long enough for expiry
            time.sleep(0.02)
            self.assertIsNone(schedule_view._get_cached_availability(schedule_type, staff_id, day, time_slot))
        finally:
            schedule_view._AVAILABILITY_CACHE_TTL = original_ttl


if __name__ == '__main__':
    unittest.main()
