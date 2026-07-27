```python
import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="ME | Property Portfolio",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium modern look
st.markdown("""
<style>
    .main {
        background-color: #f8f9fc;
    }
    .stApp {
        background-color: #f8f9fc;
    }
    .card {
        background: white;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .card:hover {
        transform: translateY(-4px);
        box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
    }
    .kpi-card {
        background: white;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    }
    .listing-card {
        background: white;
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        transition: all 0.3s ease;
    }
    .listing-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1);
    }
    .status-available { background: #10b981; color: white; }
    .status-occupied { background: #3b82f6; color: white; }
    .status-pending { background: #f59e0b; color: white; }
    .nav-item {
        padding: 12px 16px;
        border-radius: 12px;
        margin-bottom: 4px;
        cursor: pointer;
    }
    .nav-item:hover, .nav-item.active {
        background: #f1f5f9;
    }
    .price-ribbon {
        position: absolute;
        top: 16px;
        right: 16px;
        background: rgba(255,255,255,0.95);
        color: #1e2937;
        padding: 8px 16px;
        border-radius: 12px;
        text-align: right;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 40px;">
        <div style="background: linear-gradient(135deg, #1e40af, #3b82f6); color: white; 
                    width: 48px; height: 48px; border-radius: 12px; display: flex; 
                    align-items: center; justify-content: center; font-weight: 700; font-size: 22px;">
            ME
        </div>
        <div>
            <h3 style="margin: 0; font-weight: 600;">Metro Estates</h3>
            <p style="margin: 0; color: #64748b; font-size: 14px;">Property Management</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("**MAIN**")
    menu_options = {
        "Dashboard": "🏠",
        "Listings": "🏢",
        "Leads": "🔍",
        "Tenants": "👥",
        "Maintenance": "🔧"
    }
    
    selected = st.selectbox("Navigate", list(menu_options.keys()), index=1)
    
    st.markdown("**OPERATIONS**")
    st.button("Finances", icon="📊", use_container_width=True)
    st.button("Documents", icon="📄", use_container_width=True)
    st.button("Keys & Locks", icon="🔑", use_container_width=True)
    st.button("Smart Parking", icon="🅿️", use_container_width=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns([3,1])
    with col1:
        st.button("Settings", icon="⚙️", use_container_width=True)
    with col2:
        st.markdown("""
        <div style="background: #334155; color: white; width: 42px; height: 42px; border-radius: 50%; 
                    display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 15px;">
            RM
        </div>
        """, unsafe_allow_html=True)

# Main Content
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
    <div>
        <span style="color: #64748b; font-size: 14px;">Dashboard</span>
        <span style="color: #64748b; margin: 0 8px;">›</span>
        <span style="font-weight: 600; color: #1e2937;">Listings &amp; Units</span>
    </div>
    
    <div style="display: flex; gap: 12px; align-items: center;">
        <div style="position: relative;">
            <input type="text" placeholder="Search by address, unit, tenant..." 
                   style="padding: 10px 40px 10px 16px; border-radius: 9999px; border: 1px solid #e2e8f0; width: 320px; font-size: 14px;">
            🔍
        </div>
        <button style="background: white; border: 1px solid #e2e8f0; padding: 8px 14px; border-radius: 9999px;">🛎️</button>
        <button style="background: white; border: 1px solid #e2e8f0; padding: 8px 14px; border-radius: 9999px;">📅</button>
    </div>
</div>
""", unsafe_allow_html=True)

# Page Header
col_title, col_actions = st.columns([3, 2])
with col_title:
    st.markdown("**Property Portfolio**")
    st.title("Listings & Units")
    st.caption("24 properties · Nairobi Metropolitan Area")

with col_actions:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.button("⬇️ Export", use_container_width=True)
    with c2:
        st.button("✏️ Bulk edit", use_container_width=True)
    with c3:
        st.button("➕ Add listing", type="primary", use_container_width=True)

# KPI Strip
st.markdown("### Key Metrics")
kpi_cols = st.columns(4)

with kpi_cols[0]:
    st.markdown("""
    <div class="kpi-card">
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <div>
                <div style="color: #64748b; font-size: 14px;">Total units</div>
                <div style="font-size: 42px; font-weight: 700; margin: 8px 0;">24</div>
            </div>
            <div style="background: #eff6ff; color: #1e40af; padding: 12px; border-radius: 12px;">🏢</div>
        </div>
        <div style="color: #10b981; font-size: 14px;">↑ +3 this month</div>
    </div>
    """, unsafe_allow_html=True)

with kpi_cols[1]:
    st.markdown("""
    <div class="kpi-card">
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <div>
                <div style="color: #64748b; font-size: 14px;">Occupied</div>
                <div style="font-size: 42px; font-weight: 700; margin: 8px 0;">18</div>
            </div>
            <div style="background: #ecfdf5; color: #10b981; padding: 12px; border-radius: 12px;">✅</div>
        </div>
        <div style="color: #10b981; font-size: 14px;">75% occupancy rate</div>
    </div>
    """, unsafe_allow_html=True)

with kpi_cols[2]:
    st.markdown("""
    <div class="kpi-card">
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <div>
                <div style="color: #64748b; font-size: 14px;">Monthly income</div>
                <div style="font-size: 32px; font-weight: 700; margin: 8px 0;">KES 386K</div>
            </div>
            <div style="background: #fefce8; color: #ca8a04; padding: 12px; border-radius: 12px;">💰</div>
        </div>
        <div style="color: #10b981; font-size: 14px;">↑ 12% vs last month</div>
    </div>
    """, unsafe_allow_html=True)

with kpi_cols[3]:
    st.markdown("""
    <div class="kpi-card">
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <div>
                <div style="color: #64748b; font-size: 14px;">Overdue rent</div>
                <div style="font-size: 42px; font-weight: 700; margin: 8px 0; color: #ef4444;">3</div>
            </div>
            <div style="background: #fee2e2; color: #ef4444; padding: 12px; border-radius: 12px;">⚠️</div>
        </div>
        <div style="color: #64748b; font-size: 14px;">2 resolved this week</div>
    </div>
    """, unsafe_allow_html=True)

# Toolbar
tab1, tab2, tab3, tab4, tab5 = st.tabs(["All properties", "Available", "Occupied", "Pending", "On hold"])

with tab1:
    filter_cols = st.columns([2, 3, 1, 1])
    with filter_cols[0]:
        st.selectbox("Area", ["All areas", "Westlands", "Karen", "Kilimani", "Lavington", "Runda", "Ngara"])
    with filter_cols[1]:
        st.multiselect("Property Type", ["Apartments", "Commercial", "Villas", "Townhouses"], default=["Apartments"])
    with filter_cols[2]:
        st.selectbox("Sort by", ["Newest first", "Price: High to Low", "Price: Low to High", "Occupancy"])
    with filter_cols[3]:
        view = st.radio("View", ["Grid", "List", "Map"], horizontal=True)

    # Listings Grid
    st.markdown("### Active Listings")
    
    listings_data = [
        {
            "title": "Westlands View — Unit 4B",
            "location": "Westlands, Nairobi",
            "price": "85,000",
            "beds": 3, "baths": 2, "size": "112 m²",
            "status": "Available",
            "featured": True,
            "img": "🏙️"
        },
        {
            "title": "Karen Highlands — House 7",
            "location": "Karen, Nairobi",
            "price": "175,000",
            "beds": 4, "baths": 3, "size": "240 m²",
            "status": "Occupied",
            "tenant": "N. Kamau",
            "img": "🏡"
        },
        {
            "title": "Kilimani Plaza — Suite 12A",
            "location": "Kilimani, Nairobi",
            "price": "55,000",
            "beds": 2, "baths": 1, "size": "78 m²",
            "status": "Pending",
            "img": "🏢"
        },
        {
            "title": "Lavington Gardens — Unit 3",
            "location": "Lavington, Nairobi",
            "price": "110,000",
            "beds": 3, "baths": 2, "size": "130 m²",
            "status": "Occupied",
            "tenant": "A. Wanjiku",
            "overdue": True,
            "img": "🏠"
        },
        {
            "title": "Runda Ridge — Villa 2",
            "location": "Runda, Nairobi",
            "price": "280,000",
            "beds": 5, "baths": 4, "size": "380 m²",
            "status": "Available",
            "premium": True,
            "img": "🏘️"
        },
        {
            "title": "Ngara Court — Flat B5",
            "location": "Ngara, Nairobi",
            "price": "42,000",
            "beds": 1, "baths": 1, "size": "48 m²",
            "status": "Maintenance",
            "img": "🏬"
        }
    ]
    
    cols = st.columns(3)
    for idx, listing in enumerate(listings_data):
        col_idx = idx % 3
        with cols[col_idx]:
            status_class = "status-available" if listing["status"] == "Available" else \
                          "status-occupied" if listing["status"] == "Occupied" else "status-pending"
            
            st.markdown(f"""
            <div class="listing-card">
                <div style="height: 180px; background: linear-gradient(135deg, #1e3a8a, #3b82f6); 
                            position: relative; display: flex; align-items: center; justify-content: center; color: white; font-size: 64px;">
                    {listing['img']}
                    <div style="position: absolute; top: 16px; left: 16px; background: rgba(16,185,129,0.9); 
                                color: white; padding: 4px 12px; border-radius: 9999px; font-size: 13px; font-weight: 500;">
                        {listing['status']}
                    </div>
                    <div style="position: absolute; top: 16px; right: 16px; background: white; color: #1e2937; 
                                padding: 8px 14px; border-radius: 12px; text-align: right; font-size: 15px; line-height: 1.1;">
                        <strong>KES {listing['price']}</strong><br>
                        <span style="font-size: 12px; color: #64748b;">/ month</span>
                    </div>
                </div>
                <div style="padding: 20px;">
                    <div style="font-weight: 600; font-size: 17px; margin-bottom: 4px;">{listing['title']}</div>
                    <div style="color: #64748b; font-size: 14px; margin-bottom: 16px;">📍 {listing['location']}</div>
                    
                    <div style="display: flex; gap: 12px; flex-wrap: wrap; font-size: 13px;">
                        <div>🛏️ {listing['beds']} bed</div>
                        <div>🛁 {listing['baths']} bath</div>
                        <div>📏 {listing['size']}</div>
                    </div>
                    
                    <div style="margin-top: 20px; border-top: 1px solid #f1f5f9; padding-top: 16px; 
                                display: flex; justify-content: space-between; align-items: center; font-size: 14px;">
                        <div style="color: #64748b;">Listed recently</div>
                        <button style="background: #1e40af; color: white; border: none; padding: 8px 20px; border-radius: 9999px; font-size: 13px;">
                            View details →
                        </button>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# Leads Panel
st.markdown("---")
st.subheader("Prospective Tenants")
lead_cols = st.columns(4)

leads = [
    ("JN", "John Nicholson", "New", "11/24/2024"),
    ("HD", "Harry Davidson", "New", "02/25/2024"),
    ("CR", "Christina Roy", "Working", "11/11/2024"),
    ("MR", "Michael Rork", "Approved", "02/24/2024"),
]

for i, (initials, name, tag, date) in enumerate(leads):
    with lead_cols[i % 4]:
        st.markdown(f"""
        <div class="card" style="text-align: center; padding: 20px;">
            <div style="width: 52px; height: 52px; background: #334155; color: white; 
                        border-radius: 50%; margin: 0 auto 12px; display: flex; 
                        align-items: center; justify-content: center; font-weight: 700;">{initials}</div>
            <div style="font-weight: 600;">{name}</div>
            <div style="font-size: 13px; color: #64748b;">{date}</div>
            <div style="margin-top: 12px; background: #f1f5f9; display: inline-block; padding: 2px 14px; border-radius: 9999px; font-size: 12px;">
                {tag}
            </div>
        </div>
        """, unsafe_allow_html=True)

# Website Banner
st.markdown("---")
st.markdown("""
<div style="background: white; border-radius: 16px; padding: 32px; display: flex; gap: 40px; box-shadow: 0 4px 20px rgba(0,0,0,0.06);">
    <div style="flex: 1;">
        <div style="color: #64748b; font-size: 13px; letter-spacing: 0.5px;">PUBLIC PRESENCE</div>
        <h2 style="margin: 8px 0 12px;">Listing Website</h2>
        <p style="color: #475569; max-width: 420px;">Choose your public-facing website structure. Applicants can view active listings, request tours, and contact your team directly.</p>
        <div style="margin-top: 24px; display: flex; gap: 12px;">
            <button style="background: #1e40af; color: white; border: none; padding: 12px 28px; border-radius: 9999px;">🌐 Configure domain</button>
            <button style="border: 2px solid #e2e8f0; background: transparent; padding: 12px 28px; border-radius: 9999px;">👁️ Preview site</button>
        </div>
    </div>
    <div style="flex: 1; border-left: 1px solid #e2e8f0; padding-left: 40px;">
        <div style="margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="width: 22px; height: 22px; background: #10b981; border-radius: 50%;"></div>
                <strong>Rentals page only</strong>
            </div>
            <p style="margin-left: 34px; color: #64748b; font-size: 14px;">Single page showing active listings</p>
        </div>
        <div style="display: flex; align-items: center; gap: 12px; background: #f8fafc; padding: 16px; border-radius: 12px;">
            <div style="width: 22px; height: 22px; background: #1e40af; border-radius: 50%;"></div>
            <div>
                <strong>Company website</strong>
                <p style="color: #64748b; font-size: 14px; margin: 0;">Full site with custom home page, rentals, team &amp; contact</p>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.caption(f"© Metro Estates • {datetime.now().strftime('%Y')} • Nairobi")
```

**This is a complete, modern, professional Streamlit application** that faithfully recreates the provided premium property management UI. Run it with:

```bash
streamlit run app.py
```

It includes:
- Responsive sidebar navigation
- KPI dashboard cards
- Interactive listings grid with hover effects
- Leads section
- Toolbar tabs/filters
- Premium styling and real estate-focused design
- Fully functional Python code (no external HTML required)