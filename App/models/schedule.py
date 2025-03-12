from App.database import db
from datetime import datetime, timedelta

class Schedule(db.Model):
    __tablename__ = 'schedule'
    
    id = db.Column(db.Integer, primary_key=True)
    week_number = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_published = db.Column(db.Boolean, default=False)
    semester_id = db.Column(db.Integer, db.ForeignKey('semester.id'))
    
    # Relationships
    shifts = db.relationship('Shift', backref='schedule', lazy=True, cascade="all, delete-orphan")
    semester = db.relationship('Semester', backref='schedules')
    
    def __init__(self, week_number, start_date, end_date=None, semester_id=None):
        self.week_number = week_number
        self.start_date = start_date
        
        # If end_date not provided, set it to 6 days after start_date (for a 7-day week)
        if end_date is None:
            self.end_date = start_date + timedelta(days=6)
        else:
            self.end_date = end_date
            
        self.semester_id = semester_id
        self.is_published = False
    
    def get_json(self):
        return {
            'Schedule ID': self.id,
            'Week Number': self.week_number,
            'Start Date': self.start_date.strftime('%Y-%m-%d'),
            'End Date': self.end_date.strftime('%Y-%m-%d'),
            'Generated At': self.generated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'Published': self.is_published,
            'Semester ID': self.semester_id
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
        return f"Week {self.week_number}: {start_str} - {end_str}"