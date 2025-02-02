from ortools.linear_solver import pywraplp

# max 3000a + 5000b
# s.t 3a + 2b <= 18
# a <= 4
# b <= 6
# a,b >= 0

def Question2():
    # Instantiate a Glop solver, naming it LinearExample.
    solver = pywraplp.Solver.CreateSolver("GLOP")
    if not solver:
        return

    # Create the two variables and let them take on any non-negative value.
    a = solver.NumVar(0, 4, "4")
    b = solver.NumVar(0, 6, "6")

    print("Number of variables =", solver.NumVariables())

    # Constraint 0: 3a + 2b <= 18
    solver.Add(3*a + 2*b <= 18.0)

    print("Number of constraints =", solver.NumConstraints())

    # Objective function: 3000a + 5000b
    solver.Maximize(3000*a + 5000*b)

    # Solve the system.
    print(f"Solving with {solver.SolverVersion()}")
    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        print("Solution:")
        print(f"Objective value = {solver.Objective().Value():0.1f}")
        print(f"a = {a.solution_value():0.1f}")
        print(f"b = {b.solution_value():0.1f}")
    else:
        print("The problem does not have an optimal solution.")

    print("\nAdvanced usage:")
    print(f"Problem solved in {solver.wall_time():d} milliseconds")
    print(f"Problem solved in {solver.iterations():d} iterations")


Question2()
