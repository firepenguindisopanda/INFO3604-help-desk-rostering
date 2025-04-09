import os, tempfile, pytest, logging, unittest, warnings
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

# class UsersIntegrationTests(unittest.TestCase):

#     def setUp(self):
#         # Set up an in-memory SQLite database for testing
#         self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
#         self.app_context = self.app.app_context()
#         self.app_context.push()
#         create_db()

#     def tearDown(self):
#         db.session.remove()
#         db.drop_all()
#         if self.app_context is not None:
#             self.app_context.pop()

#     def test_create_user(self):
#         user = create_user("rick", "bobpass")
#         assert user.username == "rick"

#     def test_update_user(self):
#         create_user("bob", "bobpass")
#         update_user("bob", "ronnie")
#         user = get_user("ronnie")
#         assert user is not None
#         assert user.username == "ronnie"
        

class AuthIntegrationTests(unittest.TestCase):

    def setUp(self):
        # Set up a Flask app for testing
        self.app = Flask(__name__)
        self.app.config['JWT_SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        self.jwt = setup_jwt(self.app)

        self.mock_user = MagicMock()
        self.mock_user.username = "a"
        self.mock_user.type = "admin"
        self.mock_user.check_password = MagicMock(return_value=True)

    def tearDown(self):
        pass  # No database setup required for this class

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
    
class NotificationIntegrationTests(unittest.TestCase):

    def setUp(self):
        # Set up an in-memory SQLite database for testing
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
        self.app_context = self.app.app_context()
        self.app_context.push()
        create_db()

        # Create a test user with a password
        self.test_user = create_admin(username='testuser', password='testpass')
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

class RegistrationIntegrationTests(unittest.TestCase):

    def setUp(self):
        # Set up an in-memory SQLite database for testing
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
        self.app_context = self.app.app_context()
        self.app_context.push()
        create_db()

        # Create a test admin user
        self.admin_user = User(username='admin', password='adminpass', type='admin')
        db.session.add(self.admin_user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        if self.app_context is not None:
            self.app_context.pop()

    '''def test_create_registration_request(self):
        result, message = create_registration_request(
            username="student1",
            name="John Doe",
            email="johndoe@example.com",
            degree="BSc",
            reason="Enrollment",
            phone="1234567890",
            courses=["CS101", "CS102"],
            password="securepassword"
        )
        self.assertTrue(result)
        self.assertEqual(message, "Registration request submitted successfully")

        registration = RegistrationRequest.query.filter_by(username="student1").first()
        self.assertIsNotNone(registration)
        self.assertEqual(registration.name, "John Doe")
        self.assertEqual(registration.degree, "BSc")

        courses = RegistrationCourse.query.filter_by(registration_id=registration.id).all()
        self.assertEqual(len(courses), 2)
        self.assertTrue(any(course.course_code == "CS101" for course in courses))
        self.assertTrue(any(course.course_code == "CS102" for course in courses))

        notification = Notification.query.filter_by(username="admin").first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.message, "New registration request from John Doe (student1).")'''

    '''def test_approve_registration(self):
        # Create a registration request
        registration = RegistrationRequest(
            username="student1",
            name="John Doe",
            email="johndoe@example.com",
            degree="BSc"
        )
        registration.status = "PENDING"
        db.session.add(registration)
        db.session.commit()
    
        result, message = approve_registration(registration.id, "admin")
        self.assertTrue(result)
        self.assertEqual(message, "Registration approved successfully")
    
        updated_registration = RegistrationRequest.query.get(registration.id)
        self.assertEqual(updated_registration.status, "APPROVED")
        self.assertEqual(updated_registration.processed_by, "admin")
    
        user = User.query.filter_by(username="student1").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "student1")'''

    def test_reject_registration(self):
        # Create a registration request
        registration = RegistrationRequest(
            username="student1",
            name="John Doe",
            email="johndoe@example.com",
            degree="BSc",
        )
        registration.status = "PENDING"        
        db.session.add(registration)
        db.session.commit()

        # Reject the registration
        result, message = reject_registration(registration.id, "admin")
        self.assertTrue(result)
        self.assertEqual(message, "Registration rejected successfully")

        # Verify the registration status
        updated_registration = RegistrationRequest.query.get(registration.id)
        self.assertEqual(updated_registration.status, "REJECTED")
        self.assertEqual(updated_registration.processed_by, "admin")

    def test_get_all_registration_requests(self):
        pending_request = RegistrationRequest(username="student1", name="John Doe", email="johndoe@example.com", degree="BSc")
        pending_request.status = "PENDING"
    
        approved_request = RegistrationRequest(username="student2", name="Jane Doe", email="janedoe@example.com", degree="BSc")
        approved_request.status = "APPROVED"
    
        rejected_request = RegistrationRequest(username="student3", name="Jim Doe", email="jimdoe@example.com", degree="BSc")
        rejected_request.status = "REJECTED"
    
        db.session.add_all([pending_request, approved_request, rejected_request])
        db.session.commit()
    
        requests = get_all_registration_requests()
        self.assertEqual(len(requests['pending']), 1)
        self.assertEqual(len(requests['approved']), 1)
        self.assertEqual(len(requests['rejected']), 1)

    def test_get_registration_request(self):
        registration = RegistrationRequest(username="student1", name="John Doe", email="johndoe@example.com", degree="BSc")
        registration.status = "PENDING"
        db.session.add(registration)
        db.session.flush()  # Get the ID without committing
    
        course1 = RegistrationCourse(registration_id=registration.id, course_code="CS101")
        course2 = RegistrationCourse(registration_id=registration.id, course_code="CS102")
        db.session.add_all([course1, course2])
        db.session.commit()
    
        registration_data = get_registration_request(registration.id)
        self.assertIsNotNone(registration_data)
        self.assertEqual(registration_data['username'], "student1")
        self.assertEqual(len(registration_data['course_codes']), 2)
        self.assertIn("CS101", registration_data['course_codes'])
        self.assertIn("CS102", registration_data['course_codes'])

class RequestIntegrationTests(unittest.TestCase):

    def setUp(self):
        # Set up an in-memory SQLite database for testing
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
        self.app_context = self.app.app_context()
        self.app_context.push()
        create_db()

        # Create test data
        self.student = create_student("student1", "securepassword", "BSc", "John Doe")
        self.admin = create_admin("admin", "adminpass")
        db.session.add(self.student)
        db.session.add(self.admin)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        if self.app_context is not None:
            self.app_context.pop()

    def test_create_student_request(self):
        # Create a shift
        shift = Shift(
            date=datetime.utcnow() + timedelta(days=1),
            start_time=datetime.strptime("08:00", "%H:%M"),
            end_time=datetime.strptime("12:00", "%H:%M")
        )
        shift.id=1
        db.session.add(shift)
        db.session.commit()

        # Create a request
        result, message = create_student_request(
            username="student1",
            shift_id=1,
            reason="Personal reasons"
        )
        self.assertTrue(result)
        self.assertEqual(message, "Request submitted successfully")

        # Verify the request
        request = Request.query.filter_by(username="student1", shift_id=1).first()
        self.assertIsNotNone(request)
        self.assertEqual(request.reason, "Personal reasons")
        self.assertEqual(request.status, "PENDING")

    def test_approve_request(self):
        # Create a request
        request = Request(
            username="student1",
            shift_id=None,
            date=datetime.utcnow(),
            time_slot="08:00 to 12:00",
            reason="Personal reasons",
            status="PENDING"
        )
        db.session.add(request)
        db.session.commit()

        # Approve the request
        result, message = approve_request(request.id)
        self.assertTrue(result)
        self.assertEqual(message, "Request approved successfully")

        # Verify the request status
        updated_request = Request.query.get(request.id)
        self.assertEqual(updated_request.status, "APPROVED")
        self.assertIsNotNone(updated_request.approved_at)

    def test_reject_request(self):
        # Create a request
        request = Request(
            username="student1",
            shift_id=None,
            date=datetime.utcnow(),
            time_slot="08:00 to 12:00",
            reason="Personal reasons",
            status="PENDING"
        )
        db.session.add(request)
        db.session.commit()

        # Reject the request
        result, message = reject_request(request.id)
        self.assertTrue(result)
        self.assertEqual(message, "Request rejected successfully")

        # Verify the request status
        updated_request = Request.query.get(request.id)
        self.assertEqual(updated_request.status, "REJECTED")
        self.assertIsNotNone(updated_request.rejected_at)

    def test_cancel_request(self):
        # Create a request
        request = Request(
            username="student1",
            shift_id=None,
            date=datetime.utcnow(),
            time_slot="08:00 to 12:00",
            reason="Personal reasons",
            status="PENDING"
        )
        db.session.add(request)
        db.session.commit()

        # Cancel the request
        result, message = cancel_request(request.id, "student1")
        self.assertTrue(result)
        self.assertEqual(message, "Request cancelled successfully")

        # Verify the request was deleted
        deleted_request = Request.query.get(request.id)
        self.assertIsNone(deleted_request)

    def test_get_all_requests(self):
        # Create multiple requests
        request1 = Request(username="student1", date=datetime.utcnow(), time_slot="08:00 to 12:00", reason="Reason 1", status="PENDING")
        request2 = Request(username="student1", date=datetime.utcnow(), time_slot="01:00 to 05:00", reason="Reason 2", status="APPROVED")
        db.session.add_all([request1, request2])
        db.session.commit()

        requests = get_all_requests()
        self.assertEqual(len(requests), 1)
        self.assertEqual(len(requests[0]["requests"]), 2)

    '''def test_get_student_requests(self):

        request1 = Request(username="student1", date=datetime.utcnow(), time_slot="08:00 to 12:00", reason="Reason 1", status="PENDING")
        request2 = Request(username="student1", date=datetime.utcnow(), time_slot="01:00 to 05:00", reason="Reason 2", status="APPROVED")
        db.session.add_all([request1, request2])
        db.session.commit()

        requests = get_student_requests("student1")
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0]["reason"], "Reason 1") 
        self.assertEqual(requests[1]["reason"], "Reason 2")'''

    def test_get_available_shifts_for_student(self):
        # Create a shift and allocation
        shift = Shift(
            date=datetime.utcnow() + timedelta(days=1),
            start_time=datetime.strptime("08:00", "%H:%M"),
            end_time=datetime.strptime("12:00", "%H:%M")
        )
        allocation = Allocation(username="student1", shift_id=1, schedule_id=1)
        db.session.add_all([shift, allocation])
        db.session.commit()
    
        # Get available shifts
        shifts = get_available_shifts_for_student("student1")
        self.assertEqual(len(shifts), 1)
        self.assertEqual(shifts[0]["id"], 1)

    '''def test_get_available_replacements(self):
        # Create another student assistant
        student2 = Student(username="student2", name="Jane Doe", password="securepassword")
        db.session.add(student2)
        db.session.commit()
    
        shift = Shift(
            date=datetime.utcnow() + timedelta(days=1),
            start_time=datetime.strptime("08:00", "%H:%M"),
            end_time=datetime.strptime("12:00", "%H:%M")
        )
        db.session.add(shift)
        db.session.commit()
    
        allocation = Allocation(username="student1", shift_id=shift.id, schedule_id=1)
        db.session.add(allocation)
        db.session.commit()
    
        # Get available replacements
        replacements = get_available_replacements("student1")
        self.assertEqual(len(replacements), 1)
        self.assertEqual(replacements[0]["id"], "student2")
        self.assertEqual(replacements[0]["name"], "Jane Doe")'''
    
class ScheduleIntegrationTests(unittest.TestCase):

    def setUp(self):
        # Set up an in-memory SQLite database for testing
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
        self.app_context = self.app.app_context()
        self.app_context.push()
        create_db()

        # Create test data
        self.assistant = HelpDeskAssistant(username="assistant1")
        self.assistant.active = True
        self.assistant.hours_minimum = 4

        self.course = Course(code="CS101", name="Introduction to Computer Science")
        self.availability = Availability(
            username="assistant1",
            day_of_week=0,
            start_time=datetime.strptime("09:00", "%H:%M").time(),
            end_time=datetime.strptime("17:00", "%H:%M").time()
        )
        self.capability = CourseCapability(assistant_username="assistant1", course_code="CS101")

        db.session.add_all([self.assistant, self.course, self.availability, self.capability])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        if self.app_context is not None:
            self.app_context.pop()

    '''def test_check_scheduling_feasibility(self):
        result = check_scheduling_feasibility()
        self.assertTrue(result["feasible"])
        self.assertEqual(result["stats"]["assistant_count"], 1)
        self.assertEqual(result["stats"]["assistants_with_availability"], 1)
        self.assertEqual(result["stats"]["assistants_with_capabilities"], 1)

    def test_generate_schedule(self):
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=4)  # Full week
        result = generate_schedule(start_date=start_date, end_date=end_date)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["details"]["shifts_created"], 32)  
        self.assertEqual(result["details"]["is_full_week"], True)

        # Verify shifts and allocations
        shifts = Shift.query.all()
        self.assertEqual(len(shifts), 32)

        allocations = Allocation.query.all()
        self.assertGreater(len(allocations), 0)'''

    def test_get_current_schedule(self):
        # Generate a schedule
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=4)
        generate_schedule(start_date=start_date, end_date=end_date)

        # Fetch the current schedule
        schedule = get_current_schedule()
        self.assertIsNotNone(schedule)
        self.assertEqual(schedule["is_published"], False)
        self.assertEqual(len(schedule["days"]), 5)  # Monday to Friday

    def test_publish_schedule(self):
        # Generate a schedule
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=4)
        generate_schedule(start_date=start_date, end_date=end_date)

        # Publish the schedule
        schedule = Schedule.query.first()
        result = publish_schedule(schedule.id)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Schedule published and notifications sent")

        # Verify the schedule is published
        updated_schedule = Schedule.query.get(schedule.id)
        self.assertTrue(updated_schedule.is_published)

    def test_clear_schedule(self):
        # Generate a schedule
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=4)
        generate_schedule(start_date=start_date, end_date=end_date)

        # Clear the schedule
        result = clear_schedule()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["details"]["shifts_removed"], 24)

        # Verify the schedule is cleared
        shifts = Shift.query.all()
        self.assertEqual(len(shifts), 0)

class TrackingIntegrationTests(unittest.TestCase):

    def setUp(self):
        # Set up an in-memory SQLite database for testing
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
        self.app_context = self.app.app_context()
        self.app_context.push()
        create_db()

        # Create test data
        self.student = Student(username="student1", name="John Doe", password="securepassword")
        self.assistant = HelpDeskAssistant(username="student1")
        self.assistant.active = True  # Set active directly
        self.assistant.hours_minimum = 4  # Set hours_minimum directly

        # Use datetime.datetime for start_time and end_time
        now = datetime.utcnow()
        self.shift = Shift(
            date=now.date(),
            start_time=now.replace(hour=9, minute=0, second=0, microsecond=0),
            end_time=now.replace(hour=17, minute=0, second=0, microsecond=0)
        )
        db.session.add_all([self.student, self.assistant, self.shift])
        db.session.commit()

        self.allocation = Allocation(username="student1", shift_id=self.shift.id, schedule_id=1)
        db.session.add(self.allocation)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        if self.app_context is not None:
            self.app_context.pop()

    def test_get_student_stats(self):
        # Create a completed time entry
        clock_in_time = datetime.utcnow().replace(hour=9, minute=0, second=0, microsecond=0)
        clock_out_time = datetime.utcnow().replace(hour=17, minute=0, second=0, microsecond=0)
        time_entry = TimeEntry(username="student1", clock_in=clock_in_time, shift_id=self.shift.id, status="completed")
        time_entry.clock_out = clock_out_time  # Set clock_out directly
        db.session.add(time_entry)
        db.session.commit()

        stats = get_student_stats("student1")
        self.assertIsNotNone(stats)
        self.assertEqual(stats['daily']['hours'], 8.0)
        self.assertEqual(stats['weekly']['hours'], 8.0)
        self.assertEqual(stats['monthly']['hours'], 8.0)
        self.assertEqual(stats['semester']['hours'], 8.0)
        self.assertEqual(stats['absences'], 0)

    def test_get_all_assistant_stats(self):
        stats = get_all_assistant_stats()
        self.assertEqual(len(stats), 1)
        self.assertEqual(stats[0]['id'], "student1")
        self.assertEqual(stats[0]['semester_attendance'], "0.0")
        self.assertEqual(stats[0]['week_attendance'], "0.0")

    '''def test_get_today_shift(self):
        shift_details = get_today_shift("student1")
        self.assertIsNotNone(shift_details)
        self.assertEqual(shift_details['status'], "future")
        self.assertEqual(shift_details['shift_id'], self.shift.id)'''

    '''def test_clock_in(self):
        result = clock_in("student1", self.shift.id)
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], "Clocked in successfully")

        # Verify the time entry
        time_entry = TimeEntry.query.filter_by(username="student1", status="active").first()
        self.assertIsNotNone(time_entry)
        self.assertEqual(time_entry.shift_id, self.shift.id)

    def test_clock_out(self):
        # Clock in first
        clock_in("student1", self.shift.id)

        # Clock out
        result = clock_out("student1")
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], "Clocked out successfully")

        # Verify the time entry
        time_entry = TimeEntry.query.filter_by(username="student1", status="completed").first()
        self.assertIsNotNone(time_entry)
        self.assertEqual(time_entry.shift_id, self.shift.id)'''

    def test_mark_missed_shift(self):
        result = mark_missed_shift("student1", self.shift.id)
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], "Shift marked as missed")

        # Verify the time entry
        time_entry = TimeEntry.query.filter_by(username="student1", shift_id=self.shift.id, status="absent").first()
        self.assertIsNotNone(time_entry)

    '''def test_generate_attendance_report(self):
        # Create a completed time entry
        clock_in_time = datetime.utcnow().replace(hour=9, minute=0, second=0, microsecond=0)
        clock_out_time = datetime.utcnow().replace(hour=17, minute=0, second=0, microsecond=0)
        time_entry = TimeEntry(username="student1", clock_in=clock_in_time, shift_id=self.shift.id, status="completed")
        time_entry.clock_out = clock_out_time  # Set clock_out directly
        db.session.add(time_entry)
        db.session.commit()

        report = generate_attendance_report(username="student1")
        self.assertTrue(report['success'])
        self.assertEqual(len(report['report']['students']), 1)
        self.assertEqual(report['report']['students'][0]['student_id'], "student1")
        self.assertEqual(report['report']['students'][0]['total_hours'], 8.0)'''    


class UserIntegrationTests(unittest.TestCase):

    def setUp(self):
        # Set up an in-memory SQLite database for testing
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
        self.app_context = self.app.app_context()
        self.app_context.push()  # Push the app context
        create_db()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        if self.app_context is not None:
            self.app_context.pop()  # Pop the app context

    def test_create_user(self):
        user = create_user("a", "testpassword", "student")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "a")
        self.assertEqual(user.type, "student")

        # Verify user exists in the database
        db_user = User.query.filter_by(username="a").first()
        self.assertIsNotNone(db_user)
        self.assertEqual(db_user.username, "a")

    '''def test_get_user(self):
        create_user("a", "testpassword", "student")
        user = get_user("a")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "a")'''

    '''def test_get_all_users(self):
        create_user("user1", "password1", "student")
        create_user("user2", "password2", "admin")
        users = get_all_users()
        self.assertEqual(len(users), 2)
        self.assertTrue(any(user.username == "user1" for user in users))
        self.assertTrue(any(user.username == "user2" for user in users))

    def test_get_all_users_json(self):
        create_user("user1", "password1", "student")
        create_user("user2", "password2", "admin")
        users_json = get_all_users_json()
        self.assertEqual(len(users_json), 2)
        self.assertTrue(any(user["Username"] == "user1" for user in users_json))
        self.assertTrue(any(user["Username"] == "user2" for user in users_json))'''

    '''def test_update_user(self):
        create_user("a", "testpassword", "student")
        result = update_user("a", "updateduser")
        self.assertIsNotNone(result)

        # Verify the username was updated
        updated_user = User.query.filter_by(username="updateduser").first()
        self.assertIsNotNone(updated_user)
        self.assertEqual(updated_user.username, "updateduser")'''

    '''def test_get_user_profile(self):
        # Create a student user
        student = Student(username="student1", password="securepassword", name="John Doe", degree="MSc")
        db.session.add(student)

        # Create a help desk assistant
        assistant = HelpDeskAssistant(username="student1")
        assistant.rate = 25.0  # Set rate directly
        assistant.active = True
        assistant.hours_worked = 10
        assistant.hours_minimum = 5
        db.session.add(assistant)

        # Add course capabilities
        capability1 = CourseCapability(assistant_username="student1", course_code="CS101")
        capability2 = CourseCapability(assistant_username="student1", course_code="CS102")
        db.session.add_all([capability1, capability2])

        # Add availabilities using `datetime.time` objects
        availability1 = Availability(username="student1", day_of_week=0, start_time=time(9, 0), end_time=time(17, 0))
        availability2 = Availability(username="student1", day_of_week=1, start_time=time(10, 0), end_time=time(18, 0))
        db.session.add_all([availability1, availability2])

        db.session.commit()

        # Get the user profile
        profile = get_user_profile("student1")
        self.assertIsNotNone(profile)
        self.assertEqual(profile["username"], "student1")
        self.assertEqual(profile["type"], "student")
        self.assertEqual(profile["name"], "John Doe")
        self.assertEqual(profile["degree"], "MSc")
        self.assertEqual(profile["rate"], 25.0)
        self.assertTrue(profile["active"])
        self.assertEqual(profile["hours_worked"], 10)
        self.assertEqual(profile["hours_minimum"], 5)
        self.assertEqual(len(profile["courses"]), 2)
        self.assertIn("CS101", profile["courses"])
        self.assertIn("CS102", profile["courses"])
        self.assertEqual(len(profile["availabilities"]), 2)'''
    

if __name__ == '__main__':
    unittest.main()