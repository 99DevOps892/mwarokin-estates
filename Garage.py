python
# Storage Garage - Mwarokin Self-Storage
# Modern premium professional storage management system

import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import re

# ===================== DATA MODELS =====================

class UnitStatus(Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"

class PaymentStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class PaymentMethod(Enum):
    MPESA = "mpesa"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"

@dataclass
class StorageUnit:
    unit_id: str
    unit_type: str  # Small, Medium, Large
    floor: str  # Ground Floor, Second Floor, Third Floor, Fourth Floor
    level: str  # Upper, Lower
    size_sq_m: float  # floor area in square meters
    monthly_price_kes: int
    max_availability: int
    current_availability: int
    status: UnitStatus = UnitStatus.AVAILABLE
    location: str = "SC-Mombasa Road"
    features: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "status": self.status.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'StorageUnit':
        data = data.copy()
        data["status"] = UnitStatus(data["status"])
        return cls(**data)

@dataclass
class Customer:
    customer_id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    national_id: str
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Customer':
        data = data.copy()
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)

@dataclass
class Reservation:
    reservation_id: str
    unit_id: str
    customer_id: str
    start_date: datetime
    end_date: datetime
    total_amount: int
    deposit_amount: int
    status: PaymentStatus = PaymentStatus.PENDING
    payment_method: Optional[PaymentMethod] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data["start_date"] = self.start_date.isoformat()
        data["end_date"] = self.end_date.isoformat()
        data["created_at"] = self.created_at.isoformat()
        data["status"] = self.status.value
        data["payment_method"] = self.payment_method.value if self.payment_method else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Reservation':
        data = data.copy()
        data["start_date"] = datetime.fromisoformat(data["start_date"])
        data["end_date"] = datetime.fromisoformat(data["end_date"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["status"] = PaymentStatus(data["status"])
        data["payment_method"] = PaymentMethod(data["payment_method"]) if data.get("payment_method") else None
        return cls(**data)

@dataclass
class Payment:
    payment_id: str
    reservation_id: str
    amount: int
    method: PaymentMethod
    status: PaymentStatus
    transaction_reference: str
    paid_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data["method"] = self.method.value
        data["status"] = self.status.value
        data["paid_at"] = self.paid_at.isoformat() if self.paid_at else None
        data["created_at"] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Payment':
        data = data.copy()
        data["method"] = PaymentMethod(data["method"])
        data["status"] = PaymentStatus(data["status"])
        data["paid_at"] = datetime.fromisoformat(data["paid_at"]) if data.get("paid_at") else None
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)

@dataclass
class SpaceCalculatorItem:
    name: str
    area_sq_m: float
    category: str

@dataclass
class SpaceCalculatorResult:
    total_area: float
    recommended_unit_type: str
    recommended_unit_size: float
    recommended_price: int
    items_count: Dict[str, int] = field(default_factory=dict)
    units_matching: List[StorageUnit] = field(default_factory=list)

# ===================== STORAGE MANAGER =====================

class StorageGarage:
    """Main storage management system for Mwarokin Self-Storage"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.units: Dict[str, StorageUnit] = {}
        self.customers: Dict[str, Customer] = {}
        self.reservations: Dict[str, Reservation] = {}
        self.payments: Dict[str, Payment] = {}
        
        # Room item catalog for calculator
        self.item_catalog: Dict[str, List[SpaceCalculatorItem]] = self._init_item_catalog()
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Load existing data
        self._load_all_data()
        
        # If no data, initialize with sample units
        if not self.units:
            self._initialize_sample_units()
            self._save_units()
    
    def _init_item_catalog(self) -> Dict[str, List[SpaceCalculatorItem]]:
        """Initialize the item catalog for space calculator"""
        return {
            "Living Room": [
                SpaceCalculatorItem("Single chair", 0.6, "Living Room"),
                SpaceCalculatorItem("Chaise", 1.4, "Living Room"),
                SpaceCalculatorItem("Coffee table", 0.8, "Living Room"),
                SpaceCalculatorItem("Loveseat", 1.6, "Living Room"),
                SpaceCalculatorItem("Sofa", 2.4, "Living Room"),
                SpaceCalculatorItem("L-shaped sofa", 3.6, "Living Room"),
                SpaceCalculatorItem("Footstool", 0.3, "Living Room"),
            ],
            "Bedroom": [
                SpaceCalculatorItem("Single bed", 2.0, "Bedroom"),
                SpaceCalculatorItem("Double bed", 3.2, "Bedroom"),
                SpaceCalculatorItem("Wardrobe", 1.8, "Bedroom"),
                SpaceCalculatorItem("Chest of drawers", 1.0, "Bedroom"),
                SpaceCalculatorItem("Bedside table", 0.3, "Bedroom"),
                SpaceCalculatorItem("Dressing table", 1.2, "Bedroom"),
            ],
            "Kitchen and Dining": [
                SpaceCalculatorItem("Dining table", 2.2, "Kitchen and Dining"),
                SpaceCalculatorItem("Dining chair", 0.4, "Kitchen and Dining"),
                SpaceCalculatorItem("Fridge", 1.1, "Kitchen and Dining"),
                SpaceCalculatorItem("Cooker", 0.9, "Kitchen and Dining"),
                SpaceCalculatorItem("Microwave", 0.3, "Kitchen and Dining"),
                SpaceCalculatorItem("Kitchen cabinet", 1.4, "Kitchen and Dining"),
            ],
            "Childrens Room": [
                SpaceCalculatorItem("Cot", 1.6, "Childrens Room"),
                SpaceCalculatorItem("Kids bed", 1.8, "Childrens Room"),
                SpaceCalculatorItem("Toy chest", 0.6, "Childrens Room"),
                SpaceCalculatorItem("Study desk", 0.9, "Childrens Room"),
                SpaceCalculatorItem("Bookshelf", 0.7, "Childrens Room"),
            ],
            "Home Office": [
                SpaceCalculatorItem("Office desk", 1.2, "Home Office"),
                SpaceCalculatorItem("Office chair", 0.5, "Home Office"),
                SpaceCalculatorItem("Filing cabinet", 0.6, "Home Office"),
                SpaceCalculatorItem("Bookshelf", 0.9, "Home Office"),
                SpaceCalculatorItem("Printer stand", 0.4, "Home Office"),
            ],
            "Utility Room": [
                SpaceCalculatorItem("Washing machine", 0.7, "Utility Room"),
                SpaceCalculatorItem("Dryer", 0.7, "Utility Room"),
                SpaceCalculatorItem("Storage shelving", 1.0, "Utility Room"),
                SpaceCalculatorItem("Ironing board", 0.5, "Utility Room"),
            ],
            "Garden": [
                SpaceCalculatorItem("Lawn mower", 1.0, "Garden"),
                SpaceCalculatorItem("Garden table", 1.8, "Garden"),
                SpaceCalculatorItem("Garden chair", 0.5, "Garden"),
                SpaceCalculatorItem("Tool shed items", 1.4, "Garden"),
                SpaceCalculatorItem("BBQ grill", 1.1, "Garden"),
            ],
            "Others": [
                SpaceCalculatorItem("Boxes (medium)", 0.4, "Others"),
                SpaceCalculatorItem("Boxes (large)", 0.6, "Others"),
                SpaceCalculatorItem("Bicycle", 1.0, "Others"),
                SpaceCalculatorItem("Suitcase", 0.3, "Others"),
                SpaceCalculatorItem("Mattress", 1.9, "Others"),
            ]
        }
    
    def _initialize_sample_units(self):
        """Initialize the storage facility with sample units"""
        sample_units = [
            # Small Units
            StorageUnit("U-001", "Small Unit", "Second Floor", "Upper", 3.0, 8860, 2, 2),
            StorageUnit("U-002", "Small Unit", "Second Floor", "Lower", 3.0, 11310, 2, 2),
            StorageUnit("U-003", "Small Unit", "Ground Floor", "Upper", 4.0, 11813, 1, 1),
            StorageUnit("U-004", "Small Unit", "Third Floor", "Upper", 4.0, 11813, 5, 5),
            StorageUnit("U-005", "Small Unit", "Second Floor", "Upper", 5.0, 14766, 2, 2),
            StorageUnit("U-006", "Small Unit", "Third Floor", "Upper", 5.0, 14766, 15, 15),
            StorageUnit("U-007", "Small Unit", "Ground Floor", "Lower", 4.0, 15080, 2, 2),
            StorageUnit("U-008", "Small Unit", "Second Floor", "Lower", 4.0, 15080, 1, 1),
            StorageUnit("U-009", "Small Unit", "Third Floor", "Lower", 5.0, 18850, 5, 5),
            StorageUnit("U-010", "Small Unit", "Fourth Floor", "Lower", 5.0, 18850, 3, 3),
            # Medium Units
            StorageUnit("U-011", "Medium Unit", "Second Floor", "Upper", 6.0, 17719, 1, 1),
            StorageUnit("U-012", "Medium Unit", "Third Floor", "Upper", 6.0, 17719, 1, 1),
            StorageUnit("U-013", "Medium Unit", "Ground Floor", "Upper", 8.0, 23600, 2, 2),
            StorageUnit("U-014", "Medium Unit", "Second Floor", "Upper", 8.0, 23600, 1, 1),
            StorageUnit("U-015", "Medium Unit", "Fourth Floor", "Upper", 8.0, 23600, 3, 3),
            # Large Units
            StorageUnit("U-016", "Large Unit", "Ground Floor", "Upper", 12.0, 35400, 2, 2),
            StorageUnit("U-017", "Large Unit", "Second Floor", "Upper", 12.0, 35400, 1, 1),
            StorageUnit("U-018", "Large Unit", "Third Floor", "Upper", 12.0, 35400, 3, 3),
            StorageUnit("U-019", "Large Unit", "Ground Floor", "Upper", 16.0, 47200, 1, 1),
            StorageUnit("U-020", "Large Unit", "Fourth Floor", "Upper", 16.0, 47200, 2, 2),
        ]
        
        for unit in sample_units:
            self.units[unit.unit_id] = unit
    
    # ===================== DATA PERSISTENCE =====================
    
    def _get_file_path(self, name: str) -> str:
        return os.path.join(self.data_dir, f"{name}.json")
    
    def _save_data(self, name: str, data: Dict):
        with open(self._get_file_path(name), "w") as f:
            json.dump(data, f, indent=2, default=str)
    
    def _load_data(self, name: str) -> Dict:
        filepath = self._get_file_path(name)
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return json.load(f)
        return {}
    
    def _save_units(self):
        data = {uid: unit.to_dict() for uid, unit in self.units.items()}
        self._save_data("units", data)
    
    def _load_units(self):
        data = self._load_data("units")
        for uid, unit_data in data.items():
            self.units[uid] = StorageUnit.from_dict(unit_data)
    
    def _save_customers(self):
        data = {cid: customer.to_dict() for cid, customer in self.customers.items()}
        self._save_data("customers", data)
    
    def _load_customers(self):
        data = self._load_data("customers")
        for cid, customer_data in data.items():
            self.customers[cid] = Customer.from_dict(customer_data)
    
    def _save_reservations(self):
        data = {rid: reservation.to_dict() for rid, reservation in self.reservations.items()}
        self._save_data("reservations", data)
    
    def _load_reservations(self):
        data = self._load_data("reservations")
        for rid, reservation_data in data.items():
            self.reservations[rid] = Reservation.from_dict(reservation_data)
    
    def _save_payments(self):
        data = {pid: payment.to_dict() for pid, payment in self.payments.items()}
        self._save_data("payments", data)
    
    def _load_payments(self):
        data = self._load_data("payments")
        for pid, payment_data in data.items():
            self.payments[pid] = Payment.from_dict(payment_data)
    
    def _load_all_data(self):
        self._load_units()
        self._load_customers()
        self._load_reservations()
        self._load_payments()
    
    def save_all_data(self):
        self._save_units()
        self._save_customers()
        self._save_reservations()
        self._save_payments()
    
    # ===================== CUSTOMER MANAGEMENT =====================
    
    def create_customer(self, first_name: str, last_name: str, email: str, 
                        phone: str, national_id: str) -> Customer:
        """Create a new customer"""
        customer_id = f"C-{datetime.now().strftime('%Y%m%d')}-{len(self.customers) + 1:04d}"
        customer = Customer(
            customer_id=customer_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            national_id=national_id
        )
        self.customers[customer_id] = customer
        self._save_customers()
        return customer
    
    def get_customer(self, customer_id: str) -> Optional[Customer]:
        return self.customers.get(customer_id)
    
    def get_customer_by_email(self, email: str) -> Optional[Customer]:
        for customer in self.customers.values():
            if customer.email.lower() == email.lower():
                return customer
        return None
    
    def get_customer_by_phone(self, phone: str) -> Optional[Customer]:
        for customer in self.customers.values():
            if customer.phone == phone:
                return customer
        return None
    
    def update_customer(self, customer_id: str, **kwargs) -> Optional[Customer]:
        customer = self.get_customer(customer_id)
        if not customer:
            return None
        
        for key, value in kwargs.items():
            if hasattr(customer, key):
                setattr(customer, key, value)
        
        self._save_customers()
        return customer
    
    # ===================== UNIT MANAGEMENT =====================
    
    def get_available_units(self, floor: Optional[str] = None, 
                           size_range: Optional[Tuple[float, float]] = None,
                           unit_type: Optional[str] = None) -> List[StorageUnit]:
        """Get available units with optional filters"""
        available = []
        for unit in self.units.values():
            if unit.current_availability <= 0:
                continue
            if unit.status != UnitStatus.AVAILABLE:
                continue
            
            if floor and unit.floor != floor:
                continue
            
            if size_range:
                min_size, max_size = size_range
                if not (min_size <= unit.size_sq_m <= max_size):
                    continue
            
            if unit_type and unit.unit_type != unit_type:
                continue
            
            available.append(unit)
        
        # Sort by price
        return sorted(available, key=lambda u: u.monthly_price_kes)
    
    def get_unit(self, unit_id: str) -> Optional[StorageUnit]:
        return self.units.get(unit_id)
    
    def update_unit_availability(self, unit_id: str, delta: int) -> Optional[StorageUnit]:
        """Update availability count by delta (positive to increase, negative to decrease)"""
        unit = self.get_unit(unit_id)
        if not unit:
            return None
        
        new_availability = unit.current_availability + delta
        if new_availability < 0:
            raise ValueError(f"Not enough availability for unit {unit_id}")
        
        unit.current_availability = new_availability
        if new_availability == 0:
            unit.status = UnitStatus.OCCUPIED
        else:
            unit.status = UnitStatus.AVAILABLE
        
        self._save_units()
        return unit
    
    def reserve_unit(self, unit_id: str, customer_id: str, months: int = 1) -> Optional[Reservation]:
        """Reserve a unit for a customer"""
        unit = self.get_unit(unit_id)
        if not unit:
            return None
        
        if unit.current_availability <= 0:
            raise ValueError(f"Unit {unit_id} is not available")
        
        customer = self.get_customer(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        # Create reservation
        reservation_id = f"RES-{datetime.now().strftime('%Y%m%d')}-{len(self.reservations) + 1:04d}"
        start_date = datetime.now()
        end_date = start_date + timedelta(days=30 * months)
        total_amount = unit.monthly_price_kes * months
        deposit_amount = int(total_amount * 0.5)  # 50% deposit
        
        reservation = Reservation(
            reservation_id=reservation_id,
            unit_id=unit_id,
            customer_id=customer_id,
            start_date=start_date,
            end_date=end_date,
            total_amount=total_amount,
            deposit_amount=deposit_amount,
            status=PaymentStatus.PENDING
        )
        
        # Reduce availability
        self.update_unit_availability(unit_id, -1)
        
        self.reservations[reservation_id] = reservation
        self._save_reservations()
        return reservation
    
    def cancel_reservation(self, reservation_id: str) -> bool:
        """Cancel a reservation and restore unit availability"""
        reservation = self.reservations.get(reservation_id)
        if not reservation:
            return False
        
        if reservation.status == PaymentStatus.COMPLETED:
            raise ValueError("Cannot cancel a completed reservation")
        
        # Restore unit availability
        self.update_unit_availability(reservation.unit_id, 1)
        
        # Update reservation status
        reservation.status = PaymentStatus.REFUNDED
        self._save_reservations()
        return True
    
    # ===================== PAYMENT MANAGEMENT =====================
    
    def process_payment(self, reservation_id: str, method: PaymentMethod, 
                       transaction_reference: str, amount: Optional[int] = None) -> Optional[Payment]:
        """Process payment for a reservation"""
        reservation = self.reservations.get(reservation_id)
        if not reservation:
            return None
        
        if reservation.status == PaymentStatus.COMPLETED:
            raise ValueError("Reservation already paid")
        
        payment_amount = amount or reservation.deposit_amount
        if payment_amount > reservation.total_amount:
            raise ValueError("Payment amount exceeds total")
        
        payment_id = f"PAY-{datetime.now().strftime('%Y%m%d')}-{len(self.payments) + 1:04d}"
        
        payment = Payment(
            payment_id=payment_id,
            reservation_id=reservation_id,
            amount=payment_amount,
            method=method,
            status=PaymentStatus.COMPLETED,
            transaction_reference=transaction_reference,
            paid_at=datetime.now()
        )
        
        self.payments[payment_id] = payment
        
        # Update reservation status
        if payment_amount >= reservation.total_amount:
            reservation.status = PaymentStatus.COMPLETED
        else:
            reservation.status = PaymentStatus.PENDING
        
        self._save_payments()
        self._save_reservations()
        return payment
    
    def get_payment(self, payment_id: str) -> Optional[Payment]:
        return self.payments.get(payment_id)
    
    def get_reservation_payments(self, reservation_id: str) -> List[Payment]:
        return [p for p in self.payments.values() if p.reservation_id == reservation_id]
    
    # ===================== SPACE CALCULATOR =====================
    
    def calculate_space_needed(self, items: Dict[str, int], 
                              category: Optional[str] = None) -> SpaceCalculatorResult:
        """
        Calculate space needed based on selected items
        items: Dict of item_name -> quantity
        """
        total_area = 0.0
        items_count = {}
        items_used = []
        
        # Filter items by category if specified
        for cat, item_list in self.item_catalog.items():
            if category and cat != category:
                continue
            
            for item in item_list:
                quantity = items.get(item.name, 0)
                if quantity > 0:
                    total_area += quantity * item.area_sq_m
                    items_count[item.name] = quantity
                    items_used.append(item)
        
        # Add 15% circulation allowance
        total_area_with_allowance = total_area * 1.15
        
        # Find matching units
        matching_units = []
        recommended_unit = None
        
        for unit in self.units.values():
            if unit.current_availability > 0 and unit.size_sq_m >= total_area_with_allowance:
                matching_units.append(unit)
        
        if matching_units:
            matching_units.sort(key=lambda u: u.size_sq_m)
            recommended_unit = matching_units[0]
        
        result = SpaceCalculatorResult(
            total_area=round(total_area_with_allowance, 1),
            recommended_unit_type=recommended_unit.unit_type if recommended_unit else "None",
            recommended_unit_size=recommended_unit.size_sq_m if recommended_unit else 0,
            recommended_price=recommended_unit.monthly_price_kes if recommended_unit else 0,
            items_count=items_count,
            units_matching=matching_units[:5]  # Top 5 matches
        )
        
        return result
    
    def get_item_categories(self) -> List[str]:
        """Get all available item categories for the calculator"""
        return list(self.item_catalog.keys())
    
    def get_items_for_category(self, category: str) -> List[SpaceCalculatorItem]:
        """Get items for a specific category"""
        return self.item_catalog.get(category, [])
    
    # ===================== REPORTS AND STATISTICS =====================
    
    def get_facility_stats(self) -> Dict:
        """Get overall facility statistics"""
        total_units = len(self.units)
        total_available = sum(1 for u in self.units.values() if u.current_availability > 0)
        total_occupied = sum(1 for u in self.units.values() if u.current_availability == 0)
        
        occupied_capacity = 0
        total_capacity = 0
        for unit in self.units.values():
            total_capacity += unit.max_availability
            occupied_capacity += unit.max_availability - unit.current_availability
        
        occupancy_rate = (occupied_capacity / total_capacity * 100) if total_capacity > 0 else 0
        
        return {
            "total_units": total_units,
            "available_units": total_available,
            "occupied_units": total_occupied,
            "occupancy_rate": round(occupancy_rate, 1),
            "total_capacity": total_capacity,
            "occupied_capacity": occupied_capacity
        }
    
    def get_revenue_report(self, start_date: Optional[datetime] = None, 
                           end_date: Optional[datetime] = None) -> Dict:
        """Generate revenue report for a period"""
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        total_revenue = 0
        completed_payments = []
        
        for payment in self.payments.values():
            if payment.status == PaymentStatus.COMPLETED:
                if payment.paid_at and start_date <= payment.paid_at <= end_date:
                    total_revenue += payment.amount
                    completed_payments.append(payment)
        
        return {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_revenue_kes": total_revenue,
            "payment_count": len(completed_payments),
            "average_payment": round(total_revenue / len(completed_payments), 2) if completed_payments else 0
        }
    
    def get_unit_report(self) -> List[Dict]:
        """Get detailed report on all units"""
        report = []
        for unit in self.units.values():
            report.append({
                "unit_id": unit.unit_id,
                "type": unit.unit_type,
                "floor": unit.floor,
                "size_sq_m": unit.size_sq_m,
                "monthly_price_kes": unit.monthly_price_kes,
                "available": unit.current_availability,
                "max_capacity": unit.max_availability,
                "status": unit.status.value
            })
        return sorted(report, key=lambda x: x["monthly_price_kes"])
    
    # ===================== SEARCH AND FILTER =====================
    
    def search_units(self, query: str) -> List[StorageUnit]:
        """Search units by type, floor, or features"""
        query = query.lower()
        results = []
        for unit in self.units.values():
            if (query in unit.unit_type.lower() or 
                query in unit.floor.lower() or
                query in unit.level.lower() or
                str(unit.size_sq_m) in query):
                results.append(unit)
        return results
    
    def get_units_by_price_range(self, min_price: int, max_price: int) -> List[StorageUnit]:
        """Get units within a price range"""
        return [u for u in self.units.values() if min_price <= u.monthly_price_kes <= max_price]
    
    def get_units_by_size_range(self, min_size: float, max_size: float) -> List[StorageUnit]:
        """Get units within a size range"""
        return [u for u in self.units.values() if min_size <= u.size_sq_m <= max_size]
    
    # ===================== ADMIN FUNCTIONS =====================
    
    def add_unit(self, unit: StorageUnit) -> None:
        """Add a new unit to the inventory"""
        self.units[unit.unit_id] = unit
        self._save_units()
    
    def remove_unit(self, unit_id: str) -> bool:
        """Remove a unit from the inventory"""
        if unit_id in self.units:
            del self.units[unit_id]
            self._save_units()
            return True
        return False
    
    def update_unit_price(self, unit_id: str, new_price: int) -> Optional[StorageUnit]:
        """Update the price of a unit"""
        unit = self.get_unit(unit_id)
        if not unit:
            return None
        unit.monthly_price_kes = new_price
        self._save_units()
        return unit
    
    def update_unit_features(self, unit_id: str, features: List[str]) -> Optional[StorageUnit]:
        """Update features of a unit"""
        unit = self.get_unit(unit_id)
        if not unit:
            return None
        unit.features = features
        self._save_units()
        return unit
    
    def get_all_customers(self) -> List[Customer]:
        """Get all registered customers"""
        return list(self.customers.values())
    
    def get_all_reservations(self) -> List[Reservation]:
        """Get all reservations"""
        return list(self.reservations.values())
    
    def get_all_payments(self) -> List[Payment]:
        """Get all payments"""
        return list(self.payments.values())
    
    def get_customer_reservations(self, customer_id: str) -> List[Reservation]:
        """Get all reservations for a customer"""
        return [r for r in self.reservations.values() if r.customer_id == customer_id]
    
    def get_customer_payments(self, customer_id: str) -> List[Payment]:
        """Get all payments for a customer"""
        customer_reservations = self.get_customer_reservations(customer_id)
        reservation_ids = {r.reservation_id for r in customer_reservations}
        return [p for p in self.payments.values() if p.reservation_id in reservation_ids]

# ===================== COMMAND LINE INTERFACE =====================

def main():
    """Command line interface for Storage Garage"""
    storage = StorageGarage()
    
    while True:
        print("\n" + "=" * 50)
        print("STORAGE GARAGE - Mwarokin Self-Storage")
        print("=" * 50)
        print("1. View available units")
        print("2. Create customer")
        print("3. Reserve unit")
        print("4. Process payment")
        print("5. View facility statistics")
        print("6. Space calculator")
        print("7. View revenue report")
        print("8. Search units")
        print("9. Exit")
        print("-" * 50)
        
        choice = input("Enter your choice: ").strip()
        
        if choice == "1":
            # View available units
            floor = input("Filter by floor (or press Enter for all): ").strip() or None
            units = storage.get_available_units(floor=floor)
            if not units:
                print("\nNo available units found.")
            else:
                print(f"\n{'Unit ID':<10} {'Type':<15} {'Floor':<15} {'Size':<8} {'Price':<12} {'Available':<10}")
                print("-" * 80)
                for u in units[:20]:
                    print(f"{u.unit_id:<10} {u.unit_type:<15} {u.floor:<15} {u.size_sq_m:<8.1f} KES {u.monthly_price_kes:<8} {u.current_availability:<10}")
        
        elif choice == "2":
            # Create customer
            print("\n--- Create New Customer ---")
            first_name = input("First name: ").strip()
            last_name = input("Last name: ").strip()
            email = input("Email: ").strip()
            phone = input("Phone: ").strip()
            national_id = input("National ID: ").strip()
            
            try:
                customer = storage.create_customer(first_name, last_name, email, phone, national_id)
                print(f"\n✅ Customer created successfully!")
                print(f"Customer ID: {customer.customer_id}")
                print(f"Name: {customer.first_name} {customer.last_name}")
            except Exception as e:
                print(f"\n❌ Error: {e}")
        
        elif choice == "3":
            # Reserve unit
            print("\n--- Reserve a Unit ---")
            customer_id = input("Customer ID: ").strip()
            customer = storage.get_customer(customer_id)
            if not customer:
                print("❌ Customer not found.")
                continue
            
            unit_id = input("Unit ID: ").strip()
            unit = storage.get_unit(unit_id)
            if not unit:
                print("❌ Unit not found.")
                continue
            
            months = input("Number of months (default 1): ").strip()
            months = int(months) if months else 1
            
            try:
                reservation = storage.reserve_unit(unit_id, customer_id, months)
                if reservation:
                    print(f"\n✅ Reservation created successfully!")
                    print(f"Reservation ID: {reservation.reservation_id}")
                    print(f"Unit: {unit.unit_type} ({unit.size_sq_m}m²)")
                    print(f"Total: KES {reservation.total_amount:,}")
                    print(f"Deposit: KES {reservation.deposit_amount:,}")
                    print(f"Payment Status: {reservation.status.value}")
            except Exception as e:
                print(f"\n❌ Error: {e}")
        
        elif choice == "4":
            # Process payment
            print("\n--- Process Payment ---")
            reservation_id = input("Reservation ID: ").strip()
            reservation = storage.reservations.get(reservation_id)
            if not reservation:
                print("❌ Reservation not found.")
                continue
            
            print(f"\nReservation: {reservation.reservation_id}")
            print(f"Unit: {storage.get_unit(reservation.unit_id).unit_type}")
            print(f"Total Amount: KES {reservation.total_amount:,}")
            print(f"Deposit: KES {reservation.deposit_amount:,}")
            
            method_input = input("Payment Method (mpesa/card/bank_transfer): ").strip().lower()
            method_map = {
                "mpesa": PaymentMethod.MPESA,
                "card": PaymentMethod.CARD,
                "bank_transfer": PaymentMethod.BANK_TRANSFER
            }
            method = method_map.get(method_input)
            if not method:
                print("❌ Invalid payment method.")
                continue
            
            amount_input = input("Amount to pay (or press Enter for deposit amount): ").strip()
            amount = int(amount_input) if amount_input else reservation.deposit_amount
            
            transaction_ref = input("Transaction reference: ").strip()
            if not transaction_ref:
                print("❌ Transaction reference required.")
                continue
            
            try:
                payment = storage.process_payment(reservation_id, method, transaction_ref, amount)
                if payment:
                    print(f"\n✅ Payment processed successfully!")
                    print(f"Payment ID: {payment.payment_id}")
                    print(f"Amount: KES {payment.amount:,}")
                    print(f"Status: {payment.status.value}")
            except Exception as e:
                print(f"\n❌ Error: {e}")
        
        elif choice == "5":
            # Facility statistics
            stats = storage.get_facility_stats()
            print("\n--- Facility Statistics ---")
            print(f"Total Units: {stats['total_units']}")
            print(f"Available Units: {stats['available_units']}")
            print(f"Occupied Units: {stats['occupied_units']}")
            print(f"Occupancy Rate: {stats['occupancy_rate']}%")
            print(f"Total Capacity: {stats['total_capacity']}")
            print(f"Occupied Capacity: {stats['occupied_capacity']}")
        
        elif choice == "6":
            # Space calculator
            print("\n--- Space Calculator ---")
            print("Available categories:")
            categories = storage.get_item_categories()
            for i, cat in enumerate(categories, 1):
                print(f"{i}. {cat}")
            
            cat_choice = input("Select category (number or press Enter for all): ").strip()
            if cat_choice:
                try:
                    idx = int(cat_choice) - 1
                    category = categories[idx]
                except:
                    category = None
            else:
                category = None
            
            if category:
                items = storage.get_items_for_category(category)
                print(f"\nItems in {category}:")
                for item in items:
                    print(f"  - {item.name} ({item.area_sq_m}m²)")
            else:
                print("\nAll categories will be searched.")
            
            item_selections = {}
            print("\nEnter quantities for items (press Enter to finish):")
            while True:
                item_name = input("Item name (or 'done' to finish): ").strip()
                if item_name.lower() == 'done' or not item_name:
                    break
                qty = input(f"Quantity for {item_name}: ").strip()
                if qty and qty.isdigit():
                    item_selections[item_name] = int(qty)
            
            if item_selections:
                result = storage.calculate_space_needed(item_selections, category)
                print(f"\n--- Space Calculator Results ---")
                print(f"Total area needed: {result.total_area}m²")
                print(f"Recommended unit: {result.recommended_unit_type}")
                print(f"Unit size: {result.recommended_unit_size}m²")
                print(f"Monthly price: KES {result.recommended_price:,}")
                if result.units_matching:
                    print("\nMatching units:")
                    for u in result.units_matching[:3]:
                        print(f"  - {u.unit_id}: {u.unit_type} ({u.size_sq_m}m²) - KES {u.monthly_price_kes:,}/month")
        
        elif choice == "7":
            # Revenue report
            print("\n--- Revenue Report ---")
            days = input("Number of days to look back (default 30): ").strip()
            days = int(days) if days else 30
            start_date = datetime.now() - timedelta(days=days)
            
            report = storage.get_revenue_report(start_date)
            print(f"\nPeriod: {report['period_start']} to {report['period_end']}")
            print(f"Total Revenue: KES {report['total_revenue_kes']:,}")
            print(f"Payment Count: {report['payment_count']}")
            print(f"Average Payment: KES {report['average_payment']:,.2f}")
        
        elif choice == "8":
            # Search units
            query = input("Search query: ").strip()
            if query:
                results = storage.search_units(query)
                print(f"\nFound {len(results)} matching units:")
                for u in results[:10]:
                    print(f"  - {u.unit_id}: {u.unit_type} ({u.size_sq_m}m²) - Floor: {u.floor} - KES {u.monthly_price_kes:,}")
        
        elif choice == "9":
            print("\nThank you for using Storage Garage!")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
