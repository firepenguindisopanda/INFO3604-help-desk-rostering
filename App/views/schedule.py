from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for, send_file, current_app, abort
from flask_jwt_extended import jwt_required, current_user
from datetime import datetime, timedelta, time
import logging
from App.controllers.schedule import (
    generate_help_desk_schedule,
    generate_lab_schedule,
    publish_schedule,
    get_current_schedule,
    publish_and_notify,
    clear_schedule,
    get_schedule_data,
    save_schedule_assignments,
    remove_staff_allocation,
    list_available_staff_for_slot,
    check_staff_availability_for_slot,
    batch_staff_availability,
    batch_list_available_staff_for_slots,
    generate_schedule_pdf_for_type
)
from App.controllers.student import get_student
from App.controllers.help_desk_assistant import get_help_desk_assistant
from App.database import db
from App.middleware import admin_required
from App.models import Schedule, Shift, Allocation
from io import BytesIO
from weasyprint import HTML, CSS
import tempfile
import os
from functools import lru_cache
import hashlib
import json

# Simple in-memory cache for schedule data
_schedule_cache = {}
_cache_timeout_seconds = 300  # 5 minutes

# Small TTL cache for individual availability checks to reduce repeated load
# Keyed by (schedule_type, staff_id, day, time_slot) -> (timestamp, response_dict)
_availability_cache = {}
_AVAILABILITY_CACHE_TTL = 10.0  # seconds - tuneable

def _get_availability_cache_key(schedule_type, staff_id, day, time_slot):
    return (str(schedule_type), str(staff_id), str(day), str(time_slot))

def _get_cached_availability(schedule_type, staff_id, day, time_slot):
    key = _get_availability_cache_key(schedule_type, staff_id, day, time_slot)
    entry = _availability_cache.get(key)
    if not entry:
        return None
    ts, value = entry
    if (datetime.now().timestamp() - ts) > _AVAILABILITY_CACHE_TTL:
        # expired
        _availability_cache.pop(key, None)
        return None
    return value

def _set_cached_availability(schedule_type, staff_id, day, time_slot, value):
    key = _get_availability_cache_key(schedule_type, staff_id, day, time_slot)
    _availability_cache[key] = (datetime.now().timestamp(), value)

logger = logging.getLogger(__name__)


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
        data = request.json
        
        # Parse request data
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        assignments = data.get('assignments', [])
        
        # Determine schedule type based on current user role
        schedule_type = current_user.role  # This should be 'helpdesk' or 'lab'
        
        # Delegate to controller
        result, status_code = save_schedule_assignments(schedule_type, start_date_str, end_date_str, assignments)
        return jsonify(result), status_code
        
    except Exception as e:
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
        shift_id = data.get('shift_id')
        
        if not staff_id:
            return jsonify({
                'status': 'error',
                'message': 'Staff ID is required'
            }), 400
        
        # Determine schedule type
        schedule_type = current_user.role
        result, status_code = remove_staff_allocation(
            schedule_type, 
            staff_id, 
            cell_day, 
            cell_time, 
            shift_id
        )
        return jsonify(result), status_code
        
    except Exception as e:
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
        current_app.logger.info("Generating %s schedule from %s to %s", user.role, start_date, end_date)

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
            
        current_app.logger.info("Schedule generation result: %s", result)

        # Add the schedule type to the result for frontend reference
        if result.get('status') == 'success':
            result['schedule_type'] = user.role
            
        return jsonify(result)

    except (BrokenPipeError, ConnectionResetError) as e:
        current_app.logger.warning("Client disconnected during schedule generation: %s", e)
        abort(499)
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
        result = clear_schedule()
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

def _get_cache_key(schedule_id, schedule_type):
    """Generate cache key for schedule data"""
    return f"schedule_{schedule_id}_{schedule_type}"

def _is_cache_valid(cache_entry):
    """Check if cache entry is still valid"""
    if not cache_entry:
        return False
    cache_time = cache_entry.get('timestamp', 0)
    return (datetime.now().timestamp() - cache_time) < _cache_timeout_seconds

@schedule_views.route('/api/schedule/current', methods=['GET'])
@jwt_required()
def get_current_schedule_endpoint():
    """Get the current schedule based on admin role, formatted for display."""
    try:
        # Get user role and determine schedule type
        # Be defensive: in tests current_user may be a MagicMock or partially mocked.
        role = getattr(current_user, 'role', None)
        if not isinstance(role, str):
            if getattr(current_user, 'type', None) == 'admin':
                role = 'helpdesk'  # default for admins
            else:
                role = getattr(current_user, 'type', None)
        if not isinstance(role, str):
            # Fallback to helpdesk to avoid passing non-primitive types into queries
            role = 'helpdesk'
        schedule_type = role  # 'helpdesk' or 'lab'
        schedule_id = 1 if schedule_type == 'helpdesk' else 2
        
        current_app.logger.info("Getting current %s schedule (ID: %s)", schedule_type, schedule_id)

        # Single query with eager loading to prevent N+1 queries
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
            current_app.logger.info("No %s schedule found with ID %s", schedule_type, schedule_id)
            return jsonify({'status': 'error', 'message': f'No {schedule_type} schedule found'}), 404
        
        current_app.logger.info(
            "Found schedule: id=%s, start=%s, end=%s, type=%s",
            schedule.id,
            schedule.start_date,
            schedule.end_date,
            schedule.type,
        )
        current_app.logger.info("Loaded %s shifts with eager loading", len(schedule.shifts))
        
        # Format the schedule base
        formatted_schedule = {
            "schedule_id": schedule.id,
            "date_range": f"{schedule.start_date.strftime('%d %b')} - {schedule.end_date.strftime('%d %b, %Y')}",
            "is_published": schedule.is_published,
            "type": schedule_type,
            "days": []
        }
        
        # Group shifts by day index using pre-loaded data
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
                
            # Get assistants from pre-loaded data
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
        
        # Build slot queries to compute available staff for each slot in one batch call
        slot_queries = []
        for day in formatted_schedule.get('days', []):
            for shift in day.get('shifts', []):
                slot_queries.append({
                    'shift_id': shift.get('shift_id'),
                    'date': shift.get('date'),
                    'hour': shift.get('hour')
                })

        try:
            batch_result, batch_status = batch_list_available_staff_for_slots(schedule_type, slot_queries)
            if batch_status == 200 and batch_result.get('status') == 'success':
                results = batch_result.get('results', [])
                # results are in same order as slot_queries
                idx = 0
                for day in formatted_schedule.get('days', []):
                    for shift in day.get('shifts', []):
                        # default to empty list
                        shift['available_staff'] = []
                        if idx < len(results):
                            res = results[idx]
                            shift['available_staff'] = res.get('available_staff', []) or []
                        idx += 1
        except Exception as e:
            # If batch availability fails, log and continue without availability to avoid blocking schedule
            current_app.logger.exception('Batch availability attach failed: %s', e)

        current_app.logger.info(
            "Returning formatted %s schedule with %s days.", schedule_type, len(days)
        )
        return jsonify({'status': 'success', 'schedule': formatted_schedule})
        
    except (BrokenPipeError, ConnectionResetError) as e:
        # Client disconnected while we were preparing the response. Log and abort
        current_app.logger.warning("Client disconnected while getting current schedule: %s", e)
        # Abort with a non-standard code for logging (499) so the worker does not crash
        abort(499)
    except Exception as e:
        current_app.logger.exception("Error getting current schedule: %s", e)
        return jsonify({'status': 'error', 'message': f'An error occurred: {str(e)}'}), 500

@schedule_views.route('/api/staff/available', methods=['GET'])
@jwt_required()
@admin_required
def get_available_staff():
    """
    Get all staff members available for a specific day and time.
    Query parameters:
    - day: The day of the week (e.g., "Monday", "MON")
    - time: The time slot (e.g., "9:00 am")
    """
    try:
        # Input validation
        day = request.args.get('day', '').strip()
        time_slot = request.args.get('time', '').strip()
        
        if not day:
            return jsonify({
                'status': 'error',
                'message': 'day parameter is required'
            }), 400
            
        if not time_slot:
            return jsonify({
                'status': 'error',
                'message': 'time parameter is required'
            }), 400
        
        # Validate day format
        valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
                     'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
        if day.lower() not in valid_days:
            return jsonify({
                'status': 'error',
                'message': 'Invalid day format. Expected day name or abbreviation.'
            }), 400
        
        # Determine schedule type
        schedule_type = current_user.role
        
        # Delegate to controller
        result, status_code = list_available_staff_for_slot(schedule_type, day, time_slot)
        
        if status_code == 200 and result.get('status') == 'success':
            return jsonify({
                'status': 'success',
                'staff': result.get('available_staff', [])
            })
        else:
            return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Error fetching available staff: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error occurred'
        }), 500

@schedule_views.route('/api/staff/check-availability', methods=['GET'])
@jwt_required()
def check_staff_availability():
    """
    Check if a specific staff member is available at a given day and time.
    Query parameters: staff_id, day, time
    """
    try:
        # Input validation
        staff_id = request.args.get('staff_id', '').strip()
        day = request.args.get('day', '').strip()
        time_slot = request.args.get('time', '').strip()

        # Validate required parameters
        if not staff_id:
            return jsonify({'status': 'error', 'message': 'staff_id parameter is required'}), 400

        if not day:
            return jsonify({'status': 'error', 'message': 'day parameter is required'}), 400

        if not time_slot:
            return jsonify({'status': 'error', 'message': 'time parameter is required'}), 400

        # Validate day format
        valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        if day.lower() not in valid_days:
            return jsonify({'status': 'error', 'message': f'Invalid day. Must be one of: {", ".join(valid_days)}'}), 400

        # Determine schedule type
        schedule_type = current_user.role

        # Try cache first
        cached = _get_cached_availability(schedule_type, staff_id, day, time_slot)
        if cached is not None:
            return jsonify(cached)

        # Delegate to controller
        result, status_code = check_staff_availability_for_slot(schedule_type, staff_id, day, time_slot)

        # Cache successful responses (200)
        if status_code == 200:
            _set_cached_availability(schedule_type, staff_id, day, time_slot, result)

        if status_code == 200:
            return jsonify(result)
        else:
            return jsonify(result), status_code

    except Exception as e:
        logger.error(f"Error in staff availability check: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error occurred'}), 500


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


@schedule_views.route('/api/staff/check-availability/batch', methods=['POST'])
@jwt_required()
@admin_required
def batch_check_staff_availability():
    """
    Batch availability check to reduce concurrent requests.
    Request JSON: { "queries": [ {"staff_id":"...","day":"Monday","time":"9:00 am"}, ... ] }
    Response: { "status":"success", "results": [ {"staff_id":..., "day":..., "time":..., "is_available": bool} ] }
    """
    try:
        payload = request.get_json(force=True) or {}
        queries = payload.get('queries', [])
        schedule_type = current_user.role
        
        # Delegate to controller
        result, status_code = batch_staff_availability(schedule_type, queries)
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@schedule_views.route('/api/schedule/pdf', methods=['GET'])
@jwt_required()
@admin_required
def download_schedule_pdf():
    """Generate and download current schedule as PDF"""
    try:
        # Determine the schedule type from user role
        schedule_type = current_user.role
        
        # Delegate to controller
        pdf_buffer, filename, error_response, status_code = generate_schedule_pdf_for_type(schedule_type)
        
        if error_response:
            return jsonify(error_response), status_code
        
        # Send the PDF file
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500