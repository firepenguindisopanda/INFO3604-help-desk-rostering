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
@pytest.fixture(scope="module")
def empty_db():
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    with app.app_context():
        create_db()
        yield app
        with app.app_context():
            db.session.remove()
            db.drop_all()


def test_authenticate(empty_db):
    user = create_user("bob", "bobpass", "admin")
    assert login("bob", "bobpass") is not None


@pytest.mark.usefixtures("empty_db")
class UsersIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
        self.app_context = self.app.app_context()
        self.app_context.push()
        create_db()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        if self.app_context is not None:
            self.app_context.pop()

    def test_create_user(self):
        user = create_user("rick", "bobpass")
        assert user.username == "rick"

    def test_update_user(self):
        create_user("bob", "bobpass")
        update_user("bob", "ronnie")
        user = get_user("ronnie")
        assert user is not None
        assert user.username == "ronnie"
        

class AuthIntegrationTests(unittest.TestCase):

    def setUp(self):

        self.app = Flask(__name__)
        self.app.config['JWT_SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        self.jwt = setup_jwt(self.app)

        self.mock_user = MagicMock()
        self.mock_user.username = "a"
        self.mock_user.type = "admin"
        self.mock_user.check_password = MagicMock(return_value=True)

    def test_login_success(self):

        User.query = MagicMock()
        User.query.filter_by.return_value.first.return_value = self.mock_user

        with self.app.app_context():
            token, user_type = login("a", "password")
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
        self.mock_student.username = "a"
        self.mock_student.name = "Test User"

        # Mock the Shift model
        self.mock_shift = MagicMock()
        self.mock_shift.id = 1
        self.mock_shift.date = datetime(2025, 3, 29)
        self.mock_shift.start_time = datetime(2025, 3, 29, 9, 0, 0)
        self.mock_shift.end_time = datetime(2025, 3, 29, 17, 0, 0)

        # Mock the Allocation model
        self.mock_allocation = MagicMock()
        self.mock_allocation.username = "a"
        self.mock_allocation.shift_id = 1

    def tearDown(self):
        patch.stopall()

    def test_get_dashboard_data_success(self):
        Student.query.get = MagicMock(return_value=self.mock_student)

        with patch('App.controllers.dashboard.get_next_shift', return_value={"date": "29 March, 2025", "time": "9:00 AM to 5:00 PM"}):
            with patch('App.controllers.dashboard.get_my_upcoming_shifts', return_value=[{"date": "29 Mar", "time": "9:00 AM to 5:00 PM"}]):
                with patch('App.controllers.schedule.get_current_schedule', return_value={"days": []}):
                    dashboard_data = get_dashboard_data("a")

        self.assertIsNotNone(dashboard_data)
        self.assertEqual(dashboard_data['student'].username, "a")
        self.assertEqual(dashboard_data['next_shift']['date'], "29 March, 2025")
        self.assertEqual(len(dashboard_data['my_shifts']), 1)

    def test_get_next_shift_active_shift(self):
        self.mock_db_session.query.return_value.join.return_value.filter.return_value.first.return_value = (self.mock_allocation, self.mock_shift)

        now = datetime(2025, 3, 29, 10, 0, 0)
        next_shift = get_next_shift("a", now)

        self.assertEqual(next_shift['date'], "29 March, 2025")
        self.assertTrue(next_shift['starts_now'])

    def test_get_next_shift_no_upcoming_shifts(self):
        self.mock_db_session.query.return_value.join.return_value.filter.return_value.first.return_value = None

        now = datetime(2025, 3, 29, 10, 0, 0)
        next_shift = get_next_shift("a", now)

        self.assertEqual(next_shift['date'], "No upcoming shifts")
        self.assertFalse(next_shift['starts_now'])

    def test_get_my_upcoming_shifts(self):
        self.mock_db_session.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = [(self.mock_allocation, self.mock_shift)]

        today = datetime(2025, 3, 29)
        my_shifts = get_my_upcoming_shifts("a", today)

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

class InitializeIntegrationTests(unittest.TestCase):

    def setUp(self):
        # Set up an in-memory SQLite database for testing
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
        self.app_context = self.app.app_context()
        self.app_context.push()
        create_db()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        if self.app_context is not None:
            self.app_context.pop()

    def test_initialize_creates_admin_account(self):
        initialize()
        admin = User.query.filter_by(username='a').first()
        self.assertIsNotNone(admin)
        self.assertEqual(admin.username, 'a')
        self.assertTrue(admin.check_password('123'))
        self.assertEqual(admin.type, 'admin')

    def test_initialize_creates_standard_courses(self):
        initialize()
        courses = Course.query.all()
        self.assertGreater(len(courses), 0)
        self.assertTrue(any(course.code == 'COMP3602' for course in courses))

    '''
    def test_initialize_creates_student_assistants(self):
        initialize()
        students = Student.query.all()
        self.assertGreater(len(students), 0)
        self.assertTrue(any(student.username == '816031001' for student in students))
    ''' 

    def test_initialize_creates_availabilities(self):
        initialize()
        availabilities = Availability.query.all()
        self.assertGreater(len(availabilities), 0)
        # Update the attribute name to match the actual model definition
        self.assertTrue(any(avail.username == '816031001' for avail in availabilities))

    def test_initialize_creates_course_capabilities(self):
        initialize()
        capabilities = CourseCapability.query.all()
        self.assertGreater(len(capabilities), 0)
        self.assertTrue(any(capability.assistant_username == '816031001' for capability in capabilities))

    def test_create_standard_courses_skips_existing_courses(self):
        course = Course(code='COMP3602', name='Advanced Algorithms')
        db.session.add(course)
        db.session.commit()
        create_standard_courses()
        courses = Course.query.filter_by(code='COMP3602').all()
        self.assertEqual(len(courses), 1)

    def test_create_student_assistants_handles_errors(self):
        with patch('App.database.db.session.add', side_effect=Exception("Database error")):
            with self.assertLogs('App.controllers.initialize', level='ERROR') as log:
                create_student_assistants()
            self.assertTrue(any("Error creating student" in message for message in log.output))
    
@pytest.mark.usefixtures("empty_db")
class NotificationIntegrationTests(unittest.TestCase):

    def setUp(self):
        # Set up an in-memory SQLite database for testing
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
        self.app_context = self.app.app_context()
        self.app_context.push()
        create_db()

        # Create a test user with a password
        self.test_user = User(username='testuser', password='testpass', type='user')
        db.session.add(self.test_user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        if self.app_context is not None:
            self.app_context.pop()

    def test_create_notification(self):
        notification = create_notification('testuser', 'Test message', Notification.TYPE_REMINDER)
        self.assertIsNotNone(notification)
        self.assertEqual(notification.username, 'testuser')
        self.assertEqual(notification.message, 'Test message')
        self.assertEqual(notification.notification_type, Notification.TYPE_REMINDER)

    '''def test_get_user_notifications(self):
        create_notification('testuser', 'Message 1', Notification.TYPE_REMINDER)
        create_notification('testuser', 'Message 2', Notification.TYPE_REMINDER)
        create_notification('testuser', 'Message 3', Notification.TYPE_REMINDER)

        notifications = get_user_notifications('testuser', limit=2)
        self.assertEqual(len(notifications), 2)
        self.assertEqual(notifications[0].message, 'Message 3')  # Newest first
        self.assertEqual(notifications[1].message, 'Message 2')'''

    def test_get_notification(self):
        notification = create_notification('testuser', 'Test message', Notification.TYPE_REMINDER)
        fetched_notification = get_notification(notification.id)
        self.assertIsNotNone(fetched_notification)
        self.assertEqual(fetched_notification.message, 'Test message')

    def test_mark_notification_as_read(self):
        notification = create_notification('testuser', 'Test message', Notification.TYPE_REMINDER)
        self.assertFalse(notification.is_read)

        result = mark_notification_as_read(notification.id)
        self.assertTrue(result)

        updated_notification = get_notification(notification.id)
        self.assertTrue(updated_notification.is_read)

    def test_mark_all_notifications_as_read(self):
        create_notification('testuser', 'Message 1', Notification.TYPE_REMINDER)
        create_notification('testuser', 'Message 2', Notification.TYPE_REMINDER)
        create_notification('testuser', 'Message 3', Notification.TYPE_REMINDER)

        unread_count = len(get_user_notifications('testuser', include_read=False))
        self.assertEqual(unread_count, 3)

        mark_all_notifications_as_read('testuser')

        unread_count_after = len(get_user_notifications('testuser', include_read=False))
        self.assertEqual(unread_count_after, 0)

    def test_delete_notification(self):
        notification = create_notification('testuser', 'Test message', Notification.TYPE_REMINDER)
        self.assertIsNotNone(get_notification(notification.id))

        result = delete_notification(notification.id)
        self.assertTrue(result)
        self.assertIsNone(get_notification(notification.id))

    def test_count_unread_notifications(self):
        notification1 = create_notification('testuser', 'Message 1', Notification.TYPE_REMINDER)
        notification2 = create_notification('testuser', 'Message 2', Notification.TYPE_REMINDER)
        notification2.is_read = True
        db.session.add(notification2)
        db.session.commit()
        create_notification('testuser', 'Message 3', Notification.TYPE_REMINDER)

        unread_count = len(get_user_notifications('testuser', include_read=False))
        self.assertEqual(unread_count, 2)

    def test_notify_shift_approval(self):
        notification = notify_shift_approval('testuser', 'Shift on March 30, 2025')
        self.assertIsNotNone(notification)
        self.assertEqual(notification.message, 'Your shift change request for Shift on March 30, 2025 was approved.')

    '''def test_notify_all_admins(self):
        # Create admin users
        admin1 = User(username='admin1', password='adminpass1', type='admin')
        admin2 = User(username='admin2', password='adminpass2', type='admin')
        db.session.add(admin1)
        db.session.add(admin2)
        db.session.commit()

        notifications = notify_all_admins('System maintenance scheduled', Notification.TYPE_UPDATE)
        self.assertEqual(len(notifications), 2)
        self.assertTrue(any(n.username == 'admin1' for n in notifications))
        self.assertTrue(any(n.username == 'admin2' for n in notifications))'''

if __name__ == '__main__':
    unittest.main()