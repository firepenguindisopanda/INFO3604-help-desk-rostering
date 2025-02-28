from flask import Blueprint, render_template, jsonify, request
from flask_jwt_extended import jwt_required
from App.controllers.schedule import help_desk_scheduler

schedule_views = Blueprint('schedule_views', __name__, template_folder='../templates')

@schedule_views.route('/schedule')
@jwt_required()
def schedule():
    return render_template('admin/schedule/view.html')

@schedule_views.route('/api/generate_schedule', methods=['GET'])
@jwt_required()
def generate_schedule():
    try:
        # Call the help desk scheduler with default parameters
        # I = 10 staff members
        # J = 45 shifts (9 hours x 5 days)
        # K = 1 course (simplified)
        I, J, K = 10, 45, 1
        result = help_desk_scheduler(I, J, K)
        
        return jsonify(result)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error generating schedule: {error_details}")
        return jsonify({
            'status': 'error',
            'message': f"Failed to generate schedule: {str(e)}"
        }), 500

@schedule_views.route('/api/schedule/details', methods=['GET'])
@jwt_required()
def get_schedule_details():
    """Get a more detailed view of the schedule for the admin page"""
    try:
        # Call the help desk scheduler
        I, J, K = 10, 45, 1
        result = help_desk_scheduler(I, J, K)
        
        if result['status'] != 'success':
            return jsonify(result), 400
            
        # Format the data for the UI
        assignments = result['assignments']
        staff_index = result['staff_index']
        
        # Define days and shift times for hourly slots
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        shift_times = ["9:00 am", "10:00 am", "11:00 am", "12:00 pm", 
                      "1:00 pm", "2:00 pm", "3:00 pm", "4:00 pm", "5:00 pm"]
        
        # Create a formatted schedule
        formatted_schedule = []
        for day_idx, day in enumerate(days):
            day_shifts = []
            for time_idx, time in enumerate(shift_times):
                shift_id = day_idx * len(shift_times) + time_idx
                staff_list = assignments.get(shift_id, [])
                day_shifts.append({
                    'time': time,
                    'staff': staff_list
                })
            formatted_schedule.append({
                'day': day,
                'shifts': day_shifts
            })
            
        return jsonify({
            'status': 'success',
            'schedule': formatted_schedule,
            'staff_index': staff_index
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500