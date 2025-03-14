from App.models import RegistrationRequest, RegistrationCourse, Student, User, HelpDeskAssistant, CourseCapability
from App.database import db
from App.controllers.user import create_user
from App.controllers.notification import create_notification, Notification
import os
from datetime import datetime
from werkzeug.utils import secure_filename

def create_registration_request(username, name, email, degree, reason=None, phone=None, transcript_file=None, courses=None):
    """Create a new registration request"""
    try:
        # Check if user already exists
        existing_user = User.query.get(username)
        if existing_user:
            return False, "A user with this ID already exists"
        
        # Check if there's a pending registration request
        existing_request = RegistrationRequest.query.filter_by(username=username, status='PENDING').first()
        if existing_request:
            return False, "You already have a pending registration request"
        
        # Handle transcript file upload
        transcript_path = None
        if transcript_file and transcript_file.filename:
            filename = secure_filename(transcript_file.filename)
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            filename = f"{username}_{timestamp}_{filename}"
            
            # Ensure uploads directory exists
            upload_dir = os.path.join('App', 'uploads', 'transcripts')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            
            # Save file
            file_path = os.path.join(upload_dir, filename)
            transcript_file.save(file_path)
            transcript_path = f"transcripts/{filename}"
        
        # Create request
        registration = RegistrationRequest(
            username=username,
            name=name,
            email=email,
            phone=phone,
            degree=degree,
            reason=reason,
            transcript_path=transcript_path
        )
        db.session.add(registration)
        db.session.flush()  # Get ID without committing
        
        # Add selected courses
        if courses:
            for course_code in courses:
                course = RegistrationCourse(registration.id, course_code)
                db.session.add(course)
        
        # Create notification for admin users
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

def approve_registration(request_id, admin_username):
    """Approve a registration request and create the user account"""
    try:
        registration = RegistrationRequest.query.get(request_id)
        if not registration:
            return False, "Registration request not found"
        
        if registration.status != 'PENDING':
            return False, f"Registration has already been {registration.status.lower()}"
        
        # Get courses for this registration
        registration_courses = RegistrationCourse.query.filter_by(registration_id=request_id).all()
        course_codes = [course.course_code for course in registration_courses]
        
        # Create user account
        user = create_user(registration.username, registration.username, type='student')  # Use username as default password
        
        # Create student record
        student = Student(
            username=registration.username,
            password=registration.username,  # Set the same initial password
            degree=registration.degree,
            name=registration.name
        )
        db.session.add(student)
        
        # Create help desk assistant record
        assistant = HelpDeskAssistant(registration.username)
        db.session.add(assistant)
        
        # Add course capabilities
        for course_code in course_codes:
            capability = CourseCapability(registration.username, course_code)
            db.session.add(capability)
        
        # Mark registration as approved
        registration.approve(admin_username)
        db.session.add(registration)
        
        # Create notification for the student (they'll see it when they first log in)
        create_notification(
            registration.username,
            "Your registration request has been approved. Welcome to the Help Desk team!",
            Notification.TYPE_APPROVAL
        )
        
        db.session.commit()
        return True, "Registration approved successfully"
    except Exception as e:
        db.session.rollback()
        print(f"Error approving registration: {e}")
        return False, f"An error occurred: {str(e)}"

def reject_registration(request_id, admin_username, reason=None):
    """Reject a registration request"""
    try:
        registration = RegistrationRequest.query.get(request_id)
        if not registration:
            return False, "Registration request not found"
        
        if registration.status != 'PENDING':
            return False, f"Registration has already been {registration.status.lower()}"
        
        # Mark as rejected
        registration.reject(admin_username)
        db.session.add(registration)
        db.session.commit()
        
        return True, "Registration rejected successfully"
    except Exception as e:
        db.session.rollback()
        print(f"Error rejecting registration: {e}")
        return False, f"An error occurred: {str(e)}"