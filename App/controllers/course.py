from App.models import Course
from App.database import db

def create_course(code, name):
    new_course = Course(code=code, name=name)
    db.session.add(new_course)
    db.session.commit()
    return new_course


def get_all_courses():
    return Course.query.all()


# Helper function to get course name by code
def get_course_name(course_code):
    course = Course.query.filter_by(code=course_code).first()
    if course.code == course_code:
        return course.name
    return course_code # Returns supplied course code if course not found


# Helper function to get all course codes
def get_all_course_codes():
    courses = get_all_courses()
    return [course.code for course in courses]


# Helper function to get all courses as a dictionary
def get_courses_dict():
    courses = get_all_courses()    
    return {course.code: course.name for course in courses}


# Helper function to validate a course code
def is_valid_course(course_code):
    return course_code in get_all_course_codes()
