"""
Test case to reproduce the production-only clock-in error that occurs when volunteers
try to clock in during their shift with CSRF protection enabled.

This test simulates:
1. Production environment with JWT_COOKIE_CSRF_PROTECT=True
2. Volunteer clocking in late during an active shift (like on a Sunday)
3. Using cookie-based authentication without CSRF token (typical browser behavior)
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from App.main import create_app
from App.database import create_db, db
from App.controllers.student import create_student
from App.controllers.help_desk_assistant import create_help_desk_assistant
from App.models.schedule import Schedule
from App.models.shift import Shift
from App.models.allocation import Allocation
from App.utils.time_utils import trinidad_now


class ProductionClockInIssueTests(unittest.TestCase):
    """Test cases that reproduce the production-only clock-in authentication error."""

    def setUp(self):
        """Set up test environment with production-like configuration."""
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'JWT_SECRET_KEY': 'test-secret-key',
            # Simulate production JWT settings
            'JWT_COOKIE_SECURE': True,
            'JWT_COOKIE_CSRF_PROTECT': True,
            'JWT_ACCESS_COOKIE_NAME': 'access_token',
            'JWT_TOKEN_LOCATION': ['cookies', 'headers'],
        })
        self.app_context = self.app.app_context()
        self.app_context.push()
        create_db()

        self.client = self.app.test_client()
        self.username = "volunteer1"
        create_student(self.username, "password", "BSc", "Test Volunteer")
        create_help_desk_assistant(self.username)
        self.token = create_access_token(identity=self.username)

    def tearDown(self):
        """Clean up test environment."""
        db.session.remove()
        db.drop_all()
        if self.app_context is not None:
            self.app_context.pop()

    def _create_sunday_shift_in_progress(self):
        """Create a shift that's currently active on a Sunday (simulating the production scenario)."""
        # Mock the current time to be a Sunday during an active shift
        sunday_base = datetime(2024, 12, 15)  # A Sunday
        shift_start = sunday_base.replace(hour=10, minute=0)  # 10:00 AM
        shift_end = sunday_base.replace(hour=14, minute=0)    # 2:00 PM
        current_time = sunday_base.replace(hour=10, minute=30) # 10:30 AM (30 mins into shift)

        # Create schedule and shift
        schedule = Schedule(
            id=1,
            start_date=sunday_base,
            end_date=sunday_base + timedelta(days=1),
            type='helpdesk'
        )
        db.session.add(schedule)

        shift = Shift(
            date=sunday_base,
            start_time=shift_start,
            end_time=shift_end,
            schedule_id=schedule.id
        )
        db.session.add(shift)
        db.session.flush()

        # Create allocation for the volunteer
        allocation = Allocation(
            username=self.username,
            shift_id=shift.id,
            schedule_id=schedule.id
        )
        db.session.add(allocation)
        db.session.commit()

        return shift, current_time

    @patch('App.utils.time_utils.trinidad_now')
    def test_clock_in_fails_with_csrf_protection_using_standard_jwt_required(self, mock_trinidad_now):
        """Test that clock-in fails in production when using @jwt_required() without CSRF token."""
        shift, current_time = self._create_sunday_shift_in_progress()
        mock_trinidad_now.return_value = current_time

        # Simulate production environment by patching the app config directly
        with patch.dict(self.app.config, {
            'JWT_COOKIE_CSRF_PROTECT': True,
            'JWT_COOKIE_SECURE': False,  # Keep False for testing (no HTTPS)
            'ENV': 'production'
        }):
            # Set the JWT cookie using the Cookie header approach
            response = self.client.post(
                '/api/v2/volunteer/time-tracking/clock-in',
                json={},
                headers={
                    'Content-Type': 'application/json',
                    'Cookie': f'access_token={self.token}'
                    # NOTE: No X-CSRF-TOKEN header - this is the issue in production
                }
            )

            # This should fail with authentication error in production due to missing CSRF token
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.get_data(as_text=True)}")
            
            # Should be 422 (Unprocessable Entity) for CSRF token missing
            # or 401 (Unauthorized) depending on JWT-Extended version
            self.assertIn(response.status_code, [401, 422],
                          "Expected authentication failure due to missing CSRF token")

            response_data = response.get_json()
            if response_data:
                self.assertFalse(response_data.get('success', True))
                # Check for CSRF-related error message
                error_msg = response_data.get('message', '').upper()
                self.assertTrue(
                    'CSRF' in error_msg or 'UNAUTHORIZED' in error_msg or 'MISSING' in error_msg,
                    f"Expected CSRF-related error, got: {response_data.get('message')}"
                )

    @patch('App.utils.time_utils.trinidad_now')
    def test_clock_in_succeeds_with_bearer_token_in_production(self, mock_trinidad_now):
        """Test that clock-in succeeds when using Authorization header instead of cookies."""
        _, current_time = self._create_sunday_shift_in_progress()
        mock_trinidad_now.return_value = current_time

        # Simulate production environment with CSRF protection enabled
        with patch.dict(self.app.config, {
            'JWT_COOKIE_CSRF_PROTECT': True,
            'JWT_COOKIE_SECURE': False,  # Keep False for testing (no HTTPS)
            'ENV': 'production'
        }):
            # Attempt clock-in using Bearer token in Authorization header
            response = self.client.post(
                '/api/v2/volunteer/time-tracking/clock-in',
                json={},
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.token}',
                    # No CSRF token needed when using Authorization header
                }
            )

            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.get_data(as_text=True)}")

            # This should succeed with the fixed @jwt_required_secure() decorator
            self.assertEqual(response.status_code, 200, 
                           "Clock-in should succeed with Bearer token")
            
            response_data = response.get_json()
            self.assertIsNotNone(response_data, "Response should contain JSON data")
            self.assertTrue(response_data.get('success', False), "Response should indicate success")
            self.assertIn('message', response_data, "Response should contain success message")
            self.assertIn('data', response_data, "Response should contain data")

    @patch('App.utils.time_utils.trinidad_now')
    def test_clock_in_succeeds_in_development_without_csrf(self, mock_trinidad_now):
        """Test that clock-in works in development environment without CSRF protection."""
        shift, current_time = self._create_sunday_shift_in_progress()
        mock_trinidad_now.return_value = current_time

        # Reconfigure app for development settings
        self.app.config['JWT_COOKIE_CSRF_PROTECT'] = False
        self.app.config['JWT_COOKIE_SECURE'] = False

        # Simulate development environment
        with patch.dict('os.environ', {'ENV': 'development'}):
            # Attempt clock-in using only cookie authentication (no CSRF token)
            response = self.client.post(
                '/api/v2/volunteer/time-tracking/clock-in',
                json={},
                headers={
                    'Content-Type': 'application/json',
                    # No X-CSRF-TOKEN header needed in development
                },
                environ_base={'HTTP_COOKIE': f'access_token={self.token}'}
            )

            # This should succeed in development
            self.assertEqual(response.status_code, 200, 
                           "Clock-in should succeed in development without CSRF")
            
            response_data = response.get_json()
            self.assertTrue(response_data.get('success', False))

    def test_timing_validation_during_sunday_shift(self):
        """Test that timing validation works correctly for late clock-in on Sunday."""
        with patch('App.utils.time_utils.trinidad_now') as mock_trinidad_now:
            shift, current_time = self._create_sunday_shift_in_progress()
            mock_trinidad_now.return_value = current_time

            # Use Bearer token to bypass CSRF issue and test timing logic
            response = self.client.post(
                '/api/v2/volunteer/time-tracking/clock-in',
                json={'shift_id': shift.id},
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.token}',
                }
            )

            # Should succeed - clocking in 30 minutes late is within the 30-minute grace period
            self.assertEqual(response.status_code, 200)
            response_data = response.get_json()
            self.assertTrue(response_data.get('success', False))
            self.assertIn('Clocked in successfully', response_data.get('message', ''))


if __name__ == '__main__':
    # Run the specific test that demonstrates the production issue
    suite = unittest.TestSuite()
    suite.addTest(ProductionClockInIssueTests('test_clock_in_fails_with_csrf_protection_using_standard_jwt_required'))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*80)
    print("ISSUE SUMMARY:")
    print("="*80)
    print("The production clock-in error occurs because:")
    print("1. Production enables JWT_COOKIE_CSRF_PROTECT=True")
    print("2. Volunteer API routes use @jwt_required() instead of @jwt_required_secure()")
    print("3. Browsers send JWT cookies without CSRF tokens")
    print("4. Flask-JWT-Extended rejects cookie auth without CSRF token in production")
    print("\nSOLUTION: Update volunteer API routes to use @jwt_required_secure() decorator")
    print("="*80)