```python
"""
Mwarokin Estates – Hobbies, Heritage & Hobbies Backend (Page 18)
Python 3.11+ | FastAPI + SQLAlchemy + Pydantic v2
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Annotated, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────
DATABASE_URL = "sqlite:///./mwarokin_hobbies.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]

# ──────────────────────────────────────────────
# SQLAlchemy Models
# ──────────────────────────────────────────────
class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    emoji: Mapped[str] = mapped_column(String(10), default="📷")
    photo_type: Mapped[str] = mapped_column(String(40), default="skyline")  # skyline, sunset, garden...
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    initials: Mapped[str] = mapped_column(String(4), nullable=False)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    contest_entry: Mapped[bool] = mapped_column(Boolean, default=False)
    is_winner: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WildlifeSpecies(Base):
    __tablename__ = "wildlife_species"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    latin: Mapped[str] = mapped_column(String(120), nullable=False)
    emoji: Mapped[str] = mapped_column(String(10), default="🐦")
    sightings: Mapped[int] = mapped_column(Integer, default=0)
    last_seen: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class Poem(Base):
    __tablename__ = "poems"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    initials: Mapped[str] = mapped_column(String(4), nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#c8972a")
    likes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LanguageExchange(Base):
    __tablename__ = "language_exchanges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    initials: Mapped[str] = mapped_column(String(4), nullable=False)
    property_unit: Mapped[str] = mapped_column(String(120), nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#c8972a")
    teaching_flag: Mapped[str] = mapped_column(String(10))
    teaching_name: Mapped[str] = mapped_column(String(60))
    learning_flag: Mapped[str] = mapped_column(String(10))
    learning_name: Mapped[str] = mapped_column(String(60))
    level: Mapped[str] = mapped_column(String(30), default="Intermediate")
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    exchanges_count: Mapped[int] = mapped_column(Integer, default=0)


class HeritageEvent(Base):
    __tablename__ = "heritage_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    year: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    badge: Mapped[str] = mapped_column(String(40), default="Historical")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class TrailStop(Base):
    __tablename__ = "trail_stops"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    meta: Mapped[str] = mapped_column(String(150), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    distance_km: Mapped[float] = mapped_column(Float, default=0.0)


class BoardGame(Base):
    __tablename__ = "board_games"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    emoji: Mapped[str] = mapped_column(String(10), default="🎲")
    game_type: Mapped[str] = mapped_column(String(40), default="strategy")
    players: Mapped[str] = mapped_column(String(40), default="2-4 players")
    duration: Mapped[str] = mapped_column(String(40), default="30-60 min")
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")
    owned: Mapped[int] = mapped_column(Integer, default=1)
    join_count: Mapped[int] = mapped_column(Integer, default=0)


class CelestialBody(Base):
    __tablename__ = "celestial_bodies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    emoji: Mapped[str] = mapped_column(String(10), default="🌕")
    body_type: Mapped[str] = mapped_column(String(40), default="moon")
    meta: Mapped[str] = mapped_column(String(120), nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), default="visible")  # best | visible | low


class ClubStats(Base):
    """Simple key-value store for aggregate club stats."""
    __tablename__ = "club_stats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-like string for simplicity


# ──────────────────────────────────────────────
# Pydantic Schemas
# ──────────────────────────────────────────────
class StatItem(BaseModel):
    label: str
    value: str
    sub: str


class PhotoOut(BaseModel):
    id: str
    emoji: str
    type: str
    title: str
    author: str
    initials: str
    likes: int

    model_config = {"from_attributes": True}


class PhotoStatsOut(BaseModel):
    photos_shared: int
    photographers: int
    contest_entries: int
    winning_photos: int


class SpeciesOut(BaseModel):
    id: str
    emoji: str
    name: str
    latin: str
    sightings: int

    model_config = {"from_attributes": True}


class WildlifeStatsOut(BaseModel):
    species_recorded: int
    bird_sightings: int
    sanctuary_certified: int
    nesting_boxes: int


class PoemOut(BaseModel):
    id: str
    title: str
    body: str
    author: str
    initials: str
    color: str
    likes: int

    model_config = {"from_attributes": True}


class LangPair(BaseModel):
    flag: str
    name: str
    label: str


class ExchangeOut(BaseModel):
    id: str
    initials: str
    name: str
    property: str
    color: str
    teaching: LangPair
    learning: LangPair
    level: str
    available: bool

    model_config = {"from_attributes": True}


class LanguageHeroStats(BaseModel):
    participants: int
    languages: int
    exchanges: int


class HeritageItemOut(BaseModel):
    id: str
    year: str
    title: str
    desc: str
    badge: str

    model_config = {"from_attributes": True}


class TrailStopOut(BaseModel):
    id: str
    number: int
    name: str
    meta: str
    completed: bool

    model_config = {"from_attributes": True}


class HeritageTrailInfo(BaseModel):
    stops: int
    distance_km: float
    completed_stops: int


class GameOut(BaseModel):
    id: str
    emoji: str
    type: str
    title: str
    players: str
    duration: str
    difficulty: str
    owned: int

    model_config = {"from_attributes": True}


class BoardGameHeroStats(BaseModel):
    members: int
    games_owned: int
    weekly_meetups: int


class CelestialOut(BaseModel):
    id: str
    emoji: str
    type: str
    name: str
    meta: str
    visibility: str

    model_config = {"from_attributes": True}


class ObservatoryStatsOut(BaseModel):
    club_members: int
    stargazing_nights: int
    photos_captured: int
    telescopes_owned: int


class LikeResponse(BaseModel):
    id: str
    likes: int
    message: str


class ActionResponse(BaseModel):
    status: str
    message: str


# ──────────────────────────────────────────────
# App
# ──────────────────────────────────────────────
app = FastAPI(
    title="Mwarokin Estates – Hobbies & Heritage API",
    description="Backend for Hobbies, Heritage & Hobbies (Page 18)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# Seed
# ──────────────────────────────────────────────
def seed_database(db: Session) -> None:
    if db.query(Photo).first():
        return

    # Photography
    photos = [
        Photo(title="Kilimani at Dusk", emoji="🌇", photo_type="skyline", author="Grace Wanjiku", initials="GW", likes=248, contest_entry=True, is_winner=True),
        Photo(title="Lavington Sunset", emoji="🌅", photo_type="sunset", author="Amina Hassan", initials="AH", likes=184, contest_entry=True, is_winner=True),
        Photo(title="Runda Gardens Morning", emoji="🌳", photo_type="garden", author="Sarah Kilonzo", initials="SK", likes=156, contest_entry=True),
        Photo(title="Warm Living Room", emoji="🛋", photo_type="interior", author="Mary Njoki", initials="MN", likes=142),
        Photo(title="Community Day", emoji="👨‍👩‍👧", photo_type="people", author="John Wachira", initials="JW", likes=312, contest_entry=True, is_winner=True),
        Photo(title="Mural in Progress", emoji="🎨", photo_type="abstract", author="Brian Kamau", initials="BK", likes=178, contest_entry=True),
    ]
    db.add_all(photos)

    # Wildlife
    species = [
        WildlifeSpecies(name="African Grey Parrot", latin="Psittacus erithacus", emoji="🦜", sightings=42, last_seen=date(2025, 4, 12)),
        WildlifeSpecies(name="Spotted Eagle-Owl", latin="Bubo africanus", emoji="🦉", sightings=28, last_seen=date(2025, 4, 8)),
        WildlifeSpecies(name="Laughing Dove", latin="Spilopelia senegalensis", emoji="🕊", sightings=86, last_seen=date(2025, 4, 18)),
        WildlifeSpecies(name="Black Kite", latin="Milvus migrans", emoji="🦅", sightings=64, last_seen=date(2025, 4, 15)),
        WildlifeSpecies(name="Superb Starling", latin="Lamprotornis superbus", emoji="🐦", sightings=124, last_seen=date(2025, 4, 19)),
        WildlifeSpecies(name="Egyptian Goose", latin="Alopochen aegyptiaca", emoji="🦆", sightings=38, last_seen=date(2025, 4, 10)),
        WildlifeSpecies(name="African Monarch", latin="Danaus chrysippus", emoji="🦋", sightings=96, last_seen=date(2025, 4, 17)),
        WildlifeSpecies(name="Tropical House Gecko", latin="Hemidactylus mabouia", emoji="🦎", sightings=54, last_seen=date(2025, 4, 16)),
    ]
    db.add_all(species)

    # Poetry
    poems = [
        Poem(
            title="The Landlord's Lament",
            body="The pipes do leak, the tenants call,\nThe rent is late, the roof may fall.\nBut in the quiet of the night,\nI see the homes I've made just right.",
            author="Grace Wanjiku", initials="GW", color="#c8972a", likes=48,
        ),
        Poem(
            title="Concrete and Dreams",
            body="Bricks and mortar, sweat and tears,\nA vision built across the years.\nEach door a story, each window a song,\nA place where strangers learn to belong.",
            author="David Ochieng", initials="DO", color="#2c6b9e", likes=62,
        ),
        Poem(
            title="Nairobi Morning",
            body="The matatu horns begin to sing,\nThe kettle whistles, the phones all ring.\nIn my estate, the day awakes,\nWith coffee brewing and fresh-baked cakes.",
            author="Mary Njoki", initials="MN", color="#b5447a", likes=56,
        ),
    ]
    db.add_all(poems)

    # Language Exchange
    exchanges = [
        LanguageExchange(
            name="John Wachira", initials="JW", property_unit="Kilimani Court · 3B", color="#c8972a",
            teaching_flag="🇰🇪", teaching_name="Kiswahili",
            learning_flag="🇫🇷", learning_name="French",
            level="Intermediate", available=True, exchanges_count=12,
        ),
        LanguageExchange(
            name="Amina Hassan", initials="AH", property_unit="South B Apartments · 12", color="#6b4c9a",
            teaching_flag="🇸🇦", teaching_name="Arabic",
            learning_flag="🇰🇪", learning_name="Kikuyu",
            level="Beginner", available=True, exchanges_count=5,
        ),
        LanguageExchange(
            name="Mary Njoki", initials="MN", property_unit="Westlands Heights · 5A", color="#b5447a",
            teaching_flag="🇬🇧", teaching_name="English",
            learning_flag="🇪🇸", learning_name="Spanish",
            level="Advanced", available=False, exchanges_count=28,
        ),
        LanguageExchange(
            name="David Ochieng", initials="DO", property_unit="Eastleigh Plaza · 4D", color="#2c6b9e",
            teaching_flag="🇰🇪", teaching_name="Dholuo",
            learning_flag="🇩🇪", learning_name="German",
            level="Intermediate", available=True, exchanges_count=9,
        ),
    ]
    db.add_all(exchanges)

    # Heritage Timeline
    events = [
        HeritageEvent(year="1928", title="Kilimani Court Origins", description="Built during the colonial era as a residential compound for railway workers.", badge="Heritage Site", sort_order=1),
        HeritageEvent(year="1963", title="Independence Transition", description="Property transferred to Kenyan ownership, becoming a symbol of post-independence aspirations.", badge="Historical", sort_order=2),
        HeritageEvent(year="1985", title="Westlands Heights Built", description="One of the first multi-story apartment complexes in Westlands, setting a new standard.", badge="Landmark", sort_order=3),
        HeritageEvent(year="2018", title="Mwarokin Estates Founded", description="Founded to professionally manage heritage properties with modern standards.", badge="Modern Era", sort_order=4),
        HeritageEvent(year="2025", title="Heritage Trail Established", description="Officially launched 6-stop heritage trail documenting our collective property history.", badge="Current", sort_order=5),
    ]
    db.add_all(events)

    # Trail Stops
    stops = [
        TrailStop(number=1, name="Kilimani Court Gate", meta="Original 1928 gatehouse", completed=True, distance_km=0.0),
        TrailStop(number=2, name="The Railway Cottage", meta="Restored workers' residence", completed=True, distance_km=0.4),
        TrailStop(number=3, name="Independence Plaque", meta="1963 commemorative marker", completed=True, distance_km=0.9),
        TrailStop(number=4, name="Westlands Tower", meta="First high-rise apartment", completed=False, distance_km=1.4),
        TrailStop(number=5, name="Mwarokin Archive Room", meta="Historical documents museum", completed=False, distance_km=1.9),
        TrailStop(number=6, name="Heritage Garden", meta="Native plants collection", completed=False, distance_km=2.4),
    ]
    db.add_all(stops)

    # Board Games
    games = [
        BoardGame(title="Chess", emoji="♟", game_type="strategy", players="2 players", duration="30-60 min", difficulty="hard", owned=12),
        BoardGame(title="Settlers of Catan", emoji="🎲", game_type="family", players="3-4 players", duration="60-90 min", difficulty="medium", owned=8),
        BoardGame(title="Monopoly Kenya Edition", emoji="🏠", game_type="classic", players="2-6 players", duration="90-180 min", difficulty="easy", owned=14),
        BoardGame(title="Cards Against Humanity", emoji="🃏", game_type="card", players="4-8 players", duration="30-60 min", difficulty="easy", owned=6),
        BoardGame(title="Dungeons & Dragons", emoji="🐉", game_type="rpg", players="3-6 players", duration="2-4 hrs", difficulty="hard", owned=4),
        BoardGame(title="Codenames", emoji="🧩", game_type="party", players="4-8 players", duration="15-30 min", difficulty="medium", owned=10),
    ]
    db.add_all(games)

    # Celestial
    bodies = [
        CelestialBody(name="Full Moon", emoji="🌕", body_type="moon", meta="April 23, 2025", visibility="best"),
        CelestialBody(name="Mars", emoji="♂️", body_type="mars", meta="Visible at 9 PM", visibility="visible"),
        CelestialBody(name="Jupiter", emoji="♃", body_type="jupiter", meta="With 4 Galilean moons", visibility="best"),
        CelestialBody(name="Venus", emoji="♀️", body_type="venus", meta="Evening star", visibility="visible"),
        CelestialBody(name="Saturn", emoji="♄", body_type="saturn", meta="Rings visible", visibility="low"),
        CelestialBody(name="ISS Pass", emoji="🛰", body_type="station", meta="Apr 22 · 7:42 PM", visibility="best"),
    ]
    db.add_all(bodies)

    db.commit()


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()


# ──────────────────────────────────────────────
# Feature 1 – Photography
# ──────────────────────────────────────────────
@app.get("/api/v1/photography/stats", response_model=PhotoStatsOut, tags=["Photography"])
def get_photo_stats(db: DbSession):
    total = db.query(func.count(Photo.id)).scalar() or 0
    photographers = db.query(func.count(func.distinct(Photo.author))).scalar() or 0
    contest = db.query(func.count(Photo.id)).filter(Photo.contest_entry.is_(True)).scalar() or 0
    winners = db.query(func.count(Photo.id)).filter(Photo.is_winner.is_(True)).scalar() or 0
    return PhotoStatsOut(
        photos_shared=total + 1834,  # base + current
        photographers=photographers + 56,
        contest_entries=contest + 178,
        winning_photos=winners + 9,
    )


@app.get("/api/v1/photography/gallery", response_model=List[PhotoOut], tags=["Photography"])
def list_photos(db: DbSession, limit: int = Query(20, ge=1, le=50)):
    rows = db.query(Photo).order_by(Photo.likes.desc()).limit(limit).all()
    return [
        PhotoOut(
            id=p.id, emoji=p.emoji, type=p.photo_type, title=p.title,
            author=p.author, initials=p.initials, likes=p.likes,
        )
        for p in rows
    ]


@app.post("/api/v1/photography/{photo_id}/like", response_model=LikeResponse, tags=["Photography"])
def like_photo(photo_id: str, db: DbSession):
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(404, "Photo not found")
    photo.likes += 1
    db.commit()
    return LikeResponse(id=photo.id, likes=photo.likes, message=f"Liked “{photo.title}”")


# ──────────────────────────────────────────────
# Feature 2 – Wildlife
# ──────────────────────────────────────────────
@app.get("/api/v1/wildlife/stats", response_model=WildlifeStatsOut, tags=["Wildlife"])
def get_wildlife_stats(db: DbSession):
    species_count = db.query(func.count(WildlifeSpecies.id)).scalar() or 0
    total_sightings = db.query(func.sum(WildlifeSpecies.sightings)).scalar() or 0
    return WildlifeStatsOut(
        species_recorded=species_count,
        bird_sightings=total_sightings + 1100,
        sanctuary_certified=3,
        nesting_boxes=84,
    )


@app.get("/api/v1/wildlife/species", response_model=List[SpeciesOut], tags=["Wildlife"])
def list_species(db: DbSession):
    rows = db.query(WildlifeSpecies).order_by(WildlifeSpecies.sightings.desc()).all()
    return [
        SpeciesOut(id=s.id, emoji=s.emoji, name=s.name, latin=s.latin, sightings=s.sightings)
        for s in rows
    ]


@app.post("/api/v1/wildlife/{species_id}/sighting", response_model=ActionResponse, tags=["Wildlife"])
def log_sighting(species_id: str, db: DbSession):
    sp = db.query(WildlifeSpecies).filter(WildlifeSpecies.id == species_id).first()
    if not sp:
        raise HTTPException(404, "Species not found")
    sp.sightings += 1
    sp.last_seen = date.today()
    db.commit()
    return ActionResponse(
        status="recorded",
        message=f"Sighting of {sp.name} recorded. Total: {sp.sightings}",
    )


# ──────────────────────────────────────────────
# Feature 3 – Poetry
# ──────────────────────────────────────────────
@app.get("/api/v1/poetry/poems", response_model=List[PoemOut], tags=["Poetry"])
def list_poems(db: DbSession):
    rows = db.query(Poem).order_by(Poem.likes.desc()).all()
    return [
        PoemOut(
            id=p.id, title=p.title, body=p.body, author=p.author,
            initials=p.initials, color=p.color, likes=p.likes,
        )
        for p in rows
    ]


@app.post("/api/v1/poetry/{poem_id}/like", response_model=LikeResponse, tags=["Poetry"])
def like_poem(poem_id: str, db: DbSession):
    poem = db.query(Poem).filter(Poem.id == poem_id).first()
    if not poem:
        raise HTTPException(404, "Poem not found")
    poem.likes += 1
    db.commit()
    return LikeResponse(id=poem.id, likes=poem.likes, message=f"Liked “{poem.title}”")


@app.get("/api/v1/poetry/next-open-mic", tags=["Poetry"])
def next_open_mic():
    return {
        "event": "Landlord Poetry Open Mic",
        "date": "2025-05-03",
        "time": "19:00",
        "location": "Kilimani Court Community Hall",
        "status": "open",
    }


# ──────────────────────────────────────────────
# Feature 4 – Language Exchange
# ──────────────────────────────────────────────
@app.get("/api/v1/language/stats", response_model=LanguageHeroStats, tags=["Language"])
def get_language_stats(db: DbSession):
    participants = db.query(func.count(LanguageExchange.id)).scalar() or 0
    total_exchanges = db.query(func.sum(LanguageExchange.exchanges_count)).scalar() or 0
    # Unique languages (teaching + learning)
    langs = set()
    for e in db.query(LanguageExchange).all():
        langs.add(e.teaching_name)
        langs.add(e.learning_name)
    return LanguageHeroStats(
        participants=participants + 80,
        languages=len(langs) + 10,
        exchanges=total_exchanges + 200,
    )


@app.get("/api/v1/language/exchanges", response_model=List[ExchangeOut], tags=["Language"])
def list_exchanges(db: DbSession):
    rows = db.query(LanguageExchange).order_by(LanguageExchange.name).all()
    return [
        ExchangeOut(
            id=e.id, initials=e.initials, name=e.name, property=e.property_unit, color=e.color,
            teaching=LangPair(flag=e.teaching_flag, name=e.teaching_name, label="Teaching"),
            learning=LangPair(flag=e.learning_flag, name=e.learning_name, label="Learning"),
            level=e.level, available=e.available,
        )
        for e in rows
    ]


@app.post("/api/v1/language/{exchange_id}/start", response_model=ActionResponse, tags=["Language"])
def start_exchange(exchange_id: str, db: DbSession):
    e = db.query(LanguageExchange).filter(LanguageExchange.id == exchange_id).first()
    if not e:
        raise HTTPException(404, "Participant not found")
    if not e.available:
        raise HTTPException(400, f"{e.name} is currently busy")
    e.exchanges_count += 1
    db.commit()
    return ActionResponse(
        status="connected",
        message=f"Connected with {e.name} — they teach {e.teaching_name}, you learn {e.learning_name}",
    )


# ──────────────────────────────────────────────
# Feature 5 – Heritage
# ──────────────────────────────────────────────
@app.get("/api/v1/heritage/timeline", response_model=List[HeritageItemOut], tags=["Heritage"])
def get_heritage_timeline(db: DbSession):
    rows = db.query(HeritageEvent).order_by(HeritageEvent.sort_order).all()
    return [
        HeritageItemOut(id=h.id, year=h.year, title=h.title, desc=h.description, badge=h.badge)
        for h in rows
    ]


@app.get("/api/v1/heritage/trail", response_model=List[TrailStopOut], tags=["Heritage"])
def get_trail_stops(db: DbSession):
    rows = db.query(TrailStop).order_by(TrailStop.number).all()
    return [
        TrailStopOut(id=s.id, number=s.number, name=s.name, meta=s.meta, completed=s.completed)
        for s in rows
    ]


@app.get("/api/v1/heritage/trail/info", response_model=HeritageTrailInfo, tags=["Heritage"])
def get_trail_info(db: DbSession):
    stops = db.query(TrailStop).all()
    completed = sum(1 for s in stops if s.completed)
    max_dist = max((s.distance_km for s in stops), default=0.0)
    return HeritageTrailInfo(stops=len(stops), distance_km=max_dist, completed_stops=completed)


@app.post("/api/v1/heritage/trail/{stop_id}/complete", response_model=ActionResponse, tags=["Heritage"])
def complete_trail_stop(stop_id: str, db: DbSession):
    stop = db.query(TrailStop).filter(TrailStop.id == stop_id).first()
    if not stop:
        raise HTTPException(404, "Trail stop not found")
    if stop.completed:
        return ActionResponse(status="already_completed", message=f"“{stop.name}” was already marked complete")
    stop.completed = True
    db.commit()
    return ActionResponse(status="completed", message=f"Checked in at “{stop.name}”")


# ──────────────────────────────────────────────
# Feature 6 – Board Games
# ──────────────────────────────────────────────
@app.get("/api/v1/boardgames/stats", response_model=BoardGameHeroStats, tags=["Board Games"])
def get_boardgame_stats(db: DbSession):
    total_owned = db.query(func.sum(BoardGame.owned)).scalar() or 0
    return BoardGameHeroStats(members=68, games_owned=total_owned + 30, weekly_meetups=12)


@app.get("/api/v1/boardgames/games", response_model=List[GameOut], tags=["Board Games"])
def list_games(db: DbSession):
    rows = db.query(BoardGame).order_by(BoardGame.title).all()
    return [
        GameOut(
            id=g.id, emoji=g.emoji, type=g.game_type, title=g.title,
            players=g.players, duration=g.duration, difficulty=g.difficulty, owned=g.owned,
        )
        for g in rows
    ]


@app.post("/api/v1/boardgames/{game_id}/join", response_model=ActionResponse, tags=["Board Games"])
def join_game_night(game_id: str, db: DbSession):
    game = db.query(BoardGame).filter(BoardGame.id == game_id).first()
    if not game:
        raise HTTPException(404, "Game not found")
    game.join_count += 1
    db.commit()
    return ActionResponse(
        status="joined",
        message=f"You joined the next game night for “{game.title}”. {game.join_count} players signed up.",
    )


# ──────────────────────────────────────────────
# Feature 7 – Observatory
# ──────────────────────────────────────────────
@app.get("/api/v1/observatory/stats", response_model=ObservatoryStatsOut, tags=["Observatory"])
def get_observatory_stats():
    return ObservatoryStatsOut(
        club_members=42,
        stargazing_nights=18,
        photos_captured=284,
        telescopes_owned=8,
    )


@app.get("/api/v1/observatory/celestial", response_model=List[CelestialOut], tags=["Observatory"])
def list_celestial(db: DbSession):
    rows = db.query(CelestialBody).all()
    return [
        CelestialOut(
            id=c.id, emoji=c.emoji, type=c.body_type, name=c.name,
            meta=c.meta, visibility=c.visibility,
        )
        for c in rows
    ]


@app.get("/api/v1/observatory/next-event", tags=["Observatory"])
def next_stargazing():
    return {
        "event": "Mwarokin Stargazing Night",
        "date": "2025-05-05",
        "time": "20:00",
        "location": "Kilimani Court Rooftop",
        "bring": ["blanket", "binoculars (optional)"],
        "status": "open",
    }


# ──────────────────────────────────────────────
# System
# ──────────────────────────────────────────────
@app.get("/", tags=["System"])
def root():
    return {
        "service": "Mwarokin Estates Hobbies & Heritage API",
        "version": "1.0.0",
        "page": "Hobbies, Heritage & Hobbies (Page 18)",
        "docs": "/docs",
    }


@app.get("/health", tags=["System"])
def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
```

### Run it

```bash
pip install fastapi uvicorn sqlalchemy pydantic
uvicorn main:app --reload --host 0.0.0.0 --port 8018
```

### Real functionality map

| Feature              | Endpoints                                                                 | Real actions                          |
|----------------------|---------------------------------------------------------------------------|---------------------------------------|
| Photography          | `GET /stats`, `GET /gallery`, `POST /{id}/like`                           | Like photos, live counts              |
| Wildlife             | `GET /stats`, `GET /species`, `POST /{id}/sighting`                       | Log new sightings                     |
| Poetry               | `GET /poems`, `POST /{id}/like`, `GET /next-open-mic`                     | Like poems, next event                |
| Language Exchange    | `GET /stats`, `GET /exchanges`, `POST /{id}/start`                        | Start exchange (availability check)   |
| Heritage             | `GET /timeline`, `GET /trail`, `GET /trail/info`, `POST /trail/{id}/complete` | Check-in trail stops               |
| Board Games          | `GET /stats`, `GET /games`, `POST /{id}/join`                             | Join game night                       |
| Observatory          | `GET /stats`, `GET /celestial`, `GET /next-event`                         | Live celestial list + next event      |

All data is persisted in SQLite and seeded on first start. Interactive Swagger docs: `http://localhost:8018/docs`.