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
    # 0: Daniel Rasheed
    # 1: Michelle Liu
    # 2: Stayaan Maharaj
    # 3: Daniel Yatali
    # 4: Satish Maharaj
    # 5: Selena Madrey
    # 6: Veron Ramkissoon
    # 7: Tamika Ramkissoon
    # 8: Samuel Mahadeo
    # 0: Neha Maharaj
    
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
        model.Add(constraint >= 4)
    
    # Constraint 3: Σxij >= 2 for all j
    for i in range(I):
        constraint = sum(x[i, j] for i in range(I))
        model.Add(constraint >= 2)
    
    # # Constraint 4: xij <= aij for all i,j pairs
    # for i in range(I):
    #     for j in range(J):
    #         model.Add((1, 0)[x[i, j] <= a[i, j]])

    # --- Solve ---
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print('\nSolution:')
        print(f'Optimal objective value = {solver.ObjectiveValue()}')
        print('\nAssignments:')
        for i in range(I):
            for j in range(J):
                if solver.Value(x[i, j]) == 1:
                    print(f'Staff {i} assigned to Shift {j}')
        
        print('\nConstraint 1')
        for j in range(J):
            for k in range(K):
                pass
                # constraint_value = sum(solver.Value(x[i, j] * t[i, k] for i in range(I)))
                # print(f'\nShift {j}, Course {k}: Assigned = {constraint_value}, Desired = {d[j, k]}, Constraint satisfied: {constraint_value <= d[j, k]}')
        
        print('\nConstraint 2')
        for i in range(I):
            constraint_value = sum(solver.Value(x[i, j]) for j in range(J))
            print(f'Staff {i} Assigned shifts = {constraint_value}, Constraint satisfied: {constraint_value >= 4}')
        
        print('\nConstraint 3')
        for j in range(J):
            constraint_value = sum(solver.Value(x[i, j]) for i in range(I))
            print(f'Shift {j}: Assigned staff = {constraint_value}, Constraint satisfied: {constraint_value >= 2}')
        
        print('\nConstraint 4')
        for i in range(I):
            for j in range(J):
                pass
                # constraint_value = solver.Value(x[i, j])
                # print(f'\nStaff {i}, Shift {j}: x_ij = {constraint_value}, a_ij = {a[i, j]}, Constraint satisfied: {constraint_value <= a[i, j]}')
    else:
        print('\nNo solution found>')
        if status == cp_model.INFEASIBLE:
            print('\nProbleam is infeasible.')
        elif status == cp_model.MODEL_INVALID:
            print('\nModel is invalid.')
        elif status == cp_model.UNKNOWN:
            print('\nSolver status is unknown.')


def lab_assistant_scheduler():
    pass
