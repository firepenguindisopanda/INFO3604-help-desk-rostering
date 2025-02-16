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
    return render_template('auth/login.html', login_type='assistant')

@auth_views.route('/admin-login')
def admin_login():
    return render_template('auth/login.html', login_type='admin')

@auth_views.route('/login', methods=['POST'])
def login_action():
    try:
        data = request.form
        token = login(data['username'], data['password'])
        
        if not token:
            flash('Invalid credentials. Please try again.', 'error')
            return redirect(url_for('auth_views.login_page'))
        
        response = redirect(url_for('schedule_views.schedule'))
        set_access_cookies(response, token)
        flash('Login Successful', 'success')
        return response
        
    except Exception as e:
        print(f"Login error: {e}")
        flash('An error occurred during login. Please try again.', 'error')
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
        token = login(data['username'], data['password'])
        if not token:
            return jsonify(message='Invalid credentials'), 401
        response = jsonify(access_token=token)
        set_access_cookies(response, token)
        return response
    except Exception as e:
        return jsonify(message=str(e)), 500

@auth_views.route('/api/identify', methods=['GET'])
@jwt_required()
def identify_user():
    return jsonify({
        'message': f"username: {current_user.username}, id : {current_user.id}"
    })