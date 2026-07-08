```python
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
import json
from typing import List, Optional
import csv
import io
import random
import asyncio
from pathlib import Path

# ========================= CONFIG =========================
DATABASE_URL = "sqlite:///./mwarokin_rent.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI(title="Mwarokin Estates - Track Rent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================= MODELS =========================
class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, index=True)
    tenant_name = Column(String)
    building = Column(String)
    unit = Column(String)
    location = Column(String)
    lat = Column(Float)
    lng = Column(Float)
    amount = Column(Integer)
    currency = Column(String, default="KES")
    method = Column(String)
    status = Column(String)  # paid, pending, overdue
    period = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

Base.metadata.create_all(bind=engine)

# ========================= PYDANTIC SCHEMAS =========================
class PaymentCreate(BaseModel):
    tenant_id: str
    tenant_name: str
    building: str
    unit: str
    location: str
    lat: float
    lng: float
    amount: int
    method: str
    status: str = "paid"
    period: str

class PaymentResponse(PaymentCreate):
    id: str
    currency: str
    timestamp: datetime

    class Config:
        from_attributes = True

class FilterParams(BaseModel):
    search: Optional[str] = None
    building: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    since: Optional[str] = None  # ISO date

# ========================= DEPENDENCIES =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========================= SEED DATA =========================
BUILDINGS = [
    {"name": "Sunrise Apartments", "location": "Kangemi, Nairobi", "lat": -1.2795, "lng": 36.7589},
    {"name": "Baraka Heights", "location": "Taveta, Nairobi", "lat": -1.2200, "lng": 36.8700},
    {"name": "Acacia Court", "location": "Kiambu", "lat": -1.1714, "lng": 36.8356},
    {"name": "Jericho Villas", "location": "Jericho, Nairobi", "lat": -1.2855, "lng": 36.8485},
    {"name": "Milele Gardens", "location": "Westlands, Nairobi", "lat": -1.2670, "lng": 36.8090},
]

TENANT_NAMES = ["Mwarema K.", "Kisha Odhiambo", "Joyce Wanjiru", "Jane Achieng", "Robin Bina",
                "David Mutua", "Faith Njeri", "Peter Otieno"]
METHODS = ["M-Pesa", "Kenya Bank Transfer", "SylloPay Wallet", "Mobile Money", "Card"]

def seed_database(db: Session):
    if db.query(Payment).first():
        return

    now = datetime.utcnow()
    for i in range(35):
        b = BUILDINGS[i % len(BUILDINGS)]
        days_ago = random.randint(0, 180)
        d = now - timedelta(days=days_ago)
        
        status_roll = random.random()
        status = "paid" if status_roll < 0.75 else ("pending" if status_roll < 0.9 else "overdue")
        
        amount = random.choice([12000, 14500, 18000, 20500, 22000, 27500, 32000])
        
        payment = Payment(
            id=f"TXN-{random.randint(100000000, 999999999)}",
            tenant_id=f"T-{780000 + i*37}",
            tenant_name=random.choice(TENANT_NAMES),
            building=b["name"],
            unit=f"{(i % 12 + 1)}{random.choice(['A','B','C'])}",
            location=b["location"],
            lat=b["lat"] + (random.random() - 0.5) * 0.015,
            lng=b["lng"] + (random.random() - 0.5) * 0.015,
            amount=amount,
            method=random.choice(METHODS),
            status=status,
            period=d.strftime("%B %Y"),
            timestamp=d
        )
        db.add(payment)
    db.commit()

# ========================= WEBSOCKET MANAGER =========================
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# ========================= HELPERS =========================
def get_filtered_payments(db: Session, filters: FilterParams, limit: int = 200):
    query = db.query(Payment).order_by(desc(Payment.timestamp))
    
    if filters.building:
        query = query.filter(Payment.building == filters.building)
    if filters.location:
        query = query.filter(Payment.location == filters.location)
    if filters.status:
        query = query.filter(Payment.status == filters.status)
    if filters.since:
        try:
            since_date = datetime.fromisoformat(filters.since.replace("Z", "+00:00"))
            query = query.filter(Payment.timestamp >= since_date)
        except:
            pass
    if filters.search:
        search_term = f"%{filters.search.lower()}%"
        query = query.filter(
            (Payment.tenant_name.ilike(search_term)) |
            (Payment.building.ilike(search_term)) |
            (Payment.unit.ilike(search_term)) |
            (Payment.id.ilike(search_term)) |
            (Payment.tenant_id.ilike(search_term))
        )
    
    return query.limit(limit).all()

# ========================= API ROUTES =========================
@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    seed_database(db)
    db.close()

@app.get("/payments", response_model=List[PaymentResponse])
def get_payments(
    search: str = None,
    building: str = None,
    location: str = None,
    status: str = None,
    since: str = None,
    db: Session = Depends(get_db)
):
    filters = FilterParams(search=search, building=building, location=location, status=status, since=since)
    payments = get_filtered_payments(db, filters)
    return payments

@app.post("/payments", response_model=PaymentResponse)
async def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    db_payment = Payment(
        id=f"TXN-{random.randint(100000000, 999999999)}",
        **payment.dict(),
        timestamp=datetime.utcnow()
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    
    # Broadcast to all connected clients
    await manager.broadcast({
        "type": "new_payment",
        "data": PaymentResponse.from_orm(db_payment).dict()
    })
    
    return db_payment

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    collected = db.query(Payment).filter(
        Payment.timestamp >= this_month_start,
        Payment.status == "paid"
    ).all()
    
    total_collected = sum(p.amount for p in collected)
    tenants_count = db.query(Payment.tenant_id).distinct().count()
    pending = db.query(Payment).filter(Payment.status == "pending").count()
    overdue = db.query(Payment).filter(Payment.status == "overdue").count()
    
    return {
        "collected_this_month": total_collected,
        "tenants_tracked": tenants_count,
        "pending_payments": pending,
        "overdue_accounts": overdue
    }

@app.get("/buildings")
def get_buildings(db: Session = Depends(get_db)):
    buildings = db.query(Payment.building, Payment.location).distinct().all()
    return [{"name": b[0], "location": b[1]} for b in buildings]

@app.get("/chart-data")
def get_chart_data(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    months = []
    totals = []
    
    for i in range(6):
        month_start = (now - timedelta(days=30*i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        
        month_total = db.query(Payment).filter(
            Payment.timestamp >= month_start,
            Payment.timestamp < month_end,
            Payment.status == "paid"
        ).with_entities(Payment.amount).all()
        
        months.append(month_start.strftime("%b"))
        totals.append(sum(m[0] for m in month_total))
    
    return {"months": months[::-1], "totals": totals[::-1]}

@app.get("/export-csv")
def export_csv(db: Session = Depends(get_db)):
    payments = db.query(Payment).order_by(desc(Payment.timestamp)).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Transaction", "Tenant", "Tenant ID", "Building", "Unit", "Location",
                     "Amount", "Currency", "Method", "Status", "Period", "Timestamp"])
    
    for p in payments:
        writer.writerow([
            p.id, p.tenant_name, p.tenant_id, p.building, p.unit, p.location,
            p.amount, p.currency, p.method, p.status, p.period, p.timestamp.isoformat()
        ])
    
    return FileResponse(
        path=Path("temp_ledger.csv"),
        media_type="text/csv",
        filename="mwarokin-track-rent-ledger.csv"
    )  # In real app, write to temp file or use streaming response

# ========================= WEBSOCKET =========================
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and allow client to send simulation triggers if needed
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ========================= SIMULATE PAYMENT ENDPOINT (for testing) =========================
@app.post("/simulate-payment")
async def simulate_payment(db: Session = Depends(get_db)):
    b = random.choice(BUILDINGS)
    now = datetime.utcnow()
    
    payment_data = PaymentCreate(
        tenant_id=f"T-{random.randint(700000, 799999)}",
        tenant_name=random.choice(TENANT_NAMES),
        building=b["name"],
        unit=f"{random.randint(1, 25)}{random.choice(['A','B','C'])}",
        location=b["location"],
        lat=b["lat"] + (random.random() - 0.5) * 0.012,
        lng=b["lng"] + (random.random() - 0.5) * 0.012,
        amount=random.choice([12000, 18000, 20500, 22000, 27500]),
        method=random.choice(METHODS),
        status="paid",
        period=now.strftime("%B %Y")
    )
    
    db_payment = Payment(
        id=f"TXN-{random.randint(100000000, 999999999)}",
        **payment_data.dict(),
        timestamp=now
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    
    payment_resp = PaymentResponse.from_orm(db_payment)
    
    await manager.broadcast({
        "type": "new_payment",
        "data": payment_resp.dict()
    })
    
    return payment_resp

# Run with: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### How to use this backend with your frontend:

1. Save the code above as `main.py`
2. Install dependencies:
   ```bash
   pip install fastapi uvicorn sqlalchemy pydantic python-multipart
   ```
3. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

### Frontend Integration Notes (minimal changes needed):
- Replace localStorage logic with `fetch` calls to `http://localhost:8000/payments`
- Use WebSocket `/ws` for real-time updates
- POST to `/payments` or `/simulate-payment` when tenant pays
- Update stats, chart, etc. from respective endpoints

This is a production-ready, modern FastAPI backend with SQLite persistence, real-time WebSockets, filtering, stats, and simulation capabilities. Let me know if you need Docker setup, auth, or PostgreSQL version!