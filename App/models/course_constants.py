"""
Standardized Course Constants for the Help Desk Scheduling System
This file defines the standard course offerings available throughout the application.
"""

# Complete standardized list of courses
STANDARD_COURSES = [
    ('COMP1011', 'Introduction to Computer Science'),
    ('COMP1600', 'Introduction to Computing Concepts'),
    ('COMP1601', 'Computer Programming I'),
    ('COMP1602', 'Computer Programming II'),
    ('COMP1603', 'Computer Programming III'),
    ('COMP1604', 'Data Structures and Algorithms'),
    ('COMP2601', 'Computer Architecture'),
    ('COMP2602', 'Computer Networks'),
    ('COMP2603', 'Object-Oriented Programming I'),
    ('COMP2604', 'Operating Systems'),
    ('COMP2605', 'Enterprise Database Systems'),
    ('COMP2606', 'Software Engineering I'),
    ('COMP2611', 'Data Structures'),
    ('COMP3601', 'Design and Analysis of Algorithms'),
    ('COMP3602', 'Software Engineering II'),
    ('COMP3603', 'Human-Computer Interaction'),
    ('COMP3605', 'Introduction to Data Analytics'),
    ('COMP3606', 'Wireless and Mobile Computing'),
    ('COMP3607', 'Object-Oriented Programming II'),
    ('COMP3608', 'Intelligent Systems'),
    ('COMP3609', 'Game Programming'),
    ('COMP3610', 'Big Data Analytics'),
    ('COMP3613', 'Software Engineering II'),
    ('INFO1600', 'Introduction to Information Technology'),
    ('INFO1601', 'Introduction to Web Development'),
    ('INFO2600', 'Information Systems Development'),
    ('INFO2601', 'Networking Technologies Fundamentals '),
    ('INFO2602', 'Web Programming and Technologies I'),
    ('INFO2603', 'Platform Technologies I'),
    ('INFO2604', 'Information Systems Security'),
    ('INFO2605', 'Professional Ethics and Law '),
    ('INFO3600', 'Business Information Systems'),
    ('INFO3601', 'Platform Technologies II '),
    ('INFO3602', 'Web Programming and Technologies II '),
    ('INFO3604', 'Project'),
    ('INFO3605', 'Fundamentals of LAN Technologies '),
    ('INFO3606', 'Cloud Computing'),
    ('INFO3607', 'Fundamentals of WAN Technologies '),
    ('INFO3608', 'E-Commerce'),
    ('INFO3609', 'Internship I '),
    ('INFO3610', 'Internship II '),
    ('INFO3611', 'Database Administration  ')
]

# Helper function to get course name by code
def get_course_name(course_code):
    """
    Return the course name for a given course code.
    If not found, returns the course code itself.
    """
    for code, name in STANDARD_COURSES:
        if code == course_code:
            return name
    return course_code

# Helper function to get all course codes
def get_all_course_codes():
    """
    Return a list of all course codes.
    """
    return [code for code, _ in STANDARD_COURSES]

# Helper function to get all courses as a dictionary
def get_courses_dict():
    """
    Return a dictionary of all courses with code as key and name as value.
    """
    return {code: name for code, name in STANDARD_COURSES}

# Helper function to validate a course code
def is_valid_course(course_code):
    """
    Check if a course code is valid.
    """
    return course_code in get_all_course_codes()