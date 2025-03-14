from App.models import (
    Student, HelpDeskAssistant, Course, CourseCapability, 
    Availability, Allocation, User
)
from App.database import db
from datetime import time, datetime, timedelta
from App.controllers.user import create_user

def create_sample_student(username, password, name, degree='BSc'):
    """Helper function to create a student account"""
    try:
        # Check if user already exists
        existing_user = User.query.get(username)
        
        if not existing_user:
            # Create user account first
            user = create_user(username, password, type='student')
        
        # Check if student already exists
        student_model = Student.query.get(username)
        if not student_model:
            # Just create a new student record with the given attributes
            student_model = Student(username, password, degree, name)
            db.session.add(student_model)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Error creating student model: {e}")
                
                # Try to get the student again, it might have been created indirectly
                student_model = Student.query.get(username)
                if student_model:
                    student_model.degree = degree
                    student_model.name = name
                    db.session.add(student_model)
                    db.session.commit()
        else:
            # Update student info
            student_model.degree = degree
            student_model.name = name
            db.session.add(student_model)
            db.session.commit()
        
        # Create help desk assistant record if it doesn't exist
        assistant = HelpDeskAssistant.query.get(username)
        if not assistant:
            assistant = HelpDeskAssistant(username)
            db.session.add(assistant)
            db.session.commit()
        
        return assistant
    except Exception as e:
        db.session.rollback()
        print(f"Error creating sample student {username}: {e}")
        raise

def add_sample_availabilities(username, availabilities):
    """Add sample availability times for a student
    
    availabilities format: [(day_of_week, start_hour, end_hour), ...]
    day_of_week: 0=Monday, 1=Tuesday, etc.
    """
    for day, start_hour, end_hour in availabilities:
        start_time = time(hour=start_hour)
        end_time = time(hour=end_hour)
        availability = Availability(username, day, start_time, end_time)
        db.session.add(availability)
    
    db.session.commit()

def add_sample_course_capabilities(username, course_codes):
    """Add sample course capabilities for a student"""
    assistant = HelpDeskAssistant.query.get(username)
    if assistant:
        for code in course_codes:
            # Make sure course exists first
            course = Course.query.get(code)
            if not course:
                course = Course(code, f"Course {code}")
                db.session.add(course)
                db.session.flush()
            
            # Add capability
            capability = CourseCapability(username, code)
            db.session.add(capability)
    
    db.session.commit()
  
def add_sample_time_entries():
    """Add sample time entries for attendance records"""
    from datetime import datetime, timedelta
    from App.models import TimeEntry, Shift
    
    # Get all assistant usernames
    assistants = HelpDeskAssistant.query.all()
    usernames = [assistant.username for assistant in assistants]
    
    # Create sample shifts if none exist
    shifts = Shift.query.all()
    if not shifts:
        # Create a few sample shifts
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        for day_offset in range(-5, 1):  # Last 5 days + today
            day = today + timedelta(days=day_offset)
            
            # Morning shift
            morning_start = day.replace(hour=9, minute=0)
            morning_end = day.replace(hour=12, minute=0)
            morning_shift = Shift(day, morning_start, morning_end)
            db.session.add(morning_shift)
            
            # Afternoon shift
            afternoon_start = day.replace(hour=13, minute=0)
            afternoon_end = day.replace(hour=16, minute=0)
            afternoon_shift = Shift(day, afternoon_start, afternoon_end)
            db.session.add(afternoon_shift)
        
        db.session.commit()
        shifts = Shift.query.all()
    
    # Delete existing time entries to avoid duplicates
    TimeEntry.query.delete()
    db.session.commit()
    
    # Create time entries for each assistant
    for i, username in enumerate(usernames):
        # Add entries for the last 7 days
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for day_offset in range(-6, 1):  # Last 6 days + today
            day = today + timedelta(days=day_offset)
            
            # Skip weekends
            if day.weekday() >= 5:  # 5=Saturday, 6=Sunday
                continue
            
            # Alternate between morning, afternoon, and full-day shifts
            pattern = (i + day_offset) % 3
            
            # Find appropriate shifts
            day_shifts = [s for s in shifts if s.date.date() == day.date()]
            if not day_shifts:
                continue
            
            morning_shifts = [s for s in day_shifts if s.start_time.hour < 12]
            afternoon_shifts = [s for s in day_shifts if s.start_time.hour >= 12]
            
            morning_shift = morning_shifts[0] if morning_shifts else None
            afternoon_shift = afternoon_shifts[0] if afternoon_shifts else None
            
            # Create time entries based on pattern
            if pattern == 0 and morning_shift:  # Morning shift
                # Clock in between 8:45 and 9:15
                random_minutes = (i * 7 + day_offset) % 30 - 15
                clock_in = morning_shift.start_time + timedelta(minutes=random_minutes)
                
                # Clock out between 11:45 and 12:15
                random_minutes = (i * 13 + day_offset) % 30 - 15
                clock_out = morning_shift.end_time + timedelta(minutes=random_minutes)
                
                # Create time entry
                entry = TimeEntry(username, clock_in, morning_shift.id, 'completed')
                entry.clock_out = clock_out
                db.session.add(entry)
                
            elif pattern == 1 and afternoon_shift:  # Afternoon shift
                # Clock in between 12:45 and 13:15
                random_minutes = (i * 11 + day_offset) % 30 - 15
                clock_in = afternoon_shift.start_time + timedelta(minutes=random_minutes)
                
                # Clock out between 15:45 and 16:15
                random_minutes = (i * 5 + day_offset) % 30 - 15
                clock_out = afternoon_shift.end_time + timedelta(minutes=random_minutes)
                
                # Create time entry
                entry = TimeEntry(username, clock_in, afternoon_shift.id, 'completed')
                entry.clock_out = clock_out
                db.session.add(entry)
                
            elif pattern == 2 and morning_shift and afternoon_shift:  # Full day
                # Clock in for morning
                random_minutes = (i * 7 + day_offset) % 20 - 10
                clock_in = morning_shift.start_time + timedelta(minutes=random_minutes)
                
                # Clock out for morning
                random_minutes = (i * 13 + day_offset) % 10 - 5
                clock_out = morning_shift.end_time + timedelta(minutes=random_minutes)
                
                # Create morning entry
                entry = TimeEntry(username, clock_in, morning_shift.id, 'completed')
                entry.clock_out = clock_out
                db.session.add(entry)
                
                # Clock in for afternoon
                random_minutes = (i * 11 + day_offset) % 10 - 5
                clock_in = afternoon_shift.start_time + timedelta(minutes=random_minutes)
                
                # Clock out for afternoon
                random_minutes = (i * 5 + day_offset) % 20 - 10
                clock_out = afternoon_shift.end_time + timedelta(minutes=random_minutes)
                
                # Create afternoon entry
                entry = TimeEntry(username, clock_in, afternoon_shift.id, 'completed')
                entry.clock_out = clock_out
                db.session.add(entry)
    
    # Add a couple of active entries for today
    today = datetime.utcnow()
    current_hour = today.hour
    
    # Find current shifts
    today_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
    today_shifts = [s for s in shifts if s.date.date() == today_date.date()]
    
    if today_shifts and current_hour >= 9 and current_hour < 17:
        # Determine which shift is active
        active_shift = None
        for shift in today_shifts:
            if shift.start_time.hour <= current_hour < shift.end_time.hour:
                active_shift = shift
                break
        
        if active_shift:
            # Add active time entry for first user
            if usernames:
                random_minutes = (hash(usernames[0]) % 30)
                clock_in = active_shift.start_time + timedelta(minutes=random_minutes)
                
                entry = TimeEntry(usernames[0], clock_in, active_shift.id, 'active')
                db.session.add(entry)
    
    # Add a few absent records
    if shifts and usernames:
        # Mark a couple of older shifts as absent
        older_shifts = [s for s in shifts if s.date < today_date]
        if older_shifts:
            for i in range(min(3, len(older_shifts))):
                if i < len(usernames):
                    shift = older_shifts[i]
                    entry = TimeEntry(usernames[i], shift.start_time, shift.id, 'absent')
                    db.session.add(entry)
    
    db.session.commit()
    
    print(f"Added sample time entries for {len(usernames)} assistants")

def initialize_sample_assistants():
    """Create sample assistant accounts and data"""
    try:
        # Create sample courses first
        courses = [
            ('COMP3602', 'Object-Oriented Programming 2'),
            ('COMP3603', 'Human-Computer Interaction'),
            ('COMP3605', 'Introduction to Data Analytics'), 
            ('COMP3607', 'Object-Oriented Programming 3'),
            ('COMP3613', 'Software Engineering')
        ]
        
        for code, name in courses:
            existing_course = Course.query.get(code)
            if not existing_course:
                course = Course(code, name)
                db.session.add(course)
        
        db.session.commit()
        
        # Create student assistants
        assistants = [
            {
                'username': '816031872',
                'password': 'password123',
                'name': 'Liam Johnson',
                'degree': 'BSc',
                'courses': ['COMP3602', 'COMP3603', 'COMP3605', 'COMP3607', 'COMP3613'],
                'availabilities': [
                    (0, 10, 11), (0, 13, 15), (0, 15, 16),  # Monday
                    (1, 10, 12), (1, 13, 15),               # Tuesday
                    (2, 10, 11), (2, 13, 14),               # Wednesday
                    (3, 9, 13),                             # Thursday
                    (4, 10, 12), (4, 14, 16)                # Friday
                ]
            },
            # ... other assistants remain the same
        ]
        
        for assistant_data in assistants:
            try:
                # Check if user already exists
                existing_user = User.query.get(assistant_data['username'])
                if existing_user:
                    print(f"User {assistant_data['username']} already exists, updating information...")
                    
                    # Update the student record if needed
                    student = Student.query.get(assistant_data['username'])
                    if student:
                        student.name = assistant_data['name']
                        student.degree = assistant_data['degree']
                        db.session.add(student)
                        
                    # Ensure there's a help desk assistant record
                    assistant = HelpDeskAssistant.query.get(assistant_data['username'])
                    if not assistant:
                        assistant = HelpDeskAssistant(assistant_data['username'])
                        db.session.add(assistant)
                        
                    db.session.commit()
                else:
                    # Create new student and assistant
                    assistant = create_sample_student(
                        assistant_data['username'],
                        assistant_data['password'],
                        assistant_data['name'],
                        assistant_data['degree']
                    )
                
                # Add course capabilities (clear existing ones first)
                existing_capabilities = CourseCapability.query.filter_by(
                    assistant_username=assistant_data['username']
                ).all()
                
                for cap in existing_capabilities:
                    db.session.delete(cap)
                db.session.commit()
                
                add_sample_course_capabilities(
                    assistant_data['username'], 
                    assistant_data['courses']
                )
                
                # Add availabilities (clear existing ones first)
                existing_availabilities = Availability.query.filter_by(
                    username=assistant_data['username']
                ).all()
                
                for avail in existing_availabilities:
                    db.session.delete(avail)
                db.session.commit()
                
                add_sample_availabilities(
                    assistant_data['username'],
                    assistant_data['availabilities']
                )
                
            except Exception as e:
                print(f"Error processing assistant {assistant_data['username']}: {e}")
                db.session.rollback()
        
        print("Sample assistants created or updated successfully!")
    except Exception as e:
        db.session.rollback()
        print(f"Error initializing sample assistants: {e}")
        raise