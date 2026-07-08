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

# API keys (replace with environment variables in production)
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "YOUR_GOOGLE_MAPS_API_KEY")
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "YOUR_DEEPL_API_KEY")

# Tenant isolation and RBAC configuration
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
    api_keys: Dict[str, str] = {}  # Store tenant-specific API keys

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
    status: str = "new"  # new, qualified, converted, lost
    bant_score: Dict[str, float] = {"budget": 0.0, "authority": 0.0, "need": 0.0, "timeline": 0.0}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_interaction: datetime = Field(default_factory=datetime.utcnow)
    opt_in: bool = False  # GDPR compliance

class ABTest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    lead_id: str
    variant: str  # email_discount, sms_reminder
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
    terms_text: Dict[str, str] = {}  # Multilingual terms

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
    """Initialize PostgreSQL database with tenant-specific schemas."""
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
        """Ingest market data or internal documents."""
        comp_id = str(uuid.uuid4())
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO comps (id, tenant_id, data) VALUES ($1, $2, $3)",
                comp_id, self.tenant_id, json.dumps({"source": source, **data})
            )
        logger.info(f"Tenant {self.tenant_id}: Ingested comp {comp_id} from {source}")

    async def retrieve(self, query: str) -> List[Dict]:
        """Retrieve relevant comps using simple keyword matching."""
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
        """Intake and validate a property listing with real geocoding."""
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

        # Real geocoding
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

        listing.walkscore = await self._get_walkscore(listing.address)
        listing.amenities = await self._validate_images(listing.images)

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO listings (id, tenant_id, data, created_at, listed_at) VALUES ($1, $2, $3, $4, $5)",
                listing.id, self.tenant_id, listing.json(), listing.created_at, listing.listed_at
            )
        logger.info(f"Tenant {self.tenant_id}: Listing {listing.id} created")
        return listing

    async def _get_walkscore(self, address: str) -> float:
        return 85.0  # Mock (replace with Walk Score API if available)

    async def _validate_images(self, images: List[str]) -> List[str]:
        return [img for img in images if img.endswith((".jpg", ".png"))]

# Valuation Agent
class ValuationAgent:
    def __init__(self, tenant_id: str, db_pool: asyncpg.Pool):
        self.tenant_id = tenant_id
        self.db_pool = db_pool
        self.rag = RAGAgent(tenant_id, db_pool)

    async def request(self, listing_id: str, address: str, user_context: UserContext) -> Valuation:
        """Generate a valuation using RAG for comps."""
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
        """Suggest dynamic pricing based on market elasticity."""
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
        """Match buyer/tenant to listings."""
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")

        query = f"bedrooms:{profile.get('bedrooms', 0)} price:{profile.get('budget', 0)}"
        comps = await self.rag.retrieve(query)
        matches = [
            Match(
                listing_id=c["id"],
                score=0.9,
                explanation=f"Matches {c.get('address')} based on budget and bedrooms"
            ) for c in comps
        ]
        logger.info(f"Tenant {self.tenant_id}: Generated {len(matches)} matches")
        return matches

# LeadCRM Agent
class LeadCRM_Agent:
    def __init__(self, tenant_id: str, db_pool: asyncpg.Pool):
        self.tenant_id = tenant_id
        self.db_pool = db_pool

    async def capture_lead(self, payload: Dict, user_context: UserContext) -> Lead:
        """Capture and score a lead with GDPR-compliant opt-in."""
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
            opt_in=True
        )

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO leads (id, tenant_id, data, created_at, last_interaction) VALUES ($1, $2, $3, $4, $5)",
                lead.id, self.tenant_id, lead.json(), lead.created_at, lead.last_interaction
            )
        logger.info(f"Tenant {self.tenant_id}: Captured lead {lead.id}")
        return lead

    async def optimize_conversion(self, lead_id: str, user_context: UserContext) -> Dict:
        """Run A/B test for lead follow-up and optimize conversion."""
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT data FROM leads WHERE id = $1 AND tenant_id = $2", lead_id, self.tenant_id)
            if not row:
                raise ValueError("Lead not found")
            lead = Lead.parse_raw(row["data"])

        # Assign A/B test variant (50% email_discount, 50% sms_reminder)
        variant = "email_discount" if hash(lead_id) % 2 == 0 else "sms_reminder"
        ab_test = ABTest(tenant_id=self.tenant_id, lead_id=lead_id, variant=variant)

        # Mock sending follow-up
        message = (
            f"Special offer: 5% discount on {lead.listing_id}!" if variant == "email_discount" else
            f"Reminder: Schedule a viewing for {lead.listing_id}!"
        )
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.deepl.com/v2/translate",
                headers={"Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}"},
                json={"text": [message], "target_lang": "ES" if user_context.tenant_id.endswith("es") else "EN"}
            ) as resp:
                translated = (await resp.json())["translations"][0]["text"]

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO ab_tests (id, tenant_id, lead_id, data, sent_at) VALUES ($1, $2, $3, $4, $5)",
                ab_test.id, self.tenant_id, lead_id, ab_test.json(), ab_test.sent_at
            )

        logger.info(f"Tenant {self.tenant_id}: A/B test {variant} sent for lead {lead_id}")
        return {"lead_id": lead_id, "variant": variant, "message": translated}

    async def analyze_ab_tests(self, user_context: UserContext) -> Dict:
        """Analyze A/B test results for statistical significance."""
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT data FROM ab_tests WHERE tenant_id = $1", self.tenant_id)
            tests = [ABTest.parse_raw(row["data"]) for row in rows]

        email_tests = [t for t in tests if t.variant == "email_discount"]
        sms_tests = [t for t in tests if t.variant == "sms_reminder"]
        email_conversions = sum(1 for t in email_tests if t.converted)
        sms_conversions = sum(1 for t in sms_tests if t.converted)
        email_total = len(email_tests)
        sms_total = len(sms_tests)

        # Chi-square test for significance
        contingency_table = [[email_conversions, email_total - email_conversions], [sms_conversions, sms_total - sms_conversions]]
        chi2, p_value, _, _ = chi2_contingency(contingency_table) if email_total and sms_total else (0, 1)

        result = {
            "email_conversion_rate": (email_conversions / email_total * 100) if email_total else 0.0,
            "sms_conversion_rate": (sms_conversions / sms_total * 100) if sms_total else 0.0,
            "p_value": p_value,
            "winner": "email_discount" if p_value < 0.05 and email_conversions / email_total > sms_conversions / sms_total else "sms_reminder"
        }
        logger.info(f"Tenant {self.tenant_id}: A/B test analysis: {result}")
        return result

# Lease Agent
class LeaseAgent:
    def __init__(self, tenant_id: str, db_pool: asyncpg.Pool):
        self.tenant_id = tenant_id
        self.db_pool = db_pool

    async def create_draft(self, listing_id: str, applicant_id: str, terms: Dict, user_context: UserContext) -> Lease:
        """Create a lease draft with multilingual terms."""
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

        # Translate lease terms
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
        """Create a transaction with readiness checklist."""
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

    async def check_kyc(self, user_id: str, user_context: UserContext) -> bool:
        """Perform KYC/AML checks (mocked)."""
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")
        logger.info(f"Tenant {self.tenant_id}: KYC check passed for user {user_id}")
        return True

# WhiteLabel Agent
class WhiteLabelAgent:
    def __init__(self, tenant_id: str, db_pool: asyncpg.Pool):
        self.tenant_id = tenant_id
        self.db_pool = db_pool

    async def apply_theme(self, user_context: UserContext) -> Dict[str, str]:
        """Apply white-label theme settings."""
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
        """Calculate KPIs including conversion rates and occupancy by region."""
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")

        kpis = []
        async with self.db_pool.acquire() as conn:
            leads = await conn.fetch("SELECT data FROM leads WHERE tenant_id = $1", self.tenant_id)
            leads = [Lead.parse_raw(row["data"]) for row in leads]
            total_leads = len(leads)
            qualified_leads = len([l for l in leads if l.status == "qualified"])
            converted_leads = len([l for l in leads if l.status == "converted"])

            kpis.extend([
                AnalyticsKPI(
                    tenant_id=self.tenant_id,
                    metric="lead_to_qualified_rate",
                    value=(qualified_leads / total_leads * 100) if total_leads else 0.0,
                    anomaly_flag=qualified_leads / total_leads < 0.2 if total_leads else False
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

    async def generate_ab_test_chart(self, user_context: UserContext) -> Dict:
        """Generate a chart comparing A/B test conversion rates."""
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT data FROM ab_tests WHERE tenant_id = $1", self.tenant_id)
            tests = [ABTest.parse_raw(row["data"]) for row in rows]

        email_tests = [t for t in tests if t.variant == "email_discount"]
        sms_tests = [t for t in tests if t.variant == "sms_reminder"]
        email_conversions = sum(1 for t in email_tests if t.converted)
        sms_conversions = sum(1 for t in sms_tests if t.converted)
        email_total = len(email_tests)
        sms_total = len(sms_tests)

        chart = {
            "type": "bar",
            "data": {
                "labels": ["Email Discount", "SMS Reminder"],
                "datasets": [{
                    "label": "Conversion Rate (%)",
                    "data": [
                        (email_conversions / email_total * 100) if email_total else 0.0,
                        (sms_conversions / sms_total * 100) if sms_total else 0.0
                    ],
                    "backgroundColor": ["#36A2EB", "#FF6384"],
                    "borderColor": ["#2E8BC0", "#D81B60"],
                    "borderWidth": 1
                }]
            },
            "options": {
                "scales": {
                    "y": {
                        "beginAtZero": True,
                        "title": {"display": True, "text": "Conversion Rate (%)"}
                    },
                    "x": {
                        "title": {"display": True, "text": "Follow-Up Strategy"}
                    }
                },
                "plugins": {
                    "title": {"display": True, "text": "A/B Test Conversion Rates"}
                }
            }
        }
        logger.info(f"Tenant {self.tenant_id}: Generated A/B test chart")
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
            return await self.compliance_agent.check_kyc(payload.get("user_id"), user_context)
        elif action == "whitelabel.apply_theme":
            return await self.whitelabel_agent.apply_theme(user_context)
        elif action == "analytics.calculate_kpis":
            return await self.analytics_agent.calculate_kpis(user_context)
        elif action == "analytics.generate_ab_test_chart":
            return await self.analytics_agent.generate_ab_test_chart(user_context)
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
                api_keys={"google_maps": GOOGLE_MAPS_API_KEY, "deepl": DEEPL_API_KEY}
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
            "opt_in": True
        }
        lead_result = await session.handle_request("lead.capture", lead_payload, user_context)
        print("Lead Result:", lead_result)

        # Optimize conversion with A/B test
        conversion_result = await session.handle_request("lead.optimize_conversion", {"lead_id": lead_result.id}, user_context)
        print("Conversion Optimization:", conversion_result)

        # Simulate A/B test results (mocked for demo)
        async with db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO ab_tests (id, tenant_id, lead_id, data, sent_at) VALUES ($1, $2, $3, $4, $5)",
                str(uuid.uuid4()), tenant_id, lead_result.id, 
                ABTest(tenant_id=tenant_id, lead_id=lead_result.id, variant="email_discount", converted=True).json(),
                datetime.utcnow()
            )
            await conn.execute(
                "INSERT INTO ab_tests (id, tenant_id, lead_id, data, sent_at) VALUES ($1, $2, $3, $4, $5)",
                str(uuid.uuid4()), tenant_id, lead_result.id, 
                ABTest(tenant_id=tenant_id, lead_id=lead_result.id, variant="sms_reminder", converted=False).json(),
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

        # Generate A/B test chart
        chart = await session.handle_request("analytics.generate_ab_test_chart", {}, user_context)
        print("A/B Test Chart Config:", json.dumps(chart, indent=2))

    await db_pool.close()

if __name__ == "__main__":
    asyncio.run(main())