from App.database import db
from .user import User

class Student(User):
    __tablename__ = 'student'
    
    username = db.Column(db.String(20), db.ForeignKey('user.username'), primary_key=True)
    degree = db.Column(db.String(3), nullable=False)
    
    __mapper_args__ = {
        'polymorphic_identity': 'student'
    }
    
    def __init__(self, username, password, degree):
        super().__init__(username, password)
        self.degree = degree
    
    def get_json(self):
        return {
            'Student ID': self.username,
            'Degree Level': self.degree
        }
    
