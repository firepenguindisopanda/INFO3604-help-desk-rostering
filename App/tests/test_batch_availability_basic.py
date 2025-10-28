import unittest
import importlib.util
from pathlib import Path


# Load the controller module by file path to avoid importing top-level App package
ROOT = Path(__file__).resolve().parents[1]
controllers_path = ROOT / 'controllers' / 'schedule.py'
spec = importlib.util.spec_from_file_location('controllers_schedule', controllers_path)
controllers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controllers)


class BatchAvailabilitySmokeTest(unittest.TestCase):
    def test_batch_function_exists_and_handles_input(self):
        # Call with a simple slot query and assert we get a structured response (success or handled error)
        try:
            result, status = controllers.batch_list_available_staff_for_slots('helpdesk', [{'date': '2020-01-01', 'hour': 9}])
        except Exception as e:
            self.fail(f"batch_list_available_staff_for_slots raised unexpectedly: {e}")

        self.assertIsInstance(result, dict)
        self.assertIn(status, (200, 500))


if __name__ == '__main__':
    unittest.main()
