from App.database import db
from datetime import time
from App.utils.time_utils import trinidad_now


class ScheduleConfig(db.Model):
    """Single responsibility: Store scheduling configuration parameters."""
    __tablename__ = 'schedule_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    
    # Operating days (0=Monday, 6=Sunday)
    operating_days = db.Column(db.JSON, nullable=False)  # e.g., [0, 1, 2] for Mon-Wed
    
    # Time windows
    start_time = db.Column(db.Time, nullable=False)  # 10:00
    end_time = db.Column(db.Time, nullable=False)    # 14:00
    
    # Shift parameters
    shift_duration_minutes = db.Column(db.Integer, nullable=False, default=60)
    staff_per_shift = db.Column(db.Integer, nullable=False, default=1)
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=trinidad_now, index=True)
    updated_at = db.Column(db.DateTime, onupdate=trinidad_now)
    
    # Add constraints
    __table_args__ = (
        db.CheckConstraint('shift_duration_minutes > 0', name='check_positive_duration'),
        db.CheckConstraint('staff_per_shift > 0', name='check_positive_staff'),
        db.Index('idx_schedule_config_active', 'is_active'),
    )
    
    def __init__(self, name=None, operating_days=None, start_time=None, end_time=None, 
                 shift_duration_minutes=60, staff_per_shift=1, is_active=True):
        self.name = name
        self.operating_days = operating_days or []
        self.start_time = start_time
        self.end_time = end_time
        self.shift_duration_minutes = shift_duration_minutes
        self.staff_per_shift = staff_per_shift
        self.is_active = is_active
    
    def to_dict(self):
        """Abstraction: Expose data in client-friendly format."""
        return {
            'id': self.id,
            'name': self.name,
            'operating_days': self.operating_days,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'shift_duration_minutes': self.shift_duration_minutes,
            'staff_per_shift': self.staff_per_shift,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def validate(self):
        """Fail fast: Validate configuration on creation."""
        if not self.operating_days or not isinstance(self.operating_days, list):
            raise ValueError("operating_days must be a non-empty list")
        
        if not all(isinstance(day, int) and 0 <= day <= 6 for day in self.operating_days):
            raise ValueError("operating_days must contain integers 0-6 (Monday-Sunday)")
        
        if not self.start_time or not self.end_time:
            raise ValueError("start_time and end_time are required")
        
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        
        if self.shift_duration_minutes <= 0:
            raise ValueError("shift_duration_minutes must be positive")
        
        if self.staff_per_shift <= 0:
            raise ValueError("staff_per_shift must be positive")
        
        if not self.name or not self.name.strip():
            raise ValueError("name is required")
    
    def get_day_names(self):
        """Helper method to get human-readable day names."""
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return [day_names[day] for day in sorted(self.operating_days)]
    
    def get_formatted_time_range(self):
        """Return a human-friendly time range string."""
        if not self.start_time or not self.end_time:
            return "Not configured"
        return f"{self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')}"
    
    def __repr__(self):
        return f'<ScheduleConfig {self.name}: {self.get_day_names()} {self.get_formatted_time_range()}>'