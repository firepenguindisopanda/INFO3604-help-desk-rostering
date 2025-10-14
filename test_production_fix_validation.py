#!/usr/bin/env python3
"""
Validation test for the production clock-in fix.
This test confirms that our fix resolves the production CSRF issue.
"""

import unittest
from unittest.mock import patch
from datetime import datetime, timedelta

from App.main import create_app
from App.database import db
from App.controllers.initialize import create_db
from App.controllers.user import create_student
from App.controllers.help_desk_assistant import create_help_desk_assistant
from App.controllers.semester import create_semester
from App.controllers.shift import create_shift
from App.controllers.auth import get_auth_token
from App.utils.time_utils import trinidad_now


class ProductionFixValidationTests(unittest.TestCase):
    """Test suite to validate the production clock-in fix."""

    def setUp(self):
        """Set up test environment."""
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'JWT_SECRET_KEY': 'test-secret-key',
            'WTF_CSRF_ENABLED': False,
        })
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Initialize database
        create_db()

        # Create test user and data
        self.username = "testvolunteer"
        self.password = "testpass123"
        create_student(self.username, self.password, "BSc", "Test Volunteer")
        create_help_desk_assistant(self.username)

        # Get JWT token for authentication
        self.token = get_auth_token(self.username, self.password)

    def tearDown(self):
        """Clean up test environment."""
        db.session.remove()
        db.drop_all()
        if self.app_context is not None:
            self.app_context.pop()

    def _create_active_shift(self):
        """Create an active shift for testing."""
        # Create semester
        semester_id = create_semester("2024", "Semester 1", 
                                    trinidad_now().date(), 
                                    trinidad_now().date() + timedelta(days=90))

        # Create shift that started 1 hour ago and goes for 4 hours
        start_time = trinidad_now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        end_time = start_time + timedelta(hours=4)

        shift_id = create_shift(
            semester_id=semester_id,
            day_of_week=start_time.strftime('%A'),
            start_time=start_time.time(),
            end_time=end_time.time(),
            max_volunteers=3,
            shift_type='help_desk'
        )

        return shift_id, start_time

    @patch('App.utils.time_utils.trinidad_now')
    def test_production_fix_bearer_token_works(self, mock_trinidad_now):
        """Test that Bearer token authentication works in production with CSRF protection."""
        shift_id, current_time = self._create_active_shift()
        mock_trinidad_now.return_value = current_time

        # Simulate production environment with CSRF protection
        with patch.dict(self.app.config, {
            'JWT_COOKIE_CSRF_PROTECT': True,
            'JWT_COOKIE_SECURE': False,  # Keep False for testing
            'ENV': 'production'
        }):
            # Test volunteer dashboard access with Bearer token
            response = self.client.get(
                '/api/v2/volunteer/dashboard',
                headers={
                    'Authorization': f'Bearer {self.token}',
                    'Content-Type': 'application/json'
                }
            )

            self.assertEqual(response.status_code, 200,
                           "Dashboard should be accessible with Bearer token")

            # Test time tracking overview with Bearer token
            response = self.client.get(
                '/api/v2/volunteer/time-tracking',
                headers={
                    'Authorization': f'Bearer {self.token}',
                    'Content-Type': 'application/json'
                }
            )

            self.assertEqual(response.status_code, 200,
                           "Time tracking should be accessible with Bearer token")

            # Test clock-in with Bearer token
            response = self.client.post(
                '/api/v2/volunteer/time-tracking/clock-in',
                json={},
                headers={
                    'Authorization': f'Bearer {self.token}',
                    'Content-Type': 'application/json'
                }
            )

            self.assertEqual(response.status_code, 200,
                           "Clock-in should work with Bearer token")

            response_data = response.get_json()
            self.assertTrue(response_data.get('success', False))

    @patch('App.utils.time_utils.trinidad_now')
    def test_production_fix_cookie_without_csrf_fails(self, mock_trinidad_now):
        """Test that cookie authentication without CSRF token fails in production (expected behavior)."""
        _, current_time = self._create_active_shift()
        mock_trinidad_now.return_value = current_time

        # Simulate production environment with CSRF protection
        with patch.dict(self.app.config, {
            'JWT_COOKIE_CSRF_PROTECT': True,
            'JWT_COOKIE_SECURE': False,  # Keep False for testing
            'ENV': 'production'
        }):
            # Test that cookie without CSRF token fails (this is the original bug scenario)
            response = self.client.post(
                '/api/v2/volunteer/time-tracking/clock-in',
                json={},
                headers={
                    'Content-Type': 'application/json',
                    'Cookie': f'access_token={self.token}'
                    # No X-CSRF-TOKEN header
                }
            )

            # This should fail with authentication error
            self.assertIn(response.status_code, [401, 422],
                         "Cookie auth without CSRF should fail in production")

    def test_development_still_works(self):
        """Test that development environment still works as expected."""
        # Simulate development environment (CSRF protection disabled)
        with patch.dict(self.app.config, {
            'JWT_COOKIE_CSRF_PROTECT': False,
            'JWT_COOKIE_SECURE': False,
            'ENV': 'development'
        }):
            # Test that cookie authentication works in development
            response = self.client.get(
                '/api/v2/volunteer/dashboard',
                headers={
                    'Cookie': f'access_token={self.token}',
                    'Content-Type': 'application/json'
                }
            )

            self.assertEqual(response.status_code, 200,
                           "Dashboard should work with cookies in development")


if __name__ == '__main__':
    unittest.main()