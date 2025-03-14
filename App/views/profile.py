from flask import Blueprint, render_template, jsonify, request, abort, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user
from App.controllers.user import get_user_profile
from App.models import Student, HelpDeskAssistant, CourseCapability, Availability, User
from App.database import db
from App.middleware import admin_required

profile_views = Blueprint('profile_views', __name__, template_folder='../templates')

@profile_views.route('/profile')
@jwt_required()
def profile():
    # Get the current user from JWT
    user = current_user
    
    # Create admin profile data
    admin_profile = {
        'name': user.username,
        'username': user.username,
        'email': f"{user.username}@admin.uwi.edu"
    }
    
    # Get all students for the staff section
    students = Student.query.all()
    
    # Format student data for the template
    formatted_students = []
    for student in students:
        formatted_students.append({
            'username': student.username,
            'name': student.name if student.name else student.username
        })
    
    return render_template('admin/profile/index.html', 
                          admin_profile=admin_profile,
                          students=formatted_students)

@profile_views.route('/admin/staff/<username>/profile')
@jwt_required()
@admin_required
def staff_profile(username):
    # Get user details from database directly
    user = User.query.get(username)
    if not user:
        print(f"User {username} not found")
        flash("User not found", "error")
        return redirect(url_for('profile_views.profile'))
        
    # Get student details
    student = Student.query.get(username)
    if not student:
        print(f"Student {username} not found")
        flash("Student profile not found", "error")
        return redirect(url_for('profile_views.profile'))
        
    # Get help desk assistant details
    assistant = HelpDeskAssistant.query.get(username)
    if not assistant:
        print(f"Assistant {username} not found")
        # Create a default assistant object for rendering the template
        assistant = HelpDeskAssistant(username)
        
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

@profile_views.route('/api/student/profile', methods=['POST'])
@jwt_required()
@admin_required
def update_student_profile_api():
    """API endpoint for admin to update student profiles"""
    try:
        data = request.json
        username = data.get('username')
        
        if not username:
            return jsonify({
                'success': False,
                'message': 'Username is required'
            })
        
        # Get the student
        student = Student.query.get(username)
        if not student:
            return jsonify({
                'success': False,
                'message': f'Student with username {username} not found'
            })
        
        # Update student details
        if 'name' in data:
            student.name = data['name']
        
        if 'degree' in data:
            student.degree = data['degree']
        
        # Get the help desk assistant
        assistant = HelpDeskAssistant.query.get(username)
        if not assistant:
            # Create a new assistant if one doesn't exist
            assistant = HelpDeskAssistant(username)
            db.session.add(assistant)
        
        # Update assistant details
        if 'rate' in data:
            try:
                assistant.rate = float(data['rate'])
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'Rate must be a valid number'
                })
        
        if 'hours_minimum' in data:
            try:
                assistant.hours_minimum = int(data['hours_minimum'])
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'Minimum hours must be a valid integer'
                })
        
        if 'active' in data:
            # Convert to boolean
            active_value = data['active']
            if isinstance(active_value, str):
                assistant.active = active_value.lower() == 'true'
            else:
                assistant.active = bool(active_value)
        
        # Save changes
        db.session.add(student)
        db.session.add(assistant)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Student profile updated successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"Error updating student profile: {e}")
        return jsonify({
            'success': False,
            'message': f'An error occurred while updating the profile: {str(e)}'
        })

@profile_views.route('/api/admin/profile', methods=['POST'])
@jwt_required()
@admin_required
def update_admin_profile_api():
    """API endpoint for admin to update their own profile"""
    try:
        data = request.json
        username = current_user.username
        
        # Get the admin user
        admin = User.query.get(username)
        if not admin:
            return jsonify({
                'success': False,
                'message': 'Admin user not found'
            })
        
        # In a real application, you would store more profile info
        # For now, we'll just return success since there's not much to update
        
        return jsonify({
            'success': True,
            'message': 'Admin profile updated successfully'
        })
    
    except Exception as e:
        print(f"Error updating admin profile: {e}")
        return jsonify({
            'success': False,
            'message': f'An error occurred while updating the profile: {str(e)}'
        })