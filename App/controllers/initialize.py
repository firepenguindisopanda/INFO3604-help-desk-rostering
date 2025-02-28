from .user import create_user
from .notification import (
    create_notification,
    notify_shift_approval,
    notify_clock_in,
    notify_clock_out,
    notify_schedule_published,
    notify_shift_reminder,
    notify_request_submitted,
    notify_missed_shift,
    notify_availability_updated
)
from App.models import Notification
from App.database import db

def initialize():
    db.drop_all()
    db.create_all()
    
    # Create default admin account
    admin = admin = create_user('admin', 'admin123', role='admin')
    
    # Create default volunteer/assistant account
    volunteer = assistant = create_user('816000000', 'assistant123', role='volunteer')

    # Create sample notifications for demo purposes
    create_sample_notifications(admin.id, volunteer.id)
    
    print('Database initialized with default accounts:')
    print('Admin - username: admin, password: admin123')
    print('Volunteer - username: 816000000, password: assistant123')

def create_sample_notifications(admin_id, volunteer_id):
    """Create sample notifications for the demo"""
    
    # Admin notifications
    create_notification(
        admin_id, 
        "New volunteer request from Michelle Liu (816031284).", 
        Notification.TYPE_REQUEST
    )
    
    create_notification(
        admin_id, 
        "Schedule for Week 5 has been published.", 
        Notification.TYPE_SCHEDULE
    )
    
    create_notification(
        admin_id, 
        "Daniel Rasheed missed his shift on Monday.", 
        Notification.TYPE_MISSED
    )
    
    # Volunteer notifications
    notify_shift_approval(volunteer_id, "Monday, Sept 30, 3:00 PM to 4:00 PM")
    
    notify_clock_in(volunteer_id, "Friday, Sept 27, 3:00 PM to 4:00 PM")
    
    notify_clock_out(volunteer_id, "Friday, Sept 27, 3:00 PM to 4:00 PM")
    
    notify_schedule_published(volunteer_id, 5)
    
    notify_shift_reminder(volunteer_id, "Monday, Sept 30, 3:00 PM to 4:00 PM", 15)
    
    notify_request_submitted(volunteer_id, "Tuesday, Oct 1, 11:00 AM to 12:00 PM")
    
    # Mark some notifications as read to demonstrate that functionality
    notifications = Notification.query.filter_by(user_id=volunteer_id).limit(2).all()
    for notification in notifications:
        notification.is_read = True
        db.session.add(notification)
    
    db.session.commit()