import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Integer, DateTime, JSON, select
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
    bedrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    square_feet: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

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

class KycPayload(BaseModel):
    tenant_id: str
    user_id: str
    name: str
    dob: str  # ISO format, e.g., "1990-01-01"
    address: str
    document_id: str

class KycResult(BaseModel):
    status: str  # "approved", "rejected", "pending"
    details: Dict
    risks: List[str]

class ComplianceReport(BaseModel):
    status: str  # "compliant", "non_compliant"
    violations: List[str]
    suggestions: List[str]

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
    # Mock tenant lookup
    tenant_data = {"tenant_id": api_key, "role": Role.AGENT, "white_label": {"logo": "logo.png"}}
    return TenantConfig(**tenant_data)

# Database Dependency
async def get_db():
    async with async_session() as session:
        yield session

# ComplianceAgent
class ComplianceAgent:
    async def execute(self, task: str, payload: Dict, tenant_config: TenantConfig, db: AsyncSession) -> Dict:
        if task == "check_kyc":
            return await self.check_kyc(payload, tenant_config, db)
        elif task == "check_listing":
            return await self.check_listing(payload, tenant_config, db)
        else:
            raise HTTPException(status_code=400, detail="Invalid compliance task")

    async def check_kyc(self, payload: KycPayload, tenant_config: TenantConfig, db: AsyncSession) -> KycResult:
        # Validate tenant_id
        if payload.tenant_id != tenant_config.tenant_id:
            raise HTTPException(status_code=403, detail="Tenant ID mismatch")

        # Mock KYC/AML check (replace with real service like Shufti Pro)
        kyc_result = await self.mock_kyc_check(payload)
        
        # Log action (redact PII)
        await self.log_action(
            db,
            tenant_config.tenant_id,
            "kyc_check",
            {"user_id": payload.user_id, "status": kyc_result.status, "risks": kyc_result.risks}
        )
        
        return kyc_result

    async def mock_kyc_check(self, payload: KycPayload) -> KycResult:
        # Simulate external KYC/AML service
        risks = []
        if "suspicious" in payload.name.lower():  # Mock rule
            risks.append("Potential PEP match")
            status = "rejected"
        else:
            status = "approved"
        
        return KycResult(
            status=status,
            details={"name_verified": True, "document_verified": True},
            risks=risks
        )

    async def check_listing(self, payload: Dict, tenant_config: TenantConfig, db: AsyncSession) -> ComplianceReport:
        listing_id = payload.get("listing_id")
        if not listing_id:
            raise HTTPException(status_code=400, detail="Listing ID required")

        # Fetch listing from DB
        result = await db.execute(select(ListingDB).where(ListingDB.id == listing_id, ListingDB.tenant_id == tenant_config.tenant_id))
        listing = result.scalars().first()
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")

        # Check for fair-housing violations (mock)
        violations, suggestions = await self.check_fair_housing(listing.address, listing.property_type)
        
        # Log action
        await self.log_action(
            db,
            tenant_config.tenant_id,
            "listing_compliance_check",
            {"listing_id": listing_id, "violations": violations}
        )
        
        return ComplianceReport(
            status="non_compliant" if violations else "compliant",
            violations=violations,
            suggestions=suggestions
        )

    async def check_fair_housing(self, address: str, property_type: str) -> tuple[List[str], List[str]]:
        # Mock fair-housing check (replace with NLP model or external service)
        violations = []
        suggestions = []
        if "exclusive" in address.lower():  # Mock discriminatory term
            violations.append("Potentially discriminatory language in address")
            suggestions.append("Avoid terms like 'exclusive' in listing descriptions")
        return violations, suggestions

    async def log_action(self, db: AsyncSession, tenant_id: str, action: str, details: Dict):
        # Redact PII in details (simplified)
        redacted_details = {k: "REDACTED" if k in ["name", "address", "dob"] else v for k, v in details.items()}
        audit_log = AuditLog(tenant_id=tenant_id, action=action, details=redacted_details)
        db.add(audit_log)
        await db.commit()

# Orchestrator (Extended)
class Orchestrator:
    def __init__(self):
        self.agents = {
            "listing": ListingAgent(),  # From previous implementation
            "valuation": ValuationAgent(),
            "matchmaking": MatchmakingAgent(),
            "compliance": ComplianceAgent(),
        }

    async def process_task(self, task_type: str, payload: Dict, tenant_config: TenantConfig, db: AsyncSession) -> Dict:
        agent = self.agents.get(task_type)
        if not agent:
            raise HTTPException(status_code=400, detail="Invalid task type")

        # Plan
        logger.info(f"Planning {task_type} for tenant {tenant_config.tenant_id}")
        
        # Execute
        try:
            result = await agent.execute(task_type.split("_")[-1], payload, tenant_config, db)
            
            # Reflect
            logger.info(f"Completed {task_type}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in {task_type}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

# FastAPI App
app = FastAPI(title="Mwarokin Real Estate OS")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()

app.router.lifespan = lifespan

# API Endpoints
orchestrator = Orchestrator()

@app.post("/compliance/check_kyc")
@require_role(Role.AGENT)
async def check_kyc(payload: KycPayload, tenant_config: TenantConfig = Depends(get_tenant_config), db: AsyncSession = Depends(get_db)):
    return await orchestrator.process_task("compliance_check_kyc", payload.dict(), tenant_config, db)

@app.post("/compliance/check_listing")
@require_role(Role.AGENT)
async def check_listing(payload: Dict, tenant_config: TenantConfig = Depends(get_tenant_config), db: AsyncSession = Depends(get_db)):
    return await orchestrator.process_task("compliance_check_listing", payload, tenant_config, db)

# Run the app (for development)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)