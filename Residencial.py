```python
import dash
from dash import dcc, html, Input, Output, State, callback, no_update
import dash_bootstrap_components as dbc
import dash_leaflet as dl
from dash_leaflet import components as dlc
import random
import datetime
from dash_extensions.javascript import Namespace

# ------------------------- DATA -------------------------
ESTATE_CENTER = [-1.2925, 36.822]  # Mwarokin Estate hub

PROPERTIES = [
    {"id": 1, "name": "Sunset Pallazio", "address": "Mwarokin Boulevard A1", "residents": 28,
     "image": "https://picsum.photos/id/106/400/300", "lat": -1.292, "lng": 36.8212,
     "features": "Smart home ready, private garden"},
    {"id": 2, "name": "Emerald Heights", "address": "Green Valley Wing", "residents": 34,
     "image": "https://picsum.photos/id/164/400/300", "lat": -1.2938, "lng": 36.8219,
     "features": "Rooftop lounge, EV charging"},
    {"id": 3, "name": "The Windsor Manor", "address": "Majestic Row", "residents": 22,
     "image": "https://picsum.photos/id/42/400/300", "lat": -1.2912, "lng": 36.8228,
     "features": "Concierge & heated pool"},
    {"id": 4, "name": "Serein Lakeview", "address": "Lakefront Drive", "residents": 41,
     "image": "https://picsum.photos/id/157/400/300", "lat": -1.294, "lng": 36.8207,
     "features": "Lake access, modern fitness"},
    {"id": 5, "name": "Golden Crest Residences", "address": "Northgate Estate", "residents": 19,
     "image": "https://picsum.photos/id/169/400/300", "lat": -1.2905, "lng": 36.8232,
     "features": "Panoramic views, coworking hub"},
    {"id": 6, "name": "Mwarokin Sky Gardens", "address": "Aerial Heights", "residents": 53,
     "image": "https://picsum.photos/id/88/400/300", "lat": -1.2934, "lng": 36.821,
     "features": "Vertical gardens, gym & spa"}
]

AMENITIES = [
    {"id": 1, "name": "The Oasis Clubhouse", "category": "Social & Events",
     "image": "https://picsum.photos/id/259/400/300", "lat": -1.2918, "lng": 36.8225,
     "desc": "Infinity pool, co-working lounge"},
    {"id": 2, "name": "Vitality Fitness Center", "category": "Gym & Wellness",
     "image": "https://picsum.photos/id/143/400/300", "lat": -1.2922, "lng": 36.8209,
     "desc": "CrossFit, yoga terrace, spa"},
    {"id": 3, "name": "Parkside Padel & Tennis", "category": "Sports",
     "image": "https://picsum.photos/id/96/400/300", "lat": -1.2942, "lng": 36.8227,
     "desc": "Floodlit courts + academy"},
    {"id": 4, "name": "The Orchard Market Walk", "category": "Retail & dining",
     "image": "https://picsum.photos/id/130/400/300", "lat": -1.2908, "lng": 36.8215,
     "desc": "Artisan cafes, boutiques & pharmacy"}
]

# ------------------------- APP INIT -------------------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Mwarokin Estate Management"

# Custom CSS (embedded)
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body { background: #f4f7fc; font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
            .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
            .header { display: flex; justify-content: space-between; align-items: center; padding: 20px 0; border-bottom: 2px solid #e9edf4; margin-bottom: 30px; }
            .logo-area h1 { font-size: 1.8rem; font-weight: 700; color: #1e293b; margin: 0; }
            .logo-area h1 i { color: #1f6e43; }
            .logo-area p { color: #64748b; margin: 0; font-size: 0.9rem; }
            .badge-live { background: #0b3b2c; color: #fff; padding: 6px 18px; border-radius: 30px; font-size: 0.7rem; letter-spacing: 0.5px; display: flex; align-items: center; gap: 8px; }
            .stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }
            .stat-card { background: white; border-radius: 16px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.04); border: 1px solid #eef2f6; }
            .stat-title { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b; margin-bottom: 8px; }
            .stat-value { font-size: 2rem; font-weight: 700; color: #0f172a; }
            .stat-sub { font-size: 0.8rem; color: #475569; margin-top: 6px; }
            .map-section { background: white; border-radius: 20px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.04); margin-bottom: 30px; border: 1px solid #eef2f6; }
            .map-title { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
            .map-title h2 { font-size: 1.2rem; font-weight: 600; color: #1e293b; margin: 0; }
            .locate-btn { background: #1f6e43; color: white; border: none; padding: 8px 20px; border-radius: 40px; font-size: 0.8rem; display: flex; align-items: center; gap: 6px; transition: 0.2s; }
            .locate-btn:hover { background: #155a34; }
            #estateMap { height: 400px; border-radius: 12px; overflow: hidden; }
            .section-title { font-size: 1.4rem; font-weight: 600; color: #1e293b; margin: 30px 0 20px; display: flex; align-items: center; }
            .section-title i { margin-right: 12px; color: #d4af37; }
            .cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 25px; }
            .property-card, .amenity-card { background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.04); border: 1px solid #eef2f6; transition: 0.3s; }
            .property-card:hover, .amenity-card:hover { transform: translateY(-4px); box-shadow: 0 12px 24px rgba(0,0,0,0.08); }
            .card-img { width: 100%; height: 180px; object-fit: cover; }
            .card-content { padding: 18px; }
            .card-content h3 { font-size: 1.1rem; font-weight: 600; margin: 0 0 6px; }
            .card-content p { margin: 4px 0; font-size: 0.9rem; color: #475569; }
            .badge-amenity { display: inline-block; background: #ecfdf5; color: #0b3b2c; padding: 3px 12px; border-radius: 30px; font-size: 0.7rem; font-weight: 500; margin-top: 8px; }
            .feed-panel { background: white; border-radius: 16px; padding: 20px; margin-top: 30px; border: 1px solid #eef2f6; }
            .feed-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
            .feed-header h3 { font-size: 1.1rem; font-weight: 600; margin: 0; display: flex; align-items: center; gap: 10px; }
            .live-dot { display: inline-block; width: 10px; height: 10px; background: #ef4444; border-radius: 50%; animation: pulse 1.5s infinite; }
            @keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(0.9); } 100% { opacity: 1; transform: scale(1); } }
            .feed-list { max-height: 300px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
            .feed-item { display: flex; align-items: center; gap: 12px; padding: 10px 12px; background: #f8fafc; border-radius: 10px; font-size: 0.9rem; border-left: 3px solid #1f6e43; }
            .feed-time { font-weight: 500; color: #475569; min-width: 70px; font-size: 0.75rem; }
            .feed-icon { color: #1f6e43; }
            .feed-text { color: #1e293b; }
            footer { margin-top: 40px; text-align: center; color: #94a3b8; font-size: 0.8rem; border-top: 1px solid #eef2f6; padding-top: 20px; }
            footer i { margin-right: 6px; color: #1f6e43; }
            @media (max-width: 768px) {
                .stats-row { grid-template-columns: 1fr 1fr; }
                .header { flex-direction: column; align-items: flex-start; gap: 10px; }
                .badge-live { align-self: flex-start; }
            }
        </style>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# ------------------------- LAYOUT -------------------------
def create_card(item, card_type='property'):
    if card_type == 'property':
        return dbc.Col(
            dbc.Card([
                dbc.CardImg(src=item['image'], top=True, style={'height': '180px', 'object-fit': 'cover'}),
                dbc.CardBody([
                    html.H5(f"🏘️ {item['name']}", className="card-title"),
                    html.P([html.I(className="fas fa-location-dot"), f" {item['address']}"], className="card-text"),
                    html.P([html.I(className="fas fa-user-group"), f" {item['residents']} residents • {item['features']}"], className="card-text"),
                    html.Span([html.I(className="fas fa-charging-station"), " upgraded smart tech"], className="badge-amenity")
                ])
            ], className="property-card h-100")
        )
    else:  # amenity
        return dbc.Col(
            dbc.Card([
                dbc.CardImg(src=item['image'], top=True, style={'height': '180px', 'object-fit': 'cover'}),
                dbc.CardBody([
                    html.H5(f"✨ {item['name']}", className="card-title"),
                    html.P([html.I(className="fas fa-tag"), f" {item['category']}"], className="card-text"),
                    html.P(item['desc'], className="card-text"),
                    html.Span([html.I(className="fas fa-check-circle"), " open 24/7 for residents"], className="badge-amenity")
                ])
            ], className="amenity-card h-100")
        )

app.layout = html.Div(className="container", children=[
    # Header
    html.Div(className="header", children=[
        html.Div(className="logo-area", children=[
            html.H1([html.I(className="fas fa-building"), " Mwarokin Estate"]),
            html.P("Intelligent living · Real-time oversight · Ultra-modern amenities")
        ]),
        html.Div(className="badge-live", children=[
            html.I(className="fas fa-satellite-dish"),
            " LIVE MONITORING · SECURE CONNECT"
        ])
    ]),

    # Stats row
    html.Div(className="stats-row", children=[
        dbc.Card([
            dbc.CardBody([
                html.Div([html.I(className="fas fa-home"), " TOTAL PROPERTIES"], className="stat-title"),
                html.Div(str(len(PROPERTIES)), className="stat-value", id="total-properties"),
                html.Div("+2 premium units upgraded", className="stat-sub")
            ])
        ], className="stat-card"),
        dbc.Card([
            dbc.CardBody([
                html.Div([html.I(className="fas fa-users"), " RESIDENTS (LIVE)"], className="stat-title"),
                html.Div("248", className="stat-value", id="live-residents"),
                html.Div("Occupancy: 83%", className="stat-sub", id="occupancy-rate")
            ])
        ], className="stat-card"),
        dbc.Card([
            dbc.CardBody([
                html.Div([html.I(className="fas fa-tree"), " AMENITIES"], className="stat-title"),
                html.Div(str(len(AMENITIES)), className="stat-value"),
                html.Div("Pool, Gym, Club, Parks & more", className="stat-sub")
            ])
        ], className="stat-card"),
        dbc.Card([
            dbc.CardBody([
                html.Div([html.I(className="fas fa-exclamation-triangle"), " ACTIVE ISSUES"], className="stat-title"),
                html.Div("4", className="stat-value", id="active-issues"),
                html.Div("monitored & automated alerts", className="stat-sub")
            ])
        ], className="stat-card"),
    ]),

    # Map
    html.Div(className="map-section", children=[
        html.Div(className="map-title", children=[
            html.H2([html.I(className="fas fa-map-marked-alt", style={'color': '#2a7f4b'}), " Live Estate Map & Surroundings"]),
            html.Button([html.I(className="fas fa-location-dot"), " My live location"], className="locate-btn", id="locate-me-btn")
        ]),
        dl.Map(center=ESTATE_CENTER, zoom=16, style={'height': '400px', 'borderRadius': '12px'}, id="estate-map", children=[
            dl.TileLayer(url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> & CartoDB'),
            # Property markers
            *[dl.Marker(position=[p['lat'], p['lng']], children=[
                dl.Tooltip(p['name']),
                dl.Popup(html.Div([
                    html.B(f"🏡 {p['name']}"), html.Br(),
                    f"📍 {p['address']}", html.Br(),
                    f"👥 {p['residents']} residents", html.Br(),
                    f"🔧 {p['features']}", html.Br(),
                    html.I("Real-time occupancy: active")
                ]))
            ], icon=dl.Icon(icon='building', prefix='fa', markerColor='green')) for p in PROPERTIES],
            # Amenity markers
            *[dl.Marker(position=[a['lat'], a['lng']], children=[
                dl.Tooltip(a['name']),
                dl.Popup(html.Div([
                    html.B(f"✨ {a['name']}"), html.Br(),
                    f"🏷️ {a['category']}", html.Br(),
                    f"📌 {a['desc']}", html.Br(),
                    html.Span("available 24/7 for residents", style={'color': '#15803d'})
                ]))
            ], icon=dl.Icon(icon='star', prefix='fa', markerColor='gold')) for a in AMENITIES]
        ]),
        html.P([html.I(className="fas fa-info-circle"), " Markers: 🏡 Residential properties  ✨ Premium amenities around Mwarokin"], style={'fontSize': '0.75rem', 'marginTop': '12px', 'textAlign': 'right'})
    ]),

    # Properties grid
    html.Div(className="section-title", children=[html.I(className="fas fa-crown"), " Premium Residences & Upgraded Living"]),
    dbc.Row([create_card(p, 'property') for p in PROPERTIES], className="cards-grid", id="properties-grid"),

    # Amenities grid
    html.Div(className="section-title", children=[html.I(className="fas fa-spa"), " World‑Class Amenities Around"]),
    dbc.Row([create_card(a, 'amenity') for a in AMENITIES], className="cards-grid", id="amenities-grid"),

    # Feed panel
    html.Div(className="feed-panel", children=[
        html.Div(className="feed-header", children=[
            html.H3([html.I(className="fas fa-broadcast-tower"), html.Span(className="live-dot"), " Real‑Time Resident Monitoring"]),
            html.Span([html.I(className="fas fa-sync-alt"), " live events stream"], style={'fontSize': '0.7rem', 'background': '#00000030', 'padding': '4px 12px', 'borderRadius': '40px'})
        ]),
        html.Div(className="feed-list", id="live-feed", children=[
            html.Div(className="feed-item", children=[
                html.Div(datetime.datetime.now().strftime("%H:%M:%S"), className="feed-time"),
                html.Div(html.I(className="fas fa-microchip"), className="feed-icon"),
                html.Div("🟢 Mwarokin Live Monitor active — all systems nominal", className="feed-text")
            ]),
            html.Div(className="feed-item", children=[
                html.Div(datetime.datetime.now().strftime("%H:%M:%S"), className="feed-time"),
                html.Div(html.I(className="fas fa-map"), className="feed-icon"),
                html.Div("📍 Live location map ready — property & amenity markers synced", className="feed-text")
            ])
        ])
    ]),

    html.Footer([html.I(className="fas fa-shield-alt"), " Mwarokin Estate Management — Smart monitoring, AI-driven insights, live geolocation & upgraded amenities. © 2025"], style={'marginTop': '40px', 'textAlign': 'center', 'color': '#94a3b8', 'fontSize': '0.8rem', 'borderTop': '1px solid #eef2f6', 'paddingTop': '20px'})
])

# ------------------------- CALLBACKS -------------------------
# State variables for simulation
current_residents = 248
current_issues = 4
max_capacity = 300
feed_events = [
    {"time": datetime.datetime.now().strftime("%H:%M:%S"), "icon": "fa-microchip", "text": "🟢 Mwarokin Live Monitor active — all systems nominal"},
    {"time": datetime.datetime.now().strftime("%H:%M:%S"), "icon": "fa-map", "text": "📍 Live location map ready — property & amenity markers synced"},
    {"time": datetime.datetime.now().strftime("%H:%M:%S"), "icon": "fa-chart-line", "text": "👥 Occupancy sensors: real-time resident counting active"},
    {"time": datetime.datetime.now().strftime("%H:%M:%S"), "icon": "fa-solar-panel", "text": "✨ Smart upgrades: New EV chargers & rooftop gardens now live"}
]

event_templates = [
    {"msg": "🚪 Resident access at Gate B — ID verified", "icon": "fa-door-open"},
    {"msg": "🛠️ Maintenance request: AC repair at Sunset Pallazio", "icon": "fa-tools"},
    {"msg": "📦 Package delivery for Emerald Heights resident", "icon": "fa-box"},
    {"msg": "🏊 Pool area usage peak: 34 residents", "icon": "fa-swimmer"},
    {"msg": "🔔 Motion alert: garden wing (secure)", "icon": "fa-shield-alt"},
    {"msg": "💧 Smart irrigation zone 3 active", "icon": "fa-water"},
    {"msg": "📢 Community event: fitness challenge at Vitality Gym", "icon": "fa-calendar-alt"},
    {"msg": "🚨 Security patrol completed: all zones safe", "icon": "fa-check-circle"},
    {"msg": "⚡ Energy consumption peak — grid optimization active", "icon": "fa-charging-station"},
    {"msg": "🏠 New resident check-in at Golden Crest Residences", "icon": "fa-user-plus"},
]

@callback(
    Output('live-residents', 'children'),
    Output('occupancy-rate', 'children'),
    Output('active-issues', 'children'),
    Output('live-feed', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_stats_and_feed(n):
    global current_residents, current_issues, feed_events
    # Update residents
    delta = random.randint(-2, 4)
    new_res = current_residents + delta
    if new_res > max_capacity:
        new_res = max_capacity - 1
    elif new_res < 180:
        new_res = 180
    if new_res != current_residents:
        change_msg = f"👥 +{delta} residents arrived (live occupancy update)" if delta > 0 else f"👥 {delta} residents left estate (visit logs)"
        feed_events.insert(0, {"time": datetime.datetime.now().strftime("%H:%M:%S"), "icon": "fa-users", "text": change_msg})
    current_residents = new_res
    occupancy = round((current_residents / max_capacity) * 100)

    # Update issues
    issue_delta = random.randint(-1, 1)
    new_issues = current_issues + issue_delta
    if new_issues < 1:
        new_issues = 1
    elif new_issues > 8:
        new_issues = 8
    if new_issues != current_issues:
        feed_events.insert(0, {"time": datetime.datetime.now().strftime("%H:%M:%S"), "icon": "fa-clipboard-list", "text": f"⚠️ Active service tickets now: {new_issues} (updated from monitoring)"})
    current_issues = new_issues

    # Random event (70% chance)
    if random.random() < 0.75:
        evt = random.choice(event_templates)
        feed_events.insert(0, {"time": datetime.datetime.now().strftime("%H:%M:%S"), "icon": evt["icon"], "text": evt["msg"]})
    else:
        resident_names = ["Aisha M.", "James K.", "Lina W.", "Omondi R.", "Priya S.", "Ethan N."]
        rand_res = random.choice(resident_names)
        feed_events.insert(0, {"time": datetime.datetime.now().strftime("%H:%M:%S"), "icon": "fa-star", "text": f"📱 {rand_res} submitted amenity feedback via app — 5-star rating"})

    # Random property update
    if random.random() < 0.3:
        prop = random.choice(PROPERTIES)
        feed_events.insert(0, {"time": datetime.datetime.now().strftime("%H:%M:%S"), "icon": "fa-leaf", "text": f"🏡 {prop['name']} — energy efficiency report: 12% reduced consumption"})

    # Keep feed list length <= 18
    if len(feed_events) > 18:
        feed_events = feed_events[:18]

    # Render feed items
    feed_items = []
    for evt in feed_events:
        feed_items.append(html.Div(className="feed-item", children=[
            html.Div(evt["time"], className="feed-time"),
            html.Div(html.I(className=f"fas {evt['icon']}"), className="feed-icon"),
            html.Div(evt["text"], className="feed-text")
        ]))

    return str(current_residents), f"Occupancy: {occupancy}% • live flux", str(current_issues), feed_items

# Interval for real-time updates
app.layout.children.append(dcc.Interval(id='interval-component', interval=8000))  # 8 seconds

# Locate me button: clientside callback to get geolocation and center map
app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks > 0) {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function(position) {
                    var lat = position.coords.latitude;
                    var lng = position.coords.longitude;
                    // Update map center via Dash's setProps
                    var map = document.getElementById('estate-map');
                    if (map && map._leaflet) {
                        map._leaflet.setView([lat, lng], 15);
                    }
                    // Also add a marker for user? We'll just center.
                    // Could trigger a callback to add marker, but for simplicity just center.
                });
            }
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('locate-me-btn', 'n_clicks'),
    Input('locate-me-btn', 'n_clicks'),
    prevent_initial_call=True
)

# ------------------------- RUN -------------------------
if __name__ == '__main__':
    app.run_server(debug=True)
```