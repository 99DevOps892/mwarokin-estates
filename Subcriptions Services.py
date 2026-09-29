 Here’s a complete, modern **FastAPI backend** that powers the Mwarokin “Step 2: Configure & Review” page with real calculation, validation, promo handling, and order activation.

```python
"""
Mwarokin Estates – Step 2: Configure & Review
Backend API (FastAPI + Pydantic v2)
Python 3.11+
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from enum import Enum
from typing import Annotated, Optional
from uuid import uuid4
import re

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, ConfigDict

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mwarokin Estates – Configure & Review API",
    description="Pricing configuration, live quoting, promo codes & subscription activation",
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
# Domain constants (source of truth)
# ---------------------------------------------------------------------------

PLANS = {
    "msingi": {"name": "Msingi · Foundation", "price": 2500, "included_units": 10},
    "jengo":  {"name": "Jengo · Building",    "price": 6500, "included_units": 50},
    "milki":  {"name": "Milki · Estate",      "price": 15000, "included_units": 250},
    "taifa":  {"name": "Taifa · Enterprise",  "price": 45000, "included_units": 1000},
    "hybrid": {"name": "Hybrid Plan",         "price": 1500, "included_units": 30},
    "ppp":    {"name": "Pay Per Property",    "price": 4000, "included_units": 20},
}

CYCLES = {
    "m": {"name": "Monthly",   "months": 1,  "discount": 0.00, "label": "month"},
    "q": {"name": "Quarterly", "months": 3,  "discount": 0.05, "label": "quarter"},
    "y": {"name": "Annual",    "months": 12, "discount": 0.10, "label": "year"},
}

ADDONS = {
    "sms":   {"name": "SMS Bundle",            "desc": "5,000 rent & notice SMS",          "price": 1200, "icon": "💬"},
    "wa":    {"name": "WhatsApp Reminders",    "desc": "Automated tenant nudges",          "price": 1500, "icon": "📲"},
    "esign": {"name": "E-Signature Leases",    "desc": "Legally binding digital signing",  "price": 1200, "icon": "✍️"},
    "kra":   {"name": "KRA MRI Auto-Filing",   "desc": "Monthly rental income returns",    "price": 2000, "icon": "🧾"},
    "credit":{"name": "Tenant Credit Scoring", "desc": "Payment-history risk score",       "price": 1800, "icon": "📊"},
    "meter": {"name": "Smart Meter Sync",      "desc": "Water & power readings",           "price": 2500, "icon": "💧"},
    "cctv":  {"name": "CCTV & Gate Access",    "desc": "Link cameras and gate logs",       "price": 3500, "icon": "📹"},
    "ins":   {"name": "Landlord Cover",        "desc": "Rent guarantee & property cover",  "price": 3000, "icon": "🛡"},
    "store": {"name": "Extra Storage 100 GB",  "desc": "Documents, photos, contracts",     "price": 900,  "icon": "☁️"},
    "dom":   {"name": "Custom Domain",         "desc": "yourbrand.co.ke tenant portal",    "price": 800,  "icon": "🌐"},
}

SUPPORT = {
    "std": {"name": "Standard",           "desc": "Email · Business hours",     "price": 0},
    "pri": {"name": "Priority",           "desc": "Chat + phone · 24/7",        "price": 2500},
    "ded": {"name": "Dedicated Manager",  "desc": "Named contact · SLA",        "price": 8000},
}

ONBOARDING = {
    "self":   {"name": "Self-serve",     "desc": "Guides & videos",        "price": 0},
    "guided": {"name": "Guided Setup",   "desc": "Live 2-hour session",    "price": 7500},
    "mig":    {"name": "Full Migration", "desc": "We import your data",    "price": 12000},
}

PAYMENTS = {
    "mpesa":    {"name": "M-Pesa",       "icon": "📱"},
    "airtel":   {"name": "Airtel Money", "icon": "📶"},
    "sylloPay": {"name": "SylloPay",     "icon": "💳"},
}

ZONES = [
    "Nairobi – Westlands",
    "Nairobi – Kilimani",
    "Nairobi – Kasarani",
    "Nairobi – Embakasi",
    "Kiambu / Thika Rd",
    "Kajiado / Ongata Rongai",
    "Mombasa",
    "Other",
]

PROPERTY_OPTIONS = ["1", "2", "3", "4", "5", "6–10", "11–25", "26+"]

EXTRA_UNIT_RATE = 40          # KES per unit beyond plan allowance
VAT_RATE = 0.16
PROMO_CODES = {
    "WELCOME10": 0.10,        # 10 % off
    "LANDLORD5": 0.05,
    "MWAROKIN15": 0.15,
}

# In-memory order store (replace with DB in production)
orders_db: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class PlanKey(str, Enum):
    msingi = "msingi"
    jengo = "jengo"
    milki = "milki"
    taifa = "taifa"
    hybrid = "hybrid"
    ppp = "ppp"


class CycleKey(str, Enum):
    m = "m"
    q = "q"
    y = "y"


class SupportKey(str, Enum):
    std = "std"
    pri = "pri"
    ded = "ded"


class OnboardKey(str, Enum):
    self = "self"
    guided = "guided"
    mig = "mig"


class PaymentKey(str, Enum):
    mpesa = "mpesa"
    airtel = "airtel"
    sylloPay = "sylloPay"


class QuoteRequest(BaseModel):
    plan: PlanKey = PlanKey.jengo
    cycle: CycleKey = CycleKey.m
    units: int = Field(default=40, ge=1, le=1200)
    addons: list[str] = Field(default_factory=lambda: ["sms"])
    support: SupportKey = SupportKey.std
    onboarding: OnboardKey = OnboardKey.guided
    promo_code: Optional[str] = None
    trial: bool = True

    @field_validator("addons")
    @classmethod
    def validate_addons(cls, v: list[str]) -> list[str]:
        invalid = [a for a in v if a not in ADDONS]
        if invalid:
            raise ValueError(f"Unknown add-ons: {invalid}")
        return list(set(v))  # dedupe


class LineItem(BaseModel):
    label: str
    amount: float
    is_discount: bool = False


class QuoteResponse(BaseModel):
    plan_name: str
    plan_price: int
    included_units: int
    units: int
    extra_units: int
    extra_units_cost: float
    cycle_name: str
    cycle_months: int
    cycle_label: str
    addons_total: float
    support_price: float
    onboarding_price: float
    recurring_monthly: float
    per_cycle_before_discount: float
    cycle_discount: float
    promo_discount: float
    promo_applied: Optional[str] = None
    subtotal: float
    vat: float
    total: float
    due_today: float
    lines: list[LineItem]
    currency: str = "KES"


class ActivateRequest(BaseModel):
    plan: PlanKey
    cycle: CycleKey
    units: int = Field(ge=1, le=1200)
    properties: str = "1"
    zone: str = "Nairobi – Westlands"
    addons: list[str] = Field(default_factory=list)
    support: SupportKey = SupportKey.std
    onboarding: OnboardKey = OnboardKey.guided
    payment_method: PaymentKey = PaymentKey.mpesa
    phone: str
    start_date: date
    trial: bool = True
    promo_code: Optional[str] = None
    terms_accepted: bool = False

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if len(digits) < 9 or len(digits) > 12:
            raise ValueError("Phone number must contain 9–12 digits")
        return digits

    @field_validator("terms_accepted")
    @classmethod
    def must_accept_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must accept the service terms")
        return v

    @field_validator("start_date")
    @classmethod
    def start_not_in_past(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("Go-live date cannot be in the past")
        return v

    @field_validator("zone")
    @classmethod
    def validate_zone(cls, v: str) -> str:
        if v not in ZONES:
            raise ValueError(f"Invalid zone. Allowed: {ZONES}")
        return v

    @field_validator("addons")
    @classmethod
    def validate_addons(cls, v: list[str]) -> list[str]:
        invalid = [a for a in v if a not in ADDONS]
        if invalid:
            raise ValueError(f"Unknown add-ons: {invalid}")
        return list(set(v))


class ActivateResponse(BaseModel):
    success: bool
    reference: str
    message: str
    plan_name: str
    cycle_name: str
    total: float
    due_today: float
    trial_active: bool
    start_date: date
    payment_method: str
    phone: str
    created_at: datetime


class CatalogResponse(BaseModel):
    plans: dict
    cycles: dict
    addons: dict
    support: dict
    onboarding: dict
    payments: dict
    zones: list[str]
    property_options: list[str]
    extra_unit_rate: int
    vat_rate: float


# ---------------------------------------------------------------------------
# Core calculation engine
# ---------------------------------------------------------------------------

def calculate_quote(
    plan_key: str,
    cycle_key: str,
    units: int,
    addon_keys: list[str],
    support_key: str,
    onboard_key: str,
    promo_code: Optional[str] = None,
    trial: bool = True,
) -> QuoteResponse:
    plan = PLANS[plan_key]
    cycle = CYCLES[cycle_key]
    support = SUPPORT[support_key]
    onboard = ONBOARDING[onboard_key]

    extra_units = max(0, units - plan["included_units"])
    extra_cost = extra_units * EXTRA_UNIT_RATE

    addons_total = sum(ADDONS[a]["price"] for a in addon_keys)
    support_price = support["price"]
    onboard_price = onboard["price"]

    recurring_monthly = plan["price"] + extra_cost + addons_total + support_price
    per_cycle = recurring_monthly * cycle["months"]

    cycle_discount = per_cycle * cycle["discount"]

    promo_rate = 0.0
    promo_applied = None
    if promo_code:
        code = promo_code.strip().upper()
        if code in PROMO_CODES:
            promo_rate = PROMO_CODES[code]
            promo_applied = code
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Promo code not recognised",
            )

    after_cycle = per_cycle - cycle_discount
    promo_discount = after_cycle * promo_rate
    subtotal = after_cycle - promo_discount + onboard_price
    vat = subtotal * VAT_RATE
    total = subtotal + vat
    due_today = 0.0 if trial else total

    # Build line items (for the UI summary)
    lines: list[LineItem] = [
        LineItem(label=f"Plan ({cycle['months']} mo)", amount=plan["price"] * cycle["months"])
    ]
    if extra_cost:
        lines.append(
            LineItem(
                label=f"Extra units ({extra_units})",
                amount=extra_cost * cycle["months"],
            )
        )
    if addons_total:
        lines.append(
            LineItem(
                label=f"Add-ons ({len(addon_keys)})",
                amount=addons_total * cycle["months"],
            )
        )
    if support_price:
        lines.append(
            LineItem(
                label="Support upgrade",
                amount=support_price * cycle["months"],
            )
        )
    if onboard_price:
        lines.append(LineItem(label="Onboarding (one-time)", amount=onboard_price))

    if cycle_discount:
        lines.append(
            LineItem(
                label=f"{cycle['name']} discount",
                amount=-cycle_discount,
                is_discount=True,
            )
        )
    if promo_discount:
        lines.append(
            LineItem(
                label="Promo code",
                amount=-promo_discount,
                is_discount=True,
            )
        )
    lines.append(LineItem(label="VAT (16%)", amount=vat))

    return QuoteResponse(
        plan_name=plan["name"],
        plan_price=plan["price"],
        included_units=plan["included_units"],
        units=units,
        extra_units=extra_units,
        extra_units_cost=extra_cost,
        cycle_name=cycle["name"],
        cycle_months=cycle["months"],
        cycle_label=cycle["label"],
        addons_total=addons_total,
        support_price=support_price,
        onboarding_price=onboard_price,
        recurring_monthly=recurring_monthly,
        per_cycle_before_discount=per_cycle,
        cycle_discount=cycle_discount,
        promo_discount=promo_discount,
        promo_applied=promo_applied,
        subtotal=subtotal,
        vat=vat,
        total=round(total, 2),
        due_today=round(due_today, 2),
        lines=lines,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "mwarokin-configure",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/v1/catalog", response_model=CatalogResponse)
def get_catalog():
    """Return all selectable options so the frontend can render without hard-coding."""
    return CatalogResponse(
        plans=PLANS,
        cycles=CYCLES,
        addons=ADDONS,
        support=SUPPORT,
        onboarding=ONBOARDING,
        payments=PAYMENTS,
        zones=ZONES,
        property_options=PROPERTY_OPTIONS,
        extra_unit_rate=EXTRA_UNIT_RATE,
        vat_rate=VAT_RATE,
    )


@app.post("/api/v1/quote", response_model=QuoteResponse)
def create_quote(body: QuoteRequest):
    """
    Live quote calculation – mirrors the frontend `calc()` function.
    Call this on every change of plan / units / add-ons / cycle / promo.
    """
    return calculate_quote(
        plan_key=body.plan.value,
        cycle_key=body.cycle.value,
        units=body.units,
        addon_keys=body.addons,
        support_key=body.support.value,
        onboard_key=body.onboarding.value,
        promo_code=body.promo_code,
        trial=body.trial,
    )


@app.post("/api/v1/promo/validate")
def validate_promo(code: str):
    """Quick check whether a promo code is valid (without full quote)."""
    cleaned = code.strip().upper()
    if cleaned in PROMO_CODES:
        return {
            "valid": True,
            "code": cleaned,
            "discount_rate": PROMO_CODES[cleaned],
            "message": f"✓ {int(PROMO_CODES[cleaned]*100)}% off applied",
        }
    return {
        "valid": False,
        "code": cleaned,
        "discount_rate": 0.0,
        "message": "Code not recognised",
    }


@app.post("/api/v1/activate", response_model=ActivateResponse, status_code=status.HTTP_201_CREATED)
def activate_subscription(body: ActivateRequest):
    """
    Confirm & Activate – creates a real order, returns reference,
    and (in production) would trigger payment + contract generation.
    """
    quote = calculate_quote(
        plan_key=body.plan.value,
        cycle_key=body.cycle.value,
        units=body.units,
        addon_keys=body.addons,
        support_key=body.support.value,
        onboard_key=body.onboarding.value,
        promo_code=body.promo_code,
        trial=body.trial,
    )

    reference = f"MWK-{uuid4().hex[:6].upper()}"
    now = datetime.utcnow()

    order = {
        "reference": reference,
        "plan": body.plan.value,
        "cycle": body.cycle.value,
        "units": body.units,
        "properties": body.properties,
        "zone": body.zone,
        "addons": body.addons,
        "support": body.support.value,
        "onboarding": body.onboarding.value,
        "payment_method": body.payment_method.value,
        "phone": body.phone,
        "start_date": body.start_date.isoformat(),
        "trial": body.trial,
        "promo_code": body.promo_code,
        "quote": quote.model_dump(),
        "status": "trial_active" if body.trial else "pending_payment",
        "created_at": now.isoformat(),
    }
    orders_db[reference] = order

    payment_name = PAYMENTS[body.payment_method.value]["name"]
    trial_msg = (
        "Your 14-day free trial starts now."
        if body.trial
        else f"Payment request sent via {payment_name}."
    )

    return ActivateResponse(
        success=True,
        reference=reference,
        message=(
            f"{quote.plan_name} ({quote.cycle_name}) is confirmed at "
            f"KES {quote.total:,.0f} per {quote.cycle_label}. {trial_msg}"
        ),
        plan_name=quote.plan_name,
        cycle_name=quote.cycle_name,
        total=quote.total,
        due_today=quote.due_today,
        trial_active=body.trial,
        start_date=body.start_date,
        payment_method=payment_name,
        phone=body.phone,
        created_at=now,
    )


@app.get("/api/v1/orders/{reference}")
def get_order(reference: str):
    order = orders_db.get(reference.upper())
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.get("/api/v1/orders")
def list_orders(limit: Annotated[int, Field(ge=1, le=100)] = 20):
    items = list(orders_db.values())[-limit:]
    return {"count": len(orders_db), "orders": items}


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

### Real functionality provided

| Action                    | Endpoint                     | What it does                                      |
|---------------------------|------------------------------|---------------------------------------------------|
| Load all options          | `GET /api/v1/catalog`        | Plans, cycles, add-ons, support, zones, etc.      |
| Live quote                | `POST /api/v1/quote`         | Exact same math as the frontend `calc()`          |
| Validate promo            | `POST /api/v1/promo/validate`| Checks `WELCOME10`, `LANDLORD5`, `MWAROKIN15`     |
| Confirm & Activate        | `POST /api/v1/activate`      | Creates order, generates `MWK-XXXXXX` reference   |
| Fetch order               | `GET /api/v1/orders/{ref}`   | Retrieve a created subscription                   |

All money is calculated server-side (plan + extra units + add-ons + support + cycle discount + promo + VAT 16 %). The frontend can call `/quote` on every change and `/activate` when the user clicks **Confirm & Activate**.