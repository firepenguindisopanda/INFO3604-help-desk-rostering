from App.models import Notification, User
from App.database import db
from datetime import datetime

def create_notification(user_id, message, notification_type):
    """Create a new notification for a user"""
    notification = Notification(
        user_id=user_id,
        message=message,
        notification_type=notification_type
    )
    db.session.add(notification)
    db.session.commit()
    return notification

def get_user_notifications(user_id, limit=20, include_read=False):
    """Get notifications for a user, with newest first"""
    query = Notification.query.filter_by(user_id=user_id)
    
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

def mark_all_notifications_as_read(user_id):
    """Mark all notifications for a user as read"""
    notifications = Notification.query.filter_by(user_id=user_id, is_read=False).all()
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

def count_unread_notifications(user_id):
    """Count unread notifications for a user"""
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()

# Function to create common notification types
def notify_shift_approval(user_id, shift_details):
    message = f"Your shift change request for {shift_details} was approved."
    return create_notification(user_id, message, Notification.TYPE_APPROVAL)

def notify_shift_rejection(user_id, shift_details):
    message = f"Your shift change request for {shift_details} was rejected."
    return create_notification(user_id, message, Notification.TYPE_APPROVAL)

def notify_clock_in(user_id, shift_details):
    message = f"You clocked in for your {shift_details} shift."
    return create_notification(user_id, message, Notification.TYPE_CLOCK_IN)

def notify_clock_out(user_id, shift_details):
    message = f"You clocked out for your {shift_details} shift."
    return create_notification(user_id, message, Notification.TYPE_CLOCK_OUT)

def notify_schedule_published(user_id, week_number):
    message = f"Week {week_number} Schedule has been published. Check out your shifts for the week."
    return create_notification(user_id, message, Notification.TYPE_SCHEDULE)

def notify_shift_reminder(user_id, shift_details, minutes_before=15):
    message = f"Your {shift_details} shift starts in {minutes_before} minutes."
    return create_notification(user_id, message, Notification.TYPE_REMINDER)

def notify_request_submitted(user_id, shift_details):
    message = f"Your request for {shift_details} was submitted and is pending approval."
    return create_notification(user_id, message, Notification.TYPE_REQUEST)

def notify_missed_shift(user_id, shift_details):
    message = f"You missed your {shift_details} shift."
    return create_notification(user_id, message, Notification.TYPE_MISSED)

def notify_availability_updated(user_id):
    message = "Your availability was successfully updated."
    return create_notification(user_id, message, Notification.TYPE_UPDATE)