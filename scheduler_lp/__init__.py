"""Linear programming-based scheduling toolkit.

This package exposes high-level helpers for generating help desk schedules
using a mixed-integer programming model. It is intentionally decoupled from
Flask and SQLAlchemy so it can be reused in standalone experiments or notebooks.
"""

from .linear_scheduler import (
    AvailabilityWindow,
    Assistant,
    CourseDemand,
    Shift,
    SchedulerConfig,
    ScheduleResult,
    solve_helpdesk_schedule,
)

__all__ = [
    "AvailabilityWindow",
    "Assistant",
    "CourseDemand",
    "Shift",
    "SchedulerConfig",
    "ScheduleResult",
    "solve_helpdesk_schedule",
]
