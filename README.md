# Supply Chain Optimization and Risk Simulation
**Automated MILP Routing and Stochastic Risk Simulation for Global Logistics**
An end-to-end supply chain simulation that minimizes logistics costs while dynamically adapting to real-time network disruptions. This project utilizes Multi-Period Mixed-Integer Linear Programming (MILP) to provide prescriptive analytics—automatically recalculating optimal shipping routes when faced with simulated real-world risks like port closures, capacity drops, or fuel price hikes.
> Live demo: **https://supply-chain-risk-optimization-engine.streamlit.app/**
---
## What you can do
- **Simulate Logistical Disruptions**
  Inject dynamic disruptions into the network to test resilience. Supported scenarios include 🟢 Baseline Routing, 🔴 Fuel Crises (+25% freight cost), 🟠 Port Closures, and 🟣 Plant Strikes (-80% manufacturing capacity).
- **Visualize Multi-Echelon Topology**
  View the entire global routing network through a custom 3-Tier abstract node-link graph, where line opacity dynamically represents order volume and bottleneck facilities turn red under stress.
- **Drill-Down Facility Analytics**
  Click directly on specific manufacturing plants or origin ports within the UI to instantly filter the raw data tables and isolate specific order routing metrics and KPIs.
- **Evaluate Global KPIs**
  Track the ripple effects of localized risks on macro metrics, including Total Global Cost, Orders Routed, Average Cost per Order, and Maximum Days to Fulfill.
---
## High‑level architecture
**Offline pipeline (The Engine)**
1. **ETL & Data Modeling** (`src/database_builder.py`)
   - Converts an excel file with multiple sheets to individual SQLite tables.
   - Extracts raw multi-table logistics data from SQLite.
   - Cleans and structures data into mathematical sets and parameters.
2. **MILP Optimization** (`src/pyomo_solver.py`)
   - Builds a Multi-Period Mixed-Integer Linear Programming matrix.
   - Solves for the optimal order routing using the CPLEX solver while respecting strict factory capacities and port throughput constraints.
3. **Risk Simulation** (`src/risk_simulator.py`, `src/main.py`)
   - Iterates through predefined disaster scenarios, recalculating the optimal routing paths and exporting the final dataframes to static CSVs.
**Online app (The Control Tower)**
4. **Decoupled Visualization** (`src/dashboard.py`)
   - A lightweight Streamlit app that reads the pre-computed CSVs from the offline pipeline.
   - Requires zero heavy computation on the cloud server, ensuring lightning-fast load times and interaction rendering via Plotly.
---
## Tech stack
| Component       | Tooling |
| ------------- | ------- |
| UI            | Streamlit, Plotly Graph Objects |
| Optimization  | Python, Pyomo, IBM ILOG CPLEX |
| Data Eng      | SQLite, Pandas |
| Versioning    | Git, GitHub |
| Deployment    | Streamlit Community Cloud |
---
## Getting started (local)
### Prerequisites
- Python **3.10+**
- **IBM ILOG CPLEX Optimization Studio** (or the CPLEX Python API) installed and added to your system path. Instead of CPLEX, any other optimization software compatible with pyomo can be used. Make sure to update the system path in the `pyomo_solver.py` file. *This is strictly required for the Pyomo solver to function.*
### 1. Clone the repo
```bash
git clone https://github.com/yourusername/supply-chain-risk-optimization-engine.git
cd supply-chain-risk-optimization-engine
```

### 2. Create and activate a virtual environment
```bash
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Unix/macOS:
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

---

## Data preparation & simulation building

The offline pipeline generates the data required for the dashboard. Before launching the UI, you must run the optimization engine to generate the scenario files.

### Step 1 – Run the MILP Orchestrator

Execute the main script from your root directory:
```bash
python src/main.py
```

This will:

* Connect to `data/network.sqlite`.
* Run the `pyomo_solver.py` for the Baseline perfect-world scenario.
* Sequentially trigger the `risk_simulator.py` to calculate routing under Port Closures, Plant Strikes, and Fuel Crises.
* Export all optimized routing tables as `*_Network.csv` files to the `results/` folder.

> **Note:** Without these CSVs in the `results/` folder, the Streamlit dashboard will throw a file-not-found error.

---

## Running the Streamlit app

Once the optimization scenarios are solved and available under `results/`:
```bash
streamlit run src/dashboard.py
```
Open the URL printed in the terminal (typically `http://localhost:8501`) to use the interactive control tower.

---

## Using the app

### Sidebar controls

* **Network Controls:** A radio toggle that acts as the primary environment switcher. Changing this from "Baseline" to any other scenario to instantly swap the active dataset being fed into the visualizations.

---

## The Operations Research Architecture

The mathematical backbone of this project is a Multi-Period MILP model aiming to minimize transportation costs, manufacturing co and fulfillment delay penalties.

**Objective Function:**

$$\text{Minimize } Z = \sum_{l \in L} \sum_{d \in D} \left( C_{l} + P_{d} \right) \cdot X_{l,d}$$

Where $X_{l,d}$ is the binary decision variable for routing an order on a specific lane and day.

---

## Project structure

```plaintext
supply-chain-risk-optimization-engine/
├── src/                     # Core Python package
│   ├── __init__.py
│   ├── dashboard.py         # Streamlit UI entrypoint
│   ├── database_builder.py  # SQLite generation script
│   ├── main.py              # CLI orchestrator
│   ├── pyomo_solver.py      # MILP matrix formulation and CPLEX integration
│   └── risk_simulator.py    # Chaos injection parameters
├── results/                 # Auto-generated CSVs (tracked for deployment)
│   ├── Baseline_Network.csv
│   ├── Fuel_Crisis_Network.csv
│   ├── PLANT03_Capacity_Reduction_Network.csv
│   └── PORT02_Closure_Network.csv
├── data/                    # Raw inputs
│   ├── network.sqlite
│   └── supply_chain_database.xlsx
├── requirements.txt         # Package dependencies
└── README.md                # Project documentation
```

---

## Author

* **Gokul S B** 

---

## License

This project is licensed under the **MIT License**.