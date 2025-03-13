from flask import Blueprint, render_template, jsonify, request, abort
from flask_jwt_extended import jwt_required, current_user
from App.controllers.user import get_user_profile
from App.models import Student, HelpDeskAssistant, CourseCapability, Availability, User
from App.middleware import admin_required

profile_views = Blueprint('profile_views', __name__, template_folder='../templates')

@profile_views.route('/profile')
@jwt_required()
def profile():
    return render_template('admin/profile/index.html')

@profile_views.route('/admin/staff/<username>/profile')
@jwt_required()
@admin_required
def staff_profile(username):
    # Get user details from database directly
    user = User.query.get(username)
    if not user:
        print(f"User {username} not found")
        abort(404)
        
    # Get student details
    student = Student.query.get(username)
    if not student:
        print(f"Student {username} not found")
        abort(404)
        
    # Get help desk assistant details
    assistant = HelpDeskAssistant.query.get(username)
    if not assistant:
        print(f"Assistant {username} not found")
        abort(404)
        
    # Get course capabilities
    course_capabilities = CourseCapability.query.filter_by(assistant_username=username).all()
    
    # Get availabilities
    availabilities = Availability.query.filter_by(username=username).all()
    
    # Build profile data
    profile = {
        'username': username,
        'name': student.name if student.name else username,
        'degree': student.degree,
        'active': assistant.active,
        'rate': assistant.rate,
        'hours_worked': assistant.hours_worked,
        'hours_minimum': assistant.hours_minimum,
        'courses': [cap.course_code for cap in course_capabilities],
        'availabilities': [avail.get_json() for avail in availabilities]
    }
    
    print(f"Generated profile for {profile['name']} with {len(profile['courses'])} courses and {len(profile['availabilities'])} availability slots")
    
    # Render the template with the profile data
    return render_template('admin/profile/staff_profile.html', profile=profile)

@profile_views.route('/api/staff/<username>/profile')
@jwt_required()
def get_staff_profile_api(username):
    # Get user details
    user = User.query.get(username)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
        
    # Get student details
    student = Student.query.get(username)
    if not student:
        return jsonify({'success': False, 'message': 'Student not found'}), 404
        
    # Get help desk assistant details
    assistant = HelpDeskAssistant.query.get(username)
    if not assistant:
        return jsonify({'success': False, 'message': 'Assistant not found'}), 404
        
    # Get course capabilities
    course_capabilities = CourseCapability.query.filter_by(assistant_username=username).all()
    
    # Get availabilities
    availabilities = Availability.query.filter_by(username=username).all()
    
    # Build profile data
    profile = {
        'username': username,
        'name': student.name if student.name else username,
        'degree': student.degree,
        'active': assistant.active,
        'rate': assistant.rate,
        'hours_worked': assistant.hours_worked,
        'hours_minimum': assistant.hours_minimum,
        'courses': [cap.course_code for cap in course_capabilities],
        'availabilities': [avail.get_json() for avail in availabilities]
    }
    
    return jsonify({'success': True, 'profile': profile})