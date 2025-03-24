from App.database import db
from datetime import datetime
from werkzeug.security import generate_password_hash

class RegistrationRequest(db.Model):
    __tablename__ = 'registration_request'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    degree = db.Column(db.String(10), nullable=False)
    reason = db.Column(db.Text, nullable=True)
    transcript_path = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='PENDING')  # PENDING, APPROVED, REJECTED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    processed_by = db.Column(db.String(20), nullable=True)
    password = db.Column(db.String(120), nullable=True)  # Store hashed password
    
    def __init__(self, username, name, email, degree, reason=None, phone=None, transcript_path=None, password=None):
        self.username = username
        self.name = name
        self.email = email
        self.phone = phone
        self.degree = degree
        self.reason = reason
        self.transcript_path = transcript_path
        self.status = 'PENDING'
        
        # Set hashed password if provided
        if password:
            self.set_password(password)
        else:
            self.password = None
    
    def set_password(self, password):
        """Create hashed password."""
        self.password = generate_password_hash(password)
    
    def get_json(self):
        return {
            'id': self.id,
            'username': self.username,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'degree': self.degree,
            'reason': self.reason,
            'transcript_path': self.transcript_path,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'processed_at': self.processed_at.strftime('%Y-%m-%d %H:%M:%S') if self.processed_at else None,
            'processed_by': self.processed_by
        }
    
    def approve(self, admin_username):
        """Approve this registration request"""
        self.status = 'APPROVED'
        self.processed_at = datetime.utcnow()
        self.processed_by = admin_username
        return self
    
    def reject(self, admin_username):
        """Reject this registration request"""
        self.status = 'REJECTED'
        self.processed_at = datetime.utcnow()
        self.processed_by = admin_username
        return self

class RegistrationCourse(db.Model):
    __tablename__ = 'registration_course'
    
    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('registration_request.id'), nullable=False)
    course_code = db.Column(db.String(10), nullable=False)
    
    # Relationship
    registration = db.relationship('RegistrationRequest', backref=db.backref('courses', lazy=True, cascade="all, delete-orphan"))
    
    def __init__(self, registration_id, course_code):
        self.registration_id = registration_id
        self.course_code = course_code