from App.models import Student, User, Request, Shift
from App.database import db
from datetime import datetime
from App.controllers.notification import (
    create_notification, 
    notify_request_submitted,
    notify_shift_approval,
    notify_shift_rejection,
    notify_admin_new_request,
    Notification
)
from App.utils.time_utils import trinidad_now, convert_to_trinidad_time
from App.models import Allocation, Shift
from datetime import datetime, timedelta
from App.models import HelpDeskAssistant

def get_all_requests():
    """Get all requests grouped by student"""
    # Get all students who have requests
    students_with_requests = db.session.query(Student).join(
        Request, Student.username == Request.username
    ).distinct().all()
    
    result = []
    for student in students_with_requests:
        # Basic student info
        from App.utils.profile_images import resolve_profile_image
        profile_image = resolve_profile_image(getattr(student, 'profile_data', None))
        
        student_data = {
            "id": student.username,
            "name": student.get_name(),
            "role": "Student Assistant",
            "id_number": student.username,
            "image": profile_image,
            "requests": []
        }
        
        # Get all requests for this student
        requests = Request.query.filter_by(username=student.username).order_by(
            Request.created_at.desc()
        ).all()
        
        for req in requests:
            request_data = {
                "id": req.id,
                "date": req.date.strftime("%B %d, %Y") if req.date else "Unknown",
                "time_slot": req.time_slot,
                "reason": req.reason,
                "status": req.status,
                "created_at": req.created_at.strftime("%B %d, %Y, %I:%M %p")
            }
            student_data["requests"].append(request_data)
        
        # Only add students who have requests
        if student_data["requests"]:
            result.append(student_data)
    
    return result

def get_student_requests(username):
    """Get all requests for a specific student"""
    requests = Request.query.filter_by(username=username).order_by(
        Request.created_at.desc()
    ).all()
    
    result = []
    for req in requests:
        request_data = {
            "id": req.id,
            "shift_date": req.date.strftime("%d %b") if req.date else "Unknown",
            "shift_time": req.time_slot,
            "submission_date": req.created_at.strftime("%B %d, %Y, %I:%M %p"),
            "status": req.status,
            "reason": req.reason,
            "replacement": req.replacement
        }
        result.append(request_data)
    
    return result

def approve_request(request_id):
    """Approve a request"""
    request = Request.query.get(request_id)
    if not request:
        return False, "Request not found"
    
    request.status = "APPROVED"
    request.approved_at = trinidad_now()
    db.session.add(request)
    
    # Create notification for the student
    shift_details = request.time_slot
    if request.date:
        shift_details = f"{request.date.strftime('%A, %b %d')}, {request.time_slot}"
        
    notify_shift_approval(request.username, shift_details)
    
    db.session.commit()
    return True, "Request approved successfully"

def reject_request(request_id):
    """Reject a request"""
    request = Request.query.get(request_id)
    if not request:
        return False, "Request not found"
    
    request.status = "REJECTED"
    request.rejected_at = trinidad_now()
    db.session.add(request)
    
    # Create notification for the student
    shift_details = request.time_slot
    if request.date:
        shift_details = f"{request.date.strftime('%A, %b %d')}, {request.time_slot}"
        
    notify_shift_rejection(request.username, shift_details)
    
    db.session.commit()
    return True, "Request rejected successfully"

def create_student_request(username, shift_id, reason, replacement=None):
    """Create a new request for a student"""
    # Get the shift details if a shift_id is provided
    shift = None
    shift_date = None
    time_slot = None
    
    if shift_id:
        shift = Shift.query.get(shift_id)
        if not shift:
            return False, "Shift not found"
        
        shift_date = shift.date
        time_slot = f"{shift.start_time.strftime('%I:%M %p')} to {shift.end_time.strftime('%I:%M %p')}"
    else:
        # If no shift_id is provided, the time_slot should be provided directly
        time_slot = "Custom Time"
    
    # Create the request
    request = Request(
        username=username,
        shift_id=shift_id,
        date=shift_date,
        time_slot=time_slot,
        reason=reason,
        replacement=replacement,
        status="PENDING"
    )
    
    db.session.add(request)
    
    # Create notification for the student
    shift_details = time_slot
    if shift_date:
        shift_details = f"{shift_date.strftime('%A, %b %d')}, {time_slot}"
        
    notify_request_submitted(username, shift_details)
    
    # Create notification for admin users
    student = Student.query.get(username)
    student_name = student.get_name() if student else username
    
    # Notify all admins
    admin_users = User.query.filter_by(type='admin').all()
    for admin in admin_users:
        notify_admin_new_request(
            admin.username, 
            student_name, 
            username, 
            shift_details
        )
    
    db.session.commit()
    return True, "Request submitted successfully"

def cancel_request(request_id, username):
    """Cancel a pending request"""
    request = Request.query.get(request_id)
    if not request:
        return False, "Request not found"
    
    # Verify the request belongs to the student
    if request.username != username:
        return False, "Unauthorized"
    
    # Only allow canceling pending requests
    if request.status != "PENDING":
        return False, f"Cannot cancel a request with status: {request.status}"
    
    # Delete the request
    db.session.delete(request)
    db.session.commit()
    
    return True, "Request cancelled successfully"

def get_available_shifts_for_student(username):
    """Get shifts the student is assigned to for creating requests"""
    
    # Get future allocations for this student (next 2 weeks)
    now = trinidad_now()
    two_weeks_later = now + timedelta(days=14)
    
    allocations = db.session.query(Allocation, Shift).join(
        Shift, Allocation.shift_id == Shift.id
    ).filter(
        Allocation.username == username,
        Shift.date >= now,
        Shift.date <= two_weeks_later
    ).order_by(Shift.date, Shift.start_time).all()
    
    result = []
    for allocation, shift in allocations:
        # Check if there's already a pending request for this shift
        existing_request = Request.query.filter_by(
            username=username,
            shift_id=shift.id,
            status="PENDING"
        ).first()
        
        if not existing_request:
            day_name = shift.date.strftime("%a")
            shift_data = {
                "id": shift.id,
                "day": day_name,
                "date": shift.date.strftime("%d %b"),
                "time": f"{shift.start_time.strftime('%I:%M %p')} to {shift.end_time.strftime('%I:%M %p')}"
            }
            result.append(shift_data)
    
    return result

def get_available_replacements(username):
    """Get potential replacement assistants"""
    
    # Get all active assistants except the current user
    assistants = db.session.query(Student, HelpDeskAssistant).join(
        HelpDeskAssistant, Student.username == HelpDeskAssistant.username
    ).filter(
        HelpDeskAssistant.active == True,
        HelpDeskAssistant.username != username
    ).all()
    
    result = []
    for student, assistant in assistants:
        replacement = {
            "id": student.username,
            "name": student.get_name()
        }
        result.append(replacement)
    
    return result

def get_pending_requests_count():
    """Return count of pending shift requests."""
    return Request.query.filter_by(status='PENDING').count()