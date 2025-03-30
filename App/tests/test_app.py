import os, tempfile, pytest, logging, unittest
from unittest.mock import MagicMock, patch
from werkzeug.security import check_password_hash, generate_password_hash
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager, create_access_token
from datetime import datetime, timedelta


from App.main import create_app
from App.database import db, create_db
from App.models import *
from App.controllers import *


LOGGER = logging.getLogger(__name__)

'''
    Integration Tests
'''

# This fixture creates an empty database for the test and deletes it after the test
# scope="class" would execute the fixture once and resued for all methods in the class
@pytest.fixture(autouse=True, scope="module")
def empty_db():
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    with app.app_context():
        create_db()
        yield app.test_client()
        db.drop_all()


def test_authenticate():
    user = create_user("bob", "bobpass", "admin")
    assert login("bob", "bobpass") != None


class UsersIntegrationTests(unittest.TestCase):

    def test_create_user(self):
        user = create_user("rick", "bobpass")
        assert user.username == "rick"

    # def test_get_all_users_json(self):
    #     users_json = get_all_users_json()
    #     self.assertListEqual([{"Username":"bob", "Type":"admin"}, {"Username":"rick", "Type":"student"}], users_json)

    # Tests data changes in the database
    def test_update_user(self):
        update_user("bob", "ronnie")
        user = get_user("ronnie")
        assert user.username == "ronnie"
        
import unittest
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager, create_access_token
from App.controllers.auth import login, setup_jwt, add_auth_context
from App.models import User
from unittest.mock import MagicMock

class AuthIntegrationTests(unittest.TestCase):

    def setUp(self):

        self.app = Flask(__name__)
        self.app.config['JWT_SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        self.jwt = setup_jwt(self.app)

        self.mock_user = MagicMock()
        self.mock_user.username = "testuser"
        self.mock_user.type = "admin"
        self.mock_user.check_password = MagicMock(return_value=True)

    def test_login_success(self):

        User.query = MagicMock()
        User.query.filter_by.return_value.first.return_value = self.mock_user

        with self.app.app_context():
            token, user_type = login("testuser", "password")
            self.assertIsNotNone(token)
            self.assertEqual(user_type, "admin")

    def test_login_failure(self):

        User.query = MagicMock()
        User.query.filter_by.return_value.first.return_value = None

        with self.app.app_context():
            token, user_type = login("wronguser", "wrongpassword")
            self.assertIsNone(token)
            self.assertIsNone(user_type)

class DashboardIntegrationTests(unittest.TestCase):

    def setUp(self):
        # Mock the database session
        self.mock_db_session = patch('App.database.db.session').start()

        # Mock the Student model
        self.mock_student = MagicMock()
        self.mock_student.username = "testuser"
        self.mock_student.name = "Test User"

        # Mock the Shift model
        self.mock_shift = MagicMock()
        self.mock_shift.id = 1
        self.mock_shift.date = datetime(2025, 3, 29)
        self.mock_shift.start_time = datetime(2025, 3, 29, 9, 0, 0)
        self.mock_shift.end_time = datetime(2025, 3, 29, 17, 0, 0)

        # Mock the Allocation model
        self.mock_allocation = MagicMock()
        self.mock_allocation.username = "testuser"
        self.mock_allocation.shift_id = 1

    def tearDown(self):
        patch.stopall()

    def test_get_dashboard_data_success(self):
        Student.query.get = MagicMock(return_value=self.mock_student)

        with patch('App.controllers.dashboard.get_next_shift', return_value={"date": "29 March, 2025", "time": "9:00 AM to 5:00 PM"}):
            with patch('App.controllers.dashboard.get_my_upcoming_shifts', return_value=[{"date": "29 Mar", "time": "9:00 AM to 5:00 PM"}]):
                with patch('App.controllers.schedule.get_current_schedule', return_value={"days": []}):
                    dashboard_data = get_dashboard_data("testuser")

        self.assertIsNotNone(dashboard_data)
        self.assertEqual(dashboard_data['student'].username, "testuser")
        self.assertEqual(dashboard_data['next_shift']['date'], "29 March, 2025")
        self.assertEqual(len(dashboard_data['my_shifts']), 1)

    def test_get_next_shift_active_shift(self):
        self.mock_db_session.query.return_value.join.return_value.filter.return_value.first.return_value = (self.mock_allocation, self.mock_shift)

        now = datetime(2025, 3, 29, 10, 0, 0)
        next_shift = get_next_shift("testuser", now)

        self.assertEqual(next_shift['date'], "29 March, 2025")
        self.assertTrue(next_shift['starts_now'])

    def test_get_next_shift_no_upcoming_shifts(self):
        self.mock_db_session.query.return_value.join.return_value.filter.return_value.first.return_value = None

        now = datetime(2025, 3, 29, 10, 0, 0)
        next_shift = get_next_shift("testuser", now)

        self.assertEqual(next_shift['date'], "No upcoming shifts")
        self.assertFalse(next_shift['starts_now'])

    def test_get_my_upcoming_shifts(self):
        self.mock_db_session.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = [(self.mock_allocation, self.mock_shift)]

        today = datetime(2025, 3, 29)
        my_shifts = get_my_upcoming_shifts("testuser", today)

        self.assertEqual(len(my_shifts), 1)
        self.assertEqual(my_shifts[0]['date'], "29 Mar")

    def test_get_full_schedule(self):
        self.mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [self.mock_shift]
        Allocation.query = MagicMock()
        Allocation.query.filter_by.return_value.all.return_value = [self.mock_allocation]
        Student.query.get = MagicMock(return_value=self.mock_student)

        today = datetime(2025, 3, 29)
        full_schedule = get_full_schedule(today)

        self.assertIn('days_of_week', full_schedule)
        self.assertIn('time_slots', full_schedule)
        self.assertIn('staff_schedule', full_schedule)
        self.assertEqual(len(full_schedule['staff_schedule']), 8)


if __name__ == '__main__':
    unittest.main()