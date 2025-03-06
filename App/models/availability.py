from App.database import db

class Availability(db.Model):
    __tablename__ = 'availability'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), db.ForeignKey('student.username'), nullable=False)
    shift = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=False)
    
    students = db.relationship('Student', backref=db.backref('availability', lazy=True))
    shifts = db.relationship('Shift', backref=db.backref('availability', lazy=True))
    
    def __init__(self, username, shift):
        self.username = username
        self.shift = shift
    
    def get_json(self):
        return {
            'Availability ID': self.id,
            'Student ID': self.username,
            'Shift ID': self.shift,
        }
    
