
"""
Overview.py — Modern Agentic Mali Access Union Member Dashboard
Fully functional Python implementation with state management, reactive UI,
session handling, and agentic helpers.
Requires: streamlit, plotly, pandas
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Literal

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ──────────────────────────────────────────────
# Domain models
# ──────────────────────────────────────────────

@dataclass
class MemberSession:
    username: str = "Member"
    role: str = "Group member"
    credit_score: int = 724
    credit_max: int = 850
    on_time_pct: float = 98.0
    credit_limit: int = 42_000
    history_years: int = 3
    score_delta: int = 12
    wallet_balance: int = 12_400
    wallet_week_delta: int = 2_000
    active_members: int = 18
    total_members: int = 20
    new_members_month: int = 3
    language: Literal["en", "sw", "fr"] = "en"

    @property
    def initial(self) -> str:
        return self.username.strip()[:1].upper() or "M"

    @property
    def credit_status(self) -> str:
        ratio = self.credit_score / self.credit_max
        if ratio >= 0.85:
            return "Excellent"
        if ratio >= 0.70:
            return "Good Standing"
        if ratio >= 0.55:
            return "Fair"
        return "Needs Attention"


@dataclass
class Activity:
    name: str
    subtitle: str
    amount: int
    kind: Literal["in", "out", "bank"]
    icon: str


# ──────────────────────────────────────────────
# Agentic helpers (simple reactive agents)
# ──────────────────────────────────────────────

class GreetingAgent:
    """Time-aware greeting generator."""

    @staticmethod
    def generate(name: str) -> str:
        hour = dt.datetime.now().hour
        if hour < 12:
            word = "Good morning"
        elif hour < 17:
            word = "Good afternoon"
        else:
            word = "Good evening"
        return f"{word}, {name}"


class LanguageAgent:
    """Handles multi-language UI strings."""

    STRINGS = {
        "en": {
            "overview": "Overview",
            "welcome_sub": "Here's how your group is doing today.",
            "send": "Send money",
            "request": "Request funds",
            "repay": "Repay loan",
            "topup": "Top up wallet",
            "credit_score": "Credit Score",
            "on_time": "On-Time",
            "credit": "Credit",
            "history": "History",
            "wallet": "E-Wallet Balance",
            "members": "Active Members",
            "recent": "Recent activity",
            "view_all": "View all",
            "lang_title": "Language Support",
            "lang_desc": "Choose the language you'd like your dashboard, receipts, and notifications displayed in.",
            "logout": "Log Out",
            "signed_in": "Signed in as",
        },
        "sw": {
            "overview": "Muhtasari",
            "welcome_sub": "Hivi ndivyo kikundi chako kinavyofanya leo.",
            "send": "Tuma pesa",
            "request": "Omba fedha",
            "repay": "Lipa mkopo",
            "topup": "Ongeza salio",
            "credit_score": "Alama ya Mkopo",
            "on_time": "Kwa Wakati",
            "credit": "Mkopo",
            "history": "Historia",
            "wallet": "Salio la E-Wallet",
            "members": "Wanachama Hai",
            "recent": "Shughuli za hivi karibuni",
            "view_all": "Angalia zote",
            "lang_title": "Msaada wa Lugha",
            "lang_desc": "Chagua lugha unayotaka dashibodi, risiti na arifa zionyeshewe.",
            "logout": "Toka",
            "signed_in": "Umeingia kama",
        },
        "fr": {
            "overview": "Aperçu",
            "welcome_sub": "Voici comment se porte votre groupe aujourd'hui.",
            "send": "Envoyer de l'argent",
            "request": "Demander des fonds",
            "repay": "Rembourser le prêt",
            "topup": "Recharger le portefeuille",
            "credit_score": "Score de crédit",
            "on_time": "À temps",
            "credit": "Crédit",
            "history": "Historique",
            "wallet": "Solde E-Wallet",
            "members": "Membres actifs",
            "recent": "Activité récente",
            "view_all": "Voir tout",
            "lang_title": "Support linguistique",
            "lang_desc": "Choisissez la langue d'affichage de votre tableau de bord, reçus et notifications.",
            "logout": "Déconnexion",
            "signed_in": "Connecté en tant que",
        },
    }

    def t(self, key: str, lang: str) -> str:
        return self.STRINGS.get(lang, self.STRINGS["en"]).get(key, key)


# ──────────────────────────────────────────────
# Session & state management
# ──────────────────────────────────────────────

def init_session() -> None:
    if "member" not in st.session_state:
        st.session_state.member = MemberSession(username="Amina")
    if "activities" not in st.session_state:
        st.session_state.activities = [
            Activity("Monthly contribution", "via M-Pesa · 2 hrs ago", 5_000, "in", "↓"),
            Activity("Loan repayment", "Installment 4 of 6 · yesterday", -3_200, "out", "↻"),
            Activity("Bank transfer received", "Co-operative Bank · 3 days ago", 15_000, "bank", "🏦"),
        ]
    if "lang_agent" not in st.session_state:
        st.session_state.lang_agent = LanguageAgent()


def logout() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# ──────────────────────────────────────────────
# UI components
# ──────────────────────────────────────────────

def render_gauge(score: int, max_score: int) -> go.Figure:
    pct = score / max_score
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": f" / {max_score}", "font": {"size": 28}},
            gauge={
                "axis": {"range": [0, max_score], "tickwidth": 1},
                "bar": {"color": "#B08F3C"},
                "bgcolor": "#f0f0f0",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, max_score * 0.55], "color": "#f8d7da"},
                    {"range": [max_score * 0.55, max_score * 0.70], "color": "#fff3cd"},
                    {"range": [max_score * 0.70, max_score], "color": "#d4edda"},
                ],
                "threshold": {
                    "line": {"color": "#E8C97A", "width": 4},
                    "thickness": 0.8,
                    "value": score,
                },
            },
            title={"text": ""},
        )
    )
    fig.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#333"},
    )
    return fig


def render_sidebar(member: MemberSession, t: LanguageAgent) -> None:
    with st.sidebar:
        st.markdown("### MAU")
        st.caption("Mali Access Union  \nby Syllogism Technology Africa")
        st.divider()

        pages = [
            ("Overview", "overview"),
            ("Credit", "credit"),
            ("E-Wallet", "ewallet"),
            ("Members", "members"),
            ("Payments", "payments"),
            ("Language Support", "language"),
            ("Re-Payments", "repayments"),
            ("My Profile", "profile"),
        ]
        for label, key in pages:
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.active_page = key

        st.divider()
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(
                f"""
                <div style="width:40px;height:40px;border-radius:50%;
                background:#B08F3C;color:white;display:flex;align-items:center;
                justify-content:center;font-weight:700;font-size:18px;">
                {member.initial}</div>
                """,
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(f"**{member.username}**  \n{member.role}")

        if st.button(t.t("logout", member.language), use_container_width=True, type="primary"):
            logout()


def render_topbar(member: MemberSession, t: LanguageAgent) -> None:
    col1, col2, col3 = st.columns([6, 2, 1])
    with col1:
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:12px;">
                <span style="background:#e8f5e9;color:#2e7d32;padding:4px 12px;
                border-radius:20px;font-size:13px;">● {t.t('signed_in', member.language)} {member.username}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div style="text-align:right;padding-top:6px;">
                🔔 <span style="background:red;color:white;border-radius:50%;
                padding:1px 6px;font-size:11px;">3</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
            <div style="width:36px;height:36px;border-radius:50%;background:#B08F3C;
            color:white;display:flex;align-items:center;justify-content:center;
            font-weight:700;margin-left:auto;">{member.initial}</div>
            """,
            unsafe_allow_html=True,
        )


def render_actions(t: LanguageAgent, lang: str) -> None:
    c1, c2, c3, c4 = st.columns(4)
    actions = [
        (c1, "↗", t.t("send", lang)),
        (c2, "↙", t.t("request", lang)),
        (c3, "↻", t.t("repay", lang)),
        (c4, "💳", t.t("topup", lang)),
    ]
    for col, icon, label in actions:
        with col:
            if st.button(f"{icon}  {label}", use_container_width=True):
                st.toast(f"{label} — coming soon", icon="ℹ️")


def render_metric_cards(member: MemberSession, t: LanguageAgent) -> None:
    c1, c2 = st.columns(2)
    with c1:
        st.metric(
            label=t.t("wallet", member.language),
            value=f"KES {member.wallet_balance:,}",
            delta=f"KES {member.wallet_week_delta:,} this week",
        )
    with c2:
        st.metric(
            label=t.t("members", member.language),
            value=f"{member.active_members} / {member.total_members}",
            delta=f"{member.new_members_month} new this month",
        )


def render_activity(activities: list[Activity], t: LanguageAgent, lang: str) -> None:
    st.subheader(t.t("recent", lang))
    st.caption("Your latest contributions and repayments across the group.")
    for act in activities:
        color = "#2e7d32" if act.amount > 0 else "#c62828"
        sign = "+" if act.amount > 0 else ""
        st.markdown(
            f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
            padding:12px 0;border-bottom:1px solid #eee;">
                <div style="display:flex;gap:12px;align-items:center;">
                    <div style="width:36px;height:36px;border-radius:50%;background:#f5f5f5;
                    display:flex;align-items:center;justify-content:center;font-size:16px;">
                    {act.icon}</div>
                    <div>
                        <div style="font-weight:600;">{act.name}</div>
                        <div style="font-size:13px;color:#666;">{act.subtitle}</div>
                    </div>
                </div>
                <div style="font-weight:700;color:{color};">{sign} KES {abs(act.amount):,}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_language_selector(member: MemberSession, t: LanguageAgent) -> None:
    st.subheader(t.t("lang_title", member.language))
    st.caption(t.t("lang_desc", member.language))
    cols = st.columns(3)
    labels = {"en": "English", "sw": "Kiswahili", "fr": "Français"}
    for i, (code, label) in enumerate(labels.items()):
        with cols[i]:
            is_active = member.language == code
            btn_type = "primary" if is_active else "secondary"
            prefix = "✓ " if is_active else ""
            if st.button(f"{prefix}{label}", key=f"lang_{code}", use_container_width=True, type=btn_type):
                st.session_state.member.language = code
                st.rerun()


# ──────────────────────────────────────────────
# Main app
# ──────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="MAU · Overview",
        page_icon="🏦",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS for modern look
    st.markdown(
        """
        <style>
        .stApp { background: #faf9f6; }
        [data-testid="stSidebar"] { background: #1a1a1a; color: white; }
        [data-testid="stSidebar"] * { color: #f0f0f0 !important; }
        [data-testid="stSidebar"] .stButton > button {
            background: transparent; border: 1px solid #333; color: #ddd !important;
            text-align: left; justify-content: flex-start;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            background: #2a2a2a; border-color: #B08F3C;
        }
        div[data-testid="stMetric"] {
            background: white; padding: 16px 20px; border-radius: 12px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    init_session()
    member: MemberSession = st.session_state.member
    t: LanguageAgent = st.session_state.lang_agent
    activities: list[Activity] = st.session_state.activities

    render_sidebar(member, t)
    render_topbar(member, t)

    # Header
    greeting = GreetingAgent.generate(member.username)
    today = dt.datetime.now().strftime("%A, %B %d")
    st.markdown(f"### {t.t('overview', member.language)}")
    st.markdown(f"## {greeting}")
    st.caption(t.t("welcome_sub", member.language))
    st.caption(f"📅 {today}")

    st.write("")
    render_actions(t, member.language)
    st.write("")

    # Credit score + metrics
    left, right = st.columns([1.4, 1])
    with left:
        st.markdown(
            f"""
            <div style="background:white;border-radius:16px;padding:20px 24px;
            box-shadow:0 1px 6px rgba(0,0,0,0.07);">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-weight:600;">{t.t('credit_score', member.language)}</span>
                    <span style="background:#e8f5e9;color:#2e7d32;padding:3px 10px;
                    border-radius:12px;font-size:13px;">{member.credit_status}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.plotly_chart(render_gauge(member.credit_score, member.credit_max), use_container_width=True)
        m1, m2, m3 = st.columns(3)
        m1.metric(t.t("on_time", member.language), f"{member.on_time_pct:.0f}%")
        m2.metric(t.t("credit", member.language), f"KES {member.credit_limit // 1000}K")
        m3.metric(t.t("history", member.language), f"{member.history_years} yrs")
        st.caption(f"Updated today · **+{member.score_delta} pts** since last month")

    with right:
        render_metric_cards(member, t)

    st.write("")
    render_activity(activities, t, member.language)

    st.markdown("---")
    render_language_selector(member, t)


if __name__ == "__main__":
    main()
