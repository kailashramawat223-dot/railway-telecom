# 🚆 Smart Railway Telecom Asset Management System
### with QR Code Integration

A professional web application for Railway Telecom Department to manage telecom assets
such as routers, switches, OFC cables, battery banks, PA systems, and communication
equipment installed at railway stations.

---

## ✨ Features

| Module | Description |
|---|---|
| **Dashboard** | Live stats, Chart.js analytics, recent activity |
| **Asset Management** | Add / Edit / Delete / View assets with full details |
| **QR Code Integration** | Auto-generates QR code for every asset on save |
| **Asset Listing** | Searchable, filterable table with status badges |
| **Maintenance Module** | Add maintenance records, view full history |
| **Reports** | Status distribution, station-wise counts, maintenance trends |

---

## 📁 Project Structure

```
railway_telecom/
├── app.py                 ← Flask application (all routes + logic)
├── qr_generator.py        ← Pure-Python QR code generator (no pip needed)
├── seed_data.py           ← Populate DB with 15 sample assets
├── requirements.txt       ← Python dependencies
├── database/
│   └── railway.db         ← SQLite database (auto-created)
├── qr_codes/              ← Generated QR code PNG images
├── templates/
│   ├── base.html          ← Shared layout (navbar + sidebar)
│   ├── login.html         ← Login page
│   ├── dashboard.html     ← Dashboard with charts
│   ├── assets.html        ← Asset list with search/filter
│   ├── add_asset.html     ← Add new asset form
│   ├── edit_asset.html    ← Edit asset form
│   ├── view_asset.html    ← Asset details + QR + maintenance
│   ├── maintenance.html   ← All maintenance records
│   └── reports.html       ← Analytics and reports
└── static/
    ├── css/style.css      ← Railway-themed dark UI stylesheet
    └── js/main.js         ← Animations, mobile nav, UX helpers
```

---

## ⚙️ Installation

### Prerequisites
- Python 3.8+
- pip

### Step 1 — Install dependencies

```bash
pip install Flask Pillow
```

> **Note:** The QR code generator (`qr_generator.py`) is included as pure Python
> and only requires Pillow (image saving). No `qrcode` package needed.

### Step 2 — Run the application

```bash
python app.py
```

The app starts at **http://127.0.0.1:5000**

### Step 3 (Optional) — Load sample data

```bash
python seed_data.py
```

This inserts 15 sample assets across 7 stations with 6 maintenance records.

---

## 🔐 Login Credentials

| Field | Value |
|---|---|
| Username | `admin` |
| Password | `admin123` |

---

## 🗄️ Database Schema

### `assets` table
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Auto-increment PK |
| asset_id | TEXT | Unique asset identifier (e.g. RTL-NDLS-001) |
| asset_name | TEXT | Human-readable name |
| asset_type | TEXT | Router / Switch / OFC Cable / Battery Bank / PA System / Communication Equipment |
| station_name | TEXT | Railway station |
| installation_date | TEXT | ISO date |
| status | TEXT | Working / Faulty / Under Maintenance |
| qr_path | TEXT | QR image filename in qr_codes/ |
| created_at | TIMESTAMP | Auto |

### `maintenance` table
| Column | Type | Description |
|---|---|---|
| id | INTEGER | Auto-increment PK |
| asset_id | TEXT | FK → assets.asset_id |
| maintenance_date | TEXT | ISO date |
| engineer_name | TEXT | Name of engineer |
| description | TEXT | Work description |
| remarks | TEXT | Optional notes |
| created_at | TIMESTAMP | Auto |

---

## 🎨 Technology Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, Bootstrap 5.3, Bootstrap Icons |
| Typography | Inter (Google Fonts), JetBrains Mono |
| Charts | Chart.js 4.4 |
| Backend | Python Flask 3.x |
| Database | SQLite 3 |
| QR Codes | Custom pure-Python generator + Pillow |

---

## 📱 Responsive Design

The application is fully responsive:
- Desktop: sidebar + main content layout
- Mobile: collapsible sidebar, stacked stat cards

---

## 🚀 Production Deployment

For production, use Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

*Developed for Indian Railways · Telecom Department Internship Project*
