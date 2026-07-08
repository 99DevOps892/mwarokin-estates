import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Integer, DateTime, JSON, Text, select
import numpy as np
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
    preferences: Mapped[Dict] = mapped_column(JSON)
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
    white_label: Mapped[Dict] = mapped_column(JSON)
    locale: Mapped[str] = mapped_column(String, default="en_US")
    currency: Mapped[str] = mapped_column(String, default="USD")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    action: Mapped[str] = mapped_column(String)
    details: Mapped[Dict] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AnalyticsReportDB(Base):
    __tablename__ = "analytics_reports"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    kpis: Mapped[Dict] = mapped_column(JSON)
    anomalies: Mapped[List[Dict]] = mapped_column(JSON, default=[])
    time_range_start: Mapped[datetime] = mapped_column(DateTime)
    time_range_end: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

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

class AnalyticsReport(BaseModel):
    kpis: Dict  # e.g., {"conversion_rate": 0.15, "avg_time_to_lease": 14.5}
    anomalies: List[Dict]  # e.g., [{"listing_id": "123", "issue": "Price spike"}]

class LeaseDraft(BaseModel):
    clauses: Dict
    schedule: Dict
    risks: List[str]

class Match(BaseModel):
    listing_id: str
    score: float
    explanation: str

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

# AnalyticsAgent
class AnalyticsAgent:
    async def execute(self, payload: Dict, tenant_config: TenantConfig, db: AsyncSession) -> AnalyticsReport:
        time_range_start = payload.get("time_range_start", (datetime.utcnow() - timedelta(days=30)).isoformat())
        time_range_end = payload.get("time_range_end", datetime.utcnow().isoformat())
        time_range_start = datetime.fromisoformat(time_range_start)
        time_range_end = datetime.fromisoformat(time_range_end)

        # Calculate KPIs
        kpis = await self.calculate_kpis(tenant_config.tenant_id, time_range_start, time_range_end, db)
        
        # Detect anomalies
        anomalies = await self.detect_anomalies(tenant_config.tenant_id, time_range_start, time_range_end, db)
        
        # Save report
        report = AnalyticsReportDB(
            tenant_id=tenant_config.tenant_id,
            kpis=kpis,
            anomalies=anomalies,
            time_range_start=time_range_start,
            time_range_end=time_range_end
        )
        db.add(report)
        await db.commit()

        # Log action
        await self.log_action(db, tenant_config.tenant_id, "analytics_report_generated", {"report_id": report.id})

        return AnalyticsReport(kpis=kpis, anomalies=anomalies)

    async def calculate_kpis(self, tenant_id: str, start: datetime, end: datetime, db: AsyncSession) -> Dict:
        # Fetch leases and listings
        leases_result = await db.execute(
            select(LeaseDB).where(LeaseDB.tenant_id == tenant_id, LeaseDB.created_at.between(start, end))
        )
        leases = leases_result.scalars().all()
        listings_result = await db.execute(
            select(ListingDB).where(ListingDB.tenant_id == tenant_id, ListingDB.created_at.between(start, end))
        )
        listings = listings_result.scalars().all()

        # Calculate KPIs
        total_leases = len(leases)
        total_listings = len(listings)
        conversion_rate = total_leases / total_listings if total_listings > 0 else 0.0
        avg_time_to_lease = sum(
            [(lease.created_at - listing.created_at).days for lease in leases for listing in listings if lease.listing_id == listing.id]
        ) / total_leases if total_leases > 0 else 0.0
        occupancy_rate = total_leases / total_listings if total_listings > 0 else 0.0

        return {
            "conversion_rate": round(conversion_rate, 2),
            "avg_time_to_lease_days": round(avg_time_to_lease, 1),
            "occupancy_rate": round(occupancy_rate, 2),
            "total_leases": total_leases,
            "total_listings": total_listings
        }

    async def detect_anomalies(self, tenant_id: str, start: datetime, end: datetime, db: AsyncSession) -> List[Dict]:
        listings_result = await db.execute(
            select(ListingDB).where(ListingDB.tenant_id == tenant_id, ListingDB.price.isnot(None))
        )
        listings = listings_result.scalars().all()
        
        prices = [listing.price for listing in listings if listing.price]
        if not prices:
            return []
        
        # Simple z-score for price anomaly detection
        mean_price = np.mean(prices)
        std_price = np.std(prices)
        z_threshold = 2.0  # Flag prices > 2 standard deviations
        anomalies = [
            {"listing_id": listing.id, "issue": f"Price spike: ${listing.price} (z-score: {round((listing.price - mean_price) / std_price, 2)})"}
            for listing in listings if std_price > 0 and abs((listing.price - mean_price) / std_price) > z_threshold
        ]
        return anomalies

    async def log_action(self, db: AsyncSession, tenant_id: str, action: str, details: Dict):
        redacted_details = {k: "REDACTED" if k in ["name", "address", "dob"] else v for k, v in details.items()}
        audit_log = AuditLog(tenant_id=tenant_id, action=action, details=redacted_details)
        db.add(audit_log)
        await db.commit()

# Orchestrator
class Orchestrator:
    def __init__(self):
        self.agents = {
            "analytics": AnalyticsAgent(),
            "lease": LeaseAgent(),  # From previous implementation
            "matchmaking": MatchmakingAgent(),
            "whitelabel": WhiteLabelAgent(),
            # Add other agents (ComplianceAgent, etc.)
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

@app.post("/analytics/report")
@require_role(Role.ADMIN)
async def generate_analytics_report(payload: Dict, tenant_config: TenantConfig = Depends(get_tenant_config), db: AsyncSession = Depends(get_db)):
    return await orchestrator.process_task("analytics", payload, tenant_config, db)

@app.post("/lease/create_draft")
@require_role(Role.AGENT)
async def create_lease_draft(payload: LeaseDraftPayload, tenant_config: TenantConfig = Depends(get_tenant_config), db: AsyncSession = Depends(get_db)):
    return await orchestrator.process_task("lease", payload.dict(), tenant_config, db)

@app.post("/matchmaking/request")
@require_role(Role.USER)
async def matchmaking_request(payload: Dict, tenant_config: TenantConfig = Depends(get_tenant_config), db: AsyncSession = Depends(get_db)):
    return await orchestrator.process_task("matchmaking", payload, tenant_config, db)

# Run the app (for development)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)