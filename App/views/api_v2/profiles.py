from flask import request
from flask_jwt_extended import current_user, get_jwt_identity

from App.controllers.profile_management import (
    admin_update_staff_profile as admin_update_staff_profile_controller,
    get_admin_profile_context,
    get_staff_profile_details,
    update_student_profile as update_student_profile_controller,
)
from App.middleware import admin_required
from App.views.api_v2 import api_v2
from App.views.api_v2.utils import api_error, api_success, jwt_required_secure, validate_json_request


def _is_admin_user() -> bool:
    try:
        return bool(current_user and current_user.is_admin())
    except Exception:
        return False


@api_v2.route('/profiles/staff/<string:username>', methods=['GET'])
@jwt_required_secure()
def get_staff_profile(username: str):
    """Return staff profile details. Admins can fetch any profile; users can fetch their own."""
    requester = get_jwt_identity()
    if requester != username and not _is_admin_user():
        return api_error("Forbidden: cannot view another user's profile", status_code=403)

    profile_data, error = get_staff_profile_details(username)
    if error:
        return api_error(error, status_code=404)

    return api_success({"profile": profile_data})


@api_v2.route('/profiles/students/<string:username>', methods=['PUT'])
@jwt_required_secure()
@admin_required
def update_student_profile(username: str):
    """Admin update of core student profile fields."""
    data, error = validate_json_request(request)
    if error:
        return error

    success, message, status = update_student_profile_controller(username, data)
    if not success:
        return api_error(message, status_code=status)
    return api_success(message=message, data={"username": username})


@api_v2.route('/profiles/staff/<string:username>', methods=['PUT'])
@jwt_required_secure()
@admin_required
def admin_update_staff_profile(username: str):
    """Admin update of staff profile, courses, and availability."""
    data, error = validate_json_request(request)
    if error:
        return error

    success, message, status = admin_update_staff_profile_controller(username, data)
    if not success:
        return api_error(message, status_code=status)
    return api_success(message=message, data={"username": username})


@api_v2.route('/profiles/admin', methods=['GET'])
@jwt_required_secure()
@admin_required
def get_admin_profile():
    """Return admin profile context (parity with legacy admin profile page)."""
    context = get_admin_profile_context(current_user)
    return api_success({
        "profile": context.get("admin_profile"),
        "students": context.get("students", []),
    })
