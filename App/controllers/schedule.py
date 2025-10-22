from datetime import datetime, timedelta, date, time
from flask import jsonify, render_template, url_for
from ortools.sat.python import cp_model
import logging, csv, random
from sqlalchemy import text, and_, func, select
from typing import Any, Union, Optional

# Try to import SQLAlchemy ORM functions with fallback for older versions
try:
    from sqlalchemy.orm import selectinload, joinedload
    EAGER_LOADING_AVAILABLE = True
except ImportError:
    # Fallback for older SQLAlchemy versions
    try:
        from sqlalchemy.orm import subqueryload as selectinload, joinedload
        EAGER_LOADING_AVAILABLE = True
    except ImportError:
        selectinload = None
        joinedload = None
        EAGER_LOADING_AVAILABLE = False

from App.models import (
    Schedule, Shift, Student, HelpDeskAssistant, 
    CourseCapability, Availability, 
    Allocation, Course
)
from App.database import db
from App.controllers.course import create_course, get_all_courses
from App.controllers.lab_assistant import *
from App.controllers.notification import notify_schedule_published
from App.controllers.shift import create_shift
from App.utils.time_utils import trinidad_now, convert_to_trinidad_time
from weasyprint import HTML, CSS
import tempfile
import os
import time as time_module
from functools import wraps
from App.utils.performance_monitor import (
    performance_monitor, 
    database_transaction_context,
    structured_logger,
    query_profiler
)


logger = logging.getLogger(__name__)

# Using centralized performance monitoring from utils

def _to_datetime_start_of_day(d):
    """Normalize a date or datetime (or ISO string) to a datetime at 00:00:00."""
    if isinstance(d, datetime):
        return d.replace(hour=0, minute=0, second=0, microsecond=0)
    if isinstance(d, date):
        return datetime(d.year, d.month, d.day)
    if isinstance(d, str):
        try:
            parsed = datetime.fromisoformat(d)
            # If a pure date string (YYYY-MM-DD) ends up as datetime at 00:00
            return parsed.replace(hour=0, minute=0, second=0, microsecond=0)
        except Exception:
            return trinidad_now().replace(hour=0, minute=0, second=0, microsecond=0)
    return trinidad_now().replace(hour=0, minute=0, second=0, microsecond=0)

def get_published_schedules():
    """Return all published schedules ordered by end_date descending."""
    try:
        return Schedule.query.filter_by(is_published=True).order_by(Schedule.end_date.desc()).all()
    except Exception as e:
        logger.error(f"Error fetching published schedules: {e}")
        return []

def get_current_published_schedule(today=None):
    """Return the schedule that is currently in effect (today within range).

    If none is active today, fall back to the most recent published schedule.
    """
    try:
        if today is None:
            today = trinidad_now().date()
        
        current = (
            Schedule.query
            .filter(
                Schedule.is_published == True,
                Schedule.start_date <= today,
                Schedule.end_date >= today
            )
            .order_by(Schedule.end_date.desc())
            .first()
        )
        if current:
            return current
        # Fallback: latest published schedule
        return (
            Schedule.query
            .filter_by(is_published=True)
            .order_by(Schedule.end_date.desc())
            .first()
        )
    except Exception as e:
        logger.error(f"Error fetching current published schedule: {e}")
        return None

def get_shifts_for_student(username, limit=None):
    """Get upcoming shifts for a specific student."""
    try:
        from datetime import datetime
        now = trinidad_now()
        
        # Get shifts via allocations for this student, future shifts only
        query = (
            db.session.query(Shift)
            .join(Allocation, Allocation.shift_id == Shift.id)
            .filter(
                Allocation.username == username,
                Shift.date >= now.date()
            )
            .order_by(Shift.date, Shift.start_time)
        )
        
        if limit:
            query = query.limit(limit)
            
        return query.all()
    except Exception as e:
        logger.error(f"Error fetching shifts for student {username}: {e}")
        return []

def get_shifts_for_student_in_range(username, start_date, end_date):
    """Get shifts for a student within a specific date range."""
    try:
        from datetime import datetime
        
        # Parse date strings if needed
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date).date()
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date).date()
        
        # Get shifts via allocations for this student within date range
        shifts = (
            db.session.query(Shift)
            .join(Allocation, Allocation.shift_id == Shift.id)
            .filter(
                Allocation.username == username,
                Shift.date >= start_date,
                Shift.date <= end_date
            )
            .order_by(Shift.date, Shift.start_time)
            .all()
        )
        
        return shifts
    except Exception as e:
        logger.error(f"Error fetching shifts for student {username} in range {start_date}-{end_date}: {e}")
        return []


# Add debug function to check constraints before scheduling
def check_scheduling_feasibility():
    """
    Check if scheduling is feasible with current constraints
    
    Returns:
        Dictionary with feasibility information
    """
    try:
        # Count active assistants
        assistant_count = HelpDeskAssistant.query.filter_by(active=True).count()
        
        # Check if there are enough assistants
        if assistant_count < 2:
            return {
                "feasible": False,
                "message": f"Not enough active assistants: found {assistant_count}, minimum 2 needed"
            }
            
        # Check if assistants have availability data
        assistants_with_availability = 0
        assistants = HelpDeskAssistant.query.filter_by(active=True).all()
        for assistant in assistants:
            availability_count = Availability.query.filter_by(username=assistant.username).count()
            if availability_count > 0:
                assistants_with_availability += 1
                
        if assistants_with_availability < 2:
            return {
                "feasible": False,
                "message": f"Only {assistants_with_availability} assistants have availability data"
            }
            
        # Check if assistants have course capabilities
        assistants_with_capabilities = 0
        for assistant in assistants:
            capability_count = CourseCapability.query.filter_by(assistant_username=assistant.username).count()
            if capability_count > 0:
                assistants_with_capabilities += 1
                
        if assistants_with_capabilities < 2:
            return {
                "feasible": False,
                "message": f"Only {assistants_with_capabilities} assistants have course capabilities"
            }
            
        return {
            "feasible": True,
            "message": "Scheduling appears feasible",
            "stats": {
                "assistant_count": assistant_count,
                "assistants_with_availability": assistants_with_availability,
                "assistants_with_capabilities": assistants_with_capabilities
            }
        }
    except Exception as e:
        return {
            "feasible": False,
            "message": f"Error checking feasibility: {str(e)}"
        }

@performance_monitor("generate_help_desk_schedule", log_slow_threshold=2.0)
def generate_help_desk_schedule(start_date=None, end_date=None, **generation_options):
    """
    Generate a help desk schedule with flexible date range
    
    Args:
        start_date: The start date for this schedule (datetime object)
        end_date: The end date for this schedule (datetime object)
    
    Returns:
        A dictionary with the schedule information
    """
    # First check if scheduling is feasible
    feasibility = check_scheduling_feasibility()
    if not feasibility["feasible"]:
        logger.warning(f"Schedule generation may fail: {feasibility['message']}")
        # We'll continue anyway but log the warning
    with database_transaction_context("help_desk_schedule_generation"):
        # Normalize inputs to datetimes at start of day
        if start_date is None:
            start_date = trinidad_now().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = _to_datetime_start_of_day(start_date)

        if end_date is None:
            # Get the end of the current week (Friday)
            days_to_friday = 4 - start_date.weekday()  # 4 = Friday
            if days_to_friday < 0:  # If today is already past Friday
                days_to_friday += 7  # Go to next Friday
            end_date = start_date + timedelta(days=days_to_friday)
        else:
            end_date = _to_datetime_start_of_day(end_date)
        
        # Check if we're scheduling for a full week or partial week
        is_full_week = start_date.weekday() == 0 and (end_date - start_date).days >= 4
        generation_payload = {k: v for k, v in generation_options.items() if v is not None}
        
        structured_logger.info(
            "Starting help desk schedule generation",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            is_full_week=is_full_week,
            generation_options=generation_payload
        )
        
        # Get or create the main schedule
        schedule = get_schedule(1, start_date, end_date, 'helpdesk')
        
        # Clear existing shifts for the date range
        clear_shifts_in_range(schedule.id, start_date, end_date)
        
        # Get all courses from the standardized list
        all_courses = get_all_courses()
        if not all_courses:
            # Create standard courses if none exist
            with open('sample/courses.csv', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    create_course(row['code'], row['name'])
            all_courses = get_all_courses()
            logger.info(f"Created {len(all_courses)} standard courses")
        
        # Generate shifts for the schedule (only for the specified date range)
        shifts = []
        current_date = start_date

        while current_date <= end_date:
            # Skip weekends (day_of_week >= 5)
            if current_date.weekday() < 5:  # 0=Monday through 4=Friday
                # Generate hourly shifts for this day (9am-5pm)
                for hour in range(9, 17):  # 9am through 4pm
                    base_date = current_date.date() if isinstance(current_date, datetime) else current_date
                    shift_start = datetime.combine(base_date, time(0, 0)) + timedelta(hours=hour)
                    shift_end = shift_start + timedelta(hours=1)
                    
                    shift = Shift(current_date, shift_start, shift_end, schedule.id)
                    db.session.add(shift)
                    db.session.flush()  # Get the shift ID
                    shifts.append(shift)
                    
                    # Default requirement is 2 tutors per course
                    for course in all_courses:
                        try:
                            add_course_demand_to_shift(shift.id, course.code, 2, 2)
                        except Exception as e:
                            logger.error(f"Error adding course demand for {course.code} to shift {shift.id}: {str(e)}")
                            # Continue with other courses
            
            # Move to the next day
            current_date += timedelta(days=1)
        
        assistants_query = db.session.query(HelpDeskAssistant).filter_by(active=True)

        if EAGER_LOADING_AVAILABLE and selectinload:
            assistants_query = assistants_query.options(
                selectinload(HelpDeskAssistant.course_capabilities),
                selectinload(HelpDeskAssistant.student).selectinload(Student.availabilities)
            )

        assistants = assistants_query.all()
        
        if not assistants:
            raise Exception("No active assistants found")
            
        # For debugging: log how many assistants we found
        logger.info(f"Found {len(assistants)} active assistants with eager-loaded capabilities and availability")
        
        # Now let's use the optimized model from the paper to generate the schedule
        # We'll use the CP-SAT solver
        model = cp_model.CpModel()
        
        # --- Data Preparation ---
        # i = staff index (i = 1 · · · I)
        # j = shift index (j = 1 · · · J)
        # k = course index (k = 1 · · · K)
        
        # Map indexes for reference
        staff_by_index = {i: assistant for i, assistant in enumerate(assistants)}
        shift_by_index = {j: shift for j, shift in enumerate(shifts)}
        course_by_index = {k: course for k, course in enumerate(all_courses)}
        
        I = len(assistants)  # Number of staff
        J = len(shifts)      # Number of shifts
        K = len(all_courses) # Number of courses
        
        logger.info(f"Generating schedule with {I} assistants, {J} shifts, and {K} courses")
        
        # --- Get availability and capability matrices ---
        # OPTIMIZATION: t_i,k = 1 if staff i can help with course k, 0 otherwise
        # Use pre-loaded course capabilities instead of separate queries
        t = {}
        for i in range(I):
            assistant = staff_by_index[i]
            # Use pre-loaded capabilities from eager loading
            can_help_with = set(cap.course_code for cap in assistant.course_capabilities)
            
            for k in range(K):
                course = course_by_index[k]
                t[i, k] = 1 if course.code in can_help_with else 0
        
        # OPTIMIZATION: a_i,j = 1 if staff i is available during shift j
        # Use pre-loaded availability data instead of individual queries
        a = {}
        for i in range(I):
            assistant = staff_by_index[i]
            for j in range(J):
                shift = shift_by_index[j]
                # Get student's availability for this day and time
                day_of_week = shift.date.weekday()  # 0=Monday, 4=Friday
                shift_start_time = shift.start_time.time()
                shift_end_time = shift.end_time.time()

                # Use pre-loaded availability records from eager loading via student relationship
                student_availabilities = assistant.student.availabilities if assistant.student else []
                availabilities = [
                    av for av in student_availabilities if av.day_of_week == day_of_week
                ]

                # Check if any availability slot covers this shift
                is_available = False
                for avail in availabilities:
                    if avail.start_time <= shift_start_time and avail.end_time >= shift_end_time:
                        is_available = True
                        break

                a[i, j] = 1 if is_available else 0
        
        # d_j,k = desired number of tutors with course k in shift j
        # w_j,k = weight for course k in shift j
        d = {}
        w = {}
        
        for j in range(J):
            shift = shift_by_index[j]
            # Get course demands for this shift
            demands = get_course_demands_for_shift(shift.id)
            
            # Log shift and its demands
            logger.debug(f"Shift {j} (ID: {shift.id}) has {len(demands)} course demands")
            
            # Build d_j,k and w_j,k dictionaries
            for k in range(K):
                course = course_by_index[k]
                
                # Default: 2 tutors required, weight = tutors_required
                d[j, k] = 2
                w[j, k] = 2
                
                # Find course-specific demands if they exist
                for demand in demands:
                    if demand['course_code'] == course.code:
                        d[j, k] = demand['tutors_required']
                        w[j, k] = demand['weight']
                        break
        
        # --- Variables ---
        # x_i,j = 1 if staff i is assigned to shift j, 0 otherwise
        x = {}
        for i in range(I):
            for j in range(J):
                x[i, j] = model.NewBoolVar(f'x_{i}_{j}')
        
        # --- Objective Function ---
        # Implementing the mathematical model from the PDF:
        # min ∑(j=1 to J) ∑(k=1 to K) (d_j,k - ∑(i=1 to I) x_i,j * t_i,k) * w_j,k
        objective_terms = []
        for j in range(J):
            for k in range(K):
                # Calculate the shortfall in coverage for each course in each shift
                assigned_tutors_for_course = []
                for i in range(I):
                    if t[i, k] == 1:  # Only consider if this tutor can teach this course
                        assigned_tutors_for_course.append(x[i, j])
                
                if assigned_tutors_for_course:  # Only add shortfall if any tutor can teach this course
                    shortfall = model.NewIntVar(0, d[j, k], f'shortfall_{j}_{k}')
                    model.Add(shortfall >= d[j, k] - sum(assigned_tutors_for_course))
                    
                    # Add weighted shortfall to the objective
                    objective_terms.append(shortfall * w[j, k])
        
        # Minimize the weighted shortfall across all shifts and courses
        model.Minimize(sum(objective_terms))
        
        # --- Constraints ---
        # Constraint 1 from the model: Σ(i) xi,j*ti,k ≤ dj,k for all j,k pairs
        # This ensures we don't exceed the desired number of tutors per course per shift
        for j in range(J):
            for k in range(K):
                tutors_for_course_in_shift = []
                for i in range(I):
                    if t[i, k] == 1:  # Only if this tutor can teach this course
                        tutors_for_course_in_shift.append(x[i, j])
                
                if tutors_for_course_in_shift:  # Only add constraint if any tutor can teach
                    model.Add(sum(tutors_for_course_in_shift) <= d[j, k])
        
        # Constraint 2 from the model: Σ(j) xi,j ≥ 4 for all i
        # Each tutor should have at least 4 shifts (or their minimum hours)
        for i in range(I):
            assistant = staff_by_index[i]
            min_hours = assistant.hours_minimum
            
            # If this is not a full week, scale the minimum hours
            if not is_full_week:
                days_in_range = sum(1 for d in range((end_date - start_date).days + 1) 
                                   if (start_date + timedelta(days=d)).weekday() < 5)
                scaling_factor = days_in_range / 5.0  # 5 weekdays in a full week
                min_hours = max(1, int(min_hours * scaling_factor))
            
            # Make this a soft constraint - add penalty if not met
            tutor_shifts = sum(x[i, j] for j in range(J))
            hours_shortfall = model.NewIntVar(0, min_hours, f'hours_shortfall_{i}')
            model.Add(hours_shortfall >= min_hours - tutor_shifts)
            objective_terms.append(hours_shortfall * 10)  # Weight of 10
        
        # Constraint 3 from the model: Σ(i) xi,j ≥ 2 for all j
        # Each shift must have at least 2 tutors
        for j in range(J):
            shift_tutors = sum(x[i, j] for i in range(I))
            
            # Enforce at least 2 tutors per shift as a soft constraint
            zero_tutors = model.NewBoolVar(f'zero_tutors_{j}')
            one_tutor = model.NewBoolVar(f'one_tutor_{j}')
            
            # Define the conditions
            model.Add(shift_tutors == 0).OnlyEnforceIf(zero_tutors)
            model.Add(shift_tutors == 1).OnlyEnforceIf(one_tutor)
            
            # Add penalties to the objective function
            objective_terms.append(zero_tutors * 100)  # Major penalty for no tutors
            objective_terms.append(one_tutor * 50)     # Penalty for just one tutor
            
            # Maximum 3 tutors per shift (new constraint)
            model.Add(shift_tutors <= 3)
        
        # Constraint 4 from the model: xi,j ≤ ai,j for all i
        # Tutors can only be assigned to shifts they are available for
        for i in range(I):
            for j in range(J):
                if a[i, j] == 0:  # If the tutor is not available
                    model.Add(x[i, j] == 0)
        
        # Get schedule statistics
        problem_stats = {
            "assistants": I,
            "shifts": J,
            "courses": K,
            "total_shift_slots": I * J,  # theoretical maximum if everyone worked every shift
            "total_course_capacity_needed": sum(d[j, k] for j in range(J) for k in range(K)),
            "total_availability": sum(a[i, j] for i in range(I) for j in range(J)),
            "coverage_ratio": sum(a[i, j] for i in range(I) for j in range(J)) / (I * J) if I * J > 0 else 0
        }
        logger.info(f"Schedule statistics: {problem_stats}")
        
        # --- Solve the Model ---
        solver = cp_model.CpSolver()
        # Allow time limit to be configured via app config (default 60s)
        try:
            from flask import current_app
            time_limit = float(current_app.config.get('CP_SAT_TIME_LIMIT', 60))
        except Exception:
            # Fallback when not running in an app context
            time_limit = 60.0
        solver.parameters.max_time_in_seconds = float(time_limit)
        solver.parameters.num_search_workers = 8  # Use more worker threads
        solver.parameters.log_search_progress = True  # Log search progress
        status = solver.Solve(model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            # Clear existing allocations for these shifts
            clear_allocations_for_shifts(shifts)
            new_allocations = []
            assignment_count = 0
            
            for i in range(I):
                for j in range(J):
                    if solver.Value(x[i, j]) == 1:
                        assistant = staff_by_index[i]
                        shift = shift_by_index[j]
                        
                        allocation = Allocation(assistant.username, shift.id, schedule.id)
                        new_allocations.append(allocation)
                        assignment_count += 1
                        
                        logger.debug(f"Assigned {assistant.username} to shift {shift.id}")
            
            # Batch insert all allocations at once
            if new_allocations:
                db.session.add_all(new_allocations)
                logger.info(f"Created {len(new_allocations)} allocations in batch")
            # Transaction will be committed by decorator
            logger.info(f"Schedule generated successfully with status: {status}, {assignment_count} assignments")
            
            return {
                "status": "success",
                "schedule_id": schedule.id,
                "message": "Schedule generated successfully",
                "details": {
                    "start_date": start_date.strftime('%Y-%m-%d'),
                    "end_date": end_date.strftime('%Y-%m-%d'),
                    "is_full_week": is_full_week,
                    "shifts_created": len(shifts),
                    "assignments_created": assignment_count,
                    "objective_value": solver.ObjectiveValue(),
                    "generation_options": generation_payload
                }
            }
        else:
            message = 'No solution found.'
            if status == cp_model.INFEASIBLE:
                message = 'Problem is infeasible with current constraints.'
            elif status == cp_model.MODEL_INVALID:
                message = 'Model is invalid.'
            
            logger.error(f"Failed to generate schedule: {message}")
            
            return {
                "status": "error",
                "message": message
            }
    
def get_schedule(id, start_date, end_date, type='helpdesk'):
    """Get or create the main schedule object based on type"""
    # Use different IDs for different schedule types
    schedule_id = 1 if type == 'helpdesk' else 2
    
    schedule = Schedule.query.filter_by(id=schedule_id, type=type).first()
    
    if not schedule:
        # Create a new schedule
        schedule = create_schedule(schedule_id, start_date, end_date, type)
    else:
        # Update the existing schedule's date range
        schedule.start_date = start_date
        schedule.end_date = end_date
        db.session.add(schedule)
        db.session.flush()
    return schedule


def create_schedule(id, start_date, end_date, type):
    new_schedule = Schedule(id=id, start_date=start_date, end_date=end_date, type=type)
    db.session.add(new_schedule)
    db.session.commit()
    return new_schedule


def clear_shifts_in_range(schedule_id, start_date, end_date):
    """Clear existing shifts in the date range"""
    # Find shifts in this date range
    shifts_to_delete = Shift.query.filter(
        Shift.schedule_id == schedule_id,
        Shift.date >= start_date,
        Shift.date <= end_date
    ).all()
    
    # Delete allocations for these shifts
    for shift in shifts_to_delete:
        Allocation.query.filter_by(shift_id=shift.id).delete()
        db.session.execute(
            text("DELETE FROM shift_course_demand WHERE shift_id = :shift_id"),
            {'shift_id': shift.id}
        )
    
    # Now delete the shifts themselves
    for shift in shifts_to_delete:
        db.session.delete(shift)
    
    db.session.flush()


def clear_allocations_for_shifts(shifts):
    """Clear allocations for the given shifts"""
    for shift in shifts:
        Allocation.query.filter_by(shift_id=shift.id).delete()
    
    db.session.flush()


def add_course_demand_to_shift(shift_id, course_code, tutors_required=2, weight=None):
    """Add course demand for a shift using raw SQL with text()"""
    # If weight is not provided, use tutors_required as the weight
    if weight is None:
        weight = tutors_required
    db.session.execute(
        text("INSERT INTO shift_course_demand (shift_id, course_code, tutors_required, weight) VALUES (:shift_id, :course_code, :tutors_required, :weight)"),
        {
            'shift_id': shift_id, 
            'course_code': course_code, 
            'tutors_required': tutors_required, 
            'weight': weight
        }
    )
    db.session.flush()


def get_course_demands_for_shift(shift_id):

    try:
        result = db.session.execute(
            text("SELECT course_code, tutors_required, weight FROM shift_course_demand WHERE shift_id = :shift_id"),
            {'shift_id': shift_id}
        )
        
        # Convert the result to a list of dictionaries
        demands = []
        for row in result:
            demands.append({
                'course_code': row[0],
                'tutors_required': row[1],
                'weight': row[2]
            })
        
        return demands
    except Exception as e:
        logger.error(f"Error getting course demands for shift {shift_id}: {e}")
        return []  # Return empty list on error


def sync_schedule_data():

    try:
        # The main schedule is stored with ID 1
        schedule = Schedule.query.get(1)
        
        if not schedule:
            logger.info("No main schedule exists yet")
            return False
        
        # Get all shifts for this schedule
        shifts = Shift.query.filter_by(schedule_id=schedule.id).all()
        
        if not shifts:
            logger.info("Schedule exists but has no shifts")
            return False
        
        # Make sure all shifts have proper allocation records
        shift_ids = [shift.id for shift in shifts]
        allocations = Allocation.query.filter(Allocation.shift_id.in_(shift_ids)).all()
        
        # Log counts for debugging
        logger.info(f"Schedule {schedule.id} has {len(shifts)} shifts and {len(allocations)} allocations")
        
        # Count allocations per shift
        allocation_counts = {}
        for allocation in allocations:
            allocation_counts[allocation.shift_id] = allocation_counts.get(allocation.shift_id, 0) + 1
        
        shifts_without_allocations = [shift.id for shift in shifts if allocation_counts.get(shift.id, 0) == 0]
        if shifts_without_allocations:
            logger.warning(f"Found {len(shifts_without_allocations)} shifts without allocations")
        
        # Ensure all allocations have valid student assistants
        for allocation in allocations:
            student = Student.query.get(allocation.username)
            if not student:
                logger.warning(f"Allocation {allocation.id} references non-existent student {allocation.username}")
        
        return True    
    except Exception as e:
        logger.error(f"Error syncing schedule data: {e}")
        return False


def publish_and_notify(schedule_id):

    try:
        # First publish the schedule
        result = publish_schedule(schedule_id)
        
        if result.get('status') != 'success':
            return result
            
        # Then sync the data
        sync_success = sync_schedule_data()
        
        if not sync_success:
            logger.warning("Schedule published but data sync failed or was not necessary")
        
        return {
            "status": "success",
            "message": "Schedule published and notifications sent",
            "sync_status": "success" if sync_success else "warning"
        }        
    except Exception as e:
        logger.error(f"Error publishing and notifying: {e}")
        return {
            "status": "error", 
            "message": f"Error: {str(e)}"
        }


def publish_schedule(schedule_id):
    """Publish a schedule and notify all assigned staff"""
    try:
        schedule = Schedule.query.get(schedule_id)
        if not schedule:
            return {"status": "error", "message": "Schedule not found"}
            
        if schedule.publish():
            # Get all unique students assigned to this schedule
            allocations = Allocation.query.filter_by(schedule_id=schedule_id).all()
            students = set(allocation.username for allocation in allocations)
            
            # Notify each student
            for username in students:
                notify_schedule_published(username)
                
            return {"status": "success", "message": "Schedule published and notifications sent"}
        else:
            return {"status": "error", "message": "Schedule is already published"}       
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_assistants_for_shift(shift_id):
    """Get all assistants assigned to a specific shift"""
    allocations = Allocation.query.filter_by(shift_id=shift_id).all()
    assistants = []
    
    for allocation in allocations:
        student = Student.query.get(allocation.username)
        if student:
            assistants.append({
                "username": student.username,
                "name": student.get_name(),
                "degree": student.degree
            })
    
    return assistants



def clear_schedule_by_id(schedule_id):
    try:
        # Get the schedule
        schedule = Schedule.query.get(schedule_id)
        
        if not schedule:
            return {
                "status": "success",
                "message": f"No schedule exists with ID {schedule_id} to clear"
            }
        
        # Perform deletions in the correct order to avoid foreign key constraint violations
        
        # 1. First delete all allocations for this schedule
        allocation_count = Allocation.query.filter_by(schedule_id=schedule_id).delete()
        
        # 2. Get all shift IDs for this schedule
        shifts = Shift.query.filter_by(schedule_id=schedule_id).all()
        shift_ids = [shift.id for shift in shifts]
        shift_count = len(shifts)
        
        # 3. Delete all shift course demands using raw SQL
        if shift_ids:
            # Convert list to comma-separated string for SQL IN clause
            shift_ids_str = ','.join(str(id) for id in shift_ids)
            db.session.execute(
                text(f"DELETE FROM shift_course_demand WHERE shift_id IN ({shift_ids_str})")
            )
        
        # 4. Delete all shifts for this schedule
        Shift.query.filter_by(schedule_id=schedule_id).delete()
        
        # 5. Reset schedule published status but keep the schedule record
        schedule.is_published = False
        db.session.add(schedule)
        
        # Commit all changes
        db.session.commit()
        
        # 6. Force database synchronization
        db.session.expire_all()
        
        logger.info(f"Schedule {schedule_id} cleared successfully: {shift_count} shifts and {allocation_count} allocations removed")
        
        return {
            "status": "success",
            "message": "Schedule cleared successfully",
            "details": {
                "schedule_id": schedule_id,
                "shifts_removed": shift_count,
                "allocations_removed": allocation_count
            }
        }   
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing schedule: {e}")
        return {
            "status": "error",
            "message": str(e)
        }



def clear_schedule():
    try:
        # Get the main schedule
        schedule = Schedule.query.get(1)
        
        if not schedule:
            return {
                "status": "success",
                "message": "No schedule exists to clear"
            }
        
        # Perform deletions in the correct order to avoid foreign key constraint violations
        
        # 1. First delete all allocations for this schedule
        allocation_count = Allocation.query.filter_by(schedule_id=schedule.id).delete()
        
        # 2. Get all shift IDs for this schedule
        shifts = Shift.query.filter_by(schedule_id=schedule.id).all()
        shift_ids = [shift.id for shift in shifts]
        shift_count = len(shifts)
        
        # 3. Delete all shift course demands using raw SQL
        if shift_ids:
            # Convert list to comma-separated string for SQL IN clause
            shift_ids_str = ','.join(str(id) for id in shift_ids)
            db.session.execute(
                text(f"DELETE FROM shift_course_demand WHERE shift_id IN ({shift_ids_str})")
            )
        
        # 4. Delete all shifts for this schedule
        Shift.query.filter_by(schedule_id=schedule.id).delete()
        
        # 5. Reset schedule published status but keep the schedule record
        schedule.is_published = False
        db.session.add(schedule)
        
        # Commit all changes
        db.session.commit()
        
        # 6. Force database synchronization
        db.session.expire_all()
        
        logger.info(f"Schedule cleared successfully: {shift_count} shifts and {allocation_count} allocations removed")
        
        return {
            "status": "success",
            "message": "Schedule cleared successfully",
            "details": {
                "shifts_removed": shift_count,
                "allocations_removed": allocation_count
            }
        }
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing schedule: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

@performance_monitor("get_schedule_data")
def get_schedule_data(schedule_id):
    """Optimized schedule data retrieval with eager loading to prevent N+1 queries"""
    try:
        if EAGER_LOADING_AVAILABLE and selectinload:
            schedule = (
                db.session.query(Schedule)
                .options(
                    selectinload(Schedule.shifts)
                    .selectinload(Shift.allocations)
                    .selectinload(Allocation.student)
                )
                .filter_by(id=schedule_id)
                .first()
            )
        else:
            # Fallback for older SQLAlchemy versions
            schedule = Schedule.query.filter_by(id=schedule_id).first()
        
        if not schedule:
            logger.error(f"No schedule found with ID {schedule_id}")
            return None
            
        # Determine schedule type
        schedule_type = getattr(schedule, 'type', 'helpdesk')
        if schedule_id == 2:
            schedule_type = 'lab'
        
        if EAGER_LOADING_AVAILABLE and selectinload:
            logger.info(f"Loaded schedule {schedule_id} with {len(schedule.shifts)} shifts using eager loading")
        else:
            logger.info(f"Loaded schedule {schedule_id} with {len(schedule.shifts)} shifts (eager loading not available)")
        
        # Format the schedule
        formatted_schedule = {
            "schedule_id": schedule.id,
            "date_range": f"{schedule.start_date.strftime('%d %b')} - {schedule.end_date.strftime('%d %b, %Y')}",
            "is_published": schedule.is_published,
            "type": schedule_type,
            "days": []
        }
        
        # Group shifts by day (optimized - all data already loaded)
        shifts_by_day = {}
        for shift in schedule.shifts:
            day_idx = shift.date.weekday()
            
            # Skip days outside expected range
            if schedule_type == 'helpdesk' and day_idx > 4:
                continue
            if schedule_type == 'lab' and day_idx > 5:
                continue
                
            if day_idx not in shifts_by_day:
                shifts_by_day[day_idx] = []
                
            assistants = []
            for allocation in shift.allocations:
                if allocation.student:
                    assistants.append({
                        "id": allocation.student.username,
                        "name": allocation.student.get_name()
                    })
            
            # Add shift to the day
            shifts_by_day[day_idx].append({
                "shift_id": shift.id,
                "time": f"{shift.start_time.strftime('%-I:%M %p')} - {shift.end_time.strftime('%-I:%M %p')}",
                "hour": shift.start_time.hour,
                "assistants": assistants
            })
        
        # Create days array
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        max_days = 6 if schedule_type == 'lab' else 5
        
        for day_idx in range(max_days):
            if day_idx >= len(day_names):
                continue
                
            day_date = schedule.start_date + timedelta(days=day_idx)
            day_shifts = shifts_by_day.get(day_idx, [])
            
            # Sort shifts by start time
            day_shifts.sort(key=lambda x: x["hour"])
            
            # Add this day to the days array
            formatted_schedule["days"].append({
                "day": day_names[day_idx],
                "date": day_date.strftime("%d %b"),
                "shifts": day_shifts
            })
        logger.info(f"Successfully formatted schedule data for {len(formatted_schedule['days'])} days")
        return formatted_schedule
    except Exception as e:
        logger.error(f"Error getting schedule data: {e}")
        import traceback
        traceback.print_exc()
        return None
    
@performance_monitor("get_current_schedule")
def get_current_schedule():
    """Get the current schedule with all shifts"""
    try:
        # Single query with eager loading to prevent N+1 queries
        schedule = (
            db.session.query(Schedule)
            .options(
                selectinload(Schedule.shifts)
                .selectinload(Shift.allocations)
                .selectinload(Allocation.student)
            )
            .filter_by(id=1)
            .first()
        )
        
        if not schedule:
            logger.info("No schedule found - returning empty template")
            # Instead of returning None, create an empty schedule template for UI
            return {
                "schedule_id": None,
                "date_range": "No schedule available",
                "is_published": False,
                "days": [
                    {
                        "day": day,
                        "date": "",
                        "shifts": [
                            {
                                "shift_id": None,
                                "time": f"{hour}:00 - {hour+1}:00",
                                "assistants": []
                            } for hour in range(9, 17)
                        ]
                    } for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                ]
            }
            
        logger.info(f"Loaded schedule {schedule.id} with {len(schedule.shifts)} shifts using eager loading")
        # Format the schedule for display using pre-loaded data
        shifts_by_day = {}
        for shift in schedule.shifts:
            day_idx = shift.date.weekday()  # 0=Monday, 6=Sunday
            if day_idx >= 5:  # Skip weekend shifts
                continue
                
            hour = shift.start_time.hour
            
            if day_idx not in shifts_by_day:
                shifts_by_day[day_idx] = {}
                
            # Build assistants from pre-loaded data instead of separate query
            assistants = []
            for allocation in shift.allocations:
                if allocation.student:  # Already loaded via eager loading
                    assistants.append({
                        "id": allocation.student.username,
                        "name": allocation.student.get_name(),
                        "degree": getattr(allocation.student, 'degree', 'N/A')
                    })
                
            shifts_by_day[day_idx][hour] = {
                "shift_id": shift.id,
                "time": shift.formatted_time(),
                "assistants": assistants
            }
        
        # Format into days array with shifts
        days = []
        for day_idx in range(5):  # Monday to Friday
            day_date = schedule.start_date + timedelta(days=day_idx) if schedule.start_date else trinidad_now()
            day_shifts = []
            
            if day_idx in shifts_by_day:
                for hour in range(9, 17):  # 9am to 4pm
                    if hour in shifts_by_day[day_idx]:
                        day_shifts.append(shifts_by_day[day_idx][hour])
                    else:
                        day_shifts.append({
                            "shift_id": None,
                            "time": f"{hour}:00 - {hour+1}:00",
                            "assistants": []
                        })
            
            days.append({
                "day": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"][day_idx],
                "date": day_date.strftime("%d %b"),
                "shifts": day_shifts
            })
        
        result = {
            "schedule_id": schedule.id,
            "date_range": f"{schedule.start_date.strftime('%d %b')} - {schedule.end_date.strftime('%d %b, %Y')}" if schedule.start_date and schedule.end_date else "Current Schedule",
            "is_published": schedule.is_published,
            "days": days
        }
        
        logger.info(f"Successfully formatted current schedule with {len(days)} days")
        return result
    except Exception as e:
        # Log the error
        logger.error(f"Error getting current schedule: {e}")
        import traceback
        traceback.print_exc()
        # Return an empty schedule template for UI
        return {
            "schedule_id": None,
            "date_range": "Error loading schedule",
            "is_published": False,
            "days": [
                {
                    "day": day,
                    "date": "",
                    "shifts": [
                        {
                            "shift_id": None,
                            "time": f"{hour}:00 - {hour+1}:00",
                            "assistants": []
                        } for hour in range(9, 17)
                    ]
                } for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            ]
        }


def generate_lab_schedule(start_date=None, end_date=None, **generation_options):
    try:
        model = cp_model.CpModel()
        
        # --- Variables ---
        
        """ Staff Index, i = 1 · · · I """        
        # Get all active lab assistants
        assistants = get_active_lab_assistants()
        if not assistants:
            db.session.rollback()
            return {"status": "error", "message": "No active assistants found"}
        
        staff_by_index = {i: assistant for i, assistant in enumerate(assistants)}
        I = len(assistants)
        
        if I == 0:
            return {"status": "error", "message": "No active lab assistants available for scheduling"}
        
        """ Shift Index, j = 1 · · · J """
        # Normalize inputs to datetimes at start of day
        if start_date is None:
            start_date = trinidad_now().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = _to_datetime_start_of_day(start_date)

        if end_date is None:
            # Get the end of the current week (Saturday)
            days_to_saturday = 5 - start_date.weekday()
            if days_to_saturday < 0:
                days_to_saturday += 7
            end_date = start_date + timedelta(days=days_to_saturday)
        else:
            end_date = _to_datetime_start_of_day(end_date)

        # Check if we're scheduling for a full week or partial week
        is_full_week = start_date.weekday() == 0 and (end_date - start_date).days >= 5
        generation_payload = {k: v for k, v in generation_options.items() if v is not None}

        structured_logger.info(
            "Starting lab schedule generation",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            is_full_week=is_full_week,
            generation_options=generation_payload
        )
        
        # Get or create the main schedule
        schedule = get_schedule(1, start_date, end_date, 'lab')  # Change type to 'lab'
        
        # Clear existing shifts for the date range
        clear_shifts_in_range(schedule.id, start_date, end_date)
        
        shifts = []
        current_date = start_date
        
        while current_date <= end_date:
            # Skip Sunday (day_of_week >= 6)
            if current_date.weekday() < 6:  # 0=Monday through 5=Saturday
                # Generate three shifts for this day (8am-12pm, 12pm-4pm, 4pm-8pm)
                for hour in range(8, 17, 4):  # 8am, 12pm, 4pm
                    base_date = current_date.date() if isinstance(current_date, datetime) else current_date
                    shift_start = datetime.combine(base_date, datetime.min.time()) + timedelta(hours=hour)
                    shift_end = shift_start + timedelta(hours=4)
                    
                    shift = create_shift(current_date, shift_start, shift_end, schedule.id)
                    shifts.append(shift)
            
            # Move to the next day
            current_date += timedelta(days=1)
        
        shift_by_index = {j: shift for j, shift in enumerate(shifts)}
        J = len(shifts)  # Number of shifts
        
        if J == 0:
            return {"status": "error", "message": "No shifts were created for the selected date range"}
        
        # n_i = 1 if staff i is new, 0 otherwise
        n = {}
        for i in range(I):
            assistant = staff_by_index[i]
            n[i] = 1 if not assistant.experience else 0
        
        # p_ij = preference of staff i for shift j (random for demo)
        p = {}
        for i in range(I):
            for j in range(J):
                p[i, j] = random.randint(0, 10)
        
        # r_i = max shifts for staff i (1 for new, 3 for experienced)
        r = {}
        for i in range(I):
            assistant = staff_by_index[i]
            r[i] = 1 if not assistant.experience else 3
        
        # d_j = desired number of tutors for shift j
        d = {}
        for j in range(J):
            d[j] = 2  # Default is 2 assistants per shift
        
        # a_ij = 1 if staff i is available for shift j, 0 otherwise
        a = {}
        for i in range(I):
            assistant = staff_by_index[i]
            for j in range(J):
                shift = shift_by_index[j]
                # Get student's availability for this day and time
                day_of_week = shift.date.weekday()  # 0=Monday, 5=Saturday
                shift_start_time = shift.start_time.time()
                shift_end_time = shift.end_time.time()
                
                # Get all availability records for this student on this day
                availabilities = Availability.query.filter_by(
                    username=assistant.username,
                    day_of_week=day_of_week
                ).all()
                
                # Check if any availability slot covers this shift
                is_available = False
                for avail in availabilities:
                    if avail.start_time <= shift_start_time and avail.end_time >= shift_end_time:
                        is_available = True
                        break
                
                a[i, j] = 1 if is_available else 0
        
        # Use integer-scaled preferences (multiply by 10 and round to avoid floating point)
        w = {}
        for i in range(I):
            for j in range(J):
                if n[i] == 1:  # New staff
                    avg_preference = sum(p[i, j_prime] for j_prime in range(J)) / J if J > 0 else 0
                    normalized_preference = p[i, j] - avg_preference + 5
                    # Scale by 10 and convert to integer to avoid floating point issues
                    w[i, j] = int((10 / r[i]) * normalized_preference) if r[i] > 0 else 0
                else:
                    w[i, j] = p[i, j] * 10  # Scale by 10 to keep consistent scale
        
        # Decision variables: x_ij = 1 if staff i is assigned to shift j, 0 otherwise
        x = {}
        for i in range(I):
            for j in range(J):
                x[i, j] = model.NewBoolVar(f'x_{i}_{j}')
        
        # Fairness variable: L = min utility across all staff (scaled by 10)
        L = model.NewIntVar(0, 1000, 'L')  # Increased bounds due to scaling
        
        # --- Objective Function ---
        model.Maximize(L)
        
        # --- Constraints ---
        # Constraint 1: L <= sum(w_ij * x_ij) for all i (fairness)
        for i in range(I):
            utility = sum(w[i, j] * x[i, j] for j in range(J))
            model.Add(L <= utility)
        
        # Constraint 2: x_ij <= a_ij for all i, j (availability)
        for i in range(I):
            for j in range(J):
                model.Add(x[i, j] <= a[i, j])
        
        # Constraint 3: sum(x_ij for i) <= d_j for all j (shift capacity)
        for j in range(J):
            model.Add(sum(x[i, j] for i in range(I)) <= d[j])
        
        # Constraint 4: sum(x_ij for j) <= r_i for all i (max shifts per staff)
        for i in range(I):
            max_shifts = r[i]
            model.Add(sum(x[i, j] for j in range(J)) <= max_shifts)
        
        # Constraint 5: At least one experienced staff per shift
        for j in range(J):
            experienced_staff_sum = sum((1 - n[i]) * x[i, j] for i in range(I))
            model.Add(experienced_staff_sum >= 1)
        
        # Add statistics for debugging and context
        problem_stats = {
            "assistants": I,
            "shifts": J,
            "total_shift_slots": I * J,
            "total_availability": sum(a[i, j] for i in range(I) for j in range(J)),
            "coverage_ratio": sum(a[i, j] for i in range(I) for j in range(J)) / (I * J) if I * J > 0 else 0
        }
        logger.info(f"Lab schedule statistics: {problem_stats}")
        
        # --- Solve the Model ---
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 60.0  # Increase time limit to 60 seconds
        solver.parameters.num_search_workers = 8  # Use more worker threads
        solver.parameters.log_search_progress = True  # Log search progress
        status = solver.Solve(model)
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            # Clear existing allocations for these shifts
            clear_allocations_for_shifts(shifts)
            
            # Create allocations for the assignments
            for i in range(I):
                for j in range(J):
                    if solver.Value(x[i, j]) == 1:
                        assistant = staff_by_index[i]
                        shift = shift_by_index[j]
                        
                        allocation = Allocation(assistant.username, shift.id, schedule.id)
                        db.session.add(allocation)
                        
                        logger.debug(f"Assigned {assistant.username} to shift {shift.id}")
            
            # Commit the schedule and all related objects
            db.session.commit()
            
            logger.info(f"Schedule generated successfully with status: {status}")
            
            # Return format that exactly matches help_desk_schedule
            return {
                "status": "success",
                "schedule_id": schedule.id,
                "message": "Schedule generated successfully",
                "details": {
                    "start_date": start_date.strftime('%Y-%m-%d'),
                    "end_date": end_date.strftime('%Y-%m-%d'),
                    "is_full_week": is_full_week,
                    "shifts_created": len(shifts),
                    "objective_value": solver.ObjectiveValue(),
                    "generation_options": generation_payload
                }
            }
        else:
            db.session.rollback()
            message = 'No solution found.'
            if status == cp_model.INFEASIBLE:
                message = 'Problem is infeasible with current constraints.'
            elif status == cp_model.MODEL_INVALID:
                message = 'Model is invalid.'
            
            logger.error(f"Failed to generate schedule: {message}")
            
            return {
                "status": "error",
                "message": message
            }
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error generating schedule: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


def generate_help_desk_schedule_pdf(schedule_data):
    """
    Generate a PDF of the current schedule.
    
    Args:
        schedule_data: The formatted schedule data
        
    Returns:
        The PDF file as bytes
    """
    try:
        # Create a temporary HTML file to render the schedule
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            temp_html = f.name
            
        # Render the schedule template with the data
        html_content = render_template(
            'admin/schedule/pdf_template.html',
            schedule=schedule_data
        )
        
        # Write the HTML to the temporary file
        with open(temp_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Convert HTML to PDF
        pdf = HTML(filename=temp_html).write_pdf(
            stylesheets=[
                CSS(string='@page { size: letter landscape; margin: 1cm; }')
            ]
        )
        
        # Clean up the temporary file
        os.unlink(temp_html)
        
        return pdf
        
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        raise e


def generate_schedule_pdf(schedule_data, export_format='standard'):
    """
    Generate PDF from schedule data
    
    Args:
        schedule_data: Schedule data dictionary
        export_format: PDF format type
    
    Returns:
        BytesIO buffer containing PDF data
    """
    try:
        from io import BytesIO
        from weasyprint import HTML, CSS
        from flask import render_template_string
        
        if not schedule_data:
            logger.error("No schedule data provided for PDF generation")
            return None
            
        # Determine schedule type from data or default to helpdesk
        schedule_type = schedule_data.get('type', 'helpdesk')
        schedule_id = schedule_data.get('schedule_id', 'N/A')
        date_range = schedule_data.get('date_range', 'Unknown Date Range')
        
        # Create HTML template for PDF
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{{ schedule_type|title }} Schedule - {{ date_range }}</title>
            <style>
                @page {
                    size: A4 landscape;
                    margin: 1cm;
                }
                body {
                    font-family: Arial, sans-serif;
                    font-size: 10pt;
                }
                .header {
                    text-align: center;
                    margin-bottom: 20px;
                    border-bottom: 2px solid #333;
                    padding-bottom: 10px;
                }
                .schedule-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                }
                .schedule-table th, .schedule-table td {
                    border: 1px solid #ccc;
                    padding: 8px;
                    text-align: center;
                    vertical-align: top;
                }
                .schedule-table th {
                    background-color: #f5f5f5;
                    font-weight: bold;
                }
                .day-header {
                    background-color: #e8e8e8;
                    font-weight: bold;
                }
                .time-slot {
                    font-weight: bold;
                    background-color: #f9f9f9;
                }
                .staff-name {
                    display: block;
                    margin: 2px 0;
                    padding: 2px 4px;
                    background-color: #e3f2fd;
                    border-radius: 3px;
                    font-size: 9pt;
                }
                .no-staff {
                    color: #999;
                    font-style: italic;
                }
                .footer {
                    margin-top: 20px;
                    font-size: 8pt;
                    color: #666;
                    text-align: center;
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{{ schedule_type|title }} Schedule</h1>
                <h2>{{ date_range }}</h2>
                {% if schedule_id %}
                <p>Schedule ID: {{ schedule_id }}</p>
                {% endif %}
            </div>
            
            <table class="schedule-table">
                <thead>
                    <tr>
                        <th>Time</th>
                        {% for day in days %}
                        <th class="day-header">{{ day.day }}<br>{{ day.date }}</th>
                        {% endfor %}
                    </tr>
                </thead>
                <tbody>
                    {% set time_slots = [] %}
                    {% if days %}
                        {% for shift in days[0].shifts %}
                            {% set _ = time_slots.append(shift.time) %}
                        {% endfor %}
                    {% endif %}
                    
                    {% for time_slot in time_slots %}
                    <tr>
                        <td class="time-slot">{{ time_slot }}</td>
                        {% for day in days %}
                            {% set shift = day.shifts[loop.index0] if loop.index0 < day.shifts|length else None %}
                            <td>
                                {% if shift and shift.assistants %}
                                    {% for assistant in shift.assistants %}
                                    <span class="staff-name">{{ assistant.name or assistant.id }}</span>
                                    {% endfor %}
                                {% else %}
                                    <span class="no-staff">No staff assigned</span>
                                {% endif %}
                            </td>
                        {% endfor %}
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            
            <div class="footer">
                <p>Generated on {{ current_time }} | Schedule Type: {{ schedule_type|title }}</p>
                <p>Total Days: {{ days|length }} | Export Format: {{ export_format }}</p>
            </div>
        </body>
        </html>
        """
        
        # Get days data or create empty structure
        days = schedule_data.get('days', [])
        
        # Add current timestamp
        from datetime import datetime
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Render HTML with schedule data
        html_content = render_template_string(
            html_template,
            schedule_type=schedule_type,
            schedule_id=schedule_id,
            date_range=date_range,
            days=days,
            current_time=current_time,
            export_format=export_format
        )
        
        # Generate PDF from HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
        
        # Create BytesIO buffer and write PDF data
        pdf_buffer = BytesIO()
        pdf_buffer.write(pdf_bytes)
        pdf_buffer.seek(0)  # Reset pointer to beginning
        
        logger.info(f"Successfully generated PDF for {schedule_type} schedule (format: {export_format})")
        return pdf_buffer
        
    except Exception as e:
        logger.error(f"Error generating schedule PDF: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_schedule_summary_stats(schedule_type):
    """
    Get summary statistics for a schedule type
    
    Args:
        schedule_type: Type of schedule ('helpdesk' or 'lab')
    
    Returns:
        Dictionary with summary statistics
    """
    try:
        from App.models.schedule import Schedule
        from App.models.shift import Shift
        from App.models.allocation import Allocation
        
        # Get schedule for the type
        schedule_id = 1 if schedule_type == 'helpdesk' else 2
        schedule = Schedule.query.filter_by(id=schedule_id, type=schedule_type).first()
        
        if not schedule:
            return {
                'total_shifts': 0,
                'assigned_shifts': 0,
                'unassigned_shifts': 0,
                'total_staff_assignments': 0,
                'coverage_percentage': 0.0
            }
        
        # Get shift counts
        total_shifts = Shift.query.filter_by(schedule_id=schedule.id).count()
        
        # Get assignment counts
        total_assignments = db.session.query(Allocation).join(Shift).filter(
            Shift.schedule_id == schedule.id
        ).count()
        
        # Calculate assigned shifts (shifts with at least one assignment)
        assigned_shifts = db.session.query(Shift.id).join(Allocation).filter(
            Shift.schedule_id == schedule.id
        ).distinct().count()
        
        unassigned_shifts = total_shifts - assigned_shifts
        coverage_percentage = (assigned_shifts / total_shifts * 100) if total_shifts > 0 else 0.0
        
        return {
            'total_shifts': total_shifts,
            'assigned_shifts': assigned_shifts,
            'unassigned_shifts': unassigned_shifts,
            'total_staff_assignments': total_assignments,
            'coverage_percentage': round(coverage_percentage, 2),
            'schedule_type': schedule_type,
            'schedule_id': schedule.id,
            'start_date': schedule.start_date.isoformat() if schedule.start_date else None,
            'end_date': schedule.end_date.isoformat() if schedule.end_date else None,
            'is_published': getattr(schedule, 'is_published', False)
        }
        
    except Exception as e:
        logger.error(f"Error getting schedule summary for {schedule_type}: {e}")
        return {
            'total_shifts': 0,
            'assigned_shifts': 0,
            'unassigned_shifts': 0,
            'total_staff_assignments': 0,
            'coverage_percentage': 0.0,
            'error': str(e)
        }


# Mapping helpers used by scheduling views
_DAY_CODE_MAP = {
    'MON': 0, 'TUE': 1, 'WED': 2, 'THUR': 3, 'THU': 3, 'FRI': 4, 'SAT': 5, 'SUN': 6,
    'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6
}

# Error constants
_ERROR_INVALID_DAY = 'Invalid day provided.'
_ERROR_INVALID_TIME = 'Invalid time slot provided.'
_ERROR_STAFF_NOT_FOUND = 'Staff member not found.'
_ERROR_SCHEDULE_NOT_FOUND = 'Schedule not found.'
_ERROR_SHIFT_NOT_FOUND = 'Shift not found.'


_LAB_SHIFT_CONFIG = [
    {'label': '8am - 12pm', 'start': 8, 'duration': 4},
    {'label': '12pm - 4pm', 'start': 12, 'duration': 4},
    {'label': '4pm - 8pm', 'start': 16, 'duration': 4}
]


def _schedule_id_for_type(schedule_type: str) -> int:
    return 1 if schedule_type == 'helpdesk' else 2


def _normalize_day_index(day_label: str) -> Optional[int]:
    if not day_label:
        return None
    if isinstance(day_label, str):
        normalized = _DAY_CODE_MAP.get(day_label)
        if normalized is not None:
            return normalized
        return _DAY_CODE_MAP.get(day_label.upper())
    return None


def _parse_time_to_hour(time_str: str, schedule_type: str) -> Optional[int]:
    """
    Parse time string to hour with comprehensive error handling.
    Supports various time formats and handles edge cases.
    """
    if not time_str:
        return None
    
    try:
        # Handle numeric input
        if isinstance(time_str, (int, float)):
            hour = int(time_str)
            return hour if 0 <= hour <= 23 else None
        
        # Convert to string and normalize
        time_str = str(time_str).strip()
        if not time_str:
            return None
        
        # Handle range formats (take start time)
        if '-' in time_str:
            time_str = time_str.split('-')[0].strip()
        
        # Handle colon format (extract hour)
        if ':' in time_str:
            hour_part = time_str.split(':')[0].strip()
            try:
                hour = int(hour_part)
            except ValueError:
                return None
        else:
            # Try to extract hour from string
            time_str_lower = time_str.lower()
            # Remove am/pm for processing
            clean_time = time_str_lower.replace('am', '').replace('pm', '').strip()
            try:
                hour = int(clean_time)
            except ValueError:
                return None
        
        # Handle PM conversion (but not for 12pm which is noon)
        if 'pm' in time_str.lower() and hour != 12:
            hour += 12
        elif 'am' in time_str.lower() and hour == 12:
            hour = 0  # 12am is midnight (00:00)
        
        # Special handling for lab schedule blocks
        if schedule_type == 'lab':
            time_str_lower = time_str.lower()
            lab_mapping = {
                '8:00 am - 12:00 pm': 8,
                '8am - 12pm': 8,
                '8 - 12': 8,
                '12:00 pm - 4:00 pm': 12,
                '12pm - 4pm': 12,
                '12 - 4': 12,
                '4:00 pm - 8:00 pm': 16,
                '4pm - 8pm': 16,
                '16 - 20': 16,
                '4 - 8': 16
            }
            if time_str_lower in lab_mapping:
                return lab_mapping[time_str_lower]
        
        # Validate hour range
        return hour if 0 <= hour <= 23 else None    
    except (ValueError, TypeError, AttributeError) as e:
        logger.warning(f"Invalid time format encountered: '{time_str}' - {e}")
        return None


def _calculate_shift_end(schedule_type: str, start_hour: int) -> int:
    if schedule_type == 'lab':
        for slot in _LAB_SHIFT_CONFIG:
            if slot['start'] == start_hour:
                return start_hour + slot.get('duration', 4)
        return start_hour + 4
    return start_hour + 1


def save_schedule_assignments(schedule_type: str, start_date_str: str, end_date_str: str, assignments: list[dict[str, Any]]):
    try:
        if not start_date_str or not end_date_str:
            return {'status': 'error', 'message': 'Start and end dates are required.'}, 400

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            return {'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD.'}, 400

        schedule_id = _schedule_id_for_type(schedule_type)
        schedule = Schedule.query.filter_by(id=schedule_id, type=schedule_type).first()

        if not schedule:
            schedule = Schedule(schedule_id, start_date, end_date, schedule_type)
            db.session.add(schedule)
        else:
            schedule.start_date = start_date
            schedule.end_date = end_date

        db.session.flush()

        # Clear existing allocations for shifts in the date window
        existing_shifts = Shift.query.filter(
            Shift.schedule_id == schedule.id,
            Shift.date >= start_date,
            Shift.date <= end_date
        ).all()

        for shift in existing_shifts:
            Allocation.query.filter_by(shift_id=shift.id).delete()

        for entry in assignments:
            day_label = entry.get('day')
            time_slot = entry.get('time')
            staff_members = entry.get('staff', [])

            day_index = _normalize_day_index(day_label)
            if day_index is None:
                logger.warning(f"Skipping assignment with invalid day label: {day_label}")
                continue

            shift_date = start_date + timedelta(days=day_index)
            start_hour = _parse_time_to_hour(time_slot, schedule_type)
            if start_hour is None:
                logger.warning(f"Skipping assignment with invalid time slot: {time_slot}")
                continue

            shift_start = datetime.combine(shift_date.date(), datetime.min.time()) + timedelta(hours=start_hour)
            shift_end_hour = _calculate_shift_end(schedule_type, start_hour)
            shift_end = datetime.combine(shift_date.date(), datetime.min.time()) + timedelta(hours=shift_end_hour)

            shift = Shift.query.filter_by(
                schedule_id=schedule.id,
                date=shift_date,
                start_time=shift_start
            ).first()

            if not shift:
                shift = Shift(shift_date, shift_start, shift_end, schedule.id)
                db.session.add(shift)
                db.session.flush()
            else:
                shift.end_time = shift_end

            for staff in staff_members:
                staff_id = staff.get('id')
                if not staff_id:
                    continue
                student = Student.query.filter_by(username=staff_id).first()
                if not student:
                    logger.warning(f"Skipping allocation for missing student id {staff_id}")
                    continue
                existing_allocation = Allocation.query.filter_by(shift_id=shift.id, username=student.username).first()
                if existing_allocation:
                    continue
                db.session.add(Allocation(student.username, shift.id, schedule.id))
        db.session.commit()
        return {'status': 'success', 'message': 'Schedule assignments saved successfully.'}, 200
    except Exception as exc:
        logger.error(f"Error saving schedule assignments: {exc}")
        db.session.rollback()
        return {'status': 'error', 'message': str(exc)}, 500


def remove_staff_allocation(schedule_type: str, staff_id: Union[str, int], day_label: str, time_slot: str, shift_id: Optional[int] = None):
    try:
        if not staff_id:
            return {'status': 'error', 'message': 'Staff identifier is required.'}, 400

        schedule_id = _schedule_id_for_type(schedule_type)
        schedule = Schedule.query.filter_by(id=schedule_id, type=schedule_type).first()
        if not schedule:
            return {'status': 'error', 'message': _ERROR_SCHEDULE_NOT_FOUND}, 404

        target_shift = None

        if shift_id:
            target_shift = Shift.query.filter_by(id=shift_id, schedule_id=schedule.id).first()
        else:
            day_index = _normalize_day_index(day_label)
            if day_index is None:
                return {'status': 'error', 'message': _ERROR_INVALID_DAY}, 400

            start_hour = _parse_time_to_hour(time_slot, schedule_type)
            if start_hour is None:
                return {'status': 'error', 'message': _ERROR_INVALID_TIME}, 400

            shift_date = schedule.start_date + timedelta(days=day_index)
            shift_start = datetime.combine(shift_date.date(), datetime.min.time()) + timedelta(hours=start_hour)

            target_shift = Shift.query.filter_by(
                schedule_id=schedule.id,
                date=shift_date,
                start_time=shift_start
            ).first()

        if not target_shift:
            return {'status': 'error', 'message': 'Shift not found.'}, 404

        allocation = Allocation.query.filter_by(shift_id=target_shift.id, username=staff_id).first()
        if not allocation:
            return {'status': 'error', 'message': 'Staff assignment not found for the specified shift.'}, 404

        db.session.delete(allocation)
        db.session.commit()
        return {'status': 'success', 'message': 'Staff removed from shift successfully.'}, 200
    except Exception as exc:
        logger.error(f"Error removing staff from shift: {exc}")
        db.session.rollback()
        return {'status': 'error', 'message': str(exc)}, 500


def _normalize_time_object(time_value, context_description="time value"):
    """
    Convert various time representations to datetime.time object.
    Handles time, datetime, and integer hour values.
    """
    from datetime import time as dt_time, datetime
    
    if isinstance(time_value, dt_time):
        return time_value
    elif isinstance(time_value, datetime):
        return time_value.time()
    elif isinstance(time_value, int):
        if 0 <= time_value <= 23:
            return dt_time(time_value, 0)
        else:
            raise ValueError(f"Invalid hour value: {time_value}")
    else:
        raise TypeError(f"Unexpected {context_description} type: {type(time_value)}")


def _check_time_slot_availability(availability_slots, requested_time):
    """
    Check if the requested time falls within any availability slot.
    Returns the matching slot if available, None otherwise.
    """
    for slot in availability_slots:
        try:
            avail_start_time = _normalize_time_object(slot.start_time, "availability start_time")
            avail_end_time = _normalize_time_object(slot.end_time, "availability end_time")
            
            if avail_start_time <= requested_time < avail_end_time:
                return slot
        except (TypeError, ValueError) as e:
            logger.warning(f"Skipping availability slot {slot.id}: {e}")
            continue
    return None


def list_available_staff_for_slot(schedule_type: str, day_label: str, time_slot: Union[str, int]):
    try:
        day_index = _normalize_day_index(day_label)
        if day_index is None:
            return {'status': 'error', 'message': _ERROR_INVALID_DAY}, 400

        hour = _parse_time_to_hour(time_slot, schedule_type)
        if hour is None:
            return {'status': 'error', 'message': _ERROR_INVALID_TIME}, 400

        # Convert hour to time object for proper comparison
        from datetime import time as dt_time
        requested_time = dt_time(hour, 0)
        
        available_staff = []

        assistants = HelpDeskAssistant.query.filter_by(active=True).all()
        for assistant in assistants:
            availability_slots = Availability.query.filter_by(username=assistant.username, day_of_week=day_index).all()

            if not availability_slots:
                continue

            # Use helper function to check availability
            matching_slot = _check_time_slot_availability(availability_slots, requested_time)
            if matching_slot:
                assistant_data = assistant.to_dict()
                assistant_data['availability'] = [
                    {'start_time': str(slot.start_time), 'end_time': str(slot.end_time)} 
                    for slot in availability_slots
                ]
                available_staff.append(assistant_data)

        return {'status': 'success', 'available_staff': available_staff}, 200
    except Exception as exc:
        logger.error(f"Error fetching available staff: {exc}")
        return {'status': 'error', 'message': str(exc)}, 500


def check_staff_availability_for_slot(schedule_type: str, staff_id: Union[str, int], day_label: str, time_slot: Union[str, int]):
    try:
        staff = HelpDeskAssistant.query.filter_by(username=staff_id).first()
        if not staff:
            return {'status': 'error', 'message': _ERROR_STAFF_NOT_FOUND}, 404

        day_index = _normalize_day_index(day_label)
        if day_index is None:
            return {'status': 'error', 'message': _ERROR_INVALID_DAY}, 400

        hour = _parse_time_to_hour(time_slot, schedule_type)
        if hour is None:
            return {'status': 'error', 'message': _ERROR_INVALID_TIME}, 400

        # Convert hour to time object for proper comparison
        from datetime import time as dt_time
        requested_time = dt_time(hour, 0)
        
        availability_slots = Availability.query.filter_by(username=staff.username, day_of_week=day_index).all()
        matching_slot = _check_time_slot_availability(availability_slots, requested_time)
        is_available = matching_slot is not None

        # Check for existing assignments using proper database queries
        schedule_id = _schedule_id_for_type(schedule_type)
        existing_assignment = db.session.query(Allocation).join(Shift).filter(
            Allocation.username == staff_id,
            Shift.schedule_id == schedule_id,
            db.extract('dow', Shift.date) == day_index,  # Use extract for day of week comparison
            db.extract('hour', Shift.start_time) == hour  # Use extract for hour comparison
        ).first()

        response = {
            'status': 'success',
            'is_available': is_available,
            'availability': {
                'day': day_label,
                'time': time_slot,
                'matches_slot': is_available
            },
            'existing_assignment': existing_assignment is not None
        }

        if matching_slot:
            response['availability']['slot'] = {
                'start_time': str(matching_slot.start_time),
                'end_time': str(matching_slot.end_time)
            }
        return response, 200
    except Exception as exc:
        logger.error(f"Error checking staff availability: {exc}")
        return {'status': 'error', 'message': str(exc)}, 500


def batch_staff_availability(schedule_type: str, queries: list[dict[str, Any]]):
    """
    Process multiple availability queries in a single request to reduce server load.
    Each query should have: staff_id, day, time
    Returns: list of results with staff_id, day, time, is_available
    """
    try:
        results = []
        for query in queries:
            staff_id = query.get('staff_id')
            day = query.get('day')
            time_slot = query.get('time')
            
            if not all([staff_id, day, time_slot]):
                results.append({
                    'staff_id': staff_id,
                    'day': day,
                    'time': time_slot,
                    'is_available': False,
                    'error': 'Missing required parameters'
                })
                continue
            
            # Use the single availability check function
            result, status_code = check_staff_availability_for_slot(schedule_type, staff_id, day, time_slot)
            
            # Extract the availability result
            is_available = False
            if status_code == 200 and result.get('status') == 'success':
                is_available = result.get('is_available', False)
            
            results.append({
                'staff_id': staff_id,
                'day': day,
                'time': time_slot,
                'is_available': is_available
            })
        
        return {'status': 'success', 'results': results}, 200
    except Exception as exc:
        logger.error(f"Error in batch availability check: {exc}")
        return {'status': 'error', 'message': str(exc)}, 500


def generate_schedule_pdf_for_type(schedule_type: str):
    try:
        schedule_id = _schedule_id_for_type(schedule_type)
        schedule = Schedule.query.filter_by(id=schedule_id, type=schedule_type).first()
        if not schedule:
            return None, None, {'status': 'error', 'message': _ERROR_SCHEDULE_NOT_FOUND}, 404

        schedule_data = get_schedule_data(schedule_id)
        if not schedule_data:
            return None, None, {'status': 'error', 'message': 'Unable to generate schedule data.'}, 500

        pdf_buffer = generate_schedule_pdf(schedule_data, export_format='standard')
        if not pdf_buffer:
            return None, None, {'status': 'error', 'message': 'Failed to generate PDF.'}, 500

        filename = f"{schedule_type}_schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return pdf_buffer, filename, None, 200
    except Exception as exc:
        logger.error(f"Error generating schedule PDF for {schedule_type}: {exc}")
        return None, None, {'status': 'error', 'message': str(exc)}, 500