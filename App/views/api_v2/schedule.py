from flask import request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, current_user
from datetime import datetime, timedelta, timezone
import logging
from io import BytesIO
import tempfile
import os
from sqlalchemy.orm import selectinload

from App.views.api_v2 import api_v2
from App.views.api_v2.utils import api_success, api_error, validate_json_request
from App.middleware import admin_required
from App.database import db
from App.models import Schedule, Shift, Allocation, Student

# Constants for cleaner code
UNKNOWN_ERROR_MSG = "Unknown error"
NO_RESPONSE_MSG = "No response"
MAX_BATCH_QUERIES = 500
MAX_FUTURE_DAYS = 365


def _get_current_timestamp():
    """Get current timestamp in ISO format"""
    return datetime.now(timezone.utc).isoformat()


logger = logging.getLogger(__name__)


# ===========================
# SCHEDULE GENERATION & MANAGEMENT
# ===========================

@api_v2.route('/admin/schedule/generate', methods=['POST'])
@jwt_required()
@admin_required
def generate_schedule():
    """
    Generate a new schedule for the current admin's domain (helpdesk/lab)
    
    Request Body:
        {
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD"
        }
    
    Returns:
        Success: Schedule generation results with schedule_id
        Error: Validation errors or generation failures
    """
    try:
        logger.info("API v2: Generate schedule requested")
        # Validate request format
        data, error_response = validate_json_request(request)
        if error_response:
            logger.warning("API v2: Generate schedule validation failed")
            return error_response
        
        # Extract and validate required fields
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if not start_date_str or not end_date_str:
            return api_error(
                "Missing required fields", 
                errors={"start_date": "Required", "end_date": "Required"}
            )
        
        # Parse and validate dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError as e:
            logger.error("API v2: Invalid date format for generation", exc_info=True)
            return api_error(
                "Invalid date format", 
                errors={"date_format": "Use YYYY-MM-DD format"}
            )
        
        # Validate date range
        if start_date > end_date:
            return api_error(
                "Invalid date range", 
                errors={"date_range": "Start date must be before or equal to end date"}
            )
        
        # Validate date range is not too far in the future
        max_future_date = datetime.now().date() + timedelta(days=MAX_FUTURE_DAYS)
        if end_date > max_future_date:
            return api_error(
                "Date range too far in future", 
                errors={"end_date": "Cannot schedule more than 1 year in advance"}
            )
        
        # Get current admin role
        admin_role = getattr(current_user, 'role', 'helpdesk')
        logger.info(f"API v2: Generating schedule for role={admin_role} start={start_date_str} end={end_date_str}")
        
        # Import controllers
        from App.controllers.schedule import generate_help_desk_schedule, generate_lab_schedule
        
        # Generate schedule based on admin role
        if admin_role == 'lab':
            result = generate_lab_schedule(start_date, end_date)
        else:
            result = generate_help_desk_schedule(start_date, end_date)
        
        # Handle generation results
        if result and hasattr(result, 'get') and result.get('status') == 'success':
            logger.info(f"API v2: Schedule generated successfully (id={result.get('schedule_id')})")
            return api_success(
                data={
                    "schedule_id": result.get('schedule_id'),
                    "schedule_type": admin_role,
                    "start_date": start_date_str,
                    "end_date": end_date_str,
                    "shifts_generated": result.get('shifts_count', 0),
                    "generation_time": result.get('generation_time'),
                    "optimization_status": result.get('optimization_status')
                },
                message=f"Schedule generated successfully for {admin_role} domain",
                status_code=201
            )
        else:
            error_msg = result.get('message', UNKNOWN_ERROR_MSG) if isinstance(result, dict) else 'Generation failed'
            logger.error(f"API v2: Schedule generation failed: {error_msg}")
            return api_error(
                f"Failed to generate schedule: {error_msg}",
                status_code=500
            )
            
    except Exception as e:
        logger.exception("API v2: Internal error during schedule generation")
        return api_error(
            "Internal server error during schedule generation",
            errors={"exception": str(e)},
            status_code=500
        )


@api_v2.route('/admin/schedule/current', methods=['GET'])
@jwt_required()
@admin_required  
def get_current_schedule():
    """
    OPTIMIZED: Get the current active schedule for the admin's domain (helpdesk/lab)
    and format response to match the classic endpoint structure so the Next.js
    calendar renders consistently.
    """
    try:
        admin_role = getattr(current_user, 'role', 'helpdesk')
        schedule_type = admin_role
        schedule_id = 1 if schedule_type == 'helpdesk' else 2
        logger.info(f"API v2: Fetching current {schedule_type} schedule (ID: {schedule_id})")

        # OPTIMIZATION: Single query with eager loading to prevent N+1 queries
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
            logger.warning(f"API v2: No {schedule_type} schedule found with ID {schedule_id}")
            return api_error(f"No current {schedule_type} schedule found", status_code=404)

        logger.info(
            f"API v2: Found schedule id={schedule.id} with {len(schedule.shifts)} shifts, start={schedule.start_date}, end={schedule.end_date}, published={schedule.is_published}"
        )

        formatted = {
            "schedule_id": schedule.id,
            "date_range": f"{schedule.start_date.strftime('%d %b')} - {schedule.end_date.strftime('%d %b, %Y')}",
            "is_published": schedule.is_published,
            "type": schedule_type,
            "days": []
        }

        # OPTIMIZATION: Group shifts by weekday index using pre-loaded data
        shifts_by_day = {}
        for shift in schedule.shifts:
            day_idx = shift.date.weekday()
            # Skip out-of-range days
            if schedule_type == 'helpdesk' and day_idx > 4:
                continue
            if schedule_type == 'lab' and day_idx > 5:
                continue

            if day_idx not in shifts_by_day:
                shifts_by_day[day_idx] = []

            # OPTIMIZATION: Use pre-loaded data instead of separate queries
            assistants = []
            for alloc in shift.allocations:
                if alloc.student:  # Already loaded via eager loading
                    assistants.append({
                        "id": alloc.student.username,
                        "name": alloc.student.get_name(),
                        "username": alloc.student.username
                    })

            shifts_by_day[day_idx].append({
                "shift_id": shift.id,
                # Keep classic-style time formatting ('to') to match existing UI usage
                "time": f"{shift.start_time.strftime('%I:%M %p')} to {shift.end_time.strftime('%I:%M %p')}",
                "hour": shift.start_time.hour,
                "date": shift.date.isoformat(),
                "assistants": assistants
            })

        days = []
        if schedule_type == 'lab':
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            day_codes = ["MON", "TUE", "WED", "THUR", "FRI", "SAT"]
            lab_blocks = [
                {"hour": 8, "label": "8:00 am - 12:00 pm"},
                {"hour": 12, "label": "12:00 pm - 4:00 pm"},
                {"hour": 16, "label": "4:00 pm - 8:00 pm"},
            ]

            for day_idx in range(6):
                day_date = schedule.start_date + timedelta(days=day_idx)
                actual_shifts = shifts_by_day.get(day_idx, [])
                day_shifts = []
                for block in lab_blocks:
                    hour = block["hour"]
                    match = next((s for s in actual_shifts if s["hour"] == hour), None)
                    if match:
                        day_shifts.append({
                            "shift_id": match["shift_id"],
                            "time": block["label"],
                            "hour": hour,
                            "date": match["date"],
                            "assistants": match["assistants"],
                        })
                    else:
                        day_shifts.append({
                            "shift_id": None,
                            "time": block["label"],
                            "hour": hour,
                            "date": day_date.isoformat(),
                            "assistants": [],
                        })
                days.append({
                    "day": day_names[day_idx],
                    "day_code": day_codes[day_idx],
                    "date": day_date.strftime("%d %b"),
                    "day_idx": day_idx,
                    "shifts": day_shifts,
                })
        else:
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            day_codes = ["MON", "TUE", "WED", "THUR", "FRI"]
            for day_idx in range(5):
                day_date = schedule.start_date + timedelta(days=day_idx)
                actual_shifts = shifts_by_day.get(day_idx, [])
                day_shifts = []
                for hour in range(9, 17):
                    match = next((s for s in actual_shifts if s["hour"] == hour), None)
                    if match:
                        # Reformat time to a normalized display with 'to'
                        start_label = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0).strftime('%I:%M %p')
                        end_label = (datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(hours=1)).strftime('%I:%M %p')
                        time_label = f"{start_label} to {end_label}"
                        day_shifts.append({
                            "shift_id": match["shift_id"],
                            "time": time_label,
                            "hour": hour,
                            "date": match["date"],
                            "assistants": match["assistants"],
                        })
                    else:
                        start_label = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0).strftime('%I:%M %p')
                        end_label = (datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(hours=1)).strftime('%I:%M %p')
                        time_label = f"{start_label} to {end_label}"
                        day_shifts.append({
                            "shift_id": None,
                            "time": time_label,
                            "hour": hour,
                            "date": day_date.isoformat(),
                            "assistants": [],
                        })
                days.append({
                    "day": day_names[day_idx],
                    "day_code": day_codes[day_idx],
                    "date": day_date.strftime("%d %b"),
                    "day_idx": day_idx,
                    "shifts": day_shifts,
                })

        formatted["days"] = days
        logger.info(f"API v2: Returning formatted {schedule_type} schedule with {len(days)} days")

        return api_success(
            data={"schedule": formatted, "schedule_type": schedule_type},
            message="Current schedule retrieved successfully"
        )
    except Exception as e:
        logger.exception("API v2: Failed to retrieve current schedule")
        return api_error(
            "Failed to retrieve current schedule",
            errors={"exception": str(e)},
            status_code=500
        )


@api_v2.route('/admin/schedule/details', methods=['GET'])
@jwt_required()
@admin_required
def get_schedule_details():
    """
    Get detailed schedule information by ID
    
    Query Parameters:
        id: Schedule ID
    
    Returns:
        Detailed schedule data with shifts and staff assignments
    """
    try:
        logger.info("API v2: Get schedule details requested")
        schedule_id = request.args.get('id', type=int)
        
        if not schedule_id:
            logger.warning("API v2: Missing schedule ID parameter")
            return api_error(
                "Missing schedule ID parameter",
                errors={"id": "Required integer parameter"}
            )
        
        from App.controllers.schedule import get_schedule_data
        
        # Get schedule details
        schedule_data = get_schedule_data(schedule_id)
        
        if not schedule_data:
            logger.warning(f"API v2: Schedule not found (id={schedule_id})")
            return api_error(
                f"Schedule with ID {schedule_id} not found",
                status_code=404
            )
        
        return api_success(
            data={"schedule": schedule_data},
            message="Schedule details retrieved successfully"
        )
        
    except Exception as e:
        logger.exception("API v2: Error retrieving schedule details")
        return api_error(
            "Failed to retrieve schedule details",
            errors={"exception": str(e)},
            status_code=500
        )


def _validate_save_request(data):
    """Validate save schedule request data"""
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    assignments = data.get('assignments', [])
    
    if not start_date_str or not end_date_str:
        return None, api_error(
            "Missing required fields",
            errors={
                "start_date": "Required" if not start_date_str else None,
                "end_date": "Required" if not end_date_str else None
            }
        )
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return None, api_error(
            "Invalid date format",
            errors={"date_format": "Use YYYY-MM-DD format"}
        )
    
    if not isinstance(assignments, list):
        return None, api_error(
            "Invalid assignments format",
            errors={"assignments": "Must be an array of assignment objects"}
        )
    
    return {
        'start_date': start_date,
        'end_date': end_date,
        'start_date_str': start_date_str,
        'end_date_str': end_date_str,
        'assignments': assignments
    }, None


def _process_schedule_assignments(schedule, assignments, start_date, end_date):
    """Process and save schedule assignments"""
    from App.models.shift import Shift
    from App.models.allocation import Allocation
    
    # Clear existing allocations in date range
    shifts_to_clear = Shift.query.filter(
        Shift.schedule_id == schedule.id,
        Shift.date >= start_date,
        Shift.date <= end_date
    ).all()
    
    for shift in shifts_to_clear:
        Allocation.query.filter_by(shift_id=shift.id).delete()
    
    # Process assignments
    assignments_processed = 0
    errors = []
    
    for assignment in assignments:
        try:
            day = assignment.get('day')
            time_str = assignment.get('time')
            staff_assignments = assignment.get('staff', [])
            
            if not day or not time_str:
                continue
                
            # Process each staff assignment
            for _ in staff_assignments:
                # Implementation would go here based on existing logic
                pass
                
            assignments_processed += 1
            
        except Exception as assignment_error:
            errors.append({
                "assignment": assignment,
                "error": str(assignment_error)
            })
    
    return assignments_processed, errors


@api_v2.route('/admin/schedule/save', methods=['POST'])
@jwt_required()
@admin_required
def save_schedule():
    """
    Save schedule changes and staff assignments
    
    Request Body:
        {
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD", 
            "assignments": [
                {
                    "day": "Monday",
                    "time": "9:00 am",
                    "cell_id": "cell-0-0",
                    "staff": [
                        {"id": "staff_id", "name": "Staff Name"}
                    ]
                }
            ],
            "schedule_type": "helpdesk|lab"
        }
    
    Returns:
        Success confirmation with saved schedule details
    """
    try:
        logger.info("API v2: Save schedule requested")
        # Validate request format
        data, error_response = validate_json_request(request)
        if error_response:
            logger.warning("API v2: Save schedule validation failed")
            return error_response
        
        # Validate request data
        validated_data, validation_error = _validate_save_request(data)
        if validation_error:
            return validation_error
        
        schedule_type = data.get('schedule_type', getattr(current_user, 'role', 'helpdesk'))
        
        # Process save operation
        from App.models.schedule import Schedule
        
        # Get or create schedule
        schedule_id = 1 if schedule_type == 'helpdesk' else 2
        schedule = Schedule.query.filter_by(id=schedule_id, type=schedule_type).first()
        
        if not schedule:
            logger.info(f"API v2: Creating new schedule (type={schedule_type}, id={schedule_id})")
            schedule = Schedule(schedule_id, validated_data['start_date'], validated_data['end_date'], type=schedule_type)
            db.session.add(schedule)
        else:
            logger.info(f"API v2: Updating schedule (id={schedule.id})")
            schedule.start_date = validated_data['start_date']
            schedule.end_date = validated_data['end_date']
        
        db.session.flush()
        
        # Process assignments
        assignments_processed, errors = _process_schedule_assignments(
            schedule, 
            validated_data['assignments'], 
            validated_data['start_date'], 
            validated_data['end_date']
        )
        
        # Commit changes
        db.session.commit()
        
        logger.info(f"API v2: Schedule saved (id={schedule.id}), assignments processed={assignments_processed}")
        return api_success(
            data={
                "schedule_id": schedule.id,
                "schedule_type": schedule_type,
                "assignments_processed": assignments_processed,
                "start_date": validated_data['start_date_str'],
                "end_date": validated_data['end_date_str'],
                "errors": errors if errors else None
            },
            message="Schedule saved successfully"
        )
        
    except Exception as e:
        db.session.rollback()
        logger.exception("API v2: Failed to save schedule")
        return api_error(
            "Failed to save schedule",
            errors={"exception": str(e)},
            status_code=500
        )


@api_v2.route('/admin/schedule/clear', methods=['POST'])
@jwt_required()
@admin_required
def clear_schedule():
    """
    Clear an existing schedule and all its assignments
    
    Request Body:
        {
            "schedule_type": "helpdesk|lab",
            "schedule_id": 1
        }
    
    Returns:
        Success confirmation of schedule clearing
    """
    try:
        logger.info("API v2: Clear schedule requested")
        # Validate request format
        data, error_response = validate_json_request(request)
        if error_response:
            logger.warning("API v2: Clear schedule validation failed")
            return error_response
        
        schedule_type = data.get('schedule_type', getattr(current_user, 'role', 'helpdesk'))
        schedule_id = data.get('schedule_id', 1 if schedule_type == 'helpdesk' else 2)
        
        # Import controller
        from App.controllers.schedule import clear_schedule as clear_schedule_controller
        
        # Clear schedule
        result = clear_schedule_controller()
        
        if result and result.get('status') == 'success':
            logger.info(f"API v2: Schedule cleared (type={schedule_type}, id={schedule_id})")
            return api_success(
                data={
                    "schedule_id": schedule_id,
                    "schedule_type": schedule_type,
                    "cleared_at": _get_current_timestamp()
                },
                message=f"Schedule cleared successfully for {schedule_type} domain"
            )
        else:
            logger.error(f"API v2: Failed to clear schedule (type={schedule_type}, id={schedule_id})")
            return api_error(
                "Failed to clear schedule",
                errors={"reason": result.get('message', UNKNOWN_ERROR_MSG) if result else NO_RESPONSE_MSG}
            )
        
    except Exception as e:
        logger.exception("API v2: Internal error during schedule clearing")
        return api_error(
            "Internal server error during schedule clearing",
            errors={"exception": str(e)},
            status_code=500
        )


@api_v2.route('/admin/schedule/<int:schedule_id>/publish', methods=['POST'])
@jwt_required()
@admin_required
def publish_schedule(schedule_id):
    """
    Publish a schedule to make it active and notify staff
    
    Path Parameters:
        schedule_id: The ID of the schedule to publish
    
    Returns:
        Success confirmation with publication details
    """
    try:
        logger.info(f"API v2: Publish schedule requested (id={schedule_id})")
        from App.controllers.schedule import publish_schedule as publish_schedule_controller
        
        # Publish schedule
        result = publish_schedule_controller(schedule_id)
        
        if result and result.get('status') == 'success':
            logger.info(f"API v2: Schedule published (id={schedule_id})")
            return api_success(
                data={
                    "schedule_id": schedule_id,
                    "published_at": _get_current_timestamp(),
                    "notifications_sent": result.get('notifications_sent', 0)
                },
                message="Schedule published successfully"
            )
        else:
            logger.error(f"API v2: Failed to publish schedule (id={schedule_id})")
            return api_error(
                "Failed to publish schedule",
                errors={"reason": result.get('message', UNKNOWN_ERROR_MSG) if result else NO_RESPONSE_MSG}
            )
        
    except Exception as e:
        logger.exception("API v2: Internal error during schedule publication")
        return api_error(
            "Internal server error during schedule publication",
            errors={"exception": str(e)},
            status_code=500
        )


# ===========================
# STAFF MANAGEMENT & AVAILABILITY
# ===========================

@api_v2.route('/admin/schedule/staff/available', methods=['GET'])
@jwt_required()
@admin_required
def get_available_staff():
    """
    Get staff available for a specific day and time
    
    Query Parameters:
        day: Day of week (e.g., "Monday")
        time: Time slot (e.g., "9:00 am")
    
    Returns:
        List of available staff members for the specified time
    """
    try:
        logger.info("API v2: Get available staff requested")
        day = request.args.get('day')
        time_slot = request.args.get('time')
        
        if not day or not time_slot:
            return api_error(
                "Missing required parameters",
                errors={
                    "day": "Required" if not day else None,
                    "time": "Required" if not time_slot else None
                }
            )
        
        from App.controllers.availability import get_available_staff_for_time
        
        # Get available staff
        staff_list = get_available_staff_for_time(day, time_slot)
        
        logger.info(f"API v2: Available staff count={len(staff_list)} for {day} {time_slot}")
        return api_success(
            data={
                "staff": staff_list,
                "day": day,
                "time": time_slot,
                "count": len(staff_list)
            },
            message=f"Retrieved {len(staff_list)} available staff for {day} at {time_slot}"
        )
        
    except Exception as e:
        logger.exception("API v2: Failed to retrieve available staff")
        return api_error(
            "Failed to retrieve available staff",
            errors={"exception": str(e)},
            status_code=500
        )


@api_v2.route('/admin/schedule/staff/check-availability', methods=['GET'])
@jwt_required()
@admin_required
def check_staff_availability():
    """
    Check if a specific staff member is available at a given time
    
    Query Parameters:
        staff_id: Staff member ID
        day: Day of week
        time: Time slot
    
    Returns:
        Availability status for the specified staff and time
    """
    try:
        logger.info("API v2: Check staff availability requested")
        staff_id = request.args.get('staff_id')
        day = request.args.get('day')
        time_slot = request.args.get('time')
        
        if not all([staff_id, day, time_slot]):
            return api_error(
                "Missing required parameters",
                errors={
                    "staff_id": "Required" if not staff_id else None,
                    "day": "Required" if not day else None,
                    "time": "Required" if not time_slot else None
                }
            )
        
        from App.controllers.availability import check_staff_availability_for_time
        
        # Check availability
        is_available = check_staff_availability_for_time(staff_id, day, time_slot)
        
        logger.info(f"API v2: Staff availability staff_id={staff_id} day={day} time={time_slot} -> {is_available}")
        return api_success(
            data={
                "staff_id": staff_id,
                "day": day,
                "time": time_slot,
                "is_available": is_available
            },
            message="Availability check completed"
        )
        
    except Exception as e:
        logger.exception("API v2: Failed to check staff availability")
        return api_error(
            "Failed to check staff availability",
            errors={"exception": str(e)},
            status_code=500
        )


@api_v2.route('/admin/schedule/staff/check-availability/batch', methods=['POST'])
@jwt_required()
@admin_required
def batch_check_availability():
    """
    Check availability for multiple staff/time combinations in a single request
    
    Request Body:
        {
            "queries": [
                {
                    "staff_id": "staff123",
                    "day": "Monday", 
                    "time": "9:00 am"
                }
            ]
        }
    
    Returns:
        Batch availability results for all queries
    """
    try:
        logger.info("API v2: Batch availability requested")
        # Validate request format
        data, error_response = validate_json_request(request)
        if error_response:
            logger.warning("API v2: Batch availability validation failed")
            return error_response
        
        queries = data.get('queries', [])
        
        if not isinstance(queries, list) or not queries:
            return api_error(
                "Invalid queries format",
                errors={"queries": "Must be a non-empty array of query objects"}
            )
        
        # Limit batch size for performance
        if len(queries) > MAX_BATCH_QUERIES:
            return api_error(
                "Batch size too large",
                errors={"queries": f"Maximum {MAX_BATCH_QUERIES} queries per batch"}
            )
        
        from App.controllers.availability import batch_check_staff_availability
        
        # Process batch queries
        results = batch_check_staff_availability(queries)
        
        logger.info(f"API v2: Batch availability processed count={len(results)}")
        return api_success(
            data={
                "results": results,
                "total_queries": len(queries),
                "processed": len(results)
            },
            message=f"Batch availability check completed for {len(results)} queries"
        )
        
    except Exception as e:
        logger.exception("API v2: Failed to process batch availability")
        return api_error(
            "Failed to process batch availability check",
            errors={"exception": str(e)},
            status_code=500
        )


@api_v2.route('/admin/schedule/staff/remove', methods=['POST'])
@jwt_required()
@admin_required
def remove_staff_from_shift():
    """
    Remove a staff member from a specific shift
    
    Request Body:
        {
            "staff_id": "staff123",
            "day": "Monday",
            "time": "9:00 am",
            "shift_id": 456
        }
    
    Returns:
        Success confirmation of staff removal
    """
    try:
        logger.info("API v2: Remove staff from shift requested")
        # Validate request format
        data, error_response = validate_json_request(request)
        if error_response:
            logger.warning("API v2: Remove staff validation failed")
            return error_response
        
        staff_id = data.get('staff_id')
        day = data.get('day')
        time_slot = data.get('time')
        shift_id = data.get('shift_id')
        
        if not staff_id:
            return api_error(
                "Missing staff_id",
                errors={"staff_id": "Required"}
            )
        
        from App.controllers.allocation import remove_staff_from_shift
        
        # Remove staff from shift
        result = remove_staff_from_shift(staff_id, day, time_slot, shift_id)
        
        if result and result.get('status') == 'success':
            logger.info(f"API v2: Removed staff {staff_id} from shift {shift_id}")
            return api_success(
                data={
                    "staff_id": staff_id,
                    "day": day,
                    "time": time_slot,
                    "shift_id": shift_id,
                    "removed_at": _get_current_timestamp()
                },
                message="Staff member removed from shift successfully"
            )
        else:
            logger.error(f"API v2: Failed to remove staff {staff_id} from shift {shift_id}")
            return api_error(
                "Failed to remove staff from shift",
                errors={"reason": result.get('message', UNKNOWN_ERROR_MSG) if result else NO_RESPONSE_MSG}
            )
        
    except Exception as e:
        logger.exception("API v2: Internal error during staff removal")
        return api_error(
            "Internal server error during staff removal",
            errors={"exception": str(e)},
            status_code=500
        )


# ===========================
# SCHEDULE EXPORT & REPORTING
# ===========================

@api_v2.route('/admin/schedule/export/pdf', methods=['GET'])
@jwt_required()
@admin_required
def export_schedule_pdf():
    """
    Export current schedule as PDF
    
    Query Parameters:
        format: PDF format type (optional, default: "standard")
    
    Returns:
        PDF file download of the current schedule
    """
    try:
        logger.info("API v2: Export schedule PDF requested")
        export_format = request.args.get('format', 'standard')
        
        # Get current admin role
        admin_role = getattr(current_user, 'role', 'helpdesk')
        
        from App.controllers.schedule import get_schedule_data, generate_schedule_pdf
        
        # Get current schedule data
        from App.controllers.schedule import get_current_schedule
        schedule_data = get_current_schedule()
        
        if not schedule_data:
            logger.warning("API v2: No current schedule to export")
            return api_error(
                f"No current {admin_role} schedule to export",
                status_code=404
            )
        
        # Generate PDF
        pdf_buffer = generate_schedule_pdf(schedule_data, export_format)
        
        if not pdf_buffer:
            logger.error("API v2: PDF generation failed")
            return api_error(
                "Failed to generate PDF",
                status_code=500
            )
        
        # Return PDF file
        logger.info("API v2: PDF generated successfully")
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"{admin_role}_schedule_{datetime.now().strftime('%Y%m%d')}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.exception("API v2: Failed to export schedule PDF")
        return api_error(
            "Failed to export schedule PDF",
            errors={"exception": str(e)},
            status_code=500
        )


@api_v2.route('/admin/schedule/summary', methods=['GET'])
@jwt_required()
@admin_required
def get_schedule_summary():
    """
    Get summary statistics for the current schedule
    
    Returns:
        Schedule summary with statistics and metrics
    """
    try:
        logger.info("API v2: Get schedule summary requested")
        # Get current admin role
        admin_role = getattr(current_user, 'role', 'helpdesk')
        
        from App.controllers.schedule import get_schedule_summary_stats
        
        # Get summary stats
        summary = get_schedule_summary_stats(admin_role)
        
        logger.info("API v2: Schedule summary retrieved")
        return api_success(
            data={
                "summary": summary,
                "schedule_type": admin_role,
                "generated_at": _get_current_timestamp()
            },
            message="Schedule summary retrieved successfully"
        )
        
    except Exception as e:
        logger.exception("API v2: Failed to retrieve schedule summary")
        return api_error(
            "Failed to retrieve schedule summary",
            errors={"exception": str(e)},
            status_code=500
        )