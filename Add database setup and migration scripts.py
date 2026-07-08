**Updated Mwarokin Estates Subscription System**  
**With Database Setup + Alembic Migrations**

Here’s the complete addition for database configuration and migration support.

---

### 1. Create `database.py`

```python
# database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
import asyncio
from .config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,                    # Set to True for SQL logging during dev
    future=True,
    pool_pre_ping=True,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    """Dependency for FastAPI routes"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Create all tables (for development)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables initialized")

async def drop_db():
    """Drop all tables (use with caution)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("🗑️ All tables dropped")

# Optional: Health check
async def check_db_connection():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
```

---

### 2. Update `models.py` (add missing imports & relationships)

Replace your current `models.py` with this improved version:

```python
# models.py
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

class UserRole(str, enum.Enum):
    LANDLORD = "landlord"
    AGENCY = "agency"
    MWAROKIN_STAFF = "mwarokin_staff"

class SubscriptionPlan(str, enum.Enum):
    MSINGI = "msingi"
    JENGO = "jengo"
    MILKI = "milki"
    TAIFA = "taifa"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.LANDLORD)
    kra_pin = Column(String, nullable=True)
    estate_name = Column(String, nullable=True)
    county = Column(String, nullable=True)
    preferred_language = Column(String, default="English")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan = Column(SQLEnum(SubscriptionPlan), nullable=False)
    is_annual = Column(Boolean, default=False)
    status = Column(String, default="trialing")  # trialing, active, past_due, cancelled, expired
    current_period_start = Column(DateTime, default=datetime.utcnow)
    current_period_end = Column(DateTime, nullable=False)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="subscriptions")
```

---

### 3. Alembic Migration Setup

Run these commands in your project root:

```bash
pip install alembic
alembic init alembic
```

#### Update `alembic.ini`
```ini
[alembic]
script_location = alembic
sqlalchemy.url = %(DATABASE_URL)s
```

#### Update `alembic/env.py`

Replace the `env.py` file with this:

```python
# alembic/env.py
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from mwarokin_subscriptions.database import Base
from mwarokin_subscriptions.config import settings

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

### 4. Generate First Migration

```bash
alembic revision --autogenerate -m "Initial subscription models"
alembic upgrade head
```

---

### 5. Update `main.py` (add DB init)

```python
# main.py (updated)
from fastapi import FastAPI
from .database import init_db, check_db_connection
from .config import settings

app = FastAPI(
    title="Mwarokin Estates Subscription API",
    description="Modern property management SaaS - Landlords, Agencies & Mwarokin Staff",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    await check_db_connection()
    await init_db()
    print("🚀 Mwarokin Subscription API started successfully!")

# ... your existing routes here
```

---

### Final Project Structure
```
mwarokin-subscriptions/
├── main.py
├── config.py
├── database.py
├── models.py
├── schemas.py
├── crud.py
├── payments.py
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── xxxx_initial_subscription_models.py
├── requirements.txt
└── .env
```

---

**Ready to go!**

Would you like me to also add:
- JWT Authentication + Protected routes?
- Background task for monthly/annual recurring billing?
- Admin panel endpoints?
- Docker + docker-compose setup?

Just tell me what to add next. 🏘️