from functools import wraps
from flask import flash, redirect, url_for
from flask_jwt_extended import current_user, jwt_required, verify_jwt_in_request

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        verify_jwt_in_request()
        if not current_user or not current_user.is_admin():
            flash("You don't have permission to access this resource", "error")
            return redirect(url_for('auth_views.login_page'))
        return f(*args, **kwargs)
    return decorated_function

def volunteer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        verify_jwt_in_request()
        if not current_user or not current_user.is_volunteer():
            flash("You don't have permission to access this resource", "error")
            return redirect(url_for('auth_views.login_page'))
        return f(*args, **kwargs)
    return decorated_function