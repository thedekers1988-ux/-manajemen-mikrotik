
import os
import json
import time
import threading
from datetime import datetime

from flask import Flask, request, redirect, render_template_string, flash
from routeros_api import RouterOsApiPool

app = Flask(__name__)
app.secret_key = "mikrotik-management-local"

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ROUTERS_FILE = os.path.join(DATA_DIR, "routers.json")
CUSTOMERS_FILE = os.path.join(DATA_DIR, "customers.json")
STATE_FILE = os.path.join(DATA_DIR, "state.json")

os.makedirs(DATA_DIR, exist_ok=True)


# =====================================================
# PENYIMPANAN DATA
# =====================================================

def read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp = path + ".tmp"

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    os.replace(temp, path)


def get_routers():
    return read_json(ROUTERS_FILE, [])


def get_customers():
    return read_json(CUSTOMERS_FILE, [])


def get_states():
    return read_json(STATE_FILE, {})


def save_customers(data):
    write_json(CUSTOMERS_FILE, data)


def save_states(data):
    write_json(STATE_FILE, data)


# =====================================================
# FORMAT DATA
# =====================================================

def format_time(value):
    if not value:
        return "Belum tercatat"

    try:
        return datetime.fromtimestamp(float(value)).strftime(
            "%d-%m-%Y %H:%M:%S"
        )
    except Exception:
        return "-"


def format_bytes(value):
    value = float(value or 0)

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024:
            return "%.2f %s" % (value, unit)
        value /= 1024

    return "%.2f PB" % value


app.jinja_env.filters["datetime"] = format_time
app.jinja_env.filters["bytes"] = format_bytes


# =====================================================
# KONEKSI MIKROTIK
# PERBAIKAN: PARAMETER timeout DIHAPUS
# =====================================================

def fetch_router(router):
    pool = None

    try:
        pool = RouterOsApiPool(
            router["host"],
            username=router["username"],
            password=router["password"],
            port=int(router.get("port", 8728)),
            plaintext_login=True,
            use_ssl=False
        )

        api = pool.get_api()

        active = api.get_resource("/ppp/active").get()
        secrets = api.get_resource("/ppp/secret").get()

        return active, secrets, "Terhubung"

    except Exception as e:
        return [], [], str(e)

    finally:
        if pool:
            try:
                pool.disconnect()
            except Exception:
                pass


# =====================================================
# MONITORING PELANGGAN
# =====================================================

def update_monitor():
    routers = get_routers()
    customers = get_customers()
    states = get_states()

    now = time.time()
    month_key = datetime.now().strftime("%Y-%m")

    for ridx, router in enumerate(routers):
        rid = str(ridx)

        active, secrets, status = fetch_router(router)

        if rid not in states:
            states[rid] = {}

        states[rid]["router_status"] = status

        active_map = {
            x.get("name"): x
            for x in active
            if x.get("name")
        }

        for secret in secrets:
            username = secret.get("name", "").strip()

            if not username:
                continue

            info = states[rid].get(username, {})
            is_online = username in active_map

            if is_online:
                if not info.get("online", False):
                    info["online_since"] = now

                info["offline_since"] = None

            else:
                if info.get("online", False) or not info.get("offline_since"):
                    info["offline_since"] = now

            info["online"] = is_online

            if info.get("month_key") != month_key:
                info["month_key"] = month_key
                info["month_rx"] = 0
                info["month_tx"] = 0
                info["traffic"] = {"rx": 0, "tx": 0}

            if is_online:
                session = active_map[username]

                rx = int(session.get("bytes-in", 0) or 0)
                tx = int(session.get("bytes-out", 0) or 0)

                previous = info.get("traffic", {})
                old_rx = int(previous.get("rx", 0))
                old_tx = int(previous.get("tx", 0))

                info["month_rx"] = int(info.get("month_rx", 0))
                info["month_tx"] = int(info.get("month_tx", 0))

                info["month_rx"] += max(0, rx - old_rx) if rx >= old_rx else rx
                info["month_tx"] += max(0, tx - old_tx) if tx >= old_tx else tx

                info["traffic"] = {
                    "rx": rx,
                    "tx": tx
                }

                info["last_seen"] = now

            states[rid][username] = info

            found = None

            for customer in customers:
                if (
                    str(customer.get("router", "0")) == rid
                    and customer.get("username") == username
                ):
                    found = customer
                    break

            ip = ""

            if is_online:
                ip = active_map[username].get("address", "")

            if found:
                found["ip"] = ip or found.get("ip", "")
                found["profile"] = secret.get("profile", "")
                found["online"] = is_online

            else:
                customers.append({
                    "router": rid,
                    "username": username,
                    "password": "",
                    "profile": secret.get("profile", ""),
                    "ip": ip,
                    "phone": "",
                    "coordinates": "",
                    "payment": "Belum Lunas",
                    "online": is_online
                })

    save_customers(customers)
    save_states(states)


def get_monitor_data():
    update_monitor()

    customers = get_customers()
    states = get_states()

    online = []
    offline = []

    for index, customer in enumerate(customers):
        item = dict(customer)

        rid = str(item.get("router", "0"))
        username = item.get("username", "")
        info = states.get(rid, {}).get(username, {})

        item["index"] = index
        item["online"] = bool(info.get("online", False))
        item["offline_time"] = info.get("offline_since")
        item["month_rx"] = int(info.get("month_rx", 0))
        item["month_tx"] = int(info.get("month_tx", 0))

        if item["online"]:
            online.append(item)
        else:
            offline.append(item)

    return customers, online, offline


# =====================================================
# TAMPILAN UMUM
# =====================================================

BASE = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>Manajemen MikroTik</title>

<style>
*{box-sizing:border-box}

body{
    margin:0;
    background:#031329;
    color:#f1f7ff;
    font-family:Arial,sans-serif
}

header{
    background:#082b58;
    padding:22px 16px;
    border-bottom:3px solid #087cff
}

header h2{
    margin:0;
    font-size:24px
}

header small{
    color:#a9cfff
}

main{
    padding:15px;
    max-width:900px;
    margin:auto;
    padding-bottom:40px
}

.card{
    background:#092447;
    border:1px solid #205789;
    border-radius:17px;
    padding:17px;
    margin-bottom:14px;
    color:#f1f7ff
}

.grid{
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:10px
}

.menu-card{
    display:block;
    text-decoration:none;
    text-align:center;
    font-size:17px;
    font-weight:bold;
    padding:22px 8px;
    background:#0757a7;
    border-radius:13px;
    color:white
}

.stat{
    font-size:32px;
    font-weight:bold;
    margin:8px 0
}

.green{color:#32e99b}
.red{color:#ff647c}
.blue{color:#62baff}

.btn,.back{
    display:inline-block;
    padding:12px 16px;
    margin:5px 3px 5px 0;
    background:#0757a7;
    color:white;
    border:0;
    border-radius:10px;
    text-decoration:none;
    font-size:15px
}

.btn-green{background:#008d54}
.btn-red{background:#a82043}

.back{margin-bottom:15px}

input,select{
    width:100%;
    padding:13px;
    margin:7px 0 14px;
    border-radius:9px;
    border:1px solid #3278b6;
    background:#061a34;
    color:white;
    font-size:15px
}

label{
    color:#bcdcff;
    font-size:14px
}

.badge{
    display:inline-block;
    padding:6px 10px;
    border-radius:20px;
    background:#087b55;
    color:white;
    font-size:12px
}

.badge.red{background:#a82043}

a{color:#8bcaff}

h3{margin-top:0}

.small{
    font-size:12px;
    color:#a9c6e5
}

hr{
    border:0;
    border-top:1px solid #205789;
    margin:14px 0
}

@media(max-width:420px){
    .menu-card{
        font-size:15px;
        padding:19px 5px
    }

    .stat{font-size:27px}
}
</style>
</head>

<body>
<header>
<h2>◉ Manajemen MikroTik</h2>
<small>Panel Monitoring ISP</small>
</header>

<main>

{% if request.path != '/' %}
<a class="back" href="/">← Kembali ke Menu</a>
{% endif %}

{% with messages = get_flashed_messages() %}
{% for message in messages %}
<div class="card">{{message}}</div>
{% endfor %}
{% endwith %}

{{content|safe}}

</main>
</body>
</html>
"""


def page(content, **kwargs):
    return render_template_string(
        BASE,
        content=render_template_string(content, **kwargs)
    )


# =====================================================
# BERANDA
# =====================================================

@app.route("/")
def home():
    try:
        all_data, online, offline = get_monitor_data()
    except Exception:
        all_data = get_customers()
        online = []
        offline = all_data

    paid = sum(
        1 for c in all_data
        if c.get("payment") == "Lunas"
    )

    unpaid = len(all_data) - paid

    content = """
    <div class="grid">

        <a href="/online" class="card" style="text-decoration:none">
            <span class="green">ONLINE</span>
            <div class="stat">{{on}}</div>
            Lihat pelanggan online →
        </a>

        <a href="/offline" class="card" style="text-decoration:none">
            <span class="red">OFFLINE</span>
            <div class="stat">{{off}}</div>
            Lihat pelanggan offline →
        </a>

    </div>

    <a href="/pppoe" class="card" style="display:block;text-decoration:none">
        <span class="blue">TOTAL PELANGGAN / SECRET PPPoE</span>
        <div class="stat">{{total}}</div>
        Klik untuk melihat semua akun →
    </a>

    <h3>Menu Utama</h3>

    <div class="grid">
        <a href="/edit" class="menu-card">✎<br>Edit Pelanggan</a>
        <a href="/detail" class="menu-card">◎<br>Detail Pelanggan</a>
        <a href="/bandwidth" class="menu-card">▥<br>Laporan Bandwidth</a>
        <a href="/routers" class="menu-card">▤<br>Router</a>
    </div>

    <div class="card" style="margin-top:18px">
        <h3>Ringkasan Pembayaran</h3>

        <div class="grid">
            <div>
                <span class="green">LUNAS</span>
                <div class="stat">{{paid}}</div>
            </div>

            <div>
                <span class="red">BELUM LUNAS</span>
                <div class="stat">{{unpaid}}</div>
            </div>
        </div>
    </div>
    """

    return page(
        content,
        on=len(online),
        off=len(offline),
        total=len(all_data),
        paid=paid,
        unpaid=unpaid
    )


# =====================================================
# ONLINE
# =====================================================

@app.route("/online")
def online_page():
    try:
        _, online, _ = get_monitor_data()
    except Exception:
        online = []

    q = request.args.get("q", "").lower().strip()

    if q:
        online = [
            c for c in online
            if q in c.get("username", "").lower()
            or q in c.get("ip", "").lower()
        ]

    content = """
    <div class="card">

        <h3 class="green">
            Pelanggan Online ({{items|length}})
        </h3>

        <form method="get">
            <input name="q" value="{{q}}"
            placeholder="Cari nama atau IP pelanggan...">

            <button class="btn" type="submit">Cari</button>
        </form>

        {% for c in items %}
        <div class="card">
            <span class="badge">ONLINE</span>
            <h3>{{c.username}}</h3>
            IP: <b>{{c.ip or 'IP belum tersedia'}}</b>
        </div>
        {% else %}
        <p>Pelanggan tidak ditemukan.</p>
        {% endfor %}

    </div>
    """

    return page(content, items=online, q=q)


# =====================================================
# OFFLINE
# =====================================================

@app.route("/offline")
def offline_page():
    try:
        _, _, offline = get_monitor_data()
    except Exception:
        offline = []

    q = request.args.get("q", "").lower().strip()

    if q:
        offline = [
            c for c in offline
            if q in c.get("username", "").lower()
        ]

    content = """
    <div class="card">

        <h3 class="red">
            Pelanggan Offline ({{items|length}})
        </h3>

        <form method="get">
            <input name="q" value="{{q}}"
            placeholder="Cari nama pelanggan...">

            <button class="btn" type="submit">Cari</button>
        </form>

        {% for c in items %}
        <div class="card">

            <h3>{{c.username}}</h3>
            <span class="badge red">OFFLINE</span>

            <hr>

            Waktu terdeteksi mati:<br>
            <b>{{c.offline_time|datetime}}</b>

            <hr>

            Koordinat pelanggan:<br>
            {{c.coordinates or 'Belum diisi'}}

            {% if c.coordinates %}
            <p>
            <a target="_blank"
            href="https://www.google.com/maps?q={{c.coordinates}}">
            Lihat Google Maps →
            </a>
            </p>
            {% endif %}

        </div>
        {% else %}
        <p>Tidak ada pelanggan offline.</p>
        {% endfor %}

    </div>
    """

    return page(content, items=offline, q=q)


# =====================================================
# SEMUA SECRET PPPoE
# =====================================================

@app.route("/pppoe")
def pppoe_page():
    all_data = get_customers()

    q = request.args.get("q", "").lower().strip()

    if q:
        all_data = [
            c for c in all_data
            if q in c.get("username", "").lower()
        ]

    content = """
    <div class="card">

        <h3>Semua Secret PPPoE ({{items|length}})</h3>

        <form method="get">
            <input name="q" value="{{q}}"
            placeholder="Cari user PPPoE...">

            <button class="btn" type="submit">Cari</button>
        </form>

        {% for c in items %}
        <div class="card">

            <b>{{c.username}}</b><br>
            Profil: {{c.profile or '-'}}<br>
            IP: {{c.ip or '-'}}<br>

            {% if c.online %}
            <span class="badge">ONLINE</span>
            {% else %}
            <span class="badge red">OFFLINE</span>
            {% endif %}

        </div>
        {% else %}
        <p>Belum ada data PPPoE.</p>
        {% endfor %}

    </div>
    """

    return page(content, items=all_data, q=q)


# =====================================================
# EDIT DAN TAMBAH PELANGGAN
# =====================================================

@app.route("/edit", methods=["GET", "POST"])
def edit_page():
    if request.method == "POST":
        data = get_customers()

        username = request.form.get("username", "").strip()
        rid = request.form.get("router", "0")

        if not username:
            flash("User PPPoE wajib diisi.")
            return redirect("/edit")

        exists = any(
            c.get("username") == username
            and str(c.get("router", "0")) == rid
            for c in data
        )

        if exists:
            flash("User pelanggan sudah ada.")
            return redirect("/edit")

        data.append({
            "router": rid,
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

        flash(
            "Data disimpan di aplikasi. "
            "Secret MikroTik belum dibuat."
        )

        return redirect("/edit")

    items = get_customers()
    routers = get_routers()

    content = """
    <div class="card">

        <h3>Tambah Pelanggan Baru</h3>

        <form method="post">

            <label>Router</label>
            <select name="router">
                {% for r in routers %}
                <option value="{{loop.index0}}">
                    {{r.name}}
                </option>
                {% endfor %}
            </select>

            <label>User PPPoE</label>
            <input name="username" required>

            <label>Sandi PPPoE</label>
            <input name="password" type="password">

            <label>Profil PPPoE</label>
            <input name="profile" placeholder="Contoh: 5Mbps">

            <label>Nomor HP</label>
            <input name="phone" placeholder="08xxxxxxxxxx">

            <label>Koordinat GPS</label>
            <input name="coordinates"
            placeholder="-1.234567, 123.456789">

            <button class="btn btn-green" type="submit">
                Simpan Pelanggan
            </button>

        </form>
    </div>

    <div class="card">

        <h3>Daftar Pelanggan</h3>

        {% for c in items %}
        <div class="card">

            <b>{{c.username}}</b><br>
            IP: {{c.ip or '-'}}<br>
            HP: {{c.phone or '-'}}<br>

            <a href="/customer/{{loop.index0}}">
                Edit data →
            </a>

        </div>
        {% else %}
        <p>Belum ada pelanggan.</p>
        {% endfor %}

    </div>
    """

    return page(content, items=items, routers=routers)


# =====================================================
# EDIT DETAIL PELANGGAN
# =====================================================

@app.route("/customer/<int:index>", methods=["GET", "POST"])
def customer_page(index):
    data = get_customers()

    if index < 0 or index >= len(data):
        flash("Data pelanggan tidak ditemukan.")
        return redirect("/edit")

    customer = data[index]

    if request.method == "POST":
        customer["phone"] = request.form.get("phone", "")
        customer["coordinates"] = request.form.get("coordinates", "")
        customer["payment"] = request.form.get(
            "payment", "Belum Lunas"
        )

        save_customers(data)

        flash("Perubahan data pelanggan disimpan.")
        return redirect("/detail")

    content = """
    <div class="card">

        <h3>Edit Data Pelanggan</h3>

        User PPPoE:<br>
        <b>{{c.username}}</b><br><br>

        IP PPPoE:<br>
        <b>{{c.ip or '-'}}</b><br><br>

        <form method="post">

            <label>Nomor HP</label>
            <input name="phone" value="{{c.phone}}">

            <label>Koordinat GPS</label>
            <input name="coordinates" value="{{c.coordinates}}">

            <label>Status Pembayaran</label>

            <select name="payment">
                <option value="Lunas"
                {% if c.payment == 'Lunas' %}selected{% endif %}>
                    Lunas
                </option>

                <option value="Belum Lunas"
                {% if c.payment != 'Lunas' %}selected{% endif %}>
                    Belum Lunas
                </option>
            </select>

            <button class="btn btn-green" type="submit">
                Simpan Perubahan
            </button>

        </form>

        {% if c.coordinates %}
        <p>
        <a target="_blank"
        href="https://www.google.com/maps?q={{c.coordinates}}">
        Lihat Google Maps →
        </a>
        </p>
        {% endif %}

    </div>
    """

    return page(content, c=customer)


# =====================================================
# DETAIL PELANGGAN DAN PEMBAYARAN
# =====================================================

@app.route("/detail")
def detail_page():
    original = get_customers()

    q = request.args.get("q", "").lower().strip()
    payment_filter = request.args.get("status", "Semua")

    items = []

    for index, c in enumerate(original):
        item = dict(c)
        item["index"] = index

        if q and not (
            q in c.get("username", "").lower()
            or q in c.get("ip", "").lower()
            or q in c.get("phone", "").lower()
        ):
            continue

        if payment_filter in ["Lunas", "Belum Lunas"]:
            if c.get("payment", "Belum Lunas") != payment_filter:
                continue

        items.append(item)

    content = """
    <div class="card">

        <h3>Detail Pelanggan dan Pembayaran</h3>

        <form method="get">

            <input name="q" value="{{q}}"
            placeholder="Cari nama, IP, atau nomor HP...">

            <select name="status">

                <option value="Semua"
                {% if status == 'Semua' %}selected{% endif %}>
                    Semua Pelanggan
                </option>

                <option value="Lunas"
                {% if status == 'Lunas' %}selected{% endif %}>
                    Lunas
                </option>

                <option value="Belum Lunas"
                {% if status == 'Belum Lunas' %}selected{% endif %}>
                    Belum Lunas
                </option>

            </select>

            <button class="btn" type="submit">
                Cari Pelanggan
            </button>

        </form>

        {% for c in items %}
        <div class="card">

            <a href="/customer/{{c.index}}">
                <b>{{c.username}}</b>
            </a><br>

            IP: {{c.ip or '-'}}<br>
            HP: {{c.phone or '-'}}<br>

            {% if c.payment == 'Lunas' %}

                <span class="badge">LUNAS</span>

            {% else %}

                <span class="badge red">BELUM LUNAS</span>

                <form method="post"
                action="/pelunasan/{{c.index}}"
                onsubmit="return confirm('Konfirmasi pelanggan sudah membayar?')">

                    <button class="btn btn-green" type="submit">
                        Pelunasan
                    </button>

                </form>

            {% endif %}

            <p>
            <a href="/customer/{{c.index}}">
                Lihat detail / Edit →
            </a>
            </p>

        </div>

        {% else %}
        <p>Pelanggan tidak ditemukan.</p>
        {% endfor %}

    </div>
    """

    return page(
        content,
        items=items,
        q=q,
        status=payment_filter
    )


@app.route("/pelunasan/<int:index>", methods=["POST"])
def pelunasan(index):
    data = get_customers()

    if index < 0 or index >= len(data):
        flash("Data pelanggan tidak ditemukan.")
        return redirect("/detail")

    data[index]["payment"] = "Lunas"

    save_customers(data)

    flash("Status pembayaran berhasil diubah menjadi Lunas.")

    return redirect("/detail")


# =====================================================
# LAPORAN BANDWIDTH BULANAN
# =====================================================

@app.route("/bandwidth")
def bandwidth_page():
    items = get_customers()
    states = get_states()

    total_rx = 0
    total_tx = 0

    for c in items:
        rid = str(c.get("router", "0"))
        username = c.get("username", "")

        info = states.get(rid, {}).get(username, {})

        c["month_rx"] = int(info.get("month_rx", 0))
        c["month_tx"] = int(info.get("month_tx", 0))

        total_rx += c["month_rx"]
        total_tx += c["month_tx"]

    content = """
    <div class="card">

        <h3>Laporan Bandwidth Bulanan</h3>

        <p class="small">Bulan: {{month}}</p>

        <div class="grid">

            <div>
                <span class="blue">DOWNLOAD</span>
                <div class="stat">{{rx|bytes}}</div>
            </div>

            <div>
                <span class="green">UPLOAD</span>
                <div class="stat">{{tx|bytes}}</div>
            </div>

        </div>

        <hr>

        <h3>Bandwidth Per Pelanggan</h3>

        {% for c in items %}
        <div class="card">

            <b>{{c.username}}</b>
            <hr>

            Download: {{c.month_rx|bytes}}<br>
            Upload: {{c.month_tx|bytes}}<br>
            Total: {{(c.month_rx+c.month_tx)|bytes}}

        </div>

        {% else %}
        <p>Belum ada data bandwidth.</p>
        {% endfor %}

        <p class="small">
        Data dihitung sejak monitoring aktif.
        Bukan riwayat sebelum aplikasi dipasang.
        </p>

    </div>
    """

    return page(
        content,
        items=items,
        rx=total_rx,
        tx=total_tx,
        month=datetime.now().strftime("%B %Y")
    )


# =====================================================
# ROUTER: TAMBAH DAN HUBUNGKAN
# =====================================================

@app.route("/routers", methods=["GET", "POST"])
def router_page():
    data = get_routers()

    if request.method == "POST":
        host = request.form.get("host", "").strip()
        username = request.form.get("username", "").strip()

        if not host or not username:
            flash("IP router dan username wajib diisi.")
            return redirect("/routers")

        data.append({
            "name": request.form.get("name", "Router").strip() or "Router",
            "host": host,
            "username": username,
            "password": request.form.get("password", ""),
            "port": request.form.get("port", "8728")
        })

        write_json(ROUTERS_FILE, data)

        flash("Router disimpan. Silakan tekan Hubungkan.")

        return redirect("/routers")

    states = get_states()

    for i, r in enumerate(data):
        r["status"] = states.get(str(i), {}).get(
            "router_status", "Belum dites"
        )

    content = """
    <div class="card">

        <h3>Tambah Router MikroTik</h3>

        <form method="post">

            <label>Nama Router</label>
            <input name="name" placeholder="Nama router">

            <label>IP / ZeroTier</label>
            <input name="host" required placeholder="192.168.1.1">

            <label>Username API</label>
            <input name="username" required>

            <label>Password</label>
            <input name="password" type="password">

            <label>Port API</label>
            <input name="port" value="8728">

            <button class="btn btn-green" type="submit">
                Simpan Router
            </button>

        </form>

    </div>

    <div class="card">

        <h3>Router Terdaftar</h3>

        {% for r in items %}
        <div class="card">

            <h3>{{r.name}}</h3>

            {{r.host}}:{{r.port}}

            <hr>

            Status terakhir:<br>
            {{r.status}}

            <form method="post"
            action="/router-connect/{{loop.index0}}">

                <button class="btn btn-green" type="submit">
                    Hubungkan ke MikroTik
                </button>

            </form>

            <a class="btn btn-red"
            href="/router-delete-confirm/{{loop.index0}}">
                Hapus Router
            </a>

        </div>

        {% else %}
        <p>Belum ada router.</p>
        {% endfor %}

    </div>
    """

    return page(content, items=data)


@app.route("/router-delete-confirm/<int:index>", methods=["GET"])
def router_delete_confirm(index):
    routers = get_routers()

    if index < 0 or index >= len(routers):
        flash("Router tidak ditemukan.")
        return redirect("/routers")

    router = routers[index]
    content = """
    <div class="card">
        <h3>Konfirmasi Hapus Router</h3>
        <p>Apakah kamu yakin ingin menghapus router berikut dari aplikasi?</p>
        <h3>{{name}}</h3>
        <p>{{host}}:{{port}}</p>
        <p class="small">
            Data pelanggan lokal dan riwayat monitoring milik router ini
            juga akan dihapus. Konfigurasi pada perangkat MikroTik tidak berubah.
        </p>
        <form method="post" action="/router-delete/{{index}}">
            <button class="btn btn-red" type="submit">Ya, Hapus Router</button>
            <a class="btn" href="/routers">Batal</a>
        </form>
    </div>
    """
    return page(
        content,
        name=router.get("name", "MikroTik"),
        host=router.get("host", ""),
        port=router.get("port", "8728"),
        index=index
    )


@app.route("/router-delete/<int:index>", methods=["POST"])
def router_delete(index):
    routers = get_routers()

    if index < 0 or index >= len(routers):
        flash("Router tidak ditemukan.")
        return redirect("/routers")

    # Hapus router dari daftar aplikasi.
    routers.pop(index)
    write_json(ROUTERS_FILE, routers)

    # Hapus data pelanggan lokal milik router tersebut.
    customers = get_customers()
    kept_customers = []

    for customer in customers:
        try:
            customer_router = int(customer.get("router", 0))
        except (TypeError, ValueError):
            customer_router = 0

        if customer_router == index:
            continue

        # Rapikan indeks router lain yang bergeser.
        if customer_router > index:
            customer["router"] = str(customer_router - 1)

        kept_customers.append(customer)

    save_customers(kept_customers)

    # Hapus status monitoring router ini dan rapikan indeks lainnya.
    old_states = get_states()
    new_states = {}

    for old_id, state in old_states.items():
        try:
            state_index = int(old_id)
        except (TypeError, ValueError):
            continue

        if state_index == index:
            continue

        new_id = str(state_index - 1 if state_index > index else state_index)
        new_states[new_id] = state

    save_states(new_states)

    flash("Router dan data lokal terkait berhasil dihapus dari aplikasi. Konfigurasi MikroTik tidak berubah.")
    return redirect("/routers")


@app.route("/router-connect/<int:index>", methods=["POST"])
def router_connect(index):
    routers = get_routers()

    if index < 0 or index >= len(routers):
        flash("Router tidak ditemukan.")
        return redirect("/routers")

    router = routers[index]

    active, secrets, status = fetch_router(router)

    states = get_states()
    rid = str(index)

    if rid not in states:
        states[rid] = {}

    states[rid]["router_status"] = status
    save_states(states)

    if status == "Terhubung":
        flash(
            "BERHASIL TERHUBUNG ke "
            + router.get("name", "MikroTik")
            + " | Online: "
            + str(len(active))
            + " | Total Secret: "
            + str(len(secrets))
        )

    else:
        flash("GAGAL TERHUBUNG: " + status)

    return redirect("/routers")


# =====================================================
# HEALTH CHECK DAN START SERVER ANDROID
# =====================================================

@app.route("/health")
def health():
    return {
        "status": "ok",
        "app": "Manajemen MikroTik"
    }


def start_server(data_dir=None):
    global DATA_DIR
    global ROUTERS_FILE
    global CUSTOMERS_FILE
    global STATE_FILE

    if data_dir:
        DATA_DIR = data_dir

        os.makedirs(DATA_DIR, exist_ok=True)

        ROUTERS_FILE = os.path.join(DATA_DIR, "routers.json")
        CUSTOMERS_FILE = os.path.join(DATA_DIR, "customers.json")
        STATE_FILE = os.path.join(DATA_DIR, "state.json")

    thread = threading.Thread(
        target=lambda: app.run(
            host="127.0.0.1",
            port=8765,
            debug=False,
            use_reloader=False
        ),
        daemon=True
    )

    thread.start()

    return True
