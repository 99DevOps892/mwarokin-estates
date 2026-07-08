import uuid
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import hashlib
from dataclasses import dataclass
from enum import Enum
import aiohttp
from geopy.geocoders import Nominatim
from sentence_transformers import SentenceTransformer
import numpy as np
from cryptography.fernet import Fernet

# Configure logging with tenant_id for auditability
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [Tenant: %(tenant_id)s] %(message)s')

# Enums for standardized property types and statuses
class PropertyType(Enum):
    BEACH_HOUSE = "beach_house"
    APARTMENT = "apartment"
    VILLA = "villa"
    OFFICE = "office"

class PropertyStatus(Enum):
    FOR_SALE = "for sale"
    FOR_RENT = "for rent"
    FOR_BUY = "for buy"

# Data classes for structured I/O
@dataclass
class Listing:
    id: str
    tenant_id: str
    type: PropertyType
    status: PropertyStatus
    address: str
    price: float
    features: Dict
    media: List[str]
    enriched_data: Dict
    created_at: datetime

@dataclass
class ListingReco:
    status: str
    warnings: List[str]
    normalized_fields: Dict
    media_report: Dict

@dataclass
class Valuation:
    listing_id: str
    range_low: float
    range_high: float
    comp_ids: List[str]
    confidence: float
    reasoning: str
    sources: List[str]

@dataclass
class Match:
    listing_id: str
    score: float
    explanation: str

# Mock database and external service connectors
class MockDB:
    def __init__(self):
        self.listings: Dict[str, Listing] = {}
        self.comps: Dict[str, Dict] = {}

    async def save_listing(self, listing: Listing):
        self.listings[listing.id] = listing

    async def get_listing(self, listing_id: str, tenant_id: str) -> Optional[Listing]:
        listing = self.listings.get(listing_id)
        if listing and listing.tenant_id == tenant_id:
            return listing
        return None

    async def get_comps(self, tenant_id: str, address: str, radius_km: float = 5.0) -> List[Dict]:
        # Mock comps data (replace with real API call or DB query)
        return [
            {"id": f"comp_{i}", "address": address, "price": 500000 + i * 10000, "features": {"sqft": 2000}}
            for i in range(3)
        ]

db = MockDB()

# Encryption for PII
class EncryptionService:
    def __init__(self):
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def encrypt(self, data: str) -> str:
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        return self.cipher.decrypt(encrypted.encode()).decode()

encryption_service = EncryptionService()

# ListingAgent for intake, normalization, and validation
class ListingAgent:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="mwarokin")
        self.logger = logging.getLogger(__name__)

    async def intake(self, payload: Dict, tenant_id: str, role: str = "user") -> ListingReco:
        """Ingest and validate a new beach house listing."""
        if not self._check_rbac(role, "listing.create", tenant_id):
            return ListingReco(status="error", warnings=["Unauthorized access"], normalized_fields={}, media_report={})

        try:
            # Validate required fields
            required = ["address", "price", "type", "status", "media"]
            missing = [field for field in required if field not in payload]
            if missing:
                return ListingReco(
                    status="error",
                    warnings=[f"Missing fields: {missing}"],
                    normalized_fields={},
                    media_report={}
                )

            # Normalize fields
            normalized = {
                "address": encryption_service.encrypt(payload["address"]),  # Encrypt PII
                "price": float(payload["price"]),
                "type": PropertyType(payload["type"].lower()).value,
                "status": PropertyStatus(payload["status"].lower()).value,
                "features": payload.get("features", {}),
                "media": payload.get("media", [])
            }

            # Validate media (e.g., check image formats)
            media_report = self._validate_media(normalized["media"])

            # Enrich listing with geocoding and external data
            enriched_data = await self._enrich_listing(normalized["address"], tenant_id)

            # Create and save listing
            listing_id = str(uuid.uuid4())
            listing = Listing(
                id=listing_id,
                tenant_id=tenant_id,
                type=PropertyType(normalized["type"]),
                status=PropertyStatus(normalized["status"]),
                address=normalized["address"],
                price=normalized["price"],
                features=normalized["features"],
                media=normalized["media"],
                enriched_data=enriched_data,
                created_at=datetime.now()
            )
            await db.save_listing(listing)

            self.logger.info(f"Listing created: {listing_id}", extra={"tenant_id": tenant_id})
            return ListingReco(
                status="success",
                warnings=[],
                normalized_fields=normalized,
                media_report=media_report
            )

        except Exception as e:
            self.logger.error(f"Error processing listing: {str(e)}", extra={"tenant_id": tenant_id})
            return ListingReco(status="error", warnings=[str(e)], normalized_fields={}, media_report={})

    def _check_rbac(self, role: str, action: str, tenant_id: str) -> bool:
        """Mock RBAC check (replace with real RBAC system)."""
        allowed_roles = {"admin": ["listing.create"], "user": ["listing.create"]}
        return action in allowed_roles.get(role, [])

    def _validate_media(self, media: List[str]) -> Dict:
        """Validate media URLs (mock implementation)."""
        valid_formats = [".jpg", ".png"]
        report = {"valid": [], "invalid": []}
        for url in media:
            if any(url.lower().endswith(fmt) for fmt in valid_formats):
                report["valid"].append(url)
            else:
                report["invalid"].append(url)
        return report

    async def _enrich_listing(self, address: str, tenant_id: str) -> Dict:
        """Enrich listing with geocoding and external data."""
        try:
            decrypted_address = encryption_service.decrypt(address)
            location = self.geolocator.geocode(decrypted_address)
            enriched = {
                "geocode": {"lat": location.latitude, "lon": location.longitude} if location else {},
                "walkscore": 85,  # Mock external API call
                "amenities": ["beach_access", "parking"],  # Mock data
                "energy_score": "B"  # Mock data
            }
            return enriched
        except Exception as e:
            self.logger.error(f"Error enriching listing: {str(e)}", extra={"tenant_id": tenant_id})
            return {}

# ValuationAgent for pricing and valuation
class ValuationAgent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def request(self, listing_id: Optional[str], address: Optional[str], tenant_id: str, role: str = "user") -> Valuation:
        """Generate valuation for a beach house using RAG and comps."""
        if not self._check_rbac(role, "valuation.request", tenant_id):
            return Valuation(
                listing_id=listing_id or "",
                range_low=0.0,
                range_high=0.0,
                comp_ids=[],
                confidence=0.0,
                reasoning="Unauthorized access",
                sources=[]
            )

        try:
            if listing_id:
                listing = await db.get_listing(listing_id, tenant_id)
                if not listing:
                    return Valuation(
                        listing_id=listing_id,
                        range_low=0.0,
                        range_high=0.0,
                        comp_ids=[],
                        confidence=0.0,
                        reasoning="Listing not found or access denied",
                        sources=[]
                    )
                address = encryption_service.decrypt(listing.address)

            # Fetch comparable sales (comps) using RAG
            comps = await db.get_comps(tenant_id, address)
            comp_prices = [comp["price"] for comp in comps]
            comp_ids = [comp["id"] for comp in comps]

            # Simple valuation logic (replace with ML model or AVM)
            if comp_prices:
                avg_price = sum(comp_prices) / len(comp_prices)
                range_low = avg_price * 0.9
                range_high = avg_price * 1.1
                confidence = 0.85
                reasoning = f"Valuation based on {len(comps)} comparable sales within 5km. Average comp price: ${avg_price:,.2f}."
            else:
                range_low, range_high = 0.0, 0.0
                confidence = 0.0
                reasoning = "No comparable sales found."

            sources = [f"Comp {comp['id']}: ${comp['price']:,.2f}" for comp in comps]
            self.logger.info(f"Valuation generated for {listing_id or address}", extra={"tenant_id": tenant_id})

            return Valuation(
                listing_id=listing_id or "",
                range_low=range_low,
                range_high=range_high,
                comp_ids=comp_ids,
                confidence=confidence,
                reasoning=reasoning,
                sources=sources
            )

        except Exception as e:
            self.logger.error(f"Error generating valuation: {str(e)}", extra={"tenant_id": tenant_id})
            return Valuation(
                listing_id=listing_id or "",
                range_low=0.0,
                range_high=0.0,
                comp_ids=[],
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
                sources=[]
            )

    def _check_rbac(self, role: str, action: str, tenant_id: str) -> bool:
        """Mock RBAC check."""
        allowed_roles = {"admin": ["valuation.request"], "user": ["valuation.request"]}
        return action in allowed_roles.get(role, [])

# MatchmakingAgent for buyer/tenant-to-property matching
class MatchmakingAgent:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.logger = logging.getLogger(__name__)

    async def request(self, profile: Dict, tenant_id: str, role: str = "user") -> List[Match]:
        """Match buyer/tenant profile to beach house listings."""
        if not self._check_rbac(role, "matchmaking.request", tenant_id):
            return []

        try:
            # Extract profile preferences
            preferences = {
                "type": profile.get("type", "beach_house"),
                "budget": float(profile.get("budget", float("inf"))),
                "location": profile.get("location", ""),
                "features": profile.get("features", {})
            }

            # Generate embedding for preferences
            pref_text = f"{preferences['type']} in {preferences['location']} with {json.dumps(preferences['features'])}"
            pref_embedding = self.model.encode(pref_text)

            matches = []
            for listing_id, listing in db.listings.items():
                if listing.tenant_id != tenant_id:
                    continue  # Enforce tenant isolation

                # Generate embedding for listing
                listing_text = f"{listing.type.value} in {encryption_service.decrypt(listing.address)} with {json.dumps(listing.features)}"
                listing_embedding = self.model.encode(listing_text)

                # Compute similarity
                similarity = float(np.dot(pref_embedding, listing_embedding) / (np.linalg.norm(pref_embedding) * np.linalg.norm(listing_embedding)))

                # Apply rules-based filtering
                if listing.price <= preferences["budget"] and listing.type.value == preferences["type"]:
                    explanation = f"Match score {similarity:.2f} based on type, location, and features similarity."
                    matches.append(Match(listing_id=listing_id, score=similarity, explanation=explanation))

            # Sort matches by score
            matches.sort(key=lambda x: x.score, reverse=True)
            self.logger.info(f"Generated {len(matches)} matches for profile", extra={"tenant_id": tenant_id})
            return matches[:5]  # Return top 5 matches

        except Exception as e:
            self.logger.error(f"Error generating matches: {str(e)}", extra={"tenant_id": tenant_id})
            return []

    def _check_rbac(self, role: str, action: str, tenant_id: str) -> bool:
        """Mock RBAC check."""
        allowed_roles = {"admin": ["matchmaking.request"], "user": ["matchmaking.request"]}
        return action in allowed_roles.get(role, [])

# Orchestrator for coordinating agents
class MwarokinOrchestrator:
    def __init__(self):
        self.listing_agent = ListingAgent()
        self.valuation_agent = ValuationAgent()
        self.matchmaking_agent = MatchmakingAgent()
        self.logger = logging.getLogger(__name__)

    async def process_listing(self, payload: Dict, tenant_id: str, role: str) -> ListingReco:
        """Orchestrate listing intake and validation."""
        self.logger.info(f"Processing listing for tenant {tenant_id}", extra={"tenant_id": tenant_id})
        reco = await self.listing_agent.intake(payload, tenant_id, role)
        if reco.status == "success":
            # Trigger valuation for new listing
            valuation = await self.valuation_agent.request(reco.normalized_fields.get("id"), None, tenant_id, role)
            self.logger.info(f"Valuation for listing: {valuation}", extra={"tenant_id": tenant_id})
        return reco

    async def match_properties(self, profile: Dict, tenant_id: str, role: str) -> List[Match]:
        """Orchestrate property matching."""
        self.logger.info(f"Matching properties for tenant {tenant_id}", extra={"tenant_id": tenant_id})
        matches = await self.matchmaking_agent.request(profile, tenant_id, role)
        return matches

# Example usage
async def main():
    orchestrator = MwarokinOrchestrator()

    # Example listing payload for a beach house
    listing_payload = {
        "address": "123 Beachfront Dr, Mombasa, Kenya",
        "price": 750000,
        "type": "beach_house",
        "status": "for sale",
        "media": ["http://example.com/beach_house1.jpg", "http://example.com/beach_house2.png"],
        "features": {"sqft": 2500, "bedrooms": 4, "bathrooms": 3, "beach_access": True}
    }
    tenant_id = "tenant_123"
    role = "user"

    # Process listing
    listing_reco = await orchestrator.process_listing(listing_payload, tenant_id, role)
    print("Listing Result:", json.dumps(asdict(listing_reco), indent=2, default=str))

    # Example buyer profile for matching
    buyer_profile = {
        "type": "beach_house",
        "budget": 800000,
        "location": "Mombasa, Kenya",
        "features": {"bedrooms": 4, "beach_access": True}
    }

    # Match properties
    matches = await orchestrator.match_properties(buyer_profile, tenant_id, role)
    print("Matches:", json.dumps([asdict(m) for m in matches], indent=2, default=str))

# Run the example
import asyncio
if __name__ == "__main__":
    asyncio.run(main())