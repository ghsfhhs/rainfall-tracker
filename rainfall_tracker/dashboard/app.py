import streamlit as st
import pandas as pd
import plotly.express as px
import os
import requests
from bs4 import BeautifulSoup
import re
from pytz import timezone
import datetime

# ========= Timezone =========
ist = timezone('Asia/Kolkata')
now = datetime.datetime.now(ist)
st.write("🕒 Current Time:", now.strftime("%Y-%m-%d %H:%M:%S"))

# ========= Fixed parameters for CEED =========
building_name = "CEED"
roof_area_m2 = 1000  # Change this to actual rooftop area
runoff_coeff = 0.85  # Metal surface typical coefficient

LOG_FILE = 'dashboard/rainfall_log.csv'

# ========= Fetch live weather =========
def fetch_live_weather():
    url = "https://iust.ac.in/"
    try:
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        pattern = r"Temperature[:\s]*([\d]+).*?C.*?Humidity[:\s]*([\d]+)%.*?Rainfall[:\s]*([\d]+)mm"
        m = re.search(pattern, text, re.DOTALL)
        if m:
            temp, hum, rain = m.groups()
            return int(temp), int(hum), int(rain)
    except:
        pass
    return None, None, 0

temp, hum, live_rainfall = fetch_live_weather()

# ========= Heading =========
st.title("Rainwater Harvesting Dashboard - IUST Campus")
st.subheader("Live Weather Data")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Temperature", f"{temp if temp else '-'} °C")
col2.metric("Humidity", f"{hum if hum else '-'} %")
col3.metric("Rainfall (Today)", f"{live_rainfall} mm")
col4.metric("Time", now.strftime("%d %b %Y %I:%M %p"))

# ========= Messages if files not found =========
if not os.path.exists(LOG_FILE):
    st.info("rainfall_log.csv not found. Starting with empty data.")

# ========= Calculate live harvesting =========
live_harvest = live_rainfall * roof_area_m2 * runoff_coeff  # litres

if live_rainfall == 0:
    st.warning("Rainfall data is empty. Showing live harvesting box with dashes.")

# ========= Live Harvesting Section =========
st.subheader("Live Harvesting")
colA, colB = st.columns(2)
colA.metric("Rainfall", f"{live_rainfall} mm" if live_rainfall else "-")
colB.metric("Today's Harvesting", f"{int(live_harvest)} L" if live_rainfall else "-")

# ========= Load or create log =========
if os.path.exists(LOG_FILE):
    df = pd.read_csv(LOG_FILE, parse_dates=['date'])
else:
    df = pd.DataFrame(columns=['date', 'building_name', 'rainfall_mm', 'water_harvested_litres'])

# ========= Add today's entry if missing =========
today_str = now.strftime("%Y-%m-%d")
if not ((df['date'] == today_str) & (df['building_name'] == building_name)).any():
    new_entry = pd.DataFrame({
        'date': [today_str],
        'building_name': [building_name],
        'rainfall_mm': [live_rainfall],
        'water_harvested_litres': [int(live_harvest)]
    })
    df = pd.concat([df, new_entry], ignore_index=True)
    df.to_csv(LOG_FILE, index=False)

# ========= Summary & Chart =========
df['date'] = pd.to_datetime(df['date'])
df['year'] = df['date'].dt.year
df['month'] = df['date'].dt.strftime('%b')
df['month_num'] = df['date'].dt.month

if not df.empty:
    selected_year = st.selectbox("Select Year", sorted(df['year'].unique(), reverse=True))
    year_df = df[(df['year'] == selected_year) & (df['building_name'] == building_name)]

    # Monthly summary
    month_df = year_df.groupby(['month', 'month_num'])[['rainfall_mm', 'water_harvested_litres']].sum().reset_index()
    month_df = month_df.sort_values('month_num')

    # Monthly Bar Chart
    st.write(f"### Monthly Water Harvesting for {building_name} in {selected_year}")
    fig1 = px.bar(month_df, x='month', y='water_harvested_litres',
                  title=f"Monthly Water Harvesting - {building_name} ({selected_year})",
                  color_discrete_sequence=["teal"])
    st.plotly_chart(fig1, use_container_width=True)

    # Daily Line Chart
    fig2 = px.line(year_df, x='date', y=['rainfall_mm', 'water_harvested_litres'],
                   labels={"value": "Amount", "variable": "Type"},
                   title=f"Daily Rainfall & Harvesting - {building_name} ({selected_year})")
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("Show Raw Data"):
        st.dataframe(year_df)

else:
    st.info("No historical rainfall data to display yet.")

# ========= Auto refresh =========
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=60000, limit=None, key="data_refresh")






