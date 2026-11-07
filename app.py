from flask import Flask, request, render_template_string
import json, os
import urllib.request, urllib.parse
from routeros_api import RouterOsApiPool

app = Flask(__name__)
DB = os.path.expanduser("~/manajemen-mikrotik/routers.json")

def load_routers():
    try:
        with open(DB) as f:
            return json.load(f)
    except:
        return []

PAGE = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Manajemen MikroTik</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#071426;color:#eaf2ff;font-family:Arial,sans-serif}
header{padding:18px 20px;background:#102746;border-bottom:1px solid #294565}
header h2{margin:0;font-size:22px}
header small{color:#abc1dc}
main{max-width:900px;margin:auto;padding:18px}
nav{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:30px}
nav a{background:#102b49;border:1px solid #29496b;color:#b8cce4;
padding:15px 17px;border-radius:14px;text-decoration:none;font-weight:bold}
nav a.active{background:linear-gradient(120deg,#1689e8,#22b7d9);color:#071426}
h1{font-size:29px;margin-bottom:8px}
.subtitle{color:#9fb5d0;margin-bottom:28px}
.stats{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
.card{background:linear-gradient(145deg,#102b49,#0c2038);
border:1px solid #203e60;border-radius:22px;padding:22px;margin-bottom:18px}
.stat-label{color:#9fb5d0;font-size:15px}
.stat-number{font-size:42px;font-weight:bold;margin:18px 0 8px}
.green{color:#36d69b}.red{color:#ff8098}.blue{color:#eaf2ff}
.hint{color:#91aaca}
.section-head{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}
button,.btn{border:0;background:#163d60;color:#eaf2ff;padding:13px 17px;
border-radius:12px;font-weight:bold;text-decoration:none;display:inline-block}
table{width:100%;border-collapse:collapse;margin-top:25px;min-width:470px}
th,td{text-align:left;padding:14px 8px;border-bottom:1px solid #294766}
th{color:#9fb5d0}
.online{color:#36d69b;font-weight:bold}.offline{color:#ff8098;font-weight:bold}
a.ip{color:#8bcaff;text-decoration:none}
.table-wrap{overflow-x:auto}
footer{text-align:center;color:#819ab7;padding:12px}
select{background:#091d33;color:white;border:1px solid #345574;
border-radius:9px;padding:12px;width:100%;margin-top:10px}
.notice{background:#3b2634;color:#ffd8df;padding:14px;border-radius:12px;margin-top:15px}
@media(max-width:480px){
 main{padding:14px}.card{padding:18px}.stat-number{font-size:36px}
 nav a{padding:13px 14px;font-size:14px}
}

/* DESAIN DASHBOARD PREMIUM */
body {
    background: #080f1d;
    color: #e8f0fb;
}
header {
    background: #101e31;
    border-bottom: 1px solid #263c56;
    padding: 22px 25px 22px 255px;
}
header h2 {
    font-size: 23px;
    letter-spacing: 1px;
}
main {
    max-width: none;
    margin: 0 0 0 235px;
    padding: 25px;
}
nav {
    position: fixed;
    top: 0;
    bottom: 0;
    left: 0;
    width: 220px;
    padding: 100px 14px 20px;
    margin: 0;
    background: #101e31;
    border-right: 1px solid #263c56;
    display: flex;
    flex-direction: column;
    flex-wrap: nowrap;
    gap: 8px;
    overflow-y: auto;
    z-index: 100;
}
nav a {
    display: block;
    padding: 14px 15px;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 10px;
    color: #a9bdd5;
    font-size: 14px;
}
nav a:hover, nav a.active {
    background: linear-gradient(110deg,#147dcc,#176c9c);
    color: white;
    border-color: #258dd0;
}
h1 {
    font-size: 30px;
    letter-spacing: .3px;
}
.subtitle, .hint {
    color: #8fa8c5;
}
.card {
    background: linear-gradient(145deg,#14283e,#101e31);
    border: 1px solid #263e59;
    border-radius: 16px;
    box-shadow: 0 8px 24px rgba(0,0,0,.12);
}
.stats {
    gap: 14px;
}
.stat-number {
    font-size: 38px;
}
button, .btn {
    background: #176fae;
    border-radius: 9px;
}
table th {
    color: #8fa8c5;
}
@media(max-width:700px) {
    header {
        padding: 18px 15px;
    }
    header h2 {
        font-size: 19px;
    }
    main {
        margin: 0;
        padding: 15px;
    }
    nav {
        position: sticky;
        top: 0;
        width: 100%;
        height: auto;
        padding: 10px;
        flex-direction: row;
        flex-wrap: nowrap;
        overflow-x: auto;
        background: #101e31;
        border: 1px solid #263c56;
        border-radius: 0 0 12px 12px;
    }
    nav a {
        flex: 0 0 auto;
        white-space: nowrap;
        padding: 12px;
    }
    .stats {
        grid-template-columns: repeat(2,minmax(0,1fr));
        gap: 10px;
    }
    .card {
        padding: 15px;
    }
}


/* SIDEBAR NETWORK MANAGER */
#menu-toggle {display:none}
.menu-button {display:none}
.sidebar {
 position:fixed;top:0;bottom:0;left:0;width:230px;
 padding:25px 15px;background:#101d30;
 border-right:1px solid #263d58;z-index:200;
 display:flex;flex-direction:column;gap:7px;
 overflow-y:auto
}
.sidebar .side-brand {
 font-size:19px;letter-spacing:2px;
 padding:8px 12px 28px;color:#8eb9dc
}
.sidebar .side-brand b {color:#fff}
.sidebar .side-label {
 color:#66819f;font-size:11px;font-weight:bold;
 letter-spacing:1.5px;padding:18px 12px 7px
}
.sidebar a {
 display:block;padding:13px 14px;border-radius:9px;
 color:#a9bdd5;text-decoration:none;font-size:14px;
 background:transparent;border:1px solid transparent
}
.sidebar a:hover,.sidebar a.active {
 background:linear-gradient(110deg,#147dcc,#176c9c);
 color:white;border-color:#258dd0
}
@media(max-width:700px) {
 .sidebar {
  top:0;left:0;width:260px;
  transform:translateX(-105%);
  transition:transform .25s ease;
  padding-top:75px;
  box-shadow:8px 0 30px #0008
 }
 #menu-toggle:checked ~ .sidebar {transform:translateX(0)}
 .menu-button {
  display:inline-block;position:sticky;top:8px;
  z-index:210;background:#176fae;color:white;
  padding:12px 17px;border-radius:9px;
  font-weight:bold;margin:0 0 15px;cursor:pointer
 }
 main {margin:0;padding:15px}
 nav.sidebar {flex-direction:column;flex-wrap:nowrap}
}

</style>
</head>
<body>
<header>
<h2>☰ MANAJEMEN MIKROTIK</h2>
<small>Pantau router dan pelanggan internet</small>
</header>
<main>
<input type="checkbox" id="menu-toggle">
<label class="menu-button" for="menu-toggle">☰ MENU</label>
<nav class="sidebar">
<div class="side-brand">NETWORK<br><b>MANAGER</b></div>
<div class="side-label">MENU UTAMA</div>
<a class="active" href="/">▦ Dashboard</a>
<a href="#router">▣ MikroTik</a>
<a href="/pppoe/menu?router={{selected}}">◎ PPPoE</a>
<a href="/pppoe/list">♙ Pelanggan</a>
<div class="side-label">MANAJEMEN</div>
<a href="/pembayaran/lunas">✓ Pelanggan Lunas</a>
<a href="/pembayaran/belum-lunas">◷ Belum Lunas</a>
<a href="/whatsapp">✉ WhatsApp</a>
<a href="#informasi">⚙ Informasi</a>
</nav>

<h1>Dashboard</h1>
<div class="subtitle">Pantau router dan pelanggan internet.</div>

{% if error %}
<div class="notice">Gagal membaca data MikroTik: {{error}}</div>
{% endif %}

<div class="stats">
<div class="card">
<div class="stat-label">Total Pelanggan</div>
<div class="stat-number blue">{{total}}</div>
<div class="hint">PPPoE Secret</div>
</div>
<div class="card">
<div class="stat-label">Online</div>
<div class="stat-number green">{{online}}</div>
<div class="green">Terhubung</div>
</div>
<a class="card" href="/?router={{selected}}&show=offline#offline-list"
style="display:block;text-decoration:none;color:inherit">
<div class="stat-label">Offline — KLIK DI SINI</div>
<div class="stat-number red">{{offline}}</div>
<div class="red">Lihat nama pelanggan yang tidak terhubung →</div>
</a>
<div class="card">
<div class="stat-label">Router</div>
<div class="stat-number blue">{{router_count}}</div>
<div class="hint">Router tersimpan</div>
</div>
</div>

<div class="card" id="router">
<div class="section-head">
<h3>MikroTik</h3>
<span class="green">{{router_name}}</span>
</div>
<form method="get" action="/">
<label class="hint">Pilih router</label>
<select name="router" onchange="this.form.submit()">
{% for r in routers %}
<option value="{{loop.index0}}" {% if loop.index0==selected %}selected{% endif %}>
{{r.name}} — {{r.host}}
</option>
{% endfor %}
</select>
</form>
</div>

<div class="card" id="pelanggan">
<div class="section-head">
<h3>IP Pelanggan</h3>

<form method="get" action="/" style="display:flex;gap:8px;flex-wrap:wrap">
<input type="hidden" name="router" value="{{selected}}">
<input name="q" value="{{q}}" placeholder="Cari nama, username, atau IP pelanggan..."
style="min-width:180px;flex:1;padding:13px;border-radius:9px;background:#091d33;color:white;border:1px solid #345574">
<button class="btn" type="submit">🔍 CARI</button>
</form>

</div>
<p class="hint">Daftar IP pelanggan ditampilkan langsung di Dashboard. Ketuk IP untuk membukanya di Chrome.</p>
<div class="table-wrap">
<table>
<tr><th>Username PPPoE</th><th>IP Address</th><th>Status</th><th>Aksi</th></tr>
{% for c in active_customers %}
<tr>
<td>{{c.name}}</td>
<td>{% if c.ip != '-' %}<a class="ip" href="http://{{c.ip}}" target="_blank">{{c.ip}}</a>{% else %}-{% endif %}</td>
<td class="{{c.status_class}}">{{c.status}}</td>
<td>{% if c.map_url %}
<a class="btn" href="{{c.map_url}}" target="_blank">📍 LIHAT PETA</a>
{% else %}<span class="hint">BELUM ADA KOORDINAT</span>{% endif %}</td>
</tr>
{% endfor %}

</table>
</div>
{% if not customers %}
<p class="hint">Belum ada data pelanggan PPPoE.</p>
{% endif %}
</div>

{% if request.args.get('show') == 'offline' %}
<div class="card" id="offline-list">
<h3 class="red">Daftar Pelanggan OFFLINE ({{offline}})</h3>
<p class="hint">Daftar ini dibaca langsung dari MikroTik.</p>
<div class="table-wrap">
<table>
<tr><th>Username</th><th>Waktu terakhir online</th><th>Lokasi</th></tr>
{% for c in customers if c.status == 'OFFLINE' %}
<tr>
<td>{{c.name}}</td>
<td>{{c.last_offline}}</td>
<td>
{% if c.map_url %}
<a class="btn" href="{{c.map_url}}" target="_blank">📍 LIHAT PETA</a>
{% else %}
<span class="hint">BELUM ADA KOORDINAT</span>
{% endif %}
</td>
</tr>
{% else %}
<tr><td colspan="3">Tidak ada pelanggan offline.</td></tr>
{% endfor %}
</table>
</div>
<a class="btn" href="/?router={{selected}}">Kembali ke Dashboard</a>
</div>
{% endif %}

<div class="card" id="hotspot">
<h3>Tambah Hotspot</h3>
<p class="hint">Menu voucher Hotspot akan dibuat pada tahap berikutnya.</p>
</div>
<div class="card" id="informasi">
<h3>Informasi</h3>
<p class="hint">Pengaturan informasi dan pesan WhatsApp akan dibuat pada tahap berikutnya.</p>
</div>
<footer>Data langsung dari MikroTik • Mode baca saja</footer>
</main>
</body>
</html>
"""

@app.route("/")
def home():
    routers = load_routers()
    selected = request.args.get("router", "0")
    try:
        selected = int(selected)
        if selected < 0 or selected >= len(routers):
            selected = 0
    except:
        selected = 0

    customers = []
    active_customers = []
    error = None
    router_name = "Belum ada router"
    online = 0
    total = 0

    if routers:
        r = routers[selected]
        router_name = r.get("name", "MikroTik")
        pool = None
        try:
            pool = RouterOsApiPool(
                host=r["host"],
                username=r["username"],
                password=r["password"],
                port=int(r["port"]),
                plaintext_login=True
            )
            api = pool.get_api()
            secrets = api.get_resource("/ppp/secret").get()
            active = api.get_resource("/ppp/active").get()
            active_map = {x.get("name"): x for x in active}

            metadata = read_meta()
            for s in secrets:
                if s.get("service") not in ("pppoe", "any", None):
                    continue
                name = s.get("name", "-")
                a = active_map.get(name)
                meta = metadata.get(r["host"] + "|" + name, {})
                lat = meta.get("latitude", "")
                lon = meta.get("longitude", "")
                map_url = (
                    "https://www.google.com/maps/@?api=1&map_action=map&center=" + str(lat) + "," + str(lon) + "&zoom=18&basemap=satellite"
                    if lat and lon else ""
                )
                customers.append({
                    "name": name,
                    "ip": a.get("address", "-") if a else "-",
                    "status": "ONLINE" if a else "OFFLINE",
                    "status_class": "online" if a else "offline",
                    "last_offline": s.get("last-logged-out", "-"),
                    "map_url": map_url
                })
                if a:
                    active_customers.append(customers[-1])

            total = len(customers)
            online = sum(1 for c in customers if c["status"] == "ONLINE")

        except Exception as e:
            error = str(e)[:200]
        finally:
            if pool:
                try:
                    pool.disconnect()
                except:
                    pass

    q = request.args.get("q", "").strip().lower()
    if q:
        active_customers = [
            c for c in active_customers
            if q in c["name"].lower() or q in c["ip"].lower()
        ]

    return render_template_string(
        PAGE,
        routers=routers,
        selected=selected,
        router_name=router_name,
        router_count=len(routers),
        customers=customers,
        active_customers=active_customers,
        q=q,
        total=total,
        online=online,
        offline=total-online,
        error=error
    )



META_DB = os.path.expanduser("~/manajemen-mikrotik/customers_meta.json")

PPPOE_PAGE = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tambah PPPoE</title>
<style>
body{margin:0;background:#071426;color:#eaf2ff;font-family:Arial;padding:18px}
main{max-width:600px;margin:auto}
.card{background:#102b49;border:1px solid #29496b;border-radius:18px;padding:20px}
input,select{width:100%;box-sizing:border-box;padding:14px;margin:8px 0 17px;
background:#091d33;color:white;border:1px solid #345574;border-radius:10px}
button,.btn{display:inline-block;background:#1689e8;color:white;border:0;
padding:14px 18px;border-radius:10px;font-weight:bold;text-decoration:none}
label{color:#b8cce4}
.notice{padding:13px;background:#3b2634;border-radius:10px;margin-bottom:15px}
.success{background:#164432}
</style>
</head>
<body>
<main>
<h2>＋ Tambah Pelanggan PPPoE</h2>
<p>Router: <b>{{router_name}}</b></p>
<div class="card">
{% if message %}
<div class="notice {{'success' if ok else ''}}">{{message}}</div>
{% endif %}
<form method="post">
<input type="hidden" name="router" value="{{selected}}">
<label>Nama pelanggan</label>
<input name="customer_name" placeholder="Nama pelanggan" required>
<label>Username PPPoE</label>
<input name="username" placeholder="Contoh: pelanggan001" required>
<label>Password PPPoE</label>
<input name="password" type="password" placeholder="Password PPPoE" required>
<label>Nomor HP WhatsApp</label>
<input name="phone" type="tel" placeholder="Contoh: 08xxxxxxxxxx">
<label>Profile PPPoE</label>
<select name="profile" required>
{% for profile in profiles %}
<option value="{{profile}}">{{profile}}</option>
{% endfor %}
</select>
<label>Lokasi pemasangan pelanggan</label>
<p style="color:#b8cce4">Pilih lokasi rumah pelanggan melalui peta atau GPS.</p>
<button type="button" onclick="ambilLokasi()">📍 Gunakan Lokasi Saya (GPS)</button>
<div id="customer-map" style="height:600px;min-height:600px;width:100%;border-radius:12px;margin:10px 0 15px;overflow:hidden"></div>
<input type="hidden" name="latitude" id="latitude">
<input type="hidden" name="longitude" id="longitude">
<p id="map-coordinates" style="color:#9fb5d0">Belum memilih lokasi.</p>
<label>Tanggal jatuh tempo</label>
<input name="due_date" type="date">
<button type="submit">Simpan ke MikroTik</button>
</form>
<p><a class="btn" href="/?router={{selected}}">Kembali ke Dashboard</a></p>
</div>
</main>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const map = L.map('customer-map').setView([1.4748, 124.8421], 13);
const jalan = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap'
});
const satelit = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
  attribution: 'Esri World Imagery'
});
jalan.addTo(map);
L.control.layers({'Peta Jalan': jalan, 'Satelit': satelit}).addTo(map);
let marker = null;
function pilihLokasi(lat, lon) {
  document.getElementById('latitude').value = lat.toFixed(7);
  document.getElementById('longitude').value = lon.toFixed(7);
  document.getElementById('map-coordinates').textContent =
    'Lokasi dipilih: ' + lat.toFixed(6) + ', ' + lon.toFixed(6);
  if (marker) marker.setLatLng([lat, lon]);
  else marker = L.marker([lat, lon]).addTo(map);
}
map.on('click', function(e) {
  pilihLokasi(e.latlng.lat, e.latlng.lng);
});
function ambilLokasi() {
  if (!navigator.geolocation) {
    alert('GPS tidak didukung browser ini.');
    return;
  }
  document.getElementById('map-coordinates').textContent = 'Mengambil lokasi GPS...';
  navigator.geolocation.getCurrentPosition(function(pos) {
    const lat = pos.coords.latitude;
    const lon = pos.coords.longitude;
    pilihLokasi(lat, lon);
    map.setView([lat, lon], 18);
  }, function(err) {
    alert('GPS gagal: ' + err.message + '. Aktifkan lokasi HP dan izinkan Chrome.');
  }, {enableHighAccuracy:true, timeout:20000, maximumAge:0});
}
</script>
</body>
</html>
"""

def read_meta():
    try:
        with open(META_DB) as f:
            return json.load(f)
    except:
        return {}

def save_meta(data):
    temp = META_DB + ".tmp"
    with open(temp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(temp, META_DB)

@app.route("/pppoe", methods=["GET", "POST"])
def pppoe_page():
    routers = load_routers()
    if not routers:
        return "Belum ada router tersimpan."

    try:
        selected = int(request.values.get("router", "0"))
        if selected < 0 or selected >= len(routers):
            selected = 0
    except:
        selected = 0

    r = routers[selected]
    router_name = r.get("name", "MikroTik")
    pool = None
    profiles = []
    message = None
    ok = False

    try:
        pool = RouterOsApiPool(
            host=r["host"],
            username=r["username"],
            password=r["password"],
            port=int(r["port"]),
            plaintext_login=True
        )
        api = pool.get_api()
        secret_resource = api.get_resource("/ppp/secret")
        profiles = sorted([
            x.get("name") for x in api.get_resource("/ppp/profile").get()
            if x.get("name")
        ])

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            key = key_prefix + username
            wa_result = "missing"

            if key in metadata:
                old_status = metadata[key].get(
                    "payment_status", "belum-lunas"
                )
                new_status = (
                    "lunas" if status == "belum-lunas"
                    else "belum-lunas"
                )

                metadata[key]["payment_status"] = new_status
                save_meta(metadata)

                if new_status == "lunas" and old_status != "lunas":
                    customer_name = metadata[key].get(
                        "customer_name", username
                    )
                    phone = metadata[key].get("phone", "")
                    message = (
                        f"Halo {customer_name}, pembayaran internet "
                        f"PPPoE Anda telah kami terima. "
                        f"Status pembayaran sekarang LUNAS. "
                        f"Terima kasih."
                    )

                    if phone and phone != "-":
                        ok, _ = fonnte_send(phone, message)
                        wa_result = "sent" if ok else "failed"
                    else:
                        wa_result = "missing"
                elif new_status == "lunas":
                    wa_result = "already"
                else:
                    wa_result = "not-sent"

            return __import__("flask").redirect(
                f"/pembayaran/{status}?router={selected}&wa={wa_result}"
            )

        for item in secrets:
            if item.get("service") not in ("pppoe", "any", None):
                continue
            name = item.get("name", "-")
            if q and q not in name.lower():
                continue
            a = active_map.get(name)
            meta = metadata.get(r["host"] + "|" + name, {})
            lat, lon = meta.get("latitude", ""), meta.get("longitude", "")
            map_url = "https://www.google.com/maps/@?api=1&map_action=map&center=" + str(lat) + "," + str(lon) + "&zoom=18&basemap=satellite" if lat and lon else ""
            is_online = bool(a)
            online += int(is_online)
            customers.append({
                "name": name,
                "ip": a.get("address", "-") if a else "-",
                "profile": item.get("profile", "-"),
                "phone": meta.get("phone", "-") or "-",
                "status": "ONLINE" if is_online else "OFFLINE",
                "status_class": "online" if is_online else "offline",
                "map_url": map_url
            })
        customers.sort(key=lambda x: x["name"].lower())
    finally:
        if pool:
            pool.disconnect()

    return render_template_string(
        PPPOE_LIST_PAGE,
        router_name=r.get("name", "MikroTik"),
        selected=selected, customers=customers,
        total=len(customers), online=online,
        offline=len(customers)-online, q=q
    )



PPPOE_MENU = """
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Manajemen PPPoE</title>
<style>
body{margin:0;background:#071426;color:#eaf2ff;font-family:Arial;padding:20px}
main{max-width:850px;margin:auto}
h1{font-size:27px}
p{color:#9fb5d0}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}
.item{background:#102b49;border:1px solid #29496b;border-radius:17px;padding:22px 14px;color:#eaf2ff;text-decoration:none;min-height:95px}
.item b{display:block;font-size:17px;margin-bottom:9px}
.item small{color:#9fb5d0}
.btn{display:inline-block;background:#1689e8;color:white;padding:12px 16px;border-radius:10px;text-decoration:none;margin:10px 0}
@media(max-width:480px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body><main>
<h1>● MANAJEMEN PPPoE</h1>
<p>Router: <b>{{router_name}}</b></p>
<a class="btn" href="/?router={{selected}}">← Dashboard</a>
<div class="grid">
<a class="item" href="/pppoe/list?router={{selected}}">
<b>☷ Daftar Semua Secret PPPoE</b>
<small>Semua pelanggan, bisa dicari dan diedit</small>
</a>
<a class="item" href="/pppoe?router={{selected}}">
<b>＋ Tambah User PPPoE</b>
<small>Tambah pelanggan baru beserta lokasi pemasangan</small>
</a>
<a class="item" href="/pembayaran/lunas?router={{selected}}">
<b>✓ Pelanggan LUNAS</b>
<small>Daftar pelanggan yang sudah membayar</small>
</a>
<a class="item" href="/pembayaran/belum-lunas?router={{selected}}">
<b>○ Pelanggan BELUM LUNAS</b>
<small>Daftar pelanggan yang belum membayar</small>
</a>
</div>
</main></body></html>
"""

@app.route("/pppoe/menu")
def pppoe_menu():
    routers = load_routers()
    if not routers:
        return "Belum ada router tersimpan."
    try:
        selected = int(request.args.get("router", "0"))
        if selected < 0 or selected >= len(routers):
            selected = 0
    except:
        selected = 0
    return render_template_string(
        PPPOE_MENU,
        selected=selected,
        router_name=routers[selected].get("name", "MikroTik")
    )




@app.route("/pembayaran/<status>", methods=["GET", "POST"])
def pembayaran(status):
    if status not in ("lunas", "belum-lunas"):
        return "Status pembayaran tidak valid."

    routers = load_routers()
    if not routers:
        return "Belum ada router tersimpan."

    try:
        selected = int(request.args.get("router", "0"))
        if selected < 0 or selected >= len(routers):
            selected = 0
    except:
        selected = 0

    r = routers[selected]
    key_prefix = r["host"] + "|"
    metadata = read_meta()
    pool = None
    customers = []
    q = request.args.get("q", "").strip().lower()
    try:
        pool = RouterOsApiPool(
            host=r["host"], username=r["username"],
            password=r["password"], port=int(r["port"]),
            plaintext_login=True
        )
        api = pool.get_api()
        secrets = api.get_resource("/ppp/secret").get()

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            key = key_prefix + username
            wa_result = "missing"

            if key in metadata:
                meta_paid = metadata[key].get("payment_status", "belum-lunas")
                meta = metadata[key]
                new_status = (
                    "lunas" if status == "belum-lunas" else "belum-lunas"
                )
                meta["payment_status"] = new_status
                save_meta(metadata)

                if new_status == "lunas":
                    if meta_paid == "lunas":
                        wa_result = "already"
                    else:
                        phone = meta.get("phone", "")
                        settings_path = os.path.expanduser(
                            "~/manajemen-mikrotik/wa_settings.json"
                        )
                        try:
                            with open(settings_path) as f:
                                wa_settings = json.load(f)
                            template = wa_settings.get("pesan_lunas", "")
                            message = template.format(
                                nama=meta.get("customer_name", username),
                                username=username,
                                jatuh_tempo=meta.get("due_date", "-")
                            )
                            if phone and phone != "-" and message:
                                ok, result = fonnte_send(phone, message)
                                wa_result = "sent" if ok else "failed"
                                print("WhatsApp lunas:", result)
                            else:
                                wa_result = "missing"
                        except Exception as e:
                            wa_result = "failed"
                            print("Gagal menyiapkan pesan lunas:", str(e))

            return __import__("flask").redirect(
                f"/pembayaran/{status}?router={selected}&wa={wa_result}"
            )

        for item in secrets:
            if item.get("service") not in ("pppoe", "any", None):
                continue
            username = item.get("name", "-")
            meta = metadata.get(key_prefix + username, {})
            paid = meta.get("payment_status", "belum-lunas")
            if (status == "lunas" and paid != "lunas") or (
                status == "belum-lunas" and paid == "lunas"
            ):
                continue
            customers.append({
                "username": username,
                "name": meta.get("customer_name", username),
                "phone": meta.get("phone", "-") or "-",
                "due_date": meta.get("due_date", "-") or "-"
            })
        if q:
            customers = [
                c for c in customers
                if q in c["name"].lower()
                or q in c["username"].lower()
                or q in c["phone"].lower()
            ]
        customers.sort(key=lambda x: x["username"].lower())
    finally:
        if pool:
            pool.disconnect()

    title = "PELANGGAN LUNAS" if status == "lunas" else "PELANGGAN BELUM LUNAS"
    action = "belum-lunas" if status == "lunas" else "lunas"
    button = "TANDAI BELUM LUNAS" if status == "lunas" else "TANDAI LUNAS"

    return render_template_string("""
    <!DOCTYPE html><html lang="id"><head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{title}}</title>
    <style>
    body{background:#071426;color:#eaf2ff;font-family:Arial;padding:16px}
    main{max-width:900px;margin:auto}
    .card{background:#102b49;border:1px solid #29496b;border-radius:16px;padding:16px}
    .btn{display:inline-block;background:#1689e8;color:white;padding:10px 12px;border:0;border-radius:9px;text-decoration:none}
    table{width:100%;border-collapse:collapse;min-width:560px}
    td,th{text-align:left;padding:12px 8px;border-bottom:1px solid #294766}
    th{color:#9fb5d0}.wrap{overflow-x:auto}
    form{margin:0}
    </style></head><body><main>
    <h2>{{title}}</h2>
    {% if request.args.get('wa') == 'sent' %}
    <p style="color:#35d69a">Pembayaran tersimpan. WhatsApp konfirmasi berhasil dikirim ke antrean Fonnte.</p>
    {% elif request.args.get('wa') == 'failed' %}
    <p style="color:#ffb454">Pembayaran tersimpan, tetapi WhatsApp gagal dikirim.</p>
    {% elif request.args.get('wa') == 'missing' %}
    <p style="color:#ffb454">Pembayaran tersimpan. Nomor HP pelanggan belum tersedia.</p>
    {% elif request.args.get('wa') == 'already' %}
    <p>Pelanggan sudah berstatus lunas sebelumnya. WhatsApp tidak dikirim ulang.</p>
    {% endif %}
    <p>Router: <b>{{router_name}}</b></p>
    <a class="btn" href="/pppoe/menu?router={{selected}}">Menu PPPoE</a>
    <form method="get" style="margin:15px 0;display:flex;gap:8px;flex-wrap:wrap">
    <input type="hidden" name="router" value="{{selected}}">
    <input name="q" value="{{q}}" placeholder="Cari nama, username, atau No. HP..."
    style="flex:1;min-width:200px;padding:12px;border-radius:9px;background:#102b49;color:white;border:1px solid #345574">
    <button class="btn" type="submit">Cari</button>
    {% if q %}<a class="btn" href="/pembayaran/{{'lunas' if title == 'PELANGGAN LUNAS' else 'belum-lunas'}}?router={{selected}}">Reset</a>{% endif %}
    </form>
    <div class="card"><p>Jumlah pelanggan ditemukan: {{customers|length}}</p>
    <div class="wrap"><table>
    <tr><th>Nama</th><th>Username PPPoE</th><th>No. HP</th>
    <th>Jatuh Tempo</th><th>Aksi</th></tr>
    {% for c in customers %}
    <tr><td>{{c.name}}</td><td>{{c.username}}</td><td>{{c.phone}}</td>
    <td>{{c.due_date}}</td><td>
    <form method="post">
    <input type="hidden" name="username" value="{{c.username}}">
    <button class="btn" type="submit">{{button}}</button>
    </form></td></tr>
    {% else %}
    <tr><td colspan="5">Belum ada pelanggan dalam daftar ini.</td></tr>
    {% endfor %}
    </table></div></div></main></body></html>
    """, title=title, button=button, customers=customers,
         router_name=r.get("name", "MikroTik"), selected=selected, q=q)



WA_CONFIG = os.path.expanduser("~/manajemen-mikrotik/fonnte_config.json")

def get_fonnte_token():
    try:
        with open(WA_CONFIG) as f:
            return json.load(f).get("token", "")
    except:
        return ""

def save_fonnte_token(token):
    with open(WA_CONFIG, "w") as f:
        json.dump({"token": token}, f)
    os.chmod(WA_CONFIG, 0o600)

def fonnte_send(target, message):
    token = get_fonnte_token()
    if not token:
        return False, "Token Fonnte belum diisi."
    target = "".join(c for c in str(target) if c.isdigit())
    if target.startswith("0"):
        target = "62" + target[1:]
    elif target.startswith("8"):
        target = "62" + target
    if not target.startswith("62") or len(target) < 10:
        return False, "Nomor HP pelanggan tidak valid."
    data = urllib.parse.urlencode({
        "target": target,
        "message": message,
        "countryCode": "0"
    }).encode()
    req = urllib.request.Request(
        "https://api.fonnte.com/send",
        data=data,
        headers={"Authorization": token}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.loads(response.read().decode())
        if result.get("status") is True:
            return True, "Pesan masuk antrean Fonnte."
        return False, "Fonnte menolak pesan. Periksa token, nomor, dan perangkat."
    except Exception:
        return False, "Tidak dapat menghubungi Fonnte. Periksa koneksi internet."

@app.route("/whatsapp", methods=["GET", "POST"])
def whatsapp_settings():
    notice = ""
    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "save":
            token = request.form.get("token", "").strip()
            if token:
                save_fonnte_token(token)
                notice = "Token berhasil disimpan."
            else:
                notice = "Token tidak boleh kosong."
        elif action == "test":
            target = request.form.get("target", "").strip()
            ok, result = fonnte_send(
                target, "Tes WhatsApp dari aplikasi Manajemen MikroTik. Pesan berhasil diuji."
            )
            notice = result
    return render_template_string("""
    <!DOCTYPE html><html lang="id"><head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Pengaturan WhatsApp</title>
    <style>
    body{background:#071426;color:#eaf2ff;font-family:Arial;padding:18px}
    main{max-width:600px;margin:auto}
    .card{background:#102b49;border:1px solid #29496b;border-radius:16px;padding:20px;margin:15px 0}
    input{box-sizing:border-box;width:100%;padding:13px;margin:9px 0 15px;background:#091d33;color:white;border:1px solid #345574;border-radius:9px}
    button,.btn{display:inline-block;padding:12px 16px;background:#1689e8;color:white;border:0;border-radius:9px;text-decoration:none;font-weight:bold}
    .notice{padding:13px;background:#203e60;border-radius:9px;margin:12px 0}
    .hint{color:#abc1dc}
    </style></head><body><main>
    <h2>💬 Pengaturan WhatsApp</h2>
    <p><a class="btn" href="/whatsapp/pengaturan">Atur Pesan Lunas & Jadwal Tagihan</a></p>
    <a class="btn" href="/">Kembali ke Dashboard</a>
    {% if notice %}<div class="notice">{{notice}}</div>{% endif %}
    <div class="card">
    <h3>Token Fonnte</h3>
    <p class="hint">Masukkan token dari akun Fonnte milik Anda. Token tidak ditampilkan kembali setelah disimpan.</p>
    <form method="post">
    <input type="hidden" name="action" value="save">
    <input type="password" name="token" placeholder="Tempel token Fonnte di sini" required>
    <button type="submit">SIMPAN TOKEN</button>
    </form>
    <p class="hint">Status: {{'Token sudah tersimpan' if configured else 'Token belum diisi'}}</p>
    </div>
    <div class="card">
    <h3>Tes WhatsApp</h3>
    <form method="post">
    <input type="hidden" name="action" value="test">
    <label>Nomor WhatsApp tujuan</label>
    <input name="target" placeholder="Contoh: 081234567890" required>
    <button type="submit">KIRIM PESAN TES</button>
    </form>
    </div>
    </main></body></html>
    """, notice=notice, configured=bool(get_fonnte_token()))



WA_SETTINGS = os.path.expanduser("~/manajemen-mikrotik/wa_settings.json")

def load_wa_settings():
    default = {
        "pesan_lunas": "Halo {nama}, pembayaran internet Anda untuk username {username} sudah kami terima. Status: LUNAS. Terima kasih.",
        "pesan_tagihan": "Halo {nama}, ini pengingat tagihan internet Anda. Username: {username}. Jatuh tempo: {jatuh_tempo}. Mohon segera melakukan pembayaran. Terima kasih.",
        "aktif": False,
        "tanggal": 5,
        "jam": "09:00"
    }
    try:
        with open(WA_SETTINGS) as f:
            saved = json.load(f)
        default.update(saved)
    except Exception:
        pass
    return default

def save_wa_settings(data):
    temp = WA_SETTINGS + ".tmp"
    with open(temp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(temp, WA_SETTINGS)

@app.route("/whatsapp/pengaturan", methods=["GET", "POST"])
def whatsapp_message_settings():
    notice = ""
    cfg = load_wa_settings()

    if request.method == "POST":
        try:
            lunas = request.form.get("pesan_lunas", "").strip()
            tagihan = request.form.get("pesan_tagihan", "").strip()
            tanggal = int(request.form.get("tanggal", "5"))
            jam = request.form.get("jam", "09:00").strip()
            aktif = request.form.get("aktif") == "on"

            import datetime
            datetime.datetime.strptime(jam, "%H:%M")

            if not lunas or not tagihan:
                raise ValueError("Isi kedua pesan tidak boleh kosong.")
            if not 1 <= tanggal <= 31:
                raise ValueError("Tanggal harus antara 1 sampai 31.")

            cfg.update({
                "pesan_lunas": lunas,
                "pesan_tagihan": tagihan,
                "tanggal": tanggal,
                "jam": jam,
                "aktif": aktif
            })
            save_wa_settings(cfg)
            notice = "Pengaturan pesan dan jadwal berhasil disimpan."
        except Exception as e:
            notice = "Gagal menyimpan: " + str(e)

    return render_template_string("""
    <!DOCTYPE html><html lang="id"><head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Pesan dan Jadwal WhatsApp</title>
    <style>
    body{margin:0;padding:18px;background:#071426;color:#eaf2ff;font-family:Arial}
    main{max-width:720px;margin:auto}
    .card{background:#102b49;border:1px solid #29496b;border-radius:15px;padding:18px;margin:15px 0}
    textarea,input{box-sizing:border-box;width:100%;padding:12px;margin:8px 0 15px;background:#091d33;color:white;border:1px solid #345574;border-radius:9px}
    textarea{min-height:115px;font-family:Arial}
    button,.btn{display:inline-block;padding:12px 16px;background:#1689e8;color:white;border:0;border-radius:9px;text-decoration:none;font-weight:bold}
    .hint{color:#abc1dc;font-size:13px}
    .notice{padding:12px;background:#203e60;border-radius:9px}
    label{display:block;margin-top:10px}
    </style></head><body><main>
    <h2>💬 Pesan dan Jadwal WhatsApp</h2>
    <a class="btn" href="/whatsapp">Kembali ke WhatsApp</a>
    {% if notice %}<p class="notice">{{notice}}</p>{% endif %}
    <form method="post">
    <div class="card">
    <h3>✅ Pesan Konfirmasi Lunas</h3>
    <textarea name="pesan_lunas" required>{{cfg.pesan_lunas}}</textarea>
    <p class="hint">Variabel: {nama}, {username}, {jatuh_tempo}</p>
    </div>
    <div class="card">
    <h3>🧾 Pesan Tagihan</h3>
    <textarea name="pesan_tagihan" required>{{cfg.pesan_tagihan}}</textarea>
    <p class="hint">Variabel: {nama}, {username}, {jatuh_tempo}</p>
    </div>
    <div class="card">
    <h3>🗓️ Jadwal Tagihan Bulanan</h3>
    <label>Tanggal pengiriman setiap bulan (1–31)</label>
    <input type="number" name="tanggal" min="1" max="31" value="{{cfg.tanggal}}" required>
    <label>Jam pengiriman</label>
    <input type="time" name="jam" value="{{cfg.jam}}" required>
    <label><input style="width:auto" type="checkbox" name="aktif" {% if cfg.aktif %}checked{% endif %}> Aktifkan jadwal otomatis</label>
    <p class="hint">Jadwal saat ini: {{'AKTIF' if cfg.aktif else 'NONAKTIF'}}. Pengiriman otomatis belum dijalankan sampai mesin jadwal dipasang.</p>
    </div>
    <button type="submit">SIMPAN PENGATURAN</button>
    </form>
    </main></body></html>
    """, cfg=cfg, notice=notice)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8765)
