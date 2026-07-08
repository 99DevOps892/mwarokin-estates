```python
"""
Mwarokin Estates — Advanced Subscription & Automated Disbursement Engine
Supports 16+ pricing models with flexible fee calculation and automated payment processing.
"""

from __future__ import annotations

import logging
import random
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import List, Optional, Dict, Any, Callable, Union
from uuid import uuid4

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Constants & Helpers
# ---------------------------------------------------------------------
def to_decimal(value: Union[int, float, str, Decimal]) -> Decimal:
    """Convert to Decimal with rounding to 2 decimal places."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------
class FeeModelType(str, Enum):
    """All pricing models supported by the system."""
    REVENUE_SHARING = "revenue-share"
    MSINGI = "msingi"
    JENGO = "jengo"
    MILKI = "milki"
    TAIFA = "taifa"
    COMMISSION_PER_UNIT = "commission-per-unit"
    ANNUAL_MEMBERSHIP = "annual-membership"
    PAY_PER_PROPERTY = "pay-per-property"
    TENANT_PLACEMENT = "tenant-placement"          # one-time
    RENT_COLLECTION_ONLY = "rent-collection-only"
    LEASING_MARKETING = "leasing-marketing"        # one-time
    MAINTENANCE_SUBSCRIPTION = "maintenance-subscription"
    PREMIUM_CONCIERGE = "premium-concierge"
    PERFORMANCE_BASED = "performance-based"
    REVENUE_SHARE_ADDONS = "revenue-share-addons"
    ESTATE_ENTERPRISE = "estate-enterprise"
    TRANSACTION_BASED = "transaction-based"        # per-event
    AI_SMART_ESTATE = "ai-smart-estate"
    SUCCESS_FEE_RECOVERY = "success-fee-recovery"  # one-time
    HYBRID = "hybrid-plan"


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
    full_name: str
    national_id: str
    phone: str
    email: str
    landlord_id: str = field(default_factory=lambda: f"LND-{uuid4().hex[:8].upper()}")

    def __post_init__(self):
        self._validate()

    def _validate(self) -> None:
        if not re.match(r"^[A-Za-z\s\-']+$", self.full_name):
            raise ValueError("Full name contains invalid characters")
        if not re.match(r"^\d{6,12}$", self.national_id):
            raise ValueError("Invalid national ID format")
        phone_clean = self.phone.replace(" ", "")
        if not re.match(r"^(07|01)\d{8}$", phone_clean):
            raise ValueError("Invalid Kenyan phone number")
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", self.email):
            raise ValueError("Invalid email address")


@dataclass
class PayoutAccount:
    account_type: AccountType
    identifier: str          # phone number or bank account number
    holder_name: str
    bank_name: Optional[str] = None
    branch: Optional[str] = None
    is_verified: bool = False

    def mask_identifier(self) -> str:
        if self.account_type == AccountType.MPESA:
            digits = re.sub(r"\D", "", self.identifier)
            if len(digits) >= 7:
                return digits[:4] + " *** " + digits[-3:]
            return digits
        else:
            if len(self.identifier) >= 4:
                return "••••" + self.identifier[-4:]
            return self.identifier

    def verify(self) -> bool:
        # Simulate external verification
        self.is_verified = True
        return True


@dataclass
class Property:
    name: str
    county: str
    unit_count: int
    average_rent: Decimal = to_decimal(20000.00)

    def __post_init__(self):
        if self.unit_count < 1:
            raise ValueError("Unit count must be at least 1")


# ---------------------------------------------------------------------
# Fee Calculators (Strategy Pattern)
# ---------------------------------------------------------------------
class FeeCalculator:
    """Base class for fee calculation strategies."""

    def calculate_monthly_fee(self, contract: "Contract") -> Decimal:
        """Compute the monthly fee for the given contract."""
        raise NotImplementedError


class RevenueSharingCalculator(FeeCalculator):
    def calculate_monthly_fee(self, contract: "Contract") -> Decimal:
        total_rent = contract.property.average_rent * contract.property.unit_count
        return (total_rent * to_decimal(0.05)).quantize(Decimal("0.01"))


class SubscriptionCalculator(FeeCalculator):
    """Base for fixed subscription plans."""
    def __init__(self, monthly_fee: Decimal):
        self.monthly_fee = monthly_fee

    def calculate_monthly_fee(self, contract: "Contract") -> Decimal:
        return self.monthly_fee


class CommissionPerUnitCalculator(FeeCalculator):
    """Tiered per-unit commission based on unit type (simplified)."""
    def __init__(self, rates: Dict[str, Decimal]):
        """
        rates: dict mapping unit type to fee, e.g. {"bedsitter": 500, "1br": 700, ...}
        For simplicity, we use average rent to determine a rate.
        In real scenario, contract would store unit breakdown.
        """
        self.rates = rates

    def calculate_monthly_fee(self, contract: "Contract") -> Decimal:
        # Simplified: use average rent to pick a rate
        rent = contract.property.average_rent
        if rent <= 10000:
            rate = to_decimal(500)
        elif rent <= 20000:
            rate = to_decimal(700)
        elif rent <= 30000:
            rate = to_decimal(900)
        elif rent <= 40000:
            rate = to_decimal(1200)
        else:
            rate = to_decimal(1500)
        return rate * contract.property.unit_count


class AnnualMembershipCalculator(FeeCalculator):
    """Monthly equivalent of annual subscription."""
    def __init__(self, annual_fee: Decimal):
        self.annual_fee = annual_fee

    def calculate_monthly_fee(self, contract: "Contract") -> Decimal:
        return (self.annual_fee / to_decimal(12)).quantize(Decimal("0.01"))


class PayPerPropertyCalculator(FeeCalculator):
    def __init__(self, price_per_property: Decimal):
        self.price_per_property = price_per_property

    def calculate_monthly_fee(self, contract: "Contract") -> Decimal:
        # Assume one property per contract; for multiple properties, this would be extended.
        return self.price_per_property


class RentCollectionOnlyCalculator(FeeCalculator):
    def __init__(self, per_unit_fee: Decimal):
        self.per_unit_fee = per_unit_fee

    def calculate_monthly_fee(self, contract: "Contract") -> Decimal:
        return self.per_unit_fee * contract.property.unit_count


class MaintenanceSubscriptionCalculator(FeeCalculator):
    def __init__(self, per_property_fee: Decimal):
        self.per_property_fee = per_property_fee

    def calculate_monthly_fee(self, contract: "Contract") -> Decimal:
        return self.per_property_fee  # one property per contract


class PremiumConciergeCalculator(FeeCalculator):
    def __init__(self, base_fee: Decimal):
        self.base_fee = base_fee

    def calculate_monthly_fee(self, contract: "Contract") -> Decimal:
        return self.base_fee


class PerformanceBasedCalculator(FeeCalculator):
    def __init__(self, base_fee: Decimal, bonus_rate: Decimal = to_decimal(0.0)):
        self.base_fee = base_fee
        self.bonus_rate = bonus_rate  # could be based on KPIs

    def calculate_monthly_fee(self, contract: "Contract") -> Decimal:
        # In real implementation, bonuses would be computed from performance data.
        # For demo, we just add a small random bonus.
        bonus = to_decimal(random.randint(0, 500))
        return self.base_fee + bonus


class RevenueShareAddonsCalculator(FeeCalculator):
    def calculate_monthly_fee(self, contract: "Contract") -> Decimal:
        # Estimate 2% of total rent as add-on revenue share
        total_rent = contract.property.average_rent * contract.property.unit_count
        return (total_rent * to_decimal(0.02)).quantize(Decimal("0.01"))


class EstateEnterpriseCalculator(FeeCalculator):
    def __init__(self, per_unit_rates: Dict[int, Decimal]):
        self.per_unit_rates = per_unit_rates  # e.g., {500: 75000, 1000: 120000}

    def calculate_monthly_fee(self, contract: "Contract") -> Decimal:
        units = contract.property.unit_count
        rate = to_decimal(75000)  # default
        for threshold, fee in sorted(self.per_unit_rates.items()):
            if units <= threshold:
                rate = fee
                break
        return rate


class AISmartEstateCalculator(FeeCalculator):
    def __init__(self, base_fee: Decimal):
        self.base_fee = base_fee

    def calculate_monthly_fee(self, contract: "Contract") -> Decimal:
        return self.base_fee


class HybridCalculator(FeeCalculator):
    def __init__(self, platform_fee: Decimal, commission_percent: Decimal, placement_fee: Decimal = to_decimal(0)):
        self.platform_fee = platform_fee
        self.commission_percent = commission_percent
        self.placement_fee = placement_fee

    def calculate_monthly_fee(self, contract: "Contract") -> Decimal:
        total_rent = contract.property.average_rent * contract.property.unit_count
        commission = (total_rent * self.commission_percent).quantize(Decimal("0.01"))
        # Placement fee is one-time, not monthly; here we include it as zero for monthly.
        return self.platform_fee + commission


class TransactionBasedCalculator(FeeCalculator):
    """Not monthly; we return 0 for monthly cycle."""
    def calculate_monthly_fee(self, contract: "Contract") -> Decimal:
        return to_decimal(0)


class TenantPlacementCalculator(FeeCalculator):
    """One-time, not monthly."""
    def calculate_monthly_fee(self, contract: "Contract") -> Decimal:
        return to_decimal(0)


class LeasingMarketingCalculator(FeeCalculator):
    """One-time, not monthly."""
    def calculate_monthly_fee(self, contract: "Contract") -> Decimal:
        return to_decimal(0)


class SuccessFeeRecoveryCalculator(FeeCalculator):
    """One-time, not monthly."""
    def calculate_monthly_fee(self, contract: "Contract") -> Decimal:
        return to_decimal(0)


# ---------------------------------------------------------------------
# Fee Calculator Factory
# ---------------------------------------------------------------------
class FeeCalculatorFactory:
    @staticmethod
    def get_calculator(model_type: FeeModelType, **kwargs) -> FeeCalculator:
        if model_type == FeeModelType.REVENUE_SHARING:
            return RevenueSharingCalculator()
        elif model_type == FeeModelType.MSINGI:
            return SubscriptionCalculator(to_decimal(2500))
        elif model_type == FeeModelType.JENGO:
            return SubscriptionCalculator(to_decimal(6500))
        elif model_type == FeeModelType.MILKI:
            return SubscriptionCalculator(to_decimal(15000))
        elif model_type == FeeModelType.TAIFA:
            return SubscriptionCalculator(to_decimal(45000))
        elif model_type == FeeModelType.COMMISSION_PER_UNIT:
            return CommissionPerUnitCalculator({})
        elif model_type == FeeModelType.ANNUAL_MEMBERSHIP:
            # We need to know which plan, but we'll use a default: Msingi equivalent
            return AnnualMembershipCalculator(to_decimal(27000))  # 10% off annual
        elif model_type == FeeModelType.PAY_PER_PROPERTY:
            return PayPerPropertyCalculator(to_decimal(4000))
        elif model_type == FeeModelType.RENT_COLLECTION_ONLY:
            return RentCollectionOnlyCalculator(to_decimal(250))
        elif model_type == FeeModelType.MAINTENANCE_SUBSCRIPTION:
            return MaintenanceSubscriptionCalculator(to_decimal(1000))
        elif model_type == FeeModelType.PREMIUM_CONCIERGE:
            return PremiumConciergeCalculator(to_decimal(25000))
        elif model_type == FeeModelType.PERFORMANCE_BASED:
            return PerformanceBasedCalculator(to_decimal(2000))
        elif model_type == FeeModelType.REVENUE_SHARE_ADDONS:
            return RevenueShareAddonsCalculator()
        elif model_type == FeeModelType.ESTATE_ENTERPRISE:
            return EstateEnterpriseCalculator({500: to_decimal(75000), 1000: to_decimal(120000)})
        elif model_type == FeeModelType.AI_SMART_ESTATE:
            return AISmartEstateCalculator(to_decimal(5000))
        elif model_type == FeeModelType.HYBRID:
            return HybridCalculator(to_decimal(1500), to_decimal(0.02))
        elif model_type == FeeModelType.TRANSACTION_BASED:
            return TransactionBasedCalculator()
        elif model_type == FeeModelType.TENANT_PLACEMENT:
            return TenantPlacementCalculator()
        elif model_type == FeeModelType.LEASING_MARKETING:
            return LeasingMarketingCalculator()
        elif model_type == FeeModelType.SUCCESS_FEE_RECOVERY:
            return SuccessFeeRecoveryCalculator()
        else:
            raise ValueError(f"Unsupported fee model: {model_type}")


# ---------------------------------------------------------------------
# Contract (main entity)
# ---------------------------------------------------------------------
@dataclass
class Contract:
    landlord: Landlord
    property: Property
    fee_model_type: FeeModelType
    payout_account: PayoutAccount
    contract_id: str = field(default_factory=lambda: f"MWK-{random.randint(100000, 999999)}")
    status: ContractStatus = ContractStatus.DRAFT
    start_date: date = field(default_factory=date.today)
    end_date: Optional[date] = None
    extra_config: Dict[str, Any] = field(default_factory=dict)  # for model-specific config

    def __post_init__(self):
        self._fee_calculator = FeeCalculatorFactory.get_calculator(
            self.fee_model_type, **self.extra_config
        )

    def calculate_monthly_fee(self) -> Decimal:
        """Compute the monthly fee based on the model."""
        return self._fee_calculator.calculate_monthly_fee(self)

    def activate(self) -> None:
        if self.status != ContractStatus.DRAFT:
            raise ValueError("Contract is not in draft state")
        if not self.payout_account.is_verified:
            raise ValueError("Payout account not verified")
        self.status = ContractStatus.ACTIVE
        logger.info(f"Contract {self.contract_id} activated for {self.landlord.full_name}")


# ---------------------------------------------------------------------
# Payment Processor (simulated)
# ---------------------------------------------------------------------
class PaymentProcessor:
    @staticmethod
    def deduct_fee(account: PayoutAccount, amount: Decimal) -> bool:
        logger.info(f"Deducting {amount} from {account.holder_name} ({account.account_type.value})")
        if not account.is_verified:
            logger.error("Account not verified, deduction failed")
            return False
        # Simulate 2% failure rate
        if random.random() < 0.02:
            logger.warning("Simulated deduction failure")
            return False
        return True

    @staticmethod
    def disburse_to_landlord(account: PayoutAccount, amount: Decimal) -> bool:
        logger.info(f"Disbursing {amount} to {account.holder_name}")
        if not account.is_verified:
            logger.error("Account not verified, disbursement failed")
            return False
        if random.random() < 0.02:
            logger.warning("Simulated disbursement failure")
            return False
        return True

    @staticmethod
    def disburse_to_estate(amount: Decimal) -> bool:
        logger.info(f"Transferring {amount} to Mwarokin Estates")
        if random.random() < 0.01:
            logger.warning("Simulated transfer to estate failed")
            return False
        return True


# ---------------------------------------------------------------------
# Subscription Manager
# ---------------------------------------------------------------------
class SubscriptionManager:
    def __init__(self, contracts: Optional[List[Contract]] = None):
        self.contracts: List[Contract] = contracts or []

    def add_contract(self, contract: Contract) -> None:
        if contract not in self.contracts:
            self.contracts.append(contract)

    def get_active_contracts(self) -> List[Contract]:
        return [c for c in self.contracts if c.status == ContractStatus.ACTIVE]

    def monthly_billing_cycle(self, contracts: List[Contract]) -> Dict[str, Any]:
        results = {
            "total_fees_collected": to_decimal(0),
            "total_disbursed": to_decimal(0),
            "contracts_processed": [],
            "errors": [],
        }
        for contract in contracts:
            if contract.status != ContractStatus.ACTIVE:
                results["errors"].append(f"Contract {contract.contract_id} not active, skipped.")
                continue
            if not contract.payout_account.is_verified:
                results["errors"].append(f"Contract {contract.contract_id} has no verified account, skipped.")
                continue

            fee = contract.calculate_monthly_fee()
            if fee == to_decimal(0):
                # Some models are one-time, skip monthly processing
                results["contracts_processed"].append(contract.contract_id)
                continue

            logger.info(f"Processing {contract.contract_id} – Fee: {fee}")

            # Deduct fee from landlord's account
            if not PaymentProcessor.deduct_fee(contract.payout_account, fee):
                results["errors"].append(f"Deduction failed for {contract.contract_id}")
                continue

            # Transfer fee to estate
            if not PaymentProcessor.disburse_to_estate(fee):
                results["errors"].append(f"Estate transfer failed for {contract.contract_id}")
                continue

            results["total_fees_collected"] += fee

            # For models that involve rent disbursement (e.g., revenue sharing)
            # In other models, rent is handled separately or not managed by us.
            if contract.fee_model_type == FeeModelType.REVENUE_SHARING:
                total_rent = contract.property.average_rent * contract.property.unit_count
                net_rent = total_rent - fee
                if not PaymentProcessor.disburse_to_landlord(contract.payout_account, net_rent):
                    results["errors"].append(f"Disbursement to landlord failed for {contract.contract_id}")
                    continue
                results["total_disbursed"] += net_rent
            # For other models, we may not disburse rent through us.

            results["contracts_processed"].append(contract.contract_id)

        return results


# ---------------------------------------------------------------------
# Automated Disbursement Engine (Orchestrator)
# ---------------------------------------------------------------------
class AutomatedDisbursementEngine:
    def __init__(self, manager: SubscriptionManager):
        self.manager = manager

    def run_monthly_cycle(self) -> Dict[str, Any]:
        logger.info("Starting monthly disbursement cycle")
        active = self.manager.get_active_contracts()
        if not active:
            logger.warning("No active contracts found.")
            return {"message": "No active contracts", "errors": []}

        result = self.manager.monthly_billing_cycle(active)
        logger.info(
            f"Monthly cycle completed: collected {result['total_fees_collected']}, "
            f"disbursed {result['total_disbursed']}"
        )
        if result["errors"]:
            logger.warning(f"Errors: {result['errors']}")
        return result


# ---------------------------------------------------------------------
# Demo / Usage
# ---------------------------------------------------------------------
def create_sample_contract(
    model_type: FeeModelType,
    landlord_name: str = "Grace Wanjiku",
    property_name: str = "Kilimani Court",
    units: int = 12,
    rent: Decimal = to_decimal(20000),
) -> Contract:
    landlord = Landlord(
        full_name=landlord_name,
        national_id="24681012",
        phone="0712345678",
        email=f"{landlord_name.replace(' ', '.').lower()}@example.com",
    )
    property = Property(
        name=property_name,
        county="Nairobi",
        unit_count=units,
        average_rent=rent,
    )
    account = PayoutAccount(
        account_type=AccountType.MPESA,
        identifier="0712345678",
        holder_name=landlord.full_name,
    )
    account.verify()

    contract = Contract(
        landlord=landlord,
        property=property,
        fee_model_type=model_type,
        payout_account=account,
    )
    contract.activate()
    return contract


def run_demo():
    print("\n" + "=" * 60)
    print("MWAROKIN ESTATES – ADVANCED SUBSCRIPTION ENGINE")
    print("=" * 60 + "\n")

    manager = SubscriptionManager()

    # Create contracts for various models
    models = [
        FeeModelType.REVENUE_SHARING,
        FeeModelType.MSINGI,
        FeeModelType.JENGO,
        FeeModelType.COMMISSION_PER_UNIT,
        FeeModelType.ANNUAL_MEMBERSHIP,
        FeeModelType.PAY_PER_PROPERTY,
        FeeModelType.RENT_COLLECTION_ONLY,
        FeeModelType.MAINTENANCE_SUBSCRIPTION,
        FeeModelType.PREMIUM_CONCIERGE,
        FeeModelType.PERFORMANCE_BASED,
        FeeModelType.REVENUE_SHARE_ADDONS,
        FeeModelType.ESTATE_ENTERPRISE,
        FeeModelType.AI_SMART_ESTATE,
        FeeModelType.HYBRID,
    ]

    for model in models:
        contract = create_sample_contract(model)
        manager.add_contract(contract)
        print(f"✅ Created {model.value} contract: {contract.contract_id}")
        print(f"   Fee: {contract.calculate_monthly_fee()}")

    print("\n" + "-" * 40)
    print("Running monthly cycle...\n")
    engine = AutomatedDisbursementEngine(manager)
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