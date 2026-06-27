import sqlite3
import pandas as pd

sc_db = pd.read_excel('data/supply_chain_database.xlsx', sheet_name = None)

# Store each sheet (table) as a df
order_list_table = sc_db['OrderList']
freight_rates_table = sc_db['FreightRates']
wh_costs_table = sc_db['WhCosts']
wh_capacities_table = sc_db['WhCapacities']
products_per_plant = sc_db['ProductsPerPlant']
vmi_customers = sc_db['VmiCustomers']
plant_ports = sc_db['PlantPorts']

# DATA CLEANING

# freight_rates_table transformation
freight_rates_table['minimum cost'] = freight_rates_table['minimum cost'].round(4)
freight_rates_table['rate'] = freight_rates_table['rate'].round(4)
freight_rates_table['max_wgh_qty'] = freight_rates_table['max_wgh_qty'].round(4)
freight_rates_table['minm_wgh_qty'] = freight_rates_table['minm_wgh_qty'].round(4)

# order_list_table transformation
order_list_table[['Order ID', 'Product ID']] = order_list_table[['Order ID', 'Product ID']].astype("string")
order_list_table['Order ID'] = order_list_table['Order ID'].str[:-2]
order_list_table['Weight'] = order_list_table['Weight'].round(4)

# products_per_plant transformation
products_per_plant['Product ID'] = products_per_plant['Product ID'].astype("string")

# wh_costs_table transformation
wh_costs_table['Cost/unit'] = wh_costs_table['Cost/unit'].round(4)


# TABLE CREATION IN SQLITE DB

conn = sqlite3.connect('data/network.sqlite')

order_list_table.to_sql('OrderListTable', conn, index = False, if_exists='replace')
freight_rates_table.to_sql('FreightRatesTable', conn, index = False, if_exists='replace')
wh_costs_table.to_sql('WarehouseCostTable', conn, index = False, if_exists='replace')
wh_capacities_table.to_sql('WarehouseCapacityTable', conn, index= False, if_exists= 'replace')
products_per_plant.to_sql('ProductsPerPlantTable', conn, index= False, if_exists= 'replace')
vmi_customers.to_sql('VmiCustomersTable', conn, index= False, if_exists='replace')
plant_ports.to_sql('PlantPortsTable', conn, index= False, if_exists= 'replace')

conn.close()


