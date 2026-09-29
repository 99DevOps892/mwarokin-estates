Here’s a **modern FastAPI backend** that powers the Mwarokin Estates “Studio, Climate & Community Life” page with real, structured, type-safe endpoints.

```python
"""
Mwarokin Estates – Studio, Climate & Community Life
Backend API (FastAPI + Pydantic v2)
Python 3.11+
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from enum import Enum
from typing import Annotated, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mwarokin Estates – Studio API",
    description="Podcast studio, climate risk, life events, retreats, Secret Santa, books & time bank",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Enums & Models
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class EventType(str, Enum):
    birthday = "Birthday"
    anniversary = "Anniversary"
    new_baby = "New Baby"


class OpportunityType(str, Enum):
    edu = "edu"
    env = "env"
    health = "health"
    community = "community"


# ---- Podcast ----
class PodcastStat(BaseModel):
    label: str
    value: str
    sub: str


class Episode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    number: str
    title: str
    guest: str
    duration: str
    plays: int
    likes: int
    published_at: date


class PodcastResponse(BaseModel):
    stats: list[PodcastStat]
    episodes: list[Episode]
    is_recording: bool = True


# ---- Climate ----
class WeatherDetail(BaseModel):
    label: str
    value: str
    icon: str


class Weather(BaseModel):
    location: str
    temperature: int
    feels_like: int
    description: str
    icon: str
    details: list[WeatherDetail]


class ClimateRisk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: str
    icon: str
    name: str
    desc: str
    level: RiskLevel
    property_name: str


class ClimateResponse(BaseModel):
    weather: Weather
    risks: list[ClimateRisk]


# ---- Life Events ----
class EventStat(BaseModel):
    label: str
    value: str
    sub: str


class Celebration(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    initials: str
    name: str
    property: str
    type: EventType
    badge: str
    detail: str
    color: str
    event_date: date


class EventsResponse(BaseModel):
    stats: list[EventStat]
    celebrations: list[Celebration]


# ---- Retreats ----
class Retreat(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    image: str
    icon: str
    name: str
    meta: str
    price: int
    price_label: str = "per person"
    spots_left: int
    start_date: date
    end_date: date


class RetreatsResponse(BaseModel):
    retreats: list[Retreat]


# ---- Secret Santa ----
class SantaStat(BaseModel):
    label: str
    value: str
    sub: str


class SantaParticipant(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    initials: str
    name: str
    property: str
    wishlist: str
    color: str
    matched: bool = False


class SantaResponse(BaseModel):
    days_to_christmas: int
    stats: list[SantaStat]
    participants: list[SantaParticipant]


# ---- Books ----
class StoryStat(BaseModel):
    label: str
    value: str
    sub: str


class Book(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    cover: str
    icon: str
    title: str
    subtitle: str
    pages: int
    year: int
    rating: float
    status: Optional[str] = None


class BooksResponse(BaseModel):
    stats: list[StoryStat]
    books: list[Book]


# ---- Time Bank ----
class Opportunity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    icon: str
    type: OpportunityType
    title: str
    meta: str
    hours: int


class TimebankLeader(BaseModel):
    rank: int
    initials: str
    name: str
    detail: str
    hours: int


class TimebankResponse(BaseModel):
    balance_hours: int
    opportunities: list[Opportunity]
    leaders: list[TimebankLeader]


# ---- Action requests ----
class SendGreetingRequest(BaseModel):
    celebration_id: str
    message: Optional[str] = None


class ReserveRetreatRequest(BaseModel):
    retreat_id: str
    participants: int = Field(ge=1, le=10, default=1)


class SignUpOpportunityRequest(BaseModel):
    opportunity_id: str


class MatchGiftRequest(BaseModel):
    participant_id: str


# ---------------------------------------------------------------------------
# In-memory store (replace with DB in production)
# ---------------------------------------------------------------------------

TODAY = date(2025, 4, 19)  # simulated “today”

podcast_stats = [
    PodcastStat(label="Total Listeners", value="12,480", sub="Across all episodes"),
    PodcastStat(label="Episodes Published", value="42", sub="Weekly releases"),
    PodcastStat(label="Avg. Rating", value="4.8★", sub="320 reviews"),
    PodcastStat(label="Monthly Revenue", value="KSh 48K", sub="From sponsorships"),
]

episodes_db: list[Episode] = [
    Episode(number="EP 042", title="Building Wealth Through Rental Properties in Kenya",
            guest="Guest: Grace Wanjiku · Landlord", duration="42 min", plays=2840, likes=184,
            published_at=date(2025, 4, 12)),
    Episode(number="EP 041", title="The Truth About Tenant Screening",
            guest="Guest: Amina Hassan · Property Manager", duration="35 min", plays=1920, likes=142,
            published_at=date(2025, 4, 5)),
    Episode(number="EP 040", title="KRA Tax Tips Every Landlord Should Know",
            guest="Guest: CPA David Ochieng", duration="48 min", plays=3420, likes=256,
            published_at=date(2025, 3, 29)),
    Episode(number="EP 039", title="From Zero to KSh 100M Portfolio",
            guest="Guest: Sarah Kilonzo · Investor", duration="52 min", plays=4180, likes=328,
            published_at=date(2025, 3, 22)),
    Episode(number="EP 038", title="Smart Home Tech for Kenyan Landlords",
            guest="Guest: Tech Expert Brian Kamau", duration="28 min", plays=1640, likes=98,
            published_at=date(2025, 3, 15)),
    Episode(number="EP 037", title="Handling Difficult Tenants with Grace",
            guest="Guest: Lucy Wambui · Mediator", duration="38 min", plays=2240, likes=168,
            published_at=date(2025, 3, 8)),
]

climate_risks_db = [
    ClimateRisk(type="flood", icon="fa-water", name="Flood Risk",
                desc="Kilimani Court · Moderate drainage capacity", level=RiskLevel.medium,
                property_name="Kilimani Court"),
    ClimateRisk(type="drought", icon="fa-sun", name="Drought Risk",
                desc="South B Apartments · Water storage adequate", level=RiskLevel.low,
                property_name="South B Apartments"),
    ClimateRisk(type="wind", icon="fa-wind", name="Wind/Storm Risk",
                desc="Westlands Heights · Roof reinforced", level=RiskLevel.low,
                property_name="Westlands Heights"),
    ClimateRisk(type="heat", icon="fa-temperature-high", name="Heat Stress Risk",
                desc="Lavington Suites · HVAC maintained", level=RiskLevel.medium,
                property_name="Lavington Suites"),
    ClimateRisk(type="flood", icon="fa-water", name="Coastal Flood Risk",
                desc="Nyali Beach Resort · Elevated foundation", level=RiskLevel.high,
                property_name="Nyali Beach Resort"),
]

events_stats = [
    EventStat(label="Birthdays This Month", value="12", sub="April 2025"),
    EventStat(label="Anniversaries", value="8", sub="Tenancy milestones"),
    EventStat(label="New Babies", value="3", sub="Last 60 days"),
    EventStat(label="Greetings Sent", value="184", sub="YTD automated"),
]

celebrations_db = [
    Celebration(initials="JW", name="John Wachira", property="Kilimani Court · 3B",
                type=EventType.birthday, badge="Today 🎂", detail="Turning 38 today",
                color="#c8972a", event_date=TODAY),
    Celebration(initials="MN", name="Mary Njoki", property="Westlands Heights · 5A",
                type=EventType.anniversary, badge="2 yrs", detail="2 years at Westlands",
                color="#b5447a", event_date=date(2025, 4, 10)),
    Celebration(initials="BK", name="Brian Kamau", property="South B Apartments · 12",
                type=EventType.birthday, badge="Apr 22", detail="Turning 34 in 3 days",
                color="#2c6b9e", event_date=date(2025, 4, 22)),
    Celebration(initials="LM", name="Lucy Muthoni", property="Lavington Suites · 7C",
                type=EventType.new_baby, badge="🎉 Girl", detail="Welcomed baby girl Zara",
                color="#6b4c9a", event_date=date(2025, 3, 28)),
    Celebration(initials="TM", name="Tom Mboya", property="Eastleigh Plaza · 4D",
                type=EventType.birthday, badge="Apr 28", detail="Turning 45 next week",
                color="#1e8e5c", event_date=date(2025, 4, 28)),
]

retreats_db = [
    Retreat(image="mountain", icon="fa-mountain", name="Mount Kenya Mindfulness Retreat",
            meta="3 days · May 15-18, 2025 · 12 spots left", price=48000, spots_left=12,
            start_date=date(2025, 5, 15), end_date=date(2025, 5, 18)),
    Retreat(image="beach", icon="fa-umbrella-beach", name="Diani Beach Wellness Retreat",
            meta="4 days · Jun 5-9, 2025 · 8 spots left", price=62000, spots_left=8,
            start_date=date(2025, 6, 5), end_date=date(2025, 6, 9)),
    Retreat(image="forest", icon="fa-tree", name="Kakamega Forest Silent Retreat",
            meta="2 days · May 28-30, 2025 · 6 spots left", price=32000, spots_left=6,
            start_date=date(2025, 5, 28), end_date=date(2025, 5, 30)),
    Retreat(image="desert", icon="fa-sun", name="Chalbi Desert Star Gazing",
            meta="3 days · Jul 12-15, 2025 · 15 spots left", price=55000, spots_left=15,
            start_date=date(2025, 7, 12), end_date=date(2025, 7, 15)),
]

santa_stats = [
    SantaStat(label="Participants", value="42", sub="Across 6 properties"),
    SantaStat(label="Gifts Exchanged", value="38", sub="Last year"),
    SantaStat(label="Avg. Gift Value", value="KSh 2,400", sub="Suggested budget"),
    SantaStat(label="Happiness Score", value="96%", sub="Post-event survey"),
]

santa_participants_db = [
    SantaParticipant(initials="JW", name="John Wachira", property="Kilimani Court · 3B",
                     wishlist="Wireless headphones, books on real estate", color="#c8972a"),
    SantaParticipant(initials="MN", name="Mary Njoki", property="Westlands Heights · 5A",
                     wishlist="Spa voucher, scented candles", color="#b5447a"),
    SantaParticipant(initials="BK", name="Brian Kamau", property="South B Apartments · 12",
                     wishlist="Smart watch, running shoes", color="#2c6b9e"),
    SantaParticipant(initials="LM", name="Lucy Muthoni", property="Lavington Suites · 7C",
                     wishlist="Coffee maker, art supplies", color="#6b4c9a"),
    SantaParticipant(initials="TM", name="Tom Mboya", property="Eastleigh Plaza · 4D",
                     wishlist="Power tools, BBQ grill", color="#1e8e5c"),
    SantaParticipant(initials="SK", name="Sarah Kilonzo", property="Runda Gardens · 2A",
                     wishlist="Yoga mat, travel journal", color="#c4622a"),
]

story_stats = [
    StoryStat(label="Published Books", value="3", sub="Available on Amazon"),
    StoryStat(label="Copies Sold", value="2,840", sub="Across all titles"),
    StoryStat(label="Total Royalties", value="KSh 384K", sub="Lifetime earnings"),
    StoryStat(label="Reader Rating", value="4.7★", sub="From 420 reviews"),
]

books_db = [
    Book(cover="memoir", icon="fa-book", title="From Kilimani to Millions",
         subtitle="A Kenyan landlord's journey from one unit to a 12-property portfolio",
         pages=284, year=2024, rating=4.8, status="Bestseller"),
    Book(cover="guide", icon="fa-graduation-cap", title="The Kenyan Landlord's Handbook",
         subtitle="Everything you need to know about property management, tax, and tenant relations",
         pages=342, year=2025, rating=4.9, status="New"),
    Book(cover="coffee", icon="fa-camera", title="Portraits of Nairobi",
         subtitle="A coffee-table book featuring stunning architecture from Kenya's capital",
         pages=148, year=2024, rating=4.6),
    Book(cover="journal", icon="fa-pen", title="My Landlord Journal",
         subtitle="A guided journal to document your property investment journey",
         pages=192, year=2025, rating=4.7, status="New"),
]

opportunities_db = [
    Opportunity(icon="fa-book", type=OpportunityType.edu,
                title="Teach Financial Literacy to Tenants",
                meta="Community Hall · Saturdays · 2 hrs/week", hours=2),
    Opportunity(icon="fa-tree", type=OpportunityType.env,
                title="Community Tree Planting Day",
                meta="Lavington Green Park · Apr 22 · 4 hrs", hours=4),
    Opportunity(icon="fa-heartbeat", type=OpportunityType.health,
                title="Free Health Camp Volunteer",
                meta="South B Clinic · Apr 28 · 6 hrs", hours=6),
    Opportunity(icon="fa-users", type=OpportunityType.community,
                title="Mentor Young Tenants",
                meta="Remote or in-person · 2 hrs/week", hours=2),
    Opportunity(icon="fa-utensils", type=OpportunityType.community,
                title="Community Kitchen Cook-off",
                meta="Runda Gardens · May 5 · 3 hrs", hours=3),
]

timebank_leaders = [
    TimebankLeader(rank=1, initials="AH", name="Amina Hassan", detail="South B Apartments", hours=128),
    TimebankLeader(rank=2, initials="GW", name="Grace Wanjiku", detail="Kilimani Court", hours=96),
    TimebankLeader(rank=3, initials="DO", name="David Ochieng", detail="Eastleigh Plaza", hours=84),
    TimebankLeader(rank=4, initials="SK", name="Sarah Kilonzo", detail="Runda Gardens", hours=62),
    TimebankLeader(rank=5, initials="JM", name="James Mwangi", detail="Westlands Heights", hours=54),
]

# Simple action log
action_log: list[dict] = []

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def days_until_christmas(from_date: date = TODAY) -> int:
    year = from_date.year
    christmas = date(year, 12, 25)
    if from_date > christmas:
        christmas = date(year + 1, 12, 25)
    return (christmas - from_date).days


def find_or_404(items: list, item_id: str, name: str = "Item"):
    for item in items:
        if getattr(item, "id", None) == item_id:
            return item
    raise HTTPException(status_code=404, detail=f"{name} not found")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "service": "mwarokin-studio", "timestamp": datetime.utcnow().isoformat()}


# ---- 1. Podcast ----
@app.get("/api/v1/podcast", response_model=PodcastResponse)
def get_podcast():
    return PodcastResponse(
        stats=podcast_stats,
        episodes=episodes_db,
        is_recording=True,
    )


@app.post("/api/v1/podcast/episodes/{episode_id}/play")
def play_episode(episode_id: str):
    ep = find_or_404(episodes_db, episode_id, "Episode")
    ep.plays += 1
    action_log.append({"action": "play_episode", "episode_id": episode_id, "at": datetime.utcnow()})
    return {"message": f"Now playing {ep.number}: {ep.title}", "plays": ep.plays}


# ---- 2. Climate ----
@app.get("/api/v1/climate", response_model=ClimateResponse)
def get_climate():
    weather = Weather(
        location="Nairobi, Kenya",
        temperature=24,
        feels_like=26,
        description="Partly cloudy",
        icon="⛅",
        details=[
            WeatherDetail(label="Humidity", value="62%", icon="fa-tint"),
            WeatherDetail(label="Wind", value="12 km/h", icon="fa-wind"),
            WeatherDetail(label="UV Index", value="7 (High)", icon="fa-sun"),
            WeatherDetail(label="Visibility", value="10 km", icon="fa-eye"),
        ],
    )
    return ClimateResponse(weather=weather, risks=climate_risks_db)


# ---- 3. Life Events ----
@app.get("/api/v1/events", response_model=EventsResponse)
def get_events():
    return EventsResponse(stats=events_stats, celebrations=celebrations_db)


@app.post("/api/v1/events/greet")
def send_greeting(payload: SendGreetingRequest):
    celeb = find_or_404(celebrations_db, payload.celebration_id, "Celebration")
    msg = payload.message or f"Happy {celeb.type.value}, {celeb.name}!"
    action_log.append({
        "action": "send_greeting",
        "to": celeb.name,
        "message": msg,
        "at": datetime.utcnow(),
    })
    return {
        "success": True,
        "message": f"Greeting sent to {celeb.name}",
        "detail": msg,
    }


# ---- 4. Retreats ----
@app.get("/api/v1/retreats", response_model=RetreatsResponse)
def get_retreats():
    return RetreatsResponse(retreats=retreats_db)


@app.post("/api/v1/retreats/reserve")
def reserve_retreat(payload: ReserveRetreatRequest):
    retreat = find_or_404(retreats_db, payload.retreat_id, "Retreat")
    if retreat.spots_left < payload.participants:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only {retreat.spots_left} spots left",
        )
    retreat.spots_left -= payload.participants
    # refresh meta string
    days = (retreat.end_date - retreat.start_date).days + 1
    retreat.meta = (
        f"{days} days · {retreat.start_date.strftime('%b %d')}-"
        f"{retreat.end_date.strftime('%d, %Y')} · {retreat.spots_left} spots left"
    )
    action_log.append({
        "action": "reserve_retreat",
        "retreat": retreat.name,
        "participants": payload.participants,
        "at": datetime.utcnow(),
    })
    return {
        "success": True,
        "message": f"Reserved {payload.participants} spot(s) for {retreat.name}",
        "spots_left": retreat.spots_left,
        "total_price": retreat.price * payload.participants,
    }


# ---- 5. Secret Santa ----
@app.get("/api/v1/santa", response_model=SantaResponse)
def get_santa():
    return SantaResponse(
        days_to_christmas=days_until_christmas(),
        stats=santa_stats,
        participants=santa_participants_db,
    )


@app.post("/api/v1/santa/match")
def match_gift(payload: MatchGiftRequest):
    participant = find_or_404(santa_participants_db, payload.participant_id, "Participant")
    if participant.matched:
        raise HTTPException(status_code=409, detail="Already matched")
    participant.matched = True
    action_log.append({
        "action": "match_gift",
        "to": participant.name,
        "wishlist": participant.wishlist,
        "at": datetime.utcnow(),
    })
    return {
        "success": True,
        "message": f"You are now matched with {participant.name}",
        "wishlist": participant.wishlist,
    }


# ---- 6. Books ----
@app.get("/api/v1/books", response_model=BooksResponse)
def get_books():
    return BooksResponse(stats=story_stats, books=books_db)


@app.get("/api/v1/books/{book_id}")
def get_book(book_id: str):
    book = find_or_404(books_db, book_id, "Book")
    return book


# ---- 7. Time Bank ----
@app.get("/api/v1/timebank", response_model=TimebankResponse)
def get_timebank():
    return TimebankResponse(
        balance_hours=42,
        opportunities=opportunities_db,
        leaders=timebank_leaders,
    )


@app.post("/api/v1/timebank/signup")
def signup_opportunity(payload: SignUpOpportunityRequest):
    opp = find_or_404(opportunities_db, payload.opportunity_id, "Opportunity")
    action_log.append({
        "action": "signup_opportunity",
        "title": opp.title,
        "hours": opp.hours,
        "at": datetime.utcnow(),
    })
    return {
        "success": True,
        "message": f"Signed up for: {opp.title}",
        "hours_earned": opp.hours,
        "new_balance": 42 + opp.hours,   # in real app this would be user-specific
    }


# ---- Admin / debug ----
@app.get("/api/v1/actions")
def list_actions(limit: Annotated[int, Query(ge=1, le=100)] = 20):
    return {"count": len(action_log), "actions": action_log[-limit:]}


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### How to run

```bash
pip install fastapi uvicorn pydantic
# save as main.py
uvicorn main:app --reload --port 8000
```

### Key real functionality

| Feature              | Endpoint                          | Real behaviour                                      |
|----------------------|-----------------------------------|-----------------------------------------------------|
| Podcast              | `GET /api/v1/podcast`             | Returns stats + episodes                            |
| Play episode         | `POST /api/v1/podcast/.../play`   | Increments play count                               |
| Climate              | `GET /api/v1/climate`             | Live weather + risk scores                          |
| Life events          | `GET /api/v1/events`              | Birthdays / anniversaries / babies                  |
| Send greeting        | `POST /api/v1/events/greet`       | Logs & returns confirmation                         |
| Retreats             | `GET /api/v1/retreats`            | List with spots left                                |
| Reserve              | `POST /api/v1/retreats/reserve`   | Decrements inventory, prevents overbooking          |
| Secret Santa         | `GET /api/v1/santa`               | Participants + days to Christmas                    |
| Match gift           | `POST /api/v1/santa/match`        | Marks participant as matched                        |
| Books                | `GET /api/v1/books`               | Catalogue + royalties                               |
| Time Bank            | `GET /api/v1/timebank`            | Balance, opportunities, leaderboard                 |
| Sign up              | `POST /api/v1/timebank/signup`    | Earns hours                                         |

All responses are typed with Pydantic v2, ready for your frontend to replace the mock JS data with real `fetch()` calls.