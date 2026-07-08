import asyncio
import uuid
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Integer, DateTime, JSON, Text, select
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import redis.asyncio as redis
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

# Redis Setup
redis_client = redis.Redis(host='localhost', port=6379, db=0)

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
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class BuyerProfileDB(Base):
    __tablename__ = "buyer_profiles"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    preferences: Mapped[Dict] = mapped_column(JSON)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)
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

class Comp(BaseModel):
    listing_id: str
    price: float
    features: Dict
    source: str

class Match(BaseModel):
    listing_id: str
    score: float
    explanation: str

class LeaseDraftPayload(BaseModel):
    tenant_id: str
    listing_id: str
    applicant_id: str
    terms: Dict

class LeaseDraft(BaseModel):
    clauses: Dict
    schedule: Dict
    risks: List[str]

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

# RAG Setup with HNSW
class RAGStore:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = faiss.IndexHNSWFlat(384, 32)  # HNSW index, 384-dim, 32 neighbors
        self.index.hnsw.efConstruction = 200  # Higher for better accuracy
        self.index.hnsw.efSearch = 40  # Higher for better recall
        self.metadata = []
        self.embeddings = []

    def add_document(self, text: str, metadata: Dict):
        embedding = self.model.encode(text, convert_to_numpy=True)
        self.embeddings.append(embedding)
        self.metadata.append(metadata)
        self.index.add(np.array([embedding], dtype=np.float32))

    def search(self, query: str, k: int = 5) -> List[Dict]:
        query_embedding = self.model.encode(query, convert_to_numpy=True)
        distances, indices = self.index.search(np.array([query_embedding], dtype=np.float32), k)
        return [(self.metadata[i], distances[0][idx]) for idx, i in enumerate(indices[0]) if i < len(self.metadata)]

rag_store = RAGStore()

class RAGAgent:
    async def execute(self, payload: Dict, tenant_config: TenantConfig, db: AsyncSession) -> List[Comp]:
        query = payload.get("query")
        k = payload.get("k", 5)
        if not query:
            raise HTTPException(status_code=400, detail="Query required")

        # Check Redis cache
        cache_key = f"rag:comps:{tenant_config.tenant_id}:{query}:{k}"
        cached = await redis_client.get(cache_key)
        if cached:
            logger.info(f"Cache hit for {cache_key}")
            return [Comp(**comp) for comp in json.loads(cached)]

        # Fetch tenant-specific listings
        listings_result = await db.execute(select(ListingDB).where(ListingDB.tenant_id == tenant_config.tenant_id))
        listings = listings_result.scalars().all()

        # Update embeddings if needed
        for listing in listings:
            if not listing.embedding and listing.description:
                embedding = rag_store.model.encode(listing.description, convert_to_numpy=True).tolist()
                listing.embedding = embedding
                db.add(listing)
        await db.commit()

        # Mock MLS API (replace with real API in production)
        comps_data = await self.mock_mls_api(query)
        for comp in comps_data:
            rag_store.add_document(comp["description"], {
                "listing_id": comp["id"],
                "price": comp["price"],
                "features": comp["features"],
                "source": comp["source"]
            })

        # Search RAG store
        results = rag_store.search(query, k)
        comps = [
            Comp(
                listing_id=meta["listing_id"],
                price=meta["price"],
                features=meta["features"],
                source=meta["source"]
            ) for meta, _ in results
        ]

        # Cache results (expire in 1 hour)
        await redis_client.setex(cache_key, 3600, json.dumps([comp.dict() for comp in comps]))

        # Log action
        await self.log_action(db, tenant_config.tenant_id, "rag_retrieve_comps", {"query": query, "comps_count": len(comps)})
        
        return comps

    async def mock_mls_api(self, query: str) -> List[Dict]:
        return [
            {
                "id": str(uuid.uuid4()),
                "description": f"Modern {query} with 3 bedrooms, 2 bathrooms",
                "price": 500000,
                "features": {"bedrooms": 3, "bathrooms": 2, "square_feet": 1500},
                "source": "MLS"
            }
        ]

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

        # Check Redis cache
        cache_key = f"matchmaking:{tenant_config.tenant_id}:{profile_id}"
        cached = await redis_client.get(cache_key)
        if cached:
            logger.info(f"Cache hit for {cache_key}")
            return [Match(**match) for match in json.loads(cached)]

        # Fetch profile
        profile_result = await db.execute(select(BuyerProfileDB).where(BuyerProfileDB.id == profile_id, BuyerProfileDB.tenant_id == tenant_config.tenant_id))
        profile = profile_result.scalars().first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        # Update profile embedding
        if not profile.embedding:
            pref_text = " ".join([f"{k}: {v}" for k, v in profile.preferences.items()])
            profile.embedding = rag_store.model.encode(pref_text, convert_to_numpy=True).tolist()
            db.add(profile)
            await db.commit()

        # Fetch listings
        listings_result = await db.execute(select(ListingDB).where(ListingDB.tenant_id == tenant_config.tenant_id))
        listings = listings_result.scalars().all()

        # Calculate matches
        matches = []
        profile_embedding = np.array(profile.embedding, dtype=np.float32)
        for listing in listings:
            if listing.embedding:
                listing_embedding = np.array(listing.embedding, dtype=np.float32)
                score = float(np.dot(profile_embedding, listing_embedding) / (np.linalg.norm(profile_embedding) * np.linalg.norm(listing_embedding)))
                matches.append(Match(
                    listing_id=listing.id,
                    score=score,
                    explanation=f"Match based on similarity: bedrooms ({profile.preferences.get('bedrooms')} vs {listing.bedrooms}), price (${profile.preferences.get('max_price')} vs ${listing.price})"
                ))

        # Cache results (expire in 1 hour)
        await redis_client.setex(cache_key, 3600, json.dumps([match.dict() for match in matches]))

        # Log action
        await self.log_action(db, tenant_config.tenant_id, "matchmaking_request", {"profile_id": profile_id, "matches_count": len(matches)})

        return sorted(matches, key=lambda x: x.score, reverse=True)[:5]

    async def log_action(self, db: AsyncSession, tenant_id: str, action: str, details: Dict):
        redacted_details = {k: "REDACTED" if k in ["name", "address", "dob"] else v for k, v in details.items()}
        audit_log = AuditLog(tenant_id=tenant_id, action=action, details=redacted_details)
        db.add(audit_log)
        await db.commit()

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

        # Generate detailed lease clauses
        clauses = {
            "duration": payload.terms.get("duration_months", 12),
            "rent": payload.terms.get("monthly_rent", 2000),
            "renewal_option": payload.terms.get("renewal_option", False),
            "renewal_terms": {"extension_months": 12, "rent_increase_percent": 5} if payload.terms.get("renewal_option") else None,
            "late_payment_penalty": {"amount": 50, "grace_period_days": 5},
            "maintenance_responsibility": "Tenant responsible for minor repairs under $100"
        }
        schedule = {
            "start_date": "2025-10-01",
            "payments": [{"date": "2025-11-01", "amount": clauses["rent"]}]
        }
        risks = []
        if clauses["renewal_option"] and not profile.preferences.get("credit_score"):
            risks.append("Credit check required for renewal option")
        if clauses["rent"] > profile.preferences.get("max_price", float("inf")):
            risks.append("Rent exceeds applicant’s budget")

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

# Orchestrator
class Orchestrator:
    def __init__(self):
        self.agents = {
            "rag": RAGAgent(),
            "matchmaking": MatchmakingAgent(),
            "lease": LeaseAgent(),
            "analytics": AnalyticsAgent(),  # From previous implementation
            "compliance": ComplianceAgent(),
            "whitelabel": WhiteLabelAgent(),
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
    await redis_client.close()

app.router.lifespan = lifespan

# API Endpoints
orchestrator = Orchestrator()

@app.post("/rag/retrieve_comps")
@require_role(Role.AGENT)
async def retrieve_comps(payload: Dict, tenant_config: TenantConfig = Depends(get_tenant_config), db: AsyncSession = Depends(get_db)):
    return await orchestrator.process_task("rag", payload, tenant_config, db)

@app.post("/matchmaking/request")
@require_role(Role.USER)
async def matchmaking_request(payload: Dict, tenant_config: TenantConfig = Depends(get_tenant_config), db: AsyncSession = Depends(get_db)):
    return await orchestrator.process_task("matchmaking", payload, tenant_config, db)

@app.post("/lease/create_draft")
@require_role(Role.AGENT)
async def create_lease_draft(payload: LeaseDraftPayload, tenant_config: TenantConfig = Depends(get_tenant_config), db: AsyncSession = Depends(get_db)):
    return await orchestrator.process_task("lease", payload.dict(), tenant_config, db)

@app.post("/analytics/report")
@require_role(Role.ADMIN)
async def generate_analytics_report(payload: Dict, tenant_config: TenantConfig = Depends(get_tenant_config), db: AsyncSession = Depends(get_db)):
    return await orchestrator.process_task("analytics", payload, tenant_config, db)

# Run the app (for development)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)