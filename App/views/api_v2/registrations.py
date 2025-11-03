"""
API v2 Registration Management Endpoints

This module handles user registration requests with design principles:
- Single Responsibility: Each function handles one registration operation
- Encapsulation: Abstracts file handling and business logic
- Security: Safe file handling and proper validation
- Extensibility: Supports both local and remote file storage
"""

from flask import request, redirect, current_app
from flask_jwt_extended import get_jwt_identity, current_user
import mimetypes

from App.views.api_v2 import api_v2
from App.views.api_v2.utils import (
    api_success, 
    api_error, 
    jwt_required_secure,
    validate_json_request_secure
)
from App.middleware import admin_required

# Import controllers (dependency injection pattern)
from App.controllers.registration import (
    get_all_registration_requests,
    approve_registration,
    reject_registration,
    get_registration_request,
    resolve_transcript_asset
)

# Constants (DRY principle)
INVALID_REGISTRATION_ID_MSG = "Invalid registration ID"
REGISTRATION_NOT_FOUND_MSG = "Registration not found"
TRANSCRIPT_NOT_FOUND_MSG = "Transcript not found"
FAILED_TO_APPROVE_MSG = "Failed to approve registration"
FAILED_TO_REJECT_MSG = "Failed to reject registration"
FAILED_TO_RETRIEVE_MSG = "Failed to retrieve registrations"
FAILED_TO_DOWNLOAD_MSG = "Failed to download transcript"


def _validate_registration_id(registration_id):
    """
    Validate registration ID parameter
    
    Single Responsibility: Only validates registration ID
    Type Safety: Ensures proper integer format
    """
    return isinstance(registration_id, int) and registration_id > 0


def _format_registration_data(registration_data):
    """
    Format registration data for API response
    
    Single Responsibility: Only handles data formatting
    Consistency: Standardizes response structure
    """
    if not registration_data or not isinstance(registration_data, dict):
        return {
            'pending': [],
            'approved': [],
            'rejected': []
        }
    
    return {
        'pending': registration_data.get('pending', []),
        'approved': registration_data.get('approved', []),
        'rejected': registration_data.get('rejected', [])
    }


def _safe_resolve_transcript(registration, base_path=None):
    """
    Safely resolve transcript asset with error handling
    
    Single Responsibility: Only handles transcript resolution
    Defensive Programming: Handles all error cases gracefully
    """
    try:
        if not registration:
            return None
        
        base_path = base_path or current_app.root_path
        return resolve_transcript_asset(registration, base_path=base_path)
    except Exception as e:
        current_app.logger.warning(f"Failed to resolve transcript: {e}")
        return None


@api_v2.route('/registrations', methods=['GET'])
@jwt_required_secure()
@admin_required
def get_registrations_api():
    """
    Get all registration requests (admin only)
    
    Single Responsibility: Only retrieves registration data
    Authorization: Admin access required
    """
    try:
        # Use controller for business logic (loose coupling)
        registration_data = get_all_registration_requests()
        
        # Format data for consistent API response
        formatted_data = _format_registration_data(registration_data)
        
        # Calculate totals for summary
        total_registrations = (
            len(formatted_data['pending']) + 
            len(formatted_data['approved']) + 
            len(formatted_data['rejected'])
        )
        
        return api_success(
            data={
                'registrations': formatted_data,
                'summary': {
                    'total_registrations': total_registrations,
                    'pending_count': len(formatted_data['pending']),
                    'approved_count': len(formatted_data['approved']),
                    'rejected_count': len(formatted_data['rejected'])
                }
            },
            message="Registration requests retrieved successfully"
        )
        
    except Exception as e:
        return api_error(
            f"{FAILED_TO_RETRIEVE_MSG}: {str(e)}", 
            status_code=500
        )


@api_v2.route('/registrations/<int:registration_id>/approve', methods=['POST'])
@jwt_required_secure()
@admin_required
def approve_registration_api(registration_id):
    """
    Approve a registration request (admin only)
    
    Single Responsibility: Only handles registration approval
    Audit Trail: Records admin who approved
    """
    try:
        # Validate registration_id (fail fast)
        if not _validate_registration_id(registration_id):
            return api_error(INVALID_REGISTRATION_ID_MSG, status_code=400)
        
        # Get admin username for audit trail
        admin_username = current_user.username if current_user else get_jwt_identity()
        
        # Use controller for business logic (loose coupling)
        success, message = approve_registration(registration_id, admin_username)
        
        if success:
            return api_success(
                data={
                    'registration_id': registration_id,
                    'approved_by': admin_username
                },
                message=message
            )
        else:
            return api_error(message, status_code=400)
            
    except Exception as e:
        return api_error(
            f"{FAILED_TO_APPROVE_MSG}: {str(e)}", 
            status_code=500
        )


@api_v2.route('/registrations/<int:registration_id>/reject', methods=['POST'])
@jwt_required_secure()
@admin_required
def reject_registration_api(registration_id):
    """
    Reject a registration request (admin only)
    
    Single Responsibility: Only handles registration rejection
    Optional Reason: Allows providing rejection reason
    """
    try:
        # Validate registration_id (fail fast)
        if not _validate_registration_id(registration_id):
            return api_error(INVALID_REGISTRATION_ID_MSG, status_code=400)
        
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
        success, message = reject_registration(registration_id, admin_username)
        
        if success:
            response_data = {
                'registration_id': registration_id,
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


@api_v2.route('/registrations/<int:registration_id>', methods=['GET'])
@jwt_required_secure()
@admin_required
def get_registration_details_api(registration_id):
    """
    Get details of a specific registration request (admin only)
    
    Single Responsibility: Only retrieves single registration details
    URL Parameters: Clean RESTful interface
    """
    try:
        # Validate registration_id (fail fast)
        if not _validate_registration_id(registration_id):
            return api_error(INVALID_REGISTRATION_ID_MSG, status_code=400)
        
        # Use controller to get specific registration
        registration = get_registration_request(registration_id)
        
        if not registration:
            return api_error(REGISTRATION_NOT_FOUND_MSG, status_code=404)
        
        # Convert to dict if needed (defensive programming)
        if hasattr(registration, '__dict__'):
            registration_data = {
                'id': getattr(registration, 'id', registration_id),
                'username': getattr(registration, 'username', None),
                'email': getattr(registration, 'email', None),
                'status': getattr(registration, 'status', None),
                'created_at': getattr(registration, 'created_at', None),
                'transcript_url': getattr(registration, 'transcript_url', None)
            }
        else:
            registration_data = registration
        
        # Check if transcript is available
        transcript_asset = _safe_resolve_transcript(registration)
        if transcript_asset:
            registration_data['transcript_available'] = True
            registration_data['transcript_type'] = transcript_asset.get('mode', 'unknown')
        else:
            registration_data['transcript_available'] = False
        
        return api_success(
            data={'registration': registration_data},
            message=f"Registration {registration_id} retrieved successfully"
        )
        
    except Exception as e:
        return api_error(
            f"Failed to retrieve registration details: {str(e)}", 
            status_code=500
        )


@api_v2.route('/registrations/<int:registration_id>/transcript', methods=['GET'])
@jwt_required_secure()
@admin_required
def get_transcript_info_api(registration_id):
    """
    Get transcript information for a registration (admin only)
    
    Single Responsibility: Only handles transcript metadata
    Security: Returns info without exposing file paths
    """
    try:
        # Validate registration_id (fail fast)
        if not _validate_registration_id(registration_id):
            return api_error(INVALID_REGISTRATION_ID_MSG, status_code=400)
        
        # Get registration using controller
        registration = get_registration_request(registration_id)
        if not registration:
            return api_error(REGISTRATION_NOT_FOUND_MSG, status_code=404)
        
        # Resolve transcript asset safely
        transcript_asset = _safe_resolve_transcript(registration)
        if not transcript_asset:
            return api_error(TRANSCRIPT_NOT_FOUND_MSG, status_code=404)
        
        # Return safe metadata (don't expose file paths)
        transcript_info = {
            'available': True,
            'filename': transcript_asset.get('filename'),
            'mode': transcript_asset.get('mode'),  # 'local' or 'remote'
            'size': transcript_asset.get('size'),
            'download_url': f"/api/v2/registrations/{registration_id}/transcript/download"
        }
        
        # Add MIME type if available
        if transcript_asset.get('filename'):
            mimetype, _ = mimetypes.guess_type(transcript_asset['filename'])
            if mimetype:
                transcript_info['mime_type'] = mimetype
        
        return api_success(
            data={'transcript': transcript_info},
            message="Transcript information retrieved successfully"
        )
        
    except Exception as e:
        return api_error(
            f"Failed to get transcript info: {str(e)}", 
            status_code=500
        )


@api_v2.route('/registrations/<int:registration_id>/transcript/download', methods=['GET'])
@jwt_required_secure()
@admin_required
def download_transcript_api(registration_id):
    """
    Download transcript file for a registration (admin only)
    
    Single Responsibility: Only handles transcript file delivery
    Security: Validates access and handles both local/remote files
    """
    try:
        # Validate registration_id (fail fast)
        if not _validate_registration_id(registration_id):
            return api_error(INVALID_REGISTRATION_ID_MSG, status_code=400)
        
        # Get registration using controller
        registration = get_registration_request(registration_id)
        if not registration:
            return api_error(REGISTRATION_NOT_FOUND_MSG, status_code=404)
        
        # Resolve transcript asset safely
        transcript_asset = _safe_resolve_transcript(registration)
        if not transcript_asset:
            return api_error(TRANSCRIPT_NOT_FOUND_MSG, status_code=404)
        
        # Handle remote files (redirect)
        if transcript_asset.get('mode') == 'remote':
            remote_url = transcript_asset.get('url')
            if remote_url:
                return redirect(remote_url)
            else:
                return api_error("Remote transcript URL not available", status_code=404)
        
        # Handle local files
        if transcript_asset.get('mode') == 'local':
            from flask import send_file
            
            file_path = transcript_asset.get('absolute_path')
            filename = transcript_asset.get('filename', 'transcript')
            
            if not file_path:
                return api_error("Local transcript path not available", status_code=404)
            
            # Determine MIME type
            mimetype, _ = mimetypes.guess_type(filename)
            
            try:
                response = send_file(
                    file_path,
                    mimetype=mimetype or 'application/pdf',
                    as_attachment=False,
                    conditional=True
                )
                response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
                return response
            except FileNotFoundError:
                return api_error("Transcript file not found on server", status_code=404)
        
        return api_error("Unknown transcript storage mode", status_code=500)
        
    except Exception as e:
        current_app.logger.exception(f"Error downloading transcript: {e}")
        return api_error(
            f"{FAILED_TO_DOWNLOAD_MSG}: {str(e)}", 
            status_code=500
        )


@api_v2.route('/registrations/pending', methods=['GET'])
@jwt_required_secure()
@admin_required
def get_pending_registrations_api():
    """
    Get only pending registration requests (admin only)
    
    Single Responsibility: Only retrieves pending registrations
    Convenience: Filtered view for common admin task
    """
    try:
        # Use controller for business logic
        registration_data = get_all_registration_requests()
        formatted_data = _format_registration_data(registration_data)
        
        pending_registrations = formatted_data.get('pending', [])
        
        return api_success(
            data={
                'pending_registrations': pending_registrations,
                'count': len(pending_registrations)
            },
            message=f"Found {len(pending_registrations)} pending registration requests"
        )
        
    except Exception as e:
        return api_error(
            f"{FAILED_TO_RETRIEVE_MSG} pending registrations: {str(e)}", 
            status_code=500
        )