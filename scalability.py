import pandas as pd

# 1. Lettura file
mibs_raw = pd.read_csv("mibs_final_result.csv")
ils_raw  = pd.read_csv("scalability_results.csv")

# 2. Selezione colonne MiBs realmente usate
mibs = mibs_raw[[
    "instance",
    "cpu_time_s",
    "open_hotels",
    "best_obj"
]].rename(columns={
    "open_hotels": "open_hotels_mibs",
    "best_obj": "best_obj_mibs"
})

# 3. Selezione colonne ILS realmente usate
ils = ils_raw[[
    "instance",
    "ils_time_s",
    "delta_pct",
    "open_hotels",
    "best_obj",
    "ll_vars"
]].rename(columns={
    "open_hotels": "open_hotels_ils",
    "best_obj": "best_obj_ils",
    "ll_vars": "ll_vars_ils"
})

# 4. Colonna derivata ratio_cpu
ils["ratio_cpu"] = ils["ils_time_s"] / mibs["cpu_time_s"].values

# 5. Merge finale
merged = ils.merge(mibs, on="instance")

# 6. Salvataggio CSV finale
merged.to_csv("merged_ils_mibs.csv", index=False)

print(" File minimale salvato come merged_ils_mibs_minimal.csv")
