from App.models import Allocation, Shift
from App.database import db
import logging

logger = logging.getLogger(__name__)

def create_allocation(username, schedule, shift):
    new_allocation = Allocation(username, schedule, shift)
    db.session.add(new_allocation)
    db.session.commit()
    return new_allocation


def remove_staff_from_shift(staff_id, day=None, time_slot=None, shift_id=None):
    """
    Remove a staff member from a shift
    
    Args:
        staff_id: Staff member ID/username
        day: Day of the week (optional if shift_id provided) - reserved for future use
        time_slot: Time slot (optional if shift_id provided) - reserved for future use
        shift_id: Specific shift ID (optional)
    
    Returns:
        Dictionary with status and message
    """
    try:
        # If shift_id is provided, use it directly
        if shift_id:
            allocation = Allocation.query.filter_by(
                shift_id=shift_id,
                username=staff_id
            ).first()
        else:
            # Find allocation by staff - could be enhanced to use day/time_slot in future
            # For now, we'll use a simpler approach
            allocation = Allocation.query.filter_by(username=staff_id).first()
        
        if not allocation:
            return {
                'status': 'error',
                'message': f'Staff member {staff_id} not found in specified shift'
            }
        
        # Remove the allocation
        db.session.delete(allocation)
        db.session.commit()
        
        return {
            'status': 'success',
            'message': f'Staff member {staff_id} removed from shift successfully'
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing staff {staff_id} from shift: {e}")
        return {
            'status': 'error',
            'message': f'Failed to remove staff member: {str(e)}'
        }


def assign_staff_to_shift(staff_id, shift_id):
    """
    Assign a staff member to a shift
    
    Args:
        staff_id: Staff member ID/username
        shift_id: Shift ID
    
    Returns:
        Dictionary with status and message
    """
    try:
        # Check if allocation already exists
        existing = Allocation.query.filter_by(
            shift_id=shift_id,
            username=staff_id
        ).first()
        
        if existing:
            return {
                'status': 'error',
                'message': 'Staff member already assigned to this shift'
            }
        
        # Create new allocation
        allocation = Allocation(username=staff_id, shift_id=shift_id)
        db.session.add(allocation)
        db.session.commit()
        
        return {
            'status': 'success',
            'message': f'Staff member {staff_id} assigned to shift successfully'
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error assigning staff {staff_id} to shift {shift_id}: {e}")
        return {
            'status': 'error',
            'message': f'Failed to assign staff member: {str(e)}'
        }
