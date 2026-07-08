import uuid
import datetime
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json

# Configure logging for audit trails
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='mwarokin_billing_audit.log'
)

@dataclass
class BillingTier:
    min_homes: int
    max_homes: Optional[int]
    base_fee: Decimal
    max_fee: Decimal

@dataclass
class BillingResult:
    tenant_id: str
    total_fee: Decimal
    breakdown: Dict[str, Decimal]
    explanation: str
    audit_id: str
    timestamp: datetime.datetime

class BillingAgent:
    def __init__(self):
        # Define billing tiers based on provided structure
        self.tiers = [
            BillingTier(0, 10, Decimal('7000'), Decimal('15000')),
            BillingTier(11, 30, Decimal('15000'), Decimal('30000')),
            BillingTier(31, 100, Decimal('30000'), Decimal('60000')),
            BillingTier(101, 500, Decimal('60000'), Decimal('150000')),
            BillingTier(501, 1000, Decimal('150000'), Decimal('200000')),
        ]
        self.multi_estate_fee = Decimal('1000000')
        self.multi_estate_periods = [3, 6]  # 3 or 6 months
        self.leasing_fee_rate = Decimal('0.05')  # 5% of monthly rent
        self.white_label_fee = Decimal('10000')  # Flat fee for white-labeling
        self.transaction_fee_rate = Decimal('0.015')  # 1.5% transaction fee

    def calculate_property_management_fee(self, num_homes: int) -> Tuple[Decimal, str]:
        """Calculate property management fee based on number of homes."""
        for tier in self.tiers:
            if tier.max_homes is None or (num_homes >= tier.min_homes and num_homes <= tier.max_homes):
                # Linear interpolation within tier
                if tier.max_homes and tier.max_homes > tier.min_homes:
                    range_size = tier.max_homes - tier.min_homes
                    fee_range = tier.max_fee - tier.base_fee
                    fee = tier.base_fee + (fee_range * (num_homes - tier.min_homes) / range_size)
                else:
                    fee = tier.base_fee
                explanation = (
                    f"Property Management Fee: {num_homes} homes in tier "
                    f"({tier.min_homes}-{tier.max_homes or '∞'}). "
                    f"Base fee: Ksh{tier.base_fee}, Max fee: Ksh{tier.max_fee}. "
                    f"Calculated: Ksh{fee:.2f}"
                )
                return fee, explanation
        return Decimal('0'), "No applicable tier found"

    def calculate_multi_estate_fee(self, months: int) -> Tuple[Decimal, str]:
        """Calculate multi-estate fee for 3 or 6 months."""
        if months not in self.multi_estate_periods:
            return Decimal('0'), f"Invalid period: {months}. Must be 3 or 6 months."
        fee = self.multi_estate_fee
        explanation = f"Multi-Estate Fee: Ksh{fee:.2f} for {months}-month plan."
        return fee, explanation

    def calculate_leasing_fee(self, monthly_rent: Decimal) -> Tuple[Decimal, str]:
        """Calculate leasing fee as a percentage of monthly rent."""
        fee = monthly_rent * self.leasing_fee_rate
        explanation = (
            f"Leasing Fee: {self.leasing_fee_rate*100}% of monthly rent (Ksh{monthly_rent:.2f}). "
            f"Calculated: Ksh{fee:.2f}"
        )
        return fee, explanation

    def calculate_transaction_fee(self, transaction_amount: Decimal) -> Tuple[Decimal, str]:
        """Calculate transaction fee for a sale or lease."""
        fee = transaction_amount * self.transaction_fee_rate
        explanation = (
            f"Transaction Fee: {self.transaction_fee_rate*100}% of transaction amount "
            f"(Ksh{transaction_amount:.2f}). Calculated: Ksh{fee:.2f}"
        )
        return fee, explanation

    def calculate_roi(self, revenue: Decimal, expenses: Decimal) -> Tuple[Decimal, str]:
        """Calculate ROI for billing decisions."""
        if expenses == 0:
            return Decimal('0'), "ROI: Cannot calculate, expenses are zero."
        roi = ((revenue - expenses) / expenses) * 100
        explanation = f"ROI: {(revenue - expenses):.2f} / {expenses:.2f} * 100 = {roi:.2f}%"
        return roi, explanation

    def generate_billing(
        self,
        tenant_id: str,
        num_homes: int,
        monthly_rent: Decimal,
        transaction_amount: Decimal,
        is_multi_estate: bool = False,
        multi_estate_months: int = 0,
        use_white_label: bool = False
    ) -> BillingResult:
        """Agentic billing calculation with RBAC and audit logging."""
        audit_id = str(uuid.uuid4())
        breakdown = {}
        explanations = []
        total_fee = Decimal('0')

        # RBAC check simulation (tenant_id validation)
        if not tenant_id or not isinstance(tenant_id, str):
            logging.error(f"Invalid tenant_id: {tenant_id}")
            raise ValueError("Valid tenant_id required")

        # Property Management Fee
        if is_multi_estate:
            fee, explanation = self.calculate_multi_estate_fee(multi_estate_months)
            breakdown['multi_estate_fee'] = fee
            explanations.append(explanation)
        else:
            fee, explanation = self.calculate_property_management_fee(num_homes)
            breakdown['property_management_fee'] = fee
            explanations.append(explanation)
        total_fee += fee

        # Leasing Fee
        if monthly_rent > 0:
            fee, explanation = self.calculate_leasing_fee(monthly_rent)
            breakdown['leasing_fee'] = fee
            explanations.append(explanation)
            total_fee += fee

        # Transaction Fee
        if transaction_amount > 0:
            fee, explanation = self.calculate_transaction_fee(transaction_amount)
            breakdown['transaction_fee'] = fee
            explanations.append(explanation)
            total_fee += fee

        # White-Label Fee
        if use_white_label:
            breakdown['white_label_fee'] = self.white_label_fee
            explanations.append(f"White-Label Fee: Ksh{self.white_label_fee:.2f}")
            total_fee += self.white_label_fee

        # ROI Calculation (example: revenue from rent and transaction)
        revenue = monthly_rent + transaction_amount
        roi, roi_explanation = self.calculate_roi(revenue, total_fee)
        breakdown['roi_percent'] = roi
        explanations.append(roi_explanation)

        # Log audit trail (redact sensitive data)
        audit_log = {
            'audit_id': audit_id,
            'tenant_id': hashlib.sha256(tenant_id.encode()).hexdigest(),  # Redact PII
            'timestamp': datetime.datetime.now().isoformat(),
            'num_homes': num_homes,
            'monthly_rent': float(monthly_rent),
            'transaction_amount': float(transaction_amount),
            'is_multi_estate': is_multi_estate,
            'multi_estate_months': multi_estate_months,
            'use_white_label': use_white_label,
            'total_fee': float(total_fee),
            'breakdown': {k: float(v) for k, v in breakdown.items()}
        }
        logging.info(json.dumps(audit_log))

        # Explanation for human audit
        explanation = "\n".join(explanations)

        return BillingResult(
            tenant_id=tenant_id,
            total_fee=total_fee,
            breakdown=breakdown,
            explanation=explanation,
            audit_id=audit_id,
            timestamp=datetime.datetime.now()
        )

    def stream_billing_progress(self, tenant_id: str, num_homes: int) -> List[str]:
        """Stream partial billing results for long-running calculations."""
        results = []
        fee, explanation = self.calculate_property_management_fee(num_homes)
        results.append(f"Progress: Calculated property management fee for tenant {tenant_id}: {explanation}")
        # Simulate additional steps
        results.append(f"Progress: Checking leasing and transaction fees for tenant {tenant_id}...")
        return results

# Example usage
if __name__ == "__main__":
    agent = BillingAgent()
    result = agent.generate_billing(
        tenant_id="tenant_123",
        num_homes=50,
        monthly_rent=Decimal('50000'),
        transaction_amount=Decimal('1000000'),
        is_multi_estate=False,
        multi_estate_months=0,
        use_white_label=True
    )
    print(f"Total Fee: Ksh{result.total_fee:.2f}")
    print("Breakdown:", result.breakdown)
    print("Explanation:\n", result.explanation)
    print("Audit ID:", result.audit_id)

    # Stream example
    for progress in agent.stream_billing_progress("tenant_123", 50):
        print(progress)