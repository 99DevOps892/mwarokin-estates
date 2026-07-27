
"""
Lipa Mdogo Mdogo - Modern Python Package for Property Management
Agentic UI-ready code with functional programming paradigms
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Callable, Any, Union
from functools import reduce, partial
import json
import re
from enum import Enum

# ============================================================================
# Core Domain Models
# ============================================================================  

class Currency(Enum):
    KES = "KES"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    TZS = "TZS"
    UGX = "UGX"
    NGN = "NGN"
    GHS = "GHS"
    ZAR = "ZAR"

class PaymentStatus(Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    PARTIAL = "partial"
    CANCELLED = "cancelled"

@dataclass
class Address:
    """Property address value object"""
    street: str = ""
    city: str = ""
    country: str = ""
    postal_code: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "street": self.street,
            "city": self.city,
            "country": self.country,
            "postal_code": self.postal_code,
            "coordinates": {
                "lat": self.latitude,
                "lng": self.longitude
            } if self.latitude and self.longitude else None
        }

@dataclass
class Tenant:
    """Tenant entity with personal information"""
    tenant_id: str
    name: str
    account_number: str
    phone: str
    email: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        # Validate phone format
        if not re.match(r"^0\d{9}$", self.phone):
            raise ValueError("Phone must be 10 digits starting with 0")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "account_number": self.account_number,
            "phone": self.phone,
            "email": self.email,
            "created_at": self.created_at.isoformat()
        }

@dataclass
class Property:
    """Property entity with location and details"""
    property_id: str
    name: str
    location: Address
    building: str
    unit_number: str = ""
    monthly_rent: Decimal = Decimal("0.00")
    bills: Decimal = Decimal("0.00")
    country: str = ""
    
    @property
    def total_monthly_cost(self) -> Decimal:
        """Calculate total monthly cost (rent + bills)"""
        return self.monthly_rent + self.bills
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "property_id": self.property_id,
            "name": self.name,
            "location": self.location.to_dict(),
            "building": self.building,
            "unit_number": self.unit_number,
            "monthly_rent": str(self.monthly_rent),
            "bills": str(self.bills),
            "total": str(self.total_monthly_cost),
            "country": self.country
        }

@dataclass
class Installment:
    """Individual installment in a payment plan"""
    installment_number: int
    amount: Decimal
    due_date: datetime
    status: PaymentStatus = PaymentStatus.PENDING
    paid_date: Optional[datetime] = None
    
    def mark_paid(self, paid_date: Optional[datetime] = None) -> 'Installment':
        """Functional update - returns new Installment instance"""
        return Installment(
            installment_number=self.installment_number,
            amount=self.amount,
            due_date=self.due_date,
            status=PaymentStatus.PAID,
            paid_date=paid_date or datetime.now()
        )
    
    def is_overdue(self, as_of: Optional[datetime] = None) -> bool:
        """Check if installment is overdue"""
        if self.status == PaymentStatus.PAID:
            return False
        check_date = as_of or datetime.now()
        return self.due_date < check_date
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.installment_number,
            "amount": str(self.amount),
            "due_date": self.due_date.strftime("%Y-%m-%d"),
            "status": self.status.value,
            "paid_date": self.paid_date.strftime("%Y-%m-%d") if self.paid_date else None
        }

@dataclass
class PaymentPlan:
    """Complete payment plan with all installments"""
    plan_id: str
    tenant: Tenant
    property: Property
    month: datetime
    installments: List[Installment]
    created_at: datetime = field(default_factory=datetime.now)
    currency: Currency = Currency.KES
    
    @classmethod
    def create(
        cls,
        tenant: Tenant,
        property: Property,
        month: datetime,
        num_installments: int,
        currency: Currency = Currency.KES
    ) -> 'PaymentPlan':
        """Factory method to create a payment plan with calculated installments"""
        total = property.total_monthly_cost
        per_installment = (total / Decimal(str(num_installments))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        # Distribute any rounding difference
        installments = []
        remaining = total
        for i in range(num_installments):
            if i == num_installments - 1:
                amount = remaining
            else:
                amount = per_installment
                remaining -= amount
            
            due_date = month.replace(day=1) + timedelta(days=(i + 1) * 7)
            installments.append(
                Installment(
                    installment_number=i + 1,
                    amount=amount,
                    due_date=due_date,
                    status=PaymentStatus.PENDING
                )
            )
        
        return cls(
            plan_id=f"LM-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            tenant=tenant,
            property=property,
            month=month,
            installments=installments,
            currency=currency
        )
    
    @property
    def total_amount(self) -> Decimal:
        """Total amount of all installments"""
        return reduce(
            lambda acc, inst: acc + inst.amount,
            self.installments,
            Decimal("0.00")
        )
    
    @property
    def paid_amount(self) -> Decimal:
        """Total paid amount"""
        return reduce(
            lambda acc, inst: acc + (inst.amount if inst.status == PaymentStatus.PAID else Decimal("0.00")),
            self.installments,
            Decimal("0.00")
        )
    
    @property
    def remaining_amount(self) -> Decimal:
        """Remaining amount to be paid"""
        return self.total_amount - self.paid_amount
    
    @property
    def progress_percentage(self) -> float:
        """Payment progress as percentage"""
        if self.total_amount == Decimal("0.00"):
            return 0.0
        return float((self.paid_amount / self.total_amount) * 100)
    
    def mark_installment_paid(self, installment_number: int, paid_date: Optional[datetime] = None) -> 'PaymentPlan':
        """Functional update - returns new PaymentPlan with updated installment"""
        def update_installment(inst: Installment) -> Installment:
            if inst.installment_number == installment_number:
                return inst.mark_paid(paid_date)
            return inst
        
        return PaymentPlan(
            plan_id=self.plan_id,
            tenant=self.tenant,
            property=self.property,
            month=self.month,
            installments=[update_installment(inst) for inst in self.installments],
            created_at=self.created_at,
            currency=self.currency
        )
    
    def get_overdue_installments(self, as_of: Optional[datetime] = None) -> List[Installment]:
        """Get all overdue installments"""
        check_date = as_of or datetime.now()
        return [inst for inst in self.installments if inst.is_overdue(check_date)]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "tenant": self.tenant.to_dict(),
            "property": self.property.to_dict(),
            "month": self.month.strftime("%Y-%m"),
            "currency": self.currency.value,
            "installments": [inst.to_dict() for inst in self.installments],
            "total_amount": str(self.total_amount),
            "paid_amount": str(self.paid_amount),
            "remaining_amount": str(self.remaining_amount),
            "progress": round(self.progress_percentage, 2),
            "created_at": self.created_at.isoformat()
        }

# ============================================================================
# Pure Functions
# ============================================================================

def validate_phone(phone: str) -> bool:
    """Pure function to validate phone number"""
    return bool(re.match(r"^0\d{9}$", phone))

def format_currency(amount: Decimal, currency: Currency = Currency.KES) -> str:
    """Pure function to format currency"""
    return f"{currency.value} {amount:.2f}"

def calculate_installment_amount(
    total: Decimal,
    num_installments: int,
    installment_index: int,
    precision: int = 2
) -> Decimal:
    """Calculate a single installment amount with rounding"""
    base = (total / Decimal(str(num_installments))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if installment_index == num_installments - 1:
        return total - (base * Decimal(str(num_installments - 1)))
    return base

def generate_next_due_date(
    month: datetime,
    installment_number: int,
    days_between: int = 7
) -> datetime:
    """Generate due date for an installment"""
    return month.replace(day=1) + timedelta(days=installment_number * days_between)

def calculate_progress(paid: Decimal, total: Decimal) -> float:
    """Calculate progress percentage"""
    if total == Decimal("0.00"):
        return 0.0
    return float((paid / total) * 100)

def filter_paid_installments(installments: List[Installment]) -> List[Installment]:
    """Filter paid installments"""
    return [i for i in installments if i.status == PaymentStatus.PAID]

def filter_pending_installments(installments: List[Installment]) -> List[Installment]:
    """Filter pending installments"""
    return [i for i in installments if i.status == PaymentStatus.PENDING]

# ============================================================================
# Service Layer (Composable Functions)
# ============================================================================

def create_payment_plan_service(
    tenant: Tenant,
    property: Property,
    month: datetime,
    num_installments: int
) -> PaymentPlan:
    """Service function to create a payment plan"""
    if num_installments not in [1, 2, 4, 6]:
        raise ValueError("Installments must be 1, 2, 4, or 6")
    return PaymentPlan.create(tenant, property, month, num_installments)

def process_payment_service(
    plan: PaymentPlan,
    installment_number: int
) -> PaymentPlan:
    """Service function to process a payment"""
    return plan.mark_installment_paid(installment_number)

def get_payment_summary_service(plan: PaymentPlan) -> Dict[str, Any]:
    """Service function to get payment summary"""
    return {
        "total": plan.total_amount,
        "paid": plan.paid_amount,
        "remaining": plan.remaining_amount,
        "progress": plan.progress_percentage,
        "overdue": plan.get_overdue_installments(),
        "next_due": next(
            (i.due_date for i in plan.installments 
             if i.status == PaymentStatus.PENDING),
            None
        )
    }

# ============================================================================
# Agentic UI State Management
# ============================================================================

class AppState:
    """Application state container for agentic UI"""
    
    def __init__(self):
        self._state: Dict[str, Any] = {
            "plans": {},
            "tenants": {},
            "properties": {},
            "current_plan": None,
            "search_results": [],
            "filters": {
                "keyword": "",
                "country": "",
                "max_price": None
            }
        }
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get state value"""
        return self._state.get(key, default)
    
    def set(self, key: str, value: Any) -> 'AppState':
        """Set state value with notification"""
        self._state[key] = value
        self._notify()
        return self
    
    def update(self, updates: Dict[str, Any]) -> 'AppState':
        """Update multiple state values"""
        self._state.update(updates)
        self._notify()
        return self
    
    def subscribe(self, listener: Callable[[Dict[str, Any]], None]) -> Callable[[], None]:
        """Subscribe to state changes"""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)
    
    def _notify(self):
        """Notify all listeners"""
        for listener in self._listeners:
            listener(self._state)

# ============================================================================
# API/Service Interface for UI
# ============================================================================

class LipaMdogoService:
    """Main service interface for the Lipa Mdogo system"""
    
    def __init__(self):
        self.state = AppState()
        self._plans: Dict[str, PaymentPlan] = {}
        self._tenants: Dict[str, Tenant] = {}
        self._properties: Dict[str, Property] = {}
    
    def register_tenant(self, tenant: Tenant) -> str:
        """Register a new tenant"""
        self._tenants[tenant.tenant_id] = tenant
        return tenant.tenant_id
    
    def register_property(self, property: Property) -> str:
        """Register a new property"""
        self._properties[property.property_id] = property
        return property.property_id
    
    def create_plan(
        self,
        tenant_id: str,
        property_id: str,
        month: datetime,
        num_installments: int
    ) -> PaymentPlan:
        """Create a payment plan"""
        tenant = self._tenants.get(tenant_id)
        property = self._properties.get(property_id)
        
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        if not property:
            raise ValueError(f"Property {property_id} not found")
        
        plan = create_payment_plan_service(
            tenant, property, month, num_installments
        )
        self._plans[plan.plan_id] = plan
        self.state.set("current_plan", plan.to_dict())
        return plan
    
    def make_payment(self, plan_id: str, installment_number: int) -> PaymentPlan:
        """Process a payment"""
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        updated_plan = process_payment_service(plan, installment_number)
        self._plans[plan_id] = updated_plan
        self.state.set("current_plan", updated_plan.to_dict())
        return updated_plan
    
    def get_plan(self, plan_id: str) -> Optional[PaymentPlan]:
        """Get a payment plan"""
        return self._plans.get(plan_id)
    
    def get_plan_summary(self, plan_id: str) -> Dict[str, Any]:
        """Get plan summary"""
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        return get_payment_summary_service(plan)
    
    def search_properties(self, keyword: str, country: str = "") -> List[Property]:
        """Search for properties by keyword and country"""
        results = []
        keyword_lower = keyword.lower()
        for prop in self._properties.values():
            if keyword_lower in prop.name.lower() or keyword_lower in prop.building.lower():
                if not country or country.lower() == prop.country.lower():
                    results.append(prop)
        self.state.set("search_results", [p.to_dict() for p in results])
        return results
    
    def get_location_info(self, lat: float, lng: float) -> Dict[str, Any]:
        """Get location-based information"""
        # Determine currency based on coordinates
        currency = Currency.KES
        if -35 <= lat <= 38 and -25 <= lng <= 55:
            currency = Currency.KES
        return {
            "latitude": lat,
            "longitude": lng,
            "currency": currency.value,
            "exchange_rate": 129.2 if currency == Currency.KES else 1.0
        }

# ============================================================================
# Chat/Assistant Agent
# ============================================================================

class AssistantAgent:
    """AI Assistant for handling Lipa Mdogo queries"""
    
    def __init__(self, service: LipaMdogoService):
        self.service = service
        self._response_functions: Dict[str, Callable] = {
            "hello": self._handle_greeting,
            "hi": self._handle_greeting,
            "installment": self._handle_installment_query,
            "instalment": self._handle_installment_query,
            "payment": self._handle_installment_query,
            "fee": self._handle_fee_query,
            "cost": self._handle_fee_query,
            "due": self._handle_due_date_query,
            "date": self._handle_due_date_query,
            "help": self._handle_help,
            "plan": self._handle_plan_query,
            "tenant": self._handle_tenant_query
        }
    
    def process_query(self, query: str) -> str:
        """Process user query and return response"""
        query_lower = query.lower()
        
        # Find matching response function
        for keyword, handler in self._response_functions.items():
            if keyword in query_lower:
                return handler(query)
        
        return "I'm here for anything about your Lipa Mdogo plan — instalments, due dates, or setup."
    
    def _handle_greeting(self, query: str) -> str:
        return "Hello — how can I help with your Lipa Mdogo plan today?"
    
    def _handle_installment_query(self, query: str) -> str:
        return "You may split rent and bills into 2, 4, or 6 instalments. Would you like help setting one up?"
    
    def _handle_fee_query(self, query: str) -> str:
        return "Lipa Mdogo carries no extra fees — the same total, simply spread across the month."
    
    def _handle_due_date_query(self, query: str) -> str:
        return "Due dates are set automatically from your chosen plan, typically weekly for a 4-instalment schedule."
    
    def _handle_help(self, query: str) -> str:
        return "I can help with opening a plan, explaining instalment options, or checking due dates."
    
    def _handle_plan_query(self, query: str) -> str:
        return "To create a plan, provide tenant details and property information. I'll then calculate the instalments for you."
    
    def _handle_tenant_query(self, query: str) -> str:
        return "Tenants need to provide their name, account number, and phone number. I'll help register them."

# ============================================================================
# Builder Pattern for Configuration
# ============================================================================

class PaymentPlanBuilder:
    """Builder for creating payment plans with fluent interface"""
    
    def __init__(self):
        self._tenant: Optional[Tenant] = None
        self._property: Optional[Property] = None
        self._month: Optional[datetime] = None
        self._num_installments: int = 4
        self._currency: Currency = Currency.KES
    
    def with_tenant(self, tenant: Tenant) -> 'PaymentPlanBuilder':
        self._tenant = tenant
        return self
    
    def with_property(self, property: Property) -> 'PaymentPlanBuilder':
        self._property = property
        return self
    
    def for_month(self, month: datetime) -> 'PaymentPlanBuilder':
        self._month = month
        return self
    
    def with_installments(self, num: int) -> 'PaymentPlanBuilder':
        if num not in [1, 2, 4, 6]:
            raise ValueError("Installments must be 1, 2, 4, or 6")
        self._num_installments = num
        return self
    
    def with_currency(self, currency: Currency) -> 'PaymentPlanBuilder':
        self._currency = currency
        return self
    
    def build(self) -> PaymentPlan:
        if not all([self._tenant, self._property, self._month]):
            raise ValueError("Tenant, property, and month are required")
        return PaymentPlan.create(
            self._tenant,
            self._property,
            self._month,
            self._num_installments,
            self._currency
        )

# ============================================================================
# Main Application Entry Point
# ============================================================================

def main():
    """Example usage of the Lipa Mdogo system"""
    
    # Initialize service
    service = LipaMdogoService()
    assistant = AssistantAgent(service)
    
    # Create sample data
    address = Address(
        street="123 Main Street",
        city="Nairobi",
        country="Kenya",
        latitude=-1.286389,
        longitude=36.817223
    )
    
    tenant = Tenant(
        tenant_id="T001",
        name="John Doe",
        account_number="ACC-001",
        phone="0712345678",
        email="john@example.com"
    )
    
    property = Property(
        property_id="P001",
        name="Kilimani Heights",
        location=address,
        building="Tower A",
        unit_number="201",
        monthly_rent=Decimal("85000.00"),
        bills=Decimal("5000.00"),
        country="Kenya"
    )
    
    # Register tenant and property
    service.register_tenant(tenant)
    service.register_property(property)
    
    # Create a payment plan
    plan = service.create_plan(
        tenant_id="T001",
        property_id="P001",
        month=datetime(2026, 7, 1),
        num_installments=4
    )
    
    # Get summary
    summary = service.get_plan_summary(plan.plan_id)
    print("\n=== Payment Plan Summary ===")
    print(f"Plan ID: {plan.plan_id}")
    print(f"Total: KES {plan.total_amount:.2f}")
    print(f"Paid: KES {plan.paid_amount:.2f}")
    print(f"Remaining: KES {plan.remaining_amount:.2f}")
    print(f"Progress: {plan.progress_percentage:.1f}%")
    
    # Show installments
    print("\n=== Installments ===")
    for inst in plan.installments:
        print(f"  #{inst.installment_number}: KES {inst.amount:.2f} due {inst.due_date.strftime('%Y-%m-%d')} [{inst.status.value}]")
    
    # Process a payment
    print("\n=== Processing Payment ===")
    updated_plan = service.make_payment(plan.plan_id, 1)
    print(f"Installment 1 paid. Progress: {updated_plan.progress_percentage:.1f}%")
    
    # Test assistant
    print("\n=== Assistant Demo ===")
    queries = [
        "Hello",
        "How many installments can I choose?",
        "Are there any fees?",
        "When is my next payment due?",
        "Help"
    ]
    for q in queries:
        print(f"Q: {q}")
        print(f"A: {assistant.process_query(q)}\n")

if __name__ == "__main__":
    main()