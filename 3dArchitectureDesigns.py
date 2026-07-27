```python
import streamlit as st
import time
import random
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

# Page configuration
st.set_page_config(
    page_title="Mwarokin Estates — Premium Architectural Design",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (modern dark theme matching the original)
st.markdown("""
<style>
    .main {
        background: #0a0a0f;
        color: #f0f0f5;
    }
    .stApp {
        background: #0a0a0f;
    }
    .glow-text {
        background: linear-gradient(135deg, #6c5ce7, #00d4ff);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        font-weight: 800;
    }
    .card {
        background: rgba(28, 28, 46, 0.8);
        border-radius: 14px;
        padding: 1.5rem;
        border: 1px solid rgba(255,255,255,0.06);
        box-shadow: 0 12px 40px rgba(0,0,0,0.5);
        transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    }
    .card:hover {
        transform: translateY(-6px);
        box-shadow: 0 0 60px rgba(108, 92, 231, 0.25);
        border-color: rgba(108, 92, 231, 0.3);
    }
    .feature-icon {
        width: 56px;
        height: 56px;
        background: linear-gradient(135deg, #6c5ce7, #00d4ff);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.6rem;
        color: white;
        margin-bottom: 1rem;
    }
    .hero-title {
        font-size: 3.8rem;
        line-height: 1.05;
        font-weight: 800;
        letter-spacing: -2px;
    }
    .section-header {
        text-align: center;
        margin-bottom: 3rem;
    }
    .ai-chat-container {
        height: 420px;
        overflow-y: auto;
        background: #1c1c2e;
        border-radius: 12px;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Navigation
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 2rem;">
        <div style="width: 48px; height: 48px; background: linear-gradient(135deg, #6c5ce7, #00d4ff); 
                    border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-size: 1.4rem;">
            🏗️
        </div>
        <h2 style="margin: 0; font-weight: 800;">Mwarokin</h2>
    </div>
    """, unsafe_allow_html=True)
    
    page = st.radio("Navigation", 
                   ["🏠 Home", "🎨 Design Studio", "📊 Dashboard", "✨ Features", "🤖 AI Assistant"],
                   label_visibility="collapsed")
    
    st.divider()
    st.markdown("**Quick Actions**")
    if st.button("🚀 Start New Project", type="primary", use_container_width=True):
        st.success("New project initialized! Redirecting to studio...")
        time.sleep(1)
        st.rerun()
    
    if st.button("📥 Export Current Design", use_container_width=True):
        st.toast("✅ Exported as .obj + .dwg", icon="📦")

# Main Content
if page == "🏠 Home":
    # Hero Section
    col1, col2 = st.columns([5, 4])
    
    with col1:
        st.markdown('<div class="hero-badge" style="display: inline-flex; align-items: center; gap: 8px; background: rgba(108,92,231,0.15); padding: 8px 16px; border-radius: 50px; font-size: 0.9rem; margin-bottom: 1rem;">'
                    '<span style="color:#00e676;">●</span> AI-Powered Design Platform</div>', unsafe_allow_html=True)
        
        st.markdown('<h1 class="hero-title">Transform Concepts into<br><span class="glow-text">Architectural Masterpieces</span></h1>', unsafe_allow_html=True)
        
        st.markdown("""
        <p style="font-size: 1.25rem; color: #b0b0c8; max-width: 520px; line-height: 1.7;">
            Mwarokin Estates combines real-time 3D rendering, AI-driven assistance, 
            and immersive visualization to bring your architectural visions to life.
        </p>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Try for Free", type="primary", use_container_width=True):
                st.switch_page("pages/Design_Studio.py") if hasattr(st, "switch_page") else st.success("Studio opened!")
        with c2:
            if st.button("Watch Demo", use_container_width=True):
                st.toast("🎥 Demo video would play here")
    
    with col2:
        # 3D House Visualization (CSS + HTML embedded)
        house_html = """
        <div style="width:100%; height:420px; background: radial-gradient(circle at 30% 40%, rgba(108,92,231,0.15), transparent 70%); 
                    border-radius: 24px; border: 1px solid rgba(255,255,255,0.08); display: flex; align-items: center; justify-content: center; position: relative;">
            <div style="width: 260px; height: 240px; transform-style: preserve-3d; transition: transform 0.4s; cursor: grab;" 
                 onmousedown="this.style.cursor='grabbing'; let rot=0; function move(e){rot+=(e.movementX||0)*0.8; this.style.transform=`rotateY(${rot}deg)`;}"
                 onmouseup="this.style.cursor='grab'">
                <!-- Roof -->
                <div style="position:absolute; width:0; height:0; border-left:130px solid transparent; border-right:130px solid transparent; 
                            border-bottom:110px solid #8b5a2b; top:-90px; left:0; filter: drop-shadow(0 10px 30px rgba(0,0,0,0.6));"></div>
                <!-- Base -->
                <div style="position:absolute; width:260px; height:170px; background:linear-gradient(145deg,#a67b5b,#7a5a3a); 
                            border-radius:8px 8px 0 0; top:20px; box-shadow:0 20px 50px rgba(0,0,0,0.6);">
                    <!-- Windows -->
                    <div style="position:absolute; width:52px; height:52px; background:linear-gradient(135deg,#6bb8e8,#3a8ab8); 
                                border:4px solid #4a3a2a; border-radius:8px; top:32px; left:32px; box-shadow:inset 0 0 25px rgba(0,0,0,0.4);"></div>
                    <div style="position:absolute; width:52px; height:52px; background:linear-gradient(135deg,#6bb8e8,#3a8ab8); 
                                border:4px solid #4a3a2a; border-radius:8px; top:32px; right:32px; box-shadow:inset 0 0 25px rgba(0,0,0,0.4);"></div>
                    <!-- Door -->
                    <div style="position:absolute; width:52px; height:88px; background:linear-gradient(145deg,#5a3a1a,#3a2510); 
                                bottom:0; left:50%; transform:translateX(-50%); border-radius:8px 8px 0 0;"></div>
                    <!-- Chimney -->
                    <div style="position:absolute; width:28px; height:58px; background:linear-gradient(#8b4513,#5a2d0c); top:-25px; right:32px; border-radius:6px;"></div>
                </div>
            </div>
            <div style="position:absolute; bottom:24px; left:50%; transform:translateX(-50%); background:rgba(0,0,0,0.7); 
                        padding:8px 20px; border-radius:50px; font-size:0.85rem; border:1px solid rgba(108,92,231,0.3);">
                🖱️ Drag to rotate • Real-time 3D
            </div>
        </div>
        """
        st.components.v1.html(house_html, height=460)

    # Features Teaser
    st.markdown("---")
    st.markdown('<h2 style="text-align:center; margin: 3rem 0 2rem;">Built for Next-Gen Architecture</h2>', unsafe_allow_html=True)
    
    cols = st.columns(3)
    features = [
        ("🧊 Real-Time 3D", "Photorealistic rendering with instant updates"),
        ("🕶️ VR/AR Ready", "Immerse yourself in your designs"),
        ("🤖 AI Assistant", "Smart suggestions and structural analysis")
    ]
    for col, (title, desc) in zip(cols, features):
        with col:
            st.markdown(f'<div class="card"><h3>{title}</h3><p>{desc}</p></div>', unsafe_allow_html=True)

elif page == "🎨 Design Studio":
    st.markdown('<h1 class="glow-text" style="text-align:center;">Interactive Design Studio</h1>', unsafe_allow_html=True)
    
    col_tools, col_canvas = st.columns([1, 3])
    
    with col_tools:
        st.markdown("### 🛠️ Toolbox")
        
        st.selectbox("Structure", ["Walls", "Floors", "Roofs", "Windows", "Doors"], index=0)
        
        st.markdown("**Materials**")
        mat_cols = st.columns(2)
        with mat_cols[0]:
            st.button("🌲 Wood", use_container_width=True)
            st.button("🪨 Concrete", use_container_width=True)
        with mat_cols[1]:
            st.button("🪟 Glass", use_container_width=True)
            st.button("⚙️ Metal", use_container_width=True)
        
        if st.button("✨ Generate with AI", type="primary", use_container_width=True):
            st.success("AI generating optimized layout... (demo)")
            time.sleep(1.5)
            st.balloons()
    
    with col_canvas:
        st.markdown('<div style="background:#1c1c2e; border-radius:16px; height:520px; display:flex; align-items:center; justify-content:center; border:1px solid rgba(108,92,231,0.2);">'
                    '<div style="text-align:center;"><h2>🏠 Live 3D Canvas</h2><p>Real-time rendering active</p></div></div>', 
                    unsafe_allow_html=True)
        
        ctrl_cols = st.columns(4)
        for i, label in enumerate(["3D View", "VR Mode", "AR Overlay", "Blueprint"]):
            with ctrl_cols[i]:
                st.button(label, use_container_width=True)

elif page == "📊 Dashboard":
    st.markdown('<h1 style="text-align:center;">Project Performance</h1>', unsafe_allow_html=True)
    
    # Live metrics
    if "dash_values" not in st.session_state:
        st.session_state.dash_values = {
            "projects": 12,
            "hours": 156,
            "efficiency": 87,
            "savings": 24.5
        }
    
    cols = st.columns(4)
    
    with cols[0]:
        st.metric("Active Projects", st.session_state.dash_values["projects"], "+2 this month")
    with cols[1]:
        st.metric("Design Hours", st.session_state.dash_values["hours"], "+24 this week")
    with cols[2]:
        st.metric("AI Efficiency", f"{st.session_state.dash_values['efficiency']}%", "+5%")
    with cols[3]:
        st.metric("Cost Savings", f"${st.session_state.dash_values['savings']}K", "est.")
    
    # Auto-update simulation
    if st.button("Refresh Live Data"):
        st.session_state.dash_values["projects"] += random.randint(0, 1)
        st.session_state.dash_values["hours"] += random.randint(2, 6)
        st.session_state.dash_values["efficiency"] = min(98, st.session_state.dash_values["efficiency"] + random.randint(0, 2))
        st.session_state.dash_values["savings"] += round(random.uniform(-0.3, 0.8), 1)
        st.rerun()
    
    # Charts
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[1,2,3,4,5], y=[65,72,81,84,87], mode="lines+markers", name="Efficiency Trend"))
    fig.update_layout(template="plotly_dark", height=380, title="Efficiency Over Time")
    st.plotly_chart(fig, use_container_width=True)

elif page == "✨ Features":
    st.markdown('<h1 style="text-align:center;">Capabilities</h1>', unsafe_allow_html=True)
    
    features_list = [
        ("Real-Time 3D Rendering", "Photorealistic materials, dynamic lighting, instant feedback", "🧊", 95),
        ("VR / AR Immersion", "Step inside your designs", "🥽", 85),
        ("AI Design Assistant", "Intelligent recommendations", "🤖", 92),
        ("Smart Automation", "Auto-generate floor plans", "⚡", 88),
        ("Collaboration Tools", "Real-time cloud sync", "👥", 91),
        ("Export & Integration", "DWG, OBJ, FBX support", "📤", 96)
    ]
    
    cols = st.columns(2)
    for i, (title, desc, icon, perc) in enumerate(features_list):
        with cols[i % 2]:
            st.markdown(f"""
            <div class="card">
                <div style="display:flex; gap:16px;">
                    <div class="feature-icon">{icon}</div>
                    <div style="flex:1;">
                        <h3>{title}</h3>
                        <p style="color:#b0b0c8;">{desc}</p>
                        <div style="background:#333; height:6px; border-radius:4px; margin-top:12px;">
                            <div style="width:{perc}%; height:100%; background:linear-gradient(90deg,#6c5ce7,#00d4ff); border-radius:4px;"></div>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

elif page == "🤖 AI Assistant":
    st.markdown("### 🤖 AI Design Assistant")
    st.caption("Ask anything about architecture, materials, codes, or optimization")
    
    # Chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! I'm your AI architectural assistant. How can I help today?"}
        ]
    
    # Display chat
    chat_container = st.container(height=420)
    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f"**You:** {msg['content']}")
            else:
                st.markdown(f"**🧠 AI:** {msg['content']}")
    
    # Input
    with st.form("ai_form", clear_on_submit=True):
        prompt = st.text_input("Ask me anything...", placeholder="Suggest sustainable kitchen materials...")
        submitted = st.form_submit_button("Send", type="primary")
        
        if submitted and prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Simulated AI responses
            responses = [
                "I recommend using bamboo flooring combined with recycled steel beams for sustainability.",
                "Optimizing window placement on the south side could increase natural light by ~28%.",
                "Your current layout passes 96% of building codes. Would you like me to generate alternatives?",
                "Consider adding a green roof to reduce cooling costs by up to 25%."
            ]
            reply = random.choice(responses)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#6a6a82; padding:2rem 0;">
    Mwarokin Estates © 2026 — Powered by Modern Python + Streamlit<br>
    <small>Real-time 3D • AI Assistant • Live Dashboard</small>
</div>
""", unsafe_allow_html=True)

# Background glow effect simulation via CSS
st.markdown("""
<style>
    body::before {
        content: '';
        position: fixed;
        top: -300px;
        right: -300px;
        width: 600px;
        height: 600px;
        background: radial-gradient(circle, rgba(108,92,231,0.12), transparent 70%);
        z-index: -1;
        pointer-events: none;
    }
</style>
""", unsafe_allow_html=True)
```

**How to run:**

1. Save as `app.py`
2. Install: `pip install streamlit plotly`
3. Run: `streamlit run app.py`

This is a complete, modern, single-file Python Streamlit application that captures the spirit, interactivity, and real-time feel of the original HTML design using pure Python. It includes live dashboard updates, interactive AI chat, drag-hint 3D preview (via HTML canvas), and responsive sections. Enjoy!