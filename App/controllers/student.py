from datetime import datetime, time as dt_time

from App.models import Student, HelpDeskAssistant, CourseCapability, Availability, Course
from App.database import db

def create_student(username, password, degree, name):
    new_student = Student(username, password, degree, name)
    db.session.add(new_student)
    db.session.commit()
    return new_student

def get_student(username):
    return Student.query.filter_by(username=username).first()

def get_student_by_id(student_id):
    """Get student by ID"""
    return Student.query.get(student_id)

def get_student_profile_data(student):
    """Get formatted profile data for a student"""
    if not student:
        return None
    
    profile_data = {
        'id': student.username,  # Using username as the primary key
        'username': student.username,
        'name': student.name,
        'degree': student.degree,
        'email': f"{student.username}@my.uwi.edu"
    }
    
    # Check if student is a help desk assistant
    help_desk_assistant = HelpDeskAssistant.query.filter_by(username=student.username).first()
    if help_desk_assistant:
        profile_data['is_help_desk_assistant'] = True
        profile_data['help_desk_id'] = help_desk_assistant.username
        
        # Get course capabilities
        capabilities = CourseCapability.query.filter_by(
            assistant_username=help_desk_assistant.username
        ).all()
        profile_data['course_capabilities'] = [
            {'course_code': cap.course.code, 'course_name': cap.course.name}
            for cap in capabilities if cap.course
        ]
        
        # Get availability
        availability = Availability.query.filter_by(
            username=help_desk_assistant.username
        ).all()
        profile_data['availability'] = [
            {
                'day_of_week': avail.day_of_week,
                'start_time': avail.start_time.strftime('%H:%M') if avail.start_time else None,
                'end_time': avail.end_time.strftime('%H:%M') if avail.end_time else None
            }
            for avail in availability
        ]
    else:
        profile_data['is_help_desk_assistant'] = False
        profile_data['course_capabilities'] = []
        profile_data['availability'] = []
    
    return profile_data

def update_student_courses(student_id, course_codes):
    """Update student's course capabilities"""
    help_desk_assistant = HelpDeskAssistant.query.filter_by(username=student_id).first()
    if not help_desk_assistant:
        return False, "Student is not a help desk assistant"
    
    try:
        # Remove existing capabilities
        CourseCapability.query.filter_by(
            assistant_username=help_desk_assistant.username
        ).delete()
        
        # Add new capabilities
        for course_code in course_codes:
            course = Course.query.filter_by(code=course_code).first()
            if course:
                capability = CourseCapability(
                    assistant_username=help_desk_assistant.username,
                    course_code=course.code
                )
                db.session.add(capability)
        
        db.session.commit()
        return True, "Courses updated successfully"
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error updating courses: {str(e)}"

def _parse_time_string(time_str):
    """Normalize various time string formats into a time object."""
    if not time_str:
        return None

    if isinstance(time_str, dt_time):
        return time_str

    value = str(time_str).strip()
    patterns = ['%H:%M', '%H:%M:%S', '%I:%M %p', '%I:%M:%S %p']

    for pattern in patterns:
        try:
            return datetime.strptime(value, pattern).time()
        except ValueError:
            continue

    if ':' in value:
        parts = value.split(':')
        try:
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            return dt_time(hour=hour, minute=minute)
        except (ValueError, IndexError):
            pass

    return None


def update_student_availability(student_id, availability_data):
    """Update student's availability"""
    help_desk_assistant = HelpDeskAssistant.query.filter_by(username=student_id).first()
    if not help_desk_assistant:
        return False, "Student is not a help desk assistant"
    
    try:
        # Remove existing availability
        Availability.query.filter_by(
            username=help_desk_assistant.username
        ).delete()
        
        # Add new availability
        for avail_item in availability_data:
            start_time = _parse_time_string(avail_item.get('start_time'))
            end_time = _parse_time_string(avail_item.get('end_time'))

            if start_time is None or end_time is None:
                return False, "Invalid time format provided for availability."

            try:
                day_of_week = int(avail_item.get('day_of_week'))
            except (TypeError, ValueError):
                return False, "Invalid day value provided for availability."

            availability = Availability(
                username=help_desk_assistant.username,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time
            )
            db.session.add(availability)
        
        db.session.commit()
        return True, "Availability updated successfully"
        
    except Exception as e:
        db.session.rollback()
        return False, f"Error updating availability: {str(e)}"
