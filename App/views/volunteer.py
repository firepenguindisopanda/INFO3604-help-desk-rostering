from flask import Blueprint, render_template, jsonify, request
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
    time_slots = ['9:00 am', '10:00 am', '11:00 am', '12:00 pm', '1:00 pm', '2:00 pm', '3:00 pm', '4:00 pm']
    
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
    
    return render_template('volunteer/dashboard/dashboard.html', 
                          my_shifts=my_shifts,
                          next_shift=next_shift, 
                          days_of_week=days_of_week,
                          time_slots=time_slots,
                          staff_schedule=staff_schedule,
                          current_user=current_user)

@volunteer_views.route('/volunteer/time_tracking')
@jwt_required()
@volunteer_required
def time_tracking():
    # Get current date
    now = datetime.datetime.now()
    today = now.strftime("%d %B, %Y")
    
    # Mock today's shift data
    today_shift = {
        "date": "30 September, 2024",
        "start_time": "03:00 pm",
        "end_time": "04:00 pm",
        "status": "now",  # Can be 'future', 'active', 'now', or 'completed'
        "time_until": "18 hours",
        "time_left": "49 minutes"
    }
    
    # Mock shift history data
    shift_history = [
        {"date": "27 Sept", "time_range": "09:00 am to 11:00 am", "hours": "2 hrs"},
        {"date": "26 Sept", "time_range": "11:00 am to 12:00 pm", "hours": "1 hr"},
        {"date": "25 Sept", "time_range": "01:00 pm to 02:00 pm", "hours": "ABS"},
        {"date": "24 Sept", "time_range": "10:00 am to 12:00 pm", "hours": "2 hrs"},
        {"date": "23 Sept", "time_range": "03:00 pm to 04:00 pm", "hours": "1 hrs"}
    ]
    
    # Mock time distribution data
    time_distribution = [
        {"label": "Mon", "percentage": 80},
        {"label": "Tue", "percentage": 40},
        {"label": "Wed", "percentage": 0},
        {"label": "Thur", "percentage": 30},
        {"label": "Fri", "percentage": 85}
    ]
    
    # Mock hours data
    daily = {
        "date_range": "30 Sept, 3:00 PM - 4:00 PM",
        "hours": "01"
    }
    
    weekly = {
        "date_range": "Week 5, Sept 30 - Oct 4",
        "hours": "00"  # Before clocking in
    }
    
    monthly = {
        "date_range": "September, 2024",
        "hours": "59"
    }
    
    semester = {
        "date_range": "Sept. 24 - Nov. 24",
        "hours": "59"
    }
    
    return render_template('volunteer/time_tracking/index.html',
                          today_shift=today_shift,
                          shift_history=shift_history,
                          time_distribution=time_distribution,
                          daily=daily,
                          weekly=weekly,
                          monthly=monthly,
                          semester=semester)

@volunteer_views.route('/volunteer/time_tracking/clock_in', methods=['POST'])
@jwt_required()
@volunteer_required
def clock_in():
    # In a real application, you would:
    # 1. Record the clock-in time in the database
    # 2. Update the shift status
    
    # For this mock implementation, we'll just return success
    return jsonify({"success": True})

@volunteer_views.route('/volunteer/time_tracking/clock_out', methods=['POST'])
@jwt_required()
@volunteer_required
def clock_out():
    # In a real application, you would:
    # 1. Record the clock-out time in the database
    # 2. Calculate hours worked
    # 3. Update the shift status
    
    # For this mock implementation, we'll just return success
    return jsonify({"success": True})

@volunteer_views.route('/volunteer/requests')
@jwt_required()
@volunteer_required
def requests():
    # Mock data for requests
    pending_requests = [
        {
            "shift_date": "03 Oct",
            "shift_time": "11:00 am to 12:00 pm",
            "submission_date": "October 1st 2024, 3:33 pm",
            "status": "PENDING"
        }
    ]
    
    approved_requests = [
        {
            "shift_date": "24 Sept",
            "shift_time": "10:00 am to 12:00 pm",
            "submission_date": "September 24th 2024, 08:00 am",
            "status": "APPROVED"
        }
    ]
    
    rejected_requests = [
        {
            "shift_date": "11 Sept",
            "shift_time": "01:00 pm to 02:00 pm",
            "submission_date": "September 10th 2024, 08:00 am",
            "status": "REJECTED"
        }
    ]
    
    # Mock data for available shifts
    available_shifts = [
        {"id": 1, "day": "Mon", "date": "30 Sept", "time": "10:00 am to 11:00 am"},
        {"id": 2, "day": "Wed", "date": "02 Oct", "time": "01:00 pm to 02:00 pm"},
        {"id": 3, "day": "Fri", "date": "04 Oct", "time": "11:00 am to 12:00 pm"}
    ]
    
    # Mock data for available replacements
    available_replacements = [
        {"id": 1, "name": "Daniel Martinez"},
        {"id": 2, "name": "Michelle Liu"},
        {"id": 3, "name": "Joshua Anderson"}
    ]
    
    return render_template('volunteer/requests/index.html',
                          pending_requests=pending_requests,
                          approved_requests=approved_requests,
                          rejected_requests=rejected_requests,
                          available_shifts=available_shifts,
                          available_replacements=available_replacements)

@volunteer_views.route('/volunteer/profile')
@jwt_required()
@volunteer_required
def profile():
    # Mock user data
    user_data = {
        "name": "Liam Johnson",
        "id": "816031872",
        "phone": "398-3921",
        "email": "liam.johnson@my.uwi.edu",
        "address": {
            "street": "45 Coconut Drive",
            "city": "San Fernando",
            "country": "Trinidad and Tobago"
        },
        "enrolled_courses": ["COMP 3602", "COMP 3603", "COMP 3605", "COMP 3607", "COMP 3613"],
        "availability": {
            "MON": ["10am - 11am", "1pm - 2pm", "2pm - 3pm", "3pm - 4pm"],
            "TUE": ["10am - 11am", "11am - 12pm", "1pm - 2pm", "2pm - 3pm"],
            "WED": ["10am - 11am", "1pm - 2pm"],
            "THUR": ["9am - 10am", "10am - 11am", "11am - 12pm", "12pm - 1pm"],
            "FRI": ["10am - 11am", "11am - 12pm", "2pm - 3pm", "3pm - 4pm"]
        },
        "stats": {
            "weekly": {
                "date_range": "Week 5, Sept 30 - Oct 4",
                "hours": "00"
            },
            "monthly": {
                "date_range": "September, 2024",
                "hours": "59"
            },
            "semester": {
                "date_range": "Sept. 24 - Nov. 24",
                "hours": "59"
            },
            "absences": "3"
        }
    }
    
    return render_template('volunteer/profile/index.html', user=user_data)

@volunteer_views.route('/volunteer/notifications')
@jwt_required()
@volunteer_required
def notifications():
    # Mock notifications data
    notifications_data = [
        {
            "message": "Your shift change request was approved.",
            "time": "Tuesday at 10:30 AM",
            "type": "approval"
        },
        {
            "message": "You clocked out for your 03:00 pm to 04:00 pm shift.",
            "time": "Monday at 4:00 PM",
            "type": "clock"
        },
        {
            "message": "You clocked in for your 03:00 pm to 04:00 pm shift.",
            "time": "Monday at 3:00 PM",
            "type": "clock"
        },
        {
            "message": "Week 5 Schedule has been published. Check out your shifts for the week.",
            "time": "Saturday, Sept 28 2024 at 10:30 PM",
            "type": "schedule"
        },
        {
            "message": "Your 03:00 pm to 04:00 pm shift starts in 15 minutes.",
            "time": "Monday at 2:45 PM",
            "type": "reminder"
        },
        {
            "message": "Your request was submitted and is pending approval.",
            "time": "Saturday at 1:30 PM",
            "type": "request"
        },
        {
            "message": "You missed your 01:00 pm to 02:00 pm shift.",
            "time": "Wednesday, Sept 25 at 2:05 PM",
            "type": "missed"
        },
        {
            "message": "Your 01:00 pm to 02:00 pm shift starts in 15 minutes.",
            "time": "Wednesday, Sept 25 at 12:45 PM",
            "type": "reminder"
        },
        {
            "message": "Your availability was successfully updated.",
            "time": "Friday, Sept 20 2024 at 10:30 AM",
            "type": "update"
        }
    ]
    
    return render_template('volunteer/notifications/index.html', 
                          notifications=notifications_data)

@volunteer_views.route('/volunteer/submit_request', methods=['POST'])
@jwt_required()
@volunteer_required
def submit_request():
    # In a real application, you would:
    # 1. Get the form data from request.form or request.json
    # 2. Validate the data
    # 3. Save the request to the database
    
    # For this mock implementation, we'll just return success
    return jsonify({"success": True, "message": "Request submitted successfully"})

@volunteer_views.route('/volunteer/update_availability', methods=['POST'])
@jwt_required()
@volunteer_required
def update_availability():
    # In a real application, you would:
    # 1. Get the availability data from request.json
    # 2. Update the user's availability in the database
    
    # For this mock implementation, we'll just return success
    return jsonify({"success": True, "message": "Availability updated successfully"})

# This function allows us to use your friend's scheduler without modifying it
def get_schedule_with_original_scheduler():
    # Import the original scheduler function safely
    from App.controllers.scheduler import help_desk_scheduler
    
    # Call the original scheduler with default parameters
    I, J, K = 10, 45, 1
    result = help_desk_scheduler(I, J, K)
    
    # Process the result if needed without modifying the original function
    # Here we just return it directly
    return result