import os, tempfile, pytest, logging, unittest
from werkzeug.security import check_password_hash, generate_password_hash

from datetime import time, datetime
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
