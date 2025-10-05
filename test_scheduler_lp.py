from datetime import time

from scheduler_lp import (
    AvailabilityWindow,
    Assistant,
    CourseDemand,
    SchedulerConfig,
    Shift,
    solve_helpdesk_schedule,
)


def test_lp_scheduler_finds_feasible_solution():
    assistants = [
        Assistant(
            id="aisha",
            courses=["COMP1000", "COMP2000"],
            availability=[AvailabilityWindow(day_of_week=0, start=time(9), end=time(12))],
            min_hours=2,
            max_hours=4,
        ),
        Assistant(
            id="daryl",
            courses=["COMP2000"],
            availability=[AvailabilityWindow(day_of_week=0, start=time(9), end=time(12))],
            min_hours=1,
            max_hours=3,
        ),
    ]

    shifts = [
        Shift(
            id="mon_09",
            day_of_week=0,
            start=time(9),
            end=time(10),
            course_demands=[CourseDemand(course_code="COMP2000", tutors_required=1, weight=2.0)],
        ),
        Shift(
            id="mon_10",
            day_of_week=0,
            start=time(10),
            end=time(11),
            course_demands=[CourseDemand(course_code="COMP2000", tutors_required=1, weight=2.0)],
        ),
    ]

    config = SchedulerConfig(course_shortfall_penalty=5.0, understaffed_penalty=20.0)

    result = solve_helpdesk_schedule(assistants, shifts, config=config)

    assert result.status in {"Optimal", "Feasible"}
    assert len(result.assignments) == 2
    assert all(shortfall <= 0.001 for shortfall in result.course_shortfalls.values())
    assert all(shortfall <= 0.001 for shortfall in result.staff_shortfalls.values())
    # Ensure hour accounting matches expected duration
    total_hours = result.assistant_hours["aisha"] + result.assistant_hours["daryl"]
    assert abs(total_hours - 2.0) <= 1e-6
