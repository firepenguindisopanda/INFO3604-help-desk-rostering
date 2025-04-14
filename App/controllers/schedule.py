from datetime import datetime, timedelta
from flask import jsonify
from ortools.sat.python import cp_model
from ortools.linear_solver import pywraplp
import logging, csv, random
from sqlalchemy import text

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


# Configure logger
logger = logging.getLogger(__name__)


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


def generate_schedule(start_date=None, end_date=None):
    """
    Generate a help desk schedule with flexible date range.
    
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
    try:
        # If start_date is not provided, use the current date
        if start_date is None:
            start_date = trinidad_now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # If end_date is not provided, set it to the end of the week (Friday)
        if end_date is None:
            # Get the end of the current week (Friday)
            days_to_friday = 4 - start_date.weekday()  # 4 = Friday
            if days_to_friday < 0:  # If today is already past Friday
                days_to_friday += 7  # Go to next Friday
            end_date = start_date + timedelta(days=days_to_friday)
        
        # Check if we're scheduling for a full week or partial week
        is_full_week = start_date.weekday() == 0 and (end_date - start_date).days >= 4
        
        # Get or create the main schedule
        schedule = get_schedule(1, start_date, end_date)
        
        # Clear existing shifts for the date range
        clear_shifts_in_range(schedule.id, start_date, end_date)
        
        # Get all courses from the standardized list
        all_courses = get_all_courses()
        if not all_courses:
            # Create standard courses if none exist
            with open('sample/courses.csv', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    course = create_course(course_code=row['code'], course_name=row['name'])
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
                    shift_start = datetime.combine(current_date.date(), datetime.min.time()) + timedelta(hours=hour)
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
        
        # Get all active assistants
        assistants = HelpDeskAssistant.query.filter_by(active=True).all()
        if not assistants:
            db.session.rollback()
            return {"status": "error", "message": "No active assistants found"}
            
        # For debugging: log how many assistants we found
        logger.info(f"Found {len(assistants)} active assistants")
        
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
        # t_i,k = 1 if staff i can help with course k, 0 otherwise
        t = {}
        for i in range(I):
            assistant = staff_by_index[i]
            # Get courses this assistant can help with
            capabilities = CourseCapability.query.filter_by(
                assistant_username=assistant.username
            ).all()
            can_help_with = set(cap.course_code for cap in capabilities)
            
            for k in range(K):
                course = course_by_index[k]
                t[i, k] = 1 if course.code in can_help_with else 0
        
        # a_i,j = 1 if staff i is available during shift j
        a = {}
        for i in range(I):
            assistant = staff_by_index[i]
            for j in range(J):
                shift = shift_by_index[j]
                # Get student's availability for this day and time
                day_of_week = shift.date.weekday()  # 0=Monday, 4=Friday
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
            
            return {
                "status": "success",
                "schedule_id": schedule.id,
                "message": "Schedule generated successfully",
                "details": {
                    "start_date": start_date.strftime('%Y-%m-%d'),
                    "end_date": end_date.strftime('%Y-%m-%d'),
                    "is_full_week": is_full_week,
                    "shifts_created": len(shifts),
                    "objective_value": solver.ObjectiveValue()
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
    

def get_schedule(id, start_date, end_date):
    """Get or create the main schedule object"""
    schedule = Schedule.query.get(id)
    
    if not schedule:
        # Create a new main schedule
        schedule = create_schedule(id, start_date, end_date)
    else:
        # Update the existing schedule's date range
        schedule.start_date = start_date
        schedule.end_date = end_date
        db.session.add(schedule)
        db.session.flush()
    return schedule


def create_schedule(id, start_date, end_date):
    new_schedule = Schedule(id, start_date, end_date)
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
        
        # Delete course demands for these shifts using text() for SQL
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
    
    # Use text() for SQL queries to avoid the error
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
    """
    Get course demands for a shift using text() SQL
    
    Args:
        shift_id: ID of the shift
        
    Returns:
        List of dictionaries with course demand information
    """
    try:
        # Use text() for SQL queries to avoid the error
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
    """
    Ensure schedule data is synced between admin and volunteer views.
    This ensures both views are looking at the same database information.
    
    Returns:
        bool: True if successful, False otherwise
    """
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
    """
    Publish the schedule and notify all assigned staff.
    Also ensures data is synced between admin and volunteer views.
    
    Args:
        schedule_id: ID of the schedule to publish
        
    Returns:
        dict: Result of the operation
    """
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


def clear_schedule():
    """
    Clear the entire schedule, removing all shifts, allocations, and course demands.
    Uses direct database operations to ensure complete removal.
    
    Returns:
        Dictionary with operation status
    """
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


def get_current_schedule():
    """Get the current schedule with all shifts"""
    try:
        # Get the main schedule (id=1)
        schedule = Schedule.query.get(1)
        if not schedule:
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
            
        # Format the schedule for display
        shifts_by_day = {}
        
        for shift in schedule.shifts:
            day_idx = shift.date.weekday()  # 0=Monday, 6=Sunday
            if day_idx >= 5:  # Skip weekend shifts
                continue
                
            hour = shift.start_time.hour
            
            if day_idx not in shifts_by_day:
                shifts_by_day[day_idx] = {}
                
            shifts_by_day[day_idx][hour] = {
                "shift_id": shift.id,
                "time": shift.formatted_time(),
                "assistants": get_assistants_for_shift(shift.id)
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
        
        return {
            "schedule_id": schedule.id,
            "date_range": f"{schedule.start_date.strftime('%d %b')} - {schedule.end_date.strftime('%d %b, %Y')}" if schedule.start_date and schedule.end_date else "Current Schedule",
            "is_published": schedule.is_published,
            "days": days
        }
    except Exception as e:
        # Log the error
        logger.error(f"Error getting current schedule: {e}")
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


def generate_lab_assistant_schedule(start_date=None, end_date=None):
    try:
        solver = pywraplp.Solver.CreateSolver('SCIP')
        
        # --- Variables ---
        
        """ Staff Index, i = 1 · · · I """        
        # Get all active lab assistants
        assistants = get_active_lab_assistants()
        if not assistants:
            db.session.rollback()
            return {"status": "error", "message": "No active assistants found"}
        
        staff_by_index = {i: assistant for i, assistant in enumerate(assistants)}
        I = len(assistants)
        
        
        """ Shift Index, j = 1 · · · J """
        # If start_date is not provided, use the current date
        if start_date is None:
            start_date = trinidad_now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # If end_date is not provided, set it to the end of the week (Saturday)
        if end_date is None:
            # Get the end of the current week (Saturday)
            days_to_saturday = 5 - start_date.weekday()  # 5 = Saturday
            if days_to_saturday < 0:  # If today is already past Saturday
                days_to_saturday += 7  # Go to next Friday
            end_date = start_date + timedelta(days=days_to_saturday)

        # Check if we're scheduling for a full week or partial week
        is_full_week = start_date.weekday() == 0 and (end_date - start_date).days >= 5
        
        # Get or create the main schedule
        schedule = get_schedule(1, start_date, end_date)
        
        # Clear existing shifts for the date range
        clear_shifts_in_range(schedule.id, start_date, end_date)
        
        shifts = []
        current_date = start_date
        
        while current_date <= end_date:
            # Skip Sunday (day_of_week >= 6)
            if current_date.weekday() < 6:  # 0=Monday through 5=Saturday
                # Generate three shifts for this day
                for hour in range(8, 16, 4):  # 8am through 8pm
                    shift_start = datetime.combine(current_date.date(), datetime.min.time()) + timedelta(hours=hour)
                    shift_end = shift_start + timedelta(hours=4)
                    
                    shift = create_shift(current_date, shift_start, shift_end, schedule.id)
                    shifts.append(shift)
            
            # Move to the next day
            current_date += timedelta(days=1)
        
        shift_by_index = {j: shift for j, shift in enumerate(shifts)}
        J = len(shifts)  # Number of shifts
        
        n = {}
        for i in range(I):
            assistant = staff_by_index[i]
            n[i] = 1 if not assistant.experience else 0
        
        p = {}
        for i in range(I):
            for j in range(J):
                p[i, j] = random.randint(0, 10)
        
        r = {}
        for i in range(I):
            assistant = staff_by_index[i]
            r[i] = 1 if not assistant.experience else 3
        
        d = {}
        for j in range(J):
            d[j] = 2 # Default
        
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
        
        
        # Calculate normalized preferences (w_ij)
        w = {}
        w = [[0 for _ in range(J)] for _ in range(I)]
        for i in range(I):
            for j in range(J):
                if n[i] == 1:  # New staff
                    w[i][j] = (1 / r[i])(p[i][j] - (1 / J) * sum(p[i][j] + 5 for j in range(J)))
                else:
                    w[i][j] = p[i][j]
        
        
        x = [[solver.IntVar(0, 1, f'x_{i}_{j}') for j in range(J)] for i in range(I)]
        L = solver.NumVar(0, solver.inifity(), 'L')
        
        
        # --- Objective Function ---
        solver.Maximize(L)
        
        
        # --- Constraints ---
        # Constraint 1: L <= sum(w_ij * x_ij) for all i
        for i in range(I):
            solver.Add(L <= sum(w[i][j] * x[i][j] for j in range(J)))
        
        # Constraint 2: x_ij <= a_ij for all i, j
        for i in range(I):
            for j in range(J):
                solver.Add(x[i][j] <= a[i][j])
        
        # Constraint 3: sum(x_ij) <= d_j for all j
        for j in range(J):
            solver.Add(sum(x[i][j] for i in range(I)) <= d[j])
        
        # Constraint 4: sum(x_ij) <= 3 * (1 - n_i) + n_i for all i
        for i in range(I):
            solver.Add(sum(x[i][j] for j in range(J)) <= 3 * (1 - n[i]) + n[i])
        
        # Constraint 5: sum((1 - n_i) * x_ij) >= 1 for all j
        for j in range(J):
            solver.Add(sum((1 - n[i]) * x[i][j] for i in range(I)) >= 1)
        
        
        # --- Solve the Model ---
        status = solver.Solve()
        
        if status == pywraplp.Solver.OPTIMAL:
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
            
            return {
                "status": "success",
                "schedule_id": schedule.id,
                "message": "Schedule generated successfully",
                "details": {
                    "start_date": start_date.strftime('%Y-%m-%d'),
                    "end_date": end_date.strftime('%Y-%m-%d'),
                    "is_full_week": is_full_week,
                    "shifts_created": len(shifts),
                    "objective_value": solver.ObjectiveValue()
                }
            }
        else:
            db.session.rollback()
            message = 'No solution found.'
            if status == pywraplp.Solver.INFEASIBLE:
                message = 'Problem is infeasible with current constraints.'
            elif status == pywraplp.Solver.MODEL_INVALID:
                message = 'Model is invalid.'
            
            logger.error(f"Failed to generate schedule: {message}")
            
            return {
                "status": "error",
                "message": message
            }
    except Exception as e:
        logger.error(f"Error generating schedule: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

