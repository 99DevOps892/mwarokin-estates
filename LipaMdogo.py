```python
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
import json
from pathlib import Path
import uuid


class Amenity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    cost: float = Field(ge=0)


class Payment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: str  # "DD MMM YYYY"
    day: int
    amount: float = Field(gt=0)
    method: str
    balance_after: float


class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    amount: float
    tenant: str
    time: str  # "HH:MM · DD MMM"


class LipaMdogoState(BaseModel):
    tenant_name: str = ""
    account_no: str = ""
    bill_month: str  # YYYY-MM
    base_rent: float = Field(default=0, ge=0)
    amenities: List[Amenity] = Field(default_factory=list)
    carry_over: float = Field(default=0, ge=0)
    total_due: float = Field(default=0, ge=0)
    paid: float = Field(default=0, ge=0)
    payments: List[Payment] = Field(default_factory=list)
    notifications: List[Notification] = Field(default_factory=list)

    @field_validator('bill_month')
    @classmethod
    def validate_month(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m")
            return v
        except ValueError:
            raise ValueError("bill_month must be in YYYY-MM format")


class LipaMdogoCalculator:
    """Modern, premium backend service for Lipa Mdogo Mdogo payments."""

    def __init__(self, storage_path: str = "lipa_mdogo_data.json"):
        self.storage_path = Path(storage_path)
        self.state: LipaMdogoState = self._load_state()

    def _load_state(self) -> LipaMdogoState:
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return LipaMdogoState.model_validate(data)
            except Exception:
                pass
        # Default state
        default_month = datetime.now().strftime("%Y-%m")
        return LipaMdogoState(bill_month=default_month)

    def _save_state(self):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            f.write(self.state.model_dump_json(indent=2))

    def fmt(self, amount: float) -> str:
        """Format amount in Kenyan Shillings."""
        return f"KSh {round(amount):,}"

    def calculate_totals(self) -> Dict[str, Any]:
        """Recalculate all totals."""
        amenities_sum = sum(a.cost for a in self.state.amenities)
        self.state.total_due = self.state.base_rent + amenities_sum + self.state.carry_over
        return {
            "base_rent": self.state.base_rent,
            "amenities": amenities_sum,
            "carry_over": self.state.carry_over,
            "total_due": self.state.total_due,
            "paid": self.state.paid,
            "remaining": max(self.state.total_due - self.state.paid, 0)
        }

    def save_setup(
        self,
        tenant_name: str,
        account_no: str,
        bill_month: str,
        base_rent: float,
        amenities: List[Dict[str, Any]],
        carry_over: float = 0
    ) -> Dict[str, Any]:
        """Save monthly setup."""
        self.state.tenant_name = tenant_name.strip()
        self.state.account_no = account_no.strip()
        self.state.bill_month = bill_month
        self.state.base_rent = float(base_rent)
        self.state.carry_over = float(carry_over)

        self.state.amenities = [
            Amenity(name=a["name"].strip(), cost=float(a["cost"])) 
            for a in amenities if a.get("name") and float(a.get("cost", 0)) > 0
        ]

        totals = self.calculate_totals()
        self.state.paid = 0.0  # Reset paid when new setup (or carry handled separately)
        self.state.payments.clear()
        self.state.notifications.clear()

        self._save_state()
        return {
            "success": True,
            "totals": totals,
            "message": "Rent setup saved successfully."
        }

    def add_payment(self, amount: float, method: str = "M-Pesa") -> Dict[str, Any]:
        """Record a new payment contribution."""
        if self.state.total_due <= 0:
            return {"success": False, "message": "Please set up rent first."}

        remaining = max(self.state.total_due - self.state.paid, 0)
        if remaining <= 0:
            return {"success": False, "message": "Balance already cleared."}

        applied = min(amount, remaining)
        self.state.paid += applied

        now = datetime.now()
        payment = Payment(
            date=now.strftime("%d %b %Y"),
            day=now.day,
            amount=applied,
            method=method,
            balance_after=max(self.state.total_due - self.state.paid, 0)
        )
        self.state.payments.append(payment)

        # Notification
        notification = Notification(
            amount=applied,
            tenant=self.state.tenant_name or "Tenant",
            time=now.strftime("%H:%M · %d %b")
        )
        self.state.notifications.append(notification)

        totals = self.calculate_totals()
        self._save_state()

        return {
            "success": True,
            "payment": payment.model_dump(),
            "totals": totals,
            "message": "Payment recorded successfully."
        }

    def start_new_month(self) -> Dict[str, Any]:
        """Carry over remaining balance to next month."""
        remaining = max(self.state.total_due - self.state.paid, 0)
        
        # Advance month
        y, m = map(int, self.state.bill_month.split('-'))
        next_month = datetime(y, m, 1)
        next_month = next_month.replace(month=next_month.month % 12 + 1)
        if next_month.month == 1:
            next_month = next_month.replace(year=next_month.year + 1)
        
        self.state.carry_over = remaining
        self.state.base_rent = 0
        self.state.amenities.clear()
        self.state.paid = 0
        self.state.payments.clear()
        self.state.notifications.clear()
        self.state.bill_month = next_month.strftime("%Y-%m")
        self.state.total_due = remaining

        self._save_state()
        return {
            "success": True,
            "new_month": self.state.bill_month,
            "carry_over": remaining,
            "message": "New month started with remaining balance carried over."
        }

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Full dashboard data for UI consumption."""
        totals = self.calculate_totals()
        remaining = totals["remaining"]

        # Calendar info
        y, m = map(int, self.state.bill_month.split('-'))
        first_day = datetime(y, m, 1)
        days_in_month = (first_day.replace(month=m % 12 + 1) - first_day).days if m < 12 else 31
        
        paid_days = {p.day for p in self.state.payments}
        is_current_month = (datetime.now().year == y and datetime.now().month == m)
        
        # Progress
        progress_pct = round((totals["paid"] / totals["total_due"] * 100) if totals["total_due"] > 0 else 0)

        # Suggested daily
        days_left = days_in_month
        if is_current_month:
            days_left = max(days_in_month - datetime.now().day + 1, 1)
        
        suggested_daily = round(remaining / days_left) if remaining > 0 and days_left > 0 else 0

        return {
            "tenant_name": self.state.tenant_name,
            "account_no": self.state.account_no,
            "bill_month": self.state.bill_month,
            "totals": totals,
            "progress_pct": progress_pct,
            "paid_days": sorted(list(paid_days)),
            "days_in_month": days_in_month,
            "days_left": days_left,
            "suggested_daily": suggested_daily,
            "payments": [p.model_dump() for p in sorted(self.state.payments, key=lambda x: x.date, reverse=True)],
            "notifications": [n.model_dump() for n in sorted(self.state.notifications, key=lambda x: x.time, reverse=True)],
            "amenities": [a.model_dump() for a in self.state.amenities]
        }

    def get_state(self) -> LipaMdogoState:
        """Return full current state."""
        return self.state


# Example usage / FastAPI integration ready
if __name__ == "__main__":
    calc = LipaMdogoCalculator()
    
    # Example setup
    calc.save_setup(
        tenant_name="Amina Wanjiru",
        account_no="MWK-2201",
        bill_month="2026-07",
        base_rent=45000,
        amenities=[
            {"name": "Water", "cost": 2500},
            {"name": "Electricity", "cost": 3200}
        ]
    )
    
    # Make a payment
    result = calc.add_payment(5000, "M-Pesa")
    print(result["message"])
    
    dashboard = calc.get_dashboard_data()
    print(f"Progress: {dashboard['progress_pct']}%")
    print(f"Remaining: {dashboard['totals']['remaining']:,} KSh")
```

**This is production-grade, type-safe Python backend code** ready for:

- FastAPI / Flask integration (add routes easily)
- Persistent JSON storage
- Full Lipa Mdogo logic mirroring the UI
- Premium calculations (progress ring, calendar, projections, etc.)

Let me know if you want the **FastAPI version with full REST endpoints** or **Django models**.