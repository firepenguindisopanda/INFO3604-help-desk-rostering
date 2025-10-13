from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user, unset_jwt_cookies, set_access_cookies
import json
from datetime import datetime, time

from App.controllers import (
    login,
    create_registration_request
)
from App.controllers.registration import get_registration_request, get_registration_request_by_username
from App.controllers.course import get_all_courses
from App.controllers.password_reset import create_password_reset_request
from App.database import db

auth_views = Blueprint('auth_views', __name__, template_folder='../templates')

@auth_views.route('/login', methods=['GET'])
def login_page():
    # If redirected here after an approval, show accepted message
    status = request.args.get('status')
    username = request.args.get('username')
    if status and status.lower() == 'accepted':
        flash('Your registration request has been approved. You may now log in.', 'request_accepted')
    return render_template('auth/login.html', prefill_username=username)

@auth_views.route('/assistant-login')
def assistant_login():
    return render_template('auth/login.html', login_type='volunteer')

@auth_views.route('/admin-login')
def admin_login():
    return render_template('auth/login.html', login_type='admin')

@auth_views.route('/register', methods=['GET'])
def register():
    courses = get_all_courses()
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
        username = data.get('username')
        password = data.get('password')

        # Check for existing registration requests for this username using controller
        reg = get_registration_request_by_username(username)
        if reg:
            status = (reg.status or '').upper()
            if status == 'PENDING':
                flash('Your registration request is still pending approval.', 'request_pending')
                return redirect(url_for('auth_views.login_page'))
            if status == 'REJECTED':
                flash('Your registration request was rejected. Please contact an administrator.', 'request_rejected')
                return redirect(url_for('auth_views.login_page'))

        token, role = login(username, password)

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