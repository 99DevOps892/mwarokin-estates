```python
"""
Mwarokin Estates - Premium Property Management Dashboard
A modern FastAPI backend serving a responsive real estate dashboard with
interactive filtering, mapping, and property management features.

Dependencies:
    fastapi
    uvicorn
    pydantic
    python-multipart (optional, for form data)

Run with:
    uvicorn app:app --reload
"""

import logging
import json
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# 1. Data Models
# --------------------------------------------------------------------------
class Property(BaseModel):
    id: int
    name: str
    location: str
    price: int
    beds: int
    baths: int
    area: str
    status: str  # "occupied" or "vacant"
    imgId: str
    lat: float
    lng: float
    desc: str
    amenities: List[str]

class PropertyFilterParams(BaseModel):
    search: Optional[str] = None
    location: Optional[str] = None
    beds: Optional[int] = None
    price_range: Optional[str] = None  # "all", "0-30000", "30000-80000", "80000+"

# --------------------------------------------------------------------------
# 2. Mock Database (In-memory)
# --------------------------------------------------------------------------
PROPERTIES_DB: List[Property] = [
    Property(
        id=1,
        name="The Horizon Villa",
        location="Kangemi",
        price=125000,
        beds=4,
        baths=3,
        area="280 sqm",
        status="occupied",
        imgId="101",
        lat=-1.2921,
        lng=36.8219,
        desc="Luxury villa with private pool, smart home ready.",
        amenities=["Pool", "Gym", "Smart Security"]
    ),
    Property(
        id=2,
        name="Silver Springs Manor",
        location="Westlands",
        price=185000,
        beds=5,
        baths=4,
        area="350 sqm",
        status="vacant",
        imgId="104",
        lat=-1.2698,
        lng=36.8034,
        desc="Premium gated community with panoramic views.",
        amenities=["Jacuzzi", "Garden", "EV Charging"]
    ),
    Property(
        id=3,
        name="Kiambu Oasis",
        location="Kiambu",
        price=45000,
        beds=3,
        baths=2,
        area="160 sqm",
        status="vacant",
        imgId="107",
        lat=-1.1765,
        lng=36.8284,
        desc="Modern family home near schools.",
        amenities=["Solar Panels", "Lawn"]
    ),
    Property(
        id=4,
        name="Taveta Courtyard",
        location="Taveta",
        price=32000,
        beds=2,
        baths=2,
        area="105 sqm",
        status="occupied",
        imgId="115",
        lat=-3.4024,
        lng=37.6910,
        desc="Cosy apartment, close to CBD.",
        amenities=["Parking", "CCTV"]
    ),
    Property(
        id=5,
        name="Jericho Heights",
        location="Jericho",
        price=22000,
        beds=2,
        baths=1,
        area="78 sqm",
        status="vacant",
        imgId="127",
        lat=-1.2855,
        lng=36.8509,
        desc="Affordable modern unit with fast internet.",
        amenities=["Fiber", "Playground"]
    ),
    Property(
        id=6,
        name="Palmwood Residences",
        location="Westlands",
        price=98000,
        beds=3,
        baths=3,
        area="210 sqm",
        status="occupied",
        imgId="131",
        lat=-1.2630,
        lng=36.8020,
        desc="Luxury duplex with rooftop terrace.",
        amenities=["Rooftop", "Concierge"]
    ),
    Property(
        id=7,
        name="Riverside Executive",
        location="Kangemi",
        price=165000,
        beds=4,
        baths=4,
        area="310 sqm",
        status="vacant",
        imgId="143",
        lat=-1.2848,
        lng=36.8152,
        desc="Elegant riverside estate with smart features.",
        amenities=["Wine Cellar", "Home Office"]
    ),
    Property(
        id=8,
        name="Mountain View Cottages",
        location="Kiambu",
        price=55000,
        beds=3,
        baths=2,
        area="145 sqm",
        status="occupied",
        imgId="156",
        lat=-1.1690,
        lng=36.8370,
        desc="Scenic mountain view home.",
        amenities=["Fireplace", "Backyard"]
    ),
]

# --------------------------------------------------------------------------
# 3. Filtering Logic
# --------------------------------------------------------------------------
def apply_filters(
    properties: List[Property],
    search: Optional[str] = None,
    location: Optional[str] = None,
    beds: Optional[int] = None,
    price_range: Optional[str] = None
) -> List[Property]:
    """Apply all filters to the property list."""
    filtered = properties

    if search:
        search_lower = search.lower()
        filtered = [
            p for p in filtered
            if search_lower in p.name.lower() or search_lower in p.location.lower()
        ]

    if location and location != "all":
        filtered = [p for p in filtered if p.location == location]

    if beds and beds > 0:
        filtered = [p for p in filtered if p.beds >= beds]

    if price_range and price_range != "all":
        if price_range == "0-30000":
            filtered = [p for p in filtered if p.price <= 30000]
        elif price_range == "30000-80000":
            filtered = [p for p in filtered if 30000 <= p.price <= 80000]
        elif price_range == "80000+":
            filtered = [p for p in filtered if p.price > 80000]

    return filtered

# --------------------------------------------------------------------------
# 4. FastAPI Application
# --------------------------------------------------------------------------
app = FastAPI(
    title="Mwarokin Estates API",
    description="Premium property management and intelligence backend.",
    version="1.0.0",
)

# --------------------------------------------------------------------------
# 5. API Endpoints
# --------------------------------------------------------------------------
@app.get("/api/properties", response_model=List[Property])
async def get_properties(
    search: Optional[str] = Query(None, description="Search by name or location"),
    location: Optional[str] = Query("all", description="Filter by area"),
    beds: Optional[int] = Query(0, description="Minimum number of bedrooms", ge=0),
    price_range: Optional[str] = Query("all", description="Price range: all, 0-30000, 30000-80000, 80000+")
):
    """
    Retrieve properties with optional filtering.
    """
    logger.info(f"Fetching properties with filters: search='{search}', location='{location}', beds={beds}, price_range='{price_range}'")
    try:
        filtered = apply_filters(PROPERTIES_DB, search, location, beds, price_range)
        return filtered
    except Exception as e:
        logger.error(f"Error filtering properties: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """
    Serve the main property management dashboard HTML.
    """
    # The complete UI is embedded here for a single‑file deployment.
    # In production, you would serve static files separately.
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>Mwarokin Estates · Home Management</title>
      <!-- Font Awesome (icons) -->
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" />
      <!-- Leaflet CSS -->
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
      <style>
        * { margin:0; padding:0; box-sizing:border-box; font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif; }
        body { background:#f2f6fc; color:#1a2b3c; padding:24px; }
        .container { max-width:1320px; margin:0 auto; }
        /* Header */
        .header { display:flex; justify-content:space-between; align-items:center; background:white; border-radius:32px; padding:18px 32px; box-shadow:0 8px 32px rgba(0,20,50,0.06); margin-bottom:28px; flex-wrap:wrap; }
        .logo h1 { font-size:26px; font-weight:700; color:#0b1e33; display:flex; align-items:center; }
        .logo span { font-size:14px; color:#5c7a9a; font-weight:400; margin-left:6px; }
        .header-actions { display:flex; align-items:center; gap:20px; }
        .notif-badge { position:relative; cursor:pointer; }
        .badge-count { background:#e53e3e; color:white; border-radius:40px; padding:0 8px; font-size:12px; font-weight:600; position:absolute; top:-6px; right:-8px; }
        .avatar { background:#2c5282; color:white; width:44px; height:44px; border-radius:40px; display:flex; align-items:center; justify-content:center; font-weight:600; font-size:18px; }
        /* Stats */
        .stats-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:16px; margin-bottom:28px; }
        .stat-card { background:white; border-radius:28px; padding:20px 24px; box-shadow:0 4px 16px rgba(0,0,0,0.02); border:1px solid #edf2f7; }
        .stat-title { font-size:15px; color:#5c7a9a; font-weight:500; letter-spacing:0.3px; }
        .stat-number { font-size:32px; font-weight:700; color:#0b1e33; margin:6px 0 2px; }
        .stat-trend { font-size:14px; color:#2b6cb0; background:#e8f0fe; padding:2px 12px; border-radius:40px; display:inline-block; }
        /* Filter Bar */
        .filter-bar { display:flex; flex-wrap:wrap; gap:12px; background:white; padding:16px 24px; border-radius:60px; align-items:center; box-shadow:0 4px 20px rgba(0,0,0,0.02); margin-bottom:28px; border:1px solid #edf2f7; }
        .filter-group { display:flex; align-items:center; gap:8px; background:#f8fafd; padding:6px 16px 6px 12px; border-radius:40px; }
        .filter-group i { color:#5c7a9a; font-size:14px; }
        .filter-group input, .filter-group select { background:transparent; border:none; padding:8px 4px; font-size:15px; color:#1a2b3c; outline:none; min-width:120px; }
        .filter-group select { cursor:pointer; }
        .search-btn { background:#2563eb; color:white; border:none; padding:10px 24px; border-radius:40px; font-weight:600; font-size:15px; display:flex; align-items:center; gap:8px; cursor:pointer; transition:0.2s; }
        .search-btn:hover { background:#1a4b9e; transform:scale(1.02); }
        /* Section header */
        .section-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; flex-wrap:wrap; }
        .section-header h3 { font-size:22px; }
        /* Property Grid */
        .property-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:24px; margin-bottom:32px; }
        .property-card { background:white; border-radius:32px; overflow:hidden; box-shadow:0 8px 28px rgba(0,0,0,0.03); border:1px solid #edf2f7; transition:0.2s; }
        .property-card:hover { transform:translateY(-4px); box-shadow:0 16px 40px rgba(0,20,50,0.08); }
        .card-img { height:180px; position:relative; }
        .card-badge { position:absolute; top:14px; right:14px; padding:6px 14px; border-radius:40px; font-size:13px; font-weight:600; color:white; }
        .card-content { padding:18px 20px 20px; }
        .property-title { font-size:20px; font-weight:700; color:#0b1e33; }
        .property-location { font-size:14px; color:#5c7a9a; margin:4px 0 6px; }
        .property-location i { margin-right:4px; }
        .property-price { font-size:22px; font-weight:700; color:#1a3a5c; margin:8px 0 6px; }
        .property-price span { font-weight:400; color:#5c7a9a; }
        .property-features { display:flex; gap:14px; font-size:14px; color:#3a4f6b; margin:8px 0 12px; }
        .property-features span { display:flex; align-items:center; gap:4px; }
        .card-actions { display:flex; gap:10px; }
        .btn-outline-premium, .btn-primary-premium { border:none; padding:10px 16px; border-radius:40px; font-weight:600; font-size:14px; cursor:pointer; transition:0.15s; display:inline-flex; align-items:center; gap:6px; }
        .btn-outline-premium { background:transparent; border:1px solid #d0dbe8; color:#1a2b3c; }
        .btn-outline-premium:hover { background:#f0f4fa; border-color:#a0b8d0; }
        .btn-primary-premium { background:#2563eb; color:white; }
        .btn-primary-premium:hover { background:#1a4b9e; }
        /* Insight row */
        .insight-row { display:grid; grid-template-columns:2fr 1fr; gap:24px; margin-bottom:32px; }
        .map-card, .recent-activities { background:white; border-radius:32px; padding:20px 24px; border:1px solid #edf2f7; }
        .map-card #propertyMap { height:240px; border-radius:24px; background:#e8edf4; }
        .activity-item { display:flex; gap:12px; padding:12px 0; border-bottom:1px solid #f0f4fa; align-items:center; }
        .activity-item i { font-size:18px; color:#2c5282; width:28px; text-align:center; }
        .activity-item div { font-size:15px; color:#1a2b3c; }
        .activity-item strong { font-weight:600; }
        /* Modal */
        .modal { display:none; position:fixed; top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.3); backdrop-filter:blur(6px); justify-content:center;align-items:center;z-index:1000; }
        .modal-container { background:white; max-width:600px; width:90%; border-radius:40px; padding:32px; box-shadow:0 40px 80px rgba(0,0,0,0.2); animation:fadeIn 0.25s ease; }
        .modal-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; }
        .modal-header h3 { font-size:24px; }
        @keyframes fadeIn { from{opacity:0;transform:scale(0.96);} to{opacity:1;transform:scale(1);} }
        /* Responsive */
        @media (max-width:768px) { .insight-row { grid-template-columns:1fr; } .filter-bar { border-radius:32px; } .filter-group { flex:1 1 auto; } }
      </style>
    </head>
    <body>
    <div class="container">
      <!-- header -->
      <div class="header">
        <div class="logo">
          <h1><i class="fas fa-building" style="color:#2563eb; margin-right: 8px;"></i> Mwarokin Estates</h1>
          <span>Home Management • Intelligent Portfolio</span>
        </div>
        <div class="header-actions">
          <div class="notif-badge"><i class="fas fa-bell fa-lg" style="color:#2c5282;"></i><span class="badge-count">3</span></div>
          <div class="avatar">MW</div>
        </div>
      </div>

      <!-- stats -->
      <div class="stats-grid">
        <div class="stat-card"><div class="stat-title">Total Properties</div><div class="stat-number" id="totalProps">24</div><span class="stat-trend">+2 this month</span></div>
        <div class="stat-card"><div class="stat-title">Occupied Homes</div><div class="stat-number" id="occupiedCount">18</div><span class="stat-trend">75% occupancy</span></div>
        <div class="stat-card"><div class="stat-title">Vacant Listings</div><div class="stat-number" id="vacantCount">6</div><span class="stat-trend">↓ 1 from last week</span></div>
        <div class="stat-card"><div class="stat-title">Monthly Revenue</div><div class="stat-number">KSh 1.28M</div><span class="stat-trend">+8.2%</span></div>
      </div>

      <!-- advanced filter bar -->
      <div class="filter-bar">
        <div class="filter-group"><i class="fas fa-search"></i><input type="text" id="searchInput" placeholder="Search by name or location..."></div>
        <div class="filter-group"><i class="fas fa-map-marker-alt"></i><select id="locationFilter"><option value="all">All Areas</option><option value="Kangemi">Kangemi</option><option value="Westlands">Westlands</option><option value="Kiambu">Kiambu</option><option value="Taveta">Taveta</option><option value="Jericho">Jericho</option></select></div>
        <div class="filter-group"><i class="fas fa-bed"></i><select id="bedsFilter"><option value="0">Any Beds</option><option value="1">1+ Bed</option><option value="2">2+ Beds</option><option value="3">3+ Beds</option></select></div>
        <div class="filter-group"><i class="fas fa-tag"></i><select id="priceFilter"><option value="all">All Prices</option><option value="0-30000">Under KSh 30k</option><option value="30000-80000">KSh 30k - 80k</option><option value="80000+">Above KSh 80k</option></select></div>
        <button class="search-btn" id="applyFilterBtn"><i class="fas fa-sliders-h"></i> Apply Filters</button>
      </div>

      <!-- property grid -->
      <div class="section-header"><h3 style="font-weight: 700;"><i class="fas fa-home"></i> Premium Residences</h3><span id="resultCount" style="color:#5c7a9a;">6 properties available</span></div>
      <div class="property-grid" id="propertyGrid"></div>

      <!-- Map + recent insights -->
      <div class="insight-row">
        <div class="map-card"><h4 style="margin-bottom: 12px;"><i class="fas fa-map-pin"></i> Property Intelligence Map</h4><div id="propertyMap"></div></div>
        <div class="recent-activities"><h4 style="margin-bottom: 16px;"><i class="fas fa-clock"></i> Recent Home Management Activity</h4>
          <div id="activityFeed">
            <div class="activity-item"><i class="fas fa-calendar-check" style="color:#2b6cb0;"></i><div><strong>Villa A</strong> – Tour scheduled with client (Today 3PM)</div></div>
            <div class="activity-item"><i class="fas fa-file-signature"></i><div><strong>Sunset Apartment</strong> – Lease renewal signed by tenant</div></div>
            <div class="activity-item"><i class="fas fa-wrench"></i><div><strong>Kiambu Bungalow</strong> – Maintenance request completed</div></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Property Detail Management Modal -->
    <div id="propertyModal" class="modal">
      <div class="modal-container">
        <div class="modal-header"><h3 id="modalTitle">Property Management</h3><button id="closeModalBtn" style="background: none; border: none; font-size: 24px; cursor:pointer;">&times;</button></div>
        <div id="modalBodyContent"><p>Loading details...</p></div>
        <div style="display: flex; gap: 12px; margin-top: 24px;">
          <button class="btn-outline-premium" id="scheduleTourModalBtn"><i class="fas fa-calendar-alt"></i> Schedule Tour</button>
          <button class="btn-primary-premium" id="manageHomeModalBtn"><i class="fas fa-tools"></i> Manage Home</button>
        </div>
      </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
      // ------------------------------------------------------------------
      //  JavaScript – consumes the FastAPI backend
      // ------------------------------------------------------------------
      let activeProperties = [];
      let mapInstance = null;
      let markersLayer = [];
      let currentModalProperty = null;

      const API_BASE = '/api/properties';

      // Format currency
      function formatKES(amount) {
        return 'KSh ' + Number(amount).toLocaleString();
      }

      // Fetch properties with current filters
      async function fetchProperties() {
        const search = document.getElementById('searchInput').value;
        const location = document.getElementById('locationFilter').value;
        const beds = document.getElementById('bedsFilter').value;
        const price_range = document.getElementById('priceFilter').value;

        const params = new URLSearchParams({
          search: search,
          location: location,
          beds: beds,
          price_range: price_range
        });

        try {
          const response = await fetch(API_BASE + '?' + params.toString());
          if (!response.ok) throw new Error('Network error');
          const data = await response.json();
          activeProperties = data;
          renderProperties(activeProperties);
          updateMapMarkers(activeProperties);
          updateStats(activeProperties);
        } catch (error) {
          console.error('Failed to fetch properties:', error);
          document.getElementById('propertyGrid').innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:40px;">⚠️ Error loading properties</div>';
        }
      }

      // Render property cards
      function renderProperties(propArray) {
        const grid = document.getElementById('propertyGrid');
        grid.innerHTML = '';
        if (propArray.length === 0) {
          grid.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:40px;">🏡 No properties match filters</div>';
          document.getElementById('resultCount').innerText = '0 properties';
          return;
        }
        document.getElementById('resultCount').innerText = propArray.length + ' properties';
        propArray.forEach(prop => {
          const statusText = prop.status === 'occupied' ? 'Occupied' : 'Available';
          const statusColor = prop.status === 'occupied' ? '#2b6e3c' : '#0f5c7a';
          const imageUrl = `https://picsum.photos/id/${prop.imgId}/400/240`;
          const card = document.createElement('div');
          card.className = 'property-card';
          card.innerHTML = `
            <div class="card-img" style="background-image: url('${imageUrl}'); background-size: cover;">
              <span class="card-badge" style="background: ${statusColor};">${statusText}</span>
            </div>
            <div class="card-content">
              <div class="property-title">${prop.name}</div>
              <div class="property-location"><i class="fas fa-map-pin"></i> ${prop.location}</div>
              <div class="property-price">${formatKES(prop.price)}<span style="font-size:14px; font-weight:normal;">/month</span></div>
              <div class="property-features"><span><i class="fas fa-bed"></i> ${prop.beds} beds</span><span><i class="fas fa-bath"></i> ${prop.baths} baths</span><span><i class="fas fa-arrows-alt"></i> ${prop.area}</span></div>
              <div class="card-actions">
                <button class="btn-outline-premium view-details" data-id="${prop.id}"><i class="fas fa-eye"></i> Details</button>
                <button class="btn-primary-premium schedule-quick" data-id="${prop.id}"><i class="fas fa-calendar-week"></i> Tour</button>
              </div>
            </div>
          `;
          grid.appendChild(card);
        });

        // Attach event listeners
        document.querySelectorAll('.view-details').forEach(btn => {
          btn.addEventListener('click', () => {
            const id = parseInt(btn.dataset.id);
            const prop = activeProperties.find(p => p.id === id);
            if (prop) openPropertyModal(prop);
          });
        });
        document.querySelectorAll('.schedule-quick').forEach(btn => {
          btn.addEventListener('click', () => {
            const id = parseInt(btn.dataset.id);
            const prop = activeProperties.find(p => p.id === id);
            if (prop) quickScheduleTour(prop);
          });
        });
      }

      // Update stats (computed from visible properties)
      function updateStats(visibleProps) {
        const total = visibleProps.length;
        const occupied = visibleProps.filter(p => p.status === 'occupied').length;
        const vacant = total - occupied;
        document.getElementById('totalProps').innerText = total;
        document.getElementById('occupiedCount').innerText = occupied;
        document.getElementById('vacantCount').innerText = vacant;
      }

      // Map
      function initMap() {
        if (mapInstance) mapInstance.remove();
        mapInstance = L.map('propertyMap').setView([-1.2864, 36.8172], 12);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> & CartoDB'
        }).addTo(mapInstance);
        updateMapMarkers(activeProperties);
      }

      function updateMapMarkers(propertiesArr) {
        if (!mapInstance) return;
        markersLayer.forEach(marker => mapInstance.removeLayer(marker));
        markersLayer = [];
        propertiesArr.forEach(prop => {
          if (prop.lat && prop.lng) {
            const marker = L.marker([prop.lat, prop.lng]).addTo(mapInstance)
              .bindPopup(`<b>${prop.name}</b><br>${prop.location}<br>${formatKES(prop.price)}/month<br><i>${prop.status}</i>`);
            markersLayer.push(marker);
          }
        });
        if (propertiesArr.length > 0 && propertiesArr[0].lat) {
          mapInstance.setView([propertiesArr[0].lat, propertiesArr[0].lng], 13);
        }
      }

      // Modal
      function openPropertyModal(prop) {
        currentModalProperty = prop;
        const modal = document.getElementById('propertyModal');
        document.getElementById('modalTitle').innerText = `🏡 ${prop.name} • Management Hub`;
        const body = document.getElementById('modalBodyContent');
        body.innerHTML = `
          <div style="margin-bottom:16px;"><img src="https://picsum.photos/id/${prop.imgId}/500/280" style="width:100%; border-radius:24px; object-fit:cover;"></div>
          <p><strong><i class="fas fa-map-marker-alt"></i> Location:</strong> ${prop.location}</p>
          <p><strong>💰 Monthly Rent:</strong> ${formatKES(prop.price)}</p>
          <p><strong>🛏️ Bedrooms:</strong> ${prop.beds} | 🛁 Bathrooms: ${prop.baths} | 📐 Area: ${prop.area}</p>
          <p><strong>✨ Amenities:</strong> ${prop.amenities.join(', ')}</p>
          <p><strong>📋 Status:</strong> <span style="background:${prop.status === 'occupied' ? '#e6f7e6' : '#fff3e0'}; padding:4px 12px; border-radius:40px;">${prop.status === 'occupied' ? 'Occupied' : 'Vacant / Available'}</span></p>
          <p><strong>🏠 Description:</strong> ${prop.desc}</p>
          <div style="background:#f8fafd; padding:12px; border-radius:20px; margin-top:12px;"><i class="fas fa-chart-line"></i> <strong>Home Management Insights:</strong> Last maintenance: 25 days ago, Lease health: ${prop.status === 'occupied' ? 'Active' : 'Ready for lease'}</div>
        `;
        modal.style.display = 'flex';
      }

      function quickScheduleTour(prop) {
        alert(`✨ Tour request sent for ${prop.name} (${prop.location}). Our property manager will confirm within 2 hours.`);
        addActivity(`${prop.name} – Tour inquiry via Home Management panel`);
      }

      function addActivity(msg) {
        const feed = document.getElementById('activityFeed');
        const newItem = document.createElement('div');
        newItem.className = 'activity-item';
        newItem.innerHTML = `<i class="fas fa-bell" style="color:#2563eb;"></i><div><strong>${msg}</strong> – just now</div>`;
        feed.prepend(newItem);
        if (feed.children.length > 5) feed.removeChild(feed.lastChild);
      }

      // Event listeners
      document.getElementById('closeModalBtn').addEventListener('click', () => {
        document.getElementById('propertyModal').style.display = 'none';
      });
      document.getElementById('scheduleTourModalBtn').addEventListener('click', () => {
        if (currentModalProperty) quickScheduleTour(currentModalProperty);
        document.getElementById('propertyModal').style.display = 'none';
      });
      document.getElementById('manageHomeModalBtn').addEventListener('click', () => {
        if (currentModalProperty) {
          alert(`🔧 Manage Home: "${currentModalProperty.name}" – Advanced options: lease renewal, maintenance log, financial report. (Demo) Full CRM integration ready.`);
          addActivity(`Management action triggered for ${currentModalProperty.name}`);
        }
        document.getElementById('propertyModal').style.display = 'none';
      });
      window.onclick = function(e) {
        if (e.target === document.getElementById('propertyModal')) {
          document.getElementById('propertyModal').style.display = 'none';
        }
      };

      document.getElementById('applyFilterBtn').addEventListener('click', fetchProperties);
      document.getElementById('searchInput').addEventListener('keyup', fetchProperties);

      // Initialise
      window.addEventListener('load', () => {
        fetchProperties().then(() => {
          initMap();
        });
      });
    </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# --------------------------------------------------------------------------
# 6. Application Entry Point
# --------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
```