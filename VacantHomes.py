I've created a modern, fully functional Python Flask application for the Mwarokin Estates property management dashboard, complete with dynamic data and interactive features.
```python
"""
Mwarokin Estates - Property Management Dashboard
A modern Flask application for managing vacant homes and property listings.

Requirements:
    Flask==2.3.3
    python-dotenv==1.0.0
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from flask import Flask, abort, jsonify, render_template, request, url_for

# ─── CONFIGURATION ──────────────────────────────────────────────────────────────


class Config:
    """Application configuration."""

    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG: bool = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    PORT: int = int(os.environ.get("PORT", 5000))


# ─── DATA MODELS ────────────────────────────────────────────────────────────────


@dataclass
class Address:
    """Property address information."""

    street: str
    area: str
    city: str = "Nairobi"
    country: str = "Kenya"

    def full(self) -> str:
        return f"{self.street}, {self.area}, {self.city}"

    def short(self) -> str:
        return f"{self.area}, {self.city}"


@dataclass
class Features:
    """Property features and specifications."""

    bedrooms: int
    bathrooms: float
    area_sqft: int
    parking_spots: int = 1
    has_garden: bool = False
    has_pool: bool = False
    has_gym: bool = False
    furnished: bool = False

    def to_list(self) -> List[Dict[str, str | int]]:
        """Convert features to a list of display items."""
        items = [
            {"icon": "bed", "label": f"{self.bedrooms} Beds"},
            {"icon": "bath", "label": f"{self.bathrooms} Baths"},
            {"icon": "ruler-combined", "label": f"{self.area_sqft:,} sqft"},
            {"icon": "car", "label": f"{self.parking_spots} Parking"},
        ]
        if self.has_garden:
            items.append({"icon": "tree", "label": "Garden"})
        if self.has_pool:
            items.append({"icon": "swimming-pool", "label": "Pool"})
        if self.has_gym:
            items.append({"icon": "dumbbell", "label": "Gym"})
        if self.furnished:
            items.append({"icon": "couch", "label": "Furnished"})
        return items


@dataclass
class Property:
    """Complete property listing."""

    id: int
    title: str
    address: Address
    price: int  # Monthly rent in USD
    features: Features
    description: str
    images: List[str] = field(default_factory=list)
    is_vacant: bool = True
    is_favorite: bool = False
    image_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def price_display(self) -> str:
        """Formatted price string."""
        return f"${self.price:,} / mo"

    @property
    def location_display(self) -> str:
        """Short location string."""
        return self.address.short()

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        data = asdict(self)
        data["price_display"] = self.price_display
        data["location_display"] = self.location_display
        data["created_at"] = self.created_at.isoformat() if self.created_at else None
        data["features_list"] = self.features.to_list()
        return data


# ─── SAMPLE DATA ────────────────────────────────────────────────────────────────


def get_sample_properties() -> List[Property]:
    """Generate sample property data for the dashboard."""
    return [
        Property(
            id=1,
            title="Modern Downtown Apartment",
            address=Address("123 Main Street", "Downtown"),
            price=2500,
            features=Features(bedrooms=3, bathrooms=2, area_sqft=1850, parking_spots=1),
            description="Stunning modern apartment in the heart of downtown offering breathtaking city views and premium finishes. Features an open floor plan, gourmet kitchen with stainless steel appliances, and access to a rooftop terrace.",
            images=[
                "https://images.unsplash.com/photo-1568605114967-8130f3a36994?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
            ],
            image_count=8,
        ),
        Property(
            id=2,
            title="Luxury Westlands Villa",
            address=Address("456 Oak Avenue", "Westlands"),
            price=3200,
            features=Features(
                bedrooms=4,
                bathrooms=3,
                area_sqft=2400,
                parking_spots=2,
                has_garden=True,
                has_pool=True,
            ),
            description="Elegant villa in prestigious Westlands with a gourmet kitchen, luxurious master suite, and private backyard. Includes a two-car garage and is close to shopping, dining, and top-rated schools.",
            images=[
                "https://images.unsplash.com/photo-1513584684374-8bab748fbf90?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
            ],
            is_favorite=True,
            image_count=12,
        ),
        Property(
            id=3,
            title="Cozy Kilimani Condo",
            address=Address("789 Pine Road", "Kilimani"),
            price=1800,
            features=Features(bedrooms=2, bathrooms=1, area_sqft=1200, parking_spots=1),
            description="Charming condo in vibrant Kilimani with an open floor plan, hardwood floors, and a private balcony. Within walking distance to cafes, restaurants, and public transport. Perfect for professionals.",
            images=[
                "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
            ],
            image_count=6,
        ),
        Property(
            id=4,
            title="Riverside Penthouse",
            address=Address("101 Skyline Drive", "Riverside"),
            price=4500,
            features=Features(
                bedrooms=3,
                bathrooms=3,
                area_sqft=2800,
                parking_spots=2,
                has_gym=True,
                furnished=True,
            ),
            description="Luxurious penthouse with panoramic views, floor-to-ceiling windows, and high-end finishes. Features a private rooftop terrace, smart home technology, and 24-hour concierge service.",
            images=[
                "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
            ],
            image_count=10,
        ),
        Property(
            id=5,
            title="Garden Home in Lavington",
            address=Address("234 Garden Lane", "Lavington"),
            price=2100,
            features=Features(
                bedrooms=3,
                bathrooms=2,
                area_sqft=1950,
                parking_spots=1,
                has_garden=True,
            ),
            description="Beautiful garden home surrounded by lush greenery. Features a spacious living area, modern kitchen, and a private garden perfect for entertaining. Located in a quiet, family-friendly neighborhood.",
            images=[
                "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
            ],
            image_count=9,
        ),
        Property(
            id=6,
            title="Modern Loft in Kilimani",
            address=Address("567 Loft Street", "Kilimani"),
            price=1950,
            features=Features(bedrooms=2, bathrooms=2, area_sqft=1400, parking_spots=1),
            description="Modern loft-style apartment with exposed brick and high ceilings. Open-concept living and dining area, gourmet kitchen, and a balcony with city views. Close to nightlife and dining.",
            images=[
                "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
            ],
            image_count=7,
        ),
    ]


# ─── DATA STORE ─────────────────────────────────────────────────────────────────


class PropertyStore:
    """In-memory property data store."""

    def __init__(self) -> None:
        self._properties: Dict[int, Property] = {}
        self._next_id: int = 100
        self._load_sample_data()

    def _load_sample_data(self) -> None:
        """Load sample properties into the store."""
        for prop in get_sample_properties():
            self._properties[prop.id] = prop
            if prop.id >= self._next_id:
                self._next_id = prop.id + 1

    def get_all(self, vacant_only: bool = False) -> List[Property]:
        """Get all properties, optionally filtered by vacancy."""
        props = list(self._properties.values())
        if vacant_only:
            props = [p for p in props if p.is_vacant]
        return sorted(props, key=lambda p: p.id)

    def get_by_id(self, property_id: int) -> Optional[Property]:
        """Get a property by ID."""
        return self._properties.get(property_id)

    def get_vacant_count(self) -> int:
        """Get the number of vacant properties."""
        return sum(1 for p in self._properties.values() if p.is_vacant)

    def get_stats(self) -> Dict[str, int | str]:
        """Get dashboard statistics."""
        total = len(self._properties)
        vacant = self.get_vacant_count()
        active_agents = 18
        monthly_revenue = 82500
        return {
            "total_properties": total,
            "vacant_homes": vacant,
            "active_agents": active_agents,
            "monthly_revenue": f"${monthly_revenue:,}",
        }

    def toggle_favorite(self, property_id: int) -> Optional[Property]:
        """Toggle the favorite status of a property."""
        prop = self._properties.get(property_id)
        if prop:
            prop.is_favorite = not prop.is_favorite
        return prop

    def get_recent_activity(self, limit: int = 4) -> List[Dict]:
        """Get recent activity items."""
        activities = [
            {
                "icon": "key",
                "icon_class": "gold-bg",
                "title": "New Lease Signed",
                "description": "Property at 567 Elm Street leased to Robert Johnson",
                "time": "2 hours ago",
            },
            {
                "icon": "home",
                "icon_class": "blue-bg",
                "title": "Property Added",
                "description": "New vacant listing at 321 Maple Avenue",
                "time": "5 hours ago",
            },
            {
                "icon": "file-invoice-dollar",
                "icon_class": "green-bg",
                "title": "Payment Received",
                "description": "Rent payment from Michael Brown for 159 Oak Lane",
                "time": "Yesterday",
            },
            {
                "icon": "calendar-check",
                "icon_class": "gold-bg",
                "title": "Viewing Scheduled",
                "description": "Tour booked for 123 Main Street with Sarah Kim",
                "time": "Yesterday",
            },
        ]
        return activities[:limit]


# ─── FLASK APPLICATION ──────────────────────────────────────────────────────────


app = Flask(__name__)
app.config.from_object(Config)

# Initialize the data store
store = PropertyStore()


# ─── ROUTES ─────────────────────────────────────────────────────────────────────


@app.route("/")
def dashboard() -> str:
    """Render the main dashboard page."""
    properties = store.get_all(vacant_only=True)
    stats = store.get_stats()
    recent_activity = store.get_recent_activity()

    return render_template(
        "index.html",
        properties=properties,
        stats=stats,
        recent_activity=recent_activity,
        user_name="John Doe",
        user_role="Property Manager",
    )


@app.route("/api/properties")
def api_properties() -> str:
    """API endpoint for all properties."""
    vacant_only = request.args.get("vacant", "true").lower() == "true"
    properties = store.get_all(vacant_only=vacant_only)
    return jsonify([p.to_dict() for p in properties])


@app.route("/api/properties/<int:property_id>")
def api_property_detail(property_id: int) -> str:
    """API endpoint for a single property."""
    prop = store.get_by_id(property_id)
    if not prop:
        abort(404, description=f"Property {property_id} not found")
    return jsonify(prop.to_dict())


@app.route("/api/properties/<int:property_id>/favorite", methods=["POST"])
def api_toggle_favorite(property_id: int) -> str:
    """Toggle favorite status for a property."""
    prop = store.toggle_favorite(property_id)
    if not prop:
        abort(404, description=f"Property {property_id} not found")
    return jsonify({"success": True, "favorite": prop.is_favorite})


@app.route("/api/stats")
def api_stats() -> str:
    """API endpoint for dashboard statistics."""
    return jsonify(store.get_stats())


@app.route("/api/activity")
def api_activity() -> str:
    """API endpoint for recent activity."""
    limit = request.args.get("limit", 4, type=int)
    return jsonify(store.get_recent_activity(limit))


# ─── TEMPLATE FILTERS ──────────────────────────────────────────────────────────


@app.template_filter("json")
def to_json(value) -> str:
    """Convert a Python object to JSON string for use in templates."""
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return json.dumps(value, default=str)


@app.template_filter("format_price")
def format_price(value: int) -> str:
    """Format a price value."""
    return f"${value:,} / mo"


# ─── ERROR HANDLERS ────────────────────────────────────────────────────────────


@app.errorhandler(404)
def not_found(error) -> tuple[str, int]:
    """Handle 404 errors."""
    return jsonify({"error": "Resource not found", "status": 404}), 404


@app.errorhandler(500)
def server_error(error) -> tuple[str, int]:
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error", "status": 500}), 500


# ─── APPLICATION ENTRY POINT ──────────────────────────────────────────────────


def main() -> None:
    """Run the Flask application."""
    app.run(
        host="0.0.0.0",
        port=Config.PORT,
        debug=Config.DEBUG,
    )


if __name__ == "__main__":
    main()

```

And here's the HTML template that goes with it:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Mwarokin Estates · Vacant Homes</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400;14..32,500;14..32,600;14..32,700&display=swap" rel="stylesheet" />
    <style>
        /* ── RESET & BASE ── */
        *,
        *::before,
        *::after {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        :root {
            --gold: #c9a84c;
            --gold-light: #e8d5a3;
            --gold-dark: #a8892e;
            --slate: #7a8a9e;
            --slate-light: #eef1f5;
            --bg: #f7f9fc;
            --card-bg: #ffffff;
            --text: #1a2634;
            --text-muted: #6b7a8d;
            --border: #e4e9f0;
            --shadow: 0 8px 30px rgba(0, 0, 0, 0.06);
            --shadow-hover: 0 16px 48px rgba(0, 0, 0, 0.10);
            --radius: 16px;
            --radius-sm: 10px;
            --transition: 0.25s ease;
            --sidebar-width: 260px;
            --topbar-height: 72px;
        }
        html {
            scroll-behavior: smooth;
        }
        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--bg);
            color: var(--text);
            display: flex;
            min-height: 100vh;
        }
        a {
            text-decoration: none;
            color: inherit;
        }
        button {
            cursor: pointer;
            font-family: inherit;
            border: none;
            background: none;
            font-size: inherit;
        }
        img {
            display: block;
            max-width: 100%;
        }
        .app {
            display: flex;
            width: 100%;
            min-height: 100vh;
        }

        /* ── SIDEBAR ── */
        .sidebar {
            width: var(--sidebar-width);
            background: linear-gradient(180deg, #0d1b2a 0%, #162433 100%);
            color: rgba(255, 255, 255, 0.8);
            padding: 1.5rem 1rem;
            display: flex;
            flex-direction: column;
            position: sticky;
            top: 0;
            height: 100vh;
            overflow-y: auto;
            flex-shrink: 0;
            z-index: 100;
            transition: transform var(--transition);
        }
        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            margin-bottom: 1.5rem;
        }
        .brand-icon {
            width: 40px;
            height: 40px;
            background: var(--gold);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
            color: #0d1b2a;
            flex-shrink: 0;
        }
        .sidebar-brand h1 {
            font-size: 1.2rem;
            font-weight: 700;
            color: #fff;
            letter-spacing: -0.3px;
        }
        .sidebar-brand h1 span {
            color: var(--gold);
            font-weight: 400;
            display: block;
            font-size: 0.7rem;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-top: 1px;
        }
        .sidebar-nav {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        .nav-label {
            font-size: 0.65rem;
            text-transform: uppercase;
            letter-spacing: 1.2px;
            color: rgba(255, 255, 255, 0.25);
            padding: 0.75rem 0.75rem 0.4rem;
            font-weight: 600;
        }
        .sidebar-nav a {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.6rem 0.75rem;
            border-radius: var(--radius-sm);
            font-size: 0.875rem;
            font-weight: 500;
            color: rgba(255, 255, 255, 0.55);
            transition: all var(--transition);
            position: relative;
        }
        .sidebar-nav a i {
            width: 20px;
            font-size: 1rem;
            text-align: center;
            flex-shrink: 0;
        }
        .sidebar-nav a:hover {
            background: rgba(255, 255, 255, 0.06);
            color: #fff;
        }
        .sidebar-nav a.active {
            background: rgba(201, 168, 76, 0.15);
            color: var(--gold);
        }
        .sidebar-nav a.active::before {
            content: '';
            position: absolute;
            left: 0;
            top: 30%;
            height: 40%;
            width: 3px;
            background: var(--gold);
            border-radius: 0 4px 4px 0;
        }
        .sidebar-nav a .badge {
            margin-left: auto;
            background: var(--gold);
            color: #0d1b2a;
            font-size: 0.65rem;
            font-weight: 700;
            padding: 0.1rem 0.6rem;
            border-radius: 20px;
        }
        .sidebar-footer {
            margin-top: auto;
            padding-top: 1rem;
            border-top: 1px solid rgba(255, 255, 255, 0.06);
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .avatar {
            width: 38px;
            height: 38px;
            border-radius: 50%;
            background: var(--gold);
            color: #0d1b2a;
            font-weight: 700;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        .avatar-sm {
            width: 34px;
            height: 34px;
            border-radius: 50%;
            background: var(--gold);
            color: #0d1b2a;
            font-weight: 700;
            font-size: 0.75rem;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        .user-info .name {
            color: #fff;
            font-weight: 600;
            font-size: 0.85rem;
        }
        .user-info .role {
            font-size: 0.7rem;
            color: rgba(255, 255, 255, 0.4);
        }

        /* ── MAIN ── */
        .main {
            flex: 1;
            min-width: 0;
            padding: 0 1.75rem 2rem;
            max-width: calc(100vw - var(--sidebar-width));
        }

        /* ── TOPBAR ── */
        .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem 0 1.25rem;
            border-bottom: 1px solid var(--border);
            flex-wrap: wrap;
            gap: 0.75rem;
            position: sticky;
            top: 0;
            background: var(--bg);
            z-index: 50;
        }
        .topbar-left {
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        .menu-toggle {
            display: none;
            font-size: 1.25rem;
            color: var(--text);
            padding: 0.25rem 0.5rem;
            border-radius: 8px;
            transition: background var(--transition);
        }
        .menu-toggle:hover {
            background: var(--slate-light);
        }
        .topbar-left h2 {
            font-size: 1.3rem;
            font-weight: 600;
            letter-spacing: -0.3px;
        }
        .topbar-left h2 span {
            color: var(--gold);
        }
        .topbar-right {
            display: flex;
            align-items: center;
            gap: 1.25rem;
            flex-wrap: wrap;
        }
        .search-wrapper {
            display: flex;
            align-items: center;
            background: #fff;
            border: 1px solid var(--border);
            border-radius: 100px;
            padding: 0.3rem 1rem 0.3rem 1.25rem;
            gap: 0.6rem;
            transition: box-shadow var(--transition), border-color var(--transition);
            min-width: 220px;
        }
        .search-wrapper:focus-within {
            border-color: var(--gold);
            box-shadow: 0 0 0 3px rgba(201, 168, 76, 0.12);
        }
        .search-wrapper i {
            color: var(--slate);
            font-size: 0.9rem;
        }
        .search-wrapper input {
            border: none;
            outline: none;
            padding: 0.5rem 0;
            font-size: 0.85rem;
            width: 100%;
            min-width: 120px;
            background: transparent;
            color: var(--text);
        }
        .search-wrapper input::placeholder {
            color: var(--text-muted);
        }
        .topbar-actions {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .topbar-actions button {
            width: 38px;
            height: 38px;
            border-radius: 50%;
            background: #fff;
            border: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-muted);
            font-size: 0.95rem;
            transition: all var(--transition);
            position: relative;
        }
        .topbar-actions button:hover {
            border-color: var(--gold);
            color: var(--gold);
        }
        .notif-dot {
            position: absolute;
            top: 8px;
            right: 8px;
            width: 7px;
            height: 7px;
            background: #e74c3c;
            border-radius: 50%;
            border: 2px solid #fff;
        }

        /* ── STATS ── */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin: 1.5rem 0 1.25rem;
        }
        .stat-card {
            background: var(--card-bg);
            border-radius: var(--radius);
            padding: 1.25rem 1.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
            transition: all var(--transition);
        }
        .stat-card:hover {
            box-shadow: var(--shadow-hover);
            transform: translateY(-2px);
        }
        .stat-left h3 {
            font-size: 1.6rem;
            font-weight: 700;
            letter-spacing: -0.5px;
            line-height: 1.2;
        }
        .stat-left p {
            font-size: 0.8rem;
            color: var(--text-muted);
            font-weight: 500;
            margin-top: 2px;
        }
        .stat-icon {
            width: 44px;
            height: 44px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            flex-shrink: 0;
        }
        .stat-icon.gold {
            background: rgba(201, 168, 76, 0.15);
            color: var(--gold);
        }
        .stat-icon.blue {
            background: rgba(52, 152, 219, 0.15);
            color: #3498db;
        }
        .stat-icon.purple {
            background: rgba(155, 89, 182, 0.15);
            color: #9b59b6;
        }
        .stat-icon.green {
            background: rgba(46, 204, 113, 0.15);
            color: #2ecc71;
        }

        /* ── FILTER BAR ── */
        .filter-bar {
            display: flex;
            flex-wrap: wrap;
            gap: 1rem 1.5rem;
            background: var(--card-bg);
            padding: 1rem 1.5rem;
            border-radius: var(--radius);
            border: 1px solid var(--border);
            margin-bottom: 1.75rem;
            align-items: flex-end;
            box-shadow: var(--shadow);
        }
        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
            flex: 1 0 120px;
            min-width: 110px;
        }
        .filter-group label {
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
        }
        .filter-group select {
            padding: 0.5rem 0.75rem;
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            background: var(--bg);
            font-size: 0.85rem;
            color: var(--text);
            font-weight: 500;
            transition: border-color var(--transition);
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%236b7a8d' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 0.75rem center;
            cursor: pointer;
        }
        .filter-group select:focus {
            outline: none;
            border-color: var(--gold);
        }
        .filter-actions {
            display: flex;
            gap: 0.6rem;
            margin-left: auto;
            align-items: center;
        }
        .btn-reset,
        .btn-apply {
            padding: 0.5rem 1.2rem;
            border-radius: var(--radius-sm);
            font-weight: 600;
            font-size: 0.8rem;
            transition: all var(--transition);
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }
        .btn-reset {
            background: var(--slate-light);
            color: var(--text-muted);
        }
        .btn-reset:hover {
            background: #dce2ea;
        }
        .btn-apply {
            background: var(--gold);
            color: #fff;
        }
        .btn-apply:hover {
            background: var(--gold-dark);
            transform: translateY(-1px);
        }

        /* ── SECTION HEADER ── */
        .section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.25rem;
            flex-wrap: wrap;
            gap: 0.5rem;
        }
        .section-header h2 {
            font-size: 1.2rem;
            font-weight: 600;
            letter-spacing: -0.3px;
        }
        .section-header h2 span {
            color: var(--gold);
        }
        .view-toggles {
            display: flex;
            gap: 4px;
            background: var(--slate-light);
            border-radius: var(--radius-sm);
            padding: 4px;
        }
        .view-toggles button {
            padding: 0.35rem 0.9rem;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-muted);
            transition: all var(--transition);
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }
        .view-toggles button i {
            font-size: 0.85rem;
        }
        .view-toggles button.active {
            background: #fff;
            color: var(--text);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        }
        .view-toggles button:hover:not(.active) {
            color: var(--text);
        }

        /* ── PROPERTY GRID ── */
        .property-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        .property-card {
            background: var(--card-bg);
            border-radius: var(--radius);
            overflow: hidden;
            border: 1px solid var(--border);
            box-shadow: var(--shadow);
            transition: all var(--transition);
        }
        .property-card:hover {
            box-shadow: var(--shadow-hover);
            transform: translateY(-4px);
        }
        .card-image {
            position: relative;
            aspect-ratio: 16/10;
            overflow: hidden;
            background: var(--slate-light);
        }
        .card-image img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.4s ease;
        }
        .property-card:hover .card-image img {
            transform: scale(1.03);
        }
        .card-image .badge {
            position: absolute;
            top: 12px;
            left: 12px;
            padding: 0.2rem 0.9rem;
            border-radius: 100px;
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            background: #e74c3c;
            color: #fff;
        }
        .card-image .badge.vacant {
            background: #e67e22;
        }
        .favorite {
            position: absolute;
            top: 12px;
            right: 12px;
            width: 34px;
            height: 34px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(4px);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.95rem;
            color: var(--text-muted);
            transition: all var(--transition);
            border: none;
        }
        .favorite:hover {
            transform: scale(1.1);
        }
        .favorite.active {
            color: #e74c3c;
        }
        .favorite.active i {
            font-weight: 900;
        }
        .image-count {
            position: absolute;
            bottom: 12px;
            right: 12px;
            padding: 0.15rem 0.7rem;
            border-radius: 100px;
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(4px);
            color: #fff;
            font-size: 0.7rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.3rem;
        }
        .card-body {
            padding: 1rem 1.25rem 1.25rem;
        }
        .card-body .price {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--gold-dark);
        }
        .card-body .address {
            font-weight: 600;
            font-size: 1rem;
            margin-top: 2px;
        }
        .card-body .location {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin: 4px 0 10px;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .card-body .location i {
            font-size: 0.75rem;
        }
        .features {
            display: flex;
            gap: 0.75rem;
            flex-wrap: wrap;
            margin-bottom: 1rem;
            padding: 0.5rem 0;
            border-top: 1px solid var(--border);
            border-bottom: 1px solid var(--border);
        }
        .features span {
            font-size: 0.75rem;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .features span i {
            color: var(--gold);
            width: 14px;
        }
        .actions {
            display: flex;
            gap: 0.5rem;
        }
        .actions button {
            padding: 0.4rem 1rem;
            border-radius: var(--radius-sm);
            font-size: 0.8rem;
            font-weight: 600;
            transition: all var(--transition);
            display: flex;
            align-items: center;
            gap: 0.4rem;
            flex: 1;
            justify-content: center;
        }
        .btn-details {
            background: var(--slate-light);
            color: var(--text);
        }
        .btn-details:hover {
            background: #dce2ea;
        }
        .btn-tour {
            background: var(--gold);
            color: #fff;
        }
        .btn-tour:hover {
            background: var(--gold-dark);
        }

        /* ── MAP CONTAINER ── */
        .map-container {
            display: none;
            background: var(--card-bg);
            border-radius: var(--radius);
            border: 1px solid var(--border);
            min-height: 420px;
            margin-bottom: 2rem;
            box-shadow: var(--shadow);
            overflow: hidden;
        }
        .map-container.active {
            display: block;
        }
        .map-placeholder {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 420px;
            background: linear-gradient(135deg, #f0f4f9 0%, #e4eaf2 100%);
            color: var(--text-muted);
        }
        .map-placeholder i {
            font-size: 3rem;
            color: var(--gold);
            opacity: 0.4;
            margin-bottom: 0.75rem;
        }
        .map-placeholder p {
            font-weight: 600;
            font-size: 1.1rem;
        }

        /* ── ACTIVITY SECTION ── */
        .activity-section {
            margin-top: 0.5rem;
        }
        .activity-list {
            background: var(--card-bg);
            border-radius: var(--radius);
            border: 1px solid var(--border);
            box-shadow: var(--shadow);
            overflow: hidden;
        }
        .activity-item {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 0.9rem 1.25rem;
            border-bottom: 1px solid var(--border);
            transition: background var(--transition);
        }
        .activity-item:last-child {
            border-bottom: none;
        }
        .activity-item:hover {
            background: var(--slate-light);
        }
        .a-icon {
            width: 40px;
            height: 40px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            flex-shrink: 0;
            font-size: 0.95rem;
        }
        .a-icon.gold-bg {
            background: var(--gold);
        }
        .a-icon.blue-bg {
            background: #3498db;
        }
        .a-icon.green-bg {
            background: #2ecc71;
        }
        .a-content {
            flex: 1;
            min-width: 0;
        }
        .a-content h4 {
            font-size: 0.9rem;
            font-weight: 600;
        }
        .a-content p {
            font-size: 0.8rem;
            color: var(--text-muted);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .a-time {
            font-size: 0.7rem;
            color: var(--text-muted);
            white-space: nowrap;
            font-weight: 500;
        }

        /* ── FOOTER ── */
        .footer {
            margin-top: 2.5rem;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.5rem;
            font-size: 0.8rem;
            color: var(--text-muted);
        }
        .footer span {
            font-weight: 700;
            color: var(--text);
        }
        .footer p span {
            color: var(--gold);
            font-weight: 600;
        }

        /* ── BACK TO TOP ── */
        .back-top {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: var(--gold);
            color: #fff;
            font-size: 1.2rem;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 16px rgba(201, 168, 76, 0.35);
            opacity: 0;
            transform: scale(0.8);
            pointer-events: none;
            transition: all var(--transition);
            z-index: 200;
            border: none;
        }
        .back-top.active {
            opacity: 1;
            transform: scale(1);
            pointer-events: auto;
        }
        .back-top:hover {
            background: var(--gold-dark);
            transform: scale(1.06);
        }

        /* ── MODALS ── */
        .modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(6px);
            z-index: 300;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
            padding: 1.5rem;
        }
        .modal-overlay.active {
            opacity: 1;
            pointer-events: auto;
        }
        .modal {
            background: var(--card-bg);
            border-radius: var(--radius);
            max-width: 720px;
            width: 100%;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 32px 80px rgba(0, 0, 0, 0.3);
            transform: translateY(20px) scale(0.96);
            transition: transform 0.3s ease;
        }
        .modal-overlay.active .modal {
            transform: translateY(0) scale(1);
        }
        .modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid var(--border);
        }
        .modal-header h2 {
            font-size: 1.2rem;
            font-weight: 600;
        }
        .close-modal {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-muted);
            transition: all var(--transition);
            font-size: 1.1rem;
        }
        .close-modal:hover {
            background: var(--slate-light);
            color: var(--text);
        }
        .modal-body {
            padding: 1.5rem;
        }
        .detail-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }
        .detail-img img {
            width: 100%;
            height: auto;
            border-radius: var(--radius-sm);
            object-fit: cover;
            aspect-ratio: 4/3;
        }
        .detail-price {
            font-size: 1.6rem;
            font-weight: 700;
            color: var(--gold-dark);
        }
        .detail-address {
            font-weight: 600;
            font-size: 1.1rem;
            margin: 2px 0 4px;
        }
        .detail-location {
            font-size: 0.85rem;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .detail-features {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.4rem 1rem;
            margin: 0.75rem 0;
            padding: 0.75rem 0;
            border-top: 1px solid var(--border);
            border-bottom: 1px solid var(--border);
        }
        .detail-features div {
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 6px;
            color: var(--text-muted);
        }
        .detail-features div i {
            color: var(--gold);
            width: 16px;
        }
        .detail-desc {
            font-size: 0.9rem;
            color: var(--text-muted);
            line-height: 1.6;
            margin-bottom: 1rem;
        }
        .detail-actions {
            display: flex;
            gap: 0.75rem;
            flex-wrap: wrap;
        }
        .detail-actions button {
            padding: 0.6rem 1.5rem;
            border-radius: var(--radius-sm);
            font-weight: 600;
            font-size: 0.85rem;
            transition: all var(--transition);
            display: flex;
            align-items: center;
            gap: 0.5rem;
            flex: 1;
            justify-content: center;
        }
        .btn-outline {
            border: 2px solid var(--gold);
            color: var(--gold);
            background: transparent;
        }
        .btn-outline:hover {
            background: var(--gold);
            color: #fff;
        }
        .btn-primary {
            background: var(--gold);
            color: #fff;
        }
        .btn-primary:hover {
            background: var(--gold-dark);
        }

        /* ── SCHEDULE FORM ── */
        .schedule-form {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
        }
        .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }
        .form-group.full {
            grid-column: 1 / -1;
        }
        .form-group label {
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-muted);
        }
        .form-group input,
        .form-group select,
        .form-group textarea {
            padding: 0.6rem 0.9rem;
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            font-size: 0.9rem;
            font-family: inherit;
            color: var(--text);
            background: #fff;
            transition: border-color var(--transition);
            width: 100%;
        }
        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {
            outline: none;
            border-color: var(--gold);
            box-shadow: 0 0 0 3px rgba(201, 168, 76, 0.10);
        }
        .form-group textarea {
            resize: vertical;
            min-height: 80px;
        }
        .form-group input[readonly] {
            background: var(--slate-light);
            color: var(--text);
            font-weight: 500;
        }
        .submit-btn {
            grid-column: 1 / -1;
            padding: 0.75rem;
            border-radius: var(--radius-sm);
            background: var(--gold);
            color: #fff;
            font-weight: 700;
            font-size: 1rem;
            transition: all var(--transition);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            border: none;
        }
        .submit-btn:hover {
            background: var(--gold-dark);
            transform: translateY(-2px);
        }

        /* ── RESPONSIVE ── */
        @media (max-width: 992px) {
            .sidebar {
                transform: translateX(-100%);
                position: fixed;
                width: 280px;
                height: 100vh;
                border-radius: 0;
                box-shadow: 0 0 40px rgba(0, 0, 0, 0.2);
                padding-top: 1rem;
            }
            .sidebar.open {
                transform: translateX(0);
            }
            .menu-toggle {
                display: flex;
            }
            .main {
                max-width: 100%;
                padding: 0 1rem 1.5rem;
            }
            .detail-grid {
                grid-template-columns: 1fr;
            }
            .schedule-form {
                grid-template-columns: 1fr;
            }
            .topbar-right .search-wrapper {
                min-width: 160px;
            }
            .filter-bar {
                flex-direction: column;
                align-items: stretch;
            }
            .filter-actions {
                margin-left: 0;
                justify-content: flex-end;
            }
            .stats-grid {
                grid-template-columns: 1fr 1fr;
            }
        }
        @media (max-width: 600px) {
            .stats-grid {
                grid-template-columns: 1fr;
            }
            .property-grid {
                grid-template-columns: 1fr;
            }
            .topbar {
                flex-direction: column;
                align-items: stretch;
            }
            .topbar-right {
                flex-wrap: wrap;
            }
            .topbar-right .search-wrapper {
                flex: 1;
                min-width: 120px;
            }
            .modal {
                margin: 1rem;
                max-height: 95vh;
            }
            .modal-body {
                padding: 1rem;
            }
            .detail-actions {
                flex-direction: column;
            }
            .footer {
                flex-direction: column;
                text-align: center;
            }
            .view-toggles button span {
                display: none;
            }
        }
    </style>
</head>
<body>
    <div class="app">

        <!-- ─── SIDEBAR ─── -->
        <aside class="sidebar" id="sidebar">
            <div class="sidebar-brand">
                <div class="brand-icon"><i class="fas fa-crown"></i></div>
                <h1>Mwarokin<span>Estates</span></h1>
            </div>

            <nav class="sidebar-nav">
                <div class="nav-label">Main</div>
                <a href="#" class="active"><i class="fas fa-th-large"></i> Dashboard</a>
                <a href="#"><i class="fas fa-home"></i> Properties <span class="badge">{{ stats.vacant_homes }}</span></a>
                <a href="#"><i class="fas fa-calendar-check"></i> Viewings</a>
                <a href="#"><i class="fas fa-file-contract"></i> Leases</a>

                <div class="nav-label" style="margin-top:0.75rem;">Management</div>
                <a href="#"><i class="fas fa-users"></i> Tenants</a>
                <a href="#"><i class="fas fa-user-tie"></i> Agents</a>
                <a href="#"><i class="fas fa-wallet"></i> Payments</a>
                <a href="#"><i class="fas fa-chart-line"></i> Analytics</a>

                <div class="nav-label" style="margin-top:0.75rem;">Settings</div>
                <a href="#"><i class="fas fa-user"></i> My Profile</a>
                <a href="#"><i class="fas fa-globe"></i> Language</a>
                <a href="#"><i class="fas fa-sign-out-alt"></i> Logout</a>
            </nav>

            <div class="sidebar-footer">
                <div class="avatar">JD</div>
                <div class="user-info">
                    <div class="name">{{ user_name }}</div>
                    <div class="role">{{ user_role }}</div>
                </div>
                <i class="fas fa-ellipsis-v" style="color: rgba(255,255,255,0.25); cursor:pointer;"></i>
            </div>
        </aside>

        <!-- ─── MAIN ─── -->
        <main class="main">

            <!-- Top Bar -->
            <header class="topbar">
                <div class="topbar-left">
                    <button class="menu-toggle" id="menuToggle" aria-label="Toggle menu">
                        <i class="fas fa-bars"></i>
                    </button>
                    <h2>Vacant <span>Homes</span></h2>
                </div>
                <div class="topbar-right">
                    <div class="search-wrapper">
                        <i class="fas fa-search"></i>
                        <input type="text" placeholder="Search properties, locations..." id="searchInput" />
                    </div>
                    <div class="topbar-actions">
                        <button aria-label="Notifications">
                            <i class="fas fa-bell"></i>
                            <span class="notif-dot"></span>
                        </button>
                        <button aria-label="Messages">
                            <i class="fas fa-envelope"></i>
                        </button>
                        <div class="avatar-sm">JD</div>
                    </div>
                </div>
            </header>

            <!-- Stats -->
            <section class="stats-grid">
                <div class="stat-card">
                    <div class="stat-left">
                        <h3>{{ stats.total_properties }}</h3>
                        <p>Total Properties</p>
                    </div>
                    <div class="stat-icon gold"><i class="fas fa-building"></i></div>
                </div>
                <div class="stat-card">
                    <div class="stat-left">
                        <h3>{{ stats.vacant_homes }}</h3>
                        <p>Vacant Homes</p>
                    </div>
                    <div class="stat-icon blue"><i class="fas fa-door-open"></i></div>
                </div>
                <div class="stat-card">
                    <div class="stat-left">
                        <h3>{{ stats.active_agents }}</h3>
                        <p>Active Agents</p>
                    </div>
                    <div class="stat-icon purple"><i class="fas fa-user-tie"></i></div>
                </div>
                <div class="stat-card">
                    <div class="stat-left">
                        <h3>{{ stats.monthly_revenue }}</h3>
                        <p>Monthly Revenue</p>
                    </div>
                    <div class="stat-icon green"><i class="fas fa-arrow-up"></i></div>
                </div>
            </section>

            <!-- Filter Bar -->
            <div class="filter-bar">
                <div class="filter-group">
                    <label>Type</label>
                    <select id="filterType">
                        <option value="all">All Types</option>
                        <option value="apartment">Apartment</option>
                        <option value="house">House</option>
                        <option value="condo">Condo</option>
                        <option value="villa">Villa</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Price</label>
                    <select id="filterPrice">
                        <option value="any">Any Price</option>
                        <option value="0-1000">$0 – $1,000</option>
                        <option value="1000-2000">$1,000 – $2,000</option>
                        <option value="2000-3000">$2,000 – $3,000</option>
                        <option value="3000+">$3,000+</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Beds</label>
                    <select id="filterBeds">
                        <option value="any">Any</option>
                        <option value="1">1</option>
                        <option value="2">2</option>
                        <option value="3">3</option>
                        <option value="4">4+</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Location</label>
                    <select id="filterLocation">
                        <option value="all">All Areas</option>
                        <option value="Downtown">Downtown</option>
                        <option value="Westlands">Westlands</option>
                        <option value="Kilimani">Kilimani</option>
                        <option value="Riverside">Riverside</option>
                        <option value="Lavington">Lavington</option>
                    </select>
                </div>
                <div class="filter-actions">
                    <button class="btn-reset" id="resetFilters"><i class="fas fa-undo-alt"></i> Reset</button>
                    <button class="btn-apply" id="applyFilters"><i class="fas fa-sliders-h"></i> Apply</button>
                </div>
            </div>

            <!-- Section Header -->
            <div class="section-header">
                <h2>Available <span>Vacant Homes</span></h2>
                <div class="view-toggles">
                    <button class="active" data-view="grid"><i class="fas fa-th"></i> <span>Grid</span></button>
                    <button data-view="map"><i class="fas fa-map"></i> <span>Map</span></button>
                </div>
            </div>

            <!-- Property Grid -->
            <div class="property-grid" id="propertyGrid">
                {% for prop in properties %}
                <div class="property-card" data-id="{{ prop.id }}">
                    <div class="card-image">
                        <img src="{{ prop.images[0] if prop.images else 'https://images.unsplash.com/photo-1568605114967-8130f3a36994?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80' }}"
                        alt="{{ prop.title }}" loading="lazy" />
                        <span class="badge vacant">Vacant</span>
                        <button class="favorite {% if prop.is_favorite %}active{% endif %}" aria-label="Favorite" data-id="{{ prop.id }}">
                            <i class="{% if prop.is_favorite %}fas{% else %}far{% endif %} fa-heart"></i>
                        </button>
                        <div class="image-count"><i class="fas fa-camera"></i> {{ prop.image_count or 0 }}</div>
                    </div>
                    <div class="card-body">
                        <div class="price">{{ prop.price_display }}</div>
                        <div class="address">{{ prop.address.street }}</div>
                        <div class="location"><i class="fas fa-map-marker-alt"></i> {{ prop.location_display }}</div>
                        <div class="features">
                            <span><i class="fas fa-bed"></i> {{ prop.features.bedrooms }} Beds</span>
                            <span><i class="fas fa-bath"></i> {{ prop.features.bathrooms }} Baths</span>
                            <span><i class="fas fa-ruler-combined"></i> {{ prop.features.area_sqft|format_price or prop.features.area_sqft }} sqft</span>
                        </div>
                        <div class="actions">
                            <button class="btn-details" data-id="{{ prop.id }}"><i class="fas fa-eye"></i> Details</button>
                            <button class="btn-tour" data-id="{{ prop.id }}"><i class="fas fa-calendar-alt"></i> Tour</button>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>

            <!-- Map Container -->
            <div class="map-container" id="mapContainer">
                <div class="map-placeholder">
                    <i class="fas fa-map-marked-alt"></i>
                    <p>Interactive Map View</p>
                    <span style="font-size:0.85rem; opacity:0.6;">Vacant properties displayed on map</span>
                </div>
            </div>

            <!-- Recent Activity -->
            <section class="activity-section">
                <div class="section-header">
                    <h2>Recent <span>Activity</span></h2>
                    <span style="color:var(--slate);font-size:0.85rem;">Last 24 hours</span>
                </div>
                <div class="activity-list">
                    {% for activity in recent_activity %}
                    <div class="activity-item">
                        <div class="a-icon {{ activity.icon_class }}"><i class="fas fa-{{ activity.icon }}"></i></div>
                        <div class="a-content">
                            <h4>{{ activity.title }}</h4>
                            <p>{{ activity.description }}</p>
                        </div>
                        <div class="a-time">{{ activity.time }}</div>
                    </div>
                    {% endfor %}
                </div>
            </section>

            <!-- Footer -->
            <footer class="footer">
                <span>Mwarokin Estates</span>
                <p>&copy; 2026 · All Rights Reserved. Powered by <span>Syllogism Technology Africa</span></p>
            </footer>

        </main>
    </div>

    <!-- ─── BACK TO TOP ─── -->
    <button class="back-top" id="backTop" aria-label="Back to top">
        <i class="fas fa-chevron-up"></i>
    </button>

    <!-- ─── DETAIL MODAL ─── -->
    <div class="modal-overlay" id="detailModal">
        <div class="modal">
            <div class="modal-header">
                <h2>Property Details</h2>
                <button class="close-modal" id="closeDetail"><i class="fas fa-times"></i></button>
            </div>
            <div class="modal-body">
                <div class="detail-grid">
                    <div class="detail-img">
                        <img id="detailImg" src="" alt="Property" />
                    </div>
                    <div class="detail-info">
                        <div class="detail-price" id="detailPrice">$2,500 / mo</div>
                        <div class="detail-address" id="detailAddress">123 Main Street</div>
                        <div class="detail-location"><i class="fas fa-map-marker-alt"></i> <span id="detailLocation">Downtown, Nairobi</span></div>
                        <div class="detail-features">
                            <div><i class="fas fa-bed"></i> <span id="detailBeds">3</span> Bedrooms</div>
                            <div><i class="fas fa-bath"></i> <span id="detailBaths">2</span> Bathrooms</div>
                            <div><i class="fas fa-ruler-combined"></i> <span id="detailArea">1,850</span> sqft</div>
                            <div><i class="fas fa-car"></i> <span id="detailParking">1</span> Parking</div>
                        </div>
                        <div class="detail-desc" id="detailDesc">
                            This stunning modern apartment offers breathtaking city views and luxurious amenities.
                        </div>
                        <div class="detail-actions">
                            <button class="btn-outline" id="detailTourBtn"><i class="fas fa-calendar-alt"></i> Schedule Tour</button>
                            <button class="btn-primary"><i class="fas fa-phone"></i> Contact Agent</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- ─── SCHEDULE MODAL ─── -->
    <div class="modal-overlay" id="scheduleModal">
        <div class="modal">
            <div class="modal-header">
                <h2>Schedule a Tour</h2>
                <button class="close-modal" id="closeSchedule"><i class="fas fa-times"></i></button>
            </div>
            <div class="modal-body">
                <form class="schedule-form" id="scheduleForm">
                    <div class="form-group full">
                        <label>Property</label>
                        <input type="text" id="scheduleProperty" readonly value="123 Main Street" />
                    </div>
                    <div class="form-group">
                        <label>Full Name</label>
                        <input type="text" placeholder="John Doe" required />
                    </div>
                    <div class="form-group">
                        <label>Email</label>
                        <input type="email" placeholder="john@example.com" required />
                    </div>
                    <div class="form-group">
                        <label>Phone</label>
                        <input type="tel" placeholder="+254 700 123 456" required />
                    </div>
                    <div class="form-group">
                        <label>Preferred Date</label>
                        <input type="date" required />
                    </div>
                    <div class="form-group">
                        <label>Preferred Time</label>
                        <select>
                            <option>9:00 AM</option>
                            <option>10:00 AM</option>
                            <option>11:00 AM</option>
                            <option selected>12:00 PM</option>
                            <option>1:00 PM</option>
                            <option>2:00 PM</option>
                            <option>3:00 PM</option>
                            <option>4:00 PM</option>
                        </select>
                    </div>
                    <div class="form-group full">
                        <label>Additional Notes</label>
                        <textarea placeholder="Any special requests or questions..."></textarea>
                    </div>
                    <div class="form-group full">
                        <button type="submit" class="submit-btn"><i class="fas fa-paper-plane"></i> Submit Request</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <!-- ─── JAVASCRIPT ─── -->
    <script>
        document.addEventListener('DOMContentLoaded', () => {

            // ── Data ──
            const propertyData = {
                {% for prop in properties %}
                {{ prop.id }}: {
                    img: "{{ prop.images[0] if prop.images else '' }}",
                    price: "{{ prop.price_display }}",
                    address: "{{ prop.address.street }}",
                    location: "{{ prop.location_display }}",
                    beds: "{{ prop.features.bedrooms }}",
                    baths: "{{ prop.features.bathrooms }}",
                    area: "{{ prop.features.area_sqft }}",
                    parking: "{{ prop.features.parking_spots }}",
                    desc: "{{ prop.description|escape }}"
                },
                {% endfor %}
            };

            // ── DOM refs ──
            const sidebar = document.getElementById('sidebar');
            const menuToggle = document.getElementById('menuToggle');
            const viewBtns = document.querySelectorAll('.view-toggles button');
            const grid = document.getElementById('propertyGrid');
            const mapContainer = document.getElementById('mapContainer');
            const backTop = document.getElementById('backTop');
            const detailModal = document.getElementById('detailModal');
            const scheduleModal = document.getElementById('scheduleModal');
            const closeDetail = document.getElementById('closeDetail');
            const closeSchedule = document.getElementById('closeSchedule');
            const detailImg = document.getElementById('detailImg');
            const detailPrice = document.getElementById('detailPrice');
            const detailAddress = document.getElementById('detailAddress');
            const detailLocation = document.getElementById('detailLocation');
            const detailBeds = document.getElementById('detailBeds');
            const detailBaths = document.getElementById('detailBaths');
            const detailArea = document.getElementById('detailArea');
            const detailParking = document.getElementById('detailParking');
            const detailDesc = document.getElementById('detailDesc');
            const detailTourBtn = document.getElementById('detailTourBtn');
            const scheduleProperty = document.getElementById('scheduleProperty');

            let currentPropertyId = null;

            // ── Sidebar toggle ──
            menuToggle.addEventListener('click', () => {
                sidebar.classList.toggle('open');
            });
            document.addEventListener('click', (e) => {
                if (window.innerWidth <= 992) {
                    if (!sidebar.contains(e.target) && e.target !== menuToggle && !menuToggle.contains(e.target)) {
                        sidebar.classList.remove('open');
                    }
                }
            });

            // ── View toggle ──
            viewBtns.forEach(btn => {
                btn.addEventListener('click', () => {
                    viewBtns.forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    const view = btn.dataset.view;
                    if (view === 'grid') {
                        grid.style.display = 'grid';
                        mapContainer.classList.remove('active');
                    } else {
                        grid.style.display = 'none';
                        mapContainer.classList.add('active');
                    }
                });
            });

            // ── Favorite toggle ──
            document.querySelectorAll('.favorite').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    btn.classList.toggle('active');
                    const icon = btn.querySelector('i');
                    if (btn.classList.contains('active')) {
                        icon.className = 'fas fa-heart';
                        // Optionally send to API
                        const id = btn.dataset.id;
                        fetch(`/api/properties/${id}/favorite`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' }
                            })
                            .then(r => r.json())
                            .catch(() => {});
                    } else {
                        icon.className = 'far fa-heart';
                    }
                });
            });

            // ── Open Detail Modal ──
            function openDetail(id) {
                const data = propertyData[id];
                if (!data) return;
                currentPropertyId = id;
                detailImg.src = data.img;
                detailPrice.textContent = data.price;
                detailAddress.textContent = data.address;
                detailLocation.textContent = data.location;
                detailBeds.textContent = data.beds;
                detailBaths.textContent = data.baths;
                detailArea.textContent = data.area;
                detailParking.textContent = data.parking;
                detailDesc.textContent = data.desc;
                detailTourBtn.dataset.id = id;
                detailModal.classList.add('active');
                document.body.style.overflow = 'hidden';
            }

            document.querySelectorAll('.btn-details').forEach(btn => {
                btn.addEventListener('click', () => {
                    const id = btn.dataset.id;
                    openDetail(id);
                });
            });

            // ── Open Schedule from detail ──
            detailTourBtn.addEventListener('click', () => {
                const id = detailTourBtn.dataset.id;
                const data = propertyData[id];
                if (data) {
                    scheduleProperty.value = data.address;
                }
                detailModal.classList.remove('active');
                scheduleModal.classList.add('active');
            });

            // ── Open Schedule from card ──
            document.querySelectorAll('.btn-tour').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const id = btn.dataset.id;
                    const data = propertyData[id];
                    if (data) {
                        scheduleProperty.value = data.address;
                    }
                    scheduleModal.classList.add('active');
                    document.body.style.overflow = 'hidden';
                });
            });

            // ── Close modals ──
            function closeAllModals() {
                detailModal.classList.remove('active');
                scheduleModal.classList.remove('active');
                document.body.style.overflow = '';
            }

            closeDetail.addEventListener('click', closeAllModals);
            closeSchedule.addEventListener('click', closeAllModals);

            [detailModal, scheduleModal].forEach(modal => {
                modal.addEventListener('click', (e) => {
                    if (e.target === modal) closeAllModals();
                });
            });

            // ── Schedule form submit ──
            document.getElementById('scheduleForm').addEventListener('submit', (e) => {
                e.preventDefault();
                alert('✅ Tour request submitted! We\'ll contact you shortly.');
                closeAllModals();
            });

            // ── Back to top ──
            window.addEventListener('scroll', () => {
                if (window.scrollY > 350) {
                    backTop.classList.add('active');
                } else {
                    backTop.classList.remove('active');
                }
            });
            backTop.addEventListener('click', () => {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });

            // ── Filter apply ──
            document.getElementById('applyFilters').addEventListener('click', () => {
                const cards = document.querySelectorAll('.property-card');
                cards.forEach((card, i) => {
                    card.style.transition = 'all 0.4s ease';
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.96) translateY(20px)';
                    setTimeout(() => {
                        card.style.opacity = '1';
                        card.style.transform = 'scale(1) translateY(0)';
                    }, 50 + i * 80);
                });
            });

            // ── Reset filters ──
            document.getElementById('resetFilters').addEventListener('click', () => {
                document.querySelectorAll('.filter-bar select').forEach(el => el.selectedIndex = 0);
                document.querySelectorAll('.property-card').forEach(card => {
                    card.style.opacity = '1';
                    card.style.transform = 'scale(1) translateY(0)';
                });
            });

            // ── Keyboard shortcuts ──
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') closeAllModals();
            });

            // ── Search input (filter by address/location) ──
            document.getElementById('searchInput').addEventListener('input', function() {
                const query = this.value.toLowerCase().trim();
                document.querySelectorAll('.property-card').forEach(card => {
                    const address = card.querySelector('.address')?.textContent?.toLowerCase() || '';
                    const location = card.querySelector('.location')?.textContent?.toLowerCase() || '';
                    const match = address.includes(query) || location.includes(query);
                    card.style.display = match || query === '' ? '' : 'none';
                });
            });

            console.log('🏡 Mwarokin Estates · Vacant Homes UI loaded.');
        });
    </script>

</body>
</html>
```
### Dashboard Features

This dashboard combines a clean, gold-accented interface with seamless property management tools. Let's walk through its key parts:

- **Sidebar Navigation & User Context:** The fixed sidebar provides quick access to main sections (Properties, Viewings, Tenants) and displays the logged-in user's avatar and role, keeping the workspace organized.
- **Property Grid & Interactive Cards:** Each property card displays an image, price, address, key features (beds, baths, sqft), and action buttons. You can **favorite** a property (heart icon), view **Details** to open a modal with full info, or schedule a **Tour**.
- **Filtering & Search:** The filter bar lets you narrow properties by Type, Price, Beds, and Location. The **search input** in the top bar filters cards by address or location in real-time. The **Reset** and **Apply** buttons control the filter state.
- **View Toggle & Map Placeholder:** Switch between **Grid** and **Map** views using the toggle buttons. The map view currently shows a placeholder, ready for integration with a mapping service.
- **Recent Activity Feed:** The bottom section displays a chronological list of recent events (new leases, payments, viewings) with color-coded icons, providing a quick snapshot of system activity.
- **Modals for Detail & Tour Scheduling:** Clicking **Details** opens a modal with full property information, including a description and a "Schedule Tour" button. The **Tour** button opens a separate modal with a form to collect visitor details and preferred date/time.