```python
# tenant_transactions.py
# Modern Python backend for Mwarokin Estates Tenant Portal
# Handles monthly subscriptions, tenant transactions, and low-cost fees (KSh 1-5)

import asyncio
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
import uvicorn
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
from sqlalchemy.exc import NoResultFound

# ====================== CONFIG ======================
DATABASE_URL = "sqlite:///./mwarokin_tenants.db"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ====================== MODELS ======================
class PaymentMethod(str, Enum):
    MPESA = "mpesa"
    AIRTEL = "airtel"
    BANK = "bank"
    EQUITY = "equity"
    COOP = "coop"
    CARD = "card"

class BillType(str, Enum):
    RENT = "monthly_rent"
    ELECTRICITY = "electricity"
    WATER = "water_sewerage"
    INTERNET = "internet"
    MAINTENANCE = "maintenance_fee"
    OTHER = "other"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    unit = Column(String, unique=True, index=True)  # e.g., "A-304"
    name = Column(String)
    phone = Column(String)
    email = Column(String)
    balance_due = Column(Float, default=0.0)
    next_due_date = Column(DateTime)
    transactions = relationship("Transaction", back_populates="tenant")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    amount = Column(Float)
    bill_type: BillType = Column(SQLEnum(BillType))
    payment_method: PaymentMethod = Column(SQLEnum(PaymentMethod))
    transaction_fee = Column(Float, default=0.0)  # 1-5 KSh
    status: TransactionStatus = Column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING)
    reference = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    tenant = relationship("Tenant", back_populates="transactions")

Base.metadata.create_all(bind=engine)

# ====================== PYDANTIC SCHEMAS ======================
class TenantCreate(BaseModel):
    unit: str
    name: str
    phone: str
    email: Optional[str] = None

class PaymentRequest(BaseModel):
    tenant_unit: str
    amount: float = Field(..., gt=0)
    bill_type: BillType
    payment_method: PaymentMethod
    phone: Optional[str] = None  # for M-Pesa etc.

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v < 1:
            raise ValueError("Amount must be at least KSh 1")
        return round(v, 2)

class TransactionResponse(BaseModel):
    id: str
    tenant_unit: str
    amount: float
    bill_type: str
    payment_method: str
    transaction_fee: float
    status: str
    reference: str
    created_at: datetime

# ====================== DEPENDENCIES ======================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ====================== HELPERS ======================
def calculate_transaction_fee(amount: float) -> float:
    """Low-cost transaction fee: KSh 1 to 5 based on amount"""
    if amount <= 100:
        return 1.0
    elif amount <= 500:
        return 2.0
    elif amount <= 2000:
        return 3.0
    else:
        return min(5.0, round(amount * 0.002, 2))  # cap at 5 KSh

async def simulate_payment_processing(transaction: Transaction, db: Session):
    """Background simulation of payment gateway (M-Pesa, etc.)"""
    await asyncio.sleep(2)  # simulate network delay
    transaction.status = TransactionStatus.COMPLETED
    transaction.completed_at = datetime.utcnow()
    tenant = db.query(Tenant).filter(Tenant.id == transaction.tenant_id).first()
    if tenant:
        tenant.balance_due = max(0.0, tenant.balance_due - transaction.amount)
    db.commit()

# ====================== FASTAPI APP ======================
app = FastAPI(
    title="Mwarokin Estates Tenant API",
    description="Modern backend for tenant portal - bills, payments & transactions",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================== ROUTES ======================
@app.post("/tenants/", response_model=dict)
def create_tenant(tenant: TenantCreate, db: Session = Depends(get_db)):
    existing = db.query(Tenant).filter(Tenant.unit == tenant.unit).first()
    if existing:
        raise HTTPException(400, "Unit already registered")
    
    new_tenant = Tenant(
        unit=tenant.unit,
        name=tenant.name,
        phone=tenant.phone,
        email=tenant.email,
        balance_due=1250.0,  # example monthly rent
        next_due_date=datetime.utcnow() + timedelta(days=30)
    )
    db.add(new_tenant)
    db.commit()
    db.refresh(new_tenant)
    return {"message": "Tenant created", "unit": new_tenant.unit}

@app.get("/tenants/{unit}", response_model=dict)
def get_tenant(unit: str, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.unit == unit).first()
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    return {
        "unit": tenant.unit,
        "name": tenant.name,
        "balance_due": tenant.balance_due,
        "next_due_date": tenant.next_due_date.date().isoformat(),
        "recent_transactions": len(tenant.transactions)
    }

@app.post("/payments/", response_model=TransactionResponse)
async def make_payment(
    payment: PaymentRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    tenant = db.query(Tenant).filter(Tenant.unit == payment.tenant_unit).first()
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    
    fee = calculate_transaction_fee(payment.amount)
    total_due = payment.amount + fee
    
    transaction = Transaction(
        tenant_id=tenant.id,
        amount=payment.amount,
        bill_type=payment.bill_type,
        payment_method=payment.payment_method,
        transaction_fee=fee,
        reference=f"INV-{uuid.uuid4().hex[:8].upper()}",
        status=TransactionStatus.PENDING
    )
    
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    
    # Simulate async payment processing
    background_tasks.add_task(simulate_payment_processing, transaction, db)
    
    return TransactionResponse(
        id=transaction.id,
        tenant_unit=tenant.unit,
        amount=transaction.amount,
        bill_type=transaction.bill_type.value,
        payment_method=transaction.payment_method.value,
        transaction_fee=transaction.transaction_fee,
        status=transaction.status.value,
        reference=transaction.reference,
        created_at=transaction.created_at
    )

@app.get("/transactions/{unit}", response_model=List[TransactionResponse])
def get_tenant_transactions(unit: str, limit: int = 10, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.unit == unit).first()
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    
    txs = db.query(Transaction).filter(Transaction.tenant_id == tenant.id)\
        .order_by(Transaction.created_at.desc()).limit(limit).all()
    
    return [
        TransactionResponse(
            id=t.id,
            tenant_unit=unit,
            amount=t.amount,
            bill_type=t.bill_type.value,
            payment_method=t.payment_method.value,
            transaction_fee=t.transaction_fee,
            status=t.status.value,
            reference=t.reference,
            created_at=t.created_at
        ) for t in txs
    ]

@app.get("/monthly-subscription-summary/{unit}")
def monthly_summary(unit: str, db: Session = Depends(get_db)):
    """Monthly subscription overview with transaction costs"""
    tenant = db.query(Tenant).filter(Tenant.unit == unit).first()
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    
    this_month = date.today().replace(day=1)
    txs = db.query(Transaction).filter(
        Transaction.tenant_id == tenant.id,
        Transaction.created_at >= this_month
    ).all()
    
    total_paid = sum(t.amount for t in txs if t.status == TransactionStatus.COMPLETED)
    total_fees = sum(t.transaction_fee for t in txs)
    
    return {
        "unit": unit,
        "base_monthly_rent": 1250.0,
        "total_paid_this_month": round(total_paid, 2),
        "total_transaction_fees": round(total_fees, 2),
        "transaction_count": len(txs),
        "avg_fee_per_tx": round(total_fees / len(txs), 2) if txs else 0,
        "next_due": tenant.next_due_date.date().isoformat(),
        "balance": tenant.balance_due
    }

# ====================== SEED DATA ======================
@app.post("/seed-demo-data")
def seed_demo_data(db: Session = Depends(get_db)):
    # Demo tenant
    tenant = db.query(Tenant).filter(Tenant.unit == "A-304").first()
    if not tenant:
        tenant = Tenant(
            unit="A-304",
            name="John Doe",
            phone="+254712345678",
            email="john@example.com",
            balance_due=130.0,
            next_due_date=datetime(2024, 10, 1)
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
    
    # Demo transactions
    if len(tenant.transactions) == 0:
        demo_tx = Transaction(
            tenant_id=tenant.id,
            amount=1250,
            bill_type=BillType.RENT,
            payment_method=PaymentMethod.MPESA,
            transaction_fee=3.0,
            status=TransactionStatus.COMPLETED,
            reference="INV-SEP2024"
        )
        db.add(demo_tx)
        db.commit()
    
    return {"status": "Demo data seeded"}

# ====================== RUN ======================
if __name__ == "__main__":
    print("🚀 Starting Mwarokin Estates Tenant Transaction API")
    print("Monthly subscriptions + KSh 1-5 transaction fees supported")
    uvicorn.run("tenant_transactions:app", host="0.0.0.0", port=8000, reload=True)
```

### How to run:

1. Save as `tenant_transactions.py`
2. Install dependencies:
   ```bash
   pip install fastapi uvicorn sqlalchemy pydantic
   ```
3. Run:
   ```bash
   python tenant_transactions.py
   ```

### Features:
- **Modern FastAPI** with async support
- **Transaction fees** automatically 1-5 KSh based on amount
- **Monthly subscription** tracking (rent + utilities)
- **SQLite** persistence (easy to swap to PostgreSQL)
- Endpoints match the HTML portal (payments, bills, history)
- Background payment simulation (M-Pesa style)

You can easily connect this backend to your existing HTML frontend by calling the API endpoints (`/payments/`, `/transactions/`, etc.). Let me know if you need React/HTMX integration or additional features!