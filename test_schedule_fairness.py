#!/usr/bin/env python3
"""
Test script to verify the help desk scheduling fairness implementation.

This script tests the fairness requirements outlined in the fairness document:
1. Every assistant receives up to 6 hours baseline
2. Assistants with <6 hours availability get all they can work
3. Extra hours distributed evenly after baselines are met
"""

import os
import sys
from datetime import time, datetime

# Add the project root to the path
sys.path.insert(0, os.path.abspath('.'))

from scheduler_lp import Assistant, Shift, CourseDemand, AvailabilityWindow, SchedulerConfig, solve_helpdesk_schedule


def create_test_assistants():
    """Create test assistants with varying availability."""
    assistants = []
    
    # Assistant 1: Can work 8 hours (should get 6 baseline + 2 extra if needed)
    assistants.append(Assistant(
        id="assistant1",
        courses=["INFO1600", "INFO2600"],
        availability=[
            AvailabilityWindow(0, time(9, 0), time(17, 0)),  # Monday 8 hours
        ],
        min_hours=6.0,  # Baseline target
        max_hours=8.0,
    ))
    
    # Assistant 2: Can work 4 hours (should get all 4 hours as baseline)
    assistants.append(Assistant(
        id="assistant2", 
        courses=["INFO1600", "INFO3604"],
        availability=[
            AvailabilityWindow(1, time(9, 0), time(13, 0)),  # Tuesday 4 hours
        ],
        min_hours=4.0,  # Limited by availability
        max_hours=4.0,
    ))
    
    # Assistant 3: Can work 10 hours (should get 6 baseline + up to 4 extra)
    assistants.append(Assistant(
        id="assistant3",
        courses=["INFO2600", "INFO3604"], 
        availability=[
            AvailabilityWindow(2, time(9, 0), time(17, 0)),  # Wednesday 8 hours
            AvailabilityWindow(3, time(9, 0), time(11, 0)),  # Thursday 2 hours
        ],
        min_hours=6.0,  # Baseline target
        max_hours=10.0,
    ))
    
    # Assistant 4: Can work 6 hours exactly (should get exactly 6 hours)
    assistants.append(Assistant(
        id="assistant4",
        courses=["INFO1600", "INFO2600", "INFO3604"],
        availability=[
            AvailabilityWindow(4, time(9, 0), time(15, 0)),  # Friday 6 hours
        ],
        min_hours=6.0,  # Baseline target
        max_hours=6.0,
    ))
    
    return assistants


def create_test_shifts():
    """Create test shifts for one week."""
    shifts = []
    
    # Create shifts for Monday through Friday, 9am-5pm (8 hours per day)
    for day in range(5):  # Monday to Friday
        for hour in range(9, 17):  # 9am to 5pm
            shift_id = f"shift_day{day}_hour{hour}"
            
            # Mix of course demands
            course_demands = [
                CourseDemand("INFO1600", 1, 1.0),
                CourseDemand("INFO2600", 1, 1.0),
                CourseDemand("INFO3604", 1, 1.0),
            ]
            
            shift = Shift(
                id=shift_id,
                day_of_week=day,
                start=time(hour),
                end=time(hour + 1),
                course_demands=course_demands,
                min_staff=2,
                max_staff=3,
            )
            shifts.append(shift)
    
    return shifts


def test_fairness_implementation():
    """Test the fairness implementation."""
    print("=" * 60)
    print("TESTING HELP DESK SCHEDULING FAIRNESS")
    print("=" * 60)
    
    assistants = create_test_assistants()
    shifts = create_test_shifts()
    
    print(f"Created {len(assistants)} assistants and {len(shifts)} shifts")
    print()
    
    # Print assistant availability summary
    print("ASSISTANT AVAILABILITY:")
    for assistant in assistants:
        total_hours = sum(
            (window.end.hour - window.start.hour) for window in assistant.availability
        )
        print(f"  {assistant.id}: {total_hours} hours available, "
              f"baseline target: {assistant.min_hours}, max: {assistant.max_hours}")
    print()
    
    # Configure scheduler with fairness settings
    config = SchedulerConfig(
        course_shortfall_penalty=1.0,
        min_hours_penalty=100.0,    # High penalty for baseline violations
        max_hours_penalty=5.0,
        understaffed_penalty=25.0,
        extra_hours_penalty=15.0,   # Penalty for extra hours
        max_extra_penalty=50.0,     # High penalty for unfair distribution
        baseline_hours_target=6,    # Target 6 hours baseline
        allow_minimum_violation=False,  # Hard constraint for baselines
        solver_time_limit=30,
        log_solver_output=True
    )
    
    print("SOLVING SCHEDULE...")
    result = solve_helpdesk_schedule(assistants, shifts, config=config)
    
    print(f"Solver Status: {result.status}")
    print(f"Objective Value: {result.objective_value}")
    print()
    
    if result.status in ['Optimal', 'Feasible']:
        print("ASSIGNMENT RESULTS:")
        
        # Analyze fairness
        assistant_hours = result.assistant_hours
        baseline_violations = []
        extra_hours = {}
        
        for assistant in assistants:
            assigned_hours = assistant_hours.get(assistant.id, 0.0)
            baseline_target = assistant.min_hours
            
            print(f"  {assistant.id}:")
            print(f"    Assigned: {assigned_hours:.1f} hours")
            print(f"    Baseline: {baseline_target:.1f} hours")
            
            if assigned_hours < baseline_target:
                violation = baseline_target - assigned_hours
                baseline_violations.append((assistant.id, violation))
                print(f"BASELINE VIOLATION: -{violation:.1f} hours")
            else:
                print(f"Baseline satisfied")
            
            extra = max(0, assigned_hours - baseline_target)
            extra_hours[assistant.id] = extra
            if extra > 0:
                print(f"Extra hours: +{extra:.1f}")
            print()
        
        # Fairness analysis
        print("FAIRNESS ANALYSIS:")
        if baseline_violations:
            print(f"{len(baseline_violations)} baseline violations found:")
            for assistant_id, violation in baseline_violations:
                print(f"    - {assistant_id}: -{violation:.1f} hours")
        else:
            print("All baselines satisfied")
        
        extra_values = list(extra_hours.values())
        if extra_values:
            max_extra = max(extra_values)
            min_extra = min(extra_values)
            extra_range = max_extra - min_extra
            print(f"Extra hours range: {min_extra:.1f} - {max_extra:.1f} (spread: {extra_range:.1f})")
            
            if extra_range <= 1.0:  # Within 1 hour is considered fair
                print("Extra hours distributed fairly")
            else:
                print("Extra hours distribution could be more even")

        print()
        print("ASSIGNMENTS BY SHIFT:")
        
        # Group assignments by shift for analysis
        shift_assignments = {}
        for assistant_id, shift_id in result.assignments:
            if shift_id not in shift_assignments:
                shift_assignments[shift_id] = []
            shift_assignments[shift_id].append(assistant_id)
        
        # Show a sample of assignments
        sample_shifts = list(shift_assignments.keys())[:10]
        for shift_id in sample_shifts:
            assigned_assistants = shift_assignments[shift_id]
            print(f"  {shift_id}: {', '.join(assigned_assistants)}")
        
        if len(shift_assignments) > 10:
            print(f"  ... and {len(shift_assignments) - 10} more shifts")
    
    else:
        print(f"Scheduling failed with status: {result.status}")
        print("This indicates the fairness constraints may be too strict or")
        print("there is insufficient capacity to meet baseline requirements.")
    
    print("=" * 60)


if __name__ == "__main__":
    test_fairness_implementation()