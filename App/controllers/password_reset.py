from App.models import User, PasswordResetRequest
from App.database import db
from App.controllers.notification import create_notification
from App.utils.time_utils import trinidad_now
from werkzeug.security import generate_password_hash

def create_password_reset_request(username, reason):
    """Create a new password reset request"""
    # Check if user exists
    user = User.query.filter_by(username=username).first()
    if not user:
        return False, "User not found"
    
    # Check if there's already a pending request
    existing_request = PasswordResetRequest.query.filter_by(
        username=username,
        status="PENDING"
    ).first()
    
    if existing_request:
        return False, "You already have a pending password reset request"
    
    # Create the request
    reset_request = PasswordResetRequest(
        username=username,
        reason=reason,
        status="PENDING",
        created_at=trinidad_now()
    )
    
    db.session.add(reset_request)
    
    # Create notification for admin users
    admin_users = User.query.filter_by(type='admin').all()
    
    user_display = f"{user.first_name} {user.last_name}" if hasattr(user, 'first_name') else username
    
    for admin in admin_users:
        # Added the notification_type parameter
        create_notification(
            username=admin.username,
            message=f"New password reset request from {user_display} (ID: {username})",
            notification_type="password_reset"
        )
    
    db.session.commit()
    return True, "Password reset request submitted successfully. Please visit the admin office to complete the process."

def get_all_password_reset_requests():
    """Get all password reset requests sorted by status and date"""
    # Get all password reset requests
    all_requests = PasswordResetRequest.query.order_by(
        PasswordResetRequest.created_at.desc()
    ).all()
    
    # Organize by status
    pending = []
    completed = []
    
    for req in all_requests:
        # Get user info
        user = User.query.filter_by(username=req.username).first()
        user_name = f"{user.first_name} {user.last_name}" if user and hasattr(user, 'first_name') else req.username
        
        request_data = {
            "id": req.id,
            "username": req.username,
            "name": user_name,
            "reason": req.reason,
            "status": req.status,
            "created_at": req.created_at,
            "processed_at": req.processed_at,
            "processed_by": req.processed_by
        }
        
        if req.status == "PENDING":
            pending.append(request_data)
        else:
            completed.append(request_data)
    
    return {
        "pending": pending,
        "completed": completed
    }

def complete_password_reset(reset_id, new_password, admin_username):
    """Complete a password reset request by setting a new password"""
    # Find the reset request
    reset_request = PasswordResetRequest.query.get(reset_id)
    if not reset_request:
        return False, "Reset request not found"
    
    if reset_request.status != "PENDING":
        return False, "This request has already been processed"
    
    # Find the user
    user = User.query.filter_by(username=reset_request.username).first()
    if not user:
        return False, "User not found"
    
    # Update the user's password
    password_hash = generate_password_hash(new_password)
    user.password = password_hash
    
    # Update the reset request
    reset_request.status = "COMPLETED"
    reset_request.processed_at = trinidad_now()
    reset_request.processed_by = admin_username
    
    # Create notification for the user with notification_type
    create_notification(
        username=reset_request.username,
        message="Your password has been reset. Please log in with your new password.",
        notification_type="password_reset"
    )
    
    db.session.commit()
    return True, "Password has been reset successfully"

def reject_password_reset(reset_id, admin_username, reason=None):
    """Reject a password reset request"""
    # Find the reset request
    reset_request = PasswordResetRequest.query.get(reset_id)
    if not reset_request:
        return False, "Reset request not found"
    
    if reset_request.status != "PENDING":
        return False, "This request has already been processed"
    
    # Update the reset request
    reset_request.status = "REJECTED"
    reset_request.processed_at = trinidad_now()
    reset_request.processed_by = admin_username
    reset_request.rejection_reason = reason
    
    # Create notification for the user with notification_type
    message = "Your password reset request has been rejected."
    if reason:
        message += f" Reason: {reason}"
    
    create_notification(
        username=reset_request.username,
        message=message,
        notification_type="password_reset"
    )
    
    db.session.commit()
    return True, "Password reset request has been rejected"