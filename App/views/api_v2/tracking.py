"""
API v2 Time Tracking and Attendance Management Endpoints

This module handles time tracking and attendance with design principles:
- Single Responsibility: Each function has one clear job
- Encapsulation: Uses controllers, hides complexity
- Fail Fast: Validates inputs immediately
- Defensive Programming: Handles edge cases gracefully
"""

from datetime import datetime, timedelta
from flask import request, Response, current_app
from flask_jwt_extended import get_jwt_identity
import json

from App.views.api_v2 import api_v2
from App.views.api_v2.utils import (
    api_success, 
    api_error, 
    jwt_required_secure,
    validate_json_request_secure
)
from App.middleware import admin_required

# Import controllers (dependency injection pattern)
from App.controllers.tracking import (
    get_shift_attendance_records,
    mark_missed_shift,
    generate_attendance_report
)
from App.utils.time_utils import trinidad_now

# Constants (DRY principle)
INVALID_STAFF_ID_MSG = "Invalid staff ID"
INVALID_SHIFT_ID_MSG = "Invalid shift ID"
INVALID_DATE_FORMAT_MSG = "Invalid date format. Use YYYY-MM-DD"
FAILED_TO_RETRIEVE_MSG = "Failed to retrieve attendance"
FAILED_TO_MARK_MISSED_MSG = "Failed to mark missed shift"
FAILED_TO_GENERATE_REPORT_MSG = "Failed to generate attendance report"


def _validate_staff_id(staff_id):
    """
    Validate staff ID parameter
    
    Single Responsibility: Only validates staff ID
    Reusability: Can be used by multiple endpoints
    """
    if not staff_id or not isinstance(staff_id, str) or not staff_id.strip():
        return False
    return True


def _parse_date_safely(date_str, field_name):
    """
    Parse date string safely with proper error handling
    
    Single Responsibility: Only handles date parsing
    Fail Fast: Returns None if invalid
    """
    if not date_str:
        return None
    
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        current_app.logger.warning(f"Invalid {field_name} format: {date_str}")
        return None


def _calculate_default_date_range():
    """
    Calculate default date range for attendance queries
    
    Single Responsibility: Only calculates date range
    Business Logic: Default to last 14 days
    """
    now = trinidad_now()
    start_date = now - timedelta(days=14)
    return start_date, now


@api_v2.route('/staff/<staff_id>/attendance', methods=['GET'])
@jwt_required_secure()
@admin_required
def get_staff_attendance_api(staff_id):
    """
    Get attendance records for a specific staff member
    
    Single Responsibility: Only retrieves attendance data
    Validation: Validates staff_id and date parameters
    """
    try:
        # Validate staff_id (fail fast)
        if not _validate_staff_id(staff_id):
            return api_error(INVALID_STAFF_ID_MSG, status_code=400)
        
        # Get query parameters with safe defaults
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # Parse dates or use defaults (defensive programming)
        if start_date_str or end_date_str:
            start_date = _parse_date_safely(start_date_str, "start_date")
            end_date = _parse_date_safely(end_date_str, "end_date")
            
            if start_date_str and not start_date:
                return api_error(INVALID_DATE_FORMAT_MSG, status_code=400)
            if end_date_str and not end_date:
                return api_error(INVALID_DATE_FORMAT_MSG, status_code=400)
        else:
            start_date, end_date = _calculate_default_date_range()
        
        # Use controller for business logic (loose coupling)
        attendance_records = get_shift_attendance_records(
            date_range=(start_date, end_date)
        )
        
        # Filter for specific staff member
        staff_records = [
            record for record in attendance_records 
            if record.get('staff_id') == staff_id
        ]
        
        return api_success(
            data={
                'staff_id': staff_id,
                'attendance_records': staff_records,
                'date_range': {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d')
                }
            },
            message="Staff attendance retrieved successfully"
        )
        
    except Exception as e:
        current_app.logger.exception(f"Error fetching staff attendance: {e}")
        return api_error(
            f"{FAILED_TO_RETRIEVE_MSG}: {str(e)}", 
            status_code=500
        )


@api_v2.route('/staff/<staff_id>/mark-missed', methods=['POST'])
@jwt_required_secure()
@admin_required
def mark_staff_missed_api(staff_id):
    """
    Mark a shift as missed for a staff member
    
    Single Responsibility: Only handles marking missed shifts
    Authorization: Admin only operation
    """
    try:
        # Validate staff_id (fail fast)
        if not _validate_staff_id(staff_id):
            return api_error(INVALID_STAFF_ID_MSG, status_code=400)
        
        # Validate JSON request
        data, error = validate_json_request_secure(['shift_id'])
        if error:
            return error
        
        shift_id = data.get('shift_id')
        
        # Additional validation (defensive programming)
        if not isinstance(shift_id, int) or shift_id <= 0:
            return api_error(INVALID_SHIFT_ID_MSG, status_code=400)
        
        # Use controller for business logic (loose coupling)
        result = mark_missed_shift(staff_id, shift_id)
        
        # Handle controller response format
        if isinstance(result, dict):
            if result.get('success'):
                return api_success(
                    data={
                        'staff_id': staff_id,
                        'shift_id': shift_id
                    },
                    message=result.get('message', 'Shift marked as missed successfully')
                )
            else:
                return api_error(
                    result.get('message', 'Failed to mark shift as missed'), 
                    status_code=400
                )
        else:
            # Legacy format handling
            return api_success(
                data={
                    'staff_id': staff_id,
                    'shift_id': shift_id
                },
                message="Shift marked as missed successfully"
            )
        
    except Exception as e:
        current_app.logger.exception(f"Error marking missed shift: {e}")
        return api_error(
            f"{FAILED_TO_MARK_MISSED_MSG}: {str(e)}", 
            status_code=500
        )


@api_v2.route('/staff/attendance/report', methods=['POST'])
@jwt_required_secure()
@admin_required
def generate_attendance_report_api():
    """
    Generate attendance report for staff
    
    Single Responsibility: Only generates attendance reports
    Extensibility: Supports different output formats
    """
    try:
        # Validate JSON request
        data, error = validate_json_request_secure()
        if error:
            return error
        
        # Extract parameters with safe defaults
        staff_id = data.get('staff_id')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        download = data.get('download', False)
        
        # Validate staff_id if provided
        if staff_id and not _validate_staff_id(staff_id):
            return api_error(INVALID_STAFF_ID_MSG, status_code=400)
        
        # Parse dates (defensive programming)
        start_date = _parse_date_safely(start_date_str, "start_date") if start_date_str else None
        end_date = _parse_date_safely(end_date_str, "end_date") if end_date_str else None
        
        if start_date_str and not start_date:
            return api_error(INVALID_DATE_FORMAT_MSG, status_code=400)
        if end_date_str and not end_date:
            return api_error(INVALID_DATE_FORMAT_MSG, status_code=400)
        
        # Use controller for business logic (loose coupling)
        report = generate_attendance_report(staff_id, start_date, end_date)
        
        # Handle download request (strategy pattern for different outputs)
        if download:
            # Return as downloadable JSON file
            filename = f"attendance_report_{trinidad_now().strftime('%Y%m%d')}.json"
            response = Response(
                json.dumps(report, indent=2),
                mimetype='application/json',
                headers={
                    'Content-Disposition': f'attachment;filename={filename}'
                }
            )
            return response
        else:
            # Return as API response
            return api_success(
                data={'report': report},
                message="Attendance report generated successfully"
            )
        
    except Exception as e:
        current_app.logger.exception(f"Error generating attendance report: {e}")
        return api_error(
            f"{FAILED_TO_GENERATE_REPORT_MSG}: {str(e)}", 
            status_code=500
        )


@api_v2.route('/staff/attendance/summary', methods=['GET'])
@jwt_required_secure()
@admin_required
def get_attendance_summary_api():
    """
    Get attendance summary statistics
    
    Single Responsibility: Only provides summary statistics
    Read-only Operation: Safe to call multiple times
    """
    try:
        # Get query parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # Parse dates or use defaults
        if start_date_str or end_date_str:
            start_date = _parse_date_safely(start_date_str, "start_date")
            end_date = _parse_date_safely(end_date_str, "end_date")
            
            if start_date_str and not start_date:
                return api_error(INVALID_DATE_FORMAT_MSG, status_code=400)
            if end_date_str and not end_date:
                return api_error(INVALID_DATE_FORMAT_MSG, status_code=400)
        else:
            start_date, end_date = _calculate_default_date_range()
        
        # Get attendance records using controller
        attendance_records = get_shift_attendance_records(
            date_range=(start_date, end_date)
        )
        
        # Calculate summary statistics (business logic)
        total_shifts = len(attendance_records)
        completed_shifts = len([r for r in attendance_records if r.get('status') == 'completed'])
        missed_shifts = len([r for r in attendance_records if r.get('status') == 'missed'])
        
        # Get unique staff count
        unique_staff = len({r.get('staff_id') for r in attendance_records if r.get('staff_id')})
        
        summary = {
            'total_shifts': total_shifts,
            'completed_shifts': completed_shifts,
            'missed_shifts': missed_shifts,
            'completion_rate': round((completed_shifts / total_shifts * 100) if total_shifts > 0 else 0, 2),
            'unique_staff_count': unique_staff,
            'date_range': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            }
        }
        
        return api_success(
            data={'summary': summary},
            message="Attendance summary retrieved successfully"
        )
        
    except Exception as e:
        current_app.logger.exception(f"Error getting attendance summary: {e}")
        return api_error(
            f"{FAILED_TO_RETRIEVE_MSG} summary: {str(e)}", 
            status_code=500
        )