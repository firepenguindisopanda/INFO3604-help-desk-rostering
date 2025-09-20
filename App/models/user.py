from werkzeug.security import check_password_hash, generate_password_hash
from App.database import db

class User(db.Model):
    __tablename__ = 'users'
    
    username = db.Column(db.String(20), nullable=False, primary_key=True)
    password = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False, index=True)
    
    # Add constraints
    __table_args__ = (
        db.CheckConstraint("type IN ('admin', 'student')", name='check_valid_user_type'),
    )
    
    __mapper_args__ = {
        'polymorphic_on': type
    }

    def __init__(self, username, password, type='student'):
        self.username = username
        self.set_password(password)
        self.type = type

    def get_json(self):
        return{
            'Username': self.username,
            'Type': self.type
        }

    def to_dict(self):
        """Convert user to dictionary for API responses (excludes password)"""
        return {
            'username': self.username,
            'type': self.type,
            'is_admin': self.is_admin(),
            'is_student': self.is_student()
        }

    def set_password(self, password):
        """Create hashed password."""
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.password, password)

    def is_admin(self):
        return self.type == 'admin'

    def is_student(self):
        return self.type == 'student'