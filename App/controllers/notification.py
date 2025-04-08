from App.models import Notification, User
from App.database import db
from datetime import datetime

def create_notification(username, message, notification_type):
    """Create a new notification for a user"""
    notification = Notification(
        username=username,
        message=message,
        notification_type=notification_type
    )
    db.session.add(notification)
    db.session.commit()
    return notification

def get_user_notifications(username, limit=20, include_read=False):
    """Get notifications for a user, with newest first"""
    query = Notification.query.filter_by(username=username)
    
    if not include_read:
        query = query.filter_by(is_read=False)
    
    return query.order_by(Notification.created_at.desc()).limit(limit).all()

def get_notification(notification_id):
    """Get a specific notification by ID"""
    return Notification.query.get(notification_id)

def mark_notification_as_read(notification_id):
    """Mark a notification as read"""
    notification = get_notification(notification_id)
    if notification:
        notification.is_read = True
        db.session.add(notification)
        db.session.commit()
        return True
    return False

def mark_all_notifications_as_read(username):
    """Mark all notifications for a user as read"""
    notifications = Notification.query.filter_by(username=username, is_read=False).all()
    for notification in notifications:
        notification.is_read = True
        db.session.add(notification)
    db.session.commit()
    return len(notifications)

def delete_notification(notification_id):
    """Delete a notification by ID"""
    notification = get_notification(notification_id)
    if notification:
        db.session.delete(notification)
        db.session.commit()
        return True
    return False

def count_unread_notifications(username):
    """Count unread notifications for a user"""
    return Notification.query.filter_by(username=username, is_read=False).count()

# Functions to create common notification types
def notify_shift_approval(username, shift_details):
    """Notify a user that their shift change request was approved"""
    message = f"Your shift change request for {shift_details} was approved."
    return create_notification(username, message, Notification.TYPE_APPROVAL)

def notify_shift_rejection(username, shift_details):
    """Notify a user that their shift change request was rejected"""
    message = f"Your shift change request for {shift_details} was rejected."
    return create_notification(username, message, Notification.TYPE_APPROVAL)

def notify_clock_in(username, shift_details):
    """Notify a user that they clocked in for a shift"""
    message = f"You clocked in for your {shift_details} shift."
    return create_notification(username, message, Notification.TYPE_CLOCK_IN)

def notify_clock_out(username, shift_details, auto_completed=False):
    """Notify a user that they clocked out for a shift"""
    if auto_completed:
        message = f"Your shift for {shift_details} has ended and you've been automatically clocked out."
    else:
        message = f"You clocked out for your {shift_details} shift."
    return create_notification(username, message, Notification.TYPE_CLOCK_OUT)

def notify_schedule_published(username, schedule_date_range=None):
    """Notify a user that a new schedule was published"""
    if schedule_date_range:
        message = f"A new schedule for {schedule_date_range} has been published. Check out your shifts."
    else:
        message = f"A new schedule has been published. Check out your shifts for the upcoming period."
    return create_notification(username, message, Notification.TYPE_SCHEDULE)

def notify_shift_reminder(username, shift_details, minutes_before=15):
    """Notify a user about an upcoming shift"""
    message = f"Your {shift_details} shift starts in {minutes_before} minutes."
    return create_notification(username, message, Notification.TYPE_REMINDER)

def notify_request_submitted(username, shift_details):
    """Notify a user that their shift change request was submitted"""
    message = f"Your request for {shift_details} was submitted and is pending approval."
    return create_notification(username, message, Notification.TYPE_REQUEST)

def notify_missed_shift(username, shift_details):
    """Notify a user that they missed a shift"""
    message = f"You missed your {shift_details} shift."
    return create_notification(username, message, Notification.TYPE_MISSED)

def notify_availability_updated(username):
    """Notify a user that their availability was updated"""
    message = "Your availability was successfully updated."
    return create_notification(username, message, Notification.TYPE_UPDATE)

def notify_admin_new_request(admin_username, student_name, student_id, shift_details):
    """Notify an admin about a new shift change request"""
    message = f"New request from {student_name} ({student_id}) for {shift_details}."
    return create_notification(admin_username, message, Notification.TYPE_REQUEST)

def notify_all_admins(message, notification_type):
    """Send a notification to all admin users"""
    admins = User.query.filter_by(type='admin').all()
    notifications = []
    
    for admin in admins:
        notification = create_notification(admin.username, message, notification_type)
        notifications.append(notification)
    
    return notifications