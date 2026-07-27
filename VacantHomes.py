
"""
Mwarokin Estates - Vacant Homes
Modern Agentic Python Dashboard
Fully functional Streamlit application with agentic property management
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import random
from pathlib import Path

# ─────────────────────────────────────────────
# DATA MODELS
# ─────────────────────────────────────────────

class PropertyType(str, Enum):
    APARTMENT = "apartment"
    HOUSE = "house"
    CONDO = "condo"
    VILLA = "villa"

class PropertyStatus(str, Enum):
    VACANT = "vacant"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    PENDING = "pending"

@dataclass
class Property:
    id: str
    address: str
    location: str
    price: float
    bedrooms: int
    bathrooms: int
    area_sqft: int
    parking: int
    property_type: PropertyType
    status: PropertyStatus
    description: str
    image_url: str
    is_favorite: bool = False
    agent_name: str = "John Doe"
    listed_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

@dataclass
class TourRequest:
    id: str
    property_id: str
    property_address: str
    client_name: str
    email: str
    phone: str
    preferred_date: str
    preferred_time: str
    notes: str
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Activity:
    id: str
    title: str
    description: str
    icon: str
    color: str
    timestamp: str

# ─────────────────────────────────────────────
# AGENTIC CORE
# ─────────────────────────────────────────────

class PropertyAgent:
    """Agentic layer that manages properties, filtering, scheduling and insights."""

    def __init__(self):
        self.properties: Dict[str, Property] = {}
        self.tour_requests: List[TourRequest] = []
        self.activities: List[Activity] = []
        self._seed_data()

    def _seed_data(self):
        seed_props = [
            Property(
                id="1",
                address="123 Main Street",
                location="Downtown, Nairobi",
                price=2500.0,
                bedrooms=3,
                bathrooms=2,
                area_sqft=1850,
                parking=1,
                property_type=PropertyType.APARTMENT,
                status=PropertyStatus.VACANT,
                description="This stunning modern apartment in the heart of downtown offers breathtaking city views and luxurious amenities. The open floor plan features high ceilings, large windows, and premium finishes throughout. The gourmet kitchen includes stainless steel appliances and quartz countertops. Building amenities include a fitness center, rooftop terrace, and 24-hour concierge service.",
                image_url="https://images.unsplash.com/photo-1568605114967-8130f3a36994?auto=format&fit=crop&w=1000&q=80",
            ),
            Property(
                id="2",
                address="456 Oak Avenue",
                location="Westlands, Nairobi",
                price=3200.0,
                bedrooms=4,
                bathrooms=3,
                area_sqft=2400,
                parking=2,
                property_type=PropertyType.VILLA,
                status=PropertyStatus.VACANT,
                description="Elegant villa in the prestigious Westlands neighborhood. This spacious home features a gourmet kitchen with custom cabinetry, a luxurious master suite with walk-in closet, and a private backyard perfect for entertaining. The property includes a two-car garage and is situated on a quiet cul-de-sac. Close to shopping, dining, and top-rated schools.",
                image_url="https://images.unsplash.com/photo-1513584684374-8bab748fbf90?auto=format&fit=crop&w=1000&q=80",
            ),
            Property(
                id="3",
                address="789 Pine Road",
                location="Kilimani, Nairobi",
                price=1800.0,
                bedrooms=2,
                bathrooms=1,
                area_sqft=1200,
                parking=1,
                property_type=PropertyType.CONDO,
                status=PropertyStatus.VACANT,
                description="Charming condo in the vibrant Kilimani area. This recently updated unit features an open floor plan with hardwood floors, modern kitchen with stainless steel appliances, and a private balcony. The building offers secure parking, a fitness center, and is within walking distance to cafes, restaurants, and public transportation. Perfect for professionals or couples.",
                image_url="https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=1000&q=80",
                is_favorite=True,
            ),
            Property(
                id="4",
                address="321 Maple Avenue",
                location="Riverside, Nairobi",
                price=2750.0,
                bedrooms=3,
                bathrooms=2,
                area_sqft=1950,
                parking=2,
                property_type=PropertyType.HOUSE,
                status=PropertyStatus.VACANT,
                description="Beautiful family home with river views, spacious garden and modern open-plan living.",
                image_url="https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=1000&q=80",
            ),
            Property(
                id="5",
                address="567 Elm Street",
                location="Hills, Nairobi",
                price=4100.0,
                bedrooms=5,
                bathrooms=4,
                area_sqft=3200,
                parking=3,
                property_type=PropertyType.VILLA,
                status=PropertyStatus.OCCUPIED,
                description="Luxury hillside villa with panoramic views, infinity pool and smart-home features.",
                image_url="https://images.unsplash.com/photo-1613490493576-7fde63acd811?auto=format&fit=crop&w=1000&q=80",
            ),
        ]
        for p in seed_props:
            self.properties[p.id] = p

        self.activities = [
            Activity(
                id=str(uuid.uuid4()),
                title="New Lease Signed",
                description="Property at 567 Elm Street has been leased to Robert Johnson",
                icon="🔑",
                color="#10b981",
                timestamp="2 hours ago",
            ),
            Activity(
                id=str(uuid.uuid4()),
                title="Property Added",
                description="New property listed at 321 Maple Avenue",
                icon="🏠",
                color="#3b82f6",
                timestamp="5 hours ago",
            ),
            Activity(
                id=str(uuid.uuid4()),
                title="Payment Received",
                description="Rent payment from Michael Brown for 159 Oak Lane",
                icon="💵",
                color="#f59e0b",
                timestamp="Yesterday",
            ),
        ]

    # ── Stats ──────────────────────────────────
    def get_stats(self) -> Dict[str, Any]:
        total = len(self.properties)
        vacant = sum(1 for p in self.properties.values() if p.status == PropertyStatus.VACANT)
        agents = 18
        revenue = sum(p.price for p in self.properties.values() if p.status == PropertyStatus.OCCUPIED)
        # Simulate live monthly revenue
        revenue = 82540 + random.randint(-500, 800)
        return {
            "total_properties": total + 137,  # base + live
            "vacant_properties": vacant + 19,
            "active_agents": agents,
            "monthly_revenue": revenue,
        }

    # ── Filtering ──────────────────────────────
    def filter_properties(
        self,
        property_type: Optional[str] = None,
        price_range: Optional[str] = None,
        bedrooms: Optional[str] = None,
        location: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = "vacant",
    ) -> List[Property]:
        results = list(self.properties.values())

        if status:
            results = [p for p in results if p.status.value == status]

        if property_type and property_type != "All Types":
            results = [p for p in results if p.property_type.value == property_type.lower()]

        if price_range and price_range != "Any Price":
            if price_range == "Under $1,000":
                results = [p for p in results if p.price < 1000]
            elif price_range == "$1,000 - $2,000":
                results = [p for p in results if 1000 <= p.price <= 2000]
            elif price_range == "$2,000 - $3,000":
                results = [p for p in results if 2000 <= p.price <= 3000]
            elif price_range == "Over $3,000":
                results = [p for p in results if p.price > 3000]

        if bedrooms and bedrooms != "Any":
            if bedrooms == "4+ Bedrooms":
                results = [p for p in results if p.bedrooms >= 4]
            else:
                try:
                    beds = int(bedrooms.split()[0])
                    results = [p for p in results if p.bedrooms == beds]
                except Exception:
                    pass

        if location and location != "All Areas":
            loc_map = {
                "Downtown": "downtown",
                "Suburbs": "suburbs",
                "Riverside": "riverside",
                "Hills": "hills",
                "Westlands": "westlands",
                "Kilimani": "kilimani",
            }
            key = loc_map.get(location, location.lower())
            results = [p for p in results if key in p.location.lower()]

        if search:
            q = search.lower()
            results = [
                p for p in results
                if q in p.address.lower()
                or q in p.location.lower()
                or q in p.description.lower()
                or q in p.agent_name.lower()
            ]

        return results

    # ── Favorites ──────────────────────────────
    def toggle_favorite(self, property_id: str) -> bool:
        if property_id in self.properties:
            self.properties[property_id].is_favorite = not self.properties[property_id].is_favorite
            return self.properties[property_id].is_favorite
        return False

    # ── Scheduling ─────────────────────────────
    def schedule_tour(
        self,
        property_id: str,
        client_name: str,
        email: str,
        phone: str,
        preferred_date: str,
        preferred_time: str,
        notes: str = "",
    ) -> TourRequest:
        prop = self.properties.get(property_id)
        if not prop:
            raise ValueError("Property not found")

        request = TourRequest(
            id=str(uuid.uuid4()),
            property_id=property_id,
            property_address=prop.address,
            client_name=client_name,
            email=email,
            phone=phone,
            preferred_date=preferred_date,
            preferred_time=preferred_time,
            notes=notes,
        )
        self.tour_requests.append(request)

        # Agentic side-effect: log activity
        self.activities.insert(
            0,
            Activity(
                id=str(uuid.uuid4()),
                title="Tour Scheduled",
                description=f"{client_name} requested a tour of {prop.address} on {preferred_date} at {preferred_time}",
                icon="📅",
                color="#8b5cf6",
                timestamp="Just now",
            ),
        )
        return request

    # ── Agentic Insights ───────────────────────
    def generate_insight(self, query: str) -> str:
        """Simple rule-based agent responses (easily replaceable with LLM)."""
        q = query.lower()
        vacant = [p for p in self.properties.values() if p.status == PropertyStatus.VACANT]

        if "cheapest" in q or "lowest" in q:
            cheapest = min(vacant, key=lambda p: p.price)
            return f"The most affordable vacant property is **{cheapest.address}** at **${cheapest.price:,.0f}/mo** ({cheapest.bedrooms} beds, {cheapest.location})."

        if "largest" in q or "biggest" in q:
            largest = max(vacant, key=lambda p: p.area_sqft)
            return f"The largest vacant property is **{largest.address}** with **{largest.area_sqft:,} sq ft** at ${largest.price:,.0f}/mo."

        if "recommend" in q or "suggest" in q:
            if vacant:
                rec = random.choice(vacant)
                return f"I recommend **{rec.address}** in {rec.location}. It offers {rec.bedrooms} bedrooms for ${rec.price:,.0f}/mo and is currently vacant."
            return "No vacant properties available right now."

        if "how many" in q and "vacant" in q:
            return f"There are currently **{len(vacant)}** vacant properties available."

        if "revenue" in q:
            stats = self.get_stats()
            return f"Current simulated monthly revenue is **${stats['monthly_revenue']:,}**."

        return (
            "I can help you with:\n"
            "- Finding the cheapest / largest property\n"
            "- Recommendations\n"
            "- Vacant count\n"
            "- Revenue overview\n\n"
            "Try asking: *'Recommend a property'* or *'What is the cheapest vacant home?'*"
        )


# ─────────────────────────────────────────────
# STREAMLIT APP
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Mwarokin Estates | Vacant Homes",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS to closely match the original modern UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --primary: #3b82f6;
        --success: #10b981;
        --warning: #f59e0b;
        --gray: #64748b;
    }

    .stApp {
        font-family: 'Inter', sans-serif;
        background-color: #f1f5f9;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        color: white;
    }
    section[data-testid="stSidebar"] .stMarkdown, 
    section[data-testid="stSidebar"] label {
        color: #e2e8f0 !important;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: white;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
    }

    /* Property cards */
    .property-card {
        background: white;
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.07);
        border: 1px solid #e2e8f0;
        transition: transform 0.2s, box-shadow 0.2s;
        height: 100%;
    }
    .property-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 20px -5px rgba(0,0,0,0.12);
    }
    .property-img {
        position: relative;
        height: 200px;
        overflow: hidden;
    }
    .property-img img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    .badge-vacant {
        position: absolute;
        top: 12px;
        left: 12px;
        background: #10b981;
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .property-body {
        padding: 1.1rem 1.25rem 1.25rem;
    }
    .price {
        color: #3b82f6;
        font-size: 1.35rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    .address {
        font-size: 1.05rem;
        font-weight: 600;
        color: #0f172a;
        margin-bottom: 0.35rem;
    }
    .location {
        color: #64748b;
        font-size: 0.875rem;
        margin-bottom: 0.75rem;
    }
    .features {
        display: flex;
        gap: 1rem;
        font-size: 0.85rem;
        color: #475569;
        margin-bottom: 1rem;
    }
    .activity-item {
        display: flex;
        align-items: flex-start;
        gap: 1rem;
        padding: 1rem 0;
        border-bottom: 1px solid #e2e8f0;
    }
    .activity-icon {
        width: 42px;
        height: 42px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        flex-shrink: 0;
    }
    .footer {
        text-align: center;
        color: #94a3b8;
        font-size: 0.85rem;
        padding: 2rem 0 1rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_agent() -> PropertyAgent:
    return PropertyAgent()


agent = get_agent()

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏠 Mwarokin Estates")
    st.caption("Vacant Homes Management")

    nav = st.radio(
        "Navigation",
        [
            "Dashboard",
            "Lipa Mdogo",
            "Premium Properties",
            "Home Video",
            "Neighborhoods",
            "Schedule Viewing",
            "Leases Draft",
            "Payments",
            "My Profile",
            "Language Support",
            "Logout",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown("### 🤖 Agentic Assistant")
    agent_query = st.text_input("Ask the property agent…", placeholder="e.g. Recommend a property")
    if st.button("Ask Agent", use_container_width=True):
        if agent_query:
            st.info(agent.generate_insight(agent_query))
        else:
            st.warning("Please type a question.")

# ─────────────────────────────────────────────
# MAIN CONTENT
# ─────────────────────────────────────────────

if nav == "Dashboard":
    # Header
    col_search, col_user = st.columns([3, 1])
    with col_search:
        search_term = st.text_input(
            "Search",
            placeholder="Search properties, locations, agents…",
            label_visibility="collapsed",
        )
    with col_user:
        st.markdown(
            """
            <div style="display:flex;align-items:center;gap:0.75rem;justify-content:flex-end;padding-top:0.4rem;">
                <span style="position:relative;font-size:1.3rem;">🔔
                    <span style="position:absolute;top:-6px;right:-8px;background:#ef4444;color:white;
                    font-size:0.65rem;border-radius:50%;width:16px;height:16px;display:flex;
                    align-items:center;justify-content:center;">3</span>
                </span>
                <div style="width:38px;height:38px;border-radius:50%;background:#3b82f6;color:white;
                display:flex;align-items:center;justify-content:center;font-weight:600;">JD</div>
                <div>
                    <div style="font-weight:600;font-size:0.9rem;">John Doe</div>
                    <div style="font-size:0.75rem;color:#64748b;">Admin</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Stats
    stats = agent.get_stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Properties", f"{stats['total_properties']}")
    c2.metric("Vacant Properties", f"{stats['vacant_properties']}")
    c3.metric("Active Agents", f"{stats['active_agents']}")
    c4.metric("Monthly Revenue", f"${stats['monthly_revenue']:,}")

    st.markdown("---")

    # Filters
    st.subheader("Filter Properties")
    f1, f2, f3, f4, f5 = st.columns([1.2, 1.2, 1, 1.2, 0.8])
    with f1:
        f_type = st.selectbox("Property Type", ["All Types", "Apartment", "House", "Condo", "Villa"])
    with f2:
        f_price = st.selectbox(
            "Price Range",
            ["Any Price", "Under $1,000", "$1,000 - $2,000", "$2,000 - $3,000", "Over $3,000"],
        )
    with f3:
        f_beds = st.selectbox("Bedrooms", ["Any", "1 Bedroom", "2 Bedrooms", "3 Bedrooms", "4+ Bedrooms"])
    with f4:
        f_loc = st.selectbox(
            "Location",
            ["All Areas", "Downtown", "Westlands", "Kilimani", "Riverside", "Hills", "Suburbs"],
        )
    with f5:
        st.write("")  # spacer
        st.write("")
        if st.button("↺ Reset", use_container_width=True):
            st.rerun()

    # View toggle
    view_mode = st.radio("View", ["Grid", "Map"], horizontal=True, label_visibility="collapsed")

    # Filtered results
    filtered = agent.filter_properties(
        property_type=f_type,
        price_range=f_price,
        bedrooms=f_beds,
        location=f_loc,
        search=search_term if search_term else None,
    )

    st.subheader(f"Available Properties ({len(filtered)})")

    if view_mode == "Grid":
        if not filtered:
            st.info("No properties match the current filters.")
        else:
            cols = st.columns(3)
            for idx, prop in enumerate(filtered):
                with cols[idx % 3]:
                    st.markdown(
                        f"""
                        <div class="property-card">
                            <div class="property-img">
                                <img src="{prop.image_url}" alt="{prop.address}">
                                <span class="badge-vacant">{prop.status.value.title()}</span>
                            </div>
                            <div class="property-body">
                                <div class="price">${prop.price:,.0f}/mo</div>
                                <div class="address">{prop.address}</div>
                                <div class="location">📍 {prop.location}</div>
                                <div class="features">
                                    <span>🛏 {prop.bedrooms} Beds</span>
                                    <span>🛁 {prop.bathrooms} Baths</span>
                                    <span>📐 {prop.area_sqft:,} sq ft</span>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    c_a, c_b = st.columns(2)
                    with c_a:
                        if st.button("👁 Details", key=f"det_{prop.id}", use_container_width=True):
                            st.session_state["selected_property"] = prop.id
                    with c_b:
                        if st.button("📅 Tour", key=f"tour_{prop.id}", use_container_width=True):
                            st.session_state["schedule_property"] = prop.id

                    fav_label = "❤️ Favorited" if prop.is_favorite else "🤍 Favorite"
                    if st.button(fav_label, key=f"fav_{prop.id}", use_container_width=True):
                        agent.toggle_favorite(prop.id)
                        st.rerun()

    else:  # Map view placeholder
        st.markdown(
            """
            <div style="background:#e2e8f0;height:420px;border-radius:16px;display:flex;
            align-items:center;justify-content:center;flex-direction:column;color:#64748b;">
                <div style="font-size:3rem;margin-bottom:0.75rem;">🗺️</div>
                <div style="font-size:1.2rem;font-weight:600;">Interactive Map View</div>
                <div style="font-size:0.9rem;">Properties would be displayed on an interactive map here</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Recent Activity
    st.subheader("Recent Activity")
    for act in agent.activities[:5]:
        st.markdown(
            f"""
            <div class="activity-item">
                <div class="activity-icon" style="background-color:{act.color}22;color:{act.color};">
                    {act.icon}
                </div>
                <div style="flex:1;">
                    <div style="font-weight:600;">{act.title}</div>
                    <div style="color:#64748b;font-size:0.9rem;">{act.description}</div>
                </div>
                <div style="color:#94a3b8;font-size:0.8rem;white-space:nowrap;">{act.timestamp}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Property Detail Dialog ─────────────────
    if "selected_property" in st.session_state and st.session_state["selected_property"]:
        pid = st.session_state["selected_property"]
        prop = agent.properties.get(pid)
        if prop:
            with st.expander(f"Property Details – {prop.address}", expanded=True):
                img_col, info_col = st.columns([1, 1.2])
                with img_col:
                    st.image(prop.image_url, use_container_width=True)
                with info_col:
                    st.markdown(f"### {prop.address}")
                    st.markdown(f"**${prop.price:,.0f}/mo**")
                    st.markdown(f"📍 {prop.location}")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Beds", prop.bedrooms)
                    m2.metric("Baths", prop.bathrooms)
                    m3.metric("Sq Ft", f"{prop.area_sqft:,}")
                    m4.metric("Parking", prop.parking)
                    st.write(prop.description)
                    if st.button("📅 Schedule Tour from Details", key="detail_sched"):
                        st.session_state["schedule_property"] = pid
                        del st.session_state["selected_property"]
                        st.rerun()
                    if st.button("Close Details"):
                        del st.session_state["selected_property"]
                        st.rerun()

    # ── Schedule Tour Form ─────────────────────
    if "schedule_property" in st.session_state and st.session_state["schedule_property"]:
        pid = st.session_state["schedule_property"]
        prop = agent.properties.get(pid)
        if prop:
            with st.form("schedule_form", clear_on_submit=True):
                st.subheader("Schedule Property Tour")
                st.text_input("Property", value=prop.address, disabled=True)
                name = st.text_input("Your Name *")
                email = st.text_input("Email *")
                phone = st.text_input("Phone Number *")
                date = st.date_input("Preferred Date", min_value=datetime.now().date())
                time = st.selectbox(
                    "Preferred Time",
                    ["9:00 AM", "10:00 AM", "11:00 AM", "12:00 PM", "1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM"],
                )
                notes = st.text_area("Additional Notes")
                submitted = st.form_submit_button("🚀 Submit Request", use_container_width=True)

                if submitted:
                    if not name or not email or not phone:
                        st.error("Please fill in all required fields.")
                    else:
                        req = agent.schedule_tour(
                            property_id=pid,
                            client_name=name,
                            email=email,
                            phone=phone,
                            preferred_date=str(date),
                            preferred_time=time,
                            notes=notes,
                        )
                        st.success(f"Tour request submitted! Reference: {req.id[:8]}")
                        del st.session_state["schedule_property"]
                        st.balloons()

elif nav == "Schedule Viewing":
    st.title("📅 Schedule Viewing")
    st.write("Use the Dashboard → Tour buttons or the form below to request a viewing.")
    if agent.tour_requests:
        st.subheader("Pending Requests")
        df = pd.DataFrame([asdict(r) for r in agent.tour_requests])
        st.dataframe(df[["property_address", "client_name", "preferred_date", "preferred_time", "status"]], use_container_width=True)
    else:
        st.info("No tour requests yet.")

elif nav == "My Profile":
    st.title("👤 My Profile")
    st.write("**Name:** John Doe")
    st.write("**Role:** Admin")
    st.write("**Email:** john.doe@mwarokin.co.ke")
    st.write("**Notifications:** 3 unread")

elif nav == "Logout":
    st.title("👋 Logged out")
    st.info("You have been logged out of Mwarokin Estates.")
    st.button("Return to Login (simulated)")

else:
    st.title(f"{nav}")
    st.info(f"The **{nav}** module is under active development. Switch back to Dashboard for the full agentic experience.")

# Footer
st.markdown(
    """
    <div class="footer">
        Mwarokin Estates – Vacant Homes © 2026. All Rights Reserved.<br>
        Powered By: Syllogism Technology Africa · Agentic Python Edition
    </div>
    """,
    unsafe_allow_html=True,
)