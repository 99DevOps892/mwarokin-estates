```python
"""
Mwarokin Estate Ledger - Modern Python Backend
Functional programming style with real-time capabilities
"""

from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import json
import random
import hashlib
from functools import wraps, reduce
from itertools import chain
import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

# ============================= CORE TYPES =============================

class BillStatus(Enum):
    PAID = "paid"
    PENDING = "pending"
    OVERDUE = "overdue"

class PaymentMethod(Enum):
    MPESA = "M-Pesa"
    SYLLOPAY = "SylloPay"
    BANK = "Bank"
    CASH = "Cash"

@dataclass
class CurrencyInfo:
    country: str
    rate: Decimal
    currency: str
    symbol: str

@dataclass
class BillBreakdown:
    monthly_rent: Decimal = Decimal('0')
    electricity: Decimal = Decimal('0')
    water: Decimal = Decimal('0')
    internet: Decimal = Decimal('0')
    digital_tv: Decimal = Decimal('0')
    security: Decimal = Decimal('0')
    parking: Decimal = Decimal('0')
    trash: Decimal = Decimal('0')

    def total(self) -> Decimal:
        return sum([
            self.monthly_rent, self.electricity, self.water,
            self.internet, self.digital_tv, self.security,
            self.parking, self.trash
        ], Decimal('0'))

@dataclass
class Bill:
    id: str
    tenant: str
    property_name: str
    amount: Decimal
    due_date: datetime
    status: BillStatus
    method: Optional[PaymentMethod] = None
    breakdown: BillBreakdown = field(default_factory=BillBreakdown)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class FeedEvent:
    id: str
    verb: str
    icon: str
    tone: str
    tenant: str
    property_name: str
    amount: Optional[Decimal]
    timestamp: datetime

@dataclass
class FinancialSummary:
    collected: Decimal
    pending: Decimal
    overdue: Decimal
    outstanding: Decimal
    collection_rate: float

# ============================= PURE FUNCTIONS =============================

def create_breakdown(amount: Decimal) -> BillBreakdown:
    """Create synthetic bill breakdown from total amount."""
    if not amount or amount <= 0:
        return BillBreakdown()
    
    return BillBreakdown(
        monthly_rent=(amount * Decimal('0.70')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        electricity=(amount * Decimal('0.12')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        water=(amount * Decimal('0.06')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        internet=(amount * Decimal('0.05')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        security=(amount * Decimal('0.04')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        trash=(amount * Decimal('0.03')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    )

def generate_bill_id(sequence: int) -> str:
    """Generate sequential bill ID with format BL-XXXX."""
    return f"BL-{2400 + sequence:04d}"

def format_currency(amount: Decimal, symbol: str = "KSh") -> str:
    """Format currency with proper rounding."""
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    return f"{symbol} {amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,.2f}"

def calculate_summary(bills: List[Bill]) -> FinancialSummary:
    """Calculate financial summary from bills list."""
    paid = [b for b in bills if b.status == BillStatus.PAID]
    pending = [b for b in bills if b.status == BillStatus.PENDING]
    overdue = [b for b in bills if b.status == BillStatus.OVERDUE]
    
    collected = sum((b.amount for b in paid), Decimal('0'))
    pending_total = sum((b.amount for b in pending), Decimal('0'))
    overdue_total = sum((b.amount for b in overdue), Decimal('0'))
    outstanding = pending_total + overdue_total
    total = collected + outstanding
    rate = float(collected / total * 100) if total > 0 else 0.0
    
    return FinancialSummary(
        collected=collected,
        pending=pending_total,
        overdue=overdue_total,
        outstanding=outstanding,
        collection_rate=rate
    )

def filter_bills(bills: List[Bill], status: Optional[BillStatus] = None, 
                 search: str = "", property_name: str = "") -> List[Bill]:
    """Pure function to filter bills by various criteria."""
    result = bills.copy()
    
    if status:
        result = [b for b in result if b.status == status]
    
    if search:
        search_lower = search.lower()
        result = [
            b for b in result 
            if search_lower in b.tenant.lower() 
            or search_lower in b.property_name.lower()
            or search_lower in b.id.lower()
        ]
    
    if property_name:
        result = [b for b in result if b.property_name == property_name]
    
    return result

def sort_bills(bills: List[Bill], key: str, ascending: bool = True) -> List[Bill]:
    """Pure function to sort bills by specified key."""
    def get_key(bill: Bill):
        if key == "amount":
            return bill.amount
        elif key == "due_date":
            return bill.due_date
        elif key == "status":
            return bill.status.value
        elif key == "tenant":
            return bill.tenant.lower()
        elif key == "id":
            return bill.id
        return getattr(bill, key, "")
    
    return sorted(bills, key=get_key, reverse=not ascending)

def create_feed_event(verb: Dict[str, str], tenant: str, 
                      property_name: str, amount: Optional[Decimal] = None) -> FeedEvent:
    """Create a feed event from components."""
    return FeedEvent(
        id=hashlib.md5(f"{datetime.now().isoformat()}{tenant}{property_name}".encode()).hexdigest()[:8],
        verb=verb["v"],
        icon=verb["icon"],
        tone=verb["tone"],
        tenant=tenant,
        property_name=property_name,
        amount=amount,
        timestamp=datetime.now()
    )

def generate_historical_data(days: int = 14, base_amount: int = 60000) -> List[Dict]:
    """Generate synthetic historical data for trend visualization."""
    history = []
    now = datetime.now()
    for i in range(days - 1, -1, -1):
        date = now - timedelta(days=i)
        collected = base_amount + random.randint(0, 40000) + (days - 1 - i) * 1800
        history.append({
            "label": date.strftime("%d %b"),
            "collected": Decimal(str(collected))
        })
    return history

# ============================= HIGHER-ORDER FUNCTIONS =============================

def with_validation(func: Callable) -> Callable:
    """Decorator for validating bill operations."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        bills = args[0] if args else kwargs.get('bills', [])
        if not isinstance(bills, list):
            raise TypeError("bills must be a list")
        if not all(isinstance(b, Bill) for b in bills):
            raise TypeError("all items must be Bill instances")
        return func(*args, **kwargs)
    return wrapper

def with_logging(func: Callable) -> Callable:
    """Decorator for logging bill operations."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        # In production, this would log to a proper logging system
        print(f"[LOG] {func.__name__} called with {len(args[0]) if args else 0} bills")
        return result
    return wrapper

def compose(*functions):
    """Function composition utility."""
    def compose2(f, g):
        return lambda x: f(g(x))
    return reduce(compose2, functions)

# ============================= SERVICE CLASS (Functional Style) =============================

class LedgerService:
    """Functional-style service for managing estate ledger operations."""
    
    def __init__(self):
        self._bills: List[Bill] = []
        self._feed: List[FeedEvent] = []
        self._subscribers: List[Callable] = []
        self._sequence_counter = 0
    
    # ===== BILL OPERATIONS =====
    
    def add_bill(self, tenant: str, property_name: str, amount: Decimal,
                 breakdown: Optional[BillBreakdown] = None) -> Bill:
        """Add a new bill to the ledger."""
        self._sequence_counter += 1
        
        bill = Bill(
            id=generate_bill_id(self._sequence_counter),
            tenant=tenant,
            property_name=property_name,
            amount=amount,
            due_date=datetime.now() + timedelta(days=7),
            status=BillStatus.PENDING,
            breakdown=breakdown or create_breakdown(amount)
        )
        
        self._bills.append(bill)
        self._notify_subscribers()
        return bill
    
    def mark_paid(self, bill_id: str, method: PaymentMethod = PaymentMethod.MPESA) -> Optional[Bill]:
        """Mark a specific bill as paid."""
        for bill in self._bills:
            if bill.id == bill_id:
                bill.status = BillStatus.PAID
                bill.method = method
                bill.updated_at = datetime.now()
                self._notify_subscribers()
                return bill
        return None
    
    def mark_overdue(self, bill_id: str) -> Optional[Bill]:
        """Mark a specific bill as overdue."""
        for bill in self._bills:
            if bill.id == bill_id and bill.status == BillStatus.PENDING:
                bill.status = BillStatus.OVERDUE
                bill.updated_at = datetime.now()
                self._notify_subscribers()
                return bill
        return None
    
    def bulk_mark_paid(self, bill_ids: List[str], method: PaymentMethod = PaymentMethod.MPESA) -> List[Bill]:
        """Mark multiple bills as paid."""
        updated_bills = []
        for bill_id in bill_ids:
            bill = self.mark_paid(bill_id, method)
            if bill:
                updated_bills.append(bill)
        return updated_bills
    
    def get_bill(self, bill_id: str) -> Optional[Bill]:
        """Retrieve a specific bill by ID."""
        for bill in self._bills:
            if bill.id == bill_id:
                return bill
        return None
    
    # ===== QUERY OPERATIONS =====
    
    def get_summary(self) -> FinancialSummary:
        """Calculate current financial summary."""
        return calculate_summary(self._bills)
    
    def search_bills(self, query: str) -> List[Bill]:
        """Search bills by tenant, property, or ID."""
        return filter_bills(self._bills, search=query)
    
    def get_bills_by_status(self, status: BillStatus) -> List[Bill]:
        """Get bills filtered by status."""
        return filter_bills(self._bills, status=status)
    
    def get_bills_by_property(self, property_name: str) -> List[Bill]:
        """Get bills for a specific property."""
        return filter_bills(self._bills, property_name=property_name)
    
    def get_sorted_bills(self, sort_key: str, ascending: bool = True) -> List[Bill]:
        """Get bills sorted by specified key."""
        return sort_bills(self._bills, sort_key, ascending)
    
    def get_overdue_bills(self) -> List[Bill]:
        """Get all overdue bills."""
        return [b for b in self._bills if b.status == BillStatus.OVERDUE]
    
    # ===== FEED OPERATIONS =====
    
    def add_feed_event(self, event: FeedEvent) -> None:
        """Add a feed event to the activity feed."""
        self._feed.append(event)
        if len(self._feed) > 30:
            self._feed = self._feed[-30:]
    
    def get_feed(self, limit: int = 20) -> List[FeedEvent]:
        """Get recent feed events."""
        return self._feed[-limit:][::-1]
    
    def create_and_add_feed_event(self, verb: Dict[str, str], tenant: str, 
                                   property_name: str, amount: Optional[Decimal] = None) -> FeedEvent:
        """Create and add a feed event in one operation."""
        event = create_feed_event(verb, tenant, property_name, amount)
        self.add_feed_event(event)
        return event
    
    # ===== SUBSCRIPTION OPERATIONS =====
    
    def subscribe(self, callback: Callable) -> None:
        """Subscribe to ledger changes."""
        self._subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable) -> None:
        """Unsubscribe from ledger changes."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
    
    def _notify_subscribers(self) -> None:
        """Notify all subscribers of changes."""
        for callback in self._subscribers:
            callback(self._bills)
    
    # ===== SERIALIZATION =====
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize ledger data to dictionary."""
        def serialize_bill(bill: Bill) -> Dict:
            return {
                "id": bill.id,
                "tenant": bill.tenant,
                "property": bill.property_name,
                "amount": float(bill.amount),
                "due": bill.due_date.isoformat()[:10],
                "status": bill.status.value,
                "method": bill.method.value if bill.method else "—",
                "breakdown": asdict(bill.breakdown)
            }
        
        def serialize_event(event: FeedEvent) -> Dict:
            return {
                "id": event.id,
                "verb": event.verb,
                "icon": event.icon,
                "tone": event.tone,
                "tenant": event.tenant,
                "property": event.property_name,
                "amount": float(event.amount) if event.amount else None,
                "time": event.timestamp.isoformat()
            }
        
        return {
            "bills": [serialize_bill(b) for b in self._bills],
            "feed": [serialize_event(e) for e in self._feed[:20]],
            "summary": {
                "collected": float(self.get_summary().collected),
                "pending": float(self.get_summary().pending),
                "overdue": float(self.get_summary().overdue),
                "outstanding": float(self.get_summary().outstanding),
                "rate": self.get_summary().collection_rate
            }
        }
    
    # ===== STATISTICS =====
    
    def get_collection_trend(self, days: int = 14) -> List[Dict]:
        """Generate collection trend data."""
        return generate_historical_data(days)
    
    def get_property_summaries(self) -> Dict[str, Dict]:
        """Get per-property financial summaries."""
        properties = {}
        for bill in self._bills:
            if bill.property_name not in properties:
                properties[bill.property_name] = {
                    "total": Decimal('0'),
                    "paid": Decimal('0'),
                    "pending": Decimal('0'),
                    "overdue": Decimal('0'),
                    "count": 0
                }
            
            props = properties[bill.property_name]
            props["total"] += bill.amount
            props["count"] += 1
            
            if bill.status == BillStatus.PAID:
                props["paid"] += bill.amount
            elif bill.status == BillStatus.PENDING:
                props["pending"] += bill.amount
            elif bill.status == BillStatus.OVERDUE:
                props["overdue"] += bill.amount
        
        return properties

# ============================= FACTORY FUNCTIONS =============================

def create_sample_data() -> LedgerService:
    """Create a ledger service with sample data."""
    service = LedgerService()
    
    sample_tenants = [
        ("Grace Muthoni", "Riverside 12A", 24500),
        ("David Ochieng", "Kilimani 7B", 32000),
        ("Sarah Wanjiru", "Westlands 4C", 18500),
        ("Michael Kamau", "Langata 9D", 41000),
        ("Faith Akinyi", "Parklands 2E", 27500),
        ("Brian Kiptoo", "Riverside 3F", 29800),
    ]
    
    for tenant, property_name, amount in sample_tenants:
        service.add_bill(tenant, property_name, Decimal(str(amount)))
    
    # Mark some as paid
    for bill in service._bills[:2]:
        service.mark_paid(bill.id, PaymentMethod.MPESA)
    
    # Mark one as overdue
    if len(service._bills) > 2:
        service._bills[2].status = BillStatus.OVERDUE
    
    return service

# ============================= ASYNC SUPPORT =============================

class AsyncLedgerService(LedgerService):
    """Async wrapper for ledger service."""
    
    async def add_bill_async(self, *args, **kwargs) -> Bill:
        """Add bill asynchronously."""
        return await asyncio.to_thread(self.add_bill, *args, **kwargs)
    
    async def mark_paid_async(self, *args, **kwargs) -> Optional[Bill]:
        """Mark paid asynchronously."""
        return await asyncio.to_thread(self.mark_paid, *args, **kwargs)
    
    async def get_summary_async(self) -> FinancialSummary:
        """Get summary asynchronously."""
        return await asyncio.to_thread(self.get_summary)
    
    async def bulk_mark_paid_async(self, *args, **kwargs) -> List[Bill]:
        """Bulk mark paid asynchronously."""
        return await asyncio.to_thread(self.bulk_mark_paid, *args, **kwargs)

# ============================= FUNCTIONAL PIPELINE =============================

def pipeline_bills(service: LedgerService, *functions):
    """Create a pipeline for processing bills."""
    def process_pipeline():
        result = service._bills.copy()
        for func in functions:
            result = func(result)
        return result
    return process_pipeline

# Example pipelines
def filter_overdue_pipeline(service: LedgerService):
    """Pipeline: get only overdue bills."""
    return pipeline_bills(
        service,
        lambda bills: filter_bills(bills, status=BillStatus.OVERDUE)
    )

def search_and_sort_pipeline(service: LedgerService, query: str, sort_key: str = "amount"):
    """Pipeline: search and sort bills."""
    return pipeline_bills(
        service,
        lambda bills: filter_bills(bills, search=query),
        lambda bills: sort_bills(bills, sort_key, ascending=False)
    )

# ============================= USAGE EXAMPLE =============================

def main():
    """Example usage of the ledger system."""
    # Create service with sample data
    service = create_sample_data()
    
    # Get financial summary
    summary = service.get_summary()
    print(f"Collected: {format_currency(summary.collected)}")
    print(f"Outstanding: {format_currency(summary.outstanding)}")
    print(f"Collection Rate: {summary.collection_rate:.1f}%")
    
    # Add a new bill
    new_bill = service.add_bill(
        "Peter Mwangi",
        "Riverside 15G",
        Decimal("35000.00")
    )
    print(f"\nAdded bill: {new_bill.id} - {new_bill.tenant} - {format_currency(new_bill.amount)}")
    
    # Search for bills
    results = service.search_bills("Riverside")
    print(f"\nFound {len(results)} bills for Riverside properties")
    
    # Get sorted bills by amount
    sorted_bills = service.get_sorted_bills("amount", ascending=False)
    print(f"\nTop 3 bills by amount:")
    for bill in sorted_bills[:3]:
        print(f"  {bill.id}: {bill.tenant} - {format_currency(bill.amount)}")
    
    # Use asynchronous service
    async def async_example():
        async_service = AsyncLedgerService()
        
        # Add bills concurrently
        tasks = [
            async_service.add_bill_async("Alice Nyambura", "Parklands 8A", Decimal("22000")),
            async_service.add_bill_async("Bob Omondi", "Langata 3B", Decimal("18500")),
        ]
        results = await asyncio.gather(*tasks)
        print(f"\nAdded {len(results)} bills asynchronously")
        
        # Get summary
        summary = await async_service.get_summary_async()
        print(f"Total collected: {format_currency(summary.collected)}")
    
    # Run async example
    # asyncio.run(async_example())
    
    return service

if __name__ == "__main__":
    main()

# ============================= EXPORTS =============================

__all__ = [
    'Bill', 'BillStatus', 'PaymentMethod', 'BillBreakdown', 'FeedEvent',
    'FinancialSummary', 'CurrencyInfo',
    'LedgerService', 'AsyncLedgerService',
    'create_sample_data', 'create_breakdown', 'format_currency',
    'filter_bills', 'sort_bills', 'calculate_summary',
    'generate_bill_id', 'generate_historical_data'
]
```