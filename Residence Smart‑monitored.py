```python
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
import random
import time
import threading
import math

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# ====================== HTML TEMPLATE (embedded) ======================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>Mwarokin Estate · Premium Residence</title>
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css"/>
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <!-- Leaflet -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <!-- Socket.IO -->
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', system-ui, -apple-system, sans-serif; }
        body { background: #f5f9f7; display: flex; justify-content: center; padding: 24px; }
        .container { max-width: 1280px; width: 100%; background: #ffffff; border-radius: 42px; padding: 32px 40px; box-shadow: 0 20px 50px rgba(0,0,0,0.06); transition: all 0.2s; }
        .profile-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 28px; }
        .title-section h2 { font-weight: 700; font-size: 28px; letter-spacing: -0.02em; color: #1a2e2a; }
        .title-section p { color: #4f6b62; font-size: 15px; margin-top: 4px; }
        .live-badge { background: #1f6e43; color: white; padding: 10px 22px; border-radius: 40px; font-size: 13px; font-weight: 600; letter-spacing: 0.5px; display: flex; align-items: center; gap: 8px; }
        .live-badge i { font-size: 10px; color: #b3ffb3; animation: pulse 1.2s infinite; }
        @keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }
        .hero-gallery { display: flex; gap: 18px; margin-bottom: 32px; }
        .main-img { flex: 2.2; border-radius: 32px; overflow: hidden; background: #eef3f0; }
        .main-img img { width: 100%; height: 340px; object-fit: cover; display: block; }
        .thumb-stack { flex: 1; display: flex; flex-direction: column; gap: 12px; }
        .thumb-stack img { width: 100%; height: 102px; object-fit: cover; border-radius: 20px; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; border: 2px solid transparent; }
        .thumb-stack img:hover { transform: scale(1.02); box-shadow: 0 8px 18px rgba(0,0,0,0.08); border-color: #1f6e43; }
        .monitoring-dashboard { display: grid; grid-template-columns: repeat(4,1fr); gap: 18px; margin-bottom: 32px; }
        .metric-card { background: #f8fbfa; border-radius: 26px; padding: 18px 22px; box-shadow: 0 4px 12px rgba(0,0,0,0.02); border: 1px solid #e4eee9; transition: 0.15s; }
        .metric-title { font-size: 13px; font-weight: 600; color: #4f6b62; letter-spacing: 0.3px; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }
        .metric-value { font-size: 32px; font-weight: 700; color: #1a2e2a; line-height: 1.2; }
        .metric-unit { font-size: 18px; font-weight: 500; color: #6b8a7d; margin-left: 2px; }
        .trend { font-size: 14px; color: #2c5e4a; margin-top: 8px; display: flex; align-items: center; gap: 4px; }
        .insight-row { display: flex; gap: 28px; margin-bottom: 32px; }
        .chart-box { flex: 2; background: #fafdfb; border-radius: 32px; padding: 24px 28px; border: 1px solid #e4eee9; }
        .chart-box h3 { font-weight: 700; font-size: 18px; color: #1a2e2a; display: flex; align-items: center; gap: 8px; }
        .feed-box { flex: 1.2; background: #fafdfb; border-radius: 32px; padding: 20px 24px; border: 1px solid #e4eee9; max-height: 340px; display: flex; flex-direction: column; }
        .feed-header { font-weight: 700; font-size: 16px; color: #1a2e2a; display: flex; align-items: center; margin-bottom: 16px; }
        .feed-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
        .feed-event { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 16px; background: #f2f8f5; font-size: 14px; transition: 0.1s; }
        .feed-time { font-family: monospace; font-size: 12px; color: #5b7d6e; min-width: 70px; }
        .feed-icon { width: 28px; color: #1f6e43; text-align: center; }
        .feed-text { flex: 1; color: #1e3d32; }
        .upgrade-section { margin: 32px 0 28px; }
        .upgrade-section h3 { font-weight: 700; font-size: 20px; color: #1a2e2a; display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
        .upgrade-grid { display: flex; flex-wrap: wrap; gap: 12px 24px; }
        .upgrade-item { background: #f2f8f5; padding: 8px 18px; border-radius: 30px; font-size: 14px; color: #1a2e2a; display: flex; align-items: center; gap: 8px; border: 1px solid #d8e8e0; }
        footer { margin-top: 36px; border-top: 1px solid #e4eee9; padding-top: 22px; font-size: 14px; color: #5b7d6e; display: flex; align-items: center; gap: 8px; justify-content: center; }
        @media (max-width: 900px) {
            .container { padding: 20px; }
            .hero-gallery { flex-direction: column; }
            .thumb-stack { flex-direction: row; }
            .thumb-stack img { height: 80px; }
            .monitoring-dashboard { grid-template-columns: repeat(2,1fr); }
            .insight-row { flex-direction: column; }
        }
        @media (max-width: 540px) {
            .profile-header { flex-direction: column; align-items: start; gap: 12px; }
            .monitoring-dashboard { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
<div class="container">

    <!-- header -->
    <div class="profile-header">
        <div class="title-section">
            <h2><i class="fas fa-crown" style="color:#eab308; margin-right:10px;"></i> Mwarokin Estate</h2>
            <p><i class="fas fa-map-pin"></i> · Windsor Manor Premier Wing | Smart‑monitored unit</p>
        </div>
        <div class="live-badge">
            <i class="fas fa-circle"></i> LIVE RESIDENCE MONITORING · ACTIVE
        </div>
    </div>

    <!-- gallery -->
    <div class="hero-gallery">
        <div class="main-img">
            <img id="mainGalleryImg" src="https://picsum.photos/id/106/800/500" alt="Residence main view">
        </div>
        <div class="thumb-stack">
            <img src="https://picsum.photos/id/164/400/280" alt="Living room" onclick="changeMainImage(this.src)">
            <img src="https://picsum.photos/id/42/400/280" alt="Bedroom suite" onclick="changeMainImage(this.src)">
            <img src="https://picsum.photos/id/169/400/280" alt="Private terrace" onclick="changeMainImage(this.src)">
        </div>
    </div>

    <!-- metrics -->
    <div class="monitoring-dashboard">
        <div class="metric-card">
            <div class="metric-title"><i class="fas fa-thermometer-half"></i> INDOOR TEMPERATURE</div>
            <div class="metric-value" id="tempValue">22.4<span class="metric-unit">°C</span></div>
            <div class="trend" id="tempTrend"><i class="fas fa-leaf"></i> Optimal climate</div>
        </div>
        <div class="metric-card">
            <div class="metric-title"><i class="fas fa-tint"></i> HUMIDITY LEVEL</div>
            <div class="metric-value" id="humValue">48<span class="metric-unit">%</span></div>
            <div class="trend" id="humTrend"><i class="fas fa-check-circle"></i> Balanced</div>
        </div>
        <div class="metric-card">
            <div class="metric-title"><i class="fas fa-bolt"></i> ENERGY USAGE</div>
            <div class="metric-value" id="energyValue">2.8<span class="metric-unit">kW</span></div>
            <div class="trend" id="energyTrend">⬇️ 12% vs yesterday</div>
        </div>
        <div class="metric-card">
            <div class="metric-title"><i class="fas fa-shield-alt"></i> SECURITY STATUS</div>
            <div class="metric-value" id="securityStatus">ARMED</div>
            <div class="trend" style="color:#16a34a;">🔒 All sensors OK</div>
        </div>
    </div>

    <!-- chart + feed -->
    <div class="insight-row">
        <div class="chart-box">
            <h3><i class="fas fa-chart-line"></i> Energy Consumption (last 12h)</h3>
            <canvas id="energyChart" width="400" height="200" style="max-height:240px; width:100%;"></canvas>
            <p class="trend" style="margin-top:16px;"><i class="fas fa-microchip"></i> Smart grid optimized · real‑time efficiency</p>
        </div>
        <div class="feed-box">
            <div class="feed-header"><i class="fas fa-broadcast-tower"></i> <span class="live-dot" style="display:inline-block; width:8px; height:8px; background:#22c55e; border-radius:50%; margin:0 8px 0 4px;"></span> LIVE ACTIVITY STREAM</div>
            <div class="feed-list" id="liveActivityFeed">
                <!-- items inserted by JS -->
            </div>
        </div>
    </div>

    <!-- upgrades -->
    <div class="upgrade-section">
        <h3><i class="fas fa-gem" style="color:#1f6e43;"></i> Upgraded Residence Perks & Smart Living</h3>
        <div class="upgrade-grid">
            <div class="upgrade-item"><i class="fas fa-microphone-alt fa-fw"></i> Voice‑activated AI assistant</div>
            <div class="upgrade-item"><i class="fas fa-water fa-fw"></i> Smart irrigation & garden</div>
            <div class="upgrade-item"><i class="fas fa-car-battery"></i> EV charging | V2G ready</div>
            <div class="upgrade-item"><i class="fas fa-temperature-low"></i> Zoned climate control</div>
            <div class="upgrade-item"><i class="fas fa-vr-cardboard"></i> Virtual concierge 24/7</div>
        </div>
    </div>

    <!-- map -->
    <div style="margin-top:32px;">
        <h4 style="margin-bottom:12px;"><i class="fas fa-map-marker-alt"></i> Residence Geo‑Location (Mwarokin Estate)</h4>
        <div id="residenceMiniMap" style="height:260px; border-radius:28px; overflow:hidden; box-shadow:0 12px 22px rgba(0,0,0,0.08);"></div>
    </div>
    <footer>
        <i class="fas fa-shield-heart"></i> Mwarokin Estate — Premium Residence Profile · Real‑time IoT monitoring & live scenario simulation. All data encrypted.
    </footer>
</div>

<script>
    // ========== Socket.IO connection ==========
    const socket = io();

    // ========== DOM refs ==========
    const tempSpan = document.getElementById('tempValue');
    const humSpan = document.getElementById('humValue');
    const energySpan = document.getElementById('energyValue');
    const securitySpan = document.getElementById('securityStatus');
    const tempTrendSpan = document.getElementById('tempTrend');
    const humTrendSpan = document.getElementById('humTrend');
    const energyTrendSpan = document.getElementById('energyTrend');
    const feedContainer = document.getElementById('liveActivityFeed');

    // ========== Chart initialization ==========
    const ctx = document.getElementById('energyChart').getContext('2d');
    const initialData = [2.4, 2.7, 3.0, 2.9, 3.2, 3.4, 3.1, 2.8, 2.6, 2.5, 2.7, 2.8];
    const timeLabels = ['10:00','11:00','12:00','13:00','14:00','15:00','16:00','17:00','18:00','19:00','20:00','21:00'];
    let energyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: timeLabels,
            datasets: [{
                label: 'kWh consumed',
                data: initialData,
                borderColor: '#2c8c5a',
                backgroundColor: 'rgba(44,140,90,0.05)',
                tension: 0.3,
                fill: true,
                pointBackgroundColor: '#1f6e43',
                pointBorderColor: '#fff',
                pointRadius: 4,
                pointHoverRadius: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: { legend: { position: 'top' }, tooltip: { mode: 'index' } },
            scales: { y: { grid: { color: '#e0ece8' }, title: { display: true, text: 'Power (kW)' } } }
        }
    });

    // ========== Gallery ==========
    window.changeMainImage = function(src) {
        document.getElementById('mainGalleryImg').src = src;
        // also send an event via socket? optional
    };

    // ========== Leaflet map ==========
    function initMiniMap() {
        const residenceCoord = [-1.2925, 36.822];
        const miniMap = L.map('residenceMiniMap').setView(residenceCoord, 17);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
        }).addTo(miniMap);
        const premiumIcon = L.divIcon({
            html: '<i class="fas fa-home" style="background:#1f6e43; color:white; padding:8px 10px; border-radius:40px; font-size:14px; box-shadow:0 4px 8px rgba(0,0,0,0.2);"></i>',
            iconSize: [32,32],
            popupAnchor: [0,-12]
        });
        L.marker(residenceCoord, { icon: premiumIcon }).addTo(miniMap)
            .bindPopup('<b>The Windsor Manor · 7B</b><br>Premium monitored unit')
            .openPopup();
    }
    document.addEventListener('DOMContentLoaded', initMiniMap);

    // ========== Socket event handlers ==========
    socket.on('connect', function() {
        console.log('Connected to server');
        // request initial data? server will push on connect
    });

    socket.on('update_metrics', function(data) {
        // data: { temp, hum, energy, armed, tempTrend, humTrend, energyTrend }
        tempSpan.innerHTML = data.temp.toFixed(1) + '<span class="metric-unit">°C</span>';
        humSpan.innerHTML = Math.round(data.hum) + '<span class="metric-unit">%</span>';
        energySpan.innerHTML = data.energy.toFixed(1) + '<span class="metric-unit">kW</span>';
        securitySpan.innerHTML = data.armed ? "ARMED · GUARD" : "DISARMED";
        securitySpan.style.color = data.armed ? "#16a34a" : "#e67e22";
        tempTrendSpan.innerHTML = data.tempTrend;
        humTrendSpan.innerHTML = data.humTrend;
        energyTrendSpan.innerHTML = data.energyTrend;
    });

    socket.on('new_feed_event', function(event) {
        // event: { time, icon, message }
        const feedDiv = document.createElement('div');
        feedDiv.className = 'feed-event';
        feedDiv.innerHTML = `
            <div class="feed-time">${event.time}</div>
            <div class="feed-icon"><i class="${event.icon}"></i></div>
            <div class="feed-text">${event.message}</div>
        `;
        feedContainer.prepend(feedDiv);
        while (feedContainer.children.length > 16) {
            feedContainer.removeChild(feedContainer.lastChild);
        }
    });

    socket.on('update_chart', function(newPoint) {
        // newPoint: number (kW)
        energyChart.data.datasets[0].data.push(newPoint);
        if (energyChart.data.datasets[0].data.length > 12) {
            energyChart.data.datasets[0].data.shift();
        }
        energyChart.update();
    });

    // ========== Initial feed warmup ==========
    function addFeedEvent(msg, icon) {
        // used for initial static items
        const feedDiv = document.createElement('div');
        feedDiv.className = 'feed-event';
        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour:'2-digit', minute:'2-digit', second:'2-digit' });
        feedDiv.innerHTML = `
            <div class="feed-time">${timeStr}</div>
            <div class="feed-icon"><i class="${icon}"></i></div>
            <div class="feed-text">${msg}</div>
        `;
        feedContainer.prepend(feedDiv);
        while (feedContainer.children.length > 16) {
            feedContainer.removeChild(feedContainer.lastChild);
        }
    }

    // initial feed items (will be overridden by server events)
    addFeedEvent("🟢 Windsor Manor Residence Monitor online — upgraded sensors active", "fas fa-check-circle");
    addFeedEvent("🌍 Real‑time geofence & occupancy tracking live", "fas fa-map-marked-alt");
    addFeedEvent("🎛️ Smart climate & energy dashboard updated every 9s", "fas fa-chart-line");
    addFeedEvent("✨ New upgrade: HEPA filtration & AQI monitoring ready", "fas fa-leaf");
</script>
</body>
</html>
"""

# ====================== BACKEND SIMULATION ======================
# Global state (will be updated by background thread)
current_temp = 22.4
current_hum = 48.0
current_energy = 2.8
armed = True
energy_history = [2.4, 2.7, 3.0, 2.9, 3.2, 3.4, 3.1, 2.8, 2.6, 2.5, 2.7, 2.8]  # last 12 points

scenario_messages = [
    ("🪟 Smart windows adjusted: natural ventilation mode", "fas fa-wind"),
    ("🏊‍♂️ Resident detected: pool access via biometric", "fas fa-swimmer"),
    ("📦 Package arrival at smart locker – notification sent", "fas fa-box"),
    ("🔊 Voice command: 'Set lights to cinematic' – living room", "fas fa-microphone-alt"),
    ("🌿 Garden humidity sensor triggered irrigation", "fas fa-seedling"),
    ("⚡ EV charger plugged in – scheduled green charging", "fas fa-charging-station"),
    ("🛋️ Presence sensor: resident in home office", "fas fa-user-check"),
    ("🔒 Front door locked automatically (geofence exit)", "fas fa-door-closed"),
    ("📹 Security camera: motion detected at private terrace", "fas fa-video"),
    ("🧹 Robotic vacuum started cleaning routine", "fas fa-robot"),
]

def generate_trend_text(temp, hum, energy):
    # temperature trend
    if temp > 24.5:
        temp_trend = '<i class="fas fa-temperature-high"></i> Slight warm → AC adjusting'
    elif temp < 19:
        temp_trend = '<i class="fas fa-snowflake"></i> Heating optimization'
    else:
        temp_trend = '<i class="fas fa-leaf"></i> Optimal climate'
    # humidity
    if hum > 65:
        hum_trend = '<i class="fas fa-tint"></i> High humidity, dehumidifier active'
    elif hum < 35:
        hum_trend = '<i class="fas fa-wind"></i> Dry air → humidifier on'
    else:
        hum_trend = '<i class="fas fa-check-circle"></i> Balanced comfort'
    # energy
    if energy > 3.5:
        energy_trend = '⚠️ Peak usage, load balancing'
    elif energy < 1.8:
        energy_trend = '💚 Low consumption, eco mode'
    else:
        energy_trend = '⬇️ Efficient range'
    return temp_trend, hum_trend, energy_trend

def background_thread():
    """Simulate real-time sensor data and emit via Socket.IO."""
    global current_temp, current_hum, current_energy, armed, energy_history
    with app.app_context():
        # send initial data to connected clients
        temp_trend, hum_trend, energy_trend = generate_trend_text(current_temp, current_hum, current_energy)
        socketio.emit('update_metrics', {
            'temp': current_temp,
            'hum': current_hum,
            'energy': current_energy,
            'armed': armed,
            'tempTrend': temp_trend,
            'humTrend': hum_trend,
            'energyTrend': energy_trend
        })
        # send initial chart data (all points)
        for val in energy_history:
            socketio.emit('update_chart', val)
        # send some initial feed events
        initial_events = [
            ("🟢 Windsor Manor Residence Monitor online — upgraded sensors active", "fas fa-check-circle"),
            ("🌍 Real‑time geofence & occupancy tracking live", "fas fa-map-marked-alt"),
            ("🎛️ Smart climate & energy dashboard updated every 9s", "fas fa-chart-line"),
            ("✨ New upgrade: HEPA filtration & AQI monitoring ready", "fas fa-leaf"),
        ]
        for msg, icon in initial_events:
            now = time.strftime("%H:%M:%S")
            socketio.emit('new_feed_event', {'time': now, 'icon': icon, 'message': msg})

    while True:
        time.sleep(9)  # update every 9 seconds

        # ---- Simulate temperature random walk ----
        temp_delta = (random.random() * 0.7) - 0.3
        new_temp = current_temp + temp_delta
        new_temp = max(18.5, min(27.0, new_temp))
        if abs(new_temp - current_temp) > 0.05:
            now = time.strftime("%H:%M:%S")
            socketio.emit('new_feed_event', {
                'time': now,
                'icon': 'fas fa-thermometer-half',
                'message': f"🌡️ Indoor temperature changed from {current_temp:.1f}°C to {new_temp:.1f}°C (HVAC adaptive)"
            })
        current_temp = new_temp

        # ---- Simulate humidity ----
        hum_delta = (random.random() * 3) - 1.2
        new_hum = current_hum + hum_delta
        new_hum = max(32, min(72, new_hum))
        if abs(new_hum - current_hum) > 1.5:
            now = time.strftime("%H:%M:%S")
            socketio.emit('new_feed_event', {
                'time': now,
                'icon': 'fas fa-tint',
                'message': f"💧 Humidity now {round(new_hum)}% — {'dehumidifier active' if new_hum > 60 else 'optimal'}"
            })
        current_hum = new_hum

        # ---- Simulate energy ----
        energy_delta = (random.random() * 0.6) - 0.2
        new_energy = current_energy + energy_delta
        new_energy = max(1.0, min(5.2, new_energy))
        if abs(new_energy - current_energy) > 0.15:
            now = time.strftime("%H:%M:%S")
            socketio.emit('new_feed_event', {
                'time': now,
                'icon': 'fas fa-charging-station',
                'message': f"⚡ Power consumption: {new_energy:.1f} kW (smart meter reading)"
            })
        current_energy = new_energy
        # update chart history
        energy_history.append(current_energy)
        if len(energy_history) > 12:
            energy_history.pop(0)
        # emit new chart point
        socketio.emit('update_chart', current_energy)

        # ---- Random security ----
        if random.random() < 0.12:
            now = time.strftime("%H:%M:%S")
            msg = "🔔 Perimeter sensor: no anomaly" if random.random() > 0.3 else "🛡️ Security patrol check completed"
            socketio.emit('new_feed_event', {'time': now, 'icon': 'fas fa-shield-alt', 'message': msg})
        if random.random() < 0.05:
            armed = not armed
            now = time.strftime("%H:%M:%S")
            msg = "🔒 Security system ARMED (instant lockdown mode)" if armed else "🔓 Security system temporarily disarmed – authorized access"
            socketio.emit('new_feed_event', {'time': now, 'icon': 'fas fa-lock', 'message': msg})
        elif random.random() < 0.1:
            now = time.strftime("%H:%M:%S")
            socketio.emit('new_feed_event', {'time': now, 'icon': 'fas fa-cloud-upload-alt', 'message': "📡 IoT hub: Firmware auto-update completed"})

        # ---- Random scenario ----
        if random.random() < 0.65:
            msg, icon = random.choice(scenario_messages)
            now = time.strftime("%H:%M:%S")
            socketio.emit('new_feed_event', {'time': now, 'icon': icon, 'message': msg})
        else:
            now = time.strftime("%H:%M:%S")
            socketio.emit('new_feed_event', {
                'time': now,
                'icon': 'fas fa-microchip',
                'message': "👑 Windsor Manor: Energy optimization AI reduced standby usage by 8%"
            })

        # extra resident interaction
        if random.random() < 0.2:
            now = time.strftime("%H:%M:%S")
            socketio.emit('new_feed_event', {
                'time': now,
                'icon': 'fas fa-mobile-alt',
                'message': "📱 Mobile app command received: 'set ambiance – evening relaxation'"
            })

        # emit updated metrics
        temp_trend, hum_trend, energy_trend = generate_trend_text(current_temp, current_hum, current_energy)
        socketio.emit('update_metrics', {
            'temp': current_temp,
            'hum': current_hum,
            'energy': current_energy,
            'armed': armed,
            'tempTrend': temp_trend,
            'humTrend': hum_trend,
            'energyTrend': energy_trend
        })

# ====================== FLASK ROUTE ======================
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# ====================== SOCKET EVENT ======================
@socketio.on('connect')
def handle_connect():
    """Send initial state to newly connected client."""
    temp_trend, hum_trend, energy_trend = generate_trend_text(current_temp, current_hum, current_energy)
    emit('update_metrics', {
        'temp': current_temp,
        'hum': current_hum,
        'energy': current_energy,
        'armed': armed,
        'tempTrend': temp_trend,
        'humTrend': hum_trend,
        'energyTrend': energy_trend
    })
    # send chart history
    for val in energy_history:
        emit('update_chart', val)

# ====================== START APP ======================
if __name__ == '__main__':
    # Start background thread
    thread = threading.Thread(target=background_thread)
    thread.daemon = True
    thread.start()
    # Run with eventlet
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False)
```