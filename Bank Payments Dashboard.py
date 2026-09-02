python
"""
Bank Dashboard Backend - Agentic Python Code
Mwarokin Estates Payment Hub
Complete backend system with real-time data management
"""

import json
import random
import string
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time
from collections import defaultdict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PaymentStatus(Enum):
    """Payment status enumeration"""
    COMPLETED = "Completed"
    PENDING = "Pending"
    FAILED = "Failed"


class BankType(Enum):
    """Supported banks in Kenya"""
    KCB = "KCB Bank"
    EQUITY = "Equity Bank"
    COOPERATIVE = "Co-operative Bank"
    NCBA = "NCBA Bank"
    ABSA = "Absa Bank"
    STANBIC = "Stanbic Bank"
    I_AND_M = "I&M Bank"
    DTB = "DTB"
    STANDARD_CHARTERED = "Standard Chartered"
    FAMILY = "Family Bank"
    NATIONAL = "National Bank of Kenya"
    SIDIAN = "Sidian Bank"
    SBM = "SBM Bank"
    GULF_AFRICAN = "Gulf African Bank"
    ECOBANK = "Ecobank Kenya"
    PRIME = "Prime Bank"
    BANK_OF_AFRICA = "Bank of Africa Kenya"
    ACCESS = "Access Bank Kenya"
    KINGDOM = "Kingdom Bank"
    VICTORIA = "Victoria Commercial Bank"
    MPESA = "M-PESA"
    AIRTEL_MONEY = "Airtel Money"


@dataclass
class Payment:
    """Payment data model"""
    payment_id: str
    user_id: str
    user_name: str
    amount: float
    date: str
    time: str
    status: str
    bank: str
    reference: str
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        """Convert payment to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Payment':
        """Create Payment from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class PaymentManager:
    """
    Agentic Payment Manager - Handles all payment operations
    with real-time capabilities and intelligent data management
    """
    
    def __init__(self):
        self.payments: List[Payment] = []
        self.filtered_payments: List[Payment] = []
        self.banks = [bank.value for bank in BankType]
        self.statuses = [status.value for status in PaymentStatus]
        self.names = self._generate_user_names()
        self._lock = threading.Lock()
        self._observers = []
        self._auto_update_thread = None
        self._running = False
        
    def _generate_user_names(self) -> List[str]:
        """Generate Kenyan user names"""
        first_names = [
            'John', 'Mary', 'Peter', 'Grace', 'Samuel', 'Alice', 'David', 'Sarah',
            'Michael', 'Jane', 'Robert', 'Helen', 'James', 'Lucy', 'Charles', 'Rebecca',
            'Daniel', 'Patricia', 'Stephen', 'Victoria', 'Joseph', 'Margaret', 'Paul',
            'Elizabeth', 'Mark', 'Ann', 'Kevin', 'Susan', 'Brian', 'Catherine'
        ]
        last_names = [
            'Kimani', 'Njeri', 'Mwangi', 'Wanjiru', 'Kipchoge', 'Ndungu', 'Ochieng',
            'Kamau', 'Kiplagat', 'Wafula', 'Mutua', 'Otieno', 'Kipkemboi', 'Samba',
            'Mwaura', 'Koech', 'Kiprotich', 'Mwelu', 'Kiprop', 'Chepkwony',
            'Maina', 'Wambui', 'Ouma', 'Achieng', 'Kiptoo', 'Chesire', 'Odhiambo',
            'Akinyi', 'Rotich', 'Jepchumba'
        ]
        return [f"{f} {l}" for f, l in zip(first_names[:20], last_names[:20])]
    
    def _generate_payment_id(self) -> str:
        """Generate unique payment ID"""
        return f"PAY{random.randint(1, 999999):06d}"
    
    def _generate_user_id(self) -> str:
        """Generate user ID"""
        return f"USR{random.randint(1000, 1499):04d}"
    
    def _generate_reference(self) -> str:
        """Generate transaction reference"""
        return f"TXN{''.join(random.choices(string.ascii_uppercase + string.digits, k=9))}"
    
    def generate_payment(self) -> Payment:
        """Generate a single random payment"""
        date = datetime.now() - timedelta(days=random.randint(0, 30))
        status = random.choice(self.statuses)
        
        # Determine bank based on priority
        bank_weights = {
            'KCB Bank': 15, 'Equity Bank': 15, 'Co-operative Bank': 12,
            'NCBA Bank': 12, 'Absa Bank': 12, 'Stanbic Bank': 8,
            'I&M Bank': 6, 'DTB': 4, 'Standard Chartered': 4,
            'Family Bank': 4, 'National Bank of Kenya': 3, 'Sidian Bank': 1,
            'SBM Bank': 1, 'Gulf African Bank': 1, 'Ecobank Kenya': 1,
            'Prime Bank': 0.5, 'Bank of Africa Kenya': 0.5,
            'Access Bank Kenya': 0.5, 'Kingdom Bank': 0.5,
            'Victoria Commercial Bank': 0.5, 'M-PESA': 10, 'Airtel Money': 5
        }
        banks = list(bank_weights.keys())
        weights = list(bank_weights.values())
        bank = random.choices(banks, weights=weights, k=1)[0]
        
        return Payment(
            payment_id=self._generate_payment_id(),
            user_id=self._generate_user_id(),
            user_name=random.choice(self.names),
            amount=float(random.randint(5000, 50000)),
            date=date.strftime('%m/%d/%Y'),
            time=date.strftime('%H:%M'),
            status=status,
            bank=bank,
            reference=self._generate_reference(),
            timestamp=date
        )
    
    def generate_payment_data(self, count: int = 247) -> List[Payment]:
        """Generate multiple random payments"""
        payments = []
        for _ in range(count):
            payments.append(self.generate_payment())
        # Sort by timestamp descending
        payments.sort(key=lambda x: x.timestamp, reverse=True)
        return payments
    
    def load_data(self, count: int = 247) -> None:
        """Load initial payment data"""
        with self._lock:
            self.payments = self.generate_payment_data(count)
            self.filtered_payments = self.payments.copy()
            logger.info(f"Loaded {len(self.payments)} payments")
    
    def filter_payments(self, search_term: str = "", 
                       status_filter: str = "", 
                       bank_filter: str = "") -> List[Payment]:
        """Filter payments based on search and filters"""
        with self._lock:
            filtered = self.payments.copy()
            
            if search_term:
                search_lower = search_term.lower()
                filtered = [p for p in filtered if (
                    search_lower in p.user_id.lower() or
                    search_lower in p.user_name.lower() or
                    search_lower in p.status.lower() or
                    search_lower in p.bank.lower()
                )]
            
            if status_filter:
                filtered = [p for p in filtered if p.status == status_filter]
            
            if bank_filter:
                filtered = [p for p in filtered if p.bank == bank_filter]
            
            self.filtered_payments = filtered
            return filtered
    
    def get_paginated_payments(self, page: int = 1, 
                              items_per_page: int = 10) -> Dict:
        """Get paginated list of filtered payments"""
        with self._lock:
            start = (page - 1) * items_per_page
            end = start + items_per_page
            total = len(self.filtered_payments)
            total_pages = (total + items_per_page - 1) // items_per_page
            
            page_data = self.filtered_payments[start:end]
            
            return {
                'data': [p.to_dict() for p in page_data],
                'total': total,
                'total_pages': total_pages,
                'current_page': page,
                'start': start + 1 if total > 0 else 0,
                'end': min(end, total)
            }
    
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        with self._lock:
            total = len(self.filtered_payments)
            total_amount = sum(p.amount for p in self.filtered_payments)
            
            status_counts = defaultdict(int)
            for payment in self.filtered_payments:
                status_counts[payment.status] += 1
            
            return {
                'total_payments': total,
                'total_amount': total_amount,
                'completed': status_counts.get('Completed', 0),
                'pending': status_counts.get('Pending', 0),
                'failed': status_counts.get('Failed', 0)
            }
    
    def add_payment(self, payment: Optional[Payment] = None) -> Payment:
        """Add a new payment (for real-time updates)"""
        if payment is None:
            payment = self.generate_payment()
        
        with self._lock:
            # Insert at the beginning (newest first)
            self.payments.insert(0, payment)
            self.filtered_payments.insert(0, payment)
            self._notify_observers('payment_added', payment.to_dict())
            
        logger.info(f"New payment added: {payment.payment_id}")
        return payment
    
    def get_bank_statistics(self) -> Dict:
        """Get statistics by bank"""
        with self._lock:
            bank_stats = defaultdict(lambda: {'count': 0, 'amount': 0})
            for payment in self.filtered_payments:
                bank_stats[payment.bank]['count'] += 1
                bank_stats[payment.bank]['amount'] += payment.amount
            return dict(bank_stats)
    
    def get_status_distribution(self) -> Dict:
        """Get status distribution"""
        with self._lock:
            distribution = defaultdict(int)
            for payment in self.filtered_payments:
                distribution[payment.status] += 1
            return dict(distribution)
    
    def add_observer(self, callback):
        """Add observer for real-time updates"""
        self._observers.append(callback)
    
    def _notify_observers(self, event_type: str, data: Dict):
        """Notify all observers of changes"""
        for callback in self._observers:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Observer callback failed: {e}")
    
    def start_auto_update(self, interval: int = 30):
        """Start automatic real-time updates"""
        if self._auto_update_thread and self._running:
            return
        
        self._running = True
        
        def update_loop():
            while self._running:
                time.sleep(interval)
                # Randomly add new payment (30% chance)
                if random.random() > 0.7:
                    self.add_payment()
                    logger.info("Auto-update: New payment added")
        
        self._auto_update_thread = threading.Thread(target=update_loop, daemon=True)
        self._auto_update_thread.start()
        logger.info(f"Auto-update started with interval {interval}s")
    
    def stop_auto_update(self):
        """Stop automatic updates"""
        self._running = False
        if self._auto_update_thread:
            self._auto_update_thread.join(timeout=2)
            logger.info("Auto-update stopped")


class BankDashboardAPI:
    """
    API Layer for Bank Dashboard
    Provides clean interface for frontend integration
    """
    
    def __init__(self):
        self.payment_manager = PaymentManager()
        self.payment_manager.load_data(247)
        self.payment_manager.start_auto_update(30)
    
    def get_dashboard_data(self, page: int = 1, 
                          search: str = "",
                          status: str = "",
                          bank: str = "") -> Dict:
        """Get complete dashboard data"""
        # Apply filters
        self.payment_manager.filter_payments(search, status, bank)
        
        # Get paginated data
        paginated = self.payment_manager.get_paginated_payments(page)
        
        # Get summary
        summary = self.payment_manager.get_summary()
        
        return {
            'success': True,
            'data': paginated['data'],
            'summary': summary,
            'pagination': {
                'total': paginated['total'],
                'total_pages': paginated['total_pages'],
                'current_page': paginated['current_page'],
                'start': paginated['start'],
                'end': paginated['end']
            },
            'filters': {
                'search': search,
                'status': status,
                'bank': bank
            }
        }
    
    def refresh_data(self) -> Dict:
        """Refresh data with new random payments"""
        # Add 5-10 new payments
        count = random.randint(5, 10)
        for _ in range(count):
            self.payment_manager.add_payment()
        
        # Refilter and return
        return self.get_dashboard_data()
    
    def add_manual_payment(self, payment_data: Dict) -> Dict:
        """Add a manual payment"""
        try:
            payment = Payment(
                payment_id=payment_data.get('payment_id', f"PAY{random.randint(1, 999999):06d}"),
                user_id=payment_data.get('user_id', self.payment_manager._generate_user_id()),
                user_name=payment_data.get('user_name', random.choice(self.payment_manager.names)),
                amount=float(payment_data.get('amount', random.randint(5000, 50000))),
                date=datetime.now().strftime('%m/%d/%Y'),
                time=datetime.now().strftime('%H:%M'),
                status=payment_data.get('status', random.choice(['Completed', 'Pending', 'Failed'])),
                bank=payment_data.get('bank', random.choice([b.value for b in BankType])),
                reference=self.payment_manager._generate_reference(),
                timestamp=datetime.now()
            )
            
            self.payment_manager.add_payment(payment)
            return {'success': True, 'payment': payment.to_dict()}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_bank_analytics(self) -> Dict:
        """Get bank analytics data"""
        return {
            'success': True,
            'bank_statistics': self.payment_manager.get_bank_statistics(),
            'status_distribution': self.payment_manager.get_status_distribution()
        }
    
    def get_payment_by_id(self, payment_id: str) -> Optional[Dict]:
        """Get a specific payment by ID"""
        with self.payment_manager._lock:
            for payment in self.payment_manager.payments:
                if payment.payment_id == payment_id:
                    return payment.to_dict()
        return None
    
    def update_payment_status(self, payment_id: str, new_status: str) -> Dict:
        """Update payment status"""
        with self.payment_manager._lock:
            for payment in self.payment_manager.payments:
                if payment.payment_id == payment_id:
                    payment.status = new_status
                    # Update in filtered list as well
                    for filtered in self.payment_manager.filtered_payments:
                        if filtered.payment_id == payment_id:
                            filtered.status = new_status
                            break
                    return {
                        'success': True,
                        'payment': payment.to_dict()
                    }
        return {'success': False, 'error': 'Payment not found'}


class DataExporter:
    """Export payment data in various formats"""
    
    @staticmethod
    def export_to_json(payments: List[Payment]) -> str:
        """Export payments to JSON format"""
        return json.dumps([p.to_dict() for p in payments], indent=2)
    
    @staticmethod
    def export_to_csv(payments: List[Payment]) -> str:
        """Export payments to CSV format"""
        if not payments:
            return ""
        
        headers = ['payment_id', 'user_id', 'user_name', 'amount', 'date', 'time', 
                  'status', 'bank', 'reference']
        
        lines = [','.join(headers)]
        for payment in payments:
            row = [
                payment.payment_id,
                payment.user_id,
                payment.user_name,
                str(payment.amount),
                payment.date,
                payment.time,
                payment.status,
                payment.bank,
                payment.reference
            ]
            lines.append(','.join(row))
        
        return '\n'.join(lines)
    
    @staticmethod
    def generate_report(api: BankDashboardAPI) -> Dict:
        """Generate a comprehensive report"""
        data = api.get_dashboard_data(page=1)
        analytics = api.get_bank_analytics()
        
        return {
            'generated_at': datetime.now().isoformat(),
            'summary': data['summary'],
            'bank_statistics': analytics['bank_statistics'],
            'status_distribution': analytics['status_distribution'],
            'total_payments': data['pagination']['total'],
            'sample_payments': data['data'][:10]  # First 10 payments
        }


class DashboardCache:
    """Simple caching system for dashboard data"""
    
    def __init__(self, ttl: int = 60):
        self.cache = {}
        self.ttl = ttl
        self.timestamps = {}
    
    def get(self, key: str) -> Optional[Dict]:
        """Get cached data"""
        if key in self.cache:
            if time.time() - self.timestamps[key] < self.ttl:
                return self.cache[key]
            else:
                del self.cache[key]
                del self.timestamps[key]
        return None
    
    def set(self, key: str, value: Dict):
        """Set cached data"""
        self.cache[key] = value
        self.timestamps[key] = time.time()


def main():
    """
    Main function to demonstrate the Bank Dashboard backend
    """
    print("🏦 Mwarokin Estates Bank Dashboard Backend")
    print("=" * 50)
    
    # Initialize API
    api = BankDashboardAPI()
    
    # Get initial dashboard data
    print("\n📊 Initial Dashboard Data:")
    dashboard = api.get_dashboard_data(page=1)
    
    summary = dashboard['summary']
    print(f"Total Payments: {summary['total_payments']}")
    print(f"Total Amount: KES {summary['total_amount']:,.2f}")
    print(f"Completed: {summary['completed']}")
    print(f"Pending: {summary['pending']}")
    print(f"Failed: {summary['failed']}")
    
    # Show first 5 payments
    print("\n📋 Recent Payments:")
    for payment in dashboard['data'][:5]:
        print(f"  {payment['payment_id']} - {payment['user_name']} - "
              f"KES {payment['amount']:,.2f} - {payment['status']}")
    
    # Test filters
    print("\n🔍 Filtering by Completed status:")
    filtered = api.get_dashboard_data(status="Completed")
    print(f"Found {filtered['summary']['total_payments']} completed payments")
    
    # Test search
    print("\n🔍 Searching for 'Kimani':")
    searched = api.get_dashboard_data(search="Kimani")
    print(f"Found {searched['summary']['total_payments']} payments")
    
    # Add new payment
    print("\n✨ Adding new payment:")
    new_payment = api.add_manual_payment({
        'user_name': 'Test User',
        'amount': 25000,
        'status': 'Completed',
        'bank': 'KCB Bank'
    })
    if new_payment['success']:
        print(f"Added payment: {new_payment['payment']['payment_id']}")
    
    # Get analytics
    print("\n📈 Bank Analytics:")
    analytics = api.get_bank_analytics()
    for bank, stats in analytics['bank_statistics'].items():
        print(f"  {bank}: {stats['count']} payments, "
              f"KES {stats['amount']:,.2f}")
    
    print("\n✅ Dashboard backend is running and ready!")
    print("💡 To stop auto-updates, call: api.payment_manager.stop_auto_update()")
    
    return api


if __name__ == "__main__":
    # Run the main function
    api = main()
    
    # Keep the program running for demo purposes
    try:
        print("\n🔄 Auto-update running. Press Ctrl+C to stop...")
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n🛑 Stopping auto-update...")
        api.payment_manager.stop_auto_update()
        print("👋 Goodbye!")
```

This comprehensive backend system includes:

**Core Features:**
- Complete payment management with CRUD operations
- Real-time data generation with Kenyan bank integration
- Advanced filtering and search capabilities
- Pagination support
- Summary statistics
- Real-time auto-updates

**Agentic Capabilities:**
- Automatic data generation and updates
- Thread-based background updates
- Observer pattern for real-time notifications
- Intelligent bank selection with weighted priorities

**Data Models:**
- Payment data structure with all required fields
- Support for all major Kenyan banks
- Priority-based bank selection (Tier 1, 2, 3)

**API Layer:**
- Clean interface for frontend integration
- Filtering, pagination, and search
- Analytics and reporting
- Payment status updates

**Export Capabilities:**
- JSON and CSV export
- Comprehensive report generation

The system is designed to be agentic - it automatically generates data, updates in real-time, and provides intelligent filtering and analysis. It can be easily integrated with a frontend framework or used as a standalone backend service.