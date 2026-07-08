```python
# main.py - Modern FastAPI Backend for Lipa Mdogo Mdogo (Mwarokin Estates)
# Run with: uvicorn main:app --reload

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime, date
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func

# ====================== DATABASE SETUP ======================
DATABASE_URL = "sqlite:///./lipa_mdogo.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Amenity(Base):
    __tablename__ = "amenities"
    id = Column(Integer, primary_key=True, index=True)
    month_id = Column(Integer, ForeignKey("months.id", ondelete="CASCADE"))
    name = Column(String(100))
    cost = Column(Float)

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    month_id = Column(Integer, ForeignKey("months.id", ondelete="CASCADE"))
    amount = Column(Float)
    method = Column(String(50))
    date_str = Column(String(30))      # e.g. "08 Jul 2026"
    day = Column(Integer)
    balance_after = Column(Float)
    timestamp = Column(DateTime, default=func.now())

class MonthSetup(Base):
    __tablename__ = "months"
    id = Column(Integer, primary_key=True, index=True)
    tenant_name = Column(String(100))
    account_no = Column(String(50), index=True)
    bill_month = Column(String(7), unique=True)  # YYYY-MM
    base_rent = Column(Float)
    carry_over = Column(Float, default=0.0)
    total_due = Column(Float)
    paid = Column(Float, default=0.0)
    
    amenities = relationship("Amenity", backref="month", cascade="all, delete-orphan")
    payments = relationship("Payment", backref="month", cascade="all, delete-orphan", order_by=Payment.timestamp.desc())

Base.metadata.create_all(bind=engine)

# ====================== PYDANTIC SCHEMAS ======================
class AmenityIn(BaseModel):
    name: str
    cost: float

class PaymentIn(BaseModel):
    amount: float
    method: str = "M-Pesa"

class MonthSetupIn(BaseModel):
    tenant_name: str
    account_no: str
    bill_month: str
    base_rent: float
    amenities: List[AmenityIn] = []
    carry_over: float = 0.0

class MonthOut(BaseModel):
    id: int
    tenant_name: str
    account_no: str
    bill_month: str
    base_rent: float
    carry_over: float
    total_due: float
    paid: float
    remaining: float
    amenities: List[Dict]
    payments: List[Dict]
    progress: float

class PaymentResponse(BaseModel):
    success: bool
    new_paid: float
    balance_after: float
    payment: Dict

# ====================== FASTAPI APP ======================
app = FastAPI(
    title="Mwarokin Estates — Lipa Mdogo Mdogo API",
    description="Modern backend for monthly micro-payments rent tracker",
    version="2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ====================== UTILITIES ======================
def calculate_month_state(month: MonthSetup):
    amenities_list = [{"name": a.name, "cost": a.cost} for a in month.amenities]
    payments_list = [
        {
            "date": p.date_str,
            "amount": p.amount,
            "method": p.method,
            "balance_after": p.balance_after,
            "day": p.day
        }
        for p in month.payments
    ]
    remaining = max(month.total_due - month.paid, 0)
    progress = (month.paid / month.total_due * 100) if month.total_due > 0 else 0
    
    return {
        "id": month.id,
        "tenant_name": month.tenant_name,
        "account_no": month.account_no,
        "bill_month": month.bill_month,
        "base_rent": month.base_rent,
        "carry_over": month.carry_over,
        "total_due": month.total_due,
        "paid": month.paid,
        "remaining": remaining,
        "amenities": amenities_list,
        "payments": payments_list,
        "progress": round(progress, 2)
    }

# ====================== ENDPOINTS ======================
@app.get("/")
async def root():
    return {"message": "🚀 Lipa Mdogo Mdogo Backend Running", "status": "live"}

@app.post("/api/setup", response_model=MonthOut)
def setup_month(data: MonthSetupIn, db: Session = Depends(get_db)):
    # Check existing month
    month = db.query(MonthSetup).filter(MonthSetup.bill_month == data.bill_month).first()
    
    if not month:
        month = MonthSetup(
            tenant_name=data.tenant_name,
            account_no=data.account_no,
            bill_month=data.bill_month,
            base_rent=data.base_rent,
            carry_over=data.carry_over,
        )
        db.add(month)
        db.commit()
        db.refresh(month)
    else:
        # Update existing
        month.tenant_name = data.tenant_name
        month.account_no = data.account_no
        month.base_rent = data.base_rent
        month.carry_over = data.carry_over
        db.commit()
    
    # Replace amenities
    db.query(Amenity).filter(Amenity.month_id == month.id).delete()
    for am in data.amenities:
        amenity = Amenity(name=am.name, cost=am.cost, month_id=month.id)
        db.add(amenity)
    db.commit()
    db.refresh(month)
    
    # Recalculate total due
    amenities_sum = sum(a.cost for a in month.amenities)
    month.total_due = month.base_rent + amenities_sum + month.carry_over
    db.commit()
    
    return calculate_month_state(month)

@app.get("/api/month/{bill_month}", response_model=MonthOut)
def get_month_state(bill_month: str, db: Session = Depends(get_db)):
    month = db.query(MonthSetup).filter(MonthSetup.bill_month == bill_month).first()
    if not month:
        raise HTTPException(status_code=404, detail="Month setup not found")
    return calculate_month_state(month)

@app.post("/api/pay/{bill_month}", response_model=PaymentResponse)
def make_payment(bill_month: str, payment: PaymentIn, db: Session = Depends(get_db)):
    month = db.query(MonthSetup).filter(MonthSetup.bill_month == bill_month).first()
    if not month:
        raise HTTPException(status_code=404, detail="Month not found")
    
    remaining = max(month.total_due - month.paid, 0)
    if remaining <= 0:
        raise HTTPException(status_code=400, detail="Balance already cleared for this month")
    
    if payment.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    now = datetime.now()
    new_paid = month.paid + payment.amount
    balance_after = max(month.total_due - new_paid, 0)
    
    pay = Payment(
        month_id=month.id,
        amount=payment.amount,
        method=payment.method,
        date_str=now.strftime("%d %b %Y"),
        day=now.day,
        balance_after=balance_after
    )
    db.add(pay)
    month.paid = new_paid
    db.commit()
    db.refresh(month)
    
    return {
        "success": True,
        "new_paid": new_paid,
        "balance_after": balance_after,
        "payment": {
            "date": pay.date_str,
            "amount": pay.amount,
            "method": pay.method,
            "balance_after": balance_after,
            "day": pay.day
        }
    }

@app.get("/api/months")
def list_all_months(db: Session = Depends(get_db)):
    months = db.query(MonthSetup).order_by(MonthSetup.bill_month.desc()).all()
    return [
        {
            "bill_month": m.bill_month,
            "tenant_name": m.tenant_name,
            "account_no": m.account_no,
            "total_due": m.total_due,
            "paid": m.paid,
            "remaining": max(m.total_due - m.paid, 0)
        }
        for m in months
    ]

@app.post("/api/reset-month/{bill_month}")
def reset_month(bill_month: str, db: Session = Depends(get_db)):
    month = db.query(MonthSetup).filter(MonthSetup.bill_month == bill_month).first()
    if not month:
        raise HTTPException(status_code=404, detail="Month not found")
    
    remaining = max(month.total_due - month.paid, 0)
    
    # Carry over to next month logic can be handled on frontend/backend as needed
    month.carry_over = remaining
    month.paid = 0.0
    db.query(Payment).filter(Payment.month_id == month.id).delete()
    db.commit()
    
    return {"message": "Month reset. Balance carried over.", "new_carry_over": remaining}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### How to run:

1. Save the code above as `main.py`
2. Create `requirements.txt`:

```txt
fastapi>=0.115.0
uvicorn[standard]
sqlalchemy>=2.0.0
pydantic>=2.0.0
```

3. Install & run:

```bash
pip install -r requirements.txt
python main.py
```

**API Base**: `http://localhost:8000`

**Key Endpoints**:
- `POST /api/setup` → Create/update monthly rent setup
- `GET /api/month/{YYYY-MM}` → Full state (for ring, beads, ledger)
- `POST /api/pay/{YYYY-MM}` → Record a payment (real-time updates)
- `GET /api/months` → List history

The backend mirrors all logic from your frontend JS (totals, progress, beads via `day`, ledger, etc.) and uses SQLite for persistence. The frontend can be updated to call these APIs instead of local storage. Let me know if you need the updated frontend integration script or Docker setup!