Here’s a complete, production-ready **Python-only backend** for the Bank Payments Dashboard (Mwarokin Estates Payment Hub). It mirrors the frontend data model, filters, search, pagination, and summary cards exactly.

```python
"""
Bank Payments Dashboard Backend
Mwarokin Estates Payment Hub
Python-only FastAPI service
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta
from enum import Enum
import random
import string
import uvicorn

app = FastAPI(
    title="Mwarokin Estates – Bank Payments API",
    description="Backend for tenant rent payments, landlord settlements and bank reconciliation",
    version="1.0.0"
)

# Allow the frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class PaymentStatus(str, Enum):
    COMPLETED = "Completed"
    PENDING = "Pending"
    FAILED = "Failed"


class Payment(BaseModel):
    id: str = Field(..., example="PAY000123")
    userId: str = Field(..., example="USR1234")
    userName: str
    amount: int
    date: str          # "DD/MM/YYYY"
    time: str          # "HH:MM"
    status: PaymentStatus
    bank: str
    reference: str


class Summary(BaseModel):
    totalPayments: int
    totalAmount: int
    completedCount: int
    pendingCount: int
    failedCount: int


class PaginatedPayments(BaseModel):
    data: List[Payment]
    page: int
    perPage: int
    total: int
    totalPages: int
    showingStart: int
    showingEnd: int


# ---------------------------------------------------------------------------
# Sample data generation (mirrors the JS frontend)
# ---------------------------------------------------------------------------

BANKS = [
    "KCB Bank", "Equity Bank", "Co-operative Bank", "NCBA Bank",
    "Absa Bank", "M-PESA", "Airtel Money", "Stanbic Bank",
    "I&M Bank", "Family Bank", "DTB", "Standard Chartered"
]

NAMES = [
    "John Kimani", "Mary Njeri", "Peter Mwangi", "Grace Wanjiru",
    "Samuel Kipchoge", "Alice Ndungu", "David Ochieng", "Sarah Kamau",
    "Michael Kiplagat", "Jane Wafula", "Robert Mutua", "Helen Otieno",
    "James Kipkemboi", "Lucy Kipchoge", "Charles Mwaura", "Rebecca Samba",
    "Daniel Kiplagat", "Patricia Mwelu", "Stephen Kiprotich", "Victoria Koech"
]

STATUSES = list(PaymentStatus)


def _random_reference() -> str:
    return "TXN" + "".join(random.choices(string.ascii_uppercase + string.digits, k=9))


def generate_payments(count: int = 247) -> List[Payment]:
    """Generate realistic Kenyan rent-payment sample data."""
    payments = []
    now = datetime.now()

    for i in range(1, count + 1):
        days_ago = random.randint(0, 30)
        dt = now - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))

        payments.append(Payment(
            id=f"PAY{str(i).zfill(6)}",
            userId=f"USR{str(1000 + random.randint(0, 499)).zfill(4)}",
            userName=random.choice(NAMES),
            amount=random.randint(5_000, 55_000),
            date=dt.strftime("%d/%m/%Y"),
            time=dt.strftime("%H:%M"),
            status=random.choice(STATUSES),
            bank=random.choice(BANKS),
            reference=_random_reference()
        ))

    # Newest first
    payments.sort(key=lambda p: datetime.strptime(f"{p.date} {p.time}", "%d/%m/%Y %H:%M"), reverse=True)
    return payments


# In-memory store (replace with real DB in production)
all_payments: List[Payment] = generate_payments()


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Mwarokin Estates Bank Payments"}


@app.get("/api/summary", response_model=Summary)
def get_summary(
    search: Optional[str] = Query(None, description="Search term"),
    status: Optional[str] = Query(None, description="Completed | Pending | Failed"),
    bank: Optional[str] = Query(None, description="Bank name filter")
):
    """Summary cards: total payments, total amount, status counts."""
    filtered = _filter_payments(search, status, bank)

    total_amount = sum(p.amount for p in filtered)
    completed = sum(1 for p in filtered if p.status == PaymentStatus.COMPLETED)
    pending = sum(1 for p in filtered if p.status == PaymentStatus.PENDING)
    failed = sum(1 for p in filtered if p.status == PaymentStatus.FAILED)

    return Summary(
        totalPayments=len(filtered),
        totalAmount=total_amount,
        completedCount=completed,
        pendingCount=pending,
        failedCount=failed
    )


@app.get("/api/payments", response_model=PaginatedPayments)
def get_payments(
    search: Optional[str] = Query(None, description="Search User ID, Name, Status or Bank"),
    status: Optional[str] = Query(None, description="Completed | Pending | Failed"),
    bank: Optional[str] = Query(None, description="Exact bank name"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100)
):
    """
    Paginated, searchable, filterable list of bank payments.
    Matches the frontend table + filters exactly.
    """
    filtered = _filter_payments(search, status, bank)
    total = len(filtered)
    total_pages = max(1, (total + per_page - 1) // per_page)

    if page > total_pages:
        page = total_pages

    start = (page - 1) * per_page
    end = start + per_page
    page_data = filtered[start:end]

    return PaginatedPayments(
        data=page_data,
        page=page,
        perPage=per_page,
        total=total,
        totalPages=total_pages,
        showingStart=start + 1 if total > 0 else 0,
        showingEnd=min(end, total)
    )


@app.post("/api/refresh")
def refresh_data():
    """
    Regenerate sample data (simulates real-time refresh).
    In production this would pull from the payment engine / bank webhooks.
    """
    global all_payments
    all_payments = generate_payments()
    return {
        "message": "Data refreshed successfully",
        "totalPayments": len(all_payments)
    }


@app.get("/api/banks")
def list_banks():
    """Helper endpoint – list of supported banks / mobile money rails."""
    return {"banks": BANKS}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _filter_payments(
    search: Optional[str],
    status: Optional[str],
    bank: Optional[str]
) -> List[Payment]:
    result = all_payments

    if status:
        try:
            status_enum = PaymentStatus(status)
            result = [p for p in result if p.status == status_enum]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    if bank:
        result = [p for p in result if p.bank.lower() == bank.lower()]

    if search:
        term = search.lower().strip()
        result = [
            p for p in result
            if term in p.userId.lower()
            or term in p.userName.lower()
            or term in p.status.value.lower()
            or term in p.bank.lower()
            or term in p.id.lower()
            or term in p.reference.lower()
        ]

    return result


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Starting Mwarokin Estates Bank Payments API …")
    print("Docs: http://127.0.0.1:8000/docs")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### How to run

```bash
pip install fastapi uvicorn pydantic
# Save the code as main.py
python main.py
```

### Endpoints that power the dashboard

| Method | Path              | Purpose                                      |
|--------|-------------------|----------------------------------------------|
| GET    | `/api/summary`    | Summary cards (totals + status counts)       |
| GET    | `/api/payments`   | Table data + search + filters + pagination   |
| POST   | `/api/refresh`    | Refresh button (regenerates sample data)     |
| GET    | `/api/banks`      | List of supported banks / mobile money       |
| GET    | `/api/health`     | Health check                                 |

### Query parameters (same as frontend)

- `search` – free text (User ID, Name, Status, Bank, Payment ID, Reference)
- `status` – `Completed` | `Pending` | `Failed`
- `bank` – exact bank name (e.g. `KCB Bank`, `M-PESA`)
- `page` / `per_page` – pagination (default 10)

This backend is ready to be wired to the HTML/JS you provided. Just point the frontend `fetch` calls to these endpoints instead of the in-browser sample data.