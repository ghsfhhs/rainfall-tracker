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

# ========== Timezone ==========
ist = timezone('Asia/Kolkata')
now = datetime.datetime.now(ist)
st.write("🕒 Current Time:", now.strftime("%Y-%m-%d %H:%M:%S"))

LOG_FILE = 'rainfall_log.csv'
BUILDING_FILE = 'buildings.csv'

# ========== Fetch Live Weather ==========
def fetch_live_weather():
    url = "https://iust.ac.in/"
    try:
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)

        # Debug: print text to see structure
        # st.text(text[:2000])

        pattern = r"Temperature[:\s]*(\d+)\s*°C.*?Humidity[:\s]*(\d+)\s*%.*?Rainfall[:\s]*(\d+)\s*mm"
        m = re.search(pattern, text, re.DOTALL)
        if m:
            temp, hum, rain = m.groups()
            now = datetime.datetime.now(ist).strftime("%d %b %Y %I:%M %p")
            return {
                "timestamp": now,
                "temperature": f"{temp} °C",
                "humidity": f"{hum} %",
                "rainfall": f"{rain} mm"
            }
        else:
            st.warning("Weather data pattern not matched. Check website structure.")

    except Exception as e:
        st.warning(f"Error fetching weather: {e}")

    now = datetime.datetime.now(ist).strftime("%d %b %Y %I:%M %p")
    return {"timestamp": now, "temperature": "-", "humidity": "-", "rainfall": "-"}

# ========== Load Data ==========
@st.cache_data
def load_data():
    if os.path.exists(LOG_FILE):
        df = pd.read_csv(LOG_FILE, parse_dates=["date"])
    else:
        st.info("rainfall_log.csv not found. Starting with empty data.")
        df = pd.DataFrame(columns=["date", "building_name", "rainfall_mm", "water_harvested_litres"])

    if os.path.exists(BUILDING_FILE):
        buildings = pd.read_csv(BUILDING_FILE)
    else:
        st.info("buildings.csv not found. Building list will be empty.")
        buildings = pd.DataFrame(columns=["building_name"])

    return df, buildings

# ========== Page Config ==========
st.set_page_config(page_title="Campus Rainwater Harvesting", layout="wide")
st_autorefresh(interval=60000, key="datarefresh")

st.title("Rainwater Harvesting Dashboard - IUST Campus")

# ========== Live Weather Data ==========
st.subheader("Live Weather Data")
live = fetch_live_weather()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Temperature", live["temperature"])
col2.metric("Humidity", live["humidity"])
col3.metric("Rainfall (Today)", live["rainfall"])
col4.metric("Time", live["timestamp"])

# ========== Load Data ==========
df, buildings = load_data()

if df.empty:
    st.warning("Rainfall data is empty. Please upload or check the file.")
    st.stop()

building_list = sorted(df["building_name"].unique())
building = st.selectbox("Select Building", building_list)
building_df = df[df["building_name"] == building]

# ========== Live Harvesting Section ==========
st.subheader("Live Harvesting")

total_water = building_df["water_harvested_litres"].sum()

if live["rainfall"] != "-" and live["rainfall"] != "0 mm":
    rainfall_value = live["rainfall"]
    harvesting_value = f"{total_water:,.0f} L"
else:
    rainfall_value = "-"
    harvesting_value = "-"

colA, colB = st.columns(2)
colA.metric("Rainfall", rainfall_value)
colB.metric("Total Harvesting", harvesting_value)

# ========== Year-wise Harvesting ==========
st.subheader("Year-wise Harvesting")
building_df["year"] = building_df["date"].dt.year
year_list = sorted(building_df["year"].unique(), reverse=True)
selected_year = st.selectbox("Select Year", year_list)

year_df = building_df[building_df["year"] == selected_year]
year_df["month"] = year_df["date"].dt.strftime("%b")
monthly = year_df.groupby("month")[["rainfall_mm", "water_harvested_litres"]].sum().reset_index()

# Monthly table
monthly_table = monthly[["month", "water_harvested_litres"]].rename(columns={"water_harvested_litres": "Total Harvesting (L)"})
st.table(monthly_table)

# Monthly bar chart
fig1 = px.bar(monthly, x="month", y="water_harvested_litres",
              title="Monthly Water Harvested",
              labels={"water_harvested_litres": "Litres"},
              color_discrete_sequence=["teal"])
st.plotly_chart(fig1, use_container_width=True)

# Daily line chart
fig2 = px.line(year_df, x="date", y=["rainfall_mm", "water_harvested_litres"],
               labels={"value": "Amount", "variable": "Type"},
               title="Daily Rainfall & Harvesting")
st.plotly_chart(fig2, use_container_width=True)

# ========== Compare Buildings ==========
st.subheader("Compare Buildings")
compare_df = df.groupby("building_name")[["rainfall_mm", "water_harvested_litres"]].sum().reset_index()
fig3 = px.bar(compare_df, x="building_name", y="water_harvested_litres",
              title="Total Water Harvested by Building",
              labels={"water_harvested_litres": "Litres"},
              color_discrete_sequence=["indianred"])
st.plotly_chart(fig3, use_container_width=True)

# ========== Download ==========
st.subheader("Download Building Data")
csv = building_df.to_csv(index=False).encode('utf-8')
st.download_button("Download as CSV", data=csv, file_name=f"{building}_rainfall_data.csv", mime='text/csv')

with st.expander("Show Raw Data"):
    st.dataframe(building_df)




