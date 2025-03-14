from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user
from datetime import datetime, timedelta
from App.controllers.schedule import (
    help_desk_scheduler,  # Keep for testing
    generate_help_desk_schedule,
    publish_schedule,
    get_schedule_for_week
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
    # For demo purposes, you can still use the hard-coded scheduler
    # In a real application, you would get the week number from the request
    # and use get_schedule_for_week(week_number)
    
    try:
        # Original demo implementation
        I, J, K = 10, 40, 1
        result = help_desk_scheduler(I, J, K)
        
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
def generate_schedule():
    """Generate a new schedule using the model-based approach"""
    try:
        data = request.json
        week_number = data.get('week_number', 1)
        
        # Parse the start date or default to next Monday
        start_date_str = data.get('start_date')
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        else:
            # Default to next Monday
            today = datetime.now()
            days_ahead = (0 - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            start_date = today + timedelta(days=days_ahead)
        
        # Call the new schedule generator
        result = generate_help_desk_schedule(week_number, start_date)
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

@schedule_views.route('/api/schedule/week/<int:week_number>', methods=['GET'])
@jwt_required()
def get_week_schedule(week_number):
    """Get the schedule for a specific week"""
    schedule = get_schedule_for_week(week_number)
    if schedule:
        return jsonify({'status': 'success', 'schedule': schedule})
    else:
        return jsonify({'status': 'error', 'message': 'Schedule not found'}), 404