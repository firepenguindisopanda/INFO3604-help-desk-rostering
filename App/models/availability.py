from App.database import db

class Availability(db.Model):
    __tablename__ = 'availability'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), db.ForeignKey('student.username'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Monday, 1=Tuesday, etc.
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    
    def __init__(self, username, day_of_week, start_time, end_time):
        self.username = username
        self.day_of_week = day_of_week
        self.start_time = start_time
        self.end_time = end_time
    
    def get_json(self):
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_name = days[self.day_of_week] if 0 <= self.day_of_week < 7 else "Unknown"
        
        return {
            'Availability ID': self.id,
            'Student ID': self.username,
            'Day': day_name,
            'Start Time': self.start_time.strftime('%H:%M'),
            'End Time': self.end_time.strftime('%H:%M')
        }
    
    def is_available_for_shift(self, shift):
        """Check if this availability window covers the given shift"""
        shift_day = shift.date.weekday()
        shift_start = shift.start_time.time()
        shift_end = shift.end_time.time()
        
        return (self.day_of_week == shift_day and 
                self.start_time <= shift_start and 
                self.end_time >= shift_end)