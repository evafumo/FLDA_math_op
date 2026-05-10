# main_flda.py
# Pipeline completa: parser → MPS → AUX → MibS → Solve
# Crea una cartella per ogni scenario

import os
import glob
import shutil
import subprocess
import pandas as pd
import json
import re

# ============================================================
# FUNZIONI PARSER (copiate dal tuo parser_flda.py)
# ============================================================

LABELS = ["DAMEND", "CAPACITY", "COST", "PRICE", "REVENUE"]

def find_label_positions(df, labels):
    positions = {}
    for r in range(df.shape[0]):
        for c in range(df.shape[1]):
            cell = str(df.iloc[r, c]).strip().upper()
            if cell in labels and cell not in positions:
                positions[cell] = (r, c)
    return positions

def extract_table(df, label, start_pos):
    row_label, col_label = start_pos[label]
    row_start = row_label + 1
    col_start = col_label + 1

    next_cols = [pos[1] for lab, pos in start_pos.items() if pos[1] > col_label]
    col_end = min(next_cols) if next_cols else df.shape[1]

    row_end = row_start
    while row_end < df.shape[0] and df.iloc[row_end, col_label] != "":
        row_end += 1

    table = df.iloc[row_start:row_end, col_start:col_end]
    table = table.apply(pd.to_numeric, errors='coerce').fillna(0)
    table = table.loc[:, (table != 0).any(axis=0)]
    table.columns = range(table.shape[1])
    return table, (row_start, row_end, col_start, col_end)

def extract_penalty(df, shape_CAPACITY, start_pos):
    row_start, row_end, col_start, col_end = shape_CAPACITY
    _, col_label = start_pos["CAPACITY"]
    penalty_row = row_end + 2
    raw_value = df.iloc[penalty_row, col_label]
    return float(raw_value)

def parse_excel_file(df):
    df = df.fillna("")
    start_pos = find_label_positions(df, LABELS)

    DEMAND, shape_DEMAND = extract_table(df, "DAMEND", start_pos)
    CAPACITY, shape_CAPACITY = extract_table(df, "CAPACITY", start_pos)
    COST, shape_COST = extract_table(df, "COST", start_pos)
    PRICE, shape_PRICE = extract_table(df, "PRICE", start_pos)
    REVENUE, shape_REVENUE = extract_table(df, "REVENUE", start_pos)

    penalty = extract_penalty(df, shape_CAPACITY, start_pos)

    num_hotels = CAPACITY.shape[0]
    num_hubs = DEMAND.shape[0]
    num_types = DEMAND.shape[1]

    I = list(range(1, num_hotels + 1))
    J = list(range(1, num_hubs + 1))
    K = list(range(1, num_types + 1))

    Q = {f"{j},{k}": int(DEMAND.iloc[j-1, k-1]) for j in J for k in K}
    Ccap = {f"{i},{w}": int(CAPACITY.iloc[i-1, w-1]) for i in I for w in K}
    c = {f"{i},{j}": float(COST.iloc[i-1, j-1]) for i in I for j in J}
    p_price = {f"{i},{w}": float(PRICE.iloc[i-1, w-1]) for i in I for w in K}
    R = {f"{i}": float(REVENUE.iloc[i-1, 0]) for i in I}

    return {
        "I": I,
        "J": J,
        "K": K,
        "c": c,
        "Q": Q,
        "Ccap": Ccap,
        "R": R,
        "p_price": p_price,
        "penalty": penalty
    }

# ============================================================
# GENERA PARAMS AUTOMATICAMENTE PER TUTTI I FILE E SHEET
# ============================================================

def run_parser_automatic():
    print("\n=== PARSER AUTOMATICO ===")

    files = glob.glob("*.xlsx")
    numeric_files = []

    for f in files:
        m = re.match(r"(\d+)\.xlsx$", f)
        if m:
            numeric_files.append((int(m.group(1)), f))

    numeric_files.sort()

    for num, excel_file in numeric_files:
        xls = pd.ExcelFile(excel_file)
        for sheet_index in range(len(xls.sheet_names)):
            df = pd.read_excel(excel_file, sheet_name=sheet_index, header=None)
            params = parse_excel_file(df)

            out_name = f"params_{num}_sheet{sheet_index}.json"
            with open(out_name, "w") as f:
                json.dump(params, f, indent=4)

            print(f"✔ Creato {out_name}")

    print("=== PARSER COMPLETATO ===\n")

# ============================================================
# ESECUZIONE COMPLETA PER OGNI PARAMS
# ============================================================

def run_flda_for_params(params_file):
    print(f"\n=== SCENARIO: {params_file} ===")
    base_name = os.path.splitext(params_file)[0]
    scenario_dir = f"scenario_{base_name}"
    os.makedirs(scenario_dir, exist_ok=True)

    shutil.copy(params_file, "params.json")
    shutil.copy(params_file, os.path.join(scenario_dir, params_file))

    # 1. MPS
    subprocess.call(["python", "generate_mps.py"])
    mps_name = f"flda_{base_name}.mps"
    shutil.move("flda.mps", os.path.join(scenario_dir, mps_name))

    # 2. AUX
    subprocess.call(["python", "generate_aux.py"])
    aux_name = f"aux_{base_name}.txt"
    shutil.move("aux_file.txt", os.path.join(scenario_dir, aux_name))

    # 3. MibS
    mibs_output = os.path.join(scenario_dir, f"mibs_output_{base_name}.txt")
    cmd = [
        "mibs",
        "-Alps_instance", os.path.join(scenario_dir, mps_name),
        "-MibS_auxiliaryInfoFile", os.path.join(scenario_dir, aux_name)
    ]
    with open(mibs_output, "w") as fout:
        subprocess.call(cmd, stdout=fout, stderr=fout)

    # 4. Solve FLDA
    subprocess.call(["python", "solve_flda.py"])
    shutil.move("risultati_flda.txt", os.path.join(scenario_dir, f"risultati_flda_{base_name}.txt"))
    shutil.move("risultati_flda.csv", os.path.join(scenario_dir, f"risultati_flda_{base_name}.csv"))

    print(f"✔ Scenario {params_file} completato.")

# ============================================================
# MAIN
# ============================================================

def main():
    print("Scegli modalità:")
    print("1 = Parser automatico + solve di tutti gli scenari")
    print("2 = Usa solo i params_*.json già presenti")

    mode = input("Modalità: ").strip()

    if mode == "1":
        run_parser_automatic()

    params_files = sorted(glob.glob("params_*.json"))
    if not params_files:
        print("Nessun params_*.json trovato.")
        return

    for p in params_files:
        run_flda_for_params(p)

    print("\n=== TUTTI GLI SCENARI COMPLETATI ===")

if __name__ == "__main__":
    main()
