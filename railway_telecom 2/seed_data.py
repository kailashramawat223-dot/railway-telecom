"""
seed_data.py — Populate the database with realistic sample data
Run: python seed_data.py
"""
import sqlite3, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import init_db, generate_qr, DB_PATH

ASSETS = [
    ("RTL-NDLS-001","Core Router NDLS","Router","New Delhi","2022-03-15","Working"),
    ("RTL-NDLS-002","Edge Switch A","Switch","New Delhi","2022-04-01","Working"),
    ("RTL-NDLS-003","OFC Cable Main","OFC Cable","New Delhi","2021-12-10","Working"),
    ("RTL-NDLS-004","Battery Bank #1","Battery Bank","New Delhi","2023-01-20","Under Maintenance"),
    ("RTL-NDLS-005","PA System Hall","PA System","New Delhi","2022-08-05","Working"),
    ("RTL-MUM-001","Core Router Mumbai","Router","Mumbai Central","2022-05-11","Working"),
    ("RTL-MUM-002","Distribution Switch","Switch","Mumbai Central","2023-02-14","Faulty"),
    ("RTL-MUM-003","Battery Bank B","Battery Bank","Mumbai Central","2022-11-30","Working"),
    ("RTL-HWH-001","Howrah Main Router","Router","Howrah","2021-09-20","Working"),
    ("RTL-HWH-002","OFC Cable Ring","OFC Cable","Howrah","2022-06-18","Working"),
    ("RTL-CHN-001","Chennai Router","Router","Chennai Central","2023-03-01","Working"),
    ("RTL-CHN-002","CCTV Comm Equip","Communication Equipment","Chennai Central","2022-10-10","Faulty"),
    ("RTL-BLR-001","Bengaluru Core SW","Switch","Bengaluru","2023-04-15","Working"),
    ("RTL-BLR-002","PA System PF1","PA System","Bengaluru","2022-07-22","Under Maintenance"),
    ("RTL-JPR-001","Jaipur Router","Router","Jaipur","2023-05-10","Working"),
]

MAINTENANCE = [
    ("RTL-NDLS-004","2024-01-10","Rajesh Kumar","Battery cells replaced, capacity restored to 100%","Scheduled annual replacement"),
    ("RTL-MUM-002","2024-02-05","Amit Sharma","Port 24 faulty — replaced SFP module","Vendor called"),
    ("RTL-BLR-002","2024-03-12","Srinivas Rao","PA amplifier board replaced","Under warranty"),
    ("RTL-NDLS-001","2023-11-20","Priya Singh","Firmware upgraded to v14.2","No downtime"),
    ("RTL-HWH-001","2023-12-18","Debangshu Das","Cooling fan replaced","Preventive maintenance"),
    ("RTL-CHN-002","2024-01-28","Meenakshi R","CCTV recorder HDD replaced","Old HDD failed — SMART alert"),
]

def seed():
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM maintenance")
        conn.execute("DELETE FROM assets")

        for row in ASSETS:
            asset_id = row[0]
            qr_file  = generate_qr(asset_id)
            conn.execute(
                "INSERT INTO assets (asset_id,asset_name,asset_type,station_name,installation_date,status,qr_path) VALUES (?,?,?,?,?,?,?)",
                (*row, qr_file)
            )

        for row in MAINTENANCE:
            conn.execute(
                "INSERT INTO maintenance (asset_id,maintenance_date,engineer_name,description,remarks) VALUES (?,?,?,?,?)",
                row
            )

    print(f"✓ Seeded {len(ASSETS)} assets and {len(MAINTENANCE)} maintenance records.")

if __name__ == '__main__':
    seed()
