import pandas as pd
import qrcode
import os

BUILDINGS_CSV = '../data/buildings.csv'
QR_DIR = '../data/qr_codes/'
BASE_URL = 'http://localhost:8501/?building='

os.makedirs(QR_DIR, exist_ok=True)

df = pd.read_csv(BUILDINGS_CSV)
for _, row in df.iterrows():
    building = row['building_name']
    url = f"{BASE_URL}{building.replace(' ', '%20')}"
    img = qrcode.make(url)
    img.save(os.path.join(QR_DIR, f"{building}.png"))

print("QR codes generated in /data/qr_codes/")
