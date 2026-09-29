Here’s a complete **modern FastAPI backend** for **Page 5 – Premium Operations & Intelligence** with live feed simulation, loyalty tiers, escrow ledgers, invoice rules, behavior analytics, legal cases, and ESG scoring.

```python
# main.py
"""
Mwarokin Estates – Page 5 Backend
Premium Operations & Intelligence
FastAPI · Python 3.11+
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="Mwarokin Estates – Premium Operations API",
    description="Real-time monitor, loyalty, escrow, invoice engine, analytics, legal & ESG",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────

class RealtimeStat(BaseModel):
    label: str
    value: str
    sub: str
    color: str = ""


class FeedItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    icon: str
    color: str
    text: str
    time: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class LoyaltyTierName(str, Enum):
    bronze = "bronze"
    silver = "silver"
    gold = "gold"
    platinum = "platinum"


class LoyaltyTier(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    tier: LoyaltyTierName
    name: str
    icon: str
    initials: str
    landlord: str
    points: int
    nextTier: str
    nextPoints: int
    progress: int = Field(ge=0, le=100)
    perks: List[str]


class EscrowMeta(BaseModel):
    label: str
    value: str
    color: str = ""


class TxnType(str, Enum):
    credit = "credit"
    debit = "debit"


class EscrowTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    desc: str
    date: str
    amount: str
    type: TxnType
    amount_raw: int = 0  # signed KES for ledger math


class RuleStatus(str, Enum):
    active = "active"
    paused = "paused"


class InvoiceRule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    status: RuleStatus
    desc: str
    meta: str


class BehaviorMetric(BaseModel):
    icon: str
    color: str
    label: str
    value: str
    sub: str


class CasePriority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class CaseStatus(str, Enum):
    open = "open"
    progress = "progress"
    resolved = "resolved"
    closed = "closed"


class LegalCase(BaseModel):
    id: str
    subject: str
    type: str
    priority: CasePriority
    status: CaseStatus
    filed: str
    next: str


class ESGCategory(str, Enum):
    env = "env"
    social = "social"
    gov = "gov"


class ESGMetric(BaseModel):
    label: str
    value: str
    color: str


class ESGCard(BaseModel):
    icon: str
    category: ESGCategory
    title: str
    desc: str
    metrics: List[ESGMetric]
    score: int = Field(ge=0, le=100)
    scoreLabel: str


class ToggleRuleRequest(BaseModel):
    rule_id: str
    status: RuleStatus


class ReleaseEscrowRequest(BaseModel):
    amount: int = Field(gt=0)
    description: str
    property: Optional[str] = None


class AddPointsRequest(BaseModel):
    landlord_name: str
    points: int = Field(gt=0)
    reason: Optional[str] = None


class CreateLegalCaseRequest(BaseModel):
    subject: str
    type: str
    priority: CasePriority = CasePriority.medium
    next: str = "To be scheduled"


class UpdateCaseRequest(BaseModel):
    status: Optional[CaseStatus] = None
    priority: Optional[CasePriority] = None
    next: Optional[str] = None


# ──────────────────────────────────────────────────────────────
# In-memory store
# ──────────────────────────────────────────────────────────────

realtime_stats: List[RealtimeStat] = [
    RealtimeStat(label="Collected Today", value="KSh 384,500", sub="+12 transactions", color="green"),
    RealtimeStat(label="Pending STK Push", value="8", sub="Awaiting tenant approval", color="gold"),
    RealtimeStat(label="Active Sessions", value="42", sub="Landlords online now", color=""),
    RealtimeStat(label="Avg. Payment Time", value="2.4 hrs", sub="From invoice to receipt", color="amber"),
]

realtime_feed: List[FeedItem] = [
    FeedItem(icon="fa-check-circle", color="green",
             text="<strong>Grace Wanjiku</strong> paid KSh 240,000 via M-Pesa", time="2 min ago"),
    FeedItem(icon="fa-clock", color="gold",
             text="STK push sent to <strong>James Mwangi</strong> for KSh 168,000", time="6 min ago"),
    FeedItem(icon="fa-sync", color="blue",
             text="Bank reconciliation completed for <strong>Equity Bank</strong>", time="12 min ago"),
    FeedItem(icon="fa-check-circle", color="green",
             text="<strong>Amina Hassan</strong> paid KSh 360,000 via bank transfer", time="18 min ago"),
    FeedItem(icon="fa-exclamation-triangle", color="gold",
             text="Payment reminder sent to <strong>Peter Njoroge</strong>", time="24 min ago"),
]

loyalty_tiers: List[LoyaltyTier] = [
    LoyaltyTier(tier=LoyaltyTierName.bronze, name="Bronze", icon="fa-medal",
                initials="PN", landlord="Peter Njoroge", points=340,
                nextTier="Silver", nextPoints=500, progress=68,
                perks=["Priority Support", "5% Fee Discount"]),
    LoyaltyTier(tier=LoyaltyTierName.silver, name="Silver", icon="fa-award",
                initials="JM", landlord="James Mwangi", points=720,
                nextTier="Gold", nextPoints=1000, progress=72,
                perks=["Priority Support", "10% Fee Discount", "Free Monthly Report"]),
    LoyaltyTier(tier=LoyaltyTierName.gold, name="Gold", icon="fa-crown",
                initials="GW", landlord="Grace Wanjiku", points=1450,
                nextTier="Platinum", nextPoints=2000, progress=72,
                perks=["24/7 Support", "15% Fee Discount", "Dedicated Manager", "Free KRA Filing"]),
    LoyaltyTier(tier=LoyaltyTierName.platinum, name="Platinum", icon="fa-gem",
                initials="AH", landlord="Amina Hassan", points=2340,
                nextTier="Max", nextPoints=2340, progress=100,
                perks=["VIP Support", "25% Fee Discount", "Dedicated Manager", "Free KRA Filing", "Custom Reports"]),
]

ESCROW_BALANCE = 4_285_000  # mutable

escrow_meta: List[EscrowMeta] = [
    EscrowMeta(label="Held in Trust", value="KSh 3,120,000", color="gold"),
    EscrowMeta(label="Pending Release", value="KSh 1,165,000", color=""),
    EscrowMeta(label="Released (Apr)", value="KSh 8,420,000", color="green"),
    EscrowMeta(label="Disputes Held", value="KSh 96,000", color=""),
]

escrow_transactions: List[EscrowTransaction] = [
    EscrowTransaction(desc="Rent deposit · Kilimani Court", date="Apr 12, 2025",
                      amount="+ KSh 240,000", type=TxnType.credit, amount_raw=240000),
    EscrowTransaction(desc="Disbursement · South B Apartments", date="Apr 11, 2025",
                      amount="- KSh 360,000", type=TxnType.debit, amount_raw=-360000),
    EscrowTransaction(desc="Rent deposit · Lavington Suites", date="Apr 11, 2025",
                      amount="+ KSh 450,000", type=TxnType.credit, amount_raw=450000),
    EscrowTransaction(desc="Disbursement · Westlands Heights", date="Apr 10, 2025",
                      amount="- KSh 168,000", type=TxnType.debit, amount_raw=-168000),
    EscrowTransaction(desc="Security deposit · Runda Gardens", date="Apr 9, 2025",
                      amount="+ KSh 300,000", type=TxnType.credit, amount_raw=300000),
]

invoice_rules: List[InvoiceRule] = [
    InvoiceRule(name="Monthly Rent Invoices", status=RuleStatus.active,
                desc="Generates invoices for all active tenancies on the 1st of each month. Includes rent, water, and service charges.",
                meta="Last run: Apr 1, 2025 · 312 invoices"),
    InvoiceRule(name="Late Payment Penalty", status=RuleStatus.active,
                desc="Applies a 2% penalty to any invoice unpaid 5 days after the due date. Auto-generates a new line item.",
                meta="Last run: Apr 10, 2025 · 8 penalties"),
    InvoiceRule(name="Service Charge Billing", status=RuleStatus.active,
                desc="Quarterly billing for common area maintenance, security, and waste management.",
                meta="Next run: May 1, 2025"),
    InvoiceRule(name="Utility Reconciliation", status=RuleStatus.paused,
                desc="Reconciles water and electricity meter readings against actual consumption for accurate billing.",
                meta="Paused by admin · Mar 28, 2025"),
    InvoiceRule(name="Annual Escalation", status=RuleStatus.active,
                desc="Applies annual rent escalation based on CPI + 2% cap to all eligible tenancies.",
                meta="Next run: Jul 1, 2025"),
    InvoiceRule(name="Deposit Refund Invoices", status=RuleStatus.active,
                desc="Generates refund invoices when a tenancy ends, deducting any outstanding charges.",
                meta="Last run: Apr 5, 2025 · 3 refunds"),
]

behavior_data: List[BehaviorMetric] = [
    BehaviorMetric(icon="fa-clock", color="green", label="On-Time Payments",
                   value="87%", sub="Of tenants pay before due date"),
    BehaviorMetric(icon="fa-hourglass-half", color="amber", label="Avg. Days Late",
                   value="4.2", sub="Down from 6.8 days last quarter"),
    BehaviorMetric(icon="fa-exclamation-triangle", color="red", label="Default Rate",
                   value="3.1%", sub="8 tenants in arrears"),
    BehaviorMetric(icon="fa-mobile-alt", color="blue", label="Mobile Money Usage",
                   value="94%", sub="Preferred payment method"),
]

legal_cases: List[LegalCase] = [
    LegalCase(id="LGL-2025-0142", subject="Peter Njoroge · Kasarani Villas",
              type="Rent Arrears Recovery", priority=CasePriority.high,
              status=CaseStatus.open, filed="Mar 15, 2025", next="Hearing · Apr 22, 2025"),
    LegalCase(id="LGL-2025-0138", subject="Eastleigh Plaza · Tenant Dispute",
              type="Lease Violation", priority=CasePriority.medium,
              status=CaseStatus.progress, filed="Mar 8, 2025", next="Mediation · Apr 18, 2025"),
    LegalCase(id="LGL-2025-0129", subject="Westlands Heights · Deposit Refund",
              type="Security Deposit", priority=CasePriority.low,
              status=CaseStatus.resolved, filed="Feb 22, 2025", next="Closed · Mar 30, 2025"),
    LegalCase(id="LGL-2025-0151", subject="South B Apartments · Structural Issue",
              type="Compliance", priority=CasePriority.high,
              status=CaseStatus.progress, filed="Apr 2, 2025", next="Inspection · Apr 20, 2025"),
    LegalCase(id="LGL-2025-0119", subject="Kilimani Court · Noise Complaint",
              type="Tenant Conduct", priority=CasePriority.low,
              status=CaseStatus.closed, filed="Jan 28, 2025", next="Closed · Feb 15, 2025"),
]

esg_data: List[ESGCard] = [
    ESGCard(
        icon="fa-leaf", category=ESGCategory.env, title="Environmental",
        desc="Energy efficiency, water conservation, waste management, and carbon footprint reduction.",
        metrics=[
            ESGMetric(label="Energy Reduction", value="-18% YoY", color="green"),
            ESGMetric(label="Water Saved", value="2.4M litres", color="green"),
            ESGMetric(label="Waste Recycled", value="68%", color="green"),
            ESGMetric(label="Carbon Offset", value="142 tons", color="green"),
        ],
        score=82, scoreLabel="Environmental Score",
    ),
    ESGCard(
        icon="fa-users", category=ESGCategory.social, title="Social",
        desc="Tenant welfare, community engagement, safety, and affordable housing initiatives.",
        metrics=[
            ESGMetric(label="Tenant Satisfaction", value="91%", color="blue"),
            ESGMetric(label="Safety Incidents", value="0", color="blue"),
            ESGMetric(label="Community Events", value="14", color="blue"),
            ESGMetric(label="Affordable Units", value="22%", color="blue"),
        ],
        score=78, scoreLabel="Social Score",
    ),
    ESGCard(
        icon="fa-balance-scale", category=ESGCategory.gov, title="Governance",
        desc="Transparency, ethical practices, regulatory compliance, and anti-corruption measures.",
        metrics=[
            ESGMetric(label="KRA Compliance", value="100%", color="gold"),
            ESGMetric(label="Board Diversity", value="45%", color="gold"),
            ESGMetric(label="Policy Reviews", value="6", color="gold"),
            ESGMetric(label="Transparency Index", value="A+", color="gold"),
        ],
        score=88, scoreLabel="Governance Score",
    ),
]

# Simulated live events pool
_LIVE_EVENTS = [
    {"icon": "fa-check-circle", "color": "green",
     "text": "<strong>Lucy Wambui</strong> paid KSh 75,000 via M-Pesa"},
    {"icon": "fa-clock", "color": "gold",
     "text": "STK push sent to <strong>David Ochieng</strong> for KSh 300,000"},
    {"icon": "fa-check-circle", "color": "green",
     "text": "<strong>Michael Kariuki</strong> paid KSh 300,000 via bank transfer"},
    {"icon": "fa-sync", "color": "blue",
     "text": "Auto-reconciliation completed for 12 transactions"},
    {"icon": "fa-exclamation-triangle", "color": "gold",
     "text": "Payment reminder sent to <strong>Sarah Kilonzo</strong>"},
    {"icon": "fa-check-circle", "color": "green",
     "text": "<strong>Brian Kamau</strong> paid KSh 45,000 via M-Pesa"},
]

action_log: List[dict] = []
TIER_THRESHOLDS = {"Bronze": 0, "Silver": 500, "Gold": 1000, "Platinum": 2000}


def log_action(action: str, detail: dict) -> None:
    action_log.append({
        "id": str(uuid4()),
        "action": action,
        "detail": detail,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })


def _recalc_loyalty(tier: LoyaltyTier) -> None:
    pts = tier.points
    if pts >= 2000:
        tier.tier = LoyaltyTierName.platinum
        tier.name = "Platinum"
        tier.icon = "fa-gem"
        tier.nextTier = "Max"
        tier.nextPoints = pts
        tier.progress = 100
        tier.perks = ["VIP Support", "25% Fee Discount", "Dedicated Manager", "Free KRA Filing", "Custom Reports"]
    elif pts >= 1000:
        tier.tier = LoyaltyTierName.gold
        tier.name = "Gold"
        tier.icon = "fa-crown"
        tier.nextTier = "Platinum"
        tier.nextPoints = 2000
        tier.progress = min(100, int((pts - 1000) / 10))
        tier.perks = ["24/7 Support", "15% Fee Discount", "Dedicated Manager", "Free KRA Filing"]
    elif pts >= 500:
        tier.tier = LoyaltyTierName.silver
        tier.name = "Silver"
        tier.icon = "fa-award"
        tier.nextTier = "Gold"
        tier.nextPoints = 1000
        tier.progress = min(100, int((pts - 500) / 5))
        tier.perks = ["Priority Support", "10% Fee Discount", "Free Monthly Report"]
    else:
        tier.tier = LoyaltyTierName.bronze
        tier.name = "Bronze"
        tier.icon = "fa-medal"
        tier.nextTier = "Silver"
        tier.nextPoints = 500
        tier.progress = min(100, int(pts / 5))
        tier.perks = ["Priority Support", "5% Fee Discount"]


def _fmt_ksh(n: int) -> str:
    return f"KSh {n:,}"


# ──────────────────────────────────────────────────────────────
# Real-time Payment Monitor
# ──────────────────────────────────────────────────────────────

@app.get("/api/realtime/stats", response_model=List[RealtimeStat])
def get_realtime_stats():
    return realtime_stats


@app.get("/api/realtime/feed", response_model=List[FeedItem])
def get_realtime_feed(limit: int = 20):
    return realtime_feed[:limit]


@app.post("/api/realtime/simulate")
def simulate_live_event():
    """Push a simulated live payment event into the feed."""
    ev = random.choice(_LIVE_EVENTS)
    item = FeedItem(
        icon=ev["icon"],
        color=ev["color"],
        text=ev["text"],
        time="Just now",
    )
    realtime_feed.insert(0, item)
    # Keep feed manageable
    if len(realtime_feed) > 50:
        realtime_feed.pop()
    log_action("live_event", {"text": ev["text"]})
    return {"status": "pushed", "item": item}


@app.get("/api/realtime/summary")
def realtime_summary():
    return {
        "stats": realtime_stats,
        "feed": realtime_feed[:10],
        "auto_refresh_seconds": 30,
    }


# ──────────────────────────────────────────────────────────────
# Loyalty & Rewards
# ──────────────────────────────────────────────────────────────

@app.get("/api/loyalty/tiers", response_model=List[LoyaltyTier])
def list_loyalty_tiers():
    return loyalty_tiers


@app.get("/api/loyalty/{landlord_name}")
def get_landlord_loyalty(landlord_name: str):
    tier = next((t for t in loyalty_tiers if t.landlord.lower() == landlord_name.lower()), None)
    if not tier:
        raise HTTPException(status_code=404, detail="Landlord not found in loyalty program")
    return tier


@app.post("/api/loyalty/add-points")
def add_loyalty_points(req: AddPointsRequest):
    tier = next((t for t in loyalty_tiers if t.landlord.lower() == req.landlord_name.lower()), None)
    if not tier:
        raise HTTPException(status_code=404, detail="Landlord not found")
    old_tier = tier.name
    tier.points += req.points
    _recalc_loyalty(tier)
    log_action("loyalty_points_added", {
        "landlord": req.landlord_name,
        "points": req.points,
        "new_total": tier.points,
        "tier": tier.name,
        "reason": req.reason,
    })
    return {
        "status": "updated",
        "previous_tier": old_tier,
        "current_tier": tier.name,
        "points": tier.points,
        "tier": tier,
    }


# ──────────────────────────────────────────────────────────────
# Escrow & Trust Account
# ──────────────────────────────────────────────────────────────

@app.get("/api/escrow/balance")
def get_escrow_balance():
    return {
        "balance": ESCROW_BALANCE,
        "formatted": _fmt_ksh(ESCROW_BALANCE),
        "currency": "KES",
        "change_pct": 12.4,
        "meta": escrow_meta,
    }


@app.get("/api/escrow/transactions", response_model=List[EscrowTransaction])
def list_escrow_transactions(limit: int = 50):
    return escrow_transactions[:limit]


@app.post("/api/escrow/deposit")
def escrow_deposit(req: ReleaseEscrowRequest):
    global ESCROW_BALANCE
    ESCROW_BALANCE += req.amount
    txn = EscrowTransaction(
        desc=req.description,
        date=datetime.utcnow().strftime("%b %d, %Y"),
        amount=f"+ {_fmt_ksh(req.amount)}",
        type=TxnType.credit,
        amount_raw=req.amount,
    )
    escrow_transactions.insert(0, txn)
    log_action("escrow_deposit", {"amount": req.amount, "desc": req.description})
    return {
        "status": "deposited",
        "new_balance": ESCROW_BALANCE,
        "formatted": _fmt_ksh(ESCROW_BALANCE),
        "transaction": txn,
    }


@app.post("/api/escrow/release")
def escrow_release(req: ReleaseEscrowRequest):
    global ESCROW_BALANCE
    if req.amount > ESCROW_BALANCE:
        raise HTTPException(status_code=400, detail="Insufficient escrow balance")
    ESCROW_BALANCE -= req.amount
    txn = EscrowTransaction(
        desc=req.description,
        date=datetime.utcnow().strftime("%b %d, %Y"),
        amount=f"- {_fmt_ksh(req.amount)}",
        type=TxnType.debit,
        amount_raw=-req.amount,
    )
    escrow_transactions.insert(0, txn)
    log_action("escrow_release", {"amount": req.amount, "desc": req.description})
    return {
        "status": "released",
        "new_balance": ESCROW_BALANCE,
        "formatted": _fmt_ksh(ESCROW_BALANCE),
        "transaction": txn,
    }


# ──────────────────────────────────────────────────────────────
# Automated Invoice Engine
# ──────────────────────────────────────────────────────────────

@app.get("/api/invoice-rules", response_model=List[InvoiceRule])
def list_invoice_rules(status: Optional[RuleStatus] = None):
    if status:
        return [r for r in invoice_rules if r.status == status]
    return invoice_rules


@app.patch("/api/invoice-rules/toggle")
def toggle_invoice_rule(req: ToggleRuleRequest):
    rule = next((r for r in invoice_rules if r.id == req.rule_id), None)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule.status = req.status
    if req.status == RuleStatus.paused:
        rule.meta = f"Paused by admin · {datetime.utcnow().strftime('%b %d, %Y')}"
    else:
        rule.meta = f"Resumed · {datetime.utcnow().strftime('%b %d, %Y')}"
    log_action("invoice_rule_toggled", {"name": rule.name, "status": req.status})
    return {"status": "updated", "rule": rule}


@app.post("/api/invoice-rules/{rule_id}/run")
def run_invoice_rule(rule_id: str):
    rule = next((r for r in invoice_rules if r.id == rule_id), None)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    if rule.status != RuleStatus.active:
        raise HTTPException(status_code=400, detail="Rule is paused")
    count = random.randint(3, 50)
    rule.meta = f"Last run: {datetime.utcnow().strftime('%b %d, %Y')} · {count} invoices"
    log_action("invoice_rule_run", {"name": rule.name, "invoices": count})
    return {
        "status": "executed",
        "message": f"Rule '{rule.name}' executed · {count} invoices generated",
        "rule": rule,
    }


# ──────────────────────────────────────────────────────────────
# Tenant Payment Behavior Analytics
# ──────────────────────────────────────────────────────────────

@app.get("/api/behavior", response_model=List[BehaviorMetric])
def get_behavior_metrics():
    return behavior_data


@app.get("/api/behavior/summary")
def behavior_summary():
    return {
        "metrics": behavior_data,
        "insights": [
            "On-time payment rate improved 4pp vs last quarter",
            "Mobile money remains dominant (94%)",
            "Default rate within industry target (<5%)",
        ],
    }


# ──────────────────────────────────────────────────────────────
# Legal & Compliance Case Tracker
# ──────────────────────────────────────────────────────────────

@app.get("/api/legal/cases", response_model=List[LegalCase])
def list_legal_cases(
    status: Optional[CaseStatus] = None,
    priority: Optional[CasePriority] = None,
):
    result = legal_cases
    if status:
        result = [c for c in result if c.status == status]
    if priority:
        result = [c for c in result if c.priority == priority]
    return result


@app.get("/api/legal/cases/{case_id}", response_model=LegalCase)
def get_legal_case(case_id: str):
    case = next((c for c in legal_cases if c.id == case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@app.post("/api/legal/cases", response_model=LegalCase, status_code=status.HTTP_201_CREATED)
def create_legal_case(req: CreateLegalCaseRequest):
    case_id = f"LGL-2025-{random.randint(1000, 9999)}"
    case = LegalCase(
        id=case_id,
        subject=req.subject,
        type=req.type,
        priority=req.priority,
        status=CaseStatus.open,
        filed=datetime.utcnow().strftime("%b %d, %Y"),
        next=req.next,
    )
    legal_cases.insert(0, case)
    log_action("legal_case_created", case.model_dump())
    return case


@app.patch("/api/legal/cases/{case_id}")
def update_legal_case(case_id: str, req: UpdateCaseRequest):
    case = next((c for c in legal_cases if c.id == case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if req.status is not None:
        case.status = req.status
    if req.priority is not None:
        case.priority = req.priority
    if req.next is not None:
        case.next = req.next
    log_action("legal_case_updated", {"id": case_id, **req.model_dump(exclude_none=True)})
    return case


# ──────────────────────────────────────────────────────────────
# Sustainability & ESG Reporting
# ──────────────────────────────────────────────────────────────

@app.get("/api/esg", response_model=List[ESGCard])
def get_esg_data():
    return esg_data


@app.get("/api/esg/summary")
def esg_summary():
    scores = {c.category.value: c.score for c in esg_data}
    overall = round(sum(scores.values()) / len(scores), 1)
    return {
        "overall_score": overall,
        "grade": "A" if overall >= 85 else "B+" if overall >= 75 else "B",
        "categories": esg_data,
        "scores": scores,
    }


@app.get("/api/esg/{category}", response_model=ESGCard)
def get_esg_category(category: ESGCategory):
    card = next((c for c in esg_data if c.category == category), None)
    if not card:
        raise HTTPException(status_code=404, detail="Category not found")
    return card


# ──────────────────────────────────────────────────────────────
# Full Page 5 payload
# ──────────────────────────────────────────────────────────────

@app.get("/api/page5")
def page5_data():
    return {
        "realtime": {
            "stats": realtime_stats,
            "feed": realtime_feed[:10],
            "auto_refresh_seconds": 30,
        },
        "loyalty": loyalty_tiers,
        "escrow": {
            "balance": ESCROW_BALANCE,
            "formatted": _fmt_ksh(ESCROW_BALANCE),
            "change_pct": 12.4,
            "meta": escrow_meta,
            "transactions": escrow_transactions[:10],
        },
        "invoice_rules": invoice_rules,
        "behavior": behavior_data,
        "legal": legal_cases,
        "esg": {
            "overall": round(sum(c.score for c in esg_data) / len(esg_data), 1),
            "categories": esg_data,
        },
    }


@app.get("/api/actions")
def get_action_log(limit: int = 50):
    return action_log[-limit:]


@app.get("/")
def root():
    return {
        "service": "Mwarokin Estates – Premium Operations & Intelligence",
        "page": 5,
        "version": "1.0.0",
        "docs": "/docs",
        "page5": "/api/page5",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### Run

```bash
pip install fastapi uvicorn pydantic
python main.py
```

→ **http://localhost:8000/docs**

### Real functionality

| Feature                | Key endpoints                                           | Behaviour                                      |
|------------------------|---------------------------------------------------------|------------------------------------------------|
| **Live Monitor**       | `GET /api/realtime/*`, `POST /api/realtime/simulate`    | Stats + feed; push simulated live events       |
| **Loyalty**            | `GET /api/loyalty/*`, `POST /api/loyalty/add-points`    | Add points → auto-recalculate tier & perks     |
| **Escrow**             | `GET /api/escrow/*`, `POST .../deposit`, `.../release`  | Real balance ledger with credit/debit          |
| **Invoice Engine**     | `GET /api/invoice-rules`, `PATCH .../toggle`, `POST .../run` | Pause/resume rules, execute on demand     |
| **Behavior Analytics** | `GET /api/behavior`                                     | Payment behaviour KPIs                         |
| **Legal Tracker**      | `GET/POST /api/legal/cases`, `PATCH .../{id}`           | Create, filter, update status/priority         |
| **ESG**                | `GET /api/esg`, `/api/esg/summary`                      | Category scores + overall grade                |
| **Full page**          | `GET /api/page5`                                        | Single payload for the UI                      |
| **Audit**              | `GET /api/actions`                                      | Every write is logged                          |

Call `POST /api/realtime/simulate` on a timer (or from the frontend every 8–30s) to keep the live feed moving. Escrow deposits/releases update the running balance. Loyalty points automatically promote tiers. Swap the in-memory stores for a database when you need persistence.