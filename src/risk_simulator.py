import random

# Port Closure Simulation
def simulate_port_closure(valid_lanes, plant_port_dict):
    '''
    Analyse the ports in plant_port_dict and randomly choose only those ports
    that is solely related to a plant so as to not make the model infeasible
    '''

    # Select only active ports
    active_ports = set(lane[2] for lane in valid_lanes)
    all_ports = set(port for ports in plant_port_dict.values() for port in ports)
    safe_for_closure = []

    for port in all_ports:
        if port not in active_ports:
            continue

        can_close = True

        for plant, connected_ports in plant_port_dict.items():
            if port in connected_ports:
                # Check if this is the only port availabe for this plant
                if len(connected_ports) <= 1:
                    can_close = False
                    break
        
        if can_close:
            safe_for_closure.append(port)
        
    
    # Check if no such ports exist
    if not safe_for_closure:
        print("\nEvery port is a single point of failure.")
        return valid_lanes, None
    
    # Pick a random port for closure
    target_port = random.choice(safe_for_closure)
    print(f"{target_port} has been chosen for closure!")

    # Filter the valid lanes to only surviving lanes
    open_lanes = [lane for lane in valid_lanes if lane[2] != target_port]
    no_of_routes_closed = len(valid_lanes) - len(open_lanes)
    print(f"[ALERT] {no_of_routes_closed} shipping lanes closed.")

    return open_lanes, target_port

# Plant Capacity Reduction
def simulate_plant_strike(valid_lanes, plant_capacities):
    '''
    Simulate a major labor strike or machine failure at a random 
    factory by reducing the plant capacity by 80%
    '''

    modified_capacities = plant_capacities.copy()

    active_plants = list(set(lane[1] for lane in valid_lanes))

    # target_plant = random.choice(active_plants)
    target_plant = "PLANT03"
    print(f"[ALERT] {target_plant} capacity is reduced by 80%.")
    original_cap = modified_capacities[target_plant]

    # Decrease the capacity by 80%
    new_cap = int(original_cap * 0.2)
    modified_capacities[target_plant] = new_cap

    print(f'{target_plant} capacity reduced from {original_cap} to {new_cap}')

    return modified_capacities, target_plant

# Fuel Cost Increase
def simulate_fuel_crisis(shipping_costs):
    '''
    Simulate a increase in fuel prices across all lanes which 
    results in shipping costs increasing by 25%
    '''

    modified_costs = {}

    for lane, cost in shipping_costs.items():
        modified_costs[lane] = cost * 1.25

    print(f"\n[ALERT] Freight rates across {len(shipping_costs)} shipping lanes increased by 25%.")
    
    return modified_costs, "Fuel_Crisis"