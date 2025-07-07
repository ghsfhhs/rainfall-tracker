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
ROOFTOP_AREA = 1000  # m²
RUNOFF_COEFFICIENT = 0.85
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
        df = pd.read_csv(LOG_FILE)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['building_name'] = df['building_name'].astype(str).str.strip().str.upper()  # ✅ Normalize
        return df
    else:
        return pd.DataFrame(columns=['date', 'building_name', 'rainfall_mm', 'water_harvested_litres'])

# ========== Save Log ==========
def save_log(df):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    df.to_csv(LOG_FILE, index=False)

# ========== App Start ==========
st.title("🌧️ Rainwater Harvesting Dashboard - IUST Campus (CEED)")

temp, hum, rain_today = fetch_live_weather()
if rain_today is None:
    st.warning("Live weather data unavailable. Using fallback value: 0 mm")
    rain_today = 0

# Header Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("🌡️ Temperature", f"{temp if temp is not None else '-'} °C")
col2.metric("💧 Humidity", f"{hum if hum is not None else '-'} %")
col3.metric("🌧️ Rainfall (Today)", f"{rain_today} mm")
col4.metric("📅 Date", now.strftime("%d %b %Y"))

# ========== Load + Update Log ==========
df = load_log()
df = df.dropna(subset=['date'])

today_str = now.strftime("%Y-%m-%d")
if today_str not in df['date'].dt.strftime("%Y-%m-%d").values:
    new_row = {
        'date': today_str,
        'building_name': BUILDING_NAME,
        'rainfall_mm': rain_today,
        'water_harvested_litres': int(calculate_harvest(rain_today))
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_log(df)

# ========== Tabs ==========
tab1, tab2 = st.tabs(["📈 Live Dashboard", "📅 Year Wise Harvesting"])

# ========== TAB 1: LIVE DASHBOARD ==========
with tab1:
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.strftime('%b')
    df['month_num'] = df['date'].dt.month

    df_building = df[df['building_name'] == BUILDING_NAME]

    if not df_building.empty:
        selected_year = st.selectbox("Select Year", sorted(df_building['year'].unique(), reverse=True))
        year_df = df_building[df_building['year'] == selected_year]

        # Ensure numeric types
        year_df['rainfall_mm'] = pd.to_numeric(year_df['rainfall_mm'], errors='coerce')
        year_df['water_harvested_litres'] = pd.to_numeric(year_df['water_harvested_litres'], errors='coerce')

        # Monthly aggregation
        month_df = (
            year_df.groupby(['month', 'month_num'])[['rainfall_mm', 'water_harvested_litres']]
            .sum()
            .reset_index()
            .sort_values('month_num')
        )

        # === Monthly Summary Chart ===
        st.write(f"### 📊 Monthly Water Harvesting - {BUILDING_NAME} ({selected_year})")
        fig1 = px.bar(month_df, x='month', y='water_harvested_litres',
                      labels={'water_harvested_litres': 'Litres'},
                      color_discrete_sequence=["teal"])
        st.plotly_chart(fig1, use_container_width=True)

        # === Daily Line Chart ===
        fig2 = px.line(
            year_df, x='date', y=['rainfall_mm', 'water_harvested_litres'],
            labels={"value": "Amount", "variable": "Metric"},
            title=f"📈 Daily Rainfall & Harvesting - {BUILDING_NAME} ({selected_year})"
        )
        st.plotly_chart(fig2, use_container_width=True)

        # === Raw Data ===
        with st.expander("📋 Show Raw Data"):
            st.dataframe(year_df)
    else:
        st.warning("No data found for this building.")

# ========== TAB 2: YEAR WISE HARVESTING ==========
with tab2:
    st.header("📅 Year Wise Water Harvesting Summary")

    df['year'] = df['date'].dt.year
    df['building_name'] = df['building_name'].astype(str).str.strip().str.upper()  # normalize
    df_building = df[df['building_name'] == BUILDING_NAME.upper()]

    year_summary = (
        df_building
        .groupby('year')[['water_harvested_litres']]
        .sum()
        .reset_index()
        .sort_values('year', ascending=False)
    )

    st.subheader("💧 Total Water Harvested by Year")
    st.dataframe(year_summary.rename(columns={"year": "Year", "water_harvested_litres": "Total (Litres)"}))

    selected_year_tab2 = st.selectbox("🔽 Select Year to View Monthly Details", year_summary['year'])

    monthly_breakdown = (
        df_building[df_building['year'] == selected_year_tab2]
        .groupby(['month', 'month_num'])[['rainfall_mm', 'water_harvested_litres']]
        .sum()
        .reset_index()
        .sort_values('month_num')
    )

    st.subheader(f"📆 Monthly Harvesting for {selected_year_tab2}")
    st.dataframe(
        monthly_breakdown[['month', 'rainfall_mm', 'water_harvested_litres']]
        .rename(columns={
            "month": "Month",
            "rainfall_mm": "Rainfall (mm)",
            "water_harvested_litres": "Harvested (Litres)"
        })
    )










