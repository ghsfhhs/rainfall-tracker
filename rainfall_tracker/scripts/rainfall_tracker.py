import requests
from bs4 import BeautifulSoup
import csv
import datetime
import os

BUILDING_FILE = '../data/buildings.csv'
LOG_FILE = '../data/rainfall_log.csv'
IUST_URL = "https://www.iust.ac.in"

def get_today_rainfall_mm():
    response = requests.get(IUST_URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    text = soup.get_text()
    for line in text.splitlines():
        if 'Rainfall' in line and 'mm' in line:
            parts = line.strip().split()
            try:
                mm = float(parts[1])
                return mm
            except:
                continue
    raise ValueError("Rainfall data not found")

def read_buildings():
    with open(BUILDING_FILE, 'r') as f:
        reader = csv.DictReader(f)
        return list(reader)

def write_log(date, building_data, rainfall_mm):
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["date", "building_name", "rainfall_mm", "water_harvested_litres"])
        for b in building_data:
            area = float(b['area_m2'])
            coeff = float(b['runoff_coefficient'])
            harvested = rainfall_mm * area * coeff
            writer.writerow([date, b['building_name'], rainfall_mm, round(harvested, 2)])

def main():
    today = datetime.date.today().isoformat()
    rainfall = get_today_rainfall_mm()
    buildings = read_buildings()
    write_log(today, buildings, rainfall)
    print(f"Logged rainfall: {rainfall} mm for {len(buildings)} buildings.")

if __name__ == "__main__":
    main()
