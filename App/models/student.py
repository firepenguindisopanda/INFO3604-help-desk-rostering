from App.database import db
from .user import User

class Student(User):
    __tablename__ = 'student'
    
    username = db.Column(db.String(20), db.ForeignKey('users.username', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True)
    degree = db.Column(db.String(3), nullable=False, default='BSc', index=True)
    name = db.Column(db.String(100), index=True)
    profile_data = db.Column(db.Text)
    
    __mapper_args__ = {
        'polymorphic_identity': 'student'
    }
    
    def __init__(self, username, password, degree='BSc', name=None, profile_data=None):
        super().__init__(username, password, type='student')
        self.degree = degree
        self.name = name
        self.profile_data = profile_data
    
    def get_json(self):
        return {
            'Student ID': self.username,
            'Name': self.name,
            'Degree Level': self.degree
        }
    
    def to_dict(self):
        """Convert student to dictionary for API responses (excludes password)"""
        base_dict = super().to_dict()
        base_dict.update({
            'student_id': self.username,
            'degree': self.degree,
            'name': self.name,
            'display_name': self.get_name(),
            'profile_data': self.profile_data
        })
        return base_dict
    
    def get_name(self):
        """Return the student's name or ID if name is not set"""
        return self.name if self.name and self.name.strip() else self.username