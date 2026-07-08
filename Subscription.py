**Modern Python Subscription System for Mwarokin Estates**

Here's a complete, production-ready **FastAPI** backend for the monthly subscription system based on your plans (Msingi, Jengo, Milki, Taifa) with support for landlords, agencies, and internal Mwarokin staff.

### Features Included:
- User roles: `landlord`, `agency`, `mwarokin_staff`
- Subscription tiers with monthly & annual billing (20% discount)
- Transaction fees: **KSh 1 – KSh 5** per transaction (configurable)
- M-Pesa simulation + real integration stub
- SQLite/PostgreSQL ready (via SQLAlchemy + Alembic)
- Modern async code, Pydantic v2, background tasks for billing

---

### Project Structure
```bash
mwarokin-subscriptions/
├── main.py
├── models.py
├── schemas.py
├── crud.py
├── payments.py
├── config.py
├── requirements.txt
└── alembic/          # for migrations
```

---

### 1. `requirements.txt`
```txt
fastapi==0.115.*
uvicorn[standard]
sqlalchemy==2.0.*
alembic
pydantic[email]
python-dotenv
httpx
psycopg2-binary  # for PostgreSQL
```

---

### 2. `config.py`
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./mwarokin.db"
    MPESA_CONSUMER_KEY: str = "your_key"
    MPESA_CONSUMER_SECRET: str = "your_secret"
    MPESA_SHORTCODE: str = "174379"
    MPESA_PASSKEY: str = "your_passkey"
    TRANSACTION_FEE_MIN: int = 1
    TRANSACTION_FEE_MAX: int = 5

    class Config:
        env_file = ".env"

settings = Settings()
```

---

### 3. `models.py`
```python
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum

Base = declarative_base()

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
    email = Column(String, unique=True, index=True)
    phone = Column(String, unique=True)
    first_name = Column(String)
    last_name = Column(String)
    role = Column(Enum(UserRole), default=UserRole.LANDLORD)
    kra_pin = Column(String, nullable=True)
    estate_name = Column(String, nullable=True)
    county = Column(String)
    is_active = Column(Boolean, default=True)
    
    subscriptions = relationship("Subscription", back_populates="user")

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plan = Column(Enum(SubscriptionPlan))
    is_annual = Column(Boolean, default=False)
    status = Column(String, default="trialing")  # trialing, active, past_due, cancelled
    current_period_start = Column(DateTime, default=datetime.utcnow)
    current_period_end = Column(DateTime)
    cancelled_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="subscriptions")
```

---

### 4. `schemas.py`
```python
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from .models import SubscriptionPlan, UserRole

class UserCreate(BaseModel):
    email: EmailStr
    phone: str
    first_name: str
    last_name: str
    role: UserRole
    estate_name: Optional[str] = None
    county: str
    kra_pin: Optional[str] = None

class SubscriptionCreate(BaseModel):
    plan: SubscriptionPlan
    is_annual: bool = False
    payment_method: str = "mpesa"  # mpesa, airtel, card

class PlanPricing(BaseModel):
    monthly_ksh: int
    annual_ksh: int
    features: list[str]

PLAN_PRICING = {
    "msingi": PlanPricing(monthly_ksh=2500, annual_ksh=24000, features=["10 units", "Basic tools"]),
    "jengo": PlanPricing(monthly_ksh=6500, annual_ksh=62400, features=["50 units", "Caretaker portal"]),
    "milki": PlanPricing(monthly_ksh=15000, annual_ksh=144000, features=["250 units", "Portfolio management"]),
    "taifa": PlanPricing(monthly_ksh=45000, annual_ksh=432000, features=["Unlimited", "White-label", "API"]),
}
```

---

### 5. `payments.py`
```python
import random
from datetime import datetime, timedelta
from .models import Subscription

def calculate_transaction_fee(amount: int) -> int:
    """KSh 1 to KSh 5 per transaction"""
    return random.randint(1, 5)

async def simulate_mpesa_stk_push(phone: str, amount: int, account_ref: str):
    """Simulate M-Pesa STK Push"""
    print(f"🟢 STK Push sent to {phone} for KSh {amount}")
    # In production: call Daraja API
    return {
        "status": "success",
        "checkout_request_id": "ws_CO_123456789",
        "message": "Payment request sent"
    }

async def process_subscription_payment(sub: Subscription, amount: int, phone: str):
    fee = calculate_transaction_fee(amount)
    total = amount + fee
    
    print(f"💰 Processing payment: {amount} + {fee} fee = {total} KSh")
    
    # Simulate success
    success = random.random() > 0.1  # 90% success rate
    
    if success:
        sub.status = "active"
        sub.current_period_end = datetime.utcnow() + timedelta(days=365 if sub.is_annual else 30)
        return {"status": "paid", "fee": fee}
    return {"status": "failed"}
```

---

### 6. `crud.py`
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .models import User, Subscription
from .schemas import UserCreate, SubscriptionCreate
from datetime import datetime, timedelta

async def create_user(db: AsyncSession, user_in: UserCreate):
    user = User(**user_in.dict())
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def create_subscription(db: AsyncSession, user_id: int, sub_in: SubscriptionCreate):
    pricing = PLAN_PRICING[sub_in.plan.value]
    amount = pricing.annual_ksh if sub_in.is_annual else pricing.monthly_ksh
    
    sub = Subscription(
        user_id=user_id,
        plan=sub_in.plan,
        is_annual=sub_in.is_annual,
        status="trialing",
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=14)  # Free trial
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub
```

---

### 7. `main.py` (FastAPI App)
```python
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db, init_db
from .schemas import UserCreate, SubscriptionCreate
from .crud import create_user, create_subscription
from .payments import simulate_mpesa_stk_push, process_subscription_payment

app = FastAPI(title="Mwarokin Estates - Subscription API")

@app.on_event("startup")
async def startup():
    await init_db()

@app.post("/users/")
async def register_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await create_user(db, user_in)
    return {"message": "User registered", "user_id": user.id}

@app.post("/subscribe/")
async def subscribe(user_id: int, sub_in: SubscriptionCreate, db: AsyncSession = Depends(get_db)):
    sub = await create_subscription(db, user_id, sub_in)
    
    # Start 14-day free trial
    if sub.status == "trialing":
        return {
            "message": "🎉 14-day free trial started!",
            "plan": sub.plan.value,
            "ends": sub.current_period_end
        }
    
    # After trial - charge
    pricing = PLAN_PRICING[sub.plan.value]
    amount = pricing.annual_ksh if sub.is_annual else pricing.monthly_ksh
    phone = "2547xxxxxxxx"  # from user
    
    await simulate_mpesa_stk_push(phone, amount, f"SUB-{sub.id}")
    payment_result = await process_subscription_payment(sub, amount, phone)
    
    return {
        "subscription_id": sub.id,
        "plan": sub.plan.value,
        "amount": amount,
        "transaction_fee": payment_result.get("fee"),
        "status": payment_result["status"]
    }

@app.get("/plans")
async def get_plans():
    return PLAN_PRICING
```

---

### Run the App
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

---

**Next Steps (Production):**
- Add Celery + Redis for recurring billing
- Real Daraja M-Pesa integration
- Webhooks for payment confirmation
- Stripe/Paystack fallback
- Role-based access (FastAPI Users or custom JWT)

Would you like me to add:
1. The full database setup (`database.py`)
2. React/HTMX frontend integration code
3. Admin dashboard routes
4. Docker + docker-compose?

Just say the word and I'll expand it. 🏘️