# rainfall-tracker
# 🌧️ Rainfall Tracker - Automated Rainwater Harvesting System

This project tracks daily rainfall using scraped weather data, calculates rainwater harvesting per building based on rooftop area, and shows it in an interactive dashboard with QR code access.

## 📁 Features
- Automatic rainfall logging from IUST website
- Calculates harvested water per building
- Generates QR codes for building-wise dashboard
- Interactive dashboard with graphs and download
- Easy deployment with Streamlit

## 🚀 Getting Started
1. Clone this repo
2. Run `pip install -r requirements.txt`
3. Add rooftop data in `data/buildings.csv`
4. Run `scripts/rainfall_tracker.py` to log rainfall
5. Launch dashboard with `streamlit run dashboard/app.py`

