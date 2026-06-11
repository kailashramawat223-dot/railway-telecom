from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
import sqlite3
import os
from qr_generator import generate_qr_image
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'railway_telecom_secret_2024'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database', 'railway.db')
QR_DIR = os.path.join(BASE_DIR, 'qr_codes')

os.makedirs(QR_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'database'), exist_ok=True)

# ── Database ──────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS assets (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id        TEXT    UNIQUE NOT NULL,
            asset_name      TEXT    NOT NULL,
            asset_type      TEXT    NOT NULL,
            station_name    TEXT    NOT NULL,
            installation_date TEXT,
            status          TEXT    NOT NULL DEFAULT 'Working',
            qr_path         TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS maintenance (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id         TEXT    NOT NULL,
            maintenance_date TEXT    NOT NULL,
            engineer_name    TEXT    NOT NULL,
            description      TEXT    NOT NULL,
            remarks          TEXT,
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE
        );
        """)
    print("Database initialised.")

# ── Auth ──────────────────────────────────────────────────────────────────────

ADMIN_USER = 'admin'
ADMIN_PASS = 'admin123'

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ── QR Code ───────────────────────────────────────────────────────────────────

def generate_qr(asset_id):
    data = f'/asset/{asset_id}'
    img = generate_qr_image(data, fill=(26, 39, 68), back=(255, 255, 255), box=10, border=4)
    filename = f'qr_{asset_id}.png'
    path = os.path.join(QR_DIR, filename)
    img.save(path)
    return filename

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USER and request.form['password'] == ADMIN_PASS:
            session['logged_in'] = True
            session['username'] = ADMIN_USER
            flash('Welcome back, Administrator!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials. Please try again.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    with get_db() as conn:
        total   = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
        working = conn.execute("SELECT COUNT(*) FROM assets WHERE status='Working'").fetchone()[0]
        faulty  = conn.execute("SELECT COUNT(*) FROM assets WHERE status='Faulty'").fetchone()[0]
        maint   = conn.execute("SELECT COUNT(*) FROM assets WHERE status='Under Maintenance'").fetchone()[0]

        type_rows = conn.execute(
            "SELECT asset_type, COUNT(*) as cnt FROM assets GROUP BY asset_type"
        ).fetchall()
        station_rows = conn.execute(
            "SELECT station_name, COUNT(*) as cnt FROM assets GROUP BY station_name ORDER BY cnt DESC LIMIT 8"
        ).fetchall()
        recent = conn.execute(
            "SELECT a.asset_name, a.asset_type, a.station_name, m.maintenance_date, m.engineer_name "
            "FROM maintenance m JOIN assets a ON m.asset_id=a.asset_id "
            "ORDER BY m.created_at DESC LIMIT 5"
        ).fetchall()
        new_assets = conn.execute(
            "SELECT asset_id, asset_name, asset_type, station_name, status, created_at "
            "FROM assets ORDER BY created_at DESC LIMIT 5"
        ).fetchall()

    stats = {'total': total, 'working': working, 'faulty': faulty, 'maintenance': maint}
    type_labels  = [r['asset_type'] for r in type_rows]
    type_counts  = [r['cnt']        for r in type_rows]
    stn_labels   = [r['station_name'] for r in station_rows]
    stn_counts   = [r['cnt']          for r in station_rows]
    return render_template('dashboard.html', stats=stats,
                           type_labels=type_labels, type_counts=type_counts,
                           stn_labels=stn_labels, stn_counts=stn_counts,
                           recent=recent, new_assets=new_assets)

# Asset list
@app.route('/assets')
@login_required
def assets():
    search  = request.args.get('search', '')
    station = request.args.get('station', '')
    status  = request.args.get('status', '')
    with get_db() as conn:
        query  = "SELECT * FROM assets WHERE 1=1"
        params = []
        if search:
            query += " AND (asset_id LIKE ? OR asset_name LIKE ? OR station_name LIKE ?)"
            params += [f'%{search}%', f'%{search}%', f'%{search}%']
        if station:
            query += " AND station_name=?"
            params.append(station)
        if status:
            query += " AND status=?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        rows     = conn.execute(query, params).fetchall()
        stations = conn.execute("SELECT DISTINCT station_name FROM assets ORDER BY station_name").fetchall()
    return render_template('assets.html', assets=rows, stations=stations,
                           search=search, sel_station=station, sel_status=status)

# Add asset
@app.route('/assets/add', methods=['GET', 'POST'])
@login_required
def add_asset():
    if request.method == 'POST':
        asset_id   = request.form['asset_id'].strip()
        asset_name = request.form['asset_name'].strip()
        asset_type = request.form['asset_type']
        station    = request.form['station_name'].strip()
        inst_date  = request.form['installation_date']
        status     = request.form['status']
        with get_db() as conn:
            exists = conn.execute("SELECT id FROM assets WHERE asset_id=?", (asset_id,)).fetchone()
            if exists:
                flash(f'Asset ID "{asset_id}" already exists.', 'danger')
                return render_template('add_asset.html')
            qr_file = generate_qr(asset_id)
            conn.execute(
                "INSERT INTO assets (asset_id,asset_name,asset_type,station_name,installation_date,status,qr_path) "
                "VALUES (?,?,?,?,?,?,?)",
                (asset_id, asset_name, asset_type, station, inst_date, status, qr_file)
            )
        flash(f'Asset "{asset_name}" added successfully with QR code!', 'success')
        return redirect(url_for('assets'))
    return render_template('add_asset.html')

# Edit asset
@app.route('/assets/edit/<asset_id>', methods=['GET', 'POST'])
@login_required
def edit_asset(asset_id):
    with get_db() as conn:
        asset = conn.execute("SELECT * FROM assets WHERE asset_id=?", (asset_id,)).fetchone()
        if not asset:
            flash('Asset not found.', 'danger')
            return redirect(url_for('assets'))
        if request.method == 'POST':
            conn.execute(
                "UPDATE assets SET asset_name=?,asset_type=?,station_name=?,installation_date=?,status=? "
                "WHERE asset_id=?",
                (request.form['asset_name'], request.form['asset_type'],
                 request.form['station_name'], request.form['installation_date'],
                 request.form['status'], asset_id)
            )
            flash('Asset updated successfully.', 'success')
            return redirect(url_for('view_asset', asset_id=asset_id))
    return render_template('edit_asset.html', asset=asset)

# Delete asset
@app.route('/assets/delete/<asset_id>', methods=['POST'])
@login_required
def delete_asset(asset_id):
    with get_db() as conn:
        asset = conn.execute("SELECT * FROM assets WHERE asset_id=?", (asset_id,)).fetchone()
        if asset and asset['qr_path']:
            qr_path = os.path.join(QR_DIR, asset['qr_path'])
            if os.path.exists(qr_path):
                os.remove(qr_path)
        conn.execute("DELETE FROM assets WHERE asset_id=?", (asset_id,))
    flash('Asset deleted successfully.', 'success')
    return redirect(url_for('assets'))

# View asset
@app.route('/asset/<asset_id>')
@login_required
def view_asset(asset_id):
    with get_db() as conn:
        asset = conn.execute("SELECT * FROM assets WHERE asset_id=?", (asset_id,)).fetchone()
        if not asset:
            flash('Asset not found.', 'danger')
            return redirect(url_for('assets'))
        history = conn.execute(
            "SELECT * FROM maintenance WHERE asset_id=? ORDER BY maintenance_date DESC",
            (asset_id,)
        ).fetchall()
    return render_template('view_asset.html', asset=asset, history=history)

# Maintenance – add
@app.route('/maintenance/add/<asset_id>', methods=['POST'])
@login_required
def add_maintenance(asset_id):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO maintenance (asset_id,maintenance_date,engineer_name,description,remarks) "
            "VALUES (?,?,?,?,?)",
            (asset_id, request.form['maintenance_date'],
             request.form['engineer_name'], request.form['description'],
             request.form.get('remarks', ''))
        )
        # Auto-update status to Under Maintenance
        conn.execute("UPDATE assets SET status='Under Maintenance' WHERE asset_id=?", (asset_id,))
    flash('Maintenance record added.', 'success')
    return redirect(url_for('view_asset', asset_id=asset_id))

# Maintenance list
@app.route('/maintenance')
@login_required
def maintenance():
    with get_db() as conn:
        records = conn.execute(
            "SELECT m.*, a.asset_name, a.station_name, a.asset_type "
            "FROM maintenance m JOIN assets a ON m.asset_id=a.asset_id "
            "ORDER BY m.maintenance_date DESC"
        ).fetchall()
        assets = conn.execute("SELECT asset_id, asset_name FROM assets ORDER BY asset_name").fetchall()
    return render_template('maintenance.html', records=records, assets=assets)

# Reports
@app.route('/reports')
@login_required
def reports():
    with get_db() as conn:
        total   = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
        working = conn.execute("SELECT COUNT(*) FROM assets WHERE status='Working'").fetchone()[0]
        faulty  = conn.execute("SELECT COUNT(*) FROM assets WHERE status='Faulty'").fetchone()[0]
        maint   = conn.execute("SELECT COUNT(*) FROM assets WHERE status='Under Maintenance'").fetchone()[0]

        type_rows    = conn.execute("SELECT asset_type, COUNT(*) as cnt FROM assets GROUP BY asset_type").fetchall()
        station_rows = conn.execute("SELECT station_name, COUNT(*) as cnt FROM assets GROUP BY station_name ORDER BY cnt DESC").fetchall()
        status_rows  = conn.execute("SELECT status, COUNT(*) as cnt FROM assets GROUP BY status").fetchall()
        maint_rows   = conn.execute(
            "SELECT strftime('%Y-%m', maintenance_date) as month, COUNT(*) as cnt "
            "FROM maintenance GROUP BY month ORDER BY month DESC LIMIT 12"
        ).fetchall()

    return render_template('reports.html',
        total=total, working=working, faulty=faulty, maintenance=maint,
        type_labels=[r['asset_type']    for r in type_rows],
        type_counts=[r['cnt']           for r in type_rows],
        stn_labels =[r['station_name']  for r in station_rows],
        stn_counts =[r['cnt']           for r in station_rows],
        status_labels=[r['status']      for r in status_rows],
        status_counts=[r['cnt']         for r in status_rows],
        maint_months=[r['month']        for r in maint_rows],
        maint_counts=[r['cnt']          for r in maint_rows],
    )

# Serve QR images
@app.route('/qr_codes/<filename>')
@login_required
def qr_image(filename):
    return send_from_directory(QR_DIR, filename)

# API: quick stats for AJAX refresh
@app.route('/api/stats')
@login_required
def api_stats():
    with get_db() as conn:
        total   = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
        working = conn.execute("SELECT COUNT(*) FROM assets WHERE status='Working'").fetchone()[0]
        faulty  = conn.execute("SELECT COUNT(*) FROM assets WHERE status='Faulty'").fetchone()[0]
        maint   = conn.execute("SELECT COUNT(*) FROM assets WHERE status='Under Maintenance'").fetchone()[0]
    return jsonify(total=total, working=working, faulty=faulty, maintenance=maint)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
