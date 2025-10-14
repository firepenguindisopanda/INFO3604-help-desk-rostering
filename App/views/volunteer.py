from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user
from werkzeug.utils import secure_filename
from App.middleware import volunteer_required
from App.controllers.student import (
    get_student, get_student_by_id, get_student_profile_data,
    update_student_courses, update_student_availability
)
from App.controllers.help_desk_assistant import get_help_desk_assistant
from App.controllers.course import get_all_courses
from App.controllers.tracking import (
    get_student_stats, 
    get_today_shift,
    get_shift_history,
    get_time_distribution,
    clock_in,
    clock_out,
    check_and_complete_abandoned_entry,
    auto_complete_time_entries
)
from App.controllers.notification import notify_availability_updated
from App.controllers.dashboard import get_dashboard_data
from App.controllers.request import (
    get_student_requests,
    get_available_shifts_for_student,
    get_available_replacements,
    create_student_request
)
from App.database import db
import datetime
import os
import json
from App.utils.time_utils import trinidad_now, convert_to_trinidad_time
from datetime import datetime, timedelta, time
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
    # Get current user data using controller
    username = current_user.username
    import json  # Ensure json is imported here
   
    # Get the student profile data using controller
    student = get_student(username)
    if not student:
        flash("Student profile not found", "error")
        return redirect(url_for('volunteer_views.dashboard'))
    
    # Get profile data using controller
    profile_data = get_student_profile_data(student)
    if not profile_data:
        flash("Unable to retrieve profile data", "error")
        return redirect(url_for('volunteer_views.dashboard'))
    
    # Format availabilities by day
    availability_by_day = {
        'MON': [], 'TUE': [], 'WED': [], 'THUR': [], 'FRI': []
    }
    
    days_mapping = {
        0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THUR', 4: 'FRI'
    }
    
    # Use availability data from profile_data controller
    availabilities = profile_data.get('availability', [])
    
    for avail in availabilities:
        try:
            day_idx = avail.get('day_of_week')
            day_name = days_mapping.get(day_idx)
            if not day_name:
                print(f"Warning: Invalid day_of_week value: {day_idx}")
                continue
                
            # Format time slot based on the hour
            start_time_str = avail.get('start_time')
            if start_time_str:
                try:
                    hour = int(start_time_str.split(':')[0])
                    
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
                    
                    if hour in time_slot_mapping:
                        time_slot = time_slot_mapping[hour]
                        if time_slot not in availability_by_day[day_name]:
                            availability_by_day[day_name].append(time_slot)
                    else:
                        print(f"Warning: Hour {hour} not in expected time slots")
                except (ValueError, IndexError) as e:
                    print(f"Error parsing time {start_time_str}: {e}")
            else:
                print(f"Warning: Missing start time for availability")
                
        except Exception as e:
            print(f"Error processing availability: {e}")
    
    # Get stats

    stats = get_student_stats(username) or {
        'daily': {'hours': 0, 'date': trinidad_now().strftime('%Y-%m-%d')},
        'weekly': {'hours': 0, 'start_date': (trinidad_now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d'), 'end_date': trinidad_now().strftime('%Y-%m-%d')},
        'monthly': {'hours': 0, 'month': trinidad_now().strftime('%B %Y')},
        'semester': {'hours': 0},
        'absences': 0
    }
    
    # Get profile data from student record for image/contact info
    stored_profile_data = {}
    if hasattr(student, 'profile_data') and student.profile_data:
        try:
            stored_profile_data = json.loads(student.profile_data)
        except:
            stored_profile_data = {}

    image_url = resolve_profile_image(getattr(student, 'profile_data', None))
    legacy_filename = stored_profile_data.get('image_filename') if isinstance(stored_profile_data, dict) else None
    if legacy_filename and '://' not in str(legacy_filename):
        import os
        filepath = os.path.join('App', 'static', str(legacy_filename).lstrip('/'))
        if os.path.exists(filepath):
            image_url = url_for('static', filename=str(legacy_filename))

    # Build user data dictionary - use profile_data from controller for courses
    user_data = {
        "name": student.name if student.name else username,
        "id": username,
        "phone": stored_profile_data.get('phone', ''),
        "email": stored_profile_data.get('email', f"{username}@my.uwi.edu"),
        "image_url": image_url,
        "profile_image_url": image_url,
        "degree": getattr(student, 'degree', ''),
        "enrolled_courses": [cap.get('course_code', '') for cap in profile_data.get('course_capabilities', [])],
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
                
                # Update the user's profile data using controller
                student = get_student(username)
                if student:
                    # Get existing profile data or create new
                    if hasattr(student, 'profile_data') and student.profile_data:
                        try:
                            profile_data = json.loads(student.profile_data)
                        except (json.JSONDecodeError, TypeError):
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
        
        # Parse availability data for controller
        availability_data = []
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
                    
                    availability_data.append({
                        'day_of_week': day,
                        'start_time': start_time_str,
                        'end_time': end_time_str
                    })
                except Exception as e:
                    print(f"Error processing availability slot: {e}")
                    continue
        
        # Use controller to update availability
        student = get_student(username)
        if not student:
            return jsonify({
                'success': False,
                'message': 'Student not found'
            })
        
        success, message = update_student_availability(student.username, availability_data)
        
        if success:
            # Send notification about availability update
            notify_availability_updated(username)
            
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            })
            
    except Exception as e:
        print(f"Error updating availability: {e}")
        return jsonify({
            'success': False,
            'message': f'An error occurred while updating availability: {str(e)}'
        })

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
    
    # Get student and profile data using controller
    student = get_student(username)
    if not student:
        return jsonify({'error': 'Student not found'})
    
    profile_data = get_student_profile_data(student)
    if not profile_data:
        return jsonify({'error': 'Profile data not found'})
    
    # Return availability from profile data
    availabilities = profile_data.get('availability', [])
    
    return jsonify(availabilities)