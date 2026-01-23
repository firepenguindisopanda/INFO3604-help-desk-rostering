from flask import request
from flask_jwt_extended import get_jwt_identity
from App.views.api_v2 import api_v2
from App.views.api_v2.utils import api_success, api_error, jwt_required_secure
from App.controllers.user import get_user

@api_v2.route('/me', methods=['GET'])
@jwt_required_secure()
def get_me():
    """Return info for the currently authenticated user (for session bootstrap)"""
    username = get_jwt_identity()
    if not username:
        return api_error("Not authenticated", status_code=401)
    user = get_user(username)
    if not user:
        return api_error("User not found", status_code=404)
    # Return user info (sanitize as needed)
    return api_success({
        "user": {
            "id": getattr(user, 'id', None),
            "username": getattr(user, 'username', None),
            "email": getattr(user, 'email', None),
            "first_name": getattr(user, 'first_name', None),
            "last_name": getattr(user, 'last_name', None),
            "role": getattr(user, 'role', None),
            "active": getattr(user, 'active', None),
        }
    }, message="User info loaded")