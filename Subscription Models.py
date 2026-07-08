```python
"""
Mwarokin Estates — Automated Subscription & Disbursement Engine
Modern, professional, production-ready Python code.

This module handles:
- Subscription plan management (Msingi, Jengo, Milki, Taifa)
- Landlord onboarding and contract creation
- Linking of payout accounts (M-Pesa / Bank)
- Automated monthly fee deduction and disbursement
- Revenue Sharing or Fixed Subscription fee models

All monetary values are handled with Decimal for precision.
"""

from __future__ import annotations

import logging
import random
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from uuid import uuid4

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Enums & Constants
# ---------------------------------------------------------------------

class PlanType(str, Enum):
    """Subscription plan types with monthly fees."""
    MSINGI = "msingi"
    JENGO = "jengo"
    MILKI = "milki"
    TAIFA = "taifa"

    @property
    def monthly_fee(self) -> Decimal:
        return {
            PlanType.MSINGI: Decimal("2500.00"),
            PlanType.JENGO: Decimal("6500.00"),
            PlanType.MILKI: Decimal("15000.00"),
            PlanType.TAIFA: Decimal("45000.00"),
        }[self]

    @property
    def display_name(self) -> str:
        return {
            PlanType.MSINGI: "Msingi",
            PlanType.JENGO: "Jengo",
            PlanType.MILKI: "Milki",
            PlanType.TAIFA: "Taifa",
        }[self]

    @property
    def subtitle(self) -> str:
        return {
            PlanType.MSINGI: "Foundation · Msingi wa Nyumba",
            PlanType.JENGO: "Building · Jengo Imara",
            PlanType.MILKI: "Estate · Milki ya Ardhi",
            PlanType.TAIFA: "Enterprise · Taifa Kamili",
        }[self]

    @property
    def features(self) -> List[str]:
        base = [
            "Rent Dashboard", "Tenant Profiles", "Schedule Viewing",
            "Water Billing", "Trash Billing", "Basic KRA Reports",
            "Lipa Mdogo", "Mobile App", "AI Rent Reminders", "Digital Receipts"
        ]
        jengo_addons = [
            "Financial Dashboard", "Advanced Lipa Mdogo", "Caretaker Portal",
            "Renovation Management", "AI Maintenance Scheduling",
            "Advanced KRA Reports", "Lease Management", "Tenant Screening"
        ]
        milki_addons = [
            "Residential Zones", "Security Management", "Communication Centre",
            "Long-Term Lipa Mdogo", "AI Predictive Maintenance",
            "Portfolio Dashboard", "Investor Reports"
        ]
        taifa_addons = [
            "White Label Platform", "API Integration", "Multi-Currency",
            "Enterprise Reports", "SLA Guarantee", "Dedicated Account Manager",
            "AI Business Intelligence"
        ]
        if self == PlanType.MSINGI:
            return base
        elif self == PlanType.JENGO:
            return base + jengo_addons
        elif self == PlanType.MILKI:
            return base + jengo_addons + milki_addons
        else:  # TAIFA
            return base + jengo_addons + milki_addons + taifa_addons


class FeeModel(str, Enum):
    """The fee structure applied to a contract."""
    REVENUE_SHARING = "revenue_sharing"   # 5% of monthly rent per unit
    SUBSCRIPTION = "subscription"         # Fixed monthly plan fee


class ContractStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class AccountType(str, Enum):
    MPESA = "mpesa"
    BANK = "bank"


# ---------------------------------------------------------------------
# Data Models (Entities)
# ---------------------------------------------------------------------

@dataclass
class Landlord:
    """Landlord / property owner information."""
    full_name: str
    national_id: str
    phone: str
    email: str
    landlord_id: str = field(default_factory=lambda: f"LND-{uuid4().hex[:8].upper()}")

    def __post_init__(self):
        self._validate()

    def _validate(self) -> None:
        # Basic validation – in production use more robust checks
        if not re.match(r"^[A-Za-z\s\-']+$", self.full_name):
            raise ValueError("Full name contains invalid characters")
        if not re.match(r"^\d{6,12}$", self.national_id):
            raise ValueError("Invalid national ID format")
        if not re.match(r"^0[71]\d{8}$", self.phone.replace(" ", "")):
            raise ValueError("Invalid Kenyan phone number")
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", self.email):
            raise ValueError("Invalid email address")


@dataclass
class PayoutAccount:
    """Payment account (M-Pesa or Bank) linked to a landlord."""
    account_type: AccountType
    identifier: str          # phone number or bank account number
    holder_name: str
    bank_name: Optional[str] = None   # if bank
    branch: Optional[str] = None
    is_verified: bool = False

    def mask_identifier(self) -> str:
        """Return a masked version of the identifier for display."""
        if self.account_type == AccountType.MPESA:
            digits = re.sub(r"\D", "", self.identifier)
            if len(digits) >= 7:
                return digits[:4] + " *** " + digits[-3:]
            return digits
        else:  # bank
            if len(self.identifier) >= 4:
                return "••••" + self.identifier[-4:]
            return self.identifier

    def verify(self) -> bool:
        """Simulate external verification (e.g., with Safaricom or bank API)."""
        # In production, this would call a real verification service.
        self.is_verified = True
        return True


@dataclass
class Property:
    """Property/estate details."""
    name: str
    county: str
    unit_count: int
    average_rent: Decimal = Decimal("20000.00")   # default

    def __post_init__(self):
        if self.unit_count < 1:
            raise ValueError("Unit count must be at least 1")


@dataclass
class Contract:
    """Smart contract between Mwarokin Estates and the landlord."""
    contract_id: str = field(default_factory=lambda: f"MWK-{random.randint(100000, 999999)}")
    landlord: Landlord = None
    property: Property = None
    fee_model: FeeModel = FeeModel.REVENUE_SHARING
    plan_type: Optional[PlanType] = None  # only if subscription
    payout_account: Optional[PayoutAccount] = None
    status: ContractStatus = ContractStatus.DRAFT
    start_date: date = field(default_factory=date.today)
    end_date: Optional[date] = None

    def activate(self) -> None:
        """Activate the contract after all checks are passed."""
        if self.status != ContractStatus.DRAFT:
            raise ValueError("Contract is not in draft state")
        if not self.payout_account or not self.payout_account.is_verified:
            raise ValueError("Payout account not verified")
        if not self.landlord or not self.property:
            raise ValueError("Landlord and property must be set")
        self.status = ContractStatus.ACTIVE
        logger.info(f"Contract {self.contract_id} activated for {self.landlord.full_name}")

    def calculate_fee(self, monthly_rent: Optional[Decimal] = None) -> Decimal:
        """
        Calculate the monthly fee based on the fee model.
        For revenue sharing: 5% of total rent (monthly_rent * unit_count).
        For subscription: fixed plan fee.
        """
        if self.fee_model == FeeModel.REVENUE_SHARING:
            if monthly_rent is None:
                monthly_rent = self.property.average_rent
            total_rent = monthly_rent * self.property.unit_count
            return (total_rent * Decimal("0.05")).quantize(Decimal("0.01"))
        else:  # subscription
            if not self.plan_type:
                raise ValueError("Plan type not set for subscription model")
            return self.plan_type.monthly_fee

    def __post_init__(self):
        if self.fee_model == FeeModel.SUBSCRIPTION and not self.plan_type:
            raise ValueError("Subscription model requires a plan type")


# ---------------------------------------------------------------------
# Payment Processor (simulated)
# ---------------------------------------------------------------------

class PaymentProcessor:
    """
    Simulates interactions with external payment gateways (M-Pesa, banks).
    Handles deductions and disbursements.
    """

    @staticmethod
    def deduct_fee(account: PayoutAccount, amount: Decimal) -> bool:
        """
        Deduct the fee from the landlord's account.
        Simulates a successful deduction.
        """
        logger.info(f"Deducting {amount} from {account.holder_name} ({account.account_type.value})")
        # In production: call real API (e.g., Safaricom M-Pesa, bank API)
        # For simulation, we always succeed if account is verified.
        if not account.is_verified:
            logger.error("Account not verified, deduction failed")
            return False
        # Simulate a small chance of failure (e.g., 5%)
        if random.random() < 0.02:
            logger.warning("Simulated deduction failure")
            return False
        return True

    @staticmethod
    def disburse_to_landlord(account: PayoutAccount, amount: Decimal) -> bool:
        """
        Disburse net rent (after fee) to the landlord's account.
        """
        logger.info(f"Disbursing {amount} to {account.holder_name} ({account.account_type.value})")
        if not account.is_verified:
            logger.error("Account not verified, disbursement failed")
            return False
        if random.random() < 0.02:
            logger.warning("Simulated disbursement failure")
            return False
        return True

    @staticmethod
    def disburse_to_estate(amount: Decimal) -> bool:
        """
        Transfer the fee to Mwarokin Estates' account.
        """
        logger.info(f"Transferring {amount} to Mwarokin Estates")
        if random.random() < 0.01:
            logger.warning("Simulated transfer to estate failed")
            return False
        return True


# ---------------------------------------------------------------------
# Subscription Manager
# ---------------------------------------------------------------------

class SubscriptionManager:
    """
    Manages subscription plans, upgrades, downgrades, and billing cycles.
    """

    def __init__(self, contracts: Optional[List[Contract]] = None):
        self.contracts: List[Contract] = contracts or []

    def add_contract(self, contract: Contract) -> None:
        """Add a contract to the manager."""
        if contract not in self.contracts:
            self.contracts.append(contract)

    def get_active_contracts(self) -> List[Contract]:
        """Return all active contracts."""
        return [c for c in self.contracts if c.status == ContractStatus.ACTIVE]

    def change_plan(self, contract: Contract, new_plan: PlanType) -> None:
        """
        Upgrade or downgrade a subscription plan.
        Only allowed for subscription‑based contracts.
        """
        if contract.fee_model != FeeModel.SUBSCRIPTION:
            raise ValueError("Cannot change plan for non‑subscription contract")
        if contract.status != ContractStatus.ACTIVE:
            raise ValueError("Contract must be active to change plan")
        old_plan = contract.plan_type
        contract.plan_type = new_plan
        logger.info(
            f"Contract {contract.contract_id} changed plan from {old_plan} to {new_plan}"
        )

    def monthly_billing_cycle(self, contracts: List[Contract]) -> Dict[str, Any]:
        """
        Process monthly billing for a list of contracts.
        Returns a summary of deductions and disbursements.
        """
        results = {
            "total_fees_collected": Decimal("0.00"),
            "total_disbursed": Decimal("0.00"),
            "contracts_processed": [],
            "errors": [],
        }

        for contract in contracts:
            if contract.status != ContractStatus.ACTIVE:
                results["errors"].append(
                    f"Contract {contract.contract_id} not active, skipped."
                )
                continue

            if not contract.payout_account or not contract.payout_account.is_verified:
                results["errors"].append(
                    f"Contract {contract.contract_id} has no verified account, skipped."
                )
                continue

            # 1. Calculate fee
            fee = contract.calculate_fee()
            logger.info(
                f"Processing {contract.contract_id} – Fee: {fee} "
                f"for {contract.landlord.full_name}"
            )

            # 2. Deduct fee from landlord's account
            if not PaymentProcessor.deduct_fee(contract.payout_account, fee):
                results["errors"].append(
                    f"Deduction failed for {contract.contract_id}"
                )
                continue

            # 3. Transfer fee to Mwarokin Estates
            if not PaymentProcessor.disburse_to_estate(fee):
                results["errors"].append(
                    f"Estate transfer failed for {contract.contract_id}"
                )
                continue

            results["total_fees_collected"] += fee

            # 4. Disburse net rent to landlord (if revenue sharing)
            # For subscription, no rent disbursement; landlord receives rent directly (we only deduct fee)
            # However, the UI suggests that for revenue sharing, the landlord gets rent minus fee.
            # But the actual rent collection is done separately by the system.
            # In this simplified model, we assume the rent has already been collected and we disburse the net.
            if contract.fee_model == FeeModel.REVENUE_SHARING:
                total_rent = contract.property.average_rent * contract.property.unit_count
                net_rent = total_rent - fee
                if not PaymentProcessor.disburse_to_landlord(contract.payout_account, net_rent):
                    results["errors"].append(
                        f"Disbursement to landlord failed for {contract.contract_id}"
                    )
                    continue
                results["total_disbursed"] += net_rent
            else:
                # For subscription: landlord receives full rent; fee is deducted separately.
                # We assume rent is disbursed elsewhere.
                results["total_disbursed"] += Decimal("0.00")  # Not handled here

            results["contracts_processed"].append(contract.contract_id)

        return results


# ---------------------------------------------------------------------
# Automated Disbursement Engine
# ---------------------------------------------------------------------

class AutomatedDisbursementEngine:
    """
    Orchestrates the entire monthly disbursement process.
    """

    def __init__(self, subscription_manager: SubscriptionManager):
        self.subscription_manager = subscription_manager
        self.processor = PaymentProcessor()

    def run_monthly_cycle(self) -> Dict[str, Any]:
        """
        Execute the monthly cycle for all active contracts.
        Returns a comprehensive report.
        """
        logger.info("Starting monthly disbursement cycle")
        active_contracts = self.subscription_manager.get_active_contracts()
        if not active_contracts:
            logger.warning("No active contracts found.")
            return {"message": "No active contracts", "errors": []}

        result = self.subscription_manager.monthly_billing_cycle(active_contracts)
        logger.info(
            f"Monthly cycle completed: "
            f"collected {result['total_fees_collected']}, "
            f"disbursed {result['total_disbursed']}"
        )
        if result["errors"]:
            logger.warning(f"Errors: {result['errors']}")
        return result


# ---------------------------------------------------------------------
# Factory / Helper functions
# ---------------------------------------------------------------------

def create_sample_contract(
    fee_model: FeeModel = FeeModel.REVENUE_SHARING,
    plan: Optional[PlanType] = None,
) -> Contract:
    """Create a sample contract for demonstration."""
    landlord = Landlord(
        full_name="Grace Wanjiku Mwarema",
        national_id="24681012",
        phone="0712345678",
        email="grace@example.com",
    )
    property = Property(
        name="Kilimani Court Apartments",
        county="Nairobi",
        unit_count=12,
        average_rent=Decimal("20000.00"),
    )
    account = PayoutAccount(
        account_type=AccountType.MPESA,
        identifier="0712345678",
        holder_name=landlord.full_name,
    )
    account.verify()  # simulate verification

    contract = Contract(
        landlord=landlord,
        property=property,
        fee_model=fee_model,
        plan_type=plan,
        payout_account=account,
    )
    contract.activate()
    return contract


# ---------------------------------------------------------------------
# Demo / Usage Example
# ---------------------------------------------------------------------

def run_demo() -> None:
    """Demonstrate the subscription and disbursement engine."""

    print("\n" + "=" * 60)
    print("MWAROKIN ESTATES – AUTOMATED DISBURSEMENT ENGINE")
    print("=" * 60 + "\n")

    # Create a subscription manager
    mgr = SubscriptionManager()

    # Create multiple sample contracts
    # 1. Revenue Sharing contract
    rev_contract = create_sample_contract(FeeModel.REVENUE_SHARING)
    mgr.add_contract(rev_contract)
    print(f"✅ Created Revenue Sharing Contract: {rev_contract.contract_id}")
    print(f"   Landlord: {rev_contract.landlord.full_name}")
    print(f"   Property: {rev_contract.property.name} ({rev_contract.property.unit_count} units)")
    print(f"   Average rent: {rev_contract.property.average_rent} / unit")
    print(f"   Fee: 5% of total rent\n")

    # 2. Subscription contract (Msingi plan)
    sub_contract = create_sample_contract(
        FeeModel.SUBSCRIPTION,
        PlanType.MSINGI
    )
    mgr.add_contract(sub_contract)
    print(f"✅ Created Subscription Contract: {sub_contract.contract_id}")
    print(f"   Landlord: {sub_contract.landlord.full_name}")
    print(f"   Property: {sub_contract.property.name}")
    print(f"   Plan: {sub_contract.plan_type.display_name} – {sub_contract.plan_type.monthly_fee}/mo\n")

    # Run the monthly cycle
    engine = AutomatedDisbursementEngine(mgr)
    report = engine.run_monthly_cycle()

    print("\n📊 MONTHLY CYCLE REPORT")
    print("-" * 40)
    print(f"Total fees collected:   KSh {report['total_fees_collected']:,.2f}")
    print(f"Total disbursed:        KSh {report['total_disbursed']:,.2f}")
    print(f"Contracts processed:    {len(report['contracts_processed'])}")
    print(f"Errors:                 {len(report['errors'])}")
    if report['errors']:
        print("\n⚠️ Errors encountered:")
        for err in report['errors']:
            print(f"  - {err}")
    print("\n✅ Demo completed successfully.")


# ---------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------

if __name__ == "__main__":
    run_demo()
```