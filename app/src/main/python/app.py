
from flask import Flask, request, redirect, render_template_string
from routeros_api import RouterOsApiPool
from pathlib import Path
import json
import os

app = Flask(__name__)

# Penyimpanan data lokal aplikasi
DATA_DIR = Path(
    os.environ.get(
        "MIKROTIK_DATA_DIR",
        str(Path(__file__).resolve().parent)
    )
)

DATA_DIR.mkdir(parents=True, exist_ok=True)
DB = DATA_DIR / "routers.json"


def load_routers():
    try:
        with open(DB, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_routers(routers):
    with open(DB, "w", encoding="utf-8") as f:
        json.dump(routers, f, indent=2)


def connect_router(router):
    return RouterOsApiPool(
        router["host"],
        username=router["username"],
        password=router["password"],
        port=int(router.get("port", 8728)),
        plaintext_login=True,
        use_ssl=False,
        ssl_verify=False,
        timeout=5
    )


PAGE = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Manajemen MikroTik</title>

<style>
* {
    box-sizing: border-box;
}

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
}

main {
    max-width: 850px;
    margin: auto;
    padding: 16px;
}

.card {
    background: #142238;
    border: 1px solid #29415f;
    border-radius: 14px;
    padding: 17px;
    margin-bottom: 15px;
}

h2 {
    margin-top: 0;
}

input, button {
    width: 100%;
    padding: 13px;
    margin: 6px 0;
    border-radius: 8px;
    border: 1px solid #405574;
    background: #0c1728;
    color: white;
}

button {
    background: #1677ee;
    border: 0;
    font-weight: bold;
}

.online {
    color: #42df91;
}

.error {
    color: #ff7979;
    overflow-wrap: anywhere;
}

table {
    width: 100%;
    border-collapse: collapse;
}

td, th {
    text-align: left;
    padding: 10px;
    border-bottom: 1px solid #344761;
}

.small {
    color: #9aabc5;
    font-size: 13px;
}

a {
    text-decoration: none;
}
</style>
</head>

<body>

<header>
    <h2>⚡ MANAJEMEN MIKROTIK</h2>
    <div class="small">
        Monitoring Router dan Pelanggan PPPoE
    </div>
</header>

<main>

<div class="card">
    <h3>Tambah Router</h3>

    <form method="post" action="/add">
        <input name="name"
               placeholder="Nama router"
               required>

        <input name="host"
               placeholder="IP MikroTik / IP ZeroTier"
               required>

        <input name="port"
               type="number"
               value="8728"
               required>

        <input name="username"
               placeholder="Username API"
               required>

        <input name="password"
               type="password"
               placeholder="Password API"
               required>

        <button type="submit">SIMPAN ROUTER</button>
    </form>

    <p class="small">
        Data router disimpan di penyimpanan lokal aplikasi.
    </p>
</div>

{% for r in routers %}
<div class="card">
    <h3>{{ r.name }}</h3>

    <p>
        Alamat: {{ r.host }}:{{ r.port }}
    </p>

    <a href="/router/{{ loop.index0 }}">
        <button>HUBUNGKAN & LIHAT PPPoE</button>
    </a>
</div>
{% endfor %}

{% if result is not none %}
<div class="card">

    <h3>Hasil Koneksi: {{ selected }}</h3>

    {% if error %}
        <p class="error">{{ error }}</p>
    {% else %}

        <p class="online">
            ● Terhubung ke MikroTik
        </p>

        <p>
            Total PPPoE aktif:
            <b>{{ result|length }}</b>
        </p>

        <div style="overflow-x:auto">
            <table>
                <tr>
                    <th>Username</th>
                    <th>IP Address</th>
                    <th>Uptime</th>
                </tr>

                {% for c in result %}
                <tr>
                    <td>{{ c.get('name', '-') }}</td>
                    <td>{{ c.get('address', '-') }}</td>
                    <td>{{ c.get('uptime', '-') }}</td>
                </tr>
                {% endfor %}

            </table>
        </div>

    {% endif %}
</div>
{% endif %}

</main>
</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(
        PAGE,
        routers=load_routers(),
        result=None,
        error=None,
        selected=""
    )


@app.route("/add", methods=["POST"])
def add_router():
    routers = load_routers()

    routers.append({
        "name": request.form["name"].strip(),
        "host": request.form["host"].strip(),
        "port": int(request.form["port"]),
        "username": request.form["username"].strip(),
        "password": request.form["password"]
    })

    save_routers(routers)
    return redirect("/")


@app.route("/router/<int:index>")
def router_detail(index):
    routers = load_routers()

    if index >= len(routers):
        return "Router tidak ditemukan", 404

    router = routers[index]
    pool = None
    result = []
    error = None

    try:
        pool = connect_router(router)
        api = pool.get_api()
        result = api.get_resource("/ppp/active").get()

    except Exception as e:
        error = "Koneksi gagal: " + str(e)

    finally:
        if pool:
            try:
                pool.disconnect()
            except Exception:
                pass

    return render_template_string(
        PAGE,
        routers=routers,
        result=result if error is None else None,
        error=error,
        selected=router["name"]
    )


def start_server(data_dir=None):
    global DATA_DIR, DB

    # Gunakan folder penyimpanan internal Android
    if data_dir:
        DATA_DIR = Path(data_dir)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        DB = DATA_DIR / "routers.json"

    app.run(
        host="127.0.0.1",
        port=8765,
        debug=False,
        use_reloader=False,
        threaded=True
    )


if __name__ == "__main__":
    start_server()
