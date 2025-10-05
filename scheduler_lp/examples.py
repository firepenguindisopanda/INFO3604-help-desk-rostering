"""Executable examples for the linear programming scheduler.

Run this module directly to solve a small synthetic rostering problem. Use it as a
starting point for experimentation or as documentation for the data structures.
"""
from __future__ import annotations

from datetime import time
from pprint import pprint

from . import (
    AvailabilityWindow,
    Assistant,
    CourseDemand,
    SchedulerConfig,
    Shift,
    solve_helpdesk_schedule,
)


def build_demo_inputs() -> tuple[list[Assistant], list[Shift], SchedulerConfig]:
    """Construct a small demonstration instance.

    Returns:
        assistants: List of :class:`Assistant` objects with availability windows.
        shifts: List of :class:`Shift` objects with course demand requirements.
        config: :class:`SchedulerConfig` with tuned penalty weights.
    """

    # Assistants -----------------------------------------------------------
    assistants = [
        Assistant(
            id="alice",
            courses=["COMP1600", "COMP2603"],
            availability=[
                AvailabilityWindow(day_of_week=0, start=time(9), end=time(17)),
                AvailabilityWindow(day_of_week=2, start=time(9), end=time(17)),
            ],
            min_hours=4,
            max_hours=8,
        ),
        Assistant(
            id="bryan",
            courses=["COMP1600", "INFO2602"],
            availability=[
                AvailabilityWindow(day_of_week=0, start=time(12), end=time(17)),
                AvailabilityWindow(day_of_week=1, start=time(9), end=time(17)),
            ],
            min_hours=4,
            max_hours=8,
        ),
        Assistant(
            id="carmen",
            courses=["COMP2603", "INFO2602"],
            availability=[
                AvailabilityWindow(day_of_week=1, start=time(9), end=time(13)),
                AvailabilityWindow(day_of_week=3, start=time(9), end=time(17)),
            ],
            min_hours=4,
        ),
    ]

    # Shifts ----------------------------------------------------------------
    shifts = [
        Shift(
            id="mon_09",
            day_of_week=0,
            start=time(9),
            end=time(10),
            course_demands=[
                CourseDemand(course_code="COMP1600", tutors_required=1, weight=2.0),
                CourseDemand(course_code="COMP2603", tutors_required=1, weight=1.0),
            ],
        ),
        Shift(
            id="mon_10",
            day_of_week=0,
            start=time(10),
            end=time(11),
            course_demands=[
                CourseDemand(course_code="COMP1600", tutors_required=1, weight=2.0),
                CourseDemand(course_code="INFO2602", tutors_required=1, weight=3.0),
            ],
        ),
        Shift(
            id="tue_09",
            day_of_week=1,
            start=time(9),
            end=time(10),
            course_demands=[
                CourseDemand(course_code="COMP1600", tutors_required=1, weight=1.0),
                CourseDemand(course_code="INFO2602", tutors_required=1, weight=2.0),
            ],
        ),
        Shift(
            id="wed_13",
            day_of_week=2,
            start=time(13),
            end=time(14),
            course_demands=[
                CourseDemand(course_code="COMP2603", tutors_required=1, weight=1.0),
                CourseDemand(course_code="INFO2602", tutors_required=1, weight=2.5),
            ],
        ),
    ]

    config = SchedulerConfig(
        course_shortfall_penalty=5.0,
        understaffed_penalty=40.0,
        min_hours_penalty=12.0,
        max_hours_penalty=5.0,
        solver_time_limit=60,
        log_solver_output=False,
    )

    return assistants, shifts, config


def run_demo() -> None:
    """Solve the demo problem and print readable diagnostics."""

    assistants, shifts, config = build_demo_inputs()
    result = solve_helpdesk_schedule(assistants, shifts, config=config)

    print("Solver status:", result.status)
    print("Objective value:", result.objective_value)
    print("Assignments (assistant -> shift):")
    for assistant_id, shift_id in result.assignments:
        print(f"  - {assistant_id} -> {shift_id}")

    print("\nAssistant hours worked:")
    pprint(result.assistant_hours)

    print("\nCourse shortfalls (shift_id, course_code -> tutors missing):")
    pprint(result.course_shortfalls)

    print("\nShift understaffing (shift_id -> tutors missing):")
    pprint(result.staff_shortfalls)


if __name__ == "__main__":
    run_demo()
