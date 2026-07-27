
"""
Mwarokin Estates — Advanced Staff Portal
Modern agentic Python rewrite (Streamlit + SQLite + Plotly)
Fully functional: sidebar nav, overview, maintenance, rentals, leases,
analytics charts, preferences, live CRUD, agent insights, search, toasts.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─── Config ────────────────────────────────────────────────────────────────
DB_PATH = Path("mwarokin_staff_portal.db")
CURRENCY = "KES"

# ─── Database ──────────────────────────────────────────────────────────────
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS maintenance (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                unit        TEXT NOT NULL,
                priority    TEXT CHECK(priority IN ('High','Medium','Low')),
                status      TEXT CHECK(status IN ('open','in-progress','resolved')),
                assigned    TEXT,
                date        TEXT NOT NULL,
                notes       TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS payments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant      TEXT NOT NULL,
                unit        TEXT NOT NULL,
                amount      REAL NOT NULL,
                date        TEXT NOT NULL,
                status      TEXT CHECK(status IN ('paid','pending','overdue'))
            );
            CREATE TABLE IF NOT EXISTS leases (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                property    TEXT NOT NULL,
                tenant      TEXT NOT NULL,
                start_date  TEXT NOT NULL,
                end_date    TEXT NOT NULL,
                rent        REAL NOT NULL,
                status      TEXT CHECK(status IN ('active','expiring','expired'))
            );
            CREATE TABLE IF NOT EXISTS activity (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                kind        TEXT,
                title       TEXT,
                detail      TEXT,
                created_at  TEXT
            );
            CREATE TABLE IF NOT EXISTS preferences (
                key         TEXT PRIMARY KEY,
                value       INTEGER DEFAULT 0
            );
            """
        )
        conn.commit()


def seed_if_empty() -> None:
    with get_conn() as conn:
        if conn.execute("SELECT COUNT(*) FROM maintenance").fetchone()[0] > 0:
            return

        maint = [
            ("Leaking faucet in kitchen", "Unit 90", "High", "open", "John Kamau", "2026-07-05"),
            ("HVAC not cooling", "Unit 102", "Medium", "in-progress", "David Mwangi", "2026-07-04"),
            ("Broken window glass", "Unit 45", "Low", "open", "Peter Ochieng", "2026-07-03"),
            ("Electrical outlet sparking", "Unit 12", "High", "in-progress", "Mary Wanjiru", "2026-07-02"),
            ("Garden irrigation repair", "Common Area", "Medium", "resolved", "Grace Akinyi", "2026-06-30"),
        ]
        conn.executemany(
            "INSERT INTO maintenance (title, unit, priority, status, assigned, date) VALUES (?,?,?,?,?,?)",
            maint,
        )

        pays = [
            ("Michael Brown", "159 Oak Lane", 2500, "2026-07-01", "paid"),
            ("Robert Johnson", "567 Elm St", 1800, "2026-06-28", "paid"),
            ("Sarah Kimani", "Unit 102", 2100, "2026-06-25", "pending"),
            ("Emily Wanjiru", "Unit 90", 1200, "2026-06-20", "overdue"),
            ("David Ochieng", "Unit 45", 850, "2026-06-15", "overdue"),
        ]
        conn.executemany(
            "INSERT INTO payments (tenant, unit, amount, date, status) VALUES (?,?,?,?,?)",
            pays,
        )

        leases = [
            ("Boston Ave", "Michael Brown", "2026-01-01", "2026-12-31", 2500, "active"),
            ("Boylston St · Unit 1", "Robert Johnson", "2026-03-15", "2027-03-14", 1800, "active"),
            ("Unit 102", "Sarah Kimani", "2025-07-01", "2026-06-30", 2100, "expiring"),
            ("Unit 90", "Emily Wanjiru", "2025-08-01", "2026-07-31", 1200, "active"),
            ("Skyline Penthouse", "David Ochieng", "2026-02-01", "2027-01-31", 4500, "active"),
            ("Garden Lane Home", "Grace Akinyi", "2025-05-01", "2026-04-30", 2100, "expired"),
        ]
        conn.executemany(
            "INSERT INTO leases (property, tenant, start_date, end_date, rent, status) VALUES (?,?,?,?,?,?)",
            leases,
        )

        acts = [
            ("maintenance", "Maintenance request #102", "Leaking faucet in Unit 90 – assigned to John Kamau", "2026-07-26T13:00:00"),
            ("payment", "Rent payment received", "$2,500 from Michael Brown for 159 Oak Lane", "2026-07-26T10:00:00"),
            ("lease", "Lease renewal", "Sarah Kimani renewed lease for Unit 102 for 12 months", "2026-07-25T18:00:00"),
        ]
        conn.executemany(
            "INSERT INTO activity (kind, title, detail, created_at) VALUES (?,?,?,?)",
            acts,
        )

        prefs = [("dark_mode", 1), ("email_notifications", 1), ("auto_assign", 0)]
        conn.executemany("INSERT OR REPLACE INTO preferences (key, value) VALUES (?,?)", prefs)
        conn.commit()


def log_activity(kind: str, title: str, detail: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO activity (kind, title, detail, created_at) VALUES (?,?,?,?)",
            (kind, title, detail, datetime.now().isoformat()),
        )
        conn.commit()


# ─── Data accessors ────────────────────────────────────────────────────────
def df_maintenance(search: str = "") -> pd.DataFrame:
    q = "SELECT * FROM maintenance ORDER BY date DESC"
    with get_conn() as conn:
        df = pd.read_sql_query(q, conn)
    if search:
        mask = df.apply(lambda r: search.lower() in " ".join(map(str, r.values)).lower(), axis=1)
        df = df[mask]
    return df


def df_payments() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query("SELECT * FROM payments ORDER BY date DESC", conn)


def df_leases() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query("SELECT * FROM leases ORDER BY end_date", conn)


def df_activity(limit: int = 10) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT * FROM activity ORDER BY created_at DESC LIMIT ?", conn, params=(limit,)
        )


def get_pref(key: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM preferences WHERE key=?", (key,)).fetchone()
    return bool(row["value"]) if row else False


def set_pref(key: str, value: bool) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO preferences (key, value) VALUES (?,?)",
            (key, int(value)),
        )
        conn.commit()


# ─── Agentic insights ──────────────────────────────────────────────────────
def agent_insights() -> list[str]:
    insights: list[str] = []
    m = df_maintenance()
    open_high = m[(m["status"] != "resolved") & (m["priority"] == "High")]
    if not open_high.empty:
        for _, r in open_high.iterrows():
            insights.append(
                f"🔧 Urgent: {r['title']} ({r['unit']}) — {r['status']} · assigned to {r['assigned']}"
            )
    p = df_payments()
    overdue = p[p["status"] == "overdue"]
    if not overdue.empty:
        total = overdue["amount"].sum()
        insights.append(f"💰 {len(overdue)} overdue payment(s) totaling {CURRENCY} {total:,.0f}")
    l = df_leases()
    now = datetime.now().date()
    for _, r in l.iterrows():
        end = datetime.strptime(r["end_date"], "%Y-%m-%d").date()
        days = (end - now).days
        if 0 <= days <= 30:
            insights.append(f"📄 Lease expiring soon: {r['tenant']} @ {r['property']} ({days} days)")
        elif days < 0 and r["status"] != "expired":
            insights.append(f"⚠️ Expired lease still marked active: {r['tenant']} @ {r['property']}")
    if not insights:
        insights.append("✅ All systems nominal — no urgent actions.")
    return insights


# ─── Helpers ───────────────────────────────────────────────────────────────
def fmt_money(n: float) -> str:
    return f"{CURRENCY} {n:,.0f}"


def status_badge(status: str) -> str:
    colors = {
        "open": "#e74c3c",
        "in-progress": "#f39c12",
        "resolved": "#2ecc71",
        "paid": "#2ecc71",
        "pending": "#f39c12",
        "overdue": "#e74c3c",
        "active": "#2ecc71",
        "expiring": "#f39c12",
        "expired": "#e74c3c",
    }
    c = colors.get(status, "#9aa4bf")
    return f'<span style="background:{c}22;color:{c};padding:2px 10px;border-radius:12px;font-size:0.75rem;font-weight:600;">{status.replace("-"," ").title()}</span>'


# ─── App setup ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mwarokin Estates · Staff Portal",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700&family=DM+Sans:wght@400;500;600&display=swap');
    .stApp { background: #0f1629; color: #e8e6e3; }
    h1, h2, h3, h4 { font-family: 'Syne', sans-serif !important; }
    section[data-testid="stSidebar"] {
        background: #0a0f1c; border-right: 1px solid #1e2740;
    }
    div[data-testid="stMetric"] {
        background: #151c2e; border: 1px solid #1e2740; border-radius: 12px;
        padding: 1rem 1.2rem;
    }
    .activity-row {
        display:flex; align-items:center; gap:12px; padding:0.7rem 0;
        border-bottom:1px solid #1e2740;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

init_db()
seed_if_empty()

# ─── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:1.5rem;">
            <div style="width:40px;height:40px;background:linear-gradient(135deg,#c9a03d,#e8c547);
                        border-radius:10px;display:flex;align-items:center;justify-content:center;
                        font-size:1.2rem;">👑</div>
            <div>
                <div style="font-family:'Syne';font-weight:700;font-size:1.15rem;color:#e8e6e3;">
                    Mwarokin<span style="color:#c9a03d;">Estates</span>
                </div>
                <div style="font-size:0.7rem;color:#9aa4bf;">Advanced Portal</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Navigation",
        [
            "Overview",
            "Maintenance",
            "Rentals",
            "Leases",
            "Analytics",
            "Preferences",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:36px;height:36px;border-radius:50%;background:#c9a03d;
                        color:#0f1629;display:flex;align-items:center;justify-content:center;
                        font-weight:700;font-size:0.85rem;">JD</div>
            <div>
                <div style="font-weight:600;font-size:0.9rem;">James Duncan</div>
                <div style="font-size:0.75rem;color:#9aa4bf;">Property Manager</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ─── Global search ─────────────────────────────────────────────────────────
search = st.text_input("🔍 Search maintenance, tenants…", placeholder="Type to filter…", key="global_search")

# ─── OVERVIEW ──────────────────────────────────────────────────────────────
if page == "Overview":
    st.markdown("## Advanced <span style='color:#c9a03d;'>Overview</span>", unsafe_allow_html=True)
    st.caption("📍 Mwarokin Estates · Premium Tools")

    m = df_maintenance()
    p = df_payments()
    l = df_leases()

    open_maint = len(m[m["status"] != "resolved"])
    collected = p[p["status"] == "paid"]["amount"].sum()
    active_leases = len(l[l["status"] == "active"])
    occupancy = 92  # demo static; can be computed from units if available

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Open Maintenance", open_maint, delta=None)
    c2.metric("Monthly Rent Collected", fmt_money(collected))
    c3.metric("Active Leases", active_leases)
    c4.metric("Occupancy Rate", f"{occupancy}%")

    st.markdown("### Quick Actions")
    qa1, qa2, qa3 = st.columns(3)
    with qa1:
        if st.button("➕ New Maintenance Request", use_container_width=True, type="primary"):
            st.session_state["force_page"] = "Maintenance"
            st.rerun()
    with qa2:
        if st.button("🧾 Record Payment", use_container_width=True):
            st.session_state["force_page"] = "Rentals"
            st.rerun()
    with qa3:
        if st.button("📝 New Lease", use_container_width=True):
            st.session_state["force_page"] = "Leases"
            st.rerun()

    st.markdown("### 🧠 Agent Insights")
    for tip in agent_insights():
        st.markdown(f"- {tip}")

    st.markdown("### Recent Activity")
    acts = df_activity()
    icon_map = {"maintenance": "🔧", "payment": "💰", "lease": "📄"}
    for _, a in acts.iterrows():
        icon = icon_map.get(a["kind"], "•")
        ts = a["created_at"][:16].replace("T", " ")
        st.markdown(
            f"""
            <div class="activity-row">
                <div style="width:36px;height:36px;border-radius:50%;background:rgba(201,160,61,0.15);
                            display:flex;align-items:center;justify-content:center;">{icon}</div>
                <div style="flex:1;">
                    <strong>{a['title']}</strong><br>
                    <span style="font-size:0.8rem;color:#9aa4bf;">{a['detail']}</span>
                </div>
                <span style="font-size:0.7rem;color:#6b7280;">{ts}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ─── MAINTENANCE ───────────────────────────────────────────────────────────
elif page == "Maintenance":
    st.markdown("## Maintenance <span style='color:#c9a03d;'>Requests</span>", unsafe_allow_html=True)

    with st.expander("➕ New Maintenance Request", expanded=False):
        with st.form("new_maint"):
            title = st.text_input("Title")
            unit = st.text_input("Unit / Location")
            col1, col2 = st.columns(2)
            with col1:
                priority = st.selectbox("Priority", ["High", "Medium", "Low"])
            with col2:
                status = st.selectbox("Status", ["open", "in-progress", "resolved"])
            assigned = st.text_input("Assigned to", value="Unassigned")
            notes = st.text_area("Notes", height=80)
            if st.form_submit_button("Create Request", type="primary"):
                if title and unit:
                    with get_conn() as conn:
                        conn.execute(
                            "INSERT INTO maintenance (title, unit, priority, status, assigned, date, notes) VALUES (?,?,?,?,?,?,?)",
                            (title, unit, priority, status, assigned, datetime.now().strftime("%Y-%m-%d"), notes),
                        )
                        conn.commit()
                    log_activity("maintenance", f"New request: {title}", f"{unit} · {priority} · {assigned}")
                    st.success("Request created")
                    st.rerun()
                else:
                    st.error("Title and Unit are required")

    df = df_maintenance(search)
    if df.empty:
        st.info("No maintenance requests match.")
    else:
        for _, r in df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([3, 1, 1.2])
                with c1:
                    st.markdown(f"**{r['title']}**  <span style='color:#9aa4bf;font-size:0.8rem;'>#{r['id']}</span>", unsafe_allow_html=True)
                    st.caption(f"🏢 {r['unit']}  ·  👤 {r['assigned']}  ·  📅 {r['date']}  ·  🚩 {r['priority']}")
                with c2:
                    st.markdown(status_badge(r["status"]), unsafe_allow_html=True)
                with c3:
                    new_status = st.selectbox(
                        "Update",
                        ["open", "in-progress", "resolved"],
                        index=["open", "in-progress", "resolved"].index(r["status"]),
                        key=f"st_{r['id']}",
                        label_visibility="collapsed",
                    )
                    if new_status != r["status"]:
                        with get_conn() as conn:
                            conn.execute("UPDATE maintenance SET status=? WHERE id=?", (new_status, r["id"]))
                            conn.commit()
                        log_activity("maintenance", f"Status updated #{r['id']}", f"{r['title']} → {new_status}")
                        st.rerun()
                st.divider()

# ─── RENTALS ───────────────────────────────────────────────────────────────
elif page == "Rentals":
    st.markdown("## Rent <span style='color:#c9a03d;'>Collection</span>", unsafe_allow_html=True)

    with st.expander("➕ Record Payment", expanded=False):
        with st.form("new_pay"):
            tenant = st.text_input("Tenant")
            unit = st.text_input("Unit")
            amount = st.number_input("Amount", min_value=0.0, step=100.0)
            status = st.selectbox("Status", ["paid", "pending", "overdue"])
            if st.form_submit_button("Record", type="primary"):
                if tenant and unit and amount > 0:
                    with get_conn() as conn:
                        conn.execute(
                            "INSERT INTO payments (tenant, unit, amount, date, status) VALUES (?,?,?,?,?)",
                            (tenant, unit, amount, datetime.now().strftime("%Y-%m-%d"), status),
                        )
                        conn.commit()
                    log_activity("payment", "Payment recorded", f"{fmt_money(amount)} from {tenant} · {unit}")
                    st.success("Payment recorded")
                    st.rerun()
                else:
                    st.error("Fill all fields")

    p = df_payments()
    left, right = st.columns(2)
    with left:
        st.subheader("✅ Recent Payments")
        paid = p[p["status"] == "paid"]
        if paid.empty:
            st.caption("No paid records")
        else:
            for _, r in paid.iterrows():
                st.markdown(
                    f"**{r['tenant']}**  \n"
                    f"<span style='color:#9aa4bf;font-size:0.8rem;'>{r['unit']} · {r['date']}</span>  "
                    f"<span style='float:right;color:#2ecc71;font-weight:600;'>{fmt_money(r['amount'])}</span>",
                    unsafe_allow_html=True,
                )
                st.divider()
    with right:
        st.subheader("⚠️ Overdue / Pending")
        bad = p[p["status"].isin(["pending", "overdue"])]
        if bad.empty:
            st.caption("All clear")
        else:
            for _, r in bad.iterrows():
                st.markdown(
                    f"**{r['tenant']}**  \n"
                    f"<span style='color:#9aa4bf;font-size:0.8rem;'>{r['unit']} · {r['date']}</span>  "
                    f"<span style='float:right;'>{fmt_money(r['amount'])} {status_badge(r['status'])}</span>",
                    unsafe_allow_html=True,
                )
                st.divider()

# ─── LEASES ────────────────────────────────────────────────────────────────
elif page == "Leases":
    st.markdown("## Lease <span style='color:#c9a03d;'>Management</span>", unsafe_allow_html=True)

    with st.expander("➕ New Lease", expanded=False):
        with st.form("new_lease"):
            prop = st.text_input("Property")
            tenant = st.text_input("Tenant")
            c1, c2 = st.columns(2)
            with c1:
                start = st.date_input("Start date")
            with c2:
                end = st.date_input("End date", value=datetime.now().date() + timedelta(days=365))
            rent = st.number_input("Monthly rent", min_value=0.0, step=100.0)
            if st.form_submit_button("Create Lease", type="primary"):
                if prop and tenant and rent > 0:
                    days_left = (end - datetime.now().date()).days
                    status = "expired" if days_left < 0 else ("expiring" if days_left < 30 else "active")
                    with get_conn() as conn:
                        conn.execute(
                            "INSERT INTO leases (property, tenant, start_date, end_date, rent, status) VALUES (?,?,?,?,?,?)",
                            (prop, tenant, start.isoformat(), end.isoformat(), rent, status),
                        )
                        conn.commit()
                    log_activity("lease", f"New lease: {prop}", f"{tenant} · {fmt_money(rent)}/mo")
                    st.success("Lease created")
                    st.rerun()
                else:
                    st.error("Fill required fields")

    leases = df_leases()
    now = datetime.now().date()
    cols = st.columns(2)
    for idx, (_, r) in enumerate(leases.iterrows()):
        end = datetime.strptime(r["end_date"], "%Y-%m-%d").date()
        days = (end - now).days
        with cols[idx % 2]:
            st.markdown(
                f"""
                <div style="background:#151c2e;border:1px solid #1e2740;border-radius:12px;padding:1rem;margin-bottom:1rem;">
                    <div style="display:flex;justify-content:space-between;">
                        <strong>{r['property']}</strong>
                        {status_badge(r['status'])}
                    </div>
                    <div style="color:#9aa4bf;font-size:0.85rem;margin:0.4rem 0;">{r['tenant']}</div>
                    <div style="font-size:0.9rem;">{fmt_money(r['rent'])} / mo</div>
                    <div style="font-size:0.8rem;color:#9aa4bf;">{r['start_date']} → {r['end_date']}</div>
                    <div style="margin-top:0.5rem;font-size:0.8rem;">
                        {"Expired" if days < 0 else f"{days} days remaining"}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ─── ANALYTICS ─────────────────────────────────────────────────────────────
elif page == "Analytics":
    st.markdown("## Financial <span style='color:#c9a03d;'>Analytics</span>", unsafe_allow_html=True)

    # Demo series (can be replaced by real aggregates)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    revenue = [32000, 34000, 36000, 38000, 42000, 48200]
    occupancy = [85, 88, 90, 89, 91, 92]
    costs = {"Plumbing": 3200, "Electrical": 1800, "HVAC": 1200, "Landscaping": 800, "Other": 600}

    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure(
            data=[
                go.Bar(
                    x=months,
                    y=revenue,
                    marker_color="rgba(201,160,61,0.7)",
                    marker_line_color="#c9a03d",
                    marker_line_width=2,
                )
            ]
        )
        fig.update_layout(
            title="Monthly Rent Revenue",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#9aa4bf",
            height=320,
            margin=dict(t=40, b=20, l=20, r=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig2 = go.Figure(
            data=[
                go.Pie(
                    labels=list(costs.keys()),
                    values=list(costs.values()),
                    hole=0.65,
                    marker_colors=["#c9a03d", "#5dade2", "#58d68d", "#af7ac5", "#e74c3c"],
                )
            ]
        )
        fig2.update_layout(
            title="Maintenance Costs",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#9aa4bf",
            height=320,
            margin=dict(t=40, b=20, l=20, r=20),
            showlegend=True,
        )
        st.plotly_chart(fig2, use_container_width=True)

    fig3 = go.Figure()
    fig3.add_trace(
        go.Scatter(
            x=months,
            y=occupancy,
            mode="lines+markers",
            fill="tozeroy",
            line=dict(color="#c9a03d", width=3),
            marker=dict(size=8, color="#c9a03d"),
            fillcolor="rgba(201,160,61,0.15)",
        )
    )
    fig3.update_layout(
        title="Occupancy & Vacancy Trends",
        yaxis=dict(range=[70, 100]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#9aa4bf",
        height=280,
        margin=dict(t=40, b=20, l=20, r=20),
    )
    st.plotly_chart(fig3, use_container_width=True)

# ─── PREFERENCES ───────────────────────────────────────────────────────────
elif page == "Preferences":
    st.markdown("## Preferences", unsafe_allow_html=True)

    dark = st.toggle("Dark Mode", value=get_pref("dark_mode"))
    email = st.toggle("Email Notifications", value=get_pref("email_notifications"))
    auto = st.toggle("Auto-assign Maintenance", value=get_pref("auto_assign"))

    if st.button("Save Preferences", type="primary"):
        set_pref("dark_mode", dark)
        set_pref("email_notifications", email)
        set_pref("auto_assign", auto)
        st.success("Preferences saved")
        st.toast("Preferences updated", icon="✅")

# ─── Footer ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="text-align:center;color:#6b7280;font-size:0.8rem;margin-top:2.5rem;padding-top:1rem;border-top:1px solid #1e2740;">
        Mwarokin Estates © 2026 · Advanced Portal. Powered by
        <span style="color:#c9a03d;">Syllogism Technology Africa</span>
    </div>
    """,
    unsafe_allow_html=True,
)
