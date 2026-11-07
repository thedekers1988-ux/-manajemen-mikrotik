
from flask import Flask, request, redirect, render_template_string
from routeros_api import RouterOsApiPool
from pathlib import Path
import json
import os
import threading
import socket
import time

app = Flask(__name__)

DATA_DIR = Path(__file__).resolve().parent
DB = DATA_DIR / "routers.json"
_server_thread = None
_server_lock = threading.Lock()


def setup_storage(data_dir=None):
    global DATA_DIR, DB

    if data_dir:
        DATA_DIR = Path(data_dir)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB = DATA_DIR / "routers.json"


def load_routers():
    try:
        with open(DB, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_routers(routers):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(DB, "w", encoding="utf-8") as f:
        json.dump(routers, f, indent=2)


def connect_router(router):
    pool = RouterOsApiPool(
        router["host"],
        username=router["username"],
        password=router["password"],
        port=int(router.get("port", 8728)),
        plaintext_login=True,
        use_ssl=False,
        ssl_verify=False
    )
    return pool


PAGE = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Manajemen MikroTik</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0;
    background: #0b1220;
    color: #edf3ff;
    font-family: Arial, sans-serif;
}
header {
    padding: 22px;
    background: #111d30;
    border-bottom: 1px solid #263b59;
    font-size: 24px;
    font-weight: bold;
}
main {
    max-width: 850px;
    margin: auto;
    padding: 16px;
}
.card {
    background: #14243a;
    border: 1px solid #304765;
    border-radius: 18px;
    padding: 22px;
    margin-bottom: 18px;
}
h2 { margin-top: 0; }
input, button {
    width: 100%;
    padding: 14px;
    margin: 6px 0;
    border-radius: 10px;
    font-size: 16px;
}
input {
    background: #0b1728;
    color: white;
    border: 1px solid #405574;
}
button {
    background: #1877ed;
    color: white;
    border: 0;
    font-weight: bold;
    cursor: pointer;
}
.router {
    border-top: 1px solid #405574;
    padding-top: 15px;
    margin-top: 15px;
}
.error { color: #ff8585; }
.success { color: #62e6a0; }
.customer {
    background: #0c1a2d;
    padding: 12px;
    border-radius: 10px;
    margin: 8px 0;
    overflow-wrap: anywhere;
}
.small { color: #9eafc9; font-size: 14px; }
</style>
</head>
<body>
<header>MANAJEMEN MIKROTIK</header>
<main>

<div class="card">
<h2>Tambah Router MikroTik</h2>

<form method="POST" action="/add">
<input name="name" placeholder="Nama Router" required>
<input name="host" placeholder="IP MikroTik / IP ZeroTier" required>
<input name="port" type="number" value="8728" placeholder="Port API" required>
<input name="username" placeholder="Username API" required>
<input name="password" type="password" placeholder="Password API" required>
<button type="submit">SIMPAN ROUTER</button>
</form>

<p class="small">Data disimpan di penyimpanan internal aplikasi.</p>
</div>

<div class="card">
<h2>Daftar Router</h2>

{% if routers %}
    {% for router in routers %}
    <div class="router">
        <h2>{{ router.name }}</h2>
        <p>Alamat: {{ router.host }}:{{ router.port }}</p>

        <form method="POST" action="/router/{{ loop.index0 }}">
            <button type="submit">HUBUNGKAN & LIHAT PPPoE</button>
        </form>
    </div>
    {% endfor %}
{% else %}
<p>Belum ada router. Silakan tambahkan router.</p>
{% endif %}
</div>

{% if selected %}
<div class="card">
<h2>Hasil Koneksi: {{ selected.name }}</h2>

{% if error %}
<p class="error">● Koneksi gagal</p>
<p class="error">{{ error }}</p>
{% else %}
<p class="success">● Koneksi berhasil</p>
<h3>PPPoE Aktif: {{ customers|length }}</h3>

{% for customer in customers %}
<div class="customer">
<strong>{{ customer.name or "Tanpa nama" }}</strong><br>
IP: {{ customer.address or "-" }}<br>
Service: {{ customer.service or "-" }}<br>
Uptime: {{ customer.uptime or "-" }}<br>
Caller ID: {{ customer["caller-id"] or "-" }}
</div>
{% else %}
<p>Belum ada pelanggan PPPoE aktif.</p>
{% endfor %}
{% endif %}
</div>
{% endif %}

</main>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    return render_template_string(
        PAGE,
        routers=load_routers(),
        selected=None,
        customers=[],
        error=None
    )


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


@app.route("/router/<int:index>", methods=["POST"])
def router_detail(index):
    routers = load_routers()

    if index < 0 or index >= len(routers):
        return "Router tidak ditemukan.", 404

    selected = routers[index]
    customers = []
    error = None
    pool = None

    try:
        pool = connect_router(selected)
        api = pool.get_api()

        resource = api.get_resource("/ppp/active")
        customers = resource.get()

    except Exception as e:
        error = str(e)

    finally:
        if pool:
            try:
                pool.disconnect()
            except Exception:
                pass

    return render_template_string(
        PAGE,
        routers=routers,
        selected=selected,
        customers=customers,
        error=error
    )


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}


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

        if _server_thread and _server_thread.is_alive():
            pass
        else:
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
