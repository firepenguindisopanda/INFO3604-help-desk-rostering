"""OR-Tools CP-SAT help desk scheduler (framework-agnostic).

This package mirrors the CP-SAT solver used by the Flask API so notebooks
and scripts can experiment with identical behaviour without importing any
Flask code.
"""

from .cp_sat_solver import (
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
