from App.database import db
from .student import Student

class LabAssistant(db.Model):
    __tablename__ = 'lab_assistant'
    
    username = db.Column(db.String(20), db.ForeignKey('student.username', ondelete='CASCADE'), primary_key=True)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    experience = db.Column(db.Boolean, nullable=False, default=False, index=True)
    
    # Relationships
    student = db.relationship('Student', backref=db.backref('lab_assistant', uselist=False, cascade="all, delete-orphan"))
    
    def __init__(self, username, experience):
        self.username = username
        self.experience = experience
        self.active = True
    
    def get_json(self):
        return {
            'Student ID': self.username,
            'Account State': 'Active' if self.active else 'Inactive',
            'Experience': 'Experienced' if self.experience else 'New'
        }
    
    def activate(self):
        self.active = True
    
    def deactivate(self):
        self.active = False

