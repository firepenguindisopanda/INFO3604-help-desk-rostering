"""Standalone help desk scheduling via OR-Tools CP-SAT.

This module mirrors the CP-SAT model used inside the Flask API so that
experiments in notebooks or scripts produce identical behaviour. It is
framework-agnostic: no Flask, SQLAlchemy, or application globals are
required. Inputs are plain Python dataclasses; outputs are simple
containers suitable for analysis or visualisation.

The model structure follows `App.controllers.schedule.generate_help_desk_schedule_ortools`:
- Weighted course coverage shortfall minimisation
- Soft minimum shifts (hours_minimum) with a penalty
- Soft understaffing penalties (0 or 1 tutor in a shift)
- Availability and capability filtering per assistant
- Upper bound on staff per shift

Only CP-SAT is used here; if you want PuLP/linear programming, use the
`scheduler_lp` package in this repository.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:
    from ortools.sat.python import cp_model
except ImportError as exc:  # pragma: no cover - dependency guard
    raise ImportError(
        "OR-Tools is required to use cp_sat_solver_scheduler.\n"
        "Install it with `pip install ortools` or add it to your environment."
    ) from exc


# ---------------------------------------------------------------------------
# Data structures (mirrors scheduler_lp for notebook parity)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AvailabilityWindow:
    """Represents when an assistant is available to work."""

    day_of_week: int  # 0=Monday, 6=Sunday
    start: time # inclusive
    end: time # exclusive

    def __post_init__(self) -> None:
        if not 0 <= self.day_of_week <= 6:
            raise ValueError("day_of_week must be in the range [0, 6]")
        if self.end <= self.start:
            raise ValueError("Availability end time must be after start time")

    def covers(self, shift: "Shift") -> bool:
        if shift.day_of_week != self.day_of_week:
            return False
        return self.start <= shift.start <= shift.end <= self.end


@dataclass
class Assistant:
    """Metadata required to schedule an assistant."""

    id: str
    courses: Sequence[str]
    availability: Sequence[AvailabilityWindow]
    min_shifts: int = 4  # Equivalent to hours_minimum in the Flask model
    cost_per_hour: float = 0.0  # Unused here, kept for parity

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
        base_day = date(2000, 1, 1)
        start_dt = datetime.combine(base_day, self.start)
        end_dt = datetime.combine(base_day, self.end)
        return (end_dt - start_dt).total_seconds() / 3600.0


@dataclass
class SchedulerConfig:
    """Weights and solver settings matching the Flask CP-SAT defaults."""

    # Penalties / weights (aligned with App.controllers.schedule)
    min_shifts_penalty: int = 10
    zero_tutor_penalty: int = 100
    one_tutor_penalty: int = 50

    # Staffing bounds
    min_staff_per_shift: int = 2
    max_staff_per_shift: int = 3

    # Course demand defaults when not provided
    default_tutors_required: int = 2
    default_course_weight: int = 2

    # Solver controls
    solver_time_limit: float = 240.0  # Matches CP_SAT_TIME_LIMIT in default_config.py
    num_search_workers: int = 8
    log_search_progress: bool = True

    # Optional date range to scale minimum shifts (partial weeks)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


@dataclass
class ScheduleResult:
    status: str
    objective_value: Optional[float]
    assignments: List[Tuple[str, str]]
    assistant_hours: Dict[str, float]
    course_shortfalls: Dict[Tuple[str, str], int]
    staff_shortfalls: Dict[str, int]
    solver_status_code: int

    def to_assignment_matrix(self) -> Mapping[str, List[str]]:
        matrix: Dict[str, List[str]] = {}
        for assistant_id, shift_id in self.assignments:
            matrix.setdefault(assistant_id, []).append(shift_id)
        return matrix


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _infer_date_range(shifts: Sequence[Shift], config: SchedulerConfig) -> Tuple[Optional[date], Optional[date]]:
    if config.start_date and config.end_date:
        return config.start_date, config.end_date

    dates: List[date] = []
    for shift in shifts:
        raw = shift.metadata.get("date")
        if isinstance(raw, date):
            dates.append(raw)
        elif isinstance(raw, datetime):
            dates.append(raw.date())
        elif isinstance(raw, str):
            try:
                dates.append(date.fromisoformat(raw))
            except ValueError:
                continue

    if not dates:
        return None, None

    return min(dates), max(dates)


def _weekday_count(start: date, end: date) -> int:
    days = 0
    current = start
    while current <= end:
        if current.weekday() < 5:
            days += 1
        current += timedelta(days=1)
    return days


def _scale_minimum_shifts(min_shifts: int, start: Optional[date], end: Optional[date]) -> int:
    if start is None or end is None:
        return min_shifts

    weekday_days = _weekday_count(start, end)
    if weekday_days <= 0:
        return min_shifts

    scaling_factor = weekday_days / 5.0
    scaled = int(min_shifts * scaling_factor)
    return max(1, scaled)


def _build_capability_matrix(assistants: Sequence[Assistant], course_codes: Sequence[str]) -> Dict[Tuple[int, int], int]:
    t: Dict[Tuple[int, int], int] = {}
    for i, assistant in enumerate(assistants):
        for k, course_code in enumerate(course_codes):
            t[i, k] = 1 if course_code.upper() in assistant.course_set else 0
    return t


def _build_availability_matrix(assistants: Sequence[Assistant], shifts: Sequence[Shift]) -> Dict[Tuple[int, int], int]:
    a: Dict[Tuple[int, int], int] = {}
    for i, assistant in enumerate(assistants):
        for j, shift in enumerate(shifts):
            a[i, j] = 1 if assistant.is_available(shift) else 0
    return a


def _build_demand_weights(
    shifts: Sequence[Shift],
    course_codes: Sequence[str],
    config: SchedulerConfig,
) -> Tuple[Dict[Tuple[int, int], int], Dict[Tuple[int, int], int]]:
    d: Dict[Tuple[int, int], int] = {}
    w: Dict[Tuple[int, int], int] = {}

    for j, shift in enumerate(shifts):
        # Map course code -> demand for quick lookup
        shift_demands = {cd.course_code.upper(): cd for cd in shift.course_demands}
        for k, course_code in enumerate(course_codes):
            demand = shift_demands.get(course_code)
            if demand:
                d[j, k] = int(demand.tutors_required)
                w[j, k] = int(demand.weight if demand.weight is not None else demand.tutors_required)
            else:
                d[j, k] = config.default_tutors_required
                w[j, k] = config.default_course_weight
    return d, w


def _validate_inputs(assistants: Sequence[Assistant], shifts: Sequence[Shift]) -> None:
    if not assistants:
        raise ValueError("At least one assistant is required")
    if not shifts:
        raise ValueError("At least one shift is required")


def _course_shortfall_terms(
    model: cp_model.CpModel,
    x: Dict[Tuple[int, int], cp_model.IntVar],
    t: Dict[Tuple[int, int], int],
    d: Dict[Tuple[int, int], int],
    w: Dict[Tuple[int, int], int],
    staff_count: int,
    shift_count: int,
    course_count: int,
) -> Tuple[List[cp_model.LinearExpr], Dict[Tuple[int, int], cp_model.IntVar]]:
    terms: List[cp_model.LinearExpr] = []
    shortfalls: Dict[Tuple[int, int], cp_model.IntVar] = {}

    for j in range(shift_count):
        for k in range(course_count):
            capable = [x[i, j] for i in range(staff_count) if t[i, k] == 1]
            if not capable:
                continue
            shortfall = model.NewIntVar(0, d[j, k], f"shortfall_{j}_{k}")
            model.Add(shortfall >= d[j, k] - sum(capable))
            terms.append(shortfall * w[j, k])
            shortfalls[j, k] = shortfall

    return terms, shortfalls


def _capacity_constraints(
    model: cp_model.CpModel,
    x: Dict[Tuple[int, int], cp_model.IntVar],
    t: Dict[Tuple[int, int], int],
    d: Dict[Tuple[int, int], int],
    staff_count: int,
    shift_count: int,
    course_count: int,
) -> None:
    for j in range(shift_count):
        for k in range(course_count):
            capable = [x[i, j] for i in range(staff_count) if t[i, k] == 1]
            if capable:
                model.Add(sum(capable) <= d[j, k])


def _minimum_shift_terms(
    model: cp_model.CpModel,
    x: Dict[Tuple[int, int], cp_model.IntVar],
    assistants: Sequence[Assistant],
    shift_count: int,
    cfg: SchedulerConfig,
    start_dt: Optional[date],
    end_dt: Optional[date],
) -> List[cp_model.LinearExpr]:
    terms: List[cp_model.LinearExpr] = []
    for i, assistant in enumerate(assistants):
        required_shifts = _scale_minimum_shifts(assistant.min_shifts, start_dt, end_dt)
        total_assigned = sum(x[i, j] for j in range(shift_count))
        shortfall = model.NewIntVar(0, required_shifts, f"hours_shortfall_{i}")
        model.Add(shortfall >= required_shifts - total_assigned)
        terms.append(shortfall * cfg.min_shifts_penalty)
    return terms


def _staffing_terms(
    model: cp_model.CpModel,
    x: Dict[Tuple[int, int], cp_model.IntVar],
    a: Dict[Tuple[int, int], int],
    cfg: SchedulerConfig,
    staff_count: int,
    shift_count: int,
) -> List[cp_model.LinearExpr]:
    terms: List[cp_model.LinearExpr] = []
    for j in range(shift_count):
        shift_tutors = sum(x[i, j] for i in range(staff_count))
        zero_tutors = model.NewBoolVar(f"zero_tutors_{j}")
        one_tutor = model.NewBoolVar(f"one_tutor_{j}")

        model.Add(shift_tutors == 0).OnlyEnforceIf(zero_tutors)
        model.Add(shift_tutors == 1).OnlyEnforceIf(one_tutor)

        terms.append(zero_tutors * cfg.zero_tutor_penalty)
        terms.append(one_tutor * cfg.one_tutor_penalty)

        model.Add(shift_tutors <= cfg.max_staff_per_shift)

        for i in range(staff_count):
            if a[i, j] == 0:
                model.Add(x[i, j] == 0)

    return terms


def _collect_assignments(
    solver: cp_model.CpSolver,
    x: Dict[Tuple[int, int], cp_model.IntVar],
    assistants: Sequence[Assistant],
    shifts: Sequence[Shift],
) -> List[Tuple[str, str]]:
    assignments: List[Tuple[str, str]] = []
    for i, assistant in enumerate(assistants):
        for j, shift in enumerate(shifts):
            if solver.Value(x[i, j]) == 1:
                assignments.append((assistant.id, shift.id))
    return assignments


def _build_assignment_variables(
    model: cp_model.CpModel, staff_count: int, shift_count: int
) -> Dict[Tuple[int, int], cp_model.IntVar]:
    return {
        (i, j): model.NewBoolVar(f"x_{i}_{j}")
        for i in range(staff_count)
        for j in range(shift_count)
    }


def _assistant_hours(
    assignments: Sequence[Tuple[str, str]],
    shift_lookup: Mapping[str, Shift],
    assistants: Sequence[Assistant],
) -> Dict[str, float]:
    hours: Dict[str, float] = {assistant.id: 0.0 for assistant in assistants}
    for assistant_id, shift_id in assignments:
        hours[assistant_id] = hours.get(assistant_id, 0.0) + shift_lookup[shift_id].duration_hours
    return hours


def _extract_course_shortfalls(
    shortfalls: Mapping[Tuple[int, int], cp_model.IntVar],
    solver: cp_model.CpSolver,
    shifts: Sequence[Shift],
    course_codes: Sequence[str],
) -> Dict[Tuple[str, str], int]:
    result: Dict[Tuple[str, str], int] = {}
    for (shift_idx, course_idx), var in shortfalls.items():
        value = int(solver.Value(var))
        if value > 0:
            result[(shifts[shift_idx].id, course_codes[course_idx])] = value
    return result


def _staff_shortfalls(
    solver: cp_model.CpSolver,
    x: Mapping[Tuple[int, int], cp_model.IntVar],
    shifts: Sequence[Shift],
    staff_count: int,
    shift_count: int,
    min_staff: int,
) -> Dict[str, int]:
    shortfalls: Dict[str, int] = {}
    for j in range(shift_count):
        assigned = sum(1 for i in range(staff_count) if solver.Value(x[i, j]) == 1)
        if assigned < min_staff:
            shortfalls[shifts[j].id] = min_staff - assigned
    return shortfalls

# Solver
def solve_helpdesk_schedule(
    assistants: Sequence[Assistant],
    shifts: Sequence[Shift],
    *,
    config: Optional[SchedulerConfig] = None,
) -> ScheduleResult:
    """Solve the help desk scheduling problem with CP-SAT.

    Arguments mirror the PuLP helper in `scheduler_lp` so the same data
    transformation code can be reused in notebooks.
    """

    _validate_inputs(assistants, shifts)
    cfg = config or SchedulerConfig()

    # Build the course universe from both demands and assistant capabilities
    course_codes = sorted({
        cd.course_code.upper()
        for shift in shifts
        for cd in shift.course_demands
    } | {code for assistant in assistants for code in assistant.course_set})

    if not course_codes:
        raise ValueError("No course codes found in assistants or shift demands")

    # Matrices
    t = _build_capability_matrix(assistants, course_codes)
    a = _build_availability_matrix(assistants, shifts)
    d, w = _build_demand_weights(shifts, course_codes, cfg)

    model = cp_model.CpModel()

    staff_count = len(assistants)
    shift_count = len(shifts)
    course_count = len(course_codes)

    # Decision variables
    x = _build_assignment_variables(model, staff_count, shift_count)

    # Objective components
    shortfall_terms, shortfalls = _course_shortfall_terms(
        model, x, t, d, w, staff_count, shift_count, course_count
    )
    _capacity_constraints(model, x, t, d, staff_count, shift_count, course_count)

    start_dt, end_dt = _infer_date_range(shifts, cfg)
    min_shift_terms = _minimum_shift_terms(
        model, x, assistants, shift_count, cfg, start_dt, end_dt
    )
    staffing_terms = _staffing_terms(
        model, x, a, cfg, staff_count, shift_count
    )

    objective_terms: List[cp_model.LinearExpr] = (
        shortfall_terms + min_shift_terms + staffing_terms
    )

    model.Minimize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(cfg.solver_time_limit)
    solver.parameters.num_search_workers = int(cfg.num_search_workers)
    solver.parameters.log_search_progress = bool(cfg.log_search_progress)

    status_code = solver.Solve(model)
    status = cp_model.StatusName(status_code)

    if status_code not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return ScheduleResult(
            status=status,
            objective_value=None,
            assignments=[],
            assistant_hours={},
            course_shortfalls={},
            staff_shortfalls={},
            solver_status_code=status_code,
        )

    # Collect assignments
    assignments = _collect_assignments(solver, x, assistants, shifts)
    shift_lookup = {shift.id: shift for shift in shifts}
    assistant_hours = _assistant_hours(assignments, shift_lookup, assistants)
    course_shortfalls = _extract_course_shortfalls(shortfalls, solver, shifts, course_codes)
    staff_shortfalls = _staff_shortfalls(
        solver, x, shifts, staff_count, shift_count, cfg.min_staff_per_shift
    )

    objective_value = solver.ObjectiveValue()

    return ScheduleResult(
        status=status,
        objective_value=objective_value,
        assignments=assignments,
        assistant_hours=assistant_hours,
        course_shortfalls=course_shortfalls,
        staff_shortfalls=staff_shortfalls,
        solver_status_code=status_code,
    )
