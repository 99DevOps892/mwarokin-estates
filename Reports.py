```python
import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Mwarokin Estates | Reports",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium modern look
st.markdown("""
<style>
    .main-header {
        font-family: 'Segoe UI', sans-serif;
        font-weight: 700;
        color: #1a3c34;
    }
    .stButton>button {
        border-radius: 8px;
        height: 42px;
        font-weight: 600;
    }
    .report-card {
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 20px;
        background: white;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        transition: all 0.2s;
    }
    .report-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
    }
    .nav-tab {
        padding: 12px 20px;
        margin-right: 8px;
        border-radius: 8px;
        cursor: pointer;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }
    .success-box {
        background: linear-gradient(135deg, #1a3c34, #2e5c4e);
        color: white;
        padding: 24px;
        border-radius: 16px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 32px;">
        <div style="background: #1a3c34; color: white; width: 42px; height: 42px; border-radius: 10px; 
                    display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 22px;">M</div>
        <div style="font-weight: 700; font-size: 22px; color: #1a3c34;">Mwarokin Estates</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("**Navigation**")
    if st.button("🏠 Dashboard", use_container_width=True):
        st.session_state.current_screen = "grid"
    if st.button("🏢 Properties", use_container_width=True):
        st.session_state.current_screen = "grid"
    if st.button("👥 Tenants", use_container_width=True):
        st.session_state.current_screen = "grid"
    if st.button("💰 Finances", use_container_width=True):
        st.session_state.current_screen = "grid"
    if st.button("📊 Reports", use_container_width=True, type="primary"):
        st.session_state.current_screen = "grid"
    if st.button("🔧 Maintenance", use_container_width=True):
        st.session_state.current_screen = "grid"
    if st.button("📄 Documents", use_container_width=True):
        st.session_state.current_screen = "grid"
    if st.button("🗓️ Calendar", use_container_width=True):
        st.session_state.current_screen = "grid"
    
    st.markdown("**Account**")
    if st.button("⚙️ Settings", use_container_width=True):
        pass
    if st.button("💬 Support", use_container_width=True):
        pass

# Top Bar
col1, col2, col3 = st.columns([1, 3, 2])
with col1:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px;">
        <div style="background: #1a3c34; color: white; width: 38px; height: 38px; border-radius: 8px; 
                    display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 20px;">M</div>
        <div style="font-weight: 700; font-size: 20px;">Mwarokin Estates</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.text_input("🔍 Search reports, properties…", placeholder="Search reports, properties…", label_visibility="collapsed")

with col3:
    cols = st.columns([1,1,1,2])
    with cols[0]:
        st.button("🔔", use_container_width=True)
    with cols[1]:
        st.button("💬", use_container_width=True)
    with cols[2]:
        st.button("⚙️", use_container_width=True)
    with cols[3]:
        st.button("👤 RB", use_container_width=True)

# Navigation Tabs
st.markdown("---")
tabs = st.tabs(["📊 Reports", "📈 Rentability Report", "📋 Tax Preparation", "🗂️ KRA P9 Tax Form", "✅ Purchase Success"])

# Session State
if 'current_screen' not in st.session_state:
    st.session_state.current_screen = "grid"

# Screen 1: Reports Grid
with tabs[0]:
    st.markdown("<h1 class='main-header'>Reports</h1>", unsafe_allow_html=True)
    st.markdown("Generate, view & download housing management reports for your portfolio")
    
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.markdown("**Display: All** — **21 Total** reports available")
    with col_b:
        st.selectbox("Category", ["All Categories", "Financial", "Tax", "Tenant", "Property"], label_visibility="collapsed")
    
    # Reports Grid
    cols = st.columns(3)
    
    with cols[0]:
        with st.container():
            st.markdown("""
            <div class="report-card">
                <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;">
                    <div style="background:#fcd34d; color:#78350f; width:48px; height:48px; border-radius:10px; 
                                display:flex; align-items:center; justify-content:center; font-size:28px;">📈</div>
                    <div><strong>Rentability Analysis</strong></div>
                </div>
                <div style="color:#4b5563; font-size:14px; line-height:1.5; margin-bottom:20px;">
                    Detailed rent estimates & market benchmarks<br>
                    Property-specific vacancy rate analysis<br>
                    Powered by real Kenyan market data
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="background:#fef3c7; color:#78350f; padding:4px 12px; border-radius:9999px; font-size:13px;">⭐ Special Offer</div>
                    <button style="background:#1a3c34; color:white; border:none; padding:8px 20px; border-radius:8px; cursor:pointer;"
                            onclick="window.location.reload()">View →</button>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with cols[1]:
        st.markdown("""
        <div class="report-card">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;">
                <div style="background:#86efac; color:#166534; width:48px; height:48px; border-radius:10px; 
                            display:flex; align-items:center; justify-content:center; font-size:28px;">👤</div>
                <div><strong>Tenant Statement</strong></div>
            </div>
            <div style="color:#4b5563; font-size:14px; line-height:1.5; margin-bottom:20px;">
                Shows all income from tenants<br>
                Includes paid and unpaid invoices<br>
                Displays deposits and credits
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="background:#bbf7d0; color:#166534; padding:4px 12px; border-radius:9999px; font-size:13px;">Accrual</div>
                <button style="background:#1a3c34; color:white; border:none; padding:8px 20px; border-radius:8px; cursor:pointer;">View →</button>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[2]:
        st.markdown("""
        <div class="report-card">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;">
                <div style="background:#93c5fd; color:#1e40af; width:48px; height:48px; border-radius:10px; 
                            display:flex; align-items:center; justify-content:center; font-size:28px;">🏠</div>
                <div><strong>Rent Roll</strong></div>
            </div>
            <div style="color:#4b5563; font-size:14px; line-height:1.5; margin-bottom:20px;">
                Generated as of today's date<br>
                Active lease details & tenant info
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="background:#fde047; color:#78350f; padding:4px 12px; border-radius:9999px; font-size:13px;">Live Data</div>
                <button style="background:#1a3c34; color:white; border:none; padding:8px 20px; border-radius:8px; cursor:pointer;">View →</button>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # More cards in additional rows
    st.markdown("### More Reports")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.button("📋 Tax Preparation", use_container_width=True, on_click=lambda: st.session_state.update({"current_screen": "tax"}))
    with c2:
        st.button("🗂️ KRA P9 Tax Form", use_container_width=True, on_click=lambda: st.session_state.update({"current_screen": "form1099"}))
    with c3:
        st.button("🏢 Property Owner Statement", use_container_width=True)

# Screen 2: Rentability Report
with tabs[1]:
    st.markdown("<h1 class='main-header'>Rentability Report</h1>", unsafe_allow_html=True)
    st.markdown("Purchase a detailed rental market analysis for any property in your portfolio")
    
    col_left, col_right = st.columns([1, 1.3])
    
    with col_left:
        st.subheader("What's included in this report?")
        st.markdown("**Comprehensive Kenyan rental market intelligence**")
        
        features = [
            ("🗺️", "Rental Saturation", "A detailed snapshot of the local Nairobi market..."),
            ("📈", "Rent Trends", "Localized comparable properties and days on market data..."),
            ("📍", "Neighbourhood Comparison", "Gross yield data by neighbourhood...")
        ]
        
        for icon, title, desc in features:
            st.markdown(f"""
            <div style="display:flex; gap:16px; margin-bottom:24px;">
                <div style="font-size:32px;">{icon}</div>
                <div>
                    <strong>{title}</strong><br>
                    <span style="font-size:14px; color:#64748b;">{desc}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col_right:
        st.subheader("Property Information")
        property_options = ["Kilimani Heights — Apt 4B", "Westlands Tower — Unit 12", "Karen Villa — Block C"]
        selected_property = st.selectbox("Property *", property_options)
        
        subcols = st.columns(3)
        with subcols[0]:
            st.selectbox("Bedrooms *", ["1", "2", "3", "4+"])
        with subcols[1]:
            st.selectbox("Bathrooms *", ["1", "1.5", "2", "3"])
        with subcols[2]:
            st.number_input("Size (sqft)", value=1200)
        
        st.subheader("Payment Method")
        payment = st.radio("Choose payment", ["M-Pesa / Mobile Money", "Saved Card", "Enter New Card"], horizontal=True)
        
        if payment == "M-Pesa / Mobile Money":
            st.markdown("**📱 M-Pesa**")
        
        st.markdown("---")
        st.markdown("""
        <div style="background: #fefce8; padding: 20px; border-radius: 12px; text-align: center;">
            <div style="font-size: 28px; font-weight: 700; color: #78350f;">KES 2,499</div>
            <button style="background: #ca8a04; color: white; border: none; padding: 14px 32px; border-radius: 8px; 
                          font-weight: 700; margin-top: 16px; width: 100%;">🛒 Purchase Report</button>
        </div>
        """, unsafe_allow_html=True)

# Screen 3: Tax Preparation
with tabs[2]:
    st.markdown("<h1 class='main-header'>Tax Preparation Report</h1>", unsafe_allow_html=True)
    
    st.subheader("Date Range")
    preset = st.selectbox("Presets", ["Current Financial Year (Jul–Jun)", "Last Financial Year", "Custom range"])
    
    dcols = st.columns(2)
    with dcols[0]:
        st.date_input("Date From", value=date(2025, 7, 1))
    with dcols[1]:
        st.date_input("Date To", value=date(2026, 6, 30))
    
    st.subheader("Accounting Type")
    accounting = st.radio("Type", ["Accrual", "Cash"], horizontal=True)
    
    st.subheader("Expense Section Format")
    kra_format = st.toggle("KRA Schedule Format", value=True)
    
    st.subheader("Report Format")
    format_choice = st.radio("Output", ["PDF Download", "Excel (.xlsx)", "Email to Owner"], horizontal=True)
    
    st.markdown("---")
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        st.button("Cancel", use_container_width=True)
    with c2:
        st.button("👁 Preview", use_container_width=True, type="secondary")
    with c3:
        st.button("⬇️ Download Report", use_container_width=True, type="primary")

# Screen 4: KRA P9
with tabs[3]:
    st.markdown("<h1 class='main-header'>KRA P9 Tax Form</h1>", unsafe_allow_html=True)
    
    left, right = st.columns([1, 1])
    
    with left:
        st.subheader("P9 Form Generation")
        st.markdown("P9A for Service Professionals and P9B for Property Owners")
        st.subheader("Determining Amounts")
        st.subheader("Send Digital Copies")
    
    with right:
        st.subheader("Date Range")
        st.selectbox("Tax Year", ["FY 2025 (Jan–Dec 2025)", "FY 2024"])
        d1, d2 = st.columns(2)
        with d1:
            st.date_input("From", value=date(2025, 1, 1))
        with d2:
            st.date_input("To", value=date(2025, 12, 31))
        
        st.subheader("Recipients")
        st.multiselect("Service Pros", ["Kamau Plumbing", "Elite Electricals", "Quick Fix Ltd"])
        
        st.button("⬇️ Generate P9 Forms", type="primary", use_container_width=True)

# Screen 5: Success
with tabs[4]:
    st.markdown("""
    <div class="success-box">
        <h2>✅ Purchase Complete</h2>
        <p style="font-size:18px;">Your rentability report has been generated and is ready to download</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.success("You have successfully purchased the report!")
    
    st.subheader("Property Information")
    st.info("**Kilimani Heights — Apt 4B, Nairobi**")
    
    metrics = st.columns(4)
    with metrics[0]:
        st.metric("Mwarokin Estimate", "KES 85,000 / mo")
    with metrics[1]:
        st.metric("Confidence Score", "89.0%")
    with metrics[2]:
        st.metric("Est. Vacancy Rate", "3.74%")
    with metrics[3]:
        st.metric("Comps Found", "36")
    
    st.button("⬇️ Download Report", type="primary", use_container_width=True)

# Footer
st.markdown("---")
st.markdown("© 2026 Mwarokin Estates • Nairobi, Kenya", unsafe_allow_html=True)
```

**This is a complete, modern, premium Streamlit Python application** that faithfully recreates the provided UI with professional styling, interactivity, and all major sections. Run with `streamlit run app.py`.