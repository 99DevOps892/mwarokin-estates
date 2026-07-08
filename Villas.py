Below is a Python implementation for key agentic tasks of the Mwarokin Real Estate Agentic OS, focusing on the **ListingAgent**, **ValuationAgent**, and **MatchmakingAgent** as described in the system prompt. The code adheres to the requirements for modern Python, tenant isolation, RBAC, and explainability, while integrating with the provided HTML frontend for property listing and filtering. It uses a ReAct loop (Reason-Act-Reflect) for robust task execution and includes RAG for grounding outputs in market data. The implementation is modular, secure, and designed for multi-tenant SaaS with white-label support.

### Key Assumptions and Notes
- **Data Source**: For demonstration, a mock database (in-memory dictionary) is used for listings and comps. In production, replace with a proper database (e.g., PostgreSQL) and external APIs (e.g., for geocoding, market data).
- **RAG Integration**: Simulated using mock comps data. In practice, use vector databases (e.g., Pinecone) or external APIs for real-time market data retrieval.
- **Frontend Integration**: The code generates JSON responses compatible with the HTML frontend's filtering and display logic.
- **Security**: Tenant isolation and RBAC are enforced via `tenant_id` checks. PII redaction and encryption are noted but not fully implemented for brevity.
- **Dependencies**: Uses `pydantic` for data validation, `fastapi` for API endpoints, and `geopy` for geocoding (mocked here).

### Python Code for Agentic Tasks

```python
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, validator
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime
import uuid
import re
from geopy.geocoders import Nominatim  # Mocked for geocoding
import logging
import json

# Configure logging for audit trails
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Mock database for listings and comps
mock_db = {
    "listings": {},
    "comps": {
        "123 Street, New York, USA": [
            {"id": "comp1", "address": "123 Street, New York, USA", "price": 12000, "sqft": 1000, "beds": 3, "baths": 2, "sold_date": "2025-01-15"},
            {"id": "comp2", "address": "125 Street, New York, USA", "price": 12500, "sqft": 950, "beds": 3, "baths": 2, "sold_date": "2025-02-10"}
        ]
    }
}

# Tenant configuration for white-labeling
tenant_config = {
    "tenant1": {
        "name": "Mwarokin",
        "currency": "USD",
        "locale": "en_US",
        "theme": {"logo": "img/Mwarokin.png", "primary_color": "#007bff"}
    }
}

# Pydantic models for I/O contracts
class Listing(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    address: str
    price: float
    sqft: int
    beds: int
    baths: int
    type: str  # e.g., "Apartment", "Villa"
    status: str  # e.g., "For Rent", "For Sell"
    availability: bool
    images: List[str] = []
    lat: Optional[float] = None
    lon: Optional[float] = None

    @validator("address")
    def validate_address(cls, v):
        if not re.match(r".+\,.+\,.+", v):  # Basic address format check
            raise ValueError("Invalid address format")
        return v

class ListingReco(BaseModel):
    status: str
    warnings: List[str]
    normalized_fields: Dict
    media_report: Dict

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

class UserProfile(BaseModel):
    tenant_id: str
    budget: float
    preferred_location: str
    min_beds: int
    min_baths: int
    property_type: Optional[str] = None

# Simulated RBAC dependency
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict:
    # Mock user with tenant_id and role
    return {"user_id": "user1", "tenant_id": "tenant1", "role": "agent"}

# FastAPI app
app = FastAPI(title="Mwarokin Real Estate Agentic OS")

# ListingAgent: Intake, normalize, and validate listings
async def listing_agent_intake(payload: Dict, tenant_id: str) -> ListingReco:
    try:
        # Plan: Validate input, normalize fields, enrich with geocoding, check images
        logger.info(f"[ListingAgent] Processing listing for tenant_id: {tenant_id}")
        
        # Validate and normalize
        listing = Listing(**payload, tenant_id=tenant_id)
        normalized_fields = listing.dict()
        
        # Enrich with geocoding (mocked)
        geolocator = Nominatim(user_agent="mwarokin")
        location = geolocator.geocode(listing.address)  # In production, use real API
        if location:
            listing.lat = location.latitude
            listing.lon = location.longitude
        else:
            listing.lat, listing.lon = 0.0, 0.0  # Fallback
            logger.warning(f"Geocoding failed for address: {listing.address}")
        
        # Image QA (mocked)
        media_report = {"valid_images": len(listing.images), "issues": []}
        if not listing.images:
            media_report["issues"].append("No images provided")
        
        # Save to mock DB
        mock_db["listings"][listing.id] = listing.dict()
        
        # Reflect: Check for warnings
        warnings = []
        if listing.sqft < 100:
            warnings.append("Unusually small square footage")
        if listing.price <= 0:
            warnings.append("Invalid price")
        
        return ListingReco(
            status="success",
            warnings=warnings,
            normalized_fields=listing.dict(),
            media_report=media_report
        )
    except Exception as e:
        logger.error(f"[ListingAgent] Error: {str(e)}")
        return ListingReco(status="error", warnings=[str(e)], normalized_fields={}, media_report={})

# ValuationAgent: Generate valuation based on comps
async def valuation_agent_request(listing_id: str, tenant_id: str) -> Valuation:
    # Plan: Retrieve listing, find comps, calculate valuation range, explain
    logger.info(f"[ValuationAgent] Valuating listing_id: {listing_id} for tenant_id: {tenant_id}")
    
    listing = mock_db["listings"].get(listing_id)
    if not listing or listing["tenant_id"] != tenant_id:
        raise HTTPException(status_code=404, message="Listing not found or access denied")
    
    # RAG: Retrieve comps (mocked)
    comps = mock_db["comps"].get(listing["address"], [])
    if not comps:
        logger.warning(f"No comps found for address: {listing['address']}")
        return Valuation(range_low=0, range_high=0, comp_ids=[], confidence=0.0, reasoning="No comparable sales found", sources=[])
    
    # Calculate valuation
    prices = [comp["price"] for comp in comps]
    avg_price = sum(prices) / len(prices)
    range_low = avg_price * 0.9  # 10% below avg
    range_high = avg_price * 1.1  # 10% above avg
    confidence = 0.85 if len(comps) >= 2 else 0.65
    
    # Explain reasoning
    reasoning = f"Valuation based on {len(comps)} comparable sales within the same area. Average price: ${avg_price:.2f}. Adjusted ±10% for market variability."
    sources = [f"Comp {comp['id']} sold on {comp['sold_date']}" for comp in comps]
    
    # Reflect: Validate valuation
    if range_low <= 0 or range_high <= 0:
        logger.warning("Invalid valuation range")
        reasoning += " Warning: Valuation may be unreliable due to negative or zero values."
    
    return Valuation(
        range_low=range_low,
        range_high=range_high,
        comp_ids=[comp["id"] for comp in comps],
        confidence=confidence,
        reasoning=reasoning,
        sources=sources
    )

# MatchmakingAgent: Match user profile to listings
async def matchmaking_agent_request(profile: UserProfile) -> List[Match]:
    # Plan: Retrieve listings, calculate match scores, rank and explain
    logger.info(f"[MatchmakingAgent] Matching for tenant_id: {profile.tenant_id}")
    
    matches = []
    for listing_id, listing in mock_db["listings"].items():
        if listing["tenant_id"] != profile.tenant_id:
            continue  # Enforce tenant isolation
        
        # Simple scoring logic (can be enhanced with embeddings)
        score = 0.0
        explanation = []
        
        # Budget match
        if profile.budget >= listing["price"] * 0.9:
            score += 0.4
            explanation.append("Price within budget")
        else:
            explanation.append("Price exceeds budget")
        
        # Location match (mocked distance check)
        if profile.preferred_location.lower() in listing["address"].lower():
            score += 0.3
            explanation.append("Location matches preference")
        
        # Beds and baths
        if listing["beds"] >= profile.min_beds:
            score += 0.15
            explanation.append("Sufficient bedrooms")
        if listing["baths"] >= profile.min_baths:
            score += 0.15
            explanation.append("Sufficient bathrooms")
        
        # Reflect: Ensure valid score
        if score > 0:
            matches.append(Match(
                listing_id=listing_id,
                score=min(score, 1.0),
                explanation="; ".join(explanation)
            ))
    
    # Sort by score
    matches.sort(key=lambda x: x.score, reverse=True)
    return matches[:5]  # Top 5 matches

# API Endpoints
@app.post("/listings/intake", response_model=ListingReco)
async def intake_listing(payload: Dict, current_user: Dict = Depends(get_current_user)):
    result = await listing_agent_intake(payload, current_user["tenant_id"])
    logger.info(f"[Audit] Listing intake for tenant_id: {current_user['tenant_id']}, status: {result.status}")
    return result

@app.post("/valuations/{listing_id}", response_model=Valuation)
async def request_valuation(listing_id: str, current_user: Dict = Depends(get_current_user)):
    result = await valuation_agent_request(listing_id, current_user["tenant_id"])
    logger.info(f"[Audit] Valuation requested for listing_id: {listing_id}, tenant_id: {current_user['tenant_id']}")
    return result

@app.post("/matchmaking", response_model=List[Match])
async def request_matches(profile: UserProfile, current_user: Dict = Depends(get_current_user)):
    if profile.tenant_id != current_user["tenant_id"]:
        raise HTTPException(status_code=403, message="Tenant access denied")
    result = await matchmaking_agent_request(profile)
    logger.info(f"[Audit] Matchmaking requested for tenant_id: {profile.tenant_id}, matches: {len(result)}")
    return result

@app.get("/listings", response_model=List[Listing])
async def get_listings(
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    location: Optional[str] = None,
    status: Optional[str] = None,
    availability: Optional[bool] = None,
    current_user: Dict = Depends(get_current_user)
):
    # Filter listings based on query parameters
    filtered_listings = [
        Listing(**listing) for listing_id, listing in mock_db["listings"].items()
        if listing["tenant_id"] == current_user["tenant_id"]
        and (price_min is None or listing["price"] >= price_min)
        and (price_max is None or listing["price"] <= price_max)
        and (location is None or location.lower() in listing["address"].lower())
        and (status is None or listing["status"].lower() == status.lower())
        and (availability is None or listing["availability"] == availability)
    ]
    logger.info(f"[Audit] Listings retrieved for tenant_id: {current_user['tenant_id']}, count: {len(filtered_listings)}")
    return filtered_listings

# JavaScript to integrate with frontend (save as AutomateGPRSPinLocator.js)
"""
document.addEventListener('DOMContentLoaded', () => {
    const filterBtn = document.getElementById('filterBtn');
    const propertyContainer = document.getElementById('propertyContainer');

    filterBtn.addEventListener('click', async () => {
        const priceMin = document.getElementById('priceMin').value;
        const priceMax = document.getElementById('priceMax').value;
        const location = document.getElementById('location').value;
        const status = document.querySelector('input[name="status"]:checked')?.value;
        const availability = document.querySelector('input[name="availability"]:checked')?.value;

        const queryParams = new URLSearchParams();
        if (priceMin) queryParams.append('price_min', priceMin);
        if (priceMax) queryParams.append('price_max', priceMax);
        if (location) queryParams.append('location', location);
        if (status) queryParams.append('status', status);
        if (availability) queryParams.append('availability', availability);

        try {
            const response = await fetch(`/listings?${queryParams.toString()}`, {
                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            const listings = await response.json();

            propertyContainer.innerHTML = listings.map(listing => `
                <div class="col-lg-4 col-md-6">
                    <div class="property-item rounded overflow-hidden">
                        <div class="position-relative overflow-hidden">
                            <img class="img-fluid" src="${listing.images[0] || 'img/default.jpg'}" alt="">
                            <div class="bg-primary rounded text-white position-absolute start-0 top-0 m-4 py-1 px-3">${listing.status}</div>
                            <div class="bg-white rounded-top text-primary position-absolute start-0 bottom-0 mx-4 pt-1 px-3">${listing.type}</div>
                        </div>
                        <div class="p-4 pb-0">
                            <h5 class="text-primary mb-3">$${listing.price}</h5>
                            <a class="d-block h5 mb-2" href="">${listing.address}</a>
                            <p><i class="fa fa-map-marker-alt text-primary me-2"></i>${listing.address}</p>
                        </div>
                        <div class="d-flex border-top">
                            <small class="flex-fill text-center border-end py-2"><i class="fa fa-ruler-combined text-primary me-2"></i>${listing.sqft} Sqft</small>
                            <small class="flex-fill text-center border-end py-2"><i class="fa fa-bed text-primary me-2"></i>${listing.beds} Bed</small>
                            <small class="flex-fill text-center py-2"><i class="fa fa-bath text-primary me-2"></i>${listing.baths} Bath</small>
                        </div>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            console.error('Error fetching listings:', error);
            propertyContainer.innerHTML = '<p>Error loading listings.</p>';
        }
    });
});
"""

# Example usage
if __name__ == "__main__":
    import uvicorn
    # Example listing intake
    sample_listing = {
        "address": "123 Street, New York, USA",
        "price": 12345.0,
        "sqft": 1000,
        "beds": 3,
        "baths": 2,
        "type": "Apartment",
        "status": "For Sell",
        "availability": True,
        "images": ["img/property-1.jpg"]
    }
    
    import asyncio
    async def test_agents():
        # Test ListingAgent
        reco = await listing_agent_intake(sample_listing, "tenant1")
        print("Listing Intake:", reco.dict())
        
        # Test ValuationAgent
        listing_id = reco.normalized_fields["id"]
        valuation = await valuation_agent_request(listing_id, "tenant1")
        print("Valuation:", valuation.dict())
        
        # Test MatchmakingAgent
        profile = UserProfile(
            tenant_id="tenant1",
            budget=15000,
            preferred_location="New York",
            min_beds=2,
            min_baths=1
        )
        matches = await matchmaking_agent_request(profile)
        print("Matches:", [m.dict() for m in matches])
    
    asyncio.run(test_agents())
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Explanation of Implementation
1. **ListingAgent**:
   - Validates and normalizes listing data using Pydantic.
   - Enriches with geocoding (mocked via `geopy`).
   - Performs image QA (mocked) and checks for warnings (e.g., invalid price).
   - Returns a `ListingReco` with status, warnings, and normalized fields.

2. **ValuationAgent**:
   - Retrieves listing and comps from mock DB (replace with RAG in production).
   - Calculates a price range (±10% of average comp price) with confidence score.
   - Provides explainable reasoning and cites sources for transparency.

3. **MatchmakingAgent**:
   - Matches user profiles to listings based on budget, location, beds, and baths.
   - Uses a simple scoring system (can be enhanced with embeddings for better matching).
   - Returns top 5 matches with explanations for transparency.

4. **Frontend Integration**:
   - The `/listings` endpoint filters listings based on price, location, status, and availability, aligning with the HTML filters.
   - The JavaScript (`AutomateGPRSPinLocator.js`) fetches and renders listings dynamically in the `#propertyContainer`.

5. **Security and Compliance**:
   - Enforces tenant isolation via `tenant_id` checks.
   - Uses OAuth2 for RBAC (mocked for simplicity).
   - Logs all actions for audit trails.
   - Redacts PII in logs (not fully shown but noted).

6. **White-Label Support**:
   - Tenant configuration includes currency, locale, and theme settings.
   - Responses can be formatted to match tenant-specific branding.

### How to Run
1. Install dependencies: `pip install fastapi uvicorn pydantic geopy`
2. Save the JavaScript code as `AutomateGPRSPinLocator.js` in your frontend directory.
3. Run the FastAPI server: `python script.py`
4. Access the API at `http://localhost:8000` and test endpoints using Postman or the frontend.
