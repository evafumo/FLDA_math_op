# FLDA–MIBS Pipeline

## 🧩 Introduzione

Questo repository contiene una pipeline completa per la risoluzione automatica di un modello di **Facility Location con Domanda Assegnata (FLDA)** formulato come **bilevel mixed‑integer problem** e risolto tramite:

- **Gurobi** (per il modello di livello superiore e inferiore)
- **MibS** (per la decomposizione bilevel), (https://github.com/coin-or/MibS)
- parsing automatico dei dati da file Excel
- generazione automatica dei file:
  - `params.json`
  - `flda.mps`
  - `aux_file.txt`
  - risultati finali `.txt` e `.csv`

L’intero processo è orchestrato da un unico script:

 **`main_flda.py`**
---

## 🚀 Funzionalità principali

- Parsing automatico di **tutti i file Excel** del tipo `N.xlsx`
- Generazione dei file `params_*.json` per ogni scenario
- Costruzione del modello FLDA in formato **MPS**
- Generazione del file **AUX** richiesto da MibS
- Esecuzione automatica di **MibS**
- Risoluzione del modello con **Gurobi**
- Creazione di una **cartella separata per ogni scenario**
- Salvataggio ordinato di:
  - MPS
  - AUX
  - output MibS
  - risultati Gurobi (TXT + CSV)
  - params originali

-------------------------------------------------------

⚙️ Come usare la pipeline
1 Avviare l’orchestratore:

    python main_flda.py

2️ Scegliere la modalità
Modalità 1 — Automatica

    legge tutti i file N.xlsx

    legge tutti gli sheet

    genera tutti i params

    esegue MPS → AUX → MibS → Solve per ogni scenario

Modalità 2 — Manuale

    usa solo i params_*.json già presenti nella cartella

-------------------------------------------------------------
Parsing Excel -> params

Il parser estrae:

- set I, J, K

- matrici Q, Ccap, c, p_price

- vettore R

- penalty

genera file del tipo "params_3_sheet1.json"

params -> MPS

    generate_mps.py costruisce il modello Gurobi e salva: "flda.mps"

MPS -> AUX

    generate_aux.py analizza l’MPS e genera: "aux_file.txt"

MPS + AUX -> MibS

Il main esegue automaticamente: mibs -Alps_instance flda.mps -MibS_auxiliaryInfoFile aux_file.txt

Solve finale

solve_flda_mibs.py risolve il modello e salva:

    risultati_flda.txt

    risultati_flda.csv


