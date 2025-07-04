import streamlit as st
import pandas as pd
import plotly.express as px
import os
import requests
from bs4 import BeautifulSoup
import re
from pytz import timezone
import datetime

# ========= CEED building fixed parameters =========
ROOFTOP_AREA = 500   # in m² (change as needed)
RUNOFF_COEFF = 0.85 # for metal roof (can adjust)

# ========= Timezone =========
ist = timezone('Asia/Kolkata')
now = datetime.datetime.now(ist)
today_str = now.strftime("%Y-%m-%d")
st.write("🕒 Current Time:", now.strftime("%Y-%m-%d %H:%M:%S"))

# ========= File =========
LOG_FILE = 'rainfall_log.csv'

# ========= Fetch live weather =========
def fetch_live_weather():
    url = "https://iust.ac.in/"
    try:
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)

        pattern = r"Temperature[:\s]*(\d+).*?C.*?Humidity[:\s]*(\d+).*?%.*?Rainfall[:\s]*(\d+).*?mm"
        m = re.search(pattern, text, re.DOTALL)
        if m:
            temp, hum, rain = m.groups()
            return int(temp), int(hum), int(rain)
        else:
            return None, None, None
    except:
        return None, None, None

# ========= Load data =========
if os.path.exists(LOG_FILE):
    df = pd.read_csv(LOG_FILE)
else:
    df = pd.DataFrame(columns=["date", "rainfall_mm", "water_harvested_litres"])

# ========= Get live data =========
temp, hum, rain_today = fetch_live_weather()

# ========= Calculate harvesting =========
if rain_today is not None:
    harvested_today = rain_today * ROOFTOP_AREA * RUNOFF_COEFF
    harvested_today = round(harvested_today, 2)
else:
    harvested_today = "-"

# ========= Display metrics =========
col1, col2, col3, col4 = st.columns(4)
col1.metric("Temperature", f"{temp} °C" if temp is not None else "-")
col2.metric("Humidity", f"{hum} %" if hum is not None else "-")
col3.metric("Rainfall Today", f"{rain_today} mm" if rain_today is not None else "-")
col4.metric("Harvesting Today", f"{harvested_today} L" if harvested_today != "-" else "-")

# ========= Save today's data if not already saved =========
if rain_today is not None:
    # Check if today's data already exists
    if today_str not in df['date'].values:
        new_row = pd.DataFrame([[today_str, rain_today, harvested_today]],
                               columns=["date", "rainfall_mm", "water_harvested_litres"])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(LOG_FILE, index=False)

# ========= Show historical analysis =========
if not df.empty:
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year
    years = sorted(df['year'].unique(), reverse=True)
    selected_year = st.selectbox("Select Year", years)

    year_df = df[df['year'] == selected_year]
    year_df['month'] = year_df['date'].dt.strftime('%b')
    year_df['month_num'] = year_df['date'].dt.month

    month_df = year_df.groupby(['month', 'month_num'])[['rainfall_mm', 'water_harvested_litres']].sum().reset_index()
    month_df = month_df.sort_values('month_num')

    st.write(f"### Monthly Harvesting for CEED ({selected_year})")
    st.table(month_df[['month', 'rainfall_mm', 'water_harvested_litres']].rename(
        columns={"rainfall_mm": "Total Rainfall (mm)", "water_harvested_litres": "Total Harvesting (L)"}))

    fig1 = px.bar(month_df, x='month', y='water_harvested_litres',
                  title=f"Monthly Water Harvesting - CEED ({selected_year})",
                  color_discrete_sequence=['teal'])
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.line(year_df, x='date', y=['rainfall_mm', 'water_harvested_litres'],
                   labels={"value": "Amount", "variable": "Type"},
                   title=f"Daily Rainfall & Harvesting - CEED ({selected_year})")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Download CEED Data")
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download as CSV", data=csv, file_name='ceed_rainfall_data.csv', mime='text/csv')

    with st.expander("Show Raw Data"):
        st.dataframe(df)

else:
    st.info("No historical data available yet.")

# ========= Optional: Refresh every 10 minutes =========
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=10 * 60 * 1000, limit=None, key="refresh")





