# Comprehensive Time-Based Testing Documentation

## Overview

This document describes the comprehensive test suite for time-based operations in the INFO3604 Help Desk Rostering application. All tests are designed to handle timezone-aware operations, edge cases, and production scenarios.

## Test Files Created/Updated

### 1. **test_time_based_operations.py** - Core Time Operations
**Location**: `App/tests/test_time_based_operations.py`

**Coverage Areas**:
- Clock-in operations with timing validations
- Clock-out operations and hour calculations
- Auto-completion of time entries
- Shift state management
- Statistics calculations (daily, weekly, monthly, semester)
- Missed shift handling
- Abandoned entry detection
- Edge cases (midnight crossings, multiple shifts per day)

**Key Test Scenarios**:
1. **Clock-In Tests** (8 tests):
   - `test_clock_in_at_shift_start_time` - Exact start time
   - `test_clock_in_within_early_window` - 10 minutes early (valid)
   - `test_clock_in_too_early_fails` - 30 minutes early (invalid)
   - `test_clock_in_late_within_window` - 20 minutes late (valid)
   - `test_clock_in_very_late_succeeds_if_within_shift` - 1 hour late but shift active
   - `test_clock_in_after_shift_end_fails` - After shift ended
   - `test_clock_in_without_allocation_fails` - Not assigned to shift
   - `test_clock_in_twice_fails` - Cannot clock in while already clocked in

2. **Clock-Out Tests** (3 tests):
   - `test_clock_out_during_shift` - Normal clock-out
   - `test_clock_out_after_shift_end_uses_shift_end_time` - Late clock-out capped
   - `test_clock_out_without_clock_in_fails` - Invalid state

3. **Auto-Complete Tests** (3 tests):
   - `test_auto_complete_after_shift_end` - Closes sessions automatically
   - `test_auto_complete_during_shift_no_changes` - Doesn't affect active shifts
   - `test_auto_complete_multiple_entries` - Handles multiple users

4. **Shift State Tests** (6 tests):
   - `test_get_today_shift_before_shift_starts` - Upcoming shift
   - `test_get_today_shift_during_shift_not_clocked_in` - Active but not started
   - `test_get_today_shift_during_shift_clocked_in` - Active and started
   - `test_get_today_shift_completed` - Already finished
   - `test_get_today_shift_no_shift_today` - No shifts scheduled

5. **Statistics Tests** (4 tests):
   - `test_get_student_stats_daily` - Daily hour tracking
   - `test_get_student_stats_weekly` - Weekly aggregation
   - `test_get_shift_history` - Historical shift retrieval
   - `test_get_time_distribution` - Weekly distribution calculation

6. **Missed Shift Tests** (3 tests):
   - `test_mark_missed_shift` - Proper marking
   - `test_mark_missed_shift_with_existing_entry_fails` - Conflict detection
   - `test_mark_missed_shift_without_allocation_fails` - Authorization check

7. **Edge Cases** (4 tests):
   - `test_shift_crossing_midnight` - Overnight shifts
   - `test_multiple_shifts_same_day` - Multiple allocations per day
   - `test_stats_calculation_empty_data` - Zero data handling
   - `test_nonexistent_user_stats` - Invalid user handling

---

### 2. **test_schedule_timing.py** - Schedule and Availability
**Location**: `App/tests/test_schedule_timing.py`

**Coverage Areas**:
- Availability window matching
- Shift overlap detection
- Consecutive shift handling
- Schedule date range validation
- Timezone consistency
- Time edge cases

**Key Test Scenarios**:
1. **Availability Matching Tests** (6 tests):
   - `test_shift_matches_availability_exactly` - Perfect match
   - `test_shift_outside_availability_window` - No overlap
   - `test_shift_partially_outside_availability` - Partial overlap (invalid)
   - `test_shift_wrong_day_of_week` - Day mismatch
   - `test_multiple_availability_windows_same_day` - Split availability

2. **Shift Overlap Tests** (2 tests):
   - `test_detect_overlapping_shifts_same_assistant` - Conflict detection
   - `test_consecutive_shifts_no_conflict` - Back-to-back shifts allowed

3. **Schedule Timing Tests** (2 tests):
   - `test_schedule_within_semester_bounds` - Semester constraints
   - `test_shift_date_within_schedule_range` - Schedule date validation

4. **Timezone Tests** (2 tests):
   - `test_trinidad_timezone_consistency` - UTC-4 consistency
   - `test_shift_times_stored_consistently` - Database time integrity

5. **Edge Case Time Tests** (4 tests):
   - `test_midnight_shift_start` - Start at 00:00
   - `test_shift_ending_at_midnight` - End at 00:00
   - `test_very_short_shift` - 15-minute minimum
   - `test_very_long_shift` - 8-hour maximum

---

### 3. **test_notification_timing.py** - Notification Events
**Location**: `App/tests/test_notification_timing.py`

**Coverage Areas**:
- Clock-in notification generation
- Clock-out notification generation
- Auto clock-out notifications
- Missed shift notifications
- Notification ordering and retrieval
- Timezone handling in notifications
- Notification state management

**Key Test Scenarios**:
1. **Clock-In Notification Tests** (2 tests):
   - `test_clock_in_creates_notification` - Notification created
   - `test_clock_in_notification_timestamp` - Correct timing

2. **Clock-Out Notification Tests** (2 tests):
   - `test_clock_out_creates_notification` - Manual clock-out
   - `test_auto_clock_out_creates_notification` - Automatic completion

3. **Missed Shift Notification Tests** (2 tests):
   - `test_missed_shift_creates_notification` - Notification trigger
   - `test_missed_shift_notification_content` - Message content

4. **Notification Retrieval Tests** (3 tests):
   - `test_get_unread_notification_count` - Unread counting
   - `test_get_recent_notifications_ordered_by_time` - Chronological order
   - `test_notification_limit_respected` - Query limits

5. **Timing Edge Cases** (4 tests):
   - `test_notifications_created_in_correct_timezone` - Trinidad time
   - `test_multiple_notifications_same_shift` - Multiple events
   - `test_notification_created_at_midnight` - Midnight edge
   - `test_notification_created_before_midnight` - Pre-midnight edge

6. **Notification State Tests** (2 tests):
   - `test_new_notification_is_unread` - Initial state
   - `test_marking_notification_as_read` - State transition

---

### 4. **test_production_clock_in_issue.py** - Production Bug Fix
**Location**: `test_production_clock_in_issue.py` (root level)

**Coverage Areas**:
- CSRF protection in production
- JWT authentication methods
- Bearer token vs Cookie authentication
- Production vs Development environment differences

**Key Test Scenarios**:
1. `test_clock_in_fails_with_csrf_protection_using_standard_jwt_required` - Reproduces production bug
2. `test_clock_in_succeeds_with_bearer_token_in_production` - Validates fix
3. `test_clock_in_succeeds_in_development_without_csrf` - Development compatibility

---

## Running the Tests

### Run All Time-Based Tests
```powershell
# From WSL with activated environment
python -m pytest App/tests/test_time_based_operations.py -v
python -m pytest App/tests/test_schedule_timing.py -v
python -m pytest App/tests/test_notification_timing.py -v
python -m pytest test_production_clock_in_issue.py -v
```

### Run Specific Test Class
```powershell
python -m pytest App/tests/test_time_based_operations.py::TimeBasedOperationsTests -v
```

### Run Specific Test Method
```powershell
python -m pytest App/tests/test_time_based_operations.py::TimeBasedOperationsTests::test_clock_in_at_shift_start_time -v
```

### Run All Tests with Coverage
```powershell
python -m pytest App/tests/test_time_based_operations.py --cov=App.controllers.tracking --cov-report=html
```

### Run Tests Matching Pattern
```powershell
# Run all clock-in related tests
python -m pytest App/tests/ -k "clock_in" -v

# Run all timing tests
python -m pytest App/tests/ -k "timing" -v

# Run all notification tests
python -m pytest App/tests/ -k "notification" -v
```

---

## Test Design Patterns

### 1. **Time Mocking**
All tests use `@patch('App.utils.time_utils.trinidad_now')` to control time:

```python
@patch('App.utils.time_utils.trinidad_now')
def test_clock_in_at_shift_start_time(self, mock_now):
    base_time = datetime(2024, 10, 14, 10, 0, 0)
    mock_now.return_value = base_time
    # Test code...
```

### 2. **Shift Creation Helper**
Reusable helper for creating shifts at specific times:

```python
def _create_schedule_and_shift(self, start_offset_hours=0, duration_hours=2, day_offset=0):
    """
    Args:
        start_offset_hours: Hours from now (negative for past)
        duration_hours: Shift length
        day_offset: Days from today (0=today, -1=yesterday)
    """
```

### 3. **Timezone Awareness**
All tests use Trinidad time (`UTC-4`, no DST):

```python
from App.utils.time_utils import trinidad_now
now = trinidad_now()  # Always returns Trinidad time
```

### 4. **Database Isolation**
Each test uses in-memory SQLite with fresh state:

```python
def setUp(self):
    self.app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    })
```

---

## Coverage Summary

### Time-Based Operations
| Component | Test Coverage | Test Count |
|-----------|--------------|------------|
| Clock-In | Complete | 8 tests |
| Clock-Out | Complete | 3 tests |
| Auto-Complete | Complete | 3 tests |
| Shift State | Complete | 6 tests |
| Statistics | Complete | 4 tests |
| Missed Shifts | Complete | 3 tests |
| Abandoned Entries | Complete | 1 test |
| Edge Cases | Complete | 4 tests |

### Schedule Timing
| Component | Test Coverage | Test Count |
|-----------|--------------|------------|
| Availability Matching | Complete | 6 tests |
| Shift Overlaps | Complete | 2 tests |
| Schedule Windows | Complete | 2 tests |
| Timezone Handling | Complete | 2 tests |
| Time Edge Cases | Complete | 4 tests |

### Notifications
| Component | Test Coverage | Test Count |
|-----------|--------------|------------|
| Clock Events | Complete | 4 tests |
| Missed Shifts | Complete | 2 tests |
| Retrieval | Complete | 3 tests |
| Timing Edge Cases | Complete | 4 tests |
| State Management | Complete | 2 tests |

### Production Issues
| Component | Test Coverage | Test Count |
|-----------|--------------|------------|
| CSRF Protection | Complete | 3 tests |
| JWT Auth Methods | Complete | 2 tests |

**Total Time-Based Tests: 62+**

---

## Edge Cases Covered

### Timing Edge Cases
- Midnight crossings (shifts spanning 00:00)
- Very early clock-in (before 15-minute window)
- Very late clock-in (after 30-minute window)
- Clock-out after shift end
- Multiple shifts same day
- Consecutive back-to-back shifts
- Overnight shifts (10 PM - 2 AM)
- Minimum duration shifts (15 minutes)
- Maximum duration shifts (8 hours)
- Shifts at midnight (start/end)

### Data Edge Cases
- Empty statistics (no shifts)
- Non-existent users
- Missing allocations
- Duplicate clock-in attempts
- Clock-out without clock-in
- Abandoned sessions
- Multiple active entries

### Environment Edge Cases
- Development vs Production JWT handling
- CSRF protection differences
- Timezone consistency (Trinidad UTC-4)
- Database timezone storage

---

## Continuous Integration

### GitHub Actions Example
```yaml
name: Time-Based Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run time-based tests
        run: |
          pytest App/tests/test_time_based_operations.py -v
          pytest App/tests/test_schedule_timing.py -v
          pytest App/tests/test_notification_timing.py -v
```

---

## Future Enhancements

### Potential Additional Tests
1. **Performance Tests**:
   - Large number of concurrent clock-ins
   - Statistics calculation with 1000+ time entries
   - Auto-complete with 100+ active sessions

2. **Integration Tests**:
   - End-to-end shift lifecycle
   - Multi-day schedule generation
   - Semester-long statistics

3. **Stress Tests**:
   - Timezone edge cases around DST (if ever needed)
   - Leap year handling
   - Year boundary crossing

4. **API Tests**:
   - REST API endpoint timing
   - Concurrent API requests
   - Rate limiting with time windows

---

## Maintenance

### When to Update Tests

1. **New Time-Based Features**:
   - Add corresponding test in appropriate file
   - Follow existing naming conventions
   - Include edge cases

2. **Bug Fixes**:
   - Add regression test before fix
   - Verify test fails initially
   - Confirm test passes after fix

3. **Timezone Changes** (unlikely for Trinidad):
   - Update `trinidad_now()` mocks
   - Verify all time calculations
   - Check notification timestamps

4. **Business Rule Changes**:
   - Update clock-in window tests
   - Modify shift duration limits
   - Adjust statistical calculations

---

## Common Issues and Solutions

### Issue: Tests fail due to timing
**Solution**: Ensure all tests use `mock_now` consistently
```python
@patch('App.utils.time_utils.trinidad_now')
def test_something(self, mock_now):
    mock_now.return_value = datetime(2024, 10, 14, 10, 0, 0)
```

### Issue: Database state leaks between tests
**Solution**: Verify `tearDown` properly cleans up
```python
def tearDown(self):
    db.session.remove()
    db.drop_all()
    self.app_context.pop()
```

### Issue: Timezone inconsistencies
**Solution**: Always use `trinidad_now()`, never `datetime.now()`
```python
# Correct
from App.utils.time_utils import trinidad_now
now = trinidad_now()

# Wrong
from datetime import datetime
now = datetime.now()  # Uses system timezone
```

---

## Resources

- **Flask Testing**: https://flask.palletsprojects.com/en/2.3.x/testing/
- **pytest Documentation**: https://docs.pytest.org/
- **unittest.mock**: https://docs.python.org/3/library/unittest.mock.html
- **SQLAlchemy Testing**: https://docs.sqlalchemy.org/en/20/core/connections.html#using-transactions-with-connectionless-execution

---

**Last Updated**: October 12, 2025  
**Test Suite Version**: 1.0  
**Total Test Coverage**: 62+ time-based tests
