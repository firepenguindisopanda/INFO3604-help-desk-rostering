from App.database import db
from datetime import datetime
from App.utils.time_utils import trinidad_now, convert_to_trinidad_time

class Allocation(db.Model):
    __tablename__ = 'allocation'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), db.ForeignKey('student.username'), nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=trinidad_now())
    
    # Relationships
    student = db.relationship('Student', backref=db.backref('allocations', lazy=True))
    shift = db.relationship('Shift', backref=db.backref('allocations', lazy=True))
    schedule = db.relationship('Schedule', backref=db.backref('allocations', lazy=True))
    
    def __init__(self, username, shift_id, schedule_id):
        self.username = username
        self.shift_id = shift_id
        self.schedule_id = schedule_id
    
    def get_json(self):
        return {
            'Allocation ID': self.id,
            'Student ID': self.username,
            'Shift ID': self.shift_id,
            'Schedule ID': self.schedule_id,
            'Created At': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }