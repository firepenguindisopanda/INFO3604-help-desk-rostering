from flask import jsonify, request
from ortools.linear_solver import pywraplp

# l = length, w = width

# max lw
# s.t 2l + 2w <= 80
# l, w >= 0

def L1Question1(perimeter: float):

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
    solver.Add(2 * l + 2 * w <= perimeter)

    #Linearizing the product constraint using a piecewise linear approximation
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

    area = l.solution_value() * w.solution_value()

    return l.solution_value(), w.solution_value(), area

# max 3000a + 5000b
# s.t 3a + 2b <= 18
# a <= 4
# b <= 6
# a,b >= 0

def L1Question2(aUnit: float, bUnit:float, resources:float):
    # Instantiate a Glop solver, naming it LinearExample.
    solver = pywraplp.Solver.CreateSolver("GLOP")
    if not solver:
        return

    # Create the two variables and let them take on any non-negative value.
    a = solver.NumVar(0, aUnit, "4")
    b = solver.NumVar(0, bUnit, "6")

    print("Number of variables =", solver.NumVariables())

    # Constraint 0: 3a + 2b <= 18
    solver.Add(3*a + 2*b <= resources)

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

    return a.solution_value(), b.solution_value(), solver.Objective().Value()


from flask import Blueprint

lab_bp = Blueprint('lab', __name__)

@lab_bp.route('/solve_q1', methods=['POST'])
def solve_q1():
    try:
        data = request.get_json()
        perimeter = float(data['perimeter'])
        
        if perimeter <= 0:
            return jsonify({'error': 'Perimeter must be positive'}), 400
            
        length, width, area = L1Question1(perimeter)
        
        return jsonify({
            'length': length,
            'width': width,
            'area': area
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@lab_bp.route('/solve_q2', methods=['POST'])
def solve_q2():
    try:
        data = request.get_json()
        max_a = float(data['max_a'])
        max_b = float(data['max_b'])
        resource_constraint = float(data['resource_constraint'])
        
        if any(x <= 0 for x in [max_a, max_b, resource_constraint]):
            return jsonify({'error': 'All constraints must be positive'}), 400
            
        a, b, profit = L1Question2(max_a, max_b, resource_constraint)
        
        return jsonify({
            'a': a,
            'b': b,
            'profit': profit
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400
