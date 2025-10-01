from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from App.models import RegistrationRequest, RegistrationCourse, RegistrationAvailability, Student, User, HelpDeskAssistant, CourseCapability, Notification, Availability
from App.database import db
from App.controllers.user import create_user
from App.controllers.notification import create_notification, Notification
from App.controllers.availability import create_availability
import os
import json
from datetime import datetime, time
from App.utils.time_utils import trinidad_now, convert_to_trinidad_time


def create_registration_request(username, name, email, degree, reason=None, phone=None, transcript_url=None, profile_picture_url=None, courses=None, password=None, availability_slots=None):
    """Create a new registration request with password and availability"""
    import json
    import os
    
    try:
        existing_user = User.query.get(username)
        if existing_user:
            return False, "A user with this ID already exists"
        
        existing_request = RegistrationRequest.query.filter_by(username=username, status='PENDING').first()
        if existing_request:
            return False, "You already have a pending registration request"
        
        if isinstance(profile_picture_url, list):
            profile_picture_url = profile_picture_url[0] if profile_picture_url else None
            
        if isinstance(transcript_url, list):
            transcript_url = transcript_url[0] if transcript_url else None
        
        if not profile_picture_url or not isinstance(profile_picture_url, str):
            return False, "Profile picture URL is required"
        
        transcript_path = transcript_url  # Store the URL directly
        profile_picture_path = profile_picture_url  # Store the URL directly
        
        registration = RegistrationRequest(
            username=username,
            name=name,
            email=email,
            phone=phone,
            degree=degree,
            reason=reason,
            transcript_path=transcript_path,
            profile_picture_path=profile_picture_path,
            password=password
        )
        
        if password:
            registration.set_password(password)
        
        db.session.add(registration)
        db.session.flush()
        
        if courses:
            for course_code in courses:
                course = RegistrationCourse(registration.id, course_code)
                db.session.add(course)
        
        # Save availability slots to the registration availability table
        if availability_slots:
            for slot in availability_slots:
                try:
                    day = slot.get('day', 0)
                    start_time_str = slot.get('start_time', '9:00:00')
                    end_time_str = slot.get('end_time', '10:00:00')
                    start_time = None
                    end_time = None
                    
                    if isinstance(start_time_str, str):
                        try:
                            hour, minute, second = map(int, start_time_str.split(':'))
                            start_time = time(hour=hour, minute=minute, second=second)
                        except ValueError:
                            hour = int(start_time_str.split(':')[0])
                            start_time = time(hour=hour)
                    
                    if isinstance(end_time_str, str):
                        try:
                            hour, minute, second = map(int, end_time_str.split(':'))
                            end_time = time(hour=hour, minute=minute, second=second)
                        except ValueError:
                            hour = int(end_time_str.split(':')[0])
                            end_time = time(hour=hour)
                    
                    if start_time and end_time:
                        availability = RegistrationAvailability(registration.id, day, start_time, end_time)
                        db.session.add(availability)
                        
                except Exception as e:
                    print(f"Error creating availability slot: {e}")
                    # Continue with other slots even if this one fails
        
        admin_users = User.query.filter_by(type='admin').all()
        for admin in admin_users:
            create_notification(
                admin.username,
                f"New registration request from {name} ({username}).",
                Notification.TYPE_REQUEST
            )
        
        db.session.commit()
        return True, "Registration request submitted successfully"
    except Exception as e:
        db.session.rollback()
        print(f"Error creating registration request: {e}")
        return False, f"An error occurred: {str(e)}"
    
def approve_registration(request_id, admin_username):
    """Approve a registration request using ORM transactions."""
    try:
        registration = RegistrationRequest.query.get(request_id)
        if not registration:
            return False, "Registration request not found"
        if registration.status != 'PENDING':
            return False, f"Registration has already been {registration.status.lower()}"

        username = registration.username
        name = registration.name or username
        degree = registration.degree
        email = registration.email
        phone = registration.phone
        stored_password_hash = registration.password
        profile_picture_path = registration.profile_picture_path

        if User.query.get(username):
            return False, f"A user with username {username} already exists in the system"

        profile_data_payload = {
            "email": email,
            "phone": phone,
        }

        if profile_picture_path:
            profile_data_payload["profile_picture_url"] = profile_picture_path
            # Preserve legacy field for backwards compatibility when using static uploads
            profile_data_payload["image_filename"] = profile_picture_path

        profile_data = json.dumps(profile_data_payload)

        # Create Student only (inherits from User -> will insert into users + student tables once)
        # Provide a dummy plaintext; we'll overwrite with stored hash next.
        student = Student(username=username, password=username, degree=degree, name=name, profile_data=profile_data)
        if stored_password_hash:
            student.password = stored_password_hash  # override hashed password produced in constructor
        else:
            # Fallback: ensure hashed default if no password was supplied in request
            student.set_password(username)

        db.session.add(student)
        db.session.flush()  # ensure persistence for FK

        assistant = HelpDeskAssistant(username=username)
        if degree == 'MSc':
            assistant.rate = 35.00
        elif degree == 'BSc':
            assistant.rate = 20.00
        db.session.add(assistant)

        # Course capabilities
        registration_courses = RegistrationCourse.query.filter_by(registration_id=request_id).all()
        for rc in registration_courses:
            db.session.add(CourseCapability(assistant_username=username, course_code=rc.course_code))

        registration.approve(admin_username)
        notification = Notification(
            username=username,
            message="Your registration request has been approved. Welcome to the Help Desk team!",
            notification_type=Notification.TYPE_APPROVAL
        )
        db.session.add(notification)

        db.session.commit()

        # Availability after commit
        reg_availability = RegistrationAvailability.query.filter_by(registration_id=request_id).all()
        for reg_avail in reg_availability:
            create_availability(username, reg_avail.day_of_week, reg_avail.start_time, reg_avail.end_time)

        return True, "Registration approved successfully"
    except Exception as e:
        db.session.rollback()
        print(f"Error approving registration: {e}")
        return False, f"An error occurred: {str(e)}"
            
def reject_registration(request_id, admin_username):
    """Reject a registration request without creating any user accounts"""
    try:
        registration = RegistrationRequest.query.get(request_id)
        if not registration:
            return False, "Registration request not found"
        
        if registration.status != 'PENDING':
            return False, f"Registration has already been {registration.status.lower()}"
        
        registration.status = 'REJECTED'
        registration.processed_at = trinidad_now()
        registration.processed_by = admin_username
        db.session.add(registration)
        db.session.commit()
        
        return True, "Registration rejected successfully"
    except Exception as e:
        db.session.rollback()
        print(f"Error rejecting registration: {e}")
        return False, f"An error occurred: {str(e)}"
    
    
def get_all_registration_requests():
    """Get all registration requests grouped by status"""
    pending = RegistrationRequest.query.filter_by(status='PENDING').order_by(RegistrationRequest.created_at.desc()).all()
    approved = RegistrationRequest.query.filter_by(status='APPROVED').order_by(RegistrationRequest.processed_at.desc()).all()
    rejected = RegistrationRequest.query.filter_by(status='REJECTED').order_by(RegistrationRequest.processed_at.desc()).all()
    
    return {
        'pending': pending,
        'approved': approved,
        'rejected': rejected
    }

def get_pending_registrations():
    """Return list of pending registration requests."""
    return RegistrationRequest.query.filter_by(status='PENDING').order_by(RegistrationRequest.created_at.desc()).all()

def get_pending_registrations_count():
    """Return count of pending registration requests."""
    return RegistrationRequest.query.filter_by(status='PENDING').count()

def get_registration_request(request_id):
    """Get a specific registration request by ID"""
    registration = RegistrationRequest.query.get(request_id)
    if not registration:
        return None
    
    # Get the courses associated with this request
    courses = RegistrationCourse.query.filter_by(registration_id=request_id).all()
    course_codes = [course.course_code for course in courses]
    
    # Build full registration data
    registration_data = registration.get_json()
    registration_data['course_codes'] = course_codes
    
    return registration_data

