"""
Mwarokin Estates - Landlord Dashboard
Modern Python backend with functional programming patterns
Agentic UI management with real-time data processing
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
import json
import os
from functools import reduce, partial
from itertools import groupby
from operator import attrgetter
import random
import uuid

# ============================================================================
# CORE TYPES & ENUMS
# ============================================================================

class PropertyStatus(Enum):
    PAID = "paid"
    DUE = "due"
    LATE = "late"

class MaintenanceStatus(Enum):
    OPEN = "open"
    PROGRESS = "progress"
    RESOLVED = "resolved"

class Priority(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

class ActivityType(Enum):
    PAYMENT = "payment"
    MAINTENANCE = "maint"
    TENANT = "tenant"

@dataclass
class Currency:
    code: str
    symbol: str
    rate: float

class CurrencyManager:
    """Functional currency management with immutability"""
    
    CURRENCIES = {
        "KES": Currency("KES", "KSh", 1.0),
        "USD": Currency("USD", "$", 1/128.5)
    }
    
    @staticmethod
    def convert(amount: float, from_currency: str, to_currency: str) -> float:
        """Pure function for currency conversion"""
        if from_currency == to_currency:
            return amount
        rate = CurrencyManager.CURRENCIES[to_currency].rate / CurrencyManager.CURRENCIES[from_currency].rate
        return amount * rate
    
    @staticmethod
    def format_amount(amount: float, currency_code: str) -> str:
        """Pure function for currency formatting"""
        currency = CurrencyManager.CURRENCIES[currency_code]
        return f"{currency.symbol} {amount:,.0f}"

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Property:
    id: str
    name: str
    units: int
    occupied: int
    monthly: float
    status: PropertyStatus
    
    @property
    def occupancy_rate(self) -> float:
        return (self.occupied / self.units) * 100 if self.units > 0 else 0
    
    @property
    def vacant_units(self) -> int:
        return self.units - self.occupied

@dataclass
class RevenueRecord:
    month: str
    collected: float
    target: float
    
    @property
    def collection_rate(self) -> float:
        return (self.collected / self.target) * 100 if self.target > 0 else 0

@dataclass
class Deposit:
    tenant: str
    unit: str
    amount: float

@dataclass
class Maintenance:
    id: str
    unit: str
    description: str
    priority: Priority
    status: MaintenanceStatus
    logged: str
    
    @property
    def is_open(self) -> bool:
        return self.status != MaintenanceStatus.RESOLVED

@dataclass
class Activity:
    type: ActivityType
    title: str
    description: str
    timestamp: str
    
    @property
    def icon(self) -> str:
        """Functional mapping of activity type to icon"""
        return {
            ActivityType.PAYMENT: "fa-money-bill-wave",
            ActivityType.MAINTENANCE: "fa-tools",
            ActivityType.TENANT: "fa-user-check"
        }[self.type]

@dataclass
class Portfolio:
    """Immutable portfolio data structure"""
    currency: str
    properties: List[Property]
    revenue_history: List[RevenueRecord]
    deposits: List[Deposit]
    maintenance: List[Maintenance]
    activities: List[Activity]
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def total_units(self) -> int:
        return sum(p.units for p in self.properties)
    
    @property
    def occupied_units(self) -> int:
        return sum(p.occupied for p in self.properties)
    
    @property
    def occupancy_rate(self) -> float:
        return (self.occupied_units / self.total_units) * 100 if self.total_units > 0 else 0
    
    @property
    def total_monthly_revenue(self) -> float:
        return sum(p.monthly for p in self.properties)
    
    @property
    def pending_rent_count(self) -> int:
        return sum(1 for p in self.properties if p.status != PropertyStatus.PAID)
    
    @property
    def open_maintenance_count(self) -> int:
        return sum(1 for m in self.maintenance if m.is_open)
    
    @property
    def total_deposits(self) -> float:
        return sum(d.amount for d in self.deposits)
    
    def get_properties_by_status(self, status: Optional[PropertyStatus] = None) -> List[Property]:
        """Filter properties by status using functional approach"""
        if status is None:
            return self.properties
        return list(filter(lambda p: p.status == status, self.properties))
    
    def get_maintenance_by_status(self, status: Optional[MaintenanceStatus] = None) -> List[Maintenance]:
        """Filter maintenance by status using functional approach"""
        if status is None:
            return self.maintenance
        return list(filter(lambda m: m.status == status, self.maintenance))
    
    def get_revenue_for_month(self, month: str) -> Optional[RevenueRecord]:
        """Get revenue record for specific month"""
        records = list(filter(lambda r: r.month == month, self.revenue_history))
        return records[0] if records else None
    
    def get_current_month_revenue(self) -> RevenueRecord:
        """Get the most recent month's revenue"""
        return self.revenue_history[-1] if self.revenue_history else None

# ============================================================================
# DATA REPOSITORY (Functional Data Management)
# ============================================================================

class PortfolioRepository:
    """Repository pattern with functional operations for portfolio management"""
    
    STORE_KEY = "mwarokin_portfolio_v2"
    
    @staticmethod
    def default_portfolio() -> Portfolio:
        """Generate default portfolio data using functional composition"""
        properties = [
            Property("p1", "Mwarokin Riverside Apartments", 18, 16, 612000, PropertyStatus.PAID),
            Property("p2", "Kileleshwa Garden Court", 10, 9, 410000, PropertyStatus.DUE),
            Property("p3", "Ruaka Heights", 24, 20, 780000, PropertyStatus.PAID),
            Property("p4", "Syokimau Grove Villas", 8, 5, 225000, PropertyStatus.LATE),
            Property("p5", "Westlands Prime Suites", 12, 12, 540000, PropertyStatus.PAID),
            Property("p6", "Ngong Road Court", 14, 11, 392000, PropertyStatus.DUE)
        ]
        
        revenue_history = [
            RevenueRecord("Feb", 2180000, 2450000),
            RevenueRecord("Mar", 2340000, 2450000),
            RevenueRecord("Apr", 2260000, 2500000),
            RevenueRecord("May", 2410000, 2500000),
            RevenueRecord("Jun", 2380000, 2550000),
            RevenueRecord("Jul", 1920000, 2559000)
        ]
        
        deposits = [
            Deposit("John Doe", "Riverside A-101", 60000),
            Deposit("Sarah Johnson", "Ruaka Heights D-304", 78000),
            Deposit("Michael Otieno", "Westlands Suite 5", 90000),
            Deposit("Grace Wanjiru", "Kileleshwa 2B", 65000)
        ]
        
        maintenance = [
            Maintenance("m1", "Ruaka Heights D-205", "Kitchen plumbing leak reported by tenant", 
                       Priority.HIGH, MaintenanceStatus.OPEN, "2 days ago"),
            Maintenance("m2", "Kileleshwa 2B", "Bedroom window latch broken", 
                       Priority.MEDIUM, MaintenanceStatus.PROGRESS, "4 days ago"),
            Maintenance("m3", "Riverside A-101", "AC servicing due (quarterly)", 
                       Priority.LOW, MaintenanceStatus.RESOLVED, "1 week ago")
        ]
        
        activities = [
            Activity(ActivityType.PAYMENT, "Rent payment received", 
                    "Sarah Johnson — Ruaka Heights D-304 — KSh 68,000", "2 hours ago"),
            Activity(ActivityType.MAINTENANCE, "Maintenance request submitted", 
                    "Plumbing issue — Ruaka Heights D-205", "2 days ago"),
            Activity(ActivityType.TENANT, "New tenant approved", 
                    "Michael Otieno — Westlands Suite 5", "3 days ago"),
            Activity(ActivityType.PAYMENT, "Water bill generated", 
                    "All properties — due in 5 days", "4 days ago")
        ]
        
        return Portfolio("KES", properties, revenue_history, deposits, maintenance, activities)
    
    @staticmethod
    def load() -> Portfolio:
        """Load portfolio from storage or create default"""
        try:
            raw = json.loads(localStorage_get(PortfolioRepository.STORE_KEY))
            return PortfolioRepository._deserialize(raw)
        except:
            portfolio = PortfolioRepository.default_portfolio()
            PortfolioRepository.save(portfolio)
            return portfolio
    
    @staticmethod
    def save(portfolio: Portfolio) -> None:
        """Save portfolio to storage"""
        data = PortfolioRepository._serialize(portfolio)
        localStorage_set(PortfolioRepository.STORE_KEY, json.dumps(data))
    
    @staticmethod
    def _serialize(portfolio: Portfolio) -> Dict[str, Any]:
        """Serialize portfolio to dictionary"""
        return {
            "currency": portfolio.currency,
            "properties": [
                {"id": p.id, "name": p.name, "units": p.units, "occupied": p.occupied,
                 "monthly": p.monthly, "status": p.status.value}
                for p in portfolio.properties
            ],
            "revenue_history": [
                {"month": r.month, "collected": r.collected, "target": r.target}
                for r in portfolio.revenue_history
            ],
            "deposits": [
                {"tenant": d.tenant, "unit": d.unit, "amount": d.amount}
                for d in portfolio.deposits
            ],
            "maintenance": [
                {"id": m.id, "unit": m.unit, "description": m.description,
                 "priority": m.priority.value, "status": m.status.value, "logged": m.logged}
                for m in portfolio.maintenance
            ],
            "activities": [
                {"type": a.type.value, "title": a.title, "description": a.description, "timestamp": a.timestamp}
                for a in portfolio.activities
            ]
        }
    
    @staticmethod
    def _deserialize(data: Dict[str, Any]) -> Portfolio:
        """Deserialize portfolio from dictionary"""
        return Portfolio(
            currency=data["currency"],
            properties=[
                Property(
                    p["id"], p["name"], p["units"], p["occupied"], p["monthly"],
                    PropertyStatus(p["status"])
                )
                for p in data["properties"]
            ],
            revenue_history=[
                RevenueRecord(r["month"], r["collected"], r["target"])
                for r in data["revenue_history"]
            ],
            deposits=[
                Deposit(d["tenant"], d["unit"], d["amount"])
                for d in data["deposits"]
            ],
            maintenance=[
                Maintenance(
                    m["id"], m["unit"], m["description"],
                    Priority(m["priority"]), MaintenanceStatus(m["status"]), m["logged"]
                )
                for m in data["maintenance"]
            ],
            activities=[
                Activity(
                    ActivityType(a["type"]), a["title"], a["description"], a["timestamp"]
                )
                for a in data["activities"]
            ]
        )

# ============================================================================
# FUNCTIONAL OPERATIONS (Pure Functions)
# ============================================================================

# Type aliases for functional operations
PortfolioTransformer = Callable[[Portfolio], Portfolio]
DataFilter = Callable[[Any], bool]
DataMapper = Callable[[Any], Any]

def compose(*functions: PortfolioTransformer) -> PortfolioTransformer:
    """Compose multiple portfolio transformations"""
    def apply(portfolio: Portfolio) -> Portfolio:
        return reduce(lambda p, f: f(p), functions, portfolio)
    return apply

def with_transaction(operation: PortfolioTransformer) -> PortfolioTransformer:
    """Wrap operation in a transaction with error handling"""
    def transactional(portfolio: Portfolio) -> Portfolio:
        try:
            return operation(portfolio)
        except Exception as e:
            print(f"Transaction failed: {e}")
            return portfolio
    return transactional

def add_maintenance_request(
    unit: str,
    description: str,
    priority: Priority
) -> PortfolioTransformer:
    """Functional transformer to add maintenance request"""
    def transform(portfolio: Portfolio) -> Portfolio:
        new_maint = Maintenance(
            id=f"m{int(datetime.now().timestamp()*1000)}",
            unit=unit,
            description=description,
            priority=priority,
            status=MaintenanceStatus.OPEN,
            logged="just now"
        )
        new_activity = Activity(
            type=ActivityType.MAINTENANCE,
            title="Maintenance request logged",
            description=f"{description} — {unit}",
            timestamp="just now"
        )
        return Portfolio(
            currency=portfolio.currency,
            properties=portfolio.properties,
            revenue_history=portfolio.revenue_history,
            deposits=portfolio.deposits,
            maintenance=[new_maint] + portfolio.maintenance,
            activities=[new_activity] + portfolio.activities
        )
    return transform

def update_maintenance_status(
    maint_id: str,
    new_status: MaintenanceStatus
) -> PortfolioTransformer:
    """Functional transformer to update maintenance status"""
    def transform(portfolio: Portfolio) -> Portfolio:
        updated_maintenance = []
        for maint in portfolio.maintenance:
            if maint.id == maint_id:
                updated_maintenance.append(
                    Maintenance(
                        id=maint.id,
                        unit=maint.unit,
                        description=maint.description,
                        priority=maint.priority,
                        status=new_status,
                        logged=maint.logged
                    )
                )
            else:
                updated_maintenance.append(maint)
        
        return Portfolio(
            currency=portfolio.currency,
            properties=portfolio.properties,
            revenue_history=portfolio.revenue_history,
            deposits=portfolio.deposits,
            maintenance=updated_maintenance,
            activities=portfolio.activities
        )
    return transform

def update_currency(new_currency: str) -> PortfolioTransformer:
    """Functional transformer to update currency"""
    def transform(portfolio: Portfolio) -> Portfolio:
        return Portfolio(
            currency=new_currency,
            properties=portfolio.properties,
            revenue_history=portfolio.revenue_history,
            deposits=portfolio.deposits,
            maintenance=portfolio.maintenance,
            activities=portfolio.activities
        )
    return transform

# ============================================================================
# UI RENDER ENGINE (Agentic UI Management)
# ============================================================================

class UIState:
    """State management for UI with reactive updates"""
    
    def __init__(self, portfolio: Portfolio):
        self._portfolio = portfolio
        self._observers: List[Callable[[Portfolio], None]] = []
        self._filters = {
            "property_search": "",
            "status_filter": "all"
        }
    
    @property
    def portfolio(self) -> Portfolio:
        return self._portfolio
    
    def set_portfolio(self, portfolio: Portfolio) -> None:
        """Update portfolio and notify observers"""
        self._portfolio = portfolio
        self._notify_observers()
    
    def add_observer(self, observer: Callable[[Portfolio], None]) -> None:
        """Add observer for reactive updates"""
        self._observers.append(observer)
    
    def _notify_observers(self) -> None:
        """Notify all observers of state change"""
        for observer in self._observers:
            observer(self._portfolio)
    
    def get_filtered_properties(self) -> List[Property]:
        """Get properties filtered by current filters"""
        search = self._filters["property_search"].lower()
        status_filter = self._filters["status_filter"]
        
        filtered = self._portfolio.properties
        
        if search:
            filtered = list(filter(lambda p: search in p.name.lower(), filtered))
        
        if status_filter != "all":
            status = PropertyStatus(status_filter)
            filtered = list(filter(lambda p: p.status == status, filtered))
        
        return filtered

class ViewRenderer:
    """Functional view rendering with HTML generation"""
    
    @staticmethod
    def render_kpi(portfolio: Portfolio, currency: str) -> Dict[str, Any]:
        """Render KPI data as dictionary"""
        return {
            "total_properties": len(portfolio.properties),
            "total_units": portfolio.total_units,
            "occupied_units": portfolio.occupied_units,
            "occupancy_rate": f"{portfolio.occupancy_rate:.0f}%",
            "monthly_revenue": CurrencyManager.format_amount(
                portfolio.total_monthly_revenue, currency
            ),
            "pending_count": portfolio.pending_rent_count,
            "open_maintenance": portfolio.open_maintenance_count,
            "total_deposits": CurrencyManager.format_amount(
                portfolio.total_deposits, currency
            )
        }
    
    @staticmethod
    def render_property_table(properties: List[Property]) -> List[Dict[str, Any]]:
        """Render property table data"""
        return [
            {
                "name": p.name,
                "units": f"{p.occupied}/{p.units}",
                "occupancy": p.occupancy_rate,
                "status": p.status.value,
                "status_label": p.status.value.title(),
                "revenue": f"KSh {p.monthly:,.0f}"  # TODO: Use currency formatting
            }
            for p in properties
        ]
    
    @staticmethod
    def render_deposits(deposits: List[Deposit]) -> List[Dict[str, str]]:
        """Render deposit data"""
        return [
            {
                "tenant": d.tenant,
                "unit": d.unit,
                "amount": f"KSh {d.amount:,.0f}"  # TODO: Use currency formatting
            }
            for d in deposits
        ]
    
    @staticmethod
    def render_maintenance(maintenance: List[Maintenance]) -> List[Dict[str, Any]]:
        """Render maintenance data"""
        return [
            {
                "id": m.id,
                "unit": m.unit,
                "description": m.description,
                "priority": m.priority.value,
                "status": m.status.value,
                "status_label": m.status.value.title(),
                "logged": m.logged,
                "is_open": m.is_open
            }
            for m in maintenance
        ]
    
    @staticmethod
    def render_activities(activities: List[Activity]) -> List[Dict[str, Any]]:
        """Render activity data"""
        return [
            {
                "type": a.type.value,
                "icon": a.icon,
                "title": a.title,
                "description": a.description,
                "timestamp": a.timestamp
            }
            for a in activities[:6]  # Show only latest 6
        ]

# ============================================================================
# ANALYTICS ENGINE (Data Analysis Functions)
# ============================================================================

class AnalyticsEngine:
    """Pure functional analytics operations"""
    
    @staticmethod
    def calculate_collection_rate(revenue: RevenueRecord) -> float:
        """Calculate collection rate as pure function"""
        return (revenue.collected / revenue.target) * 100 if revenue.target > 0 else 0
    
    @staticmethod
    def get_monthly_trend(revenue_history: List[RevenueRecord]) -> List[Dict[str, Any]]:
        """Calculate monthly trends"""
        return [
            {
                "month": r.month,
                "collected": r.collected,
                "target": r.target,
                "collection_rate": AnalyticsEngine.calculate_collection_rate(r)
            }
            for r in revenue_history
        ]
    
    @staticmethod
    def calculate_portfolio_metrics(portfolio: Portfolio) -> Dict[str, Any]:
        """Calculate comprehensive portfolio metrics"""
        total_revenue = sum(p.monthly for p in portfolio.properties)
        total_units = sum(p.units for p in portfolio.properties)
        occupied_units = sum(p.occupied for p in portfolio.properties)
        
        # Group properties by status
        status_groups = {}
        for p in portfolio.properties:
            status_groups.setdefault(p.status, []).append(p)
        
        return {
            "total_properties": len(portfolio.properties),
            "total_units": total_units,
            "occupied_units": occupied_units,
            "vacant_units": total_units - occupied_units,
            "occupancy_rate": (occupied_units / total_units) * 100 if total_units > 0 else 0,
            "total_monthly_revenue": total_revenue,
            "properties_by_status": {
                status.value: len(group)
                for status, group in status_groups.items()
            },
            "pending_rent": portfolio.pending_rent_count,
            "open_maintenance": portfolio.open_maintenance_count,
            "total_deposits": portfolio.total_deposits
        }

# ============================================================================
# COMMAND PATTERN (Action Management)
# ============================================================================

class Command:
    """Base command interface for undoable operations"""
    
    def execute(self, portfolio: Portfolio) -> Portfolio:
        raise NotImplementedError
    
    def undo(self, portfolio: Portfolio) -> Portfolio:
        raise NotImplementedError

class AddMaintenanceCommand(Command):
    """Command for adding maintenance request"""
    
    def __init__(self, unit: str, description: str, priority: Priority):
        self.unit = unit
        self.description = description
        self.priority = priority
        self._maint_id = None
    
    def execute(self, portfolio: Portfolio) -> Portfolio:
        transformer = add_maintenance_request(self.unit, self.description, self.priority)
        new_portfolio = transformer(portfolio)
        # Store the generated ID for undo
        if new_portfolio.maintenance and len(new_portfolio.maintenance) > 0:
            self._maint_id = new_portfolio.maintenance[0].id
        return new_portfolio
    
    def undo(self, portfolio: Portfolio) -> Portfolio:
        if not self._maint_id:
            return portfolio
        
        # Remove the maintenance by filtering
        updated_maintenance = [
            m for m in portfolio.maintenance 
            if m.id != self._maint_id
        ]
        updated_activities = [
            a for a in portfolio.activities
            if a.description != f"{self.description} — {self.unit}" or a.timestamp != "just now"
        ]
        
        return Portfolio(
            currency=portfolio.currency,
            properties=portfolio.properties,
            revenue_history=portfolio.revenue_history,
            deposits=portfolio.deposits,
            maintenance=updated_maintenance,
            activities=updated_activities
        )

class CommandManager:
    """Manager for executing commands with history"""
    
    def __init__(self):
        self._history: List[Command] = []
        self._redo_stack: List[Command] = []
    
    def execute(self, command: Command, portfolio: Portfolio) -> Portfolio:
        """Execute a command and add to history"""
        result = command.execute(portfolio)
        self._history.append(command)
        self._redo_stack.clear()  # Clear redo stack on new command
        return result
    
    def undo(self, portfolio: Portfolio) -> Portfolio:
        """Undo the last command"""
        if not self._history:
            return portfolio
        
        command = self._history.pop()
        self._redo_stack.append(command)
        return command.undo(portfolio)
    
    def redo(self, portfolio: Portfolio) -> Portfolio:
        """Redo the last undone command"""
        if not self._redo_stack:
            return portfolio
        
        command = self._redo_stack.pop()
        self._history.append(command)
        return command.execute(portfolio)

# ============================================================================
# SERVICE LAYER (Application Services)
# ============================================================================

class LandlordService:
    """Main service layer for landlord application"""
    
    def __init__(self):
        self.repository = PortfolioRepository()
        self.command_manager = CommandManager()
        self._portfolio = self.repository.load()
        self._analytics = AnalyticsEngine()
        self._ui_state = UIState(self._portfolio)
    
    @property
    def portfolio(self) -> Portfolio:
        return self._portfolio
    
    @portfolio.setter
    def portfolio(self, value: Portfolio) -> None:
        self._portfolio = value
        self.repository.save(value)
        self._ui_state.set_portfolio(value)
    
    def add_maintenance_request(self, unit: str, description: str, priority: Priority) -> None:
        """Add a maintenance request using command pattern"""
        command = AddMaintenanceCommand(unit, description, priority)
        self.portfolio = self.command_manager.execute(command, self.portfolio)
    
    def update_maintenance_status(self, maint_id: str, status: MaintenanceStatus) -> None:
        """Update maintenance status using functional transformation"""
        transformer = update_maintenance_status(maint_id, status)
        self.portfolio = transformer(self.portfolio)
    
    def update_currency(self, currency_code: str) -> None:
        """Update currency using functional transformation"""
        transformer = update_currency(currency_code)
        self.portfolio = transformer(self.portfolio)
    
    def undo_last_action(self) -> None:
        """Undo the last action"""
        self.portfolio = self.command_manager.undo(self.portfolio)
    
    def redo_last_action(self) -> None:
        """Redo the last undone action"""
        self.portfolio = self.command_manager.redo(self.portfolio)
    
    def get_portfolio_metrics(self) -> Dict[str, Any]:
        """Get portfolio metrics from analytics engine"""
        return self._analytics.calculate_portfolio_metrics(self.portfolio)
    
    def get_filtered_properties(self) -> List[Property]:
        """Get filtered properties from UI state"""
        return self._ui_state.get_filtered_properties()
    
    def set_property_filter(self, search: str, status: str) -> None:
        """Set property filters"""
        self._ui_state._filters["property_search"] = search
        self._ui_state._filters["status_filter"] = status
        self._ui_state._notify_observers()
    
    def generate_report(self) -> str:
        """Generate a portfolio report"""
        metrics = self.get_portfolio_metrics()
        lines = [
            "MWAROKIN ESTATES — LANDLORD PORTFOLIO REPORT",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"Properties: {metrics['total_properties']}",
            f"Units: {metrics['occupied_units']}/{metrics['total_units']} occupied",
            f"Monthly Revenue: {CurrencyManager.format_amount(metrics['total_monthly_revenue'], self.portfolio.currency)}",
            f"Open Maintenance: {metrics['open_maintenance']}",
            "",
            "PROPERTY BREAKDOWN",
        ]
        
        for p in self.portfolio.properties:
            lines.append(f"  - {p.name}: {p.occupied}/{p.units} units, {CurrencyManager.format_amount(p.monthly, self.portfolio.currency)}/mo, status: {p.status.value}")
        
        lines.append("")
        lines.append("DEPOSITS HELD")
        for d in self.portfolio.deposits:
            lines.append(f"  - {d.tenant} ({d.unit}): {CurrencyManager.format_amount(d.amount, self.portfolio.currency)}")
        
        return "\n".join(lines)

# ============================================================================
# STORAGE PLACEHOLDERS (Browser API Mock)
# ============================================================================

def localStorage_get(key: str) -> str:
    """Get item from localStorage (placeholder for Python backend)"""
    try:
        if os.path.exists(f"_storage_{key}.json"):
            with open(f"_storage_{key}.json", "r") as f:
                return f.read()
    except:
        pass
    return ""

def localStorage_set(key: str, value: str) -> None:
    """Set item in localStorage (placeholder for Python backend)"""
    try:
        with open(f"_storage_{key}.json", "w") as f:
            f.write(value)
    except:
        pass

# ============================================================================
# MAIN APPLICATION
# ============================================================================

class MwarokinApp:
    """Main application class with agentic UI management"""
    
    def __init__(self):
        self.service = LandlordService()
        self._renderers = {
            "dashboard": self.render_dashboard,
            "properties": self.render_properties,
            "maintenance": self.render_maintenance
        }
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize the application"""
        if self._initialized:
            return
        
        # Register UI state observers
        self.service._ui_state.add_observer(self.on_state_change)
        self._initialized = True
        print("Mwarokin Estates initialized successfully")
    
    def on_state_change(self, portfolio: Portfolio) -> None:
        """React to state changes"""
        print(f"Portfolio updated: {len(portfolio.properties)} properties, {portfolio.occupied_units} occupied units")
    
    def render_dashboard(self) -> Dict[str, Any]:
        """Render dashboard data"""
        portfolio = self.service.portfolio
        metrics = self.service.get_portfolio_metrics()
        
        return {
            "title": "Landlord Command Center",
            "greeting": "Welcome back, Mr. Mwarema",
            "date": datetime.now().strftime("%d %b %Y"),
            "property_count": metrics["total_properties"],
            "occupancy": f"{metrics['occupancy_rate']:.0f}% ({metrics['occupied_units']}/{metrics['total_units']})",
            "metrics": metrics,
            "kpis": ViewRenderer.render_kpi(portfolio, portfolio.currency)
        }
    
    def render_properties(self) -> List[Dict[str, Any]]:
        """Render property table"""
        properties = self.service.get_filtered_properties()
        return ViewRenderer.render_property_table(properties)
    
    def render_maintenance(self) -> List[Dict[str, Any]]:
        """Render maintenance list"""
        maintenance = self.service.portfolio.maintenance
        return ViewRenderer.render_maintenance(maintenance)
    
    def render_deposits(self) -> List[Dict[str, str]]:
        """Render deposit ledger"""
        deposits = self.service.portfolio.deposits
        return ViewRenderer.render_deposits(deposits)
    
    def render_activities(self) -> List[Dict[str, Any]]:
        """Render activity feed"""
        activities = self.service.portfolio.activities
        return ViewRenderer.render_activities(activities)
    
    def export_report(self) -> str:
        """Export portfolio report"""
        return self.service.generate_report()
    
    def simulate_real_time_updates(self) -> None:
        """Simulate real-time updates for demonstration"""
        # Add random activity
        activity_types = [
            ActivityType.PAYMENT,
            ActivityType.MAINTENANCE,
            ActivityType.TENANT
        ]
        
        activity = Activity(
            type=random.choice(activity_types),
            title="System update",
            description=f"Automated update at {datetime.now().strftime('%H:%M:%S')}",
            timestamp="just now"
        )
        
        portfolio = self.service.portfolio
        new_portfolio = Portfolio(
            currency=portfolio.currency,
            properties=portfolio.properties,
            revenue_history=portfolio.revenue_history,
            deposits=portfolio.deposits,
            maintenance=portfolio.maintenance,
            activities=[activity] + portfolio.activities
        )
        
        self.service.portfolio = new_portfolio
        print("Real-time update simulation completed")

# ============================================================================
# CLI INTERFACE (For demonstration)
# ============================================================================

def main():
    """Main entry point for the application"""
    app = MwarokinApp()
    app.initialize()
    
    print("\n" + "="*60)
    print("MWAROKIN ESTATES - LANDLORD DASHBOARD")
    print("="*60)
    
    # Display dashboard
    dashboard = app.render_dashboard()
    print(f"\n📊 {dashboard['title']}")
    print(f"👋 {dashboard['greeting']}")
    print(f"📅 {dashboard['date']}")
    print(f"🏢 {dashboard['property_count']} properties • {dashboard['occupancy']}")
    
    # Display metrics
    metrics = dashboard['metrics']
    print(f"\n📈 Portfolio Metrics:")
    print(f"  • Total Revenue: {CurrencyManager.format_amount(metrics['total_monthly_revenue'], app.service.portfolio.currency)}/month")
    print(f"  • Pending Rent: {metrics['pending_rent']} properties")
    print(f"  • Open Maintenance: {metrics['open_maintenance']} requests")
    print(f"  • Total Deposits: {CurrencyManager.format_amount(metrics['total_deposits'], app.service.portfolio.currency)}")
    
    # Display properties
    print("\n🏠 Properties:")
    properties = app.render_properties()
    for prop in properties:
        print(f"  • {prop['name']}")
        print(f"    Units: {prop['units']} • Revenue: {prop['revenue']} • Status: {prop['status_label']}")
    
    # Display maintenance
    print("\n🔧 Maintenance Requests:")
    maintenance = app.render_maintenance()
    for maint in maintenance[:3]:
        print(f"  • {maint['unit']}: {maint['description'][:50]}...")
        print(f"    Priority: {maint['priority']} • Status: {maint['status_label']}")
    
    # Export report
    print(f"\n📄 Report saved to 'portfolio_report.txt'")
    with open("portfolio_report.txt", "w") as f:
        f.write(app.export_report())
    
    print("\n✅ Application ready! Simulating real-time update...")
    app.simulate_real_time_updates()
    
    print(f"\n🚀 Mwarokin Estates running successfully!")

if __name__ == "__main__":
    main()