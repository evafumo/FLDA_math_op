# build_flda_mibs.py
import json
from gurobipy import Model, GRB, quicksum

with open("params_1_sheet0.json") as f:
    P = json.load(f)

I = P["I"]
J = P["J"]
K = P["K"]

c       = P["c"]
Q       = P["Q"]
Ccap    = P["Ccap"]
R       = P["R"]
p_price = P["p_price"]
penalty = P["penalty"]

M = len(K)

m = Model("FLDA_MIBS")

# ---------- Variabili upper-level ----------
x     = m.addVars(I, vtype=GRB.BINARY, name="x")
y     = m.addVars(I, J, vtype=GRB.BINARY, name="y")

# ---------- Variabili lower-level ----------
z     = m.addVars(I, J, K, K, lb=0.0, ub=1.0, name="z")
B     = m.addVars(I, J, K, lb=0.0, name="B")
r     = m.addVars(J, K, vtype=GRB.BINARY, name="r")
u     = m.addVars(J, K, vtype=GRB.CONTINUOUS, lb=0.0, name="u")
vvar  = m.addVars(J, K, K, vtype=GRB.BINARY, name="v")
delta = m.addVars(I, vtype=GRB.BINARY, name="delta")
T     = m.addVars(I, lb=0.0, name="T")

# ---------- Rinomina variabili (MibS-safe) ----------
for i in I:
    x[i].VarName = f"x_{i}"
    for j in J:
        y[i, j].VarName = f"y_{i}_{j}"

for i in I:
    for j in J:
        for w in K:
            B[i, j, w].VarName = f"B_{i}_{j}_{w}"
            for k in K:
                z[i, j, k, w].VarName = f"z_{i}_{j}_{k}_{w}"

for j in J:
    for k in K:
        r[j, k].VarName = f"r_{j}_{k}"
        u[j, k].VarName = f"u_{j}_{k}"
        for w in K:
            vvar[j, k, w].VarName = f"v_{j}_{k}_{w}"

for i in I:
    delta[i].VarName = f"delta_{i}"
    T[i].VarName     = f"T_{i}"

# ---------- Obiettivo (21) ----------
obj = quicksum(T[i] for i in I)

for i in I:
    for j in J:
        for k in K:
            for w in K:
                obj += c[f"{i},{j}"] * Q[f"{j},{k}"] * z[i, j, k, w]
                if k != w:
                    obj += penalty * Q[f"{j},{k}"] * z[i, j, k, w]

m.setObjective(-obj, GRB.MINIMIZE)

# ---------- Vincoli upper-level ----------
# (3) sum_j y_ij == x_i  → spezzato in <= e >=
for i in I:
    m.addConstr(
        quicksum(y[i, j] for j in J) <= x[i],
        name=f"alloc_eq_le_{i}"
    )
    m.addConstr(
        quicksum(y[i, j] for j in J) >= x[i],
        name=f"alloc_eq_ge_{i}"
    )
    for j in J:
        m.addConstr(y[i, j] <= x[i], name=f"alloc_only_if_open_{i}_{j}")

# (4) come prima
for j in J:
    m.addConstr(
        quicksum(Ccap[f"{i},{w}"] * y[i, j] for i in I for w in K)
        >= quicksum(Q[f"{j},{k}"] for k in K),
        name=f"capacity_cover_{j}"
    )

# ---------- Vincoli lower-level ----------
# (5) sum_{i,w} z^{kw}_{ij} == 1  → spezzato
for j in J:
    for k in K:
        expr = quicksum(z[i, j, k, w] for i in I for w in K)
        m.addConstr(expr <= 1, name=f"ll_assign_le_{j}_{k}")
        m.addConstr(expr >= 1, name=f"ll_assign_ge_{j}_{k}")

# (6)
for i in I:
    for j in J:
        for w in K:
            m.addConstr(
                quicksum(Q[f"{j},{k}"] * z[i, j, k, w] for k in K)
                <= Ccap[f"{i},{w}"] * y[i, j],
                name=f"ll_cap_{i}_{j}_{w}"
            )

# (24)
for j in J:
    for k in K:
        m.addConstr(
            quicksum(z[i, j, k, w] for i in I for w in K if w != k) <= r[j, k],
            name=f"v24_{j}_{k}"
        )

# (25)
for j in J:
    for w in K:
        m.addConstr(
            quicksum(B[i, j, w] for i in I)
            <= quicksum(Ccap[f"{i},{w}"] * (1 - r[j, w]) for i in I),
            name=f"v25_{j}_{w}"
        )

# (26)
for i in I:
    for j in J:
        for w in K:
            m.addConstr(
                Ccap[f"{i},{w}"] * y[i, j]
                - quicksum(Q[f"{j},{k}"] * z[i, j, k, w] for k in K)
                <= B[i, j, w],
                name=f"v26_{i}_{j}_{w}"
            )

# (27)
for j in J:
    for k in K:
        for w in K:
            if k != w:
                m.addConstr(
                    u[j, k] - u[j, w] <= (1 - vvar[j, k, w]) * M - 1,
                    name=f"v27_{j}_{k}_{w}"
                )

# (28)
for j in J:
    for k in K:
        for w in K:
            if k != w:
                m.addConstr(
                    quicksum(z[i, j, k, w] for i in I) <= vvar[j, k, w],
                    name=f"v28_{j}_{k}_{w}"
                )

# (29)-(32)
for i in I:
    rev = quicksum(
        p_price[f"{i},{w}"] * Q[f"{j},{k}"] * z[i, j, k, w]
        for j in J for k in K for w in K
    )
    coeff_delta = (
        sum(Ccap[f"{i},{w}"] * p_price[f"{i},{w}"] for w in K) - R[str(i)]
    )
    m.addConstr(
        T[i] <= R[str(i)] - rev + coeff_delta * delta[i],
        name=f"v29_{i}"
    )
    m.addConstr(
        T[i] >= R[str(i)] * x[i] - rev,
        name=f"v30_{i}"
    )
    m.addConstr(T[i] <= R[str(i)] * x[i], name=f"v31_{i}")
    m.addConstr(T[i] <= R[str(i)] * (1 - delta[i]), name=f"v32_{i}")

m.update()
m.write("flda.mps")
print("Scritto flda.mps (per MibS)")
