from sqlalchemy import text
from werkzeug.security import generate_password_hash
from App.models import RegistrationRequest, RegistrationCourse, Student, User, HelpDeskAssistant, CourseCapability, Notification, Availability
from App.database import db
from App.controllers.user import create_user
from App.controllers.notification import create_notification, Notification
import os
from datetime import datetime, time

def create_registration_request(username, name, email, degree, reason=None, phone=None, transcript_file=None, courses=None, password=None):
    """Create a new registration request with password"""
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
            from werkzeug.utils import secure_filename
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
        
        # Create registration request
        registration = RegistrationRequest(
            username=username,
            name=name,
            email=email,
            phone=phone,
            degree=degree,
            reason=reason,
            transcript_path=transcript_path
        )
        
        # Set password if provided
        if password:
            registration.set_password(password)
        
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

def approve_registration(request_id, admin_username):
    """
    Approve a registration request and create the user account.
    This implementation uses a transaction to ensure all operations succeed or fail together.
    """
    connection = None
    transaction = None
    
    try:
        # Get the registration request
        registration = RegistrationRequest.query.get(request_id)
        if not registration:
            return False, "Registration request not found"
        
        if registration.status != 'PENDING':
            return False, f"Registration has already been {registration.status.lower()}"
        
        # Extract all needed data before making changes
        username = registration.username
        name = registration.name or username
        degree = registration.degree
        stored_password = registration.password  # This should be already hashed
        
        # Get courses for this registration
        registration_courses = RegistrationCourse.query.filter_by(registration_id=request_id).all()
        course_codes = [course.course_code for course in registration_courses]
        
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return False, f"A user with username {username} already exists in the system"
        
        # Start a new transaction
        connection = db.engine.connect()
        transaction = connection.begin()
        
        # Create user (with explicit password handling)
        if stored_password:
            # If we have a stored password hash, use it directly
            connection.execute(
                text("INSERT INTO user (username, password, type) VALUES (:username, :password, :type)"),
                {"username": username, "password": stored_password, "type": "student"}
            )
        else:
            # Otherwise, generate a new hash using the username as password
            hashed_password = generate_password_hash(username)
            connection.execute(
                text("INSERT INTO user (username, password, type) VALUES (:username, :password, :type)"),
                {"username": username, "password": hashed_password, "type": "student"}
            )
        
        # Create student record
        connection.execute(
            text("INSERT INTO student (username, degree, name) VALUES (:username, :degree, :name)"),
            {"username": username, "degree": degree, "name": name}
        )
        
        # Create help desk assistant record
        connection.execute(
            text("INSERT INTO help_desk_assistant (username, rate, active, hours_worked, hours_minimum) VALUES (:username, :rate, :active, :hours_worked, :hours_minimum)"),
            {"username": username, "rate": 20.0, "active": True, "hours_worked": 0, "hours_minimum": 4}
        )
        
        # Add course capabilities
        for course_code in course_codes:
            connection.execute(
                text("INSERT INTO course_capability (assistant_username, course_code) VALUES (:username, :course_code)"),
                {"username": username, "course_code": course_code}
            )
        
        # Mark registration as approved
        now = datetime.utcnow()
        connection.execute(
            text("UPDATE registration_request SET status = 'APPROVED', processed_at = :now, processed_by = :admin WHERE id = :id"),
            {"now": now, "admin": admin_username, "id": request_id}
        )
        
        # Create notification for the student
        connection.execute(
            text("INSERT INTO notification (username, message, notification_type, is_read, created_at) VALUES (:username, :message, :type, :is_read, :created_at)"),
            {
                "username": username, 
                "message": "Your registration request has been approved. Welcome to the Help Desk team!",
                "type": "approval",
                "is_read": False,
                "created_at": now
            }
        )
        
        # Commit the transaction
        transaction.commit()
        
        # After successful approval, also transfer over any availability settings
        availability_records = Availability.query.filter_by(username=username).all()
        print(f"Found {len(availability_records)} availability records to transfer for {username}")
        
        return True, "Registration approved successfully"
        
    except Exception as e:
        if transaction:
            transaction.rollback()
        print(f"Error approving registration: {e}")
        return False, f"An error occurred: {str(e)}"
        
    finally:
        if connection:
            connection.close()
            
def reject_registration(request_id, admin_username):
    """Reject a registration request without creating any user accounts"""
    try:
        registration = RegistrationRequest.query.get(request_id)
        if not registration:
            return False, "Registration request not found"
        
        if registration.status != 'PENDING':
            return False, f"Registration has already been {registration.status.lower()}"
        
        # Simply mark as rejected - no user accounts are created
        registration.status = 'REJECTED'
        registration.processed_at = datetime.utcnow()
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

