from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user
from werkzeug.utils import secure_filename
from App.middleware import volunteer_required
from App.models import Student, HelpDeskAssistant, CourseCapability, Availability, User, Course, TimeEntry
from App.controllers.tracking import (
    get_student_stats, 
    get_today_shift,
    get_shift_history,
    get_time_distribution,
    clock_in,
    clock_out
)
from App.database import db
from App.controllers.notification import notify_availability_updated
from App.controllers.course import get_all_courses
import datetime
import os
import json
from App.utils.time_utils import trinidad_now, convert_to_trinidad_time
from datetime import datetime, timedelta, time
from App.controllers.tracking import check_and_complete_abandoned_entry
from App.controllers.dashboard import get_dashboard_data
from App.controllers.tracking import auto_complete_time_entries
from App.controllers.tracking import get_student_stats
from App.controllers.request import (
    get_student_requests,
    get_available_shifts_for_student,
    get_available_replacements
)
from App.controllers.request import create_student_request
from App.utils.profile_images import resolve_profile_image

volunteer_views = Blueprint('volunteer_views', __name__, template_folder='../templates')

@volunteer_views.route('/volunteer/dashboard')
@jwt_required()
@volunteer_required
def dashboard():
    # Get current user's username
    username = current_user.username
    


    check_and_complete_abandoned_entry(username)

    # Get all the data needed for the dashboard (with the latest published schedule)
    dashboard_data = get_dashboard_data(username)
    
    if not dashboard_data:
        flash("Error retrieving dashboard data", "error")
        return redirect(url_for('auth_views.login_page'))
    
    # Extract data for the template
    next_shift = dashboard_data['next_shift']
    my_shifts = dashboard_data['my_shifts']
    full_schedule = dashboard_data['full_schedule']
    
    # Debug prints
    print(f"Rendering dashboard with data:")
    print(f"Next shift: {next_shift}")
    print(f"My shifts count: {len(my_shifts)}")
    print(f"Full schedule days: {full_schedule['days_of_week']}")
    print(f"Full schedule time slots: {full_schedule['time_slots']}")
    
    # Render the template with real data
    return render_template('volunteer/dashboard/dashboard.html',
                          next_shift=next_shift,
                          my_shifts=my_shifts,
                          full_schedule=full_schedule)
    
@volunteer_views.route('/volunteer/time_tracking')
@jwt_required()
@volunteer_required
def time_tracking():
    username = current_user.username
    
    # Auto-complete any expired sessions first

    auto_complete_time_entries()
    
    # Get student stats
    stats = get_student_stats(username) or {
        'daily': {'hours': 0, 'date': datetime.now().strftime('%Y-%m-%d'), 'date_range': datetime.now().strftime("%d %b, %Y")},
        'weekly': {
            'hours': 0, 
            'start_date': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'), 
            'end_date': datetime.now().strftime('%Y-%m-%d'),
            'date_range': f"Week {datetime.now().isocalendar()[1]}, {(datetime.now() - timedelta(days=7)).strftime('%b %d')} - {datetime.now().strftime('%b %d')}"
        },
        'monthly': {'hours': 0, 'month': datetime.now().strftime('%B %Y'), 'date_range': datetime.now().strftime('%B %Y')},
        'semester': {'hours': 0, 'date_range': 'Current Semester'},
        'absences': 0
    }
    
    # Get today's shift information
    today_shift = get_today_shift(username)
    
    # Get shift history
    shift_history = get_shift_history(username)
    
    # Get time distribution data for chart
    time_distribution = get_time_distribution(username)
    
    # Format stats for display
    now = datetime.now()
    
    daily = {
        "date_range": stats['daily'].get('date_range', now.strftime("%d %b, %I:%M %p")),
        "hours": f"{stats['daily']['hours']:.1f}"
    }
    
    weekly = {
        "date_range": stats['weekly'].get('date_range', f"Week {now.isocalendar()[1]}, {now.strftime('%b %d')} - {(now + timedelta(days=6)).strftime('%b %d')}"),
        "hours": f"{stats['weekly']['hours']:.1f}"
    }
    
    monthly = {
        "date_range": stats['monthly'].get('date_range', stats['monthly']['month']),
        "hours": f"{stats['monthly']['hours']:.1f}"
    }
    
    semester = {
        "date_range": stats['semester'].get('date_range', "Current Semester"),
        "hours": f"{stats['semester']['hours']:.1f}"
    }
    
    # Check if time_distribution has actual data or is empty
    has_data = time_distribution and any(day.get('hours', 0) > 0 for day in time_distribution)
    
    # If we have no time distribution data, create empty placeholder data
    if not has_data and (not time_distribution or len(time_distribution) == 0):
        day_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
        time_distribution = [
            {"label": day, "percentage": 0, "hours": 0} 
            for day in day_labels
        ]
    
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
def clock_in_endpoint():
    username = current_user.username
    
    # Get today's shift to get the shift_id
    today_shift = get_today_shift(username)
    shift_id = today_shift.get('shift_id')
    
    # If there's no active shift, return an error
    if not shift_id or today_shift.get('status') != 'active':
        return jsonify({
            'success': False,
            'message': 'No active shift found for clocking in'
        })
    
    # Check if already clocked in
    if today_shift.get('starts_now'):
        return jsonify({
            'success': False,
            'message': 'You are already clocked in for this shift'
        })
    
    # Call the clock_in controller
    result = clock_in(username, shift_id)
    
    # Log the result
    print(f"Clock in result for {username}: {result}")
    
    return jsonify(result)

@volunteer_views.route('/volunteer/time_tracking/clock_out', methods=['POST'])
@jwt_required()
@volunteer_required
def clock_out_endpoint():
    username = current_user.username
    
    # Get today's shift to verify clocked in status
    today_shift = get_today_shift(username)
    
    # Verify the user is clocked in
    if not today_shift.get('starts_now'):
        return jsonify({
            'success': False,
            'message': 'You are not currently clocked in'
        })
    
    # Call the clock_out controller
    result = clock_out(username)
    
    # Log the result
    print(f"Clock out result for {username}: {result}")
    
    return jsonify(result)

@volunteer_views.route('/volunteer/profile')
@jwt_required()
@volunteer_required
def profile():
    # Get current user data from database
    username = current_user.username
    import json  # Ensure json is imported here
   
    # Get the user details
    student = Student.query.get(username)
    if not student:
        flash("Student profile not found", "error")
        return redirect(url_for('volunteer_views.dashboard'))
    
    # Get help desk assistant details
    assistant = HelpDeskAssistant.query.get(username)
    if not assistant:
        flash("Assistant profile not found", "error")
        return redirect(url_for('volunteer_views.dashboard'))
    
    # Get course capabilities
    course_capabilities = CourseCapability.query.filter_by(assistant_username=username).all()
    
    # Get availabilities
    availabilities = Availability.query.filter_by(username=username).all()
    
    print(f"Found {len(availabilities)} availability records for {username}")
    
    # Format availabilities by day
    availability_by_day = {
        'MON': [], 'TUE': [], 'WED': [], 'THUR': [], 'FRI': []
    }
    
    days_mapping = {
        0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THUR', 4: 'FRI'
    }
    
    for avail in availabilities:
        try:
            day_name = days_mapping.get(avail.day_of_week)
            if not day_name:
                print(f"Warning: Invalid day_of_week value: {avail.day_of_week}")
                continue
                
            # Format time slot based on the hour
            if avail.start_time:
                start_hour = avail.start_time.hour
                
                # Map hours to specific slots for display
                time_slot_mapping = {
                    9: '9am - 10am', 
                    10: '10am - 11am', 
                    11: '11am - 12pm',
                    12: '12pm - 1pm',
                    13: '1pm - 2pm',
                    14: '2pm - 3pm',
                    15: '3pm - 4pm',
                    16: '4pm - 5pm'
                }
                
                if start_hour in time_slot_mapping:
                    time_slot = time_slot_mapping[start_hour]
                    if time_slot not in availability_by_day[day_name]:
                        availability_by_day[day_name].append(time_slot)
                else:
                    print(f"Warning: Hour {start_hour} not in expected time slots")
            else:
                print(f"Warning: Missing start time for availability ID {avail.id}")
                
        except Exception as e:
            print(f"Error processing availability {avail.id}: {e}")
    
    # Get stats

    stats = get_student_stats(username) or {
        'daily': {'hours': 0, 'date': trinidad_now().strftime('%Y-%m-%d')},
        'weekly': {'hours': 0, 'start_date': (trinidad_now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d'), 'end_date': trinidad_now().strftime('%Y-%m-%d')},
        'monthly': {'hours': 0, 'month': trinidad_now().strftime('%B %Y')},
        'semester': {'hours': 0},
        'absences': 0
    }
    
    # Get profile data from student record
    profile_data = {}
    if hasattr(student, 'profile_data') and student.profile_data:
        try:
            profile_data = json.loads(student.profile_data)
        except:
            profile_data = {}
    
    image_url = resolve_profile_image(getattr(student, 'profile_data', None))
    legacy_filename = profile_data.get('image_filename') if isinstance(profile_data, dict) else None
    if legacy_filename and '://' not in str(legacy_filename):
        image_url = url_for('static', filename=str(legacy_filename))
    
    # Build user data dictionary with image_url
    user_data = {
        "name": student.name if student.name else username,
        "id": username,
        "phone": profile_data.get('phone', ''),
        "email": profile_data.get('email', f"{username}@my.uwi.edu"),
    "image_url": image_url,
    "profile_image_url": image_url,
        "degree": student.degree,
        "enrolled_courses": [cap.course_code for cap in course_capabilities],
        "availability": availability_by_day,
        "stats": {
            "weekly": {
                "date_range": f"Week {trinidad_now().isocalendar()[1]}, {datetime.strptime(stats['weekly']['start_date'], '%Y-%m-%d').strftime('%b %d')} - {datetime.strptime(stats['weekly']['end_date'], '%Y-%m-%d').strftime('%b %d')}",
                "hours": f"{stats['weekly']['hours']:.1f}"
            },
            "monthly": {
                "date_range": stats['monthly']['month'],
                "hours": f"{stats['monthly']['hours']:.1f}"
            },
            "semester": {
                "date_range": "Current Semester",
                "hours": f"{stats['semester']['hours']:.1f}"
            },
            "absences": str(stats['absences'])
        }
    }
    
    return render_template('volunteer/profile/index.html', user=user_data)

@volunteer_views.route('/volunteer/update_profile', methods=['POST'])
@jwt_required()
@volunteer_required
def update_profile():
    """Update profile information including profile image"""
    try:
        username = current_user.username
        
        # Check if profile image was uploaded
        if 'profile_image' in request.files:
            profile_image = request.files['profile_image']
            
            if profile_image and profile_image.filename:
                # Validate file type
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
                file_ext = profile_image.filename.rsplit('.', 1)[1].lower() if '.' in profile_image.filename else ''
                
                if file_ext not in allowed_extensions:
                    return jsonify({
                        'success': False,
                        'message': 'Invalid file type. Allowed types: PNG, JPG, JPEG, GIF'
                    })
                
                # Ensure upload directory exists
                upload_dir = os.path.join('App', 'static', 'uploads', 'profile_images')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Generate a unique filename
                filename = f"{username}_{secure_filename(profile_image.filename)}"
                filepath = os.path.join(upload_dir, filename)
                
                # Save the file
                profile_image.save(filepath)
                
                # Update the user's profile data
                student = Student.query.get(username)
                if student:
                    # Get existing profile data or create new
                    if hasattr(student, 'profile_data') and student.profile_data:
                        try:
                            profile_data = json.loads(student.profile_data)
                        except:
                            profile_data = {}
                    else:
                        profile_data = {}
                    
                    # Update image path in profile data
                    relative_path = os.path.join('uploads', 'profile_images', filename)
                    profile_data['image_filename'] = relative_path
                    
                    # Save back to database
                    student.profile_data = json.dumps(profile_data)
                    db.session.commit()
                    
                    # Return success with the new image URL
                    return jsonify({
                        'success': True,
                        'message': 'Profile image updated successfully',
                        'image_url': url_for('static', filename=relative_path)
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Student profile not found'
                    })
        
        return jsonify({
            'success': False,
            'message': 'No profile image provided'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating profile: {e}")
        return jsonify({
            'success': False,
            'message': f"Error updating profile: {str(e)}"
        }), 500

@volunteer_views.route('/volunteer/update_availability', methods=['POST'])
@jwt_required()
@volunteer_required
def update_availability():
    try:
        data = request.json
        username = current_user.username
        
        print(f"Received availability data: {data}")
        
        # First, clear existing availabilities
        Availability.query.filter_by(username=username).delete()
        db.session.commit()
        
        # Add new availabilities
        if 'availabilities' in data and data['availabilities']:
            for slot in data['availabilities']:
                try:
                    day = slot.get('day', 0)  # 0 for Monday, 1 for Tuesday, etc.
                    
                    # Parse times with proper error handling
                    start_time_str = slot.get('start_time', '00:00:00')
                    end_time_str = slot.get('end_time', '00:00:00')
                    
                    # Ensure we have valid time strings before parsing
                    if not isinstance(start_time_str, str) or not isinstance(end_time_str, str):
                        print(f"Invalid time format: start={start_time_str}, end={end_time_str}")
                        continue
                        
                    try:
                        # Try parsing as HH:MM:SS
                        hour, minute, second = map(int, start_time_str.split(':'))
                        start_time = time(hour=hour, minute=minute, second=second)
                    except ValueError:
                        # If that fails, just use the hour
                        try:
                            hour = int(start_time_str.split(':')[0])
                            start_time = time(hour=hour)
                        except ValueError:
                            print(f"Could not parse start time: {start_time_str}")
                            continue
                            
                    try:
                        # Try parsing as HH:MM:SS
                        hour, minute, second = map(int, end_time_str.split(':'))
                        end_time = time(hour=hour, minute=minute, second=second)
                    except ValueError:
                        # If that fails, just use the hour
                        try:
                            hour = int(end_time_str.split(':')[0])
                            end_time = time(hour=hour)
                        except ValueError:
                            print(f"Could not parse end time: {end_time_str}")
                            continue
                    
                    # Ensure day is an integer in range 0-4 (Mon-Fri)
                    day = int(day)
                    if day < 0 or day > 4:
                        print(f"Day out of range (0-4): {day}")
                        continue
                    
                    availability = Availability(username, day, start_time, end_time)
                    db.session.add(availability)
                    print(f"Added availability: Day {day}, {start_time}-{end_time}")
                except Exception as e:
                    print(f"Error adding individual availability: {e}")
                    # Continue with other availabilities even if this one failed
        
        db.session.commit()
        
        # Create notification
        notify_availability_updated(username)
        
        # Get updated availabilities to return
        updated_availabilities = Availability.query.filter_by(username=username).all()
        
        print(f"Successfully updated {len(updated_availabilities)} availability slots")
        
        return jsonify({
            "success": True, 
            "message": "Availability updated successfully",
            "count": len(updated_availabilities)
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error updating availability: {e}")
        return jsonify({
            "success": False,
            "message": f"Error updating availability: {str(e)}"
        }), 500

@volunteer_views.route('/api/courses')
@jwt_required()
def get_courses():
    """Get all available courses from the standardized list"""
    try:
        # Format the courses as required by the frontend
        formatted_courses = [{'code': course.code, 'name': course.name} for course in get_all_courses()]
        
        return jsonify({
            'success': True,
            'courses': formatted_courses
        })
    except Exception as e:
        print(f"Error getting courses: {e}")
        return jsonify({'success': False, 'message': str(e)})

@volunteer_views.route('/volunteer/requests')
@jwt_required()
@volunteer_required
def requests():

    username = current_user.username
    
    # Get the student's requests
    requests_list = get_student_requests(username)
    
    # Categorize by status
    pending_requests = [r for r in requests_list if r['status'] == 'PENDING']
    approved_requests = [r for r in requests_list if r['status'] == 'APPROVED']
    rejected_requests = [r for r in requests_list if r['status'] == 'REJECTED']
    
    # Get available shifts for new requests
    available_shifts = get_available_shifts_for_student(username)
    
    # Get available replacements
    available_replacements = get_available_replacements(username)
    
    return render_template('volunteer/requests/index.html',
                          pending_requests=pending_requests,
                          approved_requests=approved_requests,
                          rejected_requests=rejected_requests,
                          available_shifts=available_shifts,
                          available_replacements=available_replacements)

@volunteer_views.route('/volunteer/submit_request', methods=['POST'])
@jwt_required()
@volunteer_required
def submit_request():
    """Submit a new shift change request"""

    
    data = request.form
    
    # Extract data from form
    shift_id = data.get('shiftToChange')
    reason = data.get('reasonForChange')
    replacement = data.get('proposedReplacement')
    
    # Validate required fields
    if not shift_id or not reason:
        flash("Shift and reason are required fields", "error")
        return redirect(url_for('volunteer_views.requests'))
    
    # Create the request
    success, message = create_student_request(
        current_user.username,
        shift_id,
        reason,
        replacement
    )
    
    if success:
        flash(message, "success")
    else:
        flash(message, "error")
        
    return redirect(url_for('volunteer_views.requests'))

@volunteer_views.route('/debug_availability')
@jwt_required()
def debug_availability():
    username = current_user.username
    availabilities = Availability.query.filter_by(username=username).all()
    
    result = []
    for avail in availabilities:
        result.append({
            'id': avail.id,
            'day_of_week': avail.day_of_week,
            'start_time': avail.start_time.strftime('%H:%M:%S') if avail.start_time else None,
            'end_time': avail.end_time.strftime('%H:%M:%S') if avail.end_time else None,
        })
    
    return jsonify(result)