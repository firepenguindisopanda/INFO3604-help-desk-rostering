from App.database import db
from .student import Student

class LabAssistant(db.Model):
    __tablename__ = 'lab_assistant'
    
    username = db.Column(db.String(20), db.ForeignKey('student.username'), primary_key=True)
    active = db.Column(db.Boolean, nullable=False)
    experience = db.Column(db.Boolean, nullable=False)
    
    def __init__(self, username, experience):
        self.username = username
        self.active = True
        self.experience = experience
    
    def get_json(self):
        return {
            'Student ID': self.username,
            'Account State': 'Active' if self.active == True else 'Inactive',
            'Experience': 'New' if self.experience == False else 'Experienced'
        }
    
    def activate(self):
        self.active = True
    
    def deactivate(self):
        self.active = False

