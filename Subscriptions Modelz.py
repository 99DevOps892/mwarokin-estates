Here’s a complete, modern **FastAPI backend** that powers the Mwarokin “Specialised Plans (Page 2)” UI with real multi-select quoting, category filtering, annual discount, and confirmation.

```python
"""
Mwarokin Estates – Specialised Plans (Page 2)
Backend API (FastAPI + Pydantic v2)
Python 3.11+
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mwarokin Estates – Specialised Plans API",
    description="Specialised plan catalogue, multi-select quoting, annual discount & confirmation",
    version="1.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Domain data
# ---------------------------------------------------------------------------

PLANS = {
    "diaspora": {
        "name": "Diaspora Landlord Care",
        "subtitle": "Own in Kenya, live abroad",
        "icon": "🌍",
        "category": "Owners",
        "price_label": "KSh 12,000",
        "price_unit": "/mo",
        "fixed_monthly": 12000,
        "one_time": 0,
        "pricing_type": "fixed",
        "description": "Full remote ownership: we inspect, collect and pay you out in your home currency while family stay in the loop.",
        "features": [
            "Video inspections each quarter",
            "USD · GBP · EUR payouts",
            "Family proxy approvals",
            "Monthly digest via WhatsApp",
        ],
        "tag": "Popular",
        "hot": True,
    },
    "chama": {
        "name": "Chama & Sacco Estate Pool",
        "subtitle": "Jointly owned property",
        "icon": "🤝",
        "category": "Groups",
        "price_label": "KSh 8,500",
        "price_unit": "/mo",
        "fixed_monthly": 8500,
        "one_time": 0,
        "pricing_type": "fixed",
        "description": "Run a shared investment property with transparent records, member voting and automatic profit splits.",
        "features": [
            "Shared ownership ledger",
            "Member voting & resolutions",
            "Automated dividend splits",
            "Contribution reminders",
        ],
        "tag": "Group",
        "hot": False,
    },
    "student": {
        "name": "Student Housing Suite",
        "subtitle": "Hostels & campus rentals",
        "icon": "🎓",
        "category": "Specialised",
        "price_label": "KSh 300",
        "price_unit": "/bed/mo",
        "fixed_monthly": 0,
        "one_time": 0,
        "pricing_type": "usage",  # per bed
        "description": "Semester-aware billing and guardian-friendly payments for hostels near universities and colleges.",
        "features": [
            "Semester billing cycles",
            "Guardian payment links",
            "Roommate matching",
            "Check-in / check-out inspections",
        ],
        "tag": "Per bed",
        "hot": False,
    },
    "shortstay": {
        "name": "Short-Stay Host Pro",
        "subtitle": "Furnished & holiday lets",
        "icon": "🛎️",
        "category": "Specialised",
        "price_label": "12%",
        "price_unit": "of bookings",
        "fixed_monthly": 0,
        "one_time": 0,
        "pricing_type": "percentage",
        "description": "Turn vacant units into nightly income with calendar sync, dynamic pricing and turnover automation.",
        "features": [
            "Multi-platform calendar sync",
            "Dynamic nightly pricing",
            "Smart check-in codes",
            "Turnover cleaning dispatch",
        ],
        "tag": "Revenue",
        "hot": True,
    },
    "cowork": {
        "name": "Commercial & Co-Working Suite",
        "subtitle": "Offices, shops, flex desks",
        "icon": "🏢",
        "category": "Specialised",
        "price_label": "KSh 18,000",
        "price_unit": "/mo",
        "fixed_monthly": 18000,
        "one_time": 0,
        "pricing_type": "fixed",
        "description": "Manage commercial floors with desk booking, service-charge billing and visitor control.",
        "features": [
            "Desk & meeting-room booking",
            "Access-card management",
            "Service charge (CAM) billing",
            "Visitor pre-registration",
        ],
        "tag": "Commercial",
        "hot": False,
    },
    "rentguard": {
        "name": "RentGuard Assurance",
        "subtitle": "Guaranteed rent cover",
        "icon": "🛡️",
        "category": "Fintech",
        "price_label": "3%",
        "price_unit": "of monthly rent",
        "fixed_monthly": 0,
        "one_time": 0,
        "pricing_type": "percentage",
        "description": "Sleep easy — get rent paid even when tenants default, with legal cover and damage protection.",
        "features": [
            "Up to 6 months rent guaranteed",
            "Eviction legal cover",
            "Damage cover to KSh 200k",
            "Claims settled in 48 hours",
        ],
        "tag": "Insurance",
        "hot": True,
    },
    "advance": {
        "name": "Rent Advance Line",
        "subtitle": "Cash today, repaid from rent",
        "icon": "💸",
        "category": "Fintech",
        "price_label": "2%",
        "price_unit": "per advance",
        "fixed_monthly": 0,
        "one_time": 0,
        "pricing_type": "percentage",
        "description": "Access up to three months of expected rent upfront, repaid automatically from tenant payments.",
        "features": [
            "Advance up to 3 months rent",
            "Instant M-Pesa disbursement",
            "Auto-repay from rent flow",
            "No collateral for verified owners",
        ],
        "tag": "Fintech",
        "hot": False,
    },
    "green": {
        "name": "Green Estate Pack",
        "subtitle": "Sustainability & savings",
        "icon": "🌱",
        "category": "Specialised",
        "price_label": "KSh 6,000",
        "price_unit": "/mo",
        "fixed_monthly": 6000,
        "one_time": 0,
        "pricing_type": "fixed",
        "description": "Cut running costs and attract eco-minded tenants with resource tracking and a green rating.",
        "features": [
            "Solar & water usage tracking",
            "Estate carbon score",
            "Rainwater harvesting alerts",
            "Green-rated listing badge",
        ],
        "tag": "Eco",
        "hot": False,
    },
    "meter": {
        "name": "Smart Metering Network",
        "subtitle": "IoT water & power meters",
        "icon": "📟",
        "category": "Specialised",
        "price_label": "KSh 350",
        "price_unit": "/meter/mo",
        "fixed_monthly": 0,
        "one_time": 0,
        "pricing_type": "usage",  # per meter
        "description": "Prepaid smart meters that end disputed bills and catch leaks before they become losses.",
        "features": [
            "Prepaid water & power",
            "Leak detection alerts",
            "Remote cut-off / reconnect",
            "Per-unit consumption analytics",
        ],
        "tag": "IoT",
        "hot": False,
    },
    "hoa": {
        "name": "Residents' Association Hub",
        "subtitle": "Gated & apartment communities",
        "icon": "🏘️",
        "category": "Groups",
        "price_label": "KSh 5,000",
        "price_unit": "+ KSh 50/household",
        "fixed_monthly": 5000,
        "one_time": 0,
        "pricing_type": "hybrid",  # base + per household
        "description": "A digital home for service charges, notices, polls and community life.",
        "features": [
            "Service-charge collection",
            "Noticeboard & live polls",
            "AGM & minutes vault",
            "Amenity & event booking",
        ],
        "tag": "Community",
        "hot": False,
    },
    "rto": {
        "name": "Rent-to-Own Programme",
        "subtitle": "Tenants build equity",
        "icon": "🔑",
        "category": "Fintech",
        "price_label": "KSh 10,000",
        "price_unit": "/mo + 1%",
        "fixed_monthly": 10000,
        "one_time": 0,
        "pricing_type": "hybrid",
        "description": "Let tenants earn equity with every payment while you secure a committed buyer at a locked price.",
        "features": [
            "Equity credit per payment",
            "Buy-out schedule tracker",
            "Price & valuation lock",
            "Digital agreement signing",
        ],
        "tag": "New",
        "hot": True,
    },
    "lifetime": {
        "name": "Founding Member Lifetime",
        "subtitle": "Pay once, own it forever",
        "icon": "👑",
        "category": "Premium",
        "price_label": "KSh 250,000",
        "price_unit": "one-time",
        "fixed_monthly": 0,
        "one_time": 250000,
        "pricing_type": "one_time",
        "description": "Permanent top-tier access for early partners, with a voice in what we build next.",
        "features": [
            "Lifetime platform access",
            "Priority feature voting",
            "Founding member badge",
            "Free onboarding & migration",
        ],
        "tag": "Limited",
        "hot": True,
    },
}

CATEGORIES = ["All", "Owners", "Groups", "Specialised", "Fintech", "Premium"]

PAYMENT_METHODS = ["M-Pesa", "Airtel Money", "SylloPay"]

ANNUAL_DISCOUNT = 0.10  # 10 % off fixed recurring when billed annually

# In-memory store of confirmed selections
selections_db: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class BillingCycle(str, Enum):
    monthly = "m"
    annual = "a"


class PaymentMethod(str, Enum):
    mpesa = "M-Pesa"
    airtel = "Airtel Money"
    syllopay = "SylloPay"


class PlanOut(BaseModel):
    id: str
    name: str
    subtitle: str
    icon: str
    category: str
    price_label: str
    price_unit: str
    fixed_monthly: int
    one_time: int
    pricing_type: str
    description: str
    features: list[str]
    tag: str
    hot: bool


class QuoteRequest(BaseModel):
    plan_ids: list[str] = Field(..., min_length=1)
    billing: BillingCycle = BillingCycle.monthly

    @field_validator("plan_ids")
    @classmethod
    def validate_plans(cls, v: list[str]) -> list[str]:
        unknown = [pid for pid in v if pid not in PLANS]
        if unknown:
            raise ValueError(f"Unknown plan id(s): {unknown}")
        return list(dict.fromkeys(v))  # preserve order, dedupe


class LineItem(BaseModel):
    plan_id: str
    name: str
    icon: str
    price_label: str
    price_unit: str
    fixed_monthly: int
    one_time: int
    pricing_type: str


class QuoteResponse(BaseModel):
    plans: list[LineItem]
    billing: str
    billing_label: str
    fixed_monthly_total: int
    fixed_recurring: float          # after annual discount if applicable
    one_time_total: int
    usage_based_count: int
    due_today: float
    currency: str = "KES"
    formatted_fixed: str
    formatted_one_time: str
    formatted_due: str


class ConfirmRequest(BaseModel):
    plan_ids: list[str] = Field(..., min_length=1)
    billing: BillingCycle = BillingCycle.monthly
    payment_method: PaymentMethod = PaymentMethod.mpesa

    @field_validator("plan_ids")
    @classmethod
    def validate_plans(cls, v: list[str]) -> list[str]:
        unknown = [pid for pid in v if pid not in PLANS]
        if unknown:
            raise ValueError(f"Unknown plan id(s): {unknown}")
        return list(dict.fromkeys(v))


class ConfirmResponse(BaseModel):
    success: bool
    reference: str
    message: str
    plan_count: int
    billing: str
    payment_method: str
    due_today: float
    fixed_recurring: float
    one_time_total: int
    created_at: datetime


class CatalogResponse(BaseModel):
    plans: list[PlanOut]
    categories: list[str]
    payment_methods: list[str]
    annual_discount: float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def kes(n: float) -> str:
    return f"KSh {round(n):,}"


def build_quote(plan_ids: list[str], billing: str) -> QuoteResponse:
    items: list[LineItem] = []
    fixed = 0
    once = 0
    usage = 0

    for pid in plan_ids:
        p = PLANS[pid]
        items.append(
            LineItem(
                plan_id=pid,
                name=p["name"],
                icon=p["icon"],
                price_label=p["price_label"],
                price_unit=p["price_unit"],
                fixed_monthly=p["fixed_monthly"],
                one_time=p["one_time"],
                pricing_type=p["pricing_type"],
            )
        )
        fixed += p["fixed_monthly"]
        once += p["one_time"]
        if p["pricing_type"] in ("usage", "percentage") and p["fixed_monthly"] == 0 and p["one_time"] == 0:
            usage += 1
        elif p["pricing_type"] == "hybrid" and p["fixed_monthly"] > 0:
            # hybrid still contributes fixed; extra usage is noted separately if needed
            pass

    discount = (1 - ANNUAL_DISCOUNT) if billing == "a" else 1.0
    months = 12 if billing == "a" else 1
    recurring = fixed * months * discount
    due = recurring + once

    return QuoteResponse(
        plans=items,
        billing=billing,
        billing_label="Annual (−10%)" if billing == "a" else "Monthly",
        fixed_monthly_total=fixed,
        fixed_recurring=round(recurring, 2),
        one_time_total=once,
        usage_based_count=usage,
        due_today=round(due, 2),
        formatted_fixed=kes(recurring) + (" /yr" if billing == "a" else " /mo"),
        formatted_one_time=kes(once) if once else "",
        formatted_due=kes(due),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "mwarokin-specialised",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/v1/catalog", response_model=CatalogResponse)
def get_catalog(
    category: Annotated[str, Query(description="Filter by category")] = "All",
):
    """Return all specialised plans, optionally filtered by category."""
    plans = []
    for pid, p in PLANS.items():
        if category != "All" and p["category"] != category:
            continue
        plans.append(
            PlanOut(
                id=pid,
                name=p["name"],
                subtitle=p["subtitle"],
                icon=p["icon"],
                category=p["category"],
                price_label=p["price_label"],
                price_unit=p["price_unit"],
                fixed_monthly=p["fixed_monthly"],
                one_time=p["one_time"],
                pricing_type=p["pricing_type"],
                description=p["description"],
                features=p["features"],
                tag=p["tag"],
                hot=p["hot"],
            )
        )
    return CatalogResponse(
        plans=plans,
        categories=CATEGORIES,
        payment_methods=PAYMENT_METHODS,
        annual_discount=ANNUAL_DISCOUNT,
    )


@app.get("/api/v1/plans/{plan_id}", response_model=PlanOut)
def get_plan(plan_id: str):
    if plan_id not in PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")
    p = PLANS[plan_id]
    return PlanOut(id=plan_id, **{k: p[k] for k in PlanOut.model_fields if k != "id"})


@app.post("/api/v1/quote", response_model=QuoteResponse)
def create_quote(body: QuoteRequest):
    """
    Live quote for a multi-select of specialised plans.
    Mirrors the frontend review modal calculation.
    """
    return build_quote(body.plan_ids, body.billing.value)


@app.post("/api/v1/confirm", response_model=ConfirmResponse, status_code=status.HTTP_201_CREATED)
def confirm_selection(body: ConfirmRequest):
    """
    Lock in the specialised-plan selection.
    Returns a reference and payment prompt message.
    """
    quote = build_quote(body.plan_ids, body.billing.value)
    reference = f"MWK-SP-{uuid4().hex[:6].upper()}"
    now = datetime.utcnow()

    record = {
        "reference": reference,
        "plan_ids": body.plan_ids,
        "billing": body.billing.value,
        "payment_method": body.payment_method.value,
        "quote": quote.model_dump(),
        "status": "confirmed",
        "created_at": now.isoformat(),
    }
    selections_db[reference] = record

    return ConfirmResponse(
        success=True,
        reference=reference,
        message=(
            f"Selection confirmed. Payment prompt sent via {body.payment_method.value}. "
            f"Due today: {quote.formatted_due}."
        ),
        plan_count=len(body.plan_ids),
        billing=quote.billing_label,
        payment_method=body.payment_method.value,
        due_today=quote.due_today,
        fixed_recurring=quote.fixed_recurring,
        one_time_total=quote.one_time_total,
        created_at=now,
    )


@app.get("/api/v1/selections/{reference}")
def get_selection(reference: str):
    rec = selections_db.get(reference.upper())
    if not rec:
        raise HTTPException(status_code=404, detail="Selection not found")
    return rec


@app.get("/api/v1/selections")
def list_selections(limit: Annotated[int, Query(ge=1, le=100)] = 20):
    items = list(selections_db.values())[-limit:]
    return {"count": len(selections_db), "selections": items}


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### Quick start

```bash
pip install fastapi uvicorn pydantic
# save as main.py
uvicorn main:app --reload --port 8000
```

### Real functionality

| Endpoint | What it does |
|----------|--------------|
| `GET /api/v1/catalog?category=Fintech` | All (or filtered) specialised plans |
| `GET /api/v1/plans/{id}` | Single plan detail |
| `POST /api/v1/quote` | Live multi-select quote (monthly / annual −10 %) |
| `POST /api/v1/confirm` | Lock selection → generates `MWK-SP-XXXXXX` + payment message |
| `GET /api/v1/selections/{ref}` | Retrieve a confirmed selection |

Pricing logic matches the frontend exactly:

- Fixed monthly plans summed
- Annual = fixed × 12 × 0.9
- One-time (Lifetime) added in full
- Usage / percentage plans counted but not monetised in the fixed total
- Due today = recurring + one-time

The frontend can replace its local `review()` / `done()` logic with calls to `/quote` and `/confirm`.