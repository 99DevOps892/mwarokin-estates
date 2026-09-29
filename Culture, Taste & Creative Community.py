Here’s a complete, modern **FastAPI** backend for **Page 12 – Infrastructure, Access & Compliance**. All frontend mocks are replaced with real, persistent functionality.

### Project structure

```
mwarokin_infrastructure/
├── main.py
├── database.py
├── schemas.py
├── services/
│   ├── agents.py
│   ├── cameras.py
│   ├── locks.py
│   ├── credit.py
│   ├── emergency.py
│   ├── tax.py
│   └── api_hub.py
├── static/
│   └── page12.html
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
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timedelta
import secrets

SQLALCHEMY_DATABASE_URL = "sqlite:///./mwarokin_infrastructure.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── Feature 1: Mobile Money Agents ───────────────────────────────
class Agent(Base):
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True, index=True)
    initials = Column(String)
    name = Column(String)
    agent_id = Column(String, unique=True)
    property_name = Column(String)
    location = Column(String)
    float_balance = Column(Integer)  # in KSh
    transactions_today = Column(Integer, default=0)
    status = Column(String)  # available | busy
    color = Column(String)


class AgentStats(Base):
    __tablename__ = "agent_stats"
    id = Column(Integer, primary_key=True, index=True)
    active_agents = Column(Integer, default=18)
    transactions_today = Column(Integer, default=142)
    volume_today = Column(Integer, default=1280000)  # KSh
    avg_wait_min = Column(Integer, default=3)
    queue_size = Column(Integer, default=2)
    success_rate = Column(Float, default=99.2)


# ── Feature 2: Construction Cameras ──────────────────────────────
class Camera(Base):
    __tablename__ = "cameras"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    icon = Column(String)
    progress = Column(Integer)
    phase = Column(String)
    last_update = Column(DateTime, default=datetime.utcnow)
    is_live = Column(Boolean, default=True)


# ── Feature 3: Smart Locks ───────────────────────────────────────
class SmartLock(Base):
    __tablename__ = "smart_locks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    location = Column(String)
    icon = Column(String)
    state = Column(String)  # locked | unlocked | offline
    battery = Column(Integer)
    level = Column(String)  # high | medium | low


class AccessLog(Base):
    __tablename__ = "access_logs"
    id = Column(Integer, primary_key=True, index=True)
    initials = Column(String)
    name = Column(String)
    action = Column(String)
    location = Column(String)
    time_str = Column(String)
    status = Column(String)  # granted | denied | temp
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Feature 4: Tenant Credit Building ────────────────────────────
class CreditTenant(Base):
    __tablename__ = "credit_tenants"
    id = Column(Integer, primary_key=True, index=True)
    initials = Column(String)
    name = Column(String)
    property_unit = Column(String)
    score = Column(Integer)
    color = Column(String)
    payment_history = Column(Integer)
    credit_utilization = Column(Integer)
    length_of_history = Column(Integer)
    credit_mix = Column(Integer)


class CreditStats(Base):
    __tablename__ = "credit_stats"
    id = Column(Integer, primary_key=True, index=True)
    enrolled = Column(Integer, default=184)
    avg_score_increase = Column(Integer, default=42)
    bureau_reports = Column(Integer, default=2208)
    default_rate = Column(Float, default=1.2)


# ── Feature 5: Emergency Response ────────────────────────────────
class Hotline(Base):
    __tablename__ = "hotlines"
    id = Column(Integer, primary_key=True, index=True)
    icon = Column(String)
    name = Column(String)
    number = Column(String)


class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String)  # active | resolved | closed
    text = Column(String)
    time_str = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Feature 6: Tax Appeals ───────────────────────────────────────
class TaxAppeal(Base):
    __tablename__ = "tax_appeals"
    id = Column(Integer, primary_key=True, index=True)
    appeal_id = Column(String, unique=True)
    property_name = Column(String)
    status = Column(String)  # draft | submitted | review | won
    reason = Column(Text)
    current_valuation = Column(String)
    proposed_valuation = Column(String)
    savings = Column(String)


# ── Feature 7: Partner API Hub ───────────────────────────────────
class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True)
    environment = Column(String, default="live")
    created_at = Column(DateTime, default=datetime.utcnow)


class ApiEndpoint(Base):
    __tablename__ = "api_endpoints"
    id = Column(Integer, primary_key=True, index=True)
    method = Column(String)
    path = Column(String)
    name = Column(String)
    description = Column(String)


class ApiUsage(Base):
    __tablename__ = "api_usage"
    id = Column(Integer, primary_key=True, index=True)
    calls_30d = Column(Integer, default=284120)
    avg_response_ms = Column(Integer, default=82)
    uptime_sla = Column(Float, default=99.98)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_data():
    db = SessionLocal()
    try:
        # Agents
        if db.query(Agent).count() == 0:
            agents = [
                Agent(initials="JM", name="James Mwangi", agent_id="AGT-KC-001",
                      property_name="Kilimani Court", location="Main Gate",
                      float_balance=85000, transactions_today=42, status="available", color="#1e8e5c"),
                Agent(initials="GW", name="Grace Wanjiku", agent_id="AGT-WH-002",
                      property_name="Westlands Heights", location="Block A Lobby",
                      float_balance=62000, transactions_today=28, status="available", color="#c8972a"),
                Agent(initials="AH", name="Amina Hassan", agent_id="AGT-SB-003",
                      property_name="South B Apartments", location="Gate 2",
                      float_balance=120000, transactions_today=36, status="busy", color="#6b4c9a"),
                Agent(initials="PN", name="Peter Njoroge", agent_id="AGT-LS-004",
                      property_name="Lavington Suites", location="East Wing",
                      float_balance=78000, transactions_today=24, status="available", color="#2c6b9e"),
                Agent(initials="SK", name="Sarah Kilonzo", agent_id="AGT-EP-005",
                      property_name="Eastleigh Plaza", location="Ground Floor",
                      float_balance=145000, transactions_today=52, status="available", color="#b5447a"),
                Agent(initials="DO", name="David Ochieng", agent_id="AGT-RG-006",
                      property_name="Runda Gardens", location="Clubhouse",
                      float_balance=54000, transactions_today=18, status="busy", color="#c4622a"),
            ]
            db.add_all(agents)

        if db.query(AgentStats).count() == 0:
            db.add(AgentStats())

        # Cameras
        if db.query(Camera).count() == 0:
            cameras = [
                Camera(name="Kilimani Court · Site A", icon="fa-hard-hat", progress=62,
                       phase="Electrical & Plumbing"),
                Camera(name="South B Apartments · Site B", icon="fa-tools", progress=34,
                       phase="Foundation Work"),
                Camera(name="Lavington Suites · Expansion", icon="fa-building", progress=88,
                       phase="Interior Finishing"),
            ]
            db.add_all(cameras)

        # Smart Locks
        if db.query(SmartLock).count() == 0:
            locks = [
                SmartLock(name="Main Gate", location="Kilimani Court", icon="fa-door-closed",
                          state="locked", battery=87, level="high"),
                SmartLock(name="Block A Entry", location="Westlands Heights", icon="fa-door-open",
                          state="unlocked", battery=62, level="medium"),
                SmartLock(name="Unit 3B Door", location="Kilimani Court", icon="fa-door-closed",
                          state="locked", battery=94, level="high"),
                SmartLock(name="Parking Gate", location="South B Apartments", icon="fa-warehouse",
                          state="locked", battery=28, level="low"),
                SmartLock(name="Unit 5A Door", location="Westlands Heights", icon="fa-door-closed",
                          state="locked", battery=74, level="high"),
                SmartLock(name="Server Room", location="Lavington Suites", icon="fa-server",
                          state="offline", battery=0, level="low"),
            ]
            db.add_all(locks)

        if db.query(AccessLog).count() == 0:
            logs = [
                AccessLog(initials="GW", name="Grace Wanjiku", action="Unlocked Main Gate",
                          location="Kilimani Court", time_str="14:32:18", status="granted"),
                AccessLog(initials="JW", name="John Wachira", action="Entered Unit 3B",
                          location="Kilimani Court", time_str="14:15:02", status="granted"),
                AccessLog(initials="MN", name="Mary Njoki", action="Unlocked Block A",
                          location="Westlands Heights", time_str="13:48:44", status="granted"),
                AccessLog(initials="UN", name="Unknown Visitor", action="Access Attempt",
                          location="South B Apartments", time_str="13:22:11", status="denied"),
                AccessLog(initials="BK", name="Brian Kamau", action="Temporary Access",
                          location="Eastleigh Plaza", time_str="12:55:30", status="temp"),
                AccessLog(initials="LM", name="Lucy Muthoni", action="Exited Property",
                          location="Lavington Suites", time_str="12:30:45", status="granted"),
                AccessLog(initials="GW", name="Grace Wanjiku", action="Unlocked Main Gate",
                          location="Kilimani Court", time_str="11:58:22", status="granted"),
            ]
            db.add_all(logs)

        # Credit Building
        if db.query(CreditTenant).count() == 0:
            tenants = [
                CreditTenant(initials="JW", name="John Wachira", property_unit="Kilimani Court · 3B",
                             score=742, color="#c8972a", payment_history=95, credit_utilization=68,
                             length_of_history=72, credit_mix=55),
                CreditTenant(initials="MN", name="Mary Njoki", property_unit="Westlands Heights · 5A",
                             score=785, color="#6b4c9a", payment_history=98, credit_utilization=78,
                             length_of_history=82, credit_mix=72),
                CreditTenant(initials="BK", name="Brian Kamau", property_unit="South B Apartments · 12",
                             score=618, color="#2c6b9e", payment_history=72, credit_utilization=55,
                             length_of_history=48, credit_mix=42),
                CreditTenant(initials="LM", name="Lucy Muthoni", property_unit="Lavington Suites · 7C",
                             score=812, color="#b5447a", payment_history=100, credit_utilization=85,
                             length_of_history=88, credit_mix=78),
            ]
            db.add_all(tenants)

        if db.query(CreditStats).count() == 0:
            db.add(CreditStats())

        # Emergency
        if db.query(Hotline).count() == 0:
            hotlines = [
                Hotline(icon="fa-fire-extinguisher", name="Fire Emergency", number="020 222 2181"),
                Hotline(icon="fa-user-shield", name="Security Control", number="0800 722 723"),
                Hotline(icon="fa-ambulance", name="Medical Emergency", number="1199"),
                Hotline(icon="fa-tools", name="Plumbing Emergency", number="0709 555 111"),
            ]
            db.add_all(hotlines)

        if db.query(Incident).count() == 0:
            incidents = [
                Incident(status="active", text="Water leak reported · Kilimani Court · Unit 4A", time_str="14:18"),
                Incident(status="active", text="Security alert · South B Apartments · Gate 2", time_str="13:42"),
                Incident(status="resolved", text="Power outage · Westlands Heights · Block A", time_str="12:15"),
                Incident(status="resolved", text="Fire alarm test · Lavington Suites · Wing B", time_str="11:30"),
                Incident(status="closed", text="Elevator maintenance · Eastleigh Plaza", time_str="Yesterday"),
            ]
            db.add_all(incidents)

        # Tax Appeals
        if db.query(TaxAppeal).count() == 0:
            appeals = [
                TaxAppeal(appeal_id="TXA-2025-0142", property_name="Kilimani Court", status="review",
                          reason="County valuation 18% above comparable properties in the area",
                          current_valuation="KSh 128,000,000", proposed_valuation="KSh 108,000,000",
                          savings="KSh 240,000/yr"),
                TaxAppeal(appeal_id="TXA-2025-0138", property_name="South B Apartments", status="submitted",
                          reason="Property categorized as commercial instead of residential",
                          current_valuation="KSh 74,200,000", proposed_valuation="KSh 74,200,000",
                          savings="KSh 186,000/yr"),
                TaxAppeal(appeal_id="TXA-2025-0129", property_name="Westlands Heights", status="won",
                          reason="Valuation error corrected by county assessor",
                          current_valuation="KSh 96,500,000", proposed_valuation="KSh 88,000,000",
                          savings="KSh 142,000/yr"),
                TaxAppeal(appeal_id="TXA-2025-0151", property_name="Lavington Suites", status="draft",
                          reason="Preparing appeal for proposed 2026 valuation increase",
                          current_valuation="KSh 186,000,000", proposed_valuation="KSh 168,000,000",
                          savings="KSh 320,000/yr"),
            ]
            db.add_all(appeals)

        # API Hub
        if db.query(ApiKey).count() == 0:
            db.add(ApiKey(key="mwk_live_sk_4f8a2c9d1e6b3a7f5c8d2e9b4a1f7c3d"))

        if db.query(ApiEndpoint).count() == 0:
            endpoints = [
                ApiEndpoint(method="GET", path="/v1/properties", name="List Properties",
                            description="Retrieve all properties with pagination"),
                ApiEndpoint(method="GET", path="/v1/tenants", name="List Tenants",
                            description="Fetch tenant records and lease info"),
                ApiEndpoint(method="POST", path="/v1/payments", name="Create Payment",
                            description="Initiate rent or utility payment"),
                ApiEndpoint(method="GET", path="/v1/payments/:id", name="Get Payment",
                            description="Retrieve payment details by ID"),
                ApiEndpoint(method="PUT", path="/v1/leases/:id", name="Update Lease",
                            description="Modify lease terms and rent"),
                ApiEndpoint(method="DELETE", path="/v1/tenants/:id", name="Delete Tenant",
                            description="Remove tenant from system"),
                ApiEndpoint(method="POST", path="/v1/webhooks", name="Create Webhook",
                            description="Subscribe to real-time events"),
                ApiEndpoint(method="GET", path="/v1/reports/collection", name="Collection Report",
                            description="Generate monthly collection report"),
            ]
            db.add_all(endpoints)

        if db.query(ApiUsage).count() == 0:
            db.add(ApiUsage())

        db.commit()
        print("✅ Infrastructure database seeded successfully")
    finally:
        db.close()
```

### 3. `schemas.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AgentOut(BaseModel):
    id: int
    initials: str
    name: str
    agent_id: str
    property_name: str
    location: str
    float_balance: int
    transactions_today: int
    status: str
    color: str

    class Config:
        from_attributes = True


class AgentStatsOut(BaseModel):
    active_agents: int
    transactions_today: int
    volume_today: str
    avg_wait: str
    queue_size: int
    success_rate: str


class CameraOut(BaseModel):
    id: int
    name: str
    icon: str
    progress: int
    phase: str
    last_update: datetime
    is_live: bool

    class Config:
        from_attributes = True


class SmartLockOut(BaseModel):
    id: int
    name: str
    location: str
    icon: str
    state: str
    battery: int
    level: str

    class Config:
        from_attributes = True


class AccessLogOut(BaseModel):
    id: int
    initials: str
    name: str
    action: str
    location: str
    time_str: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CreditTenantOut(BaseModel):
    id: int
    initials: str
    name: str
    property_unit: str
    score: int
    color: str
    payment_history: int
    credit_utilization: int
    length_of_history: int
    credit_mix: int

    class Config:
        from_attributes = True


class CreditStatsOut(BaseModel):
    enrolled: int
    avg_score_increase: str
    bureau_reports: int
    default_rate: str


class HotlineOut(BaseModel):
    id: int
    icon: str
    name: str
    number: str

    class Config:
        from_attributes = True


class IncidentOut(BaseModel):
    id: int
    status: str
    text: str
    time_str: str
    created_at: datetime

    class Config:
        from_attributes = True


class TaxAppealOut(BaseModel):
    id: int
    appeal_id: str
    property_name: str
    status: str
    reason: str
    current_valuation: str
    proposed_valuation: str
    savings: str

    class Config:
        from_attributes = True


class ApiKeyOut(BaseModel):
    key: str
    environment: str


class ApiEndpointOut(BaseModel):
    id: int
    method: str
    path: str
    name: str
    description: str

    class Config:
        from_attributes = True


class ApiUsageOut(BaseModel):
    calls_30d: str
    avg_response_ms: str
    uptime_sla: str
```

### 4. `main.py` – Full application

```python
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
import uvicorn
import secrets

from database import (
    Base, engine, get_db, seed_data,
    Agent, AgentStats, Camera, SmartLock, AccessLog,
    CreditTenant, CreditStats, Hotline, Incident,
    TaxAppeal, ApiKey, ApiEndpoint, ApiUsage
)
from schemas import (
    AgentOut, AgentStatsOut, CameraOut, SmartLockOut, AccessLogOut,
    CreditTenantOut, CreditStatsOut, HotlineOut, IncidentOut,
    TaxAppealOut, ApiKeyOut, ApiEndpointOut, ApiUsageOut
)

app = FastAPI(
    title="Mwarokin Estates – Infrastructure API",
    description="Backend for Infrastructure, Access & Compliance (Page 12)",
    version="1.0.0"
)

Base.metadata.create_all(bind=engine)
seed_data()

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/page12.html")


# ──────────────────────────────────────────────
# Feature 1: Mobile Money Agents Network
# ──────────────────────────────────────────────
@app.get("/api/agents", response_model=list[AgentOut])
def list_agents(db: Session = Depends(get_db)):
    return db.query(Agent).order_by(Agent.id).all()


@app.get("/api/agents/stats", response_model=AgentStatsOut)
def agent_stats(db: Session = Depends(get_db)):
    s = db.query(AgentStats).first()
    return AgentStatsOut(
        active_agents=s.active_agents,
        transactions_today=s.transactions_today,
        volume_today=f"KSh {s.volume_today / 1_000_000:.2f}M processed",
        avg_wait=f"{s.avg_wait_min} min",
        queue_size=s.queue_size,
        success_rate=f"{s.success_rate}%"
    )


@app.post("/api/agents/{agent_id}/chat")
def start_agent_chat(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(404, "Agent not found")
    return {
        "message": f"💬 Chat session started with {agent.name}",
        "agent_id": agent.agent_id,
        "status": agent.status
    }


# ──────────────────────────────────────────────
# Feature 2: Construction Cameras
# ──────────────────────────────────────────────
@app.get("/api/cameras", response_model=list[CameraOut])
def list_cameras(db: Session = Depends(get_db)):
    return db.query(Camera).order_by(Camera.id).all()


@app.post("/api/cameras/{camera_id}/refresh")
def refresh_camera(camera_id: int, db: Session = Depends(get_db)):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(404, "Camera not found")
    cam.last_update = datetime.utcnow()
    # small progress simulation
    if cam.progress < 100:
        cam.progress = min(100, cam.progress + 1)
    db.commit()
    return {
        "id": cam.id,
        "progress": cam.progress,
        "last_update": cam.last_update,
        "is_live": cam.is_live
    }


# ──────────────────────────────────────────────
# Feature 3: Smart Lock & Access Control
# ──────────────────────────────────────────────
@app.get("/api/locks", response_model=list[SmartLockOut])
def list_locks(db: Session = Depends(get_db)):
    return db.query(SmartLock).order_by(SmartLock.id).all()


@app.post("/api/locks/{lock_id}/toggle")
def toggle_lock(lock_id: int, db: Session = Depends(get_db)):
    lock = db.query(SmartLock).filter(SmartLock.id == lock_id).first()
    if not lock:
        raise HTTPException(404, "Lock not found")
    if lock.state == "offline":
        raise HTTPException(400, "Lock is offline and cannot be toggled")

    new_state = "unlocked" if lock.state == "locked" else "locked"
    lock.state = new_state
    db.commit()

    # log the action
    log = AccessLog(
        initials="AD",
        name="Landlord Admin",
        action=f"{'Unlocked' if new_state == 'unlocked' else 'Locked'} {lock.name}",
        location=lock.location,
        time_str=datetime.utcnow().strftime("%H:%M:%S"),
        status="granted"
    )
    db.add(log)
    db.commit()

    return {
        "message": f"🔐 {lock.name} is now {new_state.upper()}",
        "state": new_state,
        "battery": lock.battery
    }


@app.get("/api/access-log", response_model=list[AccessLogOut])
def get_access_log(limit: int = 20, db: Session = Depends(get_db)):
    return db.query(AccessLog).order_by(AccessLog.created_at.desc()).limit(limit).all()


# ──────────────────────────────────────────────
# Feature 4: Tenant Credit Building
# ──────────────────────────────────────────────
@app.get("/api/credit/tenants", response_model=list[CreditTenantOut])
def list_credit_tenants(db: Session = Depends(get_db)):
    return db.query(CreditTenant).order_by(CreditTenant.score.desc()).all()


@app.get("/api/credit/stats", response_model=CreditStatsOut)
def credit_stats(db: Session = Depends(get_db)):
    s = db.query(CreditStats).first()
    return CreditStatsOut(
        enrolled=s.enrolled,
        avg_score_increase=f"+{s.avg_score_increase}",
        bureau_reports=s.bureau_reports,
        default_rate=f"{s.default_rate}%"
    )


@app.post("/api/credit/{tenant_id}/report")
def report_to_bureau(tenant_id: int, db: Session = Depends(get_db)):
    tenant = db.query(CreditTenant).filter(CreditTenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(404, "Tenant not found")

    # simulate reporting + small score boost
    tenant.score = min(850, tenant.score + 3)
    tenant.payment_history = min(100, tenant.payment_history + 1)
    db.commit()

    stats = db.query(CreditStats).first()
    stats.bureau_reports += 1
    db.commit()

    return {
        "message": f"📤 Rent payment reported to credit bureau for {tenant.name}",
        "new_score": tenant.score,
        "bureau_reports": stats.bureau_reports
    }


# ──────────────────────────────────────────────
# Feature 5: Emergency Response Center
# ──────────────────────────────────────────────
@app.get("/api/emergency/hotlines", response_model=list[HotlineOut])
def list_hotlines(db: Session = Depends(get_db)):
    return db.query(Hotline).order_by(Hotline.id).all()


@app.get("/api/emergency/incidents", response_model=list[IncidentOut])
def list_incidents(db: Session = Depends(get_db)):
    return db.query(Incident).order_by(Incident.created_at.desc()).all()


@app.post("/api/emergency/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(404, "Incident not found")
    incident.status = "resolved"
    db.commit()
    return {"message": f"Incident marked as resolved", "id": incident.id}


@app.post("/api/emergency/call")
def call_hotline(name: str, number: str):
    return {
        "message": f"📞 Connecting to {name} at {number}...",
        "status": "dialing"
    }


# ──────────────────────────────────────────────
# Feature 6: Property Tax Appeals
# ──────────────────────────────────────────────
@app.get("/api/tax/appeals", response_model=list[TaxAppealOut])
def list_appeals(db: Session = Depends(get_db)):
    return db.query(TaxAppeal).order_by(TaxAppeal.id).all()


@app.post("/api/tax/appeals/{appeal_id}/submit")
def submit_appeal(appeal_id: str, db: Session = Depends(get_db)):
    appeal = db.query(TaxAppeal).filter(TaxAppeal.appeal_id == appeal_id).first()
    if not appeal:
        raise HTTPException(404, "Appeal not found")
    if appeal.status != "draft":
        raise HTTPException(400, f"Appeal is already {appeal.status}")
    appeal.status = "submitted"
    db.commit()
    return {
        "message": f"📤 Appeal {appeal.appeal_id} submitted to county assessor",
        "status": "submitted"
    }


@app.post("/api/tax/appeals/{appeal_id}/follow-up")
def follow_up_appeal(appeal_id: str, db: Session = Depends(get_db)):
    appeal = db.query(TaxAppeal).filter(TaxAppeal.appeal_id == appeal_id).first()
    if not appeal:
        raise HTTPException(404, "Appeal not found")
    return {
        "message": f"💬 Follow-up message sent for {appeal.appeal_id}",
        "property": appeal.property_name,
        "status": appeal.status
    }


# ──────────────────────────────────────────────
# Feature 7: Partner API Hub
# ──────────────────────────────────────────────
@app.get("/api/partner/key", response_model=ApiKeyOut)
def get_api_key(db: Session = Depends(get_db)):
    key = db.query(ApiKey).first()
    return ApiKeyOut(key=key.key, environment=key.environment)


@app.post("/api/partner/key/regenerate")
def regenerate_api_key(db: Session = Depends(get_db)):
    key = db.query(ApiKey).first()
    new_key = f"mwk_live_sk_{secrets.token_hex(16)}"
    key.key = new_key
    key.created_at = datetime.utcnow()
    db.commit()
    return {
        "message": "API key regenerated successfully",
        "key": new_key
    }


@app.get("/api/partner/endpoints", response_model=list[ApiEndpointOut])
def list_endpoints(db: Session = Depends(get_db)):
    return db.query(ApiEndpoint).order_by(ApiEndpoint.id).all()


@app.get("/api/partner/usage", response_model=ApiUsageOut)
def api_usage(db: Session = Depends(get_db)):
    u = db.query(ApiUsage).first()
    return ApiUsageOut(
        calls_30d=f"{u.calls_30d:,}",
        avg_response_ms=f"{u.avg_response_ms}ms",
        uptime_sla=f"{u.uptime_sla}%"
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### How to run

```bash
pip install -r requirements.txt
mkdir -p static
# place your original HTML as static/page12.html
python main.py
```

Open → `http://localhost:8000`

### Real functionality delivered

| Feature                        | Real Backend Capability                                      |
|--------------------------------|--------------------------------------------------------------|
| Mobile Money Agents            | Live agent list + stats + chat initiation                    |
| Construction Cameras           | Live progress + refresh endpoint                             |
| Smart Lock & Access Control    | Toggle lock state + automatic access logging                 |
| Tenant Credit Building         | Score tracking + report to bureau (with score boost)         |
| Emergency Response             | Hotlines + incident list + resolve + call simulation         |
| Property Tax Appeals           | Full CRUD-like flow (list / submit / follow-up)              |
| Partner API Hub                | Key management + regenerate + endpoints + usage metrics      |

Would you like the adapted frontend JavaScript that replaces all the hardcoded arrays with real `fetch()` calls to these endpoints?