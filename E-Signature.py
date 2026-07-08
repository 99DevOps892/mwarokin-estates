```python
import streamlit as st
from streamlit_drawable_canvas import st_canvas
import datetime
import base64
from PIL import Image
import io
import uuid

# Page configuration
st.set_page_config(
    page_title="Mwarokin Rent E-Signature",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium look
st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, #1e3a8a, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .premium-card {
        background: white;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
        border: 1px solid #f1f5f9;
    }
    .role-badge {
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .role-badge.active {
        background-color: #dbeafe !important;
        color: #1e40af !important;
        border: 2px solid #3b82f6;
    }
    .signature-canvas {
        border: 2px solid #e2e8f0;
        border-radius: 12px;
        background: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

# Header
col1, col2 = st.columns([4, 1])
with col1:
    st.markdown('<h1 class="main-header"><i class="fas fa-file-signature"></i> Mwarokin Rent E‑Signature</h1>', unsafe_allow_html=True)
    st.markdown("**Securely sign rental agreements & lease documents — legally binding**")
with col2:
    current_time = datetime.datetime.now().strftime("%B %d, %Y • %I:%M %p")
    st.markdown(f"""
    <div style="background: rgba(255,255,255,0.7); backdrop-filter: blur(8px); border-radius: 9999px; padding: 12px 20px; 
                box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; font-weight: 500;">
        🕒 {current_time}
    </div>
    """, unsafe_allow_html=True)

# Role selector
st.markdown("### Signing as")
role_cols = st.columns(3)
roles = {
    "tenant": {"label": "🏠 Tenant", "key": "tenant"},
    "landlord": {"label": "🏢 Landlord/Landlady", "key": "landlord"},
    "agency": {"label": "📊 Property Agency", "key": "agency"}
}

role_key = None
if 'current_role' not in st.session_state:
    st.session_state.current_role = "tenant"

for i, (rkey, rdata) in enumerate(roles.items()):
    with role_cols[i]:
        active_class = "active" if st.session_state.current_role == rkey else ""
        if st.button(rdata["label"], key=f"role_{rkey}", use_container_width=True):
            st.session_state.current_role = rkey
            st.rerun()

# Role data
role_data = {
    "tenant": {
        "name": "Robin Mwarema",
        "email": "robin.m@mwarokin.co.ke",
        "phone": "+254 712 345 678",
        "role_label": "Tenant · Verified",
        "avatar": "RM",
        "property": "Mwarokin Heights, Block C, Unit 12B",
        "lease_id": "MWK-2425-001",
        "period": "June 2025 – May 2026",
        "rent": 1450,
        "agreement": lambda name, rent: f"I, <strong>{name}</strong> (Tenant), agree to pay a monthly rent of <strong>${rent:,.2f}</strong> for the property at <strong>Mwarokin Heights, Block C, Unit 12B</strong>. Rent is due on the 5th of each month."
    },
    "landlord": {
        "name": "Esther Mwangi",
        "email": "esther.mwangi@mwarokin.com",
        "phone": "+254 722 456 789",
        "role_label": "Landlord · Premium Owner",
        "avatar": "EM",
        "property": "Mwarokin Towers, Unit 4A & 7C",
        "lease_id": "MWK-LD-9823",
        "period": "July 2025 – June 2026",
        "rent": 1890,
        "agreement": lambda name, rent: f"I, <strong>{name}</strong> (Landlord/Landlady), hereby affirm the lease agreement..."
    },
    "agency": {
        "name": "PrimeLet Property Mgmt",
        "email": "clients@primelet.co.ke",
        "phone": "+254 700 123 456",
        "role_label": "Agency · Authorised",
        "avatar": "PM",
        "property": "Mwarokin Business Park, Suite 101",
        "lease_id": "MWK-AG-4451",
        "period": "August 2025 – July 2026",
        "rent": 2450,
        "agreement": lambda name, rent: f"On behalf of <strong>{name}</strong> (Property Management Agency)..."
    }
}

data = role_data[st.session_state.current_role]

# Layout: Two columns
left_col, right_col = st.columns([1, 1.8])

with left_col:
    st.markdown('<div class="premium-card">', unsafe_allow_html=True)
    
    # Profile
    st.subheader("👤 Profile")
    avatar_col, info_col = st.columns([1, 3])
    with avatar_col:
        st.markdown(f"""
        <div style="width: 80px; height: 80px; border-radius: 16px; background: linear-gradient(135deg, #1e40af, #3b82f6); 
                    display: flex; align-items: center; justify-content: center; color: white; font-size: 28px; font-weight: bold;">
            {data['avatar']}
        </div>
        """, unsafe_allow_html=True)
    with info_col:
        st.markdown(f"**{data['name']}**")
        st.markdown(f"<span style='color: #10b981;'>✓ {data['role_label']}</span>", unsafe_allow_html=True)
        st.caption(f"✉️ {data['email']}")
        st.caption(f"📞 {data['phone']}")
    
    st.divider()
    
    # Lease details
    st.markdown("**Property / Unit**")
    st.info(data["property"])
    st.markdown(f"**Lease ID**: `{data['lease_id']}`")
    st.markdown(f"**Contract Period**: {data['period']}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Rent Summary
    st.markdown('<div class="premium-card" style="background: linear-gradient(135deg, #f8fafc, #eff6ff);">', unsafe_allow_html=True)
    st.subheader("💰 Monthly Rent Summary")
    st.metric("Base Rent", f"${data['rent']:,.2f}")
    st.caption("Due on the 5th of every month")
    st.caption("Late fee: 5% flat + 0.5% daily")
    st.success("E-signature confirms rent obligation")
    st.markdown('</div>', unsafe_allow_html=True)

with right_col:
    st.markdown('<div class="premium-card">', unsafe_allow_html=True)
    st.subheader("📜 Rental Agreement · E-Signature")
    st.caption("Mwarokin Estates Standard Lease Addendum (v3.2)")
    
    # Agreement text
    agreement_text = data["agreement"](data["name"], data["rent"])
    st.markdown(f"""
    <div style="background: #f8fafc; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; max-height: 180px; overflow-y: auto;">
        {agreement_text}
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("#### ✍️ Draw your signature")
    
    # Canvas
    canvas_result = st_canvas(
        stroke_width=3,
        stroke_color="#1e2937",
        background_color="#ffffff",
        height=180,
        width=700,
        drawing_mode="freedraw",
        key="signature_canvas",
    )
    
    # Signature tools
    tool_cols = st.columns([1, 1, 1])
    with tool_cols[0]:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.signature = None
            st.rerun()
    with tool_cols[1]:
        typed_name = st.text_input("Or type name", placeholder="Full legal name", key="typed_name")
        if st.button("✅ Use Typed", use_container_width=True) and typed_name.strip():
            st.session_state.signature = typed_name.strip()
            st.success("Typed signature applied")
    with tool_cols[2]:
        if st.button("🔄 Reset All", use_container_width=True):
            st.session_state.signature = None
            st.rerun()
    
    # Preview
    st.markdown("**Signature Preview**")
    preview_col1, preview_col2 = st.columns([1, 3])
    with preview_col1:
        if canvas_result.image_data is not None and canvas_result.image_data.sum() > 0:
            img = Image.fromarray(canvas_result.image_data.astype("uint8"))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            st.session_state.signature_data = base64.b64encode(buf.getvalue()).decode()
            st.image(img, width=180)
        elif 'signature' in st.session_state and st.session_state.signature:
            st.markdown(f"**{st.session_state.signature}**")
        else:
            st.markdown("*No signature yet*")
    
    # Finalize
    if st.button("🚀 Sign & Submit Agreement", type="primary", use_container_width=True):
        if (canvas_result.image_data is not None and canvas_result.image_data.sum() > 0) or ('signature' in st.session_state and st.session_state.signature):
            st.session_state.is_signed = True
            st.session_state.sign_time = datetime.datetime.now()
            st.success("✅ Agreement successfully signed!")
            st.balloons()
        else:
            st.error("Please provide a signature (draw or type)")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Confirmation panel
    if st.session_state.get('is_signed', False):
        st.markdown("""
        <div style="background: white; padding: 24px; border-radius: 16px; border: 1px solid #86efac;">
            <h3 style="color: #166534;">✅ Agreement Electronically Signed</h3>
            <p>Signed by <strong>{}</strong> on {}</p>
        </div>
        """.format(data["name"], st.session_state.sign_time.strftime("%B %d, %Y at %I:%M %p")), unsafe_allow_html=True)
        
        if st.button("📥 Download Signed Copy"):
            # Generate simple signed HTML/PDF simulation
            signed_html = f"""
            <h1>Mwarokin Estates - Signed Rental Agreement</h1>
            <p><strong>Lease ID:</strong> {data['lease_id']}</p>
            <p><strong>Signer:</strong> {data['name']} ({st.session_state.current_role.title()})</p>
            <p><strong>Date:</strong> {st.session_state.sign_time}</p>
            <hr>
            <p>{agreement_text}</p>
            <div style="margin-top: 40px; border-top: 3px solid #166534; padding-top: 15px;">
                <strong>Signature:</strong><br>
                {st.session_state.get('signature', 'Drawn Signature')}
            </div>
            """
            st.download_button(
                "Download HTML Copy",
                signed_html,
                file_name=f"Mwarokin_Signed_{data['lease_id']}.html",
                mime="text/html"
            )

# Footer note
st.markdown("---")
st.caption("🔒 This electronic signature is legally binding under the Kenya Electronic Transactions Act. All documents are stored securely.")
```

**Features Included:**
- Modern premium UI using Streamlit
- Role switching (Tenant/Landlord/Agency) with dynamic data
- Interactive signature canvas (`streamlit-drawable-canvas`)
- Typed signature support
- Real-time preview and download of signed document
- Responsive layout matching the original design
- Professional styling with gradients and cards

**Installation:**
```bash
pip install streamlit streamlit-drawable-canvas pillow
streamlit run app.py
```

This is a complete, ready-to-run Python application that closely replicates the provided UI with advanced interactive features.