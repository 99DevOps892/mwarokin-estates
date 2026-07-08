import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Integer, DateTime, JSON, Text, select
import logging
from contextlib import asynccontextmanager
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Mwarokin")

# Database Setup
DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/mwarokin"
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

# SQLAlchemy Models
class Base(DeclarativeBase):
    pass

class ListingDB(Base):
    __tablename__ = "listings"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    address: Mapped[str] = mapped_column(String)
    property_type: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bedrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    square_feet: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class BuyerProfileDB(Base):
    __tablename__ = "buyer_profiles"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    preferences: Mapped[Dict] = mapped_column(JSON)  # e.g., {"bedrooms": 2, "max_price": 500000}
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class LeaseDB(Base):
    __tablename__ = "leases"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    listing_id: Mapped[str] = mapped_column(String)
    applicant_id: Mapped[str] = mapped_column(String)
    clauses: Mapped[Dict] = mapped_column(JSON)
    payment_schedule: Mapped[Dict] = mapped_column(JSON)
    risks: Mapped[List[str]] = mapped_column(JSON, default=[])
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class TenantConfigDB(Base):
    __tablename__ = "tenant_configs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    role: Mapped[str] = mapped_column(String)
    white_label: Mapped[Dict] = mapped_column(JSON)  # e.g., {"logo": "url", "palette": {"primary": "#3182ce"}}
    locale: Mapped[str] = mapped_column(String, default="en_US")
    currency: Mapped[str] = mapped_column(String, default="USD")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    action: Mapped[str] = mapped_column(String)
    details: Mapped[Dict] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# Pydantic Models
class Role(str, Enum):
    ADMIN = "admin"
    AGENT = "agent"
    USER = "user"

class TenantConfig(BaseModel):
    tenant_id: str
    role: Role
    white_label: Dict[str, str] = {}
    locale: str = "en_US"
    currency: str = "USD"

class BuyerProfile(BaseModel):
    tenant_id: str
    profile_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    preferences: Dict  # e.g., {"bedrooms": 2, "max_price": 500000}

class LeaseDraftPayload(BaseModel):
    tenant_id: str
    listing_id: str
    applicant_id: str
    terms: Dict  # e.g., {"duration_months": 12, "monthly_rent": 2000}

class LeaseDraft(BaseModel):
    clauses: Dict
    schedule: Dict
    risks: List[str]

class Match(BaseModel):
    listing_id: str
    score: float
    explanation: str

class Theme(BaseModel):
    css: str
    js: str
    logo_url: str
    metadata: Dict

# Security and RBAC
api_key_header = APIKeyHeader(name="X-API-Key")

def require_role(min_role: Role):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, tenant_config: TenantConfig = Depends(get_tenant_config), **kwargs):
            if tenant_config.role.value < min_role.value:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return await func(*args, tenant_config=tenant_config, **kwargs)
        return wrapper
    return decorator

async def get_tenant_config(api_key: str = Depends(api_key_header)) -> TenantConfig:
    async with async_session() as db:
        result = await db.execute(select(TenantConfigDB).where(TenantConfigDB.tenant_id == api_key))
        tenant = result.scalars().first()
        if not tenant:
            raise HTTPException(status_code=403, detail="Invalid tenant")
        return TenantConfig(
            tenant_id=tenant.tenant_id,
            role=Role(tenant.role),
            white_label=tenant.white_label,
            locale=tenant.locale,
            currency=tenant.currency
        )

# Database Dependency
async def get_db():
    async with async_session() as session:
        yield session

# WhiteLabelAgent
class WhiteLabelAgent:
    async def get_theme(self, tenant_config: TenantConfig, db: AsyncSession) -> Theme:
        result = await db.execute(select(TenantConfigDB).where(TenantConfigDB.tenant_id == tenant_config.tenant_id))
        tenant = result.scalars().first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant config not found")

        # Generate dynamic CSS
        palette = tenant.white_label.get("palette", {"primary": "#3182ce", "secondary": "#2c5282"})
        css = f"""
        :root {{
            --primary-color: {palette.get("primary", "#3182ce")};
            --secondary-color: {palette.get("secondary", "#2c5282")};
        }}
        header {{
            background: linear-gradient(120deg, {palette.get("primary", "#3182ce")}, {palette.get("secondary", "#2c5282")});
        }}
        .search-btn, .view-btn, .control-btn, .region-btn.active {{
            background: {palette.get("primary", "#3182ce")};
        }}
        .search-btn:hover, .view-btn:hover, .control-btn:hover, .region-btn.active:hover {{
            background: {palette.get("secondary", "#2c5282")};
        }}
        """
        js = """
        // Dynamic tenant-specific JS (e.g., custom animations)
        console.log('Tenant-specific theme loaded');
        """
        return Theme(
            css=css,
            js=js,
            logo_url=tenant.white_label.get("logo", "default_logo.png"),
            metadata={"locale": tenant.locale, "currency": tenant.currency}
        )

# LeaseAgent
class LeaseAgent:
    async def execute(self, payload: Dict, tenant_config: TenantConfig, db: AsyncSession) -> LeaseDraft:
        payload = LeaseDraftPayload(**payload)
        if payload.tenant_id != tenant_config.tenant_id:
            raise HTTPException(status_code=403, detail="Tenant ID mismatch")

        # Validate listing and applicant
        listing_result = await db.execute(select(ListingDB).where(ListingDB.id == payload.listing_id, ListingDB.tenant_id == tenant_config.tenant_id))
        listing = listing_result.scalars().first()
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")

        profile_result = await db.execute(select(BuyerProfileDB).where(BuyerProfileDB.id == payload.applicant_id, BuyerProfileDB.tenant_id == tenant_config.tenant_id))
        profile = profile_result.scalars().first()
        if not profile:
            raise HTTPException(status_code=404, detail="Applicant not found")

        # Generate lease draft (mock clauses and schedule)
        clauses = {"duration": payload.terms.get("duration_months", 12), "rent": payload.terms.get("monthly_rent", 2000)}
        schedule = {"start_date": "2025-10-01", "payments": [{"date": "2025-11-01", "amount": clauses["rent"]}]}
        risks = ["Credit check pending"] if "credit_score" not in profile.preferences else []

        # Save to database
        lease = LeaseDB(
            tenant_id=tenant_config.tenant_id,
            listing_id=payload.listing_id,
            applicant_id=payload.applicant_id,
            clauses=clauses,
            payment_schedule=schedule,
            risks=risks
        )
        db.add(lease)
        await db.commit()

        # Log action
        await self.log_action(db, tenant_config.tenant_id, "lease_draft_created", {"lease_id": lease.id})

        return LeaseDraft(clauses=clauses, schedule=schedule, risks=risks)

    async def log_action(self, db: AsyncSession, tenant_id: str, action: str, details: Dict):
        redacted_details = {k: "REDACTED" if k in ["name", "address", "dob"] else v for k, v in details.items()}
        audit_log = AuditLog(tenant_id=tenant_id, action=action, details=redacted_details)
        db.add(audit_log)
        await db.commit()

# MatchmakingAgent
class MatchmakingAgent:
    async def execute(self, payload: Dict, tenant_config: TenantConfig, db: AsyncSession) -> List[Match]:
        profile_id = payload.get("profile_id")
        if not profile_id:
            raise HTTPException(status_code=400, detail="Profile ID required")

        # Fetch profile
        profile_result = await db.execute(select(BuyerProfileDB).where(BuyerProfileDB.id == profile_id, BuyerProfileDB.tenant_id == tenant_config.tenant_id))
        profile = profile_result.scalars().first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        # Fetch listings
        listings_result = await db.execute(select(ListingDB).where(ListingDB.tenant_id == tenant_config.tenant_id))
        listings = listings_result.scalars().all()

        # Match listings (mock scoring)
        matches = []
        for listing in listings:
            score = self.calculate_match_score(profile.preferences, {
                "bedrooms": listing.bedrooms,
                "price": listing.price,
                "location": listing.address
            })
            matches.append(Match(
                listing_id=listing.id,
                score=score,
                explanation=f"Match based on {profile.preferences} vs {listing.address}"
            ))

        # Log action
        await self.log_action(db, tenant_config.tenant_id, "matchmaking_request", {"profile_id": profile_id, "matches": len(matches)})

        return sorted(matches, key=lambda x: x.score, reverse=True)[:5]

    def calculate_match_score(self, preferences: Dict, features: Dict) -> float:
        # Mock scoring (replace with embeddings-based similarity)
        score = 0.9 if preferences.get("bedrooms") == features.get("bedrooms") and preferences.get("max_price", float("inf")) >= features.get("price", 0) else 0.7
        return score

    async def log_action(self, db: AsyncSession, tenant_id: str, action: str, details: Dict):
        redacted_details = {k: "REDACTED" if k in ["name", "address", "dob"] else v for k, v in details.items()}
        audit_log = AuditLog(tenant_id=tenant_id, action=action, details=redacted_details)
        db.add(audit_log)
        await db.commit()

# Orchestrator
class Orchestrator:
    def __init__(self):
        self.agents = {
            "lease": LeaseAgent(),
            "matchmaking": MatchmakingAgent(),
            "whitelabel": WhiteLabelAgent(),
            # Add other agents (ComplianceAgent, etc.) from previous implementation
        }

    async def process_task(self, task_type: str, payload: Dict, tenant_config: TenantConfig, db: AsyncSession) -> Dict:
        agent = self.agents.get(task_type)
        if not agent:
            raise HTTPException(status_code=400, detail="Invalid task type")

        logger.info(f"Planning {task_type} for tenant {tenant_config.tenant_id}")
        try:
            result = await agent.execute(payload, tenant_config, db)
            logger.info(f"Completed {task_type}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in {task_type}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

# FastAPI App
app = FastAPI(title="Mwarokin Real Estate OS")

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app.router.lifespan = lifespan

# API Endpoints
orchestrator = Orchestrator()

@app.post("/lease/create_draft")
@require_role(Role.AGENT)
async def create_lease_draft(payload: LeaseDraftPayload, tenant_config: TenantConfig = Depends(get_tenant_config), db: AsyncSession = Depends(get_db)):
    return await orchestrator.process_task("lease", payload.dict(), tenant_config, db)

@app.post("/matchmaking/request")
@require_role(Role.USER)
async def matchmaking_request(payload: Dict, tenant_config: TenantConfig = Depends(get_tenant_config), db: AsyncSession = Depends(get_db)):
    return await orchestrator.process_task("matchmaking", payload, tenant_config, db)

@app.get("/whitelabel/theme", response_model=Theme)
@require_role(Role.USER)
async def get_theme(tenant_config: TenantConfig = Depends(get_tenant_config), db: AsyncSession = Depends(get_db)):
    return await WhiteLabelAgent().get_theme(tenant_config, db)

# Run the app (for development)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)