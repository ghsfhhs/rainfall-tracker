import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

LOG_FILE = 'rainfall_log.csv'
BUILDING_FILE = 'buildings.csv'

import os

@st.cache_data
def load_data():
    # Load rainfall log
    if os.path.exists(LOG_FILE):
        try:
            df = pd.read_csv(LOG_FILE, parse_dates=["date"])
        except Exception as e:
            st.error(f"Error reading {LOG_FILE}: {e}")
            df = pd.DataFrame(columns=["date", "building_name", "rainfall_mm", "water_harvested_litres"])
    else:
        st.warning(f"{LOG_FILE} not found. Starting with empty data.")
        df = pd.DataFrame(columns=["date", "building_name", "rainfall_mm", "water_harvested_litres"])

    # Load building metadata
    if os.path.exists(BUILDING_FILE):
        try:
            buildings = pd.read_csv(BUILDING_FILE)
        except Exception as e:
            st.error(f"Error reading {BUILDING_FILE}: {e}")
            buildings = pd.DataFrame(columns=["building_name"])
    else:
        st.warning(f"{BUILDING_FILE} not found. Building list will be empty.")
        buildings = pd.DataFrame(columns=["building_name"])

    return df, buildings


# Load data
df, buildings = load_data()
if df.empty:
    st.error("Rainfall data is empty. Please upload or check the file.")
    st.stop()

if buildings.empty:
    st.warning("Building list is empty. Some charts may not display correctly.")


st.set_page_config(page_title="Campus Rainwater Harvesting", layout="wide")
st.title("🌧️ Rainwater Harvesting Dashboard - IUST Campus")

# Dropdown or QR-based building selection
building_list = sorted(df["building_name"].unique())
query_building = st.query_params.get("building")

if query_building in building_list:
    selected = query_building
elif building_list:
    selected = st.selectbox("Select Building", building_list)
else:
    st.warning("No building data available.")
    st.stop()

# Filter data
building_df = df[df["building_name"] == selected]

# Stats
total_water = building_df["water_harvested_litres"].sum()
avg_rainfall = building_df["rainfall_mm"].mean()

if not building_df.empty:
    total_water = building_df["water_harvested_litres"].sum()
    avg_rainfall = building_df["rainfall_mm"].mean()
    st.metric("💧 Total Harvested Water (Litres)", f"{total_water:,.0f}")
    st.metric("🌧️ Average Daily Rainfall (mm)", f"{avg_rainfall:.2f}")
else:
    st.metric("💧 Total Harvested Water (Litres)", "-")
    st.metric("🌧️ Average Daily Rainfall (mm)", "-")

# Monthly Summary
df["month"] = df["date"].dt.to_period("M")
monthly_summary = (
    building_df.groupby("month")[["rainfall_mm", "water_harvested_litres"]]
    .sum()
    .reset_index()
)
monthly_summary["month"] = monthly_summary["month"].astype(str)

st.subheader("📅 Monthly Summary")
if not building_df.empty:
    df["month"] = df["date"].dt.to_period("M")
    monthly_summary = (
        building_df.groupby("month")[["rainfall_mm", "water_harvested_litres"]]
        .sum()
        .reset_index()
    )
    monthly_summary["month"] = monthly_summary["month"].astype(str)
    
    fig1 = px.bar(
        monthly_summary,
        x="month",
        y="water_harvested_litres",
        title="Monthly Water Harvested",
        labels={"water_harvested_litres": "Litres", "month": "Month"},
        color_discrete_sequence=["teal"]
    )
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.info("No data available for monthly summary.")

# Daily Graph
st.subheader("📈 Daily Rainfall & Water Harvested")
if not building_df.empty:
    fig2 = px.line(
        building_df,
        x="date",
        y=["rainfall_mm", "water_harvested_litres"],
        labels={"value": "Amount", "variable": "Type"},
        title="Daily Trends",
    )
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("No daily data to display.")


# Building Comparison
st.subheader("🏢 Compare Buildings")
if not df.empty:
    compare_df = (
        df.groupby("building_name")[["rainfall_mm", "water_harvested_litres"]]
        .sum()
        .reset_index()
    )
    fig3 = px.bar(
        compare_df,
        x="building_name",
        y="water_harvested_litres",
        title="Total Water Harvested by Building",
        labels={"water_harvested_litres": "Litres"},
        color_discrete_sequence=["indianred"]
    )
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No building comparison data available.")


# Download button
st.subheader("⬇️ Download Building Data")
if not building_df.empty:
    csv = building_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download as CSV",
        data=csv,
        file_name=f"{selected}_rainfall_data.csv",
        mime='text/csv',
    )
else:
    st.write("No data available to download.")

with st.expander("📋 Show Raw Data"):
    if not building_df.empty:
        st.dataframe(building_df)
    else:
        st.write("No data to display.")


# Raw data table
with st.expander("📋 Show Raw Data"):
    st.dataframe(building_df)

if df.empty:
    st.warning("Rainfall data is empty. Showing placeholders.")

if buildings.empty:
    st.warning("Building list is empty. Limited functionality.")


