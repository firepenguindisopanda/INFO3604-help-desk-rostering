from App.database import db
from datetime import datetime, timedelta
from App.utils.time_utils import trinidad_now, convert_to_trinidad_time

class TimeEntry(db.Model):
    __tablename__ = 'time_entry'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), db.ForeignKey('student.username', ondelete='CASCADE'), nullable=False, index=True)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id', ondelete='SET NULL'), nullable=True, index=True)
    clock_in = db.Column(db.DateTime, nullable=False, index=True)
    clock_out = db.Column(db.DateTime, nullable=True, index=True)
    status = db.Column(db.String(20), default='active', index=True)  # active, completed, absent
    
    # Add constraints and indexes
    __table_args__ = (
        db.CheckConstraint("status IN ('active', 'completed', 'absent')", name='check_valid_status'),
        db.CheckConstraint('clock_out IS NULL OR clock_in < clock_out', name='check_clock_in_before_out'),
        db.Index('idx_time_entry_user_status', 'username', 'status'),
        db.Index('idx_time_entry_shift_status', 'shift_id', 'status'),
    )
    
    # Relationships
    student = db.relationship('Student', backref=db.backref('time_entries', lazy=True, cascade="all, delete-orphan"))
    shift = db.relationship('Shift', backref=db.backref('time_entries', lazy=True))
    
    def __init__(self, username, clock_in, shift_id=None, status='active'):
        self.username = username
        self.clock_in = clock_in
        self.shift_id = shift_id
        self.status = status
    
    def get_json(self):
        hours_worked = None
        if self.clock_out:
            delta = self.clock_out - self.clock_in
            hours_worked = round(delta.total_seconds() / 3600, 2)
            
        return {
            'Time Entry ID': self.id,
            'Student ID': self.username,
            'Shift ID': self.shift_id,
            'Clock In': self.clock_in.strftime('%Y-%m-%d %H:%M:%S') if self.clock_in else None,
            'Clock Out': self.clock_out.strftime('%Y-%m-%d %H:%M:%S') if self.clock_out else None,
            'Status': self.status,
            'Hours Worked': hours_worked
        }
    
    def complete(self, clock_out=None):
        """Mark this time entry as completed"""
        if not clock_out:
            clock_out = trinidad_now()
        self.clock_out = clock_out
        self.status = 'completed'
        
        # Calculate hours worked and update the assistant's hours_worked
        if self.student:
            assistant = self.student.help_desk_assistant
            if assistant:
                delta = self.clock_out - self.clock_in
                hours = delta.total_seconds() / 3600
                assistant.update_hours_worked(hours)
        
        return self
        
    def mark_absent(self):
        """Mark this time entry as absent"""
        self.status = 'absent'
        return self
        
    def get_hours_worked(self):
        """Calculate hours worked for this entry"""
        if self.status != 'completed' or not self.clock_out:
            return 0
            
        delta = self.clock_out - self.clock_in
        return round(delta.total_seconds() / 3600, 2)