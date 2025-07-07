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
        df = df.dropna(subset=['date'])
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.strftime('%b')
        df['month_num'] = df['date'].dt.month
        df['building_name'] = df['building_name'].astype(str).str.strip().str.upper()
        return df
    else:
        return pd.DataFrame(columns=['date', 'building_name', 'rainfall_mm', 'water_harvested_litres'])

# ========== Save Log ==========
def save_log(df):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    df.to_csv(LOG_FILE, index=False)

# Load and prepare data
df = load_log()

# ========== Update Log with Today ==========
temp, hum, rain_today = fetch_live_weather()
if rain_today is None:
    st.warning("Live weather data unavailable. Using fallback value: 0 mm")
    rain_today = 0

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

# ========== TAB 1 ==========
with tab1:
    st.subheader("Live Harvesting - CEED Building")
    col1, col2 = st.columns(2)
    col1.metric("🌧️ Rainfall", f"{rain_today} mm")
    col2.metric("💧 Harvested", f"{int(calculate_harvest(rain_today))} L")

    df_building = df[df["building_name"] == BUILDING_NAME.upper()]

    if df_building.empty:
        st.warning("No data for CEED building.")
    else:
        selected_year = st.selectbox("Select Year", sorted(df_building["year"].unique(), reverse=True))
        year_df = df_building[df_building["year"] == selected_year]

        # Clean numeric data
        year_df["rainfall_mm"] = pd.to_numeric(year_df["rainfall_mm"], errors="coerce")
        year_df["water_harvested_litres"] = pd.to_numeric(year_df["water_harvested_litres"], errors="coerce")

        # Monthly aggregation
        monthly_summary = (
            year_df.groupby(["month", "month_num"])[["rainfall_mm", "water_harvested_litres"]]
            .sum()
            .reset_index()
            .sort_values("month_num")
        )

        st.write(f"### 📊 Monthly Harvesting - {selected_year}")
        fig = px.bar(
            monthly_summary,
            x="month",
            y="water_harvested_litres",
            title="Monthly Water Harvested",
            color_discrete_sequence=["teal"]
        )
        st.plotly_chart(fig, use_container_width=True)

        fig2 = px.line(
            year_df,
            x="date",
            y=["rainfall_mm", "water_harvested_litres"],
            labels={"value": "Amount", "variable": "Type"},
            title="Daily Trends",
        )
        st.plotly_chart(fig2, use_container_width=True)

# ========== TAB 2 ==========
with tab2:
    st.header("📅 Year Wise Water Harvesting Summary")

    df_building = df[df["building_name"] == BUILDING_NAME.upper()]

    # Yearly summary
    year_summary = (
        df_building.groupby("year")[["water_harvested_litres"]]
        .sum()
        .reset_index()
        .sort_values("year")
    )

    st.subheader("💧 Total Water Harvested by Year")
    st.dataframe(
        year_summary.rename(columns={
            "year": "Year",
            "water_harvested_litres": "Total (Litres)"
        }),
        use_container_width=True
    )

    # Monthly breakdown
    selected_year = st.selectbox("📌 Select Year to View Monthly", year_summary["year"])


    monthly = (
        df_building[df_building["year"] == selected_year]
        .groupby(["month", "month_num"])[["rainfall_mm", "water_harvested_litres"]]
        .sum()
        .reset_index()
        .sort_values("month_num")
    )

    st.subheader(f"📆 Monthly Harvesting for {selected_year}")
    st.dataframe(
        monthly.rename(columns={
            "month": "Month",
            "rainfall_mm": "Rainfall (mm)",
            "water_harvested_litres": "Harvested (Litres)"
        }),
        use_container_width=True
    )










