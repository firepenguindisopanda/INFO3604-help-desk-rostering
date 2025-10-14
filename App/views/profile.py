from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user

from App.middleware import admin_required
from App.controllers.profile_management import (
    get_admin_profile_context,
    get_staff_profile_details,
    update_student_profile as update_student_profile_controller,
    admin_update_staff_profile as admin_update_staff_profile_controller,
)

profile_views = Blueprint('profile_views', __name__, template_folder='../templates')


@profile_views.route('/profile')
@jwt_required()
@admin_required
def profile():
    context = get_admin_profile_context(current_user)
    return render_template('admin/profile/index.html', **context)


@profile_views.route('/admin/staff/<username>/profile')
@jwt_required()
@admin_required
def staff_profile(username):
    profile_data, error = get_staff_profile_details(username)
    if error:
        flash(error, 'error')
        return redirect(url_for('profile_views.profile'))

    referrer = request.referrer
    return render_template('admin/profile/staff_profile.html', profile=profile_data, referrer=referrer)


@profile_views.route('/api/staff/<username>/profile')
@jwt_required()
def get_staff_profile_api(username):
    profile_data, error = get_staff_profile_details(username)
    if error:
        return jsonify({'success': False, 'message': error}), 404
    return jsonify({'success': True, 'profile': profile_data})


@profile_views.route('/api/student/profile', methods=['POST'])
@jwt_required()
@admin_required
def update_student_profile_api():
    data = request.get_json() or {}
    username = data.get('username')

    if not username:
        return jsonify({'success': False, 'message': 'Username is required'}), 400

    success, message, status = update_student_profile_controller(username, data)
    return jsonify({'success': success, 'message': message}), status


@profile_views.route('/api/admin/profile', methods=['POST'])
@jwt_required()
@admin_required
def update_admin_profile_api():
    return jsonify({
        'success': True,
        'message': 'Profile functionality disabled'
    })


@profile_views.route('/api/admin/staff/update-profile', methods=['POST'])
@jwt_required()
@admin_required
def admin_update_staff_profile():
    data = request.get_json() or {}
    username = data.get('username')

    if not username:
        return jsonify({'success': False, 'message': 'Username is required'}), 400

    success, message, status = admin_update_staff_profile_controller(username, data)
    return jsonify({'success': success, 'message': message}), status
