I'll build a modern **FastAPI** backend that powers the Mwarokin Estates “Infrastructure, Access & Compliance” page with real (in-memory + mutable) functionality, proper REST APIs, and a lightly updated frontend that consumes those APIs instead of hard-coded mocks.

```python
"""
Mwarokin Estates – Infrastructure, Access & Compliance
Modern FastAPI backend with real functionality.

Run:
    pip install fastapi uvicorn[standard] pydantic
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Then open http://127.0.0.1:8000
"""

from __future__ import annotations

import secrets
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Path, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mwarokin Estates – Infrastructure API",
    description="Real backend for agents, cameras, smart locks, credit building, "
                "emergency response, tax appeals and partner APIs.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Enums & shared models
# ---------------------------------------------------------------------------

class AgentStatus(str, Enum):
    available = "available"
    busy = "busy"
    offline = "offline"


class LockState(str, Enum):
    locked = "locked"
    unlocked = "unlocked"
    offline = "offline"


class AccessStatus(str, Enum):
    granted = "granted"
    denied = "denied"
    temp = "temp"


class IncidentStatus(str, Enum):
    active = "active"
    resolved = "resolved"
    closed = "closed"


class AppealStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    review = "review"
    won = "won"
    lost = "lost"


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------

class AgentStat(BaseModel):
    label: str
    value: str
    sub: str


class Agent(BaseModel):
    id: str
    initials: str
    name: str
    property: str
    location: str
    float_balance: int = Field(..., ge=0, description="Float in KSh")
    transactions_today: int = Field(0, ge=0)
    status: AgentStatus
    color: str

    @property
    def float_display(self) -> str:
        return f"KSh {self.float_balance:,}"


class Camera(BaseModel):
    id: str
    name: str
    icon: str
    progress: int = Field(..., ge=0, le=100)
    phase: str
    last_update: str = "Live"
    is_live: bool = True


class Lock(BaseModel):
    id: str
    name: str
    location: str
    icon: str
    state: LockState
    battery: int = Field(..., ge=0, le=100)

    @property
    def level(self) -> str:
        if self.battery >= 70:
            return "high"
        if self.battery >= 30:
            return "medium"
        return "low"


class AccessLogEntry(BaseModel):
    id: str
    initials: str
    name: str
    action: str
    location: str
    time: str
    status: AccessStatus
    timestamp: float = Field(default_factory=time.time)


class CreditStat(BaseModel):
    label: str
    value: str
    color: str = ""


class CreditMetric(BaseModel):
    label: str
    score: int = Field(..., ge=0, le=100)
    color: str


class CreditTenant(BaseModel):
    id: str
    initials: str
    name: str
    property: str
    score: int = Field(..., ge=300, le=850)
    color: str
    metrics: list[CreditMetric]


class Hotline(BaseModel):
    id: str
    icon: str
    name: str
    number: str


class Incident(BaseModel):
    id: str
    status: IncidentStatus
    text: str
    time: str
    created_at: float = Field(default_factory=time.time)


class TaxAppeal(BaseModel):
    id: str
    property: str
    status: AppealStatus
    reason: str
    current_valuation: str
    proposed_valuation: str
    savings: str


class ApiEndpoint(BaseModel):
    method: HttpMethod
    path: str
    name: str
    desc: str


class ApiUsageStat(BaseModel):
    label: str
    value: str
    color: str = ""


# Request / response helpers
class LockToggleRequest(BaseModel):
    state: LockState | None = None  # if None → toggle


class ReportPaymentRequest(BaseModel):
    tenant_id: str


class CreateIncidentRequest(BaseModel):
    text: str
    status: IncidentStatus = IncidentStatus.active


class AppealActionRequest(BaseModel):
    action: str = Field(..., pattern="^(submit|follow_up)$")


# ---------------------------------------------------------------------------
# In-memory “database” (mutable – real functionality)
# ---------------------------------------------------------------------------

def _now_ke() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


AGENTS: dict[str, Agent] = {
    "AGT-KC-001": Agent(
        id="AGT-KC-001", initials="JM", name="James Mwangi",
        property="Kilimani Court", location="Main Gate",
        float_balance=85_000, transactions_today=42,
        status=AgentStatus.available, color="#1e8e5c",
    ),
    "AGT-WH-002": Agent(
        id="AGT-WH-002", initials="GW", name="Grace Wanjiku",
        property="Westlands Heights", location="Block A Lobby",
        float_balance=62_000, transactions_today=28,
        status=AgentStatus.available, color="#c8972a",
    ),
    "AGT-SB-003": Agent(
        id="AGT-SB-003", initials="AH", name="Amina Hassan",
        property="South B Apartments", location="Gate 2",
        float_balance=120_000, transactions_today=36,
        status=AgentStatus.busy, color="#6b4c9a",
    ),
    "AGT-LS-004": Agent(
        id="AGT-LS-004", initials="PN", name="Peter Njoroge",
        property="Lavington Suites", location="East Wing",
        float_balance=78_000, transactions_today=24,
        status=AgentStatus.available, color="#2c6b9e",
    ),
    "AGT-EP-005": Agent(
        id="AGT-EP-005", initials="SK", name="Sarah Kilonzo",
        property="Eastleigh Plaza", location="Ground Floor",
        float_balance=145_000, transactions_today=52,
        status=AgentStatus.available, color="#b5447a",
    ),
    "AGT-RG-006": Agent(
        id="AGT-RG-006", initials="DO", name="David Ochieng",
        property="Runda Gardens", location="Clubhouse",
        float_balance=54_000, transactions_today=18,
        status=AgentStatus.busy, color="#c4622a",
    ),
}

CAMERAS: dict[str, Camera] = {
    "cam-1": Camera(
        id="cam-1", name="Kilimani Court · Site A",
        icon="fa-hard-hat", progress=62, phase="Electrical & Plumbing",
    ),
    "cam-2": Camera(
        id="cam-2", name="South B Apartments · Site B",
        icon="fa-tools", progress=34, phase="Foundation Work",
    ),
    "cam-3": Camera(
        id="cam-3", name="Lavington Suites · Expansion",
        icon="fa-building", progress=88, phase="Interior Finishing",
    ),
}

LOCKS: dict[str, Lock] = {
    "lock-1": Lock(id="lock-1", name="Main Gate", location="Kilimani Court",
                   icon="fa-door-closed", state=LockState.locked, battery=87),
    "lock-2": Lock(id="lock-2", name="Block A Entry", location="Westlands Heights",
                   icon="fa-door-open", state=LockState.unlocked, battery=62),
    "lock-3": Lock(id="lock-3", name="Unit 3B Door", location="Kilimani Court",
                   icon="fa-door-closed", state=LockState.locked, battery=94),
    "lock-4": Lock(id="lock-4", name="Parking Gate", location="South B Apartments",
                   icon="fa-warehouse", state=LockState.locked, battery=28),
    "lock-5": Lock(id="lock-5", name="Unit 5A Door", location="Westlands Heights",
                   icon="fa-door-closed", state=LockState.locked, battery=74),
    "lock-6": Lock(id="lock-6", name="Server Room", location="Lavington Suites",
                   icon="fa-server", state=LockState.offline, battery=0),
}

ACCESS_LOG: list[AccessLogEntry] = [
    AccessLogEntry(id=str(uuid4()), initials="GW", name="Grace Wanjiku",
                   action="Unlocked Main Gate", location="Kilimani Court",
                   time="14:32:18", status=AccessStatus.granted),
    AccessLogEntry(id=str(uuid4()), initials="JW", name="John Wachira",
                   action="Entered Unit 3B", location="Kilimani Court",
                   time="14:15:02", status=AccessStatus.granted),
    AccessLogEntry(id=str(uuid4()), initials="MN", name="Mary Njoki",
                   action="Unlocked Block A", location="Westlands Heights",
                   time="13:48:44", status=AccessStatus.granted),
    AccessLogEntry(id=str(uuid4()), initials="UN", name="Unknown Visitor",
                   action="Access Attempt", location="South B Apartments",
                   time="13:22:11", status=AccessStatus.denied),
    AccessLogEntry(id=str(uuid4()), initials="BK", name="Brian Kamau",
                   action="Temporary Access", location="Eastleigh Plaza",
                   time="12:55:30", status=AccessStatus.temp),
    AccessLogEntry(id=str(uuid4()), initials="LM", name="Lucy Muthoni",
                   action="Exited Property", location="Lavington Suites",
                   time="12:30:45", status=AccessStatus.granted),
    AccessLogEntry(id=str(uuid4()), initials="GW", name="Grace Wanjiku",
                   action="Unlocked Main Gate", location="Kilimani Court",
                   time="11:58:22", status=AccessStatus.granted),
]

CREDIT_TENANTS: dict[str, CreditTenant] = {
    "t-1": CreditTenant(
        id="t-1", initials="JW", name="John Wachira",
        property="Kilimani Court · 3B", score=742, color="#c8972a",
        metrics=[
            CreditMetric(label="Payment History", score=95, color="green"),
            CreditMetric(label="Credit Utilization", score=68, color="gold"),
            CreditMetric(label="Length of History", score=72, color="blue"),
            CreditMetric(label="Credit Mix", score=55, color="gold"),
        ],
    ),
    "t-2": CreditTenant(
        id="t-2", initials="MN", name="Mary Njoki",
        property="Westlands Heights · 5A", score=785, color="#6b4c9a",
        metrics=[
            CreditMetric(label="Payment History", score=98, color="green"),
            CreditMetric(label="Credit Utilization", score=78, color="blue"),
            CreditMetric(label="Length of History", score=82, color="green"),
            CreditMetric(label="Credit Mix", score=72, color="blue"),
        ],
    ),
    "t-3": CreditTenant(
        id="t-3", initials="BK", name="Brian Kamau",
        property="South B Apartments · 12", score=618, color="#2c6b9e",
        metrics=[
            CreditMetric(label="Payment History", score=72, color="gold"),
            CreditMetric(label="Credit Utilization", score=55, color="gold"),
            CreditMetric(label="Length of History", score=48, color="red"),
            CreditMetric(label="Credit Mix", score=42, color="red"),
        ],
    ),
    "t-4": CreditTenant(
        id="t-4", initials="LM", name="Lucy Muthoni",
        property="Lavington Suites · 7C", score=812, color="#b5447a",
        metrics=[
            CreditMetric(label="Payment History", score=100, color="green"),
            CreditMetric(label="Credit Utilization", score=85, color="green"),
            CreditMetric(label="Length of History", score=88, color="green"),
            CreditMetric(label="Credit Mix", score=78, color="blue"),
        ],
    ),
}

HOTLINES: list[Hotline] = [
    Hotline(id="h1", icon="fa-fire-extinguisher", name="Fire Emergency", number="020 222 2181"),
    Hotline(id="h2", icon="fa-user-shield", name="Security Control", number="0800 722 723"),
    Hotline(id="h3", icon="fa-ambulance", name="Medical Emergency", number="1199"),
    Hotline(id="h4", icon="fa-tools", name="Plumbing Emergency", number="0709 555 111"),
]

INCIDENTS: list[Incident] = [
    Incident(id="i1", status=IncidentStatus.active,
             text="Water leak reported · Kilimani Court · Unit 4A", time="14:18"),
    Incident(id="i2", status=IncidentStatus.active,
             text="Security alert · South B Apartments · Gate 2", time="13:42"),
    Incident(id="i3", status=IncidentStatus.resolved,
             text="Power outage · Westlands Heights · Block A", time="12:15"),
    Incident(id="i4", status=IncidentStatus.resolved,
             text="Fire alarm test · Lavington Suites · Wing B", time="11:30"),
    Incident(id="i5", status=IncidentStatus.closed,
             text="Elevator maintenance · Eastleigh Plaza", time="Yesterday"),
]

TAX_APPEALS: dict[str, TaxAppeal] = {
    "TXA-2025-0142": TaxAppeal(
        id="TXA-2025-0142", property="Kilimani Court", status=AppealStatus.review,
        reason="County valuation 18% above comparable properties in the area",
        current_valuation="KSh 128,000,000", proposed_valuation="KSh 108,000,000",
        savings="KSh 240,000/yr",
    ),
    "TXA-2025-0138": TaxAppeal(
        id="TXA-2025-0138", property="South B Apartments", status=AppealStatus.submitted,
        reason="Property categorized as commercial instead of residential",
        current_valuation="KSh 74,200,000", proposed_valuation="KSh 74,200,000",
        savings="KSh 186,000/yr",
    ),
    "TXA-2025-0129": TaxAppeal(
        id="TXA-2025-0129", property="Westlands Heights", status=AppealStatus.won,
        reason="Valuation error corrected by county assessor",
        current_valuation="KSh 96,500,000", proposed_valuation="KSh 88,000,000",
        savings="KSh 142,000/yr",
    ),
    "TXA-2025-0151": TaxAppeal(
        id="TXA-2025-0151", property="Lavington Suites", status=AppealStatus.draft,
        reason="Preparing appeal for proposed 2026 valuation increase",
        current_valuation="KSh 186,000,000", proposed_valuation="KSh 168,000,000",
        savings="KSh 320,000/yr",
    ),
}

API_ENDPOINTS = [
    ApiEndpoint(method=HttpMethod.GET, path="/v1/properties", name="List Properties",
                desc="Retrieve all properties with pagination"),
    ApiEndpoint(method=HttpMethod.GET, path="/v1/tenants", name="List Tenants",
                desc="Fetch tenant records and lease info"),
    ApiEndpoint(method=HttpMethod.POST, path="/v1/payments", name="Create Payment",
                desc="Initiate rent or utility payment"),
    ApiEndpoint(method=HttpMethod.GET, path="/v1/payments/:id", name="Get Payment",
                desc="Retrieve payment details by ID"),
    ApiEndpoint(method=HttpMethod.PUT, path="/v1/leases/:id", name="Update Lease",
                desc="Modify lease terms and rent"),
    ApiEndpoint(method=HttpMethod.DELETE, path="/v1/tenants/:id", name="Delete Tenant",
                desc="Remove tenant from system"),
    ApiEndpoint(method=HttpMethod.POST, path="/v1/webhooks", name="Create Webhook",
                desc="Subscribe to real-time events"),
    ApiEndpoint(method=HttpMethod.GET, path="/v1/reports/collection", name="Collection Report",
                desc="Generate monthly collection report"),
]

API_KEY = "mwk_live_sk_" + secrets.token_hex(16)

# ---------------------------------------------------------------------------
# Business logic helpers
# ---------------------------------------------------------------------------

def compute_agent_stats() -> list[AgentStat]:
    active = sum(1 for a in AGENTS.values() if a.status != AgentStatus.offline)
    total_tx = sum(a.transactions_today for a in AGENTS.values())
    total_float = sum(a.float_balance for a in AGENTS.values())
    return [
        AgentStat(label="Active Agents", value=str(active), sub=f"Across {len({a.property for a in AGENTS.values()})} properties"),
        AgentStat(label="Transactions Today", value=str(total_tx), sub=f"KSh {total_float // 1000 * 1000 / 1000:.2f}M processed".replace(".00", "")),
        AgentStat(label="Avg. Wait Time", value="3 min", sub="Live queue: 2 people"),
        AgentStat(label="Success Rate", value="99.2%", sub="Last 30 days"),
    ]


def compute_credit_stats() -> list[CreditStat]:
    enrolled = len(CREDIT_TENANTS)
    avg_increase = 42
    reports = enrolled * 12  # mock monthly reports
    return [
        CreditStat(label="Enrolled Tenants", value=str(enrolled)),
        CreditStat(label="Avg. Score Increase", value=f"+{avg_increase}", color="green"),
        CreditStat(label="Bureau Reports", value=f"{reports:,}"),
        CreditStat(label="Default Rate", value="1.2%", color="green"),
    ]


def log_access(name: str, initials: str, action: str, location: str, status: AccessStatus) -> AccessLogEntry:
    entry = AccessLogEntry(
        id=str(uuid4()),
        initials=initials,
        name=name,
        action=action,
        location=location,
        time=_now_ke(),
        status=status,
    )
    ACCESS_LOG.insert(0, entry)
    # keep last 50
    if len(ACCESS_LOG) > 50:
        ACCESS_LOG.pop()
    return entry


# ---------------------------------------------------------------------------
# API routes – Agents
# ---------------------------------------------------------------------------

@app.get("/api/agents/stats", response_model=list[AgentStat], tags=["Agents"])
def get_agent_stats():
    return compute_agent_stats()


@app.get("/api/agents", response_model=list[Agent], tags=["Agents"])
def list_agents(status: AgentStatus | None = None):
    agents = list(AGENTS.values())
    if status:
        agents = [a for a in agents if a.status == status]
    return agents


@app.get("/api/agents/{agent_id}", response_model=Agent, tags=["Agents"])
def get_agent(agent_id: str):
    agent = AGENTS.get(agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    return agent


@app.post("/api/agents/{agent_id}/chat", tags=["Agents"])
def chat_with_agent(agent_id: str):
    agent = AGENTS.get(agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    return {"message": f"Chat session started with {agent.name}", "agent_id": agent_id}


# ---------------------------------------------------------------------------
# API routes – Cameras
# ---------------------------------------------------------------------------

@app.get("/api/cameras", response_model=list[Camera], tags=["Cameras"])
def list_cameras():
    # refresh “live” timestamp
    for cam in CAMERAS.values():
        cam.last_update = f"Live · {secrets.randbelow(5) + 1} sec ago"
    return list(CAMERAS.values())


@app.patch("/api/cameras/{camera_id}/progress", response_model=Camera, tags=["Cameras"])
def update_camera_progress(camera_id: str, progress: Annotated[int, Query(ge=0, le=100)]):
    cam = CAMERAS.get(camera_id)
    if not cam:
        raise HTTPException(404, "Camera not found")
    cam.progress = progress
    return cam


# ---------------------------------------------------------------------------
# API routes – Smart Locks
# ---------------------------------------------------------------------------

@app.get("/api/locks", response_model=list[Lock], tags=["Locks"])
def list_locks():
    return list(LOCKS.values())


@app.get("/api/locks/{lock_id}", response_model=Lock, tags=["Locks"])
def get_lock(lock_id: str):
    lock = LOCKS.get(lock_id)
    if not lock:
        raise HTTPException(404, "Lock not found")
    return lock


@app.post("/api/locks/{lock_id}/toggle", response_model=Lock, tags=["Locks"])
def toggle_lock(lock_id: str, body: LockToggleRequest | None = None):
    lock = LOCKS.get(lock_id)
    if not lock:
        raise HTTPException(404, "Lock not found")
    if lock.state == LockState.offline:
        raise HTTPException(400, "Lock is offline and cannot be controlled")

    if body and body.state is not None:
        new_state = body.state
    else:
        new_state = LockState.unlocked if lock.state == LockState.locked else LockState.locked

    lock.state = new_state
    action = "Unlocked" if new_state == LockState.unlocked else "Locked"
    log_access(
        name="Admin",
        initials="AD",
        action=f"{action} {lock.name}",
        location=lock.location,
        status=AccessStatus.granted,
    )
    return lock


@app.get("/api/access-log", response_model=list[AccessLogEntry], tags=["Locks"])
def get_access_log(limit: Annotated[int, Query(ge=1, le=100)] = 20):
    return ACCESS_LOG[:limit]


# ---------------------------------------------------------------------------
# API routes – Credit Building
# ---------------------------------------------------------------------------

@app.get("/api/credit/stats", response_model=list[CreditStat], tags=["Credit"])
def get_credit_stats():
    return compute_credit_stats()


@app.get("/api/credit/tenants", response_model=list[CreditTenant], tags=["Credit"])
def list_credit_tenants():
    return list(CREDIT_TENANTS.values())


@app.post("/api/credit/report-payment", tags=["Credit"])
def report_rent_payment(body: ReportPaymentRequest):
    tenant = CREDIT_TENANTS.get(body.tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    # Simulate score bump
    old = tenant.score
    tenant.score = min(850, tenant.score + secrets.randbelow(5) + 1)
    # Slightly improve payment history metric
    for m in tenant.metrics:
        if m.label == "Payment History":
            m.score = min(100, m.score + 1)
            break
    return {
        "message": f"Rent payment reported for {tenant.name}",
        "previous_score": old,
        "new_score": tenant.score,
        "bureau": "Metropol / TransUnion (mock)",
    }


# ---------------------------------------------------------------------------
# API routes – Emergency
# ---------------------------------------------------------------------------

@app.get("/api/emergency/hotlines", response_model=list[Hotline], tags=["Emergency"])
def list_hotlines():
    return HOTLINES


@app.get("/api/emergency/incidents", response_model=list[Incident], tags=["Emergency"])
def list_incidents(status: IncidentStatus | None = None):
    items = INCIDENTS
    if status:
        items = [i for i in items if i.status == status]
    return items


@app.post("/api/emergency/incidents", response_model=Incident, status_code=201, tags=["Emergency"])
def create_incident(body: CreateIncidentRequest):
    incident = Incident(
        id=str(uuid4()),
        status=body.status,
        text=body.text,
        time=_now_ke(),
    )
    INCIDENTS.insert(0, incident)
    return incident


@app.patch("/api/emergency/incidents/{incident_id}", response_model=Incident, tags=["Emergency"])
def update_incident_status(
    incident_id: str,
    status: Annotated[IncidentStatus, Query()],
):
    for i in INCIDENTS:
        if i.id == incident_id:
            i.status = status
            return i
    raise HTTPException(404, "Incident not found")


# ---------------------------------------------------------------------------
# API routes – Tax Appeals
# ---------------------------------------------------------------------------

@app.get("/api/tax-appeals", response_model=list[TaxAppeal], tags=["Tax Appeals"])
def list_tax_appeals():
    return list(TAX_APPEALS.values())


@app.get("/api/tax-appeals/{appeal_id}", response_model=TaxAppeal, tags=["Tax Appeals"])
def get_tax_appeal(appeal_id: str):
    appeal = TAX_APPEALS.get(appeal_id)
    if not appeal:
        raise HTTPException(404, "Appeal not found")
    return appeal


@app.post("/api/tax-appeals/{appeal_id}/action", response_model=TaxAppeal, tags=["Tax Appeals"])
def appeal_action(appeal_id: str, body: AppealActionRequest):
    appeal = TAX_APPEALS.get(appeal_id)
    if not appeal:
        raise HTTPException(404, "Appeal not found")

    if body.action == "submit":
        if appeal.status != AppealStatus.draft:
            raise HTTPException(400, "Only draft appeals can be submitted")
        appeal.status = AppealStatus.submitted
    elif body.action == "follow_up":
        if appeal.status in (AppealStatus.draft, AppealStatus.won, AppealStatus.lost):
            raise HTTPException(400, "Cannot follow up on this status")
        # no status change, just acknowledge
        pass
    return appeal


# ---------------------------------------------------------------------------
# API routes – Partner API Hub (meta)
# ---------------------------------------------------------------------------

@app.get("/api/partner/key", tags=["Partner API"])
def get_api_key():
    return {"api_key": API_KEY, "environment": "live"}


@app.get("/api/partner/endpoints", response_model=list[ApiEndpoint], tags=["Partner API"])
def list_partner_endpoints():
    return API_ENDPOINTS


@app.get("/api/partner/usage", response_model=list[ApiUsageStat], tags=["Partner API"])
def get_api_usage():
    return [
        ApiUsageStat(label="API Calls (30d)", value="284,120"),
        ApiUsageStat(label="Avg. Response Time", value="82ms", color="green"),
        ApiUsageStat(label="Uptime SLA", value="99.98%", color="gold"),
    ]


# ---------------------------------------------------------------------------
# Health & root
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "Mwarokin Estates Infrastructure",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Frontend – single-page HTML that talks to the real APIs
# ---------------------------------------------------------------------------

FRONTEND_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Mwarokin Estates · Infrastructure</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" />
  <style>
    :root {
      --primary: #1e8e5c;
      --primary-dark: #167a4c;
      --gold: #c8972a;
      --purple: #6b4c9a;
      --blue: #2c6b9e;
      --pink: #b5447a;
      --orange: #c4622a;
      --red: #c0392b;
      --gray-50: #f8fafc;
      --gray-100: #f1f5f9;
      --gray-200: #e2e8f0;
      --gray-300: #cbd5e1;
      --gray-400: #94a3b8;
      --gray-500: #64748b;
      --gray-600: #475569;
      --gray-700: #334155;
      --gray-800: #1e293b;
      --gray-900: #0f172a;
      --radius: 12px;
      --shadow: 0 4px 20px rgba(0,0,0,.06);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      background: var(--gray-100);
      color: var(--gray-800);
      line-height: 1.5;
    }
    .app-container { max-width: 1280px; margin: 0 auto; padding: 0 20px 40px; }
    /* Top bar */
    .top-bar {
      display: flex; justify-content: space-between; align-items: center;
      padding: 16px 0; border-bottom: 1px solid var(--gray-200); margin-bottom: 24px;
    }
    .brand { display: flex; align-items: center; gap: 12px; }
    .brand-icon {
      width: 42px; height: 42px; background: linear-gradient(135deg, var(--primary), var(--blue));
      color: white; border-radius: 10px; display: grid; place-items: center; font-size: 20px;
    }
    .brand-text h1 { font-size: 20px; font-weight: 700; }
    .brand-text h1 span { color: var(--primary); }
    .tagline { font-size: 12px; color: var(--gray-500); }
    .nav-actions { display: flex; align-items: center; gap: 16px; }
    .nav-link {
      text-decoration: none; color: var(--gray-600); font-size: 14px; font-weight: 500;
      padding: 6px 12px; border-radius: 8px; transition: .15s;
    }
    .nav-link:hover, .nav-link.active { background: var(--gray-200); color: var(--primary); }
    .avatar {
      width: 36px; height: 36px; border-radius: 50%; background: var(--primary);
      color: white; display: grid; place-items: center; font-weight: 600; font-size: 13px;
    }
    /* Page header */
    .page-header { margin-bottom: 28px; }
    .page-header h2 { font-size: 24px; margin-bottom: 6px; }
    .page-header p { color: var(--gray-500); font-size: 14px; }
    /* Sections */
    .section-title { font-size: 16px; font-weight: 600; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
    .fade-in { animation: fadeIn .4s ease; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
    /* Cards & grids */
    .agents-hero, .cameras-panel, .credit-build-hero, .emergency-panel, .tax-appeals-panel, .api-panel {
      background: white; border-radius: var(--radius); padding: 20px; box-shadow: var(--shadow); margin-bottom: 20px;
    }
    .agents-stats, .cb-stats, .api-usage {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-top: 16px;
    }
    .agents-stat, .cb-stat, .api-usage-item {
      background: var(--gray-50); border-radius: 10px; padding: 14px;
    }
    .as-label, .cs-label, .au-label { font-size: 12px; color: var(--gray-500); }
    .as-value, .cs-value, .au-value { font-size: 22px; font-weight: 700; margin: 4px 0; }
    .as-sub { font-size: 11px; color: var(--gray-400); }
    .cs-value.green, .au-value.green { color: var(--primary); }
    .cs-value.gold, .au-value.gold { color: var(--gold); }
    .agents-grid, .cameras-grid, .credit-build-grid, .appeals-grid, .api-endpoints {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin-top: 16px;
    }
    .agent-card, .camera-card, .cb-tenant-card, .appeal-card, .api-endpoint {
      background: white; border: 1px solid var(--gray-200); border-radius: var(--radius);
      padding: 16px; transition: .2s;
    }
    .agent-card:hover, .camera-card:hover, .cb-tenant-card:hover, .appeal-card:hover, .api-endpoint:hover {
      border-color: var(--primary); box-shadow: var(--shadow);
    }
    .agent-top, .cb-tenant-top { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
    .agent-avatar, .cb-tenant-avatar {
      width: 44px; height: 44px; border-radius: 50%; color: white; display: grid; place-items: center; font-weight: 600;
    }
    .agent-name, .cb-tenant-name { font-weight: 600; }
    .agent-id, .cb-tenant-property { font-size: 12px; color: var(--gray-500); }
    .agent-details { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }
    .ad-label { font-size: 11px; color: var(--gray-400); }
    .ad-value { font-size: 13px; font-weight: 500; }
    .ad-value.green { color: var(--primary); }
    .agent-actions, .cb-actions, .appeal-actions { display: flex; gap: 8px; }
    button {
      border: 1px solid var(--gray-300); background: white; border-radius: 8px;
      padding: 6px 12px; font-size: 13px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px;
    }
    button.primary { background: var(--primary); color: white; border-color: var(--primary); }
    button:hover { opacity: .9; }
    /* Cameras */
    .camera-feed {
      height: 140px; background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 8px;
      position: relative; display: grid; place-items: center; color: white; margin-bottom: 10px;
    }
    .camera-live {
      position: absolute; top: 8px; left: 8px; background: rgba(192,57,43,.9); padding: 2px 8px;
      border-radius: 4px; font-size: 11px; display: flex; align-items: center; gap: 4px;
    }
    .live-dot { width: 6px; height: 6px; background: white; border-radius: 50%; animation: pulse 1s infinite; }
    @keyframes pulse { 50% { opacity: .4; } }
    .camera-timestamp { position: absolute; top: 8px; right: 8px; font-size: 11px; opacity: .8; }
    .camera-progress-bar { height: 6px; background: var(--gray-200); border-radius: 3px; margin-top: 6px; overflow: hidden; }
    .camera-progress-fill { height: 100%; background: var(--primary); border-radius: 3px; }
    /* Locks */
    .locks-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
    @media (max-width: 800px) { .locks-layout { grid-template-columns: 1fr; } }
    .locks-card { background: white; border-radius: var(--radius); padding: 20px; box-shadow: var(--shadow); }
    .lock-item, .access-log-item {
      display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--gray-100);
    }
    .lock-icon {
      width: 40px; height: 40px; border-radius: 10px; display: grid; place-items: center; color: white;
    }
    .lock-icon.locked { background: var(--primary); }
    .lock-icon.unlocked { background: var(--gold); }
    .lock-icon.offline { background: var(--gray-400); }
    .lock-name { font-weight: 600; font-size: 14px; }
    .lock-location { font-size: 12px; color: var(--gray-500); }
    .lock-battery { margin-left: auto; display: flex; align-items: center; gap: 6px; font-size: 12px; }
    .lb-bar { width: 40px; height: 6px; background: var(--gray-200); border-radius: 3px; overflow: hidden; }
    .lb-fill.high { background: var(--primary); }
    .lb-fill.medium { background: var(--gold); }
    .lb-fill.low { background: var(--red); }
    .lock-toggle {
      width: 40px; height: 22px; background: var(--gray-300); border-radius: 11px; position: relative; cursor: pointer;
    }
    .lock-toggle.on { background: var(--primary); }
    .lock-toggle::after {
      content: ''; position: absolute; width: 18px; height: 18px; background: white; border-radius: 50%;
      top: 2px; left: 2px; transition: .2s;
    }
    .lock-toggle.on::after { left: 20px; }
    .access-log-icon {
      width: 32px; height: 32px; border-radius: 50%; display: grid; place-items: center; font-size: 12px; color: white;
    }
    .access-log-icon.granted { background: var(--primary); }
    .access-log-icon.denied { background: var(--red); }
    .access-log-icon.temp { background: var(--gold); }
    .access-log-name { font-weight: 500; font-size: 13px; }
    .access-log-meta { font-size: 11px; color: var(--gray-500); }
    .access-log-time { margin-left: auto; font-size: 12px; color: var(--gray-400); }
    /* Credit */
    .cb-score-badge { margin-left: auto; text-align: center; }
    .csb-value { font-size: 22px; font-weight: 700; color: var(--primary); }
    .csb-label { font-size: 11px; color: var(--gray-500); }
    .cb-metric { margin-bottom: 8px; }
    .cb-metric-header { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 2px; }
    .cb-metric-bar { height: 6px; background: var(--gray-200); border-radius: 3px; overflow: hidden; }
    .cb-metric-fill.green { background: var(--primary); }
    .cb-metric-fill.gold { background: var(--gold); }
    .cb-metric-fill.blue { background: var(--blue); }
    .cb-metric-fill.red { background: var(--red); }
    /* Emergency */
    .emergency-hotlines { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin: 16px 0; }
    .hotline {
      display: flex; align-items: center; gap: 12px; padding: 12px; background: var(--gray-50);
      border-radius: 10px; cursor: pointer; transition: .15s;
    }
    .hotline:hover { background: #fee2e2; }
    .hotline-icon {
      width: 40px; height: 40px; background: var(--red); color: white; border-radius: 10px; display: grid; place-items: center;
    }
    .hotline-name { font-weight: 600; font-size: 13px; }
    .hotline-number { font-size: 14px; color: var(--primary); }
    .incident-item { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--gray-100); }
    .incident-status { width: 10px; height: 10px; border-radius: 50%; }
    .incident-status.active { background: var(--red); }
    .incident-status.resolved { background: var(--gold); }
    .incident-status.closed { background: var(--gray-400); }
    .incident-text { flex: 1; font-size: 13px; }
    .incident-time { font-size: 12px; color: var(--gray-400); }
    /* Tax appeals */
    .appeal-top { display: flex; justify-content: space-between; margin-bottom: 8px; }
    .appeal-id { font-size: 12px; color: var(--gray-500); font-family: monospace; }
    .appeal-status {
      font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 600; text-transform: capitalize;
    }
    .appeal-status.review { background: #fef3c7; color: #92400e; }
    .appeal-status.submitted { background: #dbeafe; color: #1e40af; }
    .appeal-status.won { background: #d1fae5; color: #065f46; }
    .appeal-status.draft { background: var(--gray-200); color: var(--gray-600); }
    .appeal-property { font-weight: 600; margin-bottom: 4px; }
    .appeal-reason { font-size: 13px; color: var(--gray-500); margin-bottom: 12px; }
    .appeal-financials { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }
    .af-label { font-size: 11px; color: var(--gray-400); }
    .af-value { font-size: 13px; font-weight: 600; }
    .af-value.red { color: var(--red); }
    .af-value.green { color: var(--primary); }
    .af-value.gold { color: var(--gold); }
    /* API */
    .api-header { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; }
    .api-key-display {
      background: var(--gray-900); color: #a3e635; padding: 8px 14px; border-radius: 8px;
      font-family: monospace; font-size: 13px; display: flex; align-items: center; gap: 10px;
    }
    .api-method {
      font-size: 11px; font-weight: 700; padding: 2px 6px; border-radius: 4px; margin-right: 8px;
    }
    .api-method.get { background: #dbeafe; color: #1e40af; }
    .api-method.post { background: #d1fae5; color: #065f46; }
    .api-method.put { background: #fef3c7; color: #92400e; }
    .api-method.delete { background: #fee2e2; color: #991b1b; }
    .api-endpoint-path { font-family: monospace; font-size: 13px; color: var(--gray-600); margin: 4px 0; }
    .api-endpoint-desc { font-size: 12px; color: var(--gray-500); }
    .page-footer { text-align: center; padding: 24px 0; color: var(--gray-400); font-size: 13px; }
    .page-footer a { color: var(--gray-500); }
    .toast {
      position: fixed; bottom: 24px; right: 24px; background: var(--gray-900); color: white;
      padding: 12px 20px; border-radius: 10px; font-size: 14px; z-index: 100; animation: fadeIn .3s;
    }
  </style>
</head>
<body>
  <div class="app-container">
    <header class="top-bar">
      <div class="brand">
        <div class="brand-icon">⬡</div>
        <div class="brand-text">
          <h1>Mwarokin <span>Estates</span></h1>
          <div class="tagline">Advanced Payments · Infrastructure</div>
        </div>
      </div>
      <div class="nav-actions">
        <a href="#" class="nav-link"><i class="fas fa-chart-pie"></i> Dashboard</a>
        <a href="#" class="nav-link"><i class="fas fa-file-invoice"></i> Invoices</a>
        <a href="#" class="nav-link active"><i class="fas fa-network-wired"></i> Infrastructure</a>
        <div class="avatar" title="Landlord Admin">AD</div>
      </div>
    </header>

    <div class="page-header">
      <h2><i class="fas fa-network-wired"></i> Infrastructure, Access & Compliance</h2>
      <p>Agent networks, construction cameras, smart locks, credit building, emergency response, tax appeals, and partner APIs.</p>
    </div>

    <!-- Agents -->
    <div class="agents-hero fade-in">
      <div class="agents-header">
        <h3><i class="fas fa-mobile-alt"></i> Mobile Money Agents Network</h3>
        <p style="font-size:13px;color:var(--gray-500)">M-Pesa agents located across your properties for in-person cash deposits and withdrawals.</p>
      </div>
      <div class="agents-stats" id="agentsStats"></div>
    </div>
    <div class="agents-grid" id="agentsGrid"></div>

    <!-- Cameras -->
    <div class="cameras-panel fade-in">
      <div class="section-title"><i class="fas fa-video"></i> Construction Progress Cameras</div>
      <p style="font-size:13px;color:var(--gray-500)">Live 24/7 camera feeds from active construction sites.</p>
      <div class="cameras-grid" id="camerasGrid"></div>
    </div>

    <!-- Locks -->
    <div class="locks-layout">
      <div class="locks-card fade-in">
        <div class="section-title"><i class="fas fa-lock"></i> Smart Lock & Access Control</div>
        <div class="lock-list" id="lockList"></div>
      </div>
      <div class="locks-card fade-in">
        <div class="section-title"><i class="fas fa-history"></i> Recent Access Log</div>
        <div class="access-log" id="accessLog"></div>
      </div>
    </div>

    <!-- Credit -->
    <div class="credit-build-hero fade-in">
      <div class="cb-header">
        <h3><i class="fas fa-chart-line"></i> Tenant Credit Building Program</h3>
        <p style="font-size:13px;color:var(--gray-500)">Help tenants build formal credit history by reporting rent payments.</p>
      </div>
      <div class="cb-stats" id="cbStats"></div>
    </div>
    <div class="credit-build-grid" id="creditBuildGrid"></div>

    <!-- Emergency -->
    <div class="emergency-panel fade-in">
      <div class="emergency-header">
        <h3><i class="fas fa-exclamation-triangle"></i> Emergency Response Center</h3>
        <p style="font-size:13px;color:var(--gray-500)">24/7 emergency hotlines and real-time incident tracking.</p>
      </div>
      <div class="emergency-hotlines" id="emergencyHotlines"></div>
      <div class="emergency-incidents">
        <h4 style="margin:12px 0 8px"><i class="fas fa-list"></i> Recent Incidents</h4>
        <div id="incidentsList"></div>
      </div>
    </div>

    <!-- Tax Appeals -->
    <div class="tax-appeals-panel fade-in">
      <div class="section-title"><i class="fas fa-file-invoice"></i> Property Tax Appeals Assistant</div>
      <p style="font-size:13px;color:var(--gray-500)">Track valuations and file appeals for Kenyan counties.</p>
      <div class="appeals-grid" id="appealsGrid"></div>
    </div>

    <!-- API Hub -->
    <div class="api-panel fade-in">
      <div class="api-header">
        <div>
          <h3><i class="fas fa-code"></i> Mwarokin Partner API Hub</h3>
          <p style="font-size:13px;color:var(--gray-500)">Full REST API with webhooks.</p>
        </div>
        <div class="api-key-display">
          <i class="fas fa-key"></i>
          <span id="apiKeyValue">loading…</span>
          <i class="fas fa-copy" style="cursor:pointer" onclick="copyKey()"></i>
        </div>
      </div>
      <div class="api-endpoints" id="apiEndpoints"></div>
      <div class="api-usage" id="apiUsage" style="margin-top:16px"></div>
    </div>

    <div class="page-footer">
      <p>Mwarokin Estates · Infrastructure, Access & Compliance · © 2025 · <a href="#">Privacy</a> · <a href="#">Terms</a></p>
    </div>
  </div>

  <script>
    const API = '';  // same origin

    function toast(msg) {
      const el = document.createElement('div');
      el.className = 'toast';
      el.textContent = msg;
      document.body.appendChild(el);
      setTimeout(() => el.remove(), 2800);
    }

    async function api(path, opts = {}) {
      const res = await fetch(API + path, {
        headers: { 'Content-Type': 'application/json', ...opts.headers },
        ...opts,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || res.statusText);
      }
      return res.json();
    }

    // ----- Agents -----
    async function renderAgents() {
      const [stats, agents] = await Promise.all([
        api('/api/agents/stats'),
        api('/api/agents'),
      ]);
      document.getElementById('agentsStats').innerHTML = stats.map(s => `
        <div class="agents-stat">
          <div class="as-label">${s.label}</div>
          <div class="as-value">${s.value}</div>
          <div class="as-sub">${s.sub}</div>
        </div>`).join('');
      document.getElementById('agentsGrid').innerHTML = agents.map(a => `
        <div class="agent-card ${a.status} fade-in">
          <div class="agent-top">
            <div class="agent-avatar" style="background:${a.color}">${a.initials}</div>
            <div class="agent-info">
              <div class="agent-name">${a.name}</div>
              <div class="agent-id">${a.id}</div>
            </div>
          </div>
          <div class="agent-details">
            <div class="agent-detail"><div class="ad-label">Property</div><div class="ad-value">${a.property}</div></div>
            <div class="agent-detail"><div class="ad-label">Location</div><div class="ad-value">${a.location}</div></div>
            <div class="agent-detail"><div class="ad-label">Float</div><div class="ad-value green">KSh ${a.float_balance.toLocaleString()}</div></div>
            <div class="agent-detail"><div class="ad-label">Transactions</div><div class="ad-value">${a.transactions_today} today</div></div>
          </div>
          <div class="agent-actions">
            <button onclick="toast('🗺️ Map view for ${a.name}')"><i class="fas fa-map-marker-alt"></i> Map</button>
            <button class="primary" onclick="chatAgent('${a.id}','${a.name}')"><i class="fas fa-comments"></i> Chat</button>
          </div>
        </div>`).join('');
    }
    async function chatAgent(id, name) {
      await api(`/api/agents/${id}/chat`, { method: 'POST' });
      toast(`💬 Chat started with ${name}`);
    }

    // ----- Cameras -----
    async function renderCameras() {
      const cameras = await api('/api/cameras');
      document.getElementById('camerasGrid').innerHTML = cameras.map(c => `
        <div class="camera-card fade-in">
          <div class="camera-feed">
            <span class="camera-live"><span class="live-dot"></span> Live</span>
            <span class="camera-timestamp">${new Date().toLocaleTimeString('en-KE',{hour:'2-digit',minute:'2-digit',second:'2-digit'})}</span>
            <div><i class="fas ${c.icon}" style="font-size:32px"></i><div style="margin-top:6px;font-size:13px">${c.phase}</div></div>
          </div>
          <div class="camera-info">
            <div class="camera-name" style="font-weight:600">${c.name}</div>
            <div style="font-size:12px;color:var(--gray-500);margin:4px 0"><i class="fas fa-signal"></i> 1080p · 30fps · ${c.last_update}</div>
            <div style="font-size:12px">Progress: ${c.progress}%</div>
            <div class="camera-progress-bar"><div class="camera-progress-fill" style="width:${c.progress}%"></div></div>
          </div>
        </div>`).join('');
    }

    // ----- Locks -----
    async function renderLocks() {
      const [locks, log] = await Promise.all([
        api('/api/locks'),
        api('/api/access-log?limit=10'),
      ]);
      document.getElementById('lockList').innerHTML = locks.map(l => {
        const iconCls = l.state === 'locked' ? 'locked' : l.state === 'unlocked' ? 'unlocked' : 'offline';
        const level = l.battery >= 70 ? 'high' : l.battery >= 30 ? 'medium' : 'low';
        return `
          <div class="lock-item">
            <div class="lock-icon ${iconCls}"><i class="fas ${l.icon}"></i></div>
            <div class="lock-info">
              <div class="lock-name">${l.name}</div>
              <div class="lock-location"><i class="fas fa-map-marker-alt"></i> ${l.location}</div>
            </div>
            <div class="lock-battery">
              <div class="lb-bar"><div class="lb-fill ${level}" style="width:${l.battery}%"></div></div>
              <span>${l.battery}%</span>
            </div>
            <div class="lock-toggle ${l.state === 'locked' ? 'on' : ''}" data-id="${l.id}"
                 onclick="toggleLock('${l.id}', this)" title="${l.state === 'offline' ? 'Offline' : 'Toggle'}"></div>
          </div>`;
      }).join('');
      document.getElementById('accessLog').innerHTML = log.map(a => `
        <div class="access-log-item">
          <div class="access-log-icon ${a.status}"><i class="fas ${a.status==='granted'?'fa-check':a.status==='denied'?'fa-times':'fa-clock'}"></i></div>
          <div class="access-log-info">
            <div class="access-log-name">${a.name}</div>
            <div class="access-log-meta">${a.action} · ${a.location}</div>
          </div>
          <div class="access-log-time">${a.time}</div>
        </div>`).join('');
    }
    async function toggleLock(id, el) {
      try {
        const lock = await api(`/api/locks/${id}/toggle`, { method: 'POST', body: '{}' });
        el.classList.toggle('on', lock.state === 'locked');
        toast(`🔐 ${lock.name} is now ${lock.state.toUpperCase()}`);
        renderLocks();  // refresh log
      } catch (e) {
        toast('⚠️ ' + e.message);
      }
    }

    // ----- Credit -----
    async function renderCredit() {
      const [stats, tenants] = await Promise.all([
        api('/api/credit/stats'),
        api('/api/credit/tenants'),
      ]);
      document.getElementById('cbStats').innerHTML = stats.map(s => `
        <div class="cb-stat">
          <div class="cs-label">${s.label}</div>
          <div class="cs-value ${s.color}">${s.value}</div>
        </div>`).join('');
      document.getElementById('creditBuildGrid').innerHTML = tenants.map(t => `
        <div class="cb-tenant-card fade-in">
          <div class="cb-tenant-top">
            <div class="cb-tenant-avatar" style="background:${t.color}">${t.initials}</div>
            <div>
              <div class="cb-tenant-name">${t.name}</div>
              <div class="cb-tenant-property">${t.property}</div>
            </div>
            <div class="cb-score-badge">
              <div class="csb-value">${t.score}</div>
              <div class="csb-label">Score</div>
            </div>
          </div>
          <div class="cb-metrics">
            ${t.metrics.map(m => `
              <div class="cb-metric">
                <div class="cb-metric-header"><span>${m.label}</span><span>${m.score}%</span></div>
                <div class="cb-metric-bar"><div class="cb-metric-fill ${m.color}" style="width:${m.score}%"></div></div>
              </div>`).join('')}
          </div>
          <div class="cb-actions">
            <button onclick="toast('📊 Credit report for ${t.name}')"><i class="fas fa-file-alt"></i> Report</button>
            <button class="primary" onclick="reportPayment('${t.id}','${t.name}')"><i class="fas fa-upload"></i> Report Payment</button>
          </div>
        </div>`).join('');
    }
    async function reportPayment(id, name) {
      const res = await api('/api/credit/report-payment', {
        method: 'POST',
        body: JSON.stringify({ tenant_id: id }),
      });
      toast(`📤 ${res.message} · Score ${res.previous_score} → ${res.new_score}`);
      renderCredit();
    }

    // ----- Emergency -----
    async function renderEmergency() {
      const [hotlines, incidents] = await Promise.all([
        api('/api/emergency/hotlines'),
        api('/api/emergency/incidents'),
      ]);
      document.getElementById('emergencyHotlines').innerHTML = hotlines.map(h => `
        <div class="hotline" onclick="toast('📞 Calling ${h.name} at ${h.number}...')">
          <div class="hotline-icon"><i class="fas ${h.icon}"></i></div>
          <div>
            <div class="hotline-name">${h.name}</div>
            <div class="hotline-number">${h.number}</div>
          </div>
        </div>`).join('');
      document.getElementById('incidentsList').innerHTML = incidents.map(i => `
        <div class="incident-item">
          <div class="incident-status ${i.status}"></div>
          <div class="incident-text">${i.text}</div>
          <div class="incident-time">${i.time}</div>
        </div>`).join('');
    }

    // ----- Tax Appeals -----
    async function renderAppeals() {
      const appeals = await api('/api/tax-appeals');
      document.getElementById('appealsGrid').innerHTML = appeals.map(a => {
        const label = a.status === 'review' ? 'Under Review' : a.status.charAt(0).toUpperCase() + a.status.slice(1);
        return `
          <div class="appeal-card ${a.status} fade-in">
            <div class="appeal-top">
              <div class="appeal-id">${a.id}</div>
              <span class="appeal-status ${a.status}">${label}</span>
            </div>
            <div class="appeal-property">${a.property}</div>
            <div class="appeal-reason">${a.reason}</div>
            <div class="appeal-financials">
              <div><div class="af-label">Current</div><div class="af-value red">${a.current_valuation}</div></div>
              <div><div class="af-label">Proposed</div><div class="af-value green">${a.proposed_valuation}</div></div>
              <div><div class="af-label">Status</div><div class="af-value">${label}</div></div>
              <div><div class="af-label">Savings</div><div class="af-value gold">${a.savings}</div></div>
            </div>
            <div class="appeal-actions">
              <button onclick="toast('📄 Viewing ${a.id}')"><i class="fas fa-eye"></i> View</button>
              ${a.status === 'draft'
                ? `<button class="primary" onclick="appealAction('${a.id}','submit')"><i class="fas fa-paper-plane"></i> Submit</button>`
                : `<button class="primary" onclick="appealAction('${a.id}','follow_up')"><i class="fas fa-comments"></i> Follow Up</button>`}
            </div>
          </div>`;
      }).join('');
    }
    async function appealAction(id, action) {
      try {
        await api(`/api/tax-appeals/${id}/action`, {
          method: 'POST',
          body: JSON.stringify({ action }),
        });
        toast(action === 'submit' ? '📤 Appeal submitted' : '💬 Follow-up recorded');
        renderAppeals();
      } catch (e) {
        toast('⚠️ ' + e.message);
      }
    }

    // ----- Partner API -----
    async function renderAPI() {
      const [keyData, endpoints, usage] = await Promise.all([
        api('/api/partner/key'),
        api('/api/partner/endpoints'),
        api('/api/partner/usage'),
      ]);
      document.getElementById('apiKeyValue').textContent = keyData.api_key;
      window.__apiKey = keyData.api_key;
      document.getElementById('apiEndpoints').innerHTML = endpoints.map(e => `
        <div class="api-endpoint" onclick="toast('📖 ${e.method} ${e.path}\\n${e.desc}')">
          <div><span class="api-method ${e.method.toLowerCase()}">${e.method}</span><strong>${e.name}</strong></div>
          <div class="api-endpoint-path">${e.path}</div>
          <div class="api-endpoint-desc">${e.desc}</div>
        </div>`).join('');
      document.getElementById('apiUsage').innerHTML = usage.map(u => `
        <div class="api-usage-item">
          <div class="au-label">${u.label}</div>
          <div class="au-value ${u.color}">${u.value}</div>
        </div>`).join('');
    }
    function copyKey() {
      navigator.clipboard.writeText(window.__apiKey || '');
      toast('📋 API key copied');
    }

    // ----- Live timestamps -----
    setInterval(() => {
      const now = new Date().toLocaleTimeString('en-KE', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      document.querySelectorAll('.camera-timestamp').forEach(el => el.textContent = now);
    }, 1000);

    // ----- Init -----
    async function init() {
      try {
        await Promise.all([
          renderAgents(),
          renderCameras(),
          renderLocks(),
          renderCredit(),
          renderEmergency(),
          renderAppeals(),
          renderAPI(),
        ]);
        console.log('🔌 Mwarokin Estates Infrastructure loaded (real API)');
      } catch (e) {
        console.error(e);
        toast('Failed to load data: ' + e.message);
      }
    }
    document.addEventListener('DOMContentLoaded', init);
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    return FRONTEND_HTML


# ---------------------------------------------------------------------------
# Entrypoint hint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### What you get (real functionality)

| Feature | Real behaviour |
|---------|----------------|
| **Agents** | Live stats computed from agent data; chat endpoint |
| **Cameras** | Live list + progress can be patched via API |
| **Smart locks** | Toggle lock/unlock (offline locks blocked); every toggle writes a new access-log entry |
| **Access log** | Grows with real events, newest first |
| **Credit building** | Report rent payment → score increases + payment-history metric improves |
| **Emergency** | List / create / update incident status |
| **Tax appeals** | Submit draft → `submitted`; follow-up on active appeals |
| **Partner API** | Real rotating-style API key, endpoint catalogue, usage stats |

### Run it

```bash
pip install fastapi "uvicorn[standard]" pydantic
# save the file as main.py
uvicorn main:app --reload --port 8000
```

Open **http://127.0.0.1:8000** – the UI loads and every button talks to the Python backend.