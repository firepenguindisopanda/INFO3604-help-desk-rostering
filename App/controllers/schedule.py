from ortools.sat.python import cp_model

def help_desk_scheduler(I, J, K):
    # Using a CP-SAT model
    model = cp_model.CpModel()
    
    # --- Data ---
    # Hard coded ranges for staff, shift and course indexes

    # Assuming staff can help with all courses
    t = {}
    for i in range(I):
        for k in range(K):
            t[i, k] = 1
    
    # Minimum desired number of tutors for each shift and course is 2
    d = {}
    for j in range(J):
        for k in range(K):
            d[j, k] = 2
    
    # Default weight = d
    w = {}
    for j in range(J):
        for k in range(K):
            w[j, k] = d[j, k]

    # Hard coded availability data
    a = {}
    a = [
        [1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 
        [0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 
        [0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0], 
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0], 
        [0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1], 
        [0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0], 
        [0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 
        [0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0], 
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0], 
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    ]
    
    # Hard coded minimum shifts
    r = {}
    r = [4, 4, 4, 4, 4, 4, 4, 4, 2, 4]

    # --- Variables ---
    x = {}
    for i in range(I):
        for j in range(J):
            x[i, j] = model.NewBoolVar(f'x_{i}_{j}')
    
    # --- Objective Function ---
    objective = []
    for j in range(J):
        for k in range(K):
            assigned_tutors = sum(x[i, j] * t[i, k] for i in range(I))
            objective.append((d[j, k] - assigned_tutors) * w[j, k])
    
    model.Minimize(sum(objective))

    # --- Constraints ---
    # Constraint 1: Σxij * tik ≤ djk for all j,k pairs
    for j in range(J):
        for k in range(K):
            constraint = sum(x[i, j] * t[i, k] for i in range(I))
            model.Add(constraint <= d[j, k])
    
    # Constraint 2: Σxij >= 4 for all i
    for i in range(I):
        constraint = sum(x[i, j] for j in range(J))
        model.Add(constraint >= r[i])
    
    # Constraint 3: Σxij >= 2 for all j
    for j in range(J):
        constraint = sum(x[i, j] for i in range(I))
        
        # Variable for constraint == 0
        weight_zero = model.NewBoolVar(f'weight_zero_{j}')
        model.Add(constraint == 0).OnlyEnforceIf(weight_zero)
        
        # Variable for constraint == 1
        weight_one = model.NewBoolVar(f'weight_one_{j}')
        model.Add(constraint == 1).OnlyEnforceIf(weight_one)
        
        # Adjusted constraint based on weighted values of availability less than 2
        model.Add(constraint + (2 * weight_zero + weight_one) >= 2)
    
    # Constraint 4: xij <= aij for all i
    for i in range(I):
        for j in range(J):
            model.Add(x[i, j] <= a[i][j])

    # --- Solve ---
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        assignments = {}
        
        for i in range(I):
            for j in range(J):
                if solver.Value(x[i, j]) == 1:
                    if j not in assignments:
                        assignments[j] = []
                    assignments[j].append(i)
        
        return {
            'status': 'success',
            'staff_index': {
                0: 'Daniel Rasheed',
                1: 'Michelle Liu',
                2: 'Stayaan Maharaj',
                3: 'Daniel Yatali',
                4: 'Satish Maharaj',
                5: 'Selena Madrey',
                6: 'Veron Ramkissoon',
                7: 'Tamika Ramkissoon',
                8: 'Samuel Mahadeo',
                9: 'Neha Maharaj'
            },
            'assignments': assignments
        }
    else:
        message = 'No solution found.'
        if status == cp_model.INFEASIBLE:
            message = 'Probleam is infeasible.'
        elif status == cp_model.MODEL_INVALID:
            message = 'Model is invalid.'
        elif status == cp_model.UNKNOWN:
            message = 'Solver status is unknown.'
        
        return {
            'status': 'error',
            'message': message
        }


def lab_assistant_scheduler():
    pass
