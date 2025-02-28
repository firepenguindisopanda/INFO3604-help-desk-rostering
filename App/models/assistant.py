from App.database import db
from App.models import User

class Assistant(User):
    __tablename__ = 'assistant'
    
    degree = db.Column(db.String(3), nullable=False)
    rate = db.Column(db.Float, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    hours_worked = db.Column(db.Integer, nullable=False, default=0)
    hours_minimum = db.Column(db.Integer, nullable=False, default=4)
    
    def __init__(self, username, password, degree):
        super().__init__(username, password)
        self.degree = degree
        self.rate = 20.00 if degree == 'BSc' else 35.00 if degree == 'MSc' else 0.00
    
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
