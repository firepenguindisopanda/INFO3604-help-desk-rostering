from App.models import Availability, Student, HelpDeskAssistant, LabAssistant
from App.database import db
from datetime import datetime, time
import logging

logger = logging.getLogger(__name__)

def create_availability(username, day_of_week, start_time, end_time):
    new_availability = Availability(username, day_of_week, start_time, end_time)
    db.session.add(new_availability)
    db.session.commit()
    return new_availability


def get_available_staff_for_time(day, time_slot):
    """
    Get all staff members available for a specific day and time
    
    Args:
        day: Day of the week (e.g., "Monday")
        time_slot: Time slot (e.g., "9:00 am")
    
    Returns:
        List of available staff with id and name
    """
    try:
        # Parse time slot to hour for comparison
        hour = _parse_time_slot_to_hour(time_slot)
        if hour is None:
            return []
        
        # Get day index (0=Monday, 6=Sunday)
        day_index = _get_day_index(day)
        if day_index is None:
            return []
        
        # Query available staff for this day and time
        available_staff = db.session.query(Availability).filter(
            Availability.day_of_week == day_index,
            Availability.start_time <= time(hour, 0),
            Availability.end_time > time(hour, 0)
        ).all()
        
        # Build staff list with details
        staff_list = []
        for availability in available_staff:
            # Get staff details from student/assistant tables
            student = Student.query.filter_by(username=availability.username).first()
            if student:
                staff_list.append({
                    "id": availability.username,
                    "name": student.name or availability.username,
                    "type": "student"
                })
        
        return staff_list
        
    except Exception as e:
        logger.error(f"Error getting available staff for {day} at {time_slot}: {e}")
        return []


def check_staff_availability_for_time(staff_id, day, time_slot):
    """
    Check if a specific staff member is available at a given time
    
    Args:
        staff_id: Staff member ID/username
        day: Day of the week
        time_slot: Time slot
    
    Returns:
        Boolean indicating availability
    """
    try:
        # Parse time slot to hour
        hour = _parse_time_slot_to_hour(time_slot)
        if hour is None:
            return False
        
        # Get day index
        day_index = _get_day_index(day)
        if day_index is None:
            return False
        
        # Check availability
        availability = Availability.query.filter(
            Availability.username == staff_id,
            Availability.day_of_week == day_index,
            Availability.start_time <= time(hour, 0),
            Availability.end_time > time(hour, 0)
        ).first()
        
        return availability is not None
        
    except Exception as e:
        logger.error(f"Error checking availability for {staff_id} on {day} at {time_slot}: {e}")
        return False


def batch_check_staff_availability(queries):
    """
    Check availability for multiple staff/time combinations
    
    Args:
        queries: List of query objects with staff_id, day, time
    
    Returns:
        List of results with availability status
    """
    results = []
    
    for query in queries:
        try:
            staff_id = query.get('staff_id')
            day = query.get('day')
            time_slot = query.get('time')
            
            if not all([staff_id, day, time_slot]):
                continue
            
            is_available = check_staff_availability_for_time(staff_id, day, time_slot)
            
            results.append({
                "staff_id": staff_id,
                "day": day,
                "time": time_slot,
                "is_available": is_available
            })
            
        except Exception as e:
            logger.error(f"Error in batch availability check for query {query}: {e}")
            results.append({
                "staff_id": query.get('staff_id'),
                "day": query.get('day'),
                "time": query.get('time'),
                "is_available": False,
                "error": str(e)
            })
    
    return results


def _parse_time_slot_to_hour(time_slot):
    """Parse time slot string to hour integer"""
    try:
        # Handle common formats
        time_slot = time_slot.lower().strip()
        
        # Remove "am" or "pm"
        if 'am' in time_slot or 'pm' in time_slot:
            is_pm = 'pm' in time_slot
            time_part = time_slot.replace('am', '').replace('pm', '').strip()
            
            # Extract hour
            if ':' in time_part:
                hour = int(time_part.split(':')[0])
            else:
                hour = int(time_part)
            
            # Convert to 24-hour format
            if is_pm and hour != 12:
                hour += 12
            elif not is_pm and hour == 12:
                hour = 0
                
            return hour
        else:
            # Assume 24-hour format
            if ':' in time_slot:
                return int(time_slot.split(':')[0])
            else:
                return int(time_slot)
                
    except (ValueError, IndexError):
        logger.error(f"Could not parse time slot: {time_slot}")
        return None


def _get_day_index(day):
    """Convert day name to index (0=Monday, 6=Sunday)"""
    day_mapping = {
        'monday': 0,
        'tuesday': 1,
        'wednesday': 2,
        'thursday': 3,
        'friday': 4,
        'saturday': 5,
        'sunday': 6
    }
    
    return day_mapping.get(day.lower())


