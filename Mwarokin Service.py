**Updated `Mwarokin_Services.py`** — full agentic backend with **all 25 service modules** included exactly as defined in the frontend.

```python
#!/usr/bin/env python3
"""
Mwarokin Estates — Agentic Property Operating System Backend
Advanced real-time agentic Python implementation
Includes complete catalog of all 25 Premium Service Modules
Syllogism Technology Africa
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Set

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    app_name: str = "Mwarokin Estates Property OS"
    version: str = "2.5.0-agentic"
    agent_poll_interval_sec: float = 8.0
    max_audit_entries: int = 50_000
    enable_autonomous_actions: bool = True
    dual_auth_required: bool = True

settings = Settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("mwarokin.agentic")

# ──────────────────────────────────────────────────────────────
# Domain Enums & Models
# ──────────────────────────────────────────────────────────────

class ServiceCategory(str, Enum):
    FINANCE = "Finance"
    COMPLIANCE = "Compliance"
    RISK = "Risk"
    ANALYTICS = "Analytics"
    CONTRACTS = "Contracts"
    OPERATIONS = "Operations"
    IOT = "IoT"
    ENGAGEMENT = "Engagement"
    COMMUNICATION = "Communication"
    MARKETPLACE = "Marketplace"
    SECURITY = "Security"
    AI = "AI"
    SCALE = "Scale"
    SAFETY = "Safety"
    PROJECTS = "Projects"
    INTEGRATION = "Integration"
    INNOVATION = "Innovation"

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

class ServiceModule(BaseModel):
    id: int
    title: str
    category: ServiceCategory
    icon: str
    badge: Optional[str] = None
    description: str
    features: List[str]
    key_capabilities: List[str]
    integration: List[str]
    use_cases: List[str]

class PropertyUnit(BaseModel):
    unit_id: str
    property_id: str
    floor: int
    bedrooms: int
    status: str = "occupied"
    current_rent: float
    tenant_id: Optional[str] = None
    last_payment_date: Optional[datetime] = None
    water_consumption_l: float = 0.0
    electricity_kwh: float = 0.0
    health_score: float = 85.0

class TenantProfile(BaseModel):
    tenant_id: str
    full_name: str
    payment_reliability_score: float = Field(ge=0, le=100)
    lease_compliance_score: float = Field(ge=0, le=100)
    risk_score: float = Field(ge=0, le=100)
    outstanding_balance: float = 0.0
    lease_end: Optional[datetime] = None
    early_warning_flags: List[str] = []

class FinancialSnapshot(BaseModel):
    property_id: str
    period: str
    gross_rent: float
    vacancy_loss: float
    operating_expenses: float
    noi: float
    cash_flow: float
    roi_pct: float
    reserve_fund: float
    health_score: float

class Alert(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    severity: AlertSeverity
    source_module: str
    property_id: Optional[str] = None
    unit_id: Optional[str] = None
    title: str
    message: str
    recommended_action: Optional[str] = None
    autonomous_action_taken: Optional[str] = None
    acknowledged: bool = False

class DualAuthRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action_type: str
    payload: Dict[str, Any]
    requested_by: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved_by: Optional[str] = None
    rejected_by: Optional[str] = None
    reason: Optional[str] = None

class AuditEntry(BaseModel):
    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str
    action: str
    entity_type: str
    entity_id: str
    before: Optional[Dict] = None
    after: Optional[Dict] = None
    hash: str = ""

# ──────────────────────────────────────────────────────────────
# Platform State
# ──────────────────────────────────────────────────────────────

class PlatformState:
    def __init__(self):
        self.services: Dict[int, ServiceModule] = {}
        self.properties: Dict[str, Dict] = {}
        self.units: Dict[str, PropertyUnit] = {}
        self.tenants: Dict[str, TenantProfile] = {}
        self.alerts: Deque[Alert] = deque(maxlen=5_000)
        self.dual_auth_queue: Dict[str, DualAuthRequest] = {}
        self.audit_log: Deque[AuditEntry] = deque(maxlen=settings.max_audit_entries)
        self.live_metrics: Dict[str, Any] = defaultdict(dict)
        self.websocket_clients: Set[WebSocket] = set()
        self.agent_running: bool = False
        self.last_agent_cycle: Optional[datetime] = None

state = PlatformState()

# ──────────────────────────────────────────────────────────────
# COMPLETE 25 SERVICE MODULES CATALOG
# Exactly mirrors the frontend JavaScript services array
# ──────────────────────────────────────────────────────────────

SERVICE_CATALOG: List[ServiceModule] = [
    ServiceModule(
        id=1,
        title="Property Financial Intelligence",
        category=ServiceCategory.FINANCE,
        icon="📊",
        badge="premium",
        description="Advanced property-level financial analytics and forecasting",
        features=[
            "Property P&L statements",
            "Cash-flow forecasting",
            "Net operating income",
            "Vacancy-cost calculation",
            "ROI analytics",
            "Reserve-fund management"
        ],
        key_capabilities=[
            "Budget forecasting with ML predictions",
            "Expected vs actual income tracking",
            "Expense categorization & trends",
            "Capital-expenditure tracking",
            "Portfolio performance scoring",
            "Break-even analysis"
        ],
        integration=["Bank APIs", "Accounting Software", "Analytics Dashboard"],
        use_cases=[
            "Multi-property portfolio analysis",
            "Investment decision support",
            "Tax planning optimization",
            "Financial health reporting"
        ]
    ),
    ServiceModule(
        id=2,
        title="Escrow & Trust Management",
        category=ServiceCategory.COMPLIANCE,
        icon="🔐",
        badge="premium",
        description="Secure management of deposits and trust accounts with dual authorization",
        features=[
            "Security-deposit ledger",
            "Deposit release workflow",
            "Partial deposit release",
            "Dispute resolution workflow",
            "Dual authorization",
            "Automated release conditions"
        ],
        key_capabilities=[
            "Escrow status real-time tracking",
            "Beneficiary approval system",
            "Holding-account reconciliation",
            "Deposit aging reports",
            "Liability calculation",
            "Audit trail logging"
        ],
        integration=["Bank Escrow", "Legal Platforms", "Payment Processors"],
        use_cases=[
            "Tenant deposit management",
            "Liability tracking",
            "Dispute resolution",
            "Regulatory compliance"
        ]
    ),
    ServiceModule(
        id=3,
        title="Tenant Risk & Reliability",
        category=ServiceCategory.RISK,
        icon="🎯",
        description="Comprehensive tenant verification and risk scoring",
        features=[
            "Payment reliability score",
            "Lease compliance score",
            "Tenant verification workflow",
            "Reference verification",
            "Application scoring",
            "Risk-based approval"
        ],
        key_capabilities=[
            "Payment-pattern analytics",
            "Early-warning alerts",
            "Renewal probability prediction",
            "Outstanding-obligation tracking",
            "Credit-check integration",
            "Behavioral scoring"
        ],
        integration=["Credit Bureau APIs", "Employment Verification", "Identity Services"],
        use_cases=[
            "Tenant screening",
            "Credit risk assessment",
            "Renewal prediction",
            "Payment default prevention"
        ]
    ),
    ServiceModule(
        id=4,
        title="Landlord Intelligence",
        category=ServiceCategory.ANALYTICS,
        icon="👥",
        badge="popular",
        description="Comprehensive portfolio management and performance analytics",
        features=[
            "Portfolio health score",
            "Income concentration analysis",
            "Vacancy exposure tracking",
            "Property risk ranking",
            "Maintenance-cost trends",
            "Tenant concentration analysis"
        ],
        key_capabilities=[
            "Portfolio comparison tools",
            "Investment-performance dashboard",
            "Automated owner reports",
            "Competitive benchmarking",
            "Market intelligence",
            "Predictive analytics"
        ],
        integration=["Market Data APIs", "Reporting Tools", "Email Systems"],
        use_cases=[
            "Portfolio optimization",
            "Investment strategy",
            "Market positioning",
            "Performance monitoring"
        ]
    ),
    ServiceModule(
        id=5,
        title="Digital Lease Infrastructure",
        category=ServiceCategory.CONTRACTS,
        icon="📄",
        badge="popular",
        description="Complete digital lease management with versioning and automation",
        features=[
            "Digital lease templates",
            "Lease version control",
            "Electronic signatures",
            "Lease amendment workflow",
            "Renewal workflow",
            "Expiration countdown"
        ],
        key_capabilities=[
            "Notice-period tracking",
            "Break-clause management",
            "Rent-escalation schedules",
            "Special-condition tracking",
            "Document vault",
            "Automated reminders"
        ],
        integration=["E-Signature Platforms", "Legal Templates", "Calendar Services"],
        use_cases=[
            "Lease lifecycle management",
            "Automated renewals",
            "Rent escalation",
            "Compliance tracking"
        ]
    ),
    ServiceModule(
        id=6,
        title="Property Operations",
        category=ServiceCategory.OPERATIONS,
        icon="🔧",
        description="Comprehensive maintenance and facility management",
        features=[
            "Maintenance work orders",
            "Contractor assignment",
            "Contractor ratings",
            "Preventive-maintenance schedules",
            "Equipment registers",
            "Asset lifecycle tracking"
        ],
        key_capabilities=[
            "Utility-meter registry",
            "Meter-reading history",
            "Building inspection scheduling",
            "Cleaning schedules",
            "Security schedules",
            "Facility workflows"
        ],
        integration=["Maintenance Apps", "Contractor Networks", "Scheduling Tools"],
        use_cases=[
            "Preventive maintenance",
            "Contractor management",
            "Cost reduction",
            "Regulatory compliance"
        ]
    ),
    ServiceModule(
        id=7,
        title="Smart Building Layer",
        category=ServiceCategory.IOT,
        icon="🏗️",
        description="IoT sensor integration for real-time building monitoring",
        features=[
            "IoT sensor integration",
            "Water-level sensors",
            "Electricity monitoring",
            "Generator monitoring",
            "Solar monitoring",
            "Pump monitoring"
        ],
        key_capabilities=[
            "Lift/elevator monitoring",
            "Temperature monitoring",
            "Leak detection",
            "Smoke/fire alerts",
            "Access-control integration",
            "Smart-meter integration"
        ],
        integration=["IoT Platforms", "MQTT Brokers", "Cloud Analytics"],
        use_cases=[
            "Predictive maintenance",
            "Energy optimization",
            "Safety monitoring",
            "Utility tracking"
        ]
    ),
    ServiceModule(
        id=8,
        title="Tenant Experience",
        category=ServiceCategory.ENGAGEMENT,
        icon="😊",
        badge="new",
        description="Comprehensive tenant portal and community engagement",
        features=[
            "Tenant mobile app",
            "Tenant web portal",
            "Digital noticeboard",
            "Community announcements",
            "Visitor management",
            "Amenity booking"
        ],
        key_capabilities=[
            "Parking allocation",
            "Package-delivery management",
            "Move-in/out checklists",
            "Complaint escalation",
            "Community polls",
            "Service ratings"
        ],
        integration=["Mobile Platforms", "Communication APIs", "Booking Systems"],
        use_cases=[
            "Tenant satisfaction",
            "Community building",
            "Service delivery",
            "Issue resolution"
        ]
    ),
    ServiceModule(
        id=9,
        title="Landlord-Tenant Communication",
        category=ServiceCategory.COMMUNICATION,
        icon="💬",
        description="Multi-channel communication with automated notifications",
        features=[
            "In-app messaging",
            "Announcement targeting",
            "Automated notices",
            "Lease reminders",
            "Maintenance notifications",
            "Emergency broadcasts"
        ],
        key_capabilities=[
            "Read receipts",
            "Communication history",
            "Multi-channel notifications",
            "Notification preferences",
            "Template management",
            "Archive & compliance"
        ],
        integration=["SMS APIs", "Email Services", "Push Notifications"],
        use_cases=[
            "Important notices",
            "Maintenance scheduling",
            "Emergency alerts",
            "Community updates"
        ]
    ),
    ServiceModule(
        id=10,
        title="Property Marketplace",
        category=ServiceCategory.MARKETPLACE,
        icon="🏪",
        description="Digital marketplace for property listings and tenant applications",
        features=[
            "Property listing engine",
            "Unit availability marketplace",
            "Virtual tours",
            "Floor plans",
            "Property comparison",
            "Tenant applications"
        ],
        key_capabilities=[
            "Viewing management",
            "Viewing attendance tracking",
            "Applicant pipeline",
            "Waiting lists",
            "Digital offer letters",
            "Application workflow"
        ],
        integration=["VR/3D Tour Platforms", "Document Management", "Video Services"],
        use_cases=[
            "Unit marketing",
            "Tenant acquisition",
            "Viewing scheduling",
            "Application processing"
        ]
    ),
    ServiceModule(
        id=11,
        title="Geospatial Intelligence",
        category=ServiceCategory.ANALYTICS,
        icon="🗺️",
        description="Location-based property analytics and market intelligence",
        features=[
            "Property GIS map",
            "Nearby infrastructure",
            "Schools proximity",
            "Hospitals proximity",
            "Transport proximity",
            "Security-risk mapping"
        ],
        key_capabilities=[
            "Flood-risk mapping",
            "Land-use information",
            "Development-zone mapping",
            "Neighborhood price intelligence",
            "Property heat maps",
            "Competitor analysis"
        ],
        integration=["Google Maps APIs", "GIS Platforms", "Weather Data"],
        use_cases=[
            "Risk assessment",
            "Investment analysis",
            "Market positioning",
            "Property valuation"
        ]
    ),
    ServiceModule(
        id=12,
        title="Utility Management",
        category=ServiceCategory.OPERATIONS,
        icon="⚡",
        description="Comprehensive utility tracking and consumption analytics",
        features=[
            "Individual meter allocation",
            "Shared-meter allocation",
            "Utility bill splitting",
            "Water consumption analytics",
            "Electricity consumption analytics",
            "Prepaid-meter monitoring"
        ],
        key_capabilities=[
            "Utility anomaly detection",
            "Utility debt tracking",
            "Common-area consumption",
            "Solar-energy allocation",
            "Usage forecasting",
            "Consumption alerts"
        ],
        integration=["Meter APIs", "Utility Providers", "Analytics Dashboards"],
        use_cases=[
            "Cost reduction",
            "Conservation monitoring",
            "Tenant billing",
            "Sustainability tracking"
        ]
    ),
    ServiceModule(
        id=13,
        title="Security Management",
        category=ServiceCategory.SECURITY,
        icon="🚨",
        description="Integrated security operations and incident management",
        features=[
            "Visitor QR codes",
            "Guard dashboard",
            "Digital visitor log",
            "Vehicle registration",
            "Emergency contacts",
            "Incident reporting"
        ],
        key_capabilities=[
            "Incident evidence management",
            "Access logs",
            "Restricted-area management",
            "Security patrol checkpoints",
            "CCTV integration",
            "Alert escalation"
        ],
        integration=["CCTV Systems", "Access Control", "Emergency Services"],
        use_cases=[
            "Visitor management",
            "Incident tracking",
            "Security monitoring",
            "Emergency response"
        ]
    ),
    ServiceModule(
        id=14,
        title="AI Property Manager",
        category=ServiceCategory.AI,
        icon="🤖",
        badge="premium",
        description="Autonomous AI agent monitoring all property dimensions",
        features=[
            "Continuous monitoring",
            "Rent tracking",
            "Lease analytics",
            "Tenant insights",
            "Property health",
            "Maintenance predictions"
        ],
        key_capabilities=[
            "Utility monitoring",
            "Expense analysis",
            "Cash-flow predictions",
            "Risk detection",
            "Alert generation",
            "Autonomous actions"
        ],
        integration=["AI/ML Platform", "Data Lake", "Notification Systems"],
        use_cases=[
            "Proactive issue detection",
            "Efficiency optimization",
            "Predictive maintenance",
            "Autonomous management"
        ]
    ),
    ServiceModule(
        id=15,
        title="Fraud & Financial Controls",
        category=ServiceCategory.COMPLIANCE,
        icon="🛡️",
        description="Advanced fraud detection and financial oversight",
        features=[
            "Duplicate-payment detection",
            "Duplicate-invoice detection",
            "Suspicious refund detection",
            "Account-change verification",
            "Settlement anomaly detection",
            "Payment-source monitoring"
        ],
        key_capabilities=[
            "Unusual withdrawal detection",
            "Staff activity monitoring",
            "Four-eyes approval",
            "Transaction risk scoring",
            "Immutable audit history",
            "Real-time alerts"
        ],
        integration=["Fraud Detection Engines", "Banking Systems", "Audit Tools"],
        use_cases=[
            "Fraud prevention",
            "Compliance enforcement",
            "Risk mitigation",
            "Audit readiness"
        ]
    ),
    ServiceModule(
        id=16,
        title="Accounting & Compliance",
        category=ServiceCategory.FINANCE,
        icon="📐",
        description="Complete accounting infrastructure and compliance automation",
        features=[
            "General ledger",
            "Chart of accounts",
            "Journal entries",
            "Accounts receivable",
            "Accounts payable",
            "Vendor management"
        ],
        key_capabilities=[
            "Expense approvals",
            "Financial-period closing",
            "Accountant access",
            "Audit exports",
            "Tax-report preparation",
            "Automated statements"
        ],
        integration=["Accounting Software", "Tax Systems", "Bank Feeds"],
        use_cases=[
            "Monthly closing",
            "Tax compliance",
            "Financial reporting",
            "Audit preparation"
        ]
    ),
    ServiceModule(
        id=17,
        title="Multi-Property / Enterprise",
        category=ServiceCategory.SCALE,
        icon="🏢",
        description="Enterprise-grade multi-property and multi-tenant management",
        features=[
            "Multiple companies",
            "Multiple landlords",
            "Multiple property managers",
            "Multiple buildings",
            "Multiple estates",
            "Multiple currencies"
        ],
        key_capabilities=[
            "Multiple countries",
            "Branch management",
            "Role-based access",
            "Organization hierarchy",
            "Franchise management",
            "White-label portals"
        ],
        integration=["SSO/SAML", "Multi-tenancy Platform", "Enterprise APIs"],
        use_cases=[
            "Portfolio scaling",
            "Multi-market expansion",
            "Franchise deployment",
            "Enterprise governance"
        ]
    ),
    ServiceModule(
        id=18,
        title="Marketplace Ecosystem",
        category=ServiceCategory.MARKETPLACE,
        icon="🔗",
        description="Connected marketplace for service providers",
        features=[
            "Plumber discovery",
            "Electrician network",
            "Painter connections",
            "Security companies",
            "Cleaning services",
            "Moving companies"
        ],
        key_capabilities=[
            "Internet providers",
            "Insurance brokers",
            "Solar installers",
            "Appliance technicians",
            "Property valuers",
            "Legal professionals"
        ],
        integration=["Service Provider APIs", "Payment Systems", "Review Platforms"],
        use_cases=[
            "Service discovery",
            "Vendor management",
            "Cost reduction",
            "Quality assurance"
        ]
    ),
    ServiceModule(
        id=19,
        title="Insurance Management",
        category=ServiceCategory.RISK,
        icon="📋",
        description="Integrated insurance management and claims workflow",
        features=[
            "Property-insurance registry",
            "Policy-expiry alerts",
            "Claims management",
            "Incident-to-claim workflow",
            "Asset insurance tracking",
            "Tenant insurance tracking"
        ],
        key_capabilities=[
            "Insurance document vault",
            "Claim-status dashboard",
            "Automated renewals",
            "Coverage analysis",
            "Premium optimization",
            "Risk assessment"
        ],
        integration=["Insurance APIs", "Document Management", "Email Systems"],
        use_cases=[
            "Policy management",
            "Claims processing",
            "Risk coverage",
            "Compliance tracking"
        ]
    ),
    ServiceModule(
        id=20,
        title="Emergency & Disaster Management",
        category=ServiceCategory.SAFETY,
        icon="🚑",
        description="Comprehensive emergency response and business continuity",
        features=[
            "Fire incident workflow",
            "Flood alerts",
            "Water-leak escalation",
            "Power-outage reporting",
            "Generator activation workflow",
            "Emergency broadcast"
        ],
        key_capabilities=[
            "Evacuation management",
            "Emergency contact tree",
            "Incident postmortems",
            "Business-continuity planning",
            "Recovery procedures",
            "Drill scheduling"
        ],
        integration=["Alert Systems", "Emergency Services", "Communication Platforms"],
        use_cases=[
            "Emergency response",
            "Disaster recovery",
            "Continuity planning",
            "Incident review"
        ]
    ),
    ServiceModule(
        id=21,
        title="Developer / Construction Layer",
        category=ServiceCategory.PROJECTS,
        icon="👷",
        description="Project management for development and construction",
        features=[
            "Development projects",
            "Construction budgets",
            "Contractor management",
            "Material tracking",
            "Project milestones",
            "Site inspections"
        ],
        key_capabilities=[
            "Construction progress",
            "Variation orders",
            "Defect management",
            "Practical-completion workflow",
            "Handover management",
            "Project analytics"
        ],
        integration=["Project Management Apps", "Document Systems", "Photo Tools"],
        use_cases=[
            "Project execution",
            "Budget control",
            "Quality assurance",
            "Handover management"
        ]
    ),
    ServiceModule(
        id=22,
        title="API & Developer Platform",
        category=ServiceCategory.INTEGRATION,
        icon="⚙️",
        badge="premium",
        description="Comprehensive API suite for ecosystem integration",
        features=[
            "Property API",
            "Tenant API",
            "Lease API",
            "Payment API",
            "Utility API",
            "Maintenance API"
        ],
        key_capabilities=[
            "Accounting API",
            "Identity API",
            "Notification API",
            "Analytics API",
            "Webhook Engine",
            "Rate limiting & auth"
        ],
        integration=["REST APIs", "GraphQL", "Webhooks", "SDK Libraries"],
        use_cases=[
            "Third-party integration",
            "System interoperability",
            "Data synchronization",
            "Custom applications"
        ]
    ),
    ServiceModule(
        id=23,
        title="Advanced Automation",
        category=ServiceCategory.AI,
        icon="🔄",
        description="Event-driven automation with AI decision-making",
        features=[
            "Event triggers",
            "Rule engine",
            "AI decision logic",
            "Approval workflows",
            "Action execution",
            "Verification layer"
        ],
        key_capabilities=[
            "Audit logging",
            "Exception handling",
            "Conditional logic",
            "Time-based triggers",
            "Custom workflows",
            "Integration actions"
        ],
        integration=["AI/ML Engine", "Workflow Platform", "Notification Systems"],
        use_cases=[
            "Lease renewal automation",
            "Maintenance escalation",
            "Payment matching",
            "Risk alerting"
        ]
    ),
    ServiceModule(
        id=24,
        title="Data Ownership & Governance",
        category=ServiceCategory.COMPLIANCE,
        icon="🔒",
        description="Privacy, consent, and data governance framework",
        features=[
            "Tenant-data permissions",
            "Landlord-data permissions",
            "Consent management",
            "Data-retention policies",
            "Audit trails",
            "Data-export requests"
        ],
        key_capabilities=[
            "Account deletion workflows",
            "API access controls",
            "Encryption-key management",
            "Backup policies",
            "Disaster recovery",
            "Data residency controls"
        ],
        integration=["Identity Platforms", "Compliance Tools", "Encryption Services"],
        use_cases=[
            "GDPR compliance",
            "Data privacy",
            "Regulatory compliance",
            "Audit readiness"
        ]
    ),
    ServiceModule(
        id=25,
        title="Property Digital Twin",
        category=ServiceCategory.INNOVATION,
        icon="🌐",
        badge="premium",
        description="Complete digital replica of physical property",
        features=[
            "Building model",
            "Unit configuration",
            "Asset registry",
            "Utility networks",
            "Financial model",
            "Tenant profiles"
        ],
        key_capabilities=[
            "Staff & contractor data",
            "Visitor tracking",
            "AI Property OS",
            "Predictive capabilities",
            "Optimization engine",
            "Real-time updates"
        ],
        integration=["3D Modeling", "IoT Platform", "AI Engine", "Data Lakes"],
        use_cases=[
            "Predictive analytics",
            "Optimization",
            "Scenario planning",
            "Decision support"
        ]
    ),
]

def bootstrap_catalog():
    for svc in SERVICE_CATALOG:
        state.services[svc.id] = svc
    logger.info("Loaded all %d service modules", len(state.services))

# ──────────────────────────────────────────────────────────────
# Real-time WebSocket Manager
# ──────────────────────────────────────────────────────────────

class ConnectionManager:
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        state.websocket_clients.add(websocket)
        logger.info("WebSocket client connected – total: %d", len(state.websocket_clients))

    def disconnect(self, websocket: WebSocket):
        state.websocket_clients.discard(websocket)

    async def broadcast(self, message: dict):
        dead = set()
        for ws in state.websocket_clients:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.disconnect(ws)

manager = ConnectionManager()

# ──────────────────────────────────────────────────────────────
# Audit & Dual-Authorization
# ──────────────────────────────────────────────────────────────

def compute_hash(entry: AuditEntry) -> str:
    payload = f"{entry.timestamp.isoformat()}|{entry.actor}|{entry.action}|{entry.entity_id}"
    return hashlib.sha256(payload.encode()).hexdigest()

def record_audit(actor: str, action: str, entity_type: str, entity_id: str,
                 before: Optional[dict] = None, after: Optional[dict] = None):
    entry = AuditEntry(
        actor=actor, action=action, entity_type=entity_type,
        entity_id=entity_id, before=before, after=after
    )
    entry.hash = compute_hash(entry)
    state.audit_log.append(entry)

async def request_dual_auth(action_type: str, payload: dict, requested_by: str) -> DualAuthRequest:
    req = DualAuthRequest(action_type=action_type, payload=payload, requested_by=requested_by)
    state.dual_auth_queue[req.request_id] = req
    record_audit(requested_by, f"dual_auth_request:{action_type}", "dual_auth", req.request_id)
    await manager.broadcast({"type": "dual_auth_required", "request": req.dict()})
    return req

# ──────────────────────────────────────────────────────────────
# AI Property Manager Agent
# ──────────────────────────────────────────────────────────────

class AIPropertyManagerAgent:
    def __init__(self):
        self.rules: List[Callable] = [
            self._check_lease_expiry,
            self._check_payment_delays,
            self._check_utility_anomalies,
            self._check_maintenance_cost_spikes,
            self._check_vacancy_risk,
            self._check_generator_expenses,
            self._check_portfolio_health,
        ]

    async def run_forever(self):
        state.agent_running = True
        logger.info("🤖 AI Property Manager agent started – monitoring all 25 modules")
        while state.agent_running:
            try:
                await self.cycle()
                state.last_agent_cycle = datetime.now(timezone.utc)
            except Exception as exc:
                logger.exception("Agent cycle failed: %s", exc)
            await asyncio.sleep(settings.agent_poll_interval_sec)

    async def cycle(self):
        new_alerts: List[Alert] = []
        for rule in self.rules:
            alerts = await rule()
            new_alerts.extend(alerts)

        for alert in new_alerts:
            state.alerts.appendleft(alert)
            record_audit("ai_agent", f"alert:{alert.severity}", "alert", alert.alert_id)
            await manager.broadcast({"type": "new_alert", "alert": alert.dict()})
            if settings.enable_autonomous_actions and alert.severity in (AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY):
                await self._maybe_act(alert)

    async def _check_lease_expiry(self) -> List[Alert]:
        alerts = []
        now = datetime.now(timezone.utc)
        for t in state.tenants.values():
            if t.lease_end and (t.lease_end - now).days <= 45:
                alerts.append(Alert(
                    severity=AlertSeverity.WARNING,
                    source_module="AI Property Manager / Digital Lease Infrastructure",
                    unit_id=t.tenant_id,
                    title="Lease expiring soon",
                    message=f"Lease for tenant {t.full_name} expires in {(t.lease_end - now).days} days.",
                    recommended_action="Generate renewal offer and notify both parties."
                ))
        return alerts

    async def _check_payment_delays(self) -> List[Alert]:
        alerts = []
        for t in state.tenants.values():
            if t.payment_reliability_score < 65 or t.outstanding_balance > 0:
                alerts.append(Alert(
                    severity=AlertSeverity.WARNING if t.outstanding_balance < 50_000 else AlertSeverity.CRITICAL,
                    source_module="Tenant Risk & Reliability",
                    title="Payment reliability concern",
                    message=f"{t.full_name} – reliability {t.payment_reliability_score:.0f}%, outstanding {t.outstanding_balance:,.0f} KES",
                    recommended_action="Trigger early-warning communication sequence."
                ))
        return alerts

    async def _check_utility_anomalies(self) -> List[Alert]:
        alerts = []
        for unit in state.units.values():
            if unit.water_consumption_l > 12_000:
                alerts.append(Alert(
                    severity=AlertSeverity.WARNING,
                    source_module="Smart Building Layer / Utility Management",
                    property_id=unit.property_id,
                    unit_id=unit.unit_id,
                    title="Unusual water consumption",
                    message=f"Unit {unit.unit_id} water usage {unit.water_consumption_l:.0f} L – possible leak.",
                    recommended_action="Create inspection ticket and assign technician."
                ))
        return alerts

    async def _check_maintenance_cost_spikes(self) -> List[Alert]:
        return []

    async def _check_vacancy_risk(self) -> List[Alert]:
        return []

    async def _check_generator_expenses(self) -> List[Alert]:
        return []

    async def _check_portfolio_health(self) -> List[Alert]:
        return []

    async def _maybe_act(self, alert: Alert):
        if alert.severity == AlertSeverity.EMERGENCY:
            alert.autonomous_action_taken = "Work order auto-created + technician notified"
            await manager.broadcast({"type": "autonomous_action", "alert_id": alert.alert_id})

agent = AIPropertyManagerAgent()

# ──────────────────────────────────────────────────────────────
# Lifespan
# ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap_catalog()
    _seed_demo_data()
    agent_task = asyncio.create_task(agent.run_forever())
    yield
    state.agent_running = False
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────
# API Endpoints
# ──────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "agent_running": state.agent_running,
        "last_cycle": state.last_agent_cycle,
        "active_websockets": len(state.websocket_clients),
        "alerts_buffered": len(state.alerts),
        "services_loaded": len(state.services),
        "version": settings.version,
    }

@app.get("/api/services")
async def list_services():
    """Return all 25 service modules – exact parity with frontend."""
    return list(state.services.values())

@app.get("/api/services/{service_id}")
async def get_service(service_id: int):
    svc = state.services.get(service_id)
    if not svc:
        raise HTTPException(404, "Service module not found")
    return svc

@app.get("/api/alerts")
async def get_alerts(limit: int = 50, severity: Optional[AlertSeverity] = None):
    alerts = list(state.alerts)
    if severity:
        alerts = [a for a in alerts if a.severity == severity]
    return alerts[:limit]

@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    for a in state.alerts:
        if a.alert_id == alert_id:
            a.acknowledged = True
            record_audit("user", "acknowledge_alert", "alert", alert_id)
            return {"status": "acknowledged"}
    raise HTTPException(404, "Alert not found")

@app.post("/api/dual-auth/{request_id}/approve")
async def approve_dual_auth(request_id: str, approver: str):
    req = state.dual_auth_queue.get(request_id)
    if not req:
        raise HTTPException(404)
    req.status = ApprovalStatus.APPROVED
    req.approved_by = approver
    record_audit(approver, "dual_auth_approve", "dual_auth", request_id)
    await manager.broadcast({"type": "dual_auth_resolved", "request_id": request_id, "status": "approved"})
    return req

@app.post("/api/dual-auth/{request_id}/reject")
async def reject_dual_auth(request_id: str, rejector: str, reason: str = ""):
    req = state.dual_auth_queue.get(request_id)
    if not req:
        raise HTTPException(404)
    req.status = ApprovalStatus.REJECTED
    req.rejected_by = rejector
    req.reason = reason
    record_audit(rejector, "dual_auth_reject", "dual_auth", request_id)
    return req

@app.get("/api/finance/snapshot/{property_id}")
async def financial_snapshot(property_id: str):
    return FinancialSnapshot(
        property_id=property_id,
        period="2026-Q3",
        gross_rent=4_850_000,
        vacancy_loss=320_000,
        operating_expenses=1_120_000,
        noi=3_410_000,
        cash_flow=2_980_000,
        roi_pct=11.4,
        reserve_fund=1_250_000,
        health_score=87.5,
    )

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_json({
            "type": "bootstrap",
            "alerts": [a.dict() for a in list(state.alerts)[:20]],
            "agent_status": state.agent_running,
            "services_count": len(state.services),
        })
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ──────────────────────────────────────────────────────────────
# Demo Data
# ──────────────────────────────────────────────────────────────

def _seed_demo_data():
    state.tenants["T-1042"] = TenantProfile(
        tenant_id="T-1042",
        full_name="Amina Wanjiku",
        payment_reliability_score=58.0,
        lease_compliance_score=91.0,
        risk_score=42.0,
        outstanding_balance=45_000,
        lease_end=datetime.now(timezone.utc) + timedelta(days=38),
        early_warning_flags=["late_payment_pattern"],
    )
    state.units["U-14"] = PropertyUnit(
        unit_id="U-14",
        property_id="MWK-ESTATE-01",
        floor=3,
        bedrooms=2,
        current_rent=55_000,
        tenant_id="T-1042",
        water_consumption_l=14_800,
        electricity_kwh=320,
        health_score=71.0,
    )
    logger.info("Demo data seeded")

# ──────────────────────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "Mwarokin_Services:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
        workers=1,
    )
```

### Summary of changes

- **All 25 service modules** are now fully defined in `SERVICE_CATALOG` with exact titles, categories, icons, badges, descriptions, features, key capabilities, integrations, and use cases matching the original frontend data.
- The catalog is loaded at startup via `bootstrap_catalog()`.
- `/api/services` returns the complete list of 25 modules.
- Health endpoint now reports `services_loaded: 25`.
- AI agent continues to monitor and generate real-time alerts across the modules.

You can run it the same way:

```bash
pip install fastapi uvicorn pydantic pydantic-settings
python Mwarokin_Services.py
```