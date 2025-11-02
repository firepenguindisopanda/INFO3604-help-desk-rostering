"""
Integration module for schedule configuration with the linear programming scheduler.

This module bridges the schedule configuration system with the existing
scheduler_lp.linear_scheduler module, providing functions to:
1. Convert ScheduleConfig to Shift objects
2. Generate schedules using active configuration
3. Integrate with existing Flask schedule controllers
"""

from datetime import time, timedelta, datetime, date
from typing import List, Dict, Optional, Sequence
import logging

from scheduler_lp.linear_scheduler import (
    Shift, CourseDemand, Assistant, ScheduleResult, 
    solve_helpdesk_schedule, SchedulerConfig
)
from App.controllers import schedule_config as config_controller
from App.models import ScheduleConfig

logger = logging.getLogger(__name__)


def config_to_shifts(config: ScheduleConfig, course_demands: Optional[List[Dict]] = None) -> List[Shift]:
    """
    Convert a ScheduleConfig to a list of Shift objects for the scheduler.
    
    Args:
        config: The schedule configuration
        course_demands: Optional list of course demands per shift
                       Format: [{'course_code': str, 'tutors_required': int, 'weight': float}]
    
    Returns:
        List of Shift objects compatible with scheduler_lp
    """
    shifts = []
    shift_delta = timedelta(minutes=config.shift_duration_minutes)
    
    # Default course demands if none provided (simplified for basic scheduling)
    default_demands = course_demands or []
    
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
            
            # Create course demands for this shift
            demands = [
                CourseDemand(
                    course_code=demand['course_code'],
                    tutors_required=demand.get('tutors_required', 1),
                    weight=demand.get('weight', 1.0)
                )
                for demand in default_demands
            ]
            
            shift = Shift(
                id=f'config_{config.id}_day{day_num}_shift{shift_counter}',
                day_of_week=day_num,
                start=current_time,
                end=shift_end,
                course_demands=demands,
                min_staff=config.staff_per_shift,
                max_staff=config.staff_per_shift,  # Use same value for both for simplicity
                metadata={
                    'config_id': str(config.id),
                    'config_name': config.name,
                    'duration_minutes': str(config.shift_duration_minutes)
                }
            )
            
            shifts.append(shift)
            current_time = shift_end
            shift_counter += 1
    
    logger.info(f"Generated {len(shifts)} shifts from config '{config.name}'")
    return shifts


def generate_schedule_from_active_config(
    assistants: Sequence[Assistant], 
    course_demands: Optional[List[Dict]] = None,
    scheduler_config: Optional[SchedulerConfig] = None
) -> Dict:
    """
    Generate a schedule using the active configuration.
    
    Args:
        assistants: List of Assistant objects
        course_demands: Optional course demands to apply to shifts
        scheduler_config: Optional scheduler configuration (uses default if None)
    
    Returns:
        Dictionary containing schedule result and metadata
        
    Raises:
        ValueError: If no active configuration found
    """
    # Get active configuration
    config = config_controller.get_active_config()
    if not config:
        raise ValueError("No active schedule configuration found")
    
    # Convert config to shifts
    shifts = config_to_shifts(config, course_demands)
    
    if not shifts:
        raise ValueError(f"No shifts generated from configuration '{config.name}'")
    
    # Use default scheduler config if none provided
    if scheduler_config is None:
        scheduler_config = SchedulerConfig(
            course_shortfall_penalty=1.0,
            min_hours_penalty=10.0,
            max_hours_penalty=5.0,
            understaffed_penalty=100.0,
            extra_hours_penalty=5.0,
            baseline_hours_target=config.shift_duration_minutes * len(shifts) // (60 * len(assistants)) if assistants else 4,
            allow_minimum_violation=True  # Be flexible for configuration-based scheduling
        )
    
    try:
        # Solve the scheduling problem
        result = solve_helpdesk_schedule(assistants, shifts, config=scheduler_config)
        
        return {
            'status': 'success',
            'config_used': config.to_dict(),
            'shifts_generated': len(shifts),
            'schedule_result': result,
            'assignments': result.assignments,
            'assistant_hours': result.assistant_hours,
            'objective_value': result.objective_value,
            'solver_status': result.status,
            'metadata': {
                'total_hours_scheduled': sum(result.assistant_hours.values()),
                'shifts_coverage': _calculate_coverage_stats(shifts, result),
                'configuration_summary': config_controller.get_config_summary(config)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to generate schedule from config '{config.name}': {e}")
        return {
            'status': 'error',
            'config_used': config.to_dict(),
            'shifts_generated': len(shifts),
            'error': str(e),
            'schedule_result': None
        }


def validate_config_for_scheduling(config: ScheduleConfig, assistants: Sequence[Assistant]) -> Dict:
    """
    Validate that a configuration can be used for scheduling with given assistants.
    
    Args:
        config: The schedule configuration to validate
        assistants: Available assistants
    
    Returns:
        Dictionary with validation results
    """
    validation = {
        'valid': True,
        'warnings': [],
        'errors': [],
        'stats': {}
    }
    
    try:
        # Generate shifts from config
        shifts = config_to_shifts(config)
        
        if not shifts:
            validation['valid'] = False
            validation['errors'].append("Configuration generates no shifts")
            return validation
        
        validation['stats']['total_shifts'] = len(shifts)
        validation['stats']['total_hours_needed'] = sum(shift.duration_hours * shift.min_staff for shift in shifts)
        
        # Check assistant availability
        available_assistants = []
        for shift in shifts:
            available_for_shift = [
                assistant for assistant in assistants 
                if assistant.is_available(shift)
            ]
            available_assistants.append(len(available_for_shift))
        
        validation['stats']['min_available_per_shift'] = min(available_assistants) if available_assistants else 0
        validation['stats']['max_available_per_shift'] = max(available_assistants) if available_assistants else 0
        validation['stats']['avg_available_per_shift'] = sum(available_assistants) / len(available_assistants) if available_assistants else 0
        
        # Check if minimum staffing can be met
        understaffed_shifts = [
            i for i, available in enumerate(available_assistants)
            if available < shifts[i].min_staff
        ]
        
        if understaffed_shifts:
            validation['valid'] = False
            validation['errors'].append(
                f"{len(understaffed_shifts)} shifts cannot meet minimum staffing requirements"
            )
        
        # Check total hours feasibility
        total_assistant_hours = sum(
            assistant.max_hours or 40 for assistant in assistants  # Default 40 hours max
        )
        total_hours_needed = validation['stats']['total_hours_needed']
        
        if total_hours_needed > total_assistant_hours:
            validation['warnings'].append(
                f"Total hours needed ({total_hours_needed:.1f}) exceeds total available hours ({total_assistant_hours:.1f})"
            )
        
        # Check for reasonable distribution
        if assistants:
            avg_hours_per_assistant = total_hours_needed / len(assistants)
            if avg_hours_per_assistant < 2:
                validation['warnings'].append("Very low average hours per assistant - consider fewer assistants")
            elif avg_hours_per_assistant > 20:
                validation['warnings'].append("High average hours per assistant - consider more assistants")
        
    except Exception as e:
        validation['valid'] = False
        validation['errors'].append(f"Validation failed: {str(e)}")
    
    return validation


def _calculate_coverage_stats(shifts: List[Shift], result: ScheduleResult) -> Dict:
    """Calculate coverage statistics for the scheduled shifts."""
    stats = {
        'total_shifts': len(shifts),
        'fully_staffed': 0,
        'understaffed': 0,
        'overstaffed': 0,
        'coverage_rate': 0.0
    }
    
    for shift in shifts:
        assigned_count = sum(
            1 for assignment in result.assignments
            if assignment.shift_id == shift.id
        )
        
        if assigned_count == shift.min_staff:
            stats['fully_staffed'] += 1
        elif assigned_count < shift.min_staff:
            stats['understaffed'] += 1
        else:
            stats['overstaffed'] += 1
    
    if stats['total_shifts'] > 0:
        stats['coverage_rate'] = stats['fully_staffed'] / stats['total_shifts']
    
    return stats


# Convenience functions for common scheduling scenarios
def create_simple_schedule_config(
    name: str,
    operating_days: List[int],
    start_hour: int,
    end_hour: int,
    shift_duration_hours: int = 1,
    staff_per_shift: int = 1
) -> ScheduleConfig:
    """
    Create a simple schedule configuration with hour-based parameters.
    
    Args:
        name: Configuration name
        operating_days: List of day numbers (0=Monday, 6=Sunday)
        start_hour: Start hour (24-hour format)
        end_hour: End hour (24-hour format)
        shift_duration_hours: Duration of each shift in hours
        staff_per_shift: Number of staff per shift
    
    Returns:
        Created ScheduleConfig object
    """
    return config_controller.create_schedule_config(
        name=name,
        operating_days=operating_days,
        start_time=time(hour=start_hour),
        end_time=time(hour=end_hour),
        shift_duration_minutes=shift_duration_hours * 60,
        staff_per_shift=staff_per_shift,
        is_active=True
    )


def get_config_based_schedule_summary(config_id: Optional[int] = None) -> Dict:
    """
    Get a summary of schedule generation capability for a configuration.
    
    Args:
        config_id: Specific config ID, or None for active config
    
    Returns:
        Dictionary with configuration and scheduling summary
    """
    if config_id:
        config = config_controller.get_schedule_config(config_id)
    else:
        config = config_controller.get_active_config()
    
    if not config:
        return {'error': 'No configuration found'}
    
    summary = config_controller.get_config_summary(config)
    shifts = config_to_shifts(config)
    
    summary['scheduler_info'] = {
        'shifts_generated': len(shifts),
        'day_distribution': {},
        'time_slots': []
    }
    
    # Calculate day distribution
    for shift in shifts:
        day = shift.day_of_week
        summary['scheduler_info']['day_distribution'][day] = summary['scheduler_info']['day_distribution'].get(day, 0) + 1
    
    # Get unique time slots
    time_slots = set()
    for shift in shifts:
        time_slots.add(f"{shift.start.strftime('%H:%M')}-{shift.end.strftime('%H:%M')}")
    summary['scheduler_info']['time_slots'] = sorted(list(time_slots))
    
    return summary