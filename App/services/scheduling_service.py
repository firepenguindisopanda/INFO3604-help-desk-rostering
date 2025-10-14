"""
Scheduling service using PuLP linear programming optimization.

This service provides the core scheduling logic for both help desk and lab
assistant schedules using the PuLP library instead of OR-Tools.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

from scheduler_lp import solve_helpdesk_schedule, SchedulerConfig
from App.models import Schedule, Shift, HelpDeskAssistant, LabAssistant, Course
from App.controllers.shift import create_shift
from App.controllers.course import get_all_courses
from App.database import db
from App.utils.time_utils import trinidad_now
from App.utils.performance_monitor import performance_monitor
from .data_transformation_service import DataTransformationService

logger = logging.getLogger(__name__)


class SchedulingService:
    """
    Service for generating optimized schedules using PuLP linear programming.
    
    This service implements the business logic for schedule generation,
    separated from HTTP request handling and database persistence details.
    """

    def __init__(self):
        self.data_transformer = DataTransformationService()

    @performance_monitor("generate_helpdesk_schedule", log_slow_threshold=2.0)
    def generate_helpdesk_schedule(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **generation_options
    ) -> Dict[str, Any]:
        """
        Generate a help desk schedule using PuLP optimization.
        
        Args:
            start_date: The start date for this schedule
            end_date: The end date for this schedule
            **generation_options: Additional options for schedule generation
            
        Returns:
            Dictionary with the schedule generation result
        """
        try:
            # Normalize dates
            if start_date is None:
                start_date = trinidad_now().replace(hour=0, minute=0, second=0, microsecond=0)
            if end_date is None:
                # Default to end of week (Friday)
                days_to_friday = 4 - start_date.weekday()
                if days_to_friday < 0:
                    days_to_friday += 7
                end_date = start_date + timedelta(days=days_to_friday)

            logger.info(f"Generating helpdesk schedule from {start_date} to {end_date}")

            # Get or create schedule
            schedule = self._get_or_create_schedule(1, start_date, end_date, 'helpdesk')
            
            # Clear existing shifts
            self._clear_shifts_in_range(schedule.id, start_date, end_date)
            
            # Get active assistants
            assistants = HelpDeskAssistant.query.filter_by(active=True).all()
            if not assistants:
                return {
                    "status": "error",
                    "message": "No active help desk assistants found"
                }

            # Transform to scheduler format with fairness baseline
            baseline_target = generation_options.get('baseline_hours_target', 6)
            scheduler_assistants = self.data_transformer.assistants_to_scheduler_format(
                assistants, 'helpdesk', baseline_target
            )
            
            if not scheduler_assistants:
                return {
                    "status": "error",
                    "message": "No valid assistants available for scheduling"
                }

            # Generate shifts for the schedule
            scheduler_shifts = self.data_transformer.generate_shifts_for_schedule(
                schedule, 'helpdesk'
            )
            
            if not scheduler_shifts:
                return {
                    "status": "error",
                    "message": "No shifts could be generated for the date range"
                }

            # Create database shifts and mapping
            shifts_mapping = self._create_database_shifts(scheduler_shifts, schedule)

            # Configure the scheduler with improved fairness settings
            config = SchedulerConfig(
                course_shortfall_penalty=1.0,
                min_hours_penalty=5000.0,  # Very high penalty for baseline violations
                max_hours_penalty=5.0,
                understaffed_penalty=2000.0, # High penalty to ensure shift coverage  
                extra_hours_penalty=1.0,    # Very low penalty for extra hours
                max_extra_penalty=500.0,    # High penalty for unfair distribution
                baseline_hours_target=6,    # Target 6 hours per assistant
                allow_minimum_violation=True, # Use soft constraints for feasibility
                solver_time_limit=60,  # 60 seconds max
                log_solver_output=False
            )

            # Solve the scheduling problem
            logger.info(f"Solving schedule with {len(scheduler_assistants)} assistants and {len(scheduler_shifts)} shifts")
            result = solve_helpdesk_schedule(
                scheduler_assistants,
                scheduler_shifts,
                config=config
            )

            if result.status in ['Optimal', 'Feasible']:
                # Convert results back to database
                stats = self.data_transformer.schedule_result_to_database(
                    result, schedule, shifts_mapping
                )
                
                return {
                    "status": "success",
                    "schedule_id": schedule.id,
                    "message": "Help desk schedule generated successfully",
                    "details": {
                        "start_date": start_date.strftime('%Y-%m-%d'),
                        "end_date": end_date.strftime('%Y-%m-%d'),
                        "shifts_created": len(shifts_mapping),
                        "assignments_created": stats['assignments_created'],
                        "objective_value": result.objective_value,
                        "solver_status": result.status,
                        "generation_options": generation_options
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": f"No feasible solution found. Solver status: {result.status}",
                    "details": {
                        "solver_status": result.status,
                        "assistants_count": len(scheduler_assistants),
                        "shifts_count": len(scheduler_shifts)
                    }
                }

        except Exception as e:
            logger.error(f"Error generating helpdesk schedule: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    @performance_monitor("generate_lab_schedule", log_slow_threshold=2.0)  
    def generate_lab_schedule(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **generation_options
    ) -> Dict[str, Any]:
        """
        Generate a lab schedule using PuLP optimization.
        
        Args:
            start_date: The start date for this schedule
            end_date: The end date for this schedule
            **generation_options: Additional options for schedule generation
            
        Returns:
            Dictionary with the schedule generation result
        """
        try:
            # Normalize dates
            if start_date is None:
                start_date = trinidad_now().replace(hour=0, minute=0, second=0, microsecond=0)
            if end_date is None:
                # Default to end of week (Saturday for lab)
                days_to_saturday = 5 - start_date.weekday()
                if days_to_saturday < 0:
                    days_to_saturday += 7
                end_date = start_date + timedelta(days=days_to_saturday)

            logger.info(f"Generating lab schedule from {start_date} to {end_date}")

            # Get or create schedule
            schedule = self._get_or_create_schedule(2, start_date, end_date, 'lab')
            
            # Clear existing shifts
            self._clear_shifts_in_range(schedule.id, start_date, end_date)
            
            # Get active lab assistants
            from App.controllers.lab_assistant import get_active_lab_assistants
            assistants = get_active_lab_assistants()
            
            if not assistants:
                return {
                    "status": "error",
                    "message": "No active lab assistants found"
                }

            # Transform to scheduler format with fairness baseline
            baseline_target = generation_options.get('baseline_hours_target', 6)
            scheduler_assistants = self.data_transformer.assistants_to_scheduler_format(
                assistants, 'lab', baseline_target
            )
            
            if not scheduler_assistants:
                return {
                    "status": "error",
                    "message": "No valid lab assistants available for scheduling"
                }

            # Generate shifts for the schedule
            scheduler_shifts = self.data_transformer.generate_shifts_for_schedule(
                schedule, 'lab'
            )
            
            if not scheduler_shifts:
                return {
                    "status": "error",
                    "message": "No shifts could be generated for the date range"
                }

            # Create database shifts and mapping
            shifts_mapping = self._create_database_shifts(scheduler_shifts, schedule)

            # Configure the scheduler with improved fairness settings for lab
            config = SchedulerConfig(
                course_shortfall_penalty=1.0,
                min_hours_penalty=5000.0,  # Very high penalty for baseline violations  
                max_hours_penalty=10.0,    # Higher penalty to prevent overwork
                understaffed_penalty=3000.0, # Very high penalty for understaffing
                extra_hours_penalty=2.0,   # Low penalty for lab extra hours
                max_extra_penalty=750.0,   # High penalty for unfair distribution
                baseline_hours_target=6,   # Same 6 hour target for lab
                allow_minimum_violation=True, # Use soft constraints for feasibility
                solver_time_limit=60,
                log_solver_output=False
            )

            # Solve the scheduling problem
            logger.info(f"Solving lab schedule with {len(scheduler_assistants)} assistants and {len(scheduler_shifts)} shifts")
            result = solve_helpdesk_schedule(  # Uses the same solver function
                scheduler_assistants,
                scheduler_shifts,
                config=config
            )

            if result.status in ['Optimal', 'Feasible']:
                # Convert results back to database
                stats = self.data_transformer.schedule_result_to_database(
                    result, schedule, shifts_mapping
                )
                
                return {
                    "status": "success",
                    "schedule_id": schedule.id,
                    "message": "Lab schedule generated successfully",
                    "details": {
                        "start_date": start_date.strftime('%Y-%m-%d'),
                        "end_date": end_date.strftime('%Y-%m-%d'),
                        "shifts_created": len(shifts_mapping),
                        "assignments_created": stats['assignments_created'],
                        "objective_value": result.objective_value,
                        "solver_status": result.status,
                        "generation_options": generation_options
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": f"No feasible solution found. Solver status: {result.status}",
                    "details": {
                        "solver_status": result.status,
                        "assistants_count": len(scheduler_assistants),
                        "shifts_count": len(scheduler_shifts)
                    }
                }

        except Exception as e:
            logger.error(f"Error generating lab schedule: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def _get_or_create_schedule(
        self, 
        schedule_id: int, 
        start_date: datetime, 
        end_date: datetime, 
        schedule_type: str
    ) -> Schedule:
        """Get or create a schedule object."""
        schedule = Schedule.query.filter_by(id=schedule_id, type=schedule_type).first()
        
        if not schedule:
            schedule = Schedule(
                id=schedule_id,
                start_date=start_date,
                end_date=end_date,
                type=schedule_type
            )
            db.session.add(schedule)
        else:
            schedule.start_date = start_date
            schedule.end_date = end_date
            db.session.add(schedule)
        
        db.session.flush()
        return schedule

    def _clear_shifts_in_range(
        self, 
        schedule_id: int, 
        start_date: datetime, 
        end_date: datetime
    ) -> None:
        """Clear existing shifts in the date range."""
        from App.controllers.schedule import clear_shifts_in_range
        clear_shifts_in_range(schedule_id, start_date, end_date)

    def _create_database_shifts(
        self, 
        scheduler_shifts: List, 
        schedule: Schedule
    ) -> Dict[str, Shift]:
        """
        Create database shift objects from scheduler shifts.
        
        Returns a mapping from scheduler shift IDs to database Shift objects.
        """
        shifts_mapping = {}
        
        for scheduler_shift in scheduler_shifts:
            # Parse the date from metadata
            shift_date_str = scheduler_shift.metadata.get('date')
            if not shift_date_str:
                logger.warning(f"No date metadata for shift {scheduler_shift.id}")
                continue
                
            try:
                shift_date = datetime.fromisoformat(shift_date_str)
                
                # Create start and end datetimes
                start_datetime = datetime.combine(
                    shift_date.date(), 
                    scheduler_shift.start
                )
                end_datetime = datetime.combine(
                    shift_date.date(), 
                    scheduler_shift.end
                )
                
                # Create database shift
                db_shift = create_shift(
                    shift_date.date(),
                    start_datetime,
                    end_datetime,
                    schedule.id
                )
                
                shifts_mapping[scheduler_shift.id] = db_shift
                
            except Exception as e:
                logger.error(f"Error creating database shift for {scheduler_shift.id}: {e}")
                continue
        
        logger.info(f"Created {len(shifts_mapping)} database shifts")
        return shifts_mapping

    def check_scheduling_feasibility(self, schedule_type: str = 'helpdesk') -> Dict[str, Any]:
        """
        Check if scheduling is feasible with current constraints.
        
        Args:
            schedule_type: Type of schedule to check ('helpdesk' or 'lab')
            
        Returns:
            Dictionary with feasibility information
        """
        try:
            # Get assistants based on type
            if schedule_type == 'helpdesk':
                assistants = HelpDeskAssistant.query.filter_by(active=True).all()
            else:
                from App.controllers.lab_assistant import get_active_lab_assistants
                assistants = get_active_lab_assistants()
            
            assistant_count = len(assistants)
            
            # Check minimum assistant count
            if assistant_count < 2:
                return {
                    "feasible": False,
                    "message": f"Not enough active assistants: found {assistant_count}, minimum 2 needed"
                }
            
            # Check availability data
            assistants_with_availability = 0
            for assistant in assistants:
                from App.models import Availability
                availability_count = Availability.query.filter_by(username=assistant.username).count()
                if availability_count > 0:
                    assistants_with_availability += 1
            
            if assistants_with_availability < 2:
                return {
                    "feasible": False,
                    "message": f"Only {assistants_with_availability} assistants have availability data"
                }
            
            # Check course capabilities
            assistants_with_capabilities = 0
            for assistant in assistants:
                capability_count = len(assistant.course_capabilities)
                if capability_count > 0:
                    assistants_with_capabilities += 1
            
            if assistants_with_capabilities < 2:
                return {
                    "feasible": False,
                    "message": f"Only {assistants_with_capabilities} assistants have course capabilities"
                }
            
            return {
                "feasible": True,
                "message": "Scheduling appears feasible",
                "stats": {
                    "assistant_count": assistant_count,
                    "assistants_with_availability": assistants_with_availability,
                    "assistants_with_capabilities": assistants_with_capabilities
                }
            }
            
        except Exception as e:
            return {
                "feasible": False,
                "message": f"Error checking feasibility: {str(e)}"
            }