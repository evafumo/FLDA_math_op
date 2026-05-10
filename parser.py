
import pandas as pd
import json
import glob
import re
import os

# ============================================================
# FUNZIONI ESTRAZIONE TABELLE
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

    penalty_row = row_end + 1
    if penalty_row >= df.shape[0]:
        raise ValueError("Penalty non trovato: file troppo corto.")

    raw_value = df.iloc[penalty_row, col_label]

    try:
        return float(raw_value)
    except:
        raise ValueError(f"Penalty non numerico nella cella ({penalty_row}, {col_label}): {raw_value}")

# ============================================================
# PARSER GENERALE PER UN SINGOLO DF
# ============================================================

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

    params = {
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

    return params

# ============================================================
# MODALITÀ MANUALE
# ============================================================

def process_single_file(excel_file, sheet_index):
    print(f"\n=== Modalità manuale: {excel_file} (sheet {sheet_index}) ===")

    df = pd.read_excel(excel_file, sheet_name=sheet_index, header=None)
    params = parse_excel_file(df)

    out_name = f"params_{os.path.basename(excel_file)}_sheet{sheet_index}.json"
    with open(out_name, "w") as f:
        json.dump(params, f, indent=4)

    print(f"✔ Creato {out_name}")

# ============================================================
# MODALITÀ AUTOMATICA (MAIN)
# ============================================================

def process_all_files():
    print("\n=== Modalità automatica: parsing di tutti i file ===")

    files = glob.glob("*.xlsx")
    numeric_files = []

    for f in files:
        m = re.match(r"(\d+)\.xlsx$", f)
        if m:
            numeric_files.append((int(m.group(1)), f))

    if not numeric_files:
        print("Nessun file numerico trovato.")
        return

    numeric_files.sort()

    for num, excel_file in numeric_files:
        print(f"\n--- File {excel_file} ---")

        xls = pd.ExcelFile(excel_file)
        num_sheets = len(xls.sheet_names)

        for sheet_index in range(num_sheets):
            print(f"  → Sheet {sheet_index}")

            df = pd.read_excel(excel_file, sheet_name=sheet_index, header=None)
            params = parse_excel_file(df)

            out_name = f"params_{num}_sheet{sheet_index}.json"
            with open(out_name, "w") as f:
                json.dump(params, f, indent=4)

            print(f"     Creato {out_name}")

    print("\n=== COMPLETATO ===")

# ============================================================
# MAIN
# ============================================================

def main():
    print("Scegli modalità:")
    print("1 = Manuale (inserisci file + sheet)")
    print("2 = Automatica (tutti i file e tutti gli sheet)")

    mode = input("Modalità: ").strip()

    if mode == "1":
        excel_file = input("Nome file Excel (es. 3.xlsx): ").strip()
        sheet_index = int(input("Indice sheet (0 = primo): ").strip())
        process_single_file(excel_file, sheet_index)

    elif mode == "2":
        process_all_files()

    else:
        print("Modalità non valida.")

if __name__ == "__main__":
    main()
