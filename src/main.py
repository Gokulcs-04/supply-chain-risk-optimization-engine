from pyomo_solver import extract_network_data, run_optimization
from risk_simulator import simulate_port_closure, simulate_plant_strike, simulate_fuel_crisis

def main():
    print(" SUPPLY CHAIN OPTIMIZATION AND RISK SIMULATION ")

    # EXTRACT DATA
    valid_lanes, shipping_costs, plant_capacities, orders_list, plant_list, plant_port_dict = extract_network_data()
    print(f"Extraction Complete: {len(valid_lanes)} valid shipping lanes identified.")

    # RUN BASE OPTIMIZATION
    run_optimization(
        valid_lanes = valid_lanes,
        shipping_costs = shipping_costs,
        plant_capacities = plant_capacities,
        orders_list = orders_list,
        plant_list = plant_list,
        required_days = 7,
        scenario_name = 'Baseline_Network'
    )

    # CLI MENU
    print("\n CHOOSE THE RISK TO SIMULATE ")
    print("\n1. Port Closure (Routing Stress)")
    print("2. Plant Capacity Reduction (Capacity Stress)")
    print("3. Global Fuel Increase (Cost Stress)")
    print("4. Exit Pipeline")

    choice = int(input("\nEnter 1, 2, 3 or 4: "))

    # default variables
    risk_lanes = valid_lanes
    risk_capacity = plant_capacities
    risk_costs = shipping_costs
    risk_days_required = 10
    target_name = None

    # RUN RISK SIMULATION

    if choice == 1:
        risk_lanes, target_name = simulate_port_closure(valid_lanes = valid_lanes, plant_port_dict = plant_port_dict)
        risk_days_required = 10
        scenario_title = target_name + "_Closure_Network"
        
    elif choice == 2:
        risk_capacity, target_name = simulate_plant_strike(valid_lanes = valid_lanes, plant_capacities = plant_capacities)
        if target_name == "PLANT03":
            risk_days_required = 35
        scenario_title = target_name + "_Capacity_Reduction_Network"
    elif choice == 3:
        risk_costs, target_name = simulate_fuel_crisis(shipping_costs = shipping_costs)
        scenario_title = "Fuel_Crisis_Network"
    elif choice == 4:
        print("\nExiting Pipeline.")
        return
    else:
        print("\nInvalid Selection. Please choose a valid option!")
        return
    
    if target_name:
        print("\nSimulating Risk...")
        run_optimization(
            valid_lanes = risk_lanes,
            shipping_costs = risk_costs,
            plant_capacities = risk_capacity,
            orders_list = orders_list,
            plant_list = plant_list,
            required_days = risk_days_required,
            scenario_name = scenario_title          
        )

if __name__ == "__main__":
    main()