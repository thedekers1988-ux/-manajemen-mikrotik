import os
import json
import time
import threading
from datetime import datetime
from flask import Flask, request, redirect, url_for, render_template_string, flash
from routeros_api import RouterOsApiPool

app = Flask(__name__)
app.secret_key = "mikrotik-management-local-key"

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

ROUTERS_FILE = os.path.join(DATA_DIR, "routers.json")
CUSTOMERS_FILE = os.path.join(DATA_DIR, "customers.json")
STATE_FILE = os.path.join(DATA_DIR, "state.json")

def read_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default

def write_json(path, data):
    temp = path + ".tmp"
    with open(temp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(temp, path)

def routers():
    return read_json(ROUTERS_FILE, [])

def customers():
    return read_json(CUSTOMERS_FILE, [])

def states():
    return read_json(STATE_FILE, {})

def save_customers(data):
    write_json(CUSTOMERS_FILE, data)

def save_states(data):
    write_json(STATE_FILE, data)

def connect_router(router):
    pool = RouterOsApiPool(
        router["host"],
        username=router["username"],
        password=router["password"],
        port=int(router.get("port", 8728)),
        plaintext_login=True
    )
    return pool

def fetch_router(router):
    pool = None
    try:
        pool = connect_router(router)
        api = pool.get_api()
        active = api.get_resource("/ppp/active").get()
        secrets = api.get_resource("/ppp/secret").get()
        return active, secrets, "Terhubung"
    except Exception as e:
        return [], [], "Gagal: " + str(e)
    finally:
        if pool:
            try:
                pool.disconnect()
            except Exception:
                pass

def update_monitor():
    """Mencatat perubahan status dan penghitung trafik saat aplikasi dibuka."""
    all_routers = routers()
    all_customers = customers()
    state = states()
    now = time.time()

    for index, router in enumerate(all_routers):
        active, secret_list, status = fetch_router(router)
        router_id = str(index)

        state.setdefault(router_id, {})
        state[router_id]["router_status"] = status

        active_by_name = {
            item.get("name"): item for item in active
        }

        for secret in secret_list:
            username = secret.get("name", "")
            if not username:
                continue

            key = router_id + ":" + username
            old = state[router_id].get(username, {})
            current = username in active_by_name

            if current and not old.get("online", False):
                old["online_since"] = now
                old["offline_since"] = None

            if not current and old.get("online", False):
                old["offline_since"] = now

            old["online"] = current

            if current:
                session = active_by_name[username]
                rx = int(session.get("bytes-in", 0) or 0)
                tx = int(session.get("bytes-out", 0) or 0)
                previous = old.get("traffic", {})
                old_rx = int(previous.get("rx", 0))
                old_tx = int(previous.get("tx", 0))

                # Tambahkan selisih trafik, termasuk jika sesi PPPoE tersambung ulang.
                if rx >= old_rx:
                    old["month_rx"] = int(old.get("month_rx", 0)) + rx - old_rx
                else:
                    old["month_rx"] = int(old.get("month_rx", 0)) + rx

                if tx >= old_tx:
                    old["month_tx"] = int(old.get("month_tx", 0)) + tx - old_tx
                else:
                    old["month_tx"] = int(old.get("month_tx", 0)) + tx

                old["traffic"] = {"rx": rx, "tx": tx}
                old["last_seen"] = now

            state[router_id][username] = old

            found = next(
                (c for c in all_customers
                 if c.get("router") == router_id and c.get("username") == username),
                None
            )

            if found:
                found["ip"] = active_by_name.get(username, {}).get("address", found.get("ip", ""))
                found["profile"] = secret.get("profile", "")
                found["online"] = current
            else:
                all_customers.append({
                    "router": router_id,
                    "username": username,
                    "ip": active_by_name.get(username, {}).get("address", ""),
                    "profile": secret.get("profile", ""),
                    "phone": "",
                    "coordinates": "",
                    "payment": "Belum Lunas",
                    "online": current
                })

    save_states(state)
    save_customers(all_customers)
    write_json(ROUTERS_FILE, all_routers)

def get_data():
    update_monitor()
    all_customers = customers()
    state = states()
    all_routers = routers()

    online = []
    offline = []
    for c in all_customers:
        rid = str(c.get("router", "0"))
        username = c.get("username", "")
        info = state.get(rid, {}).get(username, {})
        item = dict(c)
        item["online"] = bool(info.get("online", False))
        item["offline_time"] = info.get("offline_since")
        item["month_rx"] = info.get("month_rx", 0)
        item["month_tx"] = info.get("month_tx", 0)

        if item["online"]:
            online.append(item)
        else:
            offline.append(item)

    return all_customers, online, offline, all_routers

BASE = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Manajemen MikroTik</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#031329;color:#f1f7ff;font-family:Arial,sans-serif}
header{background:#082b58;padding:20px 16px;border-bottom:2px solid #087cff}
header h2{margin:0;color:white}
header small{color:#a9cfff}
main{padding:14px;max-width:1000px;margin:auto;padding-bottom:35px}
nav{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}
nav a,.btn{background:#0757a7;color:white;padding:11px 13px;border-radius:10px;text-decoration:none;border:0;display:inline-block}
.card{background:#092447;border:1px solid #15558b;border-radius:14px;padding:15px;margin-bottom:13px}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.stat{font-size:28px;font-weight:bold;margin-top:8px}
.green{color:#32e99b}.red{color:#ff647c}.blue{color:#62baff}
input,select{width:100%;padding:12px;margin:6px 0 12px;border-radius:8px;border:1px solid #3278b6;background:#061a34;color:white}
label{color:#bcdcff;font-size:14px}
button{cursor:pointer}
table{width:100%;border-collapse:collapse}
td,th{text-align:left;padding:11px 6px;border-bottom:1px solid #1b426b;font-size:14px}
.small{font-size:12px;color:#a9c6e5}
.badge{padding:5px 8px;border-radius:20px;background:#087b55;color:white;font-size:12px}
.badge.red{background:#a82043;color:white}
.btn-green{background:#008d54}
.btn-red{background:#a82043}
a{color:#8bcaff}
h3{margin-top:0}
@media(max-width:480px){.grid{grid-template-columns:1fr 1fr}td,th{font-size:12px;padding:8px 3px}}
</style>
</head>
<body>
<header>
<h2>◉ Manajemen MikroTik</h2>
<small>Panel Monitoring ISP</small>
</header>
<main>
<nav>
<a href="/">Beranda</a>
<a href="/online">Online</a>
<a href="/offline">Offline</a>
<a href="/pppoe">PPPoE</a>
<a href="/edit">Edit Pelanggan</a>
<a href="/detail">Detail Pelanggan</a>
<a href="/bandwidth">Laporan Bandwidth</a>
<a href="/routers">Router</a>
</nav>
{% with messages = get_flashed_messages() %}
{% for message in messages %}
<div class="card">{{message}}</div>
{% endfor %}
{% endwith %}
{{ content|safe }}
</main>
</body>
</html>
"""

def page(content, **kwargs):
    return render_template_string(BASE, content=render_template_string(content, **kwargs))

@app.route("/")
def home():
    try:
        all_data, online, offline, all_routers = get_data()
    except Exception:
        all_data, online, offline, all_routers = customers(), [], [], routers()

    paid = sum(1 for c in all_data if c.get("payment") == "Lunas")
    unpaid = len(all_data) - paid

    content = """
    <div class="grid">
      <a class="card" href="/online"><span class="green">ONLINE</span><div class="stat">{{on}}</div>Lihat pelanggan online →</a>
      <a class="card" href="/offline"><span class="red">OFFLINE</span><div class="stat">{{off}}</div>Lihat pelanggan offline →</a>
    </div>
    <a class="card" href="/pppoe" style="display:block;text-decoration:none">
      <span class="blue">TOTAL PELANGGAN / SECRET PPPoE</span>
      <div class="stat">{{total}}</div>Klik untuk melihat semua akun →
    </a>
    <div class="grid">
      <a class="card" href="/edit">✎<h3>Edit Pelanggan</h3>Tambah dan ubah data</a>
      <a class="card" href="/detail">◎<h3>Detail Pelanggan</h3>Status pembayaran</a>
      <a class="card" href="/bandwidth">▥<h3>Laporan Bandwidth</h3>Pemakaian satu bulan</a>
      <a class="card" href="/routers">▤<h3>Router</h3>Kelola koneksi router</a>
    </div>
    <div class="card">
      <h3>Ringkasan Pembayaran</h3>
      <div class="grid">
      <div><span class="green">Lunas</span><div class="stat">{{paid}}</div></div>
      <div><span class="red">Belum Lunas</span><div class="stat">{{unpaid}}</div></div>
      </div>
    </div>
    <div class="card"><h3>Status Router</h3>
    {% for r in routers %}
    <p>{{r.name}} — {{r.host}}</p>
    {% else %}<p>Belum ada router. Tambahkan router terlebih dahulu.</p>{% endfor %}
    </div>
    """
    return page(content, on=len(online), off=len(offline), total=len(all_data),
                paid=paid, unpaid=unpaid, routers=all_routers)

@app.route("/online")
def online_page():
    try:
        _, online, _, _ = get_data()
    except Exception:
        online = []
    content = """
    <div class="card"><h3 class="green">Pelanggan Online ({{items|length}})</h3>
    {% for c in items %}
      <div class="card"><span class="badge">ONLINE</span> <b>{{c.ip or 'IP belum tersedia'}}</b></div>
    {% else %}<p>Tidak ada pelanggan online.</p>{% endfor %}
    </div>
    """
    return page(content, items=online)

@app.route("/offline")
def offline_page():
    try:
        _, _, offline, _ = get_data()
    except Exception:
        offline = []
    content = """
    <div class="card"><h3 class="red">Pelanggan Offline ({{items|length}})</h3>
    {% for c in items %}
      <div class="card">
        <b>{{c.username}}</b><br>
        <span class="red">OFFLINE</span><br>
        <span class="small">Waktu pertama terdeteksi offline: {{ c.offline_time|datetime }}</span><br>
        Koordinat: {{c.coordinates or '-'}}
      </div>
    {% else %}<p>Tidak ada pelanggan offline.</p>{% endfor %}
    </div>
    """
    app.jinja_env.filters["datetime"] = format_time
    return page(content, items=offline)

def format_time(value):
    if not value:
        return "Belum tercatat"
    return datetime.fromtimestamp(float(value)).strftime("%d-%m-%Y %H:%M:%S")

@app.route("/pppoe")
def pppoe_page():
    all_data = customers()
    content = """
    <div class="card"><h3>Semua Secret PPPoE ({{items|length}})</h3>
    {% for c in items %}
      <div class="card">
      <b>{{c.username}}</b><br>
      Profil: {{c.profile or '-'}}<br>
      <span class="small">Status koneksi: {{'Online' if c.online else 'Offline'}}</span>
      </div>
    {% else %}<p>Belum ada data. Periksa koneksi router.</p>{% endfor %}
    </div>
    """
    return page(content, items=all_data)

@app.route("/edit", methods=["GET", "POST"])
def edit_page():
    if request.method == "POST":
        data = customers()
        username = request.form.get("username", "").strip()
        if not username:
            flash("User PPPoE wajib diisi.")
            return redirect("/edit")

        if any(c.get("username") == username and c.get("router") == request.form.get("router", "0") for c in data):
            flash("User tersebut sudah ada.")
            return redirect("/edit")

        data.append({
            "router": request.form.get("router", "0"),
            "username": username,
            "password": request.form.get("password", ""),
            "profile": request.form.get("profile", ""),
            "phone": request.form.get("phone", ""),
            "coordinates": request.form.get("coordinates", ""),
            "ip": "",
            "payment": "Belum Lunas",
            "online": False
        })
        save_customers(data)
        flash("Data pelanggan disimpan di aplikasi. Secret router belum dibuat.")
        return redirect("/edit")

    all_data = customers()
    all_routers = routers()
    content = """
    <div class="card">
    <h3>Tambah Pelanggan Baru</h3>
    <form method="post">
      <label>Router</label>
      <select name="router">
      {% for r in routers %}<option value="{{loop.index0}}">{{r.name}}</option>{% endfor %}
      </select>
      <label>User PPPoE</label><input name="username" required>
      <label>Sandi PPPoE</label><input name="password" type="password">
      <label>Profil PPPoE</label><input name="profile" placeholder="Contoh: 5Mbps-30Hari">
      <label>Nomor HP</label><input name="phone" placeholder="08xxxxxxxxxx">
      <label>Koordinat GPS</label><input name="coordinates" placeholder="-1.234567, 123.456789">
      <button class="btn btn-green" type="submit">Simpan Pelanggan</button>
    </form>
    </div>
    <div class="card"><h3>Daftar Pelanggan</h3>
    {% for c in items %}
      <div class="card">
      <b>{{c.username}}</b> — {{c.ip or '-'}}<br>
      HP: {{c.phone or '-'}}<br>
      <a href="/customer/{{loop.index0}}">Edit data →</a>
      </div>
    {% else %}<p>Belum ada pelanggan.</p>{% endfor %}
    </div>
    """
    return page(content, items=all_data, routers=all_routers)

@app.route("/customer/<int:index>", methods=["GET", "POST"])
def customer_page(index):
    data = customers()
    if index >= len(data):
        return redirect("/edit")
    c = data[index]

    if request.method == "POST":
        c["phone"] = request.form.get("phone", "")
        c["coordinates"] = request.form.get("coordinates", "")
        c["payment"] = request.form.get("payment", "Belum Lunas")
        save_customers(data)
        flash("Perubahan data pelanggan disimpan.")
        return redirect("/detail")

    content = """
    <div class="card">
    <h3>Detail Pelanggan: {{c.username}}</h3>
    <p>IP PPPoE: {{c.ip or '-'}}</p>
    <form method="post">
      <label>Nomor HP</label><input name="phone" value="{{c.phone}}">
      <label>Koordinat GPS</label><input name="coordinates" value="{{c.coordinates}}">
      <label>Status Pembayaran</label>
      <select name="payment">
        <option {% if c.payment == 'Lunas' %}selected{% endif %}>Lunas</option>
        <option {% if c.payment != 'Lunas' %}selected{% endif %}>Belum Lunas</option>
      </select>
      <button class="btn btn-green" type="submit">Simpan Perubahan</button>
    </form>
    {% if c.coordinates %}
    <p><a target="_blank" href="https://www.google.com/maps?q={{c.coordinates}}">Lihat Google Maps →</a></p>
    {% endif %}
    </div>
    """
    return page(content, c=c)

@app.route("/detail")
def detail_page():
    all_data = customers()
    content = """
    <div class="card"><h3>Detail Pelanggan dan Pembayaran</h3>
    {% for c in items %}
      <div class="card">
      <a href="/customer/{{loop.index0}}"><b>{{c.username}}</b></a><br>
      {{c.ip or '-'}} | {{c.phone or '-'}}<br>
      {% if c.payment == 'Lunas' %}
        <span class="badge">LUNAS</span>
      {% else %}
        <span class="badge red">BELUM LUNAS</span>
      {% endif %}
      </div>
    {% else %}<p>Belum ada data pelanggan.</p>{% endfor %}
    </div>
    """
    return page(content, items=all_data)

@app.route("/bandwidth")
def bandwidth_page():
    all_data = customers()
    total = sum(int(c.get("month_rx", 0)) + int(c.get("month_tx", 0)) for c in all_data)
    content = """
    <div class="card">
    <h3>Laporan Bandwidth PPPoE</h3>
    <p>Total tercatat sejak monitoring aktif bulan ini:</p>
    <div class="stat blue">{{total|bytes}}</div>
    <p class="small">Catatan: penghitung mulai merekam sejak aplikasi melakukan monitoring. Ini bukan data historis sebelum monitoring aktif.</p>
    </div>
    {% for c in items %}
    <div class="card">
      <b>{{c.username}}</b><br>
      Download: {{c.month_rx|bytes}}<br>
      Upload: {{c.month_tx|bytes}}<br>
      Total: {{(c.month_rx+c.month_tx)|bytes}}
    </div>
    {% endfor %}
    """
    return page(content, items=all_data, total=total)

def format_bytes(value):
    value = float(value or 0)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024:
            return "%.2f %s" % (value, unit)
        value /= 1024
    return "%.2f PB" % value

app.jinja_env.filters["bytes"] = format_bytes

@app.route("/routers", methods=["GET", "POST"])
def router_page():
    data = routers()
    if request.method == "POST":
        host = request.form.get("host", "").strip()
        if host:
            data.append({
                "name": request.form.get("name", "Router"),
                "host": host,
                "username": request.form.get("username", "admin"),
                "password": request.form.get("password", ""),
                "port": request.form.get("port", "8728")
            })
            write_json(ROUTERS_FILE, data)
            flash("Router disimpan di aplikasi.")
        return redirect("/routers")

    content = """
    <div class="card"><h3>Tambah Router MikroTik</h3>
    <form method="post">
      <label>Nama Router</label><input name="name" placeholder="Nama router">
      <label>IP / ZeroTier</label><input name="host" required placeholder="192.168.1.1">
      <label>Username API</label><input name="username" required>
      <label>Password</label><input name="password" type="password">
      <label>Port API</label><input name="port" value="8728">
      <button class="btn btn-green">Simpan Router</button>
    </form></div>
    <div class="card"><h3>Router Terdaftar</h3>
    {% for r in items %}
      <div class="card"><b>{{r.name}}</b><br>{{r.host}}:{{r.port}}</div>
    {% else %}<p>Belum ada router.</p>{% endfor %}
    </div>
    """
    return page(content, items=data)

@app.route("/health")
def health():
    return {"status": "ok", "app": "Manajemen MikroTik"}

def start_server(data_dir=None):
    global DATA_DIR, ROUTERS_FILE, CUSTOMERS_FILE, STATE_FILE
    if data_dir:
        DATA_DIR = data_dir
        os.makedirs(DATA_DIR, exist_ok=True)
        ROUTERS_FILE = os.path.join(DATA_DIR, "routers.json")
        CUSTOMERS_FILE = os.path.join(DATA_DIR, "customers.json")
        STATE_FILE = os.path.join(DATA_DIR, "state.json")

    thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=8765, debug=False, use_reloader=False),
        daemon=True
    )
    thread.start()
    return True
        
