from App.models import Semester
from App.database import db
from datetime import datetime

def create_semester(start, end):
    start_date = datetime.strptime(start, '%Y-%m-%d')
    end_date = datetime.strptime(end, '%Y-%m-%d')
    
    new_semester = Semester(start_date, end_date)
    db.session.add(new_semester)
    db.session.commit()
    return new_semester

def get_semester(id):
    return Semester.query.filter_by(id=id).first()

def get_semester(academic_year, semester):
    return Semester.query.filter_by(academic_year=academic_year, semester=semester).first()