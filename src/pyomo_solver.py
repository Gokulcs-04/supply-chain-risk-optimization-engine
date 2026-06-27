import os
import sqlite3
import pandas as pd
import pyomo.environ as pyo

# DATA EXTRACTION

def extract_network_data():
    """Extracts, filters, and prepares all required data for the solver from the database"""

    conn = sqlite3.connect('data/network.sqlite')

    # SETS
    '''
    O: Set of all orders
    P: Set of all plants (warehouses)
    W: Set of all origin ports
    C: Set of all carriers
    '''

    # Set of all orders
    orders_table = pd.read_sql_query('SELECT * FROM OrderListTable', conn)
    required_columns = ['Order ID', 'Customer', 'Product ID', 'Destination Port', 'Service Level', 'Unit quantity', 'Weight' ]
    required_df = orders_table[required_columns]
    grouped_orders = required_df.groupby(['Order ID', 'Customer', 'Product ID',
                                        'Destination Port', 'Service Level'])[['Unit quantity', 'Weight']].sum().reset_index()
    orders_list = grouped_orders['Order ID'].unique().tolist()

    # Set of all plants
    plants_table = pd.read_sql_query('SELECT * FROM WarehouseCapacityTable', conn)
    plant_list = plants_table['Plant ID'].unique().tolist()


    # VALID COMBINATIONS
    '''
    Plant_Product_Validity (Each plant can only manufacture specific product)
    Plant_Customer_Validity (Some plants are restricted to specific customers)
    Plant_Port_validity (Each plant is connected to a specific origin port(W))
    Carrier_Validity (Carriers that operate between W and Destination of Order and supports a specific weight)
    Plant_Capacities (Warehouse capacities where the order is considered instead of unit quantity)
    Plant_Costs (Costs associated with the plant / order)
    '''

    # Plant_Product_Combinations
    plant_product_df = pd.read_sql_query("SELECT * FROM ProductsPerPlantTable", conn)

    plant_product_combinations = {}
    for row in plant_product_df.itertuples(index = False):
        if row[0] not in plant_product_combinations:
            plant_product_combinations[row[0]] = []
            plant_product_combinations[row[0]].append(row[1])
        else:
            plant_product_combinations[row[0]].append(row[1])


    # Plant_Customer_Combinations
    plant_customer_df = pd.read_sql_query("SELECT * FROM VMICustomersTable", conn)

    plant_customer_combinations = plant_customer_df.groupby('Plant Code')['Customers'].apply(list).to_dict()

    # Plant_Port_Combinations
    plant_port_df = pd.read_sql_query("SELECT * FROM PlantPortsTable", conn)

    plant_port_combinations = plant_port_df.groupby('Plant Code')['Port'].apply(list).to_dict()

    # Carrier_Validity
    freight_rate_df = pd.read_sql_query("SELECT * FROM FreightRatesTable", conn)

    carrier_options = {}

    for row in freight_rate_df.itertuples(index=False):
        
        dict_values = {
            'carrier' : row.Carrier,
            'min_weight' : row.minm_wgh_qty,
            'max_weight' : row.max_wgh_qty,
            'rate' : row.rate,
            'min_cost' : row[6],
            'service_type': row.svc_cd
        }

        key = tuple([row.orig_port_cd, row.dest_port_cd])
        
        if key not in carrier_options.keys():
            carrier_options[key] = []
            carrier_options[key].append(dict_values)
        else:
            carrier_options[key].append(dict_values)


    # plant_capacity_combination
    wh_capacity_df = pd.read_sql_query("SELECT * FROM WarehouseCapacityTable", conn)

    plant_capacities = {}
    for row in wh_capacity_df.itertuples(index = False):
        curr_plant = row[0]
        curr_capacity = row[1]
        plant_capacities[curr_plant] = curr_capacity 


    # plant_costs_combination
    wh_costs_df = pd.read_sql_query("SELECT * FROM WarehouseCostTable", conn)

    plant_costs = {}
    for row in wh_costs_df.itertuples(index = False):
        cost_per_plant = row[1]
        plant_costs[row[0]] = cost_per_plant


    # MASTER FILTER LOOP to get a list of mathematically valid shipping lanes 
    # based on the constraints
    valid_lanes = []
    shipping_costs = {}

    for order in grouped_orders.itertuples(index=False):
        order_id = order[0]
        customer = order[1]
        product = order[2]
        dest_port = order[3]
        service_level = order[4]
        unit_qty = order[5]
        weight = order[6]

        # CHECK1: if product is manufactured by a plant and continue if no
        for plant in plant_list:
            if product not in plant_product_combinations.get(plant, []):
                continue

            # CHECK2: if a plant is assigned to a customer (VMICustomer) and customer not in the list
            if plant in plant_customer_combinations.keys() and customer not in plant_customer_combinations.get(plant, []):
                continue
            
            # CHECK3: Valid ports and route check
            valid_orig_ports = plant_port_combinations.get(plant, [])

            if not valid_orig_ports:
                continue

            for orig_port in valid_orig_ports:
                route_key = (orig_port, dest_port)

                # Check if this tuple exists in the carrier options dictionary
                if route_key not in carrier_options.keys():
                    continue
                    
                # CHECK4: if carrier_route exists and weight constraints are fulfilled
                carrier_route = carrier_options.get(route_key, [])
                if not carrier_route:
                    continue
                
                for carrier_data in carrier_route:
                    if weight < carrier_data["min_weight"] or weight > carrier_data["max_weight"]:
                        continue
                    
                    # CHECK5: if the service level is CRF(shipping handled by customer, cost is 0)
                    # and if the service type in this carrier option matches the order service level
                    if service_level != "CRF" and service_level != carrier_data['service_type']:
                        continue

                    if service_level == "CRF":
                        freight_cost = 0
                    else:
                        freight_cost = max(carrier_data['min_cost'], carrier_data['rate'] * weight)
                    
                    # Find the warehouse costs
                    wh_cost = unit_qty * plant_costs.get(plant, 0)

                    # Final Total Cost
                    final_total_cost = wh_cost + freight_cost


                    #Append the lanes to the valid lanes tuple
                    lane_tuple = (order_id, plant, orig_port, carrier_data["carrier"])
                    valid_lanes.append(lane_tuple)

                    # Shipping cost for the lane
                    shipping_costs[lane_tuple] = final_total_cost

    return valid_lanes, shipping_costs, plant_capacities, orders_list, plant_list, plant_port_combinations


# OPTIMIZATION FUNCTION

def run_optimization(valid_lanes, shipping_costs, plant_capacities, orders_list, plant_list,
                     required_days = 7, scenario_name = "Baseline"):
    """Runs the Pyomo MILP optimization and exports the results to CSV."""

    # PYOMO MODEL INITIALIZATION
    model = pyo.ConcreteModel(name = "SupplyChainNetwork")

    # SETS
    model.O = pyo.Set(initialize = orders_list, doc = 'Set of Orders')
    model.P = pyo.Set(initialize = plant_list, doc = 'Set of Origin Plants')
    # Create SET of mathematically valid lanes and SET of required days 
    model.ValidLanes = pyo.Set(initialize = valid_lanes, doc = "Set of mathematically valid shipping lanes")
    model.Days = pyo.Set(initialize = range(1, required_days + 1), doc = "Manufacturing Days")

    # Create DECISION VARIABLE "X"
    model.X = pyo.Var(model.ValidLanes, model.Days, domain = pyo.Binary, doc = "1 if lane is used on specific day, 0 otherwise")


    # OBJECTIVE FUNCTION

    # We try to satisfy all orders immediately, if the plant capacity does not allow it,
    # we add a penalty of $100 per day to backlogged orders
    LATE_FEE = 100

    def minmize_cost_rule(model):
        return sum(model.X[lane, day] * (shipping_costs[lane] + ((day - 1) * LATE_FEE)) 
                for lane in model.ValidLanes for day in model.Days)

    model.Objective = pyo.Objective(
        rule = minmize_cost_rule,
        sense = pyo.minimize,
        doc = "Minimize total costs (freight + warehouse + late fees)"
    )

    # CONSTRAINTS

    # 1. Demand Constraint: Every order must be fulfilled exactly once
    def demand_rule(model, order_id):
        lanes_for_this_order = [lane for lane in model.ValidLanes if lane[0] == order_id]

        # Check if any such lane exists if not skip
        if not lanes_for_this_order:
            return pyo.Constraint.Skip
        
        return sum(model.X[lane, day] for lane in lanes_for_this_order for day in model.Days) == 1

    # Attach demand constraint to model
    model.DemandConstraint = pyo.Constraint(
        model.O,
        rule = demand_rule,
        doc = "Fulfill every order exactly once"
    )

    # 2. Capacity Constraint: Plant capacity based on the number of orders
    def capacity_rule(model, plant_id, day):
        # All lanes assigned to this plant
        lanes_for_plant = [lane for lane in model.ValidLanes if lane[1] == plant_id]

        # Check if no valid lanes exists for this plant
        if not lanes_for_plant:
            return pyo.Constraint.Skip
        
        # Find the number of orders assigned to this plant
        # By summing the decision variables
        total_orders_assigned_today = sum(model.X[lane, day] for lane in lanes_for_plant)

        return total_orders_assigned_today <= plant_capacities[plant_id]

    # Attach the capacity constraint to model
    model.CapacityConstraint = pyo.Constraint(
        model.P,
        model.Days,
        rule = capacity_rule,
        doc = "Plant Capacity Validation per Day"
    )


    # SOLVER USING CPLEX

    cplex_path = r"C:\Program Files\IBM\ILOG\CPLEX_Studio2211\cplex\bin\x64_win64\cplex.exe"

    solver = pyo.SolverFactory('cplex', executable = cplex_path)
    results = solver.solve(model, tee = False)

    print("\nOptimization Complete")


    # RESULT EXTRACTION
    if results.solver.termination_condition == pyo.TerminationCondition.optimal:
        print("Optimal Solution Found.")
        
        optimal_routes = []
        for lane in model.ValidLanes:
            for day in model.Days:
                if pyo.value(model.X[lane, day]) > 0.5:

                    final_cost = shipping_costs[lane] + ((day - 1) * LATE_FEE)
                    optimal_routes.append({
                        "Order ID": lane[0],
                        "Assigned Plant": lane[1],
                        "Origin Port": lane[2],
                        "Assigned Carrier": lane[3],
                        "Manufacturing Day": f"Day {day}",
                        "Total Cost ($)": round(final_cost, 2)
                    })

        results_df = pd.DataFrame(optimal_routes)

        output_dir = "results"
        os.makedirs(output_dir, exist_ok = True)
        file_path = os.path.join(output_dir, f"{scenario_name}.csv")
        results_df.to_csv(file_path, index=False)
        print(f"Success! {len(results_df)} orders optimally routed and saved to CSV.")
        total_network_cost = pyo.value(model.Objective)
        print(f"[{scenario_name.upper()}]: GRAND TOTAL COST = ${total_network_cost:,.2f}\n")

    elif results.solver.termination_condition == pyo.TerminationCondition.infeasible:
        print("\n[ALERT]: The model is INFEASIBLE!")
        print("No CSV was generated because a valid supply chain network is physically impossible.")
    else:
        print(f"\nSolver stopped with an unexpected status: {results.solver.termination_condition}")