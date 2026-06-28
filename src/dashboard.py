import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import glob


# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Supply Chain Control Tower", page_icon="🕸️", layout="wide")
st.title("Supply Chain Optimization and Risk Simulation")
st.markdown("---")


# 2. DATA LOADING & PROCESSING
@st.cache_data
def load_data():
    out_dir = "results"
    baseline_path = os.path.join(out_dir, "Baseline_Network.csv")
    fuel_crisis_path = os.path.join(out_dir, "Fuel_Crisis_Network.csv")
    
    if os.path.exists(baseline_path):
        baseline_df = pd.read_csv(baseline_path)
    else:
        st.error(f"Cannot find {baseline_path}. Run main.py first!")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), "Unknown", pd.DataFrame(), "Unknown"

    if os.path.exists(fuel_crisis_path):
        fuel_df = pd.read_csv(fuel_crisis_path)
    else:
        fuel_df = baseline_df.copy() 

    closure_files = glob.glob(os.path.join(out_dir, "*_Closure_Network.csv"))
    if closure_files:
        closure_path = closure_files[0]
        closure_df = pd.read_csv(closure_path)
        closed_port = os.path.basename(closure_path).split('_')[0]
    else:
        closure_df = baseline_df.copy()
        closed_port = "None"

    capacity_files = glob.glob(os.path.join(out_dir, "*_Capacity_Reduction_Network.csv"))
    if capacity_files:
        capacity_path = capacity_files[0]
        capacity_df = pd.read_csv(capacity_path)
        struck_plant = os.path.basename(capacity_path).split('_')[0]
    else:
        capacity_df = baseline_df.copy()
        struck_plant = "None"

    return baseline_df, fuel_df, closure_df, closed_port, capacity_df, struck_plant

baseline_df, fuel_df, closure_df, closed_port, capacity_df, struck_plant = load_data()


# 3. SIDEBAR UI 
st.sidebar.title("Network Controls")
st.sidebar.markdown("Toggle the environment to observe topology shifts.")

scenario = st.sidebar.radio(
    "Select Operating Environment:",
    (
        "🟢 Baseline (Perfect World)", 
        "🔴 Fuel Crisis (+25% Freight Cost)",
        f"🟠 Port Closure ({closed_port} Shut Down)",
        f"🟣 Plant Strike ({struck_plant} Capacity -80%)"
    )
)

if "Baseline" in scenario:
    active_df = baseline_df
    base_rgb = "46, 204, 113" 
elif "Fuel" in scenario:
    active_df = fuel_df
    base_rgb = "231, 76, 60"  
elif "Port" in scenario:
    active_df = closure_df
    base_rgb = "243, 156, 18" 
else:
    active_df = capacity_df
    base_rgb = "155, 89, 182" 


# 4. DYNAMIC KPI METRICS & STATE MANAGEMENT
DEST_PORT = "DEST: PORT09"
display_df = active_df
selected_node = None


# check if the map has been clicked in the session state
if "network_map" in st.session_state:
    selection = st.session_state.network_map.get("selection", {})
    if selection and len(selection.get("points", [])) > 0:
        clicked_data = selection["points"][0]
        if "customdata" in clicked_data:
            # extract the node name
            raw_data = clicked_data["customdata"]
            selected_node = raw_data[0] if isinstance(raw_data, list) else raw_data

            # If a specific facility was clicked, filter the data before calculating KPIs
            if selected_node != DEST_PORT:
                display_df = active_df[(active_df['Assigned Plant'] == selected_node) | 
                                       (active_df['Origin Port'] == selected_node)]

if not active_df.empty:
    # 1. Provide UI feedback on what the KPIs are showing
    if selected_node and selected_node != DEST_PORT:
        st.info(f"📊 **Isolating Facility:** Showing specific metrics and active orders for **{selected_node}**.")
    else:
        st.success("🌐 **Global View:** Showing macro metrics for the entire supply chain network.")

    # 2. Calculate KPIs using the FILTERED display_df, not the master active_df!
    total_cost = display_df["Total Cost ($)"].sum()
    total_orders = len(display_df)
    avg_cost = total_cost / total_orders if total_orders > 0 else 0

    if "Manufacturing Day" in display_df.columns and not display_df.empty:
        actual_days = display_df["Manufacturing Day"].str.replace("Day ", "").astype(int)
        max_days = actual_days.max()
    else:
        max_days = 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Cost", f"${total_cost:,.2f}")
    col2.metric("Orders Routed", f"{total_orders:,}")
    col3.metric("Avg Cost per Order", f"${avg_cost:,.2f}")
    col4.metric("Max Days to Fulfill", f"{max_days} Days")

    st.markdown("---")


    # 3. ABSTRACT MULTI-ECHELON TOPOLOGY 
    st.subheader("Global Routing Topology")

    lane_summary = active_df.groupby(['Assigned Plant', 'Origin Port']).size().reset_index(name='Order Volume')
    port_summary = lane_summary.groupby('Origin Port')['Order Volume'].sum().reset_index()

    base_summary = baseline_df.groupby(['Assigned Plant', 'Origin Port']).size().reset_index()
    plants = base_summary['Assigned Plant'].unique()
    all_ports = base_summary['Origin Port'].unique()
    tier2_ports = [p for p in all_ports if p != "PORT09"]

    node_coords = {}
    for i, plant in enumerate(plants):
        node_coords[plant] = {"x": 1, "y": (i - len(plants)/2) * 2}
    for i, port in enumerate(tier2_ports):
        node_coords[port] = {"x": 3, "y": (i - len(tier2_ports)/2) * 2}
    node_coords[DEST_PORT] = {"x": 5, "y": 0}

    fig = go.Figure()

    all_volumes = pd.concat([lane_summary['Order Volume'], port_summary['Order Volume']])
    min_vol = all_volumes.min()
    max_vol = all_volumes.max()
    if max_vol == min_vol: max_vol = min_vol + 1

    for _, row in lane_summary.iterrows():
        p_name = row['Assigned Plant']
        o_name = row['Origin Port']
        volume = row['Order Volume']
        
        alpha = 0.2 + 0.8 * ((volume - min_vol) / (max_vol - min_vol))
        dynamic_color = f'rgba({base_rgb}, {alpha})'
        
        if o_name == "PORT09":
            target_x, target_y = node_coords[DEST_PORT]["x"], node_coords[DEST_PORT]["y"]
            hover_text = f"Direct Route: {p_name} ➔ {DEST_PORT}<br>Orders: {volume}"
        else:
            target_x, target_y = node_coords[o_name]["x"], node_coords[o_name]["y"]
            hover_text = f"Leg 1: {p_name} ➔ {o_name}<br>Orders: {volume}"
        
        fig.add_trace(go.Scatter(
            x=[node_coords[p_name]["x"], target_x],
            y=[node_coords[p_name]["y"], target_y],
            mode='lines', line=dict(width=3, color=dynamic_color), 
            hoverinfo='text', text=hover_text, showlegend=False
        ))

    tier2_summary = port_summary[port_summary['Origin Port'] != "PORT09"]
    for _, row in tier2_summary.iterrows():
        o_name = row['Origin Port']
        volume = row['Order Volume']
        
        alpha = 0.2 + 0.8 * ((volume - min_vol) / (max_vol - min_vol))
        dynamic_color = f'rgba({base_rgb}, {alpha})'
        
        fig.add_trace(go.Scatter(
            x=[node_coords[o_name]["x"], node_coords[DEST_PORT]["x"]],
            y=[node_coords[o_name]["y"], node_coords[DEST_PORT]["y"]],
            mode='lines', line=dict(width=3, color=dynamic_color), 
            hoverinfo='text', text=f"Leg 2: Ocean Freight from {o_name}<br>Consolidated Orders: {volume}", showlegend=False
        ))

    # 4. DRAW THE NODES 
    plant_colors = ['#e74c3c' if (p == struck_plant and "Strike" in scenario) else '#3498db' for p in plants]
    fig.add_trace(go.Scatter(
        x=[node_coords[p]["x"] for p in plants], y=[node_coords[p]["y"] for p in plants],
        mode='markers+text', marker=dict(symbol='square', size=25, color=plant_colors, line=dict(width=2, color='white')),
        text=plants, textposition="middle right", hoverinfo='text', name="Plants", 
        customdata=plants 
    ))
    
    active_ports_list = tier2_summary['Origin Port'].tolist()
    port_colors = ['#e67e22' if p in active_ports_list else '#7f8c8d' for p in tier2_ports]
    fig.add_trace(go.Scatter(
        x=[node_coords[p]["x"] for p in tier2_ports], y=[node_coords[p]["y"] for p in tier2_ports],
        mode='markers+text', marker=dict(symbol='circle', size=25, color=port_colors, line=dict(width=2, color='white')),
        text=tier2_ports, textposition="bottom center", hoverinfo='text', name="Ports",
        customdata=tier2_ports
    ))

    fig.add_trace(go.Scatter(
        x=[node_coords[DEST_PORT]["x"]], y=[node_coords[DEST_PORT]["y"]],
        mode='markers+text', marker=dict(symbol='hexagram', size=45, color='#9b59b6', line=dict(width=3, color='white')),
        text=[DEST_PORT], 
        textposition="top center", 
        hoverinfo='text', name="Destination",
        customdata=[DEST_PORT] 
    ))

    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode='markers',
        marker=dict(
            colorscale=[[0, f'rgba({base_rgb}, 0.2)'], [1, f'rgba({base_rgb}, 1.0)']],
            cmin=min_vol, cmax=max_vol, showscale=True,
            colorbar=dict(
                title=dict(text="Line Opacity = Order Volume", side="top", font=dict(color="white")),
                thickness=10, len=0.6, x=0.5, y=-0.15, orientation='h', 
                tickvals=[min_vol, max_vol], ticktext=[f"{min_vol} Orders", f"{max_vol} Orders"],
                tickfont=dict(color="white"), outlinewidth=0
            )
        ),
        showlegend=False, hoverinfo='none'
    ))

    fig.update_layout(
        height=650, 
        plot_bgcolor='rgba(0,0,0,0)', 
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), 
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=20, r=20, t=80, b=100), 
        
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(color="white")
        )
    )

    st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key="network_map")

    # 5. RAW DATA TABLE 
    with st.expander("View Raw Routing Data"):
        if selected_node and selected_node != DEST_PORT:
            st.write(f"Showing filtered data for: **{selected_node}**")
        else:
            st.write("Showing full network data. Click a node on the map to filter.")
        
        st.dataframe(display_df, use_container_width=True)