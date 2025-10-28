"""
Schedule controller with improved MVC separation.

This controller provides a clean interface between the view layer and the
business logic services, following proper MVC patterns.
"""

from datetime import datetime, timedelta, date, time
from functools import lru_cache
from flask import jsonify, render_template
import logging
from typing import Dict, Any, Optional, List, Tuple, Union

from App.models import (
    Schedule, Shift, Student, HelpDeskAssistant, 
    CourseCapability, Availability, 
    Allocation, Course
)
from App.database import db
from App.controllers.course import get_all_courses
from App.controllers.lab_assistant import get_active_lab_assistants
from App.controllers.notification import notify_schedule_published
from App.controllers.shift import create_shift
from App.utils.time_utils import trinidad_now
from App.utils.performance_monitor import (
    performance_monitor, 
    database_transaction_context,
    structured_logger
)
from App.services import SchedulingService

logger = logging.getLogger(__name__)

# Initialize the scheduling service
scheduling_service = SchedulingService()


def _to_datetime_start_of_day(d):
    """Normalize a date or datetime (or ISO string) to a datetime at 00:00:00."""
    if isinstance(d, datetime):
        return d.replace(hour=0, minute=0, second=0, microsecond=0)
    if isinstance(d, date):
        return datetime(d.year, d.month, d.day)
    if isinstance(d, str):
        try:
            parsed = datetime.fromisoformat(d)
            return parsed.replace(hour=0, minute=0, second=0, microsecond=0)
        except Exception:
            return trinidad_now().replace(hour=0, minute=0, second=0, microsecond=0)
    return trinidad_now().replace(hour=0, minute=0, second=0, microsecond=0)


def get_published_schedules():
    """Return all published schedules ordered by end_date descending."""
    try:
        return Schedule.query.filter_by(is_published=True).order_by(Schedule.end_date.desc()).all()
    except Exception as e:
        logger.error(f"Error fetching published schedules: {e}")
        return []


def get_current_published_schedule(today=None):
    """Return the schedule that is currently in effect (today within range)."""
    try:
        if today is None:
            today = trinidad_now().date()
        
        current = (
            Schedule.query
            .filter(
                Schedule.is_published == True,
                Schedule.start_date <= today,
                Schedule.end_date >= today
            )
            .order_by(Schedule.end_date.desc())
            .first()
        )
        if current:
            return current
        # Fallback: latest published schedule
        return (
            Schedule.query
            .filter_by(is_published=True)
            .order_by(Schedule.end_date.desc())
            .first()
        )
    except Exception as e:
        logger.error(f"Error fetching current published schedule: {e}")
        return None


def get_shifts_for_student(username, limit=None):
    """Get upcoming shifts for a specific student."""
    try:
        now = trinidad_now()
        
        query = (
            db.session.query(Shift)
            .join(Allocation, Allocation.shift_id == Shift.id)
            .filter(
                Allocation.username == username,
                Shift.date >= now.date()
            )
            .order_by(Shift.date, Shift.start_time)
        )
        
        if limit:
            query = query.limit(limit)
            
        return query.all()
    except Exception as e:
        logger.error(f"Error fetching shifts for student {username}: {e}")
        return []


def get_shifts_for_student_in_range(username, start_date, end_date):
    """Get shifts for a student within a specific date range."""
    try:
        # Parse date strings if needed
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date).date()
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date).date()
        
        shifts = (
            db.session.query(Shift)
            .join(Allocation, Allocation.shift_id == Shift.id)
            .filter(
                Allocation.username == username,
                Shift.date >= start_date,
                Shift.date <= end_date
            )
            .order_by(Shift.date, Shift.start_time)
            .all()
        )
        
        return shifts
    except Exception as e:
        logger.error(f"Error fetching shifts for student {username} in range {start_date}-{end_date}: {e}")
        return []


def check_scheduling_feasibility(schedule_type: str = 'helpdesk'):
    """
    Check if scheduling is feasible with current constraints.
    
    Args:
        schedule_type: Type of schedule ('helpdesk' or 'lab')
    
    Returns:
        Dictionary with feasibility information
    """
    return scheduling_service.check_scheduling_feasibility(schedule_type)


@performance_monitor("generate_help_desk_schedule", log_slow_threshold=2.0)
def generate_help_desk_schedule(start_date=None, end_date=None, **generation_options):
    """
    Generate a help desk schedule using PuLP optimization.
    
    This function now delegates to the SchedulingService for the actual
    business logic, maintaining a clean separation of concerns.
    """
    with database_transaction_context("help_desk_schedule_generation"):
        # Normalize inputs
        if start_date is not None:
            start_date = _to_datetime_start_of_day(start_date)
        if end_date is not None:
            end_date = _to_datetime_start_of_day(end_date)

        # Check feasibility first
        feasibility = check_scheduling_feasibility('helpdesk')
        if not feasibility["feasible"]:
            logger.warning(f"Schedule generation may fail: {feasibility['message']}")

        structured_logger.info(
            "Starting help desk schedule generation via PuLP",
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None,
            generation_options=generation_options
        )

        # Delegate to the scheduling service
        result = scheduling_service.generate_helpdesk_schedule(
            start_date=start_date,
            end_date=end_date,
            **generation_options
        )

        return result


def generate_lab_schedule(start_date=None, end_date=None, **generation_options):
    """
    Generate a lab schedule using PuLP optimization.
    
    This function delegates to the SchedulingService for the actual
    business logic, maintaining a clean separation of concerns.
    """
    with database_transaction_context("lab_schedule_generation"):
        # Normalize inputs
        if start_date is not None:
            start_date = _to_datetime_start_of_day(start_date)
        if end_date is not None:
            end_date = _to_datetime_start_of_day(end_date)

        # Check feasibility first
        feasibility = check_scheduling_feasibility('lab')
        if not feasibility["feasible"]:
            logger.warning(f"Lab schedule generation may fail: {feasibility['message']}")

        structured_logger.info(
            "Starting lab schedule generation via PuLP",
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None,
            generation_options=generation_options
        )

        # Delegate to the scheduling service
        result = scheduling_service.generate_lab_schedule(
            start_date=start_date,
            end_date=end_date,
            **generation_options
        )

        return result


def get_schedule(start_date, end_date, type='helpdesk'):
    """Get or create the main schedule object based on type"""
    schedule_id = 1 if type == 'helpdesk' else 2
    
    schedule = Schedule.query.filter_by(id=schedule_id, type=type).first()
    
    if not schedule:
        schedule = create_schedule(schedule_id, start_date, end_date, type)
    else:
        schedule.start_date = start_date
        schedule.end_date = end_date
        db.session.add(schedule)
        db.session.flush()
    return schedule


def create_schedule(id, start_date, end_date, type):
    """Create a new schedule."""
    new_schedule = Schedule(id=id, start_date=start_date, end_date=end_date, type=type)
    db.session.add(new_schedule)
    db.session.commit()
    return new_schedule


def clear_shifts_in_range(schedule_id, start_date, end_date):
    """Clear existing shifts in the date range"""
    from sqlalchemy import text
    
    # Find shifts in this date range
    shifts_to_delete = Shift.query.filter(
        Shift.schedule_id == schedule_id,
        Shift.date >= start_date,
        Shift.date <= end_date
    ).all()
    
    # Delete allocations for these shifts
    for shift in shifts_to_delete:
        Allocation.query.filter_by(shift_id=shift.id).delete()
        
        # Delete course demands for these shifts using text() for SQL
        db.session.execute(
            text("DELETE FROM shift_course_demand WHERE shift_id = :shift_id"),
            {'shift_id': shift.id}
        )
    
    # Now delete the shifts themselves
    for shift in shifts_to_delete:
        db.session.delete(shift)
    
    db.session.flush()


def clear_allocations_for_shifts(shifts):
    """Clear allocations for the given shifts"""
    for shift in shifts:
        Allocation.query.filter_by(shift_id=shift.id).delete()
    
    db.session.flush()


def add_course_demand_to_shift(shift_id, course_code, tutors_required=2, weight=None):
    """Add course demand for a shift using raw SQL with text()"""
    from sqlalchemy import text
    
    if weight is None:
        weight = tutors_required
    
    db.session.execute(
        text("INSERT INTO shift_course_demand (shift_id, course_code, tutors_required, weight) VALUES (:shift_id, :course_code, :tutors_required, :weight)"),
        {
            'shift_id': shift_id, 
            'course_code': course_code, 
            'tutors_required': tutors_required, 
            'weight': weight
        }
    )
    db.session.flush()


def get_course_demands_for_shift(shift_id):
    """Get course demands for a specific shift."""
    from sqlalchemy import text
    
    try:
        result = db.session.execute(
            text("SELECT course_code, tutors_required, weight FROM shift_course_demand WHERE shift_id = :shift_id"),
            {'shift_id': shift_id}
        )
        
        demands = []
        for row in result:
            demands.append({
                'course_code': row[0],
                'tutors_required': row[1],
                'weight': row[2]
            })
        
        return demands
    except Exception as e:
        logger.error(f"Error getting course demands for shift {shift_id}: {e}")
        return []


def sync_schedule_data():
    """Sync schedule data between different views."""
    try:
        schedule = Schedule.query.get(1)
        
        if not schedule:
            logger.info("No main schedule exists yet")
            return False
        
        shifts = Shift.query.filter_by(schedule_id=schedule.id).all()
        
        if not shifts:
            logger.info("Schedule exists but has no shifts")
            return False
        
        shift_ids = [shift.id for shift in shifts]
        allocations = Allocation.query.filter(Allocation.shift_id.in_(shift_ids)).all()
        
        logger.info(f"Schedule {schedule.id} has {len(shifts)} shifts and {len(allocations)} allocations")
        
        allocation_counts = {}
        for allocation in allocations:
            allocation_counts[allocation.shift_id] = allocation_counts.get(allocation.shift_id, 0) + 1
        
        shifts_without_allocations = [shift.id for shift in shifts if allocation_counts.get(shift.id, 0) == 0]
        if shifts_without_allocations:
            logger.warning(f"Found {len(shifts_without_allocations)} shifts without allocations")
        
        for allocation in allocations:
            student = Student.query.get(allocation.username)
            if not student:
                logger.warning(f"Allocation {allocation.id} references non-existent student {allocation.username}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error syncing schedule data: {e}")
        return False


def publish_and_notify(schedule_id):
    """Publish schedule and send notifications."""
    try:
        result = publish_schedule(schedule_id)
        
        if result.get('status') != 'success':
            return result
            
        sync_success = sync_schedule_data()
        
        if not sync_success:
            logger.warning("Schedule published but data sync failed or was not necessary")
        
        return {
            "status": "success",
            "message": "Schedule published and notifications sent",
            "sync_status": "success" if sync_success else "warning"
        }
            
    except Exception as e:
        logger.error(f"Error publishing and notifying: {e}")
        return {
            "status": "error", 
            "message": f"Error: {str(e)}"
        }


def publish_schedule(schedule_id):
    """Publish a schedule and notify all assigned staff"""
    try:
        schedule = Schedule.query.get(schedule_id)
        if not schedule:
            return {"status": "error", "message": _ERROR_SCHEDULE_NOT_FOUND}
            
        if schedule.publish():
            allocations = Allocation.query.filter_by(schedule_id=schedule_id).all()
            students = {allocation.username for allocation in allocations}
            
            for username in students:
                notify_schedule_published(username)
                
            return {"status": "success", "message": "Schedule published and notifications sent"}
        else:
            return {"status": "error", "message": "Schedule is already published"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_assistants_for_shift(shift_id):
    """Get all assistants assigned to a specific shift"""
    allocations = Allocation.query.filter_by(shift_id=shift_id).all()
    assistants = []
    
    for allocation in allocations:
        student = Student.query.get(allocation.username)
        if student:
            assistants.append({
                "username": student.username,
                "name": student.get_name(),
                "degree": student.degree
            })
    
    return assistants


def clear_schedule_by_id(schedule_id):
    """Clear a specific schedule by ID."""
    from sqlalchemy import text
    
    try:
        schedule = Schedule.query.get(schedule_id)
        
        if not schedule:
            return {
                "status": "success",
                "message": f"No schedule exists with ID {schedule_id} to clear"
            }
        
        # Delete allocations first
        allocation_count = Allocation.query.filter_by(schedule_id=schedule_id).delete()
        
        # Get shift IDs and delete course demands
        shifts = Shift.query.filter_by(schedule_id=schedule_id).all()
        shift_ids = [shift.id for shift in shifts]
        shift_count = len(shifts)
        
        if shift_ids:
            shift_ids_str = ','.join(str(id) for id in shift_ids)
            db.session.execute(
                text(f"DELETE FROM shift_course_demand WHERE shift_id IN ({shift_ids_str})")
            )
        
        # Delete shifts
        Shift.query.filter_by(schedule_id=schedule_id).delete()
        
        # Reset published status
        schedule.is_published = False
        db.session.add(schedule)
        
        db.session.commit()
        db.session.expire_all()
        
        logger.info(f"Schedule {schedule_id} cleared successfully: {shift_count} shifts and {allocation_count} allocations removed")
        
        return {
            "status": "success",
            "message": "Schedule cleared successfully",
            "details": {
                "schedule_id": schedule_id,
                "shifts_removed": shift_count,
                "allocations_removed": allocation_count
            }
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing schedule: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


def clear_schedule():
    """Clear the main schedule (ID=1)."""
    return clear_schedule_by_id(1)


@performance_monitor("get_schedule_data")
def get_schedule_data(schedule_id):
    """schedule data retrieval with eager loading."""
    try:
        from sqlalchemy.orm import selectinload
        
        # Single query with eager loading
        schedule = (
            db.session.query(Schedule)
            .options(
                selectinload(Schedule.shifts)
                .selectinload(Shift.allocations)
                .selectinload(Allocation.student)
            )
            .filter_by(id=schedule_id)
            .first()
        )
        
        if not schedule:
            logger.error(f"No schedule found with ID {schedule_id}")
            return None
            
        # Determine schedule type
        schedule_type = getattr(schedule, 'type', 'helpdesk')
        if schedule_id == 2:
            schedule_type = 'lab'
        
        logger.info(f"Loaded schedule {schedule_id} with {len(schedule.shifts)} shifts using eager loading")
        
        # Format the schedule
        formatted_schedule = {
            "schedule_id": schedule.id,
            "date_range": f"{schedule.start_date.strftime('%d %b')} - {schedule.end_date.strftime('%d %b, %Y')}",
            "is_published": schedule.is_published,
            "type": schedule_type,
            "days": []
        }
        
        # Group shifts by day
        shifts_by_day = {}
        for shift in schedule.shifts:
            day_idx = shift.date.weekday()
            
            # Skip days outside expected range
            if schedule_type == 'helpdesk' and day_idx > 4:
                continue
            if schedule_type == 'lab' and day_idx > 5:
                continue
                
            if day_idx not in shifts_by_day:
                shifts_by_day[day_idx] = []
                
            # Build assistants list from pre-loaded data
            assistants = []
            for allocation in shift.allocations:
                if allocation.student:
                    assistants.append({
                        "id": allocation.student.username,
                        "name": allocation.student.get_name()
                    })
            
            shifts_by_day[day_idx].append({
                "shift_id": shift.id,
                "time": f"{shift.start_time.strftime('%-I:%M %p')} - {shift.end_time.strftime('%-I:%M %p')}",
                "hour": shift.start_time.hour,
                "assistants": assistants
            })
        
        # Create days array
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        max_days = 6 if schedule_type == 'lab' else 5
        
        for day_idx in range(max_days):
            if day_idx >= len(day_names):
                continue
                
            day_date = schedule.start_date + timedelta(days=day_idx)
            day_shifts = shifts_by_day.get(day_idx, [])
            
            # Sort shifts by start time
            day_shifts.sort(key=lambda x: x["hour"])
            
            formatted_schedule["days"].append({
                "day": day_names[day_idx],
                "date": day_date.strftime("%d %b"),
                "shifts": day_shifts
            })
        
        logger.info(f"Successfully formatted schedule data for {len(formatted_schedule['days'])} days")
        return formatted_schedule
        
    except Exception as e:
        logger.error(f"Error getting schedule data: {e}")
        import traceback
        traceback.print_exc()
        return None


@performance_monitor("get_current_schedule")
def get_current_schedule():
    """Get the current schedule with all shifts"""
    try:
        from sqlalchemy.orm import selectinload
        
        schedule = (
            db.session.query(Schedule)
            .options(
                selectinload(Schedule.shifts)
                .selectinload(Shift.allocations)
                .selectinload(Allocation.student)
            )
            .filter_by(id=1)
            .first()
        )
        
        if not schedule:
            logger.info("No schedule found - returning empty template")
            return {
                "schedule_id": None,
                "date_range": "No schedule available",
                "is_published": False,
                "days": [
                    {
                        "day": day,
                        "date": "",
                        "shifts": [
                            {
                                "shift_id": None,
                                "time": f"{hour}:00 - {hour+1}:00",
                                "assistants": []
                            } for hour in range(9, 17)
                        ]
                    } for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                ]
            }
            
        logger.info(f"Loaded schedule {schedule.id} with {len(schedule.shifts)} shifts using eager loading")
            
        # Format the schedule for display using pre-loaded data
        shifts_by_day = {}
        
        for shift in schedule.shifts:
            day_idx = shift.date.weekday()
            if day_idx >= 5:  # Skip weekend shifts
                continue
                
            hour = shift.start_time.hour
            
            if day_idx not in shifts_by_day:
                shifts_by_day[day_idx] = {}
                
            assistants = []
            for allocation in shift.allocations:
                if allocation.student:
                    assistants.append({
                        "id": allocation.student.username,
                        "name": allocation.student.get_name(),
                        "degree": getattr(allocation.student, 'degree', 'N/A')
                    })
                
            shifts_by_day[day_idx][hour] = {
                "shift_id": shift.id,
                "time": shift.formatted_time(),
                "assistants": assistants
            }
        
        # Format into days array with shifts
        days = []
        for day_idx in range(5):  # Monday to Friday
            day_date = schedule.start_date + timedelta(days=day_idx) if schedule.start_date else trinidad_now()
            day_shifts = []
            
            if day_idx in shifts_by_day:
                for hour in range(9, 17):  # 9am to 4pm
                    if hour in shifts_by_day[day_idx]:
                        day_shifts.append(shifts_by_day[day_idx][hour])
                    else:
                        day_shifts.append({
                            "shift_id": None,
                            "time": f"{hour}:00 - {hour+1}:00",
                            "assistants": []
                        })
            
            days.append({
                "day": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"][day_idx],
                "date": day_date.strftime("%d %b"),
                "shifts": day_shifts
            })
        
        result = {
            "schedule_id": schedule.id,
            "date_range": f"{schedule.start_date.strftime('%d %b')} - {schedule.end_date.strftime('%d %b, %Y')}" if schedule.start_date and schedule.end_date else "Current Schedule",
            "is_published": schedule.is_published,
            "days": days
        }
        
        logger.info(f"Successfully formatted current schedule with {len(days)} days")
        return result
        
    except Exception as e:
        logger.error(f"Error getting current schedule: {e}")
        import traceback
        traceback.print_exc()
        return {
            "schedule_id": None,
            "date_range": "Error loading schedule",
            "is_published": False,
            "days": [
                {
                    "day": day,
                    "date": "",
                    "shifts": [
                        {
                            "shift_id": None,
                            "time": f"{hour}:00 - {hour+1}:00",
                            "assistants": []
                        } for hour in range(9, 17)
                    ]
                } for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            ]
        }


def generate_schedule_pdf(schedule_data, export_format='standard'):
    """
    Generate PDF from schedule data
    
    Args:
        schedule_data: Schedule data dictionary
        export_format: PDF format type
    
    Returns:
        BytesIO buffer containing PDF data
    """
    try:
        from io import BytesIO
        from weasyprint import HTML, CSS
        from flask import render_template_string
        
        if not schedule_data:
            logger.error("No schedule data provided for PDF generation")
            return None
            
        # Determine schedule type from data or default to helpdesk
        schedule_type = schedule_data.get('type', 'helpdesk')
        schedule_id = schedule_data.get('schedule_id', 'N/A')
        date_range = schedule_data.get('date_range', 'Unknown Date Range')
        
        # Create HTML template for PDF
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{{ schedule_type|title }} Schedule - {{ date_range }}</title>
            <style>
                @page {
                    size: A4 landscape;
                    margin: 1cm;
                }
                body {
                    font-family: Arial, sans-serif;
                    font-size: 10pt;
                }
                .header {
                    text-align: center;
                    margin-bottom: 20px;
                    border-bottom: 2px solid #333;
                    padding-bottom: 10px;
                }
                .schedule-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 20px;
                }
                .schedule-table th, .schedule-table td {
                    border: 1px solid #ccc;
                    padding: 8px;
                    text-align: center;
                    vertical-align: top;
                }
                .schedule-table th {
                    background-color: #f5f5f5;
                    font-weight: bold;
                }
                .day-header {
                    background-color: #e8e8e8;
                    font-weight: bold;
                }
                .time-slot {
                    font-weight: bold;
                    background-color: #f9f9f9;
                }
                .staff-name {
                    display: block;
                    margin: 2px 0;
                    padding: 2px 4px;
                    background-color: #e3f2fd;
                    border-radius: 3px;
                    font-size: 9pt;
                }
                .no-staff {
                    color: #999;
                    font-style: italic;
                }
                .footer {
                    margin-top: 20px;
                    font-size: 8pt;
                    color: #666;
                    text-align: center;
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{{ schedule_type|title }} Schedule</h1>
                <h2>{{ date_range }}</h2>
                {% if schedule_id %}
                <p>Schedule ID: {{ schedule_id }}</p>
                {% endif %}
            </div>
            
            <table class="schedule-table">
                <thead>
                    <tr>
                        <th>Time</th>
                        {% for day in days %}
                        <th class="day-header">{{ day.day }}<br>{{ day.date }}</th>
                        {% endfor %}
                    </tr>
                </thead>
                <tbody>
                    {% set time_slots = [] %}
                    {% if days %}
                        {% for shift in days[0].shifts %}
                            {% set _ = time_slots.append(shift.time) %}
                        {% endfor %}
                    {% endif %}
                    
                    {% for time_slot in time_slots %}
                    <tr>
                        <td class="time-slot">{{ time_slot }}</td>
                        {% for day in days %}
                            {% set shift = day.shifts[loop.index0] if loop.index0 < day.shifts|length else None %}
                            <td>
                                {% if shift and shift.assistants %}
                                    {% for assistant in shift.assistants %}
                                    <span class="staff-name">{{ assistant.name or assistant.id }}</span>
                                    {% endfor %}
                                {% else %}
                                    <span class="no-staff">No staff assigned</span>
                                {% endif %}
                            </td>
                        {% endfor %}
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            
            <div class="footer">
                <p>Generated on {{ current_time }} | Schedule Type: {{ schedule_type|title }}</p>
                <p>Total Days: {{ days|length }} | Export Format: {{ export_format }}</p>
            </div>
        </body>
        </html>
        """
        
        # Get days data or create empty structure
        days = schedule_data.get('days', [])
        
        # Add current timestamp
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Render HTML with schedule data
        html_content = render_template_string(
            html_template,
            schedule_type=schedule_type,
            schedule_id=schedule_id,
            date_range=date_range,
            days=days,
            current_time=current_time,
            export_format=export_format
        )
        
        # Generate PDF from HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
        
        # Create BytesIO buffer and write PDF data
        pdf_buffer = BytesIO()
        pdf_buffer.write(pdf_bytes)
        pdf_buffer.seek(0)  # Reset pointer to beginning
        
        logger.info(f"Successfully generated PDF for {schedule_type} schedule (format: {export_format})")
        return pdf_buffer
        
    except Exception as e:
        logger.error(f"Error generating schedule PDF: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_schedule_summary_stats(schedule_type):
    """
    Get summary statistics for a schedule type
    
    Args:
        schedule_type: Type of schedule ('helpdesk' or 'lab')
    
    Returns:
        Dictionary with summary statistics
    """
    try:
        # Get schedule for the type
        schedule_id = 1 if schedule_type == 'helpdesk' else 2
        schedule = Schedule.query.filter_by(id=schedule_id, type=schedule_type).first()
        
        if not schedule:
            return {
                'total_shifts': 0,
                'assigned_shifts': 0,
                'unassigned_shifts': 0,
                'total_staff_assignments': 0,
                'coverage_percentage': 0.0
            }
        
        # Get shift counts
        total_shifts = Shift.query.filter_by(schedule_id=schedule.id).count()
        
        # Get assignment counts
        total_assignments = db.session.query(Allocation).join(Shift).filter(
            Shift.schedule_id == schedule.id
        ).count()
        
        # Calculate assigned shifts (shifts with at least one assignment)
        assigned_shifts = db.session.query(Shift.id).join(Allocation).filter(
            Shift.schedule_id == schedule.id
        ).distinct().count()
        
        unassigned_shifts = total_shifts - assigned_shifts
        coverage_percentage = (assigned_shifts / total_shifts * 100) if total_shifts > 0 else 0.0
        
        return {
            'total_shifts': total_shifts,
            'assigned_shifts': assigned_shifts,
            'unassigned_shifts': unassigned_shifts,
            'total_staff_assignments': total_assignments,
            'coverage_percentage': round(coverage_percentage, 2),
            'schedule_type': schedule_type,
            'schedule_id': schedule.id,
            'start_date': schedule.start_date.isoformat() if schedule.start_date else None,
            'end_date': schedule.end_date.isoformat() if schedule.end_date else None,
            'is_published': getattr(schedule, 'is_published', False)
        }
        
    except Exception as e:
        logger.error(f"Error getting schedule summary for {schedule_type}: {e}")
        return {
            'total_shifts': 0,
            'assigned_shifts': 0,
            'unassigned_shifts': 0,
            'total_staff_assignments': 0,
            'coverage_percentage': 0.0,
            'error': str(e)
        }


# Mapping helpers used by scheduling views
_DAY_CODE_MAP = {
    'MON': 0, 'TUE': 1, 'WED': 2, 'THUR': 3, 'THU': 3, 'FRI': 4, 'SAT': 5, 'SUN': 6,
    'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6
}

# Error constants
_ERROR_INVALID_DAY = 'Invalid day provided.'
_ERROR_INVALID_TIME = 'Invalid time slot provided.'
_ERROR_STAFF_NOT_FOUND = 'Staff member not found.'
_ERROR_SCHEDULE_NOT_FOUND = 'Schedule not found.'
_ERROR_SHIFT_NOT_FOUND = 'Shift not found.'


_LAB_SHIFT_CONFIG = [
    {'label': '8am - 12pm', 'start': 8, 'duration': 4},
    {'label': '12pm - 4pm', 'start': 12, 'duration': 4},
    {'label': '4pm - 8pm', 'start': 16, 'duration': 4}
]


def _schedule_id_for_type(schedule_type: str) -> int:
    return 1 if schedule_type == 'helpdesk' else 2


def _normalize_day_index(day_label: str) -> Optional[int]:
    if not day_label:
        return None
    if isinstance(day_label, str):
        normalized = _DAY_CODE_MAP.get(day_label)
        if normalized is not None:
            return normalized
        return _DAY_CODE_MAP.get(day_label.upper())
    return None


def _parse_time_to_hour(time_str: str, schedule_type: str) -> Optional[int]:
    """
    Parse time string to hour with comprehensive error handling.
    Supports various time formats and handles edge cases.
    """
    if not time_str:
        return None
    
    try:
        # Handle numeric input
        if isinstance(time_str, (int, float)):
            hour = int(time_str)
            return hour if 0 <= hour <= 23 else None
        
        # Convert to string and normalize
        time_str = str(time_str).strip()
        if not time_str:
            return None
        
        # Handle range formats (take start time)
        if '-' in time_str:
            time_str = time_str.split('-')[0].strip()
        
        # Handle colon format (extract hour)
        if ':' in time_str:
            hour_part = time_str.split(':')[0].strip()
            try:
                hour = int(hour_part)
            except ValueError:
                return None
        else:
            # Try to extract hour from string
            time_str_lower = time_str.lower()
            # Remove am/pm for processing
            clean_time = time_str_lower.replace('am', '').replace('pm', '').strip()
            try:
                hour = int(clean_time)
            except ValueError:
                return None
        
        # Handle PM conversion (but not for 12pm which is noon)
        if 'pm' in time_str.lower() and hour != 12:
            hour += 12
        elif 'am' in time_str.lower() and hour == 12:
            hour = 0  # 12am is midnight (00:00)
        
        # Special handling for lab schedule blocks
        if schedule_type == 'lab':
            time_str_lower = time_str.lower()
            lab_mapping = {
                '8:00 am - 12:00 pm': 8,
                '8am - 12pm': 8,
                '8 - 12': 8,
                '12:00 pm - 4:00 pm': 12,
                '12pm - 4pm': 12,
                '12 - 4': 12,
                '4:00 pm - 8:00 pm': 16,
                '4pm - 8pm': 16,
                '16 - 20': 16,
                '4 - 8': 16
            }
            if time_str_lower in lab_mapping:
                return lab_mapping[time_str_lower]
        
        # Validate hour range
        return hour if 0 <= hour <= 23 else None
        
    except (ValueError, TypeError, AttributeError) as e:
        logger.warning(f"Invalid time format encountered: '{time_str}' - {e}")
        return None


def _calculate_shift_end(schedule_type: str, start_hour: int) -> int:
    if schedule_type == 'lab':
        for slot in _LAB_SHIFT_CONFIG:
            if slot['start'] == start_hour:
                return start_hour + slot.get('duration', 4)
        return start_hour + 4
    return start_hour + 1


def save_schedule_assignments(schedule_type: str, start_date_str: str, end_date_str: str, assignments: list[dict[str, Any]]):
    try:
        if not start_date_str or not end_date_str:
            return {'status': 'error', 'message': 'Start and end dates are required.'}, 400

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            return {'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD.'}, 400

        schedule_id = _schedule_id_for_type(schedule_type)
        schedule = Schedule.query.filter_by(id=schedule_id, type=schedule_type).first()

        if not schedule:
            schedule = Schedule(schedule_id, start_date, end_date, schedule_type)
            db.session.add(schedule)
        else:
            schedule.start_date = start_date
            schedule.end_date = end_date

        db.session.flush()

        # Clear existing allocations for shifts in the date window
        existing_shifts = Shift.query.filter(
            Shift.schedule_id == schedule.id,
            Shift.date >= start_date,
            Shift.date <= end_date
        ).all()

        for shift in existing_shifts:
            Allocation.query.filter_by(shift_id=shift.id).delete()

        for entry in assignments:
            day_label = entry.get('day')
            time_slot = entry.get('time')
            staff_members = entry.get('staff', [])

            day_index = _normalize_day_index(day_label)
            if day_index is None:
                logger.warning(f"Skipping assignment with invalid day label: {day_label}")
                continue

            shift_date = start_date + timedelta(days=day_index)
            start_hour = _parse_time_to_hour(time_slot, schedule_type)
            if start_hour is None:
                logger.warning(f"Skipping assignment with invalid time slot: {time_slot}")
                continue

            shift_start = datetime.combine(shift_date.date(), datetime.min.time()) + timedelta(hours=start_hour)
            shift_end_hour = _calculate_shift_end(schedule_type, start_hour)
            shift_end = datetime.combine(shift_date.date(), datetime.min.time()) + timedelta(hours=shift_end_hour)

            shift = Shift.query.filter_by(
                schedule_id=schedule.id,
                date=shift_date,
                start_time=shift_start
            ).first()

            if not shift:
                shift = Shift(shift_date, shift_start, shift_end, schedule.id)
                db.session.add(shift)
                db.session.flush()
            else:
                shift.end_time = shift_end

            for staff in staff_members:
                staff_id = staff.get('id')
                if not staff_id:
                    continue
                student = Student.query.filter_by(username=staff_id).first()
                if not student:
                    logger.warning(f"Skipping allocation for missing student id {staff_id}")
                    continue
                existing_allocation = Allocation.query.filter_by(shift_id=shift.id, username=student.username).first()
                if existing_allocation:
                    continue
                db.session.add(Allocation(student.username, shift.id, schedule.id))

        db.session.commit()
        return {'status': 'success', 'message': 'Schedule assignments saved successfully.'}, 200

    except Exception as exc:
        logger.error(f"Error saving schedule assignments: {exc}")
        db.session.rollback()
        return {'status': 'error', 'message': str(exc)}, 500


def remove_staff_allocation(schedule_type: str, staff_id: Union[str, int], day_label: str, time_slot: str, shift_id: Optional[int] = None):
    try:
        if not staff_id:
            return {'status': 'error', 'message': 'Staff identifier is required.'}, 400

        schedule_id = _schedule_id_for_type(schedule_type)
        schedule = Schedule.query.filter_by(id=schedule_id, type=schedule_type).first()
        if not schedule:
            return {'status': 'error', 'message': _ERROR_SCHEDULE_NOT_FOUND}, 404

        target_shift = None

        if shift_id:
            target_shift = Shift.query.filter_by(id=shift_id, schedule_id=schedule.id).first()
        else:
            day_index = _normalize_day_index(day_label)
            if day_index is None:
                return {'status': 'error', 'message': _ERROR_INVALID_DAY}, 400

            start_hour = _parse_time_to_hour(time_slot, schedule_type)
            if start_hour is None:
                return {'status': 'error', 'message': _ERROR_INVALID_TIME}, 400

            shift_date = schedule.start_date + timedelta(days=day_index)
            shift_start = datetime.combine(shift_date.date(), datetime.min.time()) + timedelta(hours=start_hour)

            target_shift = Shift.query.filter_by(
                schedule_id=schedule.id,
                date=shift_date,
                start_time=shift_start
            ).first()

        if not target_shift:
            return {'status': 'error', 'message': 'Shift not found.'}, 404

        allocation = Allocation.query.filter_by(shift_id=target_shift.id, username=staff_id).first()
        if not allocation:
            return {'status': 'error', 'message': 'Staff assignment not found for the specified shift.'}, 404

        db.session.delete(allocation)
        db.session.commit()
        return {'status': 'success', 'message': 'Staff removed from shift successfully.'}, 200

    except Exception as exc:
        logger.error(f"Error removing staff from shift: {exc}")
        db.session.rollback()
        return {'status': 'error', 'message': str(exc)}, 500


def _normalize_time_object(time_value, context_description="time value"):
    """
    Convert various time representations to datetime.time object.
    Handles time, datetime, and integer hour values.
    """
    from datetime import time as dt_time, datetime
    
    if isinstance(time_value, dt_time):
        return time_value
    elif isinstance(time_value, datetime):
        return time_value.time()
    elif isinstance(time_value, int):
        if 0 <= time_value <= 23:
            return dt_time(time_value, 0)
        else:
            raise ValueError(f"Invalid hour value: {time_value}")
    else:
        raise TypeError(f"Unexpected {context_description} type: {type(time_value)}")


def _check_time_slot_availability(availability_slots, requested_time):
    """
    Check if the requested time falls within any availability slot.
    Returns the matching slot if available, None otherwise.
    """
    for slot in availability_slots:
        try:
            avail_start_time = _normalize_time_object(slot.start_time, "availability start_time")
            avail_end_time = _normalize_time_object(slot.end_time, "availability end_time")
            
            if avail_start_time <= requested_time < avail_end_time:
                return slot
        except (TypeError, ValueError) as e:
            logger.warning(f"Skipping availability slot {slot.id}: {e}")
            continue
    
    return None


def list_available_staff_for_slot(schedule_type: str, day_label: str, time_slot: Union[str, int]):
    try:
        day_index = _normalize_day_index(day_label)
        if day_index is None:
            return {'status': 'error', 'message': _ERROR_INVALID_DAY}, 400

        hour = _parse_time_to_hour(time_slot, schedule_type)
        if hour is None:
            return {'status': 'error', 'message': _ERROR_INVALID_TIME}, 400

        # Convert hour to time object for proper comparison
        from datetime import time as dt_time
        requested_time = dt_time(hour, 0)
        
        available_staff = []

        assistants = HelpDeskAssistant.query.filter_by(active=True).all()
        for assistant in assistants:
            availability_slots = Availability.query.filter_by(username=assistant.username, day_of_week=day_index).all()

            if not availability_slots:
                continue

            # Use helper function to check availability
            matching_slot = _check_time_slot_availability(availability_slots, requested_time)
            if matching_slot:
                assistant_data = assistant.to_dict()
                assistant_data['availability'] = [
                    {'start_time': str(slot.start_time), 'end_time': str(slot.end_time)} 
                    for slot in availability_slots
                ]
                available_staff.append(assistant_data)

        return {'status': 'success', 'available_staff': available_staff}, 200

    except Exception as exc:
        logger.error(f"Error fetching available staff: {exc}")
        return {'status': 'error', 'message': str(exc)}, 500


def check_staff_availability_for_slot(schedule_type: str, staff_id: Union[str, int], day_label: str, time_slot: Union[str, int]):
    try:
        staff = HelpDeskAssistant.query.filter_by(username=staff_id).first()
        if not staff:
            return {'status': 'error', 'message': _ERROR_STAFF_NOT_FOUND}, 404

        day_index = _normalize_day_index(day_label)
        if day_index is None:
            return {'status': 'error', 'message': _ERROR_INVALID_DAY}, 400

        hour = _parse_time_to_hour(time_slot, schedule_type)
        if hour is None:
            return {'status': 'error', 'message': _ERROR_INVALID_TIME}, 400

        # Convert hour to time object for proper comparison
        from datetime import time as dt_time
        requested_time = dt_time(hour, 0)
        
        availability_slots = Availability.query.filter_by(username=staff.username, day_of_week=day_index).all()
        matching_slot = _check_time_slot_availability(availability_slots, requested_time)
        is_available = matching_slot is not None

        # Check for existing assignments using proper database queries
        schedule_id = _schedule_id_for_type(schedule_type)
        existing_assignment = db.session.query(Allocation).join(Shift).filter(
            Allocation.username == staff_id,
            Shift.schedule_id == schedule_id,
            db.extract('dow', Shift.date) == day_index,  # Use extract for day of week comparison
            db.extract('hour', Shift.start_time) == hour  # Use extract for hour comparison
        ).first()

        response = {
            'status': 'success',
            'is_available': is_available,
            'availability': {
                'day': day_label,
                'time': time_slot,
                'matches_slot': is_available
            },
            'existing_assignment': existing_assignment is not None
        }

        if matching_slot:
            response['availability']['slot'] = {
                'start_time': str(matching_slot.start_time),
                'end_time': str(matching_slot.end_time)
            }

        return response, 200

    except Exception as exc:
        logger.error(f"Error checking staff availability: {exc}")
        return {'status': 'error', 'message': str(exc)}, 500


def batch_staff_availability(schedule_type: str, queries: list[dict[str, Any]]):
    """
    Process multiple availability queries in a single request to reduce server load.
    Each query should have: staff_id, day, time
    Returns: list of results with staff_id, day, time, is_available
    """
    try:
        results = []
        for query in queries:
            staff_id = query.get('staff_id')
            day = query.get('day')
            time_slot = query.get('time')
            
            if not all([staff_id, day, time_slot]):
                results.append({
                    'staff_id': staff_id,
                    'day': day,
                    'time': time_slot,
                    'is_available': False,
                    'error': 'Missing required parameters'
                })
                continue
            
            # Use the single availability check function
            result, status_code = check_staff_availability_for_slot(schedule_type, staff_id, day, time_slot)
            
            # Extract the availability result
            is_available = False
            if status_code == 200 and result.get('status') == 'success':
                is_available = result.get('is_available', False)
            
            results.append({
                'staff_id': staff_id,
                'day': day,
                'time': time_slot,
                'is_available': is_available
            })
        
        return {'status': 'success', 'results': results}, 200
        
    except Exception as exc:
        logger.error(f"Error in batch availability check: {exc}")
        return {'status': 'error', 'message': str(exc)}, 500


def generate_schedule_pdf_for_type(schedule_type: str):
    try:
        schedule_id = _schedule_id_for_type(schedule_type)
        schedule = Schedule.query.filter_by(id=schedule_id, type=schedule_type).first()
        if not schedule:
            return None, None, {'status': 'error', 'message': _ERROR_SCHEDULE_NOT_FOUND}, 404

        schedule_data = get_schedule_data(schedule_id, schedule_type)
        if not schedule_data:
            return None, None, {'status': 'error', 'message': 'Unable to generate schedule data.'}, 500

        pdf_buffer = generate_schedule_pdf(schedule_data, export_format='standard')
        if not pdf_buffer:
            return None, None, {'status': 'error', 'message': 'Failed to generate PDF.'}, 500

        filename = f"{schedule_type}_schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return pdf_buffer, filename, None, 200

    except Exception as exc:
        logger.error(f"Error generating schedule PDF for {schedule_type}: {exc}")
        return None, None, {'status': 'error', 'message': str(exc)}, 500