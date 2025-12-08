"""Pluggable constraint strategies for domain-specific scheduling.

This module implements the Strategy Pattern to make scheduler_lp a general-purpose
rostering toolkit. Different scheduling domains (help desk, exams, marking, etc.)
are implemented as separate strategy classes that define their own constraints
and objective functions.

Usage:
    from scheduler_lp import solve_schedule
    from scheduler_lp.constraint_strategies import HelpDeskWeeklyStrategy
    
    result = solve_schedule(
        assistants,
        shifts,
        strategy=HelpDeskWeeklyStrategy(),
        config=config
    )
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Sequence, Tuple

if TYPE_CHECKING:
    from .linear_scheduler import (
        Assistant,
        SchedulerConfig,
        Shift,
    )

try:
    import pulp  # type: ignore
except ImportError as exc:
    raise ImportError(
        "PuLP is required to use scheduler_lp.\n"
        "Install it with `pip install pulp` or add it to your environment."
    ) from exc


class ConstraintStrategy(ABC):
    """Abstract base class for domain-specific scheduling constraints.
    
    Subclass this to create custom scheduling logic for different domains:
    - Help desk rostering (course coverage + fairness)
    - Exam invigilation (room capacity + seniority requirements)
    - Script marking (workload balancing + expertise matching)
    - Nurse rostering (shift rotation + qualification matching)
    - And more...
    
    The strategy pattern allows the core solver to remain domain-agnostic
    while supporting arbitrarily complex business rules through subclassing.
    """
    
    @abstractmethod
    def prepare_variables(
        self,
        assistants: Sequence[Assistant],
        shifts: Sequence[Shift],
        config: SchedulerConfig,
    ) -> Dict[str, any]:
        """Create auxiliary decision variables needed by this strategy.
        
        Args:
            assistants: Workers to schedule
            shifts: Time slots requiring coverage
            config: Penalty weights and solver settings
        
        Returns:
            Dictionary of auxiliary variables to pass to build_constraints()
            and build_objective_terms(). For example:
            {
                'shortfall_vars': {...},
                'slack_vars': {...},
                'fairness_vars': {...}
            }
        """
        pass
    
    @abstractmethod
    def build_constraints(
        self,
        assistants: Sequence[Assistant],
        shifts: Sequence[Shift],
        assignment_vars: Dict[Tuple[str, str], pulp.LpVariable],
        config: SchedulerConfig,
        **strategy_vars
    ) -> Iterable[pulp.LpConstraint]:
        """Generate domain-specific linear programming constraints.
        
        Args:
            assistants: Workers to schedule
            shifts: Time slots requiring coverage
            assignment_vars: Binary variables x_{assistant_id, shift_id}
            config: Penalty weights and solver settings
            **strategy_vars: Auxiliary variables from prepare_variables()
        
        Returns:
            Iterator of PuLP constraints to add to the LP problem.
            Each constraint should have a descriptive .name attribute.
        
        Example:
            # Ensure minimum coverage for each shift
            for shift in shifts:
                assigned = pulp.lpSum(
                    assignment_vars.get((a.id, shift.id), 0)
                    for a in assistants
                )
                constraint = assigned >= shift.min_staff
                constraint.name = f"min_coverage_{shift.id}"
                yield constraint
        """
        pass
    
    @abstractmethod
    def build_objective_terms(
        self,
        assistants: Sequence[Assistant],
        shifts: Sequence[Shift],
        assignment_vars: Dict[Tuple[str, str], pulp.LpVariable],
        config: SchedulerConfig,
        **strategy_vars
    ) -> List[pulp.LpAffineExpression]:
        """Generate domain-specific objective function terms to minimize.
        
        Args:
            assistants: Workers to schedule
            shifts: Time slots requiring coverage
            assignment_vars: Binary variables x_{assistant_id, shift_id}
            config: Penalty weights and solver settings
            **strategy_vars: Auxiliary variables from prepare_variables()
        
        Returns:
            List of PuLP expressions to sum in the objective function.
            Higher penalty weights prioritize satisfying certain constraints.
        
        Example:
            objective_terms = []
            
            # Penalize understaffed shifts
            for shift_id, shortfall_var in shortfall_vars.items():
                objective_terms.append(100.0 * shortfall_var)
            
            # Penalize unfair workload distribution
            objective_terms.append(20.0 * max_workload_var)
            
            return objective_terms
        """
        pass
    
    def validate_inputs(
        self,
        assistants: Sequence[Assistant],
        shifts: Sequence[Shift],
        config: SchedulerConfig,
    ) -> None:
        """Optional: Perform domain-specific input validation.
        
        Override this method to add custom validation logic for your
        scheduling domain. For example, verify that shifts have required
        metadata fields or that assistants have necessary qualifications.
        
        Args:
            assistants: Workers to schedule
            shifts: Time slots requiring coverage
            config: Penalty weights and solver settings
        
        Raises:
            ValueError: If inputs are invalid for this strategy
        """
        pass
    
    def collect_results(
        self,
        status: str,
        status_code: int,
        objective_value: Optional[float],
        assistants: Sequence[Assistant],
        shifts: Sequence[Shift],
        assignment_vars: Dict[Tuple[str, str], pulp.LpVariable],
        **strategy_vars
    ) -> 'ScheduleResult':
        """Optional: Customize result collection for this strategy.
        
        Override this to include domain-specific diagnostics in the result.
        By default, uses the generic result collector from linear_scheduler.
        
        Args:
            status: Solver status string ("Optimal", "Feasible", etc.)
            status_code: Numeric solver status code
            objective_value: Final objective function value
            assistants: Workers scheduled
            shifts: Time slots scheduled
            assignment_vars: Solution values for assignment variables
            **strategy_vars: Auxiliary variables from prepare_variables()
        
        Returns:
            ScheduleResult with assignments and diagnostics
        """
        # Import here to avoid circular dependency
        from .linear_scheduler import _collect_results
        
        return _collect_results(
            status,
            status_code,
            objective_value,
            assistants,
            shifts,
            assignment_vars,
            strategy_vars.get('course_shortfall_vars', {}),
            strategy_vars.get('staff_shortfall_vars', {}),
        )


class HelpDeskWeeklyStrategy(ConstraintStrategy):
    """Original help desk scheduling strategy with course coverage and fairness.
    
    This strategy implements the business rules for university help desk rostering:
    
    1. **Course Coverage**: Each shift has demand for tutors with specific course
       expertise. Shortfalls are penalized in the objective function.
    
    2. **Shift Staffing**: Each shift requires a minimum number of staff (usually 2-3).
       Understaffing is heavily penalized.
    
    3. **Fairness**: Assistants should work similar hours based on a baseline target
       (default 6 hours/week). Extra hours beyond baseline are penalized to ensure
       fair distribution.
    
    4. **Hour Limits**: Assistants have minimum and maximum hour constraints based
       on their availability and preferences.
    
    This is the default strategy used by solve_helpdesk_schedule() for backward
    compatibility with the Flask application.
    """
    
    def prepare_variables(
        self,
        assistants: Sequence[Assistant],
        shifts: Sequence[Shift],
        config: SchedulerConfig,
    ) -> Dict[str, any]:
        """Create course shortfall, staff shortfall, and fairness variables."""
        from .linear_scheduler import (
            _build_course_shortfall_variables,
            _build_staff_shortfall_variables,
            _build_hour_slack_variables,
            _calculate_baseline_hours,
        )
        
        # Calculate baseline hours for fairness
        baseline_hours = _calculate_baseline_hours(assistants, shifts, config)
        
        # Create auxiliary variables
        course_shortfall_vars = _build_course_shortfall_variables(shifts)
        staff_shortfall_vars = _build_staff_shortfall_variables(shifts, config)
        min_hours_vars, max_hours_vars, extra_hours_vars, max_extra_var = \
            _build_hour_slack_variables(assistants, baseline_hours)
        
        return {
            'baseline_hours': baseline_hours,
            'course_shortfall_vars': course_shortfall_vars,
            'staff_shortfall_vars': staff_shortfall_vars,
            'min_hours_vars': min_hours_vars,
            'max_hours_vars': max_hours_vars,
            'extra_hours_vars': extra_hours_vars,
            'max_extra_var': max_extra_var,
        }
    
    def build_constraints(
        self,
        assistants: Sequence[Assistant],
        shifts: Sequence[Shift],
        assignment_vars: Dict[Tuple[str, str], pulp.LpVariable],
        config: SchedulerConfig,
        **strategy_vars
    ) -> Iterable[pulp.LpConstraint]:
        """Generate shift coverage and hour fairness constraints."""
        from .linear_scheduler import (
            _build_shift_constraints,
            _build_hour_constraints,
        )
        
        # Extract strategy variables
        course_shortfall_vars = strategy_vars['course_shortfall_vars']
        staff_shortfall_vars = strategy_vars['staff_shortfall_vars']
        min_hours_vars = strategy_vars['min_hours_vars']
        max_hours_vars = strategy_vars['max_hours_vars']
        extra_hours_vars = strategy_vars['extra_hours_vars']
        max_extra_var = strategy_vars['max_extra_var']
        baseline_hours = strategy_vars['baseline_hours']
        
        # Shift coverage constraints
        yield from _build_shift_constraints(
            assistants,
            shifts,
            assignment_vars,
            course_shortfall_vars,
            staff_shortfall_vars,
        )
        
        # Hour fairness constraints
        yield from _build_hour_constraints(
            assistants,
            shifts,
            assignment_vars,
            min_hours_vars,
            max_hours_vars,
            extra_hours_vars,
            max_extra_var,
            baseline_hours,
            config,
        )
    
    def build_objective_terms(
        self,
        assistants: Sequence[Assistant],
        shifts: Sequence[Shift],
        assignment_vars: Dict[Tuple[str, str], pulp.LpVariable],
        config: SchedulerConfig,
        **strategy_vars
    ) -> List[pulp.LpAffineExpression]:
        """Generate penalty terms for course shortfalls, understaffing, and unfairness."""
        from .linear_scheduler import _build_objective_terms
        
        return _build_objective_terms(
            assistants,
            shifts,
            config,
            assignment_vars,
            strategy_vars['course_shortfall_vars'],
            strategy_vars['staff_shortfall_vars'],
            strategy_vars['min_hours_vars'],
            strategy_vars['max_hours_vars'],
            strategy_vars['extra_hours_vars'],
            strategy_vars['max_extra_var'],
        )
    
    def validate_inputs(
        self,
        assistants: Sequence[Assistant],
        shifts: Sequence[Shift],
        config: SchedulerConfig,
    ) -> None:
        """Validate that shifts have course demands (required for help desk scheduling)."""
        for shift in shifts:
            if not shift.course_demands:
                raise ValueError(
                    f"Shift {shift.id} has no course_demands. "
                    "HelpDeskWeeklyStrategy requires course coverage requirements."
                )