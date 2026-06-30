# Supply Chain Optimization and Risk Simulation
**Automated MILP Routing and Stochastic Risk Simulation for Global Logistics**

An end-to-end supply chain simulation that minimizes logistics costs while dynamically adapting to real-time network disruptions. This project utilizes Multi-Period Mixed-Integer Linear Programming (MILP) to provide prescriptive analytics—automatically recalculating optimal shipping routes when faced with simulated real-world risks like port closures, capacity drops, or fuel price hikes.
> Live demo: **https://supply-chain-risk-optimization-engine.streamlit.app/**

**Dataset**
> Supply Chain Logistics Problem Dataset: **https://doi.org/10.17633/rd.brunel.7558679**
---
## What you can do
- **Simulate Logistical Disruptions**<br>
  Inject dynamic disruptions into the network to test resilience. Supported scenarios include:
  - Baseline Routing,
  - Fuel Crises (+25% freight cost),
  - Port Closures,
  - Plant Strikes (-80% manufacturing capacity).
  
- **Visualize Multi-Echelon Topology**<br>
  View the entire global routing network through a custom 3-Tier abstract node-link graph, where line opacity dynamically represents order volume and bottleneck facilities turn red under stress.
  
- **Drill-Down Facility Analytics**<br>
  Click directly on specific manufacturing plants or origin ports within the UI to instantly filter the raw data tables and isolate specific order routing metrics and KPIs.
  
- **Evaluate Global KPIs**<br>
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

The mathematical model of this project is a Multi-Period MILP model aiming to minimize transportation costs, manufacturing costs and fulfillment delay penalties. The model formulation is as follows:<br>

**Sets and Indices**
* $O$: Set of all orders in the system ($o \in O$)
* $P$: Set of all available manufacturing plants ($p \in P$)
* $W$: Set of all available origin shipping ports ($w \in W$)
* $C$: Set of all shipping carriers ($c \in C$)
* $D$: Set of all manufacturing days in the time horizon ($d \in D$)

**Parameters**
* $Demand(o)$: Unit quantity required to fulfill order $o$
* $Weight(o)$: Total shipping weight of order $o$
* $Dest(o)$: Final destination port of order $o$
* $WHCost(p)$: Processing cost per unit at manufacturing plant $p$
* $Cap(p, d)$: Maximum unit capacity that plant $p$ can process on day $d$
* $PortCap(w, d)$: Maximum unit throughput that origin port $w$ can handle on day $d$
* $SCost(w, c, o)$: Freight cost to ship order $o$ from origin port $w$ to $Dest(o)$ using carrier $c$
* $Penalty(d)$: Late fulfillment penalty incurred for processing an order on day $d$

> **Data Engineering Preprocessing Rule:** > If the Service Level of an order $SL(o) = \text{'CRF'}$, the freight cost is pre-filtered to zero ($SCost(w, c, o) = 0$) in the Pandas pipeline prior to matrix generation. This avoids passing complex conditional logic directly to the MILP solver.

**Decision Variable**

A binary variable determining the exact route and timeline for every order in the network.

$$X_{o,p,w,c,d} \in \{0, 1\}$$

$X_{o,p,w,c,d} = 1$ if order $o$ is processed at plant $p$, shipped from origin port $w$, using carrier $c$, on day $d$. Otherwise, $0$.

**Objective Function**

*Minimize Total Network Cost*: The objective minimizes the sum of Warehouse Processing Costs, Freight Costs, and Delay Penalties.

$$\text{Minimize } Z = \sum_{o \in O} \sum_{p \in P} \sum_{w \in W} \sum_{c \in C} \sum_{d \in D} \left( Demand(o) \cdot WHCost(p) + SCost(w, c, o) + Penalty(d) \right) \cdot X_{o,p,w,c,d}$$

**Constraints**

*1. Absolute Order Fulfillment*

Every order in the system must be assigned exactly one valid routing configuration (plant, port, carrier, and day).

$$\sum_{p \in P} \sum_{w \in W} \sum_{c \in C} \sum_{d \in D} X_{o,p,w,c,d} = 1 \quad \forall o \in O$$

*2. Dynamic Plant Capacity* 

The total units assigned to a specific plant on a specific day cannot exceed its operational limit for that day. 
*(Note: During a simulated capacity reduction, $Cap(p,d)$ drops by 80%, forcing the solver to shift $X$ to alternative plants or push fulfillment to later days $d$).*

$$\sum_{o \in O} \sum_{w \in W} \sum_{c \in C} Demand(o) \cdot X_{o,p,w,c,d} \le Cap(p, d) \quad \forall p \in P, \forall d \in D$$

*3. Dynamic Port Throughput*

The total units routed through a specific origin port on a specific day cannot exceed its maximum handling capacity. 
*(Note: During a simulated closure, $PortCap(w,d) = 0$, forcing the network to bypass that node entirely).*

$$\sum_{o \in O} \sum_{p \in P} \sum_{c \in C} Demand(o) \cdot X_{o,p,w,c,d} \le PortCap(w, d) \quad \forall w \in W, \forall d \in D$$

**4. Matrix Reduction & Preprocessing Constraints**

To minimize the dimensional complexity of the MILP model and improve solve times, several network constraints are enforced during the data preprocessing phase in `pyomo_solver.py`. By filtering the dataset before matrix instantiation, we eliminate invalid routing combinations (edges) from the solver's memory entirely:

* Product-Plant Eligibility: Orders are strictly filtered to only allow routing through manufacturing plants equipped to produce that specific product.
* Dedicated Fulfillment Allocation: High-priority or *Special* customers are hard-mapped to a restricted subset of dedicated plants.
* Network Topology Connectivity: Invalid Plant-to-Port shipping lanes are dropped; plants are only permitted to route through their explicitly connected origin ports.
* Carrier Weight Limits: If a carrier operates on a specific Lane ($W \rightarrow Dest$), the order is only permitted to use that carrier if its total physical weight of order falls within the carrier's allowable threshold.

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
