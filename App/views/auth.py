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
from App.controllers.password_reset import create_password_reset_request

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
    courses = Course.query.all()
    return render_template('auth/register.html', courses=courses)

@auth_views.route('/register', methods=['POST'])
def register_action():
    try:
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        degree = request.form.get('degree')
        reason = request.form.get('reason')
        
        selected_courses = request.form.getlist('courses[]')
        
        availability_data = request.form.get('availability', '[]')
        try:
            availability_slots = json.loads(availability_data)
        except json.JSONDecodeError:
            availability_slots = []
        
        transcript_file = request.files.get('transcript_file') if 'transcript_file' in request.files else None
        profile_picture_file = request.files.get('profile_picture_file') if 'profile_picture_file' in request.files else None
        
        if 'terms' not in request.form:
            flash('You must agree to the terms before registering.', 'error')
            return redirect(url_for('auth_views.register'))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('auth_views.register'))
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return redirect(url_for('auth_views.register'))
            
        if not any(c.isupper() for c in password):
            flash('Password must contain at least one uppercase letter.', 'error')
            return redirect(url_for('auth_views.register'))
            
        if not any(c.isdigit() for c in password):
            flash('Password must contain at least one number.', 'error')
            return redirect(url_for('auth_views.register'))
            
        if not any(not c.isalnum() for c in password):
            flash('Password must contain at least one special character.', 'error')
            return redirect(url_for('auth_views.register'))
        
        if not availability_slots:
            flash('Please select at least one availability slot.', 'error')
            return redirect(url_for('auth_views.register'))
        
        profile_picture_file = request.files.get('profile_picture_file') if 'profile_picture_file' in request.files else None
        success, message = create_registration_request(
            username, name, email, degree, reason, phone, transcript_file, profile_picture_file, selected_courses, password, availability_slots
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('auth_views.login_page'))
        else:
            flash(message, 'error')
            return redirect(url_for('auth_views.register'))
            
    except Exception as e:
        flash(f'An error occurred during registration: {str(e)}', 'error')
        return redirect(url_for('auth_views.register'))

@auth_views.route('/login', methods=['POST'])
def login_action():
    try:
        data = request.form
        token, role = login(data['username'], data['password'])
        
        if not token:
            flash('Invalid credentials. Please try again.', 'error')
            return redirect(url_for('auth_views.login_page'))
        
        if role == 'admin':
            response = redirect(url_for('schedule_views.schedule'))
        else:
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

@auth_views.route('/reset_password_request', methods=['POST'])
def reset_password_request():
    """Handle password reset request submission"""
    
    username = request.form.get('username')
    reason = request.form.get('reason')
    
    if not username or not reason:
        flash("Both ID and reason are required", "error")
        return redirect(url_for('auth_views.forgot_password'))
    
    success, message = create_password_reset_request(username, reason)
    
    if success:
        flash(message, "success")
        return redirect(url_for('auth_views.login_page'))
    else:
        flash(message, "error")
        return redirect(url_for('auth_views.forgot_password'))

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