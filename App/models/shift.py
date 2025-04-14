from App.database import db
from datetime import datetime
from .shift_course_demand import ShiftCourseDemand

class Shift(db.Model):
    __tablename__ = 'shift'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'))
    
    # Course demand for this shift
    course_demands = db.relationship('ShiftCourseDemand', backref='shift', lazy=True, cascade="all, delete-orphan")
    
    def __init__(self, date, start_time, end_time, schedule_id=None):
        self.date = date
        self.start_time = start_time
        self.end_time = end_time
        self.schedule_id = schedule_id
    
    def get_json(self):
        return {
            'Shift ID': self.id,
            'Date': self.date.strftime('%Y-%m-%d'),
            'Start Time': self.start_time.strftime('%H:%M'),
            'End Time': self.end_time.strftime('%H:%M'),
            'Schedule ID': self.schedule_id,
            'Course Demands': [demand.get_json() for demand in self.course_demands]
        }
        
    def formatted_time(self):
        """Return time in a human-friendly format like 10:00 am"""
        return f"{self.start_time.strftime('%I:%M %p')} to {self.end_time.strftime('%I:%M %p')}"
    
    def add_course_demand(self, course_code, tutors_required=2, weight=None):
        """Add or update course demand for this shift"""
        demand = ShiftCourseDemand(self.id, course_code, tutors_required, weight)
        self.course_demands.append(demand)
        return demand