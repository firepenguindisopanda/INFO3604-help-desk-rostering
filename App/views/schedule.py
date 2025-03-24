# App/views/schedule.py
from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user
from datetime import datetime, timedelta
from App.controllers.schedule import (
    generate_schedule,    # Updated generator that doesn't use weeks
    publish_schedule,
    get_current_schedule  # New function to get current schedule
)
from App.middleware import admin_required

schedule_views = Blueprint('schedule_views', __name__, template_folder='../templates')

@schedule_views.route('/schedule')
@jwt_required()
@admin_required
def schedule():
    return render_template('admin/schedule/view.html')

@schedule_views.route('/api/schedule/details', methods=['GET'])
@jwt_required()
@admin_required
def get_schedule_details():
    """Get detailed schedule data for the admin UI"""
    # Check if we have a specific schedule ID to get details for
    schedule_id = request.args.get('id')
    
    if schedule_id:
        # Get the current schedule
        schedule = get_current_schedule()
        if schedule:
            return jsonify({
                'status': 'success',
                'schedule': schedule,
                'staff_index': {
                    '0': 'Daniel Rasheed',
                    '1': 'Michelle Liu',
                    '2': 'Stayaan Maharaj',
                    '3': 'Daniel Yatali',
                    '4': 'Satish Maharaj',
                    '5': 'Selena Madrey',
                    '6': 'Veron Ramkissoon',
                    '7': 'Tamika Ramkissoon',
                    '8': 'Samuel Mahadeo',
                    '9': 'Neha Maharaj'
                }
            })
    
    # Default behavior - use the hard-coded demo for now
    try:
        # Original demo implementation
        I, J, K = 10, 40, 1
        result = generate_schedule(I, J, K)
        
        if result['status'] != 'success':
            return jsonify(result), 400
            
        # Format the data for the UI (same as before)
        assignments = result['assignments']
        staff_index = result['staff_index']
        
        # Define days and shift times for hourly slots
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        shift_times = ["9:00 am", "10:00 am", "11:00 am", "12:00 pm", 
                      "1:00 pm", "2:00 pm", "3:00 pm", "4:00 pm"]
        
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

@schedule_views.route('/api/schedule/generate', methods=['POST'])
@jwt_required()
@admin_required
def generate_schedule_endpoint():
    """Generate a schedule with specified date range"""
    try:
        data = request.json
        
        # Parse dates
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        start_date = None
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        else:
            # Default to today
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        end_date = None
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        # Call the schedule generator
        result = generate_schedule(start_date, end_date)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@schedule_views.route('/api/schedule/<int:schedule_id>/publish', methods=['POST'])
@jwt_required()
@admin_required
def publish_schedule_endpoint(schedule_id):
    """Publish a schedule and notify all assigned staff"""
    result = publish_schedule(schedule_id)
    return jsonify(result)

@schedule_views.route('/api/schedule/current', methods=['GET'])
@jwt_required()
def get_current_schedule_endpoint():
    """Get the current schedule"""
    schedule = get_current_schedule()
    if schedule:
        return jsonify({'status': 'success', 'schedule': schedule})
    else:
        return jsonify({'status': 'error', 'message': 'No schedule found'}), 404