from App.database import db
from typing import Optional
from werkzeug.security import generate_password_hash
from App.utils.time_utils import trinidad_now
import os

LEGACY_UPLOAD_PREFIX = 'App/uploads/'

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
    profile_picture_path = db.Column(db.String(255), nullable=False)  # New field for profile picture
    status = db.Column(db.String(20), default='PENDING')  # PENDING, APPROVED, REJECTED
    created_at = db.Column(db.DateTime, default=trinidad_now())
    processed_at = db.Column(db.DateTime, nullable=True)
    processed_by = db.Column(db.String(20), nullable=True)
    password = db.Column(db.String(255), nullable=True)  # Store hashed password
    
    def __init__(self, username, name, email, degree, reason=None, phone=None, transcript_path=None, profile_picture_path=None, password=None):
        self.username = username
        self.name = name
        self.email = email
        self.phone = phone
        self.degree = degree
        self.reason = reason
        self.transcript_path = transcript_path
        self.status = 'PENDING'
        
        if profile_picture_path:
            self.profile_picture_path = profile_picture_path  # Initialize the new field
        else:
            self.profile_picture_path = 'App/static/images/DefaultAvatar.png'
        
        # Set hashed password if provided
        if password:
            self.set_password(password)
        else:
            self.password = None
    
    def set_password(self, password):
        """Create hashed password."""
        self.password = generate_password_hash(password)
    
    def get_profile_picture_url(self):
        """Return a usable profile picture URL, checking if file exists or using fallback"""
        from App.utils.profile_images import DEFAULT_PROFILE_IMAGE_URL

        path = self.profile_picture_path
        if not path:
            return DEFAULT_PROFILE_IMAGE_URL

        path_str = str(path)
        if '://' in path_str:
            return path_str

        fs_path = os.path.normpath(path_str)
        if os.path.exists(fs_path):
            resolved = self._build_static_path(fs_path)
            if resolved:
                return resolved

        legacy_resolved = self._resolve_legacy_upload(path_str)
        if legacy_resolved:
            return legacy_resolved

        return DEFAULT_PROFILE_IMAGE_URL

    @staticmethod
    def _build_static_path(path_str: str) -> Optional[str]:
        normalized = path_str.replace('\\', '/')
        if normalized.startswith('App/static/'):
            return '/' + normalized[4:]
        if normalized.startswith('static/'):
            return '/' + normalized
        if normalized.startswith(LEGACY_UPLOAD_PREFIX):
            legacy_relative = normalized[len(LEGACY_UPLOAD_PREFIX):]
            candidate = os.path.join('App', 'static', 'uploads', legacy_relative)
            if os.path.exists(candidate):
                normalized_candidate = str(candidate).replace('\\', '/')
                return '/' + normalized_candidate[4:] if normalized_candidate.startswith('App/') else '/' + normalized_candidate
            return None
        if not normalized.startswith('/'):
            return '/static/' + normalized.lstrip('/')
        return normalized

    @staticmethod
    def _resolve_legacy_upload(path_str: str) -> Optional[str]:
        if not path_str.startswith(LEGACY_UPLOAD_PREFIX):
            return None
        legacy_relative = path_str[len(LEGACY_UPLOAD_PREFIX):]
        candidate = os.path.join('App', 'static', 'uploads', legacy_relative)
        source_path = os.path.normpath(path_str)
        candidate_path = os.path.normpath(candidate)
        if not os.path.exists(candidate_path) and os.path.exists(source_path):
            os.makedirs(os.path.dirname(candidate_path), exist_ok=True)
            import shutil
            try:
                shutil.copy2(source_path, candidate_path)
            except OSError:
                return None
        if os.path.exists(candidate_path):
            normalized_candidate = str(candidate_path).replace('\\', '/')
            return '/' + normalized_candidate[4:] if normalized_candidate.startswith('App/') else '/' + normalized_candidate
        return None
    
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
        self.processed_at = trinidad_now()
        self.processed_by = admin_username
        return self
    
    def reject(self, admin_username):
        """Reject this registration request"""
        self.status = 'REJECTED'
        self.processed_at = trinidad_now()
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