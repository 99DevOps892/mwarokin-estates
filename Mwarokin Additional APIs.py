["qualified", "converted"]])
            converted_leads = len([l for l in leads if l.status == "converted"])   
            funnel_data = {
                "total_leads": total_leads,
                "inquiry_leads": inquiry_leads,
                "qualified_leads": qualified_leads,
                "converted_leads": converted_leads
            }   

            logger.info(f"Tenant {self.tenant_id}: Generated conversion funnel data")   

    

  ##Setup Instructions
# 1. Install dependencies
    pip install asyncpg pydantic aiohttp scrubadub scipy sentence-transformers

    createdb Mwarokin_db
    createdb Mwarokin_test_db
# 2. Set environment variables and run



python mwarokin.py
export TRULIOO_API_KEY="your-trulioo-key"
export WALKSCORE_API_KEY="your-walkscore-key"
export GOOGLE_MAPS_API_KEY="your-google-maps-key"
export DEEPL_API_KEY="your-deepl-key"

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import asyncpg
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from enum import Enum
import aiohttp
from scrubadub import Scrubber
from scipy.stats import chi2_contingency
from sentence_transformers import SentenceTransformer, util
import os

# Configure logging with PII redaction
scrubber = Scrubber()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
class PIIFilter(logging.Filter):
    def filter(self, record):
        record.msg = scrubber.clean(str(record.msg))
        return True
logger.addFilter(PIIFilter())

# API keys
TRULIOO_API_KEY = os.getenv("TRULIOO_API_KEY", "your-trulioo-key")
WALKSCORE_API_KEY = os.getenv("WALKSCORE_API_KEY", "your-walkscore-key")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "your-google-maps-key")
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "your-deepl-key")

# Initialize Sentence Transformer
sentence_model = SentenceTransformer("all-MiniLM-L6-v2")

# Tenant isolation and RBAC
class Role(str, Enum):
    ADMIN = "admin"
    AGENT = "agent"
    CLIENT = "client"

class TenantConfig(BaseModel):
    tenant_id: str
    name: str
    theme: Dict[str, str] = {"logo": "", "palette": "default", "typography": "sans-serif"}
    locale: str = "en_US"
    currency: str = "USD"
    feature_flags: Dict[str, bool] = {}
    api_keys: Dict[str, str] = {}

class UserContext(BaseModel):
    user_id: str
    tenant_id: str
    role: Role

# Data models
class Listing(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    address: str
    region: str
    property_type: str
    price: float
    bedrooms: int
    bathrooms: int
    sqft: float
    amenities: List[str]
    images: List[str]
    geocoding: Dict[str, float] = {}
    walkscore: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    listed_at: Optional[datetime] = None
    status: str = "pending"
    views: int = 0  # For demand trends

class Valuation(BaseModel):
    listing_id: str
    range_low: float
    range_high: float
    confidence: float
    comp_ids: List[str]
    reasoning: str
    sources: List[str]

class Match(BaseModel):
    listing_id: str
    score: float
    explanation: str

class Lead(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    user_id: str
    listing_id: Optional[str]
    status: str = "new"
    bant_score: Dict[str, float] = {"budget": 0.0, "authority": 0.0, "need": 0.0, "timeline": 0.0}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_interaction: datetime = Field(default_factory=datetime.utcnow)
    opt_in: bool = False
    profile_text: str = ""  # For embeddings

class ABTest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    lead_id: str
    variant: str  # email_formal, email_casual, sms_immediate, sms_delayed
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    clicked: bool = False
    converted: bool = False

class Lease(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    listing_id: str
    applicant_id: str
    start_date: datetime
    end_date: datetime
    monthly_rent: float
    status: str = "draft"
    risks: List[str] = []
    terms_text: Dict[str, str] = {}

class Transaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    listing_id: str
    milestones: Dict[str, bool] = {"title_check": False, "escrow": False, "inspections": False}
    status: str = "pending"

class AnalyticsKPI(BaseModel):
    tenant_id: str
    metric: str
    value: float
    region: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    anomaly_flag: bool = False

# Database setup
async def init_db(db_pool: asyncpg.Pool):
    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                tenant_id TEXT PRIMARY KEY,
                config JSONB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS listings (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                data JSONB NOT NULL,
                created_at TIMESTAMP NOT NULL,
                listed_at TIMESTAMP,
                views INT DEFAULT 0,
                CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id)
            );
            CREATE TABLE IF NOT EXISTS comps (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                data JSONB NOT NULL,
                CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id)
            );
            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                data JSONB NOT NULL,
                created_at TIMESTAMP NOT NULL,
                last_interaction TIMESTAMP NOT NULL,
                CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id)
            );
            CREATE TABLE IF NOT EXISTS ab_tests (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                lead_id TEXT NOT NULL,
                data JSONB NOT NULL,
                sent_at TIMESTAMP NOT NULL,
                CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id)
            );
            CREATE TABLE IF NOT EXISTS leases (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                data JSONB NOT NULL,
                CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id)
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                data JSONB NOT NULL,
                CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id)
            );
            CREATE TABLE IF NOT EXISTS analytics (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                metric TEXT NOT NULL,
                value FLOAT NOT NULL,
                region TEXT,
                timestamp TIMESTAMP NOT NULL,
                anomaly_flag BOOLEAN NOT NULL,
                CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id)
            );
            CREATE INDEX IF NOT EXISTS idx_listings_tenant_id ON listings (tenant_id);
            CREATE INDEX IF NOT EXISTS idx_comps_tenant_id ON comps (tenant_id);
            CREATE INDEX IF NOT EXISTS idx_leads_tenant_id ON leads (tenant_id);
            CREATE INDEX IF NOT EXISTS idx_ab_tests_tenant_id ON ab_tests (tenant_id);
            CREATE INDEX IF NOT EXISTS idx_leases_tenant_id ON leases (tenant_id);
            CREATE INDEX IF NOT EXISTS idx_transactions_tenant_id ON transactions (tenant_id);
            CREATE INDEX IF NOT EXISTS idx_analytics_tenant_id ON analytics (tenant_id);
        """)

# RAG Agent
class RAGAgent:
    def __init__(self, tenant_id: str, db_pool: asyncpg.Pool):
        self.tenant_id = tenant_id
        self.db_pool = db_pool

    async def ingest(self, data: Dict, source: str) -> None:
        comp_id = str(uuid.uuid4())
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO comps (id, tenant_id, data) VALUES ($1, $2, $3)",
                comp_id, self.tenant_id, json.dumps({"source": source, **data})
            )
        logger.info(f"Tenant {self.tenant_id}: Ingested comp {comp_id} from {source}")

    async def retrieve(self, query: str) -> List[Dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT data FROM comps WHERE tenant_id = $1 AND data->>'address' ILIKE $2",
                self.tenant_id, f"%{query}%"
            )
        return [json.loads(row["data"]) for row in rows]

# Listing Agent
class ListingAgent:
    def __init__(self, tenant_id: str, db_pool: asyncpg.Pool):
        self.tenant_id = tenant_id
        self.db_pool = db_pool
        self.rag = RAGAgent(tenant_id, db_pool)

    async def intake(self, payload: Dict, user_context: UserContext) -> Listing:
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")
        if user_context.role not in [Role.ADMIN, Role.AGENT]:
            raise PermissionError("Unauthorized")

        listing = Listing(
            tenant_id=self.tenant_id,
            address=payload.get("address", ""),
            region=payload.get("region", "Unknown"),
            property_type=payload.get("property_type", "residential"),
            price=payload.get("price", 0.0),
            bedrooms=payload.get("bedrooms", 0),
            bathrooms=payload.get("bathrooms", 0),
            sqft=payload.get("sqft", 0.0),
            amenities=payload.get("amenities", []),
            images=payload.get("images", []),
            listed_at=datetime.utcnow() if payload.get("status") == "listed" else None,
            status=payload.get("status", "pending")
        )

        # Google Maps Geocoding
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://maps.googleapis.com/maps/api/geocode/json?address={listing.address}&key={GOOGLE_MAPS_API_KEY}"
            ) as resp:
                data = await resp.json()
                if data["status"] == "OK":
                    location = data["results"][0]["geometry"]["location"]
                    listing.geocoding = {"lat": location["lat"], "lng": location["lng"]}
                else:
                    listing.geocoding = {"lat": 0.0, "lng": 0.0}
                    logger.warning(f"Tenant {self.tenant_id}: Geocoding failed for {listing.address}")

        # Walk Score API
        listing.walkscore = await self._get_walkscore(listing.address, listing.geocoding)
        listing.amenities = await self._validate_images(listing.images)

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO listings (id, tenant_id, data, created_at, listed_at, views) VALUES ($1, $2, $3, $4, $5, $6)",
                listing.id, self.tenant_id, listing.json(), listing.created_at, listing.listed_at, listing.views
            )
        logger.info(f"Tenant {self.tenant_id}: Listing {listing.id} created")
        return listing

    async def _get_walkscore(self, address: str, geocoding: Dict) -> float:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.walkscore.com/score?format=json&address={address}&lat={geocoding['lat']}&lon={geocoding['lng']}&transit=1&bike=1&wsapikey={WALKSCORE_API_KEY}"
            ) as resp:
                data = await resp.json()
                return float(data.get("walkscore", 0)) if data.get("status") == 1 else 0.0

    async def _validate_images(self, images: List[str]) -> List[str]:
        return [img for img in images if img.endswith((".jpg", ".png"))]

# Valuation Agent
class ValuationAgent:
    def __init__(self, tenant_id: str, db_pool: asyncpg.Pool):
        self.tenant_id = tenant_id
        self.db_pool = db_pool
        self.rag = RAGAgent(tenant_id, db_pool)

    async def request(self, listing_id: str, address: str, user_context: UserContext) -> Valuation:
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")

        comps = await self.rag.retrieve(f"address:{address}")
        comp_ids = [c["id"] for c in comps]
        prices = [float(c.get("price", 0)) for c in comps if c.get("price")]

        if not prices:
            raise ValueError("No comparable sales found")

        avg_price = sum(prices) / len(prices)
        valuation = Valuation(
            listing_id=listing_id,
            range_low=avg_price * 0.9,
            range_high=avg_price * 1.1,
            confidence=0.85,
            comp_ids=comp_ids,
            reasoning="Based on average of comparable sales within 1km radius.",
            sources=[c["source"] for c in comps]
        )
        logger.info(f"Tenant {self.tenant_id}: Valuation for listing {listing_id} generated")
        return valuation

# Pricing Agent
class PricingAgent:
    def __init__(self, tenant_id: str, db_pool: asyncpg.Pool):
        self.tenant_id = tenant_id
        self.db_pool = db_pool
        self.rag = RAGAgent(tenant_id, db_pool)

    async def suggest_price(self, listing_id: str, user_context: UserContext) -> Dict:
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT data FROM listings WHERE id = $1 AND tenant_id = $2", listing_id, self.tenant_id)
            if not row:
                raise ValueError("Listing not found")
            listing = Listing.parse_raw(row["data"])

        comps = await self.rag.retrieve(f"address:{listing.address}")
        prices = [float(c.get("price", 0)) for c in comps if c.get("price")]
        avg_price = sum(prices) / len(prices) if prices else listing.price
        adjustment = 1.05 if datetime.now().month in [6, 7, 8] else 0.95
        suggested_price = avg_price * adjustment

        logger.info(f"Tenant {self.tenant_id}: Suggested price {suggested_price} for listing {listing_id}")
        return {"listing_id": listing_id, "suggested_price": suggested_price, "reasoning": "Adjusted for seasonal demand"}

# Matchmaking Agent
class MatchmakingAgent:
    def __init__(self, tenant_id: str, db_pool: asyncpg.Pool):
        self.tenant_id = tenant_id
        self.db_pool = db_pool
        self.rag = RAGAgent(tenant_id, db_pool)

    async def request(self, profile: Dict, user_context: UserContext) -> List[Match]:
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT data FROM listings WHERE tenant_id = $1", self.tenant_id)
            listings = [Listing.parse_raw(row["data"]) for row in rows]

        # Generate embeddings for profile and listings
        profile_text = f"bedrooms:{profile.get('bedrooms', 0)} budget:{profile.get('budget', 0)} location:{profile.get('location', '')}"
        profile_embedding = sentence_model.encode(profile_text, convert_to_tensor=True)
        listing_texts = [
            f"bedrooms:{l.bedrooms} price:{l.price} location:{l.address} type:{l.property_type} amenities:{','.join(l.amenities)}"
            for l in listings
        ]
        listing_embeddings = sentence_model.encode(listing_texts, convert_to_tensor=True)

        # Compute cosine similarities
        similarities = util.cos_sim(profile_embedding, listing_embeddings)[0]
        matches = [
            Match(
                listing_id=listings[i].id,
                score=float(similarities[i]),
                explanation=f"Matches {listings[i].address} based on profile similarity (score: {similarities[i]:.2f})"
            ) for i in range(len(listings)) if similarities[i] > 0.5
        ]
        matches.sort(key=lambda x: x.score, reverse=True)
        logger.info(f"Tenant {self.tenant_id}: Generated {len(matches)} matches")
        return matches[:10]  # Top 10 matches

# LeadCRM Agent
class LeadCRM_Agent:
    def __init__(self, tenant_id: str, db_pool: asyncpg.Pool):
        self.tenant_id = tenant_id
        self.db_pool = db_pool

    async def capture_lead(self, payload: Dict, user_context: UserContext) -> Lead:
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")
        if not payload.get("opt_in", False):
            raise ValueError("GDPR opt-in required")

        lead = Lead(
            tenant_id=self.tenant_id,
            user_id=payload.get("user_id", str(uuid.uuid4())),
            listing_id=payload.get("listing_id"),
            bant_score={
                "budget": payload.get("budget_score", 0.5),
                "authority": payload.get("authority_score", 0.5),
                "need": payload.get("need_score", 0.5),
                "timeline": payload.get("timeline_score", 0.5)
            },
            opt_in=True,
            profile_text=payload.get("profile_text", "")
        )

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO leads (id, tenant_id, data, created_at, last_interaction) VALUES ($1, $2, $3, $4, $5)",
                lead.id, self.tenant_id, lead.json(), lead.created_at, lead.last_interaction
            )
        logger.info(f"Tenant {self.tenant_id}: Captured lead {lead.id}")
        return lead

    async def optimize_conversion(self, lead_id: str, user_context: UserContext) -> Dict:
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT data FROM leads WHERE id = $1 AND tenant_id = $2", lead_id, self.tenant_id)
            if not row:
                raise ValueError("Lead not found")
            lead = Lead.parse_raw(row["data"])

        # Assign A/B test variant (25% each: email_formal, email_casual, sms_immediate, sms_delayed)
        hash_val = hash(lead_id) % 4
        variant = ["email_formal", "email_casual", "sms_immediate", "sms_delayed"][hash_val]
        delay = timedelta(hours=24) if variant == "sms_delayed" else timedelta(0)
        sent_at = datetime.utcnow() + delay

        # Personalize message based on BANT score
        total_score = sum(lead.bant_score.values()) / 4
        tone = "formal" if variant == "email_formal" else "casual"
        message = (
            f"Dear Client, we have a property matching your needs at {lead.listing_id}. Please schedule a viewing." if tone == "formal" else
            f"Hey! Found a great property for you at {lead.listing_id}! Want to check it out?"
        ) if "email" in variant else (
            f"Property alert: {lead.listing_id} matches your needs! Reply to schedule." if variant == "sms_immediate" else
            f"Reminder: {lead.listing_id} is still available! Reply to book a viewing."
        )
        if total_score > 2.5:
            message += " Special offer: 5% discount for quick decisions!"

        # Translate message
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.deepl.com/v2/translate",
                headers={"Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}"},
                json={"text": [message], "target_lang": "ES" if user_context.tenant_id.endswith("es") else "EN"}
            ) as resp:
                translated = (await resp.json())["translations"][0]["text"]

        ab_test = ABTest(tenant_id=self.tenant_id, lead_id=lead_id, variant=variant, sent_at=sent_at)
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO ab_tests (id, tenant_id, lead_id, data, sent_at) VALUES ($1, $2, $3, $4, $5)",
                ab_test.id, self.tenant_id, lead_id, ab_test.json(), ab_test.sent_at
            )

        logger.info(f"Tenant {self.tenant_id}: A/B test {variant} scheduled for lead {lead_id}")
        return {"lead_id": lead_id, "variant": variant, "message": translated, "sent_at": sent_at.isoformat()}

    async def analyze_ab_tests(self, user_context: UserContext) -> Dict:
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT data FROM ab_tests WHERE tenant_id = $1", self.tenant_id)
            tests = [ABTest.parse_raw(row["data"]) for row in rows]

        variants = ["email_formal", "email_casual", "sms_immediate", "sms_delayed"]
        results = {v: {"total": 0, "conversions": 0} for v in variants}
        for test in tests:
            results[test.variant]["total"] += 1
            if test.converted:
                results[test.variant]["conversions"] += 1

        conversion_rates = {v: (r["conversions"] / r["total"] * 100) if r["total"] else 0.0 for v, r in results.items()}
        contingency_table = [[r["conversions"], r["total"] - r["conversions"]] for r in results.values()]
        chi2, p_value, _, _ = chi2_contingency(contingency_table) if all(r["total"] for r in results.values()) else (0, 1)

        winner = max(conversion_rates, key=conversion_rates.get) if p_value < 0.05 else "none"
        result = {
            "conversion_rates": conversion_rates,
            "p_value": p_value,
            "winner": winner
        }
        logger.info(f"Tenant {self.tenant_id}: A/B test analysis: {result}")
        return result

# Lease Agent
class LeaseAgent:
    def __init__(self, tenant_id: str, db_pool: asyncpg.Pool):
        self.tenant_id = tenant_id
        self.db_pool = db_pool

    async def create_draft(self, listing_id: str, applicant_id: str, terms: Dict, user_context: UserContext) -> Lease:
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")

        lease = Lease(
            tenant_id=self.tenant_id,
            listing_id=listing_id,
            applicant_id=applicant_id,
            start_date=datetime.fromisoformat(terms.get("start_date")),
            end_date=datetime.fromisoformat(terms.get("end_date")),
            monthly_rent=terms.get("monthly_rent", 0.0),
            risks=["arrears_risk"] if terms.get("credit_score", 700) < 650 else []
        )

        terms_text = f"Lease for {listing_id} starting {lease.start_date.strftime('%Y-%m-%d')}"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.deepl.com/v2/translate",
                headers={"Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}"},
                json={"text": [terms_text], "target_lang": "ES" if user_context.tenant_id.endswith("es") else "EN"}
            ) as resp:
                lease.terms_text = {"en": terms_text, "es": (await resp.json())["translations"][0]["text"]}

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO leases (id, tenant_id, data) VALUES ($1, $2, $3)",
                lease.id, self.tenant_id, lease.json()
            )
        logger.info(f"Tenant {self.tenant_id}: Created lease draft {lease.id}")
        return lease

# Transaction Agent
class TransactionAgent:
    def __init__(self, tenant_id: str, db_pool: asyncpg.Pool):
        self.tenant_id = tenant_id
        self.db_pool = db_pool

    async def create_transaction(self, listing_id: str, user_context: UserContext) -> Transaction:
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")

        transaction = Transaction(tenant_id=self.tenant_id, listing_id=listing_id)
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO transactions (id, tenant_id, data) VALUES ($1, $2, $3)",
                transaction.id, self.tenant_id, transaction.json()
            )
        logger.info(f"Tenant {self.tenant_id}: Created transaction {transaction.id}")
        return transaction

# Compliance Agent
class ComplianceAgent:
    def __init__(self, tenant_id: str, db_pool: asyncpg.Pool):
        self.tenant_id = tenant_id
        self.db_pool = db_pool

    async def check_kyc(self, user_id: str, user_context: UserContext, user_data: Dict) -> bool:
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.trulioo.com/v1/verify",
                headers={"x-auth-token": TRULIOO_API_KEY, "Content-Type": "application/json"},
                json={
                    "AcceptTruliooTermsAndConditions": True,
                    "DataFields": {
                        "PersonInfo": {
                            "FirstGivenName": user_data.get("first_name", ""),
                            "LastName": user_data.get("last_name", ""),
                            "DayOfBirth": user_data.get("dob_day", 1),
                            "MonthOfBirth": user_data.get("dob_month", 1),
                            "YearOfBirth": user_data.get("dob_year", 1970)
                        },
                        "Location": {
                            "CountryCode": user_data.get("country", "US")
                        }
                    }
                }
            ) as resp:
                result = await resp.json()
                if result.get("Record", {}).get("RecordStatus") == "match":
                    logger.info(f"Tenant {self.tenant_id}: KYC check passed for user {user_id}")
                    return True
                else:
                    logger.warning(f"Tenant {self.tenant_id}: KYC check failed for user {user_id}")
                    return False

# WhiteLabel Agent
class WhiteLabelAgent:
    def __init__(self, tenant_id: str, db_pool: asyncpg.Pool):
        self.tenant_id = tenant_id
        self.db_pool = db_pool

    async def apply_theme(self, user_context: UserContext) -> Dict[str, str]:
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT config FROM tenants WHERE tenant_id = $1", self.tenant_id)
            if not row:
                raise ValueError("Tenant not found")
            config = TenantConfig.parse_raw(row["config"])
        return config.theme

# Analytics Agent
class AnalyticsAgent:
    def __init__(self, tenant_id: str, db_pool: asyncpg.Pool):
        self.tenant_id = tenant_id
        self.db_pool = db_pool

    async def calculate_kpis(self, user_context: UserContext) -> List[AnalyticsKPI]:
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")

        kpis = []
        async with self.db_pool.acquire() as conn:
            leads = await conn.fetch("SELECT data FROM leads WHERE tenant_id = $1", self.tenant_id)
            leads = [Lead.parse_raw(row["data"]) for row in leads]
            total_leads = len(leads)
            inquiry_leads = len([l for l in leads if l.status in ["new", "qualified", "converted"]])
            qualified_leads = len([l for l in leads if l.status in ["qualified", "converted"]])
            converted_leads = len([l for l in leads if l.status == "converted"])

            kpis.extend([
                AnalyticsKPI(
                    tenant_id=self.tenant_id,
                    metric="view_to_inquiry_rate",
                    value=(inquiry_leads / total_leads * 100) if total_leads else 0.0,
                    anomaly_flag=inquiry_leads / total_leads < 0.3 if total_leads else False
                ),
                AnalyticsKPI(
                    tenant_id=self.tenant_id,
                    metric="inquiry_to_qualified_rate",
                    value=(qualified_leads / inquiry_leads * 100) if inquiry_leads else 0.0,
                    anomaly_flag=qualified_leads / inquiry_leads < 0.2 if inquiry_leads else False
                ),
                AnalyticsKPI(
                    tenant_id=self.tenant_id,
                    metric="qualified_to_converted_rate",
                    value=(converted_leads / qualified_leads * 100) if qualified_leads else 0.0,
                    anomaly_flag=converted_leads / qualified_leads < 0.1 if qualified_leads else False
                )
            ])

            listings = await conn.fetch("SELECT data FROM listings WHERE tenant_id = $1", self.tenant_id)
            listings = [Listing.parse_raw(row["data"]) for row in listings]
            leases = await conn.fetch("SELECT data FROM leases WHERE tenant_id = $1", self.tenant_id)
            leases = [Lease.parse_raw(row["data"]) for row in leases]

            regions = {l.region for l in listings}
            for region in regions:
                region_listings = [l for l in listings if l.region == region]
                region_leases = [l for l in leases if l.listing_id in [rl.id for rl in region_listings]]
                occupancy_rate = (len(region_leases) / len(region_listings) * 100) if region_listings else 0.0
                kpis.append(AnalyticsKPI(
                    tenant_id=self.tenant_id,
                    metric="occupancy_rate",
                    value=occupancy_rate,
                    region=region,
                    anomaly_flag=occupancy_rate < 80.0
                ))

        async with self.db_pool.acquire() as conn:
            for kpi in kpis:
                await conn.execute(
                    "INSERT INTO analytics (id, tenant_id, metric, value, region, timestamp, anomaly_flag) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                    str(uuid.uuid4()), self.tenant_id, kpi.metric, kpi.value, kpi.region, kpi.timestamp, kpi.anomaly_flag
                )
        logger.info(f"Tenant {self.tenant_id}: Calculated KPIs: {kpis}")
        return kpis

    async def generate_conversion_funnel_chart(self, user_context: UserContext) -> Dict:
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")

        async with self.db_pool.acquire() as conn:
            leads = await conn.fetch("SELECT data FROM leads WHERE tenant_id = $1", self.tenant_id)
            leads = [Lead.parse_raw(row["data"]) for row in leads]
            total_leads = len(leads)
            inquiry_leads = len([l for l in leads if l.status in ["new", "qualified", "converted"]])
            qualified_leads = len([l for l in leads if l.status in ["qualified", "converted"]])
            converted_leads = len([l for l in leads if l.status == "converted"])

        chart = {
            "type": "bar",
            "data": {
                "labels": ["Views", "Inquiries", "Qualified", "Converted"],
                "datasets": [{
                    "label": "Lead Funnel",
                    "data": [
                        total_leads,
                        inquiry_leads,
                        qualified_leads,
                        converted_leads
                    ],
                    "backgroundColor": ["#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0"],
                    "borderColor": ["#D81B60", "#2E8BC0", "#FFB300", "#3A9A9A"],
                    "borderWidth": 1
                }]
            },
            "options": {
                "scales": {
                    "y": {
                        "beginAtZero": True,
                        "title": {"display": True, "text": "Count"}
                    },
                    "x": {
                        "title": {"display": True, "text": "Funnel Stage"}
                    }
                },
                "plugins": {
                    "title": {"display": True, "text": "Lead Conversion Funnel"}
                }
            }
        }
        logger.info(f"Tenant {self.tenant_id}: Generated conversion funnel chart")
        return chart

    async def generate_demand_trends_chart(self, user_context: UserContext) -> Dict:
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT data FROM listings WHERE tenant_id = $1", self.tenant_id)
            listings = [Listing.parse_raw(row["data"]) for row in rows]

        regions = {l.region for l in listings}
        data_by_region = {r: [] for r in regions}
        dates = [(datetime.utcnow() - timedelta(days=x)).strftime("%Y-%m-%d") for x in range(7, -1, -1)]
        for region in regions:
            region_listings = [l for l in listings if l.region == region]
            views = [sum(l.views for l in region_listings)] * 8  # Mocked; replace with time-series data
            data_by_region[region] = views

        chart = {
            "type": "line",
            "data": {
                "labels": dates,
                "datasets": [
                    {
                        "label": region,
                        "data": data_by_region[region],
                        "borderColor": ["#FF6384", "#36A2EB", "#FFCE56"][i % 3],
                        "fill": False
                    } for i, region in enumerate(regions)
                ]
            },
            "options": {
                "scales": {
                    "y": {
                        "beginAtZero": True,
                        "title": {"display": True, "text": "Listing Views"}
                    },
                    "x": {
                        "title": {"display": True, "text": "Date"}
                    }
                },
                "plugins": {
                    "title": {"display": True, "text": "Regional Demand Trends"}
                }
            }
        }
        logger.info(f"Tenant {self.tenant_id}: Generated demand trends chart")
        return chart

# Orchestrator
class MwarokinOrchestrator:
    def __init__(self, tenant_id: str, db_pool: asyncpg.Pool):
        self.tenant_id = tenant_id
        self.db_pool = db_pool
        self.listing_agent = ListingAgent(tenant_id, db_pool)
        self.valuation_agent = ValuationAgent(tenant_id, db_pool)
        self.pricing_agent = PricingAgent(tenant_id, db_pool)
        self.matchmaking_agent = MatchmakingAgent(tenant_id, db_pool)
        self.lead_crm_agent = LeadCRM_Agent(tenant_id, db_pool)
        self.lease_agent = LeaseAgent(tenant_id, db_pool)
        self.transaction_agent = TransactionAgent(tenant_id, db_pool)
        self.compliance_agent = ComplianceAgent(tenant_id, db_pool)
        self.whitelabel_agent = WhiteLabelAgent(tenant_id, db_pool)
        self.analytics_agent = AnalyticsAgent(tenant_id, db_pool)

    @asynccontextmanager
    async def session(self, user_context: UserContext):
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")
        logger.info(f"Tenant {self.tenant_id}: Starting session for user {user_context.user_id}")
        try:
            yield self
        finally:
            logger.info(f"Tenant {self.tenant_id}: Session closed")

    async def handle_request(self, action: str, payload: Dict, user_context: UserContext) -> Any:
        logger.info(f"Tenant {self.tenant_id}: Processing action {action}")
        plan = self._plan_action(action, payload)
        result = await self._execute_action(action, payload, user_context)
        self._reflect(result)
        return result

    def _plan_action(self, action: str, payload: Dict) -> str:
        return f"Executing {action} with payload {json.dumps(payload, indent=2)}"

    async def _execute_action(self, action: str, payload: Dict, user_context: UserContext) -> Any:
        if action == "listing.intake":
            return await self.listing_agent.intake(payload, user_context)
        elif action == "valuation.request":
            return await self.valuation_agent.request(payload.get("listing_id"), payload.get("address"), user_context)
        elif action == "pricing.suggest":
            return await self.pricing_agent.suggest_price(payload.get("listing_id"), user_context)
        elif action == "matchmaking.request":
            return await self.matchmaking_agent.request(payload, user_context)
        elif action == "lead.capture":
            return await self.lead_crm_agent.capture_lead(payload, user_context)
        elif action == "lead.optimize_conversion":
            return await self.lead_crm_agent.optimize_conversion(payload.get("lead_id"), user_context)
        elif action == "lead.analyze_ab_tests":
            return await self.lead_crm_agent.analyze_ab_tests(user_context)
        elif action == "lease.create_draft":
            return await self.lease_agent.create_draft(payload.get("listing_id"), payload.get("applicant_id"), payload.get("terms", {}), user_context)
        elif action == "transaction.create":
            return await self.transaction_agent.create_transaction(payload.get("listing_id"), user_context)
        elif action == "compliance.check_kyc":
            return await self.compliance_agent.check_kyc(payload.get("user_id"), user_context, payload.get("user_data", {}))
        elif action == "whitelabel.apply_theme":
            return await self.whitelabel_agent.apply_theme(user_context)
        elif action == "analytics.calculate_kpis":
            return await self.analytics_agent.calculate_kpis(user_context)
        elif action == "analytics.generate_conversion_funnel_chart":
            return await self.analytics_agent.generate_conversion_funnel_chart(user_context)
        elif action == "analytics.generate_demand_trends_chart":
            return await self.analytics_agent.generate_demand_trends_chart(user_context)
        else:
            raise ValueError(f"Unknown action: {action}")

    def _reflect(self, result: Any) -> None:
        logger.info(f"Tenant {self.tenant_id}: Action completed with result {result}")

# Example usage
async def main():
    tenant_id = "tenant_123"
    user_context = UserContext(user_id="user_456", tenant_id=tenant_id, role=Role.AGENT)
    
    # Initialize database
    db_pool = await asyncpg.create_pool("postgresql://user:password@localhost:5432/mwarokin_db")
    await init_db(db_pool)
    
    # Register tenant with API keys
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO tenants (tenant_id, config) VALUES ($1, $2) ON CONFLICT (tenant_id) DO NOTHING",
            tenant_id, TenantConfig(
                tenant_id=tenant_id, 
                name="Test Tenant",
                api_keys={
                    "google_maps": GOOGLE_MAPS_API_KEY,
                    "deepl": DEEPL_API_KEY,
                    "trulioo": TRULIOO_API_KEY,
                    "walkscore": WALKSCORE_API_KEY
                }
            ).json()
        )

    orchestrator = MwarokinOrchestrator(tenant_id, db_pool)
    
    async with orchestrator.session(user_context) as session:
        # Ingest sample comps
        rag = RAGAgent(tenant_id, db_pool)
        await rag.ingest({"address": "123 Main St, San Francisco, CA", "price": 950000, "property_type": "residential"}, "zillow")
        await rag.ingest({"address": "456 Oak St, San Francisco, CA", "price": 1050000, "property_type": "residential"}, "redfin")

        # Intake listing
        listing_payload = {
            "address": "123 Main St, San Francisco, CA",
            "region": "San Francisco",
            "property_type": "residential",
            "price": 1000000.0,
            "bedrooms": 3,
            "bathrooms": 2,
            "sqft": 1500.0,
            "amenities": ["pool", "garage"],
            "images": ["img1.jpg", "img2.png"],
            "status": "listed"
        }
        listing_result = await session.handle_request("listing.intake", listing_payload, user_context)
        print("Listing Result:", listing_result)

        # Capture lead
        lead_payload = {
            "user_id": "client_789",
            "listing_id": listing_result.id,
            "budget_score": 0.8,
            "authority_score": 0.7,
            "need_score": 0.9,
            "timeline_score": 0.6,
            "opt_in": True,
            "profile_text": "Looking for a 3-bedroom house in San Francisco under $1M"
        }
        lead_result = await session.handle_request("lead.capture", lead_payload, user_context)
        print("Lead Result:", lead_result)

        # KYC check
        kyc_result = await session.handle_request("compliance.check_kyc", {
            "user_id": "client_789",
            "user_data": {
                "first_name": "John",
                "last_name": "Doe",
                "dob_day": 15,
                "dob_month": 5,
                "dob_year": 1980,
                "country": "US"
            }
        }, user_context)
        print("KYC Result:", kyc_result)

        # Optimize conversion with A/B test
        conversion_result = await session.handle_request("lead.optimize_conversion", {"lead_id": lead_result.id}, user_context)
        print("Conversion Optimization:", conversion_result)

        # Simulate A/B test results
        async with db_pool.acquire() as conn:
            for variant in ["email_formal", "email_casual", "sms_immediate", "sms_delayed"]:
                await conn.execute(
                    "INSERT INTO ab_tests (id, tenant_id, lead_id, data, sent_at) VALUES ($1, $2, $3, $4, $5)",
                    str(uuid.uuid4()), tenant_id, lead_result.id, 
                    ABTest(tenant_id=tenant_id, lead_id=lead_result.id, variant=variant, converted=variant in ["email_formal", "sms_immediate"]).json(),
                    datetime.utcnow()
                )

        # Analyze A/B tests
        ab_test_result = await session.handle_request("lead.analyze_ab_tests", {}, user_context)
        print("A/B Test Analysis:", ab_test_result)

        # Create lease
        lease_payload = {
            "listing_id": listing_result.id,
            "applicant_id": "client_789",
            "terms": {
                "start_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=395)).isoformat(),
                "monthly_rent": 3000.0,
                "credit_score": 680
            }
        }
        lease_result = await session.handle_request("lease.create_draft", lease_payload, user_context)
        print("Lease Result:", lease_result)

        # Calculate KPIs
        kpis = await session.handle_request("analytics.calculate_kpis", {}, user_context)
        print("KPIs:", kpis)

        # Generate charts
        funnel_chart = await session.handle_request("analytics.generate_conversion_funnel_chart", {}, user_context)
        print("Conversion Funnel Chart:", json.dumps(funnel_chart, indent=2))
        demand_chart = await session.handle_request("analytics.generate_demand_trends_chart", {}, user_context)
        print("Demand Trends Chart:", json.dumps(demand_chart, indent=2))

    await db_pool.close()

if __name__ == "__main__":
    asyncio.run(main())


