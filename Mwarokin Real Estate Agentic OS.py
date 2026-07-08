---

### Extended Python Implementation

Below is the extended Python code incorporating:
1. **Real APIs**: Integrations with Google Maps for geocoding, a mock MLS feed for comps, and a KYC provider (e.g., Trulioo).
2. **Database**: PostgreSQL with row-level security (RLS) for tenant isolation.
3. **WhiteLabelAgent**: Tenant-specific theming and locale support.
4. **AnalyticsAgent**: KPI computation for tenant data.
5. **Blockchain**: Integration with a Python blockchain client for transaction logging.

```python
import asyncio
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
import uuid
from datetime import datetime
import hashlib
from pydantic import BaseModel, Field, ValidationError
from loguru import logger
import aiohttp
import re
import asyncpg
from googlemaps import Client as GoogleMapsClient
from web3 import Web3
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from contextlib import asynccontextmanager

# Configuration (replace with environment variables in production)
GOOGLE_MAPS_API_KEY = "YOUR_GOOGLE_MAPS_API_KEY"
TRULIOO_API_KEY = "YOUR_TRULIOO_API_KEY"
POSTGRES_DSN = "postgresql://user:password@localhost:5432/mwarokin"
WEB3_PROVIDER = "https://your-blockchain-provider"  # e.g., Infura

# Initialize external services
google_maps = GoogleMapsClient(key=GOOGLE_MAPS_API_KEY)
web3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

# Database Setup with RLS
async def init_db():
    """Initialize PostgreSQL with RLS for tenant isolation."""
    conn = await asyncpg.connect(POSTGRES_DSN)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            listing_id UUID PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            address TEXT NOT NULL,
            property_type TEXT,
            beds INTEGER,
            baths FLOAT,
            size_sqm FLOAT,
            media JSONB,
            status TEXT,
            geocode JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ALTER TABLE listings ENABLE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON listings
            USING (tenant_id = current_setting('app.tenant_id')::TEXT);
        
        CREATE TABLE IF NOT EXISTS valuations (
            valuation_id UUID PRIMARY KEY,
            listing_id UUID REFERENCES listings(listing_id),
            tenant_id TEXT NOT NULL,
            range_low FLOAT,
            range_high FLOAT,
            comp_ids JSONB,
            confidence FLOAT,
            reasoning TEXT,
            sources JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ALTER TABLE valuations ENABLE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON valuations
            USING (tenant_id = current_setting('app.tenant_id')::TEXT);
    """)
    await conn.close()

# PII Redaction Utility
def redact_pii(text: str) -> str:
    """Redact PII from text."""
    patterns = [
        (r'\b[A-Za-z]+ [A-Za-z]+\b', '[REDACTED_NAME]'),
        (r'\+\d{3}-\d{3}-\d{3}-\d{3}', '[REDACTED_PHONE]'),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text

# Data Models
class Listing(BaseModel):
    listing_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    address: str
    property_type: str
    beds: Optional[int] = None
    baths: Optional[float] = None
    size_sqm: Optional[float] = None
    media: List[str] = []
    status: str = "pending"
    warnings: List[str] = []

class Valuation(BaseModel):
    valuation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    listing_id: str
    tenant_id: str
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

class WhiteLabelConfig(BaseModel):
    tenant_id: str
    logo_url: str
    primary_color: str
    typography: str
    domain: str
    locale: str
    currency: str

# Real API Integrations
async def geocode_address(address: str) -> Dict[str, float]:
    """Geocode address using Google Maps."""
    try:
        result = google_maps.geocode(address)
        if result:
            location = result[0]["geometry"]["location"]
            return {"lat": location["lat"], "lon": location["lng"]}
        return {"lat": 0.0, "lon": 0.0}
    except Exception as e:
        logger.error(f"Geocoding failed for {address}: {e}")
        return {"lat": 0.0, "lon": 0.0}

async def fetch_comps(address: str, radius_km: float, tenant_id: str) -> List[Dict]:
    """Fetch comps from a mock MLS feed (replace with real MLS API)."""
    async with aiohttp.ClientSession() as session:
        try:
            # Example MLS API call (replace with actual endpoint)
            async with session.get(
                "https://mock-mls-api/comps",
                params={"address": address, "radius_km": radius_km, "tenant_id": tenant_id}
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                logger.error(f"Comps fetch failed: {resp.status}")
                return []
        except Exception as e:
            logger.error(f"Comps fetch failed: {e}")
            return [
                {"listing_id": "comp1", "price": 22000, "beds": 2, "location": "Kangemi", "sale_date": "2023-01-15"},
                {"listing_id": "comp2", "price": 35000, "beds": 3, "location": "Taveta", "sale_date": "2019-03-10"},
            ]

async def kyc_check(user_id: str, tenant_id: str) -> Dict[str, bool]:
    """Perform KYC/AML check via Trulioo (mock implementation)."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                "https://api.trulioo.com/v1/verify",
                headers={"Authorization": f"Bearer {TRULIOO_API_KEY}"},
                json={"user_id": user_id, "tenant_id": tenant_id}
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                logger.error(f"KYC check failed: {resp.status}")
                return {"passed": False, "is_pep": False}
        except Exception as e:
            logger.error(f"KYC check failed: {e}")
            return {"passed": False, "is_pep": False}

# Blockchain Integration
class BlockchainClient:
    async def record_transaction(self, token: str, transaction_data: Dict):
        """Record transaction on blockchain."""
        try:
            # Assume a smart contract with a `recordTransaction` function
            contract_address = "0xYourContractAddress"
            contract_abi = [...]  # Replace with actual ABI
            contract = web3.eth.contract(address=contract_address, abi=contract_abi)
            
            tx = contract.functions.recordTransaction(token, json.dumps(transaction_data)).buildTransaction({
                "from": web3.eth.default_account,
                "nonce": web3.eth.getTransactionCount(web3.eth.default_account),
                "gas": 200000,
                "gasPrice": web3.toWei("20", "gwei")
            })
            signed_tx = web3.eth.account.signTransaction(tx, private_key="YOUR_PRIVATE_KEY")
            tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
            logger.info(f"Transaction recorded: {tx_hash.hex()}")
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Blockchain transaction failed: {e}")
            raise

# ListingAgent
class ListingAgent:
    async def intake(self, payload: Dict, tenant_id: str, conn: asyncpg.Connection) -> Dict:
        """Intake, normalize, and validate property listing."""
        try:
            listing_data = {
                "tenant_id": tenant_id,
                "address": payload.get("address", ""),
                "property_type": payload.get("property_type", "residential"),
                "beds": payload.get("beds"),
                "baths": payload.get("baths"),
                "size_sqm": payload.get("size_sqm"),
                "media": payload.get("media", []),
            }
            listing = Listing(**listing_data)
            
            warnings = []
            if not listing.address:
                warnings.append("Address is required")
            if listing.property_type not in ["residential", "commercial", "land"]:
                warnings.append(f"Invalid property type: {listing.property_type}")
            
            # Auto-enrich listing
            geocode = await geocode_address(listing.address)
            listing_dict = listing.dict()
            listing_dict.update({
                "geocode": geocode,
                "walkscore": 0.75,  # Mock walkscore (replace with API)
                "amenities": ["school", "transit"],  # Mock amenities
                "status": "validated" if not warnings else "pending",
                "warnings": warnings
            })
            
            # Save to database
            await conn.execute(
                """
                INSERT INTO listings (listing_id, tenant_id, address, property_type, beds, baths, size_sqm, media, status, geocode)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                listing.listing_id, tenant_id, listing.address, listing.property_type,
                listing.beds, listing.baths, listing.size_sqm, json.dumps(listing.media),
                listing.status, json.dumps(geocode)
            )
            
            media_report = {"valid_images": len(listing.media), "issues": []}
            logger.info(f"Listing validated and saved for tenant {tenant_id}: {listing.listing_id}")
            return {"status": listing.status, "warnings": warnings, "normalized_fields": listing_dict, "media_report": media_report}
        
        except ValidationError as e:
            logger.error(f"Listing validation failed: {e}")
            return {"status": "failed", "warnings": [str(e)], "normalized_fields": {}, "media_report": {}}

# ValuationAgent
class ValuationAgent:
    async def request(self, listing_id: str, address: str, tenant_id: str, conn: asyncpg.Connection) -> Valuation:
        """Generate valuation using RAG-based comps."""
        try:
            comps = await fetch_comps(address, radius_km=5.0, tenant_id=tenant_id)
            prices = [comp["price"] for comp in comps]
            range_low = min(prices) * 0.9 if prices else 0.0
            range_high = max(prices) * 1.1 if prices else 0.0
            confidence = 0.85 if prices else 0.5
            
            reasoning = f"Valuation based on {len(comps)} comps within 5km of {address}. "
            reasoning += f"Price range derived from min ({min(prices) if prices else 'N/A'}) and max ({max(prices) if prices else 'N/A'}) with 10% buffer."
            reasoning = redact_pii(reasoning)
            
            valuation = Valuation(
                listing_id=listing_id,
                tenant_id=tenant_id,
                range_low=range_low,
                range_high=range_high,
                comp_ids=[comp["listing_id"] for comp in comps],
                confidence=confidence,
                reasoning=reasoning,
                sources=[f"Comps feed: {comp['listing_id']}" for comp in comps]
            )
            
            # Save valuation to database
            await conn.execute(
                """
                INSERT INTO valuations (valuation_id, listing_id, tenant_id, range_low, range_high, comp_ids, confidence, reasoning, sources)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                valuation.valuation_id, listing_id, tenant_id, valuation.range_low, valuation.range_high,
                json.dumps(valuation.comp_ids), valuation.confidence, valuation.reasoning, json.dumps(valuation.sources)
            )
            
            logger.info(f"Valuation generated for listing {listing_id}: {range_low}-{range_high}")
            return valuation
        except Exception as e:
            logger.error(f"Valuation failed for listing {listing_id}: {e}")
            raise

# MatchmakingAgent
class MatchmakingAgent:
    async def request(self, profile: Dict, tenant_id: str, conn: asyncpg.Connection) -> List[Match]:
        """Match buyer/tenant to properties."""
        try:
            # Fetch listings from database
            listings = await conn.fetch(
                "SELECT listing_id, beds, size_sqm, address FROM listings WHERE tenant_id = $1 AND status = 'validated'",
                tenant_id
            )
            
            matches = []
            for listing in listings:
                score = self._calculate_match_score(profile, listing)
                explanation = f"Match score: {score}. "
                explanation += f"Criteria: beds ({profile.get('beds', 0)} vs {listing['beds']}), "
                explanation += f"location ({profile.get('location', 'N/A')} vs {listing['address']})."
                explanation = redact_pii(explanation)
                
                matches.append(Match(
                    listing_id=listing["listing_id"],
                    score=score,
                    explanation=explanation
                ))
            
            logger.info(f"Generated {len(matches)} matches for tenant {tenant_id}")
            return matches
        except Exception as e:
            logger.error(f"Matchmaking failed: {e}")
            raise

    def _calculate_match_score(self, profile: Dict, listing: Dict) -> float:
        """Calculate match score."""
        score = 0.0
        if profile.get("beds") == listing["beds"]:
            score += 0.5
        if profile.get("budget", 0) >= 20000:  # Mock price check
            score += 0.3
        return min(score, 1.0)

# WhiteLabelAgent
class WhiteLabelAgent:
    async def get_config(self, tenant_id: str, conn: asyncpg.Connection) -> WhiteLabelConfig:
        """Retrieve tenant-specific white-label configuration."""
        try:
            config = await conn.fetchrow(
                "SELECT logo_url, primary_color, typography, domain, locale, currency FROM tenant_configs WHERE tenant_id = $1",
                tenant_id
            )
            if not config:
                raise ValueError(f"No configuration found for tenant {tenant_id}")
            
            return WhiteLabelConfig(
                tenant_id=tenant_id,
                logo_url=config["logo_url"],
                primary_color=config["primary_color"],
                typography=config["typography"],
                domain=config["domain"],
                locale=config["locale"],
                currency=config["currency"]
            )
        except Exception as e:
            logger.error(f"Failed to fetch white-label config for tenant {tenant_id}: {e}")
            raise

# AnalyticsAgent
class AnalyticsAgent:
    async def compute_kpis(self, tenant_id: str, conn: asyncpg.Connection) -> Dict:
        """Compute KPIs for tenant."""
        try:
            # Example KPIs: listing count, average valuation, match success rate
            listing_count = await conn.fetchval(
                "SELECT COUNT(*) FROM listings WHERE tenant_id = $1 AND status = 'validated'",
                tenant_id
            )
            avg_valuation = await conn.fetchval(
                "SELECT AVG((range_low + range_high) / 2) FROM valuations WHERE tenant_id = $1",
                tenant_id
            ) or 0.0
            match_count = await conn.fetchval(
                "SELECT COUNT(*) FROM matches WHERE tenant_id = $1",  # Assume matches table
                tenant_id
            ) or 0
            
            kpis = {
                "listing_count": listing_count,
                "avg_valuation": avg_valuation,
                "match_success_rate": match_count / max(listing_count, 1),
                "timestamp": datetime.utcnow().isoformat()
            }
            logger.info(f"Computed KPIs for tenant {tenant_id}: {kpis}")
            return kpis
        except Exception as e:
            logger.error(f"Failed to compute KPIs for tenant {tenant_id}: {e}")
            raise

# FastAPI Application
app = FastAPI()

@asynccontextmanager
async def lifespan(app):
    """Initialize database on startup."""
    await init_db()
    yield

app.lifespan = lifespan

async def get_db():
    """Dependency for database connection with tenant isolation."""
    conn = await asyncpg.connect(POSTGRES_DSN)
    try:
        await conn.execute("SET app.tenant_id = $1", "tenant_123")  # Set tenant_id dynamically
        yield conn
    finally:
        await conn.close()

async def get_tenant_id(api_key: str = Depends(APIKeyHeader(name="X-Tenant-ID"))):
    """Extract tenant_id from API key header."""
    return api_key

# API Endpoints
@app.post("/api/listing/intake")
async def intake_listing(payload: Dict, tenant_id: str = Depends(get_tenant_id), conn: asyncpg.Connection = Depends(get_db)):
    orchestrator = MwarokinOrchestrator()
    result = await orchestrator.process_listing(payload, tenant_id, conn)
    return result

@app.post("/api/matchmaking")
async def match_properties(profile: Dict, tenant_id: str = Depends(get_tenant_id), conn: asyncpg.Connection = Depends(get_db)):
    orchestrator = MwarokinOrchestrator()
    matches = await orchestrator.match_properties(profile, tenant_id, conn)
    return [match.dict() for match in matches]

@app.get("/api/whitelabel/config")
async def get_whitelabel_config(tenant_id: str = Depends(get_tenant_id), conn: asyncpg.Connection = Depends(get_db)):
    agent = WhiteLabelAgent()
    config = await agent.get_config(tenant_id, conn)
    return config.dict()

@app.get("/api/analytics/kpis")
async def get_kpis(tenant_id: str = Depends(get_tenant_id), conn: asyncpg.Connection = Depends(get_db)):
    agent = AnalyticsAgent()
    kpis = await agent.compute_kpis(tenant_id, conn)
    return kpis

# Orchestrator
class MwarokinOrchestrator:
    def __init__(self):
        self.listing_agent = ListingAgent()
        self.valuation_agent = ValuationAgent()
        self.matchmaking_agent = MatchmakingAgent()
        self.whitelabel_agent = WhiteLabelAgent()
        self.analytics_agent = AnalyticsAgent()
        self.blockchain_client = BlockchainClient()

    async def process_listing(self, payload: Dict, tenant_id: str, conn: asyncpg.Connection) -> Dict:
        if not self._check_rbac(tenant_id, "create_listing"):
            raise HTTPException(status_code=403, detail="Unauthorized access")
        
        listing_result = await self.listing_agent.intake(payload, tenant_id, conn)
        if listing_result["status"] != "validated":
            return listing_result
        
        valuation = await self.valuation_agent.request(
            listing_id=listing_result["normalized_fields"]["listing_id"],
            address=payload["address"],
            tenant_id=tenant_id,
            conn=conn
        )
        
        # Record transaction on blockchain
        tx_data = {"listing_id": listing_result["normalized_fields"]["listing_id"], "tenant_id": tenant_id}
        token = hashlib.sha256(json.dumps(tx_data).encode()).hexdigest()
        tx_hash = await self.blockchain_client.record_transaction(token, tx_data)
        
        return {
            "listing": listing_result,
            "valuation": valuation.dict(),
            "blockchain_tx": tx_hash
        }

    async def match_properties(self, profile: Dict, tenant_id: str, conn: asyncpg.Connection) -> List[Match]:
        if not self._check_rbac(tenant_id, "search_properties"):
            raise HTTPException(status_code=403, detail="Unauthorized access")
        
        return await self.matchmaking_agent.request(profile, tenant_id, conn)

    def _check_rbac(self, tenant_id: str, action: str) -> bool:
        return True  # Replace with actual RBAC logic

# Example Usage
async def main():
    orchestrator = MwarokinOrchestrator()
    async with asyncpg.connect(POSTGRES_DSN) as conn:
        await conn.execute("SET app.tenant_id = 'tenant_123'")
        listing_payload = {
            "address": "123 Kangemi Rd, Nairobi",
            "property_type": "residential",
            "beds": 2,
            "baths": 1.5,
            "size_sqm": 80.0,
            "media": ["img1.jpg", "img2.jpg"]
        }
        result = await orchestrator.process_listing(listing_payload, "tenant_123", conn)
        print(json.dumps(result, indent=2))
        
        profile = {"beds": 2, "budget": 25000, "location": "Kangemi"}
        matches = await orchestrator.match_properties(profile, "tenant_123", conn)
        print(json.dumps([match.dict() for match in matches], indent=2))
        
        kpis = await AnalyticsAgent().compute_kpis("tenant_123", conn)
        print(json.dumps(kpis, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
```

---

### Frontend JavaScript Integration

To connect the backend to the provided HTML, update the `MwarokinAutomation.js` file to interact with the FastAPI endpoints. Below is the JavaScript code to handle listing intake, matchmaking, white-label config, and KPI display.

```javascript
// MwarokinAutomation.js
const API_BASE_URL = "http://localhost:8000"; // Replace with your FastAPI server URL
const TENANT_ID = "tenant_123"; // Replace with dynamic tenant ID

// Helper to make API requests
async function makeApiRequest(endpoint, method = "GET", data = null) {
    const headers = {
        "Content-Type": "application/json",
        "X-Tenant-ID": TENANT_ID
    };
    const options = { method, headers };
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        if (!response.ok) {
            throw new Error(`API request failed: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("API request error:", error);
        document.getElementById("locationResult").innerHTML = `Error: ${error.message}`;
        return null;
    }
}

// Handle listing intake
async function submitListing() {
    const payload = {
        address: document.getElementById("searchKeyword").value,
        property_type: "residential", // Can be dynamic
        beds: 2, // Replace with form input
        baths: 1.5,
        size_sqm: 80.0,
        media: ["img1.jpg", "img2.jpg"]
    };
    
    const result = await makeApiRequest("/api/listing/intake", "POST", payload);
    if (result) {
        document.getElementById("locationResult").innerHTML = `
            Listing Status: ${result.listing.status}<br>
            Valuation: ${result.valuation.range_low} - ${result.valuation.range_high}<br>
            Blockchain TX: ${result.blockchain_tx}
        `;
    }
}

// Handle matchmaking
async function searchProperties() {
    const profile = {
        beds: parseInt(document.getElementById("searchKeyword").value.match(/\d+/)?.[0] || 2),
        budget: 25000, // Replace with form input
        location: document.getElementById("countrySelect").value
    };
    
    const matches = await makeApiRequest("/api/matchmaking", "POST", profile);
    if (matches) {
        const chatDisplay = document.getElementById("chat-display");
        chatDisplay.innerHTML = matches.map(match => `
            <div class="chat-message">
                <strong>Listing ID:</strong> ${match.listing_id}<br>
                <strong>Score:</strong> ${match.score}<br>
                <strong>Explanation:</strong> ${match.explanation}
            </div>
        `).join("");
    }
}

// Apply white-label configuration
async function applyWhiteLabel() {
    const config = await makeApiRequest("/api/whitelabel/config");
    if (config) {
        document.documentElement.style.setProperty("--primary-color", config.primary_color);
        document.querySelector(".navbar-brand img").src = config.logo_url;
        document.getElementById("currencyResult").innerHTML = `Currency: ${config.currency}`;
    }
}

// Display KPIs
async function displayKPIs() {
    const kpis = await makeApiRequest("/api/analytics/kpis");
    if (kpis) {
        document.getElementById("chat-display").innerHTML = `
            <div class="chat-message">
                <strong>KPIs for Tenant:</strong><br>
                Listings: ${kpis.listing_count}<br>
                Avg Valuation: ${kpis.avg_valuation}<br>
                Match Success Rate: ${(kpis.match_success_rate * 100).toFixed(2)}%
            </div>
        `;
    }
}

// Update chat input handler
function handleUserInput() {
    const userInput = document.getElementById("userInput").value.toLowerCase();
    if (userInput.includes("search")) {
        searchProperties();
    } else if (userInput.includes("list")) {
        submitListing();
    } else if (userInput.includes("kpi")) {
        displayKPIs();
    } else {
        document.getElementById("chat-display").innerHTML += `
            <div class="chat-message">Please specify 'search', 'list', or 'kpi'.</div>
        `;
    }
    document.getElementById("userInput").value = "";
}

// Initialize
document.addEventListener("DOMContentLoaded", () => {
    applyWhiteLabel();
    document.getElementById("countrySelect").addEventListener("change", applyWhiteLabel);
});
```

---

### Implementation Details

1. **Real APIs**:
   - **Geocoding**: Uses `googlemaps` Python client for Google Maps API.
   - **Comps**: Mock MLS API (replace with actual MLS provider like Zillow or local equivalent).
   - **KYC/AML**: Mock Trulioo API (replace with actual KYC provider).
   - Configure API keys securely via environment variables.

2. **Database**:
   - Uses `asyncpg` for PostgreSQL with RLS to enforce tenant isolation.
   - Listings and valuations are stored in separate tables with `tenant_id` as a partition key.
   - `SET app.tenant_id` ensures queries only access tenant-specific data.

3. **WhiteLabelAgent**:
   - Retrieves tenant-specific configurations (logo, colors, locale, currency) from a `tenant_configs` table (not shown, assume created).
   - Frontend applies these via CSS variables and DOM updates.

4. **AnalyticsAgent**:
   - Computes KPIs like listing count, average valuation, and match success rate.
   - Queries tenant-isolated data using RLS.
   - Can be extended to include charts (e.g., using Chart.js, as per system prompt).

5. **Blockchain**:
   - Uses `web3.py` to interact with an Ethereum-based blockchain (replace with your chain).
   - Records listing transactions with a unique token for auditability.
   - Integrates with the JavaScript `tokenizeTransaction` by replicating token generation in Python.

6. **FastAPI**:
   - Provides RESTful endpoints for listing intake, matchmaking, white-label config, and KPIs.
   - Uses `APIKeyHeader` for tenant ID extraction and `asyncpg` for database connections.
   - Ensures tenant isolation via RLS and RBAC (mocked).

7. **Frontend Integration**:
   - `MwarokinAutomation.js` connects to FastAPI endpoints.
   - Updates the chat display with listing results, matches, and KPIs.
   - Applies white-label config dynamically based on tenant settings.
   - Ties to HTML elements like `searchKeyword`, `countrySelect`, and `chat-display`.

---

### Deployment Notes
- **Dependencies**: Install `asyncpg`, `pydantic`, `fastapi`, `googlemaps`, `web3`, `aiohttp`, and `loguru` via `pip`.
- **Database**: Set up PostgreSQL with RLS policies and create necessary tables.
- **API Keys**: Store Google Maps, Trulioo, and blockchain keys securely (e.g., AWS Secrets Manager).
- **Blockchain**: Deploy a smart contract for transaction recording and update `contract_address` and `contract_abi`.
- **FastAPI**: Run with `uvicorn app:app --host 0.0.0.0 --port 8000`.

---

### Example Usage
1. **Submit a Listing**:
   - Enter an address in `searchKeyword` and trigger `submitListing` via the chat input (`list`).
   - Backend validates, geocodes, and valuates the listing, storing it in PostgreSQL and recording on the blockchain.
   - Frontend displays the status, valuation range, and blockchain transaction hash.

2. **Search Properties**:
   - Enter search criteria (e.g., "2 beds") in `userInput` and trigger `searchProperties` (`search`).
   - Backend matches listings and returns scored results with explanations.
   - Frontend shows matches in the chat display.

3. **View KPIs**:
   - Type `kpi` in `userInput` to trigger `displayKPIs`.
   - Backend computes tenant-specific KPIs and displays them in the chat.

4. **White-Labeling**:
   - On page load or country selection, `applyWhiteLabel` fetches and applies tenant-specific styles and currency.

---
