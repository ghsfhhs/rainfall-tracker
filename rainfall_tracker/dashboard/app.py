import streamlit as st
import pandas as pd
import plotly.express as px
import os
import requests
from bs4 import BeautifulSoup
import re
from streamlit_autorefresh import st_autorefresh
from pytz import timezone
import datetime

# ========== Settings ==========
BUILDING_NAME = "CEED"
ROOFTOP_AREA = 1000  # m², example value
RUNOFF_COEFFICIENT = 0.85

# ========== File Paths ==========
LOG_FILE = "dashboard/rainfall_log.csv"

# ========== Time ==========
ist = timezone('Asia/Kolkata')
now = datetime.datetime.now(ist)
st.write("🕒 Current Time:", now.strftime("%Y-%m-%d %H:%M:%S"))

# ========== Fetch Live Weather ==========
def fetch_live_weather():
    url = "https://iust.ac.in/"
    try:
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)

        pattern = r"Temperature[:\s]*([\d]+).*?C.*?Humidity[:\s]*([\d]+).*?%.*?Rainfall[:\s]*([\d]+).*?mm"
        m = re.search(pattern, text, re.DOTALL)
        if m:
            temp, hum, rain = m.groups()
            return int(temp), int(hum), int(rain)
    except Exception as e:
        st.error(f"Error fetching weather: {e}")
    return None, None, None

# ========== Calculate Harvest ==========
def calculate_harvest(rain_mm):
    return rain_mm * ROOFTOP_AREA * RUNOFF_COEFFICIENT

# ========== Load Log ==========
def load_log():
    if os.path.exists(LOG_FILE):
        return pd.read_csv(LOG_FILE, parse_dates=['date'])
    else:
        return pd.DataFrame(columns=['date', 'building_name', 'rainfall_mm', 'water_harvested_litres'])

# ========== Save Log ==========
def save_log(df):
    df.to_csv(LOG_FILE, index=False)

# ========== App Logic ==========
st.title("🌧️ Rainwater Harvesting Dashboard - IUST Campus (CEED)")

temp, hum, rain_today = fetch_live_weather()
if temp is None:
    st.warning("Live weather data unavailable. Showing placeholders.")
    rain_today = 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Temperature", f"{temp if temp else '-'} °C")
col2.metric("Humidity", f"{hum if hum else '-'} %")
col3.metric("Rainfall (Today)", f"{rain_today} mm")
col4.metric("Date", now.strftime("%d %b %Y"))

# Calculate today's harvesting
today_harvest = calculate_harvest(rain_today)

st.subheader("Live Harvesting")
colA, colB = st.columns(2)
colA.metric("Rainfall", f"{rain_today} mm")
colB.metric("Today's Harvesting", f"{int(today_harvest)} L")

# Load existing log
df = load_log()

# Update today's entry
today_str = now.strftime("%Y-%m-%d")
if today_str not in df['date'].astype(str).values:
    new_row = {
        'date': today_str,
        'building_name': BUILDING_NAME,
        'rainfall_mm': rain_today,
        'water_harvested_litres': int(today_harvest)
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_log(df)

# Process data
if not df.empty:
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.strftime('%b')
    df['month_num'] = df['date'].dt.month

    # Filter by building
    df_building = df[df['building_name'] == BUILDING_NAME]

    selected_year = st.selectbox("Select Year", sorted(df_building['year'].unique(), reverse=True))
    year_df = df_building[df_building['year'] == selected_year]

    # Convert columns to numeric
    year_df['rainfall_mm'] = pd.to_numeric(year_df['rainfall_mm'], errors='coerce')
    year_df['water_harvested_litres'] = pd.to_numeric(year_df['water_harvested_litres'], errors='coerce')

    # Monthly summary
    month_df = year_df.groupby(['month', 'month_num'])[['rainfall_mm', 'water_harvested_litres']].sum().reset_index()
    month_df = month_df.sort_values('month_num')

    # Monthly bar chart
    st.write(f"### Monthly Water Harvesting - {BUILDING_NAME} ({selected_year})")
    fig1 = px.bar(month_df, x='month', y='water_harvested_litres',
                  title=f"Monthly Water Harvesting - {BUILDING_NAME} ({selected_year})",
                  color_discrete_sequence=["teal"])
    st.plotly_chart(fig1, use_container_width=True)

    # Daily line chart
    fig2 = px.line(year_df, x='date', y=['rainfall_mm', 'water_harvested_litres'],
                   labels={"value": "Amount", "variable": "Type"},
                   title=f"Daily Rainfall & Harvesting - {BUILDING_NAME} ({selected_year})")
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("Show Raw Data"):
        st.dataframe(year_df)
else:
    st.info("No historical rainfall data to display yet.")







