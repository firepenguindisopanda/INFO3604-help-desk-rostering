from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user, unset_jwt_cookies, set_access_cookies

from App.controllers import (
    login
)

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