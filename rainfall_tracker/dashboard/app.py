import streamlit as st
import pandas as pd
import plotly.express as px
import os
import requests
from datetime import datetime
from bs4 import BeautifulSoup

LOG_FILE = 'rainfall_log.csv'
BUILDING_FILE = 'buildings.csv'

# ------------------ Weather Scraper ------------------ #
def fetch_live_weather():
    try:
        url = "https://www.weather.iust.ac.in/"  # Update to actual weather URL
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')

        temp = soup.find(id="lbltemp").text.strip()
        humidity = soup.find(id="lblhumidity").text.strip()
        rainfall = soup.find(id="lblrainfall").text.strip()
        date_time = datetime.now().strftime("%d %b %Y %I:%M %p")

        return temp, humidity, rainfall, date_time
    except Exception as e:
        return "-", "-", "-", datetime.now().strftime("%d %b %Y %I:%M %p")

# ------------------ Load Data ------------------ #
@st.cache_data
def load_data():
    if os.path.exists(LOG_FILE):
        df = pd.read_csv(LOG_FILE, parse_dates=['date'])
    else:
        st.warning("rainfall_log.csv not found. Starting with empty data.")
        df = pd.DataFrame(columns=['date', 'building_name', 'rainfall_mm', 'water_harvested_litres'])

    if os.path.exists(BUILDING_FILE):
        buildings = pd.read_csv(BUILDING_FILE)
    else:
        st.warning("buildings.csv not found. Building list will be empty.")
        buildings = pd.DataFrame(columns=['building_name'])

    return df, buildings

# ------------------ Main ------------------ #
st.set_page_config(page_title="Campus Rainwater Harvesting", layout="wide")
st.title("🌧️ Rainwater Harvesting Dashboard - IUST Campus")

# Load data
df, buildings = load_data()

# Query param to detect building
query_building = st.query_params.get("building")
building_list = sorted(df["building_name"].unique())

if query_building in building_list:
    selected = query_building
elif building_list:
    selected = st.selectbox("Select Building", building_list)
else:
    st.warning("Rainfall data is empty. Please upload or check the file.")
    st.stop()

# ------------------ Live Weather ------------------ #
st.subheader("🌦️ Live Weather Conditions")
temp, humidity, rain_today, now = fetch_live_weather()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Temperature", temp)
col2.metric("Humidity", humidity)
col3.metric("Rainfall (Today)", rain_today)
col4.metric("Date & Time", now)

# ------------------ Filter & Display ------------------ #
building_df = df[df["building_name"] == selected]

if building_df.empty:
    st.error("No data available for this building.")
else:
    today = pd.Timestamp.today().normalize()
    today_data = building_df[building_df["date"] == today]

    rain_today_val = today_data["rainfall_mm"].sum() if not today_data.empty else 0
    water_today_val = today_data["water_harvested_litres"].sum() if not today_data.empty else 0

    st.subheader("📍 Live Harvesting Today")
    col5, col6 = st.columns(2)
    col5.metric("Rainfall (mm)", f"{rain_today_val:.2f}" if rain_today_val else "–")
    col6.metric("Water Harvested (Litres)", f"{water_today_val:,.0f}" if water_today_val else "–")

    # ------------------ Year-Wise Harvesting ------------------ #
    building_df["year"] = building_df["date"].dt.year
    year_list = sorted(building_df["year"].unique())[::-1]  # Latest first

    st.subheader("📆 Year-wise Harvesting")
    selected_year = st.selectbox("Select Year", year_list)

    year_df = building_df[building_df["year"] == selected_year]
    if year_df.empty:
        st.warning("No data found for selected year. Showing previous year.")
        if len(year_list) > 1:
            year_df = building_df[building_df["year"] == year_list[1]]
        else:
            year_df = building_df

    year_df["month"] = year_df["date"].dt.strftime("%b")
    monthly = year_df.groupby("month")[["rainfall_mm", "water_harvested_litres"]].sum().reset_index()

    fig1 = px.bar(monthly, x="month", y="water_harvested_litres", title="Monthly Water Harvested",
                  labels={"water_harvested_litres": "Litres"}, color_discrete_sequence=["teal"])
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("📈 Daily Trends")
    fig2 = px.line(year_df, x="date", y=["rainfall_mm", "water_harvested_litres"],
                   labels={"value": "Amount", "variable": "Type"}, title="Daily Rainfall & Harvesting")
    st.plotly_chart(fig2, use_container_width=True)

    # ------------------ Building Comparison ------------------ #
    st.subheader("🏢 Compare Buildings")
    compare_df = df.groupby("building_name")[["rainfall_mm", "water_harvested_litres"]].sum().reset_index()
    fig3 = px.bar(compare_df, x="building_name", y="water_harvested_litres",
                  title="Total Water Harvested by Building",
                  labels={"water_harvested_litres": "Litres"}, color_discrete_sequence=["indianred"])
    st.plotly_chart(fig3, use_container_width=True)

    # ------------------ Download Button ------------------ #
    st.subheader("⬇️ Download Building Data")
    csv = building_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download as CSV", data=csv,
                       file_name=f"{selected}_rainfall_data.csv", mime='text/csv')

    with st.expander("📋 Show Raw Data"):
        st.dataframe(building_df)



