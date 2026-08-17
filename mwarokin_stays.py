```python
"""
Mwarokin Stays - Premium Backend API
Syllogism Technology Africa
Production-ready FastAPI backend for Nairobi short-term rentals.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from enum import Enum
from typing import List, Optional, Set

from fastapi import FastAPI, HTTPException, Query, Path, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from sqlalchemy.sql import func

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASE_URL = "sqlite:///./mwarokin_stays.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# SQLAlchemy Models
# ---------------------------------------------------------------------------

class PropertyDB(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    location = Column(String(100), nullable=False, index=True)
    price = Column(Integer, nullable=False)  # KSh per night
    rating = Column(Float, default=0.0)
    reviews = Column(Integer, default=0)
    image = Column(String(500))  # CSS gradient or image URL
    description = Column(Text)
    bedrooms = Column(Integer, default=0)
    beds = Column(Integer, default=1)
    bathrooms = Column(Integer, default=1)
    occupancy = Column(Integer, default=0)  # percentage
    amenities = Column(JSON, default=list)
    highlights = Column(JSON, default=list)
    bookings_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    bookings = relationship("BookingDB", back_populates="property")


class BookingDB(Base):
    __tablename__ = "bookings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    guest_name = Column(String(150), nullable=True)
    guest_email = Column(String(200), nullable=True)
    guest_phone = Column(String(30), nullable=True)
    check_in = Column(Date, nullable=False)
    check_out = Column(Date, nullable=False)
    guests = Column(Integer, default=1)
    nights = Column(Integer, nullable=False)
    subtotal = Column(Integer, nullable=False)
    platform_fee = Column(Integer, nullable=False)
    total = Column(Integer, nullable=False)
    status = Column(String(30), default="pending")  # pending | confirmed | cancelled | completed
    payment_method = Column(String(50), nullable=True)
    payment_reference = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    property = relationship("PropertyDB", back_populates="bookings")


class FavoriteDB(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("session_id", "property_id", name="uq_session_property"),)

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class SortBy(str, Enum):
    rating = "rating"
    price_low = "price-low"
    price_high = "price-high"
    occupancy = "occupancy"


class PropertyBase(BaseModel):
    name: str
    location: str
    price: int = Field(..., gt=0)
    rating: float = Field(0.0, ge=0.0, le=5.0)
    reviews: int = Field(0, ge=0)
    image: Optional[str] = None
    description: Optional[str] = None
    bedrooms: int = Field(0, ge=0)
    beds: int = Field(1, ge=1)
    bathrooms: int = Field(1, ge=1)
    occupancy: int = Field(0, ge=0, le=100)
    amenities: List[str] = []
    highlights: List[str] = []
    bookings_count: int = Field(0, ge=0)


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    price: Optional[int] = Field(None, gt=0)
    rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    reviews: Optional[int] = Field(None, ge=0)
    image: Optional[str] = None
    description: Optional[str] = None
    bedrooms: Optional[int] = Field(None, ge=0)
    beds: Optional[int] = Field(None, ge=1)
    bathrooms: Optional[int] = Field(None, ge=1)
    occupancy: Optional[int] = Field(None, ge=0, le=100)
    amenities: Optional[List[str]] = None
    highlights: Optional[List[str]] = None
    is_active: Optional[bool] = None


class PropertyOut(PropertyBase):
    id: int
    is_active: bool = True
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PropertyListResponse(BaseModel):
    total: int
    count: int
    properties: List[PropertyOut]


class BookingCreate(BaseModel):
    property_id: int
    check_in: date
    check_out: date
    guests: int = Field(1, ge=1, le=12)
    guest_name: Optional[str] = Field(None, max_length=150)
    guest_email: Optional[str] = Field(None, max_length=200)
    guest_phone: Optional[str] = Field(None, max_length=30)
    payment_method: Optional[str] = Field(
        None,
        description="M-Pesa | Airtel Money | Credit/Debit Card | SylloPay | Bank Transfer",
    )

    @model_validator(mode="after")
    def validate_dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        if self.check_in < date.today():
            raise ValueError("check_in cannot be in the past")
        nights = (self.check_out - self.check_in).days
        if nights > 90:
            raise ValueError("Maximum stay is 90 nights")
        return self


class BookingOut(BaseModel):
    id: str
    property_id: int
    property_name: Optional[str] = None
    property_location: Optional[str] = None
    check_in: date
    check_out: date
    guests: int
    nights: int
    subtotal: int
    platform_fee: int
    total: int
    status: str
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    guest_name: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BookingConfirm(BaseModel):
    payment_method: str
    payment_reference: Optional[str] = None


class FavoriteToggle(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=64)
    property_id: int


class FavoriteListResponse(BaseModel):
    session_id: str
    property_ids: List[int]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime


class MetricsResponse(BaseModel):
    total_properties: int
    active_properties: int
    total_bookings: int
    confirmed_bookings: int
    average_occupancy: float
    total_revenue_estimate: int


# ---------------------------------------------------------------------------
# Constants & Seed Data
# ---------------------------------------------------------------------------

PLATFORM_FEE_RATE = 0.15  # 15%

SEED_PROPERTIES = [
    {
        "name": "Westlands Luxury Studio",
        "location": "Westlands",
        "price": 8500,
        "rating": 4.9,
        "reviews": 127,
        "image": "linear-gradient(135deg, #1F4D3D 0%, #2A6B5C 100%)",
        "description": "Contemporary studio with premium finishes in the heart of Westlands business district. Perfect for business travelers with modern workspace and high-speed connectivity.",
        "bedrooms": 0,
        "beds": 1,
        "bathrooms": 1,
        "occupancy": 82,
        "amenities": ["WiFi", "TV", "Coffee Maker", "AC", "Security", "Workspace", "Smart Lock"],
        "highlights": [
            "Fast reliable internet (50Mbps)",
            "Business traveller favourite",
            "Walk to restaurants",
            "24hr security",
        ],
        "bookings_count": 24,
    },
    {
        "name": "Kilimani Executive 1-Bedroom",
        "location": "Kilimani",
        "price": 6200,
        "rating": 4.8,
        "reviews": 94,
        "image": "linear-gradient(135deg, #D4AF37 0%, #B8941C 100%)",
        "description": "Spacious 1-bedroom apartment with stunning city views. Perfect for families and professionals seeking comfort and style in a vibrant neighborhood.",
        "bedrooms": 1,
        "beds": 1,
        "bathrooms": 1,
        "occupancy": 71,
        "amenities": ["WiFi", "Full Kitchen", "Washing Machine", "Balcony", "AC", "Security", "Parking"],
        "highlights": [
            "City views",
            "Full kitchen",
            "Washer/dryer",
            "Tranquil setting",
            "Green neighborhood",
        ],
        "bookings_count": 19,
    },
    {
        "name": "Karen Garden Villa",
        "location": "Karen",
        "price": 12800,
        "rating": 4.95,
        "reviews": 156,
        "image": "linear-gradient(135deg, #1F4D3D 0%, #0F2B24 100%)",
        "description": "Exclusive villa with private garden, perfect for families seeking luxury and privacy. Ideal for extended stays and group gatherings with premium amenities.",
        "bedrooms": 2,
        "beds": 3,
        "bathrooms": 2,
        "occupancy": 68,
        "amenities": ["WiFi", "Full Kitchen", "Pool", "Garden", "Workspace", "Security", "Parking", "Entertainment"],
        "highlights": [
            "Private pool",
            "Garden setting",
            "Multiple bedrooms",
            "Secure compound",
            "Nature proximity",
        ],
        "bookings_count": 31,
    },
    {
        "name": "CBD Premium Two-Bedroom",
        "location": "CBD",
        "price": 7400,
        "rating": 4.7,
        "reviews": 82,
        "image": "linear-gradient(135deg, #2A6B5C 0%, #1F4D3D 100%)",
        "description": "Central downtown apartment with walkable access to offices and conference venues. Modern amenities in the heart of Nairobi's business district.",
        "bedrooms": 2,
        "beds": 2,
        "bathrooms": 1,
        "occupancy": 75,
        "amenities": ["WiFi", "Lift", "Security", "Parking", "AC", "Workspace", "Coffee Maker"],
        "highlights": [
            "City centre location",
            "Walking distance to offices",
            "Modern amenities",
            "Secure building",
            "Restaurant district",
        ],
        "bookings_count": 22,
    },
    {
        "name": "Lavington Boutique Apartment",
        "location": "Lavington",
        "price": 5800,
        "rating": 4.85,
        "reviews": 109,
        "image": "linear-gradient(135deg, #D4AF37 0%, #C49A2E 100%)",
        "description": "Charming 1-bedroom with modern touches in quiet residential area. Peaceful neighborhood perfect for relaxation with excellent local restaurants nearby.",
        "bedrooms": 1,
        "beds": 1,
        "bathrooms": 1,
        "occupancy": 79,
        "amenities": ["WiFi", "Kitchen", "AC", "Security", "Parking", "Workspace", "Balcony"],
        "highlights": [
            "Quiet neighbourhood",
            "Friendly hosts",
            "Safe area",
            "Local restaurants nearby",
            "Tree-lined streets",
        ],
        "bookings_count": 18,
    },
    {
        "name": "Parklands Family Home",
        "location": "Parklands",
        "price": 9200,
        "rating": 4.88,
        "reviews": 118,
        "image": "linear-gradient(135deg, #2A6B5C 0%, #1F4D3D 100%)",
        "description": "Spacious 3-bedroom home with full amenities for family gatherings and group stays. Multiple living areas and entertainment spaces.",
        "bedrooms": 3,
        "beds": 4,
        "bathrooms": 2,
        "occupancy": 73,
        "amenities": ["WiFi", "Full Kitchen", "Garden", "AC", "Security", "Parking", "Entertainment", "Workspace"],
        "highlights": [
            "Family-friendly",
            "Large open spaces",
            "Secure compound",
            "Great value",
            "Multiple TV areas",
        ],
        "bookings_count": 26,
    },
]


def seed_database(db: Session) -> None:
    if db.query(PropertyDB).count() > 0:
        return
    for item in SEED_PROPERTIES:
        prop = PropertyDB(**item)
        db.add(prop)
    db.commit()


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mwarokin Stays API",
    description="Premium short-term rental backend for Nairobi — Syllogism Technology Africa",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Syllogism Technology Africa",
        "url": "https://syllogism.africa",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Health & Meta
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health():
    return HealthResponse(
        status="ok",
        service="Mwarokin Stays API",
        version="1.0.0",
        timestamp=datetime.utcnow(),
    )


@app.get("/metrics", response_model=MetricsResponse, tags=["System"])
def metrics(db: Session = Depends(get_db)):
    total = db.query(PropertyDB).count()
    active = db.query(PropertyDB).filter(PropertyDB.is_active == True).count()
    bookings = db.query(BookingDB).count()
    confirmed = db.query(BookingDB).filter(BookingDB.status == "confirmed").count()
    avg_occ = db.query(func.avg(PropertyDB.occupancy)).scalar() or 0.0
    revenue = (
        db.query(func.sum(BookingDB.total))
        .filter(BookingDB.status.in_(["confirmed", "completed"]))
        .scalar()
        or 0
    )
    return MetricsResponse(
        total_properties=total,
        active_properties=active,
        total_bookings=bookings,
        confirmed_bookings=confirmed,
        average_occupancy=round(float(avg_occ), 1),
        total_revenue_estimate=int(revenue),
    )


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

@app.get(
    "/properties",
    response_model=PropertyListResponse,
    tags=["Properties"],
    summary="List & filter properties",
)
def list_properties(
    q: Optional[str] = Query(None, description="Search name or description"),
    location: Optional[str] = Query(None, description="Neighborhood filter"),
    min_price: int = Query(2000, ge=0),
    max_price: int = Query(50000, ge=0),
    amenities: Optional[List[str]] = Query(None, description="Required amenities"),
    sort_by: SortBy = Query(SortBy.rating),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(PropertyDB).filter(PropertyDB.is_active == True)

    if q:
        like = f"%{q}%"
        query = query.filter(
            (PropertyDB.name.ilike(like)) | (PropertyDB.description.ilike(like))
        )

    if location and location.lower() != "all":
        query = query.filter(PropertyDB.location == location)

    query = query.filter(
        PropertyDB.price >= min_price,
        PropertyDB.price <= max_price,
    )

    # Amenities filter (all must match)
    if amenities:
        for amenity in amenities:
            query = query.filter(PropertyDB.amenities.contains([amenity]))

    total = query.count()

    if sort_by == SortBy.rating:
        query = query.order_by(PropertyDB.rating.desc())
    elif sort_by == SortBy.price_low:
        query = query.order_by(PropertyDB.price.asc())
    elif sort_by == SortBy.price_high:
        query = query.order_by(PropertyDB.price.desc())
    elif sort_by == SortBy.occupancy:
        query = query.order_by(PropertyDB.occupancy.desc())

    results = query.offset(skip).limit(limit).all()

    return PropertyListResponse(
        total=total,
        count=len(results),
        properties=[PropertyOut.model_validate(p) for p in results],
    )


@app.get(
    "/properties/{property_id}",
    response_model=PropertyOut,
    tags=["Properties"],
)
def get_property(
    property_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
):
    prop = db.query(PropertyDB).filter(PropertyDB.id == property_id).first()
    if not prop or not prop.is_active:
        raise HTTPException(status_code=404, detail="Property not found")
    return PropertyOut.model_validate(prop)


@app.get("/locations", tags=["Properties"])
def list_locations(db: Session = Depends(get_db)):
    rows = (
        db.query(PropertyDB.location)
        .filter(PropertyDB.is_active == True)
        .distinct()
        .order_by(PropertyDB.location)
        .all()
    )
    return {"locations": ["all"] + [r[0] for r in rows]}


@app.get("/amenities", tags=["Properties"])
def list_amenities(db: Session = Depends(get_db)):
    props = db.query(PropertyDB.amenities).filter(PropertyDB.is_active == True).all()
    unique: Set[str] = set()
    for (am_list,) in props:
        if am_list:
            unique.update(am_list)
    return {"amenities": sorted(unique)}


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------

@app.post(
    "/bookings",
    response_model=BookingOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Bookings"],
    summary="Create a new booking",
)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)):
    prop = (
        db.query(PropertyDB)
        .filter(PropertyDB.id == payload.property_id, PropertyDB.is_active == True)
        .first()
    )
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    nights = (payload.check_out - payload.check_in).days
    subtotal = prop.price * nights
    platform_fee = round(subtotal * PLATFORM_FEE_RATE)
    total = subtotal + platform_fee

    booking = BookingDB(
        property_id=prop.id,
        check_in=payload.check_in,
        check_out=payload.check_out,
        guests=payload.guests,
        nights=nights,
        subtotal=subtotal,
        platform_fee=platform_fee,
        total=total,
        status="pending",
        guest_name=payload.guest_name,
        guest_email=payload.guest_email,
        guest_phone=payload.guest_phone,
        payment_method=payload.payment_method,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    return BookingOut(
        id=booking.id,
        property_id=booking.property_id,
        property_name=prop.name,
        property_location=prop.location,
        check_in=booking.check_in,
        check_out=booking.check_out,
        guests=booking.guests,
        nights=booking.nights,
        subtotal=booking.subtotal,
        platform_fee=booking.platform_fee,
        total=booking.total,
        status=booking.status,
        payment_method=booking.payment_method,
        payment_reference=booking.payment_reference,
        guest_name=booking.guest_name,
        created_at=booking.created_at,
    )


@app.get("/bookings/{booking_id}", response_model=BookingOut, tags=["Bookings"])
def get_booking(booking_id: str, db: Session = Depends(get_db)):
    booking = db.query(BookingDB).filter(BookingDB.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    prop = booking.property
    return BookingOut(
        id=booking.id,
        property_id=booking.property_id,
        property_name=prop.name if prop else None,
        property_location=prop.location if prop else None,
        check_in=booking.check_in,
        check_out=booking.check_out,
        guests=booking.guests,
        nights=booking.nights,
        subtotal=booking.subtotal,
        platform_fee=booking.platform_fee,
        total=booking.total,
        status=booking.status,
        payment_method=booking.payment_method,
        payment_reference=booking.payment_reference,
        guest_name=booking.guest_name,
        created_at=booking.created_at,
    )


@app.post(
    "/bookings/{booking_id}/confirm",
    response_model=BookingOut,
    tags=["Bookings"],
    summary="Confirm payment & finalize booking",
)
def confirm_booking(
    booking_id: str,
    payload: BookingConfirm,
    db: Session = Depends(get_db),
):
    booking = db.query(BookingDB).filter(BookingDB.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != "pending":
        raise HTTPException(status_code=400, detail=f"Booking is already {booking.status}")

    booking.status = "confirmed"
    booking.payment_method = payload.payment_method
    booking.payment_reference = payload.payment_reference or f"PAY-{uuid.uuid4().hex[:12].upper()}"
    booking.updated_at = datetime.utcnow()

    # Update property metrics
    prop = booking.property
    if prop:
        prop.bookings_count = (prop.bookings_count or 0) + 1

    db.commit()
    db.refresh(booking)

    return BookingOut(
        id=booking.id,
        property_id=booking.property_id,
        property_name=prop.name if prop else None,
        property_location=prop.location if prop else None,
        check_in=booking.check_in,
        check_out=booking.check_out,
        guests=booking.guests,
        nights=booking.nights,
        subtotal=booking.subtotal,
        platform_fee=booking.platform_fee,
        total=booking.total,
        status=booking.status,
        payment_method=booking.payment_method,
        payment_reference=booking.payment_reference,
        guest_name=booking.guest_name,
        created_at=booking.created_at,
    )


@app.post("/bookings/{booking_id}/cancel", response_model=BookingOut, tags=["Bookings"])
def cancel_booking(booking_id: str, db: Session = Depends(get_db)):
    booking = db.query(BookingDB).filter(BookingDB.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status in ("cancelled", "completed"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel a {booking.status} booking")

    booking.status = "cancelled"
    booking.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(booking)

    prop = booking.property
    return BookingOut(
        id=booking.id,
        property_id=booking.property_id,
        property_name=prop.name if prop else None,
        property_location=prop.location if prop else None,
        check_in=booking.check_in,
        check_out=booking.check_out,
        guests=booking.guests,
        nights=booking.nights,
        subtotal=booking.subtotal,
        platform_fee=booking.platform_fee,
        total=booking.total,
        status=booking.status,
        payment_method=booking.payment_method,
        payment_reference=booking.payment_reference,
        guest_name=booking.guest_name,
        created_at=booking.created_at,
    )


# ---------------------------------------------------------------------------
# Favorites (session-based, no full auth required)
# ---------------------------------------------------------------------------

@app.post("/favorites/toggle", tags=["Favorites"])
def toggle_favorite(payload: FavoriteToggle, db: Session = Depends(get_db)):
    prop = db.query(PropertyDB).filter(PropertyDB.id == payload.property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    existing = (
        db.query(FavoriteDB)
        .filter(
            FavoriteDB.session_id == payload.session_id,
            FavoriteDB.property_id == payload.property_id,
        )
        .first()
    )

    if existing:
        db.delete(existing)
        db.commit()
        return {"favorited": False, "property_id": payload.property_id}

    fav = FavoriteDB(session_id=payload.session_id, property_id=payload.property_id)
    db.add(fav)
    db.commit()
    return {"favorited": True, "property_id": payload.property_id}


@app.get(
    "/favorites/{session_id}",
    response_model=FavoriteListResponse,
    tags=["Favorites"],
)
def list_favorites(session_id: str, db: Session = Depends(get_db)):
    rows = (
        db.query(FavoriteDB.property_id)
        .filter(FavoriteDB.session_id == session_id)
        .all()
    )
    return FavoriteListResponse(
        session_id=session_id,
        property_ids=[r[0] for r in rows],
    )


# ---------------------------------------------------------------------------
# Admin / Internal (simple, protect in production)
# ---------------------------------------------------------------------------

@app.post(
    "/admin/properties",
    response_model=PropertyOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Admin"],
)
def create_property(payload: PropertyCreate, db: Session = Depends(get_db)):
    prop = PropertyDB(**payload.model_dump())
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return PropertyOut.model_validate(prop)


@app.patch(
    "/admin/properties/{property_id}",
    response_model=PropertyOut,
    tags=["Admin"],
)
def update_property(
    property_id: int,
    payload: PropertyUpdate,
    db: Session = Depends(get_db),
):
    prop = db.query(PropertyDB).filter(PropertyDB.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(prop, key, value)
    prop.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(prop)
    return PropertyOut.model_validate(prop)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
```

**How to run**

```bash
pip install fastapi uvicorn sqlalchemy pydantic
# Save the code as main.py
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Key endpoints matching the UI**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/properties` | Filtered list (search, location, price, amenities, sort) |
| `GET` | `/properties/{id}` | Property detail |
| `GET` | `/locations` | Neighborhood list |
| `GET` | `/amenities` | All available amenities |
| `POST` | `/bookings` | Create booking + calculate 15% fee |
| `POST` | `/bookings/{id}/confirm` | Confirm payment |
| `POST` | `/favorites/toggle` | Like / unlike |
| `GET` | `/favorites/{session_id}` | User favorites |
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Platform stats |

The seed data matches the six properties in your React UI exactly.