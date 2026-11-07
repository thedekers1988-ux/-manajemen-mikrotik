
from flask import Flask, request, redirect, render_template_string, jsonify, url_for
from routeros_api import RouterOsApiPool
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote
import json
import threading
import socket
import time

app = Flask(__name__)

DATA_DIR = Path(__file__).resolve().parent
ROUTERS_DB = DATA_DIR / "routers.json"
CUSTOMERS_DB = DATA_DIR / "customers.json"
STATE_DB = DATA_DIR / "offline_state.json"

_server_thread = None
_server_lock = threading.Lock()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def parse_time(value):
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return datetime.now(timezone.utc)


def duration_text(start):
    seconds = max(
        0,
        int((datetime.now(timezone.utc) - parse_time(start)).total_seconds())
    )
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    if days:
        return f"{days} hari {hours} jam"
    if hours:
        return f"{hours} jam {minutes} menit"
    if minutes:
        return f"{minutes} menit {seconds} detik"
    return f"{seconds} detik"


def read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def write_json(path, data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    temp.replace(path)


def setup_storage(data_dir=None):
    global DATA_DIR, ROUTERS_DB, CUSTOMERS_DB, STATE_DB

    if data_dir:
        DATA_DIR = Path(data_dir)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    ROUTERS_DB = DATA_DIR / "routers.json"
    CUSTOMERS_DB = DATA_DIR / "customers.json"
    STATE_DB = DATA_DIR / "offline_state.json"


def load_routers():
    data = read_json(ROUTERS_DB, [])
    return data if isinstance(data, list) else []


def save_routers(data):
    write_json(ROUTERS_DB, data)


def load_customer_data():
    data = read_json(CUSTOMERS_DB, {})
    return data if isinstance(data, dict) else {}


def save_customer_data(data):
    write_json(CUSTOMERS_DB, data)


def load_states():
    data = read_json(STATE_DB, {})
    return data if isinstance(data, dict) else {}


def save_states(data):
    write_json(STATE_DB, data)


def router_key(router):
    return str(router.get("name") or router.get("host"))


def customer_key(router, username):
    return router_key(router) + "|" + str(username)


def connect_router(router):
    return RouterOsApiPool(
        router["host"],
        username=router["username"],
        password=router["password"],
        port=int(router.get("port", 8728)),
        plaintext_login=True,
        use_ssl=False,
        ssl_verify=False
    )


def fetch_router_data(router):
    pool = None

    try:
        pool = connect_router(router)
        api = pool.get_api()

        active = api.get_resource("/ppp/active").get()
        secrets = api.get_resource("/ppp/secret").get()

        return active, secrets, None

    except Exception as e:
        return [], [], str(e)

    finally:
        if pool:
            try:
                pool.disconnect()
            except Exception:
                pass


def build_customers(router, active, secrets):
    states = load_states()
    router_states = states.setdefault(router_key(router), {})
    metadata = load_customer_data()

    active_map = {
        str(x.get("name")): x
        for x in active if x.get("name")
    }

    secret_map = {
        str(x.get("name")): x
        for x in secrets if x.get("name")
    }

    names = sorted(set(active_map) | set(secret_map))
    result = []
    timestamp = now_iso()

    for username in names:
        item = active_map.get(username, {})
        secret = secret_map.get(username, {})
        state = router_states.setdefault(username, {})
        saved = metadata.get(customer_key(router, username), {})

        online = username in active_map

        if online:
            state["online"] = True
            state["last_online"] = timestamp
            state["last_ip"] = item.get("address", "-")
            state["offline_since"] = None

        else:
            if state.get("online") is True or not state.get("offline_since"):
                state["offline_since"] = timestamp

            state["online"] = False

        offline_since = state.get("offline_since")

        result.append({
            "name": username,
            "address": (
                item.get("address")
                or state.get("last_ip")
                or "-"
            ),
            "service": (
                item.get("service")
                or secret.get("service")
                or "pppoe"
            ),
            "profile": secret.get("profile", "-"),
            "uptime": item.get("uptime", "-") if online else "-",
            "caller_id": (
                item.get("caller-id")
                or state.get("caller_id")
                or "-"
            ),
            "online": online,
            "offline_since": offline_since,
            "offline_duration": (
                duration_text(offline_since)
                if offline_since and not online else "-"
            ),
            "phone": saved.get("phone", ""),
            "location": saved.get("location", ""),
            "lat": saved.get("lat", ""),
            "lon": saved.get("lon", "")
        })

    save_states(states)
    return result


PAGE = r"""
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
 background:#061020;
 color:#edf4ff;
 font-family:Arial,sans-serif;
}

header{
 padding:22px 18px;
 background:linear-gradient(120deg,#0755a9,#10233f,#071326);
 border-bottom:1px solid #24446b;
}

.brand{
 font-size:23px;
 font-weight:bold;
}

.subtitle{
 color:#b4c9e5;
 margin-top:7px;
}

main{
 max-width:950px;
 margin:auto;
 padding:16px;
}

nav{
 display:grid;
 grid-template-columns:repeat(4,1fr);
 gap:8px;
 margin-bottom:16px;
}

nav a{
 background:#142943;
 border:1px solid #263e5d;
 border-radius:14px;
 padding:15px 4px;
 text-align:center;
 color:#eaf3ff;
 text-decoration:none;
 font-size:13px;
}

nav a.active{
 background:#075ed4;
 border-color:#1685ff;
}

.card{
 background:linear-gradient(145deg,#142943,#102039);
 border:1px solid #304968;
 border-radius:20px;
 padding:18px;
 margin-bottom:16px;
}

.row{
 display:flex;
 justify-content:space-between;
 align-items:center;
 gap:10px;
}

.muted{
 color:#9fb2cc;
 font-size:13px;
}

.grid{
 display:grid;
 grid-template-columns:repeat(3,minmax(0,1fr));
 gap:9px;
 margin-top:18px;
}

.stat{
 display:block;
 color:white;
 text-decoration:none;
 padding:14px 10px;
 border-radius:16px;
 min-height:135px;
 border:2px solid transparent;
}

.stat b{
 display:block;
 font-size:32px;
 margin:12px 0 6px;
}

.green{
 background:linear-gradient(140deg,#087d50,#03452f);
 border-color:#08ce7a;
}

.red{
 background:linear-gradient(140deg,#a83242,#60202e);
 border-color:#ff5362;
}

.blue{
 background:linear-gradient(140deg,#0866bd,#093c80);
 border-color:#168bff;
}

.purple{
 background:#34285c;
}

button,.btn{
 display:block;
 width:100%;
 padding:14px;
 border:0;
 border-radius:11px;
 background:#0878ed;
 color:white;
 font-size:15px;
 font-weight:bold;
 text-align:center;
 text-decoration:none;
 cursor:pointer;
 margin-top:9px;
}

.secondary{
 background:#263e5e;
}

input{
 width:100%;
 padding:14px;
 margin:6px 0;
 border:1px solid #405a79;
 border-radius:11px;
 background:#09182b;
 color:white;
 font-size:15px;
}

.customer{
 background:#091a2e;
 border:1px solid #294463;
 border-radius:14px;
 padding:14px;
 margin:11px 0;
 overflow-wrap:anywhere;
}

.customer h3{
 margin:0;
 font-size:18px;
}

.badge{
 padding:6px 10px;
 border-radius:20px;
 font-size:12px;
 font-weight:bold;
}

.on{
 background:#075b3b;
 color:#9dffca;
}

.off{
 background:#742b3b;
 color:#ffc0c8;
}

.error{color:#ff929b}
.success{color:#67edac}

hr{
 border:0;
 border-top:1px solid #304968;
 margin:14px 0;
}

.actions{
 display:flex;
 gap:8px;
 flex-wrap:wrap;
}

.actions a{
 flex:1;
}

@media(max-width:480px){
 .stat{min-height:120px}
 .stat b{font-size:27px}
 .grid{gap:7px}
}
</style>
</head>

<body>

<header>
 <div class="brand">◈ MANAJEMEN MIKROTIK</div>
 <div class="subtitle">Panel Monitoring ISP</div>
</header>

<main>

<nav>
 <a href="/" class="{{ 'active' if view == 'dashboard' else '' }}">⌂<br>Dashboard</a>
 <a href="/router/{{ router_index }}?view=online" class="{{ 'active' if view == 'online' else '' }}">♙<br>Pelanggan</a>
 <a href="#router">▣<br>Router</a>
 <a href="#tambah">＋<br>Tambah Router</a>
</nav>

{% if selected and not error %}

<section class="card">
 <div class="row">
  <div>
   <h2 style="margin:0">Ringkasan PPPoE</h2>
   <p class="muted">Statistik pelanggan dari router {{ selected.name }}</p>
  </div>
  <span class="badge on">● Terhubung</span>
 </div>

 <div class="grid">
  <a class="stat green" href="/router/{{ router_index }}?view=online">
   Online
   <b>{{ online_count }}</b>
   <small>Pelanggan aktif</small>
  </a>

  <a class="stat red" href="/router/{{ router_index }}?view=offline">
   Offline
   <b>{{ offline_count }}</b>
   <small>Tidak aktif</small>
  </a>

  <a class="stat blue" href="/router/{{ router_index }}?view=total">
   Total
   <b>{{ total_count }}</b>
   <small>Akun PPPoE</small>
  </a>
 </div>

 <hr>
 <div class="row">
  <span class="muted">Router: {{ selected.name }}</span>
  <span class="muted">{{ selected.host }}</span>
 </div>

 <button onclick="location.reload()">↻ PERBARUI SEKARANG</button>
 <p class="muted">Data diperbarui saat halaman dimuat. Pembaruan otomatis setiap 30 detik.</p>
</section>

{% elif error %}
<section class="card">
 <h3>Koneksi MikroTik gagal</h3>
 <p class="error">{{ error }}</p>
 <a class="btn" href="/">Kembali ke Dashboard</a>
</section>
{% else %}
<section class="card">
 <h2>Selamat Datang</h2>
 <p class="muted">Pilih router untuk melihat statistik pelanggan PPPoE.</p>
</section>
{% endif %}


{% if view in ['online','offline','total'] and selected and not error %}
<section class="card" id="pelanggan">

 <div class="row">
  <h2 style="margin:0">
   {% if view == 'online' %}Pelanggan Online
   {% elif view == 'offline' %}Pelanggan Offline
   {% else %}Semua Akun PPPoE
   {% endif %}
  </h2>
  <span class="muted">{{ customers|length }} akun</span>
 </div>

 <input id="search"
        placeholder="Cari nama, IP, HP atau lokasi..."
        oninput="filterCustomers()">

 <div class="actions">
  <a class="btn" href="/router/{{ router_index }}?view=online">ONLINE</a>
  <a class="btn secondary" href="/router/{{ router_index }}?view=offline">OFFLINE</a>
  <a class="btn secondary" href="/router/{{ router_index }}?view=total">TOTAL</a>
 </div>

 <div id="customerList">

 {% for c in customers %}
 {% if view == 'total' or (view == 'online' and c.online) or (view == 'offline' and not c.online) %}

 <div class="customer customer-item"
 data-search="{{ (c.name ~ ' ' ~ c.address ~ ' ' ~ c.phone ~ ' ' ~ c.location)|lower }}">

  <div class="row">
   <h3>{{ c.name }}</h3>
   {% if c.online %}
    <span class="badge on">ONLINE</span>
   {% else %}
    <span class="badge off">OFFLINE</span>
   {% endif %}
  </div>

  <p>IP pelanggan: <b>{{ c.address }}</b></p>
  <p>Service: {{ c.service }} · Paket: {{ c.profile }}</p>

  {% if c.online %}
   <p class="success">Uptime: {{ c.uptime }}</p>
  {% else %}
   <p class="error">Mulai offline terpantau: {{ c.offline_since or '-' }}</p>
   <p class="error">Lama offline: <b>{{ c.offline_duration }}</b></p>
  {% endif %}

  <p class="muted">Caller ID: {{ c.caller_id }}</p>

  <hr>

  <form method="POST"
        action="/customer/{{ router_index }}/{{ c.name|urlencode }}">

   <input name="phone"
          placeholder="Nomor HP pelanggan"
          value="{{ c.phone }}">

   <input name="location"
          placeholder="Alamat / nama lokasi pelanggan"
          value="{{ c.location }}">

   <div class="grid">
    <input name="lat" placeholder="Latitude GPS" value="{{ c.lat }}">
    <input name="lon" placeholder="Longitude GPS" value="{{ c.lon }}">
   </div>

   <button class="secondary">SIMPAN DATA PELANGGAN</button>
  </form>

  {% if c.lat and c.lon %}
   <a class="btn"
      target="_blank"
      href="https://www.google.com/maps?q={{ c.lat }},{{ c.lon }}">
      LIHAT LOKASI GOOGLE MAPS
   </a>
  {% elif c.location %}
   <a class="btn"
      target="_blank"
      href="https://www.google.com/maps/search/?api=1&query={{ c.location|urlencode }}">
      CARI LOKASI GOOGLE MAPS
   </a>
  {% else %}
   <p class="muted">Lokasi belum diisi.</p>
  {% endif %}

 </div>
 {% endif %}
 {% endfor %}

 </div>
</section>
{% endif %}


<section class="card" id="router">
 <h2>Router MikroTik</h2>

 {% for router in routers %}
 <div class="customer">
  <div class="row">
   <h3>{{ router.name }}</h3>
   <span class="badge on">TERSIMPAN</span>
  </div>

  <p>{{ router.host }}:{{ router.port }}</p>

  <form method="POST" action="/router/{{ loop.index0 }}">
   <button>HUBUNGKAN & LIHAT DATA</button>
  </form>
 </div>
 {% else %}
 <p class="muted">Belum ada router.</p>
 {% endfor %}
</section>


<section class="card" id="tambah">
 <h2>Tambah Router</h2>

 <form method="POST" action="/add">
  <input name="name" placeholder="Nama router" required>
  <input name="host" placeholder="IP MikroTik / IP ZeroTier" required>
  <input name="port" type="number" value="8728" required>
  <input name="username" placeholder="Username API" required>
  <input name="password" type="password" placeholder="Password API" required>
  <button>SIMPAN ROUTER</button>
 </form>

 <p class="muted">Data router disimpan di penyimpanan internal aplikasi.</p>
</section>

</main>

<script>
function filterCustomers(){
 const input=document.getElementById("search");
 if(!input)return;

 const q=input.value.toLowerCase();

 document.querySelectorAll(".customer-item").forEach(el=>{
  el.style.display=el.dataset.search.includes(q)?"block":"none";
 });
}
</script>

</body>
</html>
"""


def render_dashboard(router_index=None, view="dashboard", error=None):
    routers = load_routers()
    selected = None
    customers = []
    online_count = 0
    offline_count = 0

    if router_index is not None:
        if 0 <= router_index < len(routers):
            selected = routers[router_index]

            if not error:
                active, secrets, fetch_error = fetch_router_data(selected)

                if fetch_error:
                    error = fetch_error
                else:
                    customers = build_customers(selected, active, secrets)
                    online_count = sum(1 for c in customers if c["online"])
                    offline_count = len(customers) - online_count
        else:
            error = "Router tidak ditemukan."

    return render_template_string(
        PAGE,
        routers=routers,
        selected=selected,
        customers=customers,
        error=error,
        view=view,
        router_index=router_index,
        online_count=online_count,
        offline_count=offline_count,
        total_count=len(customers)
    )


@app.route("/")
def index():
    return render_dashboard()


@app.route("/add", methods=["POST"])
def add_router():
    routers = load_routers()

    router = {
        "name": request.form.get("name", "").strip(),
        "host": request.form.get("host", "").strip(),
        "port": request.form.get("port", "8728").strip(),
        "username": request.form.get("username", "").strip(),
        "password": request.form.get("password", "")
    }

    if not all([
        router["name"],
        router["host"],
        router["username"],
        router["password"]
    ]):
        return "Semua data router wajib diisi.", 400

    routers.append(router)
    save_routers(routers)

    return redirect("/")


@app.route("/router/<int:index>", methods=["POST", "GET"])
def router_detail(index):
    if request.method == "POST":
        return redirect(url_for("router_detail", index=index))

    view = request.args.get("view", "dashboard")

    if view not in ["dashboard", "online", "offline", "total"]:
        view = "dashboard"

    return render_dashboard(index, view)


@app.route("/customer/<int:index>/<path:username>", methods=["POST"])
def save_customer(index, username):
    routers = load_routers()

    if index < 0 or index >= len(routers):
        return "Router tidak ditemukan.", 404

    data = load_customer_data()
    key = customer_key(routers[index], username)

    data[key] = {
        "phone": request.form.get("phone", "").strip(),
        "location": request.form.get("location", "").strip(),
        "lat": request.form.get("lat", "").strip(),
        "lon": request.form.get("lon", "").strip()
    }

    save_customer_data(data)

    return redirect(url_for("router_detail", index=index) + "?view=total")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


def start_server(data_dir=None):
    global _server_thread

    with _server_lock:
        setup_storage(data_dir)

        try:
            test = socket.create_connection(
                ("127.0.0.1", 8765),
                timeout=0.5
            )
            test.close()
            return "Server sudah berjalan."
        except OSError:
            pass

        if not (_server_thread and _server_thread.is_alive()):
            _server_thread = threading.Thread(
                target=lambda: app.run(
                    host="127.0.0.1",
                    port=8765,
                    debug=False,
                    use_reloader=False,
                    threaded=True
                ),
                daemon=True
            )
            _server_thread.start()

    for attempt in range(40):
        try:
            test = socket.create_connection(
                ("127.0.0.1", 8765),
                timeout=0.5
            )
            test.close()
            return "Server siap."
        except OSError:
            time.sleep(0.25)

    raise RuntimeError("Server tidak berhasil dijalankan pada port 8765.")
