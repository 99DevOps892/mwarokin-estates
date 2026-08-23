
"""
Modern Python Code for Rent Management System
A comprehensive system for landlords to manage properties, tenants, and payments.
Uses OOP principles with proper error handling and data persistence.
"""

import json
import os
from datetime import datetime, date
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PaymentStatus(Enum):
    """Enum for payment statuses"""
    PAID = "Paid"
    PENDING = "Pending"
    OVERDUE = "Overdue"
    PARTIAL = "Partial"


class PropertyType(Enum):
    """Enum for property types"""
    APARTMENT = "Apartment"
    HOUSE = "House"
    COMMERCIAL = "Commercial"
    LAND = "Land"
    STUDIO = "Studio"
    PENTHOUSE = "Penthouse"


class PaymentMethod(Enum):
    """Enum for payment methods"""
    M_PESA = "M-Pesa"
    BANK_TRANSFER = "Bank Transfer"
    FLUTTERWAVE = "Flutterwave"
    AIRTEL_MONEY = "Airtel Money"
    CARD = "Card (Visa/Mastercard)"


@dataclass
class Address:
    """Address data class for properties and tenants"""
    street: str = ""
    city: str = ""
    state: str = ""
    country: str = "Kenya"
    postal_code: str = ""
    coordinates: Optional[Dict[str, float]] = None

    def __post_init__(self):
        if self.coordinates is None:
            self.coordinates = {}

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'Address':
        return cls(**data)


@dataclass
class Tenant:
    """Tenant data class with personal and rental information"""
    tenant_id: int
    name: str
    email: str
    phone: str
    address: Address
    property_id: int
    monthly_rent: float
    move_in_date: date
    move_out_date: Optional[date] = None
    status: str = "Active"
    payment_history: List[Dict] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self):
        if isinstance(self.move_in_date, str):
            self.move_in_date = datetime.strptime(self.move_in_date, "%Y-%m-%d").date()
        if isinstance(self.move_out_date, str) and self.move_out_date:
            self.move_out_date = datetime.strptime(self.move_out_date, "%Y-%m-%d").date()
        if not self.payment_history:
            self.payment_history = []

    def get_full_name(self) -> str:
        """Returns the tenant's full name"""
        return self.name

    def get_initial(self) -> str:
        """Returns tenant initials"""
        parts = self.name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        return parts[0][:2].upper() if parts else ""

    def get_total_paid(self) -> float:
        """Calculate total amount paid by tenant"""
        return sum(p.get('amount', 0) for p in self.payment_history 
                  if p.get('status') == PaymentStatus.PAID.value)

    def get_outstanding_balance(self) -> float:
        """Calculate outstanding balance"""
        total_owed = self.monthly_rent
        total_paid = self.get_total_paid()
        return max(0, total_owed - total_paid)

    def add_payment(self, amount: float, method: str, 
                   transaction_code: str, status: str = "Paid") -> None:
        """Record a payment for this tenant"""
        payment = {
            'date': datetime.now().isoformat(),
            'amount': amount,
            'method': method,
            'transaction_code': transaction_code,
            'status': status,
            'month': datetime.now().strftime("%B"),
            'year': datetime.now().year
        }
        self.payment_history.append(payment)
        logger.info(f"Payment of {amount} recorded for tenant {self.name}")

    def to_dict(self) -> Dict:
        """Convert tenant to dictionary for serialization"""
        data = asdict(self)
        data['move_in_date'] = self.move_in_date.isoformat() if self.move_in_date else None
        data['move_out_date'] = self.move_out_date.isoformat() if self.move_out_date else None
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'Tenant':
        """Create tenant from dictionary data"""
        return cls(**data)


@dataclass
class Property:
    """Property data class with details and tenant management"""
    property_id: int
    name: str
    property_type: str
    address: Address
    total_units: int
    available_units: int
    base_rent: float
    description: str = ""
    amenities: List[str] = field(default_factory=list)
    tenants: List[int] = field(default_factory=list)  # List of tenant IDs
    is_active: bool = True

    def __post_init__(self):
        if not self.tenants:
            self.tenants = []
        if not self.amenities:
            self.amenities = []

    def get_occupancy_rate(self) -> float:
        """Calculate occupancy rate as percentage"""
        if self.total_units == 0:
            return 0.0
        occupied = self.total_units - self.available_units
        return (occupied / self.total_units) * 100

    def add_tenant(self, tenant_id: int) -> bool:
        """Add a tenant to the property"""
        if len(self.tenants) >= self.total_units:
            logger.warning(f"No available units in property {self.name}")
            return False
        if tenant_id not in self.tenants:
            self.tenants.append(tenant_id)
            self.available_units -= 1
            logger.info(f"Tenant {tenant_id} added to property {self.name}")
            return True
        return False

    def remove_tenant(self, tenant_id: int) -> bool:
        """Remove a tenant from the property"""
        if tenant_id in self.tenants:
            self.tenants.remove(tenant_id)
            self.available_units += 1
            logger.info(f"Tenant {tenant_id} removed from property {self.name}")
            return True
        return False

    def to_dict(self) -> Dict:
        """Convert property to dictionary for serialization"""
        data = asdict(self)
        data['address'] = self.address.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'Property':
        """Create property from dictionary data"""
        data['address'] = Address.from_dict(data['address'])
        return cls(**data)


class PaymentProcessor:
    """Handles payment processing and validation"""
    
    @staticmethod
    def validate_payment(amount: float, method: str) -> bool:
        """Validate payment details"""
        if amount <= 0:
            raise ValueError("Payment amount must be positive")
        
        valid_methods = [m.value for m in PaymentMethod]
        if method not in valid_methods:
            raise ValueError(f"Invalid payment method. Choose from: {', '.join(valid_methods)}")
        
        return True

    @staticmethod
    def process_payment(tenant: Tenant, amount: float, method: str, 
                       transaction_code: str) -> Dict:
        """Process a payment for a tenant"""
        try:
            PaymentProcessor.validate_payment(amount, method)
            
            if amount > tenant.get_outstanding_balance() + tenant.monthly_rent:
                raise ValueError("Payment amount exceeds total due")
            
            tenant.add_payment(amount, method, transaction_code, PaymentStatus.PAID.value)
            
            return {
                'success': True,
                'message': f"Payment of {amount} processed successfully for {tenant.name}",
                'transaction_code': transaction_code,
                'new_balance': tenant.get_outstanding_balance()
            }
        except Exception as e:
            logger.error(f"Payment processing failed: {str(e)}")
            return {
                'success': False,
                'message': f"Payment failed: {str(e)}",
                'error': str(e)
            }


class ReportGenerator:
    """Generates various reports for the rent management system"""
    
    @staticmethod
    def generate_revenue_report(tenants: List[Tenant], 
                               start_date: Optional[date] = None,
                               end_date: Optional[date] = None) -> Dict:
        """Generate revenue report for a given period"""
        if start_date is None:
            start_date = date(2026, 1, 1)
        if end_date is None:
            end_date = date.today()
        
        total_revenue = 0
        paid_tenants = []
        overdue_tenants = []
        
        for tenant in tenants:
            total_paid = sum(p.get('amount', 0) for p in tenant.payment_history
                           if p.get('status') == PaymentStatus.PAID.value)
            total_revenue += total_paid
            
            if tenant.get_outstanding_balance() > 0:
                overdue_tenants.append(tenant)
            else:
                paid_tenants.append(tenant)
        
        return {
            'total_revenue': total_revenue,
            'paid_tenants_count': len(paid_tenants),
            'overdue_tenants_count': len(overdue_tenants),
            'total_tenants': len(tenants),
            'collection_rate': (len(paid_tenants) / len(tenants) * 100) if tenants else 0,
            'overdue_amount': sum(t.get_outstanding_balance() for t in overdue_tenants),
            'paid_tenants': [t.name for t in paid_tenants],
            'overdue_tenants': [
                {'name': t.name, 'amount': t.get_outstanding_balance()} 
                for t in overdue_tenants
            ]
        }

    @staticmethod
    def generate_property_report(properties: List[Property]) -> List[Dict]:
        """Generate report for all properties"""
        reports = []
        for prop in properties:
            reports.append({
                'property_id': prop.property_id,
                'name': prop.name,
                'type': prop.property_type,
                'total_units': prop.total_units,
                'available_units': prop.available_units,
                'occupancy_rate': prop.get_occupancy_rate(),
                'base_rent': prop.base_rent,
                'tenant_count': len(prop.tenants),
                'is_active': prop.is_active
            })
        return reports

    @staticmethod
    def generate_tenant_report(tenant: Tenant) -> Dict:
        """Generate detailed report for a specific tenant"""
        payment_summary = []
        total_paid = 0
        
        for payment in tenant.payment_history:
            payment_summary.append({
                'date': payment.get('date'),
                'amount': payment.get('amount'),
                'method': payment.get('method'),
                'status': payment.get('status'),
                'month': payment.get('month'),
                'year': payment.get('year')
            })
            if payment.get('status') == PaymentStatus.PAID.value:
                total_paid += payment.get('amount', 0)
        
        return {
            'tenant_id': tenant.tenant_id,
            'name': tenant.name,
            'email': tenant.email,
            'phone': tenant.phone,
            'property_id': tenant.property_id,
            'monthly_rent': tenant.monthly_rent,
            'move_in_date': tenant.move_in_date,
            'status': tenant.status,
            'total_paid': total_paid,
            'outstanding_balance': tenant.get_outstanding_balance(),
            'payment_count': len(tenant.payment_history),
            'payment_summary': payment_summary,
            'notes': tenant.notes
        }


class DataManager:
    """Manages data persistence and retrieval"""
    
    DATA_FILE = "rent_management_data.json"
    
    def __init__(self):
        self.tenants: List[Tenant] = []
        self.properties: List[Property] = []
        self.next_tenant_id = 1
        self.next_property_id = 1
        self.load_data()

    def load_data(self) -> None:
        """Load data from JSON file"""
        try:
            if os.path.exists(self.DATA_FILE):
                with open(self.DATA_FILE, 'r') as f:
                    data = json.load(f)
                    
                # Load tenants
                self.tenants = []
                for tenant_data in data.get('tenants', []):
                    self.tenants.append(Tenant.from_dict(tenant_data))
                    if tenant_data.get('tenant_id', 0) >= self.next_tenant_id:
                        self.next_tenant_id = tenant_data['tenant_id'] + 1
                
                # Load properties
                self.properties = []
                for prop_data in data.get('properties', []):
                    self.properties.append(Property.from_dict(prop_data))
                    if prop_data.get('property_id', 0) >= self.next_property_id:
                        self.next_property_id = prop_data['property_id'] + 1
                
                logger.info(f"Loaded {len(self.tenants)} tenants and {len(self.properties)} properties")
        except Exception as e:
            logger.error(f"Failed to load data: {str(e)}")
            self.create_sample_data()

    def save_data(self) -> None:
        """Save data to JSON file"""
        try:
            data = {
                'tenants': [t.to_dict() for t in self.tenants],
                'properties': [p.to_dict() for p in self.properties],
                'last_tenant_id': self.next_tenant_id,
                'last_property_id': self.next_property_id
            }
            
            with open(self.DATA_FILE, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info("Data saved successfully")
        except Exception as e:
            logger.error(f"Failed to save data: {str(e)}")
            raise

    def create_sample_data(self) -> None:
        """Create sample data for testing"""
        try:
            # Create sample properties
            prop1 = Property(
                property_id=self.next_property_id,
                name="Jabavu Towers",
                property_type=PropertyType.APARTMENT.value,
                address=Address(
                    street="Jabavu Road",
                    city="Nairobi",
                    country="Kenya",
                    coordinates={'lat': -1.28333, 'lng': 36.81667}
                ),
                total_units=12,
                available_units=4,
                base_rent=22000,
                description="Modern apartment complex in Nairobi CBD",
                amenities=["Parking", "24hr Security", "Elevator"]
            )
            self.next_property_id += 1
            self.properties.append(prop1)

            prop2 = Property(
                property_id=self.next_property_id,
                name="Green Valley Estate",
                property_type=PropertyType.HOUSE.value,
                address=Address(
                    street="Valley Road",
                    city="Nairobi",
                    country="Kenya",
                    coordinates={'lat': -1.2976, 'lng': 36.7802}
                ),
                total_units=6,
                available_units=1,
                base_rent=35000,
                description="Spacious family homes in peaceful neighborhood",
                amenities=["Garden", "Parking", "Playground"]
            )
            self.next_property_id += 1
            self.properties.append(prop2)

            # Create sample tenants
            tenant1 = Tenant(
                tenant_id=self.next_tenant_id,
                name="John Mwarokin",
                email="john@mwarokin.com",
                phone="+254 712 345 678",
                address=Address(
                    street="Jabavu Road",
                    city="Nairobi",
                    country="Kenya"
                ),
                property_id=prop1.property_id,
                monthly_rent=22000,
                move_in_date=date(2025, 6, 1),
                status="Active"
            )
            self.next_tenant_id += 1
            tenant1.add_payment(22000, PaymentMethod.M_PESA.value, "MPESA123456", "Paid")
            self.tenants.append(tenant1)
            prop1.add_tenant(tenant1.tenant_id)

            tenant2 = Tenant(
                tenant_id=self.next_tenant_id,
                name="Kisha Otieno",
                email="kisha@example.com",
                phone="+254 723 456 789",
                address=Address(
                    street="Valley Road",
                    city="Nairobi",
                    country="Kenya"
                ),
                property_id=prop2.property_id,
                monthly_rent=35000,
                move_in_date=date(2025, 8, 15),
                status="Active"
            )
            self.next_tenant_id += 1
            self.tenants.append(tenant2)
            prop2.add_tenant(tenant2.tenant_id)

            logger.info("Sample data created successfully")
            self.save_data()
        except Exception as e:
            logger.error(f"Failed to create sample data: {str(e)}")

    def get_tenant(self, tenant_id: int) -> Optional[Tenant]:
        """Retrieve a tenant by ID"""
        for tenant in self.tenants:
            if tenant.tenant_id == tenant_id:
                return tenant
        return None

    def get_property(self, property_id: int) -> Optional[Property]:
        """Retrieve a property by ID"""
        for prop in self.properties:
            if prop.property_id == property_id:
                return prop
        return None

    def add_tenant(self, tenant_data: Dict) -> Tenant:
        """Add a new tenant to the system"""
        try:
            tenant = Tenant.from_dict(tenant_data)
            tenant.tenant_id = self.next_tenant_id
            self.next_tenant_id += 1
            self.tenants.append(tenant)
            
            # Add tenant to property
            property_obj = self.get_property(tenant.property_id)
            if property_obj:
                property_obj.add_tenant(tenant.tenant_id)
            
            self.save_data()
            logger.info(f"New tenant added: {tenant.name} (ID: {tenant.tenant_id})")
            return tenant
        except Exception as e:
            logger.error(f"Failed to add tenant: {str(e)}")
            raise

    def add_property(self, property_data: Dict) -> Property:
        """Add a new property to the system"""
        try:
            property_obj = Property.from_dict(property_data)
            property_obj.property_id = self.next_property_id
            self.next_property_id += 1
            self.properties.append(property_obj)
            
            self.save_data()
            logger.info(f"New property added: {property_obj.name} (ID: {property_obj.property_id})")
            return property_obj
        except Exception as e:
            logger.error(f"Failed to add property: {str(e)}")
            raise


class RentManagementSystem:
    """Main system class coordinating all functionality"""
    
    def __init__(self):
        self.data_manager = DataManager()
        self.payment_processor = PaymentProcessor()
        self.report_generator = ReportGenerator()
        logger.info("Rent Management System initialized")

    def get_all_properties(self) -> List[Property]:
        """Get all properties"""
        return self.data_manager.properties

    def get_all_tenants(self) -> List[Tenant]:
        """Get all tenants"""
        return self.data_manager.tenants

    def get_active_tenants(self) -> List[Tenant]:
        """Get all active tenants"""
        return [t for t in self.data_manager.tenants if t.status == "Active"]

    def get_tenant_by_id(self, tenant_id: int) -> Optional[Tenant]:
        """Get a tenant by ID"""
        return self.data_manager.get_tenant(tenant_id)

    def get_property_by_id(self, property_id: int) -> Optional[Property]:
        """Get a property by ID"""
        return self.data_manager.get_property(property_id)

    def add_tenant(self, name: str, email: str, phone: str, property_id: int,
                  monthly_rent: float, move_in_date: date, **kwargs) -> Tenant:
        """Add a new tenant to the system"""
        try:
            # Validate property exists
            if not self.get_property_by_id(property_id):
                raise ValueError(f"Property with ID {property_id} not found")
            
            # Create address if provided
            address = Address(
                street=kwargs.get('street', ''),
                city=kwargs.get('city', 'Nairobi'),
                country=kwargs.get('country', 'Kenya')
            )
            
            tenant_data = {
                'tenant_id': 0,  # Will be assigned by data manager
                'name': name,
                'email': email,
                'phone': phone,
                'address': address,
                'property_id': property_id,
                'monthly_rent': monthly_rent,
                'move_in_date': move_in_date,
                'notes': kwargs.get('notes', '')
            }
            
            return self.data_manager.add_tenant(tenant_data)
        except Exception as e:
            logger.error(f"Failed to add tenant: {str(e)}")
            raise

    def add_property(self, name: str, property_type: str, total_units: int,
                    base_rent: float, **kwargs) -> Property:
        """Add a new property to the system"""
        try:
            address = Address(
                street=kwargs.get('street', ''),
                city=kwargs.get('city', 'Nairobi'),
                country=kwargs.get('country', 'Kenya')
            )
            
            property_data = {
                'property_id': 0,  # Will be assigned by data manager
                'name': name,
                'property_type': property_type,
                'address': address,
                'total_units': total_units,
                'available_units': total_units,
                'base_rent': base_rent,
                'description': kwargs.get('description', ''),
                'amenities': kwargs.get('amenities', []),
                'is_active': True
            }
            
            return self.data_manager.add_property(property_data)
        except Exception as e:
            logger.error(f"Failed to add property: {str(e)}")
            raise

    def process_tenant_payment(self, tenant_id: int, amount: float, 
                              method: str, transaction_code: str) -> Dict:
        """Process a payment for a tenant"""
        try:
            tenant = self.get_tenant_by_id(tenant_id)
            if not tenant:
                raise ValueError(f"Tenant with ID {tenant_id} not found")
            
            # Validate payment
            if amount > tenant.get_outstanding_balance() + tenant.monthly_rent:
                raise ValueError("Payment amount exceeds total due")
            
            # Process payment
            result = self.payment_processor.process_payment(
                tenant, amount, method, transaction_code
            )
            
            # Save changes
            if result['success']:
                self.data_manager.save_data()
            
            return result
        except Exception as e:
            logger.error(f"Payment processing failed: {str(e)}")
            return {
                'success': False,
                'message': f"Payment failed: {str(e)}",
                'error': str(e)
            }

    def get_revenue_report(self, start_date: Optional[date] = None,
                          end_date: Optional[date] = None) -> Dict:
        """Generate a revenue report"""
        return self.report_generator.generate_revenue_report(
            self.get_all_tenants(),
            start_date,
            end_date
        )

    def get_property_report(self) -> List[Dict]:
        """Generate a property report"""
        return self.report_generator.generate_property_report(self.get_all_properties())

    def get_tenant_report(self, tenant_id: int) -> Optional[Dict]:
        """Generate a report for a specific tenant"""
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None
        return self.report_generator.generate_tenant_report(tenant)

    def get_overdue_tenants(self) -> List[Dict]:
        """Get all tenants with overdue payments"""
        overdue = []
        for tenant in self.get_all_tenants():
            balance = tenant.get_outstanding_balance()
            if balance > 0:
                overdue.append({
                    'tenant_id': tenant.tenant_id,
                    'name': tenant.name,
                    'email': tenant.email,
                    'phone': tenant.phone,
                    'outstanding_amount': balance,
                    'monthly_rent': tenant.monthly_rent,
                    'status': tenant.status
                })
        return overdue

    def get_dashboard_stats(self) -> Dict:
        """Get dashboard statistics"""
        tenants = self.get_all_tenants()
        properties = self.get_all_properties()
        
        total_rent = sum(t.monthly_rent for t in tenants)
        paid_rent = sum(t.get_total_paid() for t in tenants)
        overdue_rent = sum(t.get_outstanding_balance() for t in tenants)
        
        # Calculate occupancy
        total_units = sum(p.total_units for p in properties)
        occupied_units = sum(p.total_units - p.available_units for p in properties)
        occupancy_rate = (occupied_units / total_units * 100) if total_units > 0 else 0
        
        return {
            'total_properties': len(properties),
            'total_tenants': len(tenants),
            'active_tenants': len([t for t in tenants if t.status == "Active"]),
            'total_rent_amount': total_rent,
            'paid_rent_amount': paid_rent,
            'overdue_rent_amount': overdue_rent,
            'collection_rate': (paid_rent / total_rent * 100) if total_rent > 0 else 0,
            'occupancy_rate': occupancy_rate,
            'overdue_count': len([t for t in tenants if t.get_outstanding_balance() > 0])
        }

    def generate_tenant_csv(self, file_path: str = None) -> str:
        """Generate CSV of all tenants"""
        if file_path is None:
            file_path = f"tenants_export_{datetime.now().strftime('%Y%m%d')}.csv"
        
        try:
            import csv
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'ID', 'Name', 'Email', 'Phone', 'Property ID', 
                    'Monthly Rent', 'Total Paid', 'Outstanding', 'Status'
                ])
                
                for tenant in self.get_all_tenants():
                    writer.writerow([
                        tenant.tenant_id,
                        tenant.name,
                        tenant.email,
                        tenant.phone,
                        tenant.property_id,
                        tenant.monthly_rent,
                        tenant.get_total_paid(),
                        tenant.get_outstanding_balance(),
                        tenant.status
                    ])
            
            logger.info(f"CSV exported to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to generate CSV: {str(e)}")
            raise


def main():
    """Main function to demonstrate the rent management system"""
    try:
        # Initialize system
        system = RentManagementSystem()
        
        # Display dashboard statistics
        print("\n" + "="*50)
        print("MWAROKIN ESTATES - RENT MANAGEMENT SYSTEM")
        print("="*50)
        
        stats = system.get_dashboard_stats()
        print(f"\n📊 DASHBOARD STATISTICS:")
        print(f"  • Properties: {stats['total_properties']}")
        print(f"  • Tenants: {stats['total_tenants']} (Active: {stats['active_tenants']})")
        print(f"  • Occupancy Rate: {stats['occupancy_rate']:.1f}%")
        print(f"  • Monthly Rent Total: KSh {stats['total_rent_amount']:,.0f}")
        print(f"  • Collection Rate: {stats['collection_rate']:.1f}%")
        print(f"  • Overdue Amount: KSh {stats['overdue_rent_amount']:,.0f}")
        
        # Display all tenants
        print("\n👥 TENANTS:")
        print("-" * 80)
        tenants = system.get_all_tenants()
        for t in tenants:
            print(f"  #{t.tenant_id}: {t.name} | {t.email} | KSh {t.monthly_rent:,.0f} | "
                  f"Paid: KSh {t.get_total_paid():,.0f} | Status: {t.status}")
        
        # Display overdue tenants
        overdue = system.get_overdue_tenants()
        if overdue:
            print("\n⚠️ OVERDUE TENANTS:")
            for ot in overdue:
                print(f"  • {ot['name']} owes KSh {ot['outstanding_amount']:,.0f}")
        
        # Generate revenue report
        print("\n💰 REVENUE REPORT:")
        report = system.get_revenue_report()
        print(f"  • Total Revenue: KSh {report['total_revenue']:,.0f}")
        print(f"  • Paid Tenants: {report['paid_tenants_count']}")
        print(f"  • Overdue Tenants: {report['overdue_tenants_count']}")
        print(f"  • Collection Rate: {report['collection_rate']:.1f}%")
        
        # Process a payment (if tenants exist)
        if tenants:
            print("\n💳 PROCESSING PAYMENT:")
            test_tenant = tenants[0]
            result = system.process_tenant_payment(
                test_tenant.tenant_id,
                10000,
                PaymentMethod.M_PESA.value,
                f"PAY{datetime.now().strftime('%Y%m%d%H%M%S')}"
            )
            if result['success']:
                print(f"  ✓ {result['message']}")
                print(f"  New Balance: KSh {result['new_balance']:,.0f}")
            else:
                print(f"  ✗ {result['message']}")
        
        print("\n" + "="*50)
        print("System running successfully!")
        
    except Exception as e:
        logger.error(f"System error: {str(e)}")
        print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
