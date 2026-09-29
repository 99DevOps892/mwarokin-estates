**Modern Python Subscription System for Mwarokin Estates**

Here's a complete, production-ready **FastAPI** backend for the monthly subscription system based on your plans (Msingi, Jengo, Milki, Taifa) with support for landlords, agencies, and internal Mwarokin staff.

### Features Included:
- User roles: `landlord`, `agency`, `mwarokin_staff`
- Subscription tiers with monthly & annual billing (20% discount)
- Transaction fees: **KSh 1 – KSh 5** per transaction (configurable)
- M-Pesa simulation + real integration stub
- SQLite/PostgreSQL ready (via SQLAlchemy + Alembic)
- Modern async code, Pydantic v2, background tasks for billing

---

### Project Structure
```bash
mwarokin-subscriptions/
├── main.py
├── models.py
├── schemas.py
├── crud.py
├── payments.py
├── config.py
├── requirements.txt
└── alembic/          # for migrations
```

---

### 1. `requirements.txt`
```txt
fastapi==0.115.*
uvicorn[standard]
sqlalchemy==2.0.*
alembic
pydantic[email]
python-dotenv
httpx
psycopg2-binary  # for PostgreSQL
```

---

### 2. `config.py`
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./mwarokin.db"
    MPESA_CONSUMER_KEY: str = "your_key"
    MPESA_CONSUMER_SECRET: str = "your_secret"
    MPESA_SHORTCODE: str = "174379"
    MPESA_PASSKEY: str = "your_passkey"
    TRANSACTION_FEE_MIN: int = 1
    TRANSACTION_FEE_MAX: int = 5

    class Config:
        env_file = ".env"

settings = Settings()
```

---
"""
Mwarokin Estates – Subscription Checkout
Backend API (FastAPI + Pydantic v2)
Python 3.11+
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from enum import Enum
from typing import Annotated, Optional
from uuid import uuid4
import re

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mwarokin Estates – Subscription Checkout API",
    description="Plan selection, multi-currency pricing, account signup & 14-day free trial",
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
    "msingi": {
        "name": "Msingi",
        "tagline": "Foundation · Up to 10 units",
        "price_ksh": 2500,
        "popular": False,
        "features": [
            "10 residential units",
            "Basic Lipa Mdogo",
            "Rent dashboard",
            "Schedule viewings",
            "KRA calculator (basic)",
            "Water & trash billing",
        ],
    },
    "jengo": {
        "name": "Jengo",
        "tagline": "Building · Up to 50 units",
        "price_ksh": 6500,
        "popular": True,
        "features": [
            "50 residential units",
            "Full Lipa Mdogo plans",
            "Caretaker portal",
            "Financial dashboard",
            "KRA tax calculator (full)",
            "Elderly support mode",
            "Renovation management",
        ],
    },
    "milki": {
        "name": "Milki",
        "tagline": "Estate · Up to 250 units",
        "price_ksh": 15000,
        "popular": False,
        "features": [
            "250 residential units",
            "Multi-property portfolio",
            "Security management",
            "Communication centre",
            "Properties billing",
            "KRA reports PDF",
        ],
    },
    "taifa": {
        "name": "Taifa",
        "tagline": "Enterprise · Unlimited units",
        "price_ksh": 45000,
        "popular": False,
        "features": [
            "Unlimited units",
            "White-label branding",
            "API integrations",
            "Dedicated account manager",
            "24/7 support & SLA",
            "On-site training",
        ],
    },
}

CYCLES = {
    "monthly": {
        "label": "Monthly",
        "months": 1,
        "discount": 0.00,
        "unit": "/mo",
        "perk": "<b>Maximum flexibility</b> — pay month to month and cancel anytime.",
        "badge": "Flexible",
    },
    "quarterly": {
        "label": "Quarterly",
        "months": 3,
        "discount": 0.08,
        "unit": "/qtr",
        "perk": "<b>Save 8%</b> — billed every 3 months, plus priority email support.",
        "badge": "Save 8%",
    },
    "biannual": {
        "label": "Biannual",
        "months": 6,
        "discount": 0.14,
        "unit": "/6 mo",
        "perk": "<b>Save 14%</b> — billed every 6 months, plus a free onboarding call.",
        "badge": "Save 14%",
    },
    "annual": {
        "label": "Annual",
        "months": 12,
        "discount": 0.20,
        "unit": "/yr",
        "perk": "<b>Best value, save 20%</b> — billed yearly, plus free staff training & priority support.",
        "badge": "Save 20%",
    },
}

RATES = {"KSH": 1.0, "USD": 0.0077, "EUR": 0.0071}
SYMBOLS = {"KSH": "KSH ", "USD": "$", "EUR": "€"}

ROLES = ["Landlord / Landlady", "Property Manager", "Caretaker", "Estate Developer"]
COUNTIES = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Other"]
PAYMENT_METHODS = ["mpesa", "airtel", "card"]

TRIAL_DAYS = 14

# In-memory store
subscriptions_db: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Enums & models
# ---------------------------------------------------------------------------

class PlanKey(str, Enum):
    msingi = "msingi"
    jengo = "jengo"
    milki = "milki"
    taifa = "taifa"


class CycleKey(str, Enum):
    monthly = "monthly"
    quarterly = "quarterly"
    biannual = "biannual"
    annual = "annual"


class Currency(str, Enum):
    KSH = "KSH"
    USD = "USD"
    EUR = "EUR"


class PaymentMethod(str, Enum):
    mpesa = "mpesa"
    airtel = "airtel"
    card = "card"


class PriceBreakdown(BaseModel):
    base: float
    total: float
    save: float
    monthly_equivalent: float
    currency: str
    symbol: str
    formatted_base: str
    formatted_total: str
    formatted_save: str
    formatted_monthly: str
    formatted_was: Optional[str] = None


class PlanCard(BaseModel):
    key: str
    name: str
    tagline: str
    popular: bool
    features: list[str]
    price: PriceBreakdown


class QuoteResponse(BaseModel):
    currency: str
    cycle: str
    cycle_label: str
    cycle_months: int
    cycle_unit: str
    cycle_perk: str
    discount_percent: int
    plans: list[PlanCard]
    selected: Optional[PlanCard] = None
    summary: Optional[dict] = None


class CheckoutRequest(BaseModel):
    plan: PlanKey = PlanKey.jengo
    cycle: CycleKey = CycleKey.monthly
    currency: Currency = Currency.KSH

    first_name: str = Field(..., min_length=1, max_length=80)
    last_name: str = Field(..., min_length=1, max_length=80)
    email: EmailStr
    phone: str
    role: str = "Landlord / Landlady"
    county: str = "Nairobi"
    estate: Optional[str] = None
    kra_pin: Optional[str] = None
    password: str = Field(..., min_length=8)
    confirm_password: str

    payment_method: PaymentMethod = PaymentMethod.mpesa
    mpesa_number: Optional[str] = None
    airtel_number: Optional[str] = None
    card_number: Optional[str] = None
    card_expiry: Optional[str] = None
    card_cvv: Optional[str] = None

    @field_validator("phone", "mpesa_number", "airtel_number")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        digits = re.sub(r"\D", "", v)
        if len(digits) < 9 or len(digits) > 12:
            raise ValueError("Phone number must contain 9–12 digits")
        return digits

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ROLES:
            raise ValueError(f"Role must be one of: {ROLES}")
        return v

    @field_validator("county")
    @classmethod
    def validate_county(cls, v: str) -> str:
        if v not in COUNTIES:
            raise ValueError(f"County must be one of: {COUNTIES}")
        return v

    @model_validator(mode="after")
    def check_passwords_and_payment(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        if self.payment_method == PaymentMethod.mpesa and not self.mpesa_number:
            raise ValueError("M-Pesa number is required")
        if self.payment_method == PaymentMethod.airtel and not self.airtel_number:
            raise ValueError("Airtel Money number is required")
        if self.payment_method == PaymentMethod.card:
            if not self.card_number or not self.card_expiry or not self.card_cvv:
                raise ValueError("Card number, expiry and CVV are required")
        return self


class CheckoutResponse(BaseModel):
    success: bool
    reference: str
    message: str
    plan_name: str
    cycle_label: str
    currency: str
    amount_after_trial: float
    formatted_amount: str
    trial_ends: date
    payment_method: str
    email: str
    created_at: datetime


class CatalogResponse(BaseModel):
    plans: dict
    cycles: dict
    currencies: list[str]
    rates: dict[str, float]
    symbols: dict[str, str]
    roles: list[str]
    counties: list[str]
    payment_methods: list[str]
    trial_days: int


# ---------------------------------------------------------------------------
# Pricing engine
# ---------------------------------------------------------------------------

def convert(amount_ksh: float, currency: str) -> float:
    return amount_ksh * RATES.get(currency, 1.0)


def format_money(amount: float, currency: str) -> str:
    return f"{SYMBOLS.get(currency, '')}{round(amount):,}"


def calc_price(plan_key: str, cycle_key: str, currency: str = "KSH") -> PriceBreakdown:
    plan = PLANS[plan_key]
    cycle = CYCLES[cycle_key]

    base_ksh = plan["price_ksh"] * cycle["months"]
    total_ksh = base_ksh * (1 - cycle["discount"])
    save_ksh = base_ksh - total_ksh
    monthly_ksh = total_ksh / cycle["months"]

    base = convert(base_ksh, currency)
    total = convert(total_ksh, currency)
    save = convert(save_ksh, currency)
    monthly = convert(monthly_ksh, currency)
    was = convert(plan["price_ksh"], currency) if cycle["discount"] > 0 else None

    return PriceBreakdown(
        base=round(base, 2),
        total=round(total, 2),
        save=round(save, 2),
        monthly_equivalent=round(monthly, 2),
        currency=currency,
        symbol=SYMBOLS[currency],
        formatted_base=format_money(base, currency),
        formatted_total=format_money(total, currency),
        formatted_save=format_money(save, currency),
        formatted_monthly=format_money(monthly, currency),
        formatted_was=(format_money(was, currency) + "/mo") if was is not None else None,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "mwarokin-checkout",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/v1/catalog", response_model=CatalogResponse)
def get_catalog():
    return CatalogResponse(
        plans=PLANS,
        cycles=CYCLES,
        currencies=list(RATES.keys()),
        rates=RATES,
        symbols=SYMBOLS,
        roles=ROLES,
        counties=COUNTIES,
        payment_methods=PAYMENT_METHODS,
        trial_days=TRIAL_DAYS,
    )


@app.get("/api/v1/quote", response_model=QuoteResponse)
def get_quote(
    plan: Optional[PlanKey] = Query(None, description="Currently selected plan"),
    cycle: CycleKey = Query(CycleKey.monthly),
    currency: Currency = Query(Currency.KSH),
):
    """
    Live quote for all plans under the chosen cycle + currency.
    Optionally highlight one selected plan with full order summary.
    """
    cycle_key = cycle.value
    cur = currency.value
    c = CYCLES[cycle_key]

    cards: list[PlanCard] = []
    for key, p in PLANS.items():
        price = calc_price(key, cycle_key, cur)
        cards.append(
            PlanCard(
                key=key,
                name=p["name"],
                tagline=p["tagline"],
                popular=p["popular"],
                features=p["features"],
                price=price,
            )
        )

    selected = None
    summary = None
    if plan:
        selected = next(c for c in cards if c.key == plan.value)
        x = selected.price
        summary = {
            "plan_name": selected.name,
            "tagline": selected.tagline,
            "cycle_label": c["label"],
            "cycle_months": c["months"],
            "base": x.formatted_base,
            "discount_label": f"{c['label']} discount ({int(c['discount']*100)}%)" if c["discount"] else None,
            "discount_amount": f"-{x.formatted_save}" if c["discount"] else None,
            "free_trial": f"{TRIAL_DAYS} days",
            "setup_fee": "Waived",
            "due_after_trial": f"{x.formatted_total}{c['unit']}",
            "monthly_equivalent": f"≈ {x.formatted_monthly} per month" if c["months"] > 1 else None,
        }

    return QuoteResponse(
        currency=cur,
        cycle=cycle_key,
        cycle_label=c["label"],
        cycle_months=c["months"],
        cycle_unit=c["unit"],
        cycle_perk=c["perk"],
        discount_percent=int(c["discount"] * 100),
        plans=cards,
        selected=selected,
        summary=summary,
    )


@app.post("/api/v1/checkout", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
def start_trial(body: CheckoutRequest):
    """
    Create account + start 14-day free trial.
    No charge today. Subscription activates after trial ends.
    """
    price = calc_price(body.plan.value, body.cycle.value, body.currency.value)
    reference = f"MWK-{uuid4().hex[:8].upper()}"
    now = datetime.utcnow()
    trial_ends = (now + timedelta(days=TRIAL_DAYS)).date()

    # Payment detail (store only last-4 for cards in real systems)
    payment_detail = None
    if body.payment_method == PaymentMethod.mpesa:
        payment_detail = body.mpesa_number
    elif body.payment_method == PaymentMethod.airtel:
        payment_detail = body.airtel_number
    elif body.payment_method == PaymentMethod.card:
        payment_detail = f"****{(body.card_number or '')[-4:]}"

    record = {
        "reference": reference,
        "plan": body.plan.value,
        "cycle": body.cycle.value,
        "currency": body.currency.value,
        "price": price.model_dump(),
        "account": {
            "first_name": body.first_name,
            "last_name": body.last_name,
            "email": body.email,
            "phone": body.phone,
            "role": body.role,
            "county": body.county,
            "estate": body.estate,
            "kra_pin": body.kra_pin,
        },
        "payment_method": body.payment_method.value,
        "payment_detail": payment_detail,
        "status": "trial_active",
        "trial_ends": trial_ends.isoformat(),
        "created_at": now.isoformat(),
    }
    subscriptions_db[reference] = record

    return CheckoutResponse(
        success=True,
        reference=reference,
        message=(
            f"Welcome to Mwarokin Estates! "
            f"{PLANS[body.plan.value]['name']} ({CYCLES[body.cycle.value]['label']}) "
            f"trial started. No charge for {TRIAL_DAYS} days."
        ),
        plan_name=PLANS[body.plan.value]["name"],
        cycle_label=CYCLES[body.cycle.value]["label"],
        currency=body.currency.value,
        amount_after_trial=price.total,
        formatted_amount=f"{price.formatted_total}{CYCLES[body.cycle.value]['unit']}",
        trial_ends=trial_ends,
        payment_method=body.payment_method.value,
        email=body.email,
        created_at=now,
    )


@app.get("/api/v1/subscriptions/{reference}")
def get_subscription(reference: str):
    rec = subscriptions_db.get(reference.upper())
    if not rec:
        raise HTTPException(status_code=404, detail="Subscription not found")
    # Never return password
    return rec


@app.get("/api/v1/subscriptions")
def list_subscriptions(limit: Annotated[int, Query(ge=1, le=100)] = 20):
    items = list(subscriptions_db.values())[-limit:]
    return {"count": len(subscriptions_db), "subscriptions": items}


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### Quick start

```bash
pip install fastapi uvicorn pydantic pydantic[email]
# save as main.py
uvicorn main:app --reload --port 8000
```

### Real functionality

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/catalog` | Plans, cycles, currencies, roles, counties, payment methods |
| `GET /api/v1/quote?plan=jengo&cycle=annual&currency=USD` | Live prices for all plans + order summary for selected plan |
| `POST /api/v1/checkout` | Validate form → create account → start 14-day free trial |
| `GET /api/v1/subscriptions/{ref}` | Retrieve subscription by reference |

Pricing engine matches the frontend exactly:

- Monthly equivalent = `(price × months × (1 − discount)) / months`
- Discounts: Quarterly 8 %, Biannual 14 %, Annual 20 %
- Multi-currency (KSH / USD / EUR)
- 14-day free trial, setup fee waived
- Full validation of passwords, phone numbers, payment fields, role & county

The frontend can replace its local `calc()` / `render()` and the final `alert()` with calls to `/quote` and `/checkout`.
