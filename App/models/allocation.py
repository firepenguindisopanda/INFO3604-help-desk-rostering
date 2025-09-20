from App.database import db
from datetime import datetime
from App.utils.time_utils import trinidad_now, convert_to_trinidad_time

# Constants
CASCADE_ALL_DELETE_ORPHAN = "all, delete-orphan"

class Allocation(db.Model):
    __tablename__ = 'allocation'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), db.ForeignKey('student.username', ondelete='CASCADE'), nullable=False, index=True)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id', ondelete='CASCADE'), nullable=False, index=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=trinidad_now(), index=True)
    
    # Add composite index for common queries
    __table_args__ = (
        db.Index('idx_allocation_schedule_student', 'schedule_id', 'username'),
        db.Index('idx_allocation_shift_student', 'shift_id', 'username'),
    )
    
    # Relationships with proper cascade
    student = db.relationship('Student', backref=db.backref('allocations', lazy=True, cascade=CASCADE_ALL_DELETE_ORPHAN))
    shift = db.relationship('Shift', backref=db.backref('allocations', lazy=True, cascade=CASCADE_ALL_DELETE_ORPHAN))
    schedule = db.relationship('Schedule', backref=db.backref('allocations', lazy=True, cascade=CASCADE_ALL_DELETE_ORPHAN))
    
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