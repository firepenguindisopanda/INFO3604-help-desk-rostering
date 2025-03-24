from ortools.sat.python import cp_model
from datetime import datetime, timedelta
from flask import jsonify

from App.models import (
    Schedule, Shift, Student, HelpDeskAssistant, 
    CourseCapability, Availability, 
    Allocation, Course
)
from App.database import db
from App.controllers.notification import notify_schedule_published

def help_desk_scheduler(I, J, K):
    # Using a CP-SAT model
    model = cp_model.CpModel()
    
    # --- Data ---
    # Hard coded ranges for staff, shift and course indexes

    # Assuming staff can help with all courses
    t = {}
    for i in range(I):
        for k in range(K):
            t[i, k] = 1
    
    # Minimum desired number of tutors for each shift and course is 2
    d = {}
    for j in range(J):
        for k in range(K):
            d[j, k] = 2
    
    # Default weight = d
    w = {}
    for j in range(J):
        for k in range(K):
            w[j, k] = d[j, k]

    # Hard coded availability data
    a = {}
    a = [
        [1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 
        [0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 
        [0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0], 
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0], 
        [0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1], 
        [0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0], 
        [0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 
        [0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0], 
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0], 
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    ]
    
    # Hard coded minimum shifts
    r = {}
    r = [4, 4, 4, 4, 4, 4, 4, 4, 2, 4]

    # --- Variables ---
    x = {}
    for i in range(I):
        for j in range(J):
            x[i, j] = model.NewBoolVar(f'x_{i}_{j}')
    
    # --- Objective Function ---
    objective = []
    for j in range(J):
        for k in range(K):
            assigned_tutors = sum(x[i, j] * t[i, k] for i in range(I))
            objective.append((d[j, k] - assigned_tutors) * w[j, k])
    
    model.Minimize(sum(objective))

    # --- Constraints ---
    # Constraint 1: Σxij * tik ≤ djk for all j,k pairs
    for j in range(J):
        for k in range(K):
            constraint = sum(x[i, j] * t[i, k] for i in range(I))
            model.Add(constraint <= d[j, k])
    
    # Constraint 2: Σxij >= 4 for all i
    for i in range(I):
        constraint = sum(x[i, j] for j in range(J))
        model.Add(constraint >= r[i])
    
    # Constraint 3: Σxij >= 2 for all j
    for j in range(J):
        constraint = sum(x[i, j] for i in range(I))
        
        # Variable for constraint == 0
        weight_zero = model.NewBoolVar(f'weight_zero_{j}')
        model.Add(constraint == 0).OnlyEnforceIf(weight_zero)
        
        # Variable for constraint == 1
        weight_one = model.NewBoolVar(f'weight_one_{j}')
        model.Add(constraint == 1).OnlyEnforceIf(weight_one)
        
        # Adjusted constraint based on weighted values of availability less than 2
        model.Add(constraint + (2 * weight_zero + weight_one) >= 2)
    
    # Constraint 4: xij <= aij for all i
    for i in range(I):
        for j in range(J):
            model.Add(x[i, j] <= a[i][j])

    # --- Solve ---
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        assignments = {}
        
        for i in range(I):
            for j in range(J):
                if solver.Value(x[i, j]) == 1:
                    if j not in assignments:
                        assignments[j] = []
                    assignments[j].append(i)
        
        return {
            'status': 'success',
            'staff_index': {
                0: 'Daniel Rasheed',
                1: 'Michelle Liu',
                2: 'Stayaan Maharaj',
                3: 'Daniel Yatali',
                4: 'Satish Maharaj',
                5: 'Selena Madrey',
                6: 'Veron Ramkissoon',
                7: 'Tamika Ramkissoon',
                8: 'Samuel Mahadeo',
                9: 'Neha Maharaj'
            },
            'assignments': assignments
        }
    else:
        message = 'No solution found.'
        if status == cp_model.INFEASIBLE:
            message = 'Probleam is infeasible.'
        elif status == cp_model.MODEL_INVALID:
            message = 'Model is invalid.'
        elif status == cp_model.UNKNOWN:
            message = 'Solver status is unknown.'
        
        return {
            'status': 'error',
            'message': message
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
    try:
        # If start_date is not provided, use the current date
        if start_date is None:
            start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
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
        schedule = get_or_create_main_schedule(start_date, end_date)
        
        # Clear existing shifts for the date range
        clear_shifts_in_range(schedule.id, start_date, end_date)
        
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
                    
                    # Set course demands for each shift
                    active_courses = Course.query.all()
                    for course in active_courses:
                        # Default requirement is 2 tutors per course
                        add_course_demand_to_shift(shift.id, course.code, 2, 2)
            
            # Move to the next day
            current_date += timedelta(days=1)
        
        # Get all active assistants
        assistants = HelpDeskAssistant.query.filter_by(active=True).all()
        if not assistants:
            db.session.rollback()
            return {"status": "error", "message": "No active assistants found"}
            
        # Now we'll use CP-SAT model to generate optimal schedule
        model = cp_model.CpModel()
        
        # --- Variables ---
        x = {}  # x[i,j] = 1 if assistant i is assigned to shift j
        for assistant in assistants:
            for shift in shifts:
                x[assistant.username, shift.id] = model.NewBoolVar(f'x_{assistant.username}_{shift.id}')
        
        # --- Objective Function ---
        # We'll minimize the sum of the weighted course demand not met
        objective_terms = []
        
        # For each shift and course demand
        for shift in shifts:
            course_demands = get_course_demands_for_shift(shift.id)
            for demand in course_demands:
                course_code = demand['course_code']
                
                # For each course, calculate the number of assigned assistants who can teach it
                capable_assistants = []
                for assistant in assistants:
                    # Check if this assistant can teach this course
                    capabilities = CourseCapability.query.filter_by(
                        assistant_username=assistant.username,
                        course_code=course_code
                    ).all()
                    
                    if capabilities:
                        capable_assistants.append(assistant)
                
                # Sum up assigned capable assistants
                assistants_for_course = sum(
                    x[a.username, shift.id] for a in capable_assistants
                )
                
                # Objective: minimize shortfall weighted by importance
                shortfall = model.NewIntVar(0, len(assistants), f'shortfall_{shift.id}_{course_code}')
                model.Add(shortfall >= demand['tutors_required'] - assistants_for_course)
                objective_terms.append(shortfall * demand['weight'])
        
        # --- Constraints ---
        # Constraint 1: Each assistant should be assigned to a reasonable number of shifts
        # For partial week, adjust the minimum hours proportionally
        for assistant in assistants:
            min_hours = assistant.hours_minimum
            
            # If this is not a full week, scale the minimum hours based on the date range
            if not is_full_week:
                days_in_range = sum(1 for d in range((end_date - start_date).days + 1) 
                                    if (start_date + timedelta(days=d)).weekday() < 5)
                scaling_factor = days_in_range / 5.0  # 5 weekdays in a full week
                min_hours = max(1, int(min_hours * scaling_factor))  # At least 1 hour
            
            # Add a soft constraint instead of a hard constraint for minimum hours
            # This helps the model find a solution even if perfect assignment is impossible
            assistant_shifts = sum(x[assistant.username, s.id] for s in shifts)
            
            # Penalty for not meeting minimum hours
            shortfall = model.NewIntVar(0, min_hours, f'hour_shortfall_{assistant.username}')
            model.Add(shortfall >= min_hours - assistant_shifts)
            
            # Add to objective with a higher weight
            objective_terms.append(shortfall * 10)  # Higher weight makes this more important
        
        # Constraint 2: Each shift must have at least 2 assistants
        for shift in shifts:
            model.Add(sum(x[a.username, shift.id] for a in assistants) >= 2)
        
        # Constraint 3: Assistants can only be assigned to shifts they are available for
        for assistant in assistants:
            availabilities = Availability.query.filter_by(username=assistant.username).all()
            
            for shift in shifts:
                # Check if this assistant is available for this shift
                is_available = False
                for avail in availabilities:
                    if avail.is_available_for_shift(shift):
                        is_available = True
                        break
                
                if not is_available:
                    model.Add(x[assistant.username, shift.id] == 0)
        
        # Add the objective terms to the model
        model.Minimize(sum(objective_terms))
        
        # --- Solve ---
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0  # Limit solve time to 30 seconds
        status = solver.Solve(model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            # Clear existing allocations for these shifts
            clear_allocations_for_shifts(shifts)
            
            # Create allocations for the assignments
            for assistant in assistants:
                for shift in shifts:
                    if solver.Value(x[assistant.username, shift.id]) == 1:
                        allocation = Allocation(assistant.username, shift.id, schedule.id)
                        db.session.add(allocation)
            
            # Commit the schedule and all related objects
            db.session.commit()
            
            return {
                "status": "success",
                "schedule_id": schedule.id,
                "message": "Schedule generated successfully",
                "details": {
                    "start_date": start_date.strftime('%Y-%m-%d'),
                    "end_date": end_date.strftime('%Y-%m-%d'),
                    "is_full_week": is_full_week,
                    "shifts_created": len(shifts)
                }
            }
        else:
            db.session.rollback()
            message = 'No solution found.'
            if status == cp_model.INFEASIBLE:
                message = 'Problem is infeasible with current constraints.'
            
            return {
                "status": "error",
                "message": message
            }
    
    except Exception as e:
        db.session.rollback()
        return {
            "status": "error",
            "message": str(e)
        }

def get_or_create_main_schedule(start_date, end_date):
    """Get or create the main schedule object"""
    # Check for existing main schedule (id=1)
    schedule = Schedule.query.get(1)
    
    if not schedule:
        # Create a new main schedule
        schedule = Schedule(1, start_date, end_date)
        db.session.add(schedule)
        db.session.flush()
    else:
        # Update the existing schedule's date range
        schedule.start_date = start_date
        schedule.end_date = end_date
        db.session.add(schedule)
        db.session.flush()
    
    return schedule

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
        
        # Delete course demands for these shifts
        # Since we don't have direct ShiftCourseDemand class imported,
        # use db.session.execute to run a raw SQL DELETE query
        db.session.execute(
            f"DELETE FROM shift_course_demand WHERE shift_id = {shift.id}"
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
    """Add course demand for a shift using raw SQL"""
    # If weight is not provided, use tutors_required as the weight
    if weight is None:
        weight = tutors_required
    
    # Use raw SQL to insert the course demand
    db.session.execute(
        f"""INSERT INTO shift_course_demand 
            (shift_id, course_code, tutors_required, weight) 
            VALUES ({shift_id}, '{course_code}', {tutors_required}, {weight})"""
    )
    db.session.flush()

def get_course_demands_for_shift(shift_id):
    """Get course demands for a shift using raw SQL"""
    # Use raw SQL to select the course demands
    result = db.session.execute(
        f"""SELECT course_code, tutors_required, weight 
            FROM shift_course_demand 
            WHERE shift_id = {shift_id}"""
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
                notify_schenotify_schedule_published(username, 0)  # Week number 0 since we're not using weeks
                
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

def get_current_schedule():
    """Get the current schedule with all shifts"""
    # Get the main schedule (id=1)
    schedule = Schedule.query.get(1)
    if not schedule:
        return None
        
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
        day_date = schedule.start_date + timedelta(days=day_idx) if schedule.start_date else datetime.utcnow()
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