from App.models import Student
from App.database import db

def create_student(username, password, degree, name):
    new_student = Student(username, password, degree, name)
    db.session.add(new_student)
    db.session.commit()
    return new_student

def get_student(username):
    return Student.query.filter_by(username=username).first()
