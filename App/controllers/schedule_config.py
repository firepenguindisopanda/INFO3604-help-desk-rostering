from App.models import ScheduleConfig
from App.database import db
from datetime import time, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def create_schedule_config(
    name: str,
    operating_days: List[int],
    start_time: time,
    end_time: time,
    shift_duration_minutes: int = 60,
    staff_per_shift: int = 1,
    is_active: bool = True
) -> ScheduleConfig:
    """
    Single responsibility: Create and validate schedule configuration.
    
    Args:
        name: Human-readable name for the configuration
        operating_days: List of integers 0-6 (Monday-Sunday)
        start_time: Start time for operations
        end_time: End time for operations
        shift_duration_minutes: Duration of each shift in minutes
        staff_per_shift: Number of staff required per shift
        is_active: Whether this configuration is active
    
    Returns:
        ScheduleConfig: The created configuration
    
    Raises:
        ValueError: If validation fails
    """
    config = ScheduleConfig(
        name=name,
        operating_days=operating_days,
        start_time=start_time,
        end_time=end_time,
        shift_duration_minutes=shift_duration_minutes,
        staff_per_shift=staff_per_shift,
        is_active=is_active
    )
    
    # Fail fast: Validate before saving
    config.validate()
    
    # If this is set as active, deactivate all others
    if is_active:
        deactivate_all_configs()
    
    db.session.add(config)
    db.session.commit()
    
    logger.info(f"Created schedule configuration: {name}")
    return config


def get_all_schedule_configs() -> List[ScheduleConfig]:
    """Get all schedule configurations."""
    return ScheduleConfig.query.order_by(ScheduleConfig.created_at.desc()).all()


def get_schedule_config(config_id: int) -> Optional[ScheduleConfig]:
    """Get a specific schedule configuration by ID."""
    return ScheduleConfig.query.get(config_id)


def get_active_config() -> Optional[ScheduleConfig]:
    """
    Abstraction: Hide query details for getting active configuration.
    
    Returns:
        ScheduleConfig: The active configuration, or None if none exists
    """
    return ScheduleConfig.query.filter_by(is_active=True).first()


def update_schedule_config(config_id: int, **kwargs) -> ScheduleConfig:
    """
    Encapsulation: Controlled update of configuration.
    
    Args:
        config_id: ID of the configuration to update
        **kwargs: Fields to update
    
    Returns:
        ScheduleConfig: The updated configuration
    
    Raises:
        ValueError: If validation fails
        NotFoundError: If configuration doesn't exist
    """
    config = ScheduleConfig.query.get_or_404(config_id)
    
    # Handle activation logic
    if kwargs.get('is_active') and not config.is_active:
        deactivate_all_configs()
    
    # Update fields
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    # Fail fast: Validate after updates
    config.validate()
    
    db.session.commit()
    logger.info(f"Updated schedule configuration: {config.name}")
    return config


def delete_schedule_config(config_id: int) -> bool:
    """
    Delete a schedule configuration.
    
    Args:
        config_id: ID of the configuration to delete
    
    Returns:
        bool: True if deleted, False if not found
    """
    config = ScheduleConfig.query.get(config_id)
    if not config:
        return False
    
    db.session.delete(config)
    db.session.commit()
    
    logger.info(f"Deleted schedule configuration: {config.name}")
    return True


def deactivate_all_configs():
    """Helper function to deactivate all configurations."""
    ScheduleConfig.query.update({'is_active': False})
    db.session.flush()  # Don't commit yet, let the caller handle it


def activate_config(config_id: int) -> ScheduleConfig:
    """
    Activate a specific configuration and deactivate all others.
    
    Args:
        config_id: ID of the configuration to activate
    
    Returns:
        ScheduleConfig: The activated configuration
    """
    # Deactivate all first
    deactivate_all_configs()
    
    # Activate the specified one
    config = ScheduleConfig.query.get_or_404(config_id)
    config.is_active = True
    
    db.session.commit()
    logger.info(f"Activated schedule configuration: {config.name}")
    return config


def generate_shifts_from_config(config: ScheduleConfig) -> List[Dict]:
    """
    Reusability: Convert configuration into shift definitions.
    Strategy pattern: Encapsulates shift generation algorithm.
    
    Args:
        config: The schedule configuration
    
    Returns:
        List[Dict]: List of shift definitions compatible with scheduler
    """
    shifts = []
    shift_delta = timedelta(minutes=config.shift_duration_minutes)
    
    for day_num in sorted(config.operating_days):
        current_time = config.start_time
        shift_counter = 1
        
        while True:
            # Calculate shift end time
            start_dt = timedelta(hours=current_time.hour, minutes=current_time.minute)
            end_dt = start_dt + shift_delta
            
            # Convert back to time object
            total_seconds = int(end_dt.total_seconds())
            end_hour = total_seconds // 3600
            end_minute = (total_seconds % 3600) // 60
            
            # Handle overflow (past midnight)
            if end_hour >= 24:
                break
            
            shift_end = time(hour=end_hour, minute=end_minute)
            
            # Check if shift fits within operating hours
            if shift_end > config.end_time:
                break
            
            shifts.append({
                'id': f'day{day_num}_shift{shift_counter}',
                'day_of_week': day_num,
                'start': current_time,
                'end': shift_end,
                'min_staff': config.staff_per_shift,
                'max_staff': config.staff_per_shift,
                'duration_minutes': config.shift_duration_minutes
            })
            
            current_time = shift_end
            shift_counter += 1
    
    logger.info(f"Generated {len(shifts)} shifts from config: {config.name}")
    return shifts


def get_config_summary(config: ScheduleConfig) -> Dict:
    """
    Get a summary of a configuration including generated shifts.
    
    Args:
        config: The schedule configuration
    
    Returns:
        Dict: Summary with config details and shift count
    """
    shifts = generate_shifts_from_config(config)
    
    return {
        'config': config.to_dict(),
        'shift_count': len(shifts),
        'total_hours_per_week': len(shifts) * config.shift_duration_minutes / 60,
        'operating_days_names': config.get_day_names(),
        'time_range': config.get_formatted_time_range()
    }


def create_default_config() -> ScheduleConfig:
    """
    Create a default configuration matching the specified criteria:
    - Monday to Wednesday (days 0, 1, 2)
    - 10 AM to 2 PM
    - 1 hour shifts
    - 1 person per shift
    """
    try:
        return create_schedule_config(
            name="Default Help Desk Schedule",
            operating_days=[0, 1, 2],  # Mon-Wed
            start_time=time(10, 0),    # 10:00 AM
            end_time=time(14, 0),      # 2:00 PM
            shift_duration_minutes=60,  # 1 hour
            staff_per_shift=1,         # 1 person
            is_active=True
        )
    except Exception as e:
        logger.error(f"Failed to create default config: {e}")
        raise


# Helper functions for API responses
def get_configs_dict() -> List[Dict]:
    """Get all configurations as dictionaries for API responses."""
    configs = get_all_schedule_configs()
    return [config.to_dict() for config in configs]


def is_valid_operating_days(days: List[int]) -> bool:
    """Validate operating days list."""
    if not isinstance(days, list) or not days:
        return False
    return all(isinstance(day, int) and 0 <= day <= 6 for day in days)


def validate_time_range(start_time: time, end_time: time) -> bool:
    """Validate that end time is after start time."""
    return end_time > start_time