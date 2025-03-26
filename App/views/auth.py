from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user, unset_jwt_cookies, set_access_cookies
import json
from datetime import datetime, time

from App.controllers import (
    login,
    create_registration_request
)
from App.models import Course, Availability
from App.database import db

auth_views = Blueprint('auth_views', __name__, template_folder='../templates')

@auth_views.route('/login', methods=['GET'])
def login_page():
    return render_template('auth/login.html')

@auth_views.route('/assistant-login')
def assistant_login():
    return render_template('auth/login.html', login_type='volunteer')

@auth_views.route('/admin-login')
def admin_login():
    return render_template('auth/login.html', login_type='admin')

@auth_views.route('/register', methods=['GET'])
def register():
    # Get all courses to display in the form
    courses = Course.query.all()
    return render_template('auth/register.html', courses=courses)

@auth_views.route('/register', methods=['POST'])
def register_action():
    try:
        # Extract form data
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        degree = request.form.get('degree')
        reason = request.form.get('reason')
        
        # Get selected courses
        selected_courses = request.form.getlist('courses[]')
        
        # Get availability data
        availability_data = request.form.get('availability', '[]')
        try:
            availability_slots = json.loads(availability_data)
        except json.JSONDecodeError:
            availability_slots = []
        
        # Get transcript file if provided
        transcript_file = request.files.get('transcript') if 'transcript' in request.files else None
        
        # Check terms acceptance
        if 'terms' not in request.form:
            flash('You must agree to the terms before registering.', 'error')
            return redirect(url_for('auth_views.register'))
        
        # Validate password matches confirmation
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('auth_views.register'))
        
        # Validate password strength (similar to client-side validation)
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return redirect(url_for('auth_views.register'))
            
        # Check for uppercase letter
        if not any(c.isupper() for c in password):
            flash('Password must contain at least one uppercase letter.', 'error')
            return redirect(url_for('auth_views.register'))
            
        # Check for digit
        if not any(c.isdigit() for c in password):
            flash('Password must contain at least one number.', 'error')
            return redirect(url_for('auth_views.register'))
            
        # Check for special character
        if not any(not c.isalnum() for c in password):
            flash('Password must contain at least one special character.', 'error')
            return redirect(url_for('auth_views.register'))
        
        # Validate at least one availability slot is selected
        if not availability_slots:
            flash('Please select at least one availability slot.', 'error')
            return redirect(url_for('auth_views.register'))
        
        # Create registration request with password
        success, message = create_registration_request(
            username, name, email, degree, reason, phone, transcript_file, selected_courses, password
        )
        
        if success:
            # If registration is successful, save availability slots
            try:
                create_availability_slots(username, availability_slots)
                flash(message, 'success')
                return redirect(url_for('auth_views.login_page'))
            except Exception as e:
                flash(f"Registration successful but error saving availability: {str(e)}", 'error')
                return redirect(url_for('auth_views.login_page'))
        else:
            flash(message, 'error')
            return redirect(url_for('auth_views.register'))
            
    except Exception as e:
        flash(f'An error occurred during registration: {str(e)}', 'error')
        return redirect(url_for('auth_views.register'))

def create_availability_slots(username, availability_slots):
    """Create availability records for a user based on form data"""
    # First, check if any existing availability slots need to be removed
    # (this is mostly relevant for updates rather than initial registration)
    Availability.query.filter_by(username=username).delete()
    db.session.commit()
    
    # Now create new availability slots
    for slot in availability_slots:
        try:
            day = slot.get('day', 0)  # 0=Monday, 1=Tuesday, etc.
            start_time_str = slot.get('start_time', '9:00:00')
            end_time_str = slot.get('end_time', '10:00:00')
            
            # Parse the time strings into time objects
            start_time = None
            end_time = None
            
            if isinstance(start_time_str, str):
                try:
                    # Try parsing as HH:MM:SS
                    hour, minute, second = map(int, start_time_str.split(':'))
                    start_time = time(hour=hour, minute=minute, second=second)
                except ValueError:
                    # If that fails, just use the hour
                    hour = int(start_time_str.split(':')[0])
                    start_time = time(hour=hour)
            
            if isinstance(end_time_str, str):
                try:
                    # Try parsing as HH:MM:SS
                    hour, minute, second = map(int, end_time_str.split(':'))
                    end_time = time(hour=hour, minute=minute, second=second)
                except ValueError:
                    # If that fails, just use the hour + 1
                    hour = int(end_time_str.split(':')[0])
                    end_time = time(hour=hour)
            
            # Create availability record
            if start_time and end_time:
                availability = Availability(username, day, start_time, end_time)
                db.session.add(availability)
        
        except Exception as e:
            print(f"Error creating availability slot: {e}")
            # Continue with other slots even if this one fails
    
    db.session.commit()

@auth_views.route('/login', methods=['POST'])
def login_action():
    try:
        data = request.form
        token, role = login(data['username'], data['password'])
        
        if not token:
            flash('Invalid credentials. Please try again.', 'error')
            return redirect(url_for('auth_views.login_page'))
        
        # Route based on role
        if role == 'admin':
            # Admin users go to the existing schedule page
            response = redirect(url_for('schedule_views.schedule'))
        else:  # volunteer/assistant
            # Volunteers go to their dashboard
            response = redirect(url_for('volunteer_views.dashboard'))
            
        set_access_cookies(response, token)
        flash('Login Successful', 'success')
        return response
        
    except Exception as e:
        print(f"Login error: {e}")
        flash('An error occurred during login. Please try again.', 'error')
        return redirect(url_for('auth_views.login_page'))

@auth_views.route('/forgot-password', methods=['GET'])
def forgot_password():
    return render_template('auth/forgot_password.html')

@auth_views.route('/reset-password-request', methods=['POST'])
def reset_password_request():
    username = request.form.get('username', '')
    flash('If an account with this ID exists, password reset instructions have been sent.', 'success')
    return redirect(url_for('auth_views.login_page'))

@auth_views.route('/logout', methods=['GET'])
def logout_action():
    response = redirect(url_for('auth_views.login_page'))
    unset_jwt_cookies(response)
    flash("Successfully logged out!")
    return response

@auth_views.route('/api/login', methods=['POST'])
def user_login_api():
    try:
        data = request.json
        token, role = login(data['username'], data['password'])
        if not token:
            return jsonify(message='Invalid credentials'), 401
        response = jsonify(access_token=token, role=role)
        set_access_cookies(response, token)
        return response
    except Exception as e:
        return jsonify(message=str(e)), 500

@auth_views.route('/api/identify', methods=['GET'])
@jwt_required()
def identify_user():
    return jsonify({
        'message': f"username: {current_user.username}, id: {current_user.id}, role: {current_user.role}"
    })