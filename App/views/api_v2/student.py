from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from App.views.api_v2 import api_v2
from App.views.api_v2.utils import api_success, api_error
from App.middleware import volunteer_required

@api_v2.route('/student/dashboard', methods=['GET'])
@jwt_required()
@volunteer_required
def student_dashboard():
    """
    Get student dashboard data including upcoming shifts and recent activity
    
    Returns:
        Student-specific dashboard data
    """
    try:
        username = get_jwt_identity()
        
        # Import controllers as needed to avoid circular imports
        from App.controllers.user import get_user
        from App.controllers.schedule import get_shifts_for_student
        from App.controllers.tracking import get_student_time_entries
        
        # Get user info
        user = get_user(username)
        if not user:
            return api_error("User not found", status_code=404)
        
        # Get upcoming shifts for this student
        upcoming_shifts = get_shifts_for_student(username, limit=10)
        shifts_data = []
        
        if upcoming_shifts:
            for shift in upcoming_shifts:
                shift_data = {
                    "id": shift.id,
                    "date": shift.date.isoformat() if shift.date else None,
                    "start_time": shift.start_time.strftime('%H:%M') if shift.start_time else None,
                    "end_time": shift.end_time.strftime('%H:%M') if shift.end_time else None,
                    "schedule_id": shift.schedule_id
                }
                shifts_data.append(shift_data)
        
        # Get recent time entries
        time_entries = get_student_time_entries(username, limit=5)
        entries_data = []
        
        if time_entries:
            for entry in time_entries:
                entry_data = {
                    "id": entry.id,
                    "clock_in": entry.clock_in.isoformat() if entry.clock_in else None,
                    "clock_out": entry.clock_out.isoformat() if entry.clock_out else None,
                    "shift_id": entry.shift_id,
                    "status": "completed" if entry.clock_out else "in_progress"
                }
                entries_data.append(entry_data)
        
        # Get basic stats
        total_shifts_count = len(shifts_data)
        completed_entries_count = len([e for e in entries_data if e.get('status') == 'completed'])
        
        return api_success({
            "user": {
                "username": user.username,
                "first_name": getattr(user, 'first_name', ''),
                "last_name": getattr(user, 'last_name', ''),
                "email": getattr(user, 'email', ''),
                "student_id": getattr(user, 'student_id', None)
            },
            "upcoming_shifts": shifts_data,
            "recent_time_entries": entries_data,
            "stats": {
                "upcoming_shifts_count": total_shifts_count,
                "completed_shifts_count": completed_entries_count,
                "has_upcoming_shifts": total_shifts_count > 0
            }
        })
        
    except Exception as e:
        return api_error(f"Failed to load dashboard data: {str(e)}", status_code=500)

@api_v2.route('/student/schedule', methods=['GET'])
@jwt_required()
@volunteer_required
def student_schedule():
    """
    Get student's full schedule for a date range
    
    Query parameters:
        - start_date: YYYY-MM-DD (optional, default: current week)
        - end_date: YYYY-MM-DD (optional, default: current week)
    
    Returns:
        Student's schedule data
    """
    try:
        username = get_jwt_identity()
        
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        from datetime import datetime, timedelta
        from App.controllers.schedule import get_shifts_for_student_in_range
        
        # Default to current week if no dates provided
        if not start_date:
            today = datetime.now().date()
            start_of_week = today - timedelta(days=today.weekday())
            start_date = start_of_week.isoformat()
            
        if not end_date:
            today = datetime.now().date()
            end_of_week = today + timedelta(days=6-today.weekday())
            end_date = end_of_week.isoformat()

        # Get shifts using controller function
        shifts = get_shifts_for_student_in_range(username, start_date, end_date)
        shifts_data = []
        
        if shifts:
            for shift in shifts:
                shift_data = {
                    "id": shift.id,
                    "date": shift.date.isoformat() if shift.date else None,
                    "start_time": shift.start_time.strftime('%H:%M') if shift.start_time else None,
                    "end_time": shift.end_time.strftime('%H:%M') if shift.end_time else None,
                    "schedule_id": shift.schedule_id,
                    "duration_hours": (
                        (shift.end_time.hour - shift.start_time.hour) + 
                        (shift.end_time.minute - shift.start_time.minute) / 60
                    ) if shift.start_time and shift.end_time else 0
                }
                shifts_data.append(shift_data)
        
        return api_success({
            "shifts": shifts_data,
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            },
            "stats": {
                "total_shifts": len(shifts_data),
                "total_hours": sum(s.get('duration_hours', 0) for s in shifts_data)
            }
        })
        
    except Exception as e:
        return api_error(f"Failed to load schedule: {str(e)}", status_code=500)