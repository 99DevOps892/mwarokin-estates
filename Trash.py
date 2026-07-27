python
"""
Mwarokin Estates – Waste & Collection Management
Modern Agentic Python Dashboard (Streamlit)
Real-time bin monitoring · Eco Score · Special pickup agent
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import random
import time
import math

# ─────────────────────────────────────────────
# DATA MODELS
# ─────────────────────────────────────────────

class WasteType(str, Enum):
    GENERAL = "general"
    RECYCLABLE = "recyclable"
    ORGANIC = "organic"
    HAZARDOUS = "hazardous"

class PickupStatus(str, Enum):
    UPCOMING = "upcoming"
    DONE = "done"
    MISSED = "missed"
    PENDING = "pending"

@dataclass
class Bin:
    id: str
    name: str
    waste_type: WasteType
    fill_pct: float          # 0–100
    last_emptied: str
    capacity_kg: float = 120.0
    emoji: str = "🗑️"

@dataclass
class ScheduleItem:
    id: str
    waste_type: WasteType
    label: str
    days: str
    time_window: str
    status: PickupStatus
    icon: str

@dataclass
class Activity:
    id: str
    title: str
    description: str
    timestamp: str
    icon: str = "📋"

@dataclass
class SpecialPickup:
    id: str
    waste_type: str
    preferred_date: str
    time_slot: str
    instructions: str
    status: str = "confirmed"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Property:
    id: str
    name: str
    bins: Dict[str, Bin]

# ─────────────────────────────────────────────
# AGENTIC CORE + REAL-TIME ENGINE
# ─────────────────────────────────────────────

class WasteAgent:
    """Agentic waste-management brain with live bin simulation."""

    def __init__(self):
        self.properties: Dict[str, Property] = {}
        self.schedules: List[ScheduleItem] = []
        self.activities: List[Activity] = []
        self.special_pickups: List[SpecialPickup] = []
        self.eco_score: float = 75.0
        self._last_tick: float = time.time()
        self._seed()

    def _seed(self):
        # Shared bin templates
        def make_bins() -> Dict[str, Bin]:
            return {
                "general": Bin(
                    id="g1", name="General Waste", waste_type=WasteType.GENERAL,
                    fill_pct=65.0, last_emptied="yesterday", emoji="🗑️", capacity_kg=150
                ),
                "recycle": Bin(
                    id="r1", name="Recyclables", waste_type=WasteType.RECYCLABLE,
                    fill_pct=85.0, last_emptied="2 days ago", emoji="♻️", capacity_kg=100
                ),
                "organic": Bin(
                    id="o1", name="Organic Waste", waste_type=WasteType.ORGANIC,
                    fill_pct=20.0, last_emptied="today", emoji="🌿", capacity_kg=80
                ),
            }

        self.properties = {
            "all": Property(id="all", name="All Properties", bins=make_bins()),
            "va": Property(id="va", name="Villa A", bins=make_bins()),
            "vb": Property(id="vb", name="Villa B", bins=make_bins()),
            "ap": Property(id="ap", name="Apartment 1", bins=make_bins()),
        }

        # Slight variation per property
        self.properties["vb"].bins["general"].fill_pct = 42
        self.properties["vb"].bins["recycle"].fill_pct = 71
        self.properties["ap"].bins["organic"].fill_pct = 55
        self.properties["ap"].bins["general"].fill_pct = 78

        self.schedules = [
            ScheduleItem(
                id="s1", waste_type=WasteType.GENERAL, label="General Waste",
                days="Mon & Thu", time_window="7:00 – 9:00 AM",
                status=PickupStatus.UPCOMING, icon="🗑️"
            ),
            ScheduleItem(
                id="s2", waste_type=WasteType.RECYCLABLE, label="Recyclables",
                days="Wednesday", time_window="8:00 – 10:00 AM",
                status=PickupStatus.DONE, icon="♻️"
            ),
            ScheduleItem(
                id="s3", waste_type=WasteType.ORGANIC, label="Organic Waste",
                days="Saturday", time_window="6:00 – 8:00 AM",
                status=PickupStatus.UPCOMING, icon="🌿"
            ),
        ]

        self.activities = [
            Activity(id=str(uuid.uuid4()), title="Organic Waste Collected",
                     description="Your organic bin was emptied as scheduled.",
                     timestamp="Today, 8:30 AM", icon="🌿"),
            Activity(id=str(uuid.uuid4()), title="Special Pickup Requested",
                     description="Additional pickup for general waste — confirmed.",
                     timestamp="Yesterday, 2:15 PM", icon="🚛"),
            Activity(id=str(uuid.uuid4()), title="Recycling Bin Alert",
                     description="Recyclables bin reached 85% capacity.",
                     timestamp="2 days ago, 9:45 AM", icon="⚠️"),
            Activity(id=str(uuid.uuid4()), title="General Waste Collected",
                     description="Routine Monday collection completed.",
                     timestamp="3 days ago, 7:10 AM", icon="🗑️"),
        ]

    # ── REAL-TIME TICK ─────────────────────────
    def tick(self, force: bool = False, interval: float = 7.0) -> List[str]:
        now = time.time()
        if not force and (now - self._last_tick) < interval:
            return []
        self._last_tick = now
        changes: List[str] = []

        for prop in self.properties.values():
            for b in prop.bins.values():
                # Natural fill increase
                delta = random.uniform(0.4, 2.8)
                old = b.fill_pct
                b.fill_pct = min(100.0, b.fill_pct + delta)

                # Occasional empty event
                if b.fill_pct > 92 and random.random() < 0.18:
                    b.fill_pct = random.uniform(5, 18)
                    b.last_emptied = "just now"
                    changes.append(f"{prop.name} · {b.name} emptied (was {old:.0f}%)")
                    self.activities.insert(0, Activity(
                        id=str(uuid.uuid4()),
                        title=f"{b.name} Collected",
                        description=f"{prop.name} – bin emptied by collection team.",
                        timestamp="Just now",
                        icon=b.emoji
                    ))

                # High-fill alert
                if old < 80 <= b.fill_pct:
                    changes.append(f"⚠️ {prop.name} · {b.name} now {b.fill_pct:.0f}% full")
                    self.activities.insert(0, Activity(
                        id=str(uuid.uuid4()),
                        title=f"{b.name} Alert",
                        description=f"{prop.name} – bin reached {b.fill_pct:.0f}% capacity.",
                        timestamp="Just now",
                        icon="⚠️"
                    ))

        # Eco-score drift
        avg_fill = sum(
            b.fill_pct for p in self.properties.values() for b in p.bins.values()
        ) / max(1, sum(len(p.bins) for p in self.properties.values()))
        recycle_bonus = 12 if avg_fill < 60 else 0
        self.eco_score = max(40.0, min(98.0, 82 - (avg_fill * 0.25) + recycle_bonus + random.uniform(-1.5, 1.5)))

        self.activities = self.activities[:20]
        return changes

    def get_stats(self, prop_id: str = "all") -> Dict[str, Any]:
        prop = self.properties.get(prop_id, self.properties["all"])
        total_kg = 450 + random.randint(-20, 35)
        recycled = 180 + random.randint(-10, 25)
        rate = int((recycled / max(1, total_kg)) * 100)
        return {
            "total_kg": total_kg,
            "recycled_kg": recycled,
            "recycle_rate": rate,
            "pickups_done": 12 + random.randint(0, 2),
            "eco_score": round(self.eco_score),
        }

    def request_special_pickup(
        self, waste_type: str, preferred_date: str, time_slot: str, instructions: str = ""
    ) -> SpecialPickup:
        req = SpecialPickup(
            id=str(uuid.uuid4()),
            waste_type=waste_type,
            preferred_date=preferred_date,
            time_slot=time_slot,
            instructions=instructions,
        )
        self.special_pickups.append(req)
        self.activities.insert(0, Activity(
            id=str(uuid.uuid4()),
            title="Special Pickup Scheduled",
            description=f"{waste_type} · {preferred_date} · {time_slot}",
            timestamp="Just now",
            icon="📅"
        ))
        return req

    def set_reminder(self) -> str:
        self.activities.insert(0, Activity(
            id=str(uuid.uuid4()),
            title="Reminder Set",
            description="You will be notified before the next collection window.",
            timestamp="Just now",
            icon="🔔"
        ))
        return "Reminder set for your next collection day."

    def generate_insight(self, query: str, prop_id: str = "all") -> str:
        q = query.lower()
        prop = self.properties.get(prop_id, self.properties["all"])
        bins = list(prop.bins.values())

        if "fullest" in q or "highest" in q:
            fullest = max(bins, key=lambda b: b.fill_pct)
            return f"**{fullest.name}** is currently at **{fullest.fill_pct:.0f}%** – consider a special pickup soon."

        if "eco" in q or "score" in q:
            grade = "Excellent" if self.eco_score >= 85 else "Good Standing" if self.eco_score >= 65 else "Needs Improvement"
            return f"Current Eco Score is **{self.eco_score:.0f}** ({grade}). Keep recycling rates high to climb further."

        if "recommend" in q or "pickup" in q:
            high = [b for b in bins if b.fill_pct >= 75]
            if high:
                names = ", ".join(b.name for b in high)
                return f"I recommend requesting a special pickup for: **{names}**."
            return "All bins are at comfortable levels. No urgent pickup needed."

        if "schedule" in q:
            upcoming = [s for s in self.schedules if s.status == PickupStatus.UPCOMING]
            if upcoming:
                lines = [f"• {s.label}: {s.days} · {s.time_window}" for s in upcoming]
                return "Upcoming collections:\n" + "\n".join(lines)
            return "No upcoming collections currently scheduled."

        return (
            "I can help with:\n"
            "- Bin fill levels & alerts\n"
            "- Eco Score explanation\n"
            "- Pickup recommendations\n"
            "- Schedule overview\n\n"
            "Try: *'What is the fullest bin?'* or *'Recommend a pickup'*"
        )


# ─────────────────────────────────────────────
# STREAMLIT UI
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Mwarokin Estates · Waste & Collection",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Modern dark-gold theme CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    :root {
        --gold: #C9A84C;
        --gold-light: #E2C47A;
        --bg: #0f1419;
        --card: #1a2332;
        --text: #e8eef7;
        --dim: #8b9bb4;
    }
    .stApp {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(160deg, #0f1419 0%, #151c27 50%, #1a2332 100%);
        color: var(--text);
    }
    section[data-testid="stSidebar"] {
        background: #0d1218;
        border-right: 1px solid rgba(201,168,76,0.15);
    }
    section[data-testid="stSidebar"] * { color: #d0d8e8 !important; }
    .block-container { padding-top: 1.2rem; }

    .topbar {
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.6rem 0 1.2rem; border-bottom: 1px solid rgba(201,168,76,0.12);
        margin-bottom: 1.2rem;
    }
    .brand { display: flex; align-items: center; gap: 0.85rem; }
    .brand-icon {
        width: 44px; height: 44px; border-radius: 12px;
        background: linear-gradient(135deg, #C9A84C, #E2C47A);
        display: flex; align-items: center; justify-content: center;
        font-size: 1.3rem; color: #0f1419;
    }
    .brand h1 { margin: 0; font-size: 1.25rem; font-weight: 700; color: #f0f4fa; }
    .brand p { margin: 0; font-size: 0.78rem; color: #8b9bb4; }

    .card {
        background: #1a2332; border-radius: 16px; padding: 1.25rem 1.4rem;
        border: 1px solid rgba(201,168,76,0.1); margin-bottom: 1rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.25);
    }
    .card-title-eyebrow { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em; color: #C9A84C; font-weight: 600; }
    .card-title { font-size: 1.15rem; font-weight: 700; color: #f0f4fa; margin-top: 2px; }

    .bin-row {
        display: flex; align-items: center; gap: 0.9rem; padding: 0.7rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    .bin-emoji { font-size: 1.5rem; width: 36px; text-align: center; }
    .bin-name { font-weight: 600; font-size: 0.92rem; color: #e8eef7; }
    .fill-bar {
        height: 7px; background: rgba(255,255,255,0.08); border-radius: 4px;
        margin-top: 5px; overflow: hidden;
    }
    .fill-inner { height: 100%; border-radius: 4px; transition: width 0.6s ease; }
    .fill-low .fill-inner { background: linear-gradient(90deg, #34d399, #10b981); }
    .fill-med .fill-inner { background: linear-gradient(90deg, #fbbf24, #f59e0b); }
    .fill-high .fill-inner { background: linear-gradient(90deg, #f87171, #ef4444); }
    .fill-pct { font-weight: 700; font-size: 0.95rem; min-width: 42px; text-align: right; }

    .sched-item {
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.75rem 0; border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    .sched-left { display: flex; align-items: center; gap: 0.85rem; }
    .sched-icon {
        width: 40px; height: 40px; border-radius: 10px; display: flex;
        align-items: center; justify-content: center; font-size: 1.15rem;
    }
    .sched-icon.general { background: rgba(148,163,184,0.15); }
    .sched-icon.recycle { background: rgba(52,211,153,0.15); }
    .sched-icon.organic { background: rgba(74,222,128,0.12); }
    .badge {
        font-size: 0.72rem; font-weight: 600; padding: 3px 10px; border-radius: 20px;
    }
    .badge-upcoming { background: rgba(201,168,76,0.18); color: #E2C47A; }
    .badge-done { background: rgba(16,185,129,0.18); color: #34d399; }

    .stat-box {
        background: rgba(255,255,255,0.03); border-radius: 12px; padding: 1rem;
        text-align: center; border: 1px solid rgba(255,255,255,0.05);
    }
    .stat-num { font-size: 1.7rem; font-weight: 700; color: #C9A84C; }
    .stat-unit { font-size: 0.8rem; color: #8b9bb4; margin-top: 2px; }
    .stat-delta { font-size: 0.75rem; color: #34d399; margin-top: 4px; }

    .tl-item { margin-bottom: 1rem; }
    .tl-date { font-size: 0.72rem; color: #8b9bb4; margin-bottom: 4px; }
    .tl-card {
        background: rgba(255,255,255,0.03); border-radius: 10px; padding: 0.75rem 1rem;
        border-left: 3px solid #C9A84C;
    }
    .tl-title { font-weight: 600; font-size: 0.92rem; color: #e8eef7; }
    .tl-desc { font-size: 0.82rem; color: #8b9bb4; margin-top: 2px; }

    .action-tile {
        background: rgba(255,255,255,0.03); border-radius: 12px; padding: 1rem;
        border: 1px solid rgba(201,168,76,0.12); cursor: pointer;
        transition: all 0.2s; display: flex; gap: 0.85rem; align-items: center;
    }
    .action-tile:hover { border-color: #C9A84C; background: rgba(201,168,76,0.08); }
    .action-tile-icon {
        width: 42px; height: 42px; border-radius: 10px;
        background: linear-gradient(135deg, rgba(201,168,76,0.2), rgba(226,196,122,0.15));
        display: flex; align-items: center; justify-content: center; font-size: 1.2rem;
    }
    .at-title { font-weight: 600; font-size: 0.92rem; color: #e8eef7; }
    .at-sub { font-size: 0.78rem; color: #8b9bb4; }

    .eco-ring-wrap { text-align: center; padding: 1rem 0; }
    .eco-num { font-size: 1.8rem; font-weight: 700; color: #C9A84C; }
    .eco-grade { font-size: 0.85rem; color: #8b9bb4; margin-top: 4px; }

    .live-dot {
        display: inline-block; width: 8px; height: 8px; border-radius: 50%;
        background: #ef4444; margin-right: 6px; animation: pulse 1.4s infinite;
    }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

    .prop-chip {
        display: inline-block; padding: 0.4rem 0.9rem; border-radius: 20px;
        background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
        font-size: 0.85rem; margin-right: 0.4rem; cursor: pointer; color: #a0aec0;
    }
    .prop-chip.active {
        background: linear-gradient(135deg, rgba(201,168,76,0.25), rgba(226,196,122,0.15));
        border-color: #C9A84C; color: #E2C47A; font-weight: 600;
    }

    div[data-testid="stMetric"] {
        background: #1a2332; border-radius: 12px; padding: 0.8rem 1rem;
        border: 1px solid rgba(201,168,76,0.1);
    }
    .stButton > button {
        border-radius: 10px; font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_agent() -> WasteAgent:
    return WasteAgent()


agent = get_agent()

# Session state
if "live_mode" not in st.session_state:
    st.session_state.live_mode = True
if "selected_prop" not in st.session_state:
    st.session_state.selected_prop = "all"
if "show_pickup_modal" not in st.session_state:
    st.session_state.show_pickup_modal = False
if "last_changes" not in st.session_state:
    st.session_state.last_changes = []
if "toast" not in st.session_state:
    st.session_state.toast = None

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ♻️ Navigation")
    nav = st.radio(
        "nav",
        ["Dashboard", "Schedule", "History", "Reports", "Settings", "Support"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("#### Eco Score")
    score = round(agent.eco_score)
    grade = "Excellent" if score >= 85 else "Good Standing" if score >= 65 else "Needs Improvement"
    # Simple SVG ring
    circ = 2 * math.pi * 32
    offset = circ * (1 - score / 100)
    st.markdown(
        f"""
        <div class="eco-ring-wrap">
            <svg width="90" height="90" viewBox="0 0 80 80">
                <circle cx="40" cy="40" r="32" fill="none" stroke="rgba(201,168,76,0.12)" stroke-width="6"/>
                <circle cx="40" cy="40" r="32" fill="none"
                    stroke="url(#gr)" stroke-width="6"
                    stroke-dasharray="{circ:.1f}" stroke-dashoffset="{offset:.1f}"
                    stroke-linecap="round" transform="rotate(-90 40 40)"/>
                <defs>
                    <linearGradient id="gr" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stop-color="#C9A84C"/>
                        <stop offset="100%" stop-color="#E2C47A"/>
                    </linearGradient>
                </defs>
                <text x="40" y="45" text-anchor="middle" fill="#C9A84C" font-size="18" font-weight="700">{score}</text>
            </svg>
            <div class="eco-grade">{grade}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("#### 🔴 Live Engine")
    st.session_state.live_mode = st.toggle("Live Mode", value=st.session_state.live_mode)
    interval = st.slider("Tick interval (s)", 4, 15, 7)

    if st.button("⚡ Force Tick", use_container_width=True):
        ch = agent.tick(force=True)
        st.session_state.last_changes = ch
        st.rerun()

    if st.session_state.live_mode:
        ch = agent.tick(force=False, interval=interval)
        if ch:
            st.session_state.last_changes = ch

    if st.session_state.last_changes:
        with st.expander("Latest changes"):
            for c in st.session_state.last_changes[-4:]:
                st.caption(c)

    st.markdown("---")
    st.markdown("#### 🤖 Waste Agent")
    q = st.text_input("Ask…", placeholder="e.g. fullest bin?")
    if st.button("Ask", use_container_width=True) and q:
        st.info(agent.generate_insight(q, st.session_state.selected_prop))

# ─────────────────────────────────────────────
# TOPBAR
# ─────────────────────────────────────────────
live_badge = '<span class="live-dot"></span>LIVE' if st.session_state.live_mode else ""
st.markdown(
    f"""
    <div class="topbar">
        <div class="brand">
            <div class="brand-icon">♻️</div>
            <div>
                <h1>Mwarokin Estates</h1>
                <p>Waste & Collection Management</p>
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:1.2rem;">
            <span style="font-size:0.8rem;color:#C9A84C;font-weight:600;">{live_badge}</span>
            <span style="position:relative;font-size:1.25rem;">🔔
                <span style="position:absolute;top:-4px;right:-6px;width:8px;height:8px;
                background:#ef4444;border-radius:50%;"></span>
            </span>
            <div style="display:flex;align-items:center;gap:0.6rem;">
                <div style="width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#C9A84C,#E2C47A);
                color:#0f1419;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:0.85rem;">JD</div>
                <div>
                    <div style="font-weight:600;font-size:0.9rem;color:#e8eef7;">John Doe</div>
                    <div style="font-size:0.72rem;color:#8b9bb4;">Milki Tier</div>
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# MAIN ROUTING
# ─────────────────────────────────────────────

if nav == "Dashboard":
    # Property chips
    chips = [("all", "All Properties"), ("va", "Villa A"), ("vb", "Villa B"), ("ap", "Apartment 1")]
    cols = st.columns(len(chips))
    for i, (pid, label) in enumerate(chips):
        with cols[i]:
            active = st.session_state.selected_prop == pid
            if st.button(
                f"{'✅ ' if active else ''}{label}",
                key=f"chip_{pid}",
                use_container_width=True,
                type="primary" if active else "secondary",
            ):
                st.session_state.selected_prop = pid
                st.rerun()

    prop = agent.properties[st.session_state.selected_prop]
    stats = agent.get_stats(st.session_state.selected_prop)

    # Row: Schedule + Bin Status
    left, right = st.columns(2)

    with left:
        st.markdown(
            """
            <div class="card">
                <div class="card-title-eyebrow">Weekly</div>
                <div class="card-title">Collection Schedule</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for s in agent.schedules:
            badge_cls = "badge-done" if s.status == PickupStatus.DONE else "badge-upcoming"
            badge_txt = "Done" if s.status == PickupStatus.DONE else "Upcoming"
            icon_cls = s.waste_type.value if s.waste_type != WasteType.HAZARDOUS else "general"
            st.markdown(
                f"""
                <div class="sched-item">
                    <div class="sched-left">
                        <div class="sched-icon {icon_cls}">{s.icon}</div>
                        <div>
                            <div style="font-weight:600;color:#e8eef7;">{s.label}</div>
                            <div style="font-size:0.8rem;color:#8b9bb4;">{s.days} · {s.time_window}</div>
                        </div>
                    </div>
                    <span class="badge {badge_cls}">{badge_txt}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if st.button("🔔 Set Reminder", key="rem", use_container_width=True):
            msg = agent.set_reminder()
            st.session_state.toast = msg
            st.rerun()

    with right:
        st.markdown(
            """
            <div class="card">
                <div class="card-title-eyebrow">Live</div>
                <div class="card-title">Bin Status</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for b in prop.bins.values():
            level = "fill-high" if b.fill_pct >= 75 else "fill-med" if b.fill_pct >= 40 else "fill-low"
            note = ""
            if b.fill_pct >= 80:
                note = ' <span style="color:#f87171;font-size:0.75em;">· attention needed</span>'
            elif "today" in b.last_emptied or "just now" in b.last_emptied:
                note = f' <span style="color:#8b9bb4;font-size:0.75em;">· emptied {b.last_emptied}</span>'
            else:
                note = f' <span style="color:#8b9bb4;font-size:0.75em;">· last emptied {b.last_emptied}</span>'

            st.markdown(
                f"""
                <div class="bin-row {level}">
                    <div class="bin-emoji">{b.emoji}</div>
                    <div style="flex:1;">
                        <div class="bin-name">{b.name}{note}</div>
                        <div class="fill-bar"><div class="fill-inner" style="width:{b.fill_pct:.0f}%"></div></div>
                    </div>
                    <div class="fill-pct">{b.fill_pct:.0f}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if st.button("🚛 Request Pickup", key="req_pickup", use_container_width=True, type="primary"):
            st.session_state.show_pickup_modal = True
            st.rerun()

    # Stats card
    st.markdown(
        """
        <div class="card">
            <div class="card-title-eyebrow">This Month</div>
            <div class="card-title">Waste Statistics</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Total Waste", f"{stats['total_kg']} kg", delta="+4%")
    s2.metric("Recycled", f"{stats['recycled_kg']} kg", delta="+12%")
    s3.metric("Recycling Rate", f"{stats['recycle_rate']}%", delta="+3 pts")
    s4.metric("Pickups Done", f"{stats['pickups_done']}", delta="on schedule", delta_color="off")

    c1, c2 = st.columns(2)
    with c1:
        st.button("📊 Full Report", use_container_width=True)
    with c2:
        st.button("📄 Download PDF", use_container_width=True)

    # Timeline + Quick Actions
    col_tl, col_act = st.columns(2)

    with col_tl:
        st.markdown(
            """
            <div class="card">
                <div class="card-title-eyebrow">Log</div>
                <div class="card-title">Recent Activity</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for a in agent.activities[:6]:
            st.markdown(
                f"""
                <div class="tl-item">
                    <div class="tl-date">{a.timestamp}</div>
                    <div class="tl-card">
                        <div class="tl-title">{a.icon} {a.title}</div>
                        <div class="tl-desc">{a.description}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col_act:
        st.markdown(
            """
            <div class="card">
                <div class="card-title-eyebrow">Shortcuts</div>
                <div class="card-title">Quick Actions</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        a1, a2 = st.columns(2)
        with a1:
            if st.button("📅 Special Pickup", use_container_width=True):
                st.session_state.show_pickup_modal = True
                st.rerun()
            st.button("🔄 Replace Bin", use_container_width=True)
        with a2:
            st.button("⚠️ Report Issue", use_container_width=True)
            st.button("📖 Guidelines", use_container_width=True)

    # ── Special Pickup Modal ──────────────────
    if st.session_state.show_pickup_modal:
        with st.form("pickup_form", clear_on_submit=True):
            st.subheader("Schedule Special Pickup")
            ptype = st.selectbox(
                "Pickup Type",
                ["", "General Waste", "Recyclables", "Organic Waste", "Hazardous Materials"],
            )
            pdate = st.date_input("Preferred Date", min_value=date.today())
            pslot = st.selectbox(
                "Time Slot",
                ["", "Morning · 7:00 – 10:00 AM", "Afternoon · 1:00 – 4:00 PM", "Evening · 5:00 – 8:00 PM"],
            )
            notes = st.text_area("Special Instructions", placeholder="Any notes for our collection team…")
            c1, c2 = st.columns(2)
            with c1:
                cancel = st.form_submit_button("Cancel", use_container_width=True)
            with c2:
                confirm = st.form_submit_button("✅ Confirm Pickup", use_container_width=True, type="primary")

            if cancel:
                st.session_state.show_pickup_modal = False
                st.rerun()
            if confirm:
                if not ptype or not pslot:
                    st.error("Please select waste type and time slot.")
                else:
                    agent.request_special_pickup(ptype, str(pdate), pslot, notes)
                    st.session_state.show_pickup_modal = False
                    st.session_state.toast = "Special pickup scheduled successfully."
                    st.rerun()

    # Toast
    if st.session_state.toast:
        st.success(st.session_state.toast)
        st.session_state.toast = None

    # Auto-refresh
    if st.session_state.live_mode:
        time.sleep(0.04)
        st.rerun()

elif nav == "Schedule":
    st.title("📅 Collection Schedule")
    for s in agent.schedules:
        st.info(f"**{s.label}** — {s.days} · {s.time_window}  \nStatus: `{s.status.value}`")
    if agent.special_pickups:
        st.subheader("Special Pickups")
        df = pd.DataFrame([asdict(p) for p in agent.special_pickups])
        st.dataframe(df[["waste_type", "preferred_date", "time_slot", "status"]], use_container_width=True)

elif nav == "History":
    st.title("📜 Activity History")
    for a in agent.activities:
        st.markdown(f"**{a.timestamp}** — {a.icon} {a.title}  \n_{a.description}_")

elif nav == "Reports":
    st.title("📊 Reports")
    stats = agent.get_stats()
    st.metric("Eco Score", f"{stats['eco_score']}")
    st.metric("Recycling Rate", f"{stats['recycle_rate']}%")
    st.metric("Total Waste (month)", f"{stats['total_kg']} kg")
    st.button("📄 Generate PDF Report")

elif nav == "Settings":
    st.title("⚙️ Settings")
    st.toggle("Email notifications", value=True)
    st.toggle("SMS alerts for high bin levels", value=True)
    st.selectbox("Preferred language", ["English", "Swahili", "French"])

else:
    st.title("❓ Support")
    st.write("Contact the Mwarokin Estates waste team at **waste@mwarokin.co.ke** or call **+254 700 000 000**.")
    st.text_area("Describe your issue")
    st.button("Submit Ticket")

st.markdown(
    """
    <div style="text-align:center;color:#5a6a80;font-size:0.8rem;padding:2rem 0 1rem;">
        Mwarokin Estates – Waste & Collection © 2026 · Powered by Syllogism Technology Africa<br>
        Agentic + Real-time Python Edition
    </div>
    """,
    unsafe_allow_html=True,
)
