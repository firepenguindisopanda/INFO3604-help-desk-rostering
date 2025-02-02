from ortools.linear_solver import pywraplp

# l = length, w = width

# max lw
# s.t 2l + 2w <= 80
# l, w >= 0

def Question1():

    # Using the Glop solver
    solver = pywraplp.Solver.CreateSolver("GLOP")
    if not solver:
        return

    # Creating variables
    l = solver.NumVar(0, solver.infinity(), "l")
    w = solver.NumVar(0, solver.infinity(), "w")
    z = solver.NumVar(0, solver.infinity(), "z")

    print("Number of variables =", solver.NumVariables())

    # Constraint: 2l + 2w <= 80
    solver.Add(2 * l + 2 * w <= 80)

    # Linearize the product constraint using a piecewise linear approximation
    # Here we use a simple approach by adding multiple constraints
    # You can refine this by adding more constraints for better approximation
    for i in range(1, 11):
        solver.Add(z <= l * (i / 10) + w * (1 - i / 10))

    print("Number of constraints =", solver.NumConstraints())

    # Objective function: maximize z
    solver.Maximize(z)

    # Solve 
    print(f"Solving with {solver.SolverVersion()}")
    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        print("Solution:")
        print(f"Objective value = {solver.Objective().Value():0.1f}")
        print(f"l = {l.solution_value():0.1f}")
        print(f"w = {w.solution_value():0.1f}")
    else:
        print("The problem does not have an optimal solution.")

    print("\nAdvanced usage:")
    print(f"Problem solved in {solver.wall_time():d} milliseconds")
    print(f"Problem solved in {solver.iterations():d} iterations")


Question1()