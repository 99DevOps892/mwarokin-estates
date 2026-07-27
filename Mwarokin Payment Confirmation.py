python
"""
Mwarokin Estates · Payment Confirmation
Modern agentic Streamlit UI – fully functional upgrade
"""

import streamlit as st
from datetime import datetime
import base64
import json
from pathlib import Path

# ────────────────────────────────────────────── 
# Page config & global style
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Mwarokin Estates · Payment Ledger",
    page_icon="🏛️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --forest-900: #0E211B;
    --forest-800: #1E4A3B;
    --forest-600: #2F6B4F;
    --brass: #C9A227;
    --cream: #FCF9F0;
    --ink: #241F17;
    --muted: #635A49;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background: var(--forest-900) !important;
    color: var(--ink);
}

.stApp {
    background: linear-gradient(160deg, #0E211B 0%, #16352C 100%);
}

.block-container {
    padding-top: 1.5rem;
    max-width: 920px;
}

/* Top bar */
.topbar {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1.25rem;
}
.eyebrow {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #B68A2E;
    margin: 0 0 0.15rem 0;
}
.brandmark {
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-size: 1.85rem;
    color: #FCF9F0;
    margin: 0;
}
.brandmark em {
    font-style: italic;
    color: #EFDCA0;
}
.status-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    background: rgba(47, 107, 79, 0.25);
    border: 1px solid rgba(47, 107, 79, 0.55);
    color: #A8D5B5;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 0.35rem 0.85rem;
    border-radius: 999px;
}
.status-chip .dot {
    width: 7px;
    height: 7px;
    background: #4ADE80;
    border-radius: 50%;
    box-shadow: 0 0 6px #4ADE80;
}

/* Tabs override */
div[data-baseweb="tab-list"] {
    gap: 0.5rem;
    background: transparent !important;
    border-bottom: none !important;
}
button[data-baseweb="tab"] {
    background: rgba(252, 249, 240, 0.06) !important;
    border: 1px solid rgba(252, 249, 240, 0.12) !important;
    border-radius: 12px !important;
    color: #D4C9B0 !important;
    font-weight: 500 !important;
    padding: 0.55rem 1.1rem !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    background: #FCF9F0 !important;
    color: #1E4A3B !important;
    border-color: #FCF9F0 !important;
    box-shadow: 0 4px 14px rgba(0,0,0,0.25);
}

/* Ledger card */
.ledger-card {
    background: #FCF9F0;
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 30px 60px -20px rgba(0,0,0,0.55);
    margin-top: 1rem;
}
.ledger-grid {
    display: grid;
    grid-template-columns: 1.55fr 1fr;
    gap: 0;
}
@media (max-width: 720px) {
    .ledger-grid { grid-template-columns: 1fr; }
}
.ledger-main {
    padding: 2rem 2rem 1.5rem;
    position: relative;
}
.ledger-stub {
    background: linear-gradient(165deg, #1E4A3B 0%, #16352C 100%);
    padding: 1.75rem 1.5rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    color: #FCF9F0;
}
.success-row {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.5rem;
}
.check-badge {
    width: 42px;
    height: 42px;
    background: #2F6B4F;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.check-badge svg {
    width: 22px;
    height: 22px;
    stroke: white;
}
.success-title {
    font-family: 'Fraunces', serif;
    font-size: 1.35rem;
    font-weight: 600;
    margin: 0;
    color: #1E4A3B;
}
.success-sub {
    margin: 0.15rem 0 0;
    font-size: 0.85rem;
    color: #635A49;
}
.amount-block {
    margin-bottom: 1.4rem;
}
.amount-label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8C8271;
    margin: 0 0 0.2rem;
}
.amount-value {
    font-family: 'Fraunces', serif;
    font-size: 2.6rem;
    font-weight: 600;
    color: #1E4A3B;
    margin: 0;
    line-height: 1.1;
}
.bill-tag {
    display: inline-block;
    margin-top: 0.35rem;
    background: rgba(30, 74, 59, 0.1);
    color: #1E4A3B;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    letter-spacing: 0.04em;
}
.ledger-row {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    padding: 0.65rem 0;
    border-bottom: 1px dotted rgba(36, 31, 23, 0.14);
    font-size: 0.9rem;
}
.ledger-row .label {
    color: #635A49;
    flex-shrink: 0;
}
.ledger-row .leader {
    flex: 1;
    border-bottom: 1px dotted rgba(36, 31, 23, 0.2);
    height: 0.6em;
    margin: 0 0.3rem;
}
.ledger-row .value {
    font-weight: 500;
    text-align: right;
}
.mono {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
}
.confirmation-note {
    margin-top: 1.25rem;
    padding: 0.9rem 1rem;
    background: rgba(30, 74, 59, 0.06);
    border: 1px solid rgba(30, 74, 59, 0.15);
    border-radius: 10px;
    font-size: 0.85rem;
    line-height: 1.55;
    color: #635A49;
    display: flex;
    gap: 0.7rem;
    align-items: flex-start;
}
.confirmation-note svg {
    width: 18px;
    height: 18px;
    stroke: #1E4A3B;
    flex-shrink: 0;
    margin-top: 2px;
}
.verified-label {
    font-weight: 600;
    font-size: 0.95rem;
    margin: 1rem 0 0.15rem;
}
.verified-sub {
    font-size: 0.75rem;
    opacity: 0.7;
    margin: 0 0 1.25rem;
}
.stub-actions {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    width: 100%;
}
.stub-divider {
    height: 1px;
    background: rgba(252, 249, 240, 0.15);
    width: 100%;
    margin: 1.25rem 0 1rem;
}
.security-note {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    font-size: 0.72rem;
    opacity: 0.75;
}
.security-note svg {
    width: 14px;
    height: 14px;
}
.tear-stub {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.85rem 1.75rem;
    background: #F5F0E4;
    border-top: 2px dashed rgba(36, 31, 23, 0.18);
    font-size: 0.78rem;
    color: #635A49;
}
.footer-meta {
    display: flex;
    justify-content: center;
    gap: 1.75rem;
    margin-top: 1.5rem;
    flex-wrap: wrap;
    color: #A8C5B5;
    font-size: 0.78rem;
}
.footer-meta span {
    display: flex;
    align-items: center;
    gap: 0.35rem;
}
.footer-meta svg {
    width: 14px;
    height: 14px;
}

/* Button styling */
.stButton > button {
    width: 100%;
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 0.55rem 1rem !important;
    transition: all 0.2s ease;
}
.stButton > button[kind="primary"] {
    background: #C9A227 !important;
    color: #3B2C0F !important;
    border: none !important;
}
.stButton > button[kind="primary"]:hover {
    background: #EFDCA0 !important;
}
.stButton > button[kind="secondary"] {
    background: transparent !important;
    color: #FCF9F0 !important;
    border: 1px solid rgba(252,249,240,0.35) !important;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(252,249,240,0.1) !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Payment data (agentic / extensible)
# ──────────────────────────────────────────────
PAYMENT_DATA = {
    "rent": {
        "amount": 1250.00,
        "description": "Monthly Rent — Unit 4B (Premium Suite)",
        "reference": "MWK-R-2409-421",
        "txn_id": "TXN-MWK-82F4A1E3",
        "method": "Visa •••• 4821",
        "confirmation": "Your rent payment of $1,250.00 for Unit 4B has been applied successfully. No outstanding balance. Thank you for being a valued resident.",
        "bill_label": "Rent",
        "icon": "🏠",
    },
    "amenities": {
        "amount": 89.50,
        "description": "Amenities Package — Gym, Pool, Fibre WiFi, Concierge",
        "reference": "MWK-AMEN-0626-892",
        "txn_id": "TXN-MWK-9F3B2D7C",
        "method": "Mastercard •••• 2276",
        "confirmation": "Amenities fee of $89.50 successfully paid. Your access to the fitness centre, pool, and premium WiFi is confirmed through June 30, 2026.",
        "bill_label": "Amenities",
        "icon": "✨",
    },
    "paybill": {
        "amount": 210.30,
        "description": "Utilities & Service Paybill — Water, Electricity, Waste",
        "reference": "MWK-UB-9981-45",
        "txn_id": "TXN-MWK-3A9E7F2B",
        "method": "Bank Transfer · KCB",
        "confirmation": "Your paybill of $210.30 covering water, electricity, and waste services is confirmed. Outstanding balance: $0.00. Next meter reading on July 1.",
        "bill_label": "Paybill",
        "icon": "⚡",
    },
}

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def now_stamp() -> str:
    return datetime.now().strftime("%B %-d, %Y — %H:%M EAT")

def generate_receipt_html(d: dict) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Mwarokin Estates Receipt — {d['reference']}</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;}}
body{{font-family:'Inter',sans-serif;background:#0E211B;margin:0;padding:48px 16px;display:flex;justify-content:center;color:#241F17;}}
.receipt{{width:100%;max-width:480px;background:#FCF9F0;border-radius:6px 18px 18px 18px;box-shadow:0 30px 60px -20px rgba(0,0,0,.5);overflow:hidden;}}
.head{{padding:32px 32px 20px;text-align:center;border-bottom:1px dashed rgba(36,31,23,.14);}}
.head .brand{{font-family:'Fraunces',serif;font-weight:600;font-size:24px;margin:0;color:#1E4A3B;}}
.head .tag{{font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:#B68A2E;margin:6px 0 0;}}
.seal-wrap{{display:flex;justify-content:center;margin:22px 0 4px;}}
.amount{{font-family:'Fraunces',serif;font-weight:600;font-size:40px;text-align:center;color:#1E4A3B;margin:6px 0 2px;}}
.status{{text-align:center;font-size:12px;color:#2F6B4F;font-weight:600;letter-spacing:.04em;margin-bottom:24px;}}
.rows{{padding:0 32px 8px;}}
.row{{display:flex;justify-content:space-between;gap:10px;padding:11px 0;border-bottom:1px dotted rgba(36,31,23,.14);font-size:13px;}}
.row .l{{color:#635A49;}} .row .v{{font-weight:500;text-align:right;}}
.mono{{font-family:'JetBrains Mono',monospace;font-size:12px;}}
.note{{margin:20px 32px;padding:14px 16px;background:rgba(30,74,59,.06);border:1px solid rgba(30,74,59,.15);border-radius:10px;font-size:12.5px;line-height:1.6;color:#635A49;}}
.foot{{text-align:center;padding:18px 32px 30px;font-size:11px;color:#8C8271;}}
@media print{{body{{background:#fff;padding:0;}} .receipt{{box-shadow:none;}}}}
</style>
</head>
<body>
<div class="receipt">
  <div class="head">
    <p class="brand">Mwarokin Estates</p>
    <p class="tag">Official Payment Receipt</p>
  </div>
  <div class="seal-wrap">
    <svg width="88" height="88" viewBox="0 0 120 120">
      <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#EFDCA0"/><stop offset="50%" stop-color="#C9A227"/><stop offset="100%" stop-color="#8E6A1F"/>
      </linearGradient></defs>
      <circle cx="60" cy="60" r="56" fill="url(#g)"/>
      <circle cx="60" cy="60" r="47" fill="none" stroke="#6E501A" stroke-width="1" stroke-dasharray="2 3"/>
      <path d="M40 62l13 13 26-28" fill="none" stroke="#3B2C0F" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  </div>
  <p class="amount">${d['amount']:,.2f}</p>
  <p class="status">PAID &amp; CONFIRMED</p>
  <div class="rows">
    <div class="row"><span class="l">Bill type</span><span class="v">{d['bill_label']}</span></div>
    <div class="row"><span class="l">Description</span><span class="v">{d['description']}</span></div>
    <div class="row"><span class="l">Reference</span><span class="v mono">{d['reference']}</span></div>
    <div class="row"><span class="l">Transaction ID</span><span class="v mono">{d['txn_id']}</span></div>
    <div class="row"><span class="l">Date &amp; time</span><span class="v">{now_stamp()}</span></div>
    <div class="row" style="border-bottom:none;"><span class="l">Method</span><span class="v">{d['method']}</span></div>
  </div>
  <div class="note">{d['confirmation']}</div>
  <div class="foot">This is a digitally issued receipt from Mwarokin Estates.<br>Keep it for your records.</div>
</div>
</body>
</html>"""

def download_button_html(html_content: str, filename: str) -> str:
    b64 = base64.b64encode(html_content.encode()).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{filename}" style="text-decoration:none;width:100%;display:block;">'

# ──────────────────────────────────────────────
# Session state
# ──────────────────────────────────────────────
if "current_bill" not in st.session_state:
    st.session_state.current_bill = "rent"
if "copied" not in st.session_state:
    st.session_state.copied = False

# ──────────────────────────────────────────────
# Top bar
# ──────────────────────────────────────────────
st.markdown("""
<div class="topbar">
  <div>
    <p class="eyebrow">Mwarokin Estates · Payment Ledger</p>
    <h1 class="brandmark">Mwarokin <em>Estates</em></h1>
  </div>
  <div class="status-chip"><span class="dot"></span> Payment Confirmed</div>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Tabs
# ──────────────────────────────────────────────
tab_rent, tab_amen, tab_pay = st.tabs(["🏠  Rent  01", "✨  Amenities  02", "⚡  Paybill  03"])

def render_ledger(key: str):
    d = PAYMENT_DATA[key]
    st.session_state.current_bill = key

    # Main grid via columns
    left, right = st.columns([1.55, 1], gap="medium")

    with left:
        st.markdown(f"""
        <div class="ledger-card" style="border-radius:18px 0 0 0; margin:0;">
          <div class="ledger-main">
            <div class="success-row">
              <div class="check-badge">
                <svg viewBox="0 0 24 24" fill="none" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>
              </div>
              <div>
                <h2 class="success-title">Payment successful</h2>
                <p class="success-sub">Processed securely — your ledger has been updated in real time.</p>
              </div>
            </div>
            <div class="amount-block">
              <p class="amount-label">Amount paid</p>
              <p class="amount-value">${d['amount']:,.2f}</p>
              <span class="bill-tag">{d['bill_label']}</span>
            </div>
            <div class="ledger-row">
              <span class="label">Description</span><span class="leader"></span>
              <span class="value">{d['description']}</span>
            </div>
            <div class="ledger-row">
              <span class="label">Reference</span><span class="leader"></span>
              <span class="value mono">{d['reference']}</span>
            </div>
            <div class="ledger-row">
              <span class="label">Date &amp; time</span><span class="leader"></span>
              <span class="value">{now_stamp()}</span>
            </div>
            <div class="ledger-row">
              <span class="label">Method</span><span class="leader"></span>
              <span class="value">{d['method']}</span>
            </div>
            <div class="ledger-row" style="border-bottom:none;">
              <span class="label">Transaction ID</span><span class="leader"></span>
              <span class="value mono">{d['txn_id']}</span>
            </div>
            <div class="confirmation-note">
              <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 6l-10 7L2 6"/><rect x="2" y="4" width="20" height="16" rx="2"/></svg>
              <p>{d['confirmation']}</p>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with right:
        st.markdown("""
        <div style="background:linear-gradient(165deg,#1E4A3B 0%,#16352C 100%);
                    border-radius:0 18px 0 0; padding:1.75rem 1.4rem;
                    display:flex; flex-direction:column; align-items:center; color:#FCF9F0;">
          <svg width="110" height="110" viewBox="0 0 120 120">
            <defs>
              <linearGradient id="brassGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#EFDCA0"/>
                <stop offset="50%" stop-color="#C9A227"/>
                <stop offset="100%" stop-color="#8E6A1F"/>
              </linearGradient>
            </defs>
            <circle cx="60" cy="60" r="56" fill="url(#brassGrad)"/>
            <circle cx="60" cy="60" r="56" fill="none" stroke="#6E501A" stroke-width="1.5"/>
            <circle cx="60" cy="60" r="47" fill="none" stroke="#6E501A" stroke-width="1" stroke-dasharray="2 3"/>
            <text x="60" y="28" text-anchor="middle" font-family="JetBrains Mono, monospace" font-size="6.5" fill="#4E3A12" letter-spacing="2">MWAROKIN ESTATES</text>
            <path d="M40 62l13 13 26-28" fill="none" stroke="#3B2C0F" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
            <text x="60" y="98" text-anchor="middle" font-family="JetBrains Mono, monospace" font-size="6.5" fill="#4E3A12" letter-spacing="2">VERIFIED PAID</text>
          </svg>
          <p style="font-weight:600;font-size:0.95rem;margin:1rem 0 0.15rem;">Verified & secured</p>
          <p style="font-size:0.75rem;opacity:0.7;margin:0 0 1.25rem;">RBC-compliant audit trail</p>
        </div>
        """, unsafe_allow_html=True)

        # Action buttons
        receipt_html = generate_receipt_html(d)
        filename = f"Mwarokin_Receipt_{d['reference']}.html"

        col_dl, = st.columns(1)
        with col_dl:
            st.download_button(
                label="⬇️  Download receipt",
                data=receipt_html,
                file_name=filename,
                mime="text/html",
                type="primary",
                use_container_width=True,
                key=f"dl_{key}",
            )

        if st.button("🖨️  Print", type="secondary", use_container_width=True, key=f"print_{key}"):
            st.components.v1.html(
                f"""
                <script>
                const w = window.open('', '_blank');
                w.document.write(`{receipt_html.replace('`', '\\`')}`);
                w.document.close();
                setTimeout(() => w.print(), 400);
                </script>
                """,
                height=0,
            )

        if st.button(
            "✅  Copied!" if st.session_state.copied else "📋  Copy transaction ID",
            type="secondary",
            use_container_width=True,
            key=f"copy_{key}",
        ):
            st.session_state.copied = True
            st.code(d["txn_id"], language=None)
            st.toast(f"Copied: {d['txn_id']}", icon="✅")

        st.markdown("""
        <div style="text-align:center; margin-top:1.2rem; font-size:0.72rem; opacity:0.7; color:#FCF9F0;">
          🔒 Bank-grade encryption
        </div>
        """, unsafe_allow_html=True)

    # Tear stub
    st.markdown(f"""
    <div class="tear-stub" style="border-radius:0 0 18px 18px;">
      <span>Keep this stub for your records · <strong>{d['txn_id']}</strong></span>
      <a href="#" style="font-size:12px;color:#1E4A3B;font-weight:600;text-decoration:none;">View all bills →</a>
    </div>
    """, unsafe_allow_html=True)

# Render each tab
with tab_rent:
    render_ledger("rent")
with tab_amen:
    render_ledger("amenities")
with tab_pay:
    render_ledger("paybill")

# Footer
st.markdown("""
<div class="footer-meta">
  <span>⏱ Real-time confirmation</span>
  <span>📄 E-receipt available</span>
  <span>💲 Zero convenience fee</span>
</div>
""", unsafe_allow_html=True)