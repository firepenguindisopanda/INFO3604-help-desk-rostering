from App.database import db

class ShiftCourseDemand(db.Model):
    __tablename__ = 'shift_course_demand'
    
    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'), nullable=False)
    course_code = db.Column(db.String(10), db.ForeignKey('course.code'), nullable=False)
    tutors_required = db.Column(db.Integer, nullable=False, default=2)
    weight = db.Column(db.Integer, nullable=True)
    
    def __init__(self, shift_id, course_code, tutors_required=2, weight=None):
        self.shift_id = shift_id
        self.course_code = course_code
        self.tutors_required = tutors_required
        self.weight = weight if weight is not None else tutors_required
    
    def get_json(self):
        return {
            'ID': self.id,
            'Shift ID': self.shift_id,
            'Course Code': self.course_code,
            'Tutors Required': self.tutors_required,
            'Weight': self.weight
        }