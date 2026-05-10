import csv

# ============================================================
# 1) Estrai l’ordine delle variabili dalla sezione COLUMNS
# ============================================================

var_order = []
seen = set()
in_columns = False

with open("flda.mps") as f:
    for line in f:
        s = line.strip()

        if s.startswith("COLUMNS"):
            in_columns = True
            continue

        if s.startswith(("RHS", "BOUNDS", "ENDATA")):
            in_columns = False

        if not in_columns or "'MARKER'" in line:
            continue

        parts = s.split()
        if parts and parts[0] not in seen:
            var_order.append(parts[0])
            seen.add(parts[0])


# ============================================================
# 2) Leggi l’aux file e identifica TUTTE le variabili LL
# ============================================================

ll_vars = set()

with open("aux_file.txt") as f:
    for line in f:
        line = line.strip()
        if line.startswith("LLVARS"):
            parts = line.split()
            if len(parts) >= 2:
                ll_vars.add(parts[1])


# ============================================================
# 3) Leggi i bounds reali dall’MPS (versione robusta)
# ============================================================

bounds = {}  # varname → [LB, UB]

in_bounds = False

with open("flda.mps") as f:
    for line in f:
        s = line.strip()

        if s.startswith("BOUNDS"):
            in_bounds = True
            continue
        if s.startswith("ENDATA"):
            in_bounds = False

        if not in_bounds:
            continue

        parts = s.split()
        if len(parts) < 3:
            continue

        btype = parts[0]
        varname = parts[2]

        # Inizializza se non esiste
        if varname not in bounds:
            bounds[varname] = [None, None]  # LB, UB

        # Tipi con valore numerico
        if btype in ("LO", "UP", "FX"):
            try:
                val = float(parts[-1])
            except:
                continue

            if btype == "LO":
                bounds[varname][0] = val
            elif btype == "UP":
                bounds[varname][1] = val
            elif btype == "FX":
                bounds[varname][0] = val
                bounds[varname][1] = val

        # Tipi senza valore numerico
        elif btype == "FR":  # free
            bounds[varname][0] = float("-inf")
            bounds[varname][1] = float("inf")

        elif btype == "MI":  # -infinity
            bounds[varname][0] = float("-inf")

        elif btype == "PL":  # +infinity
            bounds[varname][1] = float("inf")


# ============================================================
# 4) Estrai indici e valori dal log MibS
# ============================================================

indices = []
values = []

with open("mibs_output.txt") as f:
    for line in f:
        line = line.strip()

        if "y[" not in line:
            continue

        try:
            start = line.index("y[") + 2
            end = line.index("]", start)
            idx = int(line[start:end])
        except:
            continue

        if "=" in line:
            val_str = line.split("=")[1].strip()
            try:
                val = float(val_str)
            except:
                continue
        else:
            continue

        indices.append(idx)
        values.append(val)


# ============================================================
# 5) Mappa indice → nome variabile → valore
# ============================================================

mapped = []

for idx, val in zip(indices, values):
    real_idx = idx - 1  # MibS usa indici 1-based
    if 0 <= real_idx < len(var_order):
        mapped.append((idx, var_order[real_idx], val))
    else:
        mapped.append((idx, "**OUT_OF_RANGE**", val))


# ============================================================
# 6) Controlla violazioni bounds per TUTTE le LL
# ============================================================

violations = []
spurie = []

for idx, name, val in mapped:

    # Se non è LL → variabile spurie
    if name not in ll_vars:
        spurie.append((idx, name, val))
        continue

    LB, UB = bounds.get(name, (None, None))

    if LB is not None and val < LB - 1e-9:
        violations.append((idx, name, val, LB, UB))

    if UB is not None and val > UB + 1e-9:
        violations.append((idx, name, val, LB, UB))


# ============================================================
# 7) Estrai valore funzione obiettivo da MibS
# ============================================================

objective_value = None

with open("mibs_output.txt") as f:
    for line in f:
        line = line.strip()
        if "Cost" in line and "=" in line:
            try:
                objective_value = float(line.split("=")[1].strip())
            except:
                pass


# ============================================================
# 8) Salva risultati
# ============================================================

with open("ll_vars_list.txt", "w") as f:
    f.write("=== LISTA COMPLETA VARIABILI LL ===\n\n")
    for v in sorted(ll_vars):
        f.write(v + "\n")

with open("ll_violations.txt", "w") as f:
    f.write("=== VARIABILI LL CHE VIOLANO I BOUNDS ===\n\n")
    if not violations:
        f.write("Nessuna violazione trovata.\n")
    else:
        for idx, name, val, LB, UB in violations:
            f.write(f"{idx:4d}  {name:25s}  val={val}  LB={LB}  UB={UB}\n")

with open("spurie_vars.txt", "w") as f:
    f.write("=== VARIABILI SPURIE (NON LL) CHE MIBS STAMPA ===\n\n")
    for idx, name, val in spurie:
        f.write(f"{idx:4d}  {name:25s}  {val}\n")

with open("objective_value.txt", "w") as f:
    f.write("=== VALORE FUNZIONE OBIETTIVO MIBS ===\n\n")
    if objective_value is None:
        f.write("Non trovato nel log.\n")
    else:
        f.write(f"Objective = {objective_value}\n")


print("Creati file: ll_vars_list.txt, ll_violations.txt, spurie_vars.txt, objective_value.txt")
