```python
import streamlit as st
from datetime import datetime
import re

st.set_page_config(
    page_title="Mwarokin Estates • Onboarding",
    page_icon="🏠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for premium modern look
st.markdown("""
<style>
    .main { background-color: #0f0f12; color: #f0f0f0; }
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #c9a84c, #d4b46a);
        color: #111;
        font-weight: 600;
        border: none;
        padding: 14px 24px;
        border-radius: 8px;
        font-size: 16px;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #d4b46a, #e0c080);
        transform: translateY(-2px);
    }
    .role-card {
        border: 2px solid #333;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        transition: all 0.3s;
        cursor: pointer;
        background: #1a1a1e;
    }
    .role-card:hover, .role-card.selected {
        border-color: #c9a84c;
        transform: translateY(-4px);
        box-shadow: 0 20px 40px rgba(201,168,76,0.15);
    }
    .step-indicator {
        display: flex;
        justify-content: center;
        gap: 8px;
        margin: 30px 0;
    }
    .step-dot {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        border: 3px solid #333;
        background: #1a1a1e;
    }
    .step-dot.active {
        border-color: #c9a84c;
        background: #c9a84c;
        color: #111;
    }
    .step-dot.done {
        background: #22c55e;
        color: white;
        border-color: #22c55e;
    }
    .success-screen {
        text-align: center;
        padding: 40px 20px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'step' not in st.session_state:
    st.session_state.step = 0
if 'role' not in st.session_state:
    st.session_state.role = None
if 'selected_plan' not in st.session_state:
    st.session_state.selected_plan = None
if 'addons' not in st.session_state:
    st.session_state.addons = {}
if 'profile_data' not in st.session_state:
    st.session_state.profile_data = {}
if 'terms_accepted' not in st.session_state:
    st.session_state.terms_accepted = False

TOTAL_STEPS = 4

def next_step():
    st.session_state.step += 1

def prev_step():
    if st.session_state.step > 0:
        st.session_state.step -= 1

def reset_form():
    for key in list(st.session_state.keys()):
        if key not in ['step']:
            del st.session_state[key]
    st.session_state.step = 0
    st.rerun()

# Header
st.markdown("""
<div style="text-align:center; margin-bottom:20px;">
    <h1 style="margin:0; font-size:2.4rem; background: linear-gradient(90deg, #c9a84c, #f0d090); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        Mwarokin Estates
    </h1>
    <p style="color:#aaa; font-size:1.1rem;">Africa's Finest Property Platform</p>
</div>
""", unsafe_allow_html=True)

# Progress
steps = ["Your Role", "Profile", "Services", "Confirm"]
col_progress = st.columns(len(steps))
for i, label in enumerate(steps):
    with col_progress[i]:
        active = i == st.session_state.step
        done = i < st.session_state.step
        color = "#c9a84c" if active else ("#22c55e" if done else "#444")
        st.markdown(f"""
        <div style="text-align:center;">
            <div style="margin:0 auto; width:42px; height:42px; border-radius:50%; background:{color}; color:white; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:18px; border:3px solid {'#c9a84c' if active else '#333'};">
                {i+1}
            </div>
            <p style="margin-top:8px; font-size:0.9rem; color:{'#c9a84c' if active else '#aaa'};">{label}</p>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# Step 1: Role Selection
if st.session_state.step == 0:
    st.markdown("### 👤 Select Your Role")
    st.markdown("Tell us who you are so we can personalize your experience.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🏠 Landlord", use_container_width=True, key="role_landlord"):
            st.session_state.role = "landlord"
            next_step()
            st.rerun()
    
    with col2:
        if st.button("🏢 Property Agency", use_container_width=True, key="role_agency"):
            st.session_state.role = "agency"
            next_step()
            st.rerun()
    
    with col3:
        if st.button("🔑 Tenant", use_container_width=True, key="role_tenant"):
            st.session_state.role = "tenant"
            next_step()
            st.rerun()
    
    st.info("🔒 Your information is encrypted and used only to personalize your experience.", icon="🔒")

# Step 2: Profile
elif st.session_state.step == 1:
    role = st.session_state.role
    st.markdown(f"### 📋 Complete Your {role.title()} Profile")
    
    if role == "landlord":
        with st.form("landlord_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                name = st.text_input("Full Name *", placeholder="Amina Kamau")
            with col_b:
                phone = st.text_input("Phone Number *", placeholder="+254 7XX XXX XXX")
            
            email = st.text_input("Email Address *", placeholder="you@example.com")
            
            st.markdown("**Property Information**")
            address = st.text_input("Primary Property Address *", placeholder="14 Lavington Drive, Nairobi")
            
            col_c, col_d = st.columns(2)
            with col_c:
                num_props = st.selectbox("Number of Properties *", ["", "1 – 2", "3 – 5", "6 – 10", "10+"])
            with col_d:
                prop_type = st.selectbox("Property Type", ["", "Residential", "Commercial", "Mixed-Use", "Land / Plots"])
            
            submitted = st.form_submit_button("Continue →")
            if submitted:
                if not name or not email or not phone or not address or not num_props:
                    st.error("Please fill all required fields")
                elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                    st.error("Please enter a valid email")
                else:
                    st.session_state.profile_data = {
                        "name": name, "phone": phone, "email": email,
                        "address": address, "num_properties": num_props,
                        "property_type": prop_type
                    }
                    next_step()
                    st.rerun()
    
    elif role == "agency":
        with st.form("agency_form"):
            name = st.text_input("Agency / Company Name *", placeholder="PanAfrica Property Management Ltd")
            
            col_a, col_b = st.columns(2)
            with col_a:
                contact = st.text_input("Contact Person *", placeholder="Your full name")
            with col_b:
                phone = st.text_input("Business Phone *", placeholder="+254 7XX XXX XXX")
            
            email = st.text_input("Business Email *", placeholder="agency@example.com")
            
            st.markdown("**Portfolio Details**")
            col_c, col_d = st.columns(2)
            with col_c:
                managed = st.selectbox("Properties Under Management *", ["", "1 – 20", "21 – 50", "51 – 150", "150+"])
            with col_d:
                license_no = st.text_input("Registration / License No. (Optional)")
            
            submitted = st.form_submit_button("Continue →")
            if submitted:
                if not name or not contact or not email or not phone or not managed:
                    st.error("Please fill all required fields")
                elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                    st.error("Please enter a valid email")
                else:
                    st.session_state.profile_data = {
                        "name": name, "contact": contact, "phone": phone,
                        "email": email, "managed": managed, "license": license_no
                    }
                    next_step()
                    st.rerun()
    
    elif role == "tenant":
        with st.form("tenant_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                name = st.text_input("Full Name *", placeholder="James Mwangi")
            with col_b:
                phone = st.text_input("Phone Number *", placeholder="+254 7XX XXX XXX")
            
            email = st.text_input("Email Address *", placeholder="you@example.com")
            
            address = st.text_input("Current Address *", placeholder="Kilimani, Nairobi")
            
            col_c, col_d = st.columns(2)
            with col_c:
                move_in = st.date_input("Desired Move-In Date *", value=datetime.today())
            with col_d:
                budget = st.selectbox("Monthly Budget", ["", "Under KES 20,000", "KES 20,000 – 50,000", "KES 50,000 – 100,000", "KES 100,000+"])
            
            col_e, col_f = st.columns(2)
            with col_e:
                occupants = st.number_input("Number of Occupants", min_value=1, max_value=20, value=2)
            with col_f:
                prop_type = st.selectbox("Preferred Property Type", ["Any", "Studio / Bedsitter", "1-Bedroom Apartment", "2-Bedroom Apartment", "3+ Bedroom Apartment", "Townhouse / Maisonette", "Commercial Space"])
            
            submitted = st.form_submit_button("Continue →")
            if submitted:
                if not name or not email or not phone or not address or not move_in:
                    st.error("Please fill all required fields")
                elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                    st.error("Please enter a valid email")
                else:
                    st.session_state.profile_data = {
                        "name": name, "phone": phone, "email": email,
                        "address": address, "move_in": str(move_in),
                        "budget": budget, "occupants": occupants, "preferred_type": prop_type
                    }
                    next_step()
                    st.rerun()

# Step 3: Services & Plans
elif st.session_state.step == 2:
    role = st.session_state.role
    st.markdown("### 🏷️ Choose Your Plan")
    
    if role in ["landlord", "agency"]:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("**Essential**\n\nKES 2,500/mo\n\nCore leasing & rent collection", use_container_width=True, key="plan_ess"):
                st.session_state.selected_plan = "essential"
                st.rerun()
        
        with col2:
            st.markdown("""
            <div style="border:2px solid #c9a84c; border-radius:12px; padding:16px; text-align:center; background:#1f1f24;">
                <strong>Professional</strong><br>
                <small style="color:#c9a84c;">Most Popular</small><br><br>
                KES 8,900/mo<br><br>
                Screening, analytics & automation
            </div>
            """, unsafe_allow_html=True)
            if st.button("Select Professional", use_container_width=True, key="plan_pro"):
                st.session_state.selected_plan = "professional"
                st.rerun()
        
        with col3:
            if st.button("**Enterprise**\n\nCustom Pricing\n\nUnlimited + white-label", use_container_width=True, key="plan_ent"):
                st.session_state.selected_plan = "enterprise"
                st.rerun()
        
        st.markdown("**Optional Add-ons**")
        addons_list = {
            "maintenance": "Maintenance Coordination (+KES 3,900/mo)",
            "legal": "Legal Document Automation (+KES 2,500/mo)",
            "marketing": "Premium Listing & Marketing (+KES 4,900/mo)"
        }
        for key, label in addons_list.items():
            if key not in st.session_state.addons:
                st.session_state.addons[key] = False
            st.session_state.addons[key] = st.checkbox(label, value=st.session_state.addons[key], key=f"addon_{key}")
    
    else:  # Tenant
        st.success("✅ **Free Tenant Digital Portal** included")
        st.info("Pay rent via M-Pesa, submit maintenance requests, view documents and more.")
        
        st.markdown("**Optional Services**")
        col_a, col_b = st.columns(2)
        with col_a:
            if "concierge" not in st.session_state.addons:
                st.session_state.addons["concierge"] = False
            st.session_state.addons["concierge"] = st.checkbox("Moving Concierge & Assistance (Free)", value=st.session_state.addons["concierge"])
        with col_b:
            if "rentersinsurance" not in st.session_state.addons:
                st.session_state.addons["rentersinsurance"] = False
            st.session_state.addons["rentersinsurance"] = st.checkbox("Renters Insurance (From KES 800/mo)", value=st.session_state.addons["rentersinsurance"])
    
    if st.button("Continue to Review →", type="primary", use_container_width=True):
        if role in ["landlord", "agency"] and not st.session_state.selected_plan:
            st.error("Please select a plan")
        else:
            next_step()
            st.rerun()

# Step 4: Confirmation
elif st.session_state.step == 3:
    st.markdown("### ✅ Review & Confirm")
    
    st.markdown("**Profile Summary**")
    data = st.session_state.profile_data
    role_label = {"landlord": "Landlord", "agency": "Property Agency", "tenant": "Tenant"}[st.session_state.role]
    
    summary = f"**Role:** {role_label}\n\n"
    for k, v in data.items():
        summary += f"**{k.replace('_', ' ').title()}:** {v}\n\n"
    
    st.info(summary)
    
    st.markdown("**Selected Services**")
    if st.session_state.role == "tenant":
        st.success("Tenant Digital Portal (Free)")
        for k, v in st.session_state.addons.items():
            if v:
                st.write(f"• {k.replace('_', ' ').title()}")
    else:
        plan_names = {"essential": "Essential - KES 2,500/mo", "professional": "Professional - KES 8,900/mo", "enterprise": "Enterprise - Custom"}
        st.write(f"**Plan:** {plan_names.get(st.session_state.selected_plan, '—')}")
        for k, v in st.session_state.addons.items():
            if v:
                st.write(f"• Add-on: {k.replace('_', ' ').title()}")
    
    st.checkbox("I agree to the Terms of Service and Privacy Policy", 
                value=st.session_state.terms_accepted,
                key="terms",
                on_change=lambda: setattr(st.session_state, 'terms_accepted', st.session_state.terms))
    
    col_back, col_submit = st.columns([1, 3])
    with col_back:
        if st.button("← Back", use_container_width=True):
            prev_step()
            st.rerun()
    with col_submit:
        if st.button("Complete Onboarding", type="primary", use_container_width=True):
            if not st.session_state.terms_accepted:
                st.error("Please accept the terms")
            else:
                with st.spinner("Creating your account..."):
                    import time
                    time.sleep(2.5)
                
                st.success("🎉 Welcome to Mwarokin Estates!")
                st.balloons()
                
                st.markdown("""
                <div class="success-screen">
                    <h2>Your account has been created successfully!</h2>
                    <p>Our team will contact you within 24 hours with your welcome kit and platform access.</p>
                    <p style="margin-top:30px;"><strong>Check your email for verification.</strong></p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("Go to Dashboard 🏠", type="primary", use_container_width=True):
                    st.success("Redirecting to dashboard... (Demo complete)")
                    st.session_state.step = 0
                    reset_form()

# Navigation
if st.session_state.step > 0:
    if st.button("← Back", key="global_back"):
        prev_step()
        st.rerun()

st.caption("Mwarokin Estates © 2026 • Secure Onboarding")
```