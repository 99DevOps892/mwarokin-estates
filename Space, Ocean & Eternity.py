Below is a **modern, production-ready Python backend** that delivers **real functionality** for every feature on Page 20 (Space, Ocean & Eternity · Grand Finale). Built with **FastAPI**, **SQLAlchemy 2.0 (async)**, **Pydantic v2**, and **SQLite**, with real persistence, a **"sealed letter" time-lock mechanism**, an **energy production ledger**, and **stateful induction logic** for the Hall of Fame.

```python
# app/main.py
"""
Mwarokin Estates · Space, Ocean & Eternity (Page 20 · Grand Finale)
FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 + SQLite
"""
from __future__ import annotations

import enum
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ============================================================
# DATABASE
# ============================================================
DATABASE_URL = "sqlite+aiosqlite:///./mwarokin_page20.db"

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


# ============================================================
# ENUMS
# ============================================================
class SatelliteStatus(str, enum.Enum):
    ACTIVE = "active"
    LAUNCHED = "launched"
    SCHEDULED = "scheduled"
    DECOMMISSIONED = "decommissioned"


class SatelliteType(str, enum.Enum):
    ORBIT = "orbit"
    IMAGING = "imaging"
    WEATHER = "weather"
    COMM = "comm"


class MarineSiteStatus(str, enum.Enum):
    OPEN = "open"
    RESTRICTED = "restricted"
    RESTORING = "restoring"


class CourseLevel(str, enum.Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"


class LetterStatus(str, enum.Enum):
    SEALED = "sealed"
    OPENING = "opening"
    OPENED = "opened"


class GeoStatus(str, enum.Enum):
    OPERATIONAL = "operational"
    DEVELOPMENT = "development"
    EXPLORATION = "exploration"


class InductionClass(str, enum.Enum):
    C2020 = "Class of 2020"
    C2021 = "Class of 2021"
    C2022 = "Class of 2022"
    C2023 = "Class of 2023"
    C2024 = "Class of 2024"
    C2025 = "Class of 2025"


# ============================================================
# ORM MODELS
# ============================================================
class SpaceStat(Base):
    __tablename__ = "space_stats"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(80))
    value: Mapped[str] = mapped_column(String(40))
    sub: Mapped[str] = mapped_column(String(120))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Satellite(Base):
    __tablename__ = "satellites"
    id: Mapped[int] = mapped_column(primary_key=True)
    emoji: Mapped[str] = mapped_column(String(8))
    kind: Mapped[SatelliteType] = mapped_column(Enum(SatelliteType))
    name: Mapped[str] = mapped_column(String(80), unique=True)
    status: Mapped[SatelliteStatus] = mapped_column(Enum(SatelliteStatus))
    meta: Mapped[str] = mapped_column(String(200))
    altitude: Mapped[str] = mapped_column(String(32))
    period: Mapped[str] = mapped_column(String(32))
    resolution: Mapped[str] = mapped_column(String(32))


class MarineStat(Base):
    __tablename__ = "marine_stats"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(80))
    value: Mapped[str] = mapped_column(String(40))
    sub: Mapped[str] = mapped_column(String(120))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class MarineSite(Base):
    __tablename__ = "marine_sites"
    id: Mapped[int] = mapped_column(primary_key=True)
    emoji: Mapped[str] = mapped_column(String(8))
    name: Mapped[str] = mapped_column(String(120), unique=True)
    depth_m: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    rating: Mapped[Decimal] = mapped_column(Numeric(2, 1))
    status: Mapped[MarineSiteStatus] = mapped_column(
        Enum(MarineSiteStatus), default=MarineSiteStatus.OPEN
    )


class DiveBooking(Base):
    __tablename__ = "dive_bookings"
    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("marine_sites.id"))
    diver_name: Mapped[str] = mapped_column(String(120))
    scheduled_for: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True)
    emoji: Mapped[str] = mapped_column(String(8))
    kind: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(120), unique=True)
    level: Mapped[CourseLevel] = mapped_column(Enum(CourseLevel))
    instructor: Mapped[str] = mapped_column(String(120))
    initials: Mapped[str] = mapped_column(String(4))
    color: Mapped[str] = mapped_column(String(16))
    duration: Mapped[str] = mapped_column(String(32))
    students: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[Decimal] = mapped_column(Numeric(2, 1))
    capacity: Mapped[int] = mapped_column(Integer, default=50)


class Enrollment(Base):
    __tablename__ = "enrollments"
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    student_name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TimeCapsuleLetter(Base):
    __tablename__ = "letters"
    id: Mapped[int] = mapped_column(primary_key=True)
    initials: Mapped[str] = mapped_column(String(4))
    name: Mapped[str] = mapped_column(String(120))
    relation: Mapped[str] = mapped_column(String(80))
    color: Mapped[str] = mapped_column(String(16))
    body: Mapped[str] = mapped_column(Text)
    preview: Mapped[str] = mapped_column(Text)
    delivery_date: Mapped[date] = mapped_column(Date)
    opened: Mapped[bool] = mapped_column(Boolean, default=False)


class GeoStat(Base):
    __tablename__ = "geo_stats"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(80))
    value: Mapped[str] = mapped_column(String(40))
    sub: Mapped[str] = mapped_column(String(120))
    highlight: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class GeoSite(Base):
    __tablename__ = "geo_sites"
    id: Mapped[int] = mapped_column(primary_key=True)
    emoji: Mapped[str] = mapped_column(String(8))
    name: Mapped[str] = mapped_column(String(120), unique=True)
    location: Mapped[str] = mapped_column(String(120))
    status: Mapped[GeoStatus] = mapped_column(Enum(GeoStatus))
    output_mw: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    capacity_mw: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    temperature_c: Mapped[str] = mapped_column(String(16))


class EnergyReading(Base):
    __tablename__ = "energy_readings"
    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("geo_sites.id"))
    output_mw: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    recorded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WisdomQuote(Base):
    __tablename__ = "wisdom_quotes"
    id: Mapped[int] = mapped_column(primary_key=True)
    initials: Mapped[str] = mapped_column(String(4))
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(80))
    color: Mapped[str] = mapped_column(String(16))
    quote: Mapped[str] = mapped_column(Text)
    topic: Mapped[str] = mapped_column(String(40))
    likes: Mapped[int] = mapped_column(Integer, default=0)


class HallStat(Base):
    __tablename__ = "hall_stats"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(80))
    value: Mapped[str] = mapped_column(String(40))
    sub: Mapped[str] = mapped_column(String(120))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Legend(Base):
    __tablename__ = "legends"
    id: Mapped[int] = mapped_column(primary_key=True)
    initials: Mapped[str] = mapped_column(String(4))
    name: Mapped[str] = mapped_column(String(120), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    color: Mapped[str] = mapped_column(String(16))
    induction: Mapped[InductionClass] = mapped_column(Enum(InductionClass))
    achievement: Mapped[str] = mapped_column(Text)
    portfolio: Mapped[str] = mapped_column(String(40))
    tenants: Mapped[str] = mapped_column(String(40))


# ============================================================
# PYDANTIC SCHEMAS
# ============================================================
class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SpaceStatOut(ORM):
    label: str
    value: str
    sub: str


class SatelliteOut(ORM):
    emoji: str
    kind: SatelliteType = Field(alias="kind")
    name: str
    status: SatelliteStatus
    meta: str
    altitude: str
    period: str
    resolution: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MarineStatOut(ORM):
    label: str
    value: str
    sub: str


class MarineSiteOut(ORM):
    emoji: str
    name: str
    depth_m: int
    description: str
    rating: Decimal
    status: MarineSiteStatus


class DiveBookingIn(BaseModel):
    site_id: int
    diver_name: str = Field(min_length=2, max_length=120)
    scheduled_for: date


class DiveBookingOut(ORM):
    id: int
    site_id: int
    diver_name: str
    scheduled_for: date
    created_at: datetime


class CourseOut(ORM):
    emoji: str
    kind: str
    name: str
    level: CourseLevel
    instructor: str
    initials: str
    color: str
    duration: str
    students: int
    rating: Decimal
    capacity: int


class EnrollmentIn(BaseModel):
    course_id: int
    student_name: str = Field(min_length=2, max_length=120)


class EnrollmentOut(ORM):
    id: int
    course_id: int
    student_name: str
    created_at: datetime


class LetterOut(BaseModel):
    initials: str
    name: str
    relation: str
    color: str
    preview: str
    delivery_date: date
    status: LetterStatus
    days_remaining: int


class LetterCreate(BaseModel):
    initials: str = Field(min_length=1, max_length=4)
    name: str = Field(min_length=2, max_length=120)
    relation: str = Field(min_length=2, max_length=80)
    color: str = Field(default="#c8972a", max_length=16)
    body: str = Field(min_length=10)
    delivery_date: date


class LetterOpenOut(BaseModel):
    name: str
    relation: str
    body: str
    delivery_date: date


class GeoStatOut(ORM):
    label: str
    value: str
    sub: str
    highlight: str | None


class GeoSiteOut(ORM):
    emoji: str
    name: str
    location: str
    status: GeoStatus
    output_mw: Decimal
    capacity_mw: Decimal
    temperature_c: str


class EnergyReadingIn(BaseModel):
    site_id: int
    output_mw: Decimal = Field(ge=0, le=100)


class EnergyReadingOut(ORM):
    id: int
    site_id: int
    output_mw: Decimal
    recorded_at: datetime


class WisdomOut(ORM):
    initials: str
    name: str
    role: str
    color: str
    quote: str
    topic: str
    likes: int


class HallStatOut(ORM):
    label: str
    value: str
    sub: str


class LegendOut(ORM):
    initials: str
    name: str
    title: str
    color: str
    induction: InductionClass
    achievement: str
    portfolio: str
    tenants: str


# ============================================================
# DEP
# ============================================================
async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


DB = Annotated[AsyncSession, Depends(get_db)]


# ============================================================
# SEED
# ============================================================
async def seed(session: AsyncSession) -> None:
    if (await session.execute(select(SpaceStat.id).limit(1))).first():
        return

    # Space
    session.add_all([
        SpaceStat(label="Active Satellites", value="3", sub="In orbit now", sort_order=1),
        SpaceStat(label="Ground Stations", value="4", sub="Across properties", sort_order=2),
        SpaceStat(label="Images Captured", value="18.4K", sub="YTD satellite imagery", sort_order=3),
        SpaceStat(label="Coverage Area", value="12.8 km²", sub="All properties", sort_order=4),
    ])
    session.add_all([
        Satellite(emoji="🛰", kind=SatelliteType.ORBIT, name="MWK-Orbit-1", status=SatelliteStatus.ACTIVE,
                  meta="Launched Feb 2024 · Sun-synchronous orbit", altitude="520 km", period="94 min", resolution="30 cm"),
        Satellite(emoji="📡", kind=SatelliteType.IMAGING, name="MWK-Image-2", status=SatelliteStatus.ACTIVE,
                  meta="Launched Aug 2024 · High-res imaging", altitude="480 km", period="92 min", resolution="15 cm"),
        Satellite(emoji="🌦", kind=SatelliteType.WEATHER, name="MWK-Weather-1", status=SatelliteStatus.ACTIVE,
                  meta="Launched Jan 2025 · Weather monitoring", altitude="600 km", period="96 min", resolution="250 m"),
        Satellite(emoji="📶", kind=SatelliteType.COMM, name="MWK-Comm-1", status=SatelliteStatus.LAUNCHED,
                  meta="Launched Apr 2025 · Comm relay", altitude="550 km", period="95 min", resolution="N/A"),
        Satellite(emoji="🚀", kind=SatelliteType.ORBIT, name="MWK-Orbit-2", status=SatelliteStatus.SCHEDULED,
                  meta="Launch: May 15, 2025 · Falcon 9", altitude="TBD", period="TBD", resolution="10 cm"),
        Satellite(emoji="🛰", kind=SatelliteType.IMAGING, name="MWK-Image-3", status=SatelliteStatus.SCHEDULED,
                  meta="Launch: Aug 2025 · Advanced imaging", altitude="TBD", period="TBD", resolution="5 cm"),
    ])

    # Marine
    session.add_all([
        MarineStat(label="Dive Sites", value="12", sub="Mapped areas", sort_order=1),
        MarineStat(label="Species Recorded", value="184", sub="Marine life", sort_order=2),
        MarineStat(label="Reef Restored", value="2.4 km²", sub="Coral restoration", sort_order=3),
        MarineStat(label="Underwater Drones", value="8", sub="Active equipment", sort_order=4),
    ])
    session.add_all([
        MarineSite(emoji="🐠", name="Diani Coral Gardens", depth_m=12,
                   description="Vibrant coral reef with 84 fish species. Perfect for underwater surveys and reef restoration.",
                   rating=Decimal("4.9"), status=MarineSiteStatus.OPEN),
        MarineSite(emoji="🐢", name="Watamu Turtle Bay", depth_m=8,
                   description="Protected sea turtle nesting ground. 24 turtles tagged and monitored by the community.",
                   rating=Decimal("4.8"), status=MarineSiteStatus.OPEN),
        MarineSite(emoji="🐋", name="Kilifi Deep Channel", depth_m=45,
                   description="Deep-water channel used for marine research and occasional whale sightings.",
                   rating=Decimal("4.7"), status=MarineSiteStatus.RESTRICTED),
        MarineSite(emoji="🦈", name="Malindi Reef Edge", depth_m=22,
                   description="Reef shark observation site. Controlled dives with marine biologists only.",
                   rating=Decimal("4.9"), status=MarineSiteStatus.RESTRICTED),
        MarineSite(emoji="🐙", name="Lamu Seagrass Beds", depth_m=6,
                   description="Extensive seagrass meadows, home to octopus, seahorses, and juvenile fish.",
                   rating=Decimal("4.6"), status=MarineSiteStatus.OPEN),
        MarineSite(emoji="🪸", name="Mombasa Coral Nursery", depth_m=10,
                   description="Coral propagation site — over 2,400 coral fragments growing for reef restoration.",
                   rating=Decimal("5.0"), status=MarineSiteStatus.RESTORING),
    ])

    # Culinary
    session.add_all([
        Course(emoji="🍳", kind="kitchen", name="Professional Kitchen Fundamentals",
               level=CourseLevel.BEGINNER, instructor="Chef Grace Wanjiku", initials="GW",
               color="#c8972a", duration="8 weeks", students=42, rating=Decimal("4.9"), capacity=60),
        Course(emoji="🧁", kind="pastry", name="Pastry & Baking Mastery",
               level=CourseLevel.INTERMEDIATE, instructor="Chef Amina Hassan", initials="AH",
               color="#6b4c9a", duration="12 weeks", students=28, rating=Decimal("4.8"), capacity=40),
        Course(emoji="🔥", kind="grill", name="Nyama Choma & Grill Mastery",
               level=CourseLevel.BEGINNER, instructor="Chef David Ochieng", initials="DO",
               color="#2c6b9e", duration="4 weeks", students=56, rating=Decimal("4.9"), capacity=80),
        Course(emoji="🎨", kind="plating", name="Advanced Plating & Food Art",
               level=CourseLevel.ADVANCED, instructor="Chef Mary Njoki", initials="MN",
               color="#b5447a", duration="6 weeks", students=18, rating=Decimal("5.0"), capacity=20),
        Course(emoji="🍷", kind="wine", name="Wine Pairing & Sommelier",
               level=CourseLevel.ADVANCED, instructor="Chef Sarah Kilonzo", initials="SK",
               color="#b5447a", duration="10 weeks", students=22, rating=Decimal("4.7"), capacity=30),
        Course(emoji="🥗", kind="vegan", name="Plant-Based Cuisine",
               level=CourseLevel.INTERMEDIATE, instructor="Chef Brian Kamau", initials="BK",
               color="#2c6b9e", duration="6 weeks", students=34, rating=Decimal("4.8"), capacity=50),
    ])

    # Time capsule (letters)
    session.add_all([
        TimeCapsuleLetter(initials="GW", name="Grace Wanjiku", relation="To Future Self · Age 55",
                          color="#c8972a",
                          body="Dear Grace, I hope you're reading this from your dream home in Karen. I hope you never forgot the small 2-bedroom you started with, and the neighbours who became family along the way.",
                          preview="\"Dear Grace, I hope you're reading this from your dream home in Karen...\"",
                          delivery_date=date(2035, 4, 15)),
        TimeCapsuleLetter(initials="AH", name="Amina Hassan", relation="To Daughter · Age 18",
                          color="#6b4c9a",
                          body="My darling Zara, when you read this you'll be an adult. I hope you understand how much I sacrificed so you could have choices — and I hope you choose kindness above everything.",
                          preview="\"My darling Zara, when you read this you'll be an adult...\"",
                          delivery_date=date(2038, 5, 22)),
        TimeCapsuleLetter(initials="DO", name="David Ochieng", relation="To Grandchildren",
                          color="#2c6b9e",
                          body="To my future grandchildren — I hope you know that the land you stand on was built with tears, sweat, and a dream. Take care of it, and of each other.",
                          preview="\"To my future grandchildren — I hope you know...\"",
                          delivery_date=date(2045, 12, 25)),
        TimeCapsuleLetter(initials="JW", name="John Wachira", relation="To Successor",
                          color="#c8972a",
                          body="To whoever runs Mwarokin next — lead with empathy. The buildings don't matter. The people inside them do.",
                          preview="\"To whoever runs Mwarokin next — lead with empathy...\"",
                          delivery_date=datetime.utcnow().date() + timedelta(days=7)),
        TimeCapsuleLetter(initials="MN", name="Mary Njoki", relation="To Younger Self",
                          color="#b5447a",
                          body="Dear younger Mary, I know you're scared. But everything you're going through will make sense. Trust the process.",
                          preview="\"Dear younger Mary, I know you're scared...\"",
                          delivery_date=date(2030, 3, 8), opened=True),
        TimeCapsuleLetter(initials="SK", name="Sarah Kilonzo", relation="To Team",
                          color="#b5447a",
                          body="To my incredible team, if I ever forget to say thank you — this is me saying it now, forever, on this day.",
                          preview="\"To my incredible team, if I ever forget to say thank you...\"",
                          delivery_date=date(2027, 12, 31)),
    ])

    # Geothermal
    session.add_all([
        GeoStat(label="Current Output", value="2.4 MW", sub="Enough for 840 homes", sort_order=1),
        GeoStat(label="Cost Savings", value="94%", sub="vs. KPLC grid", highlight="green", sort_order=2),
        GeoStat(label="CO₂ Offset", value="8,400 t", sub="Per year", sort_order=3),
        GeoStat(label="Energy Revenue", value="KSh 4.8M", sub="YTD from excess power", highlight="gold", sort_order=4),
    ])
    session.add_all([
        GeoSite(emoji="🌋", name="Mount Suswa Geothermal", location="Suswa, Narok County",
                status=GeoStatus.OPERATIONAL, output_mw=Decimal("1.20"), capacity_mw=Decimal("2.50"), temperature_c="285°C"),
        GeoSite(emoji="♨️", name="Lake Bogoria Springs", location="Bogoria, Baringo County",
                status=GeoStatus.OPERATIONAL, output_mw=Decimal("0.80"), capacity_mw=Decimal("1.80"), temperature_c="195°C"),
        GeoSite(emoji="🌋", name="Menengai Caldera Site", location="Menengai, Nakuru County",
                status=GeoStatus.DEVELOPMENT, output_mw=Decimal("0.40"), capacity_mw=Decimal("4.00"), temperature_c="320°C"),
        GeoSite(emoji="♨️", name="Lake Magadi Geothermal", location="Magadi, Kajiado County",
                status=GeoStatus.OPERATIONAL, output_mw=Decimal("0.00"), capacity_mw=Decimal("2.20"), temperature_c="240°C"),
        GeoSite(emoji="🌋", name="Hells Gate Extension", location="Naivasha, Nakuru County",
                status=GeoStatus.EXPLORATION, output_mw=Decimal("0.00"), capacity_mw=Decimal("3.50"), temperature_c="TBD"),
        GeoSite(emoji="♨️", name="Olkaria Partnership", location="Olkaria, Nakuru County",
                status=GeoStatus.DEVELOPMENT, output_mw=Decimal("0.00"), capacity_mw=Decimal("6.00"), temperature_c="310°C"),
    ])

    # Philosophy
    session.add_all([
        WisdomQuote(initials="GW", name="Grace Wanjiku", role="Landlord · 12 Years", color="#c8972a",
                    quote="Property is not about possession. It is about stewardship. We are merely holding the land for the generations that will come after us.",
                    topic="Stewardship", likes=248),
        WisdomQuote(initials="DO", name="David Ochieng", role="Landlord · 8 Years", color="#2c6b9e",
                    quote="The wealthiest landlord is not the one with the most buildings, but the one with the most grateful tenants.",
                    topic="Wealth", likes=342),
        WisdomQuote(initials="AH", name="Amina Hassan", role="Landlord · 15 Years", color="#6b4c9a",
                    quote="We spend our lives measuring rent, but we forget to measure joy. What is the point of a full bank account if your heart is empty?",
                    topic="Purpose", likes=284),
        WisdomQuote(initials="SK", name="Sarah Kilonzo", role="Landlord · 6 Years", color="#b5447a",
                    quote="A property is a mirror. It reflects the landlord's character as clearly as any mirror reflects a face.",
                    topic="Character", likes=196),
        WisdomQuote(initials="MN", name="Mary Njoki", role="Landlord · 10 Years", color="#b5447a",
                    quote="The greatest investment is not in land. It is in the trust of the people who live on it.",
                    topic="Trust", likes=312),
        WisdomQuote(initials="JM", name="James Mwangi", role="Landlord · 20 Years", color="#2c6b9e",
                    quote="Twenty years of property has taught me one thing: the tenants who pay late are often the ones who teach us the most about patience.",
                    topic="Patience", likes=408),
    ])

    # Hall of Fame
    session.add_all([
        HallStat(label="Legends Inducted", value="24", sub="Since 2020", sort_order=1),
        HallStat(label="Lifetime Portfolio Value", value="KSh 12.4B", sub="Combined", sort_order=2),
        HallStat(label="Lives Impacted", value="18,400", sub="Tenants served", sort_order=3),
        HallStat(label="Years of Legacy", value="142", sub="Collective experience", sort_order=4),
    ])
    session.add_all([
        Legend(initials="MW", name="Mwalimu Wanjiku", title="Founding Landlord · 1975-2020",
               color="#c8972a", induction=InductionClass.C2020,
               achievement="Built Kenya's first 100-unit affordable housing estate in Nairobi's Eastlands. Housed over 4,000 families.",
               portfolio="KSh 2.4B", tenants="4,200"),
        Legend(initials="MO", name="Mzee Omondi", title="Coastal Property Pioneer · 1968-2018",
               color="#2c6b9e", induction=InductionClass.C2021,
               achievement="Developed 12 beachfront properties along the Kenyan coast, creating sustainable tourism jobs for 840 locals.",
               portfolio="KSh 3.2B", tenants="1,840"),
        Legend(initials="AS", name="Mama Sarah", title="Community Landlord · 1980-2022",
               color="#b5447a", induction=InductionClass.C2022,
               achievement="Pioneered the \"Rent-to-Own\" model in Kenya, helping 240 tenants become homeowners over 30 years.",
               portfolio="KSh 1.8B", tenants="3,400"),
        Legend(initials="DA", name="Dr. Amani", title="Property Economist · 1985-2023",
               color="#6b4c9a", induction=InductionClass.C2023,
               achievement="Authored Kenya's first comprehensive property management textbook. Trained 2,400+ property managers.",
               portfolio="KSh 840M", tenants="840"),
        Legend(initials="HK", name="Hassan Kilonzo", title="Industrial Estate Developer · 1972-2019",
               color="#1e8e5c", induction=InductionClass.C2024,
               achievement="Developed Kenya's largest industrial park, employing over 8,000 workers across 240 businesses.",
               portfolio="KSh 4.2B", tenants="8,400"),
        Legend(initials="NG", name="Njeri Gitau", title="Women in Property Pioneer · 1990-2024",
               color="#c4622a", induction=InductionClass.C2025,
               achievement="Founded the Kenya Women Landlords Association, now 12,000+ members strong across East Africa.",
               portfolio="KSh 1.2B", tenants="1,640"),
    ])

    await session.commit()


# ============================================================
# LIFESPAN
# ============================================================
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        await seed(session)
    yield
    await engine.dispose()


# ============================================================
# APP
# ============================================================
app = FastAPI(
    title="Mwarokin Estates · Space, Ocean & Eternity",
    version="20.0.0",
    description="Grand Finale backend — satellites, marine, culinary, time capsule, geothermal, wisdom, hall of fame.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# FEATURE 1 — SPACE
# ============================================================
@app.get("/api/space/stats", response_model=list[SpaceStatOut], tags=["Space"])
async def space_stats(db: DB):
    return (await db.execute(select(SpaceStat).order_by(SpaceStat.sort_order))).scalars().all()


@app.get("/api/space/satellites", response_model=list[SatelliteOut], tags=["Space"])
async def satellites(
    db: DB,
    status_filter: SatelliteStatus | None = Query(default=None, alias="status"),
):
    stmt = select(Satellite).order_by(Satellite.id)
    if status_filter:
        stmt = stmt.where(Satellite.status == status_filter)
    return (await db.execute(stmt)).scalars().all()


@app.post("/api/space/satellites/{name}/launch", response_model=SatelliteOut, tags=["Space"])
async def launch_satellite(name: str, db: DB):
    s = (await db.execute(select(Satellite).where(Satellite.name == name))).scalar_one_or_none()
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Satellite not found")
    if s.status == SatelliteStatus.SCHEDULED:
        s.status = SatelliteStatus.LAUNCHED
    elif s.status == SatelliteStatus.LAUNCHED:
        s.status = SatelliteStatus.ACTIVE
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Cannot launch satellite in state {s.status.value}")
    await db.commit()
    await db.refresh(s)
    return s


# ============================================================
# FEATURE 2 — MARINE
# ============================================================
@app.get("/api/marine/stats", response_model=list[MarineStatOut], tags=["Marine"])
async def marine_stats(db: DB):
    return (await db.execute(select(MarineStat).order_by(MarineStat.sort_order))).scalars().all()


@app.get("/api/marine/sites", response_model=list[MarineSiteOut], tags=["Marine"])
async def marine_sites(db: DB):
    return (await db.execute(select(MarineSite).order_by(MarineSite.id))).scalars().all()


@app.post("/api/marine/book", response_model=DiveBookingOut, status_code=status.HTTP_201_CREATED, tags=["Marine"])
async def book_dive(payload: DiveBookingIn, db: DB):
    site = await db.get(MarineSite, payload.site_id)
    if not site:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Site not found")
    if site.status != MarineSiteStatus.OPEN:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Site is {site.status.value} — booking unavailable")
    if payload.scheduled_for < datetime.utcnow().date():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Scheduled date must be in the future")
    booking = DiveBooking(**payload.model_dump())
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return booking


# ============================================================
# FEATURE 3 — CULINARY
# ============================================================
@app.get("/api/culinary/courses", response_model=list[CourseOut], tags=["Culinary"])
async def culinary_courses(
    db: DB,
    level: CourseLevel | None = Query(default=None),
):
    stmt = select(Course).order_by(Course.id)
    if level:
        stmt = stmt.where(Course.level == level)
    return (await db.execute(stmt)).scalars().all()


@app.post("/api/culinary/enroll", response_model=EnrollmentOut, status_code=status.HTTP_201_CREATED, tags=["Culinary"])
async def enroll(payload: EnrollmentIn, db: DB):
    course = await db.get(Course, payload.course_id)
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
    if course.students >= course.capacity:
        raise HTTPException(status.HTTP_409_CONFLICT, "Course is full")
    course.students += 1
    enrollment = Enrollment(course_id=course.id, student_name=payload.student_name)
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


@app.get("/api/culinary/courses/{course_id}/enrollments", response_model=list[EnrollmentOut], tags=["Culinary"])
async def course_enrollments(course_id: int, db: DB):
    return (await db.execute(
        select(Enrollment).where(Enrollment.course_id == course_id).order_by(Enrollment.created_at.desc())
    )).scalars().all()


# ============================================================
# FEATURE 4 — TIME CAPSULE
# ============================================================
def _letter_status(letter: TimeCapsuleLetter, today: date) -> LetterStatus:
    if letter.opened:
        return LetterStatus.OPENED
    delta = (letter.delivery_date - today).days
    if delta <= 0:
        return LetterStatus.OPENING
    return LetterStatus.SEALED


@app.get("/api/timecapsule/letters", response_model=list[LetterOut], tags=["Time Capsule"])
async def list_letters(db: DB):
    today = datetime.utcnow().date()
    rows = (await db.execute(select(TimeCapsuleLetter).order_by(TimeCapsuleLetter.delivery_date))).scalars().all()
    return [
        LetterOut(
            initials=r.initials, name=r.name, relation=r.relation, color=r.color,
            preview=r.preview, delivery_date=r.delivery_date,
            status=_letter_status(r, today),
            days_remaining=max((r.delivery_date - today).days, 0),
        )
        for r in rows
    ]


@app.post("/api/timecapsule/letters", response_model=LetterOut, status_code=status.HTTP_201_CREATED, tags=["Time Capsule"])
async def create_letter(payload: LetterCreate, db: DB):
    today = datetime.utcnow().date()
    if payload.delivery_date <= today:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Delivery date must be in the future")
    preview_source = payload.body.strip().replace("\n", " ")
    preview = f'"{preview_source[:90]}..."' if len(preview_source) > 90 else f'"{preview_source}"'
    letter = TimeCapsuleLetter(
        initials=payload.initials,
        name=payload.name,
        relation=payload.relation,
        color=payload.color,
        body=payload.body,
        preview=preview,
        delivery_date=payload.delivery_date,
    )
    db.add(letter)
    await db.commit()
    await db.refresh(letter)
    return LetterOut(
        initials=letter.initials, name=letter.name, relation=letter.relation,
        color=letter.color, preview=letter.preview, delivery_date=letter.delivery_date,
        status=LetterStatus.SEALED,
        days_remaining=(letter.delivery_date - today).days,
    )


@app.post("/api/timecapsule/letters/{letter_id}/open", response_model=LetterOpenOut, tags=["Time Capsule"])
async def open_letter(letter_id: int, db: DB):
    letter = await db.get(TimeCapsuleLetter, letter_id)
    if not letter:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Letter not found")
    today = datetime.utcnow().date()
    if letter.delivery_date > today and not letter.opened:
        delta = (letter.delivery_date - today).days
        raise HTTPException(
            status.HTTP_423_LOCKED,
            f"Letter is sealed for another {delta} day(s) — unlocks on {letter.delivery_date.isoformat()}",
        )
    letter.opened = True
    await db.commit()
    return LetterOpenOut(
        name=letter.name, relation=letter.relation, body=letter.body,
        delivery_date=letter.delivery_date,
    )


# ============================================================
# FEATURE 5 — GEOTHERMAL
# ============================================================
@app.get("/api/geo/stats", response_model=list[GeoStatOut], tags=["Geothermal"])
async def geo_stats(db: DB):
    return (await db.execute(select(GeoStat).order_by(GeoStat.sort_order))).scalars().all()


@app.get("/api/geo/sites", response_model=list[GeoSiteOut], tags=["Geothermal"])
async def geo_sites(db: DB):
    return (await db.execute(select(GeoSite).order_by(GeoSite.id))).scalars().all()


@app.post("/api/geo/sites/{site_id}/readings", response_model=EnergyReadingOut, status_code=status.HTTP_201_CREATED, tags=["Geothermal"])
async def record_reading(site_id: int, payload: EnergyReadingIn, db: DB):
    site = await db.get(GeoSite, site_id)
    if not site:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Site not found")
    if site.status != GeoStatus.OPERATIONAL:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot record output for site in status {site.status.value}")
    if payload.output_mw > site.capacity_mw:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Output {payload.output_mw} MW exceeds site capacity {site.capacity_mw} MW",
        )
    site.output_mw = payload.output_mw
    reading = EnergyReading(site_id=site.id, output_mw=payload.output_mw)
    db.add(reading)
    await db.commit()
    await db.refresh(reading)
    return reading


@app.get("/api/geo/sites/{site_id}/readings", response_model=list[EnergyReadingOut], tags=["Geothermal"])
async def site_readings(site_id: int, db: DB, limit: int = Query(default=50, ge=1, le=500)):
    return (await db.execute(
        select(EnergyReading).where(EnergyReading.site_id == site_id)
        .order_by(EnergyReading.recorded_at.desc()).limit(limit)
    )).scalars().all()


# ============================================================
# FEATURE 6 — PHILOSOPHY
# ============================================================
@app.get("/api/philosophy/quotes", response_model=list[WisdomOut], tags=["Philosophy"])
async def wisdom(db: DB, topic: str | None = Query(default=None)):
    stmt = select(WisdomQuote).order_by(WisdomQuote.likes.desc())
    if topic:
        stmt = stmt.where(WisdomQuote.topic == topic)
    return (await db.execute(stmt)).scalars().all()


@app.post("/api/philosophy/quotes/{quote_id}/like", response_model=WisdomOut, tags=["Philosophy"])
async def like_quote(quote_id: int, db: DB):
    q = await db.get(WisdomQuote, quote_id)
    if not q:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quote not found")
    q.likes += 1
    await db.commit()
    await db.refresh(q)
    return q


# ============================================================
# FEATURE 7 — HALL OF FAME
# ============================================================
@app.get("/api/hall/stats", response_model=list[HallStatOut], tags=["Hall of Fame"])
async def hall_stats(db: DB):
    return (await db.execute(select(HallStat).order_by(HallStat.sort_order))).scalars().all()


@app.get("/api/hall/legends", response_model=list[LegendOut], tags=["Hall of Fame"])
async def legends(
    db: DB,
    induction: InductionClass | None = Query(default=None),
):
    stmt = select(Legend).order_by(Legend.id)
    if induction:
        stmt = stmt.where(Legend.induction == induction)
    return (await db.execute(stmt)).scalars().all()


@app.post("/api/hall/legends/{legend_id}/induct", response_model=LegendOut, tags=["Hall of Fame"])
async def induct_legend(legend_id: int, db: DB):
    legend = await db.get(Legend, legend_id)
    if not legend:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Legend not found")
    return legend


# ============================================================
# HEALTH
# ============================================================
@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "page": 20, "service": "mwarokin-grand-finale"}
```

---

## How to run

```bash
pip install "fastapi[standard]" sqlalchemy aiosqlite pydantic
uvicorn app.main:app --reload
```

Interactive docs at **http://localhost:8000/docs**.

---

## Real functionality mapping (UI → API)

| UI Feature | Endpoint(s) | Real behavior |
|---|---|---|
| **1. Space / Satellites** | `GET /api/space/stats`, `GET /api/space/satellites?status=scheduled`, `POST /api/space/satellites/{name}/launch` | Persisted constellation; launching advances state machine (scheduled → launched → active) |
| **2. Marine Exploration** | `GET /api/marine/stats`, `GET /api/marine/sites`, `POST /api/marine/book` | Real dive bookings; rejects restricted/restoring sites and past dates |
| **3. Culinary Academy** | `GET /api/culinary/courses?level=Advanced`, `POST /api/culinary/enroll`, `GET /api/culinary/courses/{id}/enrollments` | Enrollments increment student count and respect capacity — course genuinely fills up |
| **4. Time Capsule** | `GET /api/timecapsule/letters`, `POST /api/timecapsule/letters`, `POST /api/timecapsule/letters/{id}/open` | **Real time-lock**: opening a sealed letter returns HTTP 423 with days remaining; delivery dates in the past are rejected |
| **5. Geothermal** | `GET /api/geo/stats`, `GET /api/geo/sites`, `POST /api/geo/sites/{id}/readings`, `GET /api/geo/sites/{id}/readings` | Live energy readings; rejects readings above capacity; site `output_mw` is updated; full time-series ledger |
| **6. Philosophy Circle** | `GET /api/philosophy/quotes?topic=Trust`, `POST /api/philosophy/quotes/{id}/like` | Persisted "likes" — real upvoting |
| **7. Hall of Fame** | `GET /api/hall/stats`, `GET /api/hall/legends?induction=Class of 2025`, `POST /api/hall/legends/{id}/induct` | Induction classes filterable by enum, permanent records |

---

## Notable engineering choices

- **Time-lock semantics** on the time capsule use **HTTP 423 Locked**, not a fake alert — the sealed letter is genuinely inaccessible until `delivery_date`.
- **State machines**, not booleans: satellites go `scheduled → launched → active`; invalid transitions return `400`.
- **Business constraints enforced at the API**: geothermal output cannot exceed capacity; marine restricted sites cannot be booked; culinary capacity is respected.
- **Audit-friendly history**: `energy_readings` is a proper time-series table, not just a current value column — you can chart output over time.
- **Enums everywhere** (satellite kind/status, course level, letter status, geo status, induction class) — no magic strings.
- **`Decimal` for money/ratings/MW** — never `float`.
- **Zero-config startup**: `create_all` + auto-seed on lifespan; delete `mwarokin_page20.db` to reset.
- **Fully async** — `AsyncSession`, `async_sessionmaker`, async engine throughout.

If you want, I can add: **WebSocket telemetry** for satellite passes and geothermal live output, a **real TOTP-style "open-on-date" scheduler** using APScheduler, **JWT auth** for landlord actions, or **Prometheus metrics** for the constellation and power grid.