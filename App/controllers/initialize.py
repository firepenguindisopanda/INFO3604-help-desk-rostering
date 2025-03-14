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
from App.models import (
    Notification, Student, HelpDeskAssistant, User, Shift, TimeEntry, 
    Request, Course, RegistrationRequest, RegistrationCourse
)
from App.database import db
from datetime import datetime, timedelta, time
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
    
    # Create sample courses
    create_sample_courses()
    
    # Create sample registration requests
    create_sample_registration_requests()
    
    print('Database initialized with default accounts:')
    print(admin.get_json(), "Password: 123")
    print(student.get_json(), "Password: a")

def create_direct_time_entries():
    """Create time entries directly without relying on sample assistants"""
    try:
        # Delete existing time entries
        TimeEntry.query.delete()
        db.session.commit()
        
        # Get current date and time
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Create entries for the past 14 days
        for day_offset in range(14, -1, -1):  # From 14 days ago to today
            entry_date = today - timedelta(days=day_offset)
            
            # Skip weekends
            if entry_date.weekday() >= 5:  # Saturday or Sunday
                continue
                
            # Morning shift (9am-12pm)
            morning_start = entry_date.replace(hour=9, minute=0)
            morning_end = entry_date.replace(hour=12, minute=0)
            
            # Check if shifts exist for this day
            morning_shift = Shift.query.filter(
                Shift.date == entry_date.date(),
                Shift.start_time == morning_start
            ).first()
            
            if not morning_shift:
                # Create the shift if it doesn't exist
                morning_shift = Shift(entry_date, morning_start, morning_end)
                db.session.add(morning_shift)
                db.session.flush()  # Get ID without committing
            
            # Afternoon shift (1pm-4pm)
            afternoon_start = entry_date.replace(hour=13, minute=0)
            afternoon_end = entry_date.replace(hour=16, minute=0)
            
            afternoon_shift = Shift.query.filter(
                Shift.date == entry_date.date(),
                Shift.start_time == afternoon_start
            ).first()
            
            if not afternoon_shift:
                # Create the shift if it doesn't exist
                afternoon_shift = Shift(entry_date, afternoon_start, afternoon_end)
                db.session.add(afternoon_shift)
                db.session.flush()
                
            # Create time entries based on a pattern
            if day_offset % 3 == 0:
                # Morning shift only
                morning_in = morning_start + timedelta(minutes=15)  # Clock in at 9:15
                morning_out = morning_end - timedelta(minutes=10)   # Clock out at 11:50
                
                # For days in the past, create completed entries
                if entry_date < today:
                    entry = TimeEntry('8', morning_in, morning_shift.id, 'completed')
                    entry.clock_out = morning_out
                    db.session.add(entry)
                # For today, potentially create an active entry
                elif entry_date.date() == today.date() and now >= morning_start and now <= morning_end:
                    entry = TimeEntry('8', morning_start + timedelta(minutes=15), morning_shift.id, 'active')
                    db.session.add(entry)
                
            elif day_offset % 3 == 1:
                # Afternoon shift only
                afternoon_in = afternoon_start + timedelta(minutes=5)  # Clock in at 1:05
                afternoon_out = afternoon_end - timedelta(minutes=5)   # Clock out at 3:55
                
                # For days in the past, create completed entries
                if entry_date < today:
                    entry = TimeEntry('8', afternoon_in, afternoon_shift.id, 'completed')
                    entry.clock_out = afternoon_out
                    db.session.add(entry)
                # For today, potentially create an active entry
                elif entry_date.date() == today.date() and now >= afternoon_start and now <= afternoon_end:
                    entry = TimeEntry('8', afternoon_start + timedelta(minutes=5), afternoon_shift.id, 'active')
                    db.session.add(entry)
                
            elif day_offset % 3 == 2:
                # Both shifts (full day)
                if entry_date < today:
                    # Morning entry
                    morning_in = morning_start + timedelta(minutes=10)
                    morning_out = morning_end - timedelta(minutes=15)
                    morning_entry = TimeEntry('8', morning_in, morning_shift.id, 'completed')
                    morning_entry.clock_out = morning_out
                    db.session.add(morning_entry)
                    
                    # Afternoon entry
                    afternoon_in = afternoon_start + timedelta(minutes=10)
                    afternoon_out = afternoon_end - timedelta(minutes=15)
                    afternoon_entry = TimeEntry('8', afternoon_in, afternoon_shift.id, 'completed')
                    afternoon_entry.clock_out = afternoon_out
                    db.session.add(afternoon_entry)
                # For today, potentially create active entries based on current time
                elif entry_date.date() == today.date():
                    if now >= morning_start and now <= morning_end:
                        entry = TimeEntry('8', morning_start + timedelta(minutes=10), morning_shift.id, 'active')
                        db.session.add(entry)
                    elif now > morning_end and now < afternoon_start:
                        # Morning completed, afternoon not started
                        morning_in = morning_start + timedelta(minutes=10)
                        morning_out = morning_end - timedelta(minutes=15)
                        morning_entry = TimeEntry('8', morning_in, morning_shift.id, 'completed')
                        morning_entry.clock_out = morning_out
                        db.session.add(morning_entry)
                    elif now >= afternoon_start and now <= afternoon_end:
                        # Morning completed, afternoon active
                        morning_in = morning_start + timedelta(minutes=10)
                        morning_out = morning_end - timedelta(minutes=15)
                        morning_entry = TimeEntry('8', morning_in, morning_shift.id, 'completed')
                        morning_entry.clock_out = morning_out
                        db.session.add(morning_entry)
                        
                        afternoon_entry = TimeEntry('8', afternoon_start + timedelta(minutes=10), afternoon_shift.id, 'active')
                        db.session.add(afternoon_entry)
                        
        # Add one absent entry for demonstration
        # Choose a day from last week
        absent_date = today - timedelta(days=7)  # One week ago
        absent_shift = Shift.query.filter(
            Shift.date == absent_date.date(),
            Shift.start_time == absent_date.replace(hour=9, minute=0)
        ).first()
        
        if absent_shift:
            absent_entry = TimeEntry('8', absent_shift.start_time, absent_shift.id, 'absent')
            db.session.add(absent_entry)
        
        db.session.commit()
        print(f"Created sample time entries for the past 14 days")
        
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error creating direct time entries: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_sample_courses():
    """Create sample courses"""
    courses = [
        ('COMP3602', 'Object-Oriented Programming 2'),
        ('COMP3603', 'Human-Computer Interaction'),
        ('COMP3605', 'Introduction to Data Analytics'), 
        ('COMP3607', 'Object-Oriented Programming 3'),
        ('COMP3613', 'Software Engineering'),
        ('COMP3609', 'Game Programming'),
        ('COMP3610', 'Database Systems'),
        ('COMP3611', 'Artificial Intelligence')
    ]
    
    for code, name in courses:
        existing_course = Course.query.get(code)
        if not existing_course:
            course = Course(code, name)
            db.session.add(course)
    
    db.session.commit()
    print("Created sample courses")

def create_sample_registration_requests():
    """Create sample registration requests"""
    # First, get available courses
    courses = Course.query.all()
    course_codes = [course.code for course in courses]
    
    # Create a few registration requests with different statuses
    registration_data = [
        {
            'username': '816031001',
            'name': 'Jane Smith',
            'email': 'jane.smith@my.uwi.edu',
            'phone': '555-1234',
            'degree': 'BSc',
            'reason': 'I would like to join the Help Desk team to gain experience working with peers and improve my communication skills while reinforcing my programming knowledge.',
            'status': 'PENDING',
            'courses': course_codes[:3]  # First 3 courses
        },
        {
            'username': '816031002',
            'name': 'John Davis',
            'email': 'john.davis@my.uwi.edu',
            'phone': '555-5678',
            'degree': 'MSc',
            'reason': 'Having completed my BSc in Computer Science, I believe I can contribute effectively as a senior Help Desk Assistant while pursuing my graduate studies.',
            'status': 'APPROVED',
            'courses': course_codes[2:5]  # Courses 3-5
        },
        {
            'username': '816031003',
            'name': 'Michael Brown',
            'email': 'michael.brown@my.uwi.edu',
            'phone': '555-9012',
            'degree': 'BSc',
            'reason': 'I am passionate about helping others and would like to use my programming knowledge to assist fellow students.',
            'status': 'REJECTED',
            'courses': course_codes[1:4]  # Courses 2-4
        }
    ]
    
    for data in registration_data:
        # Create registration request
        registration = RegistrationRequest(
            username=data['username'],
            name=data['name'],
            email=data['email'],
            phone=data['phone'],
            degree=data['degree'],
            reason=data['reason']
        )
        
        # Set status directly (should normally use the approve/reject methods)
        if data['status'] != 'PENDING':
            registration.status = data['status']
            registration.processed_at = datetime.utcnow() - timedelta(days=3)
            registration.processed_by = 'a'  # Admin username
        
        db.session.add(registration)
        db.session.flush()  # Get ID without committing
        
        # Add selected courses
        for course_code in data['courses']:
            reg_course = RegistrationCourse(registration.id, course_code)
            db.session.add(reg_course)
    
    db.session.commit()
    print("Created sample registration requests")

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
    
    # Add registration notification for admin
    create_notification(
        admin_username,
        "New registration request from Jane Smith (816031001).",
        Notification.TYPE_REQUEST
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