
from flask import Flask, request, redirect, render_template_string, jsonify
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
router_locks = {}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def parse_time(value):
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return datetime.now(timezone.utc)


def duration_text(start):
    seconds = max(0, int((datetime.now(timezone.utc) - parse_time(start)).total_seconds()))
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

        try:
            secrets = api.get_resource("/ppp/secret").get()
        except Exception:
            secrets = []

        return active, secrets, None

    except Exception as e:
        return [], [], str(e)

    finally:
        if pool:
            try:
                pool.disconnect()
            except Exception:
                pass


def update_offline_state(router, active, secrets):
    states = load_states()
    key = router_key(router)
    router_states = states.setdefault(key, {})

    active_names = {
        str(item.get("name", ""))
        for item in active
        if item.get("name")
    }

    secret_names = {
        str(item.get("name", ""))
        for item in secrets
        if item.get("name")
    }

    known_names = active_names | secret_names
    timestamp = now_iso()

    for username in known_names:
        state = router_states.setdefault(username, {})

        if username in active_names:
            state["online"] = True
            state["last_online"] = timestamp
            state["offline_since"] = None
        else:
            if state.get("online") is True or not state.get("offline_since"):
                state["offline_since"] = timestamp

            state["online"] = False

    save_states(states)
    return router_states


def build_customers(router, active, secrets):
    metadata = load_customer_data()
    states = update_offline_state(router, active, secrets)

    active_map = {
        str(item.get("name", "")): item
        for item in active
        if item.get("name")
    }

    secret_map = {
        str(item.get("name", "")): item
        for item in secrets
        if item.get("name")
    }

    names = sorted(set(active_map) | set(secret_map))
    result = []

    for username in names:
        item = active_map.get(username, {})
        secret = secret_map.get(username, {})
        saved = metadata.get(customer_key(router, username), {})
        state = states.get(username, {})

        online = username in active_map
        offline_since = state.get("offline_since")

        result.append({
            "name": username,
            "address": item.get("address", "-"),
            "service": item.get("service") or secret.get("service") or "-",
            "profile": secret.get("profile", "-"),
            "uptime": item.get("uptime", "-") if online else "-",
            "caller_id": item.get("caller-id", "-"),
            "online": online,
            "offline_since": offline_since,
            "offline_duration": duration_text(offline_since) if offline_since and not online else "-",
            "phone": saved.get("phone", ""),
            "location": saved.get("location", ""),
            "lat": saved.get("lat", ""),
            "lon": saved.get("lon", "")
        })

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
body{margin:0;background:#0b1220;color:#edf3ff;font-family:Arial,sans-serif}
header{padding:20px;background:#111d30;border-bottom:1px solid #263b59;position:sticky;top:0;z-index:5}
.brand{font-size:21px;font-weight:bold}
.sub{color:#9eafc9;font-size:12px;margin-top:5px}
main{max-width:900px;margin:auto;padding:15px}
.card{background:#14243a;border:1px solid #304765;border-radius:18px;padding:17px;margin-bottom:15px}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.stat{padding:17px;border-radius:14px;min-height:100px}
.stat b{display:block;font-size:30px;margin:8px 0}
.green{background:#075b3b}.red{background:#762b3a}
.blue{background:#153d78}.purple{background:#463071}
.muted{color:#9eafc9;font-size:13px}
button,input{font:inherit}
input{width:100%;padding:13px;margin:6px 0;border-radius:10px;border:1px solid #405574;background:#0b1728;color:white}
button,.btn{display:inline-block;text-align:center;text-decoration:none;border:0;border-radius:10px;padding:12px;background:#1877ed;color:white;font-weight:bold;cursor:pointer}
button.full{width:100%;margin-top:8px}
.secondary{background:#263d5b}
.customer{background:#0c1a2d;border:1px solid #243c5a;padding:14px;border-radius:13px;margin:10px 0}
.customer h3{margin:0 0 8px}
.badge{display:inline-block;padding:5px 9px;border-radius:20px;font-size:12px;font-weight:bold}
.on{background:#075b3b;color:#8fffc0}
.off{background:#762b3a;color:#ffc0c0}
.row{display:flex;justify-content:space-between;gap:8px;align-items:center}
.actions{display:flex;gap:7px;flex-wrap:wrap;margin-top:10px}
.actions button,.actions a{flex:1;min-width:100px}
.hidden{display:none}
.error{color:#ff8585}.success{color:#62e6a0}
nav{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin-bottom:14px}
nav a{background:#1b304b;color:#d9e9ff;text-decoration:none;text-align:center;padding:12px 4px;border-radius:10px;font-size:12px}
nav a:active{background:#1877ed}
.customer small{color:#9eafc9}
hr{border:0;border-top:1px solid #304765;margin:14px 0}
@media(min-width:650px){.grid{grid-template-columns:repeat(4,1fr)}}
</style>
</head>
<body>
<header>
 <div class="brand">◈ MANAJEMEN MIKROTIK</div>
 <div class="sub">PANEL MANAJEMEN ISP · {{ selected.name if selected else "Pilih router" }}</div>
</header>
<main>

<nav>
 <a href="#dashboard">⌂<br>Dashboard</a>
 <a href="#pelanggan">♙<br>Pelanggan</a>
 <a href="#router">▣<br>Router</a>
 <a href="#tambah">＋<br>Tambah Router</a>
</nav>

<section id="dashboard" class="card">
 <div class="row">
  <div><b>Dashboard Utama</b><div class="muted">Ringkasan pelanggan PPPoE</div></div>
  {% if selected %}<span class="badge success">Router dipilih</span>{% endif %}
 </div>
 {% if selected and not error %}
 <div class="grid" style="margin-top:15px">
  <div class="stat green">● Online<b id="onlineCount">{{ online_count }}</b><small>Aktif sekarang</small></div>
  <div class="stat red">● Offline<b id="offlineCount">{{ offline_count }}</b><small>Tidak aktif</small></div>
  <div class="stat blue">♙ Total<b id="totalCount">{{ total_count }}</b><small>Akun PPPoE</small></div>
  <div class="stat purple">▣ Router<b style="font-size:19px">{{ selected.name }}</b><small>{{ selected.host }}</small></div>
 </div>
 <p class="muted">Pembaruan otomatis setiap 30 detik selama aplikasi terbuka.</p>
 <button class="full" onclick="refreshData()">↻ PERBARUI SEKARANG</button>
 {% elif error %}
 <p class="error">Koneksi gagal: {{ error }}</p>
 {% else %}
 <p class="muted">Pilih router lalu tekan Hubungkan untuk melihat statistik.</p>
 {% endif %}
</section>

<section id="router" class="card">
 <h3>Router MikroTik</h3>
 {% for router in routers %}
 <div class="customer">
  <div class="row"><b>{{ router.name }}</b><span class="badge on">Tersimpan</span></div>
  <small>{{ router.host }}:{{ router.port }}</small>
  <form method="POST" action="/router/{{ loop.index0 }}">
   <button class="full">HUBUNGKAN & LIHAT DATA</button>
  </form>
 </div>
 {% else %}
 <p class="muted">Belum ada router.</p>
 {% endfor %}
</section>

<section id="pelanggan" class="card">
 <div class="row"><h3>Daftar Pelanggan</h3><span class="muted" id="lastUpdate"></span></div>
 {% if selected and not error %}
 <input id="search" placeholder="Cari nama atau IP pelanggan..." oninput="filterCustomers()">
 <div id="customerList">
 {% for c in customers %}
 <div class="customer customer-item" data-search="{{ (c.name ~ ' ' ~ c.address)|lower }}">
  <div class="row">
   <h3>{{ c.name }}</h3>
   {% if c.online %}<span class="badge on">ONLINE</span>{% else %}<span class="badge off">OFFLINE</span>{% endif %}
  </div>
  <div>IP pelanggan: <b>{{ c.address }}</b></div>
  <div>Service: {{ c.service }} · Paket: {{ c.profile }}</div>
  {% if c.online %}
   <div>Uptime: {{ c.uptime }}</div>
  {% else %}
   <div class="error">Mulai offline: {{ c.offline_since or "Belum tercatat" }}</div>
   <div class="error">Lama offline: <b>{{ c.offline_duration }}</b></div>
  {% endif %}
  <div class="muted">Caller ID: {{ c.caller_id }}</div>
  <hr>
  <form method="POST" action="/customer/{{ router_index }}/{{ c.name }}">
   <input name="phone" placeholder="Nomor HP pelanggan" value="{{ c.phone }}">
   <input name="location" placeholder="Alamat / nama lokasi pelanggan" value="{{ c.location }}">
   <div class="grid">
    <input name="lat" placeholder="Latitude GPS" value="{{ c.lat }}">
    <input name="lon" placeholder="Longitude GPS" value="{{ c.lon }}">
   </div>
   <button class="full secondary" type="submit">SIMPAN DATA PELANGGAN</button>
  </form>
  {% if c.lat and c.lon %}
   <a class="btn full" style="display:block;margin-top:8px" target="_blank" href="https://www.google.com/maps?q={{ c.lat }},{{ c.lon }}">BUKA LOKASI DI GOOGLE MAPS</a>
  {% elif c.location %}
   <a class="btn full" style="display:block;margin-top:8px" target="_blank" href="https://www.google.com/maps/search/?api=1&query={{ c.location|urlencode }}">CARI LOKASI DI GOOGLE MAPS</a>
  {% else %}
   <small class="muted">Lokasi belum diisi.</small>
  {% endif %}
 </div>
 {% else %}
 <p class="muted">Belum ada pelanggan.</p>
 {% endfor %}
 </div>
 {% elif error %}
 <p class="error">Data pelanggan belum bisa dimuat karena koneksi gagal.</p>
 {% else %}
 <p class="muted">Hubungkan router untuk melihat pelanggan.</p>
 {% endif %}
</section>

<section id="tambah" class="card">
 <h3>Tambah Router</h3>
 <form method="POST" action="/add">
  <input name="name" placeholder="Nama router" required>
  <input name="host" placeholder="IP MikroTik / IP ZeroTier" required>
  <input name="port" type="number" value="8728" required>
  <input name="username" placeholder="Username API" required>
  <input name="password" type="password" placeholder="Password API" required>
  <button class="full">SIMPAN ROUTER</button>
 </form>
 <small class="muted">Data router disimpan di penyimpanan internal aplikasi.</small>
</section>

</main>
<script>
const routerIndex = {{ router_index if router_index is not none else "null" }};

function filterCustomers(){
 const q=document.getElementById("search").value.toLowerCase();
 document.querySelectorAll(".customer-item").forEach(el=>{
  el.style.display=el.dataset.search.includes(q)?"block":"none";
 });
}

async function refreshData(){
 if(routerIndex===null)return;
 try{
  const response=await fetch("/api/router/"+routerIndex+"/refresh");
  const data=await response.json();
  if(!response.ok||data.error)throw new Error(data.error||"Gagal memperbarui");
  document.getElementById("onlineCount").textContent=data.online;
  document.getElementById("offlineCount").textContent=data.offline;
  document.getElementById("totalCount").textContent=data.total;
  document.getElementById("lastUpdate").textContent="Baru diperbarui";
  location.reload();
 }catch(e){
  document.getElementById("lastUpdate").textContent="Gagal memperbarui";
 }
}

if(routerIndex!==null){
 setInterval(refreshData,30000);
}
</script>
</body>
</html>
"""


def render_dashboard(router_index=None, error=None):
    routers = load_routers()
    selected = None
    customers = []
    online_count = 0
    offline_count = 0

    if router_index is not None and 0 <= router_index < len(routers):
        selected = routers[router_index]

        if not error:
            active, secrets, fetch_error = fetch_router_data(selected)
            if fetch_error:
                error = fetch_error
            else:
                customers = build_customers(selected, active, secrets)
                online_count = sum(1 for c in customers if c["online"])
                offline_count = len(customers) - online_count

    return render_template_string(
        PAGE,
        routers=routers,
        selected=selected,
        customers=customers,
        error=error,
        online_count=online_count,
        offline_count=offline_count,
        total_count=len(customers),
        router_index=router_index
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

    if not all([router["name"], router["host"], router["username"], router["password"]]):
        return "Semua data router wajib diisi.", 400

    routers.append(router)
    save_routers(routers)
    return redirect("/")


@app.route("/router/<int:index>", methods=["POST", "GET"])
def router_detail(index):
    routers = load_routers()

    if index < 0 or index >= len(routers):
        return "Router tidak ditemukan.", 404

    return render_dashboard(index)


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
    return redirect(f"/router/{index}#pelanggan")


@app.route("/api/router/<int:index>/refresh")
def api_refresh(index):
    routers = load_routers()

    if index < 0 or index >= len(routers):
        return jsonify({"error": "Router tidak ditemukan"}), 404

    active, secrets, error = fetch_router_data(routers[index])

    if error:
        return jsonify({"error": error}), 502

    customers = build_customers(routers[index], active, secrets)
    online = sum(1 for c in customers if c["online"])

    return jsonify({
        "online": online,
        "offline": len(customers) - online,
        "total": len(customers),
        "updated": now_iso()
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


def start_server(data_dir=None):
    global _server_thread

    with _server_lock:
        setup_storage(data_dir)

        try:
            test = socket.create_connection(("127.0.0.1", 8765), timeout=0.5)
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
            test = socket.create_connection(("127.0.0.1", 8765), timeout=0.5)
            test.close()
            return "Server siap."
        except OSError:
            time.sleep(0.25)

    raise RuntimeError("Server tidak berhasil dijalankan pada port 8765.")
