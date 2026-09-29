Here’s a complete, modern **FastAPI backend** that powers the Mwarokin “Wellness, Wealth & Wild Ventures” (Page 19) UI with real data and actionable endpoints.

```python
"""
Mwarokin Estates – Wellness, Wealth & Wild Ventures (Page 19)
Backend API (FastAPI + Pydantic v2)
Python 3.11+
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Annotated, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mwarokin Estates – Lifestyle API (Page 19)",
    description="Spa, honey, fashion, comedy, aquaponics, Sacco & radio",
    version="1.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Domain data
# ---------------------------------------------------------------------------

SPA_STATS = [
    {"label": "Members", "value": "84", "sub": "Active wellness members"},
    {"label": "Sessions YTD", "value": "1,240", "sub": "Treatments delivered"},
    {"label": "Retreats Hosted", "value": "6", "sub": "Since 2024"},
    {"label": "Avg. Rating", "value": "4.9★", "sub": "Member satisfaction"},
]

SPA_SERVICES = [
    {"id": "deep-tissue", "icon": "fa-hand-sparkles", "type": "massage", "name": "Deep Tissue Massage",
     "desc": "Full-body 60-minute massage to melt away landlord stress and tension.", "price": 4500, "duration": "60 min"},
    {"id": "luxury-facial", "icon": "fa-spa", "type": "facial", "name": "Luxury Facial Treatment",
     "desc": "Rejuvenating facial with natural Kenyan ingredients and hot stone therapy.", "price": 3800, "duration": "45 min"},
    {"id": "aromatherapy", "icon": "fa-leaf", "type": "aroma", "name": "Aromatherapy Session",
     "desc": "Essential oil therapy with lavender, eucalyptus, and frankincense blends.", "price": 3200, "duration": "50 min"},
    {"id": "sauna", "icon": "fa-hot-tub", "type": "sauna", "name": "Sauna & Steam Room",
     "desc": "Unlimited access to sauna, steam room, and cold plunge pool.", "price": 2500, "duration": "90 min"},
    {"id": "couples", "icon": "fa-hands", "type": "massage", "name": "Couples Massage",
     "desc": "Side-by-side massage for two — perfect for landlords and their partners.", "price": 8500, "duration": "75 min"},
    {"id": "medical-facial", "icon": "fa-user-md", "type": "facial", "name": "Medical-Grade Facial",
     "desc": "Advanced skin treatment with dermatologist consultation and LED therapy.", "price": 6800, "duration": "60 min"},
]

HONEY_STATS = [
    {"label": "Active Hives", "value": "24", "sub": "Across 6 properties"},
    {"label": "YTD Harvest", "value": "248 kg", "sub": "Premium raw honey"},
    {"label": "Bee Colonies", "value": "42", "sub": "Estimated colony size"},
    {"label": "Revenue YTD", "value": "KSh 186K", "sub": "From honey sales"},
]

HIVES = [
    {"id": "alpha", "emoji": "🍯", "name": "Hive Alpha", "location": "Kilimani Court · Garden",
     "health": "thriving", "population": "45,000 bees", "last_harvest": "2025-04-08", "yield_kg": 18},
    {"id": "beta", "emoji": "🐝", "name": "Hive Beta", "location": "Westlands Heights · Roof",
     "health": "healthy", "population": "38,000 bees", "last_harvest": "2025-04-05", "yield_kg": 14},
    {"id": "gamma", "emoji": "🍯", "name": "Hive Gamma", "location": "Runda Gardens · East",
     "health": "thriving", "population": "52,000 bees", "last_harvest": "2025-04-02", "yield_kg": 22},
    {"id": "delta", "emoji": "🐝", "name": "Hive Delta", "location": "Lavington Suites · Garden",
     "health": "attention", "population": "28,000 bees", "last_harvest": "2025-03-28", "yield_kg": 8},
    {"id": "epsilon", "emoji": "🍯", "name": "Hive Epsilon", "location": "South B Apartments · Yard",
     "health": "healthy", "population": "34,000 bees", "last_harvest": "2025-04-10", "yield_kg": 12},
    {"id": "zeta", "emoji": "🐝", "name": "Hive Zeta", "location": "Eastleigh Plaza · Rooftop",
     "health": "thriving", "population": "48,000 bees", "last_harvest": "2025-04-12", "yield_kg": 16},
]

FASHION_ITEMS = [
    {"id": "gown-1", "emoji": "👗", "type": "dress", "condition": "Like New", "title": "Designer Evening Gown",
     "seller": "Grace Wanjiku", "initials": "GW", "color": "#c8972a", "price": 8500, "original": 24000},
    {"id": "suit-1", "emoji": "👔", "type": "suit", "condition": "Excellent", "title": "Classic Navy Suit",
     "seller": "John Wachira", "initials": "JW", "color": "#c8972a", "price": 6200, "original": 18000},
    {"id": "shoes-1", "emoji": "👟", "type": "shoes", "condition": "Good", "title": "Nike Air Max Sneakers",
     "seller": "Brian Kamau", "initials": "BK", "color": "#2c6b9e", "price": 4200, "original": 12000},
    {"id": "bag-1", "emoji": "👜", "type": "bag", "condition": "Like New", "title": "Leather Tote Bag",
     "seller": "Amina Hassan", "initials": "AH", "color": "#6b4c9a", "price": 3800, "original": 9500},
    {"id": "necklace-1", "emoji": "💍", "type": "jewelry", "condition": "Vintage", "title": "Gold Statement Necklace",
     "seller": "Lucy Muthoni", "initials": "LM", "color": "#6b4c9a", "price": 5500, "original": 15000},
    {"id": "jacket-1", "emoji": "🧥", "type": "vintage", "condition": "Vintage", "title": "70s Leather Jacket",
     "seller": "Sarah Kilonzo", "initials": "SK", "color": "#b5447a", "price": 7200, "original": 0},
]

COMEDY_STATS = [
    {"label": "Comedians", "value": "24", "sub": "Landlord performers"},
    {"label": "Shows Hosted", "value": "18", "sub": "Since launch"},
    {"label": "Total Audience", "value": "4,840", "sub": "Cumulative attendees"},
    {"label": "Avg. Laughs/Show", "value": "248", "sub": "Per performance"},
]

COMEDIANS = [
    {"id": "gw", "initials": "GW", "name": "Grace Wanjiku", "style": "Property Management Fails", "color": "#c8972a",
     "set": '"My tenant called me at 3 AM because the toilet was making a \'haunted house\' noise. Turns out it was just his cat."', "rating": 4.9},
    {"id": "do", "initials": "DO", "name": "David Ochieng", "style": "Tenant Stories", "color": "#2c6b9e",
     "set": '"I asked my tenant to pay rent via M-Pesa. He sent me KSh 5 with a note that said \'thinking of you\'."', "rating": 4.8},
    {"id": "ah", "initials": "AH", "name": "Amina Hassan", "style": "Diaspora Landlord Life", "color": "#6b4c9a",
     "set": '"Being a diaspora landlord is like having a long-distance relationship. Except instead of love letters, you get plumbing bills."', "rating": 4.9},
    {"id": "bk", "initials": "BK", "name": "Brian Kamau", "style": "Maintenance Woes", "color": "#2c6b9e",
     "set": '"My plumber charges by the hour. The problem is he charges for his travel time, lunch break, and time spent talking to my tenant\'s cat."', "rating": 4.7},
    {"id": "mn", "initials": "MN", "name": "Mary Njoki", "style": "Family Business", "color": "#b5447a",
     "set": '"My husband said we should buy property together. Now when we argue about the estate, I remind him — this was YOUR idea."', "rating": 4.8},
    {"id": "sk", "initials": "SK", "name": "Sarah Kilonzo", "style": "Nairobi Landlord Life", "color": "#b5447a",
     "set": '"In Nairobi, rent is like the weather — everyone complains about it, but nobody does anything about it. Except me. I raise it."', "rating": 4.9},
]

AQUA_SYSTEMS = [
    {"id": "tilapia", "emoji": "🐟", "name": "Tilapia & Lettuce System", "location": "Kilimani Court · Greenhouse",
     "status": "optimal", "fish": "Tilapia", "plants": "Lettuce, basil", "harvest": "280 kg fish/yr", "yield": "840 kg veg/yr"},
    {"id": "catfish", "emoji": "🐠", "name": "Catfish & Kale System", "location": "South B Apartments · Basement",
     "status": "good", "fish": "Catfish", "plants": "Kale, spinach", "harvest": "360 kg fish/yr", "yield": "1,200 kg veg/yr"},
    {"id": "trout", "emoji": "🐟", "name": "Trout & Herb System", "location": "Runda Gardens · Barn",
     "status": "monitoring", "fish": "Rainbow Trout", "plants": "Herbs, microgreens", "harvest": "120 kg fish/yr", "yield": "420 kg veg/yr"},
]

SACCO_STATS = [
    {"label": "Total Members", "value": "84", "sub": "Landlord investors"},
    {"label": "Sacco Assets", "value": "KSh 48.2M", "sub": "Under management"},
    {"label": "Member Deposits", "value": "KSh 38.4M", "sub": "YTD total"},
    {"label": "Loans Outstanding", "value": "KSh 22.6M", "sub": "Active loan portfolio"},
]

SACCO_MEMBERS = [
    {"rank": 1, "initials": "GW", "name": "Grace Wanjiku", "role": "Chairperson", "amount": "KSh 6.2M"},
    {"rank": 2, "initials": "AH", "name": "Amina Hassan", "role": "Treasurer", "amount": "KSh 5.4M"},
    {"rank": 3, "initials": "DO", "name": "David Ochieng", "role": "Secretary", "amount": "KSh 4.8M"},
    {"rank": 4, "initials": "SK", "name": "Sarah Kilonzo", "role": "Member", "amount": "KSh 3.6M"},
    {"rank": 5, "initials": "JM", "name": "James Mwangi", "role": "Member", "amount": "KSh 3.2M"},
]

LOAN_PRODUCTS = [
    {"id": "emergency", "name": "Emergency Loan", "rate": "8% p.a.",
     "desc": "Instant access up to 3x your savings. Processing within 24 hours."},
    {"id": "development", "name": "Property Development Loan", "rate": "10% p.a.",
     "desc": "Up to KSh 5M for renovations, expansions, or new property purchases."},
    {"id": "education", "name": "Education Loan", "rate": "7% p.a.",
     "desc": "School fees and tuition support for members and their children."},
    {"id": "asset", "name": "Asset Finance Loan", "rate": "11% p.a.",
     "desc": "Vehicle, equipment, and solar installation financing up to KSh 3M."},
]

RADIO_STATS = [
    {"label": "Monthly Listeners", "value": "12,480", "sub": "Unique listeners"},
    {"label": "Total Shows", "value": "24", "sub": "Active programming"},
    {"label": "Podcast Downloads", "value": "84,200", "sub": "All-time"},
    {"label": "Avg. Live Rating", "value": "4.8★", "sub": "Listener feedback"},
]

RADIO_SHOWS = [
    {"id": "morning", "icon": "fa-sun", "type": "morning", "name": "The Morning Drive",
     "host": "Hosted by Grace Wanjiku", "status": "live", "listeners": "1,840", "time": "7-9 AM"},
    {"id": "property", "icon": "fa-building", "type": "property", "name": "The Property Show",
     "host": "Hosted by David Ochieng", "status": "live", "listeners": "2,240", "time": "10-11 AM"},
    {"id": "beats", "icon": "fa-music", "type": "music", "name": "Nairobi Beats",
     "host": "Hosted by Sarah Kilonzo", "status": "upcoming", "listeners": "—", "time": "2-4 PM"},
    {"id": "talks", "icon": "fa-comments", "type": "talk", "name": "Landlord Talks",
     "host": "Hosted by Amina Hassan", "status": "upcoming", "listeners": "—", "time": "5-6 PM"},
    {"id": "comedy", "icon": "fa-laugh", "type": "comedy", "name": "Comedy Hour",
     "host": "Hosted by Brian Kamau", "status": "recorded", "listeners": "3,420", "time": "8-9 PM"},
    {"id": "night", "icon": "fa-moon", "type": "night", "name": "Late Night Vibes",
     "host": "Hosted by Mary Njoki", "status": "recorded", "listeners": "2,180", "time": "10 PM-12 AM"},
]

# Mutable action logs
bookings: list[dict] = []
purchases: list[dict] = []
listen_log: list[dict] = []

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Stat(BaseModel):
    label: str
    value: str
    sub: str


class SpaService(BaseModel):
    id: str
    icon: str
    type: str
    name: str
    desc: str
    price: int
    duration: str


class BookSpaRequest(BaseModel):
    service_id: str
    preferred_date: Optional[date] = None
    notes: Optional[str] = None


class Hive(BaseModel):
    id: str
    emoji: str
    name: str
    location: str
    health: str
    population: str
    last_harvest: str
    yield_kg: int


class FashionItem(BaseModel):
    id: str
    emoji: str
    type: str
    condition: str
    title: str
    seller: str
    initials: str
    color: str
    price: int
    original: int


class BuyFashionRequest(BaseModel):
    item_id: str
    buyer_name: Optional[str] = "Landlord Admin"
    payment_method: str = "M-Pesa"


class Comedian(BaseModel):
    id: str
    initials: str
    name: str
    style: str
    color: str
    set: str
    rating: float


class BookComedianRequest(BaseModel):
    comedian_id: str
    show_date: Optional[date] = None


class AquaSystem(BaseModel):
    id: str
    emoji: str
    name: str
    location: str
    status: str
    fish: str
    plants: str
    harvest: str
    yield_: str = Field(alias="yield")

    model_config = {"populate_by_name": True}


class SaccoMember(BaseModel):
    rank: int
    initials: str
    name: str
    role: str
    amount: str


class LoanProduct(BaseModel):
    id: str
    name: str
    rate: str
    desc: str


class ApplyLoanRequest(BaseModel):
    product_id: str
    amount: int = Field(ge=1000, le=5_000_000)
    purpose: Optional[str] = None


class RadioShow(BaseModel):
    id: str
    icon: str
    type: str
    name: str
    host: str
    status: str
    listeners: str
    time: str


class ListenRequest(BaseModel):
    show_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "service": "mwarokin-lifestyle", "timestamp": datetime.utcnow().isoformat()}


# ---- 1. Spa ----
@app.get("/api/v1/spa")
def get_spa():
    return {
        "next_retreat": "May 10-12 · Naivasha",
        "stats": SPA_STATS,
        "services": SPA_SERVICES,
    }


@app.post("/api/v1/spa/book", status_code=status.HTTP_201_CREATED)
def book_spa(body: BookSpaRequest):
    svc = next((s for s in SPA_SERVICES if s["id"] == body.service_id), None)
    if not svc:
        raise HTTPException(404, "Service not found")
    ref = f"SPA-{uuid4().hex[:6].upper()}"
    rec = {
        "reference": ref,
        "service": svc["name"],
        "price": svc["price"],
        "duration": svc["duration"],
        "preferred_date": body.preferred_date.isoformat() if body.preferred_date else None,
        "notes": body.notes,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }
    bookings.append(rec)
    return {"success": True, "message": f"Booked {svc['name']}", "reference": ref, "price": svc["price"]}


# ---- 2. Honey ----
@app.get("/api/v1/honey")
def get_honey():
    return {
        "ytd_harvest_kg": 248,
        "stats": HONEY_STATS,
        "hives": HIVES,
    }


@app.get("/api/v1/honey/hives/{hive_id}")
def get_hive(hive_id: str):
    hive = next((h for h in HIVES if h["id"] == hive_id), None)
    if not hive:
        raise HTTPException(404, "Hive not found")
    return hive


# ---- 3. Fashion ----
@app.get("/api/v1/fashion")
def get_fashion():
    return {
        "hero": {"items_listed": 1240, "items_sold": 864, "satisfaction": "96%"},
        "items": FASHION_ITEMS,
    }


@app.post("/api/v1/fashion/buy", status_code=status.HTTP_201_CREATED)
def buy_fashion(body: BuyFashionRequest):
    item = next((i for i in FASHION_ITEMS if i["id"] == body.item_id), None)
    if not item:
        raise HTTPException(404, "Item not found")
    ref = f"FSH-{uuid4().hex[:6].upper()}"
    rec = {
        "reference": ref,
        "item": item["title"],
        "price": item["price"],
        "seller": item["seller"],
        "buyer": body.buyer_name,
        "payment_method": body.payment_method,
        "status": "inquiry_sent",
        "created_at": datetime.utcnow().isoformat(),
    }
    purchases.append(rec)
    return {
        "success": True,
        "message": f"Inquiry sent for {item['title']}",
        "reference": ref,
        "price": item["price"],
        "seller": item["seller"],
    }


# ---- 4. Comedy ----
@app.get("/api/v1/comedy")
def get_comedy():
    return {
        "next_show": "May 2 · 8 PM",
        "stats": COMEDY_STATS,
        "comedians": COMEDIANS,
    }


@app.post("/api/v1/comedy/book", status_code=status.HTTP_201_CREATED)
def book_comedian(body: BookComedianRequest):
    comic = next((c for c in COMEDIANS if c["id"] == body.comedian_id), None)
    if not comic:
        raise HTTPException(404, "Comedian not found")
    ref = f"CMD-{uuid4().hex[:6].upper()}"
    rec = {
        "reference": ref,
        "comedian": comic["name"],
        "style": comic["style"],
        "show_date": body.show_date.isoformat() if body.show_date else None,
        "status": "requested",
        "created_at": datetime.utcnow().isoformat(),
    }
    bookings.append(rec)
    return {"success": True, "message": f"Booking requested for {comic['name']}", "reference": ref}


# ---- 5. Aquaponics ----
@app.get("/api/v1/aquaponics")
def get_aquaponics():
    return {
        "hero": {"active_systems": 3, "fish_harvested": 840, "vegetables_ytd": "1.2T"},
        "systems": AQUA_SYSTEMS,
    }


# ---- 6. Sacco ----
@app.get("/api/v1/sacco")
def get_sacco():
    return {
        "dividend_2024": "14.2% p.a.",
        "stats": SACCO_STATS,
        "top_members": SACCO_MEMBERS,
        "loan_products": LOAN_PRODUCTS,
    }


@app.post("/api/v1/sacco/loans/apply", status_code=status.HTTP_201_CREATED)
def apply_loan(body: ApplyLoanRequest):
    product = next((p for p in LOAN_PRODUCTS if p["id"] == body.product_id), None)
    if not product:
        raise HTTPException(404, "Loan product not found")
    ref = f"LN-{uuid4().hex[:6].upper()}"
    rec = {
        "reference": ref,
        "product": product["name"],
        "rate": product["rate"],
        "amount": body.amount,
        "purpose": body.purpose,
        "status": "under_review",
        "created_at": datetime.utcnow().isoformat(),
    }
    bookings.append(rec)
    return {
        "success": True,
        "message": f"Loan application submitted for {product['name']}",
        "reference": ref,
        "amount": body.amount,
        "rate": product["rate"],
    }


# ---- 7. Radio ----
@app.get("/api/v1/radio")
def get_radio():
    return {
        "live_now": "The Property Show",
        "stats": RADIO_STATS,
        "shows": RADIO_SHOWS,
    }


@app.post("/api/v1/radio/listen")
def listen_show(body: ListenRequest):
    show = next((s for s in RADIO_SHOWS if s["id"] == body.show_id), None)
    if not show:
        raise HTTPException(404, "Show not found")
    action = (
        "Tuning in live"
        if show["status"] == "live"
        else "Reminder set"
        if show["status"] == "upcoming"
        else "Playing recording"
    )
    listen_log.append({
        "show_id": body.show_id,
        "show_name": show["name"],
        "action": action,
        "at": datetime.utcnow().isoformat(),
    })
    return {
        "success": True,
        "message": f"{action}: {show['name']}",
        "status": show["status"],
        "host": show["host"],
        "time": show["time"],
    }


# ---- Aggregate page load ----
@app.get("/api/v1/page")
def get_full_page():
    """Single call that returns everything the frontend needs on load."""
    return {
        "spa": {"next_retreat": "May 10-12 · Naivasha", "stats": SPA_STATS, "services": SPA_SERVICES},
        "honey": {"ytd_harvest_kg": 248, "stats": HONEY_STATS, "hives": HIVES},
        "fashion": {"hero": {"items_listed": 1240, "items_sold": 864, "satisfaction": "96%"}, "items": FASHION_ITEMS},
        "comedy": {"next_show": "May 2 · 8 PM", "stats": COMEDY_STATS, "comedians": COMEDIANS},
        "aquaponics": {"hero": {"active_systems": 3, "fish_harvested": 840, "vegetables_ytd": "1.2T"}, "systems": AQUA_SYSTEMS},
        "sacco": {"dividend_2024": "14.2% p.a.", "stats": SACCO_STATS, "top_members": SACCO_MEMBERS, "loan_products": LOAN_PRODUCTS},
        "radio": {"live_now": "The Property Show", "stats": RADIO_STATS, "shows": RADIO_SHOWS},
    }


@app.get("/api/v1/activity")
def list_activity(limit: Annotated[int, Query(ge=1, le=100)] = 30):
    return {
        "bookings": bookings[-limit:],
        "purchases": purchases[-limit:],
        "listens": listen_log[-limit:],
    }


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### Quick start

```bash
pip install fastapi uvicorn pydantic
# save as main.py
uvicorn main:app --reload --port 8000
```

### Real functionality

| Feature | Endpoint | Action |
|---------|----------|--------|
| **Full page** | `GET /api/v1/page` | Everything in one call |
| Spa | `GET /api/v1/spa` | Stats + services |
| | `POST /api/v1/spa/book` | Book a treatment → `SPA-XXXXXX` |
| Honey | `GET /api/v1/honey` | Stats + hives |
| Fashion | `GET /api/v1/fashion` | Marketplace items |
| | `POST /api/v1/fashion/buy` | Send purchase inquiry |
| Comedy | `GET /api/v1/comedy` | Stats + comedians |
| | `POST /api/v1/comedy/book` | Request comedian booking |
| Aquaponics | `GET /api/v1/aquaponics` | Systems + yields |
| Sacco | `GET /api/v1/sacco` | Members + loan products |
| | `POST /api/v1/sacco/loans/apply` | Submit loan application |
| Radio | `GET /api/v1/radio` | Shows + live status |
| | `POST /api/v1/radio/listen` | Listen / set reminder / play recording |

All mock data from the frontend is preserved and served as typed JSON. Booking, purchase, and listen actions generate real references and are stored in-memory (ready to swap for a database).