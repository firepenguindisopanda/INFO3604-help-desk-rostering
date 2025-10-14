#!/usr/bin/env python3
"""
Advanced test to verify fairness with extra hours distribution.
"""

import os
import sys
from datetime import time

sys.path.insert(0, os.path.abspath('.'))

from scheduler_lp import Assistant, Shift, CourseDemand, AvailabilityWindow, SchedulerConfig, solve_helpdesk_schedule


def test_extra_hours_fairness():
    """Test that extra hours are distributed fairly when more capacity is needed."""
    print("TESTING EXTRA HOURS FAIRNESS")
    print("=" * 50)
    
    # Create assistants with overlapping availability to ensure they can all work
    assistants = [
        # Assistant 1: 8 hours available (6 baseline + 2 extra possible)
        Assistant(
            id="alice",
            courses=["INFO1600", "INFO2600"],
            availability=[
                AvailabilityWindow(0, time(9, 0), time(17, 0)),  # Monday
                AvailabilityWindow(1, time(9, 0), time(17, 0)),  # Tuesday
            ],
            min_hours=6.0,
            max_hours=8.0,
        ),
        # Assistant 2: 7 hours available (6 baseline + 1 extra possible)  
        Assistant(
            id="bob",
            courses=["INFO1600", "INFO3604"],
            availability=[
                AvailabilityWindow(0, time(10, 0), time(17, 0)),  # Monday 7 hours
                AvailabilityWindow(1, time(10, 0), time(17, 0)),  # Tuesday 7 hours
            ],
            min_hours=6.0,
            max_hours=7.0,
        ),
        # Assistant 3: 6 hours available (6 baseline, no extra)
        Assistant(
            id="charlie",
            courses=["INFO2600", "INFO3604"],
            availability=[
                AvailabilityWindow(0, time(9, 0), time(15, 0)),  # Monday 6 hours
                AvailabilityWindow(1, time(9, 0), time(15, 0)),  # Tuesday 6 hours
            ],
            min_hours=6.0,
            max_hours=6.0,
        ),
    ]
    
    # Create enough shifts to require some extra hours but not impossible amounts
    shifts = []
    for day in range(2):  # 2 days
        for hour in range(9, 14):  # 5 hours per day = 10 total shifts
            shifts.append(Shift(
                id=f"shift_d{day}_h{hour}",
                day_of_week=day,
                start=time(hour),
                end=time(hour + 1),
                course_demands=[CourseDemand("INFO1600", 1, 1.0)],
                min_staff=2,  # Need 2 staff per shift = 20 total assignments
                max_staff=3,
            ))
    
    total_baseline = sum(a.min_hours for a in assistants)  # 18 hours
    total_capacity = sum(a.max_hours for a in assistants)  # 21 hours  
    min_coverage_needed = len(shifts) * 2  # 20 staff-hours needed
    
    print(f"Total baseline hours: {total_baseline}")
    print(f"Total capacity: {total_capacity}")
    print(f"Coverage needed: {min_coverage_needed} staff-hours")
    print(f"Extra hours required: {min_coverage_needed - total_baseline}")
    
    # Debug: Check what each assistant can actually work
    print("\nAssistant feasibility:")
    for assistant in assistants:
        feasible_shifts = [s for s in shifts if assistant.is_available(s)]
        feasible_hours = sum(s.duration_hours for s in feasible_shifts)
        print(f"  {assistant.id}: {len(feasible_shifts)} shifts, {feasible_hours:.1f} hours available")
    print()
    
    # Configure with better balanced penalties for fairness
    config = SchedulerConfig(
        course_shortfall_penalty=1.0,
        min_hours_penalty=10000.0, # Extremely high penalty for baseline violations
        max_hours_penalty=5.0, 
        understaffed_penalty=1000.0, # High penalty for understaffing
        extra_hours_penalty=1.0,     # Very low penalty for extra hours
        max_extra_penalty=1000.0,    # Very high penalty for unfair distribution
        baseline_hours_target=6,
        allow_minimum_violation=True, # Use soft constraints for feasibility
        solver_time_limit=30,
        log_solver_output=False
    )
    
    result = solve_helpdesk_schedule(assistants, shifts, config=config)
    
    print(f"Status: {result.status}")
    if result.status in ['Optimal', 'Feasible']:
        print("\nHours Assignment:")
        extra_hours = {}
        for assistant in assistants:
            assigned = result.assistant_hours.get(assistant.id, 0)
            baseline = assistant.min_hours
            extra = assigned - baseline
            extra_hours[assistant.id] = extra
            
            print(f"  {assistant.id}: {assigned:.1f}h (baseline: {baseline:.1f}, extra: {extra:.1f})")
        
        # Check fairness of extra hours
        extra_values = list(extra_hours.values())
        if any(e > 0 for e in extra_values):
            max_extra = max(extra_values)
            min_extra = min(extra_values)
            print(f"\nExtra hours distribution:")
            print(f"  Range: {min_extra:.1f} - {max_extra:.1f}")
            print(f"  Difference: {max_extra - min_extra:.1f}")
            
            if max_extra - min_extra <= 1.0:
                print("Fair distribution (within 1 hour)")
            else:
                print("Uneven distribution")
        else:
            print("\nNo extra hours needed")
    else:
        print(f"Failed: {result.status}")


if __name__ == "__main__":
    test_extra_hours_fairness()