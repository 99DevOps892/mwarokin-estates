To transition the Mwarokin Real Estate Agentic OS from the provided mock implementation to a production-ready system, I'll address the first "Next Steps for Production" item: **Replace mock DB with a real functional PostgreSQL database with tenant partitioning**. Below, I'll provide a detailed implementation that sets up a PostgreSQL database with tenant partitioning, integrates it with the existing FastAPI-based agentic tasks, and ensures tenant isolation, RBAC, and compliance with the system prompt. The code will focus on the **ListingAgent** and **ValuationAgent** for brevity, but the structure is extensible to other agents.

### Approach
- **Database Choice**: Use PostgreSQL with schema-based tenant partitioning to ensure data isolation between tenants.
- **ORM**: Use SQLAlchemy with async support (`asyncpg`) for database interactions, compatible with FastAPI.
- **Schema Design**: Create separate schemas per tenant (e.g., `tenant1`, `tenant2`) to store listings and comps, ensuring isolation.
- **Integration**: Update the `ListingAgent` and `ValuationAgent` to interact with PostgreSQL instead of the mock DB.
- **Security**: Enforce RBAC via user roles and tenant_id checks, with audit logging for compliance.
- **Scalability**: Use connection pooling and async queries for performance.

### Prerequisites
- PostgreSQL installed and running (e.g., version 15+).
- Python packages: `pip install fastapi uvicorn pydantic sqlalchemy asyncpg psycopg2-binary`

### PostgreSQL Setup
1. **Create Database and Tenant Schemas**:
   Run the following SQL to set up the database and schemas for tenant partitioning:

   ```sql
   -- Create database
   CREATE DATABASE mwarokin;

   -- Connect to mwarokin database
   \c mwarokin

   -- Create tenant schemas (e.g., for tenant1)
   CREATE SCHEMA tenant1;

   -- Create listings table in tenant1 schema
   CREATE TABLE tenant1.listings (
       id UUID PRIMARY KEY,
       tenant_id VARCHAR(50) NOT NULL,
       address TEXT NOT NULL,
       price DECIMAL(15, 2) NOT NULL,
       sqft INTEGER NOT NULL,
       beds INTEGER NOT NULL,
       baths INTEGER NOT NULL,
       type VARCHAR(50) NOT NULL,
       status VARCHAR(50) NOT NULL,
       availability BOOLEAN NOT NULL,
       images JSONB,
       lat DECIMAL(9, 6),
       lon DECIMAL(9, 6),
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );

   -- Create comps table in tenant1 schema
   CREATE TABLE tenant1.comps (
       id UUID PRIMARY KEY,
       tenant_id VARCHAR(50) NOT NULL,
       address TEXT NOT NULL,
       price DECIMAL(15, 2) NOT NULL,
       sqft INTEGER NOT NULL,
       beds INTEGER NOT NULL,
       baths INTEGER NOT NULL,
       sold_date DATE NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );

   -- Create indexes for performance
   CREATE INDEX idx_listings_tenant_id ON tenant1.listings (tenant_id);
   CREATE INDEX idx_listings_address ON tenant1.listings (address);
   CREATE INDEX idx_comps_tenant_id ON tenant1.comps (tenant_id);
   CREATE INDEX idx_comps_address ON tenant1.comps (address);

   -- Repeat for additional tenants (e.g., tenant2)
   CREATE SCHEMA tenant2;
   -- ... replicate table creation for tenant2
   ```

2. **Sample Data**:
   Insert sample data for testing:

   ```sql
   INSERT INTO tenant1.listings (id, tenant_id, address, price, sqft, beds, baths, type, status, availability, images)
   VALUES (
       '123e4567-e89b-12d3-a456-426614174000',
       'tenant1',
       '123 Street, New York, USA',
       12345.00,
       1000,
       3,
       2,
       'Apartment',
       'For Sell',
       TRUE,
       '["img/property-1.jpg"]'::jsonb
   );

   INSERT INTO tenant1.comps (id, tenant_id, address, price, sqft, beds, baths, sold_date)
   VALUES
       ('223e4567-e89b-12d3-a456-426614174001', 'tenant1', '123 Street, New York, USA', 12000.00, 1000, 3, 2, '2025-01-15'),
       ('223e4567-e89b-12d3-a456-426614174002', 'tenant1', '125 Street, New York, USA', 12500.00, 950, 3, 2, '2025-02-10');
   ```

### Updated Python Code

Below is the updated Python code integrating PostgreSQL with tenant partitioning, replacing the mock DB. The code includes the **ListingAgent** and **ValuationAgent**, with async SQLAlchemy for database operations and tenant isolation.

```python
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, validator
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, Float, Integer, Boolean, JSON, DateTime, Date, UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import text
import uuid
import re
from geopy.geocoders import Nominatim
import logging
import json
from datetime import datetime
from contextlib import asynccontextmanager

# Configure logging for audit trails
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = "postgresql+asyncpg://username:password@localhost:5432/mwarokin"
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# SQLAlchemy Models
class ListingDB(Base):
    __tablename__ = "listings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(50), nullable=False)
    address = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    sqft = Column(Integer, nullable=False)
    beds = Column(Integer, nullable=False)
    baths = Column(Integer, nullable=False)
    type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    availability = Column(Boolean, nullable=False)
    images = Column(JSONB, default=list)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class CompDB(Base):
    __tablename__ = "comps"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(50), nullable=False)
    address = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    sqft = Column(Integer, nullable=False)
    beds = Column(Integer, nullable=False)
    baths = Column(Integer, nullable=False)
    sold_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Pydantic Models (same as before)
class Listing(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    address: str
    price: float
    sqft: int
    beds: int
    baths: int
    type: str
    status: str
    availability: bool
    images: List[str] = []
    lat: Optional[float] = None
    lon: Optional[float] = None

    @validator("address")
    def validate_address(cls, v):
        if not re.match(r".+\,.+\,.+", v):
            raise ValueError("Invalid address format")
        return v

class ListingReco(BaseModel):
    status: str
    warnings: List[str]
    normalized_fields: Dict
    media_report: Dict

class Valuation(BaseModel):
    range_low: float
    range_high: float
    comp_ids: List[str]
    confidence: float
    reasoning: str
    sources: List[str]

# Database session dependency
@asynccontextmanager
async def get_db(tenant_id: str):
    async with AsyncSessionLocal() as session:
        # Set schema for tenant isolation
        await session.execute(text(f"SET search_path TO {tenant_id}"))
        yield session

# Simulated RBAC dependency
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict:
    return {"user_id": "user1", "tenant_id": "tenant1", "role": "agent"}

# FastAPI app
app = FastAPI(title="Mwarokin Real Estate Agentic OS")

# ListingAgent: Intake, normalize, and validate listings
async def listing_agent_intake(payload: Dict, tenant_id: str) -> ListingReco:
    try:
        logger.info(f"[ListingAgent] Processing listing for tenant_id: {tenant_id}")
        
        # Validate and normalize
        listing = Listing(**payload, tenant_id=tenant_id)
        normalized_fields = listing.dict()
        
        # Enrich with geocoding (mocked)
        geolocator = Nominatim(user_agent="mwarokin")
        location = geolocator.geocode(listing.address)
        if location:
            listing.lat = location.latitude
            listing.lon = location.longitude
        else:
            listing.lat, listing.lon = 0.0, 0.0
            logger.warning(f"Geocoding failed for address: {listing.address}")
        
        # Image QA (mocked)
        media_report = {"valid_images": len(listing.images), "issues": []}
        if not listing.images:
            media_report["issues"].append("No images provided")
        
        # Save to PostgreSQL
        async with get_db(tenant_id) as db:
            db_listing = ListingDB(**listing.dict())
            db.add(db_listing)
            await db.commit()
            await db.refresh(db_listing)
        
        # Reflect: Check for warnings
        warnings = []
        if listing.sqft < 100:
            warnings.append("Unusually small square footage")
        if listing.price <= 0:
            warnings.append("Invalid price")
        
        return ListingReco(
            status="success",
            warnings=warnings,
            normalized_fields=listing.dict(),
            media_report=media_report
        )
    except Exception as e:
        logger.error(f"[ListingAgent] Error: {str(e)}")
        return ListingReco(status="error", warnings=[str(e)], normalized_fields={}, media_report={})

# ValuationAgent: Generate valuation based on comps
async def valuation_agent_request(listing_id: str, tenant_id: str) -> Valuation:
    logger.info(f"[ValuationAgent] Valuating listing_id: {listing_id} for tenant_id: {tenant_id}")
    
    async with get_db(tenant_id) as db:
        # Retrieve listing
        listing = await db.get(ListingDB, uuid.UUID(listing_id))
        if not listing or listing.tenant_id != tenant_id:
            raise HTTPException(status_code=404, message="Listing not found or access denied")
        
        # RAG: Retrieve comps
        comps_query = await db.execute(
            text("SELECT * FROM comps WHERE address ILIKE :address"),
            {"address": f"%{listing.address}%"}
        )
        comps = comps_query.fetchall()
        if not comps:
            logger.warning(f"No comps found for address: {listing.address}")
            return Valuation(
                range_low=0,
                range_high=0,
                comp_ids=[],
                confidence=0.0,
                reasoning="No comparable sales found",
                sources=[]
            )
        
        # Calculate valuation
        prices = [comp.price for comp in comps]
        avg_price = sum(prices) / len(prices)
        range_low = avg_price * 0.9
        range_high = avg_price * 1.1
        confidence = 0.85 if len(comps) >= 2 else 0.65
        
        # Explain reasoning
        reasoning = f"Valuation based on {len(comps)} comparable sales within the same area. Average price: ${avg_price:.2f}. Adjusted ±10% for market variability."
        sources = [f"Comp {comp.id} sold on {comp.sold_date}" for comp in comps]
        
        # Reflect: Validate valuation
        if range_low <= 0 or range_high <= 0:
            logger.warning("Invalid valuation range")
            reasoning += " Warning: Valuation may be unreliable due to negative or zero values."
        
        return Valuation(
            range_low=range_low,
            range_high=range_high,
            comp_ids=[str(comp.id) for comp in comps],
            confidence=confidence,
            reasoning=reasoning,
            sources=sources
        )

# API Endpoints
@app.post("/listings/intake", response_model=ListingReco)
async def intake_listing(payload: Dict, current_user: Dict = Depends(get_current_user)):
    result = await listing_agent_intake(payload, current_user["tenant_id"])
    logger.info(f"[Audit] Listing intake for tenant_id: {current_user['tenant_id']}, status: {result.status}")
    return result

@app.post("/valuations/{listing_id}", response_model=Valuation)
async def request_valuation(listing_id: str, current_user: Dict = Depends(get_current_user)):
    result = await valuation_agent_request(listing_id, current_user["tenant_id"])
    logger.info(f"[Audit] Valuation requested for listing_id: {listing_id}, tenant_id: {current_user['tenant_id']}")
    return result

@app.get("/listings", response_model=List[Listing])
async def get_listings(
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    location: Optional[str] = None,
    status: Optional[str] = None,
    availability: Optional[bool] = None,
    current_user: Dict = Depends(get_current_user)
):
    async with get_db(current_user["tenant_id"]) as db:
        query = text("SELECT * FROM listings WHERE tenant_id = :tenant_id")
        params = {"tenant_id": current_user["tenant_id"]}
        
        if price_min is not None:
            query = text(query.text + " AND price >= :price_min")
            params["price_min"] = price_min
        if price_max is not None:
            query = text(query.text + " AND price <= :price_max")
            params["price_max"] = price_max
        if location is not None:
            query = text(query.text + " AND address ILIKE :location")
            params["location"] = f"%{location}%"
        if status is not None:
            query = text(query.text + " AND status = :status")
            params["status"] = status
        if availability is not None:
            query = text(query.text + " AND availability = :availability")
            params["availability"] = availability
        
        result = await db.execute(query, params)
        listings = result.fetchall()
        
        # Convert to Pydantic model
        filtered_listings = [
            Listing(
                id=str(listing.id),
                tenant_id=listing.tenant_id,
                address=listing.address,
                price=listing.price,
                sqft=listing.sqft,
                beds=listing.beds,
                baths=listing.baths,
                type=listing.type,
                status=listing.status,
                availability=listing.availability,
                images=listing.images,
                lat=listing.lat,
                lon=listing.lon
            ) for listing in listings
        ]
        
        logger.info(f"[Audit] Listings retrieved for tenant_id: {current_user['tenant_id']}, count: {len(filtered_listings)}")
        return filtered_listings

# Initialize database
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# FastAPI startup event
@app.on_event("startup")
async def on_startup():
    await init_db()

# Example usage
if __name__ == "__main__":
    import uvicorn
    # Example listing intake
    sample_listing = {
        "address": "123 Street, New York, USA",
        "price": 12345.0,
        "sqft": 1000,
        "beds": 3,
        "baths": 2,
        "type": "Apartment",
        "status": "For Sell",
        "availability": True,
        "images": ["img/property-1.jpg"]
    }
    
    import asyncio
    async def test_agents():
        # Test ListingAgent
        reco = await listing_agent_intake(sample_listing, "tenant1")
        print("Listing Intake:", reco.dict())
        
        # Test ValuationAgent
        listing_id = reco.normalized_fields["id"]
        valuation = await valuation_agent_request(listing_id, "tenant1")
        print("Valuation:", valuation.dict())
    
    asyncio.run(test_agents())
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Key Changes and Features
1. **PostgreSQL with Tenant Partitioning**:
   - Uses schema-based partitioning (`tenant1`, `tenant2`, etc.) to isolate tenant data.
   - Each tenant has its own `listings` and `comps` tables within its schema.
   - The `search_path` is set dynamically per request to enforce tenant isolation.

2. **SQLAlchemy Async Integration**:
   - Uses `asyncpg` for asynchronous database queries, improving scalability.
   - Defines `ListingDB` and `CompDB` models with appropriate data types (e.g., `JSONB` for images).
   - Implements a context manager (`get_db`) to set the tenant schema and manage sessions.

3. **Updated Agent Logic**:
   - **ListingAgent**: Saves listings to the tenant-specific `listings` table, with geocoding and validation.
   - **ValuationAgent**: Queries comps from the tenant-specific `comps` table, with case-insensitive address matching.
   - Both agents maintain explainability and audit logging.

4. **API Endpoint for Listings**:
   - The `/listings` endpoint supports filtering by price, location, status, and availability, using dynamic SQL queries.
   - Returns results in the Pydantic `Listing` model, compatible with the frontend.

5. **Security and Compliance**:
   - Tenant isolation is enforced by setting `search_path` and validating `tenant_id`.
   - RBAC is simulated via `get_current_user` (extend with JWT or OAuth2 in production).
   - Audit logs capture all key actions (e.g., listing intake, valuation requests).
   - PII (e.g., address) is stored in the database but should be encrypted in production (see next steps).

6. **Frontend Integration**:
   - The `/listings` endpoint aligns with the HTML frontend's filtering logic (price, location, status, availability).
   - The provided JavaScript (`AutomateGPRSPinLocator.js`) remains compatible, fetching listings via the API.

### Setup Instructions
1. **Install PostgreSQL**:
   - Install PostgreSQL (e.g., `sudo apt install postgresql` on Ubuntu).
   - Create the `mwarokin` database and run the SQL setup script.

2. **Update Database URL**:
   - Replace `username:password` in `DATABASE_URL` with your PostgreSQL credentials.

3. **Install Python Dependencies**:
   ```bash
   pip install fastapi uvicorn pydantic sqlalchemy asyncpg psycopg2-binary geopy
   ```

4. **Run the Application**:
   ```bash
   python script.py
   ```
   - The API will be available at `http://localhost:8000`.
   - Test endpoints using Postman or the frontend.

5. **Test with Sample Data**:
   - Use the provided SQL to insert sample data.
   - Run the `test_agents` function to verify `ListingAgent` and `ValuationAgent`.
