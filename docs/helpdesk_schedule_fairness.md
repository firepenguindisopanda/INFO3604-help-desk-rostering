# Help Desk Scheduling Fairness Notes

This document captures the current plan for enforcing equitable hour assignments in the
help desk scheduler. Use it as a reference when refining the CP-SAT model in
`App/controllers/schedule.py` or when prototyping alternatives in the standalone
`scheduler_lp` module.

## Goals

1. Guarantee every active assistant receives up to six hours of work each week,
   bounded by their actual availability.
2. Assistants who offer fewer than six hours of availability should receive all
   of the shifts they can cover.
3. Only after every assistant hits their personal baseline should the solver
   distribute any remaining open slots, and those extras should be spread as
   evenly as possible.

## Baseline target logic

For each assistant:

- Count the number of feasible shifts they can actually work (based on
  availability, course capability, and day/time filters).
- Define their **baseline hours** as the smaller of `6` and that feasible count.
  (If you continue to use the `hours_minimum` field, set it to `6` before
  running the solver.)
- Assistants who can only cover 0–4 shifts will simply inherit that number as
  their baseline, guaranteeing they receive everything they asked for.

In code this typically looks like:

```python
available_shifts = {
    assistant.username: sum(
        1 for shift in shifts if assistant_is_available(assistant, shift)
    )
    for assistant in assistants
}
baseline_hours = {
    assistant.username: min(6, available_shifts[assistant.username])
    for assistant in assistants
}
```

## Hard minimum constraints

Replace the soft penalties currently used for minimum hours with hard
constraints:

```python
tutor_shifts = sum(x[i, j] for j in range(J))
target = baseline_hours[assistant.username]
model.Add(tutor_shifts >= target)
```

Keep a high-weight soft penalty only if you need a fallback mechanism when the
problem would otherwise become infeasible. To allow limited violations, enable a
flag (for example `generation_options["allow_minimum_violation"]`) that
re-introduces a slack variable and logs a warning when triggered.

## Extra-hour accounting

Track the number of shifts above baseline per assistant:

```python
extra_capacity = available_shifts[assistant.username] - target
extra_hours = model.NewIntVar(0, max(extra_capacity, 0), f"extra_{assistant.username}")
model.Add(extra_hours == tutor_shifts - target)
```

### Even distribution strategies

- **Minimise the maximum extra:** create a global `max_extra` variable, require
  every `extra_hours <= max_extra`, and prioritise it in the objective so nobody
  leaps too far ahead before the rest catch up.
- **Penalise per-person extras:** add terms like
  `objective_terms.append(extra_penalty * extra_hours)` with a penalty that is
  significantly larger than course shortfall weights. Combine both techniques if
  you want lexicographic control (first minimise the worst offender, then the
  total extras).

### Optional weekly caps

If you want to allow overflow but still bound total assignments, add:

```python
max_hours = baseline_hours[assistant.username]
if generation_options.get("permit_extras", True):
    max_hours = max(max_hours, available_shifts[assistant.username])
model.Add(tutor_shifts <= max_hours)
```

## Feasibility checks

Before solving, confirm the roster can satisfy everyone’s baseline:

```python
required_baseline = sum(baseline_hours.values())
max_capacity = len(shifts) * minimum_tutors_per_shift
if required_baseline > max_capacity:
    raise ValueError("Insufficient shift capacity for baseline targets")
```

Alternatively, add a single slack variable with a very high penalty to detect
shortfalls while keeping the solver running.

## Distribution order recap

1. Compute feasible shifts per assistant and establish baseline targets.
2. Add hard constraints `tutor_shifts >= baseline` for every assistant.
3. Track `extra_hours` and minimise them (individually or via a global
   bottleneck).
4. Apply optional upper bounds to prevent any assistant from exceeding their
   allowed total in the same pass.
5. Only when all baselines are satisfied should the solver hand out extra slots.
