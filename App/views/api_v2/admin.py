from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from App.views.api_v2 import api_v2
from App.views.api_v2.utils import api_success, api_error
from App.middleware import admin_required

@api_v2.route('/admin/dashboard', methods=['GET'])
@jwt_required()
@admin_required
def admin_dashboard():
    """
    Get admin dashboard data including schedules, attendance, and pending requests
    
    Returns:
        Dashboard statistics and summary data
    """
    try:
        # Import controllers to keep logic in controller layer
        from App.controllers.schedule import get_published_schedules, get_current_published_schedule
        from App.controllers.registration import get_pending_registrations_count
        from App.controllers.request import get_pending_requests_count
        
        # Get current user info
        username = get_jwt_identity()
        
        # Get published schedules count via controller
        try:
            schedules = get_published_schedules()
            schedules_count = len(schedules)
        except Exception:
            schedules_count = 0
        
        # Get current schedule if any (date-bounded preferred, fallback to latest)
        try:
            current = get_current_published_schedule()
            if current:
                start_iso = current.start_date.isoformat() if getattr(current, 'start_date', None) else None
                end_iso = current.end_date.isoformat() if getattr(current, 'end_date', None) else None
                current_schedule_data = {
                    "id": current.id,
                    "start_date": start_iso,
                    "end_date": end_iso,
                    "type": getattr(current, 'type', None),
                    "is_published": getattr(current, 'is_published', False)
                }
            else:
                current_schedule_data = None
        except Exception:
            current_schedule_data = None
        
        # Get pending items counts
        try:
            pending_registrations_count = get_pending_registrations_count()
        except Exception:
            pending_registrations_count = 0
        try:
            pending_requests_count = get_pending_requests_count()
        except Exception:
            pending_requests_count = 0
        
        # Get basic attendance summary (implement basic version)
        attendance_summary = {
            "total_shifts_this_week": 0,
            "attended_shifts": 0,
            "missed_shifts": 0,
            "attendance_rate": 0.0
        }
        
        try:
            from App.controllers.tracking import get_attendance_summary
            attendance_summary = get_attendance_summary()
        except Exception:
            # If tracking controller doesn't have this method, use defaults
            pass
        
        return api_success({
            "user": {
                "username": username
            },
            "schedules": {
                "published_count": schedules_count,
                "current_schedule": current_schedule_data
            },
            "pending_items": {
                "registrations": pending_registrations_count,
                "requests": pending_requests_count,
                "total": pending_registrations_count + pending_requests_count
            },
            "attendance": attendance_summary,
            "quick_stats": {
                "total_published_schedules": schedules_count,
                "pending_approvals": pending_registrations_count + pending_requests_count,
                "has_current_schedule": current_schedule_data is not None
            }
        })
        
    except Exception as e:
        return api_error(f"Failed to load dashboard data: {str(e)}", status_code=500)

@api_v2.route('/admin/stats', methods=['GET'])
@jwt_required()
@admin_required  
def admin_stats():
    """
    Get detailed administrative statistics
    
    Returns:
        Detailed stats for administrative overview
    """
    try:
        from App.database import db
        from App.models.user import User
        from App.models.student import Student
        from App.models.admin import Admin
        from App.models.schedule import Schedule
        from App.models.shift import Shift
        from App.models.allocation import Allocation
        
        # Get user counts
        total_users = db.session.query(User).count()
        admin_count = db.session.query(Admin).count()
        student_count = db.session.query(Student).count()
        
        # Get schedule counts
        total_schedules = db.session.query(Schedule).count()
        published_schedules = db.session.query(Schedule).filter_by(is_published=True).count()
        
        # Get shift and allocation counts
        total_shifts = db.session.query(Shift).count()
        total_allocations = db.session.query(Allocation).count()
        
        return api_success({
            "users": {
                "total": total_users,
                "admins": admin_count,
                "students": student_count
            },
            "schedules": {
                "total": total_schedules,
                "published": published_schedules,
                "draft": total_schedules - published_schedules
            },
            "shifts": {
                "total": total_shifts,
                "allocated": total_allocations,
                "unallocated": total_shifts - total_allocations
            }
        })
        
    except Exception as e:
        return api_error(f"Failed to load statistics: {str(e)}", status_code=500)