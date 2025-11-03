"""
API v2 Password Reset Management Endpoints

This module handles password reset requests with design principles:
- Single Responsibility: Each function manages one aspect of password resets
- Encapsulation: Hides complexity behind clean interfaces
- Security: Proper validation and secure password handling
- Fail Fast: Immediate validation of inputs
"""

from flask import request
from flask_jwt_extended import get_jwt_identity, current_user

from App.views.api_v2 import api_v2
from App.views.api_v2.utils import (
    api_success, 
    api_error, 
    jwt_required_secure,
    validate_json_request_secure
)
from App.middleware import admin_required

# Import controllers (dependency injection pattern)
from App.controllers.password_reset import (
    get_all_password_reset_requests,
    complete_password_reset,
    reject_password_reset
)

# Constants (DRY principle)
INVALID_RESET_ID_MSG = "Invalid reset ID"
INVALID_PASSWORD_MSG = "Invalid password"
PASSWORD_TOO_SHORT_MSG = "Password must be at least 6 characters long"
FAILED_TO_COMPLETE_MSG = "Failed to complete password reset"
FAILED_TO_REJECT_MSG = "Failed to reject password reset"
FAILED_TO_RETRIEVE_MSG = "Failed to retrieve password reset requests"


def _validate_reset_id(reset_id):
    """
    Validate reset ID parameter
    
    Single Responsibility: Only validates reset ID
    Type Safety: Ensures proper integer format
    """
    return isinstance(reset_id, int) and reset_id > 0


def _validate_new_password(password):
    """
    Validate new password according to security requirements
    
    Single Responsibility: Only validates password
    Security: Enforces minimum length and type requirements
    """
    if not password or not isinstance(password, str):
        return False, INVALID_PASSWORD_MSG
    
    password = password.strip()
    if len(password) < 6:
        return False, PASSWORD_TOO_SHORT_MSG
    
    # Could be extended for complexity requirements (uppercase, numbers, etc.)
    return True, None


def _format_reset_requests(reset_data):
    """
    Format password reset requests for API response
    
    Single Responsibility: Only handles data formatting
    Consistency: Standardizes response structure
    """
    if not reset_data or not isinstance(reset_data, dict):
        return {
            'pending': [],
            'completed': [],
            'rejected': []
        }
    
    return {
        'pending': reset_data.get('pending', []),
        'completed': reset_data.get('completed', []),
        'rejected': reset_data.get('rejected', [])
    }


@api_v2.route('/password-resets', methods=['GET'])
@jwt_required_secure()
@admin_required
def get_password_resets_api():
    """
    Get all password reset requests (admin only)
    
    Single Responsibility: Only retrieves password reset data
    Authorization: Admin access required
    """
    try:
        # Use controller for business logic (loose coupling)
        reset_data = get_all_password_reset_requests()
        
        # Format data for consistent API response
        formatted_data = _format_reset_requests(reset_data)
        
        # Calculate totals for summary
        total_requests = (
            len(formatted_data['pending']) + 
            len(formatted_data['completed']) + 
            len(formatted_data['rejected'])
        )
        
        return api_success(
            data={
                'password_resets': formatted_data,
                'summary': {
                    'total_requests': total_requests,
                    'pending_count': len(formatted_data['pending']),
                    'completed_count': len(formatted_data['completed']),
                    'rejected_count': len(formatted_data['rejected'])
                }
            },
            message="Password reset requests retrieved successfully"
        )
        
    except Exception as e:
        return api_error(
            f"{FAILED_TO_RETRIEVE_MSG}: {str(e)}", 
            status_code=500
        )


@api_v2.route('/password-resets/<int:reset_id>/complete', methods=['POST'])
@jwt_required_secure()
@admin_required
def complete_password_reset_api(reset_id):
    """
    Complete a password reset request (admin only)
    
    Single Responsibility: Only handles password reset completion
    Security: Validates new password and admin authorization
    """
    try:
        # Validate reset_id (fail fast)
        if not _validate_reset_id(reset_id):
            return api_error(INVALID_RESET_ID_MSG, status_code=400)
        
        # Validate JSON request with required fields
        data, error = validate_json_request_secure(['new_password'])
        if error:
            return error
        
        new_password = data.get('new_password', '')
        
        # Validate new password (security)
        password_valid, password_error = _validate_new_password(new_password)
        if not password_valid:
            return api_error(password_error, status_code=400)
        
        # Get admin username for audit trail
        admin_username = current_user.username if current_user else get_jwt_identity()
        
        # Use controller for business logic (loose coupling)
        success, message = complete_password_reset(reset_id, new_password.strip(), admin_username)
        
        if success:
            return api_success(
                data={
                    'reset_id': reset_id,
                    'completed_by': admin_username
                },
                message=message
            )
        else:
            return api_error(message, status_code=400)
            
    except Exception as e:
        return api_error(
            f"{FAILED_TO_COMPLETE_MSG}: {str(e)}", 
            status_code=500
        )


@api_v2.route('/password-resets/<int:reset_id>/reject', methods=['POST'])
@jwt_required_secure()
@admin_required
def reject_password_reset_api(reset_id):
    """
    Reject a password reset request (admin only)
    
    Single Responsibility: Only handles password reset rejection
    Optional Reason: Allows providing rejection reason
    """
    try:
        # Validate reset_id (fail fast)
        if not _validate_reset_id(reset_id):
            return api_error(INVALID_RESET_ID_MSG, status_code=400)
        
        # Validate JSON request (reason is optional)
        data, error = validate_json_request_secure()
        if error:
            return error
        
        reason = data.get('reason', '').strip() if data else ''
        
        # Validate reason if provided (defensive programming)
        if reason and len(reason) > 500:
            return api_error("Rejection reason must be 500 characters or less", status_code=400)
        
        # Get admin username for audit trail
        admin_username = current_user.username if current_user else get_jwt_identity()
        
        # Use controller for business logic (loose coupling)
        success, message = reject_password_reset(reset_id, admin_username, reason)
        
        if success:
            response_data = {
                'reset_id': reset_id,
                'rejected_by': admin_username
            }
            if reason:
                response_data['reason'] = reason
                
            return api_success(
                data=response_data,
                message=message
            )
        else:
            return api_error(message, status_code=400)
            
    except Exception as e:
        return api_error(
            f"{FAILED_TO_REJECT_MSG}: {str(e)}", 
            status_code=500
        )


@api_v2.route('/password-resets/<int:reset_id>', methods=['GET'])
@jwt_required_secure()
@admin_required
def get_password_reset_details_api(reset_id):
    """
    Get details of a specific password reset request (admin only)
    
    Single Responsibility: Only retrieves single reset request details
    URL Parameters: Clean RESTful interface
    """
    try:
        # Validate reset_id (fail fast)
        if not _validate_reset_id(reset_id):
            return api_error(INVALID_RESET_ID_MSG, status_code=400)
        
        # Get all reset requests and find the specific one
        reset_data = get_all_password_reset_requests()
        formatted_data = _format_reset_requests(reset_data)
        
        # Search across all status categories
        target_reset = None
        status = None
        
        for status_category, requests in formatted_data.items():
            for reset_request in requests:
                if reset_request.get('id') == reset_id:
                    target_reset = reset_request
                    status = status_category
                    break
            if target_reset:
                break
        
        if not target_reset:
            return api_error(f"Password reset request {reset_id} not found", status_code=404)
        
        # Add status to the response
        target_reset['status'] = status
        
        return api_success(
            data={'password_reset': target_reset},
            message=f"Password reset request {reset_id} retrieved successfully"
        )
        
    except Exception as e:
        return api_error(
            f"Failed to retrieve password reset details: {str(e)}", 
            status_code=500
        )


@api_v2.route('/password-resets/pending', methods=['GET'])
@jwt_required_secure()
@admin_required
def get_pending_password_resets_api():
    """
    Get only pending password reset requests (admin only)
    
    Single Responsibility: Only retrieves pending requests
    Convenience: Filtered view for common admin task
    """
    try:
        # Use controller for business logic
        reset_data = get_all_password_reset_requests()
        formatted_data = _format_reset_requests(reset_data)
        
        pending_requests = formatted_data.get('pending', [])
        
        return api_success(
            data={
                'pending_requests': pending_requests,
                'count': len(pending_requests)
            },
            message=f"Found {len(pending_requests)} pending password reset requests"
        )
        
    except Exception as e:
        return api_error(
            f"{FAILED_TO_RETRIEVE_MSG} pending requests: {str(e)}", 
            status_code=500
        )