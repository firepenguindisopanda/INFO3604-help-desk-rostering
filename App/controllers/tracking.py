from App.models import Student, HelpDeskAssistant, LabAssistant, Shift, Allocation, TimeEntry
from App.database import db
from datetime import datetime, timedelta, time
from App.controllers.notification import (
    notify_clock_in,
    notify_clock_out,
    notify_missed_shift
)
from App.utils.time_utils import trinidad_now, convert_to_trinidad_time
from App.utils.profile_images import resolve_profile_image
import json


def _resolve_profile_image_url(student):
    raw_profile_data = getattr(student, 'profile_data', None) if student else None
    image_url = resolve_profile_image(raw_profile_data)

    if raw_profile_data:
        try:
            parsed = json.loads(raw_profile_data) if isinstance(raw_profile_data, str) else raw_profile_data
        except (TypeError, ValueError):
            parsed = {}
        legacy_filename = parsed.get('image_filename') if isinstance(parsed, dict) else None
        if legacy_filename and '://' not in str(legacy_filename):
            import os
            filepath = os.path.join('App', 'static', str(legacy_filename).lstrip('/'))
            if os.path.exists(filepath):
                return f"/static/{str(legacy_filename).lstrip('/')}"

    return image_url

def get_student_stats(username):
    """Get attendance statistics for a student"""
    # Get the student
    student = Student.query.get(username)
    if not student:
        return None
        
    # Get time entries for this student
    time_entries = TimeEntry.query.filter_by(username=username).all()
    
    # Calculate stats
    now = trinidad_now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Daily stats (today)
    daily_entries = [e for e in time_entries if e.clock_in and e.clock_in >= today]
    daily_hours = sum(e.get_hours_worked() for e in daily_entries)
    
    # Weekly stats (last 7 days)
    week_start = today - timedelta(days=today.weekday())  # Monday of this week
    weekly_entries = [e for e in time_entries if e.clock_in and e.clock_in >= week_start]
    weekly_hours = sum(e.get_hours_worked() for e in weekly_entries)
    
    # Monthly stats (current month)
    month_start = today.replace(day=1)
    monthly_entries = [e for e in time_entries if e.clock_in and e.clock_in >= month_start]
    monthly_hours = sum(e.get_hours_worked() for e in monthly_entries)
    
    # Total/semester stats
    semester_hours = sum(e.get_hours_worked() for e in time_entries)
    
    # Absence count
    absences = len([e for e in time_entries if e.status == 'absent'])
    
    return {
        'daily': {
            'date': today.strftime('%Y-%m-%d'),
            'hours': daily_hours,
            'date_range': today.strftime('%b %d, %Y')
        },
        'weekly': {
            'start_date': week_start.strftime('%Y-%m-%d'),
            'end_date': (week_start + timedelta(days=6)).strftime('%Y-%m-%d'),
            'hours': weekly_hours,
            'date_range': f"{week_start.strftime('%b %d')} - {(week_start + timedelta(days=6)).strftime('%b %d, %Y')}"
        },
        'monthly': {
            'month': month_start.strftime('%B %Y'),
            'hours': monthly_hours,
            'date_range': month_start.strftime('%B %Y')
        },
        'semester': {
            'hours': semester_hours,
            'date_range': 'Current Semester'
        },
        'absences': absences
    }

def get_help_desk_assistant_stats():
    """Get attendance stats for all assistants"""
    assistants = HelpDeskAssistant.query.filter_by(active=True).all()
    
    stats = []
    for assistant in assistants:
        student = Student.query.get(assistant.username)
        if student:
            assistant_stats = get_student_stats(assistant.username) or {
                'semester': {'hours': 0},
                'weekly': {'hours': 0}
            }
            
            stats.append({
                'id': assistant.username,
                'name': student.get_name(),
                'image': _resolve_profile_image_url(student),
                'semester_attendance': f"{assistant_stats['semester']['hours']:.1f}",
                'week_attendance': f"{assistant_stats['weekly']['hours']:.1f}"
            })
    
    return stats


def get_lab_assistant_stats():
    """Get attendance stats for all assistants"""
    assistants = LabAssistant.query.filter_by(active=True).all()
    
    stats = []
    for assistant in assistants:
        student = Student.query.get(assistant.username)
        if student:
            assistant_stats = get_student_stats(assistant.username) or {
                'semester': {'hours': 0},
                'weekly': {'hours': 0}
            }
            
            stats.append({
                'id': assistant.username,
                'name': student.get_name(),
                'image': _resolve_profile_image_url(student),
                'semester_attendance': f"{assistant_stats['semester']['hours']:.1f}",
                'week_attendance': f"{assistant_stats['weekly']['hours']:.1f}"
            })
    
    return stats


def get_today_shift(username):
    """
    Get the current or next shift for today for this user
    Returns a dict with shift details including current status
    
    This function also auto-completes any shifts that have ended
    """
    try:
        now = trinidad_now()
        today_start = datetime.combine(now.date(), datetime.min.time())
        today_end = datetime.combine(now.date(), datetime.max.time())
        
        # Auto-complete any sessions that have ended
        auto_complete_time_entries()
        
        # Now check for currently active shifts
        active_shifts = db.session.query(Shift, Allocation)\
            .join(Allocation, Allocation.shift_id == Shift.id)\
            .filter(
                Allocation.username == username,
                Shift.date >= today_start,
                Shift.date <= today_end,
                Shift.start_time <= now,
                Shift.end_time >= now
            ).all()
        
        # If we have an active shift
        if active_shifts:
            shift, allocation = active_shifts[0]
            
            # Check if we have an active time entry
            active_entry = TimeEntry.query.filter_by(
                username=username,
                shift_id=shift.id,
                status='active'
            ).first()
            
            # If we have an active entry, we're clocked in
            if active_entry:
                time_left = shift.end_time - now
                hours = time_left.total_seconds() // 3600
                minutes = (time_left.total_seconds() % 3600) // 60
                
                return {
                    "date": shift.date.strftime("%d %B, %Y"),
                    "start_time": shift.start_time.strftime("%I:%M %p"),
                    "end_time": shift.end_time.strftime("%I:%M %p"),
                    "time": f"{shift.start_time.strftime('%I:%M %p')} to {shift.end_time.strftime('%I:%M %p')}",
                    "status": "active",
                    "starts_now": True,
                    "time_until": f"{int(hours)} hours {int(minutes)} minutes",
                    "shift_id": shift.id
                }
            else:
                # Shift is happening now but we're not clocked in
                return {
                    "date": shift.date.strftime("%d %B, %Y"),
                    "start_time": shift.start_time.strftime("%I:%M %p"),
                    "end_time": shift.end_time.strftime("%I:%M %p"),
                    "time": f"{shift.start_time.strftime('%I:%M %p')} to {shift.end_time.strftime('%I:%M %p')}",
                    "status": "active",
                    "starts_now": False,
                    "shift_id": shift.id
                }
        
        # If no active shift, check for an upcoming shift today
        upcoming_shifts = db.session.query(Shift, Allocation)\
            .join(Allocation, Allocation.shift_id == Shift.id)\
            .filter(
                Allocation.username == username,
                Shift.date >= today_start,
                Shift.date <= today_end,
                Shift.start_time > now
            ).order_by(Shift.start_time).all()
        
        if upcoming_shifts:
            shift, allocation = upcoming_shifts[0]
            
            # Calculate time until shift starts
            time_until = shift.start_time - now
            hours = time_until.total_seconds() // 3600
            minutes = (time_until.total_seconds() % 3600) // 60
            
            return {
                "date": shift.date.strftime("%d %B, %Y"),
                "start_time": shift.start_time.strftime("%I:%M %p"),
                "end_time": shift.end_time.strftime("%I:%M %p"),
                "time": f"{shift.start_time.strftime('%I:%M %p')} to {shift.end_time.strftime('%I:%M %p')}",
                "status": "future",
                "time_until": f"{int(hours)} hours {int(minutes)} minutes",
                "shift_id": shift.id
            }
        
        # Check for completed shifts today (already clocked out)
        completed_shifts = TimeEntry.query.filter(
            TimeEntry.username == username,
            TimeEntry.clock_in >= today_start,
            TimeEntry.clock_in <= today_end,
            TimeEntry.status == 'completed'
        ).all()
        
        if completed_shifts:
            # Get the most recent completed shift
            completed_entry = sorted(completed_shifts, key=lambda x: x.clock_out or datetime.min)[-1]
            shift = Shift.query.get(completed_entry.shift_id) if completed_entry.shift_id else None
            
            if shift:
                return {
                    "date": shift.date.strftime("%d %B, %Y"),
                    "start_time": shift.start_time.strftime("%I:%M %p"),
                    "end_time": shift.end_time.strftime("%I:%M %p"),
                    "time": f"{shift.start_time.strftime('%I:%M %p')} to {shift.end_time.strftime('%I:%M %p')}",
                    "status": "completed",
                    "shift_id": shift.id,
                    "hours_worked": completed_entry.get_hours_worked()
                }
        
        # No shifts today
        return {
            "date": now.strftime("%d %B, %Y"),
            "start_time": "No shift scheduled",
            "end_time": "N/A",
            "time": "No shift scheduled today",
            "status": "none"
        }
    except Exception as e:
        print(f"Error in get_today_shift: {e}")
        import traceback
        traceback.print_exc()
        
        # Return a safe default
        return {
            "date": now.strftime("%d %B, %Y"),
            "start_time": "Error retrieving shifts",
            "end_time": "N/A",
            "time": "Error retrieving shifts",
            "status": "error"
        }

def get_shift_attendance_records(shift_id=None, date_range=None):
    """Get attendance records for a specific shift or date range"""
    query = TimeEntry.query
    
    if shift_id:
        query = query.filter_by(shift_id=shift_id)
    
    if date_range:
        start_date, end_date = date_range
        query = query.filter(TimeEntry.clock_in >= start_date, 
                             TimeEntry.clock_in <= end_date)
    
    records = []
    for entry in query.all():
        student = Student.query.get(entry.username)
        if student:
            record = {
                'staff_id': entry.username,
                'staff_name': student.get_name(),
                'image': _resolve_profile_image_url(student),
                'date': entry.clock_in.strftime('%m-%d-%y') if entry.clock_in else 'ABSENT',
                'day': entry.clock_in.strftime('%A') if entry.clock_in else 'ABSENT',
                'login_time': entry.clock_in.strftime('%I:%M%p') if entry.clock_in else 'ABSENT',
                'logout_time': entry.clock_out.strftime('%I:%M%p') if entry.clock_out else 'ON DUTY' 
                               if entry.status == 'active' else 'ABSENT'
            }
            records.append(record)
    
    return records

def auto_complete_time_entries():
    """
    Automatically complete any active time entries where the shift has ended.
    This function should be called frequently to ensure proper time recording.
    """
    try:
        now = trinidad_now()
        
        # Find all active time entries
        active_entries = TimeEntry.query.filter_by(status='active').all()
        
        if not active_entries:
            return {"success": True, "message": "No active time entries found to auto-complete"}
            
        completed_count = 0
        
        for entry in active_entries:
            # Get the associated shift
            shift = Shift.query.get(entry.shift_id) if entry.shift_id else None
            
            # Skip if no shift is associated
            if not shift:
                continue
                
            # Check if the shift has ended
            if now > shift.end_time:
                print(f"Auto-completing time entry {entry.id} for {entry.username} - shift ended at {shift.end_time}")
                entry.clock_out = shift.end_time
                entry.status = 'completed'
                
                # Calculate hours worked
                hours_worked = (entry.clock_out - entry.clock_in).total_seconds() / 3600
                
                # Update the help desk assistant's total hours
                assistant = HelpDeskAssistant.query.get(entry.username)
                if assistant:
                    assistant.hours_worked += hours_worked
                    db.session.add(assistant)
                
                # Create notification
                shift_details = shift.formatted_time() if hasattr(shift, 'formatted_time') else f"{shift.start_time.strftime('%I:%M %p')} to {shift.end_time.strftime('%I:%M %p')}"
                # Use the auto-completed parameter for the notification
                notify_clock_out(entry.username, shift_details, auto_completed=True)
                
                db.session.add(entry)
                completed_count += 1
                
                print(f"Auto-completed time entry {entry.id} for {entry.username} - {hours_worked:.2f} hours")
        
        if completed_count > 0:
            db.session.commit()
            print(f"Successfully auto-completed {completed_count} time entries")
            
        return {
            "success": True,
            "completed_count": completed_count
        }
            
    except Exception as e:
        db.session.rollback()
        print(f"Error auto-completing time entries: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

def clock_in(username, shift_id=None):
    """Record a clock-in event for a student"""
    try:
        now = trinidad_now()
        
        # First auto-complete any sessions that have ended
        auto_complete_time_entries()
        
        # Check if there's already an active entry
        active_entry = TimeEntry.query.filter_by(username=username, status='active').first()
        if active_entry:
            return {
                'success': False,
                'message': 'You already have an active clock-in record. Please wait for your current session to end or clock out first.'
            }
        
        # If no shift_id provided, try to find the current active shift
        if not shift_id:
            # Find the current active shift for this user
            active_shift = db.session.query(Shift)\
                .join(Allocation, Allocation.shift_id == Shift.id)\
                .filter(
                    Allocation.username == username,
                    Shift.date == now.date(),
                    Shift.start_time <= now,
                    Shift.end_time >= now
                ).first()
                
            if active_shift:
                shift_id = active_shift.id
            else:
                return {
                    'success': False,
                    'message': 'No active shift found for clocking in'
                }
        
        # Verify that this user is assigned to this shift
        allocation = Allocation.query.filter_by(username=username, shift_id=shift_id).first()
        if not allocation:
            return {
                'success': False,
                'message': 'You are not assigned to this shift'
            }
        
        # Get shift to verify the timing
        shift = Shift.query.get(shift_id)
        if not shift:
            return {
                'success': False,
                'message': 'Shift not found'
            }
        
        # Check if the shift is currently active or within acceptable clock-in window
        # Allow clocking in up to 15 minutes early or 30 minutes late
        early_window = shift.start_time - timedelta(minutes=15)
        late_window = shift.start_time + timedelta(minutes=30)
        
        if now < early_window:
            return {
                'success': False,
                'message': f'Too early to clock in. Shift starts at {shift.start_time.strftime("%I:%M %p")}'
            }
        
        if now > shift.end_time:
            return {
                'success': False,
                'message': 'This shift has already ended'
            }
        
        # Create new time entry
        time_entry = TimeEntry(username, now, shift_id, 'active')
        db.session.add(time_entry)
        db.session.commit()
        
        # Send notification
        shift_details = shift.formatted_time() if hasattr(shift, 'formatted_time') else f"{shift.start_time.strftime('%I:%M %p')} to {shift.end_time.strftime('%I:%M %p')}"
        notify_clock_in(username, shift_details)
        
        return {
            'success': True,
            'time_entry_id': time_entry.id,
            'message': 'Clocked in successfully'
        }
    except Exception as e:
        db.session.rollback()
        print(f"Error clocking in: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': f'Error clocking in: {str(e)}'
        }

def clock_out(username):
    """Record a clock-out event for a student"""
    try:
        now = trinidad_now()
        
        # Find the active time entry
        time_entry = TimeEntry.query.filter_by(username=username, status='active').first()
        if not time_entry:
            return {
                'success': False,
                'message': 'No active clock-in record found'
            }
        
        # Get the shift details
        shift = Shift.query.get(time_entry.shift_id) if time_entry.shift_id else None
        
        # Determine the appropriate clock-out time
        clock_out_time = now
        
        # If shift has already ended, use the shift end time instead of current time
        if shift and now > shift.end_time:
            clock_out_time = shift.end_time
            print(f"Shift has already ended. Using shift end time for clock out: {clock_out_time}")
        
        # Update the time entry
        time_entry.clock_out = clock_out_time
        time_entry.status = 'completed'
        db.session.add(time_entry)
        
        # Calculate hours worked
        hours_worked = 0
        if time_entry.clock_in and time_entry.clock_out:
            hours_worked = (time_entry.clock_out - time_entry.clock_in).total_seconds() / 3600
        
        # Update the help desk assistant's total hours
        assistant = HelpDeskAssistant.query.get(username)
        if assistant:
            assistant.hours_worked += hours_worked
            db.session.add(assistant)
            
        db.session.commit()
        
        # Send notification
        shift_details = shift.formatted_time() if shift and hasattr(shift, 'formatted_time') else f"{time_entry.clock_in.strftime('%I:%M %p')} shift"
        notify_clock_out(username, shift_details)
        
        return {
            'success': True,
            'time_entry_id': time_entry.id,
            'hours_worked': hours_worked,
            'message': 'Clocked out successfully'
        }
    except Exception as e:
        db.session.rollback()
        print(f"Error clocking out: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': f'Error clocking out: {str(e)}'
        }

def check_and_complete_abandoned_entry(username):
    """
    Check if there's an abandoned time entry for this user where the shift has ended
    but they never clocked out. This is called when they log in again.
    """
    try:
        # Simply call auto-complete to ensure all ended sessions are completed
        return auto_complete_time_entries()
    except Exception as e:
        print(f"Error checking abandoned entries: {e}")
        return False

def mark_missed_shift(username, shift_id):
    """Mark a shift as missed for a student"""
    try:
        # Get the shift
        shift = Shift.query.get(shift_id)
        if not shift:
            return {
                'success': False,
                'message': 'Shift not found'
            }
        
        # Verify this user is assigned to this shift
        allocation = Allocation.query.filter_by(username=username, shift_id=shift_id).first()
        if not allocation:
            return {
                'success': False,
                'message': 'User not assigned to this shift'
            }
        
        # Check if there's already a time entry for this shift
        existing_entry = TimeEntry.query.filter_by(
            username=username,
            shift_id=shift_id
        ).first()
        
        if existing_entry:
            return {
                'success': False,
                'message': 'There is already a time entry for this shift'
            }
        
        # Create a time entry with absent status
        time_entry = TimeEntry(
            username, 
            shift.start_time, 
            shift_id, 
            'absent'
        )
        db.session.add(time_entry)
        db.session.commit()
        
        # Send notification
        shift_details = shift.formatted_time() if hasattr(shift, 'formatted_time') else f"{shift.start_time.strftime('%I:%M %p')} to {shift.end_time.strftime('%I:%M %p')}"
        notify_missed_shift(username, shift_details)
        
        return {
            'success': True,
            'message': 'Shift marked as missed'
        }
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'message': f'Error marking missed shift: {str(e)}'
        }

def get_shift_history(username, limit=5):
    """Get recent shift history for a user"""
    # Get completed time entries for this user
    time_entries = TimeEntry.query.filter_by(
        username=username,
        status='completed'
    ).order_by(TimeEntry.clock_in.desc()).limit(limit).all()
    
    shift_history = []
    for entry in time_entries:
        shift = Shift.query.get(entry.shift_id) if entry.shift_id else None
        
        if entry.clock_in and entry.clock_out:
            hours_worked = (entry.clock_out - entry.clock_in).total_seconds() / 3600
            hours_str = f"{hours_worked:.1f}"
        else:
            hours_str = "N/A"
            
        shift_history.append({
            "date": entry.clock_in.strftime("%d %b") if entry.clock_in else "Unknown",
            "time_range": f"{entry.clock_in.strftime('%I:%M %p')} to {entry.clock_out.strftime('%I:%M %p')}" if entry.clock_in and entry.clock_out else "N/A",
            "hours": hours_str
        })
    
    return shift_history

def get_time_distribution(username):
    """Calculate time distribution for the week"""
    # Get the start of the current week (Monday)
    now = trinidad_now()
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=7)
    
    # Get all completed time entries for this week
    entries = TimeEntry.query.filter(
        TimeEntry.username == username,
        TimeEntry.status == 'completed',
        TimeEntry.clock_in >= week_start,
        TimeEntry.clock_in < week_end
    ).all()
    
    # Initialize daily hours
    daily_hours = [0, 0, 0, 0, 0]  # Mon-Fri
    day_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    
    # Calculate hours for each day
    for entry in entries:
        if entry.clock_in and entry.clock_out:
            # Get day of week (0=Monday, 4=Friday)
            day_idx = entry.clock_in.weekday()
            if day_idx < 5:  # Only count weekdays
                # Calculate hours
                hours = (entry.clock_out - entry.clock_in).total_seconds() / 3600
                daily_hours[day_idx] += hours
    
    # Check if we have any data to display
    has_data = any(hours > 0 for hours in daily_hours)
    
    # For visualization purposes, set max scale to 8 hours unless we have larger values
    max_hours = max(max(daily_hours) if has_data else 8, 8)
    
    # Calculate percentages (scale to 0-100)
    distribution = []
    
    for i, hours in enumerate(daily_hours):
        # Calculate percentage based on max hours
        # Ensure any day with hours > 0 has at least 10% height for visibility
        percentage = (hours / max_hours) * 100 if max_hours > 0 else 0
        if hours > 0 and percentage < 10:
            percentage = 10
            
        distribution.append({
            "label": day_labels[i],
            "percentage": percentage,
            "hours": hours
        })
    
    print(f"Time distribution data: {distribution}")  # Debug output
    return distribution

def generate_attendance_report(username=None, start_date=None, end_date=None, format='json'):
    """Generate an attendance report for one or all students"""
    try:
        # Set default date range if not provided
        if not start_date:
            # Default to start of current month
            now = trinidad_now()
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if not end_date:
            # Default to now
            end_date = trinidad_now()
        
        # Query time entries
        query = TimeEntry.query
        if username:
            query = query.filter_by(username=username)
        
        query = query.filter(TimeEntry.clock_in >= start_date, 
                             TimeEntry.clock_in <= end_date)
        
        time_entries = query.all()
        
        # Group by student
        student_entries = {}
        for entry in time_entries:
            if entry.username not in student_entries:
                student = Student.query.get(entry.username)
                student_entries[entry.username] = {
                    'student_id': entry.username,
                    'student_name': student.get_name() if student else entry.username,
                    'entries': [],
                    'total_hours': 0,
                    'total_shifts': 0,
                    'completed_shifts': 0,
                    'missed_shifts': 0
                }
            
            # Add entry to student's data
            student_data = student_entries[entry.username]
            student_data['entries'].append(entry.get_json())
            
            # Update totals
            if entry.status == 'completed':
                student_data['total_hours'] += entry.get_hours_worked()
                student_data['completed_shifts'] += 1
            elif entry.status == 'absent':
                student_data['missed_shifts'] += 1
            
            student_data['total_shifts'] += 1
        
        # Format report based on requested format
        if format == 'json':
            return {
                'success': True,
                'report': {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'generated_at': trinidad_now().strftime('%Y-%m-%d %H:%M:%S'),
                    'students': list(student_entries.values())
                }
            }
        else:
            # Other formats could be added (CSV, PDF, etc.)
            return {
                'success': False,
                'message': f'Unsupported report format: {format}'
            }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'Error generating report: {str(e)}'
        }

def get_student_time_entries(username, limit=None):
    """Get recent time entries for a specific student."""
    try:
        query = (
            TimeEntry.query
            .filter_by(username=username)
            .order_by(TimeEntry.clock_in.desc())
        )
        
        if limit:
            query = query.limit(limit)
            
        return query.all()
    except Exception as e:
        print(f"Error fetching time entries for student {username}: {e}")
        return []