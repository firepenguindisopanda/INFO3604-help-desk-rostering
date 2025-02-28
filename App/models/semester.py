from App.database import db

class Semester(db.Model):
    __tablename__ = 'semester'
    
    id = db.Column(db.Integer, primary_key=True)
    academic_year = db.Column(db.String(9), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    
    def __init__(self, start, end):
        self.academic_year = f'{start.year}/{end.year}'
        self.semester = 1 if start.month < 7 else 2
        self.start = start
        self.end = end
    
    def get_json(self):
        return {
            'Semester ID': self.id,
            'Academic Year': self.academic_year,
            'Semester': self.semester,
            'Start Date': self.start,
            'End Date': self.end
        }
