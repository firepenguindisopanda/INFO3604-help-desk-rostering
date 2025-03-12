from App.database import db

class Course(db.Model):
    __tablename__ = 'course'
    
    code = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    semester = db.Column(db.Integer, db.ForeignKey('semester.id'))
    
    def __init__(self, code, name, semester=None):
        self.code = code
        self.name = name
        self.semester = semester
    
    def get_json(self):
        return {
            'Course Code': self.code,
            'Course Name': self.name,
            'Semester': self.semester
        }