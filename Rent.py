
"""
Rent.py — Mwarokin Estates Tenant Portal
Modern, fully functional Streamlit app inspired by the provided UI.
Features: multi-currency, payment methods (M-Pesa, banks, card, SylloPay),
persistent payment history + receipts, statement, chart, notifications,
quick-pay, chatbot, and step-based payment flow.
"""

import streamlit as st
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import plotly.graph_objects as go

# ─── Paths & constants ───────────────────────────────────────────────────────
STORAGE_FILE = Path("mwarokin_rent_payments.json")
DRAFT_FILE = Path("mwarokin_rent_draft.json")

BASE_RENT = 18_000
BASE_CHARGES = 2_500
TENANT_ID = "T-789456"
PROPERTY = "Sunrise Apartments, Unit 4B"
WALLET_KES = 156_000
SYLLO_KES = 24_500

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

PM_NAMES = {
    "mpesa": "M-Pesa",
    "mobile_money": "Mobile Money",
    "bank_kenya": "Kenya Bank Transfer",
    "bank_africa": "African Bank Transfer",
    "card": "Credit/Debit Card",
    "syllopay": "SylloPay Wallet",
}

# ─── Persistence helpers ─────────────────────────────────────────────────────
def load_payments() -> list:
    if STORAGE_FILE.exists():
        try:
            return json.loads(STORAGE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def save_payment(record: dict):
    records = load_payments()
    records.insert(0, record)
    STORAGE_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")

def clear_payments():
    if STORAGE_FILE.exists():
        STORAGE_FILE.unlink()

def load_draft() -> dict:
    if DRAFT_FILE.exists():
        try:
            return json.loads(DRAFT_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_draft(data: dict):
    DRAFT_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

# ─── Formatting ──────────────────────────────────────────────────────────────
def fmt(amount: float, rate: float = 1.0) -> str:
    val = amount * rate
    if rate < 1:
        return f"{val:,.2f}"
    return f"{val:,.0f}"

def money(amount: float, code: str) -> str:
    c = CURRENCIES[code]
    return f"{c['sym']}{fmt(amount, c['rate'])}"

# ─── Session state init ──────────────────────────────────────────────────────
def init_state():
    defaults = {
        "currency": "KES",
        "step": 1,
        "active_pm": "mpesa",
        "show_success": False,
        "last_receipt": None,
        "chat_history": [
            {"role": "assistant", "content": "Hello! I'm your Mwarokin assistant. How can I help you with your rent payment today?"}
        ],
        "notifications": [
            {"color": "orange", "msg": "Your rent for October is due in 5 days.", "time": "2 hours ago"},
            {"color": "blue", "msg": "Property inspection scheduled for October 20th.", "time": "1 day ago"},
            {"color": "green", "msg": "Your September payment has been confirmed.", "time": "3 days ago"},
        ],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ─── Chatbot logic ───────────────────────────────────────────────────────────
def bot_reply(msg: str, code: str) -> str:
    m = msg.lower()
    sym = CURRENCIES[code]["sym"]
    rate = CURRENCIES[code]["rate"]
    if any(w in m for w in ("balance", "wallet")):
        return f"Your wallet balance is {sym}{fmt(WALLET_KES, rate)}. Current rent due is {sym}{fmt(20_500, rate)} for October 2024."
    if "mpesa" in m or "m-pesa" in m:
        return "For M-Pesa use Paybill 522533 with your unit number as account reference. You will receive an STK push to approve."
    if any(w in m for w in ("receipt", "confirm")):
        return "Every payment is logged with a unique transaction ID. Open Payment History and click View Receipt on any entry."
    if "bank" in m or "transfer" in m:
        return "We support 26 Kenyan banks and major African banks (Ecobank, UBA, Standard Bank, etc.). Choose Kenya Bank or African Bank."
    if "due" in m or "when" in m:
        return f"October 2024 rent of {sym}{fmt(20_500, rate)} is due on October 15th. You have 5 days remaining."
    if "history" in m or "past" in m:
        return "You have 9 on-time payments (92% rate). Full history including your logged payments is in the Payment History section."
    if any(w in m for w in ("currency", "yuan", "pound", "dollar")):
        return "Switch currencies with the selector on the balance card. Supported: KES, USD, EUR, GBP, CNY, ZAR, TZS, NGN. The currency you pay in is locked on the receipt."
    if "syllopay" in m:
        return f"SylloPay is Syllogism Technology Africa's instant wallet. Balance: {sym}{fmt(SYLLO_KES, rate)} — enough for current rent."
    return "I can help with rent payments, methods, balances, receipts and your account. What would you like to know?"

# ─── UI Components ───────────────────────────────────────────────────────────
def render_hero(code: str):
    c = CURRENCIES[code]
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#1A1A2E 0%,#16213E 100%);
                    border-radius:16px;padding:1.75rem 2rem;color:white;margin-bottom:1.5rem;">
          <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:1.5rem;">
            <div>
              <div style="font-size:0.75rem;letter-spacing:0.08em;text-transform:uppercase;
                          color:rgba(255,255,255,0.45);margin-bottom:0.35rem;">Tenant Portal</div>
              <h1 style="font-size:1.85rem;margin:0 0 0.4rem 0;font-weight:700;">Welcome back, Mwarokin Tenant</h1>
              <p style="color:rgba(255,255,255,0.55);margin:0 0 1rem 0;font-size:0.9rem;">
                Manage your rent payments easily and securely from anywhere.
              </p>
              <div style="display:flex;gap:1.5rem;flex-wrap:wrap;">
                <div><small style="color:rgba(255,255,255,0.4);">Tenant ID</small><br><strong>{TENANT_ID}</strong></div>
                <div><small style="color:rgba(255,255,255,0.4);">Property</small><br><strong>{PROPERTY}</strong></div>
                <div><small style="color:rgba(255,255,255,0.4);">Next Due</small><br><strong>Oct 15, 2024</strong></div>
              </div>
            </div>
            <div style="background:rgba(255,255,255,0.08);border-radius:12px;padding:1.25rem 1.5rem;min-width:200px;">
              <div style="font-size:0.75rem;color:rgba(255,255,255,0.5);">Wallet Balance</div>
              <div style="font-size:1.75rem;font-weight:700;color:#C9A84C;">{c['sym']}{fmt(WALLET_KES, c['rate'])}</div>
              <div style="font-size:0.75rem;color:rgba(255,255,255,0.4);margin-top:4px;">Auto-pay enabled</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_flow_steps(step: int):
    labels = ["Select Payment", "Payment Method", "Review & Confirm", "Complete"]
    cols = st.columns(4)
    for i, (col, label) in enumerate(zip(cols, labels), 1):
        with col:
            if i < step:
                st.markdown(f"**✅ {i}. {label}**")
            elif i == step:
                st.markdown(f"**🔵 {i}. {label}**")
            else:
                st.markdown(f"{i}. {label}")

def render_analytics():
    c1, c2, c3 = st.columns(3)
    c1.metric("On-time Payments", "9", help="Historical on-time count")
    c2.metric("Payment Rate", "92%")
    c3.metric("Days Until Due", "5", delta="-1 day")

def render_statement(code: str):
    st.subheader("Real-time Statement")
    paid = load_payments()
    seed = [
        {"month": "October 2024", "date": "Due: Oct 15, 2024", "amount": 20500, "status": "due"},
        {"month": "September 2024", "date": "Sep 12, 2024", "amount": 20500, "status": "paid"},
        {"month": "August 2024", "date": "Aug 10, 2024", "amount": 20500, "status": "paid"},
        {"month": "July 2024", "date": "Jul 14, 2024", "amount": 19800, "status": "paid"},
    ]
    rows = []
    for r in paid[:3]:
        rows.append({
            "Month": r["month"],
            "Date / Method": f"{r['dateDisplay']} · {r['method']}",
            "Amount": f"{r['currSym']}{fmt(r['total'])}",
            "Status": f"Paid · {r['currCode']}",
        })
    rate = CURRENCIES[code]["rate"]
    sym = CURRENCIES[code]["sym"]
    for d in seed:
        rows.append({
            "Month": d["month"],
            "Date / Method": d["date"],
            "Amount": f"{sym}{fmt(d['amount'], rate)}",
            "Status": d["status"].capitalize(),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

def render_chart(code: str):
    st.subheader("Payment History Chart (Last 6 months)")
    data = [
        ("May", 18000), ("Jun", 18000), ("Jul", 19800),
        ("Aug", 20500), ("Sep", 20500), ("Oct", 20500),
    ]
    rate = CURRENCIES[code]["rate"]
    months = [m for m, _ in data]
    amounts = [a * rate for _, a in data]
    fig = go.Figure(go.Bar(
        x=months, y=amounts,
        marker_color=["#C9A84C" if m == "Oct" else "#4A5568" for m in months],
        text=[f"{CURRENCIES[code]['sym']}{fmt(a)}" for a in amounts],
        textposition="auto",
    ))
    fig.update_layout(
        height=280, margin=dict(l=20, r=20, t=30, b=20),
        yaxis_title="Amount", xaxis_title="",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

def render_payment_form(code: str):
    st.subheader("Submit Rent Payment")
    draft = load_draft()
    rate = CURRENCIES[code]["rate"]
    sym = CURRENCIES[code]["sym"]

    with st.form("rent_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            pay_month = st.text_input("Payment Month (YYYY-MM)", value=datetime.now().strftime("%Y-%m"))
        with c2:
            pay_date = st.date_input("Payment Date", value=datetime.now())

        prop_address = st.text_input("Property Address", value=draft.get("propAddress", PROPERTY))
        c3, c4 = st.columns(2)
        with c3:
            prop_building = st.text_input("Building", value=draft.get("propBuilding", "Sunrise"))
        with c4:
            prop_unit = st.text_input("Unit Number", value=draft.get("propUnit", "4B"))

        c5, c6 = st.columns(2)
        with c5:
            tenant_phone = st.text_input("Phone Number", value=draft.get("tenantPhone", "+254704919388"))
        with c6:
            tenant_account = st.text_input("Account Number", value=draft.get("tenantAccount", TENANT_ID))

        c7, c8, c9 = st.columns(3)
        with c7:
            rent = st.number_input(f"Monthly Rent ({sym.strip()})", value=round(BASE_RENT * rate, 2 if rate < 1 else 0), min_value=0.0)
        with c8:
            charges = st.number_input(f"Other Charges ({sym.strip()})", value=round(BASE_CHARGES * rate, 2 if rate < 1 else 0), min_value=0.0)
        with c9:
            total = rent + charges
            st.metric("Total Amount", f"{sym}{fmt(total)}")

        st.markdown("**Payment Method**")
        pm = st.radio(
            "Select method",
            options=list(PM_NAMES.keys()),
            format_func=lambda x: PM_NAMES[x],
            horizontal=True,
            index=list(PM_NAMES.keys()).index(st.session_state.active_pm),
            label_visibility="collapsed",
        )
        st.session_state.active_pm = pm

        # Method-specific fields
        if pm == "mpesa":
            st.info("You will receive an M-Pesa STK push after submitting. Approve on your phone.")
            mpesa_phone = st.text_input("M-Pesa Phone", value=tenant_phone)
            st.text_input("Paybill / Till", value="522533", disabled=True)
            st.text_input("Account Reference (unit)", value=prop_unit)
        elif pm == "mobile_money":
            st.selectbox("Provider", ["M-Pesa", "Airtel Money", "T-Kash", "MTN MoMo", "Vodacom M-Pesa", "Tigo Pesa", "Orange Money", "Wave"])
            st.text_input("Mobile Number", value=tenant_phone)
        elif pm == "bank_kenya":
            st.selectbox("Bank", ["KCB Bank Kenya", "Equity Bank Kenya", "Co-operative Bank", "Absa Bank Kenya", "Stanbic Bank Kenya", "NCBA Bank", "DTB", "I&M Bank", "Family Bank"])
            c_a, c_b = st.columns(2)
            c_a.text_input("Account Number")
            c_b.text_input("Account Name")
            st.text_input("Reference / Narration", value=f"Rent Unit {prop_unit} {pay_month}")
        elif pm == "bank_africa":
            st.selectbox("African Bank", ["United Bank for Africa (UBA)", "Access Bank", "GTBank", "Standard Bank", "Ecobank", "FNB", "Absa Africa"])
            c_a, c_b = st.columns(2)
            c_a.text_input("SWIFT / BIC")
            c_b.text_input("Account Number / IBAN")
            st.text_input("Correspondent Country")
        elif pm == "card":
            st.text_input("Card Number", placeholder="1234 5678 9012 3456")
            c_a, c_b, c_c = st.columns([2, 1, 1])
            c_a.text_input("Cardholder Name")
            c_b.text_input("Expiry (MM/YY)", placeholder="MM/YY")
            c_c.text_input("CVV", type="password", max_chars=4)
            st.caption("🔒 Secured with 256-bit SSL encryption (demo)")
        elif pm == "syllopay":
            st.success(f"SylloPay Balance: {sym}{fmt(SYLLO_KES, rate)} — Sufficient · Zero fee")

        recurring = st.checkbox("Enable recurring payment")
        submitted = st.form_submit_button("🚀 Submit Payment", type="primary", use_container_width=True)

        if submitted:
            if not all([prop_address.strip(), prop_building.strip(), prop_unit.strip(), tenant_phone.strip(), tenant_account.strip()]):
                st.error("Please fill all required fields.")
                return
            # Save draft
            save_draft({
                "propAddress": prop_address,
                "propBuilding": prop_building,
                "propUnit": prop_unit,
                "tenantPhone": tenant_phone,
                "tenantAccount": tenant_account,
            })
            st.session_state.step = 3
            with st.spinner("Processing your payment securely…"):
                import time
                time.sleep(1.8)
            # Create record
            now = datetime.now()
            txn = f"TXN-{uuid.uuid4().hex[:9].upper()}"
            period = datetime.strptime(pay_month + "-01", "%Y-%m-%d").strftime("%B %Y") if pay_month else "Current Month"
            record = {
                "txnId": txn,
                "dateISO": now.isoformat(),
                "dateDisplay": now.strftime("%b %d, %Y"),
                "timeDisplay": now.strftime("%H:%M"),
                "month": period,
                "property": prop_address,
                "unit": prop_unit,
                "method": PM_NAMES[pm],
                "currCode": code,
                "currSym": sym,
                "rent": rent,
                "charges": charges,
                "total": total,
                "status": "paid",
            }
            save_payment(record)
            st.session_state.last_receipt = record
            st.session_state.show_success = True
            st.session_state.step = 4
            st.rerun()

def render_success(code: str):
    rec = st.session_state.last_receipt
    if not rec:
        return
    st.balloons()
    st.success("Payment Successful!")
    st.markdown(f"**Transaction ID:** `{rec['txnId']}`")
    st.markdown(
        f"""
        | Item | Amount |
        |------|--------|
        | Monthly Rent | {rec['currSym']}{fmt(rec['rent'])} |
        | Other Charges | {rec['currSym']}{fmt(rec['charges'])} |
        | Processing Fee | Free |
        | **Total Paid** | **{rec['currSym']}{fmt(rec['total'])}** |
        """
    )
    with st.expander("Full Receipt", expanded=True):
        st.json({
            "Transaction": rec["txnId"],
            "Date": f"{rec['dateDisplay']} · {rec['timeDisplay']}",
            "Method": rec["method"],
            "Property": rec["property"],
            "Period": rec["month"],
            "Tenant ID": TENANT_ID,
            "Currency": rec["currCode"],
            "Status": "Confirmed",
        })
    if st.button("🏠 Back to Dashboard", type="primary"):
        st.session_state.show_success = False
        st.session_state.step = 1
        st.session_state.last_receipt = None
        st.rerun()

def render_history(code: str):
    st.subheader("Payment History")
    col_f1, col_f2, col_f3, col_f4 = st.columns([1, 1, 1, 2])
    filter_choice = col_f1.selectbox("Filter", ["All", "3M", "6M", "1Y"], label_visibility="collapsed")
    if col_f4.button("🗑️ Clear my logged payments"):
        clear_payments()
        st.success("Logged payments cleared.")
        st.rerun()

    seed = [
        {"month": "September 2024", "type": "Rent + Utilities", "date": "Sep 12, 2024", "amount": 20500, "status": "paid", "currCode": "KES", "currSym": "KSh ", "isReal": False},
        {"month": "August 2024", "type": "Rent + Utilities", "date": "Aug 10, 2024", "amount": 20500, "status": "paid", "currCode": "KES", "currSym": "KSh ", "isReal": False},
        {"month": "July 2024", "type": "Rent + Utilities", "date": "Jul 14, 2024", "amount": 19800, "status": "paid", "currCode": "KES", "currSym": "KSh ", "isReal": False},
        {"month": "June 2024", "type": "Rent", "date": "Jun 11, 2024", "amount": 18000, "status": "paid", "currCode": "KES", "currSym": "KSh ", "isReal": False},
        {"month": "May 2024", "type": "Rent", "date": "May 17, 2024", "amount": 18000, "status": "paid", "currCode": "KES", "currSym": "KSh ", "isReal": False},
    ]
    real = [
        {
            "txnId": r["txnId"],
            "month": r["month"],
            "type": r["method"],
            "date": f"{r['dateDisplay']} · {r['timeDisplay']}",
            "amount": r["total"],
            "status": "paid",
            "currCode": r["currCode"],
            "currSym": r["currSym"],
            "isReal": True,
        }
        for r in load_payments()
    ]
    items = real + seed
    if filter_choice == "3M":
        items = items[:3]
    elif filter_choice == "6M":
        items = items[:6]

    if not items:
        st.info("No payments logged yet. Submit a payment to see it appear here with a receipt.")
        return

    rate = CURRENCIES[code]["rate"]
    for d in items:
        display_amt = f"{d['currSym']}{fmt(d['amount'])}" if d["isReal"] else f"{CURRENCIES[code]['sym']}{fmt(d['amount'], rate)}"
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{d['month']}** {'· ' + d['currCode'] if d['isReal'] else ''}")
            c1.caption(f"{d['type']} · {d['date']}")
            c2.markdown(f"**{display_amt}**")
            c2.caption("✅ Paid")
            if d["isReal"]:
                if st.button("🧾 View Receipt", key=f"rcpt_{d['txnId']}"):
                    rec = next((r for r in load_payments() if r["txnId"] == d["txnId"]), None)
                    if rec:
                        st.json(rec)

def render_sidebar(code: str):
    with st.sidebar:
        st.markdown("### 🏢 Mwarokin Estates")
        st.caption("Africa's premium property management platform")
        st.divider()

        # Currency switcher
        st.markdown("**Currency**")
        new_code = st.selectbox(
            "Select currency",
            options=list(CURRENCIES.keys()),
            format_func=lambda x: f"{CURRENCIES[x]['flag']} {x}",
            index=list(CURRENCIES.keys()).index(code),
            label_visibility="collapsed",
        )
        if new_code != code:
            st.session_state.currency = new_code
            st.rerun()

        st.divider()
        st.markdown("**Payment Overview**")
        st.progress(0.75, text="75% progress")
        st.metric("Monthly Rent", money(20500, code))
        st.metric("On-time", "9")
        st.metric("Rating", "4.8 ★")

        st.divider()
        st.markdown("**Quick Pay QR**")
        st.code(f"PAY:{TENANT_ID}|{money(20500, code)}", language=None)
        st.caption("Scan with mobile banking app (demo placeholder)")

        st.divider()
        st.markdown(f"**Notifications** ({len(st.session_state.notifications)})")
        for n in st.session_state.notifications:
            st.markdown(f"- {n['msg']}")
            st.caption(n["time"])

        st.divider()
        if st.button("⚡ Quick Pay (M-Pesa)", use_container_width=True, type="primary"):
            st.session_state.step = 2
            st.session_state.active_pm = "mpesa"
            # Pre-fill via draft
            save_draft({
                "propAddress": PROPERTY,
                "propBuilding": "Sunrise",
                "propUnit": "4B",
                "tenantPhone": "+254704919388",
                "tenantAccount": TENANT_ID,
            })
            st.info("Form pre-filled. Scroll to Submit Rent Payment and confirm.")
            st.rerun()

def render_chat(code: str):
    st.subheader("Mwarokin Assistant")
    st.caption("Ask anything about your rent, payments, or property.")
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    if prompt := st.chat_input("Ask a question..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        reply = bot_reply(prompt, code)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.rerun()

# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Mwarokin Estates — Rent Portal",
        page_icon="🏢",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_state()
    code = st.session_state.currency

    # Custom CSS polish
    st.markdown(
        """
        <style>
        .stApp { background-color: #0F0F1A; }
        h1, h2, h3 { color: #F5F5F5 !important; }
        div[data-testid="stMetricValue"] { color: #C9A84C; }
        .stButton>button { border-radius: 8px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    render_sidebar(code)
    render_hero(code)
    render_flow_steps(st.session_state.step)

    if st.session_state.show_success:
        render_success(code)
        return

    # Main layout
    left, right = st.columns([2.2, 1])
    with left:
        render_analytics()
        st.divider()
        render_statement(code)
        st.divider()
        render_chart(code)
        st.divider()
        render_payment_form(code)
        st.divider()
        render_history(code)

    with right:
        st.markdown("### Quick Info")
        st.info(f"Next due: **Oct 15, 2024**\n\nAmount: **{money(20500, code)}**")
        st.success("Auto-pay is enabled")
        st.markdown("---")
        st.markdown("**Supported Methods**")
        st.markdown("- 📱 M-Pesa / Mobile Money\n- 🏦 26+ Kenyan banks\n- 🌍 Pan-African banks\n- 💳 Card (Visa/MC)\n- ⚡ SylloPay Wallet")

    st.divider()
    render_chat(code)

    st.markdown(
        """
        <div style="text-align:center;color:#666;font-size:0.8rem;margin-top:2rem;">
          Mwarokin Estates © 2026. All Rights Reserved.<br>
          Powered by Syllogism Technology Africa
        </div>
        """,
        unsafe_allow_html=True,
    )

if __name__ == "__main__":
    main()
