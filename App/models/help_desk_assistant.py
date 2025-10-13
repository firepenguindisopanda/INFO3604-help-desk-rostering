from App.database import db
from .student import Student

class HelpDeskAssistant(db.Model):
    __tablename__ = 'help_desk_assistant'
    
    username = db.Column(db.String(20), db.ForeignKey('student.username', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True)
    rate = db.Column(db.Float, nullable=False, default=20.00)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    hours_worked = db.Column(db.Integer, nullable=False, default=0)
    hours_minimum = db.Column(db.Integer, nullable=False, default=4)
    
    # Add constraints
    __table_args__ = (
        db.CheckConstraint('rate >= 0', name='check_rate_positive'),
        db.CheckConstraint('hours_worked >= 0', name='check_hours_worked_positive'),
        db.CheckConstraint('hours_minimum >= 0', name='check_hours_minimum_positive'),
    )
    
    # Course competency
    course_capabilities = db.relationship('CourseCapability', backref='assistant', lazy=True, cascade="all, delete-orphan")
    
    # Relationships
    student = db.relationship('Student', backref=db.backref('help_desk_assistant', uselist=False, cascade="all, delete-orphan"))
    
    def __init__(self, username):
        self.username = username
        student = Student.query.get(username)
        
        # Default values if student is not found
        self.rate = 20.00  # Default rate
        self.active = True
        self.hours_worked = 0
        self.hours_minimum = 4
        
        # Update rate if student exists and has a degree
        if student and hasattr(student, 'degree'):
            if student.degree == 'MSc':
                self.rate = 35.00
            elif student.degree == 'BSc':
                self.rate = 20.00
    
    def get_json(self):
        return {
            'Student ID': self.username,
            'Rate': f'${self.rate}',
            'Account State': 'Active' if self.active == True else 'Inactive',
            'Hours Worked': self.hours_worked,
            'Minimum Hours': self.hours_minimum,
            'Course Capabilities': [cap.course_code for cap in self.course_capabilities] if hasattr(self, 'course_capabilities') else []
        }

    def to_dict(self):
        """Return a lightweight representation for API responses."""
        student_name = None
        if hasattr(self, 'student') and self.student:
            student_name = self.student.get_name() if hasattr(self.student, 'get_name') else getattr(self.student, 'name', None)

        return {
            'id': self.username,
            'username': self.username,
            'name': student_name or self.username,
            'rate': float(self.rate) if self.rate is not None else None,
            'active': bool(self.active),
            'hours_worked': int(self.hours_worked) if self.hours_worked is not None else 0,
            'hours_minimum': int(self.hours_minimum) if self.hours_minimum is not None else 0,
        }
    
    def activate(self):
        self.active = True
    
    def deactivate(self):
        self.active = False
    
    def set_minimum_hours(self, hours):
        self.hours_minimum = hours
    
    def update_hours_worked(self, hours):
        self.hours_worked += hours
    
    def add_course_capability(self, course_code):
        from .course_capability import CourseCapability
        capability = CourseCapability(self.username, course_code)
        self.course_capabilities.append(capability)
        return capability