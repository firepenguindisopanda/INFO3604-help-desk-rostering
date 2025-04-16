from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for, send_file
from flask_jwt_extended import jwt_required, current_user
from datetime import datetime, timedelta
from App.controllers.schedule import (
    generate_help_desk_schedule,
    generate_lab_schedule,
    publish_schedule,
    get_current_schedule,
    publish_and_notify,
    clear_schedule
)
from App.models import Schedule, Shift, Allocation, Student
from App.database import db
from App.middleware import admin_required
from io import BytesIO
from weasyprint import HTML, CSS
import tempfile
import os


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
        
        print(f"Save request: start={start_date_str}, end={end_date_str}, assignments={len(assignments)}")
        
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
            
        # Get or create the main schedule
        schedule = Schedule.query.get(1)
        if not schedule:
            print("Creating new main schedule")
            schedule = Schedule(1, start_date, end_date)
            db.session.add(schedule)
        else:
            print(f"Updating existing schedule: id={schedule.id}")
            schedule.start_date = start_date
            schedule.end_date = end_date
            db.session.add(schedule)
            
        db.session.flush()
        
        # Get all current shifts for this schedule in the date range
        current_shifts = Shift.query.filter(
            Shift.schedule_id == schedule.id,
            Shift.date >= start_date,
            Shift.date <= end_date
        ).all()
        
        shift_lookup = {}
        
        # Build a lookup map to find existing shifts by date and time
        for shift in current_shifts:
            key = f"{shift.date.strftime('%Y-%m-%d')}_{shift.start_time.hour}"
            shift_lookup[key] = shift
            
        print(f"Found {len(current_shifts)} existing shifts in date range")
        
        # Track successful assignments and processed shifts
        successful_assignments = 0
        processed_shift_ids = set()
        
        # Process assignments and create/update shifts and allocations
        for assignment in assignments:
            day = assignment.get('day')
            time_str = assignment.get('time')
            staff_list = assignment.get('staff', [])
            
            print(f"Processing assignment: day={day}, time={time_str}, staff={len(staff_list)}")
                
            # Convert day name to index (0=Monday, 1=Tuesday, etc.)
            day_map = {'MON': 0, 'TUE': 1, 'WED': 2, 'THUR': 3, 'FRI': 4, 
                       'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4}
            day_idx = day_map.get(day, 0)
            
            # Calculate shift date based on start_date and day index
            shift_date = start_date + timedelta(days=day_idx)
            
            # Parse shift time
            try:
                # Time format is like "9:00 am" or "9:00 - 10:00"
                if '-' in time_str:
                    # Format is "9:00 - 10:00"
                    start_time_str = time_str.split('-')[0].strip()
                else:
                    # Format is "9:00 am"
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
                    
                # Log parsed time details
                print(f"Parsed time: original='{time_str}', extracted hour={hour}")
                
                # Create lookup key for existing shifts
                shift_key = f"{shift_date.strftime('%Y-%m-%d')}_{hour}"
                
                # Check if shift already exists
                shift = shift_lookup.get(shift_key)
                
                # If shift doesn't exist, create it
                if not shift:
                    print(f"Creating new shift for {shift_key}")
                    shift_start = datetime.combine(shift_date.date(), datetime.min.time().replace(hour=hour, minute=0))
                    shift_end = shift_start + timedelta(hours=1)
                    
                    shift = Shift(shift_date, shift_start, shift_end, schedule.id)
                    db.session.add(shift)
                    db.session.flush()  # Get the shift ID
                    # Add to lookup for future reference
                    shift_lookup[shift_key] = shift
                else:
                    print(f"Using existing shift {shift.id} for {shift_key}")
                
                # Track this shift as processed
                processed_shift_ids.add(shift.id)
                
                # Delete existing allocations for this shift
                deleted_count = Allocation.query.filter_by(shift_id=shift.id).delete()
                print(f"Deleted {deleted_count} existing allocations for shift {shift.id}")
                
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
                
                successful_assignments += 1
                
            except Exception as e:
                print(f"Error processing shift {day} at {time_str}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Handle shifts that weren't included in the assignments
        # This is important for when you remove all staff from a shift
        unprocessed_shifts = [shift for shift in current_shifts if shift.id not in processed_shift_ids]
        print(f"Found {len(unprocessed_shifts)} shifts in date range not processed in assignments")
        
        for shift in unprocessed_shifts:
            # Clear all allocations for unprocessed shifts
            deleted_count = Allocation.query.filter_by(shift_id=shift.id).delete()
            print(f"Deleted {deleted_count} allocations from unprocessed shift {shift.id} on {shift.date}")
                
        # Commit changes
        db.session.commit()
        
        print(f"Schedule saved successfully with {successful_assignments} assignments")
        
        return jsonify({
            'status': 'success',
            'message': 'Schedule saved successfully',
            'schedule_id': schedule.id,
            'assignments_saved': successful_assignments,
            'shifts_cleared': len(unprocessed_shifts)
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
            
        # Add the schedule type to the result for frontend reference
        if result.get('status') == 'success':
            result['schedule_type'] = user.role
            
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

@schedule_views.route('/api/schedule/clear', methods=['POST'])
@jwt_required()
@admin_required
def clear_schedule_endpoint():
    """Clear the entire schedule from the database"""
    try:
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

@schedule_views.route('/api/schedule/current', methods=['GET'])
@jwt_required()
def get_current_schedule_endpoint():
    """Get the current schedule based on admin role"""
    try:
        # Get user role and determine schedule type and ID
        role = current_user.role
        schedule_type = role  # 'helpdesk' or 'lab'
        schedule_id = 1 if role == 'helpdesk' else 2
        
        print(f"Getting current {schedule_type} schedule (ID: {schedule_id})")
        
        # Get the appropriate schedule based on role
        schedule = Schedule.query.filter_by(id=schedule_id, type=schedule_type).first()
        
        if not schedule:
            print(f"No {schedule_type} schedule found")
            return jsonify({'status': 'error', 'message': 'No schedule found'}), 404
        
        print(f"Found schedule: id={schedule.id}, start={schedule.start_date}, end={schedule.end_date}")
        
        # Get all shifts for this schedule
        shifts = Shift.query.filter_by(schedule_id=schedule.id).all()
        print(f"Found {len(shifts)} shifts")
        
        # Format the schedule for display
        formatted_schedule = {
            "schedule_id": schedule.id,
            "date_range": f"{schedule.start_date.strftime('%d %b')} - {schedule.end_date.strftime('%d %b, %Y')}",
            "is_published": schedule.is_published,
            "type": schedule_type,  # Add the type for frontend reference
            "days": []
        }
        
        # Group shifts by day
        shifts_by_day = {}
        for shift in shifts:
            day_idx = shift.date.weekday()  # 0=Monday, 1=Tuesday, etc.
            if day_idx >= 5:  # Skip weekend shifts
                continue
                
            if day_idx not in shifts_by_day:
                shifts_by_day[day_idx] = []
                
            # Get assistants for this shift
            assistants = []
            allocations = Allocation.query.filter_by(shift_id=shift.id).all()
            
            for allocation in allocations:
                student = Student.query.get(allocation.username)
                if student:
                    assistants.append({
                        "username": student.username,
                        "name": student.get_name(),
                        "id": student.username
                    })
            
            # Format time
            formatted_time = shift.formatted_time() if hasattr(shift, 'formatted_time') else f"{shift.start_time.strftime('%I:%M %p')} to {shift.end_time.strftime('%I:%M %p')}"
            
            # Add shift data
            shifts_by_day[day_idx].append({
                "shift_id": shift.id,
                "time": formatted_time,
                "hour": shift.start_time.hour,
                "assistants": assistants
            })
        
        # Sort shifts for each day by hour
        for day_idx in shifts_by_day:
            shifts_by_day[day_idx].sort(key=lambda s: s["hour"])
        
        # Create days array with all days (Mon-Fri)
        days = []
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        day_codes = ["MON", "TUE", "WED", "THUR", "FRI"]
        
        for day_idx in range(5):
            # Calculate the date for this day
            day_date = schedule.start_date + timedelta(days=day_idx)
            day_shifts = []
            
            # If we have shifts for this day, add them
            if day_idx in shifts_by_day:
                # Create a full day of shifts (9am-5pm)
                for hour in range(9, 17):
                    # Find the shift for this hour
                    matching_shifts = [s for s in shifts_by_day[day_idx] if s["hour"] == hour]
                    
                    if matching_shifts:
                        day_shifts.append(matching_shifts[0])
                    else:
                        # Add an empty shift for this hour
                        time_str = f"{hour}:00 am" if hour < 12 else f"{hour-12 if hour > 12 else hour}:00 pm"
                        day_shifts.append({
                            "shift_id": None,
                            "time": f"{time_str} to {hour+1}:00 am" if hour < 11 else f"{time_str} to {(hour+1)-12 if hour+1 > 12 else hour+1}:00 pm",
                            "assistants": []
                        })
            else:
                # Create all empty shifts for this day
                for hour in range(9, 17):
                    time_str = f"{hour}:00 am" if hour < 12 else f"{hour-12 if hour > 12 else hour}:00 pm"
                    day_shifts.append({
                        "shift_id": None,
                        "time": f"{time_str} to {hour+1}:00 am" if hour < 11 else f"{time_str} to {(hour+1)-12 if hour+1 > 12 else hour+1}:00 pm",
                        "assistants": []
                    })
            
            # Add this day to the days array
            days.append({
                "day": day_names[day_idx],
                "day_code": day_codes[day_idx],
                "date": day_date.strftime("%d %b"),
                "shifts": day_shifts
            })
        
        # Add days to the formatted schedule
        formatted_schedule["days"] = days
        
        print(f"Returning formatted schedule with {len(days)} days")
        return jsonify({'status': 'success', 'schedule': formatted_schedule})
        
    except Exception as e:
        print(f"Error getting current schedule: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, current_user
from App.models import Student, HelpDeskAssistant, Availability
from App.database import db
from App.middleware import admin_required
from datetime import datetime, time

# Create a new blueprint or add to the existing one
# If you have an existing controller file for staff/users, you could add this there

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
            return jsonify({
                'status': 'error',
                'message': 'Day and time parameters are required'
            }), 400
        
        # Convert day to day_of_week index (0=Monday, 1=Tuesday, etc.)
        day_map = {
            'MON': 0, 'TUE': 1, 'WED': 2, 'THUR': 3, 'FRI': 4,
            'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4
        }
        day_of_week = day_map.get(day)
        
        if day_of_week is None:
            return jsonify({
                'status': 'error',
                'message': f'Invalid day: {day}'
            }), 400
        
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
                'status': 'error',
                'message': f'Invalid time format: {time_slot}'
            }), 400
        
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
    Query parameters:
    - staff_id: The staff ID to check
    - day: The day of the week (e.g., "Monday", "MON")
    - time: The time slot (e.g., "9:00 am")
    """
    try:
        # Get query parameters
        staff_id = request.args.get('staff_id')
        day = request.args.get('day')
        time_slot = request.args.get('time')
        
        if not staff_id or not day or not time_slot:
            return jsonify({
                'status': 'error',
                'message': 'Staff ID, day, and time parameters are required'
            }), 400
        
        # Convert day to day_of_week index
        day_map = {
            'MON': 0, 'TUE': 1, 'WED': 2, 'THUR': 3, 'FRI': 4,
            'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4
        }
        day_of_week = day_map.get(day)
        
        if day_of_week is None:
            return jsonify({
                'status': 'error',
                'message': f'Invalid day: {day}'
            }), 400
        
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
                'status': 'error',
                'message': f'Invalid time format: {time_slot}'
            }), 400
        
        # Check availability
        availabilities = Availability.query.filter_by(
            username=staff_id,
            day_of_week=day_of_week
        ).all()
        
        is_available = False
        
        for avail in availabilities:
            # Create time objects for the hour we want to check
            check_time = time(hour=hour)
            
            # Check if this availability window includes our time
            if avail.start_time <= check_time and avail.end_time >= time(hour=hour+1):
                is_available = True
                break
        
        # Return availability status
        return jsonify({
            'status': 'success',
            'is_available': is_available
        })
        
    except Exception as e:
        print(f"Error checking Student Assistant availability: {e}")
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
        # Get the current schedule data
        schedule_data = get_current_schedule()
        
        if not schedule_data:
            return jsonify({
                'status': 'error',
                'message': 'No schedule found'
            }), 404
        
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
        
        # Generate a filename with current date
        from datetime import datetime
        filename = f"help_desk_schedule_{datetime.now().strftime('%Y-%m-%d')}.pdf"
        
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