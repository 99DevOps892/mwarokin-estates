import sqlite3
import uuid
import json
from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, ValidationError
from cryptography.fernet import Fernet
import hashlib
import logging
from dataclasses import dataclass

# Configure logging for audit trails
logging.basicConfig(
    filename="mwarokin_audit.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Encryption setup
ENCRYPTION_KEY = Fernet.generate_key()
CIPHER = Fernet(ENCRYPTION_KEY)

# Mock external services
def mock_geocode(address: str) -> Dict:
    """Mock geocoding service."""
    return {"lat": 40.7128, "lon": -74.0060, "formatted_address": address}

def mock_comps(address: str, tenant_id: str) -> List[Dict]:
    """Mock comparable sales data."""
    return [
        {"address": "123 Nearby St", "price": 10000, "sqft": 1000, "sold_date": "2025-01-01"},
        {"address": "456 Nearby St", "price": 12000, "sqft": 1100, "sold_date": "2025-02-01"}
    ]

# Data Models
class Listing(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    address: str
    type: str = Field(regex="^(apartment|villa|office|building|home|shop|land)$")
    status: str = Field(regex="^(for sale|for rent|for buy)$")
    price: float
    sqft: int
    bedrooms: Optional[int]
    bathrooms: Optional[int]
    availability: bool = True
    images: List[str] = []
    geocode: Optional[Dict] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class Valuation(BaseModel):
    listing_id: str
    tenant_id: str
    range_low: float
    range_high: float
    confidence: float
    comps: List[Dict]
    reasoning: str
    sources: List[str]

class Match(BaseModel):
    listing_id: str
    score: float
    explanation: str

class User(BaseModel):
    id: str
    tenant_id: str
    role: str = Field(regex="^(admin|agent|client)$")
    preferences: Dict = {}

# Database Setup
def init_db():
    conn = sqlite3.connect("mwarokin.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id TEXT PRIMARY KEY,
            tenant_id TEXT,
            data TEXT, -- Encrypted JSON
            created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT,
            user_id TEXT,
            action TEXT,
            timestamp TEXT,
            details TEXT
        )
    """)
    conn.commit()
    conn.close()

# RBAC Middleware
def check_rbac(user: User, action: str, resource: str) -> bool:
    permissions = {
        "admin": ["create_listing", "view_all_listings", "valuate", "match"],
        "agent": ["create_listing", "view_own_listings", "match"],
        "client": ["view_listings", "match"]
    }
    allowed = action in permissions.get(user.role, [])
    logging.info(f"RBAC Check: user={user.id}, action={action}, resource={resource}, allowed={allowed}")
    return allowed

# PII Redaction
def redact_pii(data: Dict) -> Dict:
    pii_fields = ["address", "name", "email"]
    redacted = data.copy()
    for field in pii_fields:
        if field in redacted:
            redacted[field] = hashlib.sha256(redacted[field].encode()).hexdigest()[:10] + "..."
    return redacted

# Listing Agent
class ListingAgent:
    @staticmethod
    def intake(payload: Dict, tenant_id: str, user: User) -> Dict:
        if not check_rbac(user, "create_listing", "listing"):
            raise PermissionError("Unauthorized action")
        
        try:
            listing = Listing(**payload, tenant_id=tenant_id)
        except ValidationError as e:
            logging.error(f"Listing validation failed: {e}")
            return {"status": "error", "warnings": str(e), "normalized_fields": None, "media_report": None}

        # Enrich listing
        listing.geocode = mock_geocode(listing.address)
        listing.images = ListingAgent.validate_images(payload.get("images", []))

        # Encrypt and store
        encrypted_data = CIPHER.encrypt(json.dumps(listing.dict()).encode()).decode()
        conn = sqlite3.connect("mwarokin.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO listings (id, tenant_id, data, created_at) VALUES (?, ?, ?, ?)",
            (listing.id, tenant_id, encrypted_data, listing.created_at)
        )
        conn.commit()
        conn.close()

        # Log action
        logging.info(f"Listing created: id={listing.id}, tenant_id={tenant_id}, user_id={user.id}")

        return {
            "status": "success",
            "warnings": [],
            "normalized_fields": listing.dict(),
            "media_report": {"image_count": len(listing.images), "valid": True}
        }

    @staticmethod
    def validate_images(images: List[str]) -> List[str]:
        """Validate image URLs (mock)."""
        return [img for img in images if img.startswith("http")]

# Valuation Agent
class ValuationAgent:
    @staticmethod
    def request(listing_id: str, tenant_id: str, user: User) -> Valuation:
        if not check_rbac(user, "valuate", "listing"):
            raise PermissionError("Unauthorized action")

        conn = sqlite3.connect("mwarokin.db")
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM listings WHERE id = ? AND tenant_id = ?", (listing_id, tenant_id))
        result = cursor.fetchone()
        conn.close()

        if not result:
            raise ValueError("Listing not found")

        listing_data = json.loads(CIPHER.decrypt(result[0].encode()).decode())
        listing = Listing(**listing_data)

        # Fetch comps via RAG (mock)
        comps = mock_comps(listing.address, tenant_id)
        prices = [comp["price"] for comp in comps]
        avg_price = sum(prices) / len(prices) if prices else listing.price
        range_low = avg_price * 0.9
        range_high = avg_price * 1.1

        reasoning = f"Valuation based on {len(comps)} comparable sales within 1km. Average price: ${avg_price:.2f}."
        sources = [f"Comps feed: {comp['address']}" for comp in comps]

        valuation = Valuation(
            listing_id=listing_id,
            tenant_id=tenant_id,
            range_low=range_low,
            range_high=range_high,
            confidence=0.85,
            comps=comps,
            reasoning=reasoning,
            sources=sources
        )

        logging.info(f"Valuation generated: listing_id={listing_id}, tenant_id={tenant_id}, user_id={user.id}")
        return valuation

# Matchmaking Agent
class MatchmakingAgent:
    @staticmethod
    def request(profile: Dict, tenant_id: str, user: User) -> List[Match]:
        if not check_rbac(user, "match", "listing"):
            raise PermissionError("Unauthorized action")

        conn = sqlite3.connect("mwarokin.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, data FROM listings WHERE tenant_id = ?", (tenant_id,))
        results = cursor.fetchall()
        conn.close()

        matches = []
        for listing_id, encrypted_data in results:
            listing_data = json.loads(CIPHER.decrypt(encrypted_data.encode()).decode())
            listing = Listing(**listing_data)

            # Simple scoring based on preferences
            score = MatchmakingAgent.calculate_score(profile, listing)
            if score > 0.5:
                explanation = f"Match score {score:.2f} based on price, location, and type preferences."
                matches.append(Match(listing_id=listing_id, score=score, explanation=explanation))

        matches.sort(key=lambda x: x.score, reverse=True)
        logging.info(f"Matches generated: count={len(matches)}, tenant_id={tenant_id}, user_id={user.id}")
        return matches[:10]

    @staticmethod
    def calculate_score(profile: Dict, listing: Listing) -> float:
        """Simple scoring logic (extend with embeddings in production)."""
        score = 0.0
        if profile.get("max_price") and listing.price <= profile["max_price"]:
            score += 0.4
        if profile.get("type") and listing.type == profile["type"]:
            score += 0.3
        if profile.get("location") and profile["location"].lower() in listing.address.lower():
            score += 0.3
        return score

# API for Frontend Integration
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    # Mock user authentication
    return User(id="user123", tenant_id="tenant1", role="client", preferences={"max_price": 15000, "type": "apartment"})

@app.post("/listings")
async def create_listing(payload: Dict, tenant_id: str, user: User = Depends(get_current_user)):
    result = ListingAgent.intake(payload, tenant_id, user)
    return result

@app.get("/listings")
async def get_listings(
    tenant_id: str,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    location: Optional[str] = None,
    status: Optional[str] = None,
    availability: Optional[bool] = None,
    user: User = Depends(get_current_user)
):
    if not check_rbac(user, "view_listings", "listing"):
        raise HTTPException(status_code=403, message="Unauthorized")

    conn = sqlite3.connect("mwarokin.db")
    cursor = conn.cursor()
    query = "SELECT data FROM listings WHERE tenant_id = ?"
    params = [tenant_id]

    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    listings = []
    for encrypted_data in results:
        listing_data = json.loads(CIPHER.decrypt(encrypted_data[0].encode()).decode())
        listing = Listing(**listing_data)
        listings.append(listing)

    # Apply filters
    filtered = listings
    if price_min:
        filtered = [l for l in filtered if l.price >= price_min]
    if price_max:
        filtered = [l for l in filtered if l.price <= price_max]
    if location:
        filtered = [l for l in filtered if location.lower() in l.address.lower()]
    if status:
        filtered = [l for l in filtered if l.status == status]
    if availability is not None:
        filtered = [l for l in filtered if l.availability == availability]

    return [redact_pii(l.dict()) for l in filtered]

@app.post("/valuations")
async def get_valuation(listing_id: str, tenant_id: str, user: User = Depends(get_current_user)):
    valuation = ValuationAgent.request(listing_id, tenant_id, user)
    return redact_pii(valuation.dict())

@app.post("/matches")
async def get_matches(profile: Dict, tenant_id: str, user: User = Depends(get_current_user)):
    matches = MatchmakingAgent.request(profile, tenant_id, user)
    return [m.dict() for m in matches]

# Initialize DB
init_db()

# Example Usage
if __name__ == "__main__":
    import uvicorn

    # Sample listing payload
    sample_listing = {
        "address": "123 Street, New York, USA",
        "type": "apartment",
        "status": "for sale",
        "price": 12345.0,
        "sqft": 1000,
        "bedrooms": 3,
        "bathrooms": 2,
        "images": ["http://example.com/property-1.jpg"]
    }

    user = User(id="user123", tenant_id="tenant1", role="agent", preferences={})
    result = ListingAgent.intake(sample_listing, "tenant1", user)
    print(json.dumps(result, indent=2))

    valuation = ValuationAgent.request(result["normalized_fields"]["id"], "tenant1", user)
    print(json.dumps(valuation.dict(), indent=2))

    profile = {"max_price": 15000, "type": "apartment", "location": "New York"}
    matches = MatchmakingAgent.request(profile, "tenant1", user)
    print(json.dumps([m.dict() for m in matches], indent=2))

    # Run FastAPI server
    uvicorn.run(app, host="0.0.0.0", port=8000)

    from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])