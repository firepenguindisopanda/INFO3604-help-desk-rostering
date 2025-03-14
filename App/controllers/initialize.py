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
from App.models import Notification, Student, HelpDeskAssistant, User, Shift, TimeEntry, Request
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
    
    # Create sample shifts and allocations
    create_sample_shifts_and_allocations()
    
    # Create time entries directly
    create_direct_time_entries()
    
    # Create sample requests
    create_sample_requests(student.username)
    
    print('Database initialized with default accounts:')
    print(admin.get_json(), "Password: 123")
    print(student.get_json(), "Password: a")

def create_sample_requests(username):
    """Create sample requests for the default student"""
    try:
        # Get some shifts to create requests for
        shifts = Shift.query.order_by(Shift.date.desc()).limit(5).all()
        
        if not shifts:
            print("No shifts found to create requests for")
            return
        
        # Create a pending request
        pending_request = Request(
            username=username,
            shift_id=shifts[0].id if shifts else None,
            date=shifts[0].date if shifts else None,
            time_slot=f"{shifts[0].start_time.strftime('%I:%M %p')} to {shifts[0].end_time.strftime('%I:%M %p')}" if shifts else "10:00 AM - 11:00 AM",
            reason="Need to attend a doctor's appointment",
            status="PENDING"
        )
        db.session.add(pending_request)
        
        # Create an approved request
        if len(shifts) > 1:
            approved_request = Request(
                username=username,
                shift_id=shifts[1].id,
                date=shifts[1].date,
                time_slot=f"{shifts[1].start_time.strftime('%I:%M %p')} to {shifts[1].end_time.strftime('%I:%M %p')}",
                reason="Family emergency",
                status="APPROVED"
            )
            approved_request.approved_at = datetime.utcnow() - timedelta(days=1)
            db.session.add(approved_request)
        
        # Create a rejected request
        if len(shifts) > 2:
            rejected_request = Request(
                username=username,
                shift_id=shifts[2].id,
                date=shifts[2].date,
                time_slot=f"{shifts[2].start_time.strftime('%I:%M %p')} to {shifts[2].end_time.strftime('%I:%M %p')}",
                reason="Academic conference",
                status="REJECTED"
            )
            rejected_request.rejected_at = datetime.utcnow() - timedelta(days=2)
            db.session.add(rejected_request)
        
        db.session.commit()
        print(f"Created sample requests for {username}")
    except Exception as e:
        db.session.rollback()
        print(f"Error creating sample requests: {e}")

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
    
    
    
def create_sample_shifts_and_allocations():
    """Create sample shifts and allocations for the next two weeks"""
    try:
        from App.models import Schedule, Shift, Allocation
        from datetime import datetime, timedelta
        
        # Delete existing schedules
        Schedule.query.delete()
        
        # Get the current time
        now = datetime.utcnow()
        
        # Create a schedule for the current week
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - timedelta(days=today.weekday())  # Monday of current week
        
        # Create a new schedule
        current_week = Schedule(
            week_number=now.isocalendar()[1],  # ISO week number
            start_date=week_start,
            end_date=week_start + timedelta(days=6)
        )
        current_week.is_published = True
        db.session.add(current_week)
        db.session.flush()  # Get ID without committing
        
        # Create a schedule for next week
        next_week_start = week_start + timedelta(days=7)
        next_week = Schedule(
            week_number=now.isocalendar()[1] + 1,
            start_date=next_week_start,
            end_date=next_week_start + timedelta(days=6)
        )
        next_week.is_published = True
        db.session.add(next_week)
        db.session.flush()
        
        # Create shifts for this week and next week (2 weeks total)
        schedules = [current_week, next_week]
        
        # Get the default student
        default_username = '8'
        
        for schedule in schedules:
            week_start = schedule.start_date
            
            # Create shifts for each day (Monday-Friday)
            for day in range(5):  # 0=Monday, 4=Friday
                shift_date = week_start + timedelta(days=day)
                
                # Morning shift (9am-12pm)
                morning_start = datetime.combine(shift_date.date(), datetime.min.time()) + timedelta(hours=9)
                morning_end = datetime.combine(shift_date.date(), datetime.min.time()) + timedelta(hours=12)
                
                morning_shift = Shift(shift_date, morning_start, morning_end, schedule.id)
                db.session.add(morning_shift)
                db.session.flush()
                
                # Afternoon shift (1pm-4pm)
                afternoon_start = datetime.combine(shift_date.date(), datetime.min.time()) + timedelta(hours=13)
                afternoon_end = datetime.combine(shift_date.date(), datetime.min.time()) + timedelta(hours=16)
                
                afternoon_shift = Shift(shift_date, afternoon_start, afternoon_end, schedule.id)
                db.session.add(afternoon_shift)
                db.session.flush()
                
                # Hourly shifts for full schedule display
                for hour in range(9, 17):  # 9am to 4pm
                    hour_start = datetime.combine(shift_date.date(), datetime.min.time()) + timedelta(hours=hour)
                    hour_end = hour_start + timedelta(hours=1)
                    
                    hourly_shift = Shift(shift_date, hour_start, hour_end, schedule.id)
                    db.session.add(hourly_shift)
                    db.session.flush()
                    
                    # Assign the default student to some shifts (but not all)
                    if (day + hour) % 3 == 0:  # Simple pattern to assign to some shifts
                        allocation = Allocation(default_username, hourly_shift.id, schedule.id)
                        db.session.add(allocation)
        
        # Commit all the new objects
        db.session.commit()
        print("Created sample shifts and allocations for 2 weeks")
        
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error creating sample shifts and allocations: {e}")
        import traceback
        traceback.print_exc()
        return False

