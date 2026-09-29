Here’s a complete **FastAPI** backend that powers the Landlord Payments Dashboard with real, mutable data and working actions.

```python
"""
Mwarokin Estates – Landlord Payments Dashboard
Modern FastAPI backend with real functionality.

Run:
    pip install fastapi uvicorn[standard] pydantic
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Open: http://127.0.0.1:8000
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Annotated, Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, computed_field

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mwarokin Estates – Landlord Payments Dashboard",
    description="Real backend for collection stats, payments, reminders and activity.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Enums & models
# ---------------------------------------------------------------------------

class PaymentStatus(str, Enum):
    paid = "paid"
    pending = "pending"
    overdue = "overdue"
    partial = "partial"


class Urgency(str, Enum):
    urgent = "urgent"
    soon = "soon"
    overdue = "overdue"
    normal = "normal"


class Landlord(BaseModel):
    id: int
    name: str
    initials: str
    property: str
    units: int
    monthly_rent: int
    service: str


class Payment(BaseModel):
    id: str
    landlord_id: int
    amount_due: int
    amount_paid: int
    status: PaymentStatus
    due_date: str  # display e.g. "Apr 5, 2025"
    due_date_iso: str  # "2025-04-05" for sorting


class PaymentRow(BaseModel):
    """Joined landlord + payment for the table."""
    payment_id: str
    landlord_id: int
    name: str
    initials: str
    property: str
    units: int
    amount_due: int
    amount_paid: int
    status: PaymentStatus
    due_date: str


class DashboardStats(BaseModel):
    total_collected: int
    total_pending: int
    total_overdue: int
    active_landlords: int
    total_units: int
    collection_rate: int
    pending_count: int
    overdue_count: int
    month_label: str


class UpcomingDue(BaseModel):
    landlord: str
    property: str
    amount: int
    due: str
    urgency: Urgency


class Activity(BaseModel):
    id: str
    icon: str
    icon_color: str
    title: str
    desc: str
    time: str
    created_at: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


class ServiceItem(BaseModel):
    icon: str
    label: str


class RecordPaymentRequest(BaseModel):
    landlord_id: int
    amount: int = Field(..., gt=0)
    note: str | None = None


class SendReminderRequest(BaseModel):
    status_filter: PaymentStatus | None = PaymentStatus.pending  # default: pending


# ---------------------------------------------------------------------------
# Seed data (mutable)
# ---------------------------------------------------------------------------

LANDLORDS: dict[int, Landlord] = {
    1: Landlord(id=1, name="Grace Wanjiku", initials="GW", property="Kilimani Court",
                units=12, monthly_rent=240_000, service="Full Management"),
    2: Landlord(id=2, name="James Mwangi", initials="JM", property="Westlands Heights",
                units=8, monthly_rent=168_000, service="Rent Collection"),
    3: Landlord(id=3, name="Amina Hassan", initials="AH", property="South B Apartments",
                units=20, monthly_rent=360_000, service="Full Management"),
    4: Landlord(id=4, name="Peter Njoroge", initials="PN", property="Kasarani Villas",
                units=6, monthly_rent=96_000, service="Maintenance Only"),
    5: Landlord(id=5, name="Sarah Kilonzo", initials="SK", property="Lavington Suites",
                units=15, monthly_rent=450_000, service="Full Management"),
    6: Landlord(id=6, name="David Ochieng", initials="DO", property="Eastleigh Plaza",
                units=30, monthly_rent=600_000, service="Revenue Sharing"),
    7: Landlord(id=7, name="Lucy Wambui", initials="LW", property="Karen Cottages",
                units=5, monthly_rent=75_000, service="Full Management"),
    8: Landlord(id=8, name="Michael Kariuki", initials="MK", property="Runda Gardens",
                units=10, monthly_rent=300_000, service="Full Management"),
    9: Landlord(id=9, name="Fatima Noor", initials="FN", property="Parklands Flats",
                units=18, monthly_rent=270_000, service="Rent Collection"),
    10: Landlord(id=10, name="Robert Maina", initials="RM", property="Embakasi Estate",
                 units=25, monthly_rent=375_000, service="Revenue Sharing"),
    11: Landlord(id=11, name="Catherine Njeri", initials="CN", property="Donholm Apartments",
                 units=14, monthly_rent=210_000, service="Full Management"),
    12: Landlord(id=12, name="Ali Mohamed", initials="AM", property="Mombasa Road Plaza",
                 units=22, monthly_rent=440_000, service="Full Management"),
}

PAYMENTS: dict[str, Payment] = {}

def _seed_payments() -> None:
    seeds = [
        (1, 240_000, 240_000, "paid", "2025-04-05", "Apr 5, 2025"),
        (2, 168_000, 0, "pending", "2025-04-10", "Apr 10, 2025"),
        (3, 360_000, 360_000, "paid", "2025-04-03", "Apr 3, 2025"),
        (4, 96_000, 0, "overdue", "2025-04-01", "Apr 1, 2025"),
        (5, 450_000, 450_000, "paid", "2025-04-07", "Apr 7, 2025"),
        (6, 600_000, 300_000, "partial", "2025-04-15", "Apr 15, 2025"),
        (7, 75_000, 75_000, "paid", "2025-04-02", "Apr 2, 2025"),
        (8, 300_000, 0, "pending", "2025-04-12", "Apr 12, 2025"),
        (9, 270_000, 270_000, "paid", "2025-04-06", "Apr 6, 2025"),
        (10, 375_000, 0, "overdue", "2025-04-01", "Apr 1, 2025"),
        (11, 210_000, 210_000, "paid", "2025-04-09", "Apr 9, 2025"),
        (12, 440_000, 0, "pending", "2025-04-18", "Apr 18, 2025"),
    ]
    for lid, due, paid, status, iso, display in seeds:
        pid = str(uuid4())
        PAYMENTS[pid] = Payment(
            id=pid,
            landlord_id=lid,
            amount_due=due,
            amount_paid=paid,
            status=PaymentStatus(status),
            due_date=display,
            due_date_iso=iso,
        )

_seed_payments()

ACTIVITIES: list[Activity] = [
    Activity(id=str(uuid4()), icon="fa-check-circle", icon_color="green",
             title="Payment received", desc="Grace Wanjiku · KSh 240,000", time="2 hours ago"),
    Activity(id=str(uuid4()), icon="fa-paper-plane", icon_color="gold",
             title="Reminder sent", desc="8 pending landlords notified", time="5 hours ago"),
    Activity(id=str(uuid4()), icon="fa-file-invoice", icon_color="navy",
             title="Invoice generated", desc="May 2025 invoices ready", time="Yesterday"),
    Activity(id=str(uuid4()), icon="fa-user-plus", icon_color="green",
             title="New landlord onboarded", desc="Ali Mohamed · Mombasa Road Plaza", time="2 days ago"),
    Activity(id=str(uuid4()), icon="fa-exclamation-triangle", icon_color="red",
             title="Overdue flagged", desc="Peter Njoroge · KSh 96,000", time="3 days ago"),
    Activity(id=str(uuid4()), icon="fa-chart-pie", icon_color="gold",
             title="Monthly report ready", desc="April 2025 collection summary", time="4 days ago"),
]

SERVICES: list[ServiceItem] = [
    ServiceItem(icon="fa-broom", label="Cleaning Services"),
    ServiceItem(icon="fa-shield-alt", label="Security Management"),
    ServiceItem(icon="fa-tools", label="Maintenance & Repairs"),
    ServiceItem(icon="fa-water", label="Water Billing"),
    ServiceItem(icon="fa-bolt", label="Electricity Billing"),
    ServiceItem(icon="fa-trash-alt", label="Waste Management"),
    ServiceItem(icon="fa-parking", label="Parking Management"),
    ServiceItem(icon="fa-wifi", label="Internet Packages"),
    ServiceItem(icon="fa-couch", label="Furnished Units"),
    ServiceItem(icon="fa-box", label="Storage Rentals"),
    ServiceItem(icon="fa-file-invoice", label="KRA Tax Reports"),
    ServiceItem(icon="fa-chart-line", label="Financial Analytics"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _recompute_status(paid: int, due: int) -> PaymentStatus:
    if paid >= due:
        return PaymentStatus.paid
    if paid > 0:
        return PaymentStatus.partial
    # simple: if due date is in the past → overdue, else pending
    return PaymentStatus.pending  # caller can override to overdue


def _add_activity(icon: str, color: str, title: str, desc: str) -> Activity:
    act = Activity(
        id=str(uuid4()),
        icon=icon,
        icon_color=color,
        title=title,
        desc=desc,
        time="Just now",
    )
    ACTIVITIES.insert(0, act)
    if len(ACTIVITIES) > 30:
        ACTIVITIES.pop()
    return act


def compute_stats() -> DashboardStats:
    collected = pending = overdue = 0
    pending_count = overdue_count = 0
    total_billed = 0

    for p in PAYMENTS.values():
        total_billed += p.amount_due
        if p.status == PaymentStatus.paid:
            collected += p.amount_paid
        elif p.status == PaymentStatus.pending:
            pending += p.amount_due
            pending_count += 1
        elif p.status == PaymentStatus.overdue:
            overdue += p.amount_due
            overdue_count += 1
        elif p.status == PaymentStatus.partial:
            collected += p.amount_paid
            remaining = p.amount_due - p.amount_paid
            pending += remaining
            pending_count += 1

    rate = round((collected / total_billed) * 100) if total_billed else 0
    total_units = sum(l.units for l in LANDLORDS.values())

    return DashboardStats(
        total_collected=collected,
        total_pending=pending,
        total_overdue=overdue,
        active_landlords=len(LANDLORDS),
        total_units=total_units,
        collection_rate=rate,
        pending_count=pending_count,
        overdue_count=overdue_count,
        month_label="April 2025",
    )


def build_payment_rows(status: PaymentStatus | None = None) -> list[PaymentRow]:
    rows: list[PaymentRow] = []
    for p in PAYMENTS.values():
        if status and p.status != status:
            continue
        ll = LANDLORDS.get(p.landlord_id)
        if not ll:
            continue
        rows.append(
            PaymentRow(
                payment_id=p.id,
                landlord_id=ll.id,
                name=ll.name,
                initials=ll.initials,
                property=ll.property,
                units=ll.units,
                amount_due=p.amount_due,
                amount_paid=p.amount_paid,
                status=p.status,
                due_date=p.due_date,
            )
        )
    # sort: overdue first, then pending, partial, paid
    order = {"overdue": 0, "pending": 1, "partial": 2, "paid": 3}
    rows.sort(key=lambda r: (order.get(r.status.value, 9), r.due_date))
    return rows


def build_upcoming() -> list[UpcomingDue]:
    """Payments that are not fully paid, ordered by due date."""
    today = date(2025, 4, 12)  # dashboard “today”
    items: list[UpcomingDue] = []
    for p in PAYMENTS.values():
        if p.status == PaymentStatus.paid:
            continue
        ll = LANDLORDS.get(p.landlord_id)
        if not ll:
            continue
        try:
            due = date.fromisoformat(p.due_date_iso)
        except ValueError:
            due = today
        remaining = p.amount_due - p.amount_paid
        if remaining <= 0:
            continue
        delta = (due - today).days
        if delta < 0:
            urgency = Urgency.overdue
        elif delta <= 3:
            urgency = Urgency.urgent
        elif delta <= 10:
            urgency = Urgency.soon
        else:
            urgency = Urgency.normal
        items.append(
            UpcomingDue(
                landlord=ll.name,
                property=ll.property,
                amount=remaining,
                due=due.strftime("%b %d"),
                urgency=urgency,
            )
        )
    items.sort(key=lambda x: (0 if x.urgency == Urgency.overdue else 1 if x.urgency == Urgency.urgent else 2, x.due))
    return items[:6]


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Landlord Payments Dashboard"}


@app.get("/api/date")
def current_date():
    # Fixed demo date so UI matches mock; switch to real date if preferred
    d = date(2025, 4, 12)
    return {
        "iso": d.isoformat(),
        "display": d.strftime("%B %d, %Y"),
    }


@app.get("/api/stats", response_model=DashboardStats, tags=["Dashboard"])
def get_stats():
    return compute_stats()


@app.get("/api/payments", response_model=list[PaymentRow], tags=["Payments"])
def list_payments(
    status: Annotated[PaymentStatus | None, Query()] = None,
):
    return build_payment_rows(status)


@app.get("/api/payments/{payment_id}", tags=["Payments"])
def get_payment(payment_id: str):
    p = PAYMENTS.get(payment_id)
    if not p:
        raise HTTPException(404, "Payment not found")
    ll = LANDLORDS.get(p.landlord_id)
    return {"payment": p, "landlord": ll}


@app.post("/api/payments/record", response_model=Payment, tags=["Payments"])
def record_payment(body: RecordPaymentRequest):
    """Record a (partial or full) payment for a landlord’s current open invoice."""
    ll = LANDLORDS.get(body.landlord_id)
    if not ll:
        raise HTTPException(404, "Landlord not found")

    # Find open payment for this landlord
    target: Payment | None = None
    for p in PAYMENTS.values():
        if p.landlord_id == body.landlord_id and p.status != PaymentStatus.paid:
            target = p
            break
    if not target:
        raise HTTPException(400, "No open payment found for this landlord")

    remaining = target.amount_due - target.amount_paid
    if body.amount > remaining:
        raise HTTPException(400, f"Amount exceeds remaining balance (KSh {remaining:,})")

    target.amount_paid += body.amount
    if target.amount_paid >= target.amount_due:
        target.status = PaymentStatus.paid
        target.amount_paid = target.amount_due
    else:
        target.status = PaymentStatus.partial

    _add_activity(
        "fa-check-circle",
        "green",
        "Payment received",
        f"{ll.name} · KSh {body.amount:,}",
    )
    return target


@app.post("/api/payments/{payment_id}/mark-paid", response_model=Payment, tags=["Payments"])
def mark_paid(payment_id: str):
    p = PAYMENTS.get(payment_id)
    if not p:
        raise HTTPException(404, "Payment not found")
    ll = LANDLORDS.get(p.landlord_id)
    p.amount_paid = p.amount_due
    p.status = PaymentStatus.paid
    _add_activity(
        "fa-check-circle",
        "green",
        "Payment received",
        f"{ll.name if ll else 'Landlord'} · KSh {p.amount_due:,}",
    )
    return p


@app.get("/api/upcoming", response_model=list[UpcomingDue], tags=["Dashboard"])
def list_upcoming():
    return build_upcoming()


@app.get("/api/activity", response_model=list[Activity], tags=["Dashboard"])
def list_activity(limit: Annotated[int, Query(ge=1, le=50)] = 10):
    return ACTIVITIES[:limit]


@app.get("/api/services", response_model=list[ServiceItem], tags=["Dashboard"])
def list_services():
    return SERVICES


@app.post("/api/actions/send-reminders", tags=["Actions"])
def send_reminders(body: SendReminderRequest | None = None):
    filter_status = (body.status_filter if body else PaymentStatus.pending) or PaymentStatus.pending
    targets = [p for p in PAYMENTS.values() if p.status == filter_status]
    count = len(targets)
    if count == 0:
        return {"message": f"No landlords with status '{filter_status.value}'", "count": 0}

    names = []
    for p in targets[:5]:
        ll = LANDLORDS.get(p.landlord_id)
        if ll:
            names.append(ll.name)

    _add_activity(
        "fa-paper-plane",
        "gold",
        "Reminder sent",
        f"{count} {filter_status.value} landlord(s) notified",
    )
    return {
        "message": f"Reminders sent to {count} landlord(s)",
        "count": count,
        "sample": names,
    }


@app.post("/api/actions/export-report", tags=["Actions"])
def export_report():
    stats = compute_stats()
    _add_activity(
        "fa-file-pdf",
        "navy",
        "Report exported",
        f"{stats.month_label} collection summary",
    )
    return {
        "message": "Monthly report generated",
        "month": stats.month_label,
        "collected": stats.total_collected,
        "pending": stats.total_pending,
        "overdue": stats.total_overdue,
        "collection_rate": stats.collection_rate,
    }


@app.post("/api/actions/auto-schedule", tags=["Actions"])
def auto_schedule():
    _add_activity(
        "fa-clock",
        "gold",
        "Auto-schedule set",
        "Reminders scheduled for next month",
    )
    return {"message": "Automatic reminders scheduled for next month"}


# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

FRONTEND_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Mwarokin Estates · Landlord Payments</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" />
  <style>
    :root {
      --primary: #0f7b6b;
      --primary-dark: #0a5c50;
      --green: #0f7b6b;
      --amber: #b45309;
      --red: #b91c1c;
      --gold: #c8972a;
      --navy: #1e3a5f;
      --gray-50: #f8fafc;
      --gray-100: #f1f5f9;
      --gray-200: #e2e8f0;
      --gray-400: #94a3b8;
      --gray-500: #64748b;
      --gray-700: #334155;
      --gray-900: #0f172a;
      --radius: 12px;
      --shadow: 0 4px 20px rgba(0,0,0,.06);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      background: var(--gray-100);
      color: var(--gray-900);
      line-height: 1.5;
    }
    .app-container { max-width: 1280px; margin: 0 auto; padding: 0 20px 40px; }

    /* Top bar */
    .top-bar {
      display: flex; justify-content: space-between; align-items: center;
      padding: 18px 0; margin-bottom: 24px; border-bottom: 1px solid var(--gray-200);
    }
    .brand { display: flex; align-items: center; gap: 12px; }
    .brand-icon {
      width: 42px; height: 42px; background: linear-gradient(135deg, var(--primary), #2c6b9e);
      color: white; border-radius: 10px; display: grid; place-items: center; font-size: 20px;
    }
    .brand-text h1 { font-size: 1.25rem; font-weight: 700; }
    .brand-text h1 span { color: var(--primary); }
    .tagline { font-size: 0.78rem; color: var(--gray-500); }
    .nav-actions { display: flex; align-items: center; gap: 14px; }
    .date-chip {
      background: white; padding: 8px 14px; border-radius: 999px; font-size: 0.85rem;
      box-shadow: var(--shadow); display: flex; align-items: center; gap: 8px; color: var(--gray-700);
    }
    .avatar {
      width: 36px; height: 36px; border-radius: 50%; background: var(--primary);
      color: white; display: grid; place-items: center; font-weight: 600; font-size: 0.8rem;
    }

    /* Stats */
    .stats-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px; margin-bottom: 24px;
    }
    .stat-card {
      background: white; border-radius: var(--radius); padding: 18px 20px; box-shadow: var(--shadow);
    }
    .stat-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .stat-label { font-size: 0.8rem; color: var(--gray-500); }
    .stat-icon {
      width: 32px; height: 32px; border-radius: 8px; background: var(--gray-100);
      display: grid; place-items: center; color: var(--gray-500); font-size: 0.85rem;
    }
    .stat-icon.green { background: #d1fae5; color: var(--green); }
    .stat-icon.red { background: #fee2e2; color: var(--red); }
    .stat-icon.gold { background: #fef3c7; color: var(--gold); }
    .stat-value { font-size: 1.4rem; font-weight: 700; margin-bottom: 4px; }
    .stat-sub { font-size: 0.78rem; color: var(--gray-500); }
    .text-green { color: var(--green); }
    .text-amber { color: var(--amber); }
    .trend-down { color: var(--red); }

    /* Layout */
    .dashboard-grid {
      display: grid; grid-template-columns: 1fr 340px; gap: 20px; margin-bottom: 20px;
    }
    @media (max-width: 960px) { .dashboard-grid { grid-template-columns: 1fr; } }
    .bottom-grid {
      display: grid; grid-template-columns: 1fr 1fr; gap: 20px;
    }
    @media (max-width: 800px) { .bottom-grid { grid-template-columns: 1fr; } }

    .card {
      background: white; border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden;
    }
    .card-header {
      display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;
      padding: 16px 18px; border-bottom: 1px solid var(--gray-200);
    }
    .card-header h2 { font-size: 0.95rem; display: flex; align-items: center; gap: 8px; }

    .filter-group { display: flex; gap: 6px; flex-wrap: wrap; }
    .filter-btn {
      border: 1px solid var(--gray-200); background: white; border-radius: 999px;
      padding: 4px 12px; font-size: 0.75rem; cursor: pointer; color: var(--gray-500);
    }
    .filter-btn.active, .filter-btn:hover { background: var(--primary); color: white; border-color: var(--primary); }

    .table-wrapper { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; }
    th {
      text-align: left; padding: 10px 14px; font-size: 0.7rem; text-transform: uppercase;
      letter-spacing: 0.04em; color: var(--gray-500); background: var(--gray-50);
      border-bottom: 1px solid var(--gray-200);
    }
    td { padding: 12px 14px; border-bottom: 1px solid var(--gray-100); font-size: 0.85rem; vertical-align: middle; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: var(--gray-50); }

    .landlord-info { display: flex; align-items: center; gap: 10px; }
    .landlord-avatar {
      width: 36px; height: 36px; border-radius: 50%; background: var(--primary);
      color: white; display: grid; place-items: center; font-weight: 600; font-size: 0.75rem; flex-shrink: 0;
    }
    .landlord-name { font-weight: 600; display: block; }
    .landlord-property { font-size: 0.72rem; color: var(--gray-500); }
    .amount { font-variant-numeric: tabular-nums; font-weight: 500; }

    .badge {
      display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 0.72rem;
      font-weight: 600; text-transform: capitalize;
    }
    .badge--paid { background: #d1fae5; color: #065f46; }
    .badge--pending { background: #fef3c7; color: #92400e; }
    .badge--overdue { background: #fee2e2; color: #991b1b; }
    .badge--partial { background: #e0e7ff; color: #3730a3; }

    .action-btn {
      border: 1px solid var(--gray-200); background: white; border-radius: 8px;
      padding: 5px 10px; font-size: 0.75rem; cursor: pointer;
      display: inline-flex; align-items: center; gap: 4px;
    }
    .action-btn:hover { border-color: var(--primary); color: var(--primary); }

    /* Right panel */
    .right-panel { display: flex; flex-direction: column; gap: 16px; }
    .upcoming-list, .activity-list { padding: 8px 0; }
    .upcoming-item, .activity-item {
      display: flex; align-items: center; gap: 12px; padding: 10px 16px;
      border-bottom: 1px solid var(--gray-100);
    }
    .upcoming-item:last-child, .activity-item:last-child { border-bottom: none; }
    .upcoming-left { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
    .due-icon {
      width: 34px; height: 34px; border-radius: 8px; background: var(--gray-100);
      display: grid; place-items: center; color: var(--gray-500); flex-shrink: 0;
    }
    .due-icon.urgent { background: #fee2e2; color: var(--red); }
    .due-icon.soon { background: #fef3c7; color: var(--amber); }
    .due-title { font-weight: 600; font-size: 0.85rem; display: block; }
    .due-date { font-size: 0.72rem; color: var(--gray-500); }
    .due-amount { font-weight: 600; font-size: 0.85rem; white-space: nowrap; }
    .due-amount small { font-weight: 400; color: var(--gray-400); }

    .activity-icon {
      width: 34px; height: 34px; border-radius: 8px; display: grid; place-items: center;
      flex-shrink: 0; font-size: 0.85rem;
    }
    .activity-icon.green { background: #d1fae5; color: var(--green); }
    .activity-icon.gold { background: #fef3c7; color: var(--gold); }
    .activity-icon.navy { background: #dbeafe; color: var(--navy); }
    .activity-icon.red { background: #fee2e2; color: var(--red); }
    .activity-content { flex: 1; min-width: 0; }
    .activity-title { font-weight: 600; font-size: 0.85rem; }
    .activity-desc { font-size: 0.75rem; color: var(--gray-500); }
    .activity-time { font-size: 0.72rem; color: var(--gray-400); white-space: nowrap; }

    .quick-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding: 14px; }
    .quick-btn {
      border: 1px solid var(--gray-200); background: var(--gray-50); border-radius: 10px;
      padding: 12px; text-align: left; cursor: pointer; transition: .15s;
      display: flex; flex-direction: column; gap: 2px;
    }
    .quick-btn:hover { border-color: var(--primary); background: white; }
    .quick-btn i { color: var(--primary); margin-bottom: 4px; }
    .quick-btn .label { font-weight: 600; font-size: 0.8rem; }
    .quick-btn .sub { font-size: 0.7rem; color: var(--gray-500); }

    .services-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      gap: 10px; padding: 14px;
    }
    .service-chip {
      display: flex; align-items: center; gap: 8px; padding: 10px 12px;
      background: var(--gray-50); border-radius: 8px; font-size: 0.8rem;
    }
    .service-chip i { color: var(--primary); }

    .fade-in { animation: fadeIn .35s ease; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }

    .toast {
      position: fixed; bottom: 24px; right: 24px; background: var(--gray-900); color: white;
      padding: 12px 18px; border-radius: 10px; font-size: 0.9rem; z-index: 100;
      animation: fadeIn .3s ease; max-width: 320px;
    }

    /* Modal */
    .modal-overlay {
      position: fixed; inset: 0; background: rgba(15,23,42,.4); display: none;
      align-items: center; justify-content: center; z-index: 90; padding: 16px;
    }
    .modal-overlay.open { display: flex; }
    .modal {
      background: white; border-radius: 14px; width: 100%; max-width: 400px;
      box-shadow: 0 20px 50px rgba(0,0,0,.15);
    }
    .modal-header {
      padding: 16px 18px; border-bottom: 1px solid var(--gray-200);
      display: flex; justify-content: space-between; align-items: center;
    }
    .modal-header h3 { font-size: 1rem; }
    .modal-close { border: none; background: none; font-size: 1.3rem; cursor: pointer; color: var(--gray-500); }
    .modal-body { padding: 18px; }
    .detail-row {
      display: flex; justify-content: space-between; padding: 8px 0;
      border-bottom: 1px solid var(--gray-100); font-size: 0.9rem;
    }
    .detail-row:last-child { border-bottom: none; }
    .detail-label { color: var(--gray-500); }
    .detail-value { font-weight: 600; }
    .modal-actions {
      padding: 14px 18px; border-top: 1px solid var(--gray-200);
      display: flex; gap: 8px; justify-content: flex-end;
    }
    .btn-primary {
      background: var(--primary); color: white; border: none; border-radius: 8px;
      padding: 8px 14px; font-size: 0.85rem; cursor: pointer;
    }
    .btn-primary:hover { background: var(--primary-dark); }
    .btn-ghost {
      background: white; border: 1px solid var(--gray-200); border-radius: 8px;
      padding: 8px 14px; font-size: 0.85rem; cursor: pointer;
    }
  </style>
</head>
<body>
  <div class="app-container">
    <header class="top-bar">
      <div class="brand">
        <div class="brand-icon">⬡</div>
        <div class="brand-text">
          <h1>Mwarokin <span>Estates</span></h1>
          <div class="tagline">Landlord Payments · Dashboard</div>
        </div>
      </div>
      <div class="nav-actions">
        <div class="date-chip">
          <i class="fas fa-calendar-alt"></i>
          <span id="currentDate">—</span>
        </div>
        <div class="avatar" title="Landlord Admin">AD</div>
      </div>
    </header>

    <section class="stats-grid" id="statsGrid">
      <!-- filled by JS -->
    </section>

    <div class="dashboard-grid">
      <div class="card fade-in">
        <div class="card-header">
          <h2><i class="fas fa-file-invoice-dollar"></i> Monthly Payments</h2>
          <div class="filter-group" id="paymentFilterGroup">
            <button class="filter-btn active" data-filter="all">All</button>
            <button class="filter-btn" data-filter="paid">Paid</button>
            <button class="filter-btn" data-filter="pending">Pending</button>
            <button class="filter-btn" data-filter="overdue">Overdue</button>
            <button class="filter-btn" data-filter="partial">Partial</button>
          </div>
        </div>
        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Landlord</th>
                <th>Property</th>
                <th>Amount Due</th>
                <th>Paid</th>
                <th>Status</th>
                <th>Due Date</th>
                <th></th>
              </tr>
            </thead>
            <tbody id="paymentsTableBody"></tbody>
          </table>
        </div>
      </div>

      <div class="right-panel">
        <div class="card fade-in">
          <div class="card-header">
            <h2><i class="fas fa-calendar-check"></i> Upcoming Dues</h2>
          </div>
          <div class="upcoming-list" id="upcomingList"></div>
        </div>
        <div class="card fade-in">
          <div class="card-header">
            <h2><i class="fas fa-bolt"></i> Quick Actions</h2>
          </div>
          <div class="quick-actions">
            <button class="quick-btn" id="btnRemind">
              <i class="fas fa-bell"></i>
              <span class="label">Send Reminder</span>
              <span class="sub" id="remindSub">To pending</span>
            </button>
            <button class="quick-btn" id="btnExport">
              <i class="fas fa-file-pdf"></i>
              <span class="label">Export Report</span>
              <span class="sub">April 2025</span>
            </button>
            <button class="quick-btn" id="btnRecord">
              <i class="fas fa-plus-circle"></i>
              <span class="label">Record Payment</span>
              <span class="sub">Manual entry</span>
            </button>
            <button class="quick-btn" id="btnSchedule">
              <i class="fas fa-clock"></i>
              <span class="label">Auto-Schedule</span>
              <span class="sub">Next month</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="bottom-grid">
      <div class="card fade-in">
        <div class="card-header">
          <h2><i class="fas fa-history"></i> Recent Activity</h2>
        </div>
        <div class="activity-list" id="activityList"></div>
      </div>
      <div class="card fade-in">
        <div class="card-header">
          <h2><i class="fas fa-concierge-bell"></i> Services Generated</h2>
        </div>
        <div class="services-grid" id="servicesGrid"></div>
      </div>
    </div>
  </div>

  <!-- View / Pay modal -->
  <div class="modal-overlay" id="modalOverlay">
    <div class="modal">
      <div class="modal-header">
        <h3 id="modalTitle">Payment details</h3>
        <button class="modal-close" id="modalClose">&times;</button>
      </div>
      <div class="modal-body" id="modalBody"></div>
      <div class="modal-actions" id="modalActions"></div>
    </div>
  </div>

  <script>
    const API = '';
    let currentFilter = 'all';
    let currentPaymentId = null;

    function toast(msg) {
      const el = document.createElement('div');
      el.className = 'toast';
      el.textContent = msg;
      document.body.appendChild(el);
      setTimeout(() => el.remove(), 3000);
    }

    async function api(path, opts = {}) {
      const res = await fetch(API + path, {
        headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
        ...opts,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(typeof err.detail === 'string' ? err.detail : (err.detail?.[0]?.msg || res.statusText));
      }
      return res.json();
    }

    function formatKsh(v) {
      return 'KSh ' + (v ?? 0).toLocaleString('en-KE');
    }

    function badgeClass(status) {
      return ({ paid: 'badge--paid', pending: 'badge--pending', overdue: 'badge--overdue', partial: 'badge--partial' })[status] || 'badge--pending';
    }

    // ----- Stats -----
    async function renderStats() {
      const s = await api('/api/stats');
      document.getElementById('statsGrid').innerHTML = `
        <div class="stat-card fade-in">
          <div class="stat-header">
            <span class="stat-label">Total Collected (Apr)</span>
            <div class="stat-icon green"><i class="fas fa-arrow-down"></i></div>
          </div>
          <div class="stat-value">${formatKsh(s.total_collected)}</div>
          <div class="stat-sub"><i class="fas fa-check-circle text-green"></i> ${s.collection_rate}% collection rate</div>
        </div>
        <div class="stat-card fade-in">
          <div class="stat-header">
            <span class="stat-label">Pending Payments</span>
            <div class="stat-icon"><i class="fas fa-clock"></i></div>
          </div>
          <div class="stat-value">${formatKsh(s.total_pending)}</div>
          <div class="stat-sub"><i class="fas fa-hourglass-half text-amber"></i> ${s.pending_count} landlords pending</div>
        </div>
        <div class="stat-card fade-in">
          <div class="stat-header">
            <span class="stat-label">Overdue</span>
            <div class="stat-icon red"><i class="fas fa-exclamation-triangle"></i></div>
          </div>
          <div class="stat-value">${formatKsh(s.total_overdue)}</div>
          <div class="stat-sub"><i class="fas fa-arrow-up trend-down"></i> ${s.overdue_count} landlords overdue</div>
        </div>
        <div class="stat-card fade-in">
          <div class="stat-header">
            <span class="stat-label">Active Landlords</span>
            <div class="stat-icon gold"><i class="fas fa-users"></i></div>
          </div>
          <div class="stat-value">${s.active_landlords}</div>
          <div class="stat-sub"><i class="fas fa-building"></i> ${s.total_units} total units</div>
        </div>`;
      document.getElementById('remindSub').textContent = `To ${s.pending_count} pending`;
    }

    // ----- Payments table -----
    async function renderPayments(filter = 'all') {
      currentFilter = filter;
      const q = filter === 'all' ? '' : `?status=${filter}`;
      const rows = await api('/api/payments' + q);
      const tbody = document.getElementById('paymentsTableBody');
      if (!rows.length) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:40px;color:var(--gray-500)">No payments found for this filter.</td></tr>`;
        return;
      }
      tbody.innerHTML = rows.map(r => `
        <tr>
          <td>
            <div class="landlord-info">
              <div class="landlord-avatar">${r.initials}</div>
              <div class="landlord-details">
                <span class="landlord-name">${r.name}</span>
                <span class="landlord-property">${r.units} units</span>
              </div>
            </div>
          </td>
          <td>${r.property}</td>
          <td class="amount">${formatKsh(r.amount_due)}</td>
          <td class="amount">${r.amount_paid > 0 ? formatKsh(r.amount_paid) : '—'}</td>
          <td><span class="badge ${badgeClass(r.status)}">${r.status}</span></td>
          <td>${r.due_date}</td>
          <td>
            <button class="action-btn" onclick="openPayment('${r.payment_id}')">
              <i class="fas fa-eye"></i> View
            </button>
          </td>
        </tr>`).join('');
    }

    // ----- Upcoming -----
    async function renderUpcoming() {
      const items = await api('/api/upcoming');
      document.getElementById('upcomingList').innerHTML = items.map(item => {
        let iconClass = 'due-icon', iconFa = 'fa-calendar-day', label = '';
        if (item.urgency === 'urgent') { iconClass += ' urgent'; iconFa = 'fa-exclamation-circle'; label = ' · Urgent'; }
        else if (item.urgency === 'soon') { iconClass += ' soon'; iconFa = 'fa-clock'; label = ' · Soon'; }
        else if (item.urgency === 'overdue') { iconClass += ' urgent'; iconFa = 'fa-exclamation-triangle'; label = ' · Overdue'; }
        return `
          <div class="upcoming-item">
            <div class="upcoming-left">
              <div class="${iconClass}"><i class="fas ${iconFa}"></i></div>
              <div class="due-info">
                <span class="due-title">${item.landlord}</span>
                <span class="due-date"><i class="far fa-building"></i> ${item.property} · Due ${item.due}${label}</span>
              </div>
            </div>
            <div class="due-amount">${formatKsh(item.amount)} <small>/mo</small></div>
          </div>`;
      }).join('') || '<div style="padding:16px;color:var(--gray-500);font-size:0.85rem">No upcoming dues</div>';
    }

    // ----- Activity -----
    async function renderActivity() {
      const items = await api('/api/activity?limit=8');
      document.getElementById('activityList').innerHTML = items.map(a => `
        <div class="activity-item">
          <div class="activity-icon ${a.icon_color}"><i class="fas ${a.icon}"></i></div>
          <div class="activity-content">
            <div class="activity-title">${a.title}</div>
            <div class="activity-desc">${a.desc}</div>
          </div>
          <div class="activity-time">${a.time}</div>
        </div>`).join('');
    }

    // ----- Services -----
    async function renderServices() {
      const items = await api('/api/services');
      document.getElementById('servicesGrid').innerHTML = items.map(s => `
        <div class="service-chip"><i class="fas ${s.icon}"></i><span>${s.label}</span></div>`).join('');
    }

    // ----- Modal -----
    async function openPayment(paymentId) {
      currentPaymentId = paymentId;
      try {
        const data = await api(`/api/payments/${paymentId}`);
        const p = data.payment;
        const ll = data.landlord;
        document.getElementById('modalTitle').textContent = ll ? ll.name : 'Payment';
        document.getElementById('modalBody').innerHTML = `
          <div class="detail-row"><span class="detail-label">Property</span><span class="detail-value">${ll?.property || '—'}</span></div>
          <div class="detail-row"><span class="detail-label">Service</span><span class="detail-value">${ll?.service || '—'}</span></div>
          <div class="detail-row"><span class="detail-label">Amount due</span><span class="detail-value">${formatKsh(p.amount_due)}</span></div>
          <div class="detail-row"><span class="detail-label">Paid</span><span class="detail-value" style="color:var(--green)">${formatKsh(p.amount_paid)}</span></div>
          <div class="detail-row"><span class="detail-label">Status</span><span class="detail-value">${p.status}</span></div>
          <div class="detail-row"><span class="detail-label">Due date</span><span class="detail-value">${p.due_date}</span></div>`;
        const actions = document.getElementById('modalActions');
        if (p.status !== 'paid') {
          actions.innerHTML = `
            <button class="btn-ghost" onclick="closeModal()">Close</button>
            <button class="btn-primary" onclick="markPaid('${p.id}')"><i class="fas fa-check"></i> Mark paid</button>`;
        } else {
          actions.innerHTML = `<button class="btn-ghost" onclick="closeModal()">Close</button>`;
        }
        document.getElementById('modalOverlay').classList.add('open');
      } catch (e) {
        toast('⚠️ ' + e.message);
      }
    }

    function closeModal() {
      document.getElementById('modalOverlay').classList.remove('open');
      currentPaymentId = null;
    }

    async function markPaid(paymentId) {
      try {
        await api(`/api/payments/${paymentId}/mark-paid`, { method: 'POST' });
        toast('✅ Marked as paid');
        closeModal();
        await refreshAll();
      } catch (e) {
        toast('⚠️ ' + e.message);
      }
    }

    // ----- Quick actions -----
    async function sendReminders() {
      try {
        const res = await api('/api/actions/send-reminders', {
          method: 'POST',
          body: JSON.stringify({ status_filter: 'pending' }),
        });
        toast('📤 ' + res.message);
        await renderActivity();
        await renderStats();
      } catch (e) {
        toast('⚠️ ' + e.message);
      }
    }

    async function exportReport() {
      try {
        const res = await api('/api/actions/export-report', { method: 'POST' });
        toast(`📊 Report ready · Collected ${formatKsh(res.collected)} (${res.collection_rate}%)`);
        await renderActivity();
      } catch (e) {
        toast('⚠️ ' + e.message);
      }
    }

    async function autoSchedule() {
      try {
        const res = await api('/api/actions/auto-schedule', { method: 'POST' });
        toast('📅 ' + res.message);
        await renderActivity();
      } catch (e) {
        toast('⚠️ ' + e.message);
      }
    }

    // Simple record: mark first pending/partial/overdue as paid (demo)
    async function recordPaymentDemo() {
      try {
        const rows = await api('/api/payments');
        const open = rows.find(r => r.status !== 'paid');
        if (!open) {
          toast('All payments are already settled');
          return;
        }
        await api('/api/payments/record', {
          method: 'POST',
          body: JSON.stringify({ landlord_id: open.landlord_id, amount: open.amount_due - open.amount_paid }),
        });
        toast(`💰 Payment recorded for ${open.name}`);
        await refreshAll();
      } catch (e) {
        toast('⚠️ ' + e.message);
      }
    }

    // ----- Refresh -----
    async function refreshAll() {
      await Promise.all([
        renderStats(),
        renderPayments(currentFilter),
        renderUpcoming(),
        renderActivity(),
      ]);
    }

    // ----- Init -----
    async function init() {
      const d = await api('/api/date');
      document.getElementById('currentDate').textContent = d.display;

      document.getElementById('paymentFilterGroup').addEventListener('click', (e) => {
        const btn = e.target.closest('.filter-btn');
        if (!btn) return;
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        renderPayments(btn.dataset.filter);
      });

      document.getElementById('btnRemind').addEventListener('click', sendReminders);
      document.getElementById('btnExport').addEventListener('click', exportReport);
      document.getElementById('btnRecord').addEventListener('click', recordPaymentDemo);
      document.getElementById('btnSchedule').addEventListener('click', autoSchedule);
      document.getElementById('modalClose').addEventListener('click', closeModal);
      document.getElementById('modalOverlay').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeModal();
      });

      await Promise.all([
        renderStats(),
        renderPayments('all'),
        renderUpcoming(),
        renderActivity(),
        renderServices(),
      ]);
      console.log('🏘️ Mwarokin Estates · Landlord Payments Dashboard ready (real API)');
    }

    document.addEventListener('DOMContentLoaded', init);
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    return FRONTEND_HTML


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### Real behaviour

| Feature | What it does |
|---------|----------------|
| **Stats** | Computed live from payments (collected, pending, overdue, rate, counts) |
| **Payments table** | Filterable by status via query param; sorted overdue → pending → partial → paid |
| **View / Mark paid** | Modal loads payment + landlord; **Mark paid** updates store and refreshes stats/table/activity |
| **Send Reminder** | Targets pending landlords, logs activity, updates pending count in UI |
| **Export Report** | Returns real aggregates and logs activity |
| **Record Payment** | Applies remaining balance on first open invoice (demo flow) |
| **Auto-Schedule** | Logs scheduling event to activity feed |
| **Upcoming dues** | Derived from open payments + urgency by due date |
| **Activity feed** | Mutable; new events appear at the top after actions |

### Run

```bash
pip install fastapi "uvicorn[standard]" pydantic
uvicorn main:app --reload --port 8000
```

Open **http://127.0.0.1:8000** — every filter, button, and modal talks to the Python backend.