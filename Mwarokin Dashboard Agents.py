"""
Agent Dashboard.py
Mwarokin Estates — Agent Console
Modern, fully functional Streamlit implementation of the provided Agent Dashboard UI.
Run:  streamlit run "Agent Dashboard.py"
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import time

# ─────────────────────────────────────────────
# Page config & global CSS
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Mwarokin Estates · Agent Console",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #F7F5F0; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1C1508 0%, #2A2114 100%);
        border-right: 1px solid #3D3220;
    }
    [data-testid="stSidebar"] * { color: #E8DFD0 !important; }
    .brand-mark {
        width: 42px; height: 42px; border-radius: 10px;
        background: linear-gradient(135deg, #E9C876, #B9903B);
        color: #1C1508; font-weight: 800; font-size: 1.1rem;
        display: flex; align-items: center; justify-content: center;
    }
    .kpi-card {
        background: white; border-radius: 14px; padding: 1.25rem 1.4rem;
        border: 1px solid #E8E0D4; box-shadow: 0 2px 8px rgba(28,21,8,0.04);
    }
    .kpi-label { font-size: 0.78rem; color: #8C93A6; font-weight: 500; }
    .kpi-value { font-size: 1.65rem; font-weight: 700; color: #1C1508; margin: 0.25rem 0; }
    .kpi-sub { font-size: 0.78rem; }
    .up { color: #177A54; } .down { color: #BC3B3B; }
    .tier-pill {
        display: inline-block; padding: 0.2rem 0.65rem; border-radius: 999px;
        font-size: 0.75rem; font-weight: 600;
    }
    .status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
    .rung {
        background: white; border-radius: 12px; padding: 1rem 1.2rem;
        border: 1px solid #E8E0D4; margin-bottom: 0.6rem;
        display: flex; align-items: center; gap: 1rem;
    }
    .tier-glyph {
        width: 40px; height: 40px; border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: 1.1rem;
    }
    .activity-item {
        display: flex; gap: 0.85rem; padding: 0.7rem 0;
        border-bottom: 1px solid #F0EAE0;
    }
    .act-icon {
        width: 36px; height: 36px; border-radius: 9px;
        display: flex; align-items: center; justify-content: center; flex-shrink: 0;
    }
    .payout-row, .viewing-row {
        display: flex; align-items: center; justify-content: space-between;
        padding: 0.75rem 0; border-bottom: 1px solid #F0EAE0;
    }
    .terr-bar-track {
        height: 6px; background: #F0EAE0; border-radius: 99px; margin-top: 0.35rem;
    }
    .terr-bar-fill {
        height: 100%; border-radius: 99px;
        background: linear-gradient(90deg, #C9A24B, #E9C876);
    }
    .pipe-track {
        height: 28px; background: #F0EAE0; border-radius: 8px; overflow: hidden;
    }
    .pipe-fill {
        height: 100%; display: flex; align-items: center; padding-left: 0.6rem;
        color: white; font-size: 0.78rem; font-weight: 600; border-radius: 8px;
    }
    div[data-testid="stExpander"] { background: white; border-radius: 12px; border: 1px solid #E8E0D4; }
    .stButton > button {
        border-radius: 10px; font-weight: 600;
    }
    .bronze-btn {
        background: linear-gradient(135deg, #C9A24B, #B9903B) !important;
        color: #1C1508 !important; border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Data (mirrors original JS constants)
# ─────────────────────────────────────────────
TIERS = [
    {"key": "taifa",  "name": "Taifa",  "req": "150+ deals · Nation-wide mandate",
     "color": "#C9A24B", "glyph": "#1C1508", "bg": "linear-gradient(155deg,#E9C876,#B9903B)"},
    {"key": "milki",  "name": "Milki",  "req": "80+ deals · Ownership tier",
     "color": "#9C8CE0", "glyph": "#1C1508", "bg": "linear-gradient(155deg,#B9ADEE,#7A6BC9)"},
    {"key": "jengo",  "name": "Jengo",  "req": "35+ deals · Building tier",
     "color": "#6FB6A8", "glyph": "#0B221C", "bg": "linear-gradient(155deg,#8FD2C4,#4C9484)"},
    {"key": "msingi", "name": "Msingi", "req": "0+ deals · Foundation tier",
     "color": "#8C93A6", "glyph": "#12141C", "bg": "linear-gradient(155deg,#AAB1C4,#6B7286)"},
]

AGENTS = [
    {"name": "Kevin Otieno",    "territory": "Kilimani",  "tier": "taifa",  "status": "active",
     "deals": 162, "commission": 284500, "kyc": "verified", "conv": "34%", "color": "#4F46E5"},
    {"name": "Amina Yusuf",     "territory": "Westlands", "tier": "taifa",  "status": "active",
     "deals": 158, "commission": 271200, "kyc": "verified", "conv": "31%", "color": "#C9A24B"},
    {"name": "Brian Kiplagat",  "territory": "Karen",     "tier": "milki",  "status": "active",
     "deals": 96,  "commission": 168300, "kyc": "verified", "conv": "27%", "color": "#177A54"},
    {"name": "Faith Njoroge",   "territory": "Ruaka",     "tier": "milki",  "status": "active",
     "deals": 88,  "commission": 151900, "kyc": "verified", "conv": "25%", "color": "#BC3B3B"},
    {"name": "Dennis Mwangi",   "territory": "South B",   "tier": "milki",  "status": "on leave",
     "deals": 81,  "commission": 139800, "kyc": "verified", "conv": "22%", "color": "#B4791A"},
    {"name": "Cynthia Wafula",  "territory": "Kasarani",  "tier": "jengo",  "status": "active",
     "deals": 52,  "commission": 88400,  "kyc": "pending",  "conv": "19%", "color": "#4F46E5"},
    {"name": "Peter Kamau",     "territory": "South C",   "tier": "jengo",  "status": "active",
     "deals": 47,  "commission": 79600,  "kyc": "verified", "conv": "21%", "color": "#177A54"},
    {"name": "Grace Achieng",   "territory": "Westlands", "tier": "jengo",  "status": "active",
     "deals": 41,  "commission": 71200,  "kyc": "verified", "conv": "18%", "color": "#C9A24B"},
    {"name": "Samuel Kiprono",  "territory": "Kilimani",  "tier": "jengo",  "status": "suspended",
     "deals": 38,  "commission": 64100,  "kyc": "rejected", "conv": "14%", "color": "#BC3B3B"},
    {"name": "Lucy Chebet",     "territory": "Ruaka",     "tier": "msingi", "status": "active",
     "deals": 19,  "commission": 32800,  "kyc": "pending",  "conv": "16%", "color": "#177A54"},
    {"name": "Hassan Ali",      "territory": "Karen",     "tier": "msingi", "status": "active",
     "deals": 14,  "commission": 24100,  "kyc": "verified", "conv": "12%", "color": "#4F46E5"},
    {"name": "Mercy Wanjiru",   "territory": "South B",   "tier": "msingi", "status": "active",
     "deals": 9,   "commission": 15600,  "kyc": "pending",  "conv": "10%", "color": "#B4791A"},
]

TERRITORIES = [
    {"name": "Kilimani",    "agents": 6, "listings": 84, "pct": 88},
    {"name": "Westlands",   "agents": 5, "listings": 71, "pct": 76},
    {"name": "Ruaka",       "agents": 4, "listings": 52, "pct": 63},
    {"name": "Karen",       "agents": 4, "listings": 38, "pct": 54},
    {"name": "South B / C", "agents": 5, "listings": 46, "pct": 49},
    {"name": "Kasarani",    "agents": 3, "listings": 29, "pct": 38},
]

PIPELINE = [
    {"stage": "New Lead",  "count": 58, "color": "#8C93A6"},
    {"stage": "Contacted", "count": 41, "color": "#4F46E5"},
    {"stage": "Viewing",   "count": 26, "color": "#B4791A"},
    {"stage": "Offer",     "count": 14, "color": "#6FB6A8"},
    {"stage": "Closed",    "count": 9,  "color": "#177A54"},
]

PAYOUTS = [
    {"name": "Kevin Otieno",   "amount": 48200, "date": "Requested 2h ago",      "status": "pending"},
    {"name": "Amina Yusuf",    "amount": 39600, "date": "Requested 5h ago",      "status": "pending"},
    {"name": "Brian Kiplagat", "amount": 22100, "date": "Requested yesterday",   "status": "pending"},
    {"name": "Grace Achieng",  "amount": 14300, "date": "Approved · paid out",   "status": "done"},
    {"name": "Faith Njoroge",  "amount": 27900, "date": "Approved · paid out",   "status": "done"},
]

VIEWINGS = [
    {"title": "2BR Apartment — Kilimani Ridge", "agent": "Kevin Otieno",   "time": "Today, 2:30 PM"},
    {"title": "Office Suite — Westlands Square","agent": "Amina Yusuf",    "time": "Today, 4:00 PM"},
    {"title": "Townhouse — Ruaka Greens",       "agent": "Faith Njoroge",  "time": "Tomorrow, 10:00 AM"},
    {"title": "Studio — South B Court",         "agent": "Cynthia Wafula", "time": "Tomorrow, 1:15 PM"},
]

ACTIVITY = [
    {"icon": "🤝", "color": "#177A54", "bg": "#D1FAE5",
     "text": "**Brian Kiplagat** closed a deal on Karen Villa 12", "time": "12 minutes ago"},
    {"icon": "👤", "color": "#4F46E5", "bg": "#EEF2FF",
     "text": "**Lucy Chebet** submitted KYC documents", "time": "48 minutes ago"},
    {"icon": "💰", "color": "#B9903B", "bg": "#FEF3C7",
     "text": "Payout of **KES 39,600** requested by Amina Yusuf", "time": "2 hours ago"},
    {"icon": "👁", "color": "#B4791A", "bg": "#FEF3C7",
     "text": "**Grace Achieng** scheduled a viewing in Westlands", "time": "3 hours ago"},
    {"icon": "⚠", "color": "#BC3B3B", "bg": "#FEE2E2",
     "text": "**Samuel Kiprono** flagged for KYC rejection", "time": "5 hours ago"},
    {"icon": "🏅", "color": "#B9903B", "bg": "#FEF3C7",
     "text": "**Kevin Otieno** promoted to Taifa tier", "time": "Yesterday"},
]

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def initials(name: str) -> str:
    return "".join(w[0] for w in name.split()[:2]).upper()

def fmt(n: int) -> str:
    return f"KES {n:,}"

def tier_info(key: str) -> dict:
    return next(t for t in TIERS if t["key"] == key)

def status_meta(s: str) -> dict:
    if s == "active":
        return {"color": "#177A54", "label": "Active"}
    if s == "on leave":
        return {"color": "#B4791A", "label": "On Leave"}
    return {"color": "#BC3B3B", "label": "Suspended"}

def kyc_meta(k: str) -> dict:
    if k == "verified":
        return {"icon": "✅", "color": "#177A54", "label": "Verified"}
    if k == "pending":
        return {"icon": "⏳", "color": "#B4791A", "label": "Pending"}
    return {"icon": "❌", "color": "#BC3B3B", "label": "Rejected"}

# ─────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────
if "payouts" not in st.session_state:
    st.session_state.payouts = [p.copy() for p in PAYOUTS]
if "activity" not in st.session_state:
    st.session_state.activity = ACTIVITY.copy()
if "agents" not in st.session_state:
    st.session_state.agents = [a.copy() for a in AGENTS]
if "show_invite" not in st.session_state:
    st.session_state.show_invite = False
if "selected_agent" not in st.session_state:
    st.session_state.selected_agent = None

# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
with st.sidebar:
    col_b1, col_b2 = st.columns([1, 4])
    with col_b1:
        st.markdown('<div class="brand-mark">ME</div>', unsafe_allow_html=True)
    with col_b2:
        st.markdown("### Mwarokin Estates")
        st.caption("Agent Console")

    st.markdown("---")
    st.markdown("**Overview**")
    nav = st.radio(
        "Navigation",
        ["Agent Dashboard", "Properties", "Tenants"],
        label_visibility="collapsed",
        index=0,
    )

    st.markdown("**Agent Operations**")
    st.markdown("Agent Directory  ·  32")
    st.markdown("Lead Pipeline  ·  58")
    st.markdown("Territories")
    st.markdown("Commissions")
    st.markdown("Rank & Incentives")
    st.markdown("Viewings & Tasks")

    st.markdown("**System**")
    st.markdown("Payout Requests  ·  6")
    st.markdown("AI Agents")
    st.markdown("Settings")

    st.markdown("---")
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:0.7rem;">
            <div style="width:36px;height:36px;border-radius:50%;background:#C9A24B;
                        color:#1C1508;display:flex;align-items:center;justify-content:center;
                        font-weight:700;">RM</div>
            <div>
                <div style="font-weight:600;font-size:0.9rem;">Robin Mwarema</div>
                <div style="font-size:0.75rem;opacity:0.7;">Estate Director</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────
# Main header
# ─────────────────────────────────────────────
st.markdown("## Agent Dashboard")
st.caption("Performance, commissions and territory coverage across all Mwarokin agencies")

# Top actions
c1, c2, c3, c4 = st.columns([3, 2, 1, 1.5])
with c1:
    search = st.text_input("Search", placeholder="Search agents, phone, territory…", label_visibility="collapsed")
with c2:
    region = st.selectbox("Region", ["All Nairobi zones", "Kilimani", "Westlands", "Ruaka", "Karen", "South B / C", "Kasarani"], label_visibility="collapsed")
with c3:
    st.button("🔔 6", use_container_width=True)
with c4:
    if st.button("＋ Invite Agent", use_container_width=True, type="primary"):
        st.session_state.show_invite = True

# ─────────────────────────────────────────────
# KPI Strip
# ─────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">Commission Payable</div>
        <div class="kpi-value">KES 1,842,300</div>
        <div class="kpi-sub up">↑ 14.2% vs last month</div>
    </div>
    """, unsafe_allow_html=True)
with k2:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">Active Agents</div>
        <div class="kpi-value">32</div>
        <div class="kpi-sub up">↑ 4 onboarded this month</div>
    </div>
    """, unsafe_allow_html=True)
with k3:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">Leads This Month</div>
        <div class="kpi-value">318</div>
        <div class="kpi-sub up">↑ 22% conversion to viewing</div>
    </div>
    """, unsafe_allow_html=True)
with k4:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">Avg Deal Close Time</div>
        <div class="kpi-value">6.4 <span style="font-size:0.95rem;color:#8C93A6;">days</span></div>
        <div class="kpi-sub down">↓ 1.1 days faster</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Rank Ladder
# ─────────────────────────────────────────────
st.markdown("### 🏅 Agent Rank Ladder")
st.caption("Progression tiers from the Mwarokin agent incentive programme · Sorted by commission earned this quarter")

for t in TIERS:
    members = sorted(
        [a for a in st.session_state.agents if a["tier"] == t["key"]],
        key=lambda x: x["commission"],
        reverse=True,
    )
    total_comm = sum(m["commission"] for m in members)
    shown = members[:6]
    extra = len(members) - len(shown)

    avatars = " ".join(
        f'<span title="{m["name"]} — {fmt(m["commission"])}" '
        f'style="display:inline-flex;width:32px;height:32px;border-radius:50%;'
        f'background:{m["color"]};color:white;font-size:0.7rem;font-weight:700;'
        f'align-items:center;justify-content:center;margin-right:-6px;border:2px solid white;">'
        f'{initials(m["name"])}</span>'
        for m in shown
    )
    if extra > 0:
        avatars += f' <span style="font-size:0.75rem;color:#8C93A6;">+{extra}</span>'

    st.markdown(f"""
    <div class="rung">
        <div class="tier-glyph" style="background:{t['bg']};color:{t['glyph']};">{t['name'][0]}</div>
        <div style="flex:1;">
            <div style="font-weight:700;">{t['name']}</div>
            <div style="font-size:0.75rem;color:#8C93A6;">{t['req']}</div>
        </div>
        <div style="display:flex;align-items:center;">{avatars}</div>
        <div style="text-align:right;min-width:110px;">
            <div style="font-weight:700;">{fmt(total_comm)}</div>
            <div style="font-size:0.75rem;color:#8C93A6;">{len(members)} agents</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Agent Directory + Territory
# ─────────────────────────────────────────────
col_left, col_right = st.columns([1.6, 1])

with col_left:
    st.markdown("### 🪪 Agent Directory")
    filter_tabs = st.radio("Filter", ["All", "Active", "Pending KYC"], horizontal=True, label_visibility="collapsed")

    df = pd.DataFrame(st.session_state.agents)
    if search:
        q = search.lower()
        df = df[df["name"].str.lower().str.contains(q) | df["territory"].str.lower().str.contains(q)]
    if filter_tabs == "Active":
        df = df[df["status"] == "active"]
    elif filter_tabs == "Pending KYC":
        df = df[df["kyc"] == "pending"]

    # Display table with interactive rows
    for _, row in df.iterrows():
        t = tier_info(row["tier"])
        s = status_meta(row["status"])
        k = kyc_meta(row["kyc"])
        with st.container():
            c_a, c_b, c_c, c_d, c_e, c_f = st.columns([2.2, 1, 1, 0.7, 1.2, 1])
            with c_a:
                if st.button(f"{initials(row['name'])}  {row['name']}", key=f"agent_{row['name']}", use_container_width=True):
                    st.session_state.selected_agent = row["name"]
                st.caption(row["territory"])
            with c_b:
                st.markdown(f'<span class="tier-pill" style="background:{t["color"]}22;color:{t["color"]};">{t["name"]}</span>', unsafe_allow_html=True)
            with c_c:
                st.markdown(f'<span class="status-dot" style="background:{s["color"]};"></span><span style="color:{s["color"]};font-size:0.85rem;">{s["label"]}</span>', unsafe_allow_html=True)
            with c_d:
                st.markdown(f"**{row['deals']}**")
            with c_e:
                st.markdown(f"**{fmt(row['commission'])}**")
            with c_f:
                st.markdown(f'<span style="color:{k["color"]};font-size:0.8rem;">{k["icon"]} {k["label"]}</span>', unsafe_allow_html=True)
            st.markdown("<hr style='margin:0.3rem 0;border-color:#F0EAE0;'>", unsafe_allow_html=True)

with col_right:
    st.markdown("### 🗺 Territory Coverage")
    for t in TERRITORIES:
        st.markdown(f"""
        <div style="margin-bottom:0.9rem;">
            <div style="display:flex;justify-content:space-between;">
                <b>{t['name']}</b>
                <span style="font-weight:700;">{t['pct']}%</span>
            </div>
            <div style="font-size:0.75rem;color:#8C93A6;">{t['agents']} agents · {t['listings']} listings</div>
            <div class="terr-bar-track"><div class="terr-bar-fill" style="width:{t['pct']}%;"></div></div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Lead Pipeline + Live Activity
# ─────────────────────────────────────────────
col_p, col_a = st.columns(2)

with col_p:
    st.markdown("### 🎯 Lead Pipeline")
    max_count = max(p["count"] for p in PIPELINE)
    for p in PIPELINE:
        pct = int(p["count"] / max_count * 100)
        st.markdown(f"""
        <div style="margin-bottom:0.7rem;">
            <div style="font-size:0.82rem;font-weight:500;margin-bottom:0.25rem;">{p['stage']}</div>
            <div class="pipe-track">
                <div class="pipe-fill" style="width:{pct}%;background:{p['color']};">{p['count']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    if st.button("＋ New Lead", key="new_lead"):
        st.toast("New lead form opened (demo)")

with col_a:
    st.markdown("### 📡 Live Activity")
    # occasional live pulse
    if random.random() < 0.15:
        pool = [
            {"icon": "👁", "color": "#4F46E5", "bg": "#EEF2FF", "text": "New lead assigned in **Kilimani**", "time": "Just now"},
            {"icon": "💰", "color": "#B9903B", "bg": "#FEF3C7", "text": "Commission credited to **Peter Kamau**", "time": "Just now"},
        ]
        st.session_state.activity.insert(0, random.choice(pool))
        if len(st.session_state.activity) > 8:
            st.session_state.activity.pop()

    for act in st.session_state.activity[:7]:
        st.markdown(f"""
        <div class="activity-item">
            <div class="act-icon" style="background:{act['bg']};color:{act['color']};">{act['icon']}</div>
            <div>
                <div style="font-size:0.85rem;">{act['text']}</div>
                <div style="font-size:0.72rem;color:#8C93A6;">{act['time']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Payouts + Upcoming Viewings
# ─────────────────────────────────────────────
col_pay, col_view = st.columns(2)

with col_pay:
    st.markdown("### 💸 Payout Requests")
    st.markdown('<span style="background:#FEF3C7;color:#B4791A;padding:0.2rem 0.6rem;border-radius:999px;font-size:0.75rem;font-weight:600;">6 pending</span>', unsafe_allow_html=True)
    for i, p in enumerate(st.session_state.payouts):
        c1, c2, c3 = st.columns([2, 1.2, 1])
        with c1:
            st.markdown(f"**{p['name']}**")
            st.caption(p["date"])
        with c2:
            st.markdown(f"**{fmt(p['amount'])}**")
        with c3:
            if p["status"] == "pending":
                if st.button("Approve", key=f"approve_{i}"):
                    st.session_state.payouts[i]["status"] = "done"
                    st.session_state.payouts[i]["date"] = "Approved · paid out"
                    st.toast("Payout approved and queued for disbursement")
                    st.rerun()
            else:
                st.markdown('<span style="background:#D1FAE5;color:#177A54;padding:0.2rem 0.55rem;border-radius:999px;font-size:0.75rem;">Paid</span>', unsafe_allow_html=True)

with col_view:
    st.markdown("### 📅 Upcoming Viewings")
    for v in VIEWINGS:
        st.markdown(f"""
        <div class="viewing-row">
            <div style="display:flex;align-items:center;gap:0.8rem;">
                <div style="width:38px;height:38px;border-radius:9px;background:#EEF2FF;color:#4F46E5;
                            display:flex;align-items:center;justify-content:center;">📅</div>
                <div>
                    <div style="font-size:0.85rem;font-weight:600;">{v['title']}</div>
                    <div style="font-size:0.72rem;color:#8C93A6;">{v['agent']} · {v['time']}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Agent Detail Drawer (expander style)
# ─────────────────────────────────────────────
if st.session_state.selected_agent:
    agent = next(a for a in st.session_state.agents if a["name"] == st.session_state.selected_agent)
    t = tier_info(agent["tier"])
    with st.expander(f"Agent Profile — {agent['name']}", expanded=True):
        col_av, col_info = st.columns([1, 4])
        with col_av:
            st.markdown(f"""
            <div style="width:64px;height:64px;border-radius:14px;background:{agent['color']};
                        color:white;font-size:1.4rem;font-weight:700;
                        display:flex;align-items:center;justify-content:center;">
                {initials(agent['name'])}
            </div>
            """, unsafe_allow_html=True)
        with col_info:
            st.markdown(f"### {agent['name']}")
            st.caption(f"{agent['territory']} · {t['name']} tier")

        m1, m2, m3 = st.columns(3)
        m1.metric("Deals Closed", agent["deals"])
        m2.metric("Conversion", agent["conv"])
        m3.metric("Commission", fmt(agent["commission"]))

        st.markdown("**Assigned Listings**")
        st.markdown(f"- {agent['territory']} Heights, Unit 4B — Active · 2BR")
        st.markdown(f"- {agent['territory']} Court, Unit 12 — Active · Studio")

        st.markdown("**Recent Deals**")
        st.markdown(f"- Closed — Apt 304 · {fmt(int(agent['commission'] * 0.18))} commission")
        st.markdown(f"- Closed — Suite 12B · {fmt(int(agent['commission'] * 0.14))} commission")

        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("✉ Message", use_container_width=True):
                st.toast("Message sent to agent")
        with b2:
            if st.button("💰 Review Payout", use_container_width=True):
                st.toast("Payout review opened")
        with b3:
            if st.button("Close", use_container_width=True):
                st.session_state.selected_agent = None
                st.rerun()

# ─────────────────────────────────────────────
# Invite Modal
# ─────────────────────────────────────────────
if st.session_state.show_invite:
    with st.form("invite_form"):
        st.markdown("### ＋ Invite New Agent")
        c1, c2 = st.columns(2)
        with c1:
            full_name = st.text_input("Full Name", placeholder="e.g. Wanjiru Kamau")
        with c2:
            phone = st.text_input("Phone Number", placeholder="+254 7…")
        email = st.text_input("Email Address", placeholder="agent@mwarokinestates.co.ke")
        c3, c4 = st.columns(2)
        with c3:
            territory = st.selectbox("Assigned Territory", ["Kilimani", "Westlands", "Ruaka", "South B / C", "Kasarani", "Karen"])
        with c4:
            tier = st.selectbox("Starting Tier", ["Msingi (Foundation)", "Jengo (Builder)", "Milki (Owner)"])
        submitted = st.form_submit_button("✉ Send Invite", type="primary")
        cancel = st.form_submit_button("Cancel")
        if submitted:
            st.session_state.show_invite = False
            st.toast("Invitation sent — agent will receive onboarding link via SMS & email")
            st.rerun()
        if cancel:
            st.session_state.show_invite = False
            st.rerun()
