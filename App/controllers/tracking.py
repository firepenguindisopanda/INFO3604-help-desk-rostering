from App.models import TimeEntry, Student, HelpDeskAssistant, Shift, Allocation
from App.database import db
from datetime import datetime, timedelta, time, date
from App.controllers.notification import notify_clock_in, notify_clock_out, notify_missed_shift

def get_student_stats(username):
    """Get attendance statistics for a student"""
    # Get the student
    student = Student.query.get(username)
    if not student:
        return None
        
    # Get time entries for this student
    time_entries = TimeEntry.query.filter_by(username=username).all()
    
    # Calculate stats
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Daily stats (today)
    daily_entries = [e for e in time_entries if e.clock_in >= today]
    daily_hours = sum(e.get_hours_worked() for e in daily_entries)
    
    # Weekly stats (last 7 days)
    week_start = today - timedelta(days=today.weekday())
    weekly_entries = [e for e in time_entries if e.clock_in >= week_start]
    weekly_hours = sum(e.get_hours_worked() for e in weekly_entries)
    
    # Monthly stats (current month)
    month_start = today.replace(day=1)
    monthly_entries = [e for e in time_entries if e.clock_in >= month_start]
    monthly_hours = sum(e.get_hours_worked() for e in monthly_entries)
    
    # Total/semester stats
    semester_hours = sum(e.get_hours_worked() for e in time_entries)
    
    # Absence count
    absences = len([e for e in time_entries if e.status == 'absent'])
    
    return {
        'daily': {
            'date': today.strftime('%Y-%m-%d'),
            'hours': daily_hours
        },
        'weekly': {
            'start_date': week_start.strftime('%Y-%m-%d'),
            'end_date': (week_start + timedelta(days=6)).strftime('%Y-%m-%d'),
            'hours': weekly_hours
        },
        'monthly': {
            'month': month_start.strftime('%B %Y'),
            'hours': monthly_hours
        },
        'semester': {
            'hours': semester_hours
        },
        'absences': absences
    }

def get_all_assistant_stats():
    """Get attendance stats for all assistants"""
    assistants = HelpDeskAssistant.query.filter_by(active=True).all()
    
    stats = []
    for assistant in assistants:
        student = Student.query.get(assistant.username)
        if student:
            assistant_stats = get_student_stats(assistant.username)
            
            stats.append({
                'id': assistant.username,
                'name': student.get_name(),
                'image': '/static/images/DefaultAvatar.jpg',
                'semester_attendance': f"{assistant_stats['semester']['hours']:.1f}",
                'week_attendance': f"{assistant_stats['weekly']['hours']:.1f}"
            })
    
    return stats

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
                'image': '/static/images/DefaultAvatar.jpg',
                'date': entry.clock_in.strftime('%m-%d-%y'),
                'day': entry.clock_in.strftime('%A'),
                'login_time': entry.clock_in.strftime('%I:%M%p') if entry.clock_in else 'ABSENT',
                'logout_time': entry.clock_out.strftime('%I:%M%p') if entry.clock_out else 'ON DUTY' 
                               if entry.status == 'active' else 'ABSENT'
            }
            records.append(record)
    
    return records

def clock_in(username, shift_id=None):
    """Record a clock-in event for a student"""
    try:
        now = datetime.utcnow()
        
        # Check if there's already an active entry
        active_entry = TimeEntry.query.filter_by(username=username, status='active').first()
        if active_entry:
            return {
                'success': False,
                'message': 'You already have an active clock-in record'
            }
        
        # Create new time entry
        time_entry = TimeEntry(username, now, shift_id, 'active')
        db.session.add(time_entry)
        db.session.commit()
        
        # Send notification
        shift = Shift.query.get(shift_id) if shift_id else None
        shift_details = shift.formatted_time() if shift else f"{now.strftime('%I:%M %p')} shift"
        notify_clock_in(username, shift_details)
        
        return {
            'success': True,
            'time_entry_id': time_entry.id,
            'message': 'Clocked in successfully'
        }
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'message': f'Error clocking in: {str(e)}'
        }

def clock_out(username):
    """Record a clock-out event for a student"""
    try:
        now = datetime.utcnow()
        
        # Find the active time entry
        time_entry = TimeEntry.query.filter_by(username=username, status='active').first()
        if not time_entry:
            return {
                'success': False,
                'message': 'No active clock-in record found'
            }
        
        # Update the time entry
        time_entry.complete(now)
        db.session.add(time_entry)
        db.session.commit()
        
        # Send notification
        shift = Shift.query.get(time_entry.shift_id) if time_entry.shift_id else None
        shift_details = shift.formatted_time() if shift else f"{time_entry.clock_in.strftime('%I:%M %p')} shift"
        notify_clock_out(username, shift_details)
        
        return {
            'success': True,
            'time_entry_id': time_entry.id,
            'hours_worked': time_entry.get_hours_worked(),
            'message': 'Clocked out successfully'
        }
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'message': f'Error clocking out: {str(e)}'
        }

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
        shift_details = shift.formatted_time()
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

def generate_attendance_report(username=None, start_date=None, end_date=None, format='json'):
    """Generate an attendance report for one or all students"""
    try:
        # Set default date range if not provided
        if not start_date:
            # Default to start of current month
            now = datetime.utcnow()
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if not end_date:
            # Default to now
            end_date = datetime.utcnow()
        
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
                    'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
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

def create_test_time_entries():
    """Create a few test time entries for demonstration purposes"""
    try:
        from datetime import datetime, timedelta
        from App.models import TimeEntry, Student, Shift
        
        # Get a student
        students = Student.query.all()
        if not students:
            print("No students found to create time entries for")
            return False
            
        student = students[0]
        
        # Create a shift if none exist
        shifts = Shift.query.all()
        if not shifts:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Create a morning shift (9am-12pm)
            morning_start = today.replace(hour=9, minute=0)
            morning_end = today.replace(hour=12, minute=0)
            morning_shift = Shift(today, morning_start, morning_end)
            db.session.add(morning_shift)
            
            # Create an afternoon shift (1pm-4pm)
            afternoon_start = today.replace(hour=13, minute=0)
            afternoon_end = today.replace(hour=16, minute=0)
            afternoon_shift = Shift(today, afternoon_start, afternoon_end)
            db.session.add(afternoon_shift)
            
            db.session.commit()
            shifts = [morning_shift, afternoon_shift]
        
        # Create a time entry for today
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Create a completed time entry (clock in and out)
        clock_in_time = today.replace(hour=9, minute=15)
        clock_out_time = today.replace(hour=11, minute=45)
        
        entry = TimeEntry(student.username, clock_in_time, shifts[0].id if shifts else None, 'completed')
        entry.clock_out = clock_out_time
        db.session.add(entry)
        
        # Create an active time entry (only clock in)
        active_clock_in = today.replace(hour=13, minute=30)
        active_entry = TimeEntry(student.username, active_clock_in, shifts[1].id if len(shifts) > 1 else None, 'active')
        db.session.add(active_entry)
        
        db.session.commit()
        
        print(f"Created test time entries for {student.username}")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error creating test time entries: {e}")
        return False