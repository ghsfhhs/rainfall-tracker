import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

LOG_FILE = '../data/rainfall_log.csv'
BUILDING_FILE = '../data/buildings.csv'

@st.cache_data
def load_data():
    df = pd.read_csv(LOG_FILE, parse_dates=["date"])
    buildings = pd.read_csv(BUILDING_FILE)
    return df, buildings

df, buildings = load_data()

st.set_page_config(page_title="Campus Rainwater Harvesting", layout="wide")
st.title("🌧️ Rainwater Harvesting Dashboard - IUST Campus")

building_list = sorted(df["building_name"].unique())

query_building = st.query_params.get("building")
if query_building and query_building in building_list:
    selected = query_building
else:
    selected = st.selectbox("Select Building", building_list)

building_df = df[df["building_name"] == selected]

total_water = building_df["water_harvested_litres"].sum()
avg_rainfall = building_df["rainfall_mm"].mean()

st.metric("💧 Total Harvested Water (Litres)", f"{total_water:,.0f}")
st.metric("🌧️ Average Daily Rainfall (mm)", f"{avg_rainfall:.2f}")

df["month"] = df["date"].dt.to_period("M")
monthly_summary = (
    building_df.groupby("month")[["rainfall_mm", "water_harvested_litres"]]
    .sum()
    .reset_index()
)
monthly_summary["month"] = monthly_summary["month"].astype(str)

st.subheader("📅 Monthly Summary")
fig1 = px.bar(
    monthly_summary,
    x="month",
    y="water_harvested_litres",
    title="Monthly Water Harvested",
    labels={"water_harvested_litres": "Litres", "month": "Month"},
    color_discrete_sequence=["teal"]
)
st.plotly_chart(fig1, use_container_width=True)

st.subheader("📈 Daily Rainfall & Water Harvested")
fig2 = px.line(
    building_df,
    x="date",
    y=["rainfall_mm", "water_harvested_litres"],
    labels={"value": "Amount", "variable": "Type"},
    title="Daily Trends",
)
st.plotly_chart(fig2, use_container_width=True)

st.subheader("🏢 Compare Buildings")
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

st.subheader("⬇️ Download Building Data")
csv = building_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Download as CSV",
    data=csv,
    file_name=f"{selected}_rainfall_data.csv",
    mime='text/csv',
)

with st.expander("📋 Show Raw Data"):
    st.dataframe(building_df)
