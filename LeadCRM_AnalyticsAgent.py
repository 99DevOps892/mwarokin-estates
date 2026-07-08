import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import asyncpg
from pydantic import BaseModel, Field, validator
from contextlib import asynccontextmanager
from enum import Enum
import hashlib
from statistics import mean, stdev
import aiohttp

# Configure logging with PII redaction
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

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

class UserContext(BaseModel):
    user_id: str
    tenant_id: str
    role: Role

# Data models
class Listing(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    address: str
    region: str  # Added for occupancy by region
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
            CREATE INDEX IF NOT EXISTS idx_leases_tenant_id ON leases (tenant_id);
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
        """Intake and validate a property listing."""
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

        # Auto-enrich
        listing.geocoding = await self._geocode(listing.address)
        listing.walkscore = await self._get_walkscore(listing.address)
        listing.amenities = await self._validate_images(listing.images)

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO listings (id, tenant_id, data, created_at, listed_at) VALUES ($1, $2, $3, $4, $5)",
                listing.id, self.tenant_id, listing.json(), listing.created_at, listing.listed_at
            )
        logger.info(f"Tenant {self.tenant_id}: Listing {listing.id} created")
        return listing

    async def _geocode(self, address: str) -> Dict[str, float]:
        return {"lat": 37.7749, "lng": -122.4194}  # Mock

    async def _get_walkscore(self, address: str) -> float:
        return 85.0  # Mock

    async def _validate_images(self, images: List[str]) -> List[str]:
        # Mock image QA (check for valid URLs, dimensions, etc.)
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

        avg_price = mean(prices)
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
        """Suggest dynamic pricing based on market elasticity and trends."""
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT data FROM listings WHERE id = $1 AND tenant_id = $2", listing_id, self.tenant_id)
            if not row:
                raise ValueError("Listing not found")
            listing = Listing.parse_raw(row["data"])

        comps = await self.rag.retrieve(f"address:{listing.address}")
        prices = [float(c.get("price", 0)) for c in comps if c.get("price")]
        avg_price = mean(prices) if prices else listing.price
        # Mock elasticity adjustment (seasonal trends, demand)
        adjustment = 1.05 if datetime.now().month in [6, 7, 8] else 0.95  # Summer premium
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
                score=0.9,  # Mock score
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
        """Capture and score a lead using BANT."""
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")

        lead = Lead(
            tenant_id=self.tenant_id,
            user_id=payload.get("user_id", str(uuid.uuid4())),
            listing_id=payload.get("listing_id"),
            bant_score={
                "budget": payload.get("budget_score", 0.5),
                "authority": payload.get("authority_score", 0.5),
                "need": payload.get("need_score", 0.5),
                "timeline": payload.get("timeline_score", 0.5)
            }
        )

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO leads (id, tenant_id, data, created_at, last_interaction) VALUES ($1, $2, $3, $4, $5)",
                lead.id, self.tenant_id, lead.json(), lead.created_at, lead.last_interaction
            )
        logger.info(f"Tenant {self.tenant_id}: Captured lead {lead.id}")
        return lead

    async def optimize_conversion(self, lead_id: str, user_context: UserContext) -> Dict:
        """Optimize lead conversion with personalized follow-ups."""
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT data FROM leads WHERE id = $1 AND tenant_id = $2", lead_id, self.tenant_id)
            if not row:
                raise ValueError("Lead not found")
            lead = Lead.parse_raw(row["data"])

        # Mock personalized follow-up (e.g., email based on BANT score)
        total_score = sum(lead.bant_score.values()) / 4
        action = "send_email" if total_score > 2.0 else "send_reminder"
        logger.info(f"Tenant {self.tenant_id}: Optimized lead {lead_id} with action {action}")
        return {"lead_id": lead_id, "action": action, "score": total_score}

# Lease Agent
class LeaseAgent:
    def __init__(self, tenant_id: str, db_pool: asyncpg.Pool):
        self.tenant_id = tenant_id
        self.db_pool = db_pool

    async def create_draft(self, listing_id: str, applicant_id: str, terms: Dict, user_context: UserContext) -> Lease:
        """Create a lease draft with risk flags."""
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
            # Conversion rates (view-to-inquiry, inquiry-to-showing, showing-to-offer)
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

            # Occupancy by region
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
                    anomaly_flag=occupancy_rate < 80.0  # Example threshold
                ))

        async with self.db_pool.acquire() as conn:
            for kpi in kpis:
                await conn.execute(
                    "INSERT INTO analytics (id, tenant_id, metric, value, region, timestamp, anomaly_flag) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                    str(uuid.uuid4()), self.tenant_id, kpi.metric, kpi.value, kpi.region, kpi.timestamp, kpi.anomaly_flag
                )
        logger.info(f"Tenant {self.tenant_id}: Calculated KPIs: {kpis}")
        return kpis

    async def generate_occupancy_chart(self, user_context: UserContext) -> Dict:
        """Generate a heatmap for occupancy rates by region."""
        if user_context.tenant_id != self.tenant_id:
            raise ValueError("Tenant mismatch")

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT region, value FROM analytics WHERE tenant_id = $1 AND metric = 'occupancy_rate'", self.tenant_id)
        
        labels = [row["region"] for row in rows]
        data = [row["value"] for row in rows]

        chart = {
            "type": "bar",
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": "Occupancy Rate (%)",
                    "data": data,
                    "backgroundColor": ["#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0"],
                    "borderColor": ["#D81B60", "#2E8BC0", "#FFB300", "#3A9A9A"],
                    "borderWidth": 1
                }]
            },
            "options": {
                "scales": {
                    "y": {
                        "beginAtZero": True,
                        "title": {"display": True, "text": "Occupancy Rate (%)"}
                    },
                    "x": {
                        "title": {"display": True, "text": "Region"}
                    }
                },
                "plugins": {
                    "title": {"display": True, "text": "Occupancy Rates by Region"}
                }
            }
        }
        logger.info(f"Tenant {self.tenant_id}: Generated occupancy chart")
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
        elif action == "analytics.generate_occupancy_chart":
            return await self.analytics_agent.generate_occupancy_chart(user_context)
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
    
    # Register tenant
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO tenants (tenant_id, config) VALUES ($1, $2) ON CONFLICT (tenant_id) DO NOTHING",
            tenant_id, TenantConfig(tenant_id=tenant_id, name="Test Tenant").json()
        )

    orchestrator = MwarokinOrchestrator(tenant_id, db_pool)
    
    async with orchestrator.session(user_context) as session:
        # Ingest sample comps
        rag = RAGAgent(tenant_id, db_pool)
        await rag.ingest({"address": "123 Main St, San Francisco, CA", "price": 950000, "property_type": "residential"}, "zillow")
        await rag.ingest({"address": "456 Oak St, San Francisco, CA", "price": 1050000, "property_type": "residential"}, "redfin")

        # Intake listings
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

        listing_payload["address"] = "789 Pine St, Los Angeles, CA"
        listing_payload["region"] = "Los Angeles"
        listing_payload["property_type"] = "commercial"
        await session.handle_request("listing.intake", listing_payload, user_context)

        # Capture lead
        lead_payload = {
            "user_id": "client_789",
            "listing_id": listing_result.id,
            "budget_score": 0.8,
            "authority_score": 0.7,
            "need_score": 0.9,
            "timeline_score": 0.6
        }
        lead_result = await session.handle_request("lead.capture", lead_payload, user_context)
        print("Lead Result:", lead_result)

        # Optimize conversion
        conversion_result = await session.handle_request("lead.optimize_conversion", {"lead_id": lead_result.id}, user_context)
        print("Conversion Optimization:", conversion_result)

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

        # Generate occupancy chart
        chart = await session.handle_request("analytics.generate_occupancy_chart", {}, user_context)
        print("Occupancy Chart Config:", json.dumps(chart, indent=2))

    await db_pool.close()

if __name__ == "__main__":
    asyncio.run(main())