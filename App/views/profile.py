from flask import Blueprint, render_template, jsonify, request, abort, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user
from App.controllers.user import get_user_profile
from App.controllers.help_desk_assistant import get_active_help_desk_assistants
from App.controllers.lab_assistant import get_active_lab_assistants
from App.controllers.student import get_student
from App.models import Student, HelpDeskAssistant, CourseCapability, Availability, User, Course
from App.database import db
from App.middleware import admin_required
from datetime import time
import json

profile_views = Blueprint('profile_views', __name__, template_folder='../templates')

@profile_views.route('/profile')
@jwt_required()
@admin_required
def profile():
    # Get the current user from JWT
    user = current_user
    
    # Create admin profile data
    admin_profile = {
        'name': user.username,
        'username': user.username,
        'email': f"{user.username}@admin.uwi.edu",
        'role': user.role
    }
    
    # Filter students based on admin role
    if user.role == 'helpdesk':
        assistants = get_active_help_desk_assistants()
    elif user.role == 'lab':
        assistants = get_active_lab_assistants()
    else:
        assistants = []
    
    # Format student data for the template
    formatted_students = []
    for assistant in assistants:
        student = get_student(assistant.username)
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
    """Staff profile view with context awareness for navigation"""
    # Get user details from database directly
    import json  # Ensure json is imported
    
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
    
    # Parse profile_data JSON to get email and phone
    profile_data = {}
    if hasattr(student, 'profile_data') and student.profile_data:
        try:
            profile_data = json.loads(student.profile_data)
        except:
            profile_data = {}
    
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
        'availabilities': [avail.get_json() for avail in availabilities],
        'email': profile_data.get('email', f"{username}@my.uwi.edu"),
        'phone': profile_data.get('phone', '')  # Get phone from profile_data
    }
    
    # Store the referrer information to use in template for back button
    referrer = request.referrer
    
    print(f"Generated profile for {profile['name']} with phone: {profile['phone']}")
    
    # Render the template with the profile data and referrer context
    return render_template('admin/profile/staff_profile.html', profile=profile, referrer=referrer)

@profile_views.route('/api/staff/<username>/profile')
@jwt_required()
def get_staff_profile_api(username):
    # Get user details
    import json  # Ensure json is imported
    
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
    
    # Parse profile_data JSON to get email and phone
    profile_data = {}
    if hasattr(student, 'profile_data') and student.profile_data:
        try:
            profile_data = json.loads(student.profile_data)
        except:
            profile_data = {}
    
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
        'availabilities': [avail.get_json() for avail in availabilities],
        'email': profile_data.get('email', f"{username}@my.uwi.edu"),
        'phone': profile_data.get('phone', '')  # Get phone from profile_data
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
    """API endpoint for admin to update their own profile - now just a stub that returns success"""
    return jsonify({
        'success': True,
        'message': 'Profile functionality disabled'
    })

@profile_views.route('/api/admin/staff/update-profile', methods=['POST'])
@jwt_required()
@admin_required
def admin_update_staff_profile():
    """Comprehensive API endpoint for admin to update all aspects of a student profile"""
    try:
        import json  # Ensure json is imported
        
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
        
        # Update profile data (email, phone, etc.)
        profile_data = {}
        if hasattr(student, 'profile_data') and student.profile_data:
            try:
                profile_data = json.loads(student.profile_data)
            except:
                profile_data = {}
        
        if 'email' in data:
            profile_data['email'] = data['email']
        
        if 'phone' in data:
            profile_data['phone'] = data['phone']
            
        # Save profile data back to student
        student.profile_data = json.dumps(profile_data)
        
        # Update course capabilities
        if 'courses' in data:
            # First, remove all existing course capabilities
            CourseCapability.query.filter_by(assistant_username=username).delete()
            
            # Add new course capabilities
            for course_code in data['courses']:
                # Verify the course exists
                course = Course.query.get(course_code)
                if not course:
                    # Create the course if it doesn't exist
                    course = Course(course_code, f"Course {course_code}")
                    db.session.add(course)
                
                # Add the capability
                capability = CourseCapability(username, course_code)
                db.session.add(capability)
        
        # Update availability
        if 'availabilities' in data:
            # First, remove all existing availabilities
            Availability.query.filter_by(username=username).delete()
            
            # Add new availabilities
            for slot in data['availabilities']:
                try:
                    day = slot.get('day', 0)  # 0 for Monday, 1 for Tuesday, etc.
                    
                    # Parse times with proper error handling
                    start_time_str = slot.get('start_time', '00:00:00')
                    end_time_str = slot.get('end_time', '00:00:00')
                    
                    # Ensure we have valid time strings before parsing
                    if not isinstance(start_time_str, str) or not isinstance(end_time_str, str):
                        print(f"Invalid time format: start={start_time_str}, end={end_time_str}")
                        continue
                        
                    try:
                        # Try parsing as HH:MM:SS
                        hour, minute, second = map(int, start_time_str.split(':'))
                        start_time = time(hour=hour, minute=minute, second=second)
                    except ValueError:
                        # If that fails, just use the hour
                        try:
                            hour = int(start_time_str.split(':')[0])
                            start_time = time(hour=hour)
                        except ValueError:
                            print(f"Could not parse start time: {start_time_str}")
                            continue
                            
                    try:
                        # Try parsing as HH:MM:SS
                        hour, minute, second = map(int, end_time_str.split(':'))
                        end_time = time(hour=hour, minute=minute, second=second)
                    except ValueError:
                        # If that fails, just use the hour
                        try:
                            hour = int(end_time_str.split(':')[0])
                            end_time = time(hour=hour)
                        except ValueError:
                            print(f"Could not parse end time: {end_time_str}")
                            continue
                    
                    # Ensure day is an integer in range 0-4 (Mon-Fri)
                    day = int(day)
                    if day < 0 or day > 4:
                        print(f"Day out of range (0-4): {day}")
                        continue
                    
                    availability = Availability(username, day, start_time, end_time)
                    db.session.add(availability)
                    print(f"Added availability: Day {day}, {start_time}-{end_time}")
                except Exception as e:
                    print(f"Error adding individual availability: {e}")
                    # Continue with other availabilities even if this one failed
        
        # Save all changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"Error updating Student Assistant profile: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'An error occurred while updating the profile: {str(e)}'
        })