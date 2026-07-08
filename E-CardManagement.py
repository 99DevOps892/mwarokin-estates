```python
import datetime
from forex_python.converter import CurrencyRates

class EnhancedMultiFunctionalCard:
    def __init__(self, card_number, user_id, tenant_id=None):
        self.card_number = card_number
        self.user_id = user_id
        self.tenant_id = tenant_id  # For multi-tenant support in real estate platform
        self.balance = {
            'credit': 5000.00,  # Credit limit
            'debit': 2000.00,   # Savings or checking
            'prepaid': 100.00,  # Stored value
            'rewards': 1500     # Reward points (e.g., 1 point = $0.01)
        }
        self.currency = 'USD'
        self.currency_converter = CurrencyRates()
        self.active_mode = 'debit'  # Default mode
        self.transaction_log = []   # Log for audit trails and compliance
        self._log_action(f"Card initialized for user {user_id} under tenant {tenant_id}")

    def _log_action(self, message):
        timestamp = datetime.datetime.now().isoformat()
        log_entry = {'timestamp': timestamp, 'message': message}
        self.transaction_log.append(log_entry)
        # In real system, this could be persisted to a database with tenant isolation

    def switch_mode(self, mode):
        if mode in self.balance:
            old_mode = self.active_mode
            self.active_mode = mode
            self._log_action(f"Switched from {old_mode.capitalize()} to {mode.capitalize()} mode")
            return f"Card switched to {mode.capitalize()} mode."
        return "Invalid mode selected."

    def check_balance(self, mode=None):
        mode = mode or self.active_mode
        if mode in self.balance:
            balance_value = self.balance[mode]
            if mode == 'rewards':
                return f"Available balance in {mode.capitalize()} mode: {balance_value} points (equivalent to ${balance_value / 100:.2f} {self.currency})"
            return f"Available balance in {mode.capitalize()} mode: ${balance_value:,.2f} {self.currency}"
        return "Invalid mode."

    def add_funds(self, amount, mode='debit', currency='USD'):
        if mode not in ['debit', 'prepaid']:
            return "Can only add funds to Debit or Prepaid modes."
        if currency != self.currency:
            amount = self.currency_converter.convert(currency, self.currency, amount)
        self.balance[mode] += amount
        self._log_action(f"Added ${amount:.2f} {self.currency} to {mode.capitalize()} mode")
        return f"Added ${amount:.2f} {self.currency} to {mode.capitalize()}. New balance: ${self.balance[mode]:,.2f} {self.currency}"

    def pay(self, amount, currency='USD', description="General payment"):
        if currency != self.currency:
            try:
                amount = self.currency_converter.convert(currency, self.currency, amount)
            except Exception as e:
                return f"Currency conversion failed: {str(e)}"
        
        if self.active_mode == 'credit' and amount <= self.balance['credit']:
            self.balance['credit'] -= amount
            self._earn_rewards(amount)  # Earn rewards on credit payments
            self._log_action(f"Paid ${amount:.2f} {self.currency} using Credit for '{description}'. Remaining credit: ${self.balance['credit']:.2f}")
            return f"Paid ${amount:.2f} {self.currency} using Credit for '{description}'. Remaining credit: ${self.balance['credit']:.2f} {self.currency}"

        elif self.active_mode == 'debit' and amount <= self.balance['debit']:
            self.balance['debit'] -= amount
            self._log_action(f"Paid ${amount:.2f} {self.currency} using Debit for '{description}'. Remaining debit: ${self.balance['debit']:.2f}")
            return f"Paid ${amount:.2f} {self.currency} using Debit for '{description}'. Remaining debit: ${self.balance['debit']:.2f} {self.currency}"

        elif self.active_mode == 'prepaid' and amount <= self.balance['prepaid']:
            self.balance['prepaid'] -= amount
            self._log_action(f"Paid ${amount:.2f} {self.currency} using Prepaid for '{description}'. Remaining prepaid: ${self.balance['prepaid']:.2f}")
            return f"Paid ${amount:.2f} {self.currency} using Prepaid for '{description}'. Remaining prepaid: ${self.balance['prepaid']:.2f} {self.currency}"

        elif self.active_mode == 'rewards' and amount <= (self.balance['rewards'] / 100):
            points_used = amount * 100
            self.balance['rewards'] -= points_used
            self._log_action(f"Paid ${amount:.2f} {self.currency} using Rewards ({points_used} points) for '{description}'. Remaining rewards: {self.balance['rewards']} points")
            return f"Paid ${amount:.2f} {self.currency} using Rewards ({points_used} points) for '{description}'. Remaining rewards: {self.balance['rewards']} points"

        self._log_action(f"Payment failed for '${amount:.2f} {self.currency}' in {self.active_mode.capitalize()} mode: Insufficient balance")
        return f"Payment failed. Insufficient balance in {self.active_mode.capitalize()} mode."

    def _earn_rewards(self, amount):
        # Example: Earn 1% rewards on credit payments (100 points per $1)
        rewards_earned = amount * 1  # 1 point per $0.01, so *100 for per dollar, but adjusted to 1% as *1 for simplicity
        self.balance['rewards'] += rewards_earned
        self._log_action(f"Earned {rewards_earned} reward points on payment of ${amount:.2f}")

    def schedule_recurring_payment(self, amount, interval_days, start_date, end_date=None, currency='USD', description="Recurring payment"):
        # Simple simulation; in real agentic system, this would integrate with LeaseAgent for scheduling
        current_date = start_date
        while (end_date is None or current_date <= end_date):
            result = self.pay(amount, currency, description=f"{description} on {current_date.date()}")
            print(result)  # For demo; in prod, yield or stream results
            current_date += datetime.timedelta(days=interval_days)
        self._log_action(f"Scheduled recurring payments completed for '{description}'")

    def view_transaction_log(self):
        return "\n".join([f"{entry['timestamp']}: {entry['message']}" for entry in self.transaction_log])

    def set_currency(self, new_currency):
        # Convert all balances to new currency (simplified, assumes conversion for monetary balances)
        for mode in ['credit', 'debit', 'prepaid']:
            self.balance[mode] = self.currency_converter.convert(self.currency, new_currency, self.balance[mode])
        # Rewards remain in points, no conversion
        old_currency = self.currency
        self.currency = new_currency
        self._log_action(f"Currency changed from {old_currency} to {new_currency}")
        return f"Currency set to {new_currency}. Balances converted accordingly."

# Example usage for real estate context (e.g., lease payment)
card = EnhancedMultiFunctionalCard("1234-5678-9101-1121", user_id=42, tenant_id="real_estate_tenant_001")

# Switch to Credit Mode
print(card.switch_mode('credit'))
print(card.check_balance())

# Make a payment (e.g., down payment)
print(card.pay(100.00, description="Down payment for listing_id:123"))

# Add funds to Prepaid
print(card.add_funds(50.00, mode='prepaid'))

# Switch to Rewards Mode
print(card.switch_mode('rewards'))
print(card.pay(5.00, description="Reward redemption for referral"))

# Set to EUR
print(card.set_currency('EUR'))

# Schedule monthly rent (simplified, assuming dates)
start = datetime.datetime(2025, 9, 10)
card.schedule_recurring_payment(500.00, 30, start, description="Monthly rent for applicant_id:456")

# View log for audit
print("\nTransaction Log:")
print(card.view_transaction_log())
```