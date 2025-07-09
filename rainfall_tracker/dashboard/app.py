import streamlit as st
import pandas as pd
import plotly.express as px
import os
import requests
from bs4 import BeautifulSoup
import re
from pytz import timezone
import datetime

# ========== Settings ==========
BUILDING_NAME = "CEED"
ROOFTOP_AREA = 1000  # m²
RUNOFF_COEFFICIENT = 0.85
MONTHLY_LOG_FILE = "dashboard/rainfall_log.csv"
DAILY_LOG_FILE = "dashboard/daily_log.csv"

# ========== Time ==========
ist = timezone('Asia/Kolkata')
now = datetime.datetime.now(ist)
today_str = now.strftime("%Y-%m-%d")
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

# ========== Load Logs ==========
def load_log(file_path):
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        return df.dropna(subset=['date'])
    return pd.DataFrame(columns=['date', 'building_name', 'rainfall_mm', 'water_harvested_litres'])

# ========== Save Logs ==========
def save_log(df, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df.to_csv(file_path, index=False)

# ========== Load Data ==========
df_daily = load_log(DAILY_LOG_FILE)
df_monthly = load_log(MONTHLY_LOG_FILE)

# ========== Fetch and Log Today's Data ==========
temp, hum, rain_today = fetch_live_weather()
if rain_today is None:
    st.warning("Live weather data unavailable. Using fallback value: 0 mm")
    rain_today = 0

today_harvest = calculate_harvest(rain_today)

# Add to daily log
if today_str not in df_daily['date'].dt.strftime("%Y-%m-%d").values:
    new_daily_row = {
        'date': pd.to_datetime(today_str),
        'building_name': BUILDING_NAME,
        'rainfall_mm': rain_today,
        'water_harvested_litres': int(today_harvest)
    }
    df_daily = pd.concat([df_daily, pd.DataFrame([new_daily_row])], ignore_index=True)
    save_log(df_daily, DAILY_LOG_FILE)

# Update monthly log if it's the last day of month
if now.day == 1 and len(df_daily) > 0:
    prev_month = (now.replace(day=1) - datetime.timedelta(days=1)).month
    prev_year = (now.replace(day=1) - datetime.timedelta(days=1)).year
    df_prev_month = df_daily[(df_daily['date'].dt.month == prev_month) & (df_daily['date'].dt.year == prev_year)]
    if not df_prev_month.empty:
        total_rainfall = df_prev_month['rainfall_mm'].sum()
        total_harvest = df_prev_month['water_harvested_litres'].sum()
        summary_date = f"{prev_year}-{prev_month:02d}-01"

        # Prevent duplicate month entry
        existing = df_monthly['date'].dt.strftime("%Y-%m").isin([f"{prev_year}-{prev_month:02d}"]).any()
        if not existing:
            new_monthly_row = {
                'date': pd.to_datetime(summary_date),
                'building_name': BUILDING_NAME,
                'rainfall_mm': total_rainfall,
                'water_harvested_litres': int(total_harvest)
            }
            df_monthly = pd.concat([df_monthly, pd.DataFrame([new_monthly_row])], ignore_index=True)
            save_log(df_monthly, MONTHLY_LOG_FILE)

# ========== UI Start ==========
st.title("🌧️ Rainwater Harvesting Dashboard - IUST Campus (CEED)")

col1, col2, col3, col4 = st.columns(4)
col1.metric("🌡️ Temperature", f"{temp if temp is not None else '-'} °C")
col2.metric("💧 Humidity", f"{hum if hum is not None else '-'} %")
col3.metric("🌧️ Rainfall (Today)", f"{rain_today} mm")
col4.metric("📅 Date", now.strftime("%d %b %Y"))

# ========== Tabs ==========
tab1, tab2 = st.tabs(["📈 Live Dashboard", "📅 Year Wise Harvesting"])

# ========== TAB 1: Live Dashboard ==========
with tab1:
    st.subheader("Live Harvesting - CEED Building")
    col1, col2 = st.columns(2)
    col1.metric("🌧️ Rainfall", f"{rain_today} mm")
    col2.metric("💧 Harvested", f"{int(today_harvest)} L")

    df_plot = df_daily.copy()
    df_plot['year'] = df_plot['date'].dt.year
    df_plot['month'] = df_plot['date'].dt.strftime('%b')
    df_plot['month_num'] = df_plot['date'].dt.month

    df_building = df_plot[df_plot['building_name'] == BUILDING_NAME]

    if not df_building.empty:
        selected_year = st.selectbox("📅 Select Year", sorted(df_building['year'].unique(), reverse=True))
        year_df = df_building[df_building['year'] == selected_year]

        year_df['rainfall_mm'] = pd.to_numeric(year_df['rainfall_mm'], errors='coerce')
        year_df['water_harvested_litres'] = pd.to_numeric(year_df['water_harvested_litres'], errors='coerce')

        month_df = (
            year_df.groupby(['month', 'month_num'])[['rainfall_mm', 'water_harvested_litres']]
            .sum()
            .reset_index()
            .sort_values('month_num')
        )

        st.write(f"### 📊 Monthly Water Harvesting - {BUILDING_NAME} ({selected_year})")
        fig1 = px.bar(month_df, x='month', y='water_harvested_litres',
                      labels={'water_harvested_litres': 'Litres'},
                      color_discrete_sequence=["teal"])
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.line(year_df, x='date', y=['rainfall_mm', 'water_harvested_litres'],
                       labels={"value": "Amount", "variable": "Metric"},
                       title=f"📈 Daily Rainfall & Harvesting - {BUILDING_NAME} ({selected_year})")
        st.plotly_chart(fig2, use_container_width=True)

        with st.expander("📋 Show Raw Daily Data"):
            st.dataframe(year_df)
    else:
        st.warning("No data found for this building.")

# ========== TAB 2: Year Wise Summary ==========
with tab2:
    st.header("📅 Year Wise Water Harvesting Summary")

    df_summary = df_monthly.copy()
    df_summary['year'] = df_summary['date'].dt.year
    df_summary['month'] = df_summary['date'].dt.strftime('%b')
    df_summary['month_num'] = df_summary['date'].dt.month

    df_summary = df_summary[df_summary['building_name'] == BUILDING_NAME]

    if not df_summary.empty:
        year_summary = (
            df_summary.groupby('year')[['water_harvested_litres']]
            .sum()
            .reset_index()
            .sort_values('year', ascending=False)
        )

        st.subheader("💧 Total Water Harvested by Year")
        st.dataframe(year_summary.rename(columns={"year": "Year", "water_harvested_litres": "Total (Litres)"}))

        selected_year_tab2 = st.selectbox("📌 Select Year to View Monthly", year_summary['Year'])

        monthly_breakdown = (
            df_summary[df_summary['year'] == selected_year_tab2]
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
    else:
        st.info("No monthly or yearly data available yet.")











