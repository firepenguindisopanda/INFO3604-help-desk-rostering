"""
API v2 User Management Endpoints

This module handles user management with design principles:
- Single Responsibility: Each function manages one aspect of users
- Loose Coupling: Uses controllers, not direct model access
- Validation: Comprehensive input validation
- Security: Proper authentication and authorization
"""

from flask import request
from flask_jwt_extended import get_jwt_identity

from App.views.api_v2 import api_v2
from App.views.api_v2.utils import (
    api_success, 
    api_error, 
    jwt_required_secure,
    validate_json_request_secure
)
from App.middleware import admin_required

# Import controllers (dependency injection pattern)
from App.controllers import (
    create_user,
    get_all_users_json
)

# Constants (DRY principle)
INVALID_USERNAME_MSG = "Invalid username"
INVALID_PASSWORD_MSG = "Invalid password"
USERNAME_TOO_SHORT_MSG = "Username must be at least 3 characters long"
PASSWORD_TOO_SHORT_MSG = "Password must be at least 6 characters long"
FAILED_TO_CREATE_USER_MSG = "Failed to create user"
FAILED_TO_RETRIEVE_USERS_MSG = "Failed to retrieve users"


def _validate_username(username):
    """
    Validate username according to business rules
    
    Single Responsibility: Only validates username
    Business Rules: Username must be at least 3 chars, alphanumeric + underscore
    """
    if not username or not isinstance(username, str):
        return False, INVALID_USERNAME_MSG
    
    username = username.strip()
    if len(username) < 3:
        return False, USERNAME_TOO_SHORT_MSG
    
    # Allow alphanumeric and underscore only (security)
    if not username.replace('_', '').isalnum():
        return False, "Username can only contain letters, numbers, and underscores"
    
    return True, None


def _validate_password(password):
    """
    Validate password according to security requirements
    
    Single Responsibility: Only validates password
    Security: Minimum length requirement, could be extended for complexity
    """
    if not password or not isinstance(password, str):
        return False, INVALID_PASSWORD_MSG
    
    if len(password) < 6:
        return False, PASSWORD_TOO_SHORT_MSG
    
    return True, None


def _sanitize_user_data(users_data):
    """
    Sanitize user data for safe API response
    
    Single Responsibility: Only handles data sanitization
    Security: Removes sensitive fields like passwords
    """
    if not users_data:
        return []
    
    sanitized = []
    for user in users_data:
        if isinstance(user, dict):
            # Remove sensitive fields (defensive programming)
            safe_user = {k: v for k, v in user.items() if k not in ['password', 'password_hash']}
            sanitized.append(safe_user)
        else:
            # Handle user objects with attributes
            safe_user = {
                'id': getattr(user, 'id', None),
                'username': getattr(user, 'username', None),
                'role': getattr(user, 'role', None),
                'active': getattr(user, 'active', None)
            }
            sanitized.append(safe_user)
    
    return sanitized


@api_v2.route('/users', methods=['GET'])
@jwt_required_secure()
@admin_required
def get_users_api():
    """
    Get all users (admin only)
    
    Single Responsibility: Only retrieves user data
    Authorization: Admin access required
    Security: Sensitive data is sanitized
    """
    try:
        # Use controller for business logic (loose coupling)
        users_data = get_all_users_json()
        
        # Sanitize data for safe API response (security)
        sanitized_users = _sanitize_user_data(users_data)
        
        return api_success(
            data={
                'users': sanitized_users,
                'count': len(sanitized_users)
            },
            message="Users retrieved successfully"
        )
        
    except Exception as e:
        return api_error(
            f"{FAILED_TO_RETRIEVE_USERS_MSG}: {str(e)}", 
            status_code=500
        )


@api_v2.route('/users', methods=['POST'])
@jwt_required_secure()
@admin_required
def create_user_api():
    """
    Create a new user (admin only)
    
    Single Responsibility: Only handles user creation
    Validation: Comprehensive input validation
    Security: Password validation, admin-only access
    """
    try:
        # Validate JSON request with required fields (fail fast)
        data, error = validate_json_request_secure(['username', 'password'])
        if error:
            return error
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        role = data.get('role', 'volunteer')  # Default role
        
        # Validate username (defensive programming)
        username_valid, username_error = _validate_username(username)
        if not username_valid:
            return api_error(username_error, status_code=400)
        
        # Validate password (security)
        password_valid, password_error = _validate_password(password)
        if not password_valid:
            return api_error(password_error, status_code=400)
        
        # Validate role if provided
        valid_roles = ['admin', 'volunteer', 'helpdesk', 'lab']
        if role not in valid_roles:
            return api_error(
                f"Invalid role. Must be one of: {', '.join(valid_roles)}", 
                status_code=400
            )
        
        # Use controller for business logic (loose coupling)
        try:
            user = create_user(username, password)
            
            if not user:
                return api_error("User creation failed", status_code=400)
            
            # Return sanitized user data (security)
            user_data = {
                'id': user.id,
                'username': user.username,
                'role': getattr(user, 'role', role)
            }
            
            return api_success(
                data={'user': user_data},
                message=f"User '{username}' created successfully"
            )
            
        except Exception as creation_error:
            # Handle specific creation errors (defensive programming)
            error_msg = str(creation_error)
            if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                return api_error(f"Username '{username}' already exists", status_code=409)
            else:
                raise  # Re-raise for general error handling
        
    except Exception as e:
        return api_error(
            f"{FAILED_TO_CREATE_USER_MSG}: {str(e)}", 
            status_code=500
        )


@api_v2.route('/users/<username>', methods=['GET'])
@jwt_required_secure()
@admin_required
def get_user_by_username_api(username):
    """
    Get a specific user by username (admin only)
    
    Single Responsibility: Only retrieves single user data
    URL Parameters: Clean RESTful interface
    """
    try:
        # Validate username parameter (fail fast)
        username_valid, username_error = _validate_username(username)
        if not username_valid:
            return api_error(username_error, status_code=400)
        
        # Get all users and find the specific one (could be optimized with a dedicated controller)
        users_data = get_all_users_json()
        
        # Find user by username
        target_user = None
        for user in users_data:
            user_username = user.get('username') if isinstance(user, dict) else getattr(user, 'username', None)
            if user_username == username:
                target_user = user
                break
        
        if not target_user:
            return api_error(f"User '{username}' not found", status_code=404)
        
        # Sanitize data for safe API response
        sanitized_user = _sanitize_user_data([target_user])[0]
        
        return api_success(
            data={'user': sanitized_user},
            message=f"User '{username}' retrieved successfully"
        )
        
    except Exception as e:
        return api_error(
            f"Failed to retrieve user: {str(e)}", 
            status_code=500
        )


@api_v2.route('/users/<username>/activate', methods=['POST'])
@jwt_required_secure()
@admin_required
def activate_user_api(username):
    """
    Activate a user account (admin only)
    
    Single Responsibility: Only handles user activation
    Extensibility: Could be extended for deactivation
    """
    try:
        # Validate username parameter
        username_valid, username_error = _validate_username(username)
        if not username_valid:
            return api_error(username_error, status_code=400)
        
        # Note: This would need a dedicated controller function for user activation
        # For now, return a placeholder response
        return api_success(
            data={'username': username, 'status': 'active'},
            message=f"User '{username}' activation endpoint - needs controller implementation"
        )
        
    except Exception as e:
        return api_error(
            f"Failed to activate user: {str(e)}", 
            status_code=500
        )


@api_v2.route('/users/search', methods=['GET'])
@jwt_required_secure()
@admin_required
def search_users_api():
    """
    Search users by criteria (admin only)
    
    Single Responsibility: Only handles user search
    Flexibility: Supports multiple search criteria
    """
    try:
        # Get search parameters
        query = request.args.get('q', '').strip()
        role = request.args.get('role', '').strip()
        active = request.args.get('active', '').strip()
        
        # Get all users
        users_data = get_all_users_json()
        sanitized_users = _sanitize_user_data(users_data)
        
        # Apply filters (business logic)
        filtered_users = sanitized_users
        
        if query:
            # Search in username (case-insensitive)
            filtered_users = [
                user for user in filtered_users 
                if query.lower() in str(user.get('username', '')).lower()
            ]
        
        if role:
            # Filter by role
            filtered_users = [
                user for user in filtered_users 
                if user.get('role') == role
            ]
        
        if active in ['true', 'false']:
            # Filter by active status
            is_active = active == 'true'
            filtered_users = [
                user for user in filtered_users 
                if user.get('active') == is_active
            ]
        
        return api_success(
            data={
                'users': filtered_users,
                'count': len(filtered_users),
                'filters': {
                    'query': query,
                    'role': role,
                    'active': active
                }
            },
            message=f"Found {len(filtered_users)} users"
        )
        
    except Exception as e:
        return api_error(
            f"Failed to search users: {str(e)}", 
            status_code=500
        )