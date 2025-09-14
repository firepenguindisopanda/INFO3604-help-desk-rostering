from App.database import db
from datetime import datetime, timedelta
from App.utils.time_utils import trinidad_now, convert_to_trinidad_time

class Schedule(db.Model):
    __tablename__ = 'schedule'
    
    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    type = db.Column(db.String(20), nullable=False)
    generated_at = db.Column(db.DateTime, default=trinidad_now())
    is_published = db.Column(db.Boolean, default=False)
    # semester_id = db.Column(db.Integer, db.ForeignKey('semester.id'))
    
    # Relationships
    shifts = db.relationship('Shift', backref='schedule', lazy=True, cascade="all, delete-orphan")
    # semester = db.relationship('Semester', backref='schedules')
    
    def __init__(self, id=None, start_date=None, end_date=None, type='helpdesk'):
        if id is not None:
            self.id = id
            
        self.start_date = start_date or trinidad_now()
        
        # If end_date not provided, set it to 6 days after start_date (for a 7-day week)
        if end_date is None:
            self.end_date = self.start_date + timedelta(days=6)
        else:
            self.end_date = end_date
        
        self.type = type
        # self.semester_id = semester_id
        self.is_published = False
    
    def get_json(self):
        return {
            'Schedule ID': self.id,
            'Start Date': self.start_date.strftime('%Y-%m-%d'),
            'End Date': self.end_date.strftime('%Y-%m-%d'),
            'Type': 'Help Desk' if self.type == 'helpdesk' else 'Lab' if self.type == 'lab' else 'Other',
            'Generated At': self.generated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'Published': self.is_published,
        }
    
    def to_dict(self):
        """Convert schedule to dictionary for API responses"""
        return {
            'id': self.id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'type': self.type,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'is_published': self.is_published,
            'formatted_date_range': self.get_formatted_date_range(),
            'shift_count': len(self.shifts) if self.shifts else 0
        }
    
    def publish(self):
        """Publish the schedule and notify all assigned staff"""
        if not self.is_published:
            self.is_published = True
            # Here you would trigger notifications to all assigned staff
            return True
        return False
        
    def get_formatted_date_range(self):
        """Return a human-friendly date range string for display"""
        start_str = self.start_date.strftime('%B %d')
        end_str = self.end_date.strftime('%B %d, %Y')
        return f"{start_str} - {end_str}"