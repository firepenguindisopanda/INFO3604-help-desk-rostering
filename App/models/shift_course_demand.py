from App.database import db

class ShiftCourseDemand(db.Model):
    __tablename__ = 'shift_course_demand'
    
    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id', ondelete='CASCADE'), nullable=False, index=True)
    course_code = db.Column(db.String(10), db.ForeignKey('course.code', ondelete='CASCADE'), nullable=False, index=True)
    tutors_required = db.Column(db.Integer, nullable=False, default=2)
    weight = db.Column(db.Integer, nullable=True)
    
    # Add constraints and indexes
    __table_args__ = (
        db.CheckConstraint('tutors_required > 0', name='check_tutors_required_positive'),
        db.CheckConstraint('weight IS NULL OR weight > 0', name='check_weight_positive'),
        db.Index('idx_shift_course_demand_shift_course', 'shift_id', 'course_code'),
        db.UniqueConstraint('shift_id', 'course_code', name='unique_shift_course_demand'),
    )
    
    # Relationships
    course = db.relationship('Course', backref=db.backref('shift_demands', lazy=True))
    
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
    
    def to_dict(self):
        """Convert shift course demand to dictionary for API responses"""
        return {
            'id': self.id,
            'shift_id': self.shift_id,
            'course_code': self.course_code,
            'tutors_required': self.tutors_required,
            'weight': self.weight
        }