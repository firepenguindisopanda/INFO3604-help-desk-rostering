"""
Combined initialization script for the Help Desk Scheduling System.
This script initializes the database with all necessary sample data:
- Admin account
- Student accounts with availability data from Excel sheet
- Course data
- Sample shifts and allocations
- Sample time entries
- Sample requests and notifications

Usage:
    from App.controllers.initialize import initialize
    initialize()
"""

from App.controllers.user import create_user
from App.controllers.notification import (
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
    Request, Course, RegistrationRequest, RegistrationCourse,
    CourseCapability, Availability, Schedule, Allocation
)
from App.database import db
from datetime import datetime, timedelta, time
from sqlalchemy import text
import logging
from App.models.course_constants import STANDARD_COURSES

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def initialize():
    """
    Initialize the database with sample data for the help desk scheduling application.
    This combines functionality from the original initialize.py and initialize_sample_data.py.
    """
    logger.info("Starting database initialization")
    
    # Drop and recreate all tables
    db.drop_all()
    db.create_all()
    
    # Create default admin account
    admin = create_user('a', '123', type='admin')
    logger.info(f"Created admin user: {admin.username}")
    
    # Create standard courses
    create_standard_courses()
    
    # Create all student assistants with availability
    create_student_assistants()
    
    logger.info('Database initialized successfully with all sample data')

def create_standard_courses():
    """Create all standard courses in the database"""
    logger.info("Creating standard courses")
    
    # First, check if courses already exist
    existing_courses = Course.query.all()
    if existing_courses:
        logger.info(f"Found {len(existing_courses)} existing courses - skipping creation")
        return
    
    # Create all courses from the standardized list
    for code, name in STANDARD_COURSES:
        course = Course(code, name)
        db.session.add(course)
    
    # Commit the courses to the database
    try:
        db.session.commit()
        logger.info(f"Successfully created {len(STANDARD_COURSES)} standard courses")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating standard courses: {e}")

def create_student_assistants():
    """Create all student assistant accounts with their availability and course capabilities"""
    logger.info("Creating student assistants with availability data")

    # Define the student data with availability from the Excel sheet
    student_data = [
        {
            'username': '816031001',
            'name': 'Daniel Rasheed',
            'password': 'password123',
            'degree': 'BSc',
            'email': 'daniel.rasheed@my.uwi.edu',
            'courses': ['COMP3602', 'COMP3603', 'COMP3605'],
            'availabilities': [
                {'day_of_week': 0, 'start_time': '9:00:00', 'end_time': '10:00:00'},
                {'day_of_week': 2, 'start_time': '9:00:00', 'end_time': '10:00:00'},
                {'day_of_week': 0, 'start_time': '10:00:00', 'end_time': '11:00:00'},
                {'day_of_week': 2, 'start_time': '10:00:00', 'end_time': '11:00:00'},
                {'day_of_week': 2, 'start_time': '11:00:00', 'end_time': '12:00:00'}
            ]
        },
        {
            'username': '816031002',
            'name': 'Michelle Liu',
            'password': 'password123',
            'degree': 'BSc',
            'email': 'michelle.liu@my.uwi.edu',
            'courses': ['COMP3602', 'COMP3607', 'COMP3613'],
            'availabilities': [
                {'day_of_week': 0, 'start_time': '10:00:00', 'end_time': '11:00:00'},
                {'day_of_week': 3, 'start_time': '10:00:00', 'end_time': '11:00:00'},
                {'day_of_week': 0, 'start_time': '11:00:00', 'end_time': '12:00:00'},
                {'day_of_week': 3, 'start_time': '11:00:00', 'end_time': '12:00:00'}
            ]
        },
        {
            'username': '816031003',
            'name': 'Stayaan Maharaj',
            'password': 'password123',
            'degree': 'MSc',
            'email': 'stayaan.maharaj@my.uwi.edu',
            'courses': ['COMP3605', 'COMP3607', 'COMP3609', 'COMP3613'],
            'availabilities': [
                {'day_of_week': 3, 'start_time': '9:00:00', 'end_time': '10:00:00'},
                {'day_of_week': 0, 'start_time': '10:00:00', 'end_time': '11:00:00'},
                {'day_of_week': 1, 'start_time': '10:00:00', 'end_time': '11:00:00'},
                {'day_of_week': 3, 'start_time': '10:00:00', 'end_time': '11:00:00'},
                {'day_of_week': 4, 'start_time': '10:00:00', 'end_time': '11:00:00'},
                {'day_of_week': 0, 'start_time': '11:00:00', 'end_time': '12:00:00'},
                {'day_of_week': 1, 'start_time': '11:00:00', 'end_time': '12:00:00'},
                {'day_of_week': 3, 'start_time': '11:00:00', 'end_time': '12:00:00'},
                {'day_of_week': 4, 'start_time': '11:00:00', 'end_time': '12:00:00'},
                {'day_of_week': 2, 'start_time': '12:00:00', 'end_time': '13:00:00'},
                {'day_of_week': 2, 'start_time': '13:00:00', 'end_time': '14:00:00'},
                {'day_of_week': 3, 'start_time': '13:00:00', 'end_time': '14:00:00'},
                {'day_of_week': 0, 'start_time': '14:00:00', 'end_time': '15:00:00'},
                {'day_of_week': 3, 'start_time': '14:00:00', 'end_time': '15:00:00'},
                {'day_of_week': 0, 'start_time': '15:00:00', 'end_time': '16:00:00'},
                {'day_of_week': 1, 'start_time': '15:00:00', 'end_time': '16:00:00'},
                {'day_of_week': 2, 'start_time': '15:00:00', 'end_time': '16:00:00'},
                {'day_of_week': 3, 'start_time': '15:00:00', 'end_time': '16:00:00'}
            ]
        },
        {
            'username': '816031004',
            'name': 'Daniel Yatali',
            'password': 'password123',
            'degree': 'BSc',
            'email': 'daniel.yatali@my.uwi.edu',
            'courses': ['COMP3603', 'COMP3609', 'COMP2611'],
            'availabilities': [
                {'day_of_week': 4, 'start_time': '10:00:00', 'end_time': '11:00:00'},
                {'day_of_week': 1, 'start_time': '11:00:00', 'end_time': '12:00:00'},
                {'day_of_week': 4, 'start_time': '11:00:00', 'end_time': '12:00:00'},
                {'day_of_week': 0, 'start_time': '13:00:00', 'end_time': '14:00:00'},
                {'day_of_week': 1, 'start_time': '13:00:00', 'end_time': '14:00:00'}
            ]
        },
        {
            'username': '816031005',
            'name': 'Satish Maharaj',
            'password': 'password123',
            'degree': 'MSc',
            'email': 'satish.maharaj@my.uwi.edu',
            'courses': ['COMP3602', 'COMP3610', 'COMP2611'],
            'availabilities': [
                {'day_of_week': 3, 'start_time': '9:00:00', 'end_time': '10:00:00'},
                {'day_of_week': 3, 'start_time': '10:00:00', 'end_time': '11:00:00'},
                {'day_of_week': 0, 'start_time': '13:00:00', 'end_time': '14:00:00'},
                {'day_of_week': 0, 'start_time': '14:00:00', 'end_time': '15:00:00'},
                {'day_of_week': 0, 'start_time': '15:00:00', 'end_time': '16:00:00'},
                {'day_of_week': 4, 'start_time': '15:00:00', 'end_time': '16:00:00'}
            ]
        },
        {
            'username': '816031006',
            'name': 'Selena Madrey',
            'password': 'password123',
            'degree': 'BSc',
            'email': 'selena.madrey@my.uwi.edu',
            'courses': ['COMP3605', 'COMP3607', 'COMP3613'],
            'availabilities': [
                {'day_of_week': 4, 'start_time': '10:00:00', 'end_time': '11:00:00'},
                {'day_of_week': 0, 'start_time': '13:00:00', 'end_time': '14:00:00'},
                {'day_of_week': 3, 'start_time': '13:00:00', 'end_time': '14:00:00'},
                {'day_of_week': 0, 'start_time': '14:00:00', 'end_time': '15:00:00'},
                {'day_of_week': 3, 'start_time': '14:00:00', 'end_time': '15:00:00'},
                {'day_of_week': 0, 'start_time': '15:00:00', 'end_time': '16:00:00'},
                {'day_of_week': 3, 'start_time': '15:00:00', 'end_time': '16:00:00'}
            ]
        },
        {
            'username': '816031007',
            'name': 'Veron Ramkissoon',
            'password': 'password123',
            'degree': 'BSc',
            'email': 'veron.ramkissoon@my.uwi.edu',
            'courses': ['COMP3603', 'COMP3610', 'COMP2611'],
            'availabilities': [
                {'day_of_week': 0, 'start_time': '14:00:00', 'end_time': '15:00:00'},
                {'day_of_week': 0, 'start_time': '15:00:00', 'end_time': '16:00:00'},
                {'day_of_week': 1, 'start_time': '15:00:00', 'end_time': '16:00:00'},
                {'day_of_week': 2, 'start_time': '15:00:00', 'end_time': '16:00:00'}
            ]
        },
        {
            'username': '816031008',
            'name': 'Tamika Ramkissoon',
            'password': 'password123',
            'degree': 'BSc',
            'email': 'tamika.ramkissoon@my.uwi.edu',
            'courses': ['COMP3605', 'COMP3607', 'COMP2611'],
            'availabilities': [
                {'day_of_week': 4, 'start_time': '11:00:00', 'end_time': '12:00:00'},
                {'day_of_week': 4, 'start_time': '12:00:00', 'end_time': '13:00:00'},
                {'day_of_week': 2, 'start_time': '13:00:00', 'end_time': '14:00:00'},
                {'day_of_week': 0, 'start_time': '14:00:00', 'end_time': '15:00:00'},
                {'day_of_week': 2, 'start_time': '14:00:00', 'end_time': '15:00:00'},
                {'day_of_week': 0, 'start_time': '15:00:00', 'end_time': '16:00:00'},
                {'day_of_week': 2, 'start_time': '15:00:00', 'end_time': '16:00:00'}
            ]
        },
        {
            'username': '816031009',
            'name': 'Samuel Mahadeo',
            'password': 'password123',
            'degree': 'BSc',
            'email': 'samuel.mahadeo@my.uwi.edu',
            'courses': ['COMP3602', 'COMP3609', 'COMP3610'],
            'availabilities': [
                {'day_of_week': 3, 'start_time': '9:00:00', 'end_time': '10:00:00'},
                {'day_of_week': 1, 'start_time': '10:00:00', 'end_time': '11:00:00'},
                {'day_of_week': 4, 'start_time': '10:00:00', 'end_time': '11:00:00'}
            ]
        },
        {
            'username': '816031010',
            'name': 'Neha Maharaj',
            'password': 'password123',
            'degree': 'MSc',
            'email': 'neha.maharaj@my.uwi.edu',
            'courses': ['COMP3603', 'COMP3605', 'COMP3613'],
            'availabilities': [
                {'day_of_week': 2, 'start_time': '12:00:00', 'end_time': '13:00:00'},
                {'day_of_week': 2, 'start_time': '13:00:00', 'end_time': '14:00:00'},
                {'day_of_week': 3, 'start_time': '13:00:00', 'end_time': '14:00:00'},
                {'day_of_week': 2, 'start_time': '14:00:00', 'end_time': '15:00:00'},
                {'day_of_week': 3, 'start_time': '14:00:00', 'end_time': '15:00:00'},
                {'day_of_week': 2, 'start_time': '15:00:00', 'end_time': '16:00:00'},
                {'day_of_week': 3, 'start_time': '15:00:00', 'end_time': '16:00:00'}
            ]
        }
    ]
    
    # Create users and their associated data
    for student in student_data:
        try:
            # Create user account
            user = create_user(student['username'], student['password'], type='student')
            logger.info(f"Created user: {user.username}")
            
            # Create student record
            db.session.execute(
                text("INSERT OR IGNORE INTO student (username, degree, name) VALUES (:username, :degree, :name)"),
                {"username": student['username'], "degree": student['degree'], "name": student['name']}
            )
            
            # Create help desk assistant record
            rate = 35.00 if student['degree'] == 'MSc' else 20.00  # Higher rate for MSc students
            db.session.execute(
                text("INSERT OR IGNORE INTO help_desk_assistant (username, rate, active, hours_worked, hours_minimum) VALUES (:username, :rate, :active, :hours_worked, :hours_minimum)"),
                {"username": student['username'], "rate": rate, "active": 1, "hours_worked": 0, "hours_minimum": 4}
            )
            
            # Add course capabilities
            for course_code in student['courses']:
                db.session.execute(
                    text("INSERT OR IGNORE INTO course_capability (assistant_username, course_code) VALUES (:username, :course_code)"),
                    {"username": student['username'], "course_code": course_code}
                )
                
            # Add availabilities
            for avail in student['availabilities']:
                # Parse time strings
                start_time_parts = avail['start_time'].split(':')
                end_time_parts = avail['end_time'].split(':')
                
                # Create time objects
                start_time_obj = time(int(start_time_parts[0]), int(start_time_parts[1]), int(start_time_parts[2]) if len(start_time_parts) > 2 else 0)
                end_time_obj = time(int(end_time_parts[0]), int(end_time_parts[1]), int(end_time_parts[2]) if len(end_time_parts) > 2 else 0)
                
                # Create availability record
                availability = Availability(student['username'], avail['day_of_week'], start_time_obj, end_time_obj)
                db.session.add(availability)
                
            db.session.commit()
            logger.info(f"Successfully created student assistant: {student['name']}")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating student {student['username']}: {e}")
            
    logger.info(f"Created {len(student_data)} student assistants with availability data")