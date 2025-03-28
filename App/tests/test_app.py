import os, tempfile, pytest, logging, unittest
from werkzeug.security import check_password_hash, generate_password_hash

from unittest.mock import patch
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

    # pure function no side effects or integrations called
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
        self.assertEqual(student.degree, "BSc")  # Default degree should be 'BSc'

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
        # Create a sample request object for testing
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
        # Create a sample registration request object for testing
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
        self.assertEqual(schedule.end_date, start_date + timedelta(days=6))  # Default end_date is 6 days after start_date
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
    def test_semester_initialization_summer(self):
        # Test for a summer semester (e.g., starting in August)
        start_date = datetime(2023, 8, 1)
        end_date = datetime(2023, 12, 15)
        semester = Semester(start=start_date, end=end_date)
        
        self.assertEqual(semester.academic_year, "2023/2024")
        self.assertEqual(semester.semester, 1)
        self.assertEqual(semester.start, start_date)
        self.assertEqual(semester.end, end_date)

    def test_semester_initialization_winter(self):
        # Test for a winter semester (e.g., starting in January)
        start_date = datetime(2023, 1, 15)
        end_date = datetime(2023, 5, 30)
        semester = Semester(start=start_date, end=end_date)
        
        self.assertEqual(semester.academic_year, "2022/2023")
        self.assertEqual(semester.semester, 2)
        self.assertEqual(semester.start, start_date)
        self.assertEqual(semester.end, end_date)

    def test_semester_initialization_spring(self):
        # Test for a spring semester (e.g., starting in March)
        start_date = datetime(2023, 3, 1)
        end_date = datetime(2023, 6, 30)
        semester = Semester(start=start_date, end=end_date)
        
        self.assertEqual(semester.academic_year, "2022/2023")
        self.assertEqual(semester.semester, 3)
        self.assertEqual(semester.start, start_date)
        self.assertEqual(semester.end, end_date)

    def test_get_json(self):
        # Test the get_json method
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
        self.assertEqual(demand.weight, 2)  # Default weight matches tutors_required

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

'''
    Integration Tests
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
