"""Linear programming-based scheduling toolkit.

This package provides a general-purpose rostering framework based on mixed-integer
linear programming. Possible improvement -> TODO: Implement different scheduling domains and make them as pluggable
constraint strategies using the Strategy Pattern.

Quick Start - Help Desk:
    >>> from scheduler_lp import solve_helpdesk_schedule, Assistant, Shift
    >>> result = solve_helpdesk_schedule(assistants, shifts)
    >>> print(result.assignments)

This package is intentionally decoupled from Flask and SQLAlchemy so it can
be reused in standalone experiments, notebooks, or other applications.
"""

from .linear_scheduler import (
    AvailabilityWindow,
    Assistant,
    CourseDemand,
    Shift,
    SchedulerConfig,
    ScheduleResult,
    solve_schedule,
    solve_helpdesk_schedule,
)

__all__ = [
    # Core data structures
    "AvailabilityWindow",
    "Assistant",
    "CourseDemand",
    "Shift",
    "SchedulerConfig",
    "ScheduleResult",
    
    # Solvers
    "solve_schedule",
    "solve_helpdesk_schedule",
]
