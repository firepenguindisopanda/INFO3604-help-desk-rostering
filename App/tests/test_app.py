import os, tempfile, pytest, logging, unittest
from unittest.mock import MagicMock
from werkzeug.security import check_password_hash, generate_password_hash
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager, create_access_token

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
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///test.db'})
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
        # Set up a Flask app and configure JWT
        self.app = Flask(__name__)
        self.app.config['JWT_SECRET_KEY'] = 'test-secret-key'
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        # Set up JWT
        self.jwt = setup_jwt(self.app)

        # Mock the User model
        self.mock_user = MagicMock()
        self.mock_user.username = "testuser"
        self.mock_user.type = "admin"
        self.mock_user.check_password = MagicMock(return_value=True)

    def test_login_success(self):
        # Mock User.query.filter_by to return the mock user
        User.query = MagicMock()
        User.query.filter_by.return_value.first.return_value = self.mock_user

        with self.app.app_context():
            token, user_type = login("testuser", "password")
            self.assertIsNotNone(token)
            self.assertEqual(user_type, "admin")

    def test_login_failure(self):
        # Mock User.query.filter_by to return None (user not found)
        User.query = MagicMock()
        User.query.filter_by.return_value.first.return_value = None

        with self.app.app_context():
            token, user_type = login("wronguser", "wrongpassword")
            self.assertIsNone(token)
            self.assertIsNone(user_type)


if __name__ == '__main__':
    unittest.main()