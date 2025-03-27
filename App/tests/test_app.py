import os, tempfile, pytest, logging, unittest
from werkzeug.security import check_password_hash, generate_password_hash

from App.main import create_app
from App.database import db, create_db
from App.models import User
from App.controllers import (
    create_user,
    get_all_users_json,
    login,
    get_user,
    update_user
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
