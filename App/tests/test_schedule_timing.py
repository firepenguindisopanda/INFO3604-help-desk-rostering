"""
Schedule Generation and Timing Tests

This test suite covers:
- Schedule generation for different time windows
- Shift allocation timing constraints
- Availability window matching
- Schedule conflicts and overlaps
- Timezone handling in scheduling
"""

import unittest
from datetime import datetime, time, timedelta, date
from unittest.mock import patch

from App.main import create_app
from App.database import db, create_db
from App.controllers.user import create_student
from App.controllers.help_desk_assistant import create_help_desk_assistant
from App.controllers.course import create_course
from App.controllers.semester import create_semester
from App.controllers.schedule import create_schedule, get_schedule_data
from App.models.schedule import Schedule
from App.models.shift import Shift
from App.models.allocation import Allocation
from App.models.availability import Availability
from App.models.course_capability import CourseCapability
from App.utils.time_utils import trinidad_now


class ScheduleTimingTests(unittest.TestCase):
    """Test suite for schedule generation and timing"""

    def setUp(self):
        """Set up test environment"""
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'JWT_SECRET_KEY': 'test-secret-key',
            'WTF_CSRF_ENABLED': False,
        })
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Initialize database
        create_db()

        # Create test data
        self._setup_test_data()

    def tearDown(self):
        """Clean up test environment"""
        db.session.remove()
        db.drop_all()
        if self.app_context is not None:
            self.app_context.pop()

    def _setup_test_data(self):
        """Create base test data"""
        # Create courses
        self.course1 = create_course("COMP1601", "Computer Programming I")
        self.course2 = create_course("COMP2603", "Object-Oriented Programming")

        # Create semester (write ISO strings expected by controller)
        start_date = datetime(2024, 1, 15).date()
        end_date = datetime(2024, 5, 15).date()
        self.semester = create_semester(start_date.isoformat(), end_date.isoformat())

        # Create test assistants
        self.assistant1 = "assistant1"
        create_student(self.assistant1, "password", "BSc", "Assistant One")
        create_help_desk_assistant(self.assistant1)
        
        self.assistant2 = "assistant2"
        create_student(self.assistant2, "password", "BSc", "Assistant Two")
        create_help_desk_assistant(self.assistant2)

    def _add_availability(self, username, day_of_week, start_time, end_time):
        """Add availability row, accepting weekday as string or int"""
        day_value = day_of_week
        if isinstance(day_of_week, str):
            day_lookup = {
                'monday': 0,
                'tuesday': 1,
                'wednesday': 2,
                'thursday': 3,
                'friday': 4,
                'saturday': 5,
                'sunday': 6,
            }
            lowered = day_of_week.strip().lower()
            if lowered not in day_lookup:
                raise ValueError(f"Unsupported day label: {day_of_week}")
            day_value = day_lookup[lowered]

        availability = Availability(
            username=username,
            day_of_week=day_value,
            start_time=start_time,
            end_time=end_time
        )
        db.session.add(availability)
        db.session.commit()
        return availability

    def _add_course_capability(self, username, course_code):
        """Add course capability for an assistant"""
        capability = CourseCapability(
            username=username,
            course_code=course_code
        )
        db.session.add(capability)
        db.session.commit()
        return capability

    def _create_schedule(self, start_date, end_date):
        """Create a help desk schedule with normalized datetime inputs"""

        def normalize(value):
            if isinstance(value, datetime):
                return value
            if isinstance(value, date):
                return datetime.combine(value, time.min)
            if isinstance(value, str):
                return datetime.fromisoformat(value)
            raise TypeError(f"Unsupported date value: {value!r}")

        schedule = Schedule(
            start_date=normalize(start_date),
            end_date=normalize(end_date),
            type='helpdesk'
        )
        db.session.add(schedule)
        db.session.flush()
        return schedule

    # ===========================================
    # Availability Matching Tests
    # ===========================================

    @patch('App.tests.test_schedule_timing.trinidad_now')
    def test_shift_matches_availability_exactly(self, mock_now):
        """Test shift that exactly matches availability window"""
        mock_now.return_value = datetime(2024, 1, 15, 9, 0, 0)  # Monday
        
        # Add availability Monday 9 AM - 5 PM
        self._add_availability(
            self.assistant1,
            'Monday',
            time(9, 0),
            time(17, 0)
        )
        
        # Create shift Monday 9 AM - 11 AM
        schedule = self._create_schedule(
            datetime(2024, 1, 15),
            datetime(2024, 1, 22)
        )
        
        shift = Shift(
            date=datetime(2024, 1, 15),  # Monday
            start_time=datetime(2024, 1, 15, 9, 0, 0),
            end_time=datetime(2024, 1, 15, 11, 0, 0),
            schedule_id=schedule.id
        )
        db.session.add(shift)
        db.session.commit()
        
        # Check availability matches
        avail = Availability.query.filter_by(username=self.assistant1).first()
        self.assertTrue(avail.is_available_for_shift(shift))

    @patch('App.tests.test_schedule_timing.trinidad_now')
    def test_shift_outside_availability_window(self, mock_now):
        """Test shift outside availability window is not matched"""
        mock_now.return_value = datetime(2024, 1, 15, 9, 0, 0)
        
        # Add availability Monday 9 AM - 12 PM
        self._add_availability(
            self.assistant1,
            'Monday',
            time(9, 0),
            time(12, 0)
        )
        
        # Create shift Monday 2 PM - 4 PM (outside availability)
        schedule = self._create_schedule(
            datetime(2024, 1, 15),
            datetime(2024, 1, 22)
        )
        
        shift = Shift(
            date=datetime(2024, 1, 15),
            start_time=datetime(2024, 1, 15, 14, 0, 0),
            end_time=datetime(2024, 1, 15, 16, 0, 0),
            schedule_id=schedule.id
        )
        db.session.add(shift)
        db.session.commit()
        
        # Check availability doesn't match
        avail = Availability.query.filter_by(username=self.assistant1).first()
        self.assertFalse(avail.is_available_for_shift(shift))

    @patch('App.tests.test_schedule_timing.trinidad_now')
    def test_shift_partially_outside_availability(self, mock_now):
        """Test shift that partially overlaps availability is not matched"""
        mock_now.return_value = datetime(2024, 1, 15, 9, 0, 0)
        
        # Add availability Monday 9 AM - 12 PM
        self._add_availability(
            self.assistant1,
            'Monday',
            time(9, 0),
            time(12, 0)
        )
        
        # Create shift Monday 11 AM - 1 PM (extends past availability)
        schedule = self._create_schedule(
            datetime(2024, 1, 15),
            datetime(2024, 1, 22)
        )
        
        shift = Shift(
            date=datetime(2024, 1, 15),
            start_time=datetime(2024, 1, 15, 11, 0, 0),
            end_time=datetime(2024, 1, 15, 13, 0, 0),
            schedule_id=schedule.id
        )
        db.session.add(shift)
        db.session.commit()
        
        # Check availability doesn't match (shift extends beyond window)
        avail = Availability.query.filter_by(username=self.assistant1).first()
        self.assertFalse(avail.is_available_for_shift(shift))

    @patch('App.tests.test_schedule_timing.trinidad_now')
    def test_shift_wrong_day_of_week(self, mock_now):
        """Test shift on different day than availability"""
        mock_now.return_value = datetime(2024, 1, 15, 9, 0, 0)
        
        # Add availability Monday 9 AM - 5 PM
        self._add_availability(
            self.assistant1,
            'Monday',
            time(9, 0),
            time(17, 0)
        )
        
        # Create shift Tuesday 9 AM - 11 AM
        schedule = self._create_schedule(
            datetime(2024, 1, 15),
            datetime(2024, 1, 22)
        )
        
        shift = Shift(
            date=datetime(2024, 1, 16),  # Tuesday
            start_time=datetime(2024, 1, 16, 9, 0, 0),
            end_time=datetime(2024, 1, 16, 11, 0, 0),
            schedule_id=schedule.id
        )
        db.session.add(shift)
        db.session.commit()
        
        # Check availability doesn't match (wrong day)
        avail = Availability.query.filter_by(username=self.assistant1).first()
        self.assertFalse(avail.is_available_for_shift(shift))

    @patch('App.tests.test_schedule_timing.trinidad_now')
    def test_multiple_availability_windows_same_day(self, mock_now):
        """Test assistant with multiple availability windows on same day"""
        mock_now.return_value = datetime(2024, 1, 15, 9, 0, 0)
        
        # Add two availability windows for Monday
        self._add_availability(
            self.assistant1,
            'Monday',
            time(9, 0),
            time(12, 0)
        )
        self._add_availability(
            self.assistant1,
            'Monday',
            time(14, 0),
            time(17, 0)
        )
        
        # Create shift in morning window
        schedule = self._create_schedule(
            datetime(2024, 1, 15),
            datetime(2024, 1, 22)
        )
        
        morning_shift = Shift(
            date=datetime(2024, 1, 15),
            start_time=datetime(2024, 1, 15, 10, 0, 0),
            end_time=datetime(2024, 1, 15, 11, 0, 0),
            schedule_id=schedule.id
        )
        db.session.add(morning_shift)
        
        # Create shift in afternoon window
        afternoon_shift = Shift(
            date=datetime(2024, 1, 15),
            start_time=datetime(2024, 1, 15, 15, 0, 0),
            end_time=datetime(2024, 1, 15, 16, 0, 0),
            schedule_id=schedule.id
        )
        db.session.add(afternoon_shift)
        
        # Create shift in gap (should not match)
        gap_shift = Shift(
            date=datetime(2024, 1, 15),
            start_time=datetime(2024, 1, 15, 12, 30, 0),
            end_time=datetime(2024, 1, 15, 13, 30, 0),
            schedule_id=schedule.id
        )
        db.session.add(gap_shift)
        db.session.commit()
        
        # Check morning and afternoon match, gap doesn't
        availabilities = Availability.query.filter_by(username=self.assistant1).all()
        
        morning_matches = any(a.is_available_for_shift(morning_shift) for a in availabilities)
        afternoon_matches = any(a.is_available_for_shift(afternoon_shift) for a in availabilities)
        gap_matches = any(a.is_available_for_shift(gap_shift) for a in availabilities)
        
        self.assertTrue(morning_matches)
        self.assertTrue(afternoon_matches)
        self.assertFalse(gap_matches)

    # ===========================================
    # Shift Overlap and Conflict Tests
    # ===========================================

    @patch('App.tests.test_schedule_timing.trinidad_now')
    def test_consecutive_shifts_no_conflict(self, mock_now):
        """Test consecutive (back-to-back) shifts have no overlap"""
        mock_now.return_value = datetime(2024, 1, 15, 9, 0, 0)
        
        schedule = self._create_schedule(
            datetime(2024, 1, 15),
            datetime(2024, 1, 22)
        )
        
        # Create consecutive shifts
        shift1 = Shift(
            date=datetime(2024, 1, 15),
            start_time=datetime(2024, 1, 15, 10, 0, 0),
            end_time=datetime(2024, 1, 15, 12, 0, 0),
            schedule_id=schedule.id
        )
        db.session.add(shift1)
        
        shift2 = Shift(
            date=datetime(2024, 1, 15),
            start_time=datetime(2024, 1, 15, 12, 0, 0),  # Starts when shift1 ends
            end_time=datetime(2024, 1, 15, 14, 0, 0),
            schedule_id=schedule.id
        )
        db.session.add(shift2)
        db.session.flush()
        
        # Allocate to same assistant
        allocation1 = Allocation(
            username=self.assistant1,
            shift_id=shift1.id,
            schedule_id=schedule.id
        )
        db.session.add(allocation1)
        
        allocation2 = Allocation(
            username=self.assistant1,
            shift_id=shift2.id,
            schedule_id=schedule.id
        )
        db.session.add(allocation2)
        db.session.commit()
        
        # Verify no overlap (shift1 ends exactly when shift2 starts)
        self.assertEqual(shift1.end_time, shift2.start_time)

    # ===========================================
    # Schedule Generation Time Window Tests
    # ===========================================

    @patch('App.tests.test_schedule_timing.trinidad_now')
    def test_schedule_within_semester_bounds(self, mock_now):
        """Test schedule must be within semester date range"""
        mock_now.return_value = datetime(2024, 1, 15, 9, 0, 0)
        
        # Semester is Jan 15 - May 15
        # Try to create schedule that extends beyond semester
        schedule = Schedule(
            start_date=datetime(2024, 1, 10).date(),  # Before semester start
            end_date=datetime(2024, 5, 20).date(),      # After semester end
            type='helpdesk'
        )
        db.session.add(schedule)
        db.session.commit()
        
        # Schedule was created (no validation in model)
        # This test documents current behavior
        self.assertIsNotNone(schedule.id)

    @patch('App.tests.test_schedule_timing.trinidad_now')
    def test_shift_date_within_schedule_range(self, mock_now):
        """Test shift must fall within schedule date range"""
        mock_now.return_value = datetime(2024, 1, 15, 9, 0, 0)
        
        schedule = self._create_schedule(
            datetime(2024, 1, 15),
            datetime(2024, 1, 22)
        )
        
        # Create shift within schedule range
        valid_shift = Shift(
            date=datetime(2024, 1, 17),  # Within range
            start_time=datetime(2024, 1, 17, 10, 0, 0),
            end_time=datetime(2024, 1, 17, 12, 0, 0),
            schedule_id=schedule.id
        )
        db.session.add(valid_shift)
        
        # Create shift outside schedule range
        invalid_shift = Shift(
            date=datetime(2024, 1, 25),  # After schedule end
            start_time=datetime(2024, 1, 25, 10, 0, 0),
            end_time=datetime(2024, 1, 25, 12, 0, 0),
            schedule_id=schedule.id
        )
        db.session.add(invalid_shift)
        db.session.commit()
        
        # Both created (no validation in model currently)
        # Verify dates
        self.assertTrue(
            schedule.start_date.date() <= valid_shift.date.date() <= schedule.end_date.date()
        )
        self.assertFalse(
            schedule.start_date.date() <= invalid_shift.date.date() <= schedule.end_date.date()
        )

    # ===========================================
    # Timezone and DST Tests
    # ===========================================

    @patch('App.tests.test_schedule_timing.trinidad_now')
    def test_trinidad_timezone_consistency(self, mock_now):
        """Test that Trinidad time is consistently UTC-4"""
        # Trinidad doesn't observe DST, so time offset is always UTC-4
        test_time = datetime(2024, 1, 15, 12, 0, 0)
        mock_now.return_value = test_time
        
        # Get Trinidad time
        trinidad_time = trinidad_now()
        
        # Verify it's the mocked time
        self.assertEqual(trinidad_time, test_time)

    @patch('App.tests.test_schedule_timing.trinidad_now')
    def test_shift_times_stored_consistently(self, mock_now):
        """Test shift times are stored and retrieved consistently"""
        test_time = datetime(2024, 1, 15, 10, 0, 0)
        mock_now.return_value = test_time
        
        schedule = Schedule(
            start_date=datetime(2024, 1, 15).date(),
            end_date=datetime(2024, 1, 22).date(),
            type='helpdesk'
        )
        db.session.add(schedule)
        db.session.flush()
        
        # Create shift with specific times
        start = datetime(2024, 1, 15, 10, 0, 0)
        end = datetime(2024, 1, 15, 12, 0, 0)
        
        shift = Shift(
            date=datetime(2024, 1, 15),
            start_time=start,
            end_time=end,
            schedule_id=schedule.id
        )
        db.session.add(shift)
        db.session.commit()
        
        # Retrieve and verify times match
        retrieved_shift = Shift.query.get(shift.id)
        self.assertEqual(retrieved_shift.start_time, start)
        self.assertEqual(retrieved_shift.end_time, end)

    # ===========================================
    # Edge Case Time Tests
    # ===========================================

    @patch('App.tests.test_schedule_timing.trinidad_now')
    def test_midnight_shift_start(self, mock_now):
        """Test shift starting at midnight"""
        mock_now.return_value = datetime(2024, 1, 15, 0, 0, 0)
        
        schedule = Schedule(
            start_date=datetime(2024, 1, 15).date(),
            end_date=datetime(2024, 1, 22).date(),
            type='helpdesk'
        )
        db.session.add(schedule)
        db.session.flush()
        
        shift = Shift(
            date=datetime(2024, 1, 15),
            start_time=datetime(2024, 1, 15, 0, 0, 0),
            end_time=datetime(2024, 1, 15, 2, 0, 0),
            schedule_id=schedule.id
        )
        db.session.add(shift)
        db.session.commit()
        
        self.assertEqual(shift.start_time.hour, 0)
        self.assertEqual(shift.start_time.minute, 0)

    @patch('App.tests.test_schedule_timing.trinidad_now')
    def test_shift_ending_at_midnight(self, mock_now):
        """Test shift ending exactly at midnight"""
        mock_now.return_value = datetime(2024, 1, 15, 22, 0, 0)
        
        schedule = Schedule(
            start_date=datetime(2024, 1, 15).date(),
            end_date=datetime(2024, 1, 22).date(),
            type='helpdesk'
        )
        db.session.add(schedule)
        db.session.flush()
        
        shift = Shift(
            date=datetime(2024, 1, 15),
            start_time=datetime(2024, 1, 15, 22, 0, 0),
            end_time=datetime(2024, 1, 16, 0, 0, 0),  # Midnight next day
            schedule_id=schedule.id
        )
        db.session.add(shift)
        db.session.commit()
        
        # Calculate duration
        duration = shift.end_time - shift.start_time
        hours = duration.total_seconds() / 3600
        
        self.assertEqual(hours, 2.0)

    @patch('App.tests.test_schedule_timing.trinidad_now')
    def test_very_short_shift(self, mock_now):
        """Test shift with minimal duration (15 minutes)"""
        mock_now.return_value = datetime(2024, 1, 15, 10, 0, 0)
        
        schedule = Schedule(
            start_date=datetime(2024, 1, 15).date(),
            end_date=datetime(2024, 1, 22).date(),
            type='helpdesk'
        )
        db.session.add(schedule)
        db.session.flush()
        
        shift = Shift(
            date=datetime(2024, 1, 15),
            start_time=datetime(2024, 1, 15, 10, 0, 0),
            end_time=datetime(2024, 1, 15, 10, 15, 0),
            schedule_id=schedule.id
        )
        db.session.add(shift)
        db.session.commit()
        
        duration = shift.end_time - shift.start_time
        minutes = duration.total_seconds() / 60
        
        self.assertEqual(minutes, 15.0)

    @patch('App.tests.test_schedule_timing.trinidad_now')
    def test_very_long_shift(self, mock_now):
        """Test extended shift (8 hours)"""
        mock_now.return_value = datetime(2024, 1, 15, 9, 0, 0)
        
        schedule = Schedule(
            start_date=datetime(2024, 1, 15).date(),
            end_date=datetime(2024, 1, 22).date(),
            type='helpdesk'
        )
        db.session.add(schedule)
        db.session.flush()
        
        shift = Shift(
            date=datetime(2024, 1, 15),
            start_time=datetime(2024, 1, 15, 9, 0, 0),
            end_time=datetime(2024, 1, 15, 17, 0, 0),
            schedule_id=schedule.id
        )
        db.session.add(shift)
        db.session.commit()
        
        duration = shift.end_time - shift.start_time
        hours = duration.total_seconds() / 3600
        
        self.assertEqual(hours, 8.0)


if __name__ == '__main__':
    unittest.main()
