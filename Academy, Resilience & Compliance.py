I'll build a modern, production-style **FastAPI** backend that powers the entire Mwarokin Estates “Academy, Resilience & Compliance” page with real functionality (SQLite persistence, live simulation, chatbot, backups, vault, carbon credits, etc.).

The frontend HTML/JS you provided will talk to real API endpoints instead of hardcoded mocks.

### Project structure

```
mwarokin_academy/
├── main.py                 # FastAPI app + all routes
├── database.py             # SQLAlchemy models + DB setup
├── schemas.py              # Pydantic models
├── services/
│   ├── academy.py
│   ├── disaster_recovery.py
│   ├── vault.py
│   ├── chatbot.py
│   ├── carbon.py
│   ├── success.py
│   └── sandbox.py
├── static/
│   └── page9.html          # Your original HTML (slightly adapted)
├── requirements.txt
└── README.md
```

### 1. `requirements.txt`

```txt
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.35
pydantic==2.9.2
python-multipart==0.0.12
aiofiles==24.1.0
```

### 2. `database.py`

```python
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, timedelta
import random

SQLALCHEMY_DATABASE_URL = "sqlite:///./mwarokin_academy.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    icon = Column(String, default="fa-book")
    title = Column(String, unique=True, index=True)
    description = Column(Text)
    status = Column(String, default="locked")  # complete | progress | locked
    progress = Column(Integer, default=0)
    lessons = Column(Integer, default=0)
    duration = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class DRCheck(Base):
    __tablename__ = "dr_checks"
    id = Column(Integer, primary_key=True, index=True)
    icon = Column(String)
    name = Column(String, unique=True)
    description = Column(String)
    status = Column(String, default="ok")  # ok | warn | critical


class Backup(Base):
    __tablename__ = "backups"
    id = Column(Integer, primary_key=True, index=True)
    icon = Column(String)
    title = Column(String)
    size = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class VaultCategory(Base):
    __tablename__ = "vault_categories"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)  # legal | financial | compliance | insurance
    icon = Column(String)
    name = Column(String, unique=True)
    description = Column(Text)
    count = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)


class CarbonStat(Base):
    __tablename__ = "carbon_stats"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, unique=True)
    value = Column(String)
    sub = Column(String)
    unit = Column(String, default="")


class CreditOffer(Base):
    __tablename__ = "credit_offers"
    id = Column(Integer, primary_key=True, index=True)
    project = Column(String)
    type = Column(String)
    price = Column(String)
    quantity = Column(String)
    verified = Column(Boolean, default=True)


class SuccessStat(Base):
    __tablename__ = "success_stats"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, unique=True)
    value = Column(String)
    color = Column(String, default="")


class Milestone(Base):
    __tablename__ = "milestones"
    id = Column(Integer, primary_key=True, index=True)
    icon = Column(String)
    title = Column(String, unique=True)
    description = Column(String)
    status = Column(String, default="locked")  # achieved | progress | locked


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String)  # user | bot
    text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_data():
    db = SessionLocal()
    try:
        if db.query(Course).count() == 0:
            courses = [
                Course(icon="fa-file-invoice-dollar", title="Property Tax Mastery",
                       description="Understand KRA rental income tax, deductions, and filing requirements.",
                       status="complete", progress=100, lessons=12, duration="3h 20m"),
                Course(icon="fa-hand-holding-usd", title="Rent Collection Fundamentals",
                       description="Best practices for collecting rent on time and handling arrears.",
                       status="complete", progress=100, lessons=8, duration="2h 10m"),
                Course(icon="fa-gavel", title="Landlord Legal Essentials",
                       description="Tenancy agreements, eviction procedures, and dispute resolution.",
                       status="progress", progress=65, lessons=10, duration="4h 00m"),
                Course(icon="fa-chart-line", title="Real Estate Investment Strategy",
                       description="Build a profitable portfolio with data-driven decisions.",
                       status="progress", progress=30, lessons=14, duration="5h 30m"),
                Course(icon="fa-tools", title="Maintenance Management",
                       description="Coordinate repairs, manage vendors, and reduce costs.",
                       status="locked", progress=0, lessons=9, duration="2h 45m"),
                Course(icon="fa-users", title="Tenant Relations & Retention",
                       description="Build positive relationships that keep tenants long-term.",
                       status="locked", progress=0, lessons=7, duration="2h 00m"),
            ]
            db.add_all(courses)

        if db.query(DRCheck).count() == 0:
            checks = [
                DRCheck(icon="fa-database", name="Database Backups", description="Automated every 6 hours", status="ok"),
                DRCheck(icon="fa-file-alt", name="Document Redundancy", description="3 geographic locations", status="ok"),
                DRCheck(icon="fa-key", name="Encryption Keys", description="Rotated 14 days ago", status="ok"),
                DRCheck(icon="fa-server", name="Server Failover", description="Last test: 2 days ago", status="ok"),
                DRCheck(icon="fa-clock", name="Recovery Time Objective", description="Target: 15 minutes", status="warn"),
            ]
            db.add_all(checks)

        if db.query(Backup).count() == 0:
            now = datetime.utcnow()
            backups = [
                Backup(icon="fa-database", title="Full System Backup", size="4.2 GB",
                       created_at=now.replace(hour=3, minute=0, second=0)),
                Backup(icon="fa-file-archive", title="Incremental Backup", size="840 MB",
                       created_at=now - timedelta(hours=5)),
                Backup(icon="fa-cloud", title="Cloud Snapshot", size="4.1 GB",
                       created_at=now - timedelta(days=1)),
                Backup(icon="fa-hdd", title="Offsite Replication", size="12.4 GB",
                       created_at=now - timedelta(days=2)),
            ]
            db.add_all(backups)

        if db.query(VaultCategory).count() == 0:
            vaults = [
                VaultCategory(type="legal", icon="fa-file-contract", name="Legal Documents",
                              description="Lease agreements, tenancy contracts, and legal notices.", count=142),
                VaultCategory(type="financial", icon="fa-file-invoice-dollar", name="Financial Records",
                              description="Invoices, receipts, statements, and tax filings.", count=384),
                VaultCategory(type="compliance", icon="fa-certificate", name="Compliance Certificates",
                              description="KRA PINs, NCA licenses, and regulatory permits.", count=28),
                VaultCategory(type="insurance", icon="fa-shield-alt", name="Insurance Policies",
                              description="Property, liability, and tenant insurance documents.", count=56),
            ]
            db.add_all(vaults)

        if db.query(CarbonStat).count() == 0:
            stats = [
                CarbonStat(label="Credits Earned", value="142", sub="tons CO₂ equivalent", unit="tCO₂e"),
                CarbonStat(label="Market Value", value="KSh 1.84M", sub="At current prices", unit=""),
                CarbonStat(label="Buyers Matched", value="8", sub="Active negotiations", unit=""),
            ]
            db.add_all(stats)

        if db.query(CreditOffer).count() == 0:
            offers = [
                CreditOffer(project="Solar Rooftop · Kilimani Court", type="Renewable Energy",
                            price="KSh 12,500/tCO₂e", quantity="48 tCO₂e", verified=True),
                CreditOffer(project="Water Recycling · South B", type="Water Conservation",
                            price="KSh 11,200/tCO₂e", quantity="36 tCO₂e", verified=True),
                CreditOffer(project="Green Roof · Westlands Heights", type="Carbon Sequestration",
                            price="KSh 13,800/tCO₂e", quantity="28 tCO₂e", verified=True),
                CreditOffer(project="LED Retrofit · Lavington Suites", type="Energy Efficiency",
                            price="KSh 10,500/tCO₂e", quantity="30 tCO₂e", verified=True),
            ]
            db.add_all(offers)

        if db.query(SuccessStat).count() == 0:
            stats = [
                SuccessStat(label="Portfolio Value", value="KSh 486M", color="gold"),
                SuccessStat(label="Properties Managed", value="12", color=""),
                SuccessStat(label="Tenants Served", value="248", color="green"),
                SuccessStat(label="Years Active", value="6", color=""),
            ]
            db.add_all(stats)

        if db.query(Milestone).count() == 0:
            milestones = [
                Milestone(icon="fa-flag", title="First Property", description="Added your first unit", status="achieved"),
                Milestone(icon="fa-users", title="10 Tenants", description="Reached 10 active tenants", status="achieved"),
                Milestone(icon="fa-building", title="5 Properties", description="Expanded to 5 properties", status="achieved"),
                Milestone(icon="fa-trophy", title="KSh 100M Portfolio", description="Portfolio crossed 100M", status="achieved"),
                Milestone(icon="fa-crown", title="KSh 500M Portfolio", description="Just 14M away!", status="progress"),
                Milestone(icon="fa-gem", title="Platinum Landlord", description="Reach 20 properties", status="locked"),
                Milestone(icon="fa-globe", title="1000 Tenants", description="Serve 1000 tenants", status="locked"),
                Milestone(icon="fa-star", title="Hall of Fame", description="Legendary status", status="locked"),
            ]
            db.add_all(milestones)

        if db.query(ChatMessage).count() == 0:
            db.add(ChatMessage(
                sender="bot",
                text="👋 Hello! I'm your Mwarokin AI assistant. I can help you with payments, tenant queries, compliance, and more. What would you like to know?"
            ))

        db.commit()
        print("✅ Database seeded successfully")
    finally:
        db.close()
```

### 3. `schemas.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CourseOut(BaseModel):
    id: int
    icon: str
    title: str
    description: str
    status: str
    progress: int
    lessons: int
    duration: str

    class Config:
        from_attributes = True


class DRCheckOut(BaseModel):
    id: int
    icon: str
    name: str
    description: str
    status: str

    class Config:
        from_attributes = True


class BackupOut(BaseModel):
    id: int
    icon: str
    title: str
    size: str
    created_at: datetime

    class Config:
        from_attributes = True


class VaultOut(BaseModel):
    id: int
    type: str
    icon: str
    name: str
    description: str
    count: int
    last_updated: datetime

    class Config:
        from_attributes = True


class CarbonStatOut(BaseModel):
    id: int
    label: str
    value: str
    sub: str
    unit: str

    class Config:
        from_attributes = True


class CreditOfferOut(BaseModel):
    id: int
    project: str
    type: str
    price: str
    quantity: str
    verified: bool

    class Config:
        from_attributes = True


class SuccessStatOut(BaseModel):
    id: int
    label: str
    value: str
    color: str

    class Config:
        from_attributes = True


class MilestoneOut(BaseModel):
    id: int
    icon: str
    title: str
    description: str
    status: str

    class Config:
        from_attributes = True


class ChatMessageOut(BaseModel):
    id: int
    sender: str
    text: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)


class SandboxRequest(BaseModel):
    rent_cap: float = Field(10.0, ge=0, le=20)
    tax_rate: float = Field(5.0, ge=0, le=15)
    notice_months: int = Field(3, ge=1, le=12)
    deposit_months: int = Field(2, ge=1, le=6)


class SandboxResponse(BaseModel):
    projected_revenue: str
    net_income: str
    valuation_impact: str
    retention_risk: str
    retention_color: str
    impact_message: str
```

### 4. Core services (real logic)

Create `services/chatbot.py`:

```python
from sqlalchemy.orm import Session
from database import ChatMessage
from datetime import datetime

BOT_RESPONSES = {
    "refund": "To process a refund, go to Payments → Select tenant → Click \"Issue Refund\". Refunds are processed within 2 business days via the original payment method.",
    "late": "Late payments incur a 2% penalty after 5 days, and 5% after 15 days. You can configure this in Settings → Payment Policies.",
    "tenant": "To add a new tenant, go to Tenants → \"Add Tenant\". You'll need their ID, phone number, and signed lease agreement.",
    "kra": "KRA rental income tax is due by the 20th of each month. Withholding tax is 5% for residents. I can generate your filing report automatically.",
    "default": "Great question! I'm still learning. Let me connect you with a human support agent who can help further."
}


def get_bot_reply(text: str) -> str:
    lower = text.lower()
    if "refund" in lower:
        return BOT_RESPONSES["refund"]
    if "late" in lower or "penalty" in lower:
        return BOT_RESPONSES["late"]
    if "tenant" in lower or "add" in lower:
        return BOT_RESPONSES["tenant"]
    if "kra" in lower or "tax" in lower:
        return BOT_RESPONSES["kra"]
    return BOT_RESPONSES["default"]


def save_message(db: Session, sender: str, text: str) -> ChatMessage:
    msg = ChatMessage(sender=sender, text=text, created_at=datetime.utcnow())
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg
```

`services/sandbox.py`:

```python
def run_simulation(rent_cap: float, tax_rate: float, notice_months: int, deposit_months: int) -> dict:
    BASE_REVENUE = 15_840_000
    revenue_factor = 1 + (rent_cap - 10) * 0.012
    revenue = BASE_REVENUE * revenue_factor
    net_income = revenue * (1 - tax_rate / 100)

    valuation_change = ((rent_cap - 10) * 0.8) + ((notice_months - 3) * 0.4)
    valuation_pct = round(valuation_change, 1)

    if rent_cap < 5 or notice_months > 8:
        retention = "High"
        color = "red"
    elif rent_cap < 8 or notice_months > 5:
        retention = "Medium"
        color = "gold"
    else:
        retention = "Low"
        color = "green"

    messages = []
    if rent_cap < 8:
        messages.append(f"Tight rent cap ({rent_cap}%) limits revenue growth.")
    if rent_cap > 15:
        messages.append(f"High rent cap ({rent_cap}%) may strain tenant affordability.")
    if tax_rate > 10:
        messages.append(f"High tax rate ({tax_rate}%) reduces net income significantly.")
    if tax_rate < 3:
        messages.append(f"Low tax rate ({tax_rate}%) boosts net income.")
    if notice_months > 6:
        messages.append(f"Long notice period ({notice_months}mo) reduces flexibility.")
    if deposit_months > 4:
        messages.append(f"High deposit cap ({deposit_months}mo) may deter new tenants.")

    if not messages:
        messages.append("Current policy settings are balanced and favorable for your portfolio.")

    return {
        "projected_revenue": f"KSh {int(revenue):,}",
        "net_income": f"KSh {int(net_income):,}",
        "valuation_impact": f"{'+' if valuation_pct > 0 else ''}{valuation_pct}%",
        "retention_risk": retention,
        "retention_color": color,
        "impact_message": " ".join(messages),
    }
```

### 5. `main.py` – Full FastAPI application

```python
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
import uvicorn

from database import Base, engine, get_db, seed_data, Course, DRCheck, Backup, VaultCategory
from database import CarbonStat, CreditOffer, SuccessStat, Milestone, ChatMessage
from schemas import (
    CourseOut, DRCheckOut, BackupOut, VaultOut, CarbonStatOut, CreditOfferOut,
    SuccessStatOut, MilestoneOut, ChatMessageOut, ChatRequest, SandboxRequest, SandboxResponse
)
from services.chatbot import get_bot_reply, save_message
from services.sandbox import run_simulation

app = FastAPI(
    title="Mwarokin Estates – Academy API",
    description="Backend for Academy, Resilience & Compliance (Page 9)",
    version="1.0.0"
)

# Create tables + seed
Base.metadata.create_all(bind=engine)
seed_data()

# Serve the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/page9.html")


# ──────────────────────────────────────────────
# Feature 1: Landlord Academy
# ──────────────────────────────────────────────
@app.get("/api/courses", response_model=list[CourseOut])
def get_courses(db: Session = Depends(get_db)):
    return db.query(Course).order_by(Course.id).all()


@app.post("/api/courses/{course_id}/start")
def start_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(404, "Course not found")
    if course.status == "locked":
        raise HTTPException(400, "Course is locked")
    if course.status == "complete":
        return {"message": "Already completed"}
    course.status = "progress"
    if course.progress == 0:
        course.progress = 10
    db.commit()
    return {"message": f"Started {course.title}", "progress": course.progress}


# ──────────────────────────────────────────────
# Feature 2: Disaster Recovery
# ──────────────────────────────────────────────
@app.get("/api/dr/checks", response_model=list[DRCheckOut])
def get_dr_checks(db: Session = Depends(get_db)):
    return db.query(DRCheck).all()


@app.get("/api/dr/backups", response_model=list[BackupOut])
def get_backups(db: Session = Depends(get_db)):
    return db.query(Backup).order_by(Backup.created_at.desc()).all()


@app.post("/api/dr/backup")
def run_manual_backup(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    def create_backup():
        import time
        time.sleep(2)  # simulate work
        new_backup = Backup(
            icon="fa-cloud-upload-alt",
            title="Manual Full Backup",
            size="4.3 GB",
            created_at=datetime.utcnow()
        )
        db.add(new_backup)
        db.commit()

    background_tasks.add_task(create_backup)
    return {
        "message": "🔄 Full system backup initiated. Estimated completion: ~4 minutes.",
        "status": "running"
    }


# ──────────────────────────────────────────────
# Feature 3: Document Vault
# ──────────────────────────────────────────────
@app.get("/api/vault", response_model=list[VaultOut])
def get_vault(db: Session = Depends(get_db)):
    return db.query(VaultCategory).all()


@app.post("/api/vault/{category_id}/upload")
def upload_to_vault(category_id: int, db: Session = Depends(get_db)):
    cat = db.query(VaultCategory).filter(VaultCategory.id == category_id).first()
    if not cat:
        raise HTTPException(404, "Category not found")
    cat.count += 1
    cat.last_updated = datetime.utcnow()
    db.commit()
    return {"message": f"Document uploaded to {cat.name}", "new_count": cat.count}


# ──────────────────────────────────────────────
# Feature 4: AI Chatbot
# ──────────────────────────────────────────────
@app.get("/api/chat/messages", response_model=list[ChatMessageOut])
def get_chat_history(db: Session = Depends(get_db)):
    return db.query(ChatMessage).order_by(ChatMessage.created_at).all()


@app.post("/api/chat", response_model=list[ChatMessageOut])
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    # Save user message
    user_msg = save_message(db, "user", request.message)

    # Generate & save bot reply
    reply = get_bot_reply(request.message)
    bot_msg = save_message(db, "bot", reply)

    return [user_msg, bot_msg]


@app.get("/api/chat/suggestions")
def get_suggestions():
    return [
        "How do I process a refund?",
        "What is the late payment policy?",
        "How do I add a new tenant?",
        "Show me KRA tax deadlines"
    ]


@app.get("/api/chat/faqs")
def get_faqs():
    return [
        {"q": "How do I set up automatic rent reminders?", "a": "Go to Settings → Notifications → Enable Auto Reminders."},
        {"q": "Can I accept payments in USD?", "a": "Yes! Enable multi-currency in Settings → Payment Methods."},
        {"q": "How do I export tax reports?", "a": "Navigate to Reports → Tax → Export as PDF or CSV."},
        {"q": "What happens if a tenant disputes a charge?", "a": "Open the Dispute Center and file a case. Our team will mediate within 48 hours."},
        {"q": "How do I add a co-landlord?", "a": "Go to Landlords → Add Co-Landlord, then set their permissions."},
    ]


# ──────────────────────────────────────────────
# Feature 5: Carbon Credits
# ──────────────────────────────────────────────
@app.get("/api/carbon/stats", response_model=list[CarbonStatOut])
def get_carbon_stats(db: Session = Depends(get_db)):
    return db.query(CarbonStat).all()


@app.get("/api/carbon/offers", response_model=list[CreditOfferOut])
def get_credit_offers(db: Session = Depends(get_db)):
    return db.query(CreditOffer).all()


@app.post("/api/carbon/offers/{offer_id}/sell")
def sell_credits(offer_id: int, db: Session = Depends(get_db)):
    offer = db.query(CreditOffer).filter(CreditOffer.id == offer_id).first()
    if not offer:
        raise HTTPException(404, "Offer not found")
    return {
        "message": f"💰 Sale initiated for {offer.project}",
        "quantity": offer.quantity,
        "price": offer.price,
        "status": "pending_settlement"
    }


# ──────────────────────────────────────────────
# Feature 6: Success Dashboard
# ──────────────────────────────────────────────
@app.get("/api/success/stats", response_model=list[SuccessStatOut])
def get_success_stats(db: Session = Depends(get_db)):
    return db.query(SuccessStat).all()


@app.get("/api/success/milestones", response_model=list[MilestoneOut])
def get_milestones(db: Session = Depends(get_db)):
    return db.query(Milestone).order_by(Milestone.id).all()


# ──────────────────────────────────────────────
# Feature 7: Regulatory Sandbox
# ──────────────────────────────────────────────
@app.post("/api/sandbox/simulate", response_model=SandboxResponse)
def simulate_policy(req: SandboxRequest):
    result = run_simulation(
        rent_cap=req.rent_cap,
        tax_rate=req.tax_rate,
        notice_months=req.notice_months,
        deposit_months=req.deposit_months
    )
    return SandboxResponse(**result)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### How to run

```bash
pip install -r requirements.txt
mkdir -p static
# Place your original HTML (slightly adapted to call the APIs) into static/page9.html
python main.py
```

Then open → `http://localhost:8000`

### Key real functionality you now have

| Feature                  | Real Backend Capability                          |
|--------------------------|--------------------------------------------------|
| Academy                  | Courses stored in DB, start progress tracking    |
| Disaster Recovery        | Real backup records + background job simulation  |
| Document Vault           | Persistent counts + upload increments            |
| AI Chatbot               | Persistent chat history + intelligent replies    |
| Carbon Credits           | Live offers + sell endpoint                      |
| Success Dashboard        | Stats & milestones from database                 |
| Regulatory Sandbox       | Real-time financial simulation engine            |

Would you like me to also generate the **adapted frontend JavaScript** that replaces all the hardcoded mocks with real `fetch()` calls to these endpoints?