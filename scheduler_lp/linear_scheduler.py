"""Standalone help desk scheduling via mixed-integer linear programming.

The functions in this module are intentionally framework agnostic so they can be
executed in a notebook, a CLI script, or any other Python environment without
requiring Flask or SQLAlchemy.  The model mirrors the business rules used in the
Flask application but relies on the open-source `PuLP` package instead of
Google's OR-Tools CP-SAT solver.

Usage overview
--------------

1. Build Python objects describing assistants, their skills, and their
   availability windows.
2. Build `Shift` objects that capture the time slot plus the course demand that
   must be satisfied during that slot.
3. Call :func:`solve_helpdesk_schedule` and inspect the returned
   :class:`ScheduleResult` for assignments and diagnostics.

See ``scheduler_lp/examples.py`` for a ready-to-run example that can be executed
outside the Flask app.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:
    import pulp  # type: ignore
except ImportError as exc: 
    raise ImportError(
        "PuLP is required to use scheduler_lp.\n"
        "Install it with `pip install pulp` or add it to your environment."
    ) from exc


@dataclass(frozen=True)
class AvailabilityWindow:
    """Represents when an assistant is available to work.

    Args:
        day_of_week: 0=Monday, 6=Sunday.
        start: Inclusive start time of the window.
        end: Exclusive end time of the window.
    """

    day_of_week: int
    start: time
    end: time

    def __post_init__(self) -> None:
        if not 0 <= self.day_of_week <= 6:
            raise ValueError("day_of_week must be in the range [0, 6]")
        if self.end <= self.start:
            raise ValueError("Availability end time must be after start time")

    def covers(self, shift: "Shift") -> bool:
        """Return ``True`` if this window fully covers the provided shift."""

        if shift.day_of_week != self.day_of_week:
            return False
        return self.start <= shift.start <= shift.end <= self.end


@dataclass
class Assistant:
    """Metadata required to schedule an assistant."""

    id: str
    courses: Sequence[str]
    availability: Sequence[AvailabilityWindow]
    min_hours: float = 0.0
    max_hours: Optional[float] = None
    cost_per_hour: float = 0.0

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Assistant id cannot be empty")
        object.__setattr__(self, "_course_set", frozenset(map(str.upper, self.courses)))

    @property
    def course_set(self) -> frozenset[str]:
        return getattr(self, "_course_set")

    def is_available(self, shift: "Shift") -> bool:
        return any(window.covers(shift) for window in self.availability)


@dataclass(frozen=True)
class CourseDemand:
    """Demand for a particular course during a shift."""

    course_code: str
    tutors_required: int
    weight: float = 1.0

    def __post_init__(self) -> None:
        if self.tutors_required < 0:
            raise ValueError("tutors_required must be non-negative")
        if self.weight < 0:
            raise ValueError("weight must be non-negative")


@dataclass
class Shift:
    """A single help desk shift that needs coverage."""

    id: str
    day_of_week: int
    start: time
    end: time
    course_demands: Sequence[CourseDemand]
    min_staff: int = 2
    max_staff: Optional[int] = 3
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0 <= self.day_of_week <= 6:
            raise ValueError("day_of_week must be in the range [0, 6]")
        if self.end <= self.start:
            raise ValueError("Shift end must be after start time")
        if self.min_staff < 0:
            raise ValueError("min_staff must be non-negative")
        if self.max_staff is not None and self.max_staff < self.min_staff:
            raise ValueError("max_staff cannot be smaller than min_staff")

    @property
    def duration_hours(self) -> float:
        """Return the shift duration in hours."""

        base_day = date(2000, 1, 1)
        start_dt = datetime.combine(base_day, self.start)
        end_dt = datetime.combine(base_day, self.end)
        delta = end_dt - start_dt
        return delta.total_seconds() / 3600.0


@dataclass
class SchedulerConfig:
    """Weights and solver settings for the optimisation model."""

    course_shortfall_penalty: float = 1.0
    min_hours_penalty: float = 10.0
    max_hours_penalty: float = 5.0
    understaffed_penalty: float = 100.0  # High penalty to ensure shifts are covered
    extra_hours_penalty: float = 5.0     # Lower penalty for extra hours
    max_extra_penalty: float = 20.0      # Moderate penalty to encourage fairness
    baseline_hours_target: int = 6       # Baseline hours target per assistant
    allow_minimum_violation: bool = False  # Flag to allow baseline violations
    staff_shortfall_max: Optional[int] = None
    solver_time_limit: Optional[int] = None
    solver_gap: Optional[float] = None
    log_solver_output: bool = False


@dataclass
class ScheduleResult:
    """Structured container for optimisation results."""

    status: str
    objective_value: Optional[float]
    assignments: List[Tuple[str, str]]
    assistant_hours: Dict[str, float]
    course_shortfalls: Dict[Tuple[str, str], float]
    staff_shortfalls: Dict[str, float]
    solver_status_code: int

    def to_assignment_matrix(self) -> Mapping[str, List[str]]:
        matrix: Dict[str, List[str]] = {}
        for assistant_id, shift_id in self.assignments:
            matrix.setdefault(assistant_id, []).append(shift_id)
        return matrix

# Fairness helper functions


def _calculate_baseline_hours(
    assistants: Sequence[Assistant],
    shifts: Sequence[Shift],
    config: SchedulerConfig,
) -> Dict[str, float]:
    """
    Calculate baseline hours for each assistant based on their feasible shifts.
    
    Returns dictionary mapping assistant ID to their baseline hours target.
    """
    baseline_hours = {}
    
    for assistant in assistants:
        # Count feasible shifts for this assistant
        feasible_shifts = [
            shift for shift in shifts 
            if assistant.is_available(shift)
        ]
        
        # Calculate total hours they could work
        total_available_hours = sum(shift.duration_hours for shift in feasible_shifts)
        
        # Baseline is minimum of target (6) and what they can actually work
        baseline_target = min(config.baseline_hours_target, total_available_hours)
        
        # If assistant has very limited availability, adjust baseline
        if total_available_hours < config.baseline_hours_target:
            baseline_target = total_available_hours
        
        baseline_hours[assistant.id] = baseline_target
    
    return baseline_hours


def _check_baseline_feasibility(
    shifts: Sequence[Shift],
    baseline_hours: Dict[str, float],
) -> Tuple[bool, str]:
    """
    Check if baseline hours can be satisfied given shift capacity.
    
    Returns (is_feasible, message) tuple.
    """
    total_baseline_required = sum(baseline_hours.values())
    
    # Calculate maximum possible capacity
    # Assume minimum tutors per shift for capacity calculation
    total_shift_capacity = sum(shift.duration_hours * shift.min_staff for shift in shifts)
    
    if total_baseline_required > total_shift_capacity:
        return False, (
            f"Insufficient shift capacity for baseline targets. "
            f"Required: {total_baseline_required:.1f} hours, "
            f"Available: {total_shift_capacity:.1f} hours"
        )
    
    return True, "Baseline hours targets appear feasible"

# Solver


def solve_helpdesk_schedule(
    assistants: Sequence[Assistant],
    shifts: Sequence[Shift],
    *,
    config: Optional[SchedulerConfig] = None,
    solver: Optional[pulp.LpSolver] = None,
) -> ScheduleResult:
    """Solve the scheduling problem using PuLP with fairness constraints."""

    _validate_inputs(assistants, shifts)
    config = config or SchedulerConfig()

    # Calculate baseline hours for fairness
    baseline_hours = _calculate_baseline_hours(assistants, shifts, config)
    
    # Check if baseline targets are feasible
    is_feasible, feasibility_msg = _check_baseline_feasibility(shifts, baseline_hours)
    if not is_feasible and not config.allow_minimum_violation:
        raise ValueError(f"Baseline fairness targets not feasible: {feasibility_msg}")

    problem = pulp.LpProblem("HelpDeskSchedule", pulp.LpMinimize)

    assignment_vars = _build_assignment_variables(assistants, shifts)
    course_shortfall_vars = _build_course_shortfall_variables(shifts)
    staff_shortfall_vars = _build_staff_shortfall_variables(shifts, config)
    min_hours_vars, max_hours_vars, extra_hours_vars, max_extra_var = _build_hour_slack_variables(assistants, baseline_hours)

    objective_terms = _build_objective_terms(
        assistants,
        shifts,
        config,
        assignment_vars,
        course_shortfall_vars,
        staff_shortfall_vars,
        min_hours_vars,
        max_hours_vars,
        extra_hours_vars,
        max_extra_var,
    )
    problem += pulp.lpSum(objective_terms), "TotalPenalty"

    for constraint in _build_shift_constraints(
        assistants,
        shifts,
        assignment_vars,
        course_shortfall_vars,
        staff_shortfall_vars,
    ):
        problem += constraint

    for constraint in _build_hour_constraints(
        assistants,
        shifts,
        assignment_vars,
        min_hours_vars,
        max_hours_vars,
        extra_hours_vars,
        max_extra_var,
        baseline_hours,
        config,
    ):
        problem += constraint

    if solver is None:
        solver = pulp.PULP_CBC_CMD(
            msg=int(config.log_solver_output),
            timeLimit=config.solver_time_limit,
            gapRel=config.solver_gap,
        )

    status_code = problem.solve(solver)
    status = pulp.LpStatus.get(status_code, "Unknown")
    objective_value = None if problem.objective is None else pulp.value(problem.objective)

    return _collect_results(
        status,
        status_code,
        objective_value,
        assistants,
        shifts,
        assignment_vars,
        course_shortfall_vars,
        staff_shortfall_vars,
    )


def _validate_inputs(assistants: Sequence[Assistant], shifts: Sequence[Shift]) -> None:
    if not assistants:
        raise ValueError("At least one assistant is required to build a schedule")
    if not shifts:
        raise ValueError("At least one shift is required to build a schedule")


def _build_assignment_variables(
    assistants: Sequence[Assistant],
    shifts: Sequence[Shift],
) -> Dict[Tuple[str, str], pulp.LpVariable]:
    assignment_vars: Dict[Tuple[str, str], pulp.LpVariable] = {}
    for assistant in assistants:
        for shift in shifts:
            if assistant.is_available(shift):
                var_name = f"x_{assistant.id}_{shift.id}"
                assignment_vars[(assistant.id, shift.id)] = pulp.LpVariable(var_name, 0, 1, cat="Binary")

    if not assignment_vars:
        raise ValueError(
            "No feasible assignments were generated. Check availability windows "
            "and shift definitions."
        )
    return assignment_vars


def _build_course_shortfall_variables(
    shifts: Sequence[Shift],
) -> Dict[Tuple[str, str], pulp.LpVariable]:
    course_shortfall_vars: Dict[Tuple[str, str], pulp.LpVariable] = {}
    for shift in shifts:
        for demand in shift.course_demands:
            key = (shift.id, demand.course_code.upper())
            var_name = f"shortfall_{shift.id}_{demand.course_code}"
            upper = demand.tutors_required if demand.tutors_required > 0 else 0
            course_shortfall_vars[key] = pulp.LpVariable(var_name, lowBound=0, upBound=upper, cat="Continuous")
    return course_shortfall_vars


def _build_staff_shortfall_variables(
    shifts: Sequence[Shift],
    config: SchedulerConfig,
) -> Dict[str, pulp.LpVariable]:
    staff_shortfall_vars: Dict[str, pulp.LpVariable] = {}
    for shift in shifts:
        up_bound = config.staff_shortfall_max if config.staff_shortfall_max is not None else shift.min_staff
        var_name = f"staff_shortfall_{shift.id}"
        staff_shortfall_vars[shift.id] = pulp.LpVariable(
            var_name,
            lowBound=0,
            upBound=max(up_bound, 0),
            cat="Continuous",
        )
    return staff_shortfall_vars


def _build_hour_slack_variables(
    assistants: Sequence[Assistant],
    baseline_hours: Dict[str, float],
) -> Tuple[Dict[str, pulp.LpVariable], Dict[str, pulp.LpVariable], Dict[str, pulp.LpVariable], pulp.LpVariable]:
    min_hours_vars: Dict[str, pulp.LpVariable] = {}
    max_hours_vars: Dict[str, pulp.LpVariable] = {}
    extra_hours_vars: Dict[str, pulp.LpVariable] = {}
    max_extra_var = pulp.LpVariable("max_extra_hours", lowBound=0)
    
    for assistant in assistants:
        # Always create slack variables for baseline constraints (fairness requirement)
        baseline = baseline_hours.get(assistant.id, 0.0)
        if baseline > 0:
            min_hours_vars[assistant.id] = pulp.LpVariable(f"baseline_shortfall_{assistant.id}", lowBound=0)
        
        # Create max hours slack if needed
        if assistant.max_hours is not None:
            max_hours_vars[assistant.id] = pulp.LpVariable(f"max_hours_excess_{assistant.id}", lowBound=0)
        
        # Add extra hours variable for fairness tracking
        extra_hours_vars[assistant.id] = pulp.LpVariable(f"extra_hours_{assistant.id}", lowBound=0)
    
    return min_hours_vars, max_hours_vars, extra_hours_vars, max_extra_var


def _build_objective_terms(
    assistants: Sequence[Assistant],
    shifts: Sequence[Shift],
    config: SchedulerConfig,
    assignment_vars: Dict[Tuple[str, str], pulp.LpVariable],
    course_shortfall_vars: Dict[Tuple[str, str], pulp.LpVariable],
    staff_shortfall_vars: Dict[str, pulp.LpVariable],
    min_hours_vars: Dict[str, pulp.LpVariable],
    max_hours_vars: Dict[str, pulp.LpVariable],
    extra_hours_vars: Dict[str, pulp.LpVariable],
    max_extra_var: pulp.LpVariable,
) -> List[pulp.LpAffineExpression]:
    objective_terms: List[pulp.LpAffineExpression] = []

    # Course shortfall penalties
    for (shift_id, course_code), var in course_shortfall_vars.items():
        shift = next(shift for shift in shifts if shift.id == shift_id)
        weight = next(
            demand.weight for demand in shift.course_demands if demand.course_code.upper() == course_code
        )
        objective_terms.append(config.course_shortfall_penalty * weight * var)

    # Staff shortfall penalties
    for var in staff_shortfall_vars.values():
        objective_terms.append(config.understaffed_penalty * var)

    # Minimum hours penalties (baseline violations)
    for var in min_hours_vars.values():
        objective_terms.append(config.min_hours_penalty * var)
    
    # Maximum hours penalties
    for var in max_hours_vars.values():
        objective_terms.append(config.max_hours_penalty * var)

    # Fairness penalties for extra hours
    for var in extra_hours_vars.values():
        objective_terms.append(config.extra_hours_penalty * var)
    
    # High penalty for maximum extra hours (promotes fairness)
    objective_terms.append(config.max_extra_penalty * max_extra_var)

    # Cost per hour penalties
    for assistant in assistants:
        if assistant.cost_per_hour == 0:
            continue
        for shift in shifts:
            var = assignment_vars.get((assistant.id, shift.id))
            if var is not None:
                objective_terms.append(assistant.cost_per_hour * shift.duration_hours * var)

    return objective_terms


def _build_shift_constraints(
    assistants: Sequence[Assistant],
    shifts: Sequence[Shift],
    assignment_vars: Dict[Tuple[str, str], pulp.LpVariable],
    course_shortfall_vars: Dict[Tuple[str, str], pulp.LpVariable],
    staff_shortfall_vars: Dict[str, pulp.LpVariable],
) -> Iterable[pulp.LpConstraint]:
    for shift in shifts:
        assigned = pulp.lpSum(
            assignment_vars[(assistant.id, shift.id)]
            for assistant in assistants
            if (assistant.id, shift.id) in assignment_vars
        )
        min_constraint = assigned + staff_shortfall_vars[shift.id] >= shift.min_staff
        min_constraint.name = f"shift_min_staff_{shift.id}"
        yield min_constraint
        if shift.max_staff is not None:
            max_constraint = assigned <= shift.max_staff
            max_constraint.name = f"shift_max_staff_{shift.id}"
            yield max_constraint

        for demand in shift.course_demands:
            key = (shift.id, demand.course_code.upper())
            coverage = pulp.lpSum(
                assignment_vars[(assistant.id, shift.id)]
                for assistant in assistants
                if (assistant.id, shift.id) in assignment_vars and demand.course_code.upper() in assistant.course_set
            )
            cap_constraint = coverage <= demand.tutors_required
            cap_constraint.name = f"coverage_cap_{shift.id}_{demand.course_code}"
            yield cap_constraint

            shortfall_constraint = coverage + course_shortfall_vars[key] >= demand.tutors_required
            shortfall_constraint.name = f"coverage_shortfall_{shift.id}_{demand.course_code}"
            yield shortfall_constraint


def _build_baseline_constraints(
    assistant: Assistant,
    total_hours: pulp.LpAffineExpression,
    baseline: float,
    min_hours_vars: Dict[str, pulp.LpVariable],
    config: SchedulerConfig,
) -> Iterable[pulp.LpConstraint]:
    """Build baseline hour constraints for an assistant."""
    if baseline <= 0:
        return
        
    # Always use soft constraints with very high penalties for baseline
    # This implements the fairness requirement while maintaining feasibility
    slack = min_hours_vars.get(assistant.id)
    if slack is not None:
        min_constraint = total_hours + slack >= baseline
        min_constraint.name = f"baseline_hours_{assistant.id}"
        yield min_constraint
    elif not config.allow_minimum_violation:
        # If no slack variable and violations not allowed, create hard constraint
        # But only if the baseline is achievable given assistant's availability
        baseline_constraint = total_hours >= baseline  
        baseline_constraint.name = f"baseline_hard_{assistant.id}"
        yield baseline_constraint


def _build_fairness_constraints(
    assistant: Assistant,
    total_hours: pulp.LpAffineExpression,
    baseline: float,
    extra_hours_vars: Dict[str, pulp.LpVariable],
    max_extra_var: pulp.LpVariable,
) -> Iterable[pulp.LpConstraint]:
    """Build fairness constraints for extra hours."""
    extra_hours = extra_hours_vars.get(assistant.id)
    if extra_hours is None:
        return
        
    # Track extra hours above baseline (can be 0 if total_hours <= baseline)
    # extra_hours = max(0, total_hours - baseline)
    # We implement this as: extra_hours >= total_hours - baseline AND extra_hours >= 0
    extra_constraint = extra_hours >= total_hours - baseline
    extra_constraint.name = f"extra_hours_{assistant.id}"
    yield extra_constraint
    
    # Constraint for max extra hours fairness (bottleneck minimization)
    max_extra_constraint = extra_hours <= max_extra_var
    max_extra_constraint.name = f"max_extra_{assistant.id}"
    yield max_extra_constraint


def _build_max_hours_constraints(
    assistant: Assistant,
    total_hours: pulp.LpAffineExpression,
    max_hours_vars: Dict[str, pulp.LpVariable],
) -> Iterable[pulp.LpConstraint]:
    """Build maximum hours constraints for an assistant."""
    if assistant.max_hours is None:
        return
        
    excess = max_hours_vars.get(assistant.id)
    if excess is not None:
        max_constraint = total_hours - excess <= assistant.max_hours
        max_constraint.name = f"max_hours_{assistant.id}"
        yield max_constraint
    else:
        # Hard max hours constraint
        hard_max_constraint = total_hours <= assistant.max_hours
        hard_max_constraint.name = f"hard_max_hours_{assistant.id}"
        yield hard_max_constraint


def _build_hour_constraints(
    assistants: Sequence[Assistant],
    shifts: Sequence[Shift],
    assignment_vars: Dict[Tuple[str, str], pulp.LpVariable],
    min_hours_vars: Dict[str, pulp.LpVariable],
    max_hours_vars: Dict[str, pulp.LpVariable],
    extra_hours_vars: Dict[str, pulp.LpVariable],
    max_extra_var: pulp.LpVariable,
    baseline_hours: Dict[str, float],
    config: SchedulerConfig,
) -> Iterable[pulp.LpConstraint]:
    for assistant in assistants:
        total_hours = pulp.lpSum(
            shift.duration_hours * assignment_vars[(assistant.id, shift.id)]
            for shift in shifts
            if (assistant.id, shift.id) in assignment_vars
        )
        
        baseline = baseline_hours.get(assistant.id, 0.0)
        
        # Build baseline constraints
        yield from _build_baseline_constraints(
            assistant, total_hours, baseline, min_hours_vars, config
        )
        
        # Build fairness constraints 
        yield from _build_fairness_constraints(
            assistant, total_hours, baseline, extra_hours_vars, max_extra_var
        )
        
        # Build max hours constraints
        yield from _build_max_hours_constraints(
            assistant, total_hours, max_hours_vars
        )


def _collect_results(
    status: str,
    status_code: int,
    objective_value: Optional[float],
    assistants: Sequence[Assistant],
    shifts: Sequence[Shift],
    assignment_vars: Dict[Tuple[str, str], pulp.LpVariable],
    course_shortfall_vars: Dict[Tuple[str, str], pulp.LpVariable],
    staff_shortfall_vars: Dict[str, pulp.LpVariable],
) -> ScheduleResult:
    shift_index = {shift.id: shift for shift in shifts}
    assignments: List[Tuple[str, str]] = []
    assistant_hours: Dict[str, float] = {assistant.id: 0.0 for assistant in assistants}

    if status in {"Optimal", "Feasible"}:
        for (assistant_id, shift_id), var in assignment_vars.items():
            value = var.value()
            if value is None:
                continue
            if value > 0.5:
                assignments.append((assistant_id, shift_id))
                assistant_hours[assistant_id] += shift_index[shift_id].duration_hours

    course_shortfalls = {
        key: float(var.value()) if var.value() is not None else 0.0
        for key, var in course_shortfall_vars.items()
    }
    staff_shortfalls = {
        shift_id: float(var.value()) if var.value() is not None else 0.0
        for shift_id, var in staff_shortfall_vars.items()
    }

    return ScheduleResult(
        status=status,
        objective_value=objective_value,
        assignments=assignments,
        assistant_hours=assistant_hours,
        course_shortfalls=course_shortfalls,
        staff_shortfalls=staff_shortfalls,
        solver_status_code=status_code,
    )
