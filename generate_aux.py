# build_aux_mibs.py
mps_file = "flda.mps"
aux_file = "aux_file.txt"

LL_VAR_PREFIXES = ["z_", "B_", "r_", "u_", "v_", "delta_", "T_"]

LL_CONSTR_PREFIXES = [
    "ll_assign_le_",
    "ll_assign_ge_",
    "ll_cap_",
    "v24_",
    "v25_",
    "v26_",
    "v27_",
    "v28_",
    "v29_",
    "v30_",
    "v31_",
    "v32_",
]

with open(mps_file, "r") as f:
    lines = f.readlines()

# --- ordine variabili (COLUMNS) ---
var_order = []
seen_vars = set()
in_columns = False
for line in lines:
    s = line.strip()
    if s.startswith("COLUMNS"):
        in_columns = True
        continue
    if s.startswith("RHS") or s.startswith("BOUNDS") or s.startswith("ENDATA"):
        in_columns = False
    if not in_columns or "'MARKER'" in line:
        continue
    parts = s.split()
    if parts and parts[0] not in seen_vars:
        var_order.append(parts[0])
        seen_vars.add(parts[0])

# --- ordine vincoli (ROWS, escludendo N) ---
con_order = []
in_rows = False
for line in lines:
    s = line.strip()
    if s.startswith("ROWS"):
        in_rows = True
        continue
    if s.startswith("COLUMNS"):
        in_rows = False
    if not in_rows:
        continue
    parts = s.split()
    if len(parts) == 2:
        rtype, cname = parts
        if rtype != "N":
            con_order.append(cname)

ll_var_indices = [
    i for i, v in enumerate(var_order)
    if any(v.startswith(p) for p in LL_VAR_PREFIXES)
]
ll_con_indices = [
    i for i, c in enumerate(con_order)
    if any(c.startswith(p) for p in LL_CONSTR_PREFIXES)
]

with open(aux_file, "w", newline="\n") as f:
    f.write(f"N {len(ll_var_indices)}\n")
    f.write(f"M {len(ll_con_indices)}\n")
    for i in ll_var_indices:
        f.write(f"LC {i}\n")
    for i in ll_con_indices:
        f.write(f"LR {i}\n")
    for _ in ll_var_indices:
        f.write("LO 0\n")
    # lower-level è un max → OS 1
    f.write("OS 1\n")

print(f"Scritto {aux_file}")
print(f"  Variabili lower-level  : {len(ll_var_indices)}")
print(f"  Vincoli  lower-level   : {len(ll_con_indices)}")
print()
print("Avvia MibS con:")
print(f"  mibs -Alps_instance {mps_file} -MibS_auxiliaryInfoFile {aux_file}")
