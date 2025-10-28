import unittest
from datetime import datetime, date, time as dt_time, timedelta

from flask_jwt_extended import create_access_token

from App.main import create_app
from App.database import db, create_db
from App.controllers.student import create_student
from App.controllers.help_desk_assistant import create_help_desk_assistant
from App.controllers.admin import create_admin
from App.models import Schedule, Shift, Availability


class ScheduleResponseIntegrationTests(unittest.TestCase):
    def setUp(self):
        # Create app and in-memory DB
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'JWT_SECRET_KEY': 'test-secret-key'
        })
        self.app_context = self.app.app_context()
        self.app_context.push()
        create_db()
        self.client = self.app.test_client()

        # Create an admin user with role 'helpdesk' so the view will pick schedule_id=1
        self.admin = create_admin('helpadmin', 'pw', 'helpdesk')

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        if self.app_context is not None:
            self.app_context.pop()

    def test_schedule_includes_available_staff_per_shift(self):
        # Create a student and make them a help desk assistant
        student = create_student('s1', 'pw', 'BSc', 'Student One')
        assistant = create_help_desk_assistant('s1')

        # Create availability for Monday 9:00-17:00 (day_of_week 0)
        avail = Availability(username='s1', day_of_week=0, start_time=dt_time(9, 0), end_time=dt_time(17, 0))
        db.session.add(avail)

        # Create a schedule for a week starting on a Monday
        monday = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        # normalize to nearest Monday (safe for tests)
        days_to_monday = (monday.weekday() - 0) % 7
        monday = monday - timedelta(days=days_to_monday)

        sched = Schedule(start_date=monday, end_date=monday + timedelta(days=4), type='helpdesk')
        db.session.add(sched)
        db.session.commit()

        # Add a shift on the Monday at 9am
        shift_start = datetime.combine(monday.date(), dt_time(9, 0))
        shift_end = datetime.combine(monday.date(), dt_time(10, 0))
        shift = Shift(monday, shift_start, shift_end, sched.id)
        db.session.add(shift)
        db.session.commit()

        # Call the schedule endpoint with admin token
        token = create_access_token(identity=self.admin.username)
        headers = {'Authorization': f'Bearer {token}'}

        resp = self.client.get('/api/schedule/current', headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get('status'), 'success')

        schedule = data.get('schedule')
        self.assertIsNotNone(schedule)
        days = schedule.get('days', [])
        # find first day and first shift
        self.assertGreaterEqual(len(days), 1)
        first_day = days[0]
        shifts = first_day.get('shifts', [])
        self.assertGreaterEqual(len(shifts), 1)
        first_shift = shifts[0]

        # available_staff should be present and include our assistant username
        available = first_shift.get('available_staff', [])
        # normalize to list of usernames
        avail_usernames = [a.get('username') or a.get('id') or a for a in available]
        self.assertIn('s1', avail_usernames)


if __name__ == '__main__':
    unittest.main()
