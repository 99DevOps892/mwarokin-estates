Here’s a complete, modern **FastAPI backend** that powers the Mwarokin Estates Subscription Plans page with live multi-currency pricing, cycle discounts, and plan comparison.

```python
"""
Mwarokin Estates – Subscription Plans
Backend API (FastAPI + Pydantic v2)
Python 3.11+
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mwarokin Estates – Subscription Plans API",
    description="Plan catalogue, multi-currency pricing, billing-cycle discounts & comparison",
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
# Domain data (single source of truth)
# ---------------------------------------------------------------------------

PLANS = {
    "msingi": {
        "name": "Msingi",
        "swahili": "Foundation · Msingi wa Nyumba",
        "price_ksh": 2500,
        "popular": False,
        "description": "For individual landlords. Manage up to 10 units with core tools.",
        "modules_heading": "Key Modules",
        "modules": [
            "🏠 Rent Dashboard",
            "👤 Tenant Profiles",
            "📅 Schedule Viewing",
            "💧 Water Billing",
            "🗑️ Trash Billing",
            "🧾 KRA Basic",
            "💰 Lipa Mdogo",
            "📱 Mobile App",
        ],
        "limits": {
            "Residential Units": "10",
            "Landlord Accounts": "1",
            "Caretakers": "1",
            "Storage": "5 GB",
        },
        "cta": "Get Started",
    },
    "jengo": {
        "name": "Jengo",
        "swahili": "Building · Jengo Imara",
        "price_ksh": 6500,
        "popular": True,
        "description": "For property managers. 50 units, Lipa Mdogo, caretaker portal.",
        "modules_heading": "Included Modules",
        "modules": [
            "📊 Financial Dashboard",
            "💰 Advanced Lipa Mdogo",
            "🔑 Caretaker Portal",
            "🔧 Renovations",
            "🗺️ My Neighbourhood",
            "👵 Elderly Mode",
            "🧾 KRA Advanced",
            "📝 Lease Mgmt",
        ],
        "limits": {
            "Residential Units": "50",
            "Landlord Accounts": "3",
            "Caretakers": "5",
            "Storage": "25 GB",
        },
        "cta": "Start Free Trial",
    },
    "milki": {
        "name": "Milki",
        "swahili": "Estate · Milki ya Ardhi",
        "price_ksh": 15000,
        "popular": False,
        "description": "Large estates & property companies. 250 units, security & portfolio.",
        "modules_heading": "All Jengo + more",
        "modules": [
            "🏘️ Residential Zones",
            "🔒 Security Mgmt",
            "💬 Communication Centre",
            "🎨 Design Tools",
            "💳 Long-term Lipa",
            "📄 KRA Reports",
            "📞 Phone Support",
        ],
        "limits": {
            "Residential Units": "250",
            "Landlord Accounts": "10",
            "Caretakers": "∞",
            "Storage": "100 GB",
        },
        "cta": "Get Started",
    },
    "taifa": {
        "name": "Taifa",
        "swahili": "Enterprise · Taifa Kamili",
        "price_ksh": 45000,
        "popular": False,
        "description": "Enterprise-grade. Unlimited units, white-label, API, SLA, dedicated manager.",
        "modules_heading": "All Milki +",
        "modules": [
            "🌟 White Label",
            "🔗 API Access",
            "🏦 Multi-currency",
            "📋 Custom Reports",
            "⚖️ SLA Guarantee",
            "🎓 On-site Training",
        ],
        "limits": {
            "Residential Units": "∞",
            "Landlord Accounts": "∞",
            "Caretakers": "∞",
            "Storage": "1 TB+",
        },
        "cta": "Contact Sales",
    },
}

CYCLES = {
    "monthly": {
        "label": "Monthly",
        "months": 1,
        "discount": 0.00,
        "unit": "/month",
        "billed": "Every month",
        "perk": "<b>Maximum flexibility</b> — pay month to month and cancel anytime.",
        "perk_short": "Cancel anytime",
        "badge": "Flexible",
    },
    "quarterly": {
        "label": "Quarterly",
        "months": 3,
        "discount": 0.08,
        "unit": "every 3 months",
        "billed": "Every 3 months",
        "perk": "<b>Save 8%</b> — billed every 3 months, plus priority email support.",
        "perk_short": "Priority email support",
        "badge": "Save 8%",
    },
    "biannual": {
        "label": "Biannual",
        "months": 6,
        "discount": 0.14,
        "unit": "every 6 months",
        "billed": "Every 6 months",
        "perk": "<b>Save 14%</b> — billed every 6 months, plus a free onboarding call.",
        "perk_short": "Free onboarding call",
        "badge": "Save 14%",
    },
    "annual": {
        "label": "Annual",
        "months": 12,
        "discount": 0.20,
        "unit": "per year",
        "billed": "Every 12 months",
        "perk": "<b>Best value, save 20%</b> — billed yearly, plus free staff training & priority support.",
        "perk_short": "Free training + priority support",
        "badge": "Save 20%",
    },
}

# Exchange rates relative to KSH (update from a real FX service in production)
RATES = {
    "KSH": 1.0,
    "USD": 0.0077,
    "EUR": 0.0071,
}

SYMBOLS = {
    "KSH": "KSH ",
    "USD": "$",
    "EUR": "€",
}

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


class PriceBreakdown(BaseModel):
    base: float          # full price before discount (for the cycle period)
    total: float         # after discount
    save: float          # amount saved
    monthly_equivalent: float
    currency: str
    symbol: str
    formatted_monthly: str
    formatted_total: str
    formatted_save: str
    formatted_was: Optional[str] = None  # strikethrough monthly price when discounted


class PlanCard(BaseModel):
    key: str
    name: str
    swahili: str
    popular: bool
    description: str
    modules_heading: str
    modules: list[str]
    limits: dict[str, str]
    cta: str
    price: PriceBreakdown
    checkout_url: str


class CycleInfo(BaseModel):
    key: str
    label: str
    months: int
    discount: float
    discount_percent: int
    unit: str
    billed: str
    perk: str
    perk_short: str
    badge: str


class ComparisonRow(BaseModel):
    cycle_key: str
    cycle_label: str
    billed: str
    discount_label: str
    total: float
    formatted_total: str
    perk_short: str
    is_active: bool


class PlansResponse(BaseModel):
    currency: str
    cycle: str
    cycle_info: CycleInfo
    plans: list[PlanCard]
    comparison: list[ComparisonRow]
    rates: dict[str, float]


class CatalogResponse(BaseModel):
    plans: dict
    cycles: dict
    currencies: list[str]
    rates: dict[str, float]
    symbols: dict[str, str]


class SelectPlanRequest(BaseModel):
    plan: PlanKey
    cycle: CycleKey = CycleKey.monthly
    currency: Currency = Currency.KSH


class SelectPlanResponse(BaseModel):
    success: bool
    plan: str
    cycle: str
    currency: str
    checkout_url: str
    price: PriceBreakdown
    message: str


# ---------------------------------------------------------------------------
# Pricing engine
# ---------------------------------------------------------------------------

def convert(amount_ksh: float, currency: str) -> float:
    rate = RATES.get(currency, 1.0)
    return amount_ksh * rate


def format_money(amount: float, currency: str) -> str:
    symbol = SYMBOLS.get(currency, "")
    return f"{symbol}{round(amount):,}"


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
        formatted_monthly=format_money(monthly, currency),
        formatted_total=format_money(total, currency),
        formatted_save=format_money(save, currency),
        formatted_was=format_money(was, currency) + "/mo" if was is not None else None,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "mwarokin-plans",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/v1/catalog", response_model=CatalogResponse)
def get_catalog():
    """Full static catalogue – useful for initial page load or offline caching."""
    return CatalogResponse(
        plans=PLANS,
        cycles=CYCLES,
        currencies=list(RATES.keys()),
        rates=RATES,
        symbols=SYMBOLS,
    )


@app.get("/api/v1/plans", response_model=PlansResponse)
def get_plans(
    cycle: CycleKey = Query(CycleKey.monthly, description="Billing cycle"),
    currency: Currency = Query(Currency.KSH, description="Display currency"),
):
    """
    Returns all plan cards with live pricing for the selected cycle + currency,
    plus the comparison table rows (focused on Jengo as in the UI).
    """
    cycle_key = cycle.value
    cur = currency.value
    cycle_data = CYCLES[cycle_key]

    cycle_info = CycleInfo(
        key=cycle_key,
        label=cycle_data["label"],
        months=cycle_data["months"],
        discount=cycle_data["discount"],
        discount_percent=int(cycle_data["discount"] * 100),
        unit=cycle_data["unit"],
        billed=cycle_data["billed"],
        perk=cycle_data["perk"],
        perk_short=cycle_data["perk_short"],
        badge=cycle_data["badge"],
    )

    cards: list[PlanCard] = []
    for key, p in PLANS.items():
        price = calc_price(key, cycle_key, cur)
        cards.append(
            PlanCard(
                key=key,
                name=p["name"],
                swahili=p["swahili"],
                popular=p["popular"],
                description=p["description"],
                modules_heading=p["modules_heading"],
                modules=p["modules"],
                limits=p["limits"],
                cta=p["cta"],
                price=price,
                checkout_url=f"checkout.html?plan={key}&billing={cycle_key}",
            )
        )

    # Comparison table – Jengo across all cycles (matches frontend)
    comparison: list[ComparisonRow] = []
    for ck, cv in CYCLES.items():
        x = calc_price("jengo", ck, cur)
        comparison.append(
            ComparisonRow(
                cycle_key=ck,
                cycle_label=cv["label"],
                billed=cv["billed"],
                discount_label=f"{int(cv['discount']*100)}% off" if cv["discount"] else "—",
                total=x.total,
                formatted_total=x.formatted_total,
                perk_short=cv["perk_short"],
                is_active=(ck == cycle_key),
            )
        )

    return PlansResponse(
        currency=cur,
        cycle=cycle_key,
        cycle_info=cycle_info,
        plans=cards,
        comparison=comparison,
        rates=RATES,
    )


@app.get("/api/v1/plans/{plan_key}")
def get_single_plan(
    plan_key: PlanKey,
    cycle: CycleKey = Query(CycleKey.monthly),
    currency: Currency = Query(Currency.KSH),
):
    """Detailed pricing for one plan."""
    if plan_key.value not in PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")

    p = PLANS[plan_key.value]
    price = calc_price(plan_key.value, cycle.value, currency.value)

    return {
        "key": plan_key.value,
        "name": p["name"],
        "swahili": p["swahili"],
        "popular": p["popular"],
        "description": p["description"],
        "modules": p["modules"],
        "limits": p["limits"],
        "cta": p["cta"],
        "price": price,
        "cycle": cycle.value,
        "checkout_url": f"checkout.html?plan={plan_key.value}&billing={cycle.value}",
    }


@app.get("/api/v1/compare")
def compare_cycles(
    plan: PlanKey = Query(PlanKey.jengo, description="Plan to compare across cycles"),
    currency: Currency = Query(Currency.KSH),
):
    """Full comparison of every billing cycle for a given plan."""
    rows = []
    for ck, cv in CYCLES.items():
        x = calc_price(plan.value, ck, currency.value)
        rows.append(
            {
                "cycle": ck,
                "label": cv["label"],
                "months": cv["months"],
                "discount_percent": int(cv["discount"] * 100),
                "billed": cv["billed"],
                "total": x.total,
                "monthly_equivalent": x.monthly_equivalent,
                "save": x.save,
                "formatted_total": x.formatted_total,
                "formatted_monthly": x.formatted_monthly,
                "formatted_save": x.formatted_save,
                "perk": cv["perk_short"],
            }
        )
    return {
        "plan": plan.value,
        "plan_name": PLANS[plan.value]["name"],
        "currency": currency.value,
        "rows": rows,
    }


@app.post("/api/v1/select", response_model=SelectPlanResponse)
def select_plan(body: SelectPlanRequest):
    """
    User clicks a CTA → validate selection and return the checkout URL
    plus the exact price that will be carried into the Configure step.
    """
    price = calc_price(body.plan.value, body.cycle.value, body.currency.value)
    url = f"checkout.html?plan={body.plan.value}&billing={body.cycle.value}&currency={body.currency.value}"

    return SelectPlanResponse(
        success=True,
        plan=body.plan.value,
        cycle=body.cycle.value,
        currency=body.currency.value,
        checkout_url=url,
        price=price,
        message=f"{PLANS[body.plan.value]['name']} ({CYCLES[body.cycle.value]['label']}) selected at {price.formatted_monthly}/mo",
    )


@app.get("/api/v1/rates")
def get_rates():
    """Current FX rates (KSH base). In production, refresh from a live provider."""
    return {
        "base": "KSH",
        "rates": RATES,
        "symbols": SYMBOLS,
        "updated_at": datetime.utcnow().isoformat(),
    }


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

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/catalog` | Full static catalogue (plans, cycles, currencies) |
| `GET /api/v1/plans?cycle=annual&currency=USD` | All plan cards with live discounted prices |
| `GET /api/v1/plans/{plan}` | Single plan detail + price |
| `GET /api/v1/compare?plan=jengo&currency=KSH` | Comparison table for any plan across all cycles |
| `POST /api/v1/select` | Validate selection → returns checkout URL + exact price |
| `GET /api/v1/rates` | Current FX rates |

Pricing engine mirrors the frontend exactly:

- Monthly equivalent = `(base_price × months × (1 − discount)) / months`
- Supports **KSH / USD / EUR**
- Discounts: Quarterly 8 %, Biannual 14 %, Annual 20 %
- “Most Popular” flag and all module/limit data preserved

The frontend can replace its local `calc()` / `render()` logic with a single call to `/api/v1/plans`.
