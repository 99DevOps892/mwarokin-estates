```python
import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime
import random

# ===================== CONFIG =====================
st.set_page_config(
    page_title="Mwarokin Estates — Milki Command Center",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - Dark Luxury Gold Theme
st.markdown("""
<style>
    /* Main Theme */
    .stApp {
        background: radial-gradient(circle at 10% 20%, #0b0e17, #030507);
        color: #e6e9f0;
    }
    .main .block-container {
        padding-top: 2rem;
        max-width: 1500px;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: rgba(3,7,12,.85) !important;
        border-right: 1px solid rgba(200,151,42,.2) !important;
    }
    .sidebar .sidebar-content {
        background: rgba(3,7,12,.75);
    }
    
    /* Cards */
    .stCard {
        background: rgba(12,18,28,.65);
        border: 1px solid rgba(200,151,42,.2);
        border-radius: 16px;
        box-shadow: 0 8px 20px rgba(0,0,0,.4);
        transition: all 0.25s cubic-bezier(0.2,0.9,0.4,1.1);
    }
    .stCard:hover {
        border-color: rgba(200,151,42,.5);
        transform: translateY(-3px);
        box-shadow: 0 12px 28px rgba(0,0,0,.5);
    }
    
    /* Stats */
    .stat-val {
        font-family: 'Cormorant Garamond', serif;
        font-size: 2.2rem;
        font-weight: 600;
        color: #fef5e7;
        line-height: 1.1;
    }
    .trend-up { color: #4ab87a; }
    .trend-dn { color: #e07070; }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(105deg, #c8972a, #a07a1f);
        color: #0a0c10;
        border-radius: 60px;
        font-weight: 700;
        border: none;
        box-shadow: 0 6px 14px rgba(200,151,42,.3);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 22px rgba(200,151,42,.4);
        background: linear-gradient(105deg, #e0b354, #c8972a);
    }
    
    /* Header */
    .dashboard-header {
        font-family: 'Cormorant Garamond', serif;
        font-size: 2.4rem;
        font-weight: 300;
        letter-spacing: -0.02em;
        color: #fef5e7;
    }
    .gold-text { color: #c8972a; }
</style>
""", unsafe_allow_html=True)

# ===================== DATA =====================
# Sample Data
rent_data = pd.DataFrame({
    'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    'Collected': [184000, 162000, 198000, 142000, 245000, 612000]
})

tenants = [
    {"name": "Amina Wanjiku", "unit": "Unit 4B", "status": "Lipa Mdogo", "avatar": "👩"},
    {"name": "James Otieno", "unit": "Unit 1A", "status": "Paid", "avatar": "👨"},
    {"name": "Grace Muthoni", "unit": "Unit 7C", "status": "Overdue", "avatar": "👩"},
    {"name": "Peter Kamau", "unit": "Unit 2F", "status": "Paid", "avatar": "👨"},
    {"name": "Fatuma Hassan", "unit": "Unit 9A", "status": "Due Soon", "avatar": "👩"},
]

lipa_data = [
    {"name": "Amina W. · 4B", "pct": 40},
    {"name": "John M. · 3C", "pct": 75},
    {"name": "Mary K. · 6D", "pct": 20},
    {"name": "Ali H. · 8B", "pct": 90},
    {"name": "Rose O. · 2A", "pct": 55},
]

activities = [
    {"time": "12 minutes ago", "text": "<strong>James Otieno</strong> paid rent for Unit 1A", "dot": "green"},
    {"time": "1 hour ago", "text": "New Lipa Mdogo plan started by <strong>Rose O.</strong>", "dot": "gold"},
    {"time": "3 hours ago", "text": "White-label domain verified for <strong>app.mwarokinestates.co.ke</strong>", "dot": "blue"},
    {"time": "5 hours ago", "text": "CCTV camera offline in <strong>Block B, Unit 6</strong>", "dot": "red"},
]

# ===================== SIDEBAR =====================
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;padding:4px 6px 26px;border-bottom:1px solid rgba(200,151,42,.2);margin-bottom:20px;">
        <span style="font-size:26px;color:#c8972a;">⬡</span>
        <span style="font-size:17px;font-weight:500;color:#fef5e7;">Mwarokin <em style="color:#c8972a;">Estates</em></span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background:linear-gradient(105deg,rgba(200,151,42,.18),rgba(160,122,31,.06));border:1px solid rgba(200,151,42,.35);border-radius:16px;padding:12px 14px;margin-bottom:24px;">
        <div style="font-size:11px;color:#7e8aa2;text-transform:uppercase;letter-spacing:0.08em;">Current Plan</div>
        <div style="font-size:20px;color:#e0b354;font-weight:600;">Milki</div>
        <div style="font-size:10px;background:#c8972a;color:#0a0c10;padding:3px 8px;border-radius:40px;display:inline-block;margin-top:6px;font-weight:700;">ALL UNLOCKED</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("**Overview**")
    st.page_link("app.py", label="🏠 Dashboard", icon="🏠", use_container_width=True)
    st.page_link("#", label="👥 Tenant Management", icon="👥", use_container_width=True)
    st.page_link("#", label="🏗️ Vacancies & Listings", icon="🏗️", use_container_width=True)
    st.page_link("#", label="🔑 Caretaker & Keys", icon="🔑", use_container_width=True)
    
    st.markdown("**Money**")
    st.page_link("#", label="💰 Lipa Mdogo", icon="💰", use_container_width=True)
    st.page_link("#", label="🧾 KRA Tax Centre", icon="🧾", use_container_width=True)
    st.page_link("#", label="📊 Financial Reports", icon="📊", use_container_width=True)
    
    st.markdown("**Milki Exclusive**")
    st.page_link("#", label="🔒 Security Management", icon="🔒", use_container_width=True)
    st.page_link("#", label="🏷️ White-Label Branding", icon="🏷️", use_container_width=True)
    st.page_link("#", label="🗺️ Unmapped Areas", icon="🗺️", use_container_width=True)
    
    st.markdown("---")
    st.caption("Milki Plan • 250 Unit Capacity")

# ===================== TOPBAR =====================
col1, col2, col3 = st.columns([1, 4, 2])
with col1:
    st.markdown(f"<h1 class='dashboard-header'>Good morning, <span class='gold-text'>Mwarokin 👋</span></h1>", unsafe_allow_html=True)
    st.caption("Here's what's happening across your portfolio today.")

with col3:
    st.markdown("""
    <div style="background:linear-gradient(105deg,rgba(200,151,42,.2),rgba(200,151,42,.05));border:1px solid #c8972a;border-radius:60px;padding:12px 20px;text-align:center;font-weight:700;color:#e0b354;">
        👑 Milki Plan · 250 Unit Capacity
    </div>
    """, unsafe_allow_html=True)

# Status Strip
st.markdown("""
<div style="background:linear-gradient(135deg,rgba(74,184,122,.1),rgba(200,151,42,.06));border:1px solid rgba(74,184,122,.3);border-radius:16px;padding:16px 26px;display:flex;align-items:center;gap:16px;margin:20px 0;">
    <span style="font-size:24px;">✅</span>
    <div style="flex:1;font-size:14px;">
        <strong>All features unlocked.</strong> Security management, white-label branding, unmapped-area mapping and every module are fully active.
    </div>
</div>
""", unsafe_allow_html=True)

# ===================== STATS =====================
st.subheader("Portfolio Snapshot")
cols = st.columns(6)

stats = [
    ("Total Units", "86", "↑ 9 this month", "trend-up"),
    ("Rent Collected", "KSH 612K", "↑ 14% vs last month", "trend-up"),
    ("Arrears", "KSH 41K", "3 tenants late", "trend-dn"),
    ("Lipa Mdogo Active", "19", "KSH 318K tracked", "trend-up"),
    ("Vacant Units", "6", "4 viewings scheduled", ""),
    ("Security Alerts", "0", "All zones clear", "trend-up")
]

for col, (label, val, trend, trend_class) in zip(cols, stats):
    with col:
        st.markdown(f"""
        <div class="stCard" style="padding:18px 16px;">
            <div style="font-size:10.5px;text-transform:uppercase;letter-spacing:0.09em;color:#7e8aa2;margin-bottom:8px;">{label}</div>
            <div class="stat-val">{val}</div>
            <div style="font-size:11px;" class="{trend_class}">{trend}</div>
        </div>
        """, unsafe_allow_html=True)

# ===================== MAIN CONTENT =====================
tab1, tab2, tab3 = st.tabs(["📊 Overview", "👥 Tenants & Payments", "🔒 Milki Exclusive"])

with tab1:
    col_a, col_b = st.columns([2, 1])
    
    with col_a:
        st.markdown('<div class="stCard" style="padding:22px;">', unsafe_allow_html=True)
        st.subheader("Monthly Rent Collection")
        fig = px.bar(
            rent_data, x='Month', y='Collected',
            text='Collected',
            color_discrete_sequence=['#c8972a']
        )
        fig.update_traces(texttemplate='K%{text:,}', textposition='outside')
        fig.update_layout(
            height=320, 
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#b9c2d4'),
            margin=dict(l=10, r=10, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col_b:
        st.markdown('<div class="stCard" style="padding:22px;">', unsafe_allow_html=True)
        st.subheader("KRA Tax Summary 2026 FY")
        kra_cols = st.columns(2)
        with kra_cols[0]:
            st.metric("Annual Rent", "KSH 3.6M")
            st.metric("Expenses", "KSH 360K")
        with kra_cols[1]:
            st.metric("Net Taxable", "KSH 3.24M")
            st.metric("Tax Due (15%)", "KSH 486K", delta="Due in 45 days", delta_color="off")
        st.button("📄 Download PDF Report", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    col_t1, col_t2 = st.columns([1, 1])
    
    with col_t1:
        st.markdown('<div class="stCard" style="padding:22px;">', unsafe_allow_html=True)
        st.subheader("Recent Tenants")
        for t in tenants:
            status_color = {
                "Paid": "#4ab87a", 
                "Lipa Mdogo": "#c8972a",
                "Overdue": "#e07070",
                "Due Soon": "#e0a343"
            }.get(t["status"], "#7e8aa2")
            
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:14px;padding:12px 0;border-bottom:1px solid rgba(200,151,42,.2);">
                <div style="width:36px;height:36px;border-radius:50%;background:rgba(255,255,255,.05);display:flex;align-items:center;justify-content:center;font-size:18px;border:1px solid rgba(200,151,42,.2);">{t['avatar']}</div>
                <div style="flex:1;">
                    <div style="font-weight:600;">{t['name']}</div>
                    <div style="font-size:12px;color:#7e8aa2;">{t['unit']}</div>
                </div>
                <span style="font-size:10px;padding:4px 12px;border-radius:30px;background:rgba(74,184,122,.15);color:{status_color};font-weight:700;">{t['status']}</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col_t2:
        st.markdown('<div class="stCard" style="padding:22px;">', unsafe_allow_html=True)
        st.subheader("Lipa Mdogo Tracker")
        for item in lipa_data:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid rgba(200,151,42,.2);">
                <div style="flex:1;font-weight:500;">{item['name']}</div>
                <div style="width:120px;height:6px;background:rgba(255,255,255,.1);border-radius:4px;overflow:hidden;">
                    <div style="height:100%;background:linear-gradient(90deg,#c8972a,#e0a343);width:{item['pct']}%;border-radius:4px;"></div>
                </div>
                <div style="width:50px;text-align:right;font-size:13px;font-weight:600;color:#e0b354;">{item['pct']}%</div>
            </div>
            """, unsafe_allow_html=True)
        st.button("View All Lipa Mdogo Plans", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

with tab3:
    col_m1, col_m2, col_m3 = st.columns(3)
    
    with col_m1:
        st.markdown('<div class="stCard" style="padding:22px;">', unsafe_allow_html=True)
        st.subheader("Security Management")
        st.success("● Main Gate - All Clear")
        st.info("12 CCTV cameras online")
        st.warning("1 camera offline - Unit 6")
        st.button("Open Security Console", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col_m2:
        st.markdown('<div class="stCard" style="padding:22px;">', unsafe_allow_html=True)
        st.subheader("White-Label Branding")
        st.markdown("**Tenant Portal**: `app.mwarokinestates.co.ke`")
        st.markdown("**Brand Color**: <span style='background:#c8972a;width:20px;height:20px;border-radius:4px;display:inline-block;vertical-align:middle;'></span> #C8972A", unsafe_allow_html=True)
        st.button("Edit Branding", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col_m3:
        st.markdown('<div class="stCard" style="padding:22px;">', unsafe_allow_html=True)
        st.subheader("Unmapped Areas")
        st.markdown("**4 New survey points detected**")
        st.image("https://picsum.photos/id/1015/600/220", use_column_width=True)
        st.button("View Full Map", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# Activity Feed & Quick Modules
st.markdown("### Activity Feed & Quick Launch")
col_feed, col_mod = st.columns([1, 2])

with col_feed:
    st.markdown('<div class="stCard" style="padding:22px;">', unsafe_allow_html=True)
    st.subheader("Recent Activity")
    for act in activities:
        dot_color = {"green": "#4ab87a", "gold": "#c8972a", "blue": "#7ab0e8", "red": "#e07070"}.get(act["dot"], "#c8972a")
        st.markdown(f"""
        <div style="display:flex;gap:12px;padding:12px 0;border-bottom:1px solid rgba(200,151,42,.15);">
            <div style="width:10px;height:10px;border-radius:50%;background:{dot_color};margin-top:4px;flex-shrink:0;"></div>
            <div style="flex:1;">
                <div style="font-size:14px;line-height:1.4;">{act['text']}</div>
                <div style="font-size:11px;color:#7e8aa2;margin-top:4px;">{act['time']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_mod:
    st.markdown('<div class="stCard" style="padding:22px;">', unsafe_allow_html=True)
    st.subheader("Quick Launch Modules")
    
    modules = [
        "🏠 Rent Dashboard", "👥 Tenant Mgmt", "💰 Lipa Mdogo", "🔑 Caretaker",
        "🏗️ Vacancies", "🅿️ Parking", "🔧 Renovations", "📅 Schedule",
        "💧 Water/Trash", "🧾 KRA Tax", "🔒 Security", "🏷️ White-Label",
        "🗺️ Unmapped Areas", "🧑‍🔧 Service Pros", "📊 Full Reports"
    ]
    
    cols_mod = st.columns(4)
    for i, mod in enumerate(modules):
        with cols_mod[i % 4]:
            st.button(mod, use_container_width=True, key=f"mod_{i}")
    st.markdown("</div>", unsafe_allow_html=True)

st.caption("© 2026 Mwarokin Estates • Milki Command Center")
```

This is a complete, modern, premium Streamlit dashboard that faithfully recreates the provided UI with dark luxury gold aesthetics, interactive charts, responsive layout, and all key sections. Run with `streamlit run app.py`.