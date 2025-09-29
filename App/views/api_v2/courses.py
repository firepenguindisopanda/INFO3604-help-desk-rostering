from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from App.views.api_v2 import api_v2
from App.views.api_v2.utils import api_success, api_error, validate_json_request
from App.models import Course
from App.database import db
import logging

logging.basicConfig(level=logging.INFO)

@api_v2.route('/courses', methods=['GET'])
def get_courses():
    """
    Get all available courses
    
    Returns:
        Success: List of all courses with code and name
        Error: Server error message
    """
    try:
        courses = Course.query.all()
        # Format courses for frontend consumption
        courses_data = []
        for course in courses:
            courses_data.append({
                "code": course.code,
                "name": course.name
            })
        
        return api_success(courses_data, "Courses retrieved successfully")
        
    except Exception as e:
        return api_error(f"Failed to retrieve courses: {str(e)}", status_code=500)

@api_v2.route('/courses', methods=['POST'])
@jwt_required()
def create_course():
    """
    Create a new course (Admin only)
    
    Expected JSON body:
    {
        "code": "COMP1601",
        "name": "Computer Programming I"
    }
    
    Returns:
        Success: Created course data
        Error: Validation or creation error
    """
    data, error = validate_json_request(request)
    if error:
        return error
    
    code = data.get('code')
    name = data.get('name')
    
    if not code or not name:
        return api_error("Course code and name are required", status_code=400)
    
    # Check if course already exists
    existing_course = Course.query.get(code)
    if existing_course:
        return api_error(f"Course with code '{code}' already exists", status_code=409)
    
    try:
        # Create new course
        new_course = Course(code=code.strip().upper(), name=name.strip())
        db.session.add(new_course)
        db.session.commit()
        
        return api_success({
            "code": new_course.code,
            "name": new_course.name
        }, "Course created successfully")
        
    except Exception as e:
        db.session.rollback()
        return api_error(f"Failed to create course: {str(e)}", status_code=500)

@api_v2.route('/courses/<string:code>', methods=['GET'])
def get_course(code):
    """
    Get a specific course by code
    
    Args:
        code: Course code (e.g., COMP1601)
    
    Returns:
        Success: Course data
        Error: Course not found
    """
    course = Course.query.get(code.upper())
    
    if not course:
        return api_error(f"Course with code '{code}' not found", status_code=404)
    
    return api_success({
        "code": course.code,
        "name": course.name
    }, "Course retrieved successfully")

@api_v2.route('/courses/<string:code>', methods=['PUT'])
@jwt_required()
def update_course(code):
    """
    Update a course (Admin only)
    
    Args:
        code: Course code to update
        
    Expected JSON body:
    {
        "name": "Updated Course Name"
    }
    
    Returns:
        Success: Updated course data
        Error: Course not found or update error
    """
    data, error = validate_json_request(request)
    if error:
        return error
    
    course = Course.query.get(code.upper())
    
    if not course:
        return api_error(f"Course with code '{code}' not found", status_code=404)
    
    name = data.get('name')
    if not name:
        return api_error("Course name is required", status_code=400)
    
    try:
        course.name = name.strip()
        db.session.commit()
        
        return api_success({
            "code": course.code,
            "name": course.name
        }, "Course updated successfully")
        
    except Exception as e:
        db.session.rollback()
        return api_error(f"Failed to update course: {str(e)}", status_code=500)

@api_v2.route('/courses/<string:code>', methods=['DELETE'])
@jwt_required()
def delete_course(code):
    """
    Delete a course (Admin only)
    
    Args:
        code: Course code to delete
    
    Returns:
        Success: Deletion confirmation
        Error: Course not found or deletion error
    """
    course = Course.query.get(code.upper())
    
    if not course:
        return api_error(f"Course with code '{code}' not found", status_code=404)
    
    try:
        db.session.delete(course)
        db.session.commit()
        
        return api_success(message=f"Course '{code}' deleted successfully")
        
    except Exception as e:
        db.session.rollback()
        return api_error(f"Failed to delete course: {str(e)}", status_code=500)