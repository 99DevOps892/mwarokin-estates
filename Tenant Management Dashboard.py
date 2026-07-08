```python
# Real Estate Management System - Tenant Dashboard Backend

from datetime import datetime, timedelta
import json
import csv
from typing import List, Dict, Optional

class Transaction:
    def __init__(self, date: str, description: str, amount: float, transaction_type: str, status: str):
        self.date = date
        self.description = description
        self.amount = amount
        self.type = transaction_type
        self.status = status

class ServiceRequest:
    def __init__(self, request_id: int, service_type: str, description: str, priority: str, status: str = "open"):
        self.request_id = request_id
        self.service_type = service_type
        self.description = description
        self.priority = priority
        self.status = status
        self.date_created = datetime.now().strftime("%Y-%m-%d")
        self.date_resolved = None

class NotificationPreferences:
    def __init__(self, email: bool = True, sms: bool = True, whatsapp: bool = False, voice: bool = False):
        self.email = email
        self.sms = sms
        self.whatsapp = whatsapp
        self.voice = voice

class Tenant:
    def __init__(self, tenant_id: int, name: str, email: str, phone: str):
        self.tenant_id = tenant_id
        self.name = name
        self.email = email
        self.phone = phone
        self.balance = 0.0
        self.balance_status = "current"
        self.transactions = []
        self.service_requests = []
        self.notification_prefs = NotificationPreferences()
        self.request_counter = 1

    def update_balance(self, amount: float, description: str, transaction_type: str):
        """Update tenant balance and add transaction"""
        transaction = Transaction(
            date=datetime.now().strftime("%Y-%m-%d"),
            description=description,
            amount=amount,
            transaction_type=transaction_type,
            status="completed"
        )
        self.transactions.append(transaction)
        
        if transaction_type == "charge":
            self.balance += amount
        elif transaction_type == "payment":
            self.balance -= amount
        
        self._update_balance_status()

    def _update_balance_status(self):
        """Update balance status based on current balance"""
        if self.balance == 0:
            self.balance_status = "current"
        elif self.balance > 0:
            self.balance_status = "overdue"
        else:
            self.balance_status = "credit"

    def generate_statement(self, days: int = 30) -> List[Dict]:
        """Generate mini statement for specified period"""
        cutoff_date = datetime.now() - timedelta(days=days)
        statement = []
        
        for transaction in self.transactions:
            transaction_date = datetime.strptime(transaction.date, "%Y-%m-%d")
            if transaction_date >= cutoff_date:
                statement.append({
                    'date': transaction.date,
                    'description': transaction.description,
                    'amount': transaction.amount,
                    'type': transaction.type,
                    'status': transaction.status
                })
        
        return statement

    def submit_service_request(self, service_type: str, description: str, priority: str) -> int:
        """Submit a new service request"""
        request = ServiceRequest(
            request_id=self.request_counter,
            service_type=service_type,
            description=description,
            priority=priority
        )
        self.service_requests.append(request)
        self.request_counter += 1
        return request.request_id

    def update_notification_preferences(self, email: bool, sms: bool, whatsapp: bool, voice: bool):
        """Update notification preferences"""
        self.notification_prefs = NotificationPreferences(email, sms, whatsapp, voice)

    def get_balance_details(self) -> Dict:
        """Get detailed balance information"""
        return {
            'current_balance': self.balance,
            'status': self.balance_status,
            'last_updated': datetime.now().strftime("%Y-%m-%d")
        }

    def export_statement_csv(self, days: int = 30) -> str:
        """Export statement as CSV format"""
        statement = self.generate_statement(days)
        csv_output = "Date,Description,Amount,Type,Status\n"
        
        for transaction in statement:
            csv_output += f"{transaction['date']},{transaction['description']},{transaction['amount']},{transaction['type']},{transaction['status']}\n"
        
        return csv_output

    def export_statement_json(self, days: int = 30) -> str:
        """Export statement as JSON format"""
        statement = self.generate_statement(days)
        return json.dumps(statement, indent=2)

class TenantManager:
    def __init__(self):
        self.tenants = {}
        self.tenant_counter = 1

    def register_tenant(self, name: str, email: str, phone: str) -> int:
        """Register a new tenant"""
        tenant_id = self.tenant_counter
        new_tenant = Tenant(tenant_id, name, email, phone)
        self.tenants[tenant_id] = new_tenant
        self.tenant_counter += 1
        return tenant_id

    def get_tenant(self, tenant_id: int) -> Optional[Tenant]:
        """Get tenant by ID"""
        return self.tenants.get(tenant_id)

    def charge_rent(self, tenant_id: int, amount: float, month: str):
        """Charge rent to tenant"""
        tenant = self.get_tenant(tenant_id)
        if tenant:
            tenant.update_balance(amount, f"{month} Rent", "charge")

    def record_payment(self, tenant_id: int, amount: float, payment_method: str):
        """Record payment from tenant"""
        tenant = self.get_tenant(tenant_id)
        if tenant:
            tenant.update_balance(amount, f"Payment - {payment_method}", "payment")

class ServiceRequestManager:
    def __init__(self, tenant_manager: TenantManager):
        self.tenant_manager = tenant_manager

    def submit_request(self, tenant_id: int, service_type: str, description: str, priority: str) -> int:
        """Submit service request for tenant"""
        tenant = self.tenant_manager.get_tenant(tenant_id)
        if tenant:
            return tenant.submit_service_request(service_type, description, priority)
        return -1

    def get_open_requests(self, tenant_id: int) -> List[ServiceRequest]:
        """Get all open service requests for tenant"""
        tenant = self.tenant_manager.get_tenant(tenant_id)
        if tenant:
            return [req for req in tenant.service_requests if req.status == "open"]
        return []

    def resolve_request(self, tenant_id: int, request_id: int, resolution_notes: str):
        """Resolve a service request"""
        tenant = self.tenant_manager.get_tenant(tenant_id)
        if tenant:
            for request in tenant.service_requests:
                if request.request_id == request_id:
                    request.status = "resolved"
                    request.date_resolved = datetime.now().strftime("%Y-%m-%d")
                    request.resolution_notes = resolution_notes
                    return True
        return False

class NotificationManager:
    def __init__(self, tenant_manager: TenantManager):
        self.tenant_manager = tenant_manager

    def send_balance_reminder(self, tenant_id: int):
        """Send balance reminder based on tenant preferences"""
        tenant = self.tenant_manager.get_tenant(tenant_id)
        if not tenant:
            return

        message = f"Balance Reminder: Your current balance is ${tenant.balance:.2f} ({tenant.balance_status})"
        
        notifications_sent = []
        prefs = tenant.notification_prefs
        
        if prefs.email:
            notifications_sent.append(f"Email sent to {tenant.email}: {message}")
        if prefs.sms:
            notifications_sent.append(f"SMS sent to {tenant.phone}: {message}")
        if prefs.whatsapp:
            notifications_sent.append(f"WhatsApp message sent: {message}")
        if prefs.voice:
            notifications_sent.append(f"Voice call initiated: {message}")
        
        return notifications_sent

# Example usage and demonstration
def main():
    # Initialize managers
    tenant_manager = TenantManager()
    service_manager = ServiceRequestManager(tenant_manager)
    notification_manager = NotificationManager(tenant_manager)

    # Register a tenant
    tenant_id = tenant_manager.register_tenant(
        "John Doe", 
        "john.doe@email.com", 
        "+1234567890"
    )

    # Simulate rent charges and payments
    tenant_manager.charge_rent(tenant_id, 1500.00, "January 2024")
    tenant_manager.charge_rent(tenant_id, 1500.00, "February 2024")
    tenant_manager.record_payment(tenant_id, 1500.00, "Bank Transfer")

    # Submit service requests
    service_manager.submit_request(
        tenant_id, 
        "maintenance", 
        "Kitchen sink is leaking", 
        "high"
    )
    
    service_manager.submit_request(
        tenant_id,
        "electrical",
        "Bedroom light not working",
        "medium"
    )

    # Update notification preferences
    tenant = tenant_manager.get_tenant(tenant_id)
    tenant.update_notification_preferences(
        email=True,
        sms=True,
        whatsapp=True,
        voice=False
    )

    # Demonstrate functionality
    print("=== TENANT DASHBOARD BACKEND DEMO ===")
    
    # Balance information
    balance_info = tenant.get_balance_details()
    print(f"\nBalance Details:")
    print(f"Current Balance: ${balance_info['current_balance']:.2f}")
    print(f"Status: {balance_info['status']}")
    
    # Generate statement
    statement = tenant.generate_statement(60)
    print(f"\nMini Statement (Last 60 days):")
    print("Date       | Description          | Amount   | Type    | Status")
    print("-" * 60)
    for transaction in statement:
        print(f"{transaction['date']} | {transaction['description']:20} | ${transaction['amount']:7.2f} | {transaction['type']:7} | {transaction['status']}")
    
    # Service requests
    open_requests = service_manager.get_open_requests(tenant_id)
    print(f"\nOpen Service Requests: {len(open_requests)}")
    for request in open_requests:
        print(f"  #{request.request_id}: {request.service_type} - {request.description} ({request.priority} priority)")
    
    # Export statements
    csv_statement = tenant.export_statement_csv(30)
    json_statement = tenant.export_statement_json(30)
    
    print(f"\nCSV Export Sample:")
    print(csv_statement.split('\n')[0])  # Show header only
    
    # Notification test
    notifications = notification_manager.send_balance_reminder(tenant_id)
    print(f"\nNotifications Sent:")
    for notification in notifications:
        print(f"  - {notification}")

if __name__ == "__main__":
    main()
```

This Python real estate management system for tenant dashboard includes:

**Core Classes:**
- `Tenant`: Manages tenant data, balance, transactions, and preferences
- `TenantManager`: Handles tenant registration and financial operations
- `ServiceRequestManager`: Manages maintenance and service requests
- `NotificationManager`: Handles communication preferences and reminders

**Key Features:**
- **Balance Management**: Track rent payments, charges, and current balance status
- **Mini Statement Generation**: Generate transaction history for specified periods
- **Service Request System**: Submit and track maintenance requests with priorities
- **Notification Preferences**: Manage communication channels (email, SMS, WhatsApp, voice)
- **Data Export**: Export statements in CSV and JSON formats

**Functionality:**
- Automated balance status updates (current, overdue, credit)
- Transaction history with filtering by date range
- Service request tracking with status management
- Flexible notification system based on tenant preferences
- Financial reporting and data export capabilities

The system provides a comprehensive backend for a tenant dashboard that can be integrated with a web frontend like the HTML template provided.