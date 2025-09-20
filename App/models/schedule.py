from App.database import db
from datetime import datetime, timedelta
from App.utils.time_utils import trinidad_now, convert_to_trinidad_time

class Schedule(db.Model):
    __tablename__ = 'schedule'
    
    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.DateTime, nullable=False, index=True)
    end_date = db.Column(db.DateTime, nullable=False, index=True)
    type = db.Column(db.String(20), nullable=False, index=True)
    generated_at = db.Column(db.DateTime, default=trinidad_now(), index=True)
    is_published = db.Column(db.Boolean, default=False, index=True)
    
    # Add constraints
    __table_args__ = (
        db.CheckConstraint("type IN ('helpdesk', 'lab')", name='check_valid_schedule_type'),
        db.CheckConstraint('start_date <= end_date', name='check_start_before_end_date'),
        db.Index('idx_schedule_type_published', 'type', 'is_published'),
        db.Index('idx_schedule_date_range', 'start_date', 'end_date'),
    )
    
    # Relationships
    shifts = db.relationship('Shift', backref='schedule', lazy=True, cascade="all, delete-orphan")
    
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
        self.is_published = False
    
    def get_json(self):
        # Get friendly type name
        if self.type == 'helpdesk':
            type_name = 'Help Desk'
        elif self.type == 'lab':
            type_name = 'Lab'
        else:
            type_name = 'Other'
            
        return {
            'Schedule ID': self.id,
            'Start Date': self.start_date.strftime('%Y-%m-%d'),
            'End Date': self.end_date.strftime('%Y-%m-%d'),
            'Type': type_name,
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