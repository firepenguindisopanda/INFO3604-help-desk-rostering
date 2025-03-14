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
from App.models import TimeEntry, Student
import json

tracking_views = Blueprint('tracking_views', __name__, template_folder='../templates')

@tracking_views.route('/timeTracking')
@jwt_required()
@admin_required
def time_tracking():
    # Hard-coded staff data for the default student
    staff_data = [{
        'id': '8',
        'name': 'Default Student',
        'image': '/static/images/DefaultAvatar.jpg',
        'semester_attendance': "10.5",
        'week_attendance': "5.5",
        'selected': True
    }]
    
    # Get current date for display
    now = datetime.utcnow()
    current_week = now.isocalendar()[1]
    current_month = now.strftime('%b')
    
    # Get all time entries directly
    entries = TimeEntry.query.all()
    print(f"Found {len(entries)} time entries")
    
    # Format as attendance records
    attendance_records = []
    for entry in entries:
        try:
            record = {
                'staff_id': entry.username,
                'staff_name': 'Default Student',  # Hard-coded for simplicity
                'image': '/static/images/DefaultAvatar.jpg',
                'date': entry.clock_in.strftime('%m-%d-%y') if entry.clock_in else 'Unknown',
                'day': entry.clock_in.strftime('%A') if entry.clock_in else 'Unknown',
                'login_time': entry.clock_in.strftime('%I:%M%p') if entry.clock_in else 'ABSENT',
                'logout_time': entry.clock_out.strftime('%I:%M%p') if entry.clock_out else 
                              ('ON DUTY' if entry.status == 'active' else 'ABSENT')
            }
            attendance_records.append(record)
        except Exception as e:
            print(f"Error formatting time entry {entry.id}: {e}")
    
    print(f"Prepared {len(attendance_records)} attendance records for display")
    
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
    # Get week and month from query parameters, or use defaults
    week = request.args.get('week', datetime.utcnow().isocalendar()[1])
    month = request.args.get('month', datetime.utcnow().strftime('%b'))
    
    # Calculate date range based on week number
    now = datetime.utcnow()
    start_of_year = datetime(now.year, 1, 1)
    week_number = int(week)
    
    # Adjust for week numbering starting at 1
    week_start = start_of_year + timedelta(days=(week_number-1)*7)
    
    # Adjust to Monday of that week
    week_start = week_start - timedelta(days=week_start.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Get attendance records
    attendance_records = get_shift_attendance_records(
        date_range=(week_start, week_end)
    )
    
    # Filter for just this staff member
    staff_records = [r for r in attendance_records if r['staff_id'] == staff_id]
    
    return jsonify({
        "staff_id": staff_id,
        "week": week,
        "month": month,
        "attendance_records": staff_records
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
        formatted_entries.append({
            'id': entry.id,
            'username': entry.username,
            'shift_id': entry.shift_id,
            'clock_in': entry.clock_in.strftime('%Y-%m-%d %H:%M:%S') if entry.clock_in else None,
            'clock_out': entry.clock_out.strftime('%Y-%m-%d %H:%M:%S') if entry.clock_out else None,
            'status': entry.status
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
                <th>Shift ID</th>
                <th>Clock In</th>
                <th>Clock Out</th>
                <th>Status</th>
            </tr>
            %s
        </table>
    </body>
    </html>
    """ % (
        len(formatted_entries),
        "\n".join([
            f"<tr><td>{e['id']}</td><td>{e['username']}</td><td>{e['shift_id']}</td><td>{e['clock_in']}</td><td>{e['clock_out']}</td><td>{e['status']}</td></tr>"
            for e in formatted_entries
        ])
    )
    
    return html