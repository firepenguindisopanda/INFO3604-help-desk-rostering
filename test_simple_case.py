#!/usr/bin/env python3
"""
Simple test to debug the infeasibility issue.
"""

import os
import sys
from datetime import time

sys.path.insert(0, os.path.abspath('.'))

from scheduler_lp import Assistant, Shift, CourseDemand, AvailabilityWindow, SchedulerConfig, solve_helpdesk_schedule


def test_simple_case():
    """Test a very simple case to see what's causing infeasibility."""
    print("TESTING SIMPLE CASE")
    print("=" * 30)
    
    # Just 2 assistants with simple availability
    assistants = [
        Assistant(
            id="alice",
            courses=["INFO1600"],
            availability=[AvailabilityWindow(0, time(9, 0), time(17, 0))],  # 8 hours
            min_hours=0.0,  # No minimum requirement
            max_hours=8.0,
        ),
        Assistant(
            id="bob", 
            courses=["INFO1600"],
            availability=[AvailabilityWindow(0, time(9, 0), time(17, 0))],  # 8 hours
            min_hours=0.0,  # No minimum requirement
            max_hours=8.0,
        ),
    ]
    
    # Just 4 simple shifts
    shifts = [
        Shift(
            id=f"shift_{i}",
            day_of_week=0,  # Monday
            start=time(9 + i),
            end=time(10 + i),
            course_demands=[CourseDemand("INFO1600", 1, 1.0)],
            min_staff=1,
            max_staff=2,
        )
        for i in range(4)  # 4 one-hour shifts
    ]
    
    print(f"Assistants: {len(assistants)}")
    print(f"Shifts: {len(shifts)}")
    
    # Very simple config
    config = SchedulerConfig(
        course_shortfall_penalty=1.0,
        min_hours_penalty=10.0,
        max_hours_penalty=5.0,
        understaffed_penalty=100.0,
        extra_hours_penalty=1.0,
        max_extra_penalty=5.0,
        baseline_hours_target=2,  # Just 2 hours baseline
        allow_minimum_violation=True,
        solver_time_limit=30,
        log_solver_output=True
    )
    
    print("\nSolving simple case...")
    result = solve_helpdesk_schedule(assistants, shifts, config=config)
    
    print(f"Status: {result.status}")
    if result.status in ['Optimal', 'Feasible']:
        print("Simple case works!")
        for assistant in assistants:
            hours = result.assistant_hours.get(assistant.id, 0)
            print(f"  {assistant.id}: {hours:.1f} hours")
    else:
        print("Even simple case fails!")
    
    return result.status in ['Optimal', 'Feasible']


if __name__ == "__main__":
    test_simple_case()