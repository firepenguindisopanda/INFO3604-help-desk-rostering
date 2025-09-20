from App.database import db

class Course(db.Model):
    __tablename__ = 'course'
    
    code = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    
    # Add constraints
    __table_args__ = (
        db.CheckConstraint("LENGTH(code) > 0", name='check_course_code_not_empty'),
        db.CheckConstraint("LENGTH(name) > 0", name='check_course_name_not_empty'),
    )
    
    def __init__(self, code, name):
        self.code = code
        self.name = name
    
    def get_json(self):
        return {
            self.code: self.name,
        }