"""
API v2 Request Management Endpoints

This module handles shift change requests with single responsibility principle:
- Each function has one clear purpose
- Controller functions are used (no direct model access)
- Consistent error handling and response format
- Proper validation and defensive programming
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
from App.middleware import admin_required, volunteer_required

# Import controllers (dependency injection pattern)
from App.controllers.request import (
    get_all_requests,
    get_student_requests,
    approve_request,
    reject_request,
    create_student_request,
    cancel_request,
    get_available_shifts_for_student,
    get_available_replacements
)

# Constants (DRY principle)
INVALID_REQUEST_ID_MSG = "Invalid request ID"
FAILED_TO_RETRIEVE_MSG = "Failed to retrieve"
FAILED_TO_APPROVE_MSG = "Failed to approve request"
FAILED_TO_REJECT_MSG = "Failed to reject request"
FAILED_TO_SUBMIT_MSG = "Failed to submit request"
FAILED_TO_CANCEL_MSG = "Failed to cancel request"


@api_v2.route('/requests', methods=['GET'])
@jwt_required_secure()
def get_requests_api():
    """
    Get requests based on user role (admin gets all, volunteers get their own)
    
    Single Responsibility: Only retrieves and formats request data
    Encapsulation: Uses controller functions, hides implementation details
    """
    try:
        username = get_jwt_identity()
        
        # Use current_user to check admin status (abstraction)
        if current_user and current_user.is_admin():
            # Admin gets all requests - flatten the tutor structure
            tutors = get_all_requests()
            all_requests = []
            for tutor in tutors:
                all_requests.extend(tutor.get('requests', []))
            
            return api_success(
                data={'requests': all_requests},
                message="All requests retrieved successfully"
            )
        else:
            # Students get only their own requests
            requests_list = get_student_requests(username)
            return api_success(
                data={'requests': requests_list},
                message="Your requests retrieved successfully"
            )
            
    except Exception as e:
        return api_error(
            f"{FAILED_TO_RETRIEVE_MSG} requests: {str(e)}", 
            status_code=500
        )


@api_v2.route('/requests/<int:request_id>/approve', methods=['POST'])
@jwt_required_secure()
@admin_required
def approve_request_api(request_id):
    """
    Approve a shift change request (admin only)
    
    Single Responsibility: Only handles request approval
    Fail Fast: Validates request_id immediately
    """
    try:
        # Validate request_id (defensive programming)
        if request_id <= 0:
            return api_error(INVALID_REQUEST_ID_MSG, status_code=400)
        
        # Use controller for business logic (loose coupling)
        success, message = approve_request(request_id)
        
        if success:
            return api_success(
                data={'request_id': request_id},
                message=message
            )
        else:
            return api_error(message, status_code=400)
            
    except Exception as e:
        return api_error(
            f"{FAILED_TO_APPROVE_MSG}: {str(e)}", 
            status_code=500
        )


@api_v2.route('/requests/<int:request_id>/reject', methods=['POST'])
@jwt_required_secure()
@admin_required  
def reject_request_api(request_id):
    """
    Reject a shift change request (admin only)
    
    Single Responsibility: Only handles request rejection
    Consistent Interface: Same pattern as approve_request_api
    """
    try:
        # Validate request_id (defensive programming)
        if request_id <= 0:
            return api_error(INVALID_REQUEST_ID_MSG, status_code=400)
        
        # Use controller for business logic (loose coupling)
        success, message = reject_request(request_id)
        
        if success:
            return api_success(
                data={'request_id': request_id},
                message=message
            )
        else:
            return api_error(message, status_code=400)
            
    except Exception as e:
        return api_error(
            f"{FAILED_TO_REJECT_MSG}: {str(e)}", 
            status_code=500
        )


@api_v2.route('/requests', methods=['POST'])
@jwt_required_secure()
@volunteer_required
def submit_request_api():
    """
    Submit a new shift change request (volunteers only)
    
    Single Responsibility: Only handles request submission
    Validation: Comprehensive input validation
    """
    try:
        # Validate JSON request with required fields (fail fast)
        data, error = validate_json_request_secure(['shift_id', 'reason'])
        if error:
            return error
        
        username = get_jwt_identity()
        shift_id = data.get('shift_id')
        reason = data.get('reason')
        replacement = data.get('replacement')  # Optional field
        
        # Additional validation (defensive programming)
        if not isinstance(shift_id, int) or shift_id <= 0:
            return api_error(INVALID_REQUEST_ID_MSG, status_code=400)
        
        if not reason or len(reason.strip()) < 5:
            return api_error("Reason must be at least 5 characters long", status_code=400)
        
        # Use controller for business logic (loose coupling)
        success, message = create_student_request(
            username, 
            shift_id, 
            reason.strip(), 
            replacement
        )
        
        if success:
            return api_success(
                data={
                    'shift_id': shift_id,
                    'reason': reason.strip(),
                    'replacement': replacement
                },
                message=message
            )
        else:
            return api_error(message, status_code=400)
            
    except Exception as e:
        return api_error(
            f"{FAILED_TO_SUBMIT_MSG}: {str(e)}", 
            status_code=500
        )


@api_v2.route('/requests/<int:request_id>/cancel', methods=['POST'])
@jwt_required_secure()
@volunteer_required
def cancel_request_api(request_id):
    """
    Cancel a pending request (volunteers only)
    
    Single Responsibility: Only handles request cancellation
    Authorization: Ensures user can only cancel their own requests
    """
    try:
        # Validate request_id (defensive programming)
        if request_id <= 0:
            return api_error(INVALID_REQUEST_ID_MSG, status_code=400)
        
        username = get_jwt_identity()
        
        # Use controller for business logic (loose coupling)
        success, message = cancel_request(request_id, username)
        
        if success:
            return api_success(
                data={'request_id': request_id},
                message=message
            )
        else:
            return api_error(message, status_code=400)
            
    except Exception as e:
        return api_error(
            f"{FAILED_TO_CANCEL_MSG}: {str(e)}", 
            status_code=500
        )


@api_v2.route('/available-shifts', methods=['GET'])
@jwt_required_secure()
@volunteer_required
def get_available_shifts_api():
    """
    Get available shifts for the current student to request changes
    
    Single Responsibility: Only retrieves available shifts
    Read-only Operation: Safe to call multiple times
    """
    try:
        username = get_jwt_identity()
        
        # Use controller for business logic (loose coupling)
        available_shifts = get_available_shifts_for_student(username)
        
        return api_success(
            data={'available_shifts': available_shifts},
            message="Available shifts retrieved successfully"
        )
        
    except Exception as e:
        return api_error(
            f"{FAILED_TO_RETRIEVE_MSG} available shifts: {str(e)}", 
            status_code=500
        )


@api_v2.route('/available-replacements', methods=['GET'])
@jwt_required_secure()
@volunteer_required
def get_available_replacements_api():
    """
    Get available replacement assistants for shift changes
    
    Single Responsibility: Only retrieves replacement options
    Read-only Operation: Safe to call multiple times
    """
    try:
        username = get_jwt_identity()
        
        # Use controller for business logic (loose coupling)
        available_replacements = get_available_replacements(username)
        
        return api_success(
            data={'available_replacements': available_replacements},
            message="Available replacements retrieved successfully"
        )
        
    except Exception as e:
        return api_error(
            f"{FAILED_TO_RETRIEVE_MSG} available replacements: {str(e)}", 
            status_code=500
        )