from App.controllers.admin import create_admin
from App.controllers.availability import create_availability
from App.controllers.course import create_course, create_course_capability, get_all_courses
from App.controllers.help_desk_assistant import create_help_desk_assistant, get_help_desk_assistant
from App.controllers.lab_assistant import create_lab_assistant, get_lab_assistant
from App.controllers.notification import *
from App.controllers.student import create_student
from App.database import db
from datetime import datetime, timedelta, time
from sqlalchemy import text
import logging, csv, os

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
    admin = create_admin('a', '123', 'helpdesk')
    logger.info(f"Created admin user: {admin.username}")
    admin = create_admin('b', '123', 'lab')
    logger.info(f"Created admin user: {admin.username}")
    create_standard_courses()
    skip_help_desk = os.environ.get('SKIP_HELP_DESK_SAMPLE', '').lower() in ['1', 'true', 'yes']
    if skip_help_desk:
        logger.info("Skipping help desk assistant sample data seeding due to SKIP_HELP_DESK_SAMPLE flag")
    else:
        create_help_desk_assistants()
        create_help_desk_assistants_availability()
        create_help_desk_assistants_course_capabilities()
    create_lab_assistants()
    create_lab_assistants_availability()
    
    if skip_help_desk:
        logger.info('Database initialized successfully (help desk assistant sample data skipped)')
    else:
        logger.info('Database initialized successfully with all sample data')


def create_standard_courses():
    """Create all standard courses in the database"""
    logger.info("Creating standard courses")
    
    # First, check if courses already exist
    existing_courses = get_all_courses()
    if existing_courses:
        for course in existing_courses:
            db.session.delete(course)
            db.session.commit()
    
    # Create all courses from the standardized list
    try:
        with open('sample/courses.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                course = create_course(code=row['code'], name=row['name'])
        
        courses = get_all_courses()
        logger.info(f"Successfully created {len(courses)} standard courses")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating standard courses: {e}")


def create_help_desk_assistants():
    logger.info("Creating help desk assistants")
    
    # Create help desk assistants from the csv
    try:
        with open('sample/help_desk_assistants.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Create student record
                student = create_student(row['username'], row['password'], row['degree'], row['name'])
                # Create help desk assistant record
                create_help_desk_assistant(student.username)
                logger.info(f"Successfully created help desk assistant: {student.name}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating help desk assistants: {e}")


def create_help_desk_assistants_availability():
    logger.info("Creating help desk assistants availability data")
    
    # Create help desk assistant availability from the csv
    try:
        with open('sample/help_desk_assistants_availability.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Parse time strings
                start_time_parts = row['start_time'].split(':')
                end_time_parts = row['end_time'].split(':')
                
                # Create time objects
                start_time= time(int(start_time_parts[0]), int(start_time_parts[1]), int(start_time_parts[2]) if len(start_time_parts) > 2 else 0)
                end_time = time(int(end_time_parts[0]), int(end_time_parts[1]), int(end_time_parts[2]) if len(end_time_parts) > 2 else 0)
                
                assistant = get_help_desk_assistant(row['username'])
                if assistant:
                    # Create availability record
                    create_availability(row['username'], row['day_of_week'], start_time, end_time)
                else:
                    logger.error(f"Help Desk assistant {row['username']} not found for availability creation")         
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating help desk assistant availability: {e}")


def create_help_desk_assistants_course_capabilities():
    logger.info("Creating help desk assistants course capability data")
    
    # Create help desk assistant course capabilities from the csv
    try:
        with open('sample/help_desk_assistants_courses.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                assistant = get_help_desk_assistant(row['username'])
                if assistant:
                    # Create course capability record
                    create_course_capability(row['username'], row['code'])
                else:
                    logger.error(f"Help Desk assistant {row['username']} not found for course capability creation")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating help desk assistant course capabilities: {e}")
    

def create_lab_assistants():
    logger.info("Creating lab assistants")
    
    # Create lab assistants from the csv
    try:
        with open('sample/lab_assistants.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Create student record
                student = create_student(row['username'], row['password'], row['degree'], row['name'])
                # Create lab assistant record
                create_lab_assistant(student.username, row['experience'])
                logger.info(f"Successfully created lab assistant: {student.name}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating lab assistants: {e}")


def create_lab_assistants_availability():
    logger.info("Creating lab assistants availability data")
    
    # Create lab assistant availability from the csv
    try:
        with open('sample/lab_assistants_availability.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Parse time strings
                start_time_parts = row['start_time'].split(':')
                end_time_parts = row['end_time'].split(':')
                
                # Create time objects
                start_time= time(int(start_time_parts[0]), int(start_time_parts[1]), int(start_time_parts[2]) if len(start_time_parts) > 2 else 0)
                end_time = time(int(end_time_parts[0]), int(end_time_parts[1]), int(end_time_parts[2]) if len(end_time_parts) > 2 else 0)
                
                assistant = get_lab_assistant(row['username'])
                if assistant:
                    # Create availability record
                    create_availability(row['username'], row['day_of_week'], start_time, end_time)
                else:
                    logger.error(f"Lab assistant {row['username']} not found for availability creation")             
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating lab assistant availability: {e}")

