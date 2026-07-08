pip install fastapi pydantic sqlalchemy asyncpg sentence-transformers faiss-cpu numpy

import asyncio
import uuid
from datetime import datetime
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
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)  # Store embedding
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class BuyerProfileDB(Base):
    __tablename__ = "buyer_profiles"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    preferences: Mapped[Dict] = mapped_column(JSON)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)  # Store embedding
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

# RAG Setup
class RAGStore:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = faiss.IndexFlatIP(384)  # 384-dim embeddings for all-MiniLM-L6-v2, inner product for cosine similarity
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

        # Mock MLS/Zillow API (replace with real API call)
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

        # Log action
        await self.log_action(db, tenant_config.tenant_id, "rag_retrieve_comps", {"query": query, "comps_count": len(comps)})
        
        return comps

    async def mock_mls_api(self, query: str) -> List[Dict]:
        # Mock MLS/Zillow API response
        return [
            {
                "id": str(uuid.uuid4()),
                "description": f"Modern {query} with 3 bedrooms, 2 bathrooms",
                "price": 500000,
                "features": {"bedrooms": 3, "bathrooms": 2, "square_feet": 1500},
                "source": "MLS"
            },
            {
                "id": str(uuid.uuid4()),
                "description": f"Spacious {query} with great amenities",
                "price": 550000,
                "features": {"bedrooms": 4, "bathrooms": 2.5, "square_feet": 1800},
                "source": "Zillow"
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

        # Fetch profile
        profile_result = await db.execute(select(BuyerProfileDB).where(BuyerProfileDB.id == profile_id, BuyerProfileDB.tenant_id == tenant_config.tenant_id))
        profile = profile_result.scalars().first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        # Update profile embedding if needed
        if not profile.embedding:
            pref_text = " ".join([f"{k}: {v}" for k, v in profile.preferences.items()])
            profile.embedding = rag_store.model.encode(pref_text, convert_to_numpy=True).tolist()
            db.add(profile)
            await db.commit()

        # Fetch listings
        listings_result = await db.execute(select(ListingDB).where(ListingDB.tenant_id == tenant_config.tenant_id))
        listings = listings_result.scalars().all()

        # Calculate matches using embeddings
        matches = []
        profile_embedding = np.array(profile.embedding, dtype=np.float32)
        for listing in listings:
            if listing.embedding:
                listing_embedding = np.array(listing.embedding, dtype=np.float32)
                score = float(np.dot(profile_embedding, listing_embedding) / (np.linalg.norm(profile_embedding) * np.linalg.norm(listing_embedding)))
                matches.append(Match(
                    listing_id=listing.id,
                    score=score,
                    explanation=f"Match based on similarity to preferences: {profile.preferences} vs listing: {listing.address}, {listing.description[:50]}..."
                ))

        # Log action
        await self.log_action(db, tenant_config.tenant_id, "matchmaking_request", {"profile_id": profile_id, "matches_count": len(matches)})

        return sorted(matches, key=lambda x: x.score, reverse=True)[:5]

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
            "analytics": AnalyticsAgent(),  # From previous implementation
            "lease": LeaseAgent(),
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
    # Initialize RAG with mock data
    rag_store.add_document("Modern apartment in Brooklyn", {"listing_id": "comp1", "price": 500000, "features": {"bedrooms": 2}, "source": "MLS"})
    yield
    await engine.dispose()

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

# Run the app (for development)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)