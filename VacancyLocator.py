
---

### Updated Python Implementation

Below is the extended Python code incorporating **PricingAgent**, **LeadCRM_Agent**, and **RAG_Agent**, alongside the existing agents (`ListingAgent`, `ValuationAgent`, `MatchmakingAgent`, `LeaseAgent`, `TransactionAgent`, `ComplianceAgent`, `WhiteLabelAgent`, `AnalyticsAgent`). The code includes enhancements to handle the new filter form, property card rendering, and blockchain transaction logging.

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

# Configuration
GOOGLE_MAPS_API_KEY = "YOUR_GOOGLE_MAPS_API_KEY"
TRULIOO_API_KEY = "YOUR_TRULIOO_API_KEY"
POSTGRES_DSN = "postgresql://user:password@localhost:5432/mwarokin"
WEB3_PROVIDER = "https://sepolia.infura.io/v3/YOUR_INFURA_PROJECT_ID"
CONTRACT_ADDRESS = "0xYourContractAddress"
PRIVATE_KEY = "YOUR_PRIVATE_KEY"

# Initialize services
google_maps = GoogleMapsClient(key=GOOGLE_MAPS_API_KEY)
web3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

# Ethereum Smart Contract ABI
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "token", "type": "string"},
            {"internalType": "string", "name": "data", "type": "string"}
        ],
        "name": "recordTransaction",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "string", "name": "token", "type": "string"}],
        "name": "getTransaction",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    }
]

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
            availability BOOLEAN,
            price FLOAT,
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

        CREATE TABLE IF NOT EXISTS leases (
            lease_id UUID PRIMARY KEY,
            listing_id UUID REFERENCES listings(listing_id),
            tenant_id TEXT NOT NULL,
            applicant_id TEXT,
            clauses JSONB,
            payment_schedule JSONB,
            risks JSONB,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ALTER TABLE leases ENABLE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON leases
            USING (tenant_id = current_setting('app.tenant_id')::TEXT);

        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id UUID PRIMARY KEY,
            listing_id UUID REFERENCES listings(listing_id),
            tenant_id TEXT NOT NULL,
            milestones JSONB,
            dependencies JSONB,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON transactions
            USING (tenant_id = current_setting('app.tenant_id')::TEXT);

        CREATE TABLE IF NOT EXISTS leads (
            lead_id UUID PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            user_id TEXT,
            listing_id UUID,
            score FLOAT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON leads
            USING (tenant_id = current_setting('app.tenant_id')::TEXT);

        CREATE TABLE IF NOT EXISTS tenant_configs (
            tenant_id TEXT PRIMARY KEY,
            logo_url TEXT,
            primary_color TEXT,
            typography TEXT,
            domain TEXT,
            locale TEXT,
            currency TEXT
        );

        CREATE TABLE IF NOT EXISTS market_data (
            data_id UUID PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            source TEXT,
            content JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ALTER TABLE market_data ENABLE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON market_data
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
    availability: bool = True
    price: Optional[float] = None
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

class LeaseDraft(BaseModel):
    lease_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    listing_id: str
    tenant_id: str
    applicant_id: str
    clauses: Dict
    payment_schedule: Dict
    risks: List[str]
    status: str = "draft"

class Transaction(BaseModel):
    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    listing_id: str
    tenant_id: str
    milestones: Dict
    dependencies: List[str]
    status: str = "pending"

class Lead(BaseModel):
    lead_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    user_id: str
    listing_id: Optional[str] = None
    score: float
    status: str = "new"

class WhiteLabelConfig(BaseModel):
    tenant_id: str
    logo_url: str
    primary_color: str
    typography: str
    domain: str
    locale: str
    currency: str

# API Integrations
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
    """Fetch comps from MLS (mock)."""
    async with aiohttp.ClientSession() as session:
        try:
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
    """Perform KYC/AML check via Trulioo (mock)."""
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

# Blockchain Client
class BlockchainClient:
    async def record_transaction(self, token: str, transaction_data: Dict) -> str:
        """Record transaction on Ethereum."""
        try:
            contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
            tx = contract.functions.recordTransaction(token, json.dumps(transaction_data)).build_transaction({
                "from": web3.eth.default_account,
                "nonce": web3.eth.get_transaction_count(web3.eth.default_account),
                "gas": 200000,
                "gasPrice": web3.to_wei("20", "gwei")
            })
            signed_tx = web3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
            tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
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
                "availability": payload.get("availability", True),
                "price": payload.get("price"),
                "status": payload.get("status", "pending"),
            }
            listing = Listing(**listing_data)
            
            warnings = []
            if not listing.address:
                warnings.append("Address is required")
            if listing.property_type not in ["residential", "commercial", "land"]:
                warnings.append(f"Invalid property type: {listing.property_type}")
            
            geocode = await geocode_address(listing.address)
            listing_dict = listing.dict()
            listing_dict.update({
                "geocode": geocode,
                "walkscore": 0.75,
                "amenities": ["school", "transit"],
                "status": "validated" if not warnings else "pending",
                "warnings": warnings
            })
            
            await conn.execute(
                """
                INSERT INTO listings (listing_id, tenant_id, address, property_type, beds, baths, size_sqm, media, status, availability, price, geocode)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                listing.listing_id, tenant_id, listing.address, listing.property_type,
                listing.beds, listing.baths, listing.size_sqm, json.dumps(listing.media),
                listing.status, listing.availability, listing.price, json.dumps(geocode)
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

# PricingAgent
class PricingAgent:
    async def set_price(self, listing_id: str, tenant_id: str, conn: asyncpg.Connection) -> Dict:
        """Set dynamic price based on market elasticity and trends."""
        try:
            listing = await conn.fetchrow(
                "SELECT listing_id, address, property_type, beds FROM listings WHERE listing_id = $1 AND tenant_id = $2",
                listing_id, tenant_id
            )
            if not listing:
                raise ValueError(f"Listing {listing_id} not found")

            # Fetch market data (mock RAG)
            comps = await fetch_comps(listing["address"], radius_km=5.0, tenant_id=tenant_id)
            avg_price = sum(comp["price"] for comp in comps) / len(comps) if comps else 20000
            seasonality_factor = 1.1 if datetime.now().month in [12, 1, 2] else 1.0  # Peak season adjustment
            elasticity = 0.8 if listing["property_type"] == "residential" else 0.9  # Mock elasticity

            suggested_price = avg_price * seasonality_factor * elasticity
            reasoning = f"Price set to {suggested_price:.2f} based on {len(comps)} comps, "
            reasoning += f"seasonality factor {seasonality_factor}, and elasticity {elasticity}."
            reasoning = redact_pii(reasoning)

            await conn.execute(
                "UPDATE listings SET price = $1 WHERE listing_id = $2 AND tenant_id = $3",
                suggested_price, listing_id, tenant_id
            )

            logger.info(f"Price set for listing {listing_id}: {suggested_price}")
            return {"listing_id": listing_id, "price": suggested_price, "reasoning": reasoning}
        except Exception as e:
            logger.error(f"Pricing failed for listing {listing_id}: {e}")
            raise

# MatchmakingAgent
class MatchmakingAgent:
    async def request(self, profile: Dict, tenant_id: str, conn: asyncpg.Connection) -> List[Match]:
        """Match buyer/tenant to properties."""
        try:
            query = """
                SELECT listing_id, beds, size_sqm, address, price, property_type, availability
                FROM listings
                WHERE tenant_id = $1 AND status = 'validated'
            """
            filters = []
            params = [tenant_id]
            if profile.get("price_min"):
                params.append(profile["price_min"])
                filters.append(f"price >= ${len(params)}")
            if profile.get("price_max"):
                params.append(profile["price_max"])
                filters.append(f"price <= ${len(params)}")
            if profile.get("location"):
                params.append(f"%{profile['location']}%")
                filters.append(f"address ILIKE ${len(params)}")
            if profile.get("property_type"):
                params.append(profile["property_type"])
                filters.append(f"property_type = ${len(params)}")
            if profile.get("availability") is not None:
                params.append(profile["availability"])
                filters.append(f"availability = ${len(params)}")

            if filters:
                query += " AND " + " AND ".join(filters)

            listings = await conn.fetch(query, *params)
            
            matches = []
            for listing in listings:
                score = self._calculate_match_score(profile, listing)
                explanation = f"Match score: {score:.2f}. "
                explanation += f"Criteria: beds ({profile.get('beds', 0)} vs {listing['beds']}), "
                explanation += f"price ({profile.get('price_min', 0)}-{profile.get('price_max', 'N/A')} vs {listing['price']}), "
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
            score += 0.4
        if profile.get("price_min", 0) <= listing["price"] <= profile.get("price_max", float("inf")):
            score += 0.3
        if profile.get("location") and profile["location"].lower() in listing["address"].lower():
            score += 0.2
        if profile.get("property_type") == listing["property_type"]:
            score += 0.1
        return min(score, 1.0)

# LeadCRM_Agent
class LeadCRM_Agent:
    async def capture_lead(self, user_id: str, listing_id: Optional[str], tenant_id: str, conn: asyncpg.Connection) -> Lead:
        """Capture and score a lead."""
        try:
            kyc_result = await kyc_check(user_id, tenant_id)
            if not kyc_result["passed"]:
                raise ValueError(f"KYC check failed for user {user_id}")

            # BANT-like scoring (Budget, Authority, Need, Timeline)
            score = 0.8 if kyc_result["passed"] else 0.3  # Mock scoring
            lead = Lead(
                tenant_id=tenant_id,
                user_id=user_id,
                listing_id=listing_id,
                score=score,
                status="new"
            )

            await conn.execute(
                """
                INSERT INTO leads (lead_id, tenant_id, user_id, listing_id, score, status)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                lead.lead_id, tenant_id, user_id, listing_id, score, lead.status
            )

            logger.info(f"Lead captured for user {user_id}, tenant {tenant_id}")
            return lead
        except Exception as e:
            logger.error(f"Lead capture failed: {e}")
            raise

# RAG_Agent
class RAG_Agent:
    async def retrieve(self, query: str, tenant_id: str, conn: asyncpg.Connection) -> List[Dict]:
        """Retrieve relevant market data or internal docs."""
        try:
            # Mock RAG retrieval (replace with vector search or API)
            results = await conn.fetch(
                "SELECT source, content FROM market_data WHERE tenant_id = $1 AND content->>'text' ILIKE $2",
                tenant_id, f"%{query}%"
            )
            
            retrieved = [
                {"source": row["source"], "content": row["content"], "relevance": 0.9}  # Mock relevance
                for row in results
            ]
            
            # Simulate external market data fetch
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        "https://mock-market-api/data",
                        params={"query": query, "tenant_id": tenant_id}
                    ) as resp:
                        if resp.status == 200:
                            external_data = await resp.json()
                            retrieved.extend([
                                {"source": f"External: {item['source']}", "content": item, "relevance": 0.7}
                                for item in external_data
                            ])
                except Exception as e:
                    logger.error(f"External RAG fetch failed: {e}")

            logger.info(f"RAG retrieved {len(retrieved)} items for query: {query}")
            return retrieved
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            raise

# LeaseAgent
class LeaseAgent:
    async def create_draft(self, listing_id: str, applicant_id: str, terms: Dict, tenant_id: str, conn: asyncpg.Connection) -> LeaseDraft:
        """Create a lease draft."""
        try:
            listing = await conn.fetchrow(
                "SELECT listing_id FROM listings WHERE listing_id = $1 AND tenant_id = $2 AND status = 'validated'",
                listing_id, tenant_id
            )
            if not listing:
                raise ValueError(f"Invalid or unauthorized listing {listing_id}")

            kyc_result = await kyc_check(applicant_id, tenant_id)
            if not kyc_result["passed"]:
                raise ValueError(f"KYC check failed for applicant {applicant_id}")

            clauses = {
                "duration_months": terms.get("duration_months", 12),
                "rent_monthly": terms.get("rent_monthly", 20000),
                "deposit": terms.get("deposit", 20000)
            }
            payment_schedule = {
                "due_dates": [f"2025-{i:02d}-01" for i in range(1, clauses["duration_months"] + 1)],
                "amounts": [clauses["rent_monthly"]] * clauses["duration_months"]
            }
            risks = []
            if clauses["rent_monthly"] > 50000:
                risks.append("High rent may increase arrears risk")

            lease = LeaseDraft(
                listing_id=listing_id,
                tenant_id=tenant_id,
                applicant_id=applicant_id,
                clauses=clauses,
                payment_schedule=payment_schedule,
                risks=risks,
                status="draft"
            )

            await conn.execute(
                """
                INSERT INTO leases (lease_id, listing_id, tenant_id, applicant_id, clauses, payment_schedule, risks, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                lease.lease_id, listing_id, tenant_id, applicant_id,
                json.dumps(clauses), json.dumps(payment_schedule), json.dumps(risks), lease.status
            )

            logger.info(f"Lease draft created for listing {listing_id}, tenant {tenant_id}")
            return lease
        except Exception as e:
            logger.error(f"Lease creation failed: {e}")
            raise

# TransactionAgent
class TransactionAgent:
    async def create_transaction(self, listing_id: str, tenant_id: str, conn: asyncpg.Connection) -> Transaction:
        """Create a transaction with readiness checklist."""
        try:
            listing = await conn.fetchrow(
                "SELECT listing_id FROM listings WHERE listing_id = $1 AND tenant_id = $2 AND status = 'validated'",
                listing_id, tenant_id
            )
            if not listing:
                raise ValueError(f"Invalid or unauthorized listing {listing_id}")

            milestones = {
                "title_check": "pending",
                "escrow_setup": "pending",
                "inspection": "pending",
                "disclosures": "pending"
            }
            dependencies = ["KYC passed", "Listing validated"]

            transaction = Transaction(
                listing_id=listing_id,
                tenant_id=tenant_id,
                milestones=milestones,
                dependencies=dependencies,
                status="pending"
            )

            await conn.execute(
                """
                INSERT INTO transactions (transaction_id, listing_id, tenant_id, milestones, dependencies, status)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                transaction.transaction_id, listing_id, tenant_id,
                json.dumps(milestones), json.dumps(dependencies), transaction.status
            )

            logger.info(f"Transaction created for listing {listing_id}, tenant {tenant_id}")
            return transaction
        except Exception as e:
            logger.error(f"Transaction creation failed: {e}")
            raise

# ComplianceAgent
class ComplianceAgent:
    async def kyc_check(self, user_id: str, tenant_id: str) -> Dict[str, bool]:
        """Perform KYC/AML checks."""
        return await kyc_check(user_id, tenant_id)

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
                return WhiteLabelConfig(
                    tenant_id=tenant_id,
                    logo_url="default_logo.png",
                    primary_color="#007bff",
                    typography="Arial",
                    domain="example.com",
                    locale="en_US",
                    currency="USD"
                )
            
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
            listing_count = await conn.fetchval(
                "SELECT COUNT(*) FROM listings WHERE tenant_id = $1 AND status = 'validated'",
                tenant_id
            )
            avg_valuation = await conn.fetchval(
                "SELECT AVG((range_low + range_high) / 2) FROM valuations WHERE tenant_id = $1",
                tenant_id
            ) or 0.0
            lease_count = await conn.fetchval(
                "SELECT COUNT(*) FROM leases WHERE tenant_id = $1 AND status = 'active'",
                tenant_id
            ) or 0
            transaction_count = await conn.fetchval(
                "SELECT COUNT(*) FROM transactions WHERE tenant_id = $1 AND status = 'completed'",
                tenant_id
            ) or 0
            lead_conversion = await conn.fetchval(
                "SELECT COUNT(*) FROM leads WHERE tenant_id = $1 AND status = 'converted'",
                tenant_id
            ) or 0
            
            kpis = {
                "listing_count": listing_count,
                "avg_valuation": avg_valuation,
                "lease_count": lease_count,
                "transaction_count": transaction_count,
                "lead_conversion_rate": lead_conversion / max(listing_count, 1),
                "timestamp": datetime.utcnow().isoformat(),
                "chart_data": {
                    "labels": ["Listings", "Avg Valuation", "Leases", "Transactions", "Lead Conversion"],
                    "datasets": [{
                        "label": "Tenant KPIs",
                        "data": [listing_count, avg_valuation, lease_count, transaction_count, lead_conversion],
                        "backgroundColor": ["#007bff", "#28a745", "#ffc107", "#dc3545", "#6f42c1"],
                        "borderColor": ["#0056b3", "#218838", "#e0a800", "#c82333", "#5a32a3"],
                        "borderWidth": 1
                    }]
                }
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
        await conn.execute("SET app.tenant_id = $1", "tenant_123")
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

@app.post("/api/lease/draft")
async def create_lease_draft(payload: Dict, tenant_id: str = Depends(get_tenant_id), conn: asyncpg.Connection = Depends(get_db)):
    orchestrator = MwarokinOrchestrator()
    lease = await orchestrator.create_lease_draft(
        payload["listing_id"], payload["applicant_id"], payload["terms"], tenant_id, conn
    )
    return lease.dict()

@app.post("/api/transaction/create")
async def create_transaction(payload: Dict, tenant_id: str = Depends(get_tenant_id), conn: asyncpg.Connection = Depends(get_db)):
    orchestrator = MwarokinOrchestrator()
    transaction = await orchestrator.create_transaction(payload["listing_id"], tenant_id, conn)
    return transaction.dict()

@app.post("/api/lead/capture")
async def capture_lead(payload: Dict, tenant_id: str = Depends(get_tenant_id), conn: asyncpg.Connection = Depends(get_db)):
    orchestrator = MwarokinOrchestrator()
    lead = await orchestrator.capture_lead(payload["user_id"], payload.get("listing_id"), tenant_id, conn)
    return lead.dict()

@app.post("/api/pricing/set")
async def set_price(payload: Dict, tenant_id: str = Depends(get_tenant_id), conn: asyncpg.Connection = Depends(get_db)):
    orchestrator = MwarokinOrchestrator()
    price = await orchestrator.set_price(payload["listing_id"], tenant_id, conn)
    return price

@app.post("/api/rag/retrieve")
async def rag_retrieve(payload: Dict, tenant_id: str = Depends(get_tenant_id), conn: asyncpg.Connection = Depends(get_db)):
    orchestrator = MwarokinOrchestrator()
    results = await orchestrator.rag_retrieve(payload["query"], tenant_id, conn)
    return results

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
        self.pricing_agent = PricingAgent()
        self.matchmaking_agent = MatchmakingAgent()
        self.lease_agent = LeaseAgent()
        self.transaction_agent = TransactionAgent()
        self.compliance_agent = ComplianceAgent()
        self.lead_crm_agent = LeadCRM_Agent()
        self.rag_agent = RAG_Agent()
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
        
        price = await self.pricing_agent.set_price(
            listing_id=listing_result["normalized_fields"]["listing_id"],
            tenant_id=tenant_id,
            conn=conn
        )
        
        tx_data = {
            "listing_id": listing_result["normalized_fields"]["listing_id"],
            "tenant_id": tenant_id,
            "price": price["price"]
        }
        token = hashlib.sha256(json.dumps(tx_data).encode()).hexdigest()
        tx_hash = await self.blockchain_client.record_transaction(token, tx_data)
        
        return {
            "listing": listing_result,
            "valuation": valuation.dict(),
            "price": price,
            "blockchain_tx": tx_hash
        }

    async def match_properties(self, profile: Dict, tenant_id: str, conn: asyncpg.Connection) -> List[Match]:
        if not self._check_rbac(tenant_id, "search_properties"):
            raise HTTPException(status_code=403, detail="Unauthorized access")
        
        return await self.matchmaking_agent.request(profile, tenant_id, conn)

    async def create_lease_draft(self, listing_id: str, applicant_id: str, terms: Dict, tenant_id: str, conn: asyncpg.Connection) -> LeaseDraft:
        if not self._check_rbac(tenant_id, "create_lease"):
            raise HTTPException(status_code=403, detail="Unauthorized access")
        
        return await self.lease_agent.create_draft(listing_id, applicant_id, terms, tenant_id, conn)

    async def create_transaction(self, listing_id: str, tenant_id: str, conn: asyncpg.Connection) -> Transaction:
        if not self._check_rbac(tenant_id, "create_transaction"):
            raise HTTPException(status_code=403, detail="Unauthorized access")
        
        return await self.transaction_agent.create_transaction(listing_id, tenant_id, conn)

    async def capture_lead(self, user_id: str, listing_id: Optional[str], tenant_id: str, conn: asyncpg.Connection) -> Lead:
        if not self._check_rbac(tenant_id, "capture_lead"):
            raise HTTPException(status_code=403, detail="Unauthorized access")
        
        return await self.lead_crm_agent.capture_lead(user_id, listing_id, tenant_id, conn)

    async def set_price(self, listing_id: str, tenant_id: str, conn: asyncpg.Connection) -> Dict:
        if not self._check_rbac(tenant_id, "set_price"):
            raise HTTPException(status_code=403, detail="Unauthorized access")
        
        return await self.pricing_agent.set_price(listing_id, tenant_id, conn)

    async def rag_retrieve(self, query: str, tenant_id: str, conn: asyncpg.Connection) -> List[Dict]:
        if not self._check_rbac(tenant_id, "rag_retrieve"):
            raise HTTPException(status_code=403, detail="Unauthorized access")
        
        return await self.rag_agent.retrieve(query, tenant_id, conn)

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
            "media": ["img1.jpg", "img2.jpg"],
            "availability": True,
            "status": "for rent",
            "price": 20000.0
        }
        result = await orchestrator.process_listing(listing_payload, "tenant_123", conn)
        print(json.dumps(result, indent=2))
        
        profile = {
            "price_min": 15000,
            "price_max": 25000,
            "location": "Kangemi",
            "beds": 2,
            "property_type": "residential",
            "availability": True,
            "status": "for rent"
        }
        matches = await orchestrator.match_properties(profile, "tenant_123", conn)
        print(json.dumps([match.dict() for match in matches], indent=2))
        
        lease_terms = {"duration_months": 12, "rent_monthly": 22000, "deposit": 22000}
        lease = await orchestrator.create_lease_draft(result["listing"]["normalized_fields"]["listing_id"], "applicant_123", lease_terms, "tenant_123", conn)
        print(json.dumps(lease.dict(), indent=2))
        
        transaction = await orchestrator.create_transaction(result["listing"]["normalized_fields"]["listing_id"], "tenant_123", conn)
        print(json.dumps(transaction.dict(), indent=2))
        
        lead = await orchestrator.capture_lead("user_123", result["listing"]["normalized_fields"]["listing_id"], "tenant_123", conn)
        print(json.dumps(lead.dict(), indent=2))
        
        rag_results = await orchestrator.rag_retrieve("market trends Kangemi", "tenant_123", conn)
        print(json.dumps(rag_results, indent=2))
        
        kpis = await orchestrator.analytics_agent.compute_kpis("tenant_123", conn)
        print(json.dumps(kpis, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
```

---

### Updated Frontend JavaScript (MwarokinAutomation.js)

Below is the updated `MwarokinAutomation.js` to integrate with all agents, handle the filter form from the provided HTML, render property cards dynamically, and display the Chart.js KPI visualization.

```javascript
// MwarokinAutomation.js
const API_BASE_URL = "http://localhost:8000";
const TENANT_ID = "tenant_123";

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

// Handle listing creation
async function submitListing() {
    const payload = {
        address: document.getElementById("listingAddress").value,
        property_type: document.getElementById("propertyType").value,
        beds: parseInt(document.getElementById("beds").value) || 1,
        baths: parseFloat(document.getElementById("baths").value) || 1.0,
        size_sqm: parseFloat(document.getElementById("sizeSqm").value) || 50.0,
        media: document.getElementById("media").value.split(",").map(url => url.trim()),
        availability: document.querySelector("input[name='availability']:checked")?.value === "true",
        status: document.querySelector("input[name='status']:checked")?.value || "for rent",
        price: parseFloat(document.getElementById("price").value) || null
    };
    
    const result = await makeApiRequest("/api/listing/intake", "POST", payload);
    if (result) {
        document.getElementById("locationResult").innerHTML = `
            Listing Status: ${result.listing.status}<br>
            Valuation: ${result.valuation.range_low} - ${result.valuation.range_high}<br>
            Price: ${result.price.price}<br>
            Blockchain TX: ${result.blockchain_tx}
        `;
        updatePropertyList();
    }
}

// Handle property search with filters
async function searchProperties() {
    const profile = {
        price_min: parseFloat(document.getElementById("priceMin").value) || 0,
        price_max: parseFloat(document.getElementById("priceMax").value) || Number.MAX_SAFE_INTEGER,
        location: document.getElementById("location").value,
        property_type: document.getElementById("searchPropertyType").value,
        beds: parseInt(document.getElementById("searchBeds").value) || 0,
        availability: document.querySelector("input[name='availability']:checked")?.value === "true",
        status: document.querySelector("input[name='status']:checked")?.value
    };
    
    const matches = await makeApiRequest("/api/matchmaking", "POST", profile);
    if (matches) {
        const properties = document.getElementById("properties");
        properties.innerHTML = matches.map(match => `
            <div class="property-card" data-listing-id="${match.listing_id}">
                <img src="/api/placeholder/400/320" alt="Property" class="property-image">
                <div class="property-details">
                    <div class="price">$${match.score * 20000}</div>
                    <h3>Property ID: ${match.listing_id}</h3>
                    <p class="location"><i class="fas fa-map-marker-alt"></i> ${profile.location || "Unknown"}</p>
                    <div class="features">
                        <span class="feature"><i class="fas fa-bed"></i> ${profile.beds || "N/A"} Beds</span>
                        <span class="feature"><i class="fas fa-bath"></i> N/A Bath</span>
                        <span class="feature"><i class="fas fa-ruler-combined"></i> N/A sq.ft</span>
                    </div>
                    <p>${match.explanation}</p>
                </div>
            </div>
        `).join("");
        addPropertyCardListeners();
    }
}

// Handle lease draft creation
async function createLeaseDraft() {
    const payload = {
        listing_id: document.getElementById("leaseListingId").value,
        applicant_id: document.getElementById("applicantId").value,
        terms: {
            duration_months: parseInt(document.getElementById("leaseDuration").value) || 12,
            rent_monthly: parseFloat(document.getElementById("rentMonthly").value) || 20000,
            deposit: parseFloat(document.getElementById("deposit").value) || 20000
        }
    };
    
    const lease = await makeApiRequest("/api/lease/draft", "POST", payload);
    if (lease) {
        document.getElementById("chat-display").innerHTML += `
            <div class="chat-message">
                <strong>Lease Draft Created:</strong><br>
                Lease ID: ${lease.lease_id}<br>
                Status: ${lease.status}<br>
                Risks: ${lease.risks.join(", ") || "None"}
            </div>
        `;
    }
}

// Handle transaction creation
async function createTransaction() {
    const payload = {
        listing_id: document.getElementById("transactionListingId").value
    };
    
    const transaction = await makeApiRequest("/api/transaction/create", "POST", payload);
    if (transaction) {
        document.getElementById("chat-display").innerHTML += `
            <div class="chat-message">
                <strong>Transaction Created:</strong><br>
                Transaction ID: ${transaction.transaction_id}<br>
                Status: ${transaction.status}<br>
                Milestones: ${JSON.stringify(transaction.milestones)}
            </div>
        `;
    }
}

// Handle lead capture
async function captureLead(listing_id) {
    const payload = {
        user_id: "user_123", // Replace with actual user ID from auth
        listing_id
    };
    
    const lead = await makeApiRequest("/api/lead/capture", "POST", payload);
    if (lead) {
        document.getElementById("chat-display").innerHTML += `
            <div class="chat-message">
                <strong>Lead Captured:</strong><br>
                Lead ID: ${lead.lead_id}<br>
                Score: ${lead.score}<br>
                Status: ${lead.status}
            </div>
        `;
    }
}

// Handle RAG query
async function ragQuery() {
    const query = document.getElementById("userInput").value;
    const results = await makeApiRequest("/api/rag/retrieve", "POST", { query });
    if (results) {
        document.getElementById("chat-display").innerHTML += `
            <div class="chat-message">
                <strong>RAG Results:</strong><br>
                ${results.map(r => `<p>${r.source}: ${JSON.stringify(r.content)}</p>`).join("")}
            </div>
        `;
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

// Display KPIs with Chart.js
async function displayKPIs() {
    const kpis = await makeApiRequest("/api/analytics/kpis");
    if (kpis) {
        document.getElementById("chat-display").innerHTML = `
            <div class="chat-message">
                <strong>KPIs for Tenant:</strong><br>
                Listings: ${kpis.listing_count}<br>
                Avg Valuation: ${kpis.avg_valuation.toFixed(2)}<br>
                Leases: ${kpis.lease_count}<br>
                Transactions: ${kpis.transaction_count}<br>
                Lead Conversion: ${(kpis.lead_conversion_rate * 100).toFixed(2)}%<br>
                <canvas id="kpiChart" style="max-height: 200px;"></canvas>
            </div>
        `;
        
        const ctx = document.getElementById("kpiChart").getContext("2d");
        new Chart(ctx, {
            type: "bar",
            data: kpis.chart_data,
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true } },
                plugins: {
                    legend: { display: true },
                    title: { display: true, text: "Tenant KPIs" }
                }
            }
        });
    }
}

// Update property list dynamically
async function updatePropertyList() {
    const profile = {
        price_min: parseFloat(document.getElementById("priceMin").value) || 0,
        price_max: parseFloat(document.getElementById("priceMax").value) || Number.MAX_SAFE_INTEGER,
        location: document.getElementById("location").value,
        property_type: document.getElementById("searchPropertyType").value,
        beds: parseInt(document.getElementById("searchBeds").value) || 0,
        availability: document.querySelector("input[name='availability']:checked")?.value === "true",
        status: document.querySelector("input[name='status']:checked")?.value
    };
    
    await searchProperties(profile);
}

// Add click listeners to property cards
function addPropertyCardListeners() {
    document.querySelectorAll(".property-card").forEach(card => {
        card.addEventListener("click", () => {
            const listing_id = card.dataset.listingId;
            captureLead(listing_id);
            const map = new google.maps.Map(document.getElementById("map"), {
                zoom: 16,
                center: { lat: -1.2921, lng: 36.8219 } // Mock coords
            });
        });
    });
}

// Update chat input handler
function handleUserInput() {
    const userInput = document.getElementById("userInput").value.toLowerCase();
    const chatDisplay = document.getElementById("chat-display");
    if (userInput.includes("search")) {
        searchProperties();
    } else if (userInput.includes("list")) {
        submitListing();
    } else if (userInput.includes("lease")) {
        createLeaseDraft();
    } else if (userInput.includes("transaction")) {
        createTransaction();
    } else if (userInput.includes("kpi")) {
        displayKPIs();
    } else if (userInput.includes("rag")) {
        ragQuery();
    } else {
        chatDisplay.innerHTML += `
            <div class="chat-message">Please specify 'search', 'list', 'lease', 'transaction', 'kpi', or 'rag'.</div>
        `;
    }
    document.getElementById("userInput").value = "";
}

// Initialize
document.addEventListener("DOMContentLoaded", () => {
    applyWhiteLabel();
    document.getElementById("filterBtn").addEventListener("click", updatePropertyList);
    document.getElementById("bedrooms-btn").addEventListener("click", () => {
        document.getElementById("searchBeds").focus();
    });
    document.getElementById("secure-booking-btn").addEventListener("click", createTransaction);
    document.getElementById("smart-contracts-btn").addEventListener("click", createTransaction);
    updatePropertyList();
});
```

---

### Updated HTML (Frontend Enhancements)

Integrate the existing HTML with the previous form additions and ensure compatibility with the property card and filter UI. Below is the consolidated HTML, incorporating the listing, search, lease, and transaction forms, plus a chat input for user commands:

```html:disable-run
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mwarokin Real Estate</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script async defer src="https://maps.googleapis.com/maps/api/js?key=YOUR_API_KEY&callback=initMap"></script>
    <style>
        /* Existing styles from provided HTML */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Arial', sans-serif;
        }
        :root {
            --primary-color: #007bff;
        }
        #propertyContainer {
            overflow-y: auto;
            padding: 20px;
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-right: 2px solid rgba(255, 255, 255, 0.1);
        }
        .filters {
            position: sticky;
            top: 0;
            background: rgba(255, 255, 255, 0.1);
            padding: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 100;
            border-radius: 10px;
        }
        .filter-btn {
            padding: 10px 20px;
            border: none;
            border-radius: 30px;
            background: var(--primary-color);
            color: white;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .filter-btn:hover {
            background: #42a5f5;
        }
        .property-card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
            cursor: pointer;
        }
        .property-card:hover {
            transform: translateY(-5px);
        }
        .property-image {
            width: 100%;
            height: 200px;
            object-fit: cover;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        .price {
            color: #00e676;
            font-size: 1.5em;
            font-weight: bold;
        }
        .features {
            display: flex;
            gap: 15px;
            color: #ccc;
        }
        .feature {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        #map {
            height: 100%;
            width: 100%;
        }
        .map-controls {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(255, 255, 255, 0.1);
            padding: 10px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            display: flex;
            gap: 10px;
        }
        .map-controls button {
            background: rgba(255, 255, 255, 0.1);
            color: white;
            border: none;
            padding: 10px;
            border-radius: 50%;
            cursor: pointer;
        }
        .map-controls button:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        .loading-skeleton {
            animation: loading 1.5s infinite;
            background: linear-gradient(90deg, #2b2b2b 25%, #444444 50%, #2b2b2b 75%);
            background-size: 200% 100%;
            border-radius: 10px;
            height: 300px;
            margin-bottom: 20px;
        }
        @keyframes loading {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }
        .chat-message {
            background: rgba(255, 255, 255, 0.1);
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
        }
        @media (max-width: 768px) {
            .container {
                grid-template-columns: 1fr;
            }
            #map {
                height: 50vh;
            }
        }
    </style>
</head>
<body>
    <div class="container-fluid">
        <!-- Navigation Bar -->
        <nav class="container-fluid nav-bar bg-transparent sticky-top">
            <div class="navbar navbar-expand-lg bg-white navbar-light py-0 px-4">
                <a href="index.html" class="navbar-brand d-flex align-items-center">
                    <img class="img-fluid" src="img/Mwarokin.png" alt="Icon" style="width: 30px; height: 30px;">
                    <h1 class="m-0 text-primary">Mwarokin</h1>
                </a>
                <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarCollapse">
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="navbarCollapse">
                    <ul class="navbar-nav ms-auto">
                        <li class="nav-item"><a href="index.html" class="nav-link">Home</a></li>
                        <li class="nav-item"><a href="ManageBills.html" class="nav-link">Manage Bills</a></li>
                        <li class="nav-item"><a href="Payments.html" class="nav-link">Payments</a></li>
                        <li class="nav-item"><a href="LipaMdogo.html" class="nav-link">Lipa Mdogo</a></li>
                        <li class="nav-item"><a href="Rent.html" class="nav-link">Rent</a></li>
                        <li class="nav-item dropdown">
                            <a href="#" class="nav-link dropdown-toggle" data-bs-toggle="dropdown">Clients</a>
                            <div class="dropdown-menu">
                                <a href="Landlord.html" class="dropdown-item">Landlord</a>
                                <a href="CareTakers.html" class="dropdown-item">Care Takers</a>
                                <a href="Renovations.html" class="dropdown-item">Renovations</a>
                                <a href="CalculatePendingRent.html" class="dropdown-item">Calculate Rent</a>
                                <a href="LanguageSupport.html" class="dropdown-item">Language Support</a>
                                <a href="Construction.html" class="dropdown-item">Construction</a>
                            </div>
                        </li>
                        <li class="nav-item"><a href="Communication.html" class="nav-link">Communication</a></li>
                        <li class="nav-item"><a href="Managetenants.html" class="nav-link">Manage Tenants</a></li>
                        <li class="nav-item"><a href="property-type.html" class="nav-link">Property Type</a></li>
                        <li class="nav-item"><a href="LipaCalculator.html" class="nav-link">Lipa Calculator</a></li>
                        <li class="nav-item"><a href="unmapped.html" class="nav-link">Unmapped</a></li>
                        <li class="nav-item"><a href="TrackProperties.html" class="nav-link">Track Properties</a></li>
                        <li class="nav-item dropdown">
                            <a href="#" class="nav-link dropdown-toggle" data-bs-toggle="dropdown">Land</a>
                            <div class="dropdown-menu">
                                <a href="Selling.html" class="dropdown-item">Selling Property</a>
                                <a href="Buying.html" class="dropdown-item">Buying Property</a>
                                <a href="Construction.html" class="dropdown-item">Construction</a>
                                <a href="Renovations.html" class="dropdown-item">Renovations</a>
                            </div>
                        </li>
                    </ul>
                    <a href="LogOut.html" class="btn btn-primary px-3 d-none d-lg-flex">Log Out</a>
                </div>
            </div>
        </nav>

        <div class="container">
            <!-- Filter Form -->
            <div class="row mb-4">
                <div class="col-md-3">
                    <input type="number" id="priceMin" class="form-control" placeholder="Min Price">
                </div>
                <div class="col-md-3">
                    <input type="number" id="priceMax" class="form-control" placeholder="Max Price">
                </div>
                <div class="col-md-3">
                    <input type="text" id="location" class="form-control" placeholder="Location">
                </div>
                <div class="col-md-3">
                    <button id="filterBtn" class="btn btn-primary w-100">Apply Filters</button>
                </div>
            </div>
            <!-- Radio Buttons for Status -->
            <div class="row mb-4">
                <div class="col-md-4">
                    <div class="form-check">
                        <input class="form-check-input" type="radio" name="status" value="for rent" id="rentOption">
                        <label class="form-check-label" for="rentOption">For Rent</label>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="form-check">
                        <input class="form-check-input" type="radio" name="status" value="for sale" id="saleOption">
                        <label class="form-check-label" for="saleOption">For Sale</label>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="form-check">
                        <input class="form-check-input" type="radio" name="status" value="for buy" id="buyOption">
                        <label class="form-check-label" for="buyOption">For Buy</label>
                    </div>
                </div>
            </div>
            <!-- Radio Buttons for Availability -->
            <div class="row mb-4">
                <div class="col-md-6">
                    <div class="form-check">
                        <input class="form-check-input" type="radio" name="availability" value="true" id="availableOption">
                        <label class="form-check-label" for="availableOption">Available</label>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="form-check">
                        <input class="form-check-input" type="radio" name="availability" value="false" id="unavailableOption">
                        <label class="form-check-label" for="unavailableOption">Unavailable</label>
                    </div>
                </div>
            </div>
            <!-- Additional Filters -->
            <div class="row mb-4">
                <div class="col-md-3">
                    <input type="number" id="searchBeds" class="form-control" placeholder="Beds">
                </div>
                <div class="col-md-3">
                    <select class="form-select" id="searchPropertyType">
                        <option value="">Any Type</option>
                        <option value="residential">Residential</option>
                        <option value="commercial">Commercial</option>
                        <option value="land">Land</option>
                    </select>
                </div>
            </div>
            <!-- Listing Creation Form -->
            <div class="row g-2 mt-3">
                <h3>Create Listing</h3>
                <div class="col-md-3">
                    <input type="text" class="form-control" id="listingAddress" placeholder="Address">
                </div>
                <div class="col-md-3">
                    <select class="form-select" id="propertyType">
                        <option value="residential">Residential</option>
                        <option value="commercial">Commercial</option>
                        <option value="land">Land</option>
                    </select>
                </div>
                <div class="col-md-2">
                    <input type="number" class="form-control" id="beds" placeholder="Beds">
                </div>
                <div class="col-md-2">
                    <input type="number" class="form-control" id="baths" placeholder="Baths">
                </div>
                <div class="col-md-2">
                    <input type="number" class="form-control" id="sizeSqm" placeholder="Size (sqm)">
                </div>
                <div class="col-md-3">
                    <input type="number" class="form-control" id="price" placeholder="Price">
                </div>
                <div class="col-md-3">
                    <input type="text" class="form-control" id="media" placeholder="Media URLs (comma-separated)">
                </div>
                <div class="col-md-2 text-end">
                    <button class="btn btn-primary" onclick="submitListing()">Submit Listing</button>
                </div>
            </div>
            <!-- Lease Draft Form -->
            <div class="row g-2 mt-3">
                <h3>Create Lease Draft</h3>
                <div class="col-md-3">
                    <input type="text" class="form-control" id="leaseListingId" placeholder="Listing ID">
                </div>
                <div class="col-md-3">
                    <input type="text" class="form-control" id="applicantId" placeholder="Applicant ID">
                </div>
                <div class="col-md-2">
                    <input type="number" class="form-control" id="leaseDuration" placeholder="Duration (months)">
                </div>
                <div class="col-md-2">
                    <input type="number" class="form-control" id="rentMonthly" placeholder="Monthly Rent">
                </div>
                <div class="col-md-2">
                    <input type="number" class="form-control" id="deposit" placeholder="Deposit">
                </div>
                <div class="col-md-2 text-end">
                    <button class="btn btn-primary" onclick="createLeaseDraft()">Create Lease</button>
                </div>
            </div>
            <!-- Transaction Form -->
            <div class="row g-2 mt-3">
                <h3>Create Transaction</h3>
                <div class="col-md-3">
                    <input type="text" class="form-control" id="transactionListingId" placeholder="Listing ID">
                </div>
                <div class="col-md-2 text-end">
                    <button class="btn btn-primary" onclick="createTransaction()">Create Transaction</button>
                </div>
            </div>
            <!-- Chat Interface -->
            <div class="row g-2 mt-3">
                <h3>Mwarokin Assistant</h3>
                <div class="col-md-9">
                    <input type="text" class="form-control" id="userInput" placeholder="Type 'search', 'list', 'lease', 'transaction', 'kpi', or 'rag'">
                </div>
                <div class="col-md-3 text-end">
                    <button class="btn btn-primary" onclick="handleUserInput()">Send</button>
                </div>
                <div class="col-12">
                    <div id="chat-display"></div>
                    <div id="locationResult"></div>
                    <div id="currencyResult"></div>
                </div>
            </div>
            <!-- Property Container -->
            <div id="propertyContainer">
                <div class="filters">
                    <div class="filter-options">
                        <button class="filter-btn" id="bedrooms-btn">Number of Bedrooms</button>
                        <button class="filter-btn" id="sqfeet-btn">Square Feet</button>
                        <button class="filter-btn" id="amenities-btn">Amenities</button>
                        <button class="filter-btn" id="map-locator-btn">Map Locator</button>
                        <button class="filter-btn" id="street-view-btn">Street View</button>
                        <button class="filter-btn" id="nearby-home-btn">Nearby Home</button>
                        <button class="filter-btn" id="3d-tours-btn">3D Home Tours</button>
                        <button class="filter-btn" id="secure-booking-btn">Secure Booking</button>
                        <button class="filter-btn" id="review-rating-btn">Review & Rating</button>
                        <button class="filter-btn" id="smart-contracts-btn">Smart Contracts</button>
                    </div>
                </div>
                <div id="properties"></div>
            </div>
            <div id="map"></div>
            <div class="map-controls">
                <button><i class="fas fa-layer-group"></i></button>
                <button><i class="fas fa-location-dot"></i></button>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <div class="container-fluid bg-dark text-white-50 footer pt-5 mt-5">
        <div class="container py-5">
            <div class="row g-5">
                <div class="col-lg-3 col-md-6">
                    <h5 class="text-white mb-4">Mwarokin Will Assist.</h5>
                    <p class="mb-2"><i class="fa fa-map-marker-alt me-3"></i>Property App</p>
                    <p class="mb-2"><i class="fa fa-phone-alt me-3"></i>+254-704-919-388</p>
                    <p class="mb-2"><i class="fa fa-envelope me-3"></i>Property@Mwarokin.com</p>
                    <div class="d-flex pt-2">
                        <a class="btn btn-outline-light btn-social" href=""><i class="fab fa-twitter"></i></a>
                        <a class="btn btn-outline-light btn-social" href=""><i class="fab fa-facebook-f"></i></a>
                        <a class="btn btn-outline-light btn-social" href=""><i class="fab fa-youtube"></i></a>
                        <a class="btn btn-outline-light btn-social" href=""><i class="fab fa-linkedin-in"></i></a>
                    </div>
                </div>
                <div class="col-lg-3 col-md-6">
                    <h5 class="text-white mb-4">Quick Links</h5>
                    <a class="btn btn-link text-white-50" href="index.html">Home</a>
                    <a class="btn btn-link text-white-50" href="about.html">About</a>
                    <a class="btn btn-link text-white-50" href="property-list.html">Property</a>
                    <a class="btn btn-link text-white-50" href="property-type.html">Guide</a>
                    <a class="btn btn-link text-white-50" href="contact.html">Contact</a>
                    <a class="btn btn-link text-white-50" href="property-agent.html">Add Property</a>
                </div>
                <div class="col-lg-3 col-md-6">
                    <h5 class="text-white mb-4">Home Gallery</h5>
                    <div class="row g-2 pt-2">
                        <div class="col-4"><img class="img-fluid rounded bg-light p-1" src="img/property-1.jpg" alt=""></div>
                        <div class="col-4"><img class="img-fluid rounded bg-light p-1" src="img/property-2.jpg" alt=""></div>
                        <div class="col-4"><img class="img-fluid rounded bg-light p-1" src="img/property-3.jpg" alt=""></div>
                        <div class="col-4"><img class="img-fluid rounded bg-light p-1" src="img/property-4.jpg" alt=""></div>
                        <div class="col-4"><img class="img-fluid rounded bg-light p-1" src="img/property-5.jpg" alt=""></div>
                        <div class="col-4"><img class="img-fluid rounded bg-light p-1" src="img/property-6.jpg" alt=""></div>
                    </div>
                </div>
                <div class="col-lg-3 col-md-6">
                    <h5 class="text-white mb-4">Home Updates</h5>
                    <p>Mwarokin ensures we secure you a great home when availability.</p>
                    <div class="position-relative mx-auto" style="max-width: 400px;">
                        <input class="form-control bg-transparent w-100 py-3 ps-4 pe-5" type="text" placeholder="Your email">
                        <button type="button" class="btn btn-primary py-2 position-absolute top-0 end-0 mt-2 me-2">Welcome</button>
                    </div>
                </div>
            </div>
        </div>
        <div class="container">
            <div class="copyright">
                <div class="row">
                    <div class="col-md-6 text-center text-md-start mb-3 mb-md-0">
                        Mwarokin 2024-2025. All Right Reserved.

```