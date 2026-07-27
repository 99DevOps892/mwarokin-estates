
"""
Video.py — Mwarokin Estates Property Films
Modern agentic Streamlit application
"""

import streamlit as st
from dataclasses import dataclass, field
from typing import List, Optional
import time
from datetime import datetime

# ──────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────

@dataclass
class Property:
    id: int
    title: str
    location: str
    type: str
    price: int
    bedrooms: int
    bathrooms: int
    area: int
    duration: str
    video: str
    description: str

PROPERTIES: List[Property] = [
    Property(1, "Luxury Villa with Pool", "Karen, Nairobi", "villa", 25_000_000, 4, 3, 3200, "02:14",
             "https://assets.mixkit.co/videos/preview/mixkit-a-modern-house-with-a-swimming-pool-43217-large.mp4",
             "Stunning modern villa with panoramic views, swimming pool, and premium finishes throughout."),
    Property(2, "Modern Apartment", "Westlands, Nairobi", "apartment", 8_500_000, 3, 2, 1800, "01:48",
             "https://assets.mixkit.co/videos/preview/mixkit-modern-living-room-with-a-large-window-43215-large.mp4",
             "Contemporary apartment in a prime location with modern amenities and gated security."),
    Property(3, "Family House", "Runda, Nairobi", "house", 18_500_000, 5, 4, 4200, "02:39",
             "https://assets.mixkit.co/videos/preview/mixkit-exterior-of-a-modern-house-43216-large.mp4",
             "Spacious family home with a large garden — built for entertaining and everyday living."),
    Property(4, "Commercial Space", "CBD, Nairobi", "commercial", 45_000_000, 0, 2, 5000, "01:56",
             "https://assets.mixkit.co/videos/preview/mixkit-modern-office-interior-43214-large.mp4",
             "Prime commercial space in the central business district with high visibility and access."),
    Property(5, "Lakeside Villa", "Naivasha", "villa", 35_000_000, 6, 5, 5500, "03:02",
             "https://assets.mixkit.co/videos/preview/mixkit-country-house-in-a-meadow-43218-large.mp4",
             "Exclusive lakeside property with private shoreline access and uninterrupted views."),
    Property(6, "Studio Apartment", "Kilimani, Nairobi", "apartment", 5_500_000, 1, 1, 800, "01:22",
             "https://assets.mixkit.co/videos/preview/mixkit-modern-bedroom-with-a-double-bed-43213-large.mp4",
             "Compact, efficient studio with modern finishes in a walkable, convenient location."),
]

# ──────────────────────────────────────────────
# Agentic Filter Engine
# ──────────────────────────────────────────────

class PropertyAgent:
    """Lightweight agent that manages filtering, ranking and recommendations."""

    def __init__(self, inventory: List[Property]):
        self.inventory = inventory
        self.view_log: List[int] = []

    def filter(self, type_filter: str = "all", price_filter: str = "all") -> List[Property]:
        result = self.inventory
        if type_filter != "all":
            result = [p for p in result if p.type == type_filter]
        if price_filter != "all":
            if price_filter == "0-5":
                result = [p for p in result if p.price < 5_000_000]
            elif price_filter == "5-10":
                result = [p for p in result if 5_000_000 <= p.price < 10_000_000]
            elif price_filter == "10-20":
                result = [p for p in result if 10_000_000 <= p.price < 20_000_000]
            elif price_filter == "20+":
                result = [p for p in result if p.price >= 20_000_000]
        return result

    def recommend(self, current: Property, top_k: int = 2) -> List[Property]:
        same_type = [p for p in self.inventory if p.type == current.type and p.id != current.id]
        return sorted(same_type, key=lambda x: abs(x.price - current.price))[:top_k]

    def log_view(self, prop_id: int):
        self.view_log.append(prop_id)

# ──────────────────────────────────────────────
# Page Config & Styling
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="Mwarokin Estates · Property Films",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:ital,wght@0,600;1,600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: #0a0a0b;
    color: #e8e6e3;
}

h1, h2, h3 {
    font-family: 'Playfair Display', serif !important;
    color: #f5f2eb !important;
}

.hero-title {
    font-size: 3.2rem;
    line-height: 1.15;
    margin-bottom: 0.6rem;
}
.hero-title em {
    color: #c9a84c;
    font-style: italic;
}
.eyebrow {
    font-size: 0.75rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #c9a84c;
    margin-bottom: 0.4rem;
}
.hero-sub {
    color: #a8a29e;
    font-size: 1.05rem;
    max-width: 520px;
    line-height: 1.65;
}
.stat-box {
    background: #141416;
    border: 1px solid #2a2a2e;
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    text-align: center;
}
.stat-box b {
    display: block;
    font-size: 1.6rem;
    color: #c9a84c;
    font-family: monospace;
}
.stat-box span {
    font-size: 0.78rem;
    color: #78716c;
}
.card {
    background: #141416;
    border: 1px solid #2a2a2e;
    border-radius: 14px;
    overflow: hidden;
    transition: border-color 0.25s;
}
.card:hover {
    border-color: #c9a84c55;
}
.price {
    font-size: 1.15rem;
    font-weight: 600;
    color: #c9a84c;
    margin: 0.6rem 0;
}
.badge {
    background: #c9a84c22;
    color: #c9a84c;
    font-size: 0.7rem;
    padding: 0.2rem 0.55rem;
    border-radius: 4px;
    font-family: monospace;
    letter-spacing: 0.05em;
}
.footer {
    margin-top: 4rem;
    padding: 2.5rem 0 1.5rem;
    border-top: 1px solid #2a2a2e;
    color: #78716c;
    font-size: 0.85rem;
}
div[data-testid="stHorizontalBlock"] > div {
    min-width: 0;
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Session State
# ──────────────────────────────────────────────

if "agent" not in st.session_state:
    st.session_state.agent = PropertyAgent(PROPERTIES)
if "selected_id" not in st.session_state:
    st.session_state.selected_id = None
if "props_count" not in st.session_state:
    st.session_state.props_count = 150

# Ambient counter simulation
if time.time() % 8 < 0.5 and st.session_state.props_count < 200:
    st.session_state.props_count += 1

# ──────────────────────────────────────────────
# Header / Navigation
# ──────────────────────────────────────────────

col_logo, col_nav = st.columns([2, 5])
with col_logo:
    st.markdown("### 🏠 **Mwarokin Estates**  \n<span style='font-size:0.75rem;color:#c9a84c;'>Property Films</span>", unsafe_allow_html=True)
with col_nav:
    st.markdown(
        """
        <div style="display:flex;gap:1.8rem;justify-content:flex-end;align-items:center;padding-top:0.8rem;font-size:0.92rem;">
            <span style="color:#a8a29e;">Home</span>
            <span style="color:#c9a84c;font-weight:600;">Films</span>
            <span style="color:#a8a29e;">Manage Bills</span>
            <span style="color:#a8a29e;">Services ▾</span>
            <span style="background:#c9a84c;color:#0a0a0b;padding:0.35rem 1rem;border-radius:6px;font-weight:600;">Communication</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# ──────────────────────────────────────────────
# Hero Section
# ──────────────────────────────────────────────

hero_left, hero_right = st.columns([1.1, 1], gap="large")

with hero_left:
    st.markdown('<div class="eyebrow">Reel 001 — Featured Estates</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">Walk every room<em>before you arrive</em></h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-sub">Cinematic walkthroughs of Mwarokin\'s finest listings — shot on location, '
        'narrated by the space itself. See the light, the layout, the finish, before you ever step through the door.</p>',
        unsafe_allow_html=True,
    )
    cta1, cta2 = st.columns(2)
    with cta1:
        if st.button("Browse the Collection", type="primary", use_container_width=True):
            st.session_state.selected_id = None
            st.rerun()
    with cta2:
        if st.button("Speak to an Agent", use_container_width=True):
            st.session_state.show_contact = True

    st.write("")
    s1, s2, s3, s4 = st.columns(4)
    s1.markdown(f'<div class="stat-box"><b>{st.session_state.props_count}+</b><span>Properties Filmed</span></div>', unsafe_allow_html=True)
    s2.markdown('<div class="stat-box"><b>500+</b><span>Happy Clients</span></div>', unsafe_allow_html=True)
    s3.markdown('<div class="stat-box"><b>12</b><span>Cities Covered</span></div>', unsafe_allow_html=True)
    s4.markdown('<div class="stat-box"><b>5+</b><span>Years in Trust</span></div>', unsafe_allow_html=True)

with hero_right:
    featured = PROPERTIES[0]
    st.video(featured.video)
    st.markdown(
        f"**{featured.title}**  \n"
        f"<span style='color:#c9a84c;font-family:monospace;'>KSh {featured.price:,}</span> · "
        f"<span class='badge'>FEATURED · {featured.duration}</span>",
        unsafe_allow_html=True,
    )

# ──────────────────────────────────────────────
# Live Band Stats
# ──────────────────────────────────────────────

st.write("")
b1, b2, b3, b4 = st.columns(4)
b1.metric("🎬 Film Tours Live", "42")
b2.metric("👁 Views This Month", "18.4K")
b3.metric("📅 Tour → Viewing Rate", "96%")
b4.metric("⭐ Client Rating", "4.9")

st.markdown("---")

# ──────────────────────────────────────────────
# Filters
# ──────────────────────────────────────────────

st.markdown("### Filters")
f1, f2 = st.columns(2)

with f1:
    type_filter = st.selectbox(
        "Property Type",
        options=["all", "house", "apartment", "villa", "commercial"],
        format_func=lambda x: {"all": "All", "house": "Houses", "apartment": "Apartments",
                               "villa": "Villas", "commercial": "Commercial"}[x],
        index=0,
    )

with f2:
    price_filter = st.selectbox(
        "Price Range",
        options=["all", "0-5", "5-10", "10-20", "20+"],
        format_func=lambda x: {"all": "Any Price", "0-5": "Under 5M", "5-10": "5M – 10M",
                               "10-20": "10M – 20M", "20+": "Over 20M"}[x],
        index=0,
    )

filtered = st.session_state.agent.filter(type_filter, price_filter)

# ──────────────────────────────────────────────
# Property Grid
# ──────────────────────────────────────────────

st.markdown('<div class="eyebrow">The Collection</div>', unsafe_allow_html=True)
st.markdown("## Featured Property Films")
st.caption("Every listing filmed on-site, in natural light, with no staging tricks — what you see is what you'll walk into.")

if not filtered:
    st.info("No properties match the selected filters.")
else:
    cols = st.columns(3)
    for idx, prop in enumerate(filtered):
        with cols[idx % 3]:
            with st.container():
                st.video(prop.video)
                st.markdown(f"**{prop.title}**")
                st.caption(f"📍 {prop.location}")
                st.markdown(
                    f"<span class='badge'>{prop.type.upper()}</span> "
                    f"<span style='color:#78716c;font-size:0.8rem;margin-left:0.5rem;'>{prop.duration}</span>",
                    unsafe_allow_html=True,
                )
                m1, m2, m3 = st.columns(3)
                m1.markdown(f"🛏 **{prop.bedrooms}**")
                m2.markdown(f"🛁 **{prop.bathrooms}**")
                m3.markdown(f"📐 **{prop.area:,}**")
                st.markdown(f"<div class='price'>KSh {prop.price:,}</div>", unsafe_allow_html=True)

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Watch Film", key=f"watch_{prop.id}", use_container_width=True):
                        st.session_state.selected_id = prop.id
                        st.session_state.agent.log_view(prop.id)
                        st.rerun()
                with c2:
                    if st.button("Schedule Tour", key=f"tour_{prop.id}", use_container_width=True):
                        st.session_state.show_contact = True
                        st.rerun()

# ──────────────────────────────────────────────
# Video Modal / Detail View
# ──────────────────────────────────────────────

if st.session_state.selected_id is not None:
    prop = next((p for p in PROPERTIES if p.id == st.session_state.selected_id), None)
    if prop:
        st.markdown("---")
        st.markdown(f"### 🎬 {prop.title}")
        st.video(prop.video)
        st.write(prop.description)

        d1, d2, d3 = st.columns(3)
        d1.markdown(f"**Location**  \n{prop.location}")
        d2.markdown(f"**Price**  \nKSh {prop.price:,}")
        d3.markdown(f"**Type**  \n{prop.type.title()}")

        d4, d5, d6 = st.columns(3)
        d4.markdown(f"**Bedrooms**  \n{prop.bedrooms}")
        d5.markdown(f"**Bathrooms**  \n{prop.bathrooms}")
        d6.markdown(f"**Area**  \n{prop.area:,} sq ft")

        # Agentic recommendations
        recs = st.session_state.agent.recommend(prop)
        if recs:
            st.markdown("#### You may also like")
            rcols = st.columns(len(recs))
            for i, r in enumerate(recs):
                with rcols[i]:
                    st.markdown(f"**{r.title}** — KSh {r.price:,}")
                    if st.button("View", key=f"rec_{r.id}"):
                        st.session_state.selected_id = r.id
                        st.rerun()

        if st.button("← Back to Collection"):
            st.session_state.selected_id = None
            st.rerun()

# ──────────────────────────────────────────────
# Contact Form
# ──────────────────────────────────────────────

if st.session_state.get("show_contact", False):
    st.markdown("---")
    st.markdown("### Speak to an Agent")
    with st.form("contact_form"):
        name = st.text_input("Your Name")
        email = st.text_input("Email Address")
        phone = st.text_input("Phone Number")
        message = st.text_area("Message", height=120)
        submitted = st.form_submit_button("Send Message", type="primary")
        if submitted:
            if name and email and message:
                st.success("Thank you — your message has been received. We will reach out shortly.")
                st.session_state.show_contact = False
                time.sleep(1.2)
                st.rerun()
            else:
                st.error("Please fill in the required fields.")

# ──────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────

st.markdown(
    """
    <div class="footer">
        <strong>Mwarokin Estates</strong> — Property, filmed honestly.<br>
        A pan-African real estate platform bringing transparent, cinematic property discovery.<br><br>
        📞 +254-704-919-388 &nbsp;|&nbsp; ✉️ info@mwarokinestates.com &nbsp;|&nbsp; 📍 Kenya, Africa<br><br>
        Mwarokin Estates — Property Films © 2026. All Rights Reserved. Powered by Syllogism Technology Africa.
    </div>
    """,
    unsafe_allow_html=True,
)
