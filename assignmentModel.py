from gurobipy import Model, GRB, quicksum



def solve_fractional_assignment_with_urgency(setI, setJ, setU, setIJ, Hi, d_ju):
    """
    Parameters:
    - setI: list of HRC types
    - setJ: list of orders
    - setU: list of urgency levels (e.g., [1, 2, 3])
    - setIJ: list of compatible (i,j) pairs
    - Hi: dict of available tons for each HRC i
    - d_ju: dict of demands for (j,u) keys → d_ju[(j,u)]
    """

    model = Model("Fractional_Assignment_MultiUrgency")

    # Variables
    x_iju = model.addVars(setIJ, setU, name="x_iju", lb=0.0)
    y_ju = model.addVars(setJ, setU, vtype=GRB.BINARY, name="y_ju")

    # Multi-objective: for each urgency level u, minimize sum of y_ju
    for priority, u in enumerate(sorted(setU), start=1):
        expr = quicksum(y_ju[j, u] for j in setJ)
        model.setObjectiveN(expr, index=u, priority=len(setU) - priority + 1, name=f"Urgency_{u}")

    # Constraint 1: Order fulfillment
    for j in setJ:
        for u in setU:
            assigned = quicksum(x_iju[i, j, u] for i in setI if (i, j) in setIJ)
            model.addConstr(assigned + y_ju[j, u] * d_ju[j, u] == d_ju[j, u], name=f"fulfill_{j}_{u}")

    # Constraint 2: HRC capacity
    for i in setI:
        total_usage = quicksum(x_iju[i, j, u] for j in setJ for u in setU if (i, j) in setIJ)
        model.addConstr(total_usage <= Hi[i], name=f"capacity_{i}")

    # Solve model
    model.optimize()

    # Return solution
    if model.status == GRB.OPTIMAL:
        solution = {
            'x_iju': {(i, j, u): x_iju[i, j, u].X for i in setI for j in setJ for u in setU if (i, j) in setIJ and x_iju[i, j, u].X > 1e-6},
            'y_ju': {(j, u): int(y_ju[j, u].X) for j in setJ for u in setU}
        }
        return solution
    else:
        return None
