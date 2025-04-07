from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for, Response
from flask_jwt_extended import jwt_required, current_user
from datetime import datetime, timedelta
from App.controllers.tracking import (
    get_all_assistant_stats,
    get_shift_attendance_records,
    get_student_stats,
    clock_in,
    clock_out,
    mark_missed_shift,
    generate_attendance_report
)
from App.middleware import admin_required
from App.models import TimeEntry, Student, HelpDeskAssistant
import json

tracking_views = Blueprint('tracking_views', __name__, template_folder='../templates')

@tracking_views.route('/timeTracking')
@jwt_required()
@admin_required
def time_tracking():
    # Get actual staff data from the database
    staff_data = get_all_assistant_stats()
    
    # If no staff data is returned, handle the empty case
    if not staff_data:
        staff_data = []
    
    # Mark the first student as selected for initial display
    if staff_data:
        staff_data[0]['selected'] = True
    
    # Get current date for display
    now = datetime.utcnow()
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
        now = datetime.utcnow()
        
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
                    'Content-Disposition': f'attachment;filename=attendance_report_{datetime.utcnow().strftime("%Y%m%d")}.json'
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
    """Display raw time entries for debugging"""
    entries = TimeEntry.query.all()
    
    # Format entries for display
    formatted_entries = []
    for entry in entries:
        # Get student name
        student = Student.query.get(entry.username)
        student_name = student.get_name() if student else entry.username
        
        formatted_entries.append({
            'id': entry.id,
            'username': entry.username,
            'name': student_name,
            'shift_id': entry.shift_id,
            'clock_in': entry.clock_in.strftime('%Y-%m-%d %H:%M:%S') if entry.clock_in else None,
            'clock_out': entry.clock_out.strftime('%Y-%m-%d %H:%M:%S') if entry.clock_out else None,
            'status': entry.status,
            'hours': entry.get_hours_worked() if entry.status == 'completed' else 'N/A'
        })
    
    # Simple HTML to display entries
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Raw Time Entries</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            h1 { color: #333; }
        </style>
    </head>
    <body>
        <h1>Raw Time Entries</h1>
        <p>Total entries: %d</p>
        <table>
            <tr>
                <th>ID</th>
                <th>Username</th>
                <th>Name</th>
                <th>Shift ID</th>
                <th>Clock In</th>
                <th>Clock Out</th>
                <th>Status</th>
                <th>Hours</th>
            </tr>
            %s
        </table>
    </body>
    </html>
    """ % (
        len(formatted_entries),
        "\n".join([
            f"<tr><td>{e['id']}</td><td>{e['username']}</td><td>{e['name']}</td><td>{e['shift_id']}</td><td>{e['clock_in']}</td><td>{e['clock_out']}</td><td>{e['status']}</td><td>{e['hours']}</td></tr>"
            for e in formatted_entries
        ])
    )
    
    return html