import asyncio
import sqlite3
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum
import hashlib
from pydantic import BaseModel, Field, ValidationError
from contextlib import asynccontextmanager

# Configure logging for audit trails
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(tenant_id)s | %(message)s',
    handlers=[logging.StreamHandler()]
)

# Mock external services
async def mock_geocode(address: str) -> Dict:
    return {"lat": 40.7128, "lon": -74.0060, "formatted_address": address}

async def mock_walkscore(lat: float, lon: float) -> int:
    return 85

async def mock_comps(address: str, radius_km: float) -> List[Dict]:
    return [
        {"address": "123 Nearby St", "price": 500000, "beds": 3, "baths": 2, "sqft": 2000, "sold_date": "2025-08-01"},
        {"address": "456 Close Ave", "price": 550000, "beds": 3, "baths": 2, "sqft": 2100, "sold_date": "2025-07-15"}
    ]

async def mock_amenities(address: str) -> Dict:
    return {"schools": 2, "transit": 3, "parks": 1}

# Enums for standardized fields
class PropertyType(Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    LAND = "land"

class ListingStatus(Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    REJECTED = "rejected"

# Pydantic models for I/O contracts
class ListingInput(BaseModel):
    tenant_id: str
    address: str
    property_type: str
    beds: int = Field(ge=0)
    baths: float = Field(ge=0)
    sqft: float = Field(ge=0)
    images: List[str] = []
    description: Optional[str] = None
    price: Optional[float] = None

class ListingReco(BaseModel):
    status: str
    warnings: List[str]
    normalized_fields: Dict[str, Any]
    media_report: Dict[str, Any]

class Valuation(BaseModel):
    range_low: float
    range_high: float
    comp_ids: List[str]
    confidence: float
    reasoning: str
    sources: List[str]

class Match(BaseModel):
    listing_id: str
    score: float
    explanation: str

class BuyerProfile(BaseModel):
    tenant_id: str
    preferences: Dict[str, Any]  # e.g., {"beds": 3, "max_price": 600000, "location": "downtown"}
    user_id: str

# Database setup (in-memory for demo)
@asynccontextmanager
async def get_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Utility for PII redaction
def redact_pii(text: str) -> str:
    # Simple regex-based PII redaction (extend with proper library in production)
    return text.replace(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED]')

# Audit logging
def log_audit(tenant_id: str, action: str, details: Dict):
    logging.info(f"{action} | Details: {json.dumps(details)}", extra={"tenant_id": tenant_id})

# Listing Agent
class ListingAgent:
    async def intake(self, payload: ListingInput) -> ListingReco:
        tenant_id = payload.tenant_id
        log_audit(tenant_id, "Listing.intake", {"address": redact_pii(payload.address)})

        # Validate property type
        try:
            property_type = PropertyType[payload.property_type.upper()].value
        except KeyError:
            return ListingReco(
                status=ListingStatus.REJECTED.value,
                warnings=["Invalid property type"],
                normalized_fields={},
                media_report={}
            )

        # Normalize and enrich
        geo_data = await mock_geocode(payload.address)
        walkscore = await mock_walkscore(geo_data["lat"], geo_data["lon"])
        amenities = await mock_amenities(payload.address)

        # Image QA (mock)
        media_report = {
            "image_count": len(payload.images),
            "issues": ["Low resolution detected"] if len(payload.images) > 0 else []
        }

        normalized = {
            "address": geo_data["formatted_address"],
            "property_type": property_type,
            "beds": payload.beds,
            "baths": payload.baths,
            "sqft": payload.sqft,
            "lat": geo_data["lat"],
            "lon": geo_data["lon"],
            "walkscore": walkscore,
            "amenities": amenities,
            "description": redact_pii(payload.description or "")
        }

        # Save to DB
        async with get_db() as db:
            listing_id = str(uuid.uuid4())
            db.execute("""
                CREATE TABLE IF NOT EXISTS listings (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT,
                    data TEXT,
                    status TEXT,
                    created_at TEXT
                )
            """)
            db.execute(
                "INSERT INTO listings (id, tenant_id, data, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (listing_id, tenant_id, json.dumps(normalized), ListingStatus.VALIDATED.value, datetime.utcnow().isoformat())
            )
            db.commit()

        return ListingReco(
            status=ListingStatus.VALIDATED.value,
            warnings=media_report["issues"],
            normalized_fields=normalized,
            media_report=media_report
        )

# Valuation Agent
class ValuationAgent:
    async def request(self, listing_id: Optional[str] = None, address: Optional[str] = None, tenant_id: str = "") -> Valuation:
        log_audit(tenant_id, "Valuation.request", {"listing_id": listing_id, "address": redact_pii(address or "")})

        if not listing_id and not address:
            raise ValueError("Either listing_id or address must be provided")

        # Fetch listing if ID provided
        listing_data = {}
        if listing_id:
            async with get_db() as db:
                cursor = db.execute("SELECT data FROM listings WHERE id = ? AND tenant_id = ?", (listing_id, tenant_id))
                row = cursor.fetchone()
                if row:
                    listing_data = json.loads(row["data"])
                else:
                    raise ValueError("Listing not found")

        target_address = address or listing_data.get("address", "")
        comps = await mock_comps(target_address, radius_km=5.0)

        # Simple valuation logic (extend with ML model in production)
        prices = [comp["price"] for comp in comps]
        avg_price = sum(prices) / len(prices) if prices else 0
        range_low = avg_price * 0.9
        range_high = avg_price * 1.1
        confidence = 0.85 if len(comps) > 1 else 0.6

        reasoning = f"Valuation based on {len(comps)} comparable properties within 5km. "
        reasoning += f"Average comp price: ${avg_price:,.2f}. Adjusted ±10% for market variability."

        return Valuation(
            range_low=range_low,
            range_high=range_high,
            comp_ids=[hashlib.md5(str(comp).encode()).hexdigest() for comp in comps],
            confidence=confidence,
            reasoning=reasoning,
            sources=["Mock Comps API"]
        )

# Pricing Agent
class PricingAgent:
    async def calculate_price(self, listing_id: str, tenant_id: str) -> Dict:
        log_audit(tenant_id, "Pricing.calculate", {"listing_id": listing_id})

        async with get_db() as db:
            cursor = db.execute("SELECT data FROM listings WHERE id = ? AND tenant_id = ?", (listing_id, tenant_id))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Listing not found")

        listing_data = json.loads(row["data"])
        valuation = await ValuationAgent().request(listing_id=listing_id, tenant_id=tenant_id)

        # Dynamic pricing logic (simplified)
        base_price = (valuation.range_low + valuation.range_high) / 2
        seasonal_adjustment = 1.05  # Mock seasonal trend
        final_price = base_price * seasonal_adjustment

        return {
            "listing_id": listing_id,
            "suggested_price": final_price,
            "reasoning": f"Base price from valuation (${base_price:,.2f}) adjusted by {seasonal_adjustment:.2%} for seasonal demand."
        }

# Matchmaking Agent
class MatchmakingAgent:
    async def request(self, profile: BuyerProfile) -> List[Match]:
        tenant_id = profile.tenant_id
        log_audit(tenant_id, "Matchmaking.request", {"user_id": profile.user_id})

        async with get_db() as db:
            cursor = db.execute("SELECT id, data FROM listings WHERE tenant_id = ?", (tenant_id,))
            listings = [{"id": row["id"], "data": json.loads(row["data"])} for row in cursor.fetchall()]

        matches = []
        for listing in listings:
            score = self._calculate_match_score(listing["data"], profile.preferences)
            if score > 0.5:  # Threshold for relevant matches
                explanation = self._explain_match(listing["data"], profile.preferences, score)
                matches.append(Match(
                    listing_id=listing["id"],
                    score=score,
                    explanation=explanation
                ))

        return sorted(matches, key=lambda x: x.score, reverse=True)[:5]  # Top 5 matches

    def _calculate_match_score(self, listing: Dict, preferences: Dict) -> float:
        score = 0.0
        max_score = 4.0  # For beds, baths, price, location

        if preferences.get("beds") and listing.get("beds") >= preferences["beds"]:
            score += 1.0
        if preferences.get("baths") and listing.get("baths") >= preferences["baths"]:
            score += 1.0
        if preferences.get("max_price") and listing.get("price", float("inf")) <= preferences["max_price"]:
            score += 1.0
        if preferences.get("location") and preferences["location"].lower() in listing.get("address", "").lower():
            score += 1.0

        return score / max_score

    def _explain_match(self, listing: Dict, preferences: Dict, score: float) -> str:
        reasons = []
        if preferences.get("beds") and listing.get("beds") >= preferences["beds"]:
            reasons.append(f"Matches desired {preferences['beds']} beds")
        if preferences.get("baths") and listing.get("baths") >= preferences["baths"]:
            reasons.append(f"Matches desired {preferences['baths']} baths")
        if preferences.get("max_price") and listing.get("price", float("inf")) <= preferences["max_price"]:
            reasons.append(f"Within budget of ${preferences['max_price']:,.2f}")
        if preferences.get("location") and preferences["location"].lower() in listing.get("address", "").lower():
            reasons.append(f"Located in preferred area: {preferences['location']}")
        return f"Score: {score:.2%}. Reasons: {', '.join(reasons)}."

# Example usage
async def main():
    listing_agent = ListingAgent()
    valuation_agent = ValuationAgent()
    pricing_agent = PricingAgent()
    matchmaking_agent = MatchmakingAgent()

    # Example listing intake
    listing_input = ListingInput(
        tenant_id="tenant_123",
        address="123 Estate Ave, Mwarokin",
        property_type="residential",
        beds=3,
        baths=2.5,
        sqft=2000,
        images=["img1.jpg", "img2.jpg"],
        description="Beautiful family home near downtown"
    )
    listing_reco = await listing_agent.intake(listing_input)
    print("Listing Result:", listing_reco.dict())

    # Example valuation
    valuation = await valuation_agent.request(address="123 Estate Ave, Mwarokin", tenant_id="tenant_123")
    print("Valuation Result:", valuation.dict())

    # Example pricing
    async with get_db() as db:
        cursor = db.execute("SELECT id FROM listings WHERE tenant_id = ?", ("tenant_123",))
        listing_id = cursor.fetchone()["id"]
    pricing_result = await pricing_agent.calculate_price(listing_id, "tenant_123")
    print("Pricing Result:", pricing_result)

    # Example matchmaking
    profile = BuyerProfile(
        tenant_id="tenant_123",
        user_id="user_456",
        preferences={"beds": 3, "baths": 2, "max_price": 600000, "location": "Mwarokin"}
    )
    matches = await matchmaking_agent.request(profile)
    print("Matches:", [m.dict() for m in matches])

if __name__ == "__main__":
    asyncio.run(main())