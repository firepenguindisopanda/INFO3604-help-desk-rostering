from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from App.models import RegistrationRequest, RegistrationCourse, Student, User, HelpDeskAssistant, CourseCapability, Notification, Availability
from App.database import db
from App.controllers.user import create_user
from App.controllers.notification import create_notification, Notification
import os
import json
from datetime import datetime, time
from App.utils.time_utils import trinidad_now, convert_to_trinidad_time


def create_registration_request(username, name, email, degree, reason=None, phone=None, transcript_file=None, profile_picture_file=None, courses=None, password=None):
    """Create a new registration request with password"""
    import json
    import os

    try:
        existing_user = User.query.get(username)
        if existing_user:
            return False, "A user with this ID already exists"

        existing_request = RegistrationRequest.query.filter_by(username=username, status='PENDING').first()
        if existing_request:
            return False, "You already have a pending registration request"

        if isinstance(profile_picture_file, list):
            profile_picture_file = profile_picture_file[0] if profile_picture_file else None

        if isinstance(transcript_file, list):
            transcript_file = transcript_file[0] if transcript_file else None

        if not profile_picture_file or not profile_picture_file.filename:
            return False, "Profile picture is required"

        transcript_path = None
        if transcript_file and transcript_file.filename:

            filename = secure_filename(transcript_file.filename)
            timestamp = trinidad_now().strftime('%Y%m%d%H%M%S')
            filename = f"{username}_{timestamp}_{filename}"

            upload_dir = os.path.join('App', 'uploads', 'transcripts')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)

            file_path = os.path.join(upload_dir, filename)
            transcript_file.save(file_path)
            transcript_path = f"transcripts/{filename}"

        profile_picture_path = None

        filename = secure_filename(profile_picture_file.filename)
        timestamp = trinidad_now().strftime('%Y%m%d%H%M%S')
        filename = f"{username}_{timestamp}_{filename}"

        upload_dir = os.path.join('App', 'static', 'uploads', 'profile_pictures')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)

        file_path = os.path.join(upload_dir, filename)
        profile_picture_file.save(file_path)
        profile_picture_path = f"uploads/profile_pictures/{filename}"




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
        stored_password = registration.password
        profile_picture_path = registration.profile_picture_path

        if User.query.get(username):
            return False, f"A user with username {username} already exists in the system"

        raw_or_hash = stored_password or generate_password_hash(username)

        user_obj = User(username=username, password=username, type='student')  # will be overwritten with hash
        user_obj.password = raw_or_hash

        profile_data = json.dumps({
            "email": email,
            "phone": phone,
            "image_filename": profile_picture_path
        })

        student = Student(username=username, password=username, degree=degree, name=name, profile_data=profile_data)
        student.password = raw_or_hash

        assistant = HelpDeskAssistant(username=username)
        if degree == 'MSc':
            assistant.rate = 35.00
        elif degree == 'BSc':
            assistant.rate = 20.00

        registration_courses = RegistrationCourse.query.filter_by(registration_id=request_id).all()
        for rc in registration_courses:
            assistant.add_course_capability(rc.course_code)

        registration.approve(admin_username)

        notification = Notification(
            username=username,
            message="Your registration request has been approved. Welcome to the Help Desk team!",
            notification_type=Notification.TYPE_APPROVAL
        )

        db.session.add_all([user_obj, student, assistant, registration, notification])
        db.session.commit()

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