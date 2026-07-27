python
"""
Mwarokin Estates — Payment Portal (Premium Python Edition)
Modern, fully functional, agentic multi-gateway payment system.
Streamlit + live simulated rates + local persistence + receipt generation.
"""

from __future__ import annotations

import json
import math
import random
import string
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components

# ─────────────────────────────────────────────────────────────
# CONFIG & STATIC DATA
# ─────────────────────────────────────────────────────────────

BUILDINGS = [
    {"id": "KLM", "name": "Kilimani Court", "units": ["A1", "A2", "B1", "B2", "C1"]},
    {"id": "WLM", "name": "Westlands Meridian", "units": ["101", "102", "201", "202"]},
    {"id": "RVL", "name": "Riverside Villas", "units": ["V1", "V2", "V3"]},
]

TENANTS = [
    {"id": "TEN-2201", "name": "Aisha Wanjiru", "buildingId": "KLM", "unit": "A1", "rent": 38000, "landlordId": "LL-001"},
    {"id": "TEN-2202", "name": "Brian Otieno", "buildingId": "KLM", "unit": "A2", "rent": 42000, "landlordId": "LL-001"},
    {"id": "TEN-2203", "name": "Cynthia Mutiso", "buildingId": "KLM", "unit": "B1", "rent": 35000, "landlordId": "LL-001"},
    {"id": "TEN-2301", "name": "David Kiptoo", "buildingId": "WLM", "unit": "101", "rent": 65000, "landlordId": "LL-002"},
    {"id": "TEN-2302", "name": "Esther Nyambura", "buildingId": "WLM", "unit": "102", "rent": 58000, "landlordId": "LL-002"},
    {"id": "TEN-2401", "name": "Farah Hassan", "buildingId": "RVL", "unit": "V1", "rent": 90000, "landlordId": "LL-003"},
]

BANKS = [
    {"name": "Equity Bank", "feeRange": [50, 110]},
    {"name": "KCB Bank", "feeRange": [45, 105]},
    {"name": "Co-operative Bank", "feeRange": [45, 100]},
    {"name": "Standard Chartered", "feeRange": [80, 180]},
    {"name": "Absa Bank Kenya", "feeRange": [55, 120]},
    {"name": "NCBA Bank", "feeRange": [50, 110]},
]

CRYPTO_COINS = [
    {"code": "BTC", "name": "Bitcoin", "base": 6_250_000, "vol": 0.006, "netFeeUsd": [3.5, 9]},
    {"code": "ETH", "name": "Ethereum", "base": 412_000, "vol": 0.012, "netFeeUsd": [1.2, 4.5]},
    {"code": "USDT", "name": "USDT (Tether)", "base": 129.4, "vol": 0.001, "netFeeUsd": [0.5, 2]},
    {"code": "LTC", "name": "Litecoin", "base": 9_850, "vol": 0.01, "netFeeUsd": [0.05, 0.3]},
]

FX_BASE = {"KES": 1.0, "USD": 129.40, "GBP": 164.80, "CNY": 17.95}
CCY_SYMBOLS = {"KES": "KSh", "USD": "$", "GBP": "£", "CNY": "¥"}

BILL_TEMPLATES = [
    {"key": "rent", "label": "Monthly Rent", "icon": "🏠", "color": "#0e1a2b"},
    {"key": "service", "label": "Service Charge", "icon": "🧱", "color": "#c9a959"},
    {"key": "water", "label": "Water Bill", "icon": "💧", "color": "#2f5f8a"},
    {"key": "garbage", "label": "Waste Management", "icon": "🗑️", "color": "#2f7d5e"},
    {"key": "parking", "label": "Parking Fee", "icon": "🅿️", "color": "#b9822f"},
    {"key": "amenities", "label": "Amenities Levy", "icon": "🏊", "color": "#b3462c"},
]

DATA_DIR = Path(__file__).parent / ".mwarokin_data"
DATA_DIR.mkdir(exist_ok=True)
PAYMENTS_FILE = DATA_DIR / "payments.json"
BILLS_FILE = DATA_DIR / "bills.json"

# ─────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────

def rid(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

def clamp_drift(val: float, base: float, spread: float) -> float:
    next_val = val + (random.random() - 0.5) * spread * 0.5
    return max(base - spread, min(base + spread, next_val))

def format_currency(amount: float, currency: str = "KES") -> str:
    symbol = CCY_SYMBOLS.get(currency, currency)
    return f"{symbol} {amount:,.2f}"

def month_label() -> str:
    return datetime.now().strftime("%B %Y")

# ─────────────────────────────────────────────────────────────
# RATE ENGINE (live simulated market data)
# ─────────────────────────────────────────────────────────────

class RateEngine:
    def __init__(self):
        self.fx = dict(FX_BASE)
        self.crypto = {c["code"]: c["base"] for c in CRYPTO_COINS}
        self.mpesa_cost = 12.0
        self.bank_avg = 78.0
        self.service_rate = 0.5
        self.crypto_net = 2.1
        self._last_tick = 0.0

    def tick(self) -> None:
        now = time.time()
        if now - self._last_tick < 3.5:
            return
        self._last_tick = now
        self.fx["USD"] = clamp_drift(self.fx["USD"], 129.40, 0.15)
        self.fx["GBP"] = clamp_drift(self.fx["GBP"], 164.80, 0.22)
        self.fx["CNY"] = clamp_drift(self.fx["CNY"], 17.95, 0.03)
        for c in CRYPTO_COINS:
            self.crypto[c["code"]] = clamp_drift(
                self.crypto[c["code"]], c["base"], c["base"] * c["vol"]
            )
        self.mpesa_cost = round(clamp_drift(self.mpesa_cost, 12, 2))
        self.bank_avg = round(clamp_drift(self.bank_avg, 78, 8))
        self.crypto_net = round(clamp_drift(self.crypto_net, 2.1, 0.4), 2)

# ─────────────────────────────────────────────────────────────
# FEE ENGINE
# ─────────────────────────────────────────────────────────────

class FeeEngine:
    @staticmethod
    def platform_fee_kes(amount_kes: float) -> float:
        if amount_kes <= 1_000:
            return 1.0
        if amount_kes <= 5_000:
            return 2.0
        if amount_kes <= 20_000:
            return 3.0
        if amount_kes <= 80_000:
            return 4.0
        return 5.0

    @staticmethod
    def bank_fee_kes(bank_name: str) -> float:
        bank = next((b for b in BANKS if b["name"] == bank_name), BANKS[0])
        lo, hi = bank["feeRange"]
        return round(lo + random.random() * (hi - lo))

    @staticmethod
    def crypto_network_fee_usd(coin_code: str) -> float:
        coin = next((c for c in CRYPTO_COINS if c["code"] == coin_code), CRYPTO_COINS[1])
        lo, hi = coin["netFeeUsd"]
        return round(lo + random.random() * (hi - lo), 2)

    @classmethod
    def breakdown(
        cls,
        method: str,
        amount: float,
        currency: str,
        rates: RateEngine,
        bank_name: str = "",
        coin_code: str = "ETH",
    ) -> Dict[str, Any]:
        fx = rates.fx.get(currency, 1.0)
        amount_kes = amount * fx
        platform = cls.platform_fee_kes(amount_kes)

        gateway_fee_kes = 0.0
        gateway_label = ""

        if method == "bank":
            gateway_fee_kes = cls.bank_fee_kes(bank_name or BANKS[0]["name"])
            gateway_label = f"{bank_name or 'Bank'} transfer fee"
        elif method == "mobile":
            gateway_fee_kes = amount_kes * 0.01
            gateway_label = "Mobile wallet fee (1.0%)"
        elif method == "crypto":
            usd_fee = cls.crypto_network_fee_usd(coin_code)
            gateway_fee_kes = usd_fee * rates.fx["USD"]
            gateway_label = f"Network fee (~${usd_fee})"
        elif method == "mpesa":
            gateway_fee_kes = min(35.0, max(1.0, amount_kes * 0.006))
            gateway_label = "M-Pesa transaction cost"
        elif method == "syllopay":
            gateway_fee_kes = amount_kes * 0.003
            gateway_label = "SylloPay routing fee (0.3%)"

        service_fee_kes = amount_kes * (rates.service_rate / 100)
        total_fee_kes = platform + gateway_fee_kes + service_fee_kes
        total_kes = amount_kes + total_fee_kes

        def to_disp(kes: float) -> float:
            return kes / fx

        return {
            "amount_kes": amount_kes,
            "platform_kes": platform,
            "gateway_fee_kes": gateway_fee_kes,
            "gateway_label": gateway_label,
            "service_fee_kes": service_fee_kes,
            "total_fee_kes": total_fee_kes,
            "total_kes": total_kes,
            "display": {
                "amount": to_disp(amount_kes),
                "platform": to_disp(platform),
                "gateway": to_disp(gateway_fee_kes),
                "service": to_disp(service_fee_kes),
                "total_fee": to_disp(total_fee_kes),
                "total": to_disp(total_kes),
            },
        }

# ─────────────────────────────────────────────────────────────
# PERSISTENCE
# ─────────────────────────────────────────────────────────────

def load_json(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default

def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

def seed_payments() -> List[Dict]:
    now = datetime.now()
    return [
        {
            "id": "sp_1",
            "status": "completed",
            "amount": 12000,
            "currency": "KES",
            "type": "syllopay",
            "sylloCode": "SYL-4XK92",
            "timestamp": (now - timedelta(hours=12)).isoformat(),
            "reference": "SYL284710",
            "tenantId": "TEN-2201",
            "totalFee": 96,
            "receiptNo": "MWK-000241",
        },
        {
            "id": "mp_1",
            "status": "completed",
            "amount": 5000,
            "currency": "KES",
            "type": "mpesa",
            "phone": "0712 *** 456",
            "timestamp": (now - timedelta(days=1)).isoformat(),
            "reference": "MPX384729",
            "tenantId": "TEN-2202",
            "totalFee": 37,
            "receiptNo": "MWK-000240",
        },
        {
            "id": "bt_1",
            "status": "completed",
            "amount": 7500,
            "currency": "KES",
            "type": "bank_transfer",
            "bankName": "Equity Bank",
            "timestamp": (now - timedelta(days=2)).isoformat(),
            "reference": "REF384729",
            "tenantId": "TEN-2203",
            "totalFee": 106,
            "receiptNo": "MWK-000239",
        },
        {
            "id": "mw_1",
            "status": "completed",
            "amount": 3500,
            "currency": "KES",
            "type": "mobile_wallet",
            "walletProvider": "Airtel Money",
            "timestamp": (now - timedelta(days=3)).isoformat(),
            "tenantId": "TEN-2301",
            "totalFee": 55,
            "receiptNo": "MWK-000238",
        },
        {
            "id": "cp_1",
            "status": "completed",
            "amount": 100,
            "currency": "USD",
            "type": "crypto",
            "cryptocurrency": "Ethereum (ETH)",
            "timestamp": (now - timedelta(days=4)).isoformat(),
            "tenantId": "TEN-2401",
            "totalFee": 5.4,
            "receiptNo": "MWK-000237",
        },
    ]

def load_payments() -> List[Dict]:
    data = load_json(PAYMENTS_FILE, None)
    if data is None:
        data = seed_payments()
        save_json(PAYMENTS_FILE, data)
    return data

def save_payments(payments: List[Dict]) -> None:
    save_json(PAYMENTS_FILE, payments)

def load_bills() -> Dict[str, List[Dict]]:
    data = load_json(BILLS_FILE, None)
    if data is not None:
        return data

    bills: Dict[str, List[Dict]] = {}
    for t in TENANTS:
        tenant_bills = []
        for tpl in BILL_TEMPLATES:
            amt = 0.0
            if tpl["key"] == "rent":
                amt = t["rent"]
            elif tpl["key"] == "service":
                amt = round(t["rent"] * 0.06)
            elif tpl["key"] == "water":
                amt = 400 + round(random.random() * 900)
            elif tpl["key"] == "garbage":
                amt = 300
            elif tpl["key"] == "parking":
                amt = 1500 if random.random() > 0.4 else 0
            elif tpl["key"] == "amenities":
                amt = round(t["rent"] * 0.02)

            if amt <= 0:
                continue

            status = "paid" if amt == 0 else (
                "unpaid" if random.random() > 0.55 else ("partial" if random.random() > 0.5 else "paid")
            )
            tenant_bills.append({**tpl, "amount": amt, "status": status, "month": month_label()})
        bills[t["id"]] = tenant_bills

    save_json(BILLS_FILE, bills)
    return bills

# ─────────────────────────────────────────────────────────────
# MOCK PAYMENT SERVICE
# ─────────────────────────────────────────────────────────────

class PaymentService:
    @staticmethod
    def process_bank_transfer(data: Dict) -> Dict:
        time.sleep(1.2)
        if not data.get("amount") or data["amount"] <= 0:
            raise ValueError("Amount must be greater than zero")
        if not data.get("bankName"):
            raise ValueError("Please select a bank")
        return {
            "id": f"bt_{rid()}",
            "status": "pending",
            "type": "bank_transfer",
            **data,
            "timestamp": datetime.now().isoformat(),
            "reference": f"REF{random.randint(100000, 999999)}",
        }

    @staticmethod
    def process_mpesa(data: Dict) -> Dict:
        time.sleep(0.9)
        if not data.get("amount") or data["amount"] <= 0:
            raise ValueError("Amount must be greater than zero")
        phone = (data.get("phone") or "").replace(" ", "")
        if not phone.startswith(("07", "01")) or len(phone) != 10:
            raise ValueError("Enter a valid M-Pesa phone number (07XX XXX XXX)")
        return {
            "id": f"mp_{rid()}",
            "status": "pending",
            "type": "mpesa",
            **data,
            "timestamp": datetime.now().isoformat(),
            "reference": f"MPX{random.randint(100000, 999999)}",
        }

    @staticmethod
    def process_syllopay(data: Dict) -> Dict:
        time.sleep(1.1)
        if not data.get("amount") or data["amount"] <= 0:
            raise ValueError("Amount must be greater than zero")
        if not data.get("sylloCode"):
            raise ValueError("Enter your SylloPay ID / SylloCode")
        return {
            "id": f"sp_{rid()}",
            "status": "completed",
            "type": "syllopay",
            **data,
            "timestamp": datetime.now().isoformat(),
            "reference": f"SYL{random.randint(100000, 999999)}",
        }

    @staticmethod
    def process_mobile_wallet(data: Dict) -> Dict:
        time.sleep(1.0)
        if not data.get("amount") or data["amount"] <= 0:
            raise ValueError("Amount must be greater than zero")
        if not data.get("walletNumber"):
            raise ValueError("Wallet number is required")
        return {
            "id": f"mw_{rid()}",
            "status": "initiated",
            "type": "mobile_wallet",
            **data,
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def process_crypto(data: Dict, rates: RateEngine) -> Dict:
        time.sleep(0.9)
        if not data.get("amount") or data["amount"] <= 0:
            raise ValueError("Amount must be greater than zero")
        coin = next(
            (c for c in CRYPTO_COINS if data.get("cryptocurrency", "").startswith(c["name"])),
            CRYPTO_COINS[1],
        )
        rate_kes = rates.crypto[coin["code"]]
        amt_kes = data["amount"] * rates.fx.get(data.get("currency", "KES"), 1)
        return {
            "id": f"cp_{rid()}",
            "status": "awaiting_confirmation",
            "type": "crypto",
            **data,
            "timestamp": datetime.now().isoformat(),
            "cryptoAmount": f"{(amt_kes / rate_kes):.8f}",
            "coinCode": coin["code"],
            "address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
        }

# ─────────────────────────────────────────────────────────────
# STREAMLIT APP
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Mwarokin Estates · Payment Portal",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS — premium dark navy + gold theme
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;500;600;700&display=swap');

:root {
    --navy: #0e1a2b;
    --navy-deep: #08111c;
    --gold: #c9a959;
    --gold-dim: #a88b3e;
    --gray-100: #f7f5f2;
    --gray-200: #ebe7e0;
    --gray-600: #6b6560;
    --green: #2f7d5e;
    --red: #b3462c;
}

html, body, [class*="css"] {
    font-family: 'Inter', system-ui, sans-serif;
}

h1, h2, h3, .serif {
    font-family: 'Playfair Display', Georgia, serif !important;
}

.stApp {
    background: linear-gradient(160deg, #f9f7f4 0%, #f0ece6 100%);
}

div[data-testid="stHeader"] { background: transparent; }

.brand-header {
    background: linear-gradient(135deg, var(--navy) 0%, var(--navy-deep) 100%);
    border-radius: 16px;
    padding: 22px 28px;
    color: white;
    margin-bottom: 18px;
    box-shadow: 0 8px 32px rgba(14,26,43,.25);
}

.brand-header h1 {
    color: white !important;
    font-size: 1.55rem !important;
    margin: 0 !important;
}

.brand-header .gold { color: var(--gold) !important; }

.rate-ticker {
    display: flex;
    gap: 10px;
    overflow-x: auto;
    padding: 10px 0;
    margin-bottom: 12px;
}

.rate-cell {
    background: white;
    border: 1px solid var(--gray-200);
    border-radius: 12px;
    padding: 10px 14px;
    min-width: 130px;
    box-shadow: 0 2px 8px rgba(0,0,0,.04);
}

.rate-cell .rl { font-size: 11px; color: var(--gray-600); font-weight: 600; }
.rate-cell .rv { font-size: 15px; font-weight: 700; color: var(--navy); font-family: monospace; }

.method-card {
    background: white;
    border: 2px solid var(--gray-200);
    border-radius: 14px;
    padding: 16px;
    text-align: center;
    cursor: pointer;
    transition: all .2s;
}

.method-card:hover, .method-card.active {
    border-color: var(--gold);
    box-shadow: 0 4px 16px rgba(201,169,89,.25);
}

.method-card .fee {
    font-size: 11px;
    color: var(--gold-dim);
    font-family: monospace;
    margin-top: 6px;
}

.p-card {
    background: white;
    border-radius: 16px;
    padding: 22px;
    border: 1px solid var(--gray-200);
    box-shadow: 0 4px 20px rgba(0,0,0,.04);
    margin-bottom: 16px;
}

.fee-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    font-size: 13px;
}

.fee-total {
    display: flex;
    justify-content: space-between;
    padding-top: 10px;
    margin-top: 8px;
    border-top: 2px solid var(--navy);
    font-weight: 800;
    font-size: 15px;
}

.pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 100px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
}

.pill-completed, .pill-paid { background: #e6f4ee; color: var(--green); }
.pill-pending, .pill-partial { background: #fef6e7; color: #b9822f; }
.pill-unpaid, .pill-error { background: #fceaea; color: var(--red); }
.pill-initiated, .pill-awaiting_confirmation { background: #eef2f7; color: #2f5f8a; }

.live-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    background: #22c55e;
    border-radius: 50%;
    margin-right: 5px;
    animation: pulse 1.5s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: .4; }
}

div[data-testid="stMetric"] {
    background: white;
    border-radius: 12px;
    padding: 12px 16px;
    border: 1px solid var(--gray-200);
}
</style>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────

if "rates" not in st.session_state:
    st.session_state.rates = RateEngine()
if "payments" not in st.session_state:
    st.session_state.payments = load_payments()
if "bills" not in st.session_state:
    st.session_state.bills = load_bills()
if "tenant_id" not in st.session_state:
    st.session_state.tenant_id = TENANTS[0]["id"]
if "currency" not in st.session_state:
    st.session_state.currency = "KES"
if "method" not in st.session_state:
    st.session_state.method = "syllopay"
if "feed" not in st.session_state:
    st.session_state.feed = []
if "last_receipt" not in st.session_state:
    st.session_state.last_receipt = None
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "pay"

rates: RateEngine = st.session_state.rates
rates.tick()  # live update on every rerun

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def current_tenant() -> Dict:
    return next((t for t in TENANTS if t["id"] == st.session_state.tenant_id), TENANTS[0])

def current_building() -> Dict:
    t = current_tenant()
    return next((b for b in BUILDINGS if b["id"] == t["buildingId"]), BUILDINGS[0])

def tenant_bills() -> List[Dict]:
    return st.session_state.bills.get(st.session_state.tenant_id, [])

def tenant_due() -> float:
    return sum(b["amount"] for b in tenant_bills() if b["status"] != "paid")

def push_feed(entry: Dict) -> None:
    st.session_state.feed = [entry] + st.session_state.feed[:7]

# ─────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────

st.markdown(
    f"""
<div class="brand-header">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
        <div>
            <h1>Mwarokin <span class="gold">Estates</span></h1>
            <p style="margin:4px 0 0;opacity:.7;font-size:13px;">Payment Portal · Real-Time Multi-Gateway Settlement</p>
        </div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;">
            <span style="background:rgba(255,255,255,.1);padding:6px 12px;border-radius:100px;font-size:12px;">
                <span class="live-dot"></span> Live rates · updates every few seconds
            </span>
            <span style="background:rgba(255,255,255,.1);padding:6px 12px;border-radius:100px;font-size:12px;">
                🔒 Bank-grade encryption
            </span>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────
# RATE TICKER
# ─────────────────────────────────────────────────────────────

cols = st.columns(8)
cells = [
    ("USD → KES", f"{rates.fx['USD']:.2f}"),
    ("GBP → KES", f"{rates.fx['GBP']:.2f}"),
    ("CNY → KES", f"{rates.fx['CNY']:.2f}"),
    ("M-Pesa cost", f"KSh {rates.mpesa_cost:.0f}"),
    ("Bank avg fee", f"KSh {rates.bank_avg:.0f}"),
    ("Service rate", f"{rates.service_rate:.2f}%"),
    ("BTC → KES", f"{rates.crypto['BTC']:,.0f}"),
    ("ETH → KES", f"{rates.crypto['ETH']:,.0f}"),
]
for col, (label, value) in zip(cols, cells):
    with col:
        st.markdown(
            f"""
            <div class="rate-cell">
                <div class="rl">{label}</div>
                <div class="rv">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────────────────────
# TENANT SELECTOR + CURRENCY
# ─────────────────────────────────────────────────────────────

tenant = current_tenant()
building = current_building()
due = tenant_due()

c1, c2, c3, c4, c5 = st.columns([2.2, 1, 1.4, 1.3, 1.8])
with c1:
    tenant_options = {f"{t['id']} — {t['name']}": t["id"] for t in TENANTS}
    selected_label = st.selectbox(
        "Tenant",
        list(tenant_options.keys()),
        index=list(tenant_options.values()).index(st.session_state.tenant_id),
    )
    st.session_state.tenant_id = tenant_options[selected_label]
with c2:
    st.markdown(f"**Unit**  \n`{tenant['unit']}`")
with c3:
    st.markdown(f"**Building**  \n{building['name']}")
with c4:
    color = "#b3462c" if due > 0 else "#2f7d5e"
    st.markdown(f"**Amount Due**  \n<span style='color:{color};font-weight:700;font-family:monospace'>{format_currency(due)}</span>", unsafe_allow_html=True)
with c5:
    st.session_state.currency = st.radio(
        "Currency",
        ["KES", "USD", "GBP", "CNY"],
        horizontal=True,
        index=["KES", "USD", "GBP", "CNY"].index(st.session_state.currency),
        label_visibility="collapsed",
    )

st.divider()

# ─────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────

tab_pay, tab_bills, tab_history = st.tabs(
    ["💳 Make Payment", "📋 Manage Bills · The Ledger", "📜 Payment History"]
)

# ═════════════════════════════════════════════════════════════
# TAB 1 — MAKE PAYMENT
# ═════════════════════════════════════════════════════════════

with tab_pay:
    st.subheader("Select Payment Method")
    method_cols = st.columns(5)
    methods = [
        ("syllopay", "🌍 SylloPay", "Pan-African wallet", "0.3% routing fee"),
        ("mpesa", "📱 M-Pesa", "STK Push", f"~KSh {rates.mpesa_cost:.0f} cost"),
        ("bank", "🏦 Bank Transfer", "Direct transfer", f"~KSh {rates.bank_avg:.0f} avg fee"),
        ("mobile", "👛 Mobile Wallet", "Airtel, T-Kash", "1.0% wallet fee"),
        ("crypto", "🪙 Crypto", "BTC, ETH, USDT", f"~${rates.crypto_net:.1f} network fee"),
    ]
    for col, (mid, name, sub, fee) in zip(method_cols, methods):
        with col:
            active = st.session_state.method == mid
            if st.button(
                f"**{name}**\n\n{sub}\n\n`{fee}`",
                key=f"m_{mid}",
                use_container_width=True,
                type="primary" if active else "secondary",
            ):
                st.session_state.method = mid
                st.rerun()

    st.markdown("---")
    left, right = st.columns([1.15, 0.85])

    with left:
        method = st.session_state.method
        currency = st.session_state.currency

        with st.form(key=f"form_{method}", clear_on_submit=False):
            if method == "syllopay":
                st.markdown("### 🌍 Pay with SylloPay")
                syllo_code = st.text_input("SylloPay ID / SylloCode", placeholder="e.g. SYL-4XK92")
                amount = st.number_input(f"Amount ({currency})", min_value=1.0, step=0.01, value=None)
                reference = st.text_input("Reference (optional)", placeholder=f"Rent — {building['name']}")
                submit = st.form_submit_button("Pay with SylloPay", type="primary", use_container_width=True)

            elif method == "mpesa":
                st.markdown("### 📱 Lipa Na M-Pesa")
                phone = st.text_input("M-Pesa phone number", placeholder="07XX XXX XXX")
                amount = st.number_input("Amount (KES)", min_value=1.0, step=1.0, value=None)
                reference = st.text_input("Account reference", value=st.session_state.tenant_id)
                submit = st.form_submit_button("Send STK Push", type="primary", use_container_width=True)

            elif method == "bank":
                st.markdown("### 🏦 Bank Transfer")
                bank_name = st.selectbox("Select bank", [""] + [b["name"] for b in BANKS])
                col_a, col_b = st.columns(2)
                with col_a:
                    account_number = st.text_input("Account number")
                with col_b:
                    account_name = st.text_input("Account name")
                amount = st.number_input(f"Amount ({currency})", min_value=1.0, step=0.01, value=None)
                reference = st.text_input("Payment reference (optional)", value=st.session_state.tenant_id)
                submit = st.form_submit_button("Initiate Bank Transfer", type="primary", use_container_width=True)

            elif method == "mobile":
                st.markdown("### 👛 Mobile Wallet")
                providers = ["Airtel Money", "T-Kash", "MTC Money", "Orange Money"]
                wallet_provider = st.selectbox("Select provider", [""] + providers)
                wallet_number = st.text_input("Wallet number")
                amount = st.number_input(f"Amount ({currency})", min_value=1.0, step=0.01, value=None)
                submit = st.form_submit_button("Initiate Payment", type="primary", use_container_width=True)

            elif method == "crypto":
                st.markdown("### 🪙 Cryptocurrency")
                coin_opts = [f"{c['name']} ({c['code']})" for c in CRYPTO_COINS]
                cryptocurrency = st.selectbox("Select cryptocurrency", [""] + coin_opts)
                amount = st.number_input(f"Amount ({currency})", min_value=1.0, step=0.01, value=None)
                wallet_address = st.text_input("Your crypto wallet address", placeholder="bc1q… or 0x…")
                submit = st.form_submit_button("Get Deposit Address", type="primary", use_container_width=True)

            # Live fee preview
            if amount and amount > 0:
                bank_for_fee = bank_name if method == "bank" else BANKS[0]["name"]
                coin_code = "ETH"
                if method == "crypto" and cryptocurrency:
                    m = cryptocurrency.split("(")
                    if len(m) > 1:
                        coin_code = m[1].rstrip(")")
                fee = FeeEngine.breakdown(
                    method=method,
                    amount=amount,
                    currency=currency if method != "mpesa" else "KES",
                    rates=rates,
                    bank_name=bank_for_fee,
                    coin_code=coin_code,
                )
                st.markdown(
                    f"""
                    <div class="p-card" style="background:#f7f5f2;border-style:dashed;">
                        <div style="font-size:11px;font-weight:700;color:#6b6560;text-transform:uppercase;letter-spacing:.4px;margin-bottom:8px;">
                            🧾 Live Fee Breakdown
                        </div>
                        <div class="fee-row"><span>Amount</span><span style="font-family:monospace">{format_currency(fee['display']['amount'], currency)}</span></div>
                        <div class="fee-row"><span>Mwarokin platform fee</span><span style="font-family:monospace">{format_currency(fee['display']['platform'], currency)}</span></div>
                        <div class="fee-row"><span>{fee['gateway_label']}</span><span style="font-family:monospace">{format_currency(fee['display']['gateway'], currency)}</span></div>
                        <div class="fee-row"><span>Service fee ({rates.service_rate:.2f}%)</span><span style="font-family:monospace">{format_currency(fee['display']['service'], currency)}</span></div>
                        <div class="fee-total"><span>Total to pay</span><span style="font-family:monospace;color:#a88b3e">{format_currency(fee['display']['total'], currency)}</span></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if submit:
                try:
                    data: Dict[str, Any] = {
                        "amount": amount,
                        "currency": currency if method != "mpesa" else "KES",
                        "tenantId": tenant["id"],
                    }
                    if method == "syllopay":
                        data["sylloCode"] = syllo_code
                        data["reference"] = reference
                        res = PaymentService.process_syllopay(data)
                    elif method == "mpesa":
                        data["phone"] = phone
                        data["reference"] = reference
                        res = PaymentService.process_mpesa(data)
                    elif method == "bank":
                        data.update(
                            {
                                "bankName": bank_name,
                                "accountNumber": account_number,
                                "accountName": account_name,
                                "reference": reference,
                            }
                        )
                        res = PaymentService.process_bank_transfer(data)
                    elif method == "mobile":
                        data.update({"walletProvider": wallet_provider, "walletNumber": wallet_number})
                        res = PaymentService.process_mobile_wallet(data)
                    elif method == "crypto":
                        data.update({"cryptocurrency": cryptocurrency, "walletAddress": wallet_address})
                        res = PaymentService.process_crypto(data, rates)

                    bank_for_fee = data.get("bankName", BANKS[0]["name"])
                    coin_code = "ETH"
                    if method == "crypto" and data.get("cryptocurrency"):
                        m = data["cryptocurrency"].split("(")
                        if len(m) > 1:
                            coin_code = m[1].rstrip(")")

                    fee = FeeEngine.breakdown(
                        method=method,
                        amount=amount,
                        currency=data["currency"],
                        rates=rates,
                        bank_name=bank_for_fee,
                        coin_code=coin_code,
                    )

                    receipt_no = f"MWK-{100000 + len(st.session_state.payments) + 1:06d}"
                    enriched = {
                        **res,
                        "totalFee": fee["display"]["total_fee"],
                        "receiptNo": receipt_no,
                        "currency": data["currency"],
                    }
                    st.session_state.payments = [enriched] + st.session_state.payments
                    save_payments(st.session_state.payments)

                    # Simulate finalization
                    if method in ("mpesa", "crypto", "mobile"):
                        time.sleep(1.5)
                        enriched["status"] = "completed"
                        for i, p in enumerate(st.session_state.payments):
                            if p["id"] == enriched["id"]:
                                st.session_state.payments[i] = enriched
                                break
                        save_payments(st.session_state.payments)

                    if enriched["status"] == "completed":
                        receipt = {
                            "receiptNo": receipt_no,
                            "tenantName": tenant["name"],
                            "unit": tenant["unit"],
                            "buildingName": building["name"],
                            "method": enriched["type"].replace("_", " "),
                            "amount": enriched["amount"],
                            "currency": enriched["currency"],
                            "totalFee": fee["display"]["total_fee"],
                            "totalPaid": fee["display"]["total"],
                            "timestamp": enriched["timestamp"],
                        }
                        st.session_state.last_receipt = receipt
                        push_feed(
                            {
                                "tenantName": tenant["name"],
                                "unit": tenant["unit"],
                                "buildingName": building["name"],
                                "amount": fee["amount_kes"],
                                "method": enriched["type"].replace("_", " "),
                                "timestamp": enriched["timestamp"],
                            }
                        )
                        st.success(
                            f"✅ {format_currency(enriched['amount'], enriched['currency'])} confirmed. "
                            f"Landlord {tenant['landlordId']} notified."
                        )
                        st.balloons()
                    else:
                        st.info(
                            f"Bank transfer initiated. Reference **{enriched.get('reference')}**. "
                            "Awaiting bank confirmation (1–2 business days)."
                        )

                except Exception as e:
                    st.error(str(e))

    with right:
        st.markdown(
            """
            <div class="p-card" style="background:linear-gradient(155deg,#0e1a2b,#08111c);color:white;border:none;">
                <h3 style="color:white;margin-top:0;">⚡ Real-Time Settlement</h3>
                <p style="opacity:.7;font-size:13px;">Every completed payment instantly notifies the landlord and posts a digital receipt.</p>
                <ul style="font-size:13px;opacity:.85;padding-left:18px;">
                    <li>Landlord account credited on confirmation</li>
                    <li>Fees quoted at live current-market rates</li>
                    <li>Receipts generated automatically, every time</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("#### 📡 Live Deposit Feed")
        if not st.session_state.feed:
            st.caption("No deposits yet this session. Completed payments will appear here in real time.")
        else:
            for f in st.session_state.feed:
                st.markdown(
                    f"""
                    <div style="display:flex;gap:10px;align-items:center;padding:10px 0;border-bottom:1px solid #ebe7e0;">
                        <div style="width:36px;height:36px;border-radius:50%;background:#f0ece6;display:flex;align-items:center;justify-content:center;">👤</div>
                        <div style="flex:1;">
                            <div style="font-weight:700;font-size:13px;">{f['tenantName']} <span style="font-weight:500;color:#6b6560;">· {f['unit']}, {f['buildingName']}</span></div>
                            <div style="font-size:12px;color:#6b6560;">Paid <strong style="color:#a88b3e;">{format_currency(f['amount'])}</strong> via {f['method']}</div>
                            <div style="font-size:11px;color:#999;">{datetime.fromisoformat(f['timestamp']).strftime('%H:%M:%S')}</div>
                        </div>
                        <span class="pill pill-completed">✓</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

# ═════════════════════════════════════════════════════════════
# TAB 2 — BILLS / LEDGER
# ═════════════════════════════════════════════════════════════

with tab_bills:
    bills = tenant_bills()
    total_due = tenant_due()
    total_all = sum(b["amount"] for b in bills)

    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
            <div>
                <h2 style="margin:0;">📋 Manage Bills · The Ledger</h2>
                <p style="color:#6b6560;margin:4px 0 0;">{tenant['name']} · {tenant['unit']}, {building['name']} — {month_label()}</p>
            </div>
            <div style="text-align:right;">
                <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:#6b6560;">Outstanding</div>
                <div style="font-size:22px;font-weight:800;font-family:monospace;color:{'#b3462c' if total_due > 0 else '#2f7d5e'};">
                    {format_currency(total_due)}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for b in bills:
        col1, col2, col3 = st.columns([3, 1.2, 1])
        with col1:
            st.markdown(f"**{b['icon']} {b['label']}**  \n<span style='font-size:12px;color:#6b6560'>{b['month']}</span>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div style='font-family:monospace;font-weight:700;font-size:15px'>{format_currency(b['amount'])}</div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<span class='pill pill-{b['status']}'>{b['status']}</span>", unsafe_allow_html=True)
            if b["status"] != "paid":
                if st.button("Pay now", key=f"pay_{b['key']}", type="secondary"):
                    st.session_state.method = "syllopay"
                    st.info("Switch to Make Payment tab and complete the payment.")
        st.divider()

    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;padding-top:12px;border-top:2px solid #0e1a2b;">
            <span style="font-weight:700;">Total billed this month</span>
            <span style="font-family:monospace;font-weight:800;font-size:17px;color:#a88b3e;">{format_currency(total_all)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ═════════════════════════════════════════════════════════════
# TAB 3 — HISTORY
# ═════════════════════════════════════════════════════════════

with tab_history:
    payments = st.session_state.payments
    st.markdown(f"### 📜 Payment History  <span style='font-size:13px;background:#f0ece6;padding:4px 12px;border-radius:100px;margin-left:8px;'>{len(payments)} payments</span>", unsafe_allow_html=True)

    type_meta = {
        "syllopay": ("🌍", "SylloPay"),
        "mpesa": ("📱", "M-Pesa"),
        "bank_transfer": ("🏦", "Bank transfer"),
        "mobile_wallet": ("👛", "Mobile wallet"),
        "crypto": ("🪙", "Crypto"),
    }

    if not payments:
        st.info("No payments found.")
    else:
        rows = []
        for p in payments:
            t = next((x for x in TENANTS if x["id"] == p.get("tenantId")), None)
            icon, label = type_meta.get(p.get("type", ""), ("💵", p.get("type", "—")))
            rows.append(
                {
                    "Receipt": p.get("receiptNo") or p.get("id"),
                    "Tenant": f"{t['name']} · {t['unit']}" if t else "—",
                    "Type": f"{icon} {label}",
                    "Amount": format_currency(p["amount"], p.get("currency", "KES")),
                    "Fee": format_currency(p.get("totalFee", 0), p.get("currency", "KES")) if p.get("totalFee") else "—",
                    "Details": p.get("bankName") or p.get("walletProvider") or p.get("cryptocurrency") or p.get("sylloCode") or p.get("phone") or "",
                    "Status": p.get("status", "").replace("_", " "),
                    "Date": datetime.fromisoformat(p["timestamp"]).strftime("%Y-%m-%d %H:%M"),
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)

        # View receipt buttons
        completed = [p for p in payments if p.get("status") == "completed"]
        if completed:
            sel = st.selectbox(
                "View receipt for",
                [f"{p.get('receiptNo')} — {p.get('type')}" for p in completed],
            )
            if st.button("Show Receipt", type="primary"):
                idx = [f"{p.get('receiptNo')} — {p.get('type')}" for p in completed].index(sel)
                p = completed[idx]
                t = next((x for x in TENANTS if x["id"] == p.get("tenantId")), None)
                bldg = next((bl for bl in BUILDINGS if bl["id"] == (t["buildingId"] if t else "")), None)
                st.session_state.last_receipt = {
                    "receiptNo": p.get("receiptNo") or p["id"],
                    "tenantName": t["name"] if t else "—",
                    "unit": t["unit"] if t else "—",
                    "buildingName": bldg["name"] if bldg else "—",
                    "method": p.get("type", "").replace("_", " "),
                    "amount": p["amount"],
                    "currency": p.get("currency", "KES"),
                    "totalFee": p.get("totalFee", 0),
                    "totalPaid": p["amount"] + (p.get("totalFee") or 0),
                    "timestamp": p["timestamp"],
                }

# ─────────────────────────────────────────────────────────────
# RECEIPT MODAL
# ─────────────────────────────────────────────────────────────

if st.session_state.last_receipt:
    r = st.session_state.last_receipt
    with st.expander("🧾 Payment Receipt", expanded=True):
        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg,#0e1a2b,#08111c);color:white;padding:20px;border-radius:12px 12px 0 0;text-align:center;">
                <div style="font-size:28px;">✅</div>
                <div style="font-weight:700;font-size:18px;">Payment Successful</div>
                <div style="opacity:.6;font-size:13px;">Landlord notified · funds settling</div>
            </div>
            <div style="background:white;padding:20px;border:1px solid #ebe7e0;border-top:none;border-radius:0 0 12px 12px;">
                <div class="fee-row"><span>Receipt No.</span><span style="font-family:monospace;font-weight:700;">{r['receiptNo']}</span></div>
                <div class="fee-row"><span>Tenant</span><span>{r['tenantName']}</span></div>
                <div class="fee-row"><span>Unit / Building</span><span>{r['unit']}, {r['buildingName']}</span></div>
                <div class="fee-row"><span>Method</span><span>{r['method']}</span></div>
                <div class="fee-row"><span>Amount</span><span style="font-family:monospace;">{format_currency(r['amount'], r['currency'])}</span></div>
                <div class="fee-row"><span>Total fees</span><span style="font-family:monospace;">{format_currency(r['totalFee'], r['currency'])}</span></div>
                <div class="fee-row" style="border-top:2px solid #0e1a2b;padding-top:10px;margin-top:8px;font-weight:800;">
                    <span>Total paid</span><span style="font-family:monospace;color:#a88b3e;">{format_currency(r['totalPaid'], r['currency'])}</span>
                </div>
                <div class="fee-row"><span>Date</span><span>{datetime.fromisoformat(r['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Close Receipt", use_container_width=True):
            st.session_state.last_receipt = None
            st.rerun()

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────

st.markdown(
    f"""
    <div style="text-align:center;margin-top:40px;padding:20px;color:#6b6560;font-size:12.5px;">
        Mwarokin Estates · Payments — © {datetime.now().year}. All rights reserved.<br>
        Powered by Syllogism Technology Africa.
    </div>
    """,
    unsafe_allow_html=True,
)