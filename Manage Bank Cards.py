```python
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import time
import plotly.express as px
import plotly.graph_objects as go
from streamlit_elements import elements, mui, html, dashboard, nivo

# Page Configuration
st.set_page_config(
    page_title="Mwarokin Estates – Manage Bank Cards",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - Premium Dark Theme matching the UI
st.markdown("""
<style>
    .main {
        background: #0b0d15;
        color: #f0f2f8;
    }
    .stApp {
        background: #0b0d15;
    }
    .sidebar .sidebar-content {
        background: #12162a;
    }
    .card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 24px;
        padding: 24px;
        transition: all 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    }
    .card:hover {
        background: rgba(255,255,255,0.08);
        border-color: rgba(212,161,69,0.25);
        transform: translateY(-4px);
        box-shadow: 0 20px 60px rgba(0,0,0,0.6);
    }
    .gold-gradient {
        background: linear-gradient(135deg, #d4a145 0%, #f0d080 50%, #b8883a 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stat-value {
        font-size: 28px;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .btn-gold {
        background: linear-gradient(135deg, #d4a145 0%, #f0d080 50%, #b8883a 100%);
        color: #0b0d15;
        border: none;
        font-weight: 600;
        padding: 10px 22px;
        border-radius: 40px;
    }
    .modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
    }
</style>
""", unsafe_allow_html=True)

# Data
if 'cards' not in st.session_state:
    st.session_state.cards = [
        {
            "id": 1,
            "type": "Visa",
            "number": "•••• •••• •••• 4821",
            "expiry": "06/27",
            "holder": "James Donovan",
            "balance": 84500,
            "default": True,
            "icon": "💳"
        },
        {
            "id": 2,
            "type": "Mastercard",
            "number": "•••• •••• •••• 7356",
            "expiry": "11/28",
            "holder": "James Donovan",
            "balance": 132000,
            "default": False,
            "icon": "💳"
        },
        {
            "id": 3,
            "type": "Amex",
            "number": "•••• •••• •••• 2390",
            "expiry": "03/29",
            "holder": "James Donovan",
            "balance": 68000,
            "default": False,
            "icon": "💳"
        }
    ]

if 'events' not in st.session_state:
    st.session_state.events = [
        {"title": "Estate Inspection", "date": "2026-06-28", "time": "09:00 AM", "color": "#d4a145"},
        {"title": "Rent Payment Due", "date": "2026-07-01", "time": "11:59 PM", "color": "#4f7cff"},
        {"title": "Board Meeting", "date": "2026-07-05", "time": "02:00 PM", "color": "#2ed573"},
    ]

if 'transactions' not in st.session_state:
    st.session_state.transactions = [
        {"name": "Rent Payment — Unit 4B", "date": "Today, 10:24 AM", "amount": 2400, "positive": True},
        {"name": "Maintenance Fee", "date": "Yesterday, 3:10 PM", "amount": -180, "positive": False},
        {"name": "Security Deposit Refund", "date": "Jun 24, 2026", "amount": 1200, "positive": True},
    ]

# Sidebar
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 14px; padding-bottom: 32px; border-bottom: 1px solid rgba(255,255,255,0.06);">
        <div style="width: 46px; height: 46px; border-radius: 12px; background: linear-gradient(135deg, #d4a145 0%, #f0d080 100%); 
                    display: flex; align-items: center; justify-content: center; font-size: 22px; color: #0b0d15; font-weight: 700;">
            ⚡
        </div>
        <div>
            <div style="font-size: 18px; font-weight: 700; letter-spacing: -0.3px;">Mwarokin</div>
            <div style="font-size: 11px; color: #d4a145; letter-spacing: 1.2px; text-transform: uppercase;">Estates · Premium</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("**MAIN**")
    st.page_link("app.py", label="Dashboard", icon="📊", active=True)
    st.page_link("#", label="Bank Cards", icon="💳", active=True)
    st.page_link("#", label="Calendar", icon="📅")
    st.page_link("#", label="Transactions", icon="🔄")
    
    st.markdown("**TOOLS**")
    st.page_link("#", label="Sync Google", icon="🔄")
    st.page_link("#", label="Analytics", icon="📈")
    st.page_link("#", label="Settings", icon="⚙️")
    
    st.markdown("---")
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown('<div style="width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#d4a145,#f0d080);display:flex;align-items:center;justify-content:center;font-weight:600;color:#0b0d15;">JD</div>', unsafe_allow_html=True)
    with col2:
        st.markdown("**James Donovan**  \nEstate Manager")

# Main Content
st.markdown('<h1 style="margin-bottom: 4px;">Welcome back, <span style="color:#d4a145;">James</span></h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#a8b2d9;"><i class="fas fa-building"></i> Mwarokin Estates · Premium Portfolio</p>', unsafe_allow_html=True)

# Top Stats
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div class="card">
        <div style="font-size:12px;text-transform:uppercase;letter-spacing:0.8px;color:#6b7aa8;font-weight:600;">Total Cards</div>
        <div class="stat-value gold-gradient" style="margin:8px 0;">{}</div>
        <div style="color:#2ed573;font-size:13px;">+1 this month</div>
    </div>
    """.format(len(st.session_state.cards)), unsafe_allow_html=True)

with col2:
    total_balance = sum(card["balance"] for card in st.session_state.cards)
    st.markdown("""
    <div class="card">
        <div style="font-size:12px;text-transform:uppercase;letter-spacing:0.8px;color:#6b7aa8;font-weight:600;">Total Balance</div>
        <div class="stat-value" style="background:linear-gradient(135deg,#4f7cff,#8ab4ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">${:,.0f}</div>
        <div style="color:#2ed573;font-size:13px;">+12.4%</div>
    </div>
    """.format(total_balance), unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="card">
        <div style="font-size:12px;text-transform:uppercase;letter-spacing:0.8px;color:#6b7aa8;font-weight:600;">Upcoming Payments</div>
        <div class="stat-value" style="background:linear-gradient(135deg,#2ed573,#7bed9f);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">$18,200</div>
        <div style="color:#a8b2d9;font-size:13px;">Due in 6 days</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="card">
        <div style="font-size:12px;text-transform:uppercase;letter-spacing:0.8px;color:#6b7aa8;font-weight:600;">Sync Status</div>
        <div style="font-size:28px;color:#2ed573;margin:8px 0;"><i class="fas fa-check-circle"></i> Live</div>
        <div style="color:#a8b2d9;font-size:13px;">Last sync: 2 min ago</div>
    </div>
    """, unsafe_allow_html=True)

# Bank Cards Section
st.markdown("---")
col_header1, col_header2 = st.columns([4, 1])
with col_header1:
    st.markdown('<h2 style="display:flex;align-items:center;gap:10px;"><span style="color:#d4a145;">💳</span> Your Bank Cards</h2>', unsafe_allow_html=True)
with col_header2:
    if st.button("➕ Add Card", type="primary", use_container_width=True):
        st.session_state.show_modal = True

# Cards Grid
cols = st.columns(3)
for idx, card in enumerate(st.session_state.cards):
    with cols[idx % 3]:
        default_tag = '<span style="background:linear-gradient(135deg,#d4a145,#f0d080);color:#0b0d15;padding:3px 12px;border-radius:20px;font-size:9px;font-weight:700;">DEFAULT</span>' if card["default"] else ""
        
        st.markdown(f"""
        <div class="card" style="height:100%;">
            <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:16px;">
                <div style="display:flex;align-items:center;gap:10px;">
                    <div style="font-size:28px;">{card['icon']}</div>
                    <div>
                        <div style="font-weight:600;">{card['type']}</div>
                        <div style="font-size:13px;color:#a8b2d9;text-transform:uppercase;">{card['number']}</div>
                    </div>
                </div>
                {default_tag}
            </div>
            
            <div style="margin:20px 0;font-family:monospace;font-size:18px;letter-spacing:2px;color:#f0f2f8;">{card['number']}</div>
            
            <div style="display:flex;gap:30px;margin-bottom:20px;">
                <div>
                    <div style="font-size:11px;color:#6b7aa8;text-transform:uppercase;">Cardholder</div>
                    <div style="font-weight:600;">{card['holder']}</div>
                </div>
                <div>
                    <div style="font-size:11px;color:#6b7aa8;text-transform:uppercase;">Expires</div>
                    <div style="font-weight:600;">{card['expiry']}</div>
                </div>
            </div>
            
            <div style="display:flex;justify-content:space-between;border-top:1px solid rgba(255,255,255,0.06);padding-top:16px;">
                <div style="font-size:22px;font-weight:700;" class="gold-gradient">${card['balance']:,}</div>
                <div style="display:flex;gap:12px;">
                    <button style="background:none;border:none;color:#a8b2d9;cursor:pointer;padding:6px 10px;border-radius:8px;">✏️</button>
                    <button onclick="delete_card({card['id']})" style="background:none;border:none;color:#ff6b6b;cursor:pointer;padding:6px 10px;border-radius:8px;">🗑️</button>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# Add Card Modal
if st.session_state.get("show_modal", False):
    with st.dialog("Add New Bank Card"):
        st.markdown("### Add Bank Card")
        
        col_a, col_b = st.columns(2)
        with col_a:
            holder = st.text_input("Cardholder Name", value="James Donovan")
        with col_b:
            card_type = st.selectbox("Card Type", ["Visa", "Mastercard", "American Express", "Discover"])
        
        card_number = st.text_input("Card Number", placeholder="4111 1111 1111 1111", value="4532 8912 3456 7890")
        col_c, col_d = st.columns(2)
        with col_c:
            expiry = st.text_input("Expiry (MM/YY)", value="08/28")
        with col_d:
            cvv = st.text_input("CVV", value="123", type="password")
        
        if st.button("Add Card", type="primary"):
            new_card = {
                "id": len(st.session_state.cards) + 1,
                "type": card_type,
                "number": "•••• •••• •••• " + str(random.randint(1000, 9999)),
                "expiry": expiry,
                "holder": holder,
                "balance": random.randint(20000, 150000),
                "default": len(st.session_state.cards) == 0,
                "icon": "💳"
            }
            st.session_state.cards.append(new_card)
            st.success(f"{card_type} card added successfully!")
            st.session_state.show_modal = False
            time.sleep(1)
            st.rerun()

# Calendar & Sync Section
st.markdown("---")
st.markdown('<h2 style="display:flex;align-items:center;gap:10px;"><span style="color:#d4a145;">📅</span> Google Calendar Sync</h2>', unsafe_allow_html=True)

cal_col1, cal_col2 = st.columns([1, 1])

with cal_col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("June 2026")
    
    # Simple Calendar Placeholder
    days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    st.markdown('<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px;text-align:center;font-size:13px;">', unsafe_allow_html=True)
    for d in days:
        st.markdown(f'<div style="padding:8px;color:#6b7aa8;font-weight:600;">{d}</div>', unsafe_allow_html=True)
    
    # Demo days
    for i in range(42):
        if i == 15:
            st.markdown('<div style="background:linear-gradient(135deg,#d4a145,#f0d080);color:#0b0d15;padding:8px;border-radius:8px;font-weight:700;">28</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="padding:8px;color:#a8b2d9;">•</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Events
    st.markdown("**Upcoming Events**")
    for event in st.session_state.events[:3]:
        st.markdown(f"""
        <div style="display:flex;gap:12px;padding:12px;background:rgba(255,255,255,0.03);border-radius:12px;margin-bottom:8px;">
            <div style="width:10px;height:10px;border-radius:50%;background:{event['color']};margin-top:6px;"></div>
            <div style="flex:1;">
                <div>{event['title']}</div>
                <div style="font-size:13px;color:#6b7aa8;">{event['date']} • {event['time']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with cal_col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🔄 Sync Settings")
    
    auto_sync = st.toggle("Auto-sync", value=True)
    
    st.markdown("**Google Account**  \njames@mwarokin.estate")
    st.markdown("**Calendar**  \n<span style='color:#d4a145;'>Mwarokin Estate Events</span>", unsafe_allow_html=True)
    
    if st.button("🔄 Sync Now", type="primary", use_container_width=True):
        st.success("✅ Google Calendar synced successfully!")
        # Add demo event
        new_event = {"title": "Manual Sync Triggered", "date": "2026-07-03", "time": "Now", "color": "#d4a145"}
        st.session_state.events.append(new_event)
        st.rerun()
    
    st.button("🔗 Connect Google", use_container_width=True)
    st.button("📤 Export .ics", use_container_width=True)
    
    st.info("All estate payment reminders & inspections are auto-synced to your Google Calendar.", icon="ℹ️")
    st.markdown('</div>', unsafe_allow_html=True)

# Recent Transactions
st.markdown("---")
st.markdown('<h2 style="display:flex;align-items:center;gap:10px;"><span style="color:#d4a145;">📃</span> Recent Transactions</h2>', unsafe_allow_html=True)

tx_cols = st.columns([3, 1, 1, 1])
for i, tx in enumerate(st.session_state.transactions):
    with tx_cols[i % 4]:
        color = "#2ed573" if tx["positive"] else "#ff6b6b"
        sign = "+" if tx["positive"] else ""
        st.markdown(f"""
        <div class="card" style="height:100%;">
            <div style="display:flex;gap:16px;">
                <div style="width:48px;height:48px;border-radius:50%;background:rgba(255,255,255,0.06);display:flex;align-items:center;justify-content:center;font-size:20px;">{ '⬇️' if tx['positive'] else '⬆️' }</div>
                <div style="flex:1;">
                    <div style="font-weight:600;">{tx['name']}</div>
                    <div style="color:#6b7aa8;font-size:13px;">{tx['date']}</div>
                </div>
                <div style="font-weight:700;color:{color};">{sign}${abs(tx['amount'])}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center;margin-top:40px;color:#6b7aa8;font-size:13px;">
    Built with ❤️ using Streamlit • Premium Banking Dashboard
</div>
""", unsafe_allow_html=True)
```