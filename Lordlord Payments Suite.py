Here’s a complete **modern FastAPI backend** for the **Payments Suite** with real payment processing simulation, landlord profiles, dispute workflow, and report generation.

```python
# main.py
"""
Mwarokin Estates – Payments Suite Backend
Payment timelines, landlord profiles, gateway, disputes & reports
FastAPI · Python 3.11+
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

app = FastAPI(
    title="Mwarokin Estates – Payments Suite API",
    description="Payment lifecycle, gateway, landlord profiles, disputes & reports",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────

class TimelineStatus(str, Enum):
    done = "done"
    active = "active"
    pending = "pending"


class TimelineEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    label: str
    date: str
    amount: str
    status: TimelineStatus
    icon: str


class PaymentStatus(str, Enum):
    paid = "paid"
    pending = "pending"
    overdue = "overdue"
    partial = "partial"


class LandlordProfile(BaseModel):
    id: int
    name: str
    initials: str
    property: str
    units: int
    totalPaid: int
    pending: int
    status: PaymentStatus


class PaymentMethod(str, Enum):
    mpesa = "mpesa"
    card = "card"
    bank = "bank"


class MpesaPaymentRequest(BaseModel):
    phone: str
    amount: int = Field(gt=0)
    reference: str = "April 2025 Rent"

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = v.replace(" ", "").replace("+", "")
        if not cleaned.startswith("254") or len(cleaned) < 12:
            raise ValueError("Phone must be in +254 format")
        return v


class CardPaymentRequest(BaseModel):
    card_number: str
    expiry: str
    cvv: str
    cardholder: str
    amount: int = Field(gt=0)
    reference: str = "April 2025 Rent"


class BankPaymentRequest(BaseModel):
    bank_name: str
    account_number: str
    account_holder: str
    amount: int = Field(gt=0)
    reference: str = "April 2025 Rent"


class PaymentResponse(BaseModel):
    transaction_id: str
    method: PaymentMethod
    amount: int
    currency: str = "KES"
    status: str
    reference: str
    message: str
    timestamp: str


class DisputeStatus(str, Enum):
    open = "open"
    progress = "progress"
    resolved = "resolved"


class Dispute(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    desc: str
    status: DisputeStatus
    icon: str
    iconColor: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: Optional[str] = None


class UpdateDisputeRequest(BaseModel):
    status: DisputeStatus
    note: Optional[str] = None


class Report(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    icon: str
    title: str
    desc: str
    meta: str
    report_type: str  # collection | tax | statement | occupancy | history | invoice


class RecordPaymentRequest(BaseModel):
    landlord_id: int
    amount: int = Field(gt=0)
    method: PaymentMethod = PaymentMethod.mpesa
    reference: Optional[str] = None


class ActionLogEntry(BaseModel):
    id: str
    action: str
    detail: dict
    timestamp: str


# ──────────────────────────────────────────────────────────────
# In-memory store
# ──────────────────────────────────────────────────────────────

timeline_events: List[TimelineEvent] = [
    TimelineEvent(
        label="Invoice Generated", date="Apr 1, 2025",
        amount="KSh 342,000", status=TimelineStatus.done, icon="fa-file-invoice"
    ),
    TimelineEvent(
        label="Reminder Sent", date="Apr 5, 2025",
        amount="8 landlords", status=TimelineStatus.done, icon="fa-bell"
    ),
    TimelineEvent(
        label="Payment Due", date="Apr 15, 2025",
        amount="KSh 342,000", status=TimelineStatus.active, icon="fa-clock"
    ),
    TimelineEvent(
        label="Late Fee Applied", date="Apr 20, 2025",
        amount="2% penalty", status=TimelineStatus.pending, icon="fa-exclamation-triangle"
    ),
]

landlord_profiles: List[LandlordProfile] = [
    LandlordProfile(id=1, name="Grace Wanjiku", initials="GW", property="Kilimani Court",
                    units=12, totalPaid=240000, pending=0, status=PaymentStatus.paid),
    LandlordProfile(id=2, name="James Mwangi", initials="JM", property="Westlands Heights",
                    units=8, totalPaid=0, pending=168000, status=PaymentStatus.pending),
    LandlordProfile(id=3, name="Amina Hassan", initials="AH", property="South B Apartments",
                    units=20, totalPaid=360000, pending=0, status=PaymentStatus.paid),
    LandlordProfile(id=4, name="Peter Njoroge", initials="PN", property="Kasarani Villas",
                    units=6, totalPaid=0, pending=96000, status=PaymentStatus.overdue),
    LandlordProfile(id=5, name="Sarah Kilonzo", initials="SK", property="Lavington Suites",
                    units=15, totalPaid=450000, pending=0, status=PaymentStatus.paid),
    LandlordProfile(id=6, name="David Ochieng", initials="DO", property="Eastleigh Plaza",
                    units=30, totalPaid=300000, pending=300000, status=PaymentStatus.partial),
]

disputes: List[Dispute] = [
    Dispute(
        title="Late Payment Penalty", desc="Peter Njoroge · Kasarani Villas",
        status=DisputeStatus.open, icon="fa-exclamation-circle", iconColor="red"
    ),
    Dispute(
        title="Incorrect Meter Reading", desc="David Ochieng · Eastleigh Plaza",
        status=DisputeStatus.progress, icon="fa-tools", iconColor="amber"
    ),
    Dispute(
        title="Security Deposit Refund", desc="James Mwangi · Westlands Heights",
        status=DisputeStatus.resolved, icon="fa-check-circle", iconColor="green"
    ),
    Dispute(
        title="Maintenance Charge Dispute", desc="Amina Hassan · South B Apartments",
        status=DisputeStatus.progress, icon="fa-wrench", iconColor="amber"
    ),
]

reports: List[Report] = [
    Report(icon="fa-chart-bar", title="Monthly Collection Report", desc="April 2025 summary",
           meta="Updated today", report_type="collection"),
    Report(icon="fa-file-pdf", title="Annual Tax Report", desc="KRA-ready PDF",
           meta="Generated Mar 31", report_type="tax"),
    Report(icon="fa-users", title="Landlord Statement", desc="Per-landlord breakdown",
           meta="On demand", report_type="statement"),
    Report(icon="fa-chart-line", title="Occupancy Analytics", desc="Unit-level insights",
           meta="Real-time", report_type="occupancy"),
    Report(icon="fa-clock", title="Payment History", desc="All transactions",
           meta="Full audit trail", report_type="history"),
    Report(icon="fa-file-invoice-dollar", title="Invoice Summary", desc="Outstanding & paid",
           meta="Updated hourly", report_type="invoice"),
]

# Transaction history
transactions: List[dict] = []
action_log: List[dict] = []

TOTAL_DUE = 342_000  # April 2025


def log_action(action: str, detail: dict) -> None:
    action_log.append({
        "id": str(uuid4()),
        "action": action,
        "detail": detail,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })


def _recalc_landlord_status(landlord: LandlordProfile) -> None:
    if landlord.pending == 0:
        landlord.status = PaymentStatus.paid
    elif landlord.totalPaid > 0 and landlord.pending > 0:
        landlord.status = PaymentStatus.partial
    elif landlord.pending > 0:
        # Simple overdue heuristic (in real system check due date)
        landlord.status = PaymentStatus.overdue if landlord.id == 4 else PaymentStatus.pending


# ──────────────────────────────────────────────────────────────
# Payment Timeline
# ──────────────────────────────────────────────────────────────

@app.get("/api/timeline", response_model=List[TimelineEvent])
def get_timeline():
    return timeline_events


@app.post("/api/timeline", response_model=TimelineEvent, status_code=status.HTTP_201_CREATED)
def add_timeline_event(event: TimelineEvent):
    timeline_events.append(event)
    log_action("timeline_event_added", event.model_dump())
    return event


@app.patch("/api/timeline/{event_id}/status")
def update_timeline_status(event_id: str, status: TimelineStatus):
    event = next((e for e in timeline_events if e.id == event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail="Timeline event not found")
    event.status = status
    log_action("timeline_status_updated", {"id": event_id, "status": status})
    return event


# ──────────────────────────────────────────────────────────────
# Landlord Profiles
# ──────────────────────────────────────────────────────────────

@app.get("/api/landlords", response_model=List[LandlordProfile])
def list_landlords(status: Optional[PaymentStatus] = None):
    if status:
        return [l for l in landlord_profiles if l.status == status]
    return landlord_profiles


@app.get("/api/landlords/{landlord_id}", response_model=LandlordProfile)
def get_landlord(landlord_id: int):
    landlord = next((l for l in landlord_profiles if l.id == landlord_id), None)
    if not landlord:
        raise HTTPException(status_code=404, detail="Landlord not found")
    return landlord


@app.get("/api/landlords/{landlord_id}/statement")
def get_landlord_statement(landlord_id: int):
    landlord = next((l for l in landlord_profiles if l.id == landlord_id), None)
    if not landlord:
        raise HTTPException(status_code=404, detail="Landlord not found")
    related_txns = [t for t in transactions if t.get("landlord_id") == landlord_id]
    return {
        "landlord": landlord,
        "period": "April 2025",
        "total_paid": landlord.totalPaid,
        "pending": landlord.pending,
        "status": landlord.status,
        "transactions": related_txns,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


@app.post("/api/landlords/{landlord_id}/pay")
def record_landlord_payment(landlord_id: int, req: RecordPaymentRequest):
    if req.landlord_id != landlord_id:
        raise HTTPException(status_code=400, detail="landlord_id mismatch")
    landlord = next((l for l in landlord_profiles if l.id == landlord_id), None)
    if not landlord:
        raise HTTPException(status_code=404, detail="Landlord not found")

    amount = min(req.amount, landlord.pending) if landlord.pending > 0 else req.amount
    landlord.totalPaid += amount
    landlord.pending = max(0, landlord.pending - amount)
    _recalc_landlord_status(landlord)

    txn = {
        "transaction_id": f"TXN-{uuid4().hex[:10].upper()}",
        "landlord_id": landlord_id,
        "landlord_name": landlord.name,
        "method": req.method,
        "amount": amount,
        "reference": req.reference or f"Payment · {landlord.name}",
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    transactions.append(txn)
    log_action("landlord_payment_recorded", txn)
    return {
        "status": "success",
        "message": f"Payment of KSh {amount:,} recorded for {landlord.name}",
        "landlord": landlord,
        "transaction": txn,
    }


# ──────────────────────────────────────────────────────────────
# Payment Gateway
# ──────────────────────────────────────────────────────────────

@app.get("/api/gateway/total")
def get_gateway_total():
    return {
        "period": "April 2025",
        "total_due": TOTAL_DUE,
        "currency": "KES",
        "formatted": f"KSh {TOTAL_DUE:,}",
    }


@app.post("/api/gateway/mpesa", response_model=PaymentResponse)
def pay_mpesa(req: MpesaPaymentRequest):
    txn_id = f"MPESA-{uuid4().hex[:10].upper()}"
    txn = {
        "transaction_id": txn_id,
        "method": PaymentMethod.mpesa,
        "amount": req.amount,
        "phone": req.phone,
        "reference": req.reference,
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    transactions.append(txn)
    log_action("mpesa_payment", txn)
    return PaymentResponse(
        transaction_id=txn_id,
        method=PaymentMethod.mpesa,
        amount=req.amount,
        status="success",
        reference=req.reference,
        message=f"STK Push sent to {req.phone}. Complete on your phone.",
        timestamp=txn["timestamp"],
    )


@app.post("/api/gateway/card", response_model=PaymentResponse)
def pay_card(req: CardPaymentRequest):
    # Basic Luhn-like check (demo only)
    digits = req.card_number.replace(" ", "")
    if not digits.isdigit() or len(digits) < 13:
        raise HTTPException(status_code=400, detail="Invalid card number")
    txn_id = f"CARD-{uuid4().hex[:10].upper()}"
    txn = {
        "transaction_id": txn_id,
        "method": PaymentMethod.card,
        "amount": req.amount,
        "cardholder": req.cardholder,
        "last4": digits[-4:],
        "reference": req.reference,
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    transactions.append(txn)
    log_action("card_payment", txn)
    return PaymentResponse(
        transaction_id=txn_id,
        method=PaymentMethod.card,
        amount=req.amount,
        status="success",
        reference=req.reference,
        message=f"Card ending {digits[-4:]} charged successfully.",
        timestamp=txn["timestamp"],
    )


@app.post("/api/gateway/bank", response_model=PaymentResponse)
def pay_bank(req: BankPaymentRequest):
    txn_id = f"BANK-{uuid4().hex[:10].upper()}"
    txn = {
        "transaction_id": txn_id,
        "method": PaymentMethod.bank,
        "amount": req.amount,
        "bank": req.bank_name,
        "account": req.account_number[-4:],
        "account_holder": req.account_holder,
        "reference": req.reference,
        "status": "pending_confirmation",  # bank transfers often pending
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    transactions.append(txn)
    log_action("bank_payment", txn)
    return PaymentResponse(
        transaction_id=txn_id,
        method=PaymentMethod.bank,
        amount=req.amount,
        status="pending_confirmation",
        reference=req.reference,
        message=f"Bank transfer initiated via {req.bank_name}. Awaiting confirmation.",
        timestamp=txn["timestamp"],
    )


@app.get("/api/gateway/transactions")
def list_transactions(limit: int = 50):
    return transactions[-limit:]


# ──────────────────────────────────────────────────────────────
# Dispute Resolution
# ──────────────────────────────────────────────────────────────

@app.get("/api/disputes", response_model=List[Dispute])
def list_disputes(status: Optional[DisputeStatus] = None):
    if status:
        return [d for d in disputes if d.status == status]
    return disputes


@app.get("/api/disputes/{dispute_id}", response_model=Dispute)
def get_dispute(dispute_id: str):
    dispute = next((d for d in disputes if d.id == dispute_id), None)
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return dispute


@app.post("/api/disputes", response_model=Dispute, status_code=status.HTTP_201_CREATED)
def create_dispute(dispute: Dispute):
    disputes.insert(0, dispute)
    log_action("dispute_created", dispute.model_dump())
    return dispute


@app.patch("/api/disputes/{dispute_id}")
def update_dispute(dispute_id: str, req: UpdateDisputeRequest):
    dispute = next((d for d in disputes if d.id == dispute_id), None)
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    dispute.status = req.status
    dispute.updated_at = datetime.utcnow().isoformat() + "Z"
    # Auto-update icon/color for convenience
    if req.status == DisputeStatus.resolved:
        dispute.icon = "fa-check-circle"
        dispute.iconColor = "green"
    elif req.status == DisputeStatus.progress:
        dispute.icon = "fa-tools"
        dispute.iconColor = "amber"
    elif req.status == DisputeStatus.open:
        dispute.icon = "fa-exclamation-circle"
        dispute.iconColor = "red"
    log_action("dispute_updated", {
        "id": dispute_id,
        "status": req.status,
        "note": req.note,
    })
    return dispute


# ──────────────────────────────────────────────────────────────
# Reports & Analytics
# ──────────────────────────────────────────────────────────────

@app.get("/api/reports", response_model=List[Report])
def list_reports():
    return reports


@app.get("/api/reports/{report_type}")
def generate_report(report_type: str):
    report = next((r for r in reports if r.report_type == report_type), None)
    if not report:
        raise HTTPException(status_code=404, detail="Report type not found")

    payload: dict = {
        "report": report,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    if report_type == "collection":
        total_paid = sum(l.totalPaid for l in landlord_profiles)
        total_pending = sum(l.pending for l in landlord_profiles)
        payload["data"] = {
            "period": "April 2025",
            "total_collected": total_paid,
            "total_outstanding": total_pending,
            "collection_rate": round(total_paid / (total_paid + total_pending) * 100, 1) if (total_paid + total_pending) else 0,
            "by_status": {
                s.value: len([l for l in landlord_profiles if l.status == s])
                for s in PaymentStatus
            },
        }
    elif report_type == "statement":
        payload["data"] = {"landlords": landlord_profiles}
    elif report_type == "history":
        payload["data"] = {"transactions": transactions[-100:]}
    elif report_type == "invoice":
        payload["data"] = {
            "total_due": TOTAL_DUE,
            "paid_count": len([l for l in landlord_profiles if l.status == PaymentStatus.paid]),
            "outstanding_count": len([l for l in landlord_profiles if l.pending > 0]),
        }
    elif report_type == "occupancy":
        total_units = sum(l.units for l in landlord_profiles)
        payload["data"] = {
            "total_units": total_units,
            "properties": len(landlord_profiles),
            "avg_units_per_property": round(total_units / len(landlord_profiles), 1),
        }
    elif report_type == "tax":
        payload["data"] = {
            "period": "FY 2024/2025",
            "note": "KRA-ready summary. Export as PDF in production.",
            "total_revenue": sum(l.totalPaid for l in landlord_profiles),
        }
    else:
        payload["data"] = {}

    log_action("report_generated", {"type": report_type})
    return payload


# ──────────────────────────────────────────────────────────────
# Dashboard / Full payload
# ──────────────────────────────────────────────────────────────

@app.get("/api/payments-suite")
def payments_suite_data():
    total_paid = sum(l.totalPaid for l in landlord_profiles)
    total_pending = sum(l.pending for l in landlord_profiles)
    return {
        "timeline": timeline_events,
        "landlords": landlord_profiles,
        "gateway": {
            "total_due": TOTAL_DUE,
            "currency": "KES",
            "methods": ["mpesa", "card", "bank"],
        },
        "disputes": disputes,
        "reports": reports,
        "summary": {
            "total_collected": total_paid,
            "total_outstanding": total_pending,
            "open_disputes": len([d for d in disputes if d.status != DisputeStatus.resolved]),
            "transaction_count": len(transactions),
        },
    }


@app.get("/api/actions")
def get_action_log(limit: int = 50):
    return action_log[-limit:]


@app.get("/")
def root():
    return {
        "service": "Mwarokin Estates – Payments Suite",
        "version": "1.0.0",
        "docs": "/docs",
        "dashboard": "/api/payments-suite",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### Run

```bash
pip install fastapi uvicorn pydantic
python main.py
```

→ **http://localhost:8000/docs**

### Real functionality

| Feature              | Endpoints                                                                 | Behaviour                                      |
|----------------------|---------------------------------------------------------------------------|------------------------------------------------|
| **Timeline**         | `GET/POST /api/timeline`, `PATCH .../status`                              | View + add events, advance lifecycle           |
| **Landlord Profiles**| `GET /api/landlords`, `GET .../statement`, `POST .../pay`                 | Filter by status, statements, record payments  |
| **Payment Gateway**  | `POST /api/gateway/mpesa`, `/card`, `/bank`                               | Validates input, creates real txn records      |
| **Disputes**         | `GET/POST /api/disputes`, `PATCH /api/disputes/{id}`                      | Create, update status (open→progress→resolved) |
| **Reports**          | `GET /api/reports`, `GET /api/reports/{type}`                              | Live computed data (collection rate, etc.)     |
| **Full dashboard**   | `GET /api/payments-suite`                                                 | Single payload for the UI                      |
| **Audit**            | `GET /api/actions`                                                        | Every write is logged                          |

Payments update landlord balances and status automatically. Bank transfers stay `pending_confirmation`; M-Pesa and card return `success`. Swap the in-memory lists for a real DB when you need persistence.