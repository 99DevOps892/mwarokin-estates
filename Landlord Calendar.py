Here’s a complete, modern **FastAPI** backend that powers the Landlord Payment Hub with real, mutable data and proper REST endpoints. The frontend is updated to consume the API instead of hard-coded JS mocks.

```python
"""
Mwarokin Estates – Landlord Payment Hub
Modern FastAPI backend with real functionality.

Run:
    pip install fastapi uvicorn[standard] pydantic
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Open: http://127.0.0.1:8000
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Annotated, Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Path, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, computed_field

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mwarokin Estates – Landlord Payment Hub",
    description="Real backend for monthly landlord payment tracking, stats and actions.",
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
    due = "due"


class MonthPayment(BaseModel):
    paid: int = Field(0, ge=0)
    due: int = Field(0, ge=0)
    pending: int = Field(0, ge=0)
    status: PaymentStatus


class Landlord(BaseModel):
    id: int
    name: str
    property: str
    service: str
    amount: int = Field(..., gt=0)  # monthly billed amount
    payments: dict[str, MonthPayment]  # key = "YYYY-MM"


class LandlordRow(BaseModel):
    """Flattened row for the table (one landlord + one month)."""
    id: int
    name: str
    property: str
    service: str
    amount: int
    paid: int
    due: int
    pending: int
    status: PaymentStatus
    month_key: str

    @computed_field
    @property
    def initials(self) -> str:
        parts = self.name.split()
        return "".join(p[0] for p in parts[:2]).upper()


class MonthStats(BaseModel):
    total_billed: int
    total_paid: int
    total_due: int
    total_pending: int
    paid_percentage: int
    month_label: str
    year: int
    month: int  # 1-12


class MonthRange(BaseModel):
    min_year: int
    min_month: int  # 1-12
    max_year: int
    max_month: int  # 1-12
    current_year: int
    current_month: int


class RecordPaymentRequest(BaseModel):
    amount: int = Field(..., gt=0)
    note: str | None = None


class PaymentDetailResponse(BaseModel):
    landlord: Landlord
    month_key: str
    record: MonthPayment
    month_label: str


# ---------------------------------------------------------------------------
# In-memory store (mutable – real functionality)
# ---------------------------------------------------------------------------

LANDLORDS: dict[int, Landlord] = {
    1: Landlord(
        id=1,
        name="James Mwangi",
        property="Kilimani Heights, Unit 4B",
        service="Property management",
        amount=45_000,
        payments={
            "2025-04": MonthPayment(paid=45_000, due=0, pending=0, status=PaymentStatus.paid),
            "2025-05": MonthPayment(paid=45_000, due=0, pending=0, status=PaymentStatus.paid),
            "2025-06": MonthPayment(paid=30_000, due=15_000, pending=0, status=PaymentStatus.pending),
            "2025-07": MonthPayment(paid=0, due=45_000, pending=0, status=PaymentStatus.due),
        },
    ),
    2: Landlord(
        id=2,
        name="Grace Wanjiku",
        property="Westlands Grove, Villa 12",
        service="Maintenance & security",
        amount=62_000,
        payments={
            "2025-04": MonthPayment(paid=62_000, due=0, pending=0, status=PaymentStatus.paid),
            "2025-05": MonthPayment(paid=62_000, due=0, pending=0, status=PaymentStatus.paid),
            "2025-06": MonthPayment(paid=62_000, due=0, pending=0, status=PaymentStatus.paid),
            "2025-07": MonthPayment(paid=20_000, due=42_000, pending=0, status=PaymentStatus.pending),
        },
    ),
    3: Landlord(
        id=3,
        name="Peter Njoroge",
        property="Lavington Edge, Apt 7",
        service="Utilities & garbage",
        amount=38_000,
        payments={
            "2025-04": MonthPayment(paid=38_000, due=0, pending=0, status=PaymentStatus.paid),
            "2025-05": MonthPayment(paid=20_000, due=18_000, pending=0, status=PaymentStatus.pending),
            "2025-06": MonthPayment(paid=0, due=38_000, pending=0, status=PaymentStatus.due),
            "2025-07": MonthPayment(paid=0, due=0, pending=38_000, status=PaymentStatus.pending),
        },
    ),
    4: Landlord(
        id=4,
        name="Amina Hassan",
        property="Parklands Residency, Suite 9",
        service="Full facility mgmt",
        amount=55_000,
        payments={
            "2025-04": MonthPayment(paid=55_000, due=0, pending=0, status=PaymentStatus.paid),
            "2025-05": MonthPayment(paid=55_000, due=0, pending=0, status=PaymentStatus.paid),
            "2025-06": MonthPayment(paid=55_000, due=0, pending=0, status=PaymentStatus.paid),
            "2025-07": MonthPayment(paid=0, due=55_000, pending=0, status=PaymentStatus.due),
        },
    ),
    5: Landlord(
        id=5,
        name="David Ochieng",
        property="Karen Breeze, House 3",
        service="Landscaping & repairs",
        amount=72_000,
        payments={
            "2025-04": MonthPayment(paid=72_000, due=0, pending=0, status=PaymentStatus.paid),
            "2025-05": MonthPayment(paid=72_000, due=0, pending=0, status=PaymentStatus.paid),
            "2025-06": MonthPayment(paid=40_000, due=32_000, pending=0, status=PaymentStatus.pending),
            "2025-07": MonthPayment(paid=0, due=72_000, pending=0, status=PaymentStatus.due),
        },
    ),
    6: Landlord(
        id=6,
        name="Mercy Kamau",
        property="Runda Meadows, Villa 8",
        service="Security & maintenance",
        amount=48_000,
        payments={
            "2025-04": MonthPayment(paid=48_000, due=0, pending=0, status=PaymentStatus.paid),
            "2025-05": MonthPayment(paid=48_000, due=0, pending=0, status=PaymentStatus.paid),
            "2025-06": MonthPayment(paid=48_000, due=0, pending=0, status=PaymentStatus.paid),
            "2025-07": MonthPayment(paid=0, due=48_000, pending=0, status=PaymentStatus.due),
        },
    ),
}

# Navigation bounds (1-indexed months)
MIN_YEAR, MIN_MONTH = 2025, 4   # April 2025
MAX_YEAR, MAX_MONTH = 2025, 7   # July 2025
DEFAULT_YEAR, DEFAULT_MONTH = 2025, 6  # June 2025


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def month_key(year: int, month: int) -> str:
    """month is 1-12."""
    return f"{year}-{month:02d}"


def format_month_label(year: int, month: int) -> str:
    d = date(year, month, 1)
    return d.strftime("%B %Y")


def get_or_default_record(landlord: Landlord, key: str) -> MonthPayment:
    if key in landlord.payments:
        return landlord.payments[key]
    # No record → treat as fully due
    return MonthPayment(paid=0, due=landlord.amount, pending=0, status=PaymentStatus.due)


def compute_stats(year: int, month: int) -> MonthStats:
    key = month_key(year, month)
    total_billed = total_paid = total_due = total_pending = 0

    for ll in LANDLORDS.values():
        rec = get_or_default_record(ll, key)
        total_billed += ll.amount
        total_paid += rec.paid
        total_due += rec.due
        total_pending += rec.pending

    pct = round((total_paid / total_billed) * 100) if total_billed else 0
    return MonthStats(
        total_billed=total_billed,
        total_paid=total_paid,
        total_due=total_due,
        total_pending=total_pending,
        paid_percentage=pct,
        month_label=format_month_label(year, month),
        year=year,
        month=month,
    )


def validate_month(year: int, month: int) -> None:
    if not (1 <= month <= 12):
        raise HTTPException(400, "Month must be 1-12")
    # Soft bounds for available data
    if (year, month) < (MIN_YEAR, MIN_MONTH) or (year, month) > (MAX_YEAR, MAX_MONTH):
        raise HTTPException(
            400,
            f"Month out of available range ({MIN_YEAR}-{MIN_MONTH:02d} to {MAX_YEAR}-{MAX_MONTH:02d})",
        )


def recompute_status(paid: int, due: int, pending: int, amount: int) -> PaymentStatus:
    if paid >= amount and due == 0 and pending == 0:
        return PaymentStatus.paid
    if pending > 0:
        return PaymentStatus.pending
    if due > 0:
        return PaymentStatus.due
    return PaymentStatus.pending


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Landlord Payment Hub"}


@app.get("/api/range", response_model=MonthRange, tags=["Navigation"])
def get_month_range():
    return MonthRange(
        min_year=MIN_YEAR,
        min_month=MIN_MONTH,
        max_year=MAX_YEAR,
        max_month=MAX_MONTH,
        current_year=DEFAULT_YEAR,
        current_month=DEFAULT_MONTH,
    )


@app.get("/api/stats", response_model=MonthStats, tags=["Stats"])
def get_stats(
    year: Annotated[int, Query(ge=2020, le=2030)] = DEFAULT_YEAR,
    month: Annotated[int, Query(ge=1, le=12)] = DEFAULT_MONTH,
):
    validate_month(year, month)
    return compute_stats(year, month)


@app.get("/api/payments", response_model=list[LandlordRow], tags=["Payments"])
def list_payments(
    year: Annotated[int, Query(ge=2020, le=2030)] = DEFAULT_YEAR,
    month: Annotated[int, Query(ge=1, le=12)] = DEFAULT_MONTH,
):
    validate_month(year, month)
    key = month_key(year, month)
    rows: list[LandlordRow] = []
    for ll in LANDLORDS.values():
        rec = get_or_default_record(ll, key)
        rows.append(
            LandlordRow(
                id=ll.id,
                name=ll.name,
                property=ll.property,
                service=ll.service,
                amount=ll.amount,
                paid=rec.paid,
                due=rec.due,
                pending=rec.pending,
                status=rec.status,
                month_key=key,
            )
        )
    return rows


@app.get("/api/landlords/{landlord_id}", response_model=Landlord, tags=["Landlords"])
def get_landlord(landlord_id: int):
    ll = LANDLORDS.get(landlord_id)
    if not ll:
        raise HTTPException(404, "Landlord not found")
    return ll


@app.get(
    "/api/landlords/{landlord_id}/payments/{year}/{month}",
    response_model=PaymentDetailResponse,
    tags=["Payments"],
)
def get_payment_detail(
    landlord_id: int,
    year: Annotated[int, Path(ge=2020, le=2030)],
    month: Annotated[int, Path(ge=1, le=12)],
):
    validate_month(year, month)
    ll = LANDLORDS.get(landlord_id)
    if not ll:
        raise HTTPException(404, "Landlord not found")
    key = month_key(year, month)
    rec = get_or_default_record(ll, key)
    return PaymentDetailResponse(
        landlord=ll,
        month_key=key,
        record=rec,
        month_label=format_month_label(year, month),
    )


@app.post(
    "/api/landlords/{landlord_id}/payments/{year}/{month}/record",
    response_model=MonthPayment,
    tags=["Payments"],
)
def record_payment(
    landlord_id: int,
    year: Annotated[int, Path(ge=2020, le=2030)],
    month: Annotated[int, Path(ge=1, le=12)],
    body: RecordPaymentRequest,
):
    """
    Record a payment against a landlord for a given month.
    Reduces due / pending and increases paid. Recalculates status.
    """
    validate_month(year, month)
    ll = LANDLORDS.get(landlord_id)
    if not ll:
        raise HTTPException(404, "Landlord not found")

    key = month_key(year, month)
    rec = get_or_default_record(ll, key)

    remaining = rec.due + rec.pending
    if body.amount > remaining + (ll.amount - rec.paid - remaining):
        # Allow overpay up to full amount for simplicity, but cap at amount
        pass

    apply = min(body.amount, max(0, ll.amount - rec.paid))
    if apply <= 0:
        raise HTTPException(400, "Nothing left to pay for this month")

    # Prefer reducing due first, then pending
    if rec.due > 0:
        reduce_due = min(apply, rec.due)
        rec.due -= reduce_due
        rec.paid += reduce_due
        apply -= reduce_due
    if apply > 0 and rec.pending > 0:
        reduce_pending = min(apply, rec.pending)
        rec.pending -= reduce_pending
        rec.paid += reduce_pending
        apply -= reduce_pending
    if apply > 0:
        # Extra payment beyond due/pending
        rec.paid += apply

    rec.status = recompute_status(rec.paid, rec.due, rec.pending, ll.amount)
    ll.payments[key] = rec
    return rec


@app.post(
    "/api/landlords/{landlord_id}/payments/{year}/{month}/mark-paid",
    response_model=MonthPayment,
    tags=["Payments"],
)
def mark_fully_paid(
    landlord_id: int,
    year: Annotated[int, Path(ge=2020, le=2030)],
    month: Annotated[int, Path(ge=1, le=12)],
):
    """Mark the entire month as fully paid."""
    validate_month(year, month)
    ll = LANDLORDS.get(landlord_id)
    if not ll:
        raise HTTPException(404, "Landlord not found")

    key = month_key(year, month)
    rec = MonthPayment(paid=ll.amount, due=0, pending=0, status=PaymentStatus.paid)
    ll.payments[key] = rec
    return rec


# ---------------------------------------------------------------------------
# Frontend (talks to real API)
# ---------------------------------------------------------------------------

FRONTEND_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Mwarokin Estates · Landlord Payment Hub</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" />
  <style>
    :root {
      --bg: #f0f4f8;
      --card: #ffffff;
      --primary: #0f7b6b;
      --primary-dark: #0a5c50;
      --warning: #b45309;
      --danger: #b91c1c;
      --muted: #64748b;
      --border: #e2e8f0;
      --radius: 12px;
      --shadow: 0 4px 16px rgba(0,0,0,.06);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      background: var(--bg);
      color: #1e293b;
      line-height: 1.5;
      min-height: 100vh;
    }
    .dashboard { max-width: 1200px; margin: 0 auto; padding: 24px 20px 48px; }

    /* Header */
    .header {
      display: flex; justify-content: space-between; align-items: center;
      flex-wrap: wrap; gap: 16px; margin-bottom: 28px;
    }
    .brand h1 { font-size: 1.6rem; font-weight: 700; color: #0f172a; }
    .estate-tag {
      display: inline-flex; align-items: center; margin-top: 4px;
      font-size: 0.85rem; color: var(--primary); font-weight: 500;
    }
    .month-selector {
      display: flex; align-items: center; gap: 12px;
      background: var(--card); padding: 8px 14px; border-radius: 999px;
      box-shadow: var(--shadow);
    }
    .nav-btn {
      width: 36px; height: 36px; border: none; border-radius: 50%;
      background: var(--bg); color: #334155; cursor: pointer;
      display: grid; place-items: center; transition: .15s;
    }
    .nav-btn:hover:not(:disabled) { background: var(--primary); color: white; }
    .nav-btn:disabled { opacity: 0.35; cursor: not-allowed; }
    #currentMonthDisplay { font-weight: 600; min-width: 130px; text-align: center; }

    /* Stats */
    .stats-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px; margin-bottom: 28px;
    }
    .stat-card {
      background: var(--card); border-radius: var(--radius); padding: 18px 20px;
      box-shadow: var(--shadow);
    }
    .stat-title { font-size: 0.8rem; color: var(--muted); display: flex; align-items: center; gap: 6px; }
    .stat-value { font-size: 1.45rem; font-weight: 700; margin: 6px 0 4px; }
    .stat-sub { font-size: 0.78rem; color: var(--muted); }
    .stat-sub.positive { color: var(--primary); }
    .stat-sub.warning { color: var(--warning); }

    /* Table */
    .table-section {
      background: var(--card); border-radius: var(--radius); box-shadow: var(--shadow);
      overflow: hidden;
    }
    .table-header {
      display: flex; justify-content: space-between; align-items: center;
      flex-wrap: wrap; gap: 12px; padding: 18px 20px; border-bottom: 1px solid var(--border);
    }
    .table-header h2 { font-size: 1.1rem; display: flex; align-items: center; gap: 8px; }
    .filter-badge {
      font-size: 0.8rem; color: var(--muted); background: var(--bg);
      padding: 6px 12px; border-radius: 999px;
    }
    .table-wrapper { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; }
    th {
      text-align: left; padding: 12px 16px; font-size: 0.75rem; text-transform: uppercase;
      letter-spacing: 0.04em; color: var(--muted); background: #f8fafc;
      border-bottom: 1px solid var(--border);
    }
    td { padding: 14px 16px; border-bottom: 1px solid var(--border); font-size: 0.9rem; vertical-align: middle; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #f8fafc; }

    .landlord-cell { display: flex; align-items: center; gap: 12px; }
    .avatar {
      width: 40px; height: 40px; border-radius: 50%; background: var(--primary);
      color: white; display: grid; place-items: center; font-weight: 600; font-size: 0.85rem;
      flex-shrink: 0;
    }
    .landlord-name { font-weight: 600; display: block; }
    .property { font-size: 0.78rem; color: var(--muted); }
    .amount { font-variant-numeric: tabular-nums; }
    .amount-paid { color: var(--primary); font-weight: 600; font-variant-numeric: tabular-nums; }
    .amount-due { color: var(--warning); font-weight: 500; }

    .status-badge {
      display: inline-flex; align-items: center; gap: 5px;
      padding: 4px 10px; border-radius: 999px; font-size: 0.78rem; font-weight: 600;
    }
    .status-paid { background: #d1fae5; color: #065f46; }
    .status-pending { background: #fef3c7; color: #92400e; }
    .status-due { background: #fee2e2; color: #991b1b; }

    .action-btn {
      border: 1px solid var(--border); background: white; border-radius: 8px;
      padding: 6px 12px; font-size: 0.8rem; cursor: pointer;
      display: inline-flex; align-items: center; gap: 5px; transition: .15s;
    }
    .action-btn:hover { border-color: var(--primary); color: var(--primary); }
    .action-btn.primary {
      background: var(--primary); color: white; border-color: var(--primary);
    }
    .action-btn.primary:hover { background: var(--primary-dark); }

    .no-results {
      display: none; text-align: center; padding: 48px 20px; color: var(--muted);
    }
    .no-results i { font-size: 2rem; margin-bottom: 8px; display: block; }
    .footer-note {
      padding: 12px 20px; font-size: 0.78rem; color: var(--muted);
      border-top: 1px solid var(--border); display: flex; align-items: center; gap: 6px;
    }

    /* Modal */
    .modal-overlay {
      position: fixed; inset: 0; background: rgba(15,23,42,.45);
      display: none; align-items: center; justify-content: center; z-index: 100; padding: 16px;
    }
    .modal-overlay.open { display: flex; }
    .modal {
      background: white; border-radius: 16px; width: 100%; max-width: 420px;
      box-shadow: 0 20px 50px rgba(0,0,0,.15); overflow: hidden;
    }
    .modal-header {
      padding: 18px 20px; border-bottom: 1px solid var(--border);
      display: flex; justify-content: space-between; align-items: center;
    }
    .modal-header h3 { font-size: 1.05rem; }
    .modal-close {
      border: none; background: none; font-size: 1.2rem; cursor: pointer; color: var(--muted);
    }
    .modal-body { padding: 20px; }
    .detail-row {
      display: flex; justify-content: space-between; padding: 8px 0;
      border-bottom: 1px solid #f1f5f9; font-size: 0.9rem;
    }
    .detail-row:last-child { border-bottom: none; }
    .detail-label { color: var(--muted); }
    .detail-value { font-weight: 600; }
    .modal-actions {
      padding: 16px 20px; border-top: 1px solid var(--border);
      display: flex; gap: 10px; justify-content: flex-end;
    }

    .toast {
      position: fixed; bottom: 24px; right: 24px; background: #0f172a; color: white;
      padding: 12px 20px; border-radius: 10px; font-size: 0.9rem; z-index: 200;
      animation: slideIn .3s ease;
    }
    @keyframes slideIn {
      from { opacity: 0; transform: translateY(12px); }
      to { opacity: 1; transform: none; }
    }
  </style>
</head>
<body>
  <div class="dashboard">
    <div class="header">
      <div class="brand">
        <h1>Mwarokin Estates</h1>
        <div class="estate-tag">
          <i class="fas fa-building" style="margin-right:0.3rem"></i> Landlord Payment Hub
        </div>
      </div>
      <div class="month-selector">
        <button class="nav-btn" id="prevMonthBtn" aria-label="Previous month"><i class="fas fa-chevron-left"></i></button>
        <span id="currentMonthDisplay">—</span>
        <button class="nav-btn" id="nextMonthBtn" aria-label="Next month"><i class="fas fa-chevron-right"></i></button>
      </div>
    </div>

    <div class="stats-grid" id="statsGrid"></div>

    <div class="table-section">
      <div class="table-header">
        <h2><i class="fas fa-file-invoice-dollar"></i> Landlord payment details</h2>
        <div class="filter-badge">
          <i class="fas fa-filter"></i> Monthly view · <span id="tableMonthLabel">—</span>
        </div>
      </div>
      <div class="table-wrapper">
        <table id="paymentsTable">
          <thead>
            <tr>
              <th>Landlord &amp; Property</th>
              <th>Service</th>
              <th>Amount (KES)</th>
              <th>Paid (KES)</th>
              <th>Due / Pending</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody id="tableBody"></tbody>
        </table>
        <div class="no-results" id="noResults">
          <i class="fas fa-inbox"></i>
          No payment records for this month.
        </div>
      </div>
      <div class="footer-note">
        <i class="fas fa-sync-alt"></i> Live data · Powered by FastAPI
      </div>
    </div>
  </div>

  <!-- Details Modal -->
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
    let currentYear = 2025;
    let currentMonth = 6;  // 1-12
    let range = null;

    function toast(msg) {
      const el = document.createElement('div');
      el.className = 'toast';
      el.textContent = msg;
      document.body.appendChild(el);
      setTimeout(() => el.remove(), 2800);
    }

    async function api(path, opts = {}) {
      const res = await fetch(API + path, {
        headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
        ...opts,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || res.statusText);
      }
      return res.json();
    }

    function formatKES(n) {
      return (n ?? 0).toLocaleString('en-KE');
    }

    // ----- Stats -----
    async function renderStats() {
      const s = await api(`/api/stats?year=${currentYear}&month=${currentMonth}`);
      document.getElementById('statsGrid').innerHTML = `
        <div class="stat-card">
          <div class="stat-title"><i class="fas fa-file-invoice"></i> Total billed</div>
          <div class="stat-value">KES ${formatKES(s.total_billed)}</div>
          <div class="stat-sub"><i class="fas fa-calendar-alt"></i> ${s.month_label}</div>
        </div>
        <div class="stat-card">
          <div class="stat-title"><i class="fas fa-check-circle"></i> Total paid</div>
          <div class="stat-value" style="color:var(--primary)">KES ${formatKES(s.total_paid)}</div>
          <div class="stat-sub positive"><i class="fas fa-arrow-up"></i> ${s.paid_percentage}% of billed</div>
        </div>
        <div class="stat-card">
          <div class="stat-title"><i class="fas fa-exclamation-triangle"></i> Due amount</div>
          <div class="stat-value" style="color:var(--warning)">KES ${formatKES(s.total_due)}</div>
          <div class="stat-sub warning"><i class="fas fa-clock"></i> Outstanding</div>
        </div>
        <div class="stat-card">
          <div class="stat-title"><i class="fas fa-hourglass-half"></i> Pending</div>
          <div class="stat-value" style="color:#2c7a7b">KES ${formatKES(s.total_pending)}</div>
          <div class="stat-sub"><i class="fas fa-hourglass-start"></i> Awaiting confirmation</div>
        </div>`;
    }

    // ----- Table -----
    async function renderTable() {
      const rows = await api(`/api/payments?year=${currentYear}&month=${currentMonth}`);
      const tbody = document.getElementById('tableBody');
      const noResults = document.getElementById('noResults');

      if (!rows.length) {
        tbody.innerHTML = '';
        noResults.style.display = 'block';
        return;
      }
      noResults.style.display = 'none';

      tbody.innerHTML = rows.map(r => {
        let badgeClass = 'status-paid', statusText = 'Paid', statusIcon = 'fa-check-circle';
        if (r.status === 'pending') {
          badgeClass = 'status-pending'; statusText = 'Pending'; statusIcon = 'fa-clock';
        } else if (r.status === 'due') {
          badgeClass = 'status-due'; statusText = 'Due'; statusIcon = 'fa-exclamation-circle';
        }

        let duePending = '—';
        if (r.due > 0) duePending = `<span class="amount-due">KES ${formatKES(r.due)} due</span>`;
        else if (r.pending > 0) duePending = `<span style="color:var(--warning)">KES ${formatKES(r.pending)} pending</span>`;
        else duePending = `<span style="color:var(--primary)">—</span>`;

        return `
          <tr>
            <td>
              <div class="landlord-cell">
                <div class="avatar">${r.initials}</div>
                <div>
                  <span class="landlord-name">${r.name}</span>
                  <span class="property"><i class="fas fa-map-pin"></i> ${r.property}</span>
                </div>
              </div>
            </td>
            <td>${r.service}</td>
            <td class="amount">KES ${formatKES(r.amount)}</td>
            <td class="amount-paid">KES ${formatKES(r.paid)}</td>
            <td>${duePending}</td>
            <td><span class="status-badge ${badgeClass}"><i class="fas ${statusIcon}"></i> ${statusText}</span></td>
            <td>
              <button class="action-btn" onclick="openDetails(${r.id})">
                <i class="fas fa-receipt"></i> Details
              </button>
            </td>
          </tr>`;
      }).join('');
    }

    // ----- Modal -----
    async function openDetails(landlordId) {
      try {
        const d = await api(`/api/landlords/${landlordId}/payments/${currentYear}/${currentMonth}`);
        const ll = d.landlord;
        const rec = d.record;

        document.getElementById('modalTitle').textContent = `${ll.name} · ${d.month_label}`;
        document.getElementById('modalBody').innerHTML = `
          <div class="detail-row"><span class="detail-label">Property</span><span class="detail-value">${ll.property}</span></div>
          <div class="detail-row"><span class="detail-label">Service</span><span class="detail-value">${ll.service}</span></div>
          <div class="detail-row"><span class="detail-label">Billed</span><span class="detail-value">KES ${formatKES(ll.amount)}</span></div>
          <div class="detail-row"><span class="detail-label">Paid</span><span class="detail-value" style="color:var(--primary)">KES ${formatKES(rec.paid)}</span></div>
          <div class="detail-row"><span class="detail-label">Due</span><span class="detail-value" style="color:var(--warning)">KES ${formatKES(rec.due)}</span></div>
          <div class="detail-row"><span class="detail-label">Pending</span><span class="detail-value">KES ${formatKES(rec.pending)}</span></div>
          <div class="detail-row"><span class="detail-label">Status</span><span class="detail-value">${rec.status}</span></div>`;

        const actions = document.getElementById('modalActions');
        actions.innerHTML = '';
        if (rec.status !== 'paid') {
          const remaining = rec.due + rec.pending || (ll.amount - rec.paid);
          if (remaining > 0) {
            actions.innerHTML = `
              <button class="action-btn" onclick="closeModal()">Close</button>
              <button class="action-btn primary" onclick="recordFullPayment(${ll.id})">
                <i class="fas fa-check"></i> Mark fully paid
              </button>`;
          } else {
            actions.innerHTML = `<button class="action-btn" onclick="closeModal()">Close</button>`;
          }
        } else {
          actions.innerHTML = `<button class="action-btn" onclick="closeModal()">Close</button>`;
        }

        document.getElementById('modalOverlay').classList.add('open');
      } catch (e) {
        toast('⚠️ ' + e.message);
      }
    }

    function closeModal() {
      document.getElementById('modalOverlay').classList.remove('open');
    }

    async function recordFullPayment(landlordId) {
      try {
        await api(`/api/landlords/${landlordId}/payments/${currentYear}/${currentMonth}/mark-paid`, {
          method: 'POST',
        });
        toast('✅ Marked as fully paid');
        closeModal();
        await refreshUI();
      } catch (e) {
        toast('⚠️ ' + e.message);
      }
    }

    // ----- Navigation -----
    function updateNavButtons() {
      const prev = document.getElementById('prevMonthBtn');
      const next = document.getElementById('nextMonthBtn');
      if (!range) return;

      const atMin = currentYear === range.min_year && currentMonth === range.min_month;
      const atMax = currentYear === range.max_year && currentMonth === range.max_month;
      prev.disabled = atMin;
      next.disabled = atMax;
    }

    async function goPrev() {
      if (currentMonth === 1) { currentMonth = 12; currentYear--; }
      else currentMonth--;
      await refreshUI();
    }

    async function goNext() {
      if (currentMonth === 12) { currentMonth = 1; currentYear++; }
      else currentMonth++;
      await refreshUI();
    }

    async function refreshUI() {
      try {
        const s = await api(`/api/stats?year=${currentYear}&month=${currentMonth}`);
        document.getElementById('currentMonthDisplay').textContent = s.month_label;
        document.getElementById('tableMonthLabel').textContent = s.month_label;
        await Promise.all([renderStats(), renderTable()]);
        updateNavButtons();
      } catch (e) {
        toast('⚠️ ' + e.message);
        // revert month if out of range
        if (e.message.includes('out of available')) {
          // stay put
        }
      }
    }

    // ----- Init -----
    async function init() {
      range = await api('/api/range');
      currentYear = range.current_year;
      currentMonth = range.current_month;

      document.getElementById('prevMonthBtn').addEventListener('click', goPrev);
      document.getElementById('nextMonthBtn').addEventListener('click', goNext);
      document.getElementById('modalClose').addEventListener('click', closeModal);
      document.getElementById('modalOverlay').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeModal();
      });

      await refreshUI();
      console.log('🔌 Landlord Payment Hub loaded (real API)');
    }

    document.addEventListener('DOMContentLoaded', init);
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    return FRONTEND_HTML


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### What is real

| Feature | Behaviour |
|---------|-----------|
| **Month navigation** | Bounded April–July 2025; prev/next disabled at edges |
| **Stats** | Aggregated live from landlord records for the selected month |
| **Payments table** | Fetched per month; status, paid/due/pending computed server-side |
| **Details modal** | Loads full payment record for landlord + month |
| **Mark fully paid** | `POST …/mark-paid` updates the in-memory record; stats & table refresh immediately |
| **Record partial payment** | Extra endpoint `POST …/record` with `{ "amount": N }` (available for further UI) |

### Run

```bash
pip install fastapi "uvicorn[standard]" pydantic
# save as main.py
uvicorn main:app --reload --port 8000
```

Open **http://127.0.0.1:8000** — the UI talks only to the Python backend.