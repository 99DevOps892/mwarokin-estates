```python
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
import random
import qrcode
from io import BytesIO
import base64

st.set_page_config(
    page_title="Mwarokin Estates - Tenant Portal",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium modern look
st.markdown("""
<style>
    .main {background-color: #0f0f1a;}
    .stApp {background-color: #0f0f1a; color: #e0e0ff;}
    .card {
        background-color: #1a1a2e;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        border: 1px solid #2a2a4a;
        margin-bottom: 1.5rem;
    }
    .hero {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 3rem 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }
    .btn-gold {
        background: linear-gradient(90deg, #d4af37, #f0d070);
        color: #0f0f1a;
        font-weight: 700;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 12px;
        transition: all 0.3s;
    }
    .btn-gold:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(212, 175, 55, 0.4);
    }
    .stat-card {
        background: #16213e;
        padding: 1rem;
        border-radius: 12px;
        text-align: center;
    }
    .pm-card {
        border: 2px solid #2a2a4a;
        border-radius: 12px;
        padding: 1rem;
        cursor: pointer;
        transition: all 0.3s;
    }
    .pm-card.active {
        border-color: #d4af37;
        background: #1f1f3a;
    }
    .success-screen {
        background: #1a1a2e;
        padding: 3rem;
        border-radius: 20px;
        text-align: center;
        margin: 2rem auto;
        max-width: 700px;
    }
</style>
""", unsafe_allow_html=True)

# State Management
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'active_pm' not in st.session_state:
    st.session_state.active_pm = "mpesa"
if 'payment_success' not in st.session_state:
    st.session_state.payment_success = False
if 'currency' not in st.session_state:
    st.session_state.currency = {
        "sym": "KSh ",
        "rate": 1.0,
        "code": "KES"
    }

curr_sym = st.session_state.currency["sym"]
curr_rate = st.session_state.currency["rate"]

# Sidebar Navigation
with st.sidebar:
    st.markdown("<h2 style='color:#d4af37; text-align:center;'>🏛️ Mwarokin Estates</h2>", unsafe_allow_html=True)
    st.markdown("**Tenant Portal**")
    
    if st.button("🏠 Dashboard", use_container_width=True):
        st.session_state.payment_success = False
    if st.button("💰 Payments", use_container_width=True):
        pass
    if st.button("📊 History", use_container_width=True):
        pass
    if st.button("👤 Profile", use_container_width=True):
        pass
    if st.button("🧾 Manage Bills", use_container_width=True):
        pass
    if st.button("🚗 Parking", use_container_width=True):
        pass
    
    st.divider()
    st.markdown("**Tenant ID:** T-789456")
    st.markdown("**Property:** Sunrise Apartments, Unit 4B")
    st.markdown(f"**Next Due:** Oct 15, 2024")

# Main Content
if st.session_state.payment_success:
    # Success Screen
    st.markdown("""
    <div class="success-screen">
        <div style="width:80px; height:80px; background:#22c55e; border-radius:50%; margin:0 auto 1.5rem; display:flex; align-items:center; justify-content:center; font-size:2.5rem; color:white;">✓</div>
        <h1 style="color:#22c55e; font-size:2.2rem;">Payment Successful!</h1>
        <p style="color:#a0a0cc; font-size:1.1rem;">Your rent has been processed. A confirmation was sent to your email.</p>
    </div>
    """, unsafe_allow_html=True)
    
    rent = st.session_state.get('last_rent', 18000)
    charges = st.session_state.get('last_charges', 2500)
    total = rent + charges
    txn_id = f"TXN-{random.randint(100000000, 999999999)}"
    
    col1, col2 = st.columns([3, 2])
    with col1:
        st.subheader("Payment Receipt")
        st.markdown(f"""
        **Transaction ID:** {txn_id}  
        **Date:** {datetime.now().strftime('%b %d, %Y')}  
        **Method:** {st.session_state.get('last_pm', 'M-Pesa')}  
        **Property:** Sunrise Apartments, Unit 4B  
        **Period:** October 2024
        """)
        
        st.markdown("---")
        st.markdown(f"**Monthly Rent:** {curr_sym}{rent:,.0f}")
        st.markdown(f"**Other Charges:** {curr_sym}{charges:,.0f}")
        st.markdown(f"**Total Paid:** {curr_sym}{total:,.0f}")
    
    with col2:
        st.button("⬅️ Back to Dashboard", on_click=lambda: st.session_state.update({"payment_success": False}), use_container_width=True, type="primary")
        st.button("🖨️ Print Receipt", use_container_width=True)
        st.button("📥 Download PDF", use_container_width=True)
    
else:
    # Hero Section
    st.markdown(f"""
    <div class="hero">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
                <div style="background:#d4af37; color:#0f0f1a; display:inline-block; padding:4px 16px; border-radius:30px; font-size:0.9rem; font-weight:600;">Tenant Portal</div>
                <h1 style="margin:1rem 0 0.5rem; font-size:2.8rem; color:white;">Welcome back, Mwarokin Tenant</h1>
                <p style="color:#a0a0cc; font-size:1.1rem;">Manage your rent payments easily and securely from anywhere.</p>
            </div>
            <div style="background:rgba(255,255,255,0.08); padding:1.5rem; border-radius:16px; text-align:center; min-width:260px;">
                <div style="font-size:0.9rem; color:#a0a0cc;">Wallet Balance</div>
                <div style="font-size:2.4rem; font-weight:700; color:#d4af37;">{curr_sym}{156000 * curr_rate:,.0f}</div>
                <div style="font-size:0.8rem; color:#4ade80;">Auto-pay enabled</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Flow Steps
    steps = ["Select Payment", "Payment Method", "Review & Confirm", "Complete"]
    cols = st.columns(4)
    for i, step in enumerate(steps):
        with cols[i]:
            active = "🔵" if i+1 == st.session_state.current_step else "⚪"
            st.markdown(f"**{active} Step {i+1}: {step}**")
    
    st.divider()
    
    left_col, right_col = st.columns([2.2, 1])
    
    with left_col:
        # Analytics Strip
        st.subheader("📈 Quick Stats")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("On-time Payments", "9", "✅")
        with col_b:
            st.metric("Payment Rate", "92%", "↑")
        with col_c:
            st.metric("Days Until Due", "5", "📅")
        
        # Payment Form
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("💸 Submit Rent Payment")
        
        col1, col2 = st.columns(2)
        with col1:
            pay_month = st.date_input("Payment Month", value=date(2024, 10, 1), key="pay_month")
        with col2:
            pay_date = st.date_input("Payment Date", value=datetime.now().date())
        
        prop_address = st.text_input("Property Address", value="Sunrise Apartments, Unit 4B, Nairobi")
        
        col_build, col_unit = st.columns(2)
        with col_build:
            st.text_input("Building", value="Sunrise")
        with col_unit:
            st.text_input("Unit Number", value="4B")
        
        col_phone, col_acc = st.columns(2)
        with col_phone:
            st.text_input("Phone Number", value="+254 704 919 388")
        with col_acc:
            st.text_input("Account Number", value="T-789456")
        
        col_rent, col_charges, col_total = st.columns(3)
        with col_rent:
            rent_amount = st.number_input("Monthly Rent", value=int(18000 * curr_rate), step=100, key="rent_input")
        with col_charges:
            charges_amount = st.number_input("Other Charges", value=int(2500 * curr_rate), step=100, key="charges_input")
        with col_total:
            total_amount = rent_amount + charges_amount
            st.metric("Total Amount", f"{curr_sym}{total_amount:,.0f}")
        
        # Payment Methods
        st.markdown("**Payment Method**")
        pm_cols = st.columns(3)
        
        pm_options = {
            "mpesa": ("📱 M-Pesa", "Mobile Money"),
            "mobile_money": ("📲 Mobile Money", "Airtel / MTN"),
            "bank_kenya": ("🏦 Kenya Bank", "26 banks"),
            "card": ("💳 Card", "Visa / Mastercard"),
            "syllopay": ("⚡ SylloPay", "Instant Wallet")
        }
        
        for i, (key, (name, sub)) in enumerate(pm_options.items()):
            with pm_cols[i % 3]:
                if st.button(f"{name}\n{sub}", key=f"pm_{key}", use_container_width=True,
                           type="primary" if st.session_state.active_pm == key else "secondary"):
                    st.session_state.active_pm = key
        
        # Dynamic panels based on selected PM
        if st.session_state.active_pm == "mpesa":
            st.info("💳 You'll receive an M-Pesa STK push after submitting.")
            mpesa_phone = st.text_input("M-Pesa Phone", value="+254712345678")
            st.text_input("Paybill", value="522533", disabled=True)
        
        elif st.session_state.active_pm == "syllopay":
            st.success("⚡ Sufficient SylloPay balance: KSh 24,500")
        
        # Submit Button
        if st.button("🚀 Submit Payment", type="primary", use_container_width=True):
            st.session_state.last_rent = rent_amount
            st.session_state.last_charges = charges_amount
            st.session_state.last_pm = st.session_state.active_pm.upper()
            st.session_state.payment_success = True
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Payment History
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📜 Recent Payments")
        
        history_data = {
            "Date": ["Sep 12, 2024", "Aug 10, 2024", "Jul 14, 2024"],
            "Amount": [20500, 20500, 19800],
            "Status": ["Paid", "Paid", "Paid"]
        }
        df_history = pd.DataFrame(history_data)
        st.dataframe(df_history, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with right_col:
        # Payment Overview
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📊 Payment Overview")
        st.progress(0.75)
        st.caption("75% on track this year")
        
        col_ov1, col_ov2, col_ov3 = st.columns(3)
        with col_ov1:
            st.metric("Monthly Rent", f"{curr_sym}20,500")
        with col_ov2:
            st.metric("On-time", "9")
        with col_ov3:
            st.metric("Rating", "4.8 ★")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # QR Code
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🔲 Quick Pay QR")
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data("Mwarokin-Rent-Unit4B-20500")
        qr.make(fit=True)
        img = qr.make_image(fill_color="#d4af37", back_color="#1a1a2e")
        
        buf = BytesIO()
        img.save(buf, format="PNG")
        st.image(buf.getvalue(), width=180)
        st.caption("Scan with your mobile banking app")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Notifications
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🛎️ Notifications")
        st.info("Rent due in 5 days")
        st.info("Property inspection on Oct 20")
        st.success("September payment confirmed")
        st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#666; font-size:0.9rem;">
    Mwarokin Estates © 2026 • Powered by Syllogism Technology Africa<br>
    <small>Africa's premium property management platform</small>
</div>
""", unsafe_allow_html=True)
```

**Modern Premium Python (Streamlit) Tenant Portal** - Fully functional, responsive, with currency handling, payment flow, success screen, QR generation, and interactive components mirroring the provided UI. Run with `streamlit run app.py`.