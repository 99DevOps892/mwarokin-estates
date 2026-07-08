```python
# Mwarokin Payment Structure Module
# This module implements the payment structure for the Mwarokin Real Estate Agentic OS.
# It includes transaction fees, leasing fees, white-labeling fees, and an ROI calculator.
# All functions respect multi-tenancy via tenant_id, though for simplicity, tenant-specific
# customizations are simulated here (e.g., via feature flags or overrides).
# Currency: KSH (Kenyan Shilling)
# Designed as a financial advisor: Fees are kept low and competitive, inspired by M-Pesa tiers
# but adjusted for real estate context to minimize costs for tenants and landlords.
# Added payment features: Installments, recurring payments, multiple gateways (low-cost options like M-Pesa, bank transfer).
# Metrics based on monthly rent: Fees scale with rent amounts for fairness.
# ROI algorithm: Calculates projected return on investment for Mwarokin based on collected fees vs. operational costs.

import random  # For simulating variability in fee ranges if needed
import math    # For calculations
from typing import Dict, List, Optional

class PaymentAgent:
    """
    PaymentAgent handles all payment-related tasks in Mwarokin.
    Delegates fee calculations, payment processing simulations, and ROI analysis.
    Ensures compliance with safety, privacy, and fairness (e.g., no discriminatory fees).
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        # Simulate tenant-specific configs (e.g., from DB or RAG)
        self.tenant_config = self._get_tenant_config()

    def _get_tenant_config(self) -> Dict:
        # Placeholder for RAG or DB fetch. For demo, hard-coded.
        # In real system, use RAG_Agent to retrieve tenant-specific settings.
        return {
            'currency': 'KSH',
            'transaction_fee_variability': True,  # If True, use random in range; else mid-point
            'leasing_fee_percentage': 0.05,  # 5% of first month's rent (competitive, per research)
            'white_label_plan': 'premium',    # basic: 5000 KSH/mo, premium: 10000 KSH/mo
            'installment_fee_rate': 0.01,     # 1% extra for installments (low cost)
            'operational_cost_per_tx': 2.0,   # Estimated Mwarokin cost per transaction
        }

    def calculate_transaction_fee(self, amount: float) -> float:
        """
        Calculates transaction fee based on tiered structure.
        Interpreted from user input: Ksh3-5 for <5000, Ksh7-10 for <15000, Ksh12-15 for >25000.
        For gaps (15000-25000), interpolated to 10-12.
        To keep low cost: Use mid-point or random in range if variability enabled.
        Inspired by M-Pesa: Tiered fixed fees, but kept smaller for competitiveness.
        :param amount: Transaction amount in KSH (e.g., rent payment)
        :return: Fee in KSH
        """
        if amount <= 0:
            raise ValueError("Amount must be positive.")
        
        config = self.tenant_config
        if config['transaction_fee_variability']:
            # Use random in range for dynamic pricing (e.g., based on market)
            if amount < 5000:
                fee = random.uniform(3, 5)
            elif amount < 15000:
                fee = random.uniform(7, 10)
            elif amount <= 25000:
                fee = random.uniform(10, 12)  # Interpolated for gap
            else:
                fee = random.uniform(12, 15)
        else:
            # Fixed mid-points for determinism
            if amount < 5000:
                fee = 4.0
            elif amount < 15000:
                fee = 8.5
            elif amount <= 25000:
                fee = 11.0
            else:
                fee = 13.5
        
        # Cap fee at 0.5% of amount to ensure not too expensive for large rents
        max_fee = amount * 0.005
        fee = min(fee, max_fee)
        
        # Explanation for auditability
        print(f"Transaction fee for {amount} KSH (tenant {self.tenant_id}): {fee} KSH")
        return round(fee, 2)

    def calculate_leasing_fee(self, monthly_rent: float, lease_months: int = 12) -> float:
        """
        Calculates leasing fee based on monthly rent.
        Recommendation: 5% of first month's rent (low compared to typical 10% management or 1 full month agent fee).
        Scaled by lease duration for longer-term value.
        :param monthly_rent: Monthly rent in KSH
        :param lease_months: Duration of lease
        :return: Total leasing fee in KSH
        """
        if monthly_rent <= 0 or lease_months <= 0:
            raise ValueError("Rent and months must be positive.")
        
        config = self.tenant_config
        base_fee = monthly_rent * config['leasing_fee_percentage']
        # Adjust for lease length: Discount for longer leases (incentivize stability)
        if lease_months > 12:
            base_fee *= 0.9  # 10% discount
        elif lease_months < 6:
            base_fee *= 1.1  # 10% premium for short-term
        
        # Explanation
        print(f"Leasing fee for rent {monthly_rent} KSH over {lease_months} months (tenant {self.tenant_id}): {base_fee} KSH")
        return round(base_fee, 2)

    def calculate_white_label_fee(self, months: int = 1) -> float:
        """
        Calculates white-labeling subscription fee.
        Basic: 5000 KSH/mo, Premium: 10000 KSH/mo (examples from SaaS research: $100-200/mo equivalent).
        Annual discount if >12 months.
        :param months: Billing period
        :return: Total fee in KSH
        """
        config = self.tenant_config
        if config['white_label_plan'] == 'basic':
            monthly_fee = 5000.0
        elif config['white_label_plan'] == 'premium':
            monthly_fee = 10000.0
        else:
            raise ValueError("Invalid white-label plan.")
        
        total_fee = monthly_fee * months
        if months >= 12:
            total_fee *= 0.85  # 15% annual discount
        
        # Explanation
        print(f"White-label fee for {months} months ({config['white_label_plan']} plan, tenant {self.tenant_id}): {total_fee} KSH")
        return round(total_fee, 2)

    def create_installment_plan(self, total_amount: float, num_installments: int, include_fee: bool = True) -> List[float]:
        """
        Added feature: Installment payments for rents or fees.
        Low cost: Optional 1% fee spread across installments.
        :param total_amount: Total to pay (e.g., annual rent)
        :param num_installments: Number of payments (e.g., monthly=12)
        :param include_fee: Whether to add installment fee
        :return: List of installment amounts
        """
        if num_installments <= 1:
            return [total_amount]
        
        config = self.tenant_config
        fee = 0.0
        if include_fee:
            fee = total_amount * config['installment_fee_rate']
        
        total_with_fee = total_amount + fee
        base_installment = total_with_fee / num_installments
        plan = [round(base_installment, 2)] * num_installments
        # Adjust last installment for rounding
        plan[-1] += round(total_with_fee - sum(plan[:-1]), 2)
        
        # Explanation
        print(f"Installment plan for {total_amount} KSH over {num_installments} payments (fee: {fee} KSH, tenant {self.tenant_id}): {plan}")
        return plan

    def simulate_payment(self, amount: float, method: str = 'm-pesa') -> Dict:
        """
        Added feature: Simulate payment with different gateways.
        Low cost options: M-Pesa (tiered), Bank transfer (flat 20 KSH), Credit card (2% but optional).
        :param amount: Amount to pay
        :param method: 'm-pesa', 'bank', 'card'
        :return: Dict with total, fee, net
        """
        tx_fee = self.calculate_transaction_fee(amount)
        gateway_fee = 0.0
        if method == 'm-pesa':
            # Simulate M-Pesa-like additional fee (low)
            gateway_fee = max(10, amount * 0.002)  # 0.2% min 10
        elif method == 'bank':
            gateway_fee = 20.0  # Flat low fee
        elif method == 'card':
            gateway_fee = amount * 0.02  # 2%, higher cost
        else:
            raise ValueError("Invalid payment method.")
        
        total_fee = tx_fee + gateway_fee
        net = amount - total_fee  # Net to landlord/Mwarokin
        return {
            'total_paid': amount,
            'platform_fee': tx_fee,
            'gateway_fee': gateway_fee,
            'net_received': net,
            'explanation': f"Payment via {method} for {amount} KSH (tenant {self.tenant_id})"
        }

    def roi_algorithm(self, projected_transactions: int, avg_tx_amount: float, operational_costs: float) -> float:
        """
        RIO (ROI) Algorithm: Calculates Return on Investment for Mwarokin.
        Based on collected fees vs. costs.
        Formula: ROI = (Total Revenue - Costs) / Costs * 100
        Revenue from transaction + leasing + white-label fees.
        :param projected_transactions: Expected number of tx per period
        :param avg_tx_amount: Average transaction amount
        :param operational_costs: Total ops costs (external input)
        :return: ROI percentage
        """
        # Estimate revenues
        tx_fee_per = self.calculate_transaction_fee(avg_tx_amount)
        total_tx_revenue = tx_fee_per * projected_transactions
        
        # Assume 10% of tx are leases, avg rent = avg_tx_amount
        num_leases = math.ceil(projected_transactions * 0.1)
        lease_fee_per = self.calculate_leasing_fee(avg_tx_amount)
        total_lease_revenue = lease_fee_per * num_leases
        
        # Assume 1 white-label per tenant (monthly)
        white_label_revenue = self.calculate_white_label_fee(months=1)
        
        total_revenue = total_tx_revenue + total_lease_revenue + white_label_revenue
        net_profit = total_revenue - operational_costs
        roi = (net_profit / operational_costs) * 100 if operational_costs > 0 else 0
        
        # Explanation
        print(f"ROI for {projected_transactions} tx at avg {avg_tx_amount} KSH, costs {operational_costs} KSH (tenant {self.tenant_id}): {roi}%")
        return round(roi, 2)

# Example Usage (for real-time functionality)
if __name__ == "__main__":
    agent = PaymentAgent(tenant_id="demo_tenant")
    
    # Transaction fee example
    agent.calculate_transaction_fee(4000)  # <5000
    
    # Leasing fee example
    agent.calculate_leasing_fee(monthly_rent=20000, lease_months=12)
    
    # White-label fee
    agent.calculate_white_label_fee(months=12)
    
    # Installment plan
    agent.create_installment_plan(total_amount=240000, num_installments=12)  # Annual rent
    
    # Simulate payment
    print(agent.simulate_payment(20000, method='m-pesa'))
    
    # ROI calculation
    agent.roi_algorithm(projected_transactions=1000, avg_tx_amount=15000, operational_costs=50000)
```