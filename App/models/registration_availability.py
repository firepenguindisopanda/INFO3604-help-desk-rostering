from App.database import db

class RegistrationAvailability(db.Model):
    __tablename__ = 'registration_availability'
    
    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('registration_request.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Monday, 1=Tuesday, etc.
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    
    # Relationship
    registration = db.relationship('RegistrationRequest', backref=db.backref('availability_slots', lazy=True, cascade="all, delete-orphan"))
    
    def __init__(self, registration_id, day_of_week, start_time, end_time):
        self.registration_id = registration_id
        self.day_of_week = day_of_week
        self.start_time = start_time
        self.end_time = end_time
    
    def get_json(self):
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_name = days[self.day_of_week] if 0 <= self.day_of_week < 7 else "Unknown"
        
        return {
            'day_of_week': self.day_of_week,
            'day_name': day_name,
            'start_time': self.start_time.strftime('%H:%M'),
            'end_time': self.end_time.strftime('%H:%M')
        }
