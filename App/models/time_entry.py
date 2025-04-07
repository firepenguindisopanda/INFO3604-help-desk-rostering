from App.database import db
from datetime import datetime, timedelta
from App.utils.time_utils import trinidad_now, convert_to_trinidad_time

class TimeEntry(db.Model):
    __tablename__ = 'time_entry'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), db.ForeignKey('student.username'), nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=True)
    clock_in = db.Column(db.DateTime, nullable=False)
    clock_out = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='active')  # active, completed, absent
    
    # Relationships
    student = db.relationship('Student', backref=db.backref('time_entries', lazy=True))
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