#!/usr/bin/env python3
"""
Mwarokin Estates — Rent Payment Portal (Python / Streamlit)
Modern, fully functional upgrade of the original HTML/JS tenant payment UI.
Real local persistence (SQLite), multi-currency, flat fees, Lipa Mdogo,
payment history, receipts, bills engine, simulated rails, and a rule-based assistant.
"""

from __future__ import annotations

import json
import math
import random
import sqlite3
import string
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
APP_TITLE = "Mwarokin Estates · Rent Payment"
DB_PATH = Path("mwarokin_rent.db")
TENANT_ID = "MWK-0123"
DEFAULT_BUILDING = "Sunrise"
DEFAULT_UNIT = "4B"
BASE_RENT_KES = 18_000
FEE_MIN, FEE_MAX = 1, 5  # flat KSh 1–5 on every rail

PROPERTY = {
    "tenant_id": TENANT_ID,
    "building": DEFAULT_BUILDING,
    "unit": DEFAULT_UNIT,
    "landlord_name": "Mwarokin Property Holdings Ltd",
    "landlord_paybill": "522533",
    "landlord_till": "9004471",
    "landlord_account_ref": f"{TENANT_ID}-{DEFAULT_UNIT}",
}

CURRENCIES = {
    "KES": {"sym": "KSh ", "rate": 1.0, "flag": "🇰🇪"},
    "USD": {"sym": "$", "rate": 0.0077, "flag": "🇺🇸"},
    "EUR": {"sym": "€", "rate": 0.0071, "flag": "🇪🇺"},
    "GBP": {"sym": "£", "rate": 0.0061, "flag": "🇬🇧"},
    "CNY": {"sym": "¥", "rate": 0.056, "flag": "🇨🇳"},
    "ZAR": {"sym": "R ", "rate": 0.143, "flag": "🇿🇦"},
    "TZS": {"sym": "TSh ", "rate": 20.5, "flag": "🇹🇿"},
    "NGN": {"sym": "₦", "rate": 11.8, "flag": "🇳🇬"},
}

PM_META = {
    "mpesa": {"label": "M-Pesa", "icon": "📲", "fee_label": "M-Pesa Transaction Fee"},
    "mobile_money": {"label": "Airtel Money", "icon": "📲", "fee_label": "Airtel Money Fee"},
    "bank_kenya": {"label": "Bank (Kenya)", "icon": "🏦", "fee_label": "Bank Transfer Fee"},
    "bank_africa": {"label": "African Bank", "icon": "🌍", "fee_label": "Pan-African Bank Fee"},
    "card": {"label": "Card", "icon": "💳", "fee_label": "Card Processing Fee"},
    "syllopay": {"label": "SylloPay", "icon": "⚡", "fee_label": "SylloPay Fee"},
    "crypto": {"label": "Crypto", "icon": "🪙", "fee_label": "Crypto Network + Gateway Fee"},
}

AMENITY_CATALOGUE = [
    {"key": "water", "label": "Water", "icon": "💧", "base": 900, "variance": 250},
    {"key": "garbage", "label": "Garbage Collection", "icon": "🗑️", "base": 400, "variance": 0},
    {"key": "security", "label": "Security & Gate", "icon": "🛡️", "base": 600, "variance": 0},
    {"key": "parking", "label": "Parking", "icon": "🚗", "base": 500, "variance": 0},
    {"key": "internet", "label": "Estate WiFi", "icon": "📶", "base": 300, "variance": 0},
    {"key": "service", "label": "Service Charge", "icon": "🧹", "base": 800, "variance": 100},
    {"key": "power_bk", "label": "Backup Power Levy", "icon": "🔋", "base": 250, "variance": 0},
]

CRYPTO_RATES_KES = {"BTC": 6_250_000.0, "ETH": 325_000.0, "USDT": 129.30, "USDC": 129.30}

# ─────────────────────────────────────────────────────────────
# DATA MODELS
# ─────────────────────────────────────────────────────────────
@dataclass
class BillLine:
    key: str
    label: str
    icon: str
    amount: float  # always stored in KES

@dataclass
class PaymentRecord:
    txn_id: str
    date_iso: str
    date_display: str
    time_display: str
    month: str
    property: str
    unit: str
    building: str
    tenant_id: str
    method: str
    rail_ref: str
    curr_code: str
    curr_sym: str
    rent: float          # display currency
    charges: float
    fee: float
    due: float
    total: float
    balance: float
    is_partial: bool
    status: str
    bill_lines: List[Dict[str, Any]] = field(default_factory=list)

# ─────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    with get_conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS payments (
                txn_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS bills (
                tenant_month TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS landlord_notifs (
                id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS drafts (
                tenant_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            );
            """
        )

def save_payment(rec: PaymentRecord) -> None:
    with get_conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO payments (txn_id, payload, created_at) VALUES (?,?,?)",
            (rec.txn_id, json.dumps(asdict(rec)), rec.date_iso),
        )

def load_payments(limit: int = 100) -> List[PaymentRecord]:
    with get_conn() as c:
        rows = c.execute(
            "SELECT payload FROM payments ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    out: List[PaymentRecord] = []
    for r in rows:
        d = json.loads(r["payload"])
        out.append(PaymentRecord(**d))
    return out

def clear_payments() -> None:
    with get_conn() as c:
        c.execute("DELETE FROM payments")

def save_bills(tenant_month: str, lines: List[BillLine]) -> None:
    payload = json.dumps([asdict(l) for l in lines])
    with get_conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO bills (tenant_month, payload) VALUES (?,?)",
            (tenant_month, payload),
        )

def load_bills(tenant_month: str) -> List[BillLine]:
    with get_conn() as c:
        row = c.execute(
            "SELECT payload FROM bills WHERE tenant_month=?", (tenant_month,)
        ).fetchone()
    if not row:
        return []
    return [BillLine(**x) for x in json.loads(row["payload"])]

def push_landlord_notif(payload: Dict[str, Any]) -> None:
    nid = "DEP-" + "".join(random.choices(string.digits, k=6))
    with get_conn() as c:
        c.execute(
            "INSERT INTO landlord_notifs (id, payload, created_at) VALUES (?,?,?)",
            (nid, json.dumps(payload), datetime.utcnow().isoformat()),
        )

def load_landlord_notifs(limit: int = 8) -> List[Dict[str, Any]]:
    with get_conn() as c:
        rows = c.execute(
            "SELECT payload, created_at FROM landlord_notifs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{**json.loads(r["payload"]), "time_iso": r["created_at"]} for r in rows]

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def seeded_variance(seed: str, spread: int) -> int:
    h = 0
    for ch in seed:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    frac = (h % 1000) / 1000.0
    return int(round((frac - 0.5) * 2 * spread))

def generate_monthly_bills(tenant_id: str, month_key: str) -> List[BillLine]:
    tm = f"{tenant_id}:{month_key}"
    existing = load_bills(tm)
    if existing:
        return existing
    lines = []
    for a in AMENITY_CATALOGUE:
        amt = a["base"] + seeded_variance(tm + a["key"], a["variance"])
        lines.append(BillLine(a["key"], a["label"], a["icon"], float(amt)))
    save_bills(tm, lines)
    return lines

def fmt_amount(n: float, curr: str) -> str:
    rate = CURRENCIES[curr]["rate"]
    decimals = 2 if rate < 1 else 0
    return f"{n:,.{decimals}f}"

def roll_fee() -> int:
    return random.randint(FEE_MIN, FEE_MAX)

def next_due_kes(rent_kes: float, bills: List[BillLine]) -> float:
    return rent_kes + sum(b.amount for b in bills)

def make_txn_id() -> str:
    return "TXN-" + "".join(random.choices(string.digits, k=9))

def time_ago(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", ""))
        mins = int((datetime.utcnow() - dt).total_seconds() // 60)
        if mins < 1:
            return "just now"
        if mins < 60:
            return f"{mins} min ago"
        hrs = mins // 60
        if hrs < 24:
            return f"{hrs} hr ago"
        return f"{hrs // 24} day(s) ago"
    except Exception:
        return "recently"

# ─────────────────────────────────────────────────────────────
# AGENTIC LAYER (simple decision helpers)
# ─────────────────────────────────────────────────────────────
class PaymentAgent:
    """Lightweight agent that recommends rail, validates, and builds rail references."""

    @staticmethod
    def recommend_method(amount_kes: float, has_syllopay_balance: bool) -> str:
        if has_syllopay_balance and amount_kes <= 25_000:
            return "syllopay"
        if amount_kes < 5_000:
            return "mpesa"
        if amount_kes > 100_000:
            return "bank_kenya"
        return "mpesa"

    @staticmethod
    def build_rail_ref(pm: str, mpesa_dest: str, manual_num: str = "") -> str:
        if pm == "mpesa":
            if mpesa_dest == "auto":
                return f"Landlord Paybill {PROPERTY['landlord_paybill']} (auto-connected)"
            return f"Paybill/Till {manual_num or '—'} (manual)"
        if pm == "mobile_money":
            return "Landlord Mobile Money Account (auto-connected)"
        if pm in ("bank_kenya", "bank_africa"):
            return f"Landlord Bank · Ref {random.randint(10000, 99999)}"
        if pm == "crypto":
            return "Landlord Crypto Wallet (demo address)"
        if pm == "card":
            return f"Card •••• {random.randint(1000, 9999)} → Landlord Settlement"
        if pm == "syllopay":
            return "SylloPay Instant → Landlord SylloPay Wallet"
        return "—"

    @staticmethod
    def validate(fields: Dict[str, Any], pay_mode: str, partial: float) -> List[str]:
        errs = []
        for k in ("prop_address", "prop_building", "prop_unit", "tenant_phone", "tenant_account"):
            if not str(fields.get(k, "")).strip():
                errs.append(f"Missing: {k.replace('_', ' ').title()}")
        if pay_mode == "partial" and (not partial or partial <= 0):
            errs.append("Partial amount must be > 0")
        return errs

# ─────────────────────────────────────────────────────────────
# CHATBOT
# ─────────────────────────────────────────────────────────────
def bot_reply(msg: str, ctx: Dict[str, Any]) -> str:
    m = msg.lower()
    due = ctx.get("next_due_disp", "—")
    if any(w in m for w in ("bill", "amenit")):
        return "Your Manage Bills panel is fully editable. Change any amount and the total recalculates instantly, or add a new line item."
    if any(w in m for w in ("paybill", "till")):
        return f"M-Pesa auto-connects to landlord paybill {PROPERTY['landlord_paybill']}. Toggle to manual if needed."
    if any(w in m for w in ("partial", "mdogo", "portion")):
        return "Choose 'Pay a portion (Lipa Mdogo)' to pay in instalments. Receipts show remaining balance."
    if any(w in m for w in ("fee", "processing")):
        return "Every rail carries only a flat KSh 1–5 Mwarokin transaction fee, shown live before you submit."
    if any(w in m for w in ("mpesa", "m-pesa")):
        return "M-Pesa auto-connects to your landlord's paybill by default."
    if any(w in m for w in ("crypto", "bitcoin", "btc", "usdt")):
        return "We accept BTC, ETH, USDT and USDC. Quotes use local reference rates."
    if any(w in m for w in ("receipt", "confirm")):
        return "Every payment is logged with a transaction ID, itemised breakdown and landlord posting reference."
    if any(w in m for w in ("landlord", "deposit")):
        return "When payment clears, the landlord account is notified with tenant ID, unit, building and amount."
    if any(w in m for w in ("due", "when")):
        return f"Your next rent + bills total is approximately {due}. Check the countdown on the dashboard."
    if "currency" in m:
        return "Switch currencies in the sidebar. The currency you pay in is locked onto that receipt."
    return (
        "I can help with rent payments, bills, methods, fees, receipts and landlord "
        "deposit notifications. What would you like to know?"
    )

# ─────────────────────────────────────────────────────────────
# STREAMLIT APP
# ─────────────────────────────────────────────────────────────
def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🏢",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_db()

    # ── session state defaults ──
    ss = st.session_state
    if "curr" not in ss:
        ss.curr = "KES"
    if "fee_kes" not in ss:
        ss.fee_kes = roll_fee()
    if "active_pm" not in ss:
        ss.active_pm = "mpesa"
    if "pay_mode" not in ss:
        ss.pay_mode = "full"
    if "mpesa_dest" not in ss:
        ss.mpesa_dest = "auto"
    if "chat" not in ss:
        ss.chat = [
            {
                "role": "bot",
                "text": "Hello! I'm your Mwarokin assistant. How can I help you with your rent payment today?",
            }
        ]
    if "step" not in ss:
        ss.step = 1
    if "last_receipt" not in ss:
        ss.last_receipt = None
    if "show_success" not in ss:
        ss.show_success = False

    curr = ss.curr
    rate = CURRENCIES[curr]["rate"]
    sym = CURRENCIES[curr]["sym"]

    # ── sidebar ──
    with st.sidebar:
        st.markdown("### 🏢 Mwarokin Estates")
        st.caption("Tenant Portal · Rent Payment")
        st.divider()
        new_curr = st.selectbox(
            "Currency",
            list(CURRENCIES.keys()),
            index=list(CURRENCIES.keys()).index(curr),
            format_func=lambda c: f"{CURRENCIES[c]['flag']} {c}",
        )
        if new_curr != curr:
            ss.curr = new_curr
            st.rerun()
        st.caption("Rates are indicative reference rates (local).")
        st.divider()
        st.markdown(f"**Tenant ID**  \n`{PROPERTY['tenant_id']}`")
        st.markdown(f"**Home**  \n{PROPERTY['building']} · Unit {PROPERTY['unit']}")
        st.divider()
        if st.button("🔄 Roll new fee (KSh 1–5)", use_container_width=True):
            ss.fee_kes = roll_fee()
            st.rerun()
        st.caption(f"Current flat fee: **KSh {ss.fee_kes}**")

    # ── header ──
    st.title("Welcome back, Mwarokin Tenant")
    st.markdown(
        "Pay this month's rent, bills and amenities in one secure checkout — "
        "mobile money, bank, card, SylloPay or crypto. Every shilling posts to "
        "your landlord's property account instantly *(demo simulation)*."
    )

    # ── success screen ──
    if ss.show_success and ss.last_receipt:
        rec: PaymentRecord = ss.last_receipt
        st.success("✅ Payment processed")
        st.subheader(
            "Partial Payment Received" if rec.is_partial else "Payment Successful"
        )
        st.write(
            "Your instalment has been posted."
            if rec.is_partial
            else "Your rent has been processed and posted to your landlord's property account."
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("Transaction ID", rec.txn_id)
        c2.metric("Amount Paid", f"{rec.curr_sym}{fmt_amount(rec.total, rec.curr_code)}")
        c3.metric("Status", "Partial" if rec.is_partial else "Confirmed")
        with st.expander("Full receipt", expanded=True):
            st.json(asdict(rec), expanded=False)
            st.markdown(
                f"""
| Field | Value |
|-------|-------|
| Date | {rec.date_display} · {rec.time_display} |
| Method | {rec.method} |
| Property | {rec.property} |
| Period | {rec.month} |
| Tenant / Unit | {rec.tenant_id} · {rec.building} {rec.unit} |
| Posted To | {rec.rail_ref} |
| Rent | {rec.curr_sym}{fmt_amount(rec.rent, rec.curr_code)} |
| Bills | {rec.curr_sym}{fmt_amount(rec.charges, rec.curr_code)} |
| Fee | {rec.curr_sym}{fmt_amount(rec.fee, rec.curr_code)} |
| **Total** | **{rec.curr_sym}{fmt_amount(rec.total, rec.curr_code)}** |
| Balance | {rec.curr_sym}{fmt_amount(rec.balance, rec.curr_code)} |
"""
            )
        if st.button("← Back to dashboard", type="primary"):
            ss.show_success = False
            ss.last_receipt = None
            ss.step = 1
            st.rerun()
        st.stop()

    # ── month / identity ──
    today = datetime.now()
    default_month = today.strftime("%Y-%m")
    col_a, col_b, col_c = st.columns([1, 1, 1])
    with col_a:
        pay_month = st.text_input("Payment Month (YYYY-MM)", value=default_month)
    with col_b:
        pay_date = st.date_input("Payment Date", value=today.date())
    with col_c:
        days_until = max(0, (datetime(today.year, today.month % 12 + 1, 5) - today).days)
        st.metric("Days until due (approx)", days_until)

    month_key = pay_month.strip() or default_month
    bills = generate_monthly_bills(TENANT_ID, month_key)
    bills_total_kes = sum(b.amount for b in bills)
    rent_disp = BASE_RENT_KES * rate
    charges_disp = bills_total_kes * rate
    fee_disp = ss.fee_kes * rate
    due_disp = rent_disp + charges_disp + fee_disp

    # ── analytics strip ──
    a1, a2, a3 = st.columns(3)
    a1.metric("On-time Payments", "9")
    a2.metric("Payment Rate", "92%")
    a3.metric("Days Until Due", days_until)

    # ── statement + bills ──
    left, right = st.columns([2, 1])

    with left:
        st.subheader("Real-time Statement")
        payments = load_payments()
        stmt_rows = []
        for p in payments[:3]:
            stmt_rows.append(
                {
                    "Month": p.month,
                    "Date": f"{p.date_display} · {p.method}",
                    "Amount": f"{p.curr_sym}{fmt_amount(p.total, p.curr_code)}",
                    "Status": "Partial" if p.is_partial else "Paid",
                }
            )
        next_due = next_due_kes(BASE_RENT_KES, bills)
        stmt_rows.append(
            {
                "Month": "This Month",
                "Date": "Due soon",
                "Amount": f"{sym}{fmt_amount(next_due * rate, curr)}",
                "Status": "Due",
            }
        )
        st.dataframe(stmt_rows, use_container_width=True, hide_index=True)

        st.subheader(f"Manage Bills — {month_key}")
        edited = []
        for i, line in enumerate(bills):
            c1, c2, c3 = st.columns([3, 2, 1])
            with c1:
                st.write(f"{line.icon} {line.label}")
            with c2:
                new_amt = st.number_input(
                    f"amt_{i}",
                    value=float(line.amount),
                    min_value=0.0,
                    step=50.0,
                    key=f"bill_{month_key}_{i}",
                    label_visibility="collapsed",
                )
            with c3:
                if st.button("✕", key=f"rm_{i}"):
                    bills.pop(i)
                    save_bills(f"{TENANT_ID}:{month_key}", bills)
                    st.rerun()
            edited.append(
                BillLine(line.key, line.label, line.icon, float(new_amt))
            )
        if edited != bills:
            save_bills(f"{TENANT_ID}:{month_key}", edited)
            bills = edited
            bills_total_kes = sum(b.amount for b in bills)
            charges_disp = bills_total_kes * rate
            due_disp = rent_disp + charges_disp + fee_disp

        if st.button("＋ Add line item"):
            bills.append(
                BillLine(f"custom_{int(time.time())}", "New Line Item", "📄", 0.0)
            )
            save_bills(f"{TENANT_ID}:{month_key}", bills)
            st.rerun()

        st.caption(
            f"Total Bills & Amenities: **{sym}{fmt_amount(bills_total_kes * rate, curr)}**"
        )

    with right:
        st.subheader("Payment Overview")
        st.progress(0.75, text="Progress 75%")
        st.metric("Monthly Rent + Bills", f"{sym}{fmt_amount(next_due * rate, curr)}")
        st.metric("On-time", "9")
        st.metric("Rating", "4.8 ★")

        st.subheader("Notifications")
        notifs = load_landlord_notifs()
        if notifs:
            for n in notifs[:4]:
                kind = "partial" if n.get("type") == "partial" else "full"
                st.info(
                    f"Landlord notified: {kind} deposit of "
                    f"{n.get('curr_sym','')}{fmt_amount(n.get('amount',0), n.get('curr_code','KES'))} "
                    f"for {n.get('tenant_id')} · {n.get('building')} {n.get('unit')} "
                    f"({n.get('month')}). · {time_ago(n.get('time_iso',''))}"
                )
        st.warning(
            f"Your rent for next period of {sym}{fmt_amount(next_due * rate, curr)} is due soon."
        )

    st.divider()

    # ── payment form ──
    st.subheader("Submit Rent Payment")
    st.info(
        "Submitting a payment posts it — with its own transaction ID, fee breakdown "
        "and receipt — to the property's ledger in real time *(simulated)*. "
        "Wire a licensed processor on a backend to move real money."
    )

    f1, f2 = st.columns(2)
    with f1:
        prop_address = st.text_input(
            "Property Address",
            value=f"{PROPERTY['building']} Apartments, Unit {PROPERTY['unit']}, Nairobi",
        )
        prop_building = st.text_input("Building", value=PROPERTY["building"])
        tenant_phone = st.text_input("Phone Number", value="+254 704 919 388")
    with f2:
        prop_unit = st.text_input("Unit Number", value=PROPERTY["unit"])
        tenant_account = st.text_input(
            "Account Number", value=PROPERTY["landlord_account_ref"]
        )

    r1, r2, r3 = st.columns(3)
    with r1:
        rent_in = st.number_input(
            "Monthly Rent", value=float(round(rent_disp, 2 if rate < 1 else 0)), step=100.0
        )
    with r2:
        st.number_input(
            "Bills & Amenities",
            value=float(round(charges_disp, 2 if rate < 1 else 0)),
            disabled=True,
        )
    with r3:
        st.number_input(
            "Transaction Fee (flat)",
            value=float(round(fee_disp, 2 if rate < 1 else 0)),
            disabled=True,
        )

    mode = st.radio(
        "Amount mode",
        ["full", "partial"],
        format_func=lambda x: "Pay in full" if x == "full" else "Pay a portion (Lipa Mdogo)",
        horizontal=True,
        index=0 if ss.pay_mode == "full" else 1,
    )
    ss.pay_mode = mode
    partial_amt = 0.0
    if mode == "partial":
        partial_amt = st.number_input(
            "Amount you're paying now",
            min_value=0.0,
            value=float(round(due_disp * 0.3, 2 if rate < 1 else 0)),
            step=100.0,
        )

    paying_now = due_disp if mode == "full" else min(partial_amt, due_disp)
    st.metric("Total Amount Due / Paying Now", f"{sym}{fmt_amount(paying_now, curr)}")

    # payment methods
    st.markdown("**Payment Method**")
    pm_cols = st.columns(len(PM_META))
    for i, (k, meta) in enumerate(PM_META.items()):
        with pm_cols[i]:
            if st.button(
                f"{meta['icon']}\n{meta['label']}\nKSh 1–5",
                key=f"pm_{k}",
                use_container_width=True,
                type="primary" if ss.active_pm == k else "secondary",
            ):
                ss.active_pm = k
                ss.fee_kes = roll_fee()
                ss.step = 2
                st.rerun()

    active = ss.active_pm
    st.caption(f"Selected: **{PM_META[active]['label']}** · Fee KSh {ss.fee_kes}")

    # method detail panels
    if active == "mpesa":
        dest = st.radio(
            "Destination",
            ["auto", "manual"],
            format_func=lambda x: (
                "Auto-connect to Landlord"
                if x == "auto"
                else "Enter Paybill/Till manually"
            ),
            horizontal=True,
            index=0 if ss.mpesa_dest == "auto" else 1,
        )
        ss.mpesa_dest = dest
        if dest == "auto":
            st.success(f"Landlord Paybill **{PROPERTY['landlord_paybill']}**")
            manual_num = ""
        else:
            manual_num = st.text_input("Paybill / Till Number")
        mpesa_phone = st.text_input("M-Pesa Phone", value=tenant_phone)
        mpesa_ref = st.text_input("Account Reference (unit)", value=prop_unit)
    elif active == "crypto":
        asset = st.selectbox("Asset", ["USDT", "BTC", "ETH", "USDC"])
        network = st.selectbox("Network", ["TRC20", "ERC20", "BEP20", "BTC"])
        total_kes = paying_now / rate if rate else paying_now
        cr = CRYPTO_RATES_KES.get(asset, CRYPTO_RATES_KES["USDT"])
        crypto_amt = total_kes / cr if cr else 0
        decimals = 8 if asset == "BTC" else (6 if asset == "ETH" else 2)
        st.info(
            f"Amount due in asset: **{crypto_amt:.{decimals}f} {asset}**  \n"
            f"Deposit address: `Twk9…MwEst4B` (demo) · Network {network}"
        )
    elif active == "syllopay":
        bal = 24_500 * rate
        st.success(f"SylloPay Balance: **{sym}{fmt_amount(bal, curr)}** — sufficient")
    elif active == "card":
        st.text_input("Card Number", placeholder="1234 5678 9012 3456")
        c1, c2, c3 = st.columns(3)
        c1.text_input("Cardholder Name")
        c2.text_input("Expiry MM/YY", placeholder="MM/YY")
        c3.text_input("CVV", type="password", max_chars=4)
        st.caption("Card data would be tokenised by a PCI-compliant processor in production.")
    elif active in ("bank_kenya", "bank_africa"):
        st.selectbox(
            "Bank",
            ["KCB", "Equity", "Co-op", "Absa", "NCBA", "DTB", "Ecobank", "UBA", "FNB"],
        )
        st.text_input("Account Number")
        st.text_input("Account Name / SWIFT")

    # agent recommendation
    rec_pm = PaymentAgent.recommend_method(next_due, True)
    if rec_pm != active:
        st.caption(
            f"💡 Agent suggestion: **{PM_META[rec_pm]['label']}** may be optimal for this amount."
        )

    # submit
    b1, b2, b3 = st.columns([1, 1, 2])
    with b1:
        if st.button("Recalculate", use_container_width=True):
            ss.fee_kes = roll_fee()
            st.rerun()
    with b3:
        submit = st.button("🚀 Submit Payment", type="primary", use_container_width=True)

    if submit:
        fields = {
            "prop_address": prop_address,
            "prop_building": prop_building,
            "prop_unit": prop_unit,
            "tenant_phone": tenant_phone,
            "tenant_account": tenant_account,
        }
        errs = PaymentAgent.validate(fields, mode, partial_amt)
        if errs:
            for e in errs:
                st.error(e)
        else:
            ss.step = 3
            with st.spinner("Processing payment securely…"):
                time.sleep(1.6)
            now = datetime.now()
            txn = make_txn_id()
            fee_d = ss.fee_kes * rate
            due_d = rent_in + charges_disp + fee_d
            pay_d = due_d if mode == "full" else min(partial_amt, due_d)
            bal_d = max(due_d - pay_d, 0)
            is_partial = mode == "partial" and bal_d > 0
            rail = PaymentAgent.build_rail_ref(
                active,
                ss.mpesa_dest,
                manual_num if active == "mpesa" and ss.mpesa_dest == "manual" else "",
            )
            period = datetime.strptime(month_key + "-01", "%Y-%m-%d").strftime("%B %Y")
            rec = PaymentRecord(
                txn_id=txn,
                date_iso=now.isoformat(),
                date_display=now.strftime("%d %b %Y"),
                time_display=now.strftime("%H:%M"),
                month=period,
                property=prop_address,
                unit=prop_unit,
                building=prop_building,
                tenant_id=TENANT_ID,
                method=PM_META[active]["fee_label"],
                rail_ref=rail,
                curr_code=curr,
                curr_sym=sym,
                rent=rent_in,
                charges=charges_disp,
                fee=fee_d,
                due=due_d,
                total=pay_d,
                balance=bal_d,
                is_partial=is_partial,
                status="partial" if is_partial else "paid",
                bill_lines=[asdict(b) for b in bills],
            )
            save_payment(rec)
            push_landlord_notif(
                {
                    "tenant_id": TENANT_ID,
                    "unit": prop_unit,
                    "building": prop_building,
                    "amount": pay_d,
                    "curr_code": curr,
                    "curr_sym": sym,
                    "type": "partial" if is_partial else "full",
                    "month": period,
                    "posted_to": rail,
                }
            )
            ss.last_receipt = rec
            ss.show_success = True
            ss.step = 4
            st.rerun()

    st.divider()

    # ── history ──
    st.subheader("Payment History")
    filt = st.radio("Filter", ["All", "3M", "6M"], horizontal=True)
    hist = load_payments()
    if filt == "3M":
        hist = hist[:3]
    elif filt == "6M":
        hist = hist[:6]
    if not hist:
        st.caption("No payments logged yet. Submit a payment above.")
    else:
        for p in hist:
            with st.container():
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.markdown(
                    f"**{p.month}** `{p.curr_code}`  \n"
                    f"{p.method} · {p.date_display} {p.time_display}"
                )
                c2.markdown(
                    f"**{p.curr_sym}{fmt_amount(p.total, p.curr_code)}**  \n"
                    f"{'Partial' if p.is_partial else 'Paid'}"
                )
                if c3.button("Receipt", key=f"rc_{p.txn_id}"):
                    st.json(asdict(p))
        if st.button("Clear my logged payments"):
            clear_payments()
            st.rerun()

    # ── chart (simple) ──
    st.subheader("Payment History Chart (last 6 months)")
    chart_data = {
        "Month": ["-5mo", "-4mo", "-3mo", "-2mo", "-1mo", "Now"],
        "Amount KES": [18000, 18000, 19800, 20500, 20500, int(next_due)],
    }
    st.bar_chart(chart_data, x="Month", y="Amount KES", height=200)

    # ── chatbot ──
    st.divider()
    st.subheader("Mwarokin Assistant")
    for m in ss.chat:
        with st.chat_message("assistant" if m["role"] == "bot" else "user"):
            st.write(m["text"])
    user_q = st.chat_input("Ask a question about rent, bills, fees…")
    if user_q:
        ss.chat.append({"role": "user", "text": user_q})
        reply = bot_reply(
            user_q,
            {"next_due_disp": f"{sym}{fmt_amount(next_due * rate, curr)}"},
        )
        ss.chat.append({"role": "bot", "text": reply})
        st.rerun()

    # ── footer ──
    st.divider()
    st.caption(
        "Mwarokin Estates © 2026 · Powered by Syllogism Technology Africa · "
        "Demo frontend — connect real Daraja / Stripe / SylloPay / crypto gateways for production."
    )
    st.caption(
        "Go-live: implement POST /api/mpesa/stkpush, bank transfer, card charge, "
        "SylloPay debit and crypto invoice endpoints on a secure backend. Never put secrets in the client."
    )


if __name__ == "__main__":
    main()
