
from flask import Flask, request, redirect, render_template_string, jsonify
from routeros_api import RouterOsApiPool
from pathlib import Path
from datetime import datetime, timezone
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

    timestamp = now_iso()

    for username in active_names | secret_names:
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
        for item in active if item.get("name")
    }

    secret_map = {
        str(item.get("name", "")): item
        for item in secrets if item.get("name")
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
            "offline_duration": (
                duration_text(offline_since)
                if offline_since and not online else "-"
            ),
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
body{
    margin:0;
    background:#0b1220;
    color:#edf3ff;
    font-family:Arial,sans-serif
}
header{
    padding:20px;
    background:#111d30;
    border-bottom:1px solid #263b59;
    position:sticky;
    top:0;
    z-index:5
}
.brand{font-size:22px;font-weight:bold}
.sub{color:#9eafc9;font-size:13px;margin-top:6px}
main{max-width:900px;margin:auto;padding:15px}
.card{
    background:#14243a;
    border:1px solid #304765;
    border-radius:18px;
    padding:17px;
    margin-bottom:15px
}
.grid{
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:10px
}
.stat{
    display:block;
    text-decoration:none;
    color:white;
    padding:17px;
    border-radius:15px;
    min-height:130px
}
.stat b{display:block;font-size:34px;margin:10px 0}
.stat small{font-size:13px}
.green{background:#075b3b}
.red{background:#762b3a}
.blue{background:#153d78}
.purple{background:#463071}
.stat:active{opacity:.75}
input,button{font:inherit}
input{
    width:100%;
    padding:14px;
    margin:6px 0;
    border-radius:10px;
    border:1px solid #405574;
    background:#0b1728;
    color:white
}
button,.btn{
    display:block;
    width:100%;
    text-align:center;
    text-decoration:none;
    border:0;
    border-radius:10px;
    padding:14px;
    margin-top:8px;
    background:#1877ed;
    color:white;
    font-weight:bold;
    cursor:pointer
}
.secondary{background:#263d5b}
.customer{
    background:#0c1a2d;
    border:1px solid #243c5a;
    padding:14px;
    border-radius:13px;
    margin:10px 0;
    overflow-wrap:anywhere
}
.customer h3{margin:0 0 9px}
.badge{
    display:inline-block;
    padding:6px 10px;
    border-radius:20px;
    font-size:12px;
    font-weight:bold
}
.on{background:#075b3b;color:#8fffc0}
.off{background:#762b3a;color:#ffc0c0}
.muted{color:#9eafc9;font-size:13px}
.error{color:#ff8585}
.row{
    display:flex;
    justify-content:space-between;
    align-items:center;
    gap:8px
}
hr{border:0;border-top:1px solid #304765;margin:14px 0}
.hidden{display:none}
.back{background:#263d5b;margin-bottom:12px}
@media(min-width:650px){
    .grid{grid-template-columns:repeat(4,1fr)}
}
</style>
</head>

<body>
<header>
    <div class="brand">◈ MANAJEMEN MIKROTIK</div>
    <div class="sub">
        PANEL ISP · {{ selected.name if selected else "Pilih router" }}
    </div>
</header>

<main>

{% if not selected %}
<section class="card">
    <h3>Pilih Router MikroTik</h3>

    {% for router in routers %}
    <div class="customer">
        <b>{{ router.name }}</b>
        <p class="muted">{{ router.host }}:{{ router.port }}</p>
        <a class="btn" href="/router/{{ loop.index0 }}">
            HUBUNGKAN ROUTER
        </a>
    </div>
    {% else %}
    <p class="muted">Belum ada router tersimpan.</p>
    {% endfor %}
</section>
{% endif %}

{% if selected and not error %}
<section class="card" id="dashboard">
    <div class="row">
        <div>
            <b>Dashboard Utama</b>
            <div class="muted">Ringkasan pelanggan PPPoE</div>
        </div>
        <span class="badge on">Terhubung</span>
    </div>

    <div class="grid" style="margin-top:15px">
        <a class="stat green" href="/router/{{ router_index }}?view=online">
            ● Online
            <b>{{ online_count }}</b>
            <small>Tekan untuk melihat</small>
        </a>

        <a class="stat red" href="/router/{{ router_index }}?view=offline">
            ● Offline
            <b>{{ offline_count }}</b>
            <small>Tekan untuk melihat</small>
        </a>

        <a class="stat blue" href="/router/{{ router_index }}?view=total">
            ♙ Total
            <b>{{ total_count }}</b>
            <small>Semua akun PPPoE</small>
        </a>

        <div class="stat purple">
            ▣ Router
            <b style="font-size:19px">{{ selected.name }}</b>
            <small>{{ selected.host }}</small>
        </div>
    </div>

    <p class="muted">
        Data diperbarui otomatis setiap 30 detik.
    </p>

    <a class="btn" href="/router/{{ router_index }}">
        ↻ PERBARUI SEKARANG
    </a>
</section>
{% endif %}

{% if error %}
<section class="card">
    <h3 class="error">Koneksi gagal</h3>
    <p class="error">{{ error }}</p>
    <a class="btn" href="/">KEMBALI</a>
</section>
{% endif %}

{% if selected and not error and view %}
<section class="card" id="daftar">
    <a class="btn back" href="/router/{{ router_index }}">
        ← KEMBALI KE DASHBOARD
    </a>

    {% if view == "online" %}
        <h2>● Pelanggan Online</h2>
        <p class="muted">Pelanggan yang sedang aktif sekarang.</p>
    {% elif view == "offline" %}
        <h2>● Pelanggan Offline</h2>
        <p class="muted">Pelanggan yang sedang tidak aktif.</p>
    {% else %}
        <h2>♙ Semua Pelanggan PPPoE</h2>
        <p class="muted">Seluruh akun PPPoE dari PPP Secret MikroTik.</p>
    {% endif %}

    <input id="search"
           placeholder="Cari nama, IP, HP atau lokasi..."
           oninput="filterCustomers()">

    <div id="customerList">
    {% for c in customers %}
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

        <div>IP pelanggan: <b>{{ c.address }}</b></div>
        <div>Service: {{ c.service }}</div>
        <div>Paket: {{ c.profile }}</div>

        {% if c.online %}
            <div>Uptime: {{ c.uptime }}</div>
        {% else %}
            <div class="error">
                Mulai offline: {{ c.offline_since or "Belum tercatat" }}
            </div>
            <div class="error">
                Lama offline: <b>{{ c.offline_duration }}</b>
            </div>
        {% endif %}

        <div class="muted">Caller ID: {{ c.caller_id }}</div>

        <hr>

        <div>Nomor HP: {{ c.phone or "-" }}</div>
        <div>Lokasi: {{ c.location or "Belum diisi" }}</div>

        <form method="POST"
              action="/customer/{{ router_index }}/{{ c.name }}">
            <input name="phone"
                   placeholder="Nomor HP pelanggan"
                   value="{{ c.phone }}">

            <input name="location"
                   placeholder="Alamat / nama lokasi pelanggan"
                   value="{{ c.location }}">

            <div class="grid">
                <input name="lat"
                       placeholder="Latitude GPS"
                       value="{{ c.lat }}">

                <input name="lon"
                       placeholder="Longitude GPS"
                       value="{{ c.lon }}">
            </div>

            <button class="secondary" type="submit">
                SIMPAN DATA PELANGGAN
            </button>
        </form>

        {% if c.lat and c.lon %}
        <a class="btn"
           target="_blank"
           href="https://www.google.com/maps?q={{ c.lat }},{{ c.lon }}">
            BUKA LOKASI GOOGLE MAPS
        </a>
        {% elif c.location %}
        <a class="btn"
           target="_blank"
           href="https://www.google.com/maps/search/?api=1&query={{ c.location|urlencode }}">
            CARI LOKASI GOOGLE MAPS
        </a>
        {% endif %}
    </div>
    {% else %}
        <p class="muted">Tidak ada pelanggan pada kategori ini.</p>
    {% endfor %}
    </div>
</section>
{% endif %}

{% if not selected %}
<section class="card" id="tambah">
    <h3>＋ Tambah Router</h3>

    <form method="POST" action="/add">
        <input name="name" placeholder="Nama router" required>
        <input name="host" placeholder="IP MikroTik / IP ZeroTier" required>
        <input name="port" type="number" value="8728" required>
        <input name="username" placeholder="Username API" required>
        <input name="password" type="password" placeholder="Password API" required>
        <button>SIMPAN ROUTER</button>
    </form>

    <p class="muted">
        Data router disimpan di penyimpanan internal aplikasi.
    </p>
</section>
{% endif %}

</main>

<script>
function filterCustomers(){
    const input = document.getElementById("search");
    if(!input) return;

    const q = input.value.toLowerCase();

    document.querySelectorAll(".customer-item").forEach(el => {
        el.style.display =
            el.dataset.search.includes(q) ? "block" : "none";
    });
}

const routerIndex = {{ router_index if router_index is not none else "null" }};

if(routerIndex !== null){
    setTimeout(() => {
        location.reload();
    }, 30000);
}
</script>

</body>
</html>
"""


def render_dashboard(router_index=None, view=None):
    routers = load_routers()
    selected = None
    customers = []
    error = None

    if router_index is not None:
        if router_index < 0 or router_index >= len(routers):
            return "Router tidak ditemukan.", 404

        selected = routers[router_index]

        active, secrets, error = fetch_router_data(selected)

        if not error:
            customers = build_customers(selected, active, secrets)

    online_count = sum(1 for c in customers if c["online"])
    offline_count = len(customers) - online_count

    if view == "online":
        customers = [c for c in customers if c["online"]]
    elif view == "offline":
        customers = [c for c in customers if not c["online"]]
    elif view == "total":
        pass
    else:
        view = None

    return render_template_string(
        PAGE,
        routers=routers,
        selected=selected,
        customers=customers,
        error=error,
        online_count=online_count,
        offline_count=offline_count,
        total_count=online_count + offline_count,
        router_index=router_index,
        view=view
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


@app.route("/router/<int:index>")
def router_detail(index):
    view = request.args.get("view", "")
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

    return redirect(f"/router/{index}?view=total")


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

    raise RuntimeError(
        "Server tidak berhasil dijalankan pada port 8765."
    )
