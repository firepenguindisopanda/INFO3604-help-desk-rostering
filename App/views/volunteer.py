from flask import Blueprint, render_template, jsonify
from flask_jwt_extended import jwt_required, current_user
from App.middleware import volunteer_required
import datetime

volunteer_views = Blueprint('volunteer_views', __name__, template_folder='../templates')

@volunteer_views.route('/volunteer/dashboard')
@jwt_required()
@volunteer_required
def dashboard():
    # Get current date for next shift calculation
    now = datetime.datetime.now()
    current_date = now.strftime("%d %B, %Y")
    
    # Mock data - in a real implementation, this would come from a database
    my_shifts = [
        {"date": "30 Sept", "time": "3:00 pm to 4:00 pm"},
        {"date": "01 Oct", "time": "10:00 am to 12:00 pm"},
        {"date": "02 Oct", "time": "1:00 pm to 2:00 pm"},
        {"date": "03 Oct", "time": "11:00 am to 12:00 pm"},
        {"date": "04 Oct", "time": "9:00 am to 11:00 am"}
    ]
    
    # Get next shift (first one in our list for this example)
    next_shift = {
        "date": "30 September, 2024",
        "time": "03:00 pm to 04:00 pm",
        "starts_now": True  # This would be calculated based on current time
    }
    
    # In a real application, this data would be pulled from your database
    # or calculated by your scheduling algorithm
    days_of_week = ['MON', 'TUE', 'WED', 'THUR', 'FRI']
    time_slots = ['9:00 am', '10:00 am', '11:00 am']
    
    # Sample staff assignments - in reality this would come from your database
    staff_schedule = {
        '9:00 am': {
            'MON': ['Liam Johnson', 'Joshua Anderson', 'Daniel Martinez'],
            'TUE': ['Liam Johnson', 'Joshua Anderson'],
            'WED': ['Liam Johnson', 'Joshua Anderson'],
            'THUR': ['Liam Johnson', 'Joshua Anderson', 'Daniel Martinez'],
            'FRI': ['Liam Johnson', 'Joshua Anderson', 'Daniel Martinez']
        },
        '10:00 am': {
            'MON': ['Liam Johnson', 'Joshua Anderson'],
            'TUE': ['Liam Johnson', 'Joshua Anderson', 'Daniel Martinez'],
            'WED': ['Liam Johnson', 'Joshua Anderson', 'Daniel Martinez'],
            'THUR': ['Liam Johnson', 'Joshua Anderson'],
            'FRI': ['Liam Johnson', 'Joshua Anderson']
        },
        '11:00 am': {
            'MON': ['Joshua Anderson', 'Liam Johnson', 'Ethan Roberts'],
            'TUE': ['Joshua Anderson', 'Liam Johnson'],
            'WED': ['Joshua Anderson', 'Liam Johnson'],
            'THUR': ['Joshua Anderson', 'Liam Johnson', 'Ethan Roberts'],
            'FRI': ['Joshua Anderson', 'Liam Johnson', 'Ethan Roberts']
        }
    }
    
    return render_template('volunteer/dashboard.html', 
                          my_shifts=my_shifts,
                          next_shift=next_shift, 
                          days_of_week=days_of_week,
                          time_slots=time_slots,
                          staff_schedule=staff_schedule,
                          current_user=current_user)