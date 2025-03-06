from App.database import db

class Allocation(db.Model):
    __tablename__ = 'allocation'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), db.ForeignKey('student.username'), nullable=False)
    schedule = db.Column(db.Integer, db.ForeignKey('schedule.id'), nullable=False)
    shift = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=False)
    
    students = db.relationship('Student', backref=db.backref('allocation', lazy=True))
    schedules = db.relationship('Schedule', backref=db.backref('allocation', lazy=True))
    shifts = db.relationship('Shift', backref=db.backref('allocation', lazy=True))
    
    def __init__(self, username, shift):
        self.username = username
        self.shift = shift
    
    def get_json(self):
        return {
            'Allocation ID': self.id,
            'Student ID': self.username,
            'Schedule ID': self.schedule,
            'Shift ID': self.shift,
        }
    
