from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for, Response
from flask_jwt_extended import jwt_required, current_user
from datetime import datetime, timedelta
from App.controllers.tracking import (
    get_help_desk_assistant_stats,
    get_lab_assistant_stats,
    get_shift_attendance_records,
    get_student_stats,
    clock_in,
    clock_out,
    mark_missed_shift,
    generate_attendance_report,
    get_student_time_entries
)
from App.controllers.student import get_student
from App.middleware import admin_required
import json
from App.utils.time_utils import trinidad_now, convert_to_trinidad_time
from App.utils.profile_images import resolve_profile_image

tracking_views = Blueprint('tracking_views', __name__, template_folder='../templates')

@tracking_views.route('/timeTracking')
@jwt_required()
@admin_required
def time_tracking():

    # Get the current user from JWT
    user = current_user
    
    # Filter staff data based on admin role
    if user.role == 'helpdesk':
        staff_data = get_help_desk_assistant_stats()
    elif user.role == 'lab':
        staff_data = get_lab_assistant_stats()
    else:
        staff_data = []
    
    # If no staff data is returned, handle the empty case
    if not staff_data:
        staff_data = []
    
    # Add profile pictures to staff data using controller
    for staff in staff_data:
        # Get the student record using controller to access profile_data
        student = get_student(staff['id'])
        profile_data = {}
        if student and hasattr(student, 'profile_data') and student.profile_data:
            try:
                profile_data = json.loads(student.profile_data)
            except Exception:
                profile_data = {}

        legacy_filename = profile_data.get('image_filename') if isinstance(profile_data, dict) else None
        profile_image_url = resolve_profile_image(getattr(student, 'profile_data', None))
        if legacy_filename and '://' not in str(legacy_filename):
            import os
            filepath = os.path.join('App', 'static', str(legacy_filename).lstrip('/'))
            if os.path.exists(filepath):
                from flask import url_for
                profile_image_url = url_for('static', filename=str(legacy_filename))

        staff['image_url'] = profile_image_url
        staff['profile_image_url'] = profile_image_url
    
    # Mark the first student as selected for initial display
    if staff_data:
        staff_data[0]['selected'] = True
    
    # Get current date for display
    now = trinidad_now()
    current_week = now.isocalendar()[1]
    current_month = now.strftime('%b')
    
    # Determine which assistant's attendance records to show
    selected_username = staff_data[0]['id'] if staff_data else None
    
    # Get attendance records for the selected assistant
    if selected_username:
        # Calculate date range for current week
        week_start = now - timedelta(days=now.weekday())  # Monday
        week_end = week_start + timedelta(days=6)  # Sunday
        
        attendance_records = get_shift_attendance_records(
            date_range=(week_start, week_end)
        )
        
        # Filter for just this staff member if specified
        if selected_username:
            attendance_records = [r for r in attendance_records if r['staff_id'] == selected_username]
    else:
        # No staff selected, show empty records
        attendance_records = []
    
    print(f"Loaded {len(staff_data)} Student Assistant and {len(attendance_records)} attendance records")
    
    return render_template('admin/tracking/index.html',
                          staff_data=staff_data,
                          attendance_records=attendance_records,
                          current_month=current_month,
                          current_week=str(current_week))

@tracking_views.route('/api/staff/<staff_id>/attendance', methods=['GET'])
@jwt_required()
@admin_required
def get_staff_attendance(staff_id):
    """API endpoint to get attendance records for a specific staff member"""
    # Get most recent attendance records for this staff member
    try:
        # Get current date for calculation
        now = trinidad_now()
        
        # Default to showing the last 14 days of attendance
        start_date = now - timedelta(days=14)
        end_date = now
        
        # Get attendance records
        attendance_records = get_shift_attendance_records(
            date_range=(start_date, end_date)
        )
        
        # Filter for just this staff member
        staff_records = [r for r in attendance_records if r['staff_id'] == staff_id]
        
        return jsonify({
            "staff_id": staff_id,
            "attendance_records": staff_records
        })
    except Exception as e:
        print(f"Error fetching staff attendance: {e}")
        return jsonify({
            "staff_id": staff_id,
            "error": str(e),
            "attendance_records": []
        })

@tracking_views.route('/api/staff/attendance/report', methods=['POST'])
@jwt_required()
@admin_required
def generate_attendance_report_endpoint():
    """Generate an attendance report for staff"""
    try:
        data = request.json
        
        # Get parameters
        staff_id = data.get('staff_id')
        
        # Parse dates
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        start_date = None
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        
        end_date = None
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        # Generate report
        report = generate_attendance_report(staff_id, start_date, end_date)
        
        # Check if download requested
        if data.get('download'):
            # Return as downloadable JSON file
            response = Response(
                json.dumps(report, indent=2),
                mimetype='application/json',
                headers={
                    'Content-Disposition': f'attachment;filename=attendance_report_{trinidad_now().strftime("%Y%m%d")}.json'
                }
            )
            return response
        else:
            return jsonify(report)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error generating report: {str(e)}'
        }), 500

@tracking_views.route('/api/staff/<staff_id>/mark_missed', methods=['POST'])
@jwt_required()
@admin_required
def mark_staff_missed_endpoint(staff_id):
    """Mark a shift as missed for a staff member"""
    try:
        data = request.json
        shift_id = data.get('shift_id')
        
        if not shift_id:
            return jsonify({
                'success': False,
                'message': 'Shift ID is required'
            }), 400
        
        result = mark_missed_shift(staff_id, shift_id)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error marking missed shift: {str(e)}'
        }), 500
        
@tracking_views.route('/raw_time_entries')
@jwt_required()
def raw_time_entries():
    """Display raw time entries for debugging - now uses controller"""
    # This would need a new controller function to replace direct TimeEntry.query.all()
    # For now, return a message that this functionality needs implementation
    return jsonify({
        'message': 'Raw time entries functionality needs to be implemented with proper controller',
        'note': 'This endpoint has been refactored to avoid direct model access'
    })
