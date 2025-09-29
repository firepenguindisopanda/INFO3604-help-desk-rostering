from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for, send_file
from flask_jwt_extended import jwt_required, current_user
from datetime import datetime, timedelta, time
from App.controllers.schedule import (
    generate_help_desk_schedule,
    generate_lab_schedule,
    publish_schedule,
    get_current_schedule,
    publish_and_notify,
    clear_schedule,
    get_schedule_data
)
from App.models import Schedule, Shift, Allocation, Student, Availability, HelpDeskAssistant
from App.database import db
from App.middleware import admin_required
from io import BytesIO
from weasyprint import HTML, CSS
import tempfile
import os
from functools import lru_cache


schedule_views = Blueprint('schedule_views', __name__, template_folder='../templates')

@schedule_views.route('/schedule')
@jwt_required()
@admin_required
def schedule():
    return render_template('admin/schedule/view.html')

@schedule_views.route('/api/schedule/save', methods=['POST'])
@jwt_required()
@admin_required
def save_schedule():
    """Save schedule changes to the database"""
    try:
        print("Received request to save schedule")
        data = request.json
        
        # Parse dates
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        assignments = data.get('assignments', [])
        
        # Determine schedule type based on current user role
        schedule_type = current_user.role  # This should be 'helpdesk' or 'lab'
        
        print(f"Save request: start={start_date_str}, end={end_date_str}, type={schedule_type}, assignments={len(assignments)}")
        
        # Validate
        if not start_date_str or not end_date_str:
            return jsonify({
                'status': 'error',
                'message': 'Start and end dates are required'
            }), 400
            
        # Parse dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid date format. Use YYYY-MM-DD.'
            }), 400
            
        # Get or create the main schedule for the appropriate type
        schedule_id = 1 if schedule_type == 'helpdesk' else 2  # Use different IDs for different schedule types
        schedule = Schedule.query.filter_by(id=schedule_id, type=schedule_type).first()
        
        if not schedule:
            print(f"Creating new {schedule_type} schedule")
            schedule = Schedule(schedule_id, start_date, end_date, type=schedule_type)
            db.session.add(schedule)
        else:
            print(f"Updating existing {schedule_type} schedule: id={schedule.id}")
            schedule.start_date = start_date
            schedule.end_date = end_date
            db.session.add(schedule)
            
        db.session.flush()  # Get the schedule ID if it's new
        
        # IMPORTANT: First, clear ALL allocations for shifts in the date range
        # This ensures proper cleanup before rebuilding assignments
        shifts_to_clear = Shift.query.filter(
            Shift.schedule_id == schedule.id,
            Shift.date >= start_date,
            Shift.date <= end_date
        ).all()
        
        for shift in shifts_to_clear:
            Allocation.query.filter_by(shift_id=shift.id).delete()
        
        # Track shifts we've processed
        processed_shifts = {}
        
        # Process assignments and create/update shifts
        for assignment in assignments:
            day = assignment.get('day')
            time_str = assignment.get('time')
            staff_list = assignment.get('staff', [])
            
            print(f"Processing assignment: day={day}, time={time_str}, staff={len(staff_list)}")
            
            # Convert day name to index (0=Monday, 1=Tuesday, etc.)
            day_map = {'MON': 0, 'TUE': 1, 'WED': 2, 'THUR': 3, 'FRI': 4, 'SAT': 5,
                       'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5}
            day_idx = day_map.get(day, 0)
            
            # Calculate shift date based on start_date and day index
            shift_date = start_date + timedelta(days=day_idx)
            
            # Parse shift time
            try:
                hour = parse_time_to_hour(time_str, schedule_type)
                
                if hour is None:
                    print(f"Could not parse hour from time: {time_str}")
                    continue
                    
                print(f"Parsed time: original='{time_str}', extracted hour={hour}")
                
                # Create or find shift
                shift_start = datetime.combine(shift_date.date(), datetime.min.time().replace(hour=hour, minute=0))
                
                # Set end time based on schedule type
                if schedule_type == 'lab':
                    # Lab shifts are 4 hours
                    shift_end = shift_start + timedelta(hours=4)
                else:
                    # Helpdesk shifts are 1 hour
                    shift_end = shift_start + timedelta(hours=1)
                
                # Look for existing shift
                shift = Shift.query.filter_by(
                    schedule_id=schedule.id,
                    date=shift_date,
                    start_time=shift_start
                ).first()
                
                # If shift doesn't exist, create it
                if not shift:
                    print(f"Creating new shift for date={shift_date}, hour={hour}")
                    shift = Shift(shift_date, shift_start, shift_end, schedule.id)
                    db.session.add(shift)
                    db.session.flush()  # Get the shift ID
                else:
                    print(f"Using existing shift {shift.id}")
                
                # Track this shift as processed
                processed_shifts[shift.id] = True
                
                # Create allocations for staff if there are any
                if staff_list:
                    for staff in staff_list:
                        staff_id = staff.get('id')
                        
                        # Verify staff exists
                        student = Student.query.get(staff_id)
                        if not student:
                            print(f"Warning: Student {staff_id} not found")
                            continue
                            
                        # Create allocation
                        allocation = Allocation(staff_id, shift.id, schedule.id)
                        db.session.add(allocation)
                        
                        print(f"Created allocation for staff {staff_id} on shift {shift.id}")
                else:
                    print(f"No Student Assistant assigned to shift {shift.id}")
                
            except Exception as e:
                print(f"Error processing shift {day} at {time_str}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Commit all changes
        db.session.commit()
        
        print(f"Schedule saved successfully")
        
        return jsonify({
            'status': 'success',
            'message': 'Schedule saved successfully',
            'schedule_id': schedule.id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error saving schedule: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


def parse_time_to_hour(time_str, schedule_type):
    """Helper function to parse time string to hour"""
    try:
        # Special handling for lab time blocks
        if schedule_type == 'lab' and '-' in time_str:
            if time_str == "8:00 am - 12:00 pm":
                return 8
            elif time_str == "12:00 pm - 4:00 pm":
                return 12
            elif time_str == "4:00 pm - 8:00 pm":
                return 16
        
        # Regular parsing for single time format
        if '-' in time_str:
            # Format is "9:00 - 10:00" or "9:00 am - 10:00 am"
            start_time_str = time_str.split('-')[0].strip()
        else:
            # Format is "9:00 am" or just "9:00"
            start_time_str = time_str
        
        # Remove am/pm and just get the hour
        start_time_str = start_time_str.lower()
        if 'am' in start_time_str:
            start_time_str = start_time_str.replace('am', '').strip()
        elif 'pm' in start_time_str:
            start_time_str = start_time_str.replace('pm', '').strip()
        
        # Extract hour
        hour = int(start_time_str.split(':')[0])
        
        # Adjust hour for PM if needed (but not for 12pm)
        if 'pm' in time_str.lower() and hour < 12:
            hour += 12
        
        return hour
    except ValueError:
        return None

@schedule_views.route('/api/schedule/remove-staff', methods=['POST'])
@jwt_required()
@admin_required
def remove_staff_from_shift():
    """Remove a specific staff from a specific shift"""
    try:
        data = request.json
        staff_id = data.get('staff_id')
        cell_day = data.get('day')
        cell_time = data.get('time')
        
        print(f"Removing staff: id={staff_id}, day={cell_day}, time={cell_time}")
        
        if not staff_id or not cell_day or not cell_time:
            return jsonify({
                'status': 'error',
                'message': 'Missing required parameters'
            }), 400
        
        # Try to parse shift_id directly if it's provided
        shift_id = data.get('shift_id')
        
        # If we have a direct shift_id, use that
        if shift_id:
            print(f"Using provided shift_id: {shift_id}")
            shift = Shift.query.get(shift_id)
        else:
            # Otherwise, find it based on day and time
            day_map = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5}
            day_index = day_map.get(cell_day)
            
            if day_index is None:
                return jsonify({'status': 'error', 'message': f'Invalid day: {cell_day}'}), 400
            
            # Get the current schedule based on user role
            schedule_type = current_user.role
            schedule = Schedule.query.filter_by(type=schedule_type).first()
            if not schedule:
                return jsonify({'status': 'error', 'message': 'No schedule found'}), 404
            
            # Calculate the date
            shift_date = schedule.start_date + timedelta(days=day_index)
            
            # Parse the time
            hour = parse_time_to_hour(cell_time, schedule_type)
            if hour is None:
                return jsonify({'status': 'error', 'message': f'Invalid time format: {cell_time}'}), 400
            
            print(f"Searching for shift: date={shift_date}, hour={hour}")
            
            # Find the shift
            shift = Shift.query.filter_by(
                schedule_id=schedule.id,
                date=shift_date,
                start_time=datetime.combine(shift_date, time(hour=hour))
            ).first()
        
        if shift:
            print(f"Found shift: id={shift.id}")
            
            # Remove the allocation
            allocation = Allocation.query.filter_by(
                shift_id=shift.id,
                username=staff_id
            ).first()
            
            if allocation:
                print(f"Found allocation to remove: shift_id={shift.id}, username={staff_id}")
                db.session.delete(allocation)
                db.session.commit()
                return jsonify({'status': 'success', 'message': 'Staff removed successfully'})
            else:
                print(f"No allocation found for shift_id={shift.id}, username={staff_id}")
                return jsonify({'status': 'error', 'message': 'Staff allocation not found'}), 404
        else:
            print(f"No shift found for the given parameters")
            return jsonify({'status': 'error', 'message': 'Shift not found'}), 404
            
    except Exception as e:
        db.session.rollback()
        print(f"Error removing staff: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500
        
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
    
    # Default behavior is to get the current schedule
    schedule = get_current_schedule()
    if schedule:
        return jsonify({
            'status': 'success',
            'schedule': schedule
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'No schedule found'
        }), 404

@schedule_views.route('/api/schedule/generate', methods=['POST'])
@jwt_required()
@admin_required
def generate_schedule_endpoint():
    """Generate a schedule with specified date range"""
    try:
        user = current_user
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
        
        # Log details about the request
        print(f"Generating {user.role} schedule from {start_date} to {end_date}")
        
        # Filter students based on admin role
        if user.role == 'helpdesk':
            result = generate_help_desk_schedule(start_date, end_date)
        elif user.role == 'lab':
            result = generate_lab_schedule(start_date, end_date)
        else:
            return jsonify({
                'status': 'error',
                'message': 'Invalid admin role for schedule generation'
            }), 400
            
        # Log the result
        print(f"Schedule generation result: {result}")
        
        # Add the schedule type to the result for frontend reference
        if result.get('status') == 'success':
            result['schedule_type'] = user.role
            
        return jsonify(result)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
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

@schedule_views.route('/api/schedule/clear', methods=['POST'])
@jwt_required()
@admin_required
def clear_schedule_endpoint():
    """Clear the entire schedule from the database"""
    try:
        # Get data from request body
        data = request.json or {}
        
        # Get schedule ID (default to 1 for helpdesk if not specified)
        schedule_id = data.get('schedule_id', 1)
        
        # Call the controller function to clear the schedule
        result = clear_schedule()  # This function now handles the schedule ID
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@schedule_views.route('/api/schedule/<int:schedule_id>/publish_with_sync', methods=['POST'])
@jwt_required()
@admin_required
def publish_schedule_with_sync(schedule_id):
    """Publish a schedule, notify all assigned staff, and sync data between views"""
    
    result = publish_and_notify(schedule_id)
    return jsonify(result)

@schedule_views.route('/api/schedule/current', methods=['GET'])
@jwt_required()
def get_current_schedule_endpoint():
    """OPTIMIZED: Get the current schedule based on admin role, formatted for display."""
    try:
        # Get user role and determine schedule type
        role = current_user.role
        schedule_type = role  # 'helpdesk' or 'lab'
        schedule_id = 1 if schedule_type == 'helpdesk' else 2 
        
        print(f"Getting current {schedule_type} schedule (ID: {schedule_id})")
        
        # OPTIMIZATION: Single query with eager loading to prevent N+1 queries
        from sqlalchemy.orm import selectinload
        
        schedule = (
            db.session.query(Schedule)
            .options(
                selectinload(Schedule.shifts)
                .selectinload(Shift.allocations)
                .selectinload(Allocation.student)
            )
            .filter_by(id=schedule_id, type=schedule_type)
            .first()
        )
        
        if not schedule:
            print(f"No {schedule_type} schedule found with ID {schedule_id}")
            return jsonify({'status': 'error', 'message': f'No {schedule_type} schedule found'}), 404
        
        print(f"Found schedule: id={schedule.id}, start={schedule.start_date}, end={schedule.end_date}, type={schedule.type}")
        print(f"Loaded {len(schedule.shifts)} shifts with eager loading")
        
        # Format the schedule base
        formatted_schedule = {
            "schedule_id": schedule.id,
            "date_range": f"{schedule.start_date.strftime('%d %b')} - {schedule.end_date.strftime('%d %b, %Y')}",
            "is_published": schedule.is_published,
            "type": schedule_type,
            "days": []
        }
        
        # OPTIMIZATION: Group shifts by day index using pre-loaded data
        shifts_by_day = {}
        for shift in schedule.shifts:
            day_idx = shift.date.weekday() 
            
            # Skip days outside the expected range
            if schedule_type == 'helpdesk' and day_idx > 4:
                continue
            if schedule_type == 'lab' and day_idx > 5:
                 continue

            if day_idx not in shifts_by_day:
                shifts_by_day[day_idx] = []
                
            # OPTIMIZATION: Get assistants from pre-loaded data
            assistants = []
            for allocation in shift.allocations:
                if allocation.student:  # Already loaded via eager loading
                    assistants.append({
                        "id": allocation.student.username, 
                        "name": allocation.student.get_name(),
                        "username": allocation.student.username  # Important: include username for removal
                    })
            
            # Store shift with ALL necessary data for later operations
            shifts_by_day[day_idx].append({
                "shift_id": shift.id,
                "time": f"{shift.start_time.strftime('%-I:%M %p')}",  # Store original time format
                "hour": shift.start_time.hour,
                "date": shift.date.isoformat(),  # Store the actual date for this shift
                "assistants": assistants
            })
        
        # Create days array with appropriate structure
        days = []
        
        # LAB SCHEDULE LOGIC
        if schedule_type == 'lab':
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            day_codes = ["MON", "TUE", "WED", "THUR", "FRI", "SAT"]
            lab_shifts_config = [
                {'hour': 8, 'time_str': "8:00 am - 12:00 pm"},
                {'hour': 12, 'time_str': "12:00 pm - 4:00 pm"},
                {'hour': 16, 'time_str': "4:00 pm - 8:00 pm"}
            ]
            
            for day_idx in range(6):
                day_date = schedule.start_date + timedelta(days=day_idx)
                day_shifts_data = []
                
                actual_shifts_today = shifts_by_day.get(day_idx, [])
                
                for config in lab_shifts_config:
                    hour = config['hour']
                    time_str = config['time_str']
                    
                    matching_shift = next((s for s in actual_shifts_today if s["hour"] == hour), None)
                    
                    if matching_shift:
                        # Important: preserve the actual shift ID and date for later operations
                        shift_data = {
                            "shift_id": matching_shift['shift_id'],
                            "time": time_str,
                            "hour": hour,
                            "date": matching_shift['date'],  # Actual date of this shift
                            "assistants": matching_shift['assistants']
                        }
                        day_shifts_data.append(shift_data)
                    else:
                        day_shifts_data.append({
                            "shift_id": None,
                            "time": time_str,
                            "hour": hour,
                            "date": day_date.isoformat(),
                            "assistants": []
                        })

                days.append({
                    "day": day_names[day_idx],
                    "day_code": day_codes[day_idx],
                    "date": day_date.strftime("%d %b"),
                    "day_idx": day_idx,  # Store day index for later reference
                    "shifts": day_shifts_data
                })

        # HELPDESK SCHEDULE LOGIC
        else:
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            day_codes = ["MON", "TUE", "WED", "THUR", "FRI"]
            
            for day_idx in range(5):
                day_date = schedule.start_date + timedelta(days=day_idx)
                day_shifts_data = []
                
                actual_shifts_today = shifts_by_day.get(day_idx, [])
                
                for hour in range(9, 17):
                    matching_shift = next((s for s in actual_shifts_today if s["hour"] == hour), None)

                    if matching_shift:
                        start_dt = datetime.now().replace(hour=hour, minute=0)
                        end_dt = start_dt + timedelta(hours=1)
                        time_str = f"{start_dt.strftime('%-I:%M %p')}"
                        
                        shift_data = {
                            "shift_id": matching_shift['shift_id'],
                            "time": time_str,
                            "hour": hour,
                            "date": matching_shift['date'],
                            "assistants": matching_shift['assistants']
                        }
                        day_shifts_data.append(shift_data)
                    else:
                        start_dt = datetime.now().replace(hour=hour, minute=0)
                        time_str = f"{start_dt.strftime('%-I:%M %p')}"
                        
                        day_shifts_data.append({
                            "shift_id": None,
                            "time": time_str,
                            "hour": hour,
                            "date": day_date.isoformat(),
                            "assistants": []
                        })

                days.append({
                    "day": day_names[day_idx],
                    "day_code": day_codes[day_idx],
                    "date": day_date.strftime("%d %b"),
                    "day_idx": day_idx,
                    "shifts": day_shifts_data
                })
        
        formatted_schedule["days"] = days
        
        print(f"Returning formatted {schedule_type} schedule with {len(days)} days.")
        return jsonify({'status': 'success', 'schedule': formatted_schedule})
        
    except Exception as e:
        print(f"Error getting current schedule: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'An error occurred: {str(e)}'}), 500

@schedule_views.route('/api/staff/available', methods=['GET'])
@jwt_required()
@admin_required
def get_available_staff():
    """
    Get all staff members available for a specific day and time
    Query parameters:
    - day: The day of the week (e.g., "Monday", "MON")
    - time: The time slot (e.g., "9:00 am")
    """
    try:
        # Get query parameters
        day = request.args.get('day')
        time_slot = request.args.get('time')
        
        if not day or not time_slot:
            # Be tolerant – return empty list instead of 400 so the UI doesn't spam errors
            return jsonify({
                'status': 'success',
                'staff': [],
                'note': 'Missing day/time parameter'
            })
        
        # Convert day to day_of_week index (0=Monday, 1=Tuesday, etc.)
        day_map = {
            'MON': 0, 'TUE': 1, 'WED': 2, 'THUR': 3, 'FRI': 4,
            'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4
        }
        day_of_week = day_map.get(day)
        
        if day_of_week is None:
            return jsonify({
                'status': 'success',
                'staff': [],
                'note': f'Unrecognized day format: {day}'
            })
        
        # Convert time_slot to hour
        hour = None
        
        # Parse formats like "9:00 am", "9:00 - 10:00"
        if time_slot:
            if '-' in time_slot:
                # Format is "9:00 - 10:00"
                start_time_str = time_slot.split('-')[0].strip()
            else:
                # Format is "9:00 am"
                start_time_str = time_slot
                
            # Remove am/pm and get hour
            if 'am' in start_time_str.lower():
                start_time_str = start_time_str.lower().replace('am', '').strip()
                hour = int(start_time_str.split(':')[0])
            elif 'pm' in start_time_str.lower():
                start_time_str = start_time_str.lower().replace('pm', '').strip()
                hour = int(start_time_str.split(':')[0])
                if hour < 12:
                    hour += 12
            else:
                # No am/pm, assume 24-hour format
                hour = int(start_time_str.split(':')[0])
        
        if hour is None:
            return jsonify({
                'status': 'success',
                'staff': [],
                'note': f'Unrecognized time format: {time_slot}'
            })
        
        # Get all active help desk assistants
        assistants = HelpDeskAssistant.query.filter_by(active=True).all()
        
        # Check availability for each assistant
        available_staff = []
        
        for assistant in assistants:
            # Get the student record for this assistant
            student = Student.query.get(assistant.username)
            
            if not student:
                continue
                
            # Check if the assistant is available at this time
            availabilities = Availability.query.filter_by(
                username=assistant.username,
                day_of_week=day_of_week
            ).all()
            
            is_available = False
            
            for avail in availabilities:
                # Create a time object for the hour we want to check
                check_time = time(hour=hour)
                
                # Check if this availability window includes our time
                if avail.start_time <= check_time and avail.end_time >= time(hour=hour+1):
                    is_available = True
                    break
            
            if is_available:
                available_staff.append({
                    'id': assistant.username,
                    'name': student.get_name(),
                    'degree': student.degree
                })
        
        # Return the available staff
        return jsonify({
            'status': 'success',
            'staff': available_staff
        })
        
    except Exception as e:
        print(f"Error getting available Student Assistant: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@schedule_views.route('/api/staff/check-availability', methods=['GET'])
@jwt_required()
def check_staff_availability():
    """
    Check if a specific staff member is available at a given day and time
    """
    try:
        # Get query parameters
        staff_id = request.args.get('staff_id')
        day = request.args.get('day')
        time_slot = request.args.get('time')
        
        # Be tolerant: instead of 400 we return success false so the front-end doesn't log noisy errors
        if not staff_id or not day or not time_slot:
            return jsonify({
                'status': 'success',
                'is_available': False,
                'note': 'Missing one or more required parameters'
            })
        
        # Convert day to day_of_week index
        day_map = {
            'MON': 0, 'TUE': 1, 'WED': 2, 'THUR': 3, 'FRI': 4, 'SAT': 5,
            'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5
        }
        day_of_week = day_map.get(day)
        
        if day_of_week is None:
            return jsonify({
                'status': 'success',
                'is_available': False,
                'note': f'Unrecognized day format: {day}'
            })
        
        # Parse time using schedule type
        schedule_type = current_user.role
        hour = parse_time_to_hour(time_slot, schedule_type)
        
        if hour is None:
            return jsonify({
                'status': 'success',
                'is_available': False,
                'note': f'Unrecognized time format: {time_slot}'
            })
        
        # Check availability in the database
        availabilities = Availability.query.filter_by(
            username=staff_id,
            day_of_week=day_of_week
        ).all()
        
        is_available = False
        
        for avail in availabilities:
            check_time = time(hour=hour)
            
            # For lab shifts, check if the entire 4-hour block is available
            if schedule_type == 'lab' and '-' in time_slot:
                end_hour = hour + 4
                if end_hour > 24:
                    end_hour = 24  # Cap at midnight
                end_time = time(hour=end_hour)
                if avail.start_time <= check_time and avail.end_time >= end_time:
                    is_available = True
                    break
            else:
                # For regular hourly shifts
                if avail.start_time <= check_time and avail.end_time >= time(hour=hour+1):
                    is_available = True
                    break
        
        # Check if the staff is already allocated to another shift at the same time
        if is_available:
            # Get the appropriate schedule
            schedule = Schedule.query.filter_by(type=schedule_type).first()
            if schedule:
                # Find shifts at this time within the current week
                if schedule.start_date:
                    # Calculate the specific date for this day
                    current_date = datetime.now().date()
                    target_date = current_date + timedelta(days=(day_of_week - current_date.weekday()) % 7)
                    
                    # Find any conflicting shifts
                    conflicting_shifts = Shift.query.filter(
                        Shift.schedule_id == schedule.id,
                        Shift.date == target_date,
                        Shift.start_time == datetime.combine(target_date, time(hour=hour))
                    ).all()
                    
                    # Check if staff is already allocated to any of these shifts
                    for shift in conflicting_shifts:
                        allocations = Allocation.query.filter_by(
                            shift_id=shift.id,
                            username=staff_id
                        ).first()
                        
                        if allocations:
                            # Staff is already allocated to a shift at this time
                            is_available = False
                            break
        
        return jsonify({
            'status': 'success',
            'is_available': is_available
        })
        
    except Exception as e:
        print(f"Error checking Student Assistant availability: {e}")
        import traceback
        traceback.print_exc()
        # Default to true in error cases to not block UI
        return jsonify({
            'status': 'success',
            'is_available': True
        })


def _normalize_day(day):
    mapping = {
        'MON':0,'TUE':1,'WED':2,'THUR':3,'FRI':4,'SAT':5,
        'Monday':0,'Tuesday':1,'Wednesday':2,'Thursday':3,'Friday':4,'Saturday':5
    }
    return mapping.get(day)

def _parse_hour(time_slot, schedule_type):
    return parse_time_to_hour(time_slot, schedule_type)

@lru_cache(maxsize=2048)
def _compute_single_availability(staff_id, day_idx, hour, schedule_type, is_block):
    """Pure helper for availability; cached to reduce DB lookups in a batch window."""
    # Query availabilities for staff & day
    avails = Availability.query.filter_by(username=staff_id, day_of_week=day_idx).all()
    if not avails:
        return False
    for avail in avails:
        base_ok = avail.start_time <= time(hour=hour) and avail.end_time >= (time(hour=hour+1) if not is_block else time(hour=hour+4))
        if base_ok:
            # Check allocation conflicts
            schedule = Schedule.query.filter_by(type=schedule_type).first()
            if not schedule or not schedule.start_date:
                return True
            target_date = schedule.start_date + timedelta(days=day_idx)
            conflict = Allocation.query.join(Shift, Allocation.shift_id==Shift.id).filter(
                Allocation.username==staff_id,
                Shift.schedule_id==schedule.id,
                Shift.date==target_date,
                Shift.start_time==datetime.combine(target_date, time(hour=hour))
            ).first()
            if conflict:
                return False
            return True
    return False

@schedule_views.route('/api/staff/check-availability/batch', methods=['POST'])
@jwt_required()
def batch_check_staff_availability():
    """
    Batch availability check.
    Request JSON: { "queries": [ {"staff_id":"...","day":"Monday","time":"9:00 am"}, ... ] }
    Response: { "status":"success", "results": [ {"staff_id":..., "day":..., "time":..., "is_available": bool} ] }
    """
    try:
        payload = request.get_json(force=True) or {}
        queries = payload.get('queries', [])
        schedule_type = current_user.role
        results = []
        for q in queries:
            staff_id = q.get('staff_id')
            day_raw = q.get('day')
            time_slot = q.get('time')
            if not staff_id or not day_raw or not time_slot:
                results.append({
                    'staff_id': staff_id,
                    'day': day_raw,
                    'time': time_slot,
                    'is_available': False,
                    'note': 'missing parameter'
                })
                continue
            day_idx = _normalize_day(day_raw)
            if day_idx is None:
                results.append({
                    'staff_id': staff_id,
                    'day': day_raw,
                    'time': time_slot,
                    'is_available': False,
                    'note': 'bad day'
                })
                continue
            hour = _parse_hour(time_slot, schedule_type)
            if hour is None:
                results.append({
                    'staff_id': staff_id,
                    'day': day_raw,
                    'time': time_slot,
                    'is_available': False,
                    'note': 'bad time'
                })
                continue
            is_block = schedule_type=='lab' and '-' in time_slot
            is_avail = _compute_single_availability(staff_id, day_idx, hour, schedule_type, is_block)
            results.append({
                'staff_id': staff_id,
                'day': day_raw,
                'time': time_slot,
                'is_available': is_avail
            })
        return jsonify({'status':'success','results':results})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'status':'error','message':str(e)}), 500

@schedule_views.route('/api/schedule/pdf', methods=['GET'])
@jwt_required()
@admin_required
def download_schedule_pdf():
    """Generate and download current schedule as PDF"""
    try:
        # Determine the schedule type from user role
        schedule_type = current_user.role
        
        # Determine the schedule ID based on type
        schedule_id = 2 if schedule_type == 'lab' else 1
        
        print(f"Generating PDF for {schedule_type} schedule (ID: {schedule_id})")
        
        # Get the schedule data based on correct schedule_id
        schedule = Schedule.query.get(schedule_id)
        if not schedule:
            return jsonify({
                'status': 'error',
                'message': f'No {schedule_type} schedule found'
            }), 404
            
        # Get the current schedule data
        # We need to modify get_current_schedule to accept a schedule_id parameter
        schedule_data = get_schedule_data(schedule_id)
        
        if not schedule_data:
            return jsonify({
                'status': 'error',
                'message': 'Failed to load schedule data'
            }), 404
        
        # Explicitly set the schedule type
        schedule_data['type'] = schedule_type
        
        # Create a temporary HTML file
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            temp_html = f.name
            
        # Render the schedule template with the data
        html_content = render_template(
            'admin/schedule/pdf_template.html',
            schedule=schedule_data
        )
        
        # Write the HTML to the temporary file
        with open(temp_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Convert HTML to PDF
        pdf = HTML(filename=temp_html).write_pdf(
            stylesheets=[
                CSS(string='@page { size: letter landscape; margin: 1cm; }')
            ]
        )
        
        # Clean up the temporary file
        os.unlink(temp_html)
        
        # Create a BytesIO object for the PDF data
        pdf_bytes = BytesIO(pdf)
        pdf_bytes.seek(0)
        
        # Generate a filename with current date and type
        schedule_name = "lab_schedule" if schedule_type == "lab" else "help_desk_schedule"
        filename = f"{schedule_name}_{datetime.now().strftime('%Y-%m-%d')}.pdf"
        
        # Send the PDF file
        return send_file(
            pdf_bytes,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500