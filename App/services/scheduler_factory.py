"""
Scheduler Factory for selecting between PuLP and OR-Tools solvers.

This factory provides a clean abstraction layer that allows the application
to switch between scheduling engines without changing calling code.
"""

from typing import Literal, Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

SolverType = Literal['pulp', 'ortools']


class SchedulerFactory:
    """Factory to get appropriate scheduler based on configuration."""
    
    _pulp_service = None
    
    @staticmethod
    def get_scheduler_type() -> SolverType:
        """
        Get configured solver type from app config or environment.
        
        Returns:
            'pulp' or 'ortools' - The configured solver type
        """
        try:
            from flask import current_app
            return current_app.config.get('SCHEDULER_ENGINE', 'pulp')
        except RuntimeError:
            # Not in app context, use environment variable
            import os
            return os.environ.get('SCHEDULER_ENGINE', 'pulp')
    
    @staticmethod
    def is_fallback_enabled() -> bool:
        """Check if automatic fallback is enabled."""
        try:
            from flask import current_app
            return current_app.config.get('SCHEDULER_FALLBACK_ENABLED', True)
        except RuntimeError:
            import os
            return os.environ.get('SCHEDULER_FALLBACK_ENABLED', 'true').lower() == 'true'
    
    @staticmethod
    def _get_pulp_service():
        """Lazy initialization of PuLP scheduling service."""
        if SchedulerFactory._pulp_service is None:
            from App.services.scheduling_service import SchedulingService
            SchedulerFactory._pulp_service = SchedulingService()
        return SchedulerFactory._pulp_service
    
    @staticmethod
    def generate_helpdesk_schedule(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        solver: Optional[SolverType] = None,
        **generation_options
    ) -> Dict[str, Any]:
        """
        Generate helpdesk schedule using configured or specified solver.
        
        Args:
            start_date: Start date for schedule
            end_date: End date for schedule
            solver: Optional solver override ('pulp' or 'ortools')
            **generation_options: Additional generation options
            
        Returns:
            Dictionary with schedule generation result
        """
        solver_type = solver or SchedulerFactory.get_scheduler_type()
        fallback_enabled = SchedulerFactory.is_fallback_enabled()
        
        logger.info(f"Generating helpdesk schedule using {solver_type} solver")
        
        try:
            if solver_type == 'pulp':
                service = SchedulerFactory._get_pulp_service()
                result = service.generate_helpdesk_schedule(
                    start_date=start_date,
                    end_date=end_date,
                    **generation_options
                )
                
                # If PuLP fails and fallback enabled, try OR-Tools
                if result.get('status') != 'success' and fallback_enabled:
                    logger.warning(
                        f"PuLP solver returned status '{result.get('status')}', "
                        "falling back to OR-Tools"
                    )
                    return SchedulerFactory._generate_helpdesk_ortools(
                        start_date, end_date, **generation_options
                    )
                
                return result
            else:
                return SchedulerFactory._generate_helpdesk_ortools(
                    start_date, end_date, **generation_options
                )
                
        except Exception as e:
            logger.error(f"Primary solver ({solver_type}) failed: {e}")
            if fallback_enabled and solver_type == 'pulp':
                logger.info("Attempting fallback to OR-Tools")
                try:
                    return SchedulerFactory._generate_helpdesk_ortools(
                        start_date, end_date, **generation_options
                    )
                except Exception as fallback_error:
                    logger.error(f"Fallback solver also failed: {fallback_error}")
                    raise
            raise
    
    @staticmethod
    def generate_lab_schedule(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        solver: Optional[SolverType] = None,
        **generation_options
    ) -> Dict[str, Any]:
        """
        Generate lab schedule using configured or specified solver.
        
        Args:
            start_date: Start date for schedule
            end_date: End date for schedule
            solver: Optional solver override ('pulp' or 'ortools')
            **generation_options: Additional generation options
            
        Returns:
            Dictionary with schedule generation result
        """
        solver_type = solver or SchedulerFactory.get_scheduler_type()
        fallback_enabled = SchedulerFactory.is_fallback_enabled()
        
        logger.info(f"Generating lab schedule using {solver_type} solver")
        
        try:
            if solver_type == 'pulp':
                service = SchedulerFactory._get_pulp_service()
                result = service.generate_lab_schedule(
                    start_date=start_date,
                    end_date=end_date,
                    **generation_options
                )
                
                # If PuLP fails and fallback enabled, try OR-Tools
                if result.get('status') != 'success' and fallback_enabled:
                    logger.warning(
                        f"PuLP solver returned status '{result.get('status')}', "
                        "falling back to OR-Tools"
                    )
                    return SchedulerFactory._generate_lab_ortools(
                        start_date, end_date, **generation_options
                    )
                
                return result
            else:
                return SchedulerFactory._generate_lab_ortools(
                    start_date, end_date, **generation_options
                )
                
        except Exception as e:
            logger.error(f"Primary solver ({solver_type}) failed: {e}")
            if fallback_enabled and solver_type == 'pulp':
                logger.info("Attempting fallback to OR-Tools")
                try:
                    return SchedulerFactory._generate_lab_ortools(
                        start_date, end_date, **generation_options
                    )
                except Exception as fallback_error:
                    logger.error(f"Fallback solver also failed: {fallback_error}")
                    raise
            raise
    
    @staticmethod
    def _generate_helpdesk_ortools(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **generation_options
    ) -> Dict[str, Any]:
        """Call OR-Tools implementation for helpdesk schedule."""
        # Import here to avoid circular dependencies
        from App.controllers.schedule import generate_help_desk_schedule_ortools
        return generate_help_desk_schedule_ortools(start_date, end_date, **generation_options)
    
    @staticmethod
    def _generate_lab_ortools(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **generation_options
    ) -> Dict[str, Any]:
        """Call OR-Tools implementation for lab schedule."""
        # Import here to avoid circular dependencies
        from App.controllers.schedule import generate_lab_schedule_ortools
        return generate_lab_schedule_ortools(start_date, end_date, **generation_options)

