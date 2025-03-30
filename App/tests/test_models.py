import os, tempfile, pytest, logging, unittest
from werkzeug.security import check_password_hash, generate_password_hash

from unittest.mock import patch, MagicMock
from datetime import time, datetime, timedelta
from App.main import create_app
from App.database import db, create_db
from App.models import *
from App.controllers import (
    create_user,
    get_all_users_json,
    login,
    get_user,
    update_user
)

from App.models.course_constants import (
    get_course_name,
    get_all_course_codes,
    get_courses_dict,
    is_valid_course
)

LOGGER = logging.getLogger(__name__)

'''
   Unit Tests
'''
class UserUnitTests(unittest.TestCase):

    def test_create_user(self):
        user = User("bob", "bobpass", "admin")
        self.assertEqual(user.username, "bob")
        self.assertNotEqual(user.password, "bobpass")  # Ensure password is hashed
        self.assertEqual(user.type, "admin")
    
    def test_default_user_type(self):
        user = User("alice", "alicepass")
        self.assertEqual(user.type, "student")  # Default type should be 'student'

    def test_get_json(self):
        user = User("bob", "bobpass", "admin")
        user_json = user.get_json()
        self.assertDictEqual(user_json, {"Username":"bob", "Type":"admin"})
    
    def test_set_password(self):
        user = User("bob", "bobpass")
        old_password_hash = user.password
        user.set_password("newpass")
        self.assertNotEqual(user.password, old_password_hash)  # Password hash should change
        self.assertTrue(check_password_hash(user.password, "newpass"))
    
    def test_hashed_password(self):
        password = "mypass"
        user = User("bob", password)
        assert user.password != password

    def test_check_password(self):
        password = "mypass"
        user = User("bob", password)
        assert user.check_password(password)
        assert not user.check_password("wrongpass")

    def test_is_admin(self):
        admin_user = User("admin", "adminpass", "admin")
        student_user = User("student", "studentpass", "student")
        self.assertTrue(admin_user.is_admin())
        self.assertFalse(student_user.is_admin())

    def test_is_student(self):
        admin_user = User("admin", "adminpass", "admin")
        student_user = User("student", "studentpass", "student")
        self.assertFalse(admin_user.is_student())
        self.assertTrue(student_user.is_student())

class StudentUnitTests(unittest.TestCase):

    def test_create_student(self):
        student = Student(username="john_doe", password="securepass", degree="MSc", name="John Doe", profile_data='{"age": 25}')
        self.assertEqual(student.username, "john_doe")
        self.assertEqual(student.degree, "MSc")
        self.assertEqual(student.name, "John Doe")
        self.assertEqual(student.profile_data, '{"age": 25}')
        self.assertEqual(student.type, "student")  # Inherited from User

    def test_default_degree(self):
        student = Student(username="jane_doe", password="securepass")
        self.assertEqual(student.degree, "BSc")

    def test_get_json(self):
        student = Student(username="john_doe", password="securepass", degree="MSc", name="John Doe")
        expected_json = {
            "Student ID": "john_doe",
            "Name": "John Doe",
            "Degree Level": "MSc"
        }
        self.assertDictEqual(student.get_json(), expected_json)

    def test_get_name_with_name_set(self):
        student = Student(username="john_doe", password="securepass", name="John Doe")
        self.assertEqual(student.get_name(), "John Doe")

    def test_get_name_without_name_set(self):
        student = Student(username="john_doe", password="securepass")
        self.assertEqual(student.get_name(), "john_doe")  # Should return username if name is not set
    
class AdminUnitTests(unittest.TestCase):
    def test_admin_initialization(self):
        admin = Admin(username="admin_user", password="securepassword")
        self.assertEqual(admin.username, "admin_user")
        # Verify the hashed password
        self.assertTrue(check_password_hash(admin.password, "securepassword"))
        self.assertEqual(admin.type, "admin")

    def test_get_json(self):
        admin = Admin(username="admin_user", password="securepassword")
        expected_json = {
            'Admin ID': "admin_user"
        }
        self.assertEqual(admin.get_json(), expected_json)

class AllocationUnitTests(unittest.TestCase):
    def test_allocation_initialization(self):
        allocation = Allocation(username="student_user", shift_id=1, schedule_id=2)
        allocation.created_at = datetime.utcnow()  # Explicitly set created_at for testing
        self.assertEqual(allocation.username, "student_user")
        self.assertEqual(allocation.shift_id, 1)
        self.assertEqual(allocation.schedule_id, 2)
        self.assertIsInstance(allocation.created_at, datetime)

    def test_get_json(self):
        allocation = Allocation(username="student_user", shift_id=1, schedule_id=2)
        allocation.id = 100  # Simulate database-assigned ID
        allocation.created_at = datetime(2023, 1, 1, 12, 0, 0)  # Set a fixed datetime for testing
        expected_json = {
            'Allocation ID': 100,
            'Student ID': "student_user",
            'Shift ID': 1,
            'Schedule ID': 2,
            'Created At': "2023-01-01 12:00:00"
        }
        self.assertEqual(allocation.get_json(), expected_json)

   
class MockShift:
    """Mock Shift class for testing is_available_for_shift"""
    def __init__(self, date, start_time, end_time):
        self.date = date
        self.start_time = start_time
        self.end_time = end_time

class AvailabilityUnitTests(unittest.TestCase):
    def test_availability_initialization(self):
        availability = Availability(username="student_user", day_of_week=0, start_time=time(9, 0), end_time=time(17, 0))
        self.assertEqual(availability.username, "student_user")
        self.assertEqual(availability.day_of_week, 0)
        self.assertEqual(availability.start_time, time(9, 0))
        self.assertEqual(availability.end_time, time(17, 0))

    def test_get_json(self):
        availability = Availability(username="student_user", day_of_week=0, start_time=time(9, 0), end_time=time(17, 0))
        availability.id = 100  # Simulate database-assigned ID
        expected_json = {
            'Availability ID': 100,
            'Student ID': "student_user",
            'Day': "Monday",
            'Start Time': "09:00",
            'End Time': "17:00"
        }
        self.assertEqual(availability.get_json(), expected_json)

    def test_is_available_for_shift(self):
        availability = Availability(username="student_user", day_of_week=0, start_time=time(9, 0), end_time=time(17, 0))
        shift = MockShift(date=datetime(2023, 1, 2), start_time=datetime(2023, 1, 2, 10, 0), end_time=datetime(2023, 1, 2, 12, 0))  # Monday
        self.assertTrue(availability.is_available_for_shift(shift))

        shift = MockShift(date=datetime(2023, 1, 2), start_time=datetime(2023, 1, 2, 8, 0), end_time=datetime(2023, 1, 2, 10, 0))  # Outside availability
        self.assertFalse(availability.is_available_for_shift(shift))

        shift = MockShift(date=datetime(2023, 1, 3), start_time=datetime(2023, 1, 3, 10, 0), end_time=datetime(2023, 1, 3, 12, 0))  # Wrong day
        self.assertFalse(availability.is_available_for_shift(shift))

class CourseCapabilityUnitTests(unittest.TestCase):
    def test_course_capability_initialization(self):
        capability = CourseCapability(assistant_username="assistant_user", course_code="CS101")
        self.assertEqual(capability.assistant_username, "assistant_user")
        self.assertEqual(capability.course_code, "CS101")

    def test_get_json(self):
        capability = CourseCapability(assistant_username="assistant_user", course_code="CS101")
        expected_json = {
            'Assistant ID': "assistant_user",
            'Course Code': "CS101"
        }
        self.assertEqual(capability.get_json(), expected_json)

class CourseConstantsUnitTests(unittest.TestCase):
    def setUp(self):
        self.mock_courses = [
            ('INFO3606', 'Cloud Computing'),
            ('INFO3607', 'Fundamentals of WAN Technologies'),
            ('INFO3608', 'E-Commerce'),
        ]

    @patch('App.models.course_constants.STANDARD_COURSES', new_callable=lambda: [
        ('INFO3606', 'Cloud Computing'),
        ('INFO3607', 'Fundamentals of WAN Technologies'),
        ('INFO3608', 'E-Commerce'),
    ])
    def test_get_course_name(self, mock_courses):
        self.assertEqual(get_course_name('INFO3606'), 'Cloud Computing')
        self.assertEqual(get_course_name('INVALID_CODE'), 'INVALID_CODE')

    @patch('App.models.course_constants.STANDARD_COURSES', new_callable=lambda: [
        ('INFO3606', 'Cloud Computing'),
        ('INFO3607', 'Fundamentals of WAN Technologies'),
        ('INFO3608', 'E-Commerce'),
    ])
    def test_get_all_course_codes(self, mock_courses):
        expected_codes = ['INFO3606', 'INFO3607', 'INFO3608']
        self.assertListEqual(get_all_course_codes(), expected_codes)

    @patch('App.models.course_constants.STANDARD_COURSES', new_callable=lambda: [
        ('INFO3606', 'Cloud Computing'),
        ('INFO3607', 'Fundamentals of WAN Technologies'),
        ('INFO3608', 'E-Commerce'),
    ])
    def test_get_courses_dict(self, mock_courses):
        expected_dict = {
            'INFO3606': 'Cloud Computing',
            'INFO3607': 'Fundamentals of WAN Technologies',
            'INFO3608': 'E-Commerce',
        }
        self.assertDictEqual(get_courses_dict(), expected_dict)

    @patch('App.models.course_constants.STANDARD_COURSES', new_callable=lambda: [
        ('INFO3606', 'Cloud Computing'),
        ('INFO3607', 'Fundamentals of WAN Technologies'),
        ('INFO3608', 'E-Commerce'),
    ])
    def test_is_valid_course(self, mock_courses):
        self.assertTrue(is_valid_course('INFO3606'))
        self.assertFalse(is_valid_course('INVALID_CODE'))
    
class CourseUnitTests(unittest.TestCase):
    def test_course_initialization(self):
        course = Course(code="CS101", name="Introduction to Computer Science", semester=1)
        self.assertEqual(course.code, "CS101")
        self.assertEqual(course.name, "Introduction to Computer Science")
        self.assertEqual(course.semester, 1)

    def test_course_initialization_without_semester(self):
        course = Course(code="CS102", name="Data Structures")
        self.assertEqual(course.code, "CS102")
        self.assertEqual(course.name, "Data Structures")
        self.assertIsNone(course.semester)

    def test_get_json(self):
        course = Course(code="CS101", name="Introduction to Computer Science", semester=1)
        expected_json = {
            'Course Code': "CS101",
            'Course Name': "Introduction to Computer Science",
            'Semester': 1
        }
        self.assertEqual(course.get_json(), expected_json)

class RequestUnitTests(unittest.TestCase):
    def setUp(self):
   
        self.request = Request(
            username="student_user",
            shift_id=101,
            date=datetime(2023, 1, 1),
            time_slot="09:00-12:00",
            reason="Personal",
            replacement=None,
            status="PENDING"
        )
        # Manually set attributes that are typically managed by the database
        self.request.id = 1
        self.request.created_at = datetime(2023, 1, 1, 8, 0, 0)  # Set created_at
        self.request.approved_at = None
        self.request.rejected_at = None

    def test_approve(self):
        self.request.approve()
        self.assertEqual(self.request.status, "APPROVED")
        self.assertIsInstance(self.request.approved_at, datetime)
        self.assertAlmostEqual(self.request.approved_at, datetime.utcnow(), delta=timedelta(seconds=1))

    def test_reject(self):
        self.request.reject()
        self.assertEqual(self.request.status, "REJECTED")
        self.assertIsInstance(self.request.rejected_at, datetime)
        self.assertAlmostEqual(self.request.rejected_at, datetime.utcnow(), delta=timedelta(seconds=1))

    def test_cancel_pending_request(self):
        result = self.request.cancel()
        self.assertTrue(result)
        self.assertEqual(self.request.status, "CANCELLED")

    def test_cancel_non_pending_request(self):
        self.request.status = "APPROVED"
        result = self.request.cancel()
        self.assertFalse(result)
        self.assertEqual(self.request.status, "APPROVED")

    def test_get_json(self):
        self.request.created_at = datetime(2023, 1, 1, 8, 0, 0)  # Ensure created_at is set
        self.request.approve()  # Approve the request to set `approved_at`
        expected_json = {
            'id': 1,
            'username': "student_user",
            'shift_id': 101,
            'date': "2023-01-01",
            'time_slot': "09:00-12:00",
            'reason': "Personal",
            'replacement': None,
            'status': "APPROVED",
            'created_at': "2023-01-01 08:00:00",  # Include created_at in expected JSON
            'approved_at': self.request.approved_at.strftime('%Y-%m-%d %H:%M:%S'),
            'rejected_at': None
        }
        self.assertEqual(self.request.get_json(), expected_json)

class RegistrationRequestUnitTests(unittest.TestCase):
    def setUp(self):

        self.registration_request = RegistrationRequest(
            username="student_user",
            name="John Doe",
            email="student@example.com",
            degree="BSc",
            reason="Enrollment",
            phone="1234567890",
            transcript_path="/path/to/transcript.pdf"
        )
        # Manually set attributes that are typically managed by the database
        self.registration_request.id = 1
        self.registration_request.status = "PENDING"
        self.registration_request.created_at = datetime(2023, 1, 1, 8, 0, 0)
        self.registration_request.processed_at = None
        self.registration_request.processed_by = None

    def test_approve(self):
        self.registration_request.approve(admin_username="admin_user")
        self.assertEqual(self.registration_request.status, "APPROVED")
        self.assertIsInstance(self.registration_request.processed_at, datetime)
        self.assertAlmostEqual(self.registration_request.processed_at, datetime.utcnow(), delta=timedelta(seconds=1))
        self.assertEqual(self.registration_request.processed_by, "admin_user")

    def test_reject(self):
        self.registration_request.reject(admin_username="admin_user")
        self.assertEqual(self.registration_request.status, "REJECTED")
        self.assertIsInstance(self.registration_request.processed_at, datetime)
        self.assertAlmostEqual(self.registration_request.processed_at, datetime.utcnow(), delta=timedelta(seconds=1))
        self.assertEqual(self.registration_request.processed_by, "admin_user")

    def test_get_json(self):
        self.registration_request.approve(admin_username="admin_user")  # Approve the request to set processed fields
        expected_json = {
            'id': 1,
            'username': "student_user",
            'name': "John Doe",
            'email': "student@example.com",
            'phone': "1234567890",
            'degree': "BSc",
            'reason': "Enrollment",
            'transcript_path': "/path/to/transcript.pdf",
            'status': "APPROVED",
            'created_at': "2023-01-01 08:00:00",
            'processed_at': self.registration_request.processed_at.strftime('%Y-%m-%d %H:%M:%S'),
            'processed_by': "admin_user"
        }
        self.assertEqual(self.registration_request.get_json(), expected_json)

    def test_set_password(self):
        self.registration_request.set_password("securepassword")
        self.assertTrue(check_password_hash(self.registration_request.password, "securepassword"))

class ScheduleUnitTests(unittest.TestCase):
    def test_schedule_initialization_with_all_parameters(self):
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 7)
        schedule = Schedule(id=1, start_date=start_date, end_date=end_date, semester_id=101)
        
        self.assertEqual(schedule.id, 1)
        self.assertEqual(schedule.start_date, start_date)
        self.assertEqual(schedule.end_date, end_date)
        self.assertEqual(schedule.semester_id, 101)
        self.assertFalse(schedule.is_published)

    def test_schedule_initialization_with_defaults(self):
        start_date = datetime(2023, 1, 1)
        schedule = Schedule(start_date=start_date)
        schedule.id = 1  # Manually set the ID for testing
        
        self.assertIsNotNone(schedule.id)
        self.assertEqual(schedule.start_date, start_date)
        self.assertEqual(schedule.end_date, start_date + timedelta(days=6))  #
        self.assertIsNone(schedule.semester_id)
        self.assertFalse(schedule.is_published)

    def test_get_json(self):
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 7)
        generated_at = datetime(2023, 1, 1, 12, 0, 0)
        
        schedule = Schedule(id=1, start_date=start_date, end_date=end_date, semester_id=101)
        schedule.generated_at = generated_at  # Manually set generated_at for testing
        
        expected_json = {
            'Schedule ID': 1,
            'Start Date': "2023-01-01",
            'End Date': "2023-01-07",
            'Generated At': "2023-01-01 12:00:00",
            'Published': False,
            'Semester ID': 101  # Include Semester ID in expected JSON
        }
        self.assertEqual(schedule.get_json(), expected_json)

class SemesterUnitTests(unittest.TestCase):

    def test_semester_initialization_one(self):

        start_date = datetime(2023, 1, 15)
        end_date = datetime(2023, 5, 30)
        semester = Semester(start=start_date, end=end_date)
        
        self.assertEqual(semester.academic_year, "2022/2023")
        self.assertEqual(semester.semester, 2)
        self.assertEqual(semester.start, start_date)
        self.assertEqual(semester.end, end_date)
    
    def test_semester_initialization_two(self):

        start_date = datetime(2023, 8, 1)
        end_date = datetime(2023, 12, 15)
        semester = Semester(start=start_date, end=end_date)
        
        self.assertEqual(semester.academic_year, "2023/2024")
        self.assertEqual(semester.semester, 1)
        self.assertEqual(semester.start, start_date)
        self.assertEqual(semester.end, end_date)

    def test_semester_initialization_three(self):

        start_date = datetime(2023, 3, 1)
        end_date = datetime(2023, 6, 30)
        semester = Semester(start=start_date, end=end_date)
        
        self.assertEqual(semester.academic_year, "2022/2023")
        self.assertEqual(semester.semester, 3)
        self.assertEqual(semester.start, start_date)
        self.assertEqual(semester.end, end_date)

    def test_get_json(self):

        start_date = datetime(2023, 8, 1)
        end_date = datetime(2023, 12, 15)
        semester = Semester(start=start_date, end=end_date)
        semester.id = 1  # Manually set the ID for testing
        
        expected_json = {
            'Semester ID': 1,
            'Academic Year': "2023/2024",
            'Semester': 1,
            'Start Date': start_date.date(),
            'End Date': end_date.date()
        }
        self.assertEqual(semester.get_json(), expected_json)

class ShiftCourseDemandUnitTests(unittest.TestCase):
    def test_initialization_with_all_parameters(self):
        demand = ShiftCourseDemand(shift_id=101, course_code="CS101", tutors_required=3, weight=5)
        
        self.assertEqual(demand.shift_id, 101)
        self.assertEqual(demand.course_code, "CS101")
        self.assertEqual(demand.tutors_required, 3)
        self.assertEqual(demand.weight, 5)

    def test_initialization_with_defaults(self):
        demand = ShiftCourseDemand(shift_id=102, course_code="CS102")
        
        self.assertEqual(demand.shift_id, 102)
        self.assertEqual(demand.course_code, "CS102")
        self.assertEqual(demand.tutors_required, 2)  # Default value
        self.assertEqual(demand.weight, 2)  

    def test_get_json(self):
        demand = ShiftCourseDemand(shift_id=101, course_code="CS101", tutors_required=3, weight=5)
        demand.id = 1  # Manually set the ID for testing
        
        expected_json = {
            'ID': 1,
            'Shift ID': 101,
            'Course Code': "CS101",
            'Tutors Required': 3,
            'Weight': 5
        }
        self.assertEqual(demand.get_json(), expected_json)

class ShiftUnitTests(unittest.TestCase):
    def setUp(self):

        self.shift = Shift(
            date=datetime(2023, 1, 1),
            start_time=datetime(2023, 1, 1, 9, 0),
            end_time=datetime(2023, 1, 1, 12, 0),
            schedule_id=101
        )
        self.shift.id = 1  # Manually set the ID for testing

    def test_shift_initialization(self):
        self.assertEqual(self.shift.date, datetime(2023, 1, 1))
        self.assertEqual(self.shift.start_time, datetime(2023, 1, 1, 9, 0))
        self.assertEqual(self.shift.end_time, datetime(2023, 1, 1, 12, 0))
        self.assertEqual(self.shift.schedule_id, 101)

    def test_get_json(self):

        self.shift.course_demands = [
            ShiftCourseDemand(shift_id=self.shift.id, course_code="CS101", tutors_required=2, weight=3),
            ShiftCourseDemand(shift_id=self.shift.id, course_code="CS102", tutors_required=3, weight=4)
        ]
        expected_json = {
            'Shift ID': 1,
            'Date': "2023-01-01",
            'Start Time': "09:00",
            'End Time': "12:00",
            'Schedule ID': 101,
            'Course Demands': [
                {
                    'ID': None,  # ID is not set because it's managed by the database
                    'Shift ID': 1,
                    'Course Code': "CS101",
                    'Tutors Required': 2,
                    'Weight': 3
                },
                {
                    'ID': None,
                    'Shift ID': 1,
                    'Course Code': "CS102",
                    'Tutors Required': 3,
                    'Weight': 4
                }
            ]
        }
        self.assertEqual(self.shift.get_json(), expected_json)

    def test_formatted_time(self):
        self.assertEqual(self.shift.formatted_time(), "09:00 AM to 12:00 PM")

    def test_add_course_demand(self):

        self.shift.course_demands = []
        self.shift.add_course_demand(course_code="CS101", tutors_required=3, weight=5)
        self.assertEqual(len(self.shift.course_demands), 1)
        self.assertEqual(self.shift.course_demands[0].course_code, "CS101")
        self.assertEqual(self.shift.course_demands[0].tutors_required, 3)
        self.assertEqual(self.shift.course_demands[0].weight, 5)

class HelpDeskAssistantModelUnitTests(unittest.TestCase):

    def test_create_help_desk_assistant_default_values(self):

        Student.query = MagicMock()
        Student.query.get.return_value = None

        assistant = HelpDeskAssistant("student1")
        self.assertEqual(assistant.username, "student1")
        self.assertEqual(assistant.rate, 20.00)  # Default rate
        self.assertTrue(assistant.active)  # Default active state
        self.assertEqual(assistant.hours_worked, 0)  # Default hours worked
        self.assertEqual(assistant.hours_minimum, 4)  # Default minimum hours

    def test_create_help_desk_assistant_with_student(self):

        mock_student = MagicMock()
        mock_student.degree = "MSc"
        Student.query = MagicMock()
        Student.query.get.return_value = mock_student

        assistant = HelpDeskAssistant("student1")
        self.assertEqual(assistant.username, "student1")
        self.assertEqual(assistant.rate, 35.00)  # MSc rate
        self.assertTrue(assistant.active)

    def test_get_json(self):
        # Mock the Student.query.get method to return None
        Student.query = MagicMock()
        Student.query.get.return_value = None

        assistant = HelpDeskAssistant("student1")
        assistant.hours_worked = 10
        assistant.hours_minimum = 5
        assistant.active = False
        assistant.course_capabilities = [MagicMock(course_code="INFO3604"), MagicMock(course_code="COMP1601")]

        expected_json = {
            'Student ID': "student1",
            'Rate': "$20.0",
            'Account State': "Inactive",
            'Hours Worked': 10,
            'Minimum Hours': 5,
            'Course Capabilities': ["INFO3604", "COMP1601"]
        }
        self.assertDictEqual(assistant.get_json(), expected_json)

    def test_activate(self):
        assistant = HelpDeskAssistant("student1")
        assistant.active = False
        assistant.activate()
        self.assertTrue(assistant.active)

    def test_deactivate(self):
        assistant = HelpDeskAssistant("student1")
        assistant.active = True
        assistant.deactivate()
        self.assertFalse(assistant.active)

    def test_set_minimum_hours(self):
        assistant = HelpDeskAssistant("student1")
        assistant.set_minimum_hours(10)
        self.assertEqual(assistant.hours_minimum, 10)

    def test_update_hours_worked(self):
        assistant = HelpDeskAssistant("student1")
        assistant.hours_worked = 5
        assistant.update_hours_worked(3)
        self.assertEqual(assistant.hours_worked, 8)

    def test_add_course_capability(self):

        from App.models.course_capability import CourseCapability
        mock_capability = MagicMock(course_code="INFO3604")

        assistant = HelpDeskAssistant("student1")

        assistant.course_capabilities.append(mock_capability)

        # Ensure the capability was added
        self.assertIn(mock_capability, assistant.course_capabilities)
        self.assertEqual(assistant.course_capabilities[0].course_code, "INFO3604")
    
class NotificationUnitTests(unittest.TestCase):
    def setUp(self):

        db.create_all()

    def tearDown(self):
        # Clean up the database after each test
        db.session.remove()
        db.drop_all()

    def test_notification_initialization(self):
        notification = Notification(username="john_doe", message="Test message", notification_type=Notification.TYPE_REMINDER)
        db.session.add(notification)
        db.session.commit()  # Commit to ensure `created_at` is set by the database
        self.assertEqual(notification.username, "john_doe")
        self.assertEqual(notification.message, "Test message")
        self.assertEqual(notification.notification_type, Notification.TYPE_REMINDER)
        self.assertFalse(notification.is_read)
        self.assertIsInstance(notification.created_at, datetime)

    def test_get_json(self):
        notification = Notification(username="john_doe", message="Test message", notification_type=Notification.TYPE_REMINDER)
        db.session.add(notification)
        db.session.commit()

        json_data = notification.get_json()
        self.assertEqual(json_data['username'], "john_doe")
        self.assertEqual(json_data['message'], "Test message")
        self.assertEqual(json_data['notification_type'], Notification.TYPE_REMINDER)
        self.assertFalse(json_data['is_read'])
        self.assertIn('created_at', json_data)
        self.assertIn('friendly_time', json_data)

    def test_get_friendly_time_today(self):
        notification = Notification(username="john_doe", message="Test message", notification_type=Notification.TYPE_REMINDER)
        notification.created_at = datetime.utcnow()
        friendly_time = notification.get_friendly_time()
        self.assertTrue(friendly_time.startswith("Today at"))

    def test_get_friendly_time_yesterday(self):
        notification = Notification(username="john_doe", message="Test message", notification_type=Notification.TYPE_REMINDER)
        notification.created_at = datetime.utcnow() - timedelta(days=1)
        friendly_time = notification.get_friendly_time()
        self.assertTrue(friendly_time.startswith("Yesterday at"))

    def test_get_friendly_time_this_week(self):
        notification = Notification(username="john_doe", message="Test message", notification_type=Notification.TYPE_REMINDER)
        notification.created_at = datetime.utcnow() - timedelta(days=3)
        friendly_time = notification.get_friendly_time()
        self.assertIn("at", friendly_time)

    def test_get_friendly_time_older(self):
        notification = Notification(username="john_doe", message="Test message", notification_type=Notification.TYPE_REMINDER)
        notification.created_at = datetime.utcnow() - timedelta(days=10)
        friendly_time = notification.get_friendly_time()
        expected_year = notification.created_at.year 
        self.assertIn(str(expected_year), friendly_time)

    def test_mark_as_read(self):
        notification = Notification(username="john_doe", message="Test message", notification_type=Notification.TYPE_REMINDER)
        db.session.add(notification)
        db.session.commit()

        notification.mark_as_read()
        self.assertTrue(notification.is_read)
    
    def setUp(self):

        db.create_all()

    def tearDown(self):
        # Remove only the Notification data, not the entire schema
        db.session.query(Notification).delete()
        db.session.commit()

class SemesterUnitTests(unittest.TestCase):

    def test_create_semester_first_semester(self):
        start_date = datetime(2025, 9, 1)  # September 1, 2025
        end_date = datetime(2025, 12, 15)  # December 15, 2025
        semester = Semester(start=start_date, end=end_date)

        self.assertEqual(semester.academic_year, "2025/2026")
        self.assertEqual(semester.semester, 1)
        self.assertEqual(semester.start, start_date)
        self.assertEqual(semester.end, end_date)

    def test_create_semester_second_semester(self):
        start_date = datetime(2025, 1, 15)  # January 15, 2025
        end_date = datetime(2025, 5, 30)   # May 30, 2025
        semester = Semester(start=start_date, end=end_date)

        self.assertEqual(semester.academic_year, "2024/2025")
        self.assertEqual(semester.semester, 2)
        self.assertEqual(semester.start, start_date)
        self.assertEqual(semester.end, end_date)

    def test_create_semester_third_semester(self):
        start_date = datetime(2025, 5, 15)  # May 15, 2025
        end_date = datetime(2025, 8, 15)   # August 15, 2025
        semester = Semester(start=start_date, end=end_date)

        self.assertEqual(semester.academic_year, "2024/2025")
        self.assertEqual(semester.semester, 3)
        self.assertEqual(semester.start, start_date)
        self.assertEqual(semester.end, end_date)

    def test_get_json(self):
        start_date = datetime(2025, 9, 1)  # September 1, 2025
        end_date = datetime(2025, 12, 15)  # December 15, 2025
        semester = Semester(start=start_date, end=end_date)

        expected_json = {
            'Semester ID': None,  # ID is None because it's not saved to the database
            'Academic Year': "2025/2026",
            'Semester': 1,
            'Start Date': start_date.date(),
            'End Date': end_date.date()
        }
        self.assertDictEqual(semester.get_json(), expected_json)

class TimeEntryUnitTests(unittest.TestCase):

    def test_create_time_entry(self):
        clock_in = datetime(2025, 3, 29, 9, 0, 0)  # March 29, 2025, 9:00 AM
        time_entry = TimeEntry(username="student1", clock_in=clock_in, shift_id=1, status="active")

        self.assertEqual(time_entry.username, "student1")
        self.assertEqual(time_entry.clock_in, clock_in)
        self.assertEqual(time_entry.shift_id, 1)
        self.assertEqual(time_entry.status, "active")
        self.assertIsNone(time_entry.clock_out)

    def test_get_json(self):
        clock_in = datetime(2025, 3, 29, 9, 0, 0)
        clock_out = datetime(2025, 3, 29, 17, 0, 0)  # 8 hours later
        time_entry = TimeEntry(username="student1", clock_in=clock_in, shift_id=1, status="completed")
        time_entry.clock_out = clock_out

        expected_json = {
            'Time Entry ID': None,  # ID is None because it's not saved to the database
            'Student ID': "student1",
            'Shift ID': 1,
            'Clock In': "2025-03-29 09:00:00",
            'Clock Out': "2025-03-29 17:00:00",
            'Status': "completed",
            'Hours Worked': 8.0
        }
        self.assertDictEqual(time_entry.get_json(), expected_json)

    def test_complete_time_entry(self):
        clock_in = datetime(2025, 3, 29, 9, 0, 0)
        clock_out = datetime(2025, 3, 29, 17, 0, 0)
        time_entry = TimeEntry(username="student1", clock_in=clock_in, shift_id=1, status="active")

        time_entry.complete(clock_out=clock_out)

        self.assertEqual(time_entry.clock_out, clock_out)
        self.assertEqual(time_entry.status, "completed")

    def test_mark_absent(self):
        clock_in = datetime(2025, 3, 29, 9, 0, 0)
        time_entry = TimeEntry(username="student1", clock_in=clock_in, shift_id=1, status="active")

        time_entry.mark_absent()

        self.assertEqual(time_entry.status, "absent")

    def test_get_hours_worked(self):
        clock_in = datetime(2025, 3, 29, 9, 0, 0)
        clock_out = datetime(2025, 3, 29, 17, 0, 0)  # 8 hours later
        time_entry = TimeEntry(username="student1", clock_in=clock_in, shift_id=1, status="completed")
        time_entry.clock_out = clock_out

        hours_worked = time_entry.get_hours_worked()
        self.assertEqual(hours_worked, 8.0)

    def test_get_hours_worked_incomplete(self):
        clock_in = datetime(2025, 3, 29, 9, 0, 0)
        time_entry = TimeEntry(username="student1", clock_in=clock_in, shift_id=1, status="active")

        hours_worked = time_entry.get_hours_worked()
        self.assertEqual(hours_worked, 0)

    def test_complete_updates_assistant_hours(self):
        clock_in = datetime(2025, 3, 29, 9, 0, 0)
        clock_out = datetime(2025, 3, 29, 17, 0, 0)  # 8 hours later
        time_entry = TimeEntry(username="student1", clock_in=clock_in, shift_id=1, status="active")

        mock_assistant = MagicMock()
        time_entry.student = MagicMock(help_desk_assistant=mock_assistant)

        time_entry.complete(clock_out=clock_out)

        # Ensure the assistant's hours_worked is updated
        mock_assistant.update_hours_worked.assert_called_once_with(8.0)

'''
    Integration Tests
'''

'''
# This fixture creates an empty database for the test and deletes it after the test
# scope="class" would execute the fixture once and resued for all methods in the class
@pytest.fixture(autouse=True, scope="module")
def empty_db():
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield app.test_client()


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
'''