
"""
Mwarokin Estates · Live Payment Portal
Modern agentic Python implementation (Streamlit)
Fully functional multi-step payment flow with live FX simulation,
Lipa Mdogo partial payments, gateway fee locking, validation & receipt.
"""

import streamlit as st
import random
import hashlib
import time
from datetime import datetime
from copy import deepcopy
from typing import Dict, List, Optional, Tuple

# ─────────────────────────────────────────────
# Page config & custom CSS (premium dark-forest theme)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Mwarokin Estates · Payment Portal",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --forest-900: #0E211B;
  --forest-800: #1E4A3B;
  --forest-700: #2F6B4F;
  --brass: #C9A227;
  --cream: #FCF9F0;
  --ink: #241F17;
  --ink-400: #8C8271;
}

html, body, [class*="css"] {
  font-family: 'Inter', sans-serif;
  background: var(--forest-900) !important;
  color: var(--cream);
}

.stApp {
  background: linear-gradient(165deg, #0E211B 0%, #132A22 40%, #0E211B 100%);
}

h1, h2, h3 {
  font-family: 'Fraunces', serif !important;
  color: #FCF9F0 !important;
}

.brandmark {
  font-family: 'Fraunces', serif;
  font-size: 2.1rem;
  font-weight: 600;
  color: #FCF9F0;
  margin: 0;
}
.brandmark em { color: var(--brass); font-style: italic; }

.eyebrow {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--brass);
  margin-bottom: 0.15rem;
}

.portal-card {
  background: rgba(252,249,240,0.97);
  border-radius: 18px;
  padding: 1.8rem 2rem;
  box-shadow: 0 25px 50px -20px rgba(0,0,0,0.55);
  color: var(--ink);
  margin-top: 1rem;
}

.stepper {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.8rem;
  flex-wrap: wrap;
}
.step {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.45rem 0.9rem;
  border-radius: 999px;
  background: #EDE8DB;
  font-size: 0.82rem;
  font-weight: 500;
  color: #635A49;
}
.step.active {
  background: var(--forest-800);
  color: #FCF9F0;
}
.step.done {
  background: #D4E8DC;
  color: var(--forest-800);
}
.step .num {
  width: 1.4rem; height: 1.4rem;
  border-radius: 50%;
  background: rgba(0,0,0,0.08);
  display: flex; align-items: center; justify-content: center;
  font-size: 0.75rem; font-weight: 600;
}
.step.active .num { background: rgba(255,255,255,0.2); }

.summary-box {
  background: #F5F1E6;
  border: 1px solid rgba(36,31,23,0.1);
  border-radius: 12px;
  padding: 1rem 1.2rem;
  margin: 1.2rem 0;
}
.summary-line {
  display: flex;
  justify-content: space-between;
  padding: 0.35rem 0;
  font-size: 0.92rem;
}
.summary-line.total {
  border-top: 1px solid rgba(36,31,23,0.12);
  margin-top: 0.4rem;
  padding-top: 0.6rem;
  font-weight: 600;
  font-size: 1.05rem;
  color: var(--forest-800);
}

.gw-card {
  border: 1.5px solid #E0D9C8;
  border-radius: 12px;
  padding: 1rem;
  cursor: pointer;
  transition: all 0.15s;
  background: #FFFEF9;
}
.gw-card:hover { border-color: var(--forest-700); }
.gw-card.selected {
  border-color: var(--forest-800);
  background: #E8F2EC;
  box-shadow: 0 0 0 2px rgba(30,74,59,0.25);
}
.gw-name { font-weight: 600; color: var(--ink); }
.gw-fee { font-size: 0.82rem; color: var(--ink-400); margin-top: 0.2rem; }
.gw-tag { font-size: 0.75rem; color: var(--forest-700); margin-top: 0.35rem; }

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.8rem;
  border-radius: 999px;
  background: rgba(47,107,79,0.15);
  font-size: 0.78rem;
  color: #A8D5C0;
}
.status-chip.locked {
  background: rgba(201,162,39,0.2);
  color: #EFDCA0;
}
.dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: #3ECF8E;
  animation: pulse 1.6s infinite;
}
.status-chip.locked .dot { background: var(--brass); animation: none; }

@keyframes pulse {
  0%,100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.receipt-card {
  background: #FCF9F0;
  border-radius: 6px 18px 18px 18px;
  padding: 2rem;
  color: var(--ink);
  box-shadow: 0 30px 60px -20px rgba(0,0,0,0.5);
}
.amount-value {
  font-family: 'Fraunces', serif;
  font-size: 2.4rem;
  font-weight: 600;
  color: var(--forest-800);
  margin: 0.3rem 0;
}
.mono { font-family: 'JetBrains Mono', monospace; font-size: 0.88rem; }

.stButton > button {
  border-radius: 10px !important;
  font-weight: 600 !important;
  padding: 0.55rem 1.3rem !important;
}
.stButton > button[kind="primary"] {
  background: var(--forest-800) !important;
  border: none !important;
}
.stButton > button[kind="secondary"] {
  background: transparent !important;
  border: 1.5px solid #C9BFA8 !important;
  color: var(--ink) !important;
}

div[data-testid="stMetric"] {
  background: #F5F1E6;
  border-radius: 10px;
  padding: 0.6rem 0.9rem;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Seeded PRNG (deterministic bills per tenant+month)
# ─────────────────────────────────────────────
def hash_seed(s: str) -> int:
    return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)

def seeded_random(seed: int):
    s = seed
    def rng():
        nonlocal s
        s = (s * 1664525 + 1013904223) & 0xFFFFFFFF
        return s / 4294967296
    return rng

def rand_range(rng, lo: float, hi: float) -> float:
    return lo + rng() * (hi - lo)

# ─────────────────────────────────────────────
# Static data
# ─────────────────────────────────────────────
TENANTS = [
    {"id": "t1", "name": "Amina Otieno", "unit": "4B", "type": "Premium Suite", "rent_kes": 85000, "has_parking": True},
    {"id": "t2", "name": "Brian Mutiso", "unit": "2A", "type": "Standard 2-Bed", "rent_kes": 62000, "has_parking": False},
    {"id": "t3", "name": "Grace Wanjiru", "unit": "7C", "type": "Executive Loft", "rent_kes": 120000, "has_parking": True},
    {"id": "t4", "name": "Daniel Kiptoo", "unit": "1F", "type": "Studio", "rent_kes": 41000, "has_parking": False},
]
MONTHS = ["July 2026", "August 2026", "September 2026", "June 2026", "May 2026"]

CURRENCY_SYMBOL = {"KES": "KES", "USD": "$", "GBP": "£", "CNY": "¥"}

GATEWAYS = [
    {"id": "mpesa", "name": "M-Pesa", "tag": "Instant STK Push", "fee_type": "pct"},
    {"id": "airtel", "name": "Airtel Money", "tag": "Instant mobile money", "fee_type": "pct"},
    {"id": "syllopay", "name": "SylloPay", "tag": "STA payment rail", "fee_type": "pct"},
    {"id": "bank", "name": "Bank Transfer", "tag": "Per-bank current rate", "fee_type": "bank"},
    {"id": "card", "name": "Visa / Mastercard", "tag": "Card network", "fee_type": "card"},
    {"id": "crypto", "name": "Crypto (BTC / USDT)", "tag": "Blockchain settlement", "fee_type": "crypto"},
]

# ─────────────────────────────────────────────
# Session state initialisation
# ─────────────────────────────────────────────
def init_state():
    defaults = {
        "step": 1,
        "currency": "KES",
        "tenant_id": TENANTS[0]["id"],
        "month": MONTHS[0],
        "selected_bills": set(),
        "partial_amounts": {},          # bill_id → amount in current currency units
        "selected_gateway": None,
        "selected_bank": None,
        "selected_crypto": None,
        "locked_rates": None,
        "form_data": {},
        "receipt": None,
        "rates": {
            "fx": {"USD": 129.10, "GBP": 165.40, "CNY": 17.85},
            "mpesa_fee_pct": 1.55,
            "airtel_fee_pct": 1.45,
            "mwarokin_fee_kes": 3,
            "service_fee_pct": 0.52,
            "banks": {"KCB": 250, "Equity Bank": 215, "Co-operative Bank": 230, "Absa Bank": 245},
            "crypto": {"BTC_KES": 11_284_500, "USDT_KES": 129.35},
            "crypto_fee_pct": 0.85,
            "card_fee_pct": 2.90,
            "card_flat_kes": 30,
            "syllopay_fee_pct": 1.00,
        },
        "last_rates": None,
        "last_tick": time.time(),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if st.session_state.last_rates is None:
        st.session_state.last_rates = deepcopy(st.session_state.rates)

init_state()

# ─────────────────────────────────────────────
# Rate helpers
# ─────────────────────────────────────────────
def active_rates() -> dict:
    return st.session_state.locked_rates or st.session_state.rates

def to_currency(amount_kes: float, ccy: Optional[str] = None) -> float:
    ccy = ccy or st.session_state.currency
    if ccy == "KES":
        return amount_kes
    return amount_kes / active_rates()["fx"][ccy]

def fmt(amount_kes: float, ccy: Optional[str] = None) -> str:
    ccy = ccy or st.session_state.currency
    val = to_currency(amount_kes, ccy)
    decimals = 0 if ccy == "KES" else 2
    return f"{CURRENCY_SYMBOL[ccy]} {val:,.{decimals}f}"

def fmt_kes_raw(amount_kes: float) -> str:
    return f"KES {round(amount_kes):,}"

def tick_rates():
    """Simulate live rate drift every ~4 s while not locked."""
    if st.session_state.locked_rates is not None:
        return
    now = time.time()
    if now - st.session_state.last_tick < 4.0:
        return
    st.session_state.last_tick = now
    st.session_state.last_rates = deepcopy(st.session_state.rates)
    r = st.session_state.rates
    r["fx"]["USD"] = round(r["fx"]["USD"] + (random.random() - 0.5) * 0.4, 2)
    r["fx"]["GBP"] = round(r["fx"]["GBP"] + (random.random() - 0.5) * 0.5, 2)
    r["fx"]["CNY"] = round(r["fx"]["CNY"] + (random.random() - 0.5) * 0.1, 2)
    r["mpesa_fee_pct"] = round(max(1.2, r["mpesa_fee_pct"] + (random.random() - 0.5) * 0.08), 2)
    r["airtel_fee_pct"] = round(max(1.1, r["airtel_fee_pct"] + (random.random() - 0.5) * 0.08), 2)
    r["service_fee_pct"] = round(max(0.2, r["service_fee_pct"] + (random.random() - 0.5) * 0.04), 2)
    r["mwarokin_fee_kes"] = max(1, min(5, round(r["mwarokin_fee_kes"] + (random.random() - 0.5) * 1.4)))
    r["crypto_fee_pct"] = round(max(0.4, r["crypto_fee_pct"] + (random.random() - 0.5) * 0.06), 2)
    r["crypto"]["BTC_KES"] = round(r["crypto"]["BTC_KES"] + (random.random() - 0.5) * 32000)
    r["crypto"]["USDT_KES"] = round(r["crypto"]["USDT_KES"] + (random.random() - 0.5) * 0.3, 2)
    for b in r["banks"]:
        r["banks"][b] = max(150, round(r["banks"][b] + (random.random() - 0.5) * 10))

# ─────────────────────────────────────────────
# Bills generation
# ─────────────────────────────────────────────
def generate_bills(tenant: dict, month: str) -> List[dict]:
    rng = seeded_random(hash_seed(tenant["id"] + month))
    bills = [
        {"id": "rent", "label": "Monthly Rent", "icon": "🏠", "amount": tenant["rent_kes"], "due": "1st of month"},
        {"id": "water", "label": "Water", "icon": "💧", "amount": round(rand_range(rng, 800, 2200)), "due": "5th of month"},
        {"id": "electricity", "label": "Electricity (KPLC token estimate)", "icon": "⚡", "amount": round(rand_range(rng, 2000, 6500)), "due": "5th of month"},
        {"id": "garbage", "label": "Waste Collection", "icon": "🗑️", "amount": 500, "due": "10th of month"},
        {"id": "security", "label": "Security & Estate Guard", "icon": "🛡️", "amount": 1500, "due": "1st of month"},
        {"id": "wifi", "label": "Fibre WiFi (Estate Bundle)", "icon": "📶", "amount": 2500, "due": "8th of month"},
        {"id": "amenities", "label": "Amenities (Gym, Pool, Clubhouse)", "icon": "⭐", "amount": 1800, "due": "1st of month"},
    ]
    if tenant["has_parking"]:
        bills.insert(4, {"id": "parking", "label": "Parking Bay", "icon": "🚗", "amount": 1000, "due": "1st of month"})
    return bills

def selected_subtotal_kes() -> float:
    tenant = next(t for t in TENANTS if t["id"] == st.session_state.tenant_id)
    bills = generate_bills(tenant, st.session_state.month)
    total = 0.0
    ccy = st.session_state.currency
    rates = active_rates()
    for b in bills:
        if b["id"] not in st.session_state.selected_bills:
            continue
        partial = st.session_state.partial_amounts.get(b["id"])
        if partial is not None and partial > 0:
            # partial is entered in current currency units → convert to KES
            if ccy == "KES":
                total += partial
            else:
                total += partial * rates["fx"][ccy]
        else:
            total += b["amount"]
    return total

# ─────────────────────────────────────────────
# Fee engine
# ─────────────────────────────────────────────
def compute_fee_kes(subtotal_kes: float) -> float:
    r = active_rates()
    gw = next(g for g in GATEWAYS if g["id"] == st.session_state.selected_gateway)
    fee = 0.0
    if gw["fee_type"] == "pct":
        pct = {
            "mpesa": r["mpesa_fee_pct"],
            "airtel": r["airtel_fee_pct"],
            "syllopay": r["syllopay_fee_pct"],
        }[gw["id"]]
        fee = subtotal_kes * (pct / 100) + r["mwarokin_fee_kes"]
    elif gw["fee_type"] == "bank":
        fee = r["banks"][st.session_state.selected_bank] + r["mwarokin_fee_kes"]
    elif gw["fee_type"] == "card":
        fee = subtotal_kes * (r["card_fee_pct"] / 100) + r["card_flat_kes"] + r["mwarokin_fee_kes"]
    elif gw["fee_type"] == "crypto":
        fee = subtotal_kes * (r["crypto_fee_pct"] / 100) + r["mwarokin_fee_kes"]
    fee += subtotal_kes * (r["service_fee_pct"] / 100)
    return fee

def fee_breakdown_lines(subtotal_kes: float) -> List[Tuple[str, float]]:
    r = active_rates()
    gw = next(g for g in GATEWAYS if g["id"] == st.session_state.selected_gateway)
    lines = []
    if gw["fee_type"] == "pct":
        pct = {"mpesa": r["mpesa_fee_pct"], "airtel": r["airtel_fee_pct"], "syllopay": r["syllopay_fee_pct"]}[gw["id"]]
        lines.append((f"{gw['name']} fee ({pct:.2f}%)", subtotal_kes * (pct / 100)))
    elif gw["fee_type"] == "bank":
        lines.append((f"{st.session_state.selected_bank} transfer fee", r["banks"][st.session_state.selected_bank]))
    elif gw["fee_type"] == "card":
        lines.append((f"Card network fee ({r['card_fee_pct']:.2f}%)", subtotal_kes * (r["card_fee_pct"] / 100)))
        lines.append(("Card flat fee", r["card_flat_kes"]))
    elif gw["fee_type"] == "crypto":
        lines.append((f"{st.session_state.selected_crypto} network fee ({r['crypto_fee_pct']:.2f}%)",
                      subtotal_kes * (r["crypto_fee_pct"] / 100)))
    lines.append(("Mwarokin service fee (Ksh 1–5)", r["mwarokin_fee_kes"]))
    lines.append((f"Platform service fee ({r['service_fee_pct']:.2f}%)",
                  subtotal_kes * (r["service_fee_pct"] / 100)))
    return lines

def gw_fee_label(gw: dict) -> str:
    r = active_rates()
    if gw["fee_type"] == "pct":
        pct = {"mpesa": r["mpesa_fee_pct"], "airtel": r["airtel_fee_pct"], "syllopay": r["syllopay_fee_pct"]}[gw["id"]]
        return f"{pct:.2f}% + Ksh{r['mwarokin_fee_kes']} Mwarokin fee"
    if gw["fee_type"] == "bank":
        return f"From Ksh{min(r['banks'].values())} flat"
    if gw["fee_type"] == "card":
        return f"{r['card_fee_pct']:.2f}% + Ksh{r['card_flat_kes']}"
    if gw["fee_type"] == "crypto":
        return f"{r['crypto_fee_pct']:.2f}% network fee"
    return ""

# ─────────────────────────────────────────────
# Validation helpers
# ─────────────────────────────────────────────
def validate_phone(v: str) -> bool:
    return bool(__import__("re").match(r"^(?:\+254|0)7\d{8}$", v.strip()))

def validate_syllo(v: str) -> bool:
    import re
    return bool(re.match(r"^SP-[A-Za-z0-9]{4,}$", v.strip()) or re.match(r"^(?:\+254|0)7\d{8}$", v.strip()))

def validate_acct(v: str) -> bool:
    return bool(__import__("re").match(r"^\d{8,16}$", v.strip()))

def validate_card(v: str) -> bool:
    return bool(__import__("re").match(r"^\d{4}\s?\d{4}\s?\d{4}\s?\d{4}$", v.strip()))

def validate_exp(v: str) -> bool:
    import re
    m = re.match(r"^(\d{2})/(\d{2})$", v.strip())
    if not m:
        return False
    mo, yr = int(m.group(1)), 2000 + int(m.group(2))
    if mo < 1 or mo > 12:
        return False
    from datetime import date
    exp = date(yr, mo, 1)
    return exp >= date.today().replace(day=1)

def validate_cvv(v: str) -> bool:
    return bool(__import__("re").match(r"^\d{3,4}$", v.strip()))

def validate_wallet(v: str) -> bool:
    return len(v.strip()) >= 26

# ─────────────────────────────────────────────
# Receipt generation
# ─────────────────────────────────────────────
def generate_txn_id() -> str:
    chars = "ABCDEF0123456789"
    return "TXN-MWK-" + "".join(random.choice(chars) for _ in range(8))

def build_receipt() -> dict:
    tenant = next(t for t in TENANTS if t["id"] == st.session_state.tenant_id)
    bills = generate_bills(tenant, st.session_state.month)
    bill_names = ", ".join(b["label"] for b in bills if b["id"] in st.session_state.selected_bills)
    sub = selected_subtotal_kes()
    fee = compute_fee_kes(sub)
    gw = next(g for g in GATEWAYS if g["id"] == st.session_state.selected_gateway)
    method = gw["name"]
    if st.session_state.selected_bank:
        method += f" — {st.session_state.selected_bank}"
    if st.session_state.selected_crypto:
        method += f" — {st.session_state.selected_crypto}"

    contact = "—"
    fd = st.session_state.form_data
    if gw["id"] in ("mpesa", "airtel"):
        contact = fd.get("phone", "—")
    elif gw["id"] == "syllopay":
        contact = fd.get("syllo", "—")
    elif gw["id"] == "bank":
        contact = fd.get("acct", "—")
    elif gw["id"] == "card":
        card = fd.get("card", "")
        contact = f"•••• {card.replace(' ', '')[-4:]}" if card else "—"
    elif gw["id"] == "crypto":
        w = fd.get("wallet", "")
        contact = f"{w[:6]}…{w[-4:]}" if w else "—"

    return {
        "tenant": f"{tenant['name']} · Unit {tenant['unit']}",
        "bills": bill_names,
        "month": st.session_state.month,
        "method": method,
        "contact": contact,
        "txn": generate_txn_id(),
        "subtotal": sub,
        "fee": fee,
        "total": sub + fee,
        "currency": st.session_state.currency,
        "date": datetime.now().strftime("%B %d, %Y · %H:%M") + " EAT",
        "fee_lines": fee_breakdown_lines(sub),
    }

# ─────────────────────────────────────────────
# UI – Header + Ticker
# ─────────────────────────────────────────────
tick_rates()

col_brand, col_ctrl = st.columns([3, 2])
with col_brand:
    st.markdown('<p class="eyebrow">Mwarokin Estates · Live Payment Portal</p>', unsafe_allow_html=True)
    st.markdown('<h1 class="brandmark">Mwarokin <em>Estates</em></h1>', unsafe_allow_html=True)

with col_ctrl:
    c1, c2 = st.columns([1.4, 1])
    with c1:
        new_ccy = st.selectbox(
            "Currency",
            options=["KES", "USD", "GBP", "CNY"],
            index=["KES", "USD", "GBP", "CNY"].index(st.session_state.currency),
            label_visibility="collapsed",
            key="ccy_select",
        )
        if new_ccy != st.session_state.currency:
            st.session_state.currency = new_ccy
            st.rerun()
    with c2:
        locked = st.session_state.locked_rates is not None
        chip_cls = "status-chip locked" if locked else "status-chip"
        label = "Checkout rate locked" if locked else "Live rates streaming"
        st.markdown(f'<div class="{chip_cls}"><span class="dot"></span> {label}</div>', unsafe_allow_html=True)

# Live ticker strip
r = st.session_state.rates
lr = st.session_state.last_rates
ticker_items = [
    f"USD/KES {r['fx']['USD']:.2f}",
    f"GBP/KES {r['fx']['GBP']:.2f}",
    f"CNY/KES {r['fx']['CNY']:.2f}",
    f"M-PESA {r['mpesa_fee_pct']:.2f}%",
    f"AIRTEL {r['airtel_fee_pct']:.2f}%",
    f"MWAROKIN Ksh{r['mwarokin_fee_kes']}",
    f"BTC {r['crypto']['BTC_KES']:,}",
    f"USDT {r['crypto']['USDT_KES']:.2f}",
]
st.markdown(
    f"""
    <div style="background:rgba(30,74,59,0.35);border-radius:8px;padding:0.45rem 1rem;
                overflow:hidden;white-space:nowrap;margin:0.6rem 0 0.2rem;
                font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:#A8D5C0;">
      {'  ·  '.join(ticker_items)}
    </div>
    <p style="font-size:0.72rem;color:#8C8271;margin:0 0 1rem;">
      Rates refresh every 4s · illustrative live feed, not financial advice · 
      Last tick {datetime.now().strftime('%H:%M:%S')} EAT
    </p>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# Stepper
# ─────────────────────────────────────────────
if st.session_state.receipt is None:
    steps = ["1 · Review bills", "2 · Payment method", "3 · Enter details", "4 · Confirm & pay"]
    step_html = '<div class="stepper">'
    for i, label in enumerate(steps, 1):
        cls = "step"
        if i == st.session_state.step:
            cls += " active"
        elif i < st.session_state.step:
            cls += " done"
        step_html += f'<div class="{cls}"><span class="num">{i}</span><span class="lbl">{label.split(" · ")[1]}</span></div>'
    step_html += "</div>"
    st.markdown(step_html, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# STEP 1 – Review bills
# ─────────────────────────────────────────────
if st.session_state.step == 1 and st.session_state.receipt is None:
    st.markdown('<div class="portal-card">', unsafe_allow_html=True)
    st.subheader("Manage bills & payments")
    st.caption("Select tenant and billing month to generate this period's charges, tick what you'd like to pay now.")

    c1, c2 = st.columns(2)
    with c1:
        tenant_opts = {f"{t['name']} — Unit {t['unit']} ({t['type']})": t["id"] for t in TENANTS}
        sel = st.selectbox("Tenant / unit", list(tenant_opts.keys()),
                           index=list(tenant_opts.values()).index(st.session_state.tenant_id))
        new_tid = tenant_opts[sel]
        if new_tid != st.session_state.tenant_id:
            st.session_state.tenant_id = new_tid
            st.session_state.selected_bills = set()
            st.session_state.partial_amounts = {}
            st.rerun()
    with c2:
        new_m = st.selectbox("Billing month", MONTHS, index=MONTHS.index(st.session_state.month))
        if new_m != st.session_state.month:
            st.session_state.month = new_m
            st.session_state.selected_bills = set()
            st.session_state.partial_amounts = {}
            st.rerun()

    tenant = next(t for t in TENANTS if t["id"] == st.session_state.tenant_id)
    bills = generate_bills(tenant, st.session_state.month)

    st.markdown("#### Bills for this period")
    for b in bills:
        cols = st.columns([0.08, 0.08, 0.42, 0.22, 0.2])
        with cols[0]:
            checked = st.checkbox("", value=b["id"] in st.session_state.selected_bills,
                                  key=f"chk_{b['id']}", label_visibility="collapsed")
            if checked:
                st.session_state.selected_bills.add(b["id"])
            else:
                st.session_state.selected_bills.discard(b["id"])
                st.session_state.partial_amounts.pop(b["id"], None)
        with cols[1]:
            st.markdown(f"<div style='font-size:1.4rem;padding-top:0.3rem'>{b['icon']}</div>", unsafe_allow_html=True)
        with cols[2]:
            st.markdown(f"**{b['label']}**")
            st.caption(f"Due {b['due']} · {tenant['name']}, Unit {tenant['unit']}")
        with cols[3]:
            st.markdown(f"**{fmt(b['amount'])}**")
            if st.session_state.currency != "KES":
                st.caption(fmt_kes_raw(b["amount"]))
        with cols[4]:
            if st.checkbox("Lipa Mdogo", key=f"lipa_{b['id']}",
                           value=b["id"] in st.session_state.partial_amounts):
                max_val = round(to_currency(b["amount"]))
                partial = st.number_input(
                    "Partial amount",
                    min_value=1.0,
                    max_value=float(max_val),
                    value=float(st.session_state.partial_amounts.get(b["id"], max_val)),
                    step=1.0 if st.session_state.currency == "KES" else 0.01,
                    key=f"partial_{b['id']}",
                    label_visibility="collapsed",
                )
                st.session_state.partial_amounts[b["id"]] = partial
            else:
                st.session_state.partial_amounts.pop(b["id"], None)

    sub = selected_subtotal_kes()
    st.markdown('<div class="summary-box">', unsafe_allow_html=True)
    st.markdown(f'<div class="summary-line"><span>Subtotal selected</span><span>{fmt(sub)}</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="summary-line"><span>Estimated gateway fee</span><span>— select method next</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="summary-line total"><span>Total due</span><span>{fmt(sub)}</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("Continue to payment method →", type="primary", disabled=sub <= 0, use_container_width=True):
        st.session_state.step = 2
        st.session_state.locked_rates = deepcopy(st.session_state.rates)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# STEP 2 – Payment gateway
# ─────────────────────────────────────────────
elif st.session_state.step == 2 and st.session_state.receipt is None:
    st.markdown('<div class="portal-card">', unsafe_allow_html=True)
    st.subheader("Choose payment gateway")
    st.caption("Fees below reflect the rate locked in for this checkout session.")

    st.info("🔒 **Rate locked for this checkout.** Fees and totals are fixed the moment you entered this step.")

    cols = st.columns(3)
    for i, gw in enumerate(GATEWAYS):
        with cols[i % 3]:
            selected = st.session_state.selected_gateway == gw["id"]
            border = "2px solid #1E4A3B" if selected else "1.5px solid #E0D9C8"
            bg = "#E8F2EC" if selected else "#FFFEF9"
            st.markdown(
                f"""
                <div style="border:{border};background:{bg};border-radius:12px;padding:1rem;margin-bottom:0.8rem;">
                  <div style="font-weight:600;color:#241F17">{gw['name']}</div>
                  <div style="font-size:0.82rem;color:#8C8271;margin-top:0.2rem">{gw_fee_label(gw)}</div>
                  <div style="font-size:0.75rem;color:#2F6B4F;margin-top:0.35rem">{gw['tag']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Select" if not selected else "✓ Selected", key=f"gw_{gw['id']}",
                         type="primary" if selected else "secondary", use_container_width=True):
                st.session_state.selected_gateway = gw["id"]
                st.session_state.selected_bank = None
                st.session_state.selected_crypto = None
                st.rerun()

    if st.session_state.selected_gateway == "bank":
        st.markdown("**Select bank**")
        banks = list(active_rates()["banks"].keys())
        bank_cols = st.columns(len(banks))
        for i, b in enumerate(banks):
            with bank_cols[i]:
                sel = st.session_state.selected_bank == b
                if st.button(f"{b}\nKsh{active_rates()['banks'][b]}", key=f"bank_{b}",
                             type="primary" if sel else "secondary", use_container_width=True):
                    st.session_state.selected_bank = b
                    st.rerun()

    if st.session_state.selected_gateway == "crypto":
        st.markdown("**Select crypto asset**")
        c1, c2 = st.columns(2)
        r = active_rates()
        with c1:
            sel = st.session_state.selected_crypto == "BTC"
            if st.button(f"BTC · {r['crypto']['BTC_KES']:,} KES", key="crypto_BTC",
                         type="primary" if sel else "secondary", use_container_width=True):
                st.session_state.selected_crypto = "BTC"
                st.rerun()
        with c2:
            sel = st.session_state.selected_crypto == "USDT"
            if st.button(f"USDT · {r['crypto']['USDT_KES']:.2f} KES", key="crypto_USDT",
                         type="primary" if sel else "secondary", use_container_width=True):
                st.session_state.selected_crypto = "USDT"
                st.rerun()

    ok = bool(st.session_state.selected_gateway)
    if st.session_state.selected_gateway == "bank":
        ok = ok and bool(st.session_state.selected_bank)
    if st.session_state.selected_gateway == "crypto":
        ok = ok and bool(st.session_state.selected_crypto)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back", use_container_width=True):
            st.session_state.step = 1
            st.session_state.locked_rates = None
            st.rerun()
    with c2:
        if st.button("Continue →", type="primary", disabled=not ok, use_container_width=True):
            st.session_state.step = 3
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# STEP 3 – Payment details
# ─────────────────────────────────────────────
elif st.session_state.step == 3 and st.session_state.receipt is None:
    st.markdown('<div class="portal-card">', unsafe_allow_html=True)
    gw = next(g for g in GATEWAYS if g["id"] == st.session_state.selected_gateway)
    extra = ""
    if st.session_state.selected_bank:
        extra = f" — {st.session_state.selected_bank}"
    if st.session_state.selected_crypto:
        extra = f" — {st.session_state.selected_crypto}"
    st.subheader("Enter payment details")
    st.caption(f"Paying via {gw['name']}{extra}.")

    form_data = {}
    if gw["id"] in ("mpesa", "airtel"):
        form_data["phone"] = st.text_input("Phone number", placeholder="07XX XXX XXX", key="f_phone")
        form_data["name"] = st.text_input("Account holder name", placeholder="Full name", key="f_name")
    elif gw["id"] == "syllopay":
        form_data["syllo"] = st.text_input("SylloPay ID or phone", placeholder="SP-XXXXXX or 07XXXXXXXX", key="f_syllo")
        form_data["name"] = st.text_input("Account holder name", placeholder="Full name", key="f_name")
    elif gw["id"] == "bank":
        form_data["acct"] = st.text_input("Bank account number", placeholder="e.g. 0112233445566", key="f_acct")
        form_data["name"] = st.text_input("Account holder name", placeholder="Full name", key="f_name")
    elif gw["id"] == "card":
        form_data["card"] = st.text_input("Card number", placeholder="4242 4242 4242 4242", max_chars=19, key="f_card")
        form_data["name"] = st.text_input("Cardholder name", placeholder="Full name", key="f_name")
        c1, c2 = st.columns(2)
        with c1:
            form_data["exp"] = st.text_input("Expiry (MM/YY)", placeholder="MM/YY", max_chars=5, key="f_exp")
        with c2:
            form_data["cvv"] = st.text_input("CVV", placeholder="123", max_chars=4, key="f_cvv")
    elif gw["id"] == "crypto":
        form_data["wallet"] = st.text_input(
            "Sending wallet address",
            placeholder=f"bc1q... or T... ({st.session_state.selected_crypto} address)",
            key="f_wallet",
        )

    st.session_state.form_data = form_data

    sub = selected_subtotal_kes()
    fee = compute_fee_kes(sub)
    st.markdown('<div class="summary-box">', unsafe_allow_html=True)
    st.markdown(f'<div class="summary-line"><span>Bills subtotal</span><span>{fmt(sub)}</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="summary-line"><span>{gw["name"]} & service fees</span><span>{fmt(fee)}</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="summary-line total"><span>Total to pay</span><span>{fmt(sub + fee)}</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    def form_valid() -> bool:
        if gw["id"] in ("mpesa", "airtel"):
            return validate_phone(form_data.get("phone", "")) and len(form_data.get("name", "").strip()) > 1
        if gw["id"] == "syllopay":
            return validate_syllo(form_data.get("syllo", "")) and len(form_data.get("name", "").strip()) > 1
        if gw["id"] == "bank":
            return validate_acct(form_data.get("acct", "")) and len(form_data.get("name", "").strip()) > 1
        if gw["id"] == "card":
            return (validate_card(form_data.get("card", "")) and
                    len(form_data.get("name", "").strip()) > 1 and
                    validate_exp(form_data.get("exp", "")) and
                    validate_cvv(form_data.get("cvv", "")))
        if gw["id"] == "crypto":
            return validate_wallet(form_data.get("wallet", ""))
        return False

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back", use_container_width=True):
            st.session_state.step = 2
            st.rerun()
    with c2:
        if st.button("Review & confirm →", type="primary", use_container_width=True):
            if form_valid():
                st.session_state.step = 4
                st.rerun()
            else:
                st.error("Please correct the highlighted fields before continuing.")
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# STEP 4 – Confirm & process
# ─────────────────────────────────────────────
elif st.session_state.step == 4 and st.session_state.receipt is None:
    st.markdown('<div class="portal-card">', unsafe_allow_html=True)
    st.subheader("Confirm & pay")
    st.caption("Double-check everything below, then authorise the payment.")

    tenant = next(t for t in TENANTS if t["id"] == st.session_state.tenant_id)
    bills = generate_bills(tenant, st.session_state.month)
    bill_names = ", ".join(b["label"] for b in bills if b["id"] in st.session_state.selected_bills)
    sub = selected_subtotal_kes()
    fee = compute_fee_kes(sub)
    gw = next(g for g in GATEWAYS if g["id"] == st.session_state.selected_gateway)
    method = gw["name"]
    if st.session_state.selected_bank:
        method += f" — {st.session_state.selected_bank}"
    if st.session_state.selected_crypto:
        method += f" — {st.session_state.selected_crypto}"

    contact = "—"
    fd = st.session_state.form_data
    if gw["id"] in ("mpesa", "airtel"):
        contact = fd.get("phone", "—")
    elif gw["id"] == "syllopay":
        contact = fd.get("syllo", "—")
    elif gw["id"] == "bank":
        contact = fd.get("acct", "—")
    elif gw["id"] == "card":
        card = fd.get("card", "")
        contact = f"•••• {card.replace(' ', '')[-4:]}" if card else "—"
    elif gw["id"] == "crypto":
        w = fd.get("wallet", "")
        contact = f"{w[:6]}…{w[-4:]}" if w else "—"

    st.markdown('<div class="summary-box">', unsafe_allow_html=True)
    rows = [
        ("Tenant", f"{tenant['name']} · Unit {tenant['unit']}"),
        ("Billing month", st.session_state.month),
        ("Bills covered", bill_names),
        ("Method", method),
        ("Phone / reference", contact),
        ("Subtotal", fmt(sub)),
        ("Fees", fmt(fee)),
    ]
    for label, val in rows:
        st.markdown(f'<div class="summary-line"><span>{label}</span><span class="v">{val}</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="summary-line total"><span>Total to authorise</span><span>{fmt(sub + fee)}</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back", use_container_width=True):
            st.session_state.step = 3
            st.rerun()
    with c2:
        if st.button("🛡️  Authorise payment", type="primary", use_container_width=True):
            with st.spinner("Contacting gateway…"):
                time.sleep(0.8)
            with st.spinner(f"Requesting {gw['name']} authorisation…"):
                time.sleep(0.9)
            with st.spinner("Verifying with Mwarokin ledger…"):
                time.sleep(0.7)
            st.session_state.receipt = build_receipt()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# RECEIPT VIEW
# ─────────────────────────────────────────────
elif st.session_state.receipt is not None:
    r = st.session_state.receipt
    st.markdown('<div class="receipt-card">', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div style="text-align:center;margin-bottom:1.2rem;">
          <div style="display:inline-flex;align-items:center;gap:0.6rem;
                      background:#E8F2EC;border:1px solid #2F6B4F;border-radius:10px;
                      padding:0.7rem 1.2rem;">
            <span style="font-size:1.4rem;">✅</span>
            <div style="text-align:left;">
              <b style="color:#1E4A3B;">Payment of {fmt(r['total'], r['currency'])} confirmed</b><br>
              <span style="font-size:0.82rem;color:#2F6B4F;">{r['method']} · Ref {r['txn']}</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(f'<p class="amount-value" style="text-align:center;">{fmt(r["total"], r["currency"])}</p>', unsafe_allow_html=True)
    if r["currency"] != "KES":
        st.caption(fmt_kes_raw(r["total"]), help="Equivalent in Kenyan Shillings")
    st.markdown('<p style="text-align:center;color:#2F6B4F;font-weight:600;letter-spacing:0.04em;">PAID & CONFIRMED</p>', unsafe_allow_html=True)

    col_main, col_stub = st.columns([2.2, 1])
    with col_main:
        for label, key in [
            ("Tenant / unit", "tenant"),
            ("Bills covered", "bills"),
            ("Billing month", "month"),
            ("Date & time", "date"),
            ("Method", "method"),
            ("Phone / reference", "contact"),
            ("Transaction ID", "txn"),
        ]:
            val = r[key]
            mono = " mono" if key == "txn" else ""
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:0.55rem 0;'
                f'border-bottom:1px dotted rgba(36,31,23,0.14);font-size:0.92rem;">'
                f'<span style="color:#635A49;">{label}</span>'
                f'<span class="v{mono}" style="font-weight:500;text-align:right;">{val}</span></div>',
                unsafe_allow_html=True,
            )

        st.markdown("#### Fee breakdown")
        for label, amt in r["fee_lines"]:
            st.markdown(f"- {label}: **{fmt_kes_raw(amt)}**")
        st.markdown(f"**Total fees: {fmt_kes_raw(r['fee'])}**")

        st.success(
            f"Your payment of {fmt(r['total'], r['currency'])} covering {r['bills']} "
            f"for {r['month']} has been applied successfully. No outstanding balance for these items."
        )

    with col_stub:
        st.markdown(
            """
            <div style="text-align:center;padding:1rem;">
              <div style="width:110px;height:110px;margin:0 auto;border-radius:50%;
                          background:linear-gradient(135deg,#EFDCA0,#C9A227,#8E6A1F);
                          display:flex;align-items:center;justify-content:center;
                          box-shadow:0 8px 20px rgba(0,0,0,0.25);">
                <span style="font-size:2.8rem;color:#3B2C0F;">✓</span>
              </div>
              <p style="font-weight:600;margin-top:0.8rem;color:#1E4A3B;">Verified & secured</p>
              <p style="font-size:0.78rem;color:#8C8271;">RBC-compliant audit trail</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("---")
        st.caption("🛡️ Bank-grade encryption")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        receipt_md = f"""# Mwarokin Estates Receipt
**{r['txn']}**

Amount paid: **{fmt(r['total'], r['currency'])}**
Tenant: {r['tenant']}
Bills: {r['bills']}
Month: {r['month']}
Method: {r['method']}
Date: {r['date']}
"""
        st.download_button(
            "⬇️ Download receipt",
            data=receipt_md,
            file_name=f"Mwarokin_Receipt_{r['txn']}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with c2:
        if st.button("🖨️ Print", use_container_width=True):
            st.info("Use your browser’s print dialog (Ctrl/Cmd+P) on this page.")
    with c3:
        if st.button("📋 Copy Txn ID", use_container_width=True):
            st.code(r["txn"], language=None)
            st.toast("Transaction ID ready to copy")
    with c4:
        if st.button("Pay another bill", use_container_width=True):
            for k in ["step", "selected_bills", "partial_amounts", "selected_gateway",
                      "selected_bank", "selected_crypto", "locked_rates", "form_data", "receipt"]:
                if k == "step":
                    st.session_state[k] = 1
                elif k in ("selected_bills", "partial_amounts"):
                    st.session_state[k] = set() if k == "selected_bills" else {}
                else:
                    st.session_state[k] = None
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────
st.markdown(
    """
    <div style="display:flex;gap:1.8rem;justify-content:center;margin-top:2rem;
                font-size:0.8rem;color:#8C8271;flex-wrap:wrap;">
      <span>⏱ Real-time confirmation</span>
      <span>📄 E-receipt available</span>
      <span>🛡️ Lipa Mdogo partial pay</span>
    </div>
    """,
    unsafe_allow_html=True,
)

**How to run**

```bash
pip install streamlit
streamlit run "Payment Portal.py"
```

The app fully replicates the original multi-step flow:

- Live FX + fee ticker (auto-refreshes every ~4 s while unlocked)
- Deterministic bills per tenant + month (seeded PRNG)
- Lipa Mdogo partial payments
- Rate lock at Step 2
- Dynamic gateway forms with validation
- Fee engine matching the original rules
- Processing animation + official receipt with download / copy / pay-another