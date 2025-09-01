from App.database import db
from .user import User

class Student(User):
    __tablename__ = 'student'
    
    username = db.Column(db.String(20), db.ForeignKey('users.username'), primary_key=True)
    degree = db.Column(db.String(3), nullable=False, default='BSc')
    name = db.Column(db.String(100))
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
    
    def get_name(self):
        """Return the student's name or ID if name is not set"""
        return self.name if self.name and self.name.strip() else self.username