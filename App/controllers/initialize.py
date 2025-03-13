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
from App.models import Notification, Student, HelpDeskAssistant, User, Shift, TimeEntry
from App.database import db
from datetime import datetime, timedelta
from sqlalchemy import text

def initialize():
    db.drop_all()
    db.create_all()
    
    # Create default admin account
    admin = create_user('a', '123', type='admin')
    
    # Create default student account
    student = create_user('8', 'a', type='student')
    
    # Directly use SQL to add student record without SQLAlchemy ORM
    db.session.execute(text("INSERT OR IGNORE INTO student (username, degree, name) VALUES ('8', 'BSc', 'Default Student')"))
    db.session.commit()
    
    # Create help desk assistant
    db.session.execute(text("INSERT OR IGNORE INTO help_desk_assistant (username, rate, active, hours_worked, hours_minimum) VALUES ('8', 20.00, 1, 0, 4)"))
    db.session.commit()

    # Create sample notifications for demo purposes
    create_sample_notifications(admin.username, student.username)
    
    # Create time entries directly
    create_direct_time_entries()
    
    print('Database initialized with default accounts:')
    print(admin.get_json(), "Password: 123")
    print(student.get_json(), "Password: a")

def create_direct_time_entries():
    """Create time entries directly without relying on sample assistants"""
    try:
        # Delete existing shifts and time entries
        Shift.query.delete()
        TimeEntry.query.delete()
        db.session.commit()
        
        # Create a few sample shifts
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Create shifts for the past 5 days
        shifts = []
        for i in range(-4, 1):  # Last 4 days + today
            day = today + timedelta(days=i)
            
            # Morning shift
            morning_start = day.replace(hour=9, minute=0)
            morning_end = day.replace(hour=12, minute=0)
            morning_shift = Shift(day, morning_start, morning_end)
            db.session.add(morning_shift)
            db.session.flush()  # Get ID without full commit
            shifts.append(morning_shift)
            
            # Afternoon shift
            afternoon_start = day.replace(hour=13, minute=0)
            afternoon_end = day.replace(hour=16, minute=0)
            afternoon_shift = Shift(day, afternoon_start, afternoon_end)
            db.session.add(afternoon_shift)
            db.session.flush()  # Get ID without full commit
            shifts.append(afternoon_shift)
        
        db.session.commit()
        
        # Create time entries
        for i, shift in enumerate(shifts):
            # Skip some shifts to simulate not working every shift
            if i % 3 == 0:
                continue
                
            # Determine status
            is_today = shift.date.date() == today.date()
            is_current_time = (is_today and 
                              shift.start_time.hour <= now.hour < shift.end_time.hour)
            
            if is_current_time:
                # Active entry (clocked in but not out)
                clock_in_time = shift.start_time + timedelta(minutes=15)
                entry = TimeEntry('8', clock_in_time, shift.id, 'active')
                db.session.add(entry)
            else:
                # Completed entry
                clock_in_time = shift.start_time + timedelta(minutes=5)
                clock_out_time = shift.end_time - timedelta(minutes=10)
                entry = TimeEntry('8', clock_in_time, shift.id, 'completed')
                entry.clock_out = clock_out_time
                db.session.add(entry)
            
        # Add one absent entry
        if shifts:
            absent_shift = shifts[0]
            absent_entry = TimeEntry('8', absent_shift.start_time, absent_shift.id, 'absent')
            db.session.add(absent_entry)
        
        db.session.commit()
        print(f"Created time entries for student '8'")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating direct time entries: {e}")
        import traceback
        traceback.print_exc()
        
def create_sample_notifications(admin_username, student_username):
    """Create sample notifications for the demo"""
    
    # Admin notifications
    create_notification(
        admin_username,
        "New volunteer request from Michelle Liu (816031284).", 
        Notification.TYPE_REQUEST
    )
    
    create_notification(
        admin_username,
        "Schedule for Week 5 has been published.", 
        Notification.TYPE_SCHEDULE
    )
    
    create_notification(
        admin_username,
        "Daniel Rasheed missed his shift on Monday.", 
        Notification.TYPE_MISSED
    )
    
    # Volunteer notifications
    notify_shift_approval(student_username, "Monday, Sept 30, 3:00 PM to 4:00 PM")
    
    notify_clock_in(student_username, "Friday, Sept 27, 3:00 PM to 4:00 PM")
    
    notify_clock_out(student_username, "Friday, Sept 27, 3:00 PM to 4:00 PM")
    
    notify_schedule_published(student_username, 5)
    
    notify_shift_reminder(student_username, "Monday, Sept 30, 3:00 PM to 4:00 PM", 15)
    
    notify_request_submitted(student_username, "Tuesday, Oct 1, 11:00 AM to 12:00 PM")
    
    # Mark some notifications as read to demonstrate that functionality
    notifications = Notification.query.filter_by(username=student_username).limit(2).all()
    for notification in notifications:
        notification.is_read = True
        db.session.add(notification)
    
    db.session.commit()