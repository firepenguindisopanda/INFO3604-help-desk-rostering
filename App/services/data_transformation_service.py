"""
Data transformation service for converting between database models and scheduler data structures.

This service follows the MVC pattern by providing a clean interface for
transforming data between the domain models and the external scheduler library.
"""

from typing import List, Sequence, Dict, Optional
from datetime import datetime, time, timedelta
import logging

from scheduler_lp import Assistant, Shift, CourseDemand, AvailabilityWindow
from App.models import (
    HelpDeskAssistant, LabAssistant, Student, Availability, 
    Course, Shift as DbShift, Schedule
)

logger = logging.getLogger(__name__)


class DataTransformationService:
    """
    Service for transforming Flask application data to scheduler_lp data structures.
    
    This service provides clean separation between the Flask domain models
    and the scheduler library's data structures.
    """

    @staticmethod
    def assistants_to_scheduler_format(
        assistants: Sequence, 
        assistant_type: str = 'helpdesk',
        baseline_hours_target: int = 6
    ) -> List[Assistant]:
        """
        Convert database assistant models to scheduler Assistant objects.
        
        Implements fairness baseline logic:
        - Calculate feasible shifts each assistant can work
        - Set baseline hours as min(6, feasible_hours)
        - This ensures assistants with <6 hours availability get all they can work
        
        Args:
            assistants: List of HelpDeskAssistant or LabAssistant objects
            assistant_type: Type of assistant ('helpdesk' or 'lab')
            baseline_hours_target: Target baseline hours (default 6)
            
        Returns:
            List of scheduler_lp.Assistant objects
        """
        scheduler_assistants = []
        
        for assistant in assistants:
            if not assistant.active:
                continue
                
            try:
                # Get student record for availability and basic info
                student = Student.query.get(assistant.username)
                if not student:
                    logger.warning(f"No student record found for assistant {assistant.username}")
                    continue
                
                # Get course capabilities
                courses = [cap.course_code for cap in assistant.course_capabilities]
                
                # Get availability windows
                availability_windows = DataTransformationService._get_availability_windows(
                    assistant.username
                )
                
                # Calculate feasible hours for this assistant
                # (This is a simplified calculation - in practice, would check against actual shifts)
                total_available_hours = sum(
                    DataTransformationService._calculate_window_hours(window)
                    for window in availability_windows
                )
                
                # Apply baseline fairness logic: min(target, available_hours)
                baseline_hours = min(baseline_hours_target, total_available_hours)
                
                # Set max hours based on assistant type and availability
                if assistant_type == 'helpdesk':
                    max_hours = min(getattr(assistant, 'hours_maximum', 20.0), total_available_hours)
                elif assistant_type == 'lab':
                    max_hours = min(getattr(assistant, 'hours_maximum', 12.0), total_available_hours)
                else:
                    max_hours = total_available_hours
                
                scheduler_assistant = Assistant(
                    id=assistant.username,
                    courses=courses,
                    availability=availability_windows,
                    min_hours=baseline_hours,  # This becomes the baseline target
                    max_hours=max_hours,
                    cost_per_hour=0.0  # Not using cost optimization currently
                )
                
                scheduler_assistants.append(scheduler_assistant)
                logger.debug(
                    f"Assistant {assistant.username}: baseline={baseline_hours:.1f}h, "
                    f"max={max_hours:.1f}h, available={total_available_hours:.1f}h"
                )
                
            except Exception as e:
                logger.error(f"Error converting assistant {assistant.username}: {e}")
                continue
        
        logger.info(f"Converted {len(scheduler_assistants)} assistants to scheduler format")
        return scheduler_assistants

    @staticmethod
    def _get_availability_windows(username: str) -> List[AvailabilityWindow]:
        """
        Get availability windows for a specific assistant.
        
        Args:
            username: Assistant's username
            
        Returns:
            List of AvailabilityWindow objects
        """
        availabilities = Availability.query.filter_by(username=username).all()
        
        windows = []
        for avail in availabilities:
            try:
                window = AvailabilityWindow(
                    day_of_week=avail.day_of_week,
                    start=avail.start_time,
                    end=avail.end_time
                )
                windows.append(window)
            except ValueError as e:
                logger.warning(f"Invalid availability window for {username}: {e}")
                continue
        
        return windows

    @staticmethod
    def _calculate_window_hours(window: AvailabilityWindow) -> float:
        """
        Calculate the number of hours in an availability window.
        
        Args:
            window: AvailabilityWindow object
            
        Returns:
            Hours as a float
        """
        from datetime import datetime, date
        
        # Use a dummy date to calculate time difference
        dummy_date = date(2000, 1, 1)
        start_dt = datetime.combine(dummy_date, window.start)
        end_dt = datetime.combine(dummy_date, window.end)
        
        # Handle case where end time is before start time (crosses midnight)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
        
        delta = end_dt - start_dt
        return delta.total_seconds() / 3600.0

    @staticmethod
    def generate_shifts_for_schedule(
        schedule: Schedule,
        schedule_type: str = 'helpdesk'
    ) -> List[Shift]:
        """
        Generate shift objects for a given schedule and type.
        
        Args:
            schedule: Schedule database object
            schedule_type: Type of schedule ('helpdesk' or 'lab')
            
        Returns:
            List of scheduler_lp.Shift objects
        """
        shifts = []
        current_date = schedule.start_date
        
        # Get all courses for demand generation
        all_courses = Course.query.all()
        
        while current_date <= schedule.end_date:
            day_of_week = current_date.weekday()
            
            # Skip weekends for helpdesk, Sunday for lab
            should_skip = (
                (schedule_type == 'helpdesk' and day_of_week >= 5) or
                (schedule_type == 'lab' and day_of_week == 6)
            )
            
            if should_skip:
                current_date += timedelta(days=1)
                continue
            
            # Generate shifts based on schedule type
            if schedule_type == 'helpdesk':
                shifts.extend(
                    DataTransformationService._generate_helpdesk_shifts(
                        current_date, all_courses
                    )
                )
            elif schedule_type == 'lab':
                shifts.extend(
                    DataTransformationService._generate_lab_shifts(
                        current_date, all_courses
                    )
                )
            
            current_date += timedelta(days=1)
        
        logger.info(f"Generated {len(shifts)} shifts for {schedule_type} schedule")
        return shifts

    @staticmethod
    def _generate_helpdesk_shifts(
        shift_date: datetime, 
        courses: List[Course]
    ) -> List[Shift]:
        """Generate hourly help desk shifts for a given date."""
        shifts = []
        
        # Help desk runs 9am-5pm (8 hours)
        for hour in range(9, 17):
            shift_id = f"helpdesk_{shift_date.strftime('%Y%m%d')}_{hour:02d}"
            
            # Create course demands (default 2 tutors per course)
            course_demands = [
                CourseDemand(
                    course_code=course.code,
                    tutors_required=2,
                    weight=2.0
                )
                for course in courses
            ]
            
            shift = Shift(
                id=shift_id,
                day_of_week=shift_date.weekday(),
                start=time(hour=hour),
                end=time(hour=hour + 1),
                course_demands=course_demands,
                min_staff=2,
                max_staff=3,
                metadata={
                    'date': shift_date.isoformat(),
                    'type': 'helpdesk'
                }
            )
            
            shifts.append(shift)
        
        return shifts

    @staticmethod
    def _generate_lab_shifts(
        shift_date: datetime, 
        courses: List[Course]
    ) -> List[Shift]:
        """Generate 4-hour lab shifts for a given date."""
        shifts = []
        
        # Lab runs in 4-hour blocks: 8am-12pm, 12pm-4pm, 4pm-8pm
        time_blocks = [
            (8, 12),   # 8am-12pm
            (12, 16),  # 12pm-4pm  
            (16, 20)   # 4pm-8pm
        ]
        
        for start_hour, end_hour in time_blocks:
            shift_id = f"lab_{shift_date.strftime('%Y%m%d')}_{start_hour:02d}"
            
            # Create course demands (default 2 tutors per course)
            course_demands = [
                CourseDemand(
                    course_code=course.code,
                    tutors_required=2,
                    weight=2.0
                )
                for course in courses
            ]
            
            shift = Shift(
                id=shift_id,
                day_of_week=shift_date.weekday(),
                start=time(hour=start_hour),
                end=time(hour=end_hour),
                course_demands=course_demands,
                min_staff=2,
                max_staff=3,
                metadata={
                    'date': shift_date.isoformat(),
                    'type': 'lab'
                }
            )
            
            shifts.append(shift)
        
        return shifts

    @staticmethod
    def schedule_result_to_database(
        result,
        schedule: Schedule,
        shifts_mapping: Dict[str, DbShift]
    ) -> Dict[str, any]:
        """
        Convert scheduler result back to database allocations.
        
        Args:
            result: ScheduleResult from scheduler_lp
            schedule: Database Schedule object
            shifts_mapping: Mapping from scheduler shift IDs to database Shift objects
            
        Returns:
            Dictionary with statistics about the conversion
        """
        from App.models import Allocation
        from App.database import db
        
        stats = {
            'assignments_created': 0,
            'assignments_failed': 0,
            'status': result.status,
            'objective_value': result.objective_value
        }
        
        if result.status not in ['Optimal', 'Feasible']:
            logger.warning(f"Scheduler returned non-optimal status: {result.status}")
            return stats
        
        # Clear existing allocations for this schedule
        from App.controllers.schedule import clear_allocations_for_shifts
        db_shifts = list(shifts_mapping.values())
        clear_allocations_for_shifts(db_shifts)
        
        # Create new allocations from the result
        for assistant_id, shift_id in result.assignments:
            try:
                db_shift = shifts_mapping.get(shift_id)
                if not db_shift:
                    logger.warning(f"No database shift found for scheduler shift {shift_id}")
                    stats['assignments_failed'] += 1
                    continue
                
                allocation = Allocation(
                    username=assistant_id,
                    shift_id=db_shift.id,
                    schedule_id=schedule.id
                )
                
                db.session.add(allocation)
                stats['assignments_created'] += 1
                
            except Exception as e:
                logger.error(f"Error creating allocation for {assistant_id} -> {shift_id}: {e}")
                stats['assignments_failed'] += 1
                continue
        
        # Commit all allocations
        try:
            db.session.commit()
            logger.info(f"Successfully created {stats['assignments_created']} allocations")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error committing allocations: {e}")
            stats['assignments_failed'] += stats['assignments_created']
            stats['assignments_created'] = 0
        
        return stats