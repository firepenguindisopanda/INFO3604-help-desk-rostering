from flask import Blueprint, render_template, jsonify, request
from flask_jwt_extended import jwt_required
import datetime
from datetime import timedelta

tracking_views = Blueprint('tracking_views', __name__, template_folder='../templates')

@tracking_views.route('/timeTracking')
@jwt_required()
def time_tracking():
    # Mock staff data for the attendance cards
    staff_data = [
        {
            "id": "816039080",
            "name": "Taylor Swift",
            "image": "/api/placeholder/60/60",
            "semester_attendance": "90%",
            "week_attendance": "92%"
        },
        {
            "id": "816031872",
            "name": "Liam Johnson",
            "image": "/api/placeholder/60/60",
            "semester_attendance": "85%",
            "week_attendance": "87%"
        },
        {
            "id": "816023111",
            "name": "Lisa Jerado",
            "image": "/api/placeholder/60/60",
            "semester_attendance": "84%",
            "week_attendance": "85%",
            "selected": True
        },
        {
            "id": "816042305",
            "name": "Lewis Winter",
            "image": "/api/placeholder/60/60",
            "semester_attendance": "74%",
            "week_attendance": "78%"
        },
        {
            "id": "816057482",
            "name": "Andy Callan",
            "image": "/api/placeholder/60/60",
            "semester_attendance": "80%",
            "week_attendance": "85%"
        },
        {
            "id": "816063921",
            "name": "Quincie Woody",
            "image": "/api/placeholder/60/60",
            "semester_attendance": "80%",
            "week_attendance": "82%"
        }
    ]
    
    # Mock attendance records for the attendance list
    # In a real application, you would fetch this data from a database
    # based on the currently selected staff member, week, and month
    attendance_records = [
        {
            "staff_id": "816023111",
            "staff_name": "Lisa Jerado",
            "image": "/api/placeholder/30/30",
            "date": "11-23-24",
            "day": "Thursday",
            "login_time": "09:30AM",
            "logout_time": "ON DUTY"
        },
        {
            "staff_id": "816019333",
            "staff_name": "Jon Kook",
            "image": "/api/placeholder/30/30",
            "date": "11-23-24",
            "day": "Thursday",
            "login_time": "09:00AM",
            "logout_time": "10:30AM"
        },
        {
            "staff_id": "816039080",
            "staff_name": "Taylor Swift",
            "image": "/api/placeholder/30/30",
            "date": "11-23-24",
            "day": "Thursday",
            "login_time": "ABSENT",
            "logout_time": "ABSENT"
        }
    ]
    
    # Current month and week information
    current_month = "Nov"
    current_week = "5"
    
    return render_template('admin/tracking/index.html',
                          staff_data=staff_data,
                          attendance_records=attendance_records,
                          current_month=current_month,
                          current_week=current_week)

@tracking_views.route('/api/staff/<staff_id>/attendance', methods=['GET'])
@jwt_required()
def get_staff_attendance(staff_id):
    """
    API endpoint to get attendance records for a specific staff member
    In a real application, this would query a database
    """
    # Mock data for demo purposes
    # For a real application, fetch from database based on staff_id
    
    # Get week and month from query parameters, or use defaults
    week = request.args.get('week', '5')
    month = request.args.get('month', 'Nov')
    
    # Generate some mock attendance records based on staff_id
    attendance_records = []
    
    # Today's date for reference
    today = datetime.datetime.now()
    
    # Generate some past dates for the records
    for i in range(5):
        record_date = today - timedelta(days=i)
        
        # Skip weekends
        if record_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
            continue
        
        record = {
            "staff_id": staff_id,
            "staff_name": get_staff_name(staff_id),
            "image": "/api/placeholder/30/30",
            "date": record_date.strftime("%m-%d-%y"),
            "day": record_date.strftime("%A"),
        }
        
        # Randomize login/logout times for demo
        # In reality, these would come from your database
        if i == 0:
            record["login_time"] = "09:30AM"
            record["logout_time"] = "ON DUTY"
        elif i == 4:
            record["login_time"] = "ABSENT"
            record["logout_time"] = "ABSENT"
        else:
            record["login_time"] = f"0{9 + (i % 2)}:00AM"
            record["logout_time"] = f"{10 + (i % 3)}:{(30 * i) % 60:02d}AM"
        
        attendance_records.append(record)
    
    return jsonify({
        "staff_id": staff_id,
        "staff_name": get_staff_name(staff_id),
        "week": week,
        "month": month,
        "attendance_records": attendance_records
    })

def get_staff_name(staff_id):
    """Helper function to get a staff name from ID"""
    # In a real application, this would query your database
    staff_map = {
        "816039080": "Taylor Swift",
        "816031872": "Liam Johnson",
        "816023111": "Lisa Jerado",
        "816042305": "Lewis Winter",
        "816057482": "Andy Callan",
        "816063921": "Quincie Woody",
        "816019333": "Jon Kook"
    }
    return staff_map.get(staff_id, "Unknown Staff")