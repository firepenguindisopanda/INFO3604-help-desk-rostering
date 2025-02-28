from App.database import db
from .user import User

class Assistant(User):
    __tablename__ = 'assistant'
    
    degree = db.Column(db.String(3), nullable=False)
    rate = db.Column(db.Float, nullable=False)
    active = db.Column(db.Boolean, nullable=False)
    hours_worked = db.Column(db.Integer, nullable=False)
    hours_minimum = db.Column(db.Integer, nullable=False)
    
    def __init__(self, username, password, degree):
        super().__init__(username, password)
        self.degree = degree
        self.rate = 20.00 if degree == 'BSc' else 35.00 if degree == 'MSc' else 0.00
        self.active = True
        self.hours_worked = 0
        self.hours_minimum = 4
    
    def get_json(self):
        return {
            'Ássistant ID': self.username,
            'Degree Level': self.degree,
            'Rate': f'${self.rate}',
            'Account State': 'Active' if self.active == True else 'Inactive',
            'Hours Worked': self.hours_worked,
            'Minimum Hours': self.hours_minimum
        }
    
    def update_hours_worked(self, hours):
        self.hours_worked += hours
    
    def deactivate(self):
        self.active = False
    
    def activate(self):
        self.active = True
    
    def set_minimum_hours(self, hours):
        self.hours_minimum = hours
