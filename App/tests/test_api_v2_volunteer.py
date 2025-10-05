import unittest
from datetime import timedelta

from flask_jwt_extended import create_access_token

from App.main import create_app
from App.database import create_db, db
from App.controllers.student import create_student
from App.controllers.help_desk_assistant import create_help_desk_assistant
from App.models.schedule import Schedule
from App.models.shift import Shift
from App.models.allocation import Allocation
from App.models.time_entry import TimeEntry
from App.utils.time_utils import trinidad_now


class VolunteerApiV2Tests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'JWT_SECRET_KEY': 'test-secret-key',
        })
        self.app_context = self.app.app_context()
        self.app_context.push()
        create_db()

        self.client = self.app.test_client()
        self.username = "volunteer1"
        create_student(self.username, "password", "BSc", "Test Volunteer")
        create_help_desk_assistant(self.username)
        self.token = create_access_token(identity=self.username)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        if self.app_context is not None:
            self.app_context.pop()

    def _authorized_get(self, path: str):
        return self.client.get(
            path,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )

    def _authorized_post(self, path: str, json_payload=None):
        return self.client.post(
            path,
            json=json_payload or {},
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )

    def _create_shift_with_allocation(self, include_active_entry=False):
        now = trinidad_now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

        schedule = Schedule(
            id=1,
            start_date=start_of_day,
            end_date=start_of_day + timedelta(days=4),
            type='helpdesk'
        )
        db.session.add(schedule)

        shift_start = now - timedelta(minutes=5)
        shift_end = now + timedelta(minutes=55)
        shift = Shift(
            date=start_of_day,
            start_time=shift_start,
            end_time=shift_end,
            schedule_id=schedule.id
        )
        db.session.add(shift)
        db.session.flush()

        allocation = Allocation(
            username=self.username,
            shift_id=shift.id,
            schedule_id=schedule.id
        )
        db.session.add(allocation)

        if include_active_entry:
            active_entry = TimeEntry(
                username=self.username,
                clock_in=shift_start,
                shift_id=shift.id,
                status='active'
            )
            db.session.add(active_entry)

        db.session.commit()

        if include_active_entry:
            active_entry = TimeEntry.query.filter_by(username=self.username, shift_id=shift.id).first()
        else:
            active_entry = None

        return shift, active_entry

    def test_dashboard_endpoint_returns_default_structure(self):
        response = self._authorized_get('/api/v2/volunteer/dashboard')
        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        self.assertTrue(payload["success"])
        data = payload["data"]

        self.assertIn("student", data)
        self.assertIn("next_shift", data)
        self.assertIn("upcoming_shifts", data)
        self.assertIn("schedule", data)
        self.assertIn("metadata", data)
        self.assertIsNotNone(data["metadata"].get("generated_at"))

    def test_time_tracking_actions_for_active_shift(self):
        self._create_shift_with_allocation(include_active_entry=True)

        response = self._authorized_get('/api/v2/volunteer/time-tracking')
        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        self.assertTrue(payload["success"])
        data = payload["data"]

        actions = data["actions"]
        self.assertFalse(actions["clock_in"]["allowed"])
        self.assertTrue(actions["clock_out"]["allowed"])
        self.assertTrue(data["today_shift"]["starts_now"])
        self.assertEqual(data["today_shift"].get("status"), "active")

    def test_clock_in_creates_active_time_entry(self):
        shift, _ = self._create_shift_with_allocation(include_active_entry=False)

        response = self._authorized_post('/api/v2/volunteer/time-tracking/clock-in')
        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        self.assertTrue(payload["success"])
        data = payload["data"]

        time_entry_info = data["time_entry"]
        self.assertIsNotNone(time_entry_info.get("id"))
        self.assertIn("snapshot", data)

        entry = TimeEntry.query.filter_by(username=self.username, shift_id=shift.id).first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.status, 'active')

    def test_clock_out_transitions_active_entry(self):
        shift, _ = self._create_shift_with_allocation(include_active_entry=False)

        clock_in_response = self._authorized_post('/api/v2/volunteer/time-tracking/clock-in')
        self.assertEqual(clock_in_response.status_code, 200)

        response = self._authorized_post('/api/v2/volunteer/time-tracking/clock-out')
        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        self.assertTrue(payload["success"])
        data = payload["data"]

        time_entry_info = data["time_entry"]
        self.assertIsNotNone(time_entry_info.get("id"))
        self.assertIn("hours_worked", time_entry_info)

        entry = TimeEntry.query.filter_by(username=self.username, shift_id=shift.id).first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.status, 'completed')


if __name__ == '__main__':
    unittest.main()
