# solve_flda_mibs.py
import json
import csv
from gurobipy import Model, GRB, quicksum

# ---------- Lettura parametri ----------
with open("params.json") as f:
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

# ---------- Obiettivo (21) e suoi tre termini ----------
# Termine 1: sum_i T_i
term_T = quicksum(T[i] for i in I)

# Termine 2: sum_{i,j,k,w} c_ij * Q_jk * z_ijkw
term_c = quicksum(
    c[f"{i},{j}"] * Q[f"{j},{k}"] * z[i, j, k, w]
    for i in I for j in J for k in K for w in K
)

# Termine 3: penalty * sum_{i,j,k!=w} Q_jk * z_ijkw
term_penalty = quicksum(
    penalty * Q[f"{j},{k}"] * z[i, j, k, w]
    for i in I for j in J for k in K for w in K
    if k != w
)

obj = term_T + term_c + term_penalty
m.setObjective(obj, GRB.MINIMIZE)

# ---------- Vincoli upper-level ----------
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

for j in J:
    m.addConstr(
        quicksum(Ccap[f"{i},{w}"] * y[i, j] for i in I for w in K)
        >= quicksum(Q[f"{j},{k}"] for k in K),
        name=f"capacity_cover_{j}"
    )

# ---------- Vincoli lower-level ----------
for j in J:
    for k in K:
        expr = quicksum(z[i, j, k, w] for i in I for w in K)
        m.addConstr(expr <= 1, name=f"ll_assign_le_{j}_{k}")
        m.addConstr(expr >= 1, name=f"ll_assign_ge_{j}_{k}")

for i in I:
    for j in J:
        for w in K:
            m.addConstr(
                quicksum(Q[f"{j},{k}"] * z[i, j, k, w] for k in K)
                <= Ccap[f"{i},{w}"] * y[i, j],
                name=f"ll_cap_{i}_{j}_{w}"
            )

for j in J:
    for k in K:
        m.addConstr(
            quicksum(z[i, j, k, w] for i in I for w in K if w != k) <= r[j, k],
            name=f"v24_{j}_{k}"
        )

for j in J:
    for w in K:
        m.addConstr(
            quicksum(B[i, j, w] for i in I)
            <= quicksum(Ccap[f"{i},{w}"] * (1 - r[j, w]) for i in I),
            name=f"v25_{j}_{w}"
        )

for i in I:
    for j in J:
        for w in K:
            m.addConstr(
                Ccap[f"{i},{w}"] * y[i, j]
                - quicksum(Q[f"{j},{k}"] * z[i, j, k, w] for k in K)
                <= B[i, j, w],
                name=f"v26_{i}_{j}_{w}"
            )

for j in J:
    for k in K:
        for w in K:
            if k != w:
                m.addConstr(
                    u[j, k] - u[j, w] <= (1 - vvar[j, k, w]) * M - 1,
                    name=f"v27_{j}_{k}_{w}"
                )

for j in J:
    for k in K:
        for w in K:
            if k != w:
                m.addConstr(
                    quicksum(z[i, j, k, w] for i in I) <= vvar[j, k, w],
                    name=f"v28_{j}_{k}_{w}"
                )

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

# ---------- Risoluzione ----------
m.optimize()

if m.status == GRB.OPTIMAL:
    # Valori numerici dei tre termini e dell'obiettivo totale
    val_T = term_T.getValue()
    val_c = term_c.getValue()
    val_penalty = term_penalty.getValue()
    obj_tot = m.objVal

    # Variabili x e y non nulle
    eps = 1e-6
    x_nonzero = [(i, x[i].X) for i in I if x[i].X > eps]
    y_nonzero = [((i, j), y[i, j].X) for i in I for j in J if y[i, j].X > eps]

    # ---------- Salvataggio TXT ----------
    with open("risultati_flda.txt", "w") as ftxt:
        ftxt.write("Risultati FLDA_MIBS\n")
        ftxt.write(f"Obiettivo totale: {obj_tot}\n")
        ftxt.write(f"Termine T (sum_i T_i): {val_T}\n")
        ftxt.write(f"Termine c*Q*z: {val_c}\n")
        ftxt.write(f"Termine penalty*Q*z: {val_penalty}\n\n")

        ftxt.write("x_i > 0:\n")
        for i, val in x_nonzero:
            ftxt.write(f"  x_{i} = {val}\n")

        ftxt.write("\ny_ij > 0:\n")
        for (i, j), val in y_nonzero:
            ftxt.write(f"  y_{i}_{j} = {val}\n")

    # ---------- Salvataggio CSV (solo riepilogo costi + x,y) ----------
    with open("risultati_flda.csv", "w", newline="") as fcsv:
        writer = csv.writer(fcsv)

        # Riga riepilogo costi
        writer.writerow(["metric", "value"])
        writer.writerow(["objective_total", obj_tot])
        writer.writerow(["term_T", val_T])
        writer.writerow(["term_cQz", val_c])
        writer.writerow(["term_penaltyQz", val_penalty])

        # Riga vuota
        writer.writerow([])
        writer.writerow(["variable_type", "i", "j", "value"])

        # x
        for i, val in x_nonzero:
            writer.writerow(["x", i, "", val])

        # y
        for (i, j), val in y_nonzero:
            writer.writerow(["y", i, j, val])

    print("Soluzione ottima trovata.")
    print(f"Obiettivo totale: {obj_tot}")
    print(f"Termine T: {val_T}, termine c*Q*z: {val_c}, termine penalty*Q*z: {val_penalty}")
    print("Risultati salvati in risultati_flda.txt e risultati_flda.csv")
else:
    print(f"Modello non ottimale, status = {m.status}")
