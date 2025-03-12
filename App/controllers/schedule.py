from ortools.sat.python import cp_model
from datetime import datetime, timedelta
from flask import jsonify

from App.models import (
    Schedule, Shift, Student, HelpDeskAssistant, 
    CourseCapability, Availability, ShiftCourseDemand, 
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


def lab_assistant_scheduler():
    pass


def generate_help_desk_schedule(week_number, start_date, semester_id=None):
    """
    Generate a help desk schedule using actual database models.
    
    Args:
        week_number: The week number for this schedule
        start_date: The start date for this schedule (datetime object)
        semester_id: Optional semester ID
    
    Returns:
        A dictionary with the schedule information
    """
    try:
        # Create the schedule object
        schedule = Schedule(week_number, start_date, semester_id=semester_id)
        db.session.add(schedule)
        db.session.flush()  # Get the schedule ID without committing yet
        
        # Generate shifts for the schedule (Monday-Friday)
        shifts = []
        for day in range(5):  # 0=Monday through 4=Friday
            date = start_date + timedelta(days=day)
            
            # Generate 8 hourly shifts per day (9am-5pm)
            for hour in range(9, 17):  # 9am through 4pm
                shift_start = datetime.combine(date.date(), datetime.min.time()) + timedelta(hours=hour)
                shift_end = shift_start + timedelta(hours=1)
                
                shift = Shift(date, shift_start, shift_end, schedule.id)
                db.session.add(shift)
                db.session.flush()  # Get the shift ID
                shifts.append(shift)
                
                # Set course demands for each shift
                # In a real application, you would get these from your requirements
                active_courses = Course.query.all()
                for course in active_courses:
                    # Default requirement is 2 tutors per course
                    shift.add_course_demand(course.code, 2, 2)
        
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
            for demand in shift.course_demands:
                course_code = demand.course_code
                
                # For each course, calculate the number of assigned assistants who can teach it
                assistants_for_course = sum(
                    x[a.username, shift.id] 
                    for a in assistants 
                    if any(c.course_code == course_code for c in a.course_capabilities)
                )
                
                # Objective: minimize shortfall weighted by importance
                shortfall = model.NewIntVar(0, len(assistants), f'shortfall_{shift.id}_{course_code}')
                model.Add(shortfall >= demand.tutors_required - assistants_for_course)
                objective_terms.append(shortfall * demand.weight)
        
        model.Minimize(sum(objective_terms))
        
        # --- Constraints ---
        # Constraint 1: Each assistant must be assigned to at least min_hours shifts
        for assistant in assistants:
            min_hours = assistant.hours_minimum
            model.Add(sum(x[assistant.username, s.id] for s in shifts) >= min_hours)
        
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
        
        # --- Solve ---
        solver = cp_model.CpSolver()
        status = solver.Solve(model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
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
                "message": "Schedule generated successfully"
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
                notify_schedule_published(username, schedule.week_number)
                
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

def get_schedule_for_week(week_number, semester_id=None):
    """Get a detailed schedule for a specific week"""
    query = Schedule.query.filter_by(week_number=week_number)
    if semester_id:
        query = query.filter_by(semester_id=semester_id)
    
    schedule = query.first()
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
        day_date = schedule.start_date + timedelta(days=day_idx)
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
        "week_number": schedule.week_number,
        "date_range": schedule.get_formatted_date_range(),
        "is_published": schedule.is_published,
        "days": days
    }