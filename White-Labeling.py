"""
Mwarokin Estates – White Label Studio
Modern agentic Python implementation (Streamlit)
Fully functional upgrade of the provided UI
"""

import streamlit as st
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime
import copy

# ============================================================
# CONFIG & CONSTANTS
# ============================================================

THEME_PRESETS = [
    {"id": 1, "name": "Obsidian Gold", "primary": "#0e1a2b", "secondary": "#c9a959", "accent": "#2f7d5e",
     "grad": "linear-gradient(135deg,#0e1a2b,#1e3352)"},
    {"id": 2, "name": "Ocean Blue", "primary": "#4361ee", "secondary": "#3a0ca3", "accent": "#4cc9f0",
     "grad": "linear-gradient(135deg,#4361ee,#3a0ca3)"},
    {"id": 3, "name": "Purple Pink", "primary": "#7209b7", "secondary": "#f72585", "accent": "#b5179e",
     "grad": "linear-gradient(135deg,#7209b7,#f72585)"},
    {"id": 4, "name": "Savanna Green", "primary": "#2a9d8f", "secondary": "#264653", "accent": "#e9c46a",
     "grad": "linear-gradient(135deg,#2a9d8f,#264653)"},
    {"id": 5, "name": "Coral Sunset", "primary": "#e76f51", "secondary": "#9c2c1d", "accent": "#f4a261",
     "grad": "linear-gradient(135deg,#e76f51,#9c2c1d)"},
    {"id": 6, "name": "Sky Teal", "primary": "#2f5f8a", "secondary": "#14314a", "accent": "#4cc9f0",
     "grad": "linear-gradient(135deg,#2f5f8a,#14314a)"},
]

FONT_PAIRS = [
    {"id": "fraunces-inter", "label": "Fraunces + Inter (Editorial)"},
    {"id": "poppins-inter", "label": "Poppins + Inter (Modern)"},
    {"id": "playfair-lato", "label": "Playfair + Lato (Classic)"},
    {"id": "space-dm", "label": "Space Grotesk + DM Sans (Tech)"},
]

PLAN_TIERS = [
    {
        "id": "msingi", "name": "Msingi", "price": "KSh 2,500/mo",
        "listings": 15, "api_calls": "2,000", "storage": "1 GB",
        "features": [
            "Up to 15 active listings",
            "Basic branding (logo + 1 color)",
            "Email support",
            "Standard subdomain",
        ],
    },
    {
        "id": "jengo", "name": "Jengo", "price": "KSh 6,900/mo",
        "listings": 60, "api_calls": "15,000", "storage": "10 GB",
        "features": [
            "Up to 60 active listings",
            "Full theme customization",
            "Priority support",
            "Custom domain (1)",
            "Lease drafting tools",
        ],
    },
    {
        "id": "milki", "name": "Milki", "price": "KSh 15,900/mo",
        "listings": 250, "api_calls": "75,000", "storage": "50 GB",
        "features": [
            "Up to 250 active listings",
            "White-label mobile web app",
            "Dedicated success manager",
            "Custom domain (3) + SSL",
            "Matchmaking AI engine",
            "Webhook automations",
        ],
    },
    {
        "id": "taifa", "name": "Taifa", "price": "Custom pricing",
        "listings": "Unlimited", "api_calls": "Unlimited", "storage": "500 GB+",
        "features": [
            "Unlimited listings & domains",
            "Full API + webhook access",
            "SLA-backed uptime",
            "Dedicated infrastructure",
            "On-boarding & migration support",
        ],
    },
]

STORAGE_KEY = "mwarokin_whitelabel_config_v1"


def rid() -> str:
    return uuid.uuid4().hex[:8].upper()


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class Theme:
    id: int = 1
    name: str = "Obsidian Gold"
    primary: str = "#0e1a2b"
    secondary: str = "#c9a959"
    accent: str = "#2f7d5e"
    grad: str = "linear-gradient(135deg,#0e1a2b,#1e3352)"


@dataclass
class Config:
    client_name: str = "Zawadi Properties Ltd"
    tenant_id: str = "TENANT-A17"
    role: str = "Premium Partner"
    locale: str = "en-KE"
    currency: str = "KES"
    theme: Theme = field(default_factory=Theme)
    font_pair: str = "fraunces-inter"
    subdomain: str = "zawadi"
    custom_domain: str = ""
    domain_verified: bool = False
    plan_id: str = "jengo"
    api_key: str = field(default_factory=lambda: f"mwk_live_{rid()}{rid()}".lower())
    webhook_url: str = ""


@dataclass
class Listing:
    id: str
    tenant_id: str
    price: int
    status: str


@dataclass
class LeaseDraft:
    clauses: List[str]
    schedule: Dict[str, Any]
    risks: List[str]


@dataclass
class MatchResult:
    listing_id: str
    score: int


@dataclass
class BuyerProfile:
    id: str
    preferences: Dict[str, Any]


# ============================================================
# MOCK API (Agentic backend simulation)
# ============================================================

class MockAPI:
    @staticmethod
    def delay(ms: float = 0.65):
        time.sleep(ms)

    @classmethod
    def get_listings(cls) -> List[Listing]:
        cls.delay()
        return [
            Listing("LST001", "TENANT_A", 250000, "available"),
            Listing("LST002", "TENANT_B", 320000, "available"),
            Listing("LST003", "TENANT_C", 180000, "pending"),
            Listing("LST004", "TENANT_A", 275000, "available"),
            Listing("LST005", "TENANT_D", 410000, "available"),
        ]

    @classmethod
    def create_lease_draft(cls, listing_id: str, applicant_id: str) -> LeaseDraft:
        cls.delay()
        return LeaseDraft(
            clauses=["Standard Lease Agreement", "Maintenance Responsibilities", "Payment Terms"],
            schedule={"start_date": "2026-08-01", "end_date": "2027-07-31", "rent": 2500},
            risks=["Credit Risk", "Market Volatility"],
        )

    @classmethod
    def matchmaking(cls) -> List[MatchResult]:
        cls.delay()
        return [
            MatchResult("LST001", 92),
            MatchResult("LST002", 87),
            MatchResult("LST004", 78),
        ]

    @classmethod
    def get_buyer_profile(cls) -> BuyerProfile:
        cls.delay()
        return BuyerProfile(
            id="BP001",
            preferences={
                "min_price": 200000,
                "max_price": 350000,
                "location": "Downtown",
                "property_type": "Apartment",
                "bedrooms": 2,
            },
        )


# ============================================================
# PERSISTENCE
# ============================================================

def load_config() -> Config:
    if "cfg" in st.session_state:
        return st.session_state.cfg
    cfg = Config()
    st.session_state.cfg = cfg
    return cfg


def save_config(cfg: Config):
    st.session_state.cfg = cfg


# ============================================================
# AGENTIC STATE MANAGER
# ============================================================

class WhiteLabelAgent:
    """Agentic controller that owns state, side-effects and orchestration."""

    def __init__(self):
        self.cfg = load_config()
        if "active_tab" not in st.session_state:
            st.session_state.active_tab = "branding"
        if "listings" not in st.session_state:
            st.session_state.listings = []
            st.session_state.listings_loading = True
        if "lease_result" not in st.session_state:
            st.session_state.lease_result = None
        if "match_result" not in st.session_state:
            st.session_state.match_result = None
        if "profile_result" not in st.session_state:
            st.session_state.profile_result = None
        if "key_visible" not in st.session_state:
            st.session_state.key_visible = False
        if "saving" not in st.session_state:
            st.session_state.saving = False

    @property
    def active_tab(self) -> str:
        return st.session_state.active_tab

    def set_tab(self, tab: str):
        st.session_state.active_tab = tab

    def notify(self, message: str, type_: str = "info", title: str = ""):
        icons = {"info": "ℹ️", "success": "✅", "error": "❌"}
        prefix = f"**{title}** — " if title else ""
        if type_ == "success":
            st.success(f"{icons.get(type_, '')} {prefix}{message}")
        elif type_ == "error":
            st.error(f"{icons.get(type_, '')} {prefix}{message}")
        else:
            st.info(f"{icons.get(type_, '')} {prefix}{message}")

    def fetch_listings(self):
        st.session_state.listings_loading = True
        try:
            listings = MockAPI.get_listings()
            st.session_state.listings = listings
            st.session_state.listings_loading = False
        except Exception:
            st.session_state.listings_loading = False
            self.notify("Failed to load listings.", "error")

    def publish(self):
        st.session_state.saving = True
        time.sleep(1.1)
        save_config(self.cfg)
        st.session_state.saving = False
        subdomain = self.cfg.subdomain or "yourbrand"
        self.notify(
            f"Your branding is now live at {subdomain}.mwarokinestates.africa",
            "success",
            "Published",
        )

    def regenerate_api_key(self):
        self.cfg.api_key = f"mwk_live_{rid()}{rid()}".lower()
        save_config(self.cfg)
        st.session_state.key_visible = True
        self.notify("New API key generated. Update your integrations.", "success")

    def switch_plan(self, plan_id: str):
        self.cfg.plan_id = plan_id
        save_config(self.cfg)
        name = next(t["name"] for t in PLAN_TIERS if t["id"] == plan_id)
        self.notify(f"Switched to the {name} plan.", "success")

    def apply_preset(self, preset_id: int):
        preset = next(p for p in THEME_PRESETS if p["id"] == preset_id)
        self.cfg.theme = Theme(**preset)
        save_config(self.cfg)


# ============================================================
# UI COMPONENTS
# ============================================================

def inject_css(theme: Theme):
    st.markdown(
        f"""
        <style>
        :root {{
            --primary: {theme.primary};
            --secondary: {theme.secondary};
            --accent: {theme.accent};
            --gold: #c9a959;
            --navy: #0e1a2b;
            --gray-100: #f8f7f4;
            --gray-600: #6b6560;
        }}
        .stApp {{ background: linear-gradient(160deg, #f8f7f4 0%, #f0ede6 100%); }}
        .main-header {{
            font-family: 'Georgia', serif;
            color: var(--navy);
            font-size: 1.75rem;
            margin-bottom: 0.25rem;
        }}
        .sub-header {{ color: var(--gray-600); font-size: 0.9rem; margin-bottom: 1.5rem; }}
        .card {{
            background: white;
            border-radius: 14px;
            padding: 1.25rem 1.4rem;
            box-shadow: 0 2px 12px rgba(14,26,43,0.06);
            border: 1px solid #ece8e0;
            margin-bottom: 1rem;
        }}
        .pill {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 600;
        }}
        .pill-available {{ background: #e6f4ea; color: #1e7e34; }}
        .pill-pending {{ background: #fff3cd; color: #856404; }}
        .pill-active {{ background: #e6f4ea; color: #1e7e34; }}
        .meter {{
            height: 6px;
            background: #ece8e0;
            border-radius: 3px;
            overflow: hidden;
            margin-top: 4px;
        }}
        .meter-fill {{ height: 100%; background: var(--accent); border-radius: 3px; }}
        .preview-frame {{
            border: 1px solid #ddd;
            border-radius: 12px;
            overflow: hidden;
            background: white;
        }}
        .preview-browserbar {{
            background: #f0f0f0;
            padding: 8px 12px;
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.75rem;
        }}
        .preview-dot {{
            width: 8px; height: 8px; border-radius: 50%;
            background: #ccc;
        }}
        .pv-header {{
            padding: 14px 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .pv-logo {{ display: flex; align-items: center; gap: 10px; }}
        .pv-logo-badge {{
            width: 32px; height: 32px; border-radius: 8px;
            display: flex; align-items: center; justify-content: center;
            font-weight: 700; font-size: 0.8rem;
        }}
        .pv-hero {{ padding: 24px 18px; text-align: center; }}
        .pv-cards {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding: 0 18px 18px; }}
        .pv-card {{
            border: 1.5px solid;
            border-radius: 10px;
            padding: 12px;
            font-size: 0.8rem;
        }}
        div[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #0e1a2b 0%, #1a2a40 100%);
        }}
        div[data-testid="stSidebar"] * {{ color: #e8e4dc !important; }}
        .sidebar-brand {{
            display: flex; align-items: center; gap: 12px;
            padding: 8px 0 20px 0; border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 16px;
        }}
        .nav-item {{
            padding: 8px 12px; border-radius: 8px; cursor: pointer;
            margin-bottom: 2px; font-size: 0.9rem;
        }}
        .nav-item:hover {{ background: rgba(255,255,255,0.08); }}
        .nav-item.active {{ background: rgba(201,169,89,0.25); color: #c9a959 !important; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(agent: WhiteLabelAgent):
    cfg = agent.cfg
    tier = next((t for t in PLAN_TIERS if t["id"] == cfg.plan_id), PLAN_TIERS[0])

    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <div style="width:40px;height:40px;background:#c9a959;border-radius:10px;
                            display:flex;align-items:center;justify-content:center;font-size:1.2rem;">
                    🛡️
                </div>
                <div>
                    <div style="font-weight:700;font-size:1.05rem;color:#fff;">Mwarokin Estates</div>
                    <div style="font-size:0.75rem;opacity:0.7;">White Label Studio</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        groups = [
            ("Brand Studio", [
                ("branding", "🎨 Branding & Theme"),
                ("domain", "🌐 Domain & SSL"),
            ]),
            ("Operations", [
                ("listings", "🏢 Property Listings"),
                ("leases", "📝 Lease Drafting"),
                ("matchmaking", "🤝 Matchmaking"),
            ]),
            ("Developer", [
                ("api", "🔌 API & Webhooks"),
            ]),
            ("Account", [
                ("plan", "📊 Plan & Usage"),
            ]),
        ]

        for group_name, tabs in groups:
            st.caption(group_name.upper())
            for tab_id, label in tabs:
                if st.button(label, key=f"nav_{tab_id}", use_container_width=True):
                    agent.set_tab(tab_id)
                    st.rerun()

        st.markdown("---")
        st.markdown(
            f"""
            <div style="background:rgba(255,255,255,0.07);border-radius:12px;padding:14px;">
                <div style="font-size:0.7rem;opacity:0.7;margin-bottom:4px;">{tier['name']} plan</div>
                <div style="font-weight:700;font-size:0.95rem;">{cfg.client_name}</div>
                <div style="font-size:0.75rem;opacity:0.65;">{cfg.tenant_id} · {cfg.role}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_topbar(agent: WhiteLabelAgent):
    titles = {
        "branding": ("Branding & Theme", "Shape how your clients experience the Mwarokin platform under your own identity."),
        "domain": ("Domain & SSL", "Serve your white-labeled portal from your own web address."),
        "listings": ("Property Listings", "All active and pending listings synced across your portfolio."),
        "leases": ("Lease Drafting", "Generate a lease draft instantly for any listing and applicant."),
        "matchmaking": ("Matchmaking", "Surface the best-fit listings for a given buyer profile."),
        "api": ("API & Webhooks", "Connect your own systems to the Mwarokin platform."),
        "plan": ("Plan & Usage", "Review your subscription tier and current usage."),
    }
    title, sub = titles[agent.active_tab]
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f'<div class="main-header">{title}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sub-header">{sub}</div>', unsafe_allow_html=True)
    with col2:
        c1, c2 = st.columns(2)
        if c1.button("🔄 Refresh", use_container_width=True):
            agent.fetch_listings()
            agent.notify("Data refreshed.", "success")
            st.rerun()
        if c2.button("🚀 Publish", use_container_width=True, type="primary",
                     disabled=st.session_state.saving):
            agent.publish()
            st.rerun()


def render_preview(cfg: Config):
    t = cfg.theme
    url = f"{cfg.subdomain or 'yourbrand'}.mwarokinestates.africa"
    initials = "".join(w[0] for w in (cfg.client_name or "M E").split()[:2]).upper()
    currency = cfg.currency or "KES"

    st.markdown(
        f"""
        <div class="preview-frame">
            <div class="preview-browserbar">
                <span class="preview-dot"></span><span class="preview-dot"></span><span class="preview-dot"></span>
                <span style="margin-left:8px;color:#555;">🔒 {url}</span>
            </div>
            <div class="pv-header" style="background:{t.primary};">
                <div class="pv-logo">
                    <div class="pv-logo-badge" style="background:{t.accent};color:{t.primary};">{initials}</div>
                    <div style="color:#fff;font-weight:600;">{cfg.client_name or 'Your Brand'}</div>
                </div>
                <div style="background:{t.secondary};color:#fff;padding:4px 12px;border-radius:999px;font-size:0.75rem;">
                    Tenant Portal
                </div>
            </div>
            <div class="pv-hero">
                <span style="background:{t.accent}22;color:{t.secondary};padding:3px 10px;border-radius:999px;font-size:0.7rem;">
                    Powered by Mwarokin Estates
                </span>
                <div style="font-size:1.15rem;font-weight:700;margin:10px 0 4px;color:#1a1a1a;">
                    Find your next home with {cfg.client_name or 'us'}
                </div>
                <div style="font-size:0.8rem;color:#666;margin-bottom:12px;">
                    Verified listings · Secure payments · Real-time support
                </div>
                <span style="background:{t.primary};color:#fff;padding:8px 18px;border-radius:8px;font-size:0.85rem;">
                    Browse listings
                </span>
            </div>
            <div class="pv-cards">
                <div class="pv-card" style="border-color:{t.primary};">
                    <div style="font-weight:600;">2-Bed Apartment</div>
                    <div style="color:#666;">{currency} 45,000 / mo</div>
                </div>
                <div class="pv-card" style="border-color:{t.accent};">
                    <div style="font-weight:600;">Studio Unit</div>
                    <div style="color:#666;">{currency} 22,000 / mo</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_branding(agent: WhiteLabelAgent):
    cfg = agent.cfg
    col_left, col_right = st.columns([1.4, 1])

    with col_left:
        with st.container():
            st.markdown("#### ✍️ Client identity")
            st.caption("Shown across the portal header, receipts, and notifications.")
            cfg.client_name = st.text_input("Client / company name", value=cfg.client_name)
            c1, c2 = st.columns(2)
            with c1:
                cfg.locale = st.selectbox(
                    "Locale",
                    ["en-KE", "en-NG", "en-GH", "en-ZA", "en-US", "fr-CI"],
                    index=["en-KE", "en-NG", "en-GH", "en-ZA", "en-US", "fr-CI"].index(cfg.locale),
                )
            with c2:
                cfg.currency = st.selectbox(
                    "Currency",
                    ["KES", "NGN", "GHS", "ZAR", "USD"],
                    index=["KES", "NGN", "GHS", "ZAR", "USD"].index(cfg.currency),
                )
            cfg.font_pair = st.selectbox(
                "Typography pairing",
                options=[f["id"] for f in FONT_PAIRS],
                format_func=lambda x: next(f["label"] for f in FONT_PAIRS if f["id"] == x),
                index=[f["id"] for f in FONT_PAIRS].index(cfg.font_pair),
            )

        with st.container():
            st.markdown("#### 🎨 Colors")
            st.caption("Pick colors — the preview updates instantly.")
            c1, c2, c3 = st.columns(3)
            with c1:
                cfg.theme.primary = st.color_picker("Primary", cfg.theme.primary)
            with c2:
                cfg.theme.secondary = st.color_picker("Secondary", cfg.theme.secondary)
            with c3:
                cfg.theme.accent = st.color_picker("Accent", cfg.theme.accent)

        with st.container():
            st.markdown("#### 📚 Theme presets")
            st.caption("Start from a curated palette, then fine-tune above.")
            cols = st.columns(3)
            for i, p in enumerate(THEME_PRESETS):
                with cols[i % 3]:
                    active = (
                        cfg.theme.primary == p["primary"]
                        and cfg.theme.secondary == p["secondary"]
                    )
                    label = f"{'✓ ' if active else ''}{p['name']}"
                    if st.button(label, key=f"preset_{p['id']}", use_container_width=True):
                        agent.apply_preset(p["id"])
                        st.rerun()

        save_config(cfg)

    with col_right:
        st.markdown("#### 👁️ Live preview")
        st.caption(f"This is what {cfg.client_name or 'your'} tenants will see.")
        render_preview(cfg)


def render_domain(agent: WhiteLabelAgent):
    cfg = agent.cfg
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🌐 Subdomain")
        st.caption("Free and instant — included with every plan.")
        sub = st.text_input(
            "Choose your subdomain",
            value=cfg.subdomain,
            help="Only lowercase letters, numbers and hyphens",
        )
        cfg.subdomain = "".join(c for c in sub.lower() if c.isalnum() or c == "-")
        st.markdown(
            f'<span class="pill pill-active">✓ Active</span> &nbsp;Live at '
            f'<code>{cfg.subdomain or "yourbrand"}.mwarokinestates.africa</code>',
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown("#### 🔗 Custom domain")
        st.caption("Point your own domain at your white-labeled portal.")
        cfg.custom_domain = st.text_input(
            "Custom domain",
            value=cfg.custom_domain,
            placeholder="e.g. portal.zawadiproperties.co.ke",
        )
        st.markdown("Add these DNS records with your domain registrar:")
        st.code("Type   CNAME\nHost   portal\nValue  cname.mwarokinestates.africa", language=None)

        status = (
            '<span class="pill pill-active">🛡️ SSL active & verified</span>'
            if cfg.domain_verified
            else '<span class="pill" style="background:#fff3cd;color:#856404;">⏳ Awaiting DNS verification</span>'
        )
        st.markdown(status, unsafe_allow_html=True)
        if st.button("Check now"):
            with st.spinner("Checking DNS records…"):
                time.sleep(1.6)
            cfg.domain_verified = True
            save_config(cfg)
            agent.notify("Domain verified and SSL issued.", "success")
            st.rerun()

    save_config(cfg)


def render_listings(agent: WhiteLabelAgent):
    if st.session_state.listings_loading and not st.session_state.listings:
        agent.fetch_listings()

    st.markdown("#### 🏢 Property listings")
    st.caption("Synced from your portfolio in real time.")

    if st.session_state.listings_loading:
        st.info("⏳ Loading listings…")
    else:
        listings = st.session_state.listings
        cols = st.columns(3)
        for i, l in enumerate(listings):
            with cols[i % 3]:
                status_class = "pill-available" if l.status == "available" else "pill-pending"
                status_label = "Available" if l.status == "available" else "Pending"
                st.markdown(
                    f"""
                    <div class="card" style="position:relative;">
                        <span class="pill {status_class}" style="position:absolute;top:12px;right:12px;">
                            {status_label}
                        </span>
                        <div style="font-weight:700;color:var(--navy);margin-bottom:4px;">{l.id}</div>
                        <div style="font-size:0.8rem;color:#666;">Tenant: {l.tenant_id}</div>
                        <div style="font-weight:600;margin-top:8px;color:var(--navy);">
                            {agent.cfg.currency} {l.price:,}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_leases(agent: WhiteLabelAgent):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 📝 Lease draft")
        st.caption("Generate a lease instantly from a listing and applicant.")
        with st.form("lease_form"):
            listing_id = st.text_input("Listing ID", placeholder="e.g. LST001")
            applicant_id = st.text_input("Applicant ID", placeholder="e.g. APP-2201")
            submitted = st.form_submit_button("Create lease draft", type="primary", use_container_width=True)
            if submitted:
                if not listing_id or not applicant_id:
                    agent.notify("Both fields are required.", "error")
                else:
                    with st.spinner("Creating…"):
                        result = MockAPI.create_lease_draft(listing_id, applicant_id)
                    st.session_state.lease_result = result
                    agent.notify("Lease draft created.", "success")
                    st.rerun()

    with col2:
        st.markdown("#### 📜 Draft result")
        r = st.session_state.lease_result
        if r:
            st.markdown(f"**Clauses:** {', '.join(r.clauses)}")
            st.markdown(f"**Term:** {r.schedule['start_date']} → {r.schedule['end_date']}")
            st.markdown(f"**Monthly rent:** {agent.cfg.currency} {r.schedule['rent']:,}")
            st.markdown(f"**Flagged risks:** {', '.join(r.risks)}")
        else:
            st.info("Submit the form to generate a lease draft.")


def render_matchmaking(agent: WhiteLabelAgent):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🤝 Find matches")
        st.caption("Match a buyer profile against your active listings.")
        with st.form("match_form"):
            profile_id = st.text_input("Buyer profile ID", placeholder="e.g. BP001")
            submitted = st.form_submit_button("Find matches", type="primary", use_container_width=True)
            if submitted:
                with st.spinner("Searching…"):
                    matches = MockAPI.matchmaking()
                    profile = MockAPI.get_buyer_profile()
                st.session_state.match_result = matches
                st.session_state.profile_result = profile
                agent.notify(f"{len(matches)} matches found.", "success")
                st.rerun()

        p = st.session_state.profile_result
        if p:
            st.markdown("---")
            prefs = p.preferences
            st.markdown(
                f"**Budget:** {agent.cfg.currency} {prefs['min_price']:,}–{prefs['max_price']:,}  \n"
                f"**Location:** {prefs['location']}  \n"
                f"**Type:** {prefs['property_type']}  \n"
                f"**Bedrooms:** {prefs['bedrooms']}"
            )

    with col2:
        st.markdown("#### ⭐ Best-fit listings")
        m = st.session_state.match_result
        if m:
            for x in m:
                st.markdown(
                    f"""
                    <div style="display:flex;justify-content:space-between;align-items:center;
                                padding:11px 14px;background:#f8f7f4;border-radius:10px;margin-bottom:8px;">
                        <span style="font-weight:700;color:#0e1a2b;">{x.listing_id}</span>
                        <span class="pill pill-available">{x.score}% match</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("Run a match to see recommended listings.")


def render_api(agent: WhiteLabelAgent):
    cfg = agent.cfg
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🔑 API key")
        st.caption("Use this key to authenticate requests from your systems.")
        masked = cfg.api_key if st.session_state.key_visible else cfg.api_key[:9] + "••••••••••••••••••"
        st.code(masked, language=None)
        c1, c2, c3 = st.columns(3)
        if c1.button("👁️ Toggle"):
            st.session_state.key_visible = not st.session_state.key_visible
            st.rerun()
        if c2.button("📋 Copy"):
            st.session_state["_copy_key"] = cfg.api_key
            agent.notify("API key ready (use clipboard in real deployment).", "success")
        if c3.button("🔄 Regenerate"):
            agent.regenerate_api_key()
            st.rerun()

        st.markdown("#### 📡 Webhook URL")
        st.caption("We'll POST payment and listing events here.")
        cfg.webhook_url = st.text_input(
            "Webhook URL",
            value=cfg.webhook_url,
            placeholder="https://yourapp.co.ke/webhooks/mwarokin",
            label_visibility="collapsed",
        )
        save_config(cfg)

    with col2:
        st.markdown("#### 💻 Example request")
        st.caption("Fetch your active listings from the API.")
        st.code(
            f'curl https://api.mwarokinestates.africa/v1/listings \\\n'
            f'  -H "Authorization: Bearer {cfg.api_key[:9]}••••••••"',
            language="bash",
        )
        st.markdown("#### ⚡ Event types")
        for evt in ["payment.completed", "lease.created", "listing.updated", "tenant.matched"]:
            st.markdown(f"✅ `{evt}`")


def render_plan(agent: WhiteLabelAgent):
    cfg = agent.cfg
    used = {"listings": 5, "api_calls": 1240, "storage": 0.4}
    tier = next(t for t in PLAN_TIERS if t["id"] == cfg.plan_id)

    st.markdown(f"#### 📈 Current usage — {tier['name']} plan")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Listings used", f"{used['listings']} / {tier['listings']}")
        pct = min(100, used["listings"] / tier["listings"] * 100) if isinstance(tier["listings"], int) else 20
        st.progress(pct / 100)
    with c2:
        st.metric("API calls this month", f"{used['api_calls']:,} / {tier['api_calls']}")
        st.progress(0.35)
    with c3:
        st.metric("Storage used", f"{used['storage']} GB / {tier['storage']}")
        st.progress(0.15)

    st.markdown("---")
    cols = st.columns(4)
    for i, t in enumerate(PLAN_TIERS):
        with cols[i]:
            is_current = t["id"] == cfg.plan_id
            st.markdown(f"**{t['name']}**")
            st.markdown(f"<div style='font-size:1.1rem;font-weight:700;color:#c9a959;'>{t['price']}</div>",
                        unsafe_allow_html=True)
            for f in t["features"]:
                st.markdown(f"• {f}")
            if is_current:
                st.button("Active plan", key=f"plan_{t['id']}", disabled=True, use_container_width=True)
            else:
                if st.button(f"Switch to {t['name']}", key=f"plan_{t['id']}", use_container_width=True):
                    agent.switch_plan(t["id"])
                    st.rerun()


# ============================================================
# MAIN
# ============================================================

def main():
    st.set_page_config(
        page_title="Mwarokin White Label Studio",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    agent = WhiteLabelAgent()
    inject_css(agent.cfg.theme)
    render_sidebar(agent)
    render_topbar(agent)

    tab_map = {
        "branding": render_branding,
        "domain": render_domain,
        "listings": render_listings,
        "leases": render_leases,
        "matchmaking": render_matchmaking,
        "api": render_api,
        "plan": render_plan,
    }
    tab_map[agent.active_tab](agent)


if __name__ == "__main__":
    main()