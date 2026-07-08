import uuid
import datetime
import logging
from typing import Dict, List, Optional, Tuple, Union, AsyncGenerator, Any
from dataclasses import dataclass, field
from decimal import Decimal
import hashlib
import json
from enum import Enum
from pydantic import BaseModel, Field, validator, root_validator
from typing_extensions import Literal
from abc import ABC, abstractmethod
import asyncio
from functools import wraps
import redis.asyncio as redis
from contextlib import asynccontextmanager
import aiohttp
from dataclasses_json import dataclass_json
import numpy as np
from scipy import stats

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mwarokin_billing_audit.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Cache configuration
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def async_cache(ttl: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{hash(str(args))}:{hash(str(kwargs))}"
            cached = await redis_client.get(key)
            if cached:
                return json.loads(cached)
            result = await func(*args, **kwargs)
            await redis_client.setex(key, ttl, json.dumps(result, default=str))
            return result
        return wrapper
    return decorator

def audit_trail(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = datetime.datetime.now()
        tenant_id = kwargs.get('tenant_id') or (args[1] if len(args) > 1 else 'unknown')
        audit_id = str(uuid.uuid4())
        
        logger.info(f"AUDIT_START {audit_id} - {func.__name__} - Tenant: {tenant_id}")
        
        try:
            result = await func(*args, **kwargs)
            duration = (datetime.datetime.now() - start_time).total_seconds()
            logger.info(f"AUDIT_SUCCESS {audit_id} - Duration: {duration:.2f}s")
            return result
        except Exception as e:
            duration = (datetime.datetime.now() - start_time).total_seconds()
            logger.error(f"AUDIT_FAILURE {audit_id} - Duration: {duration:.2f}s - Error: {str(e)}")
            raise
    return wrapper

class PaymentFrequency(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    BIANNUAL = "biannual"
    ANNUAL = "annual"

class BillingTier(str, Enum):
    TIER_1 = "1-10_homes"
    TIER_2 = "11-30_homes"
    TIER_3 = "31-100_homes"
    TIER_4 = "101-500_homes"
    TIER_5 = "501-1000_homes"
    TIER_6 = "multi_estates"

class TransactionType(str, Enum):
    LISTING_FEE = "listing_fee"
    LEASING_FEE = "leasing_fee"
    WHITELABEL_FEE = "whitelabel_fee"
    TRANSACTION_FEE = "transaction_fee"
    MANAGEMENT_FEE = "management_fee"
    SUBSCRIPTION = "subscription"
    MAINTENANCE_FEE = "maintenance_fee"
    UTILITY_FEE = "utility_fee"

class PropertyStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    VACANT = "vacant"
    LEASED = "leased"

@dataclass_json
@dataclass
class BillingTierConfig:
    min_properties: int
    max_properties: Optional[int]
    min_fee: Decimal
    max_fee: Decimal
    description: str
    discount_rate: Decimal = Decimal('0.0')
    features: List[str] = field(default_factory=list)

@dataclass_json
@dataclass
class BillingResult:
    tenant_id: str
    total_fee: Decimal
    breakdown: Dict[str, Decimal]
    explanation: str
    audit_id: str
    timestamp: datetime.datetime
    metrics: 'PropertyMetrics'
    payment_options: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    risk_score: float = 0.0

class PropertyMetrics(BaseModel):
    total_properties: int = Field(0, ge=0)
    active_listings: int = Field(0, ge=0)
    leased_properties: int = Field(0, ge=0)
    vacant_properties: int = Field(0, ge=0)
    total_rental_value: Decimal = Field(Decimal('0'), ge=0)
    average_rent: Decimal = Field(Decimal('0'), ge=0)
    occupancy_rate: Decimal = Field(Decimal('0'), ge=0, le=1)
    revenue_velocity: Decimal = Field(Decimal('0'))  # Monthly revenue growth rate
    maintenance_costs: Decimal = Field(Decimal('0'), ge=0)
    
    @root_validator
    def validate_metrics(cls, values):
        total = values.get('total_properties', 0)
        leased = values.get('leased_properties', 0)
        if total > 0:
            values['occupancy_rate'] = Decimal(str(leased / total))
        return values

class PaymentCalculation(BaseModel):
    base_amount: Decimal = Field(..., ge=0)
    transaction_fee: Decimal = Field(..., ge=0)
    platform_fee: Decimal = Field(..., ge=0)
    discount_amount: Decimal = Field(Decimal('0'), ge=0)
    total_amount: Decimal = Field(..., ge=0)
    currency: str = "KSH"
    tax_amount: Decimal = Field(Decimal('0'), ge=0)
    net_amount: Decimal = Field(..., ge=0)

    @validator('total_amount')
    def validate_total_amount(cls, v, values):
        if v < Decimal('0'):
            raise ValueError('Total amount cannot be negative')
        return v

class Property(BaseModel):
    id: str
    status: PropertyStatus
    lease_status: Literal['leased', 'vacant']
    monthly_rent: Decimal = Field(..., ge=0)
    location: Optional[str] = None
    property_type: Optional[str] = None
    maintenance_cost: Decimal = Field(Decimal('0'), ge=0)
    last_renovation: Optional[datetime.datetime] = None

class Agent(ABC):
    @abstractmethod
    async def process(self, tenant_id: str, payload: dict) -> dict:
        pass
    
    @abstractmethod
    async def validate_input(self, payload: dict) -> bool:
        pass

class BillingAgent(Agent):
    def __init__(self):
        self.tiers = self._initialize_tiers()
        self.leasing_fee_rate = Decimal('0.05')
        self.transaction_fee_rate = Decimal('0.015')
        self.white_label_fee = Decimal('10000')
        self.maintenance_fee_rate = Decimal('0.02')

    def _initialize_tiers(self) -> Dict[BillingTier, BillingTierConfig]:
        return {
            BillingTier.TIER_1: BillingTierConfig(
                1, 10, Decimal('7000'), Decimal('15000'), 
                "Small Portfolio", Decimal('0.05'),
                ["Basic Reporting", "Email Support"]
            ),
            BillingTier.TIER_2: BillingTierConfig(
                11, 30, Decimal('15000'), Decimal('30000'), 
                "Medium Portfolio", Decimal('0.07'),
                ["Advanced Analytics", "Phone Support", "API Access"]
            ),
            BillingTier.TIER_3: BillingTierConfig(
                31, 100, Decimal('30000'), Decimal('60000'), 
                "Large Portfolio", Decimal('0.10'),
                ["Custom Reporting", "Dedicated Support", "White-label Options"]
            ),
            BillingTier.TIER_4: BillingTierConfig(
                101, 500, Decimal('60000'), Decimal('150000'), 
                "Enterprise Portfolio", Decimal('0.12'),
                ["Enterprise Features", "24/7 Support", "SLA Guarantee"]
            ),
            BillingTier.TIER_5: BillingTierConfig(
                501, 1000, Decimal('150000'), Decimal('200000'), 
                "Premium Portfolio", Decimal('0.15'),
                ["Premium Support", "Custom Development", "Training"]
            ),
            BillingTier.TIER_6: BillingTierConfig(
                1001, None, Decimal('1000000'), Decimal('1000000'), 
                "Multi-Estate", Decimal('0.20'),
                ["Full Customization", "Dedicated Team", "Priority Features"]
            )
        }

    async def validate_input(self, payload: dict) -> bool:
        required_fields = ['num_homes', 'properties']
        if not all(field in payload for field in required_fields):
            return False
        
        if payload['num_homes'] < 0:
            return False
            
        try:
            properties = payload.get('properties', [])
            for prop in properties:
                if 'monthly_rent' in prop:
                    Decimal(str(prop['monthly_rent']))
        except:
            return False
            
        return True

    @audit_trail
    async def process(self, tenant_id: str, payload: dict) -> dict:
        if not await self.validate_input(payload):
            raise ValueError("Invalid payload structure")

        num_homes = payload.get('num_homes', 0)
        properties_data = payload.get('properties', [])
        monthly_rent = Decimal(str(payload.get('monthly_rent', '0')))
        transaction_amount = Decimal(str(payload.get('transaction_amount', '0')))
        is_multi_estate = payload.get('is_multi_estate', False)
        multi_estate_months = payload.get('multi_estate_months', 0)
        use_white_label = payload.get('use_white_label', False)

        audit_id = str(uuid.uuid4())
        breakdown = {}
        explanations = []
        total_fee = Decimal('0')

        # Convert properties to Pydantic models
        properties = [Property(**prop) for prop in properties_data]

        # Calculate comprehensive property metrics
        metrics = await self._calculate_advanced_metrics(properties)

        # Property Management Fee with tier-based discounts
        if is_multi_estate:
            fee, explanation = await self.calculate_multi_estate_fee(multi_estate_months)
        else:
            fee, explanation = await self.calculate_property_management_fee(num_homes)
        
        breakdown['property_management_fee'] = fee
        explanations.append(explanation)
        total_fee += fee

        # Leasing Fee
        if monthly_rent > 0:
            fee, explanation = await self.calculate_leasing_fee(monthly_rent)
            breakdown['leasing_fee'] = fee
            explanations.append(explanation)
            total_fee += fee

        # Transaction Fee
        if transaction_amount > 0:
            fee, explanation = await self.calculate_transaction_fee(transaction_amount)
            breakdown['transaction_fee'] = fee
            explanations.append(explanation)
            total_fee += fee

        # Maintenance Fee
        maintenance_fee, maintenance_explanation = await self.calculate_maintenance_fee(properties)
        if maintenance_fee > 0:
            breakdown['maintenance_fee'] = maintenance_fee
            explanations.append(maintenance_explanation)
            total_fee += maintenance_fee

        # White-Label Fee
        if use_white_label:
            breakdown['white_label_fee'] = self.white_label_fee
            explanations.append(f"White-Label Fee: Ksh{self.white_label_fee:.2f}")
            total_fee += self.white_label_fee

        # Risk Assessment
        risk_score = await self.assess_risk(metrics, properties)
        breakdown['risk_score'] = Decimal(str(risk_score))

        # ROI Calculation with risk adjustment
        revenue = monthly_rent + transaction_amount
        roi, roi_explanation = await self.calculate_enhanced_roi(revenue, total_fee, risk_score)
        breakdown['roi_percent'] = roi
        explanations.append(roi_explanation)

        # Generate payment options
        payment_options = await PaymentFeatures.generate_payment_options(total_fee)

        result = BillingResult(
            tenant_id=tenant_id,
            total_fee=total_fee,
            breakdown=breakdown,
            explanation="\n".join(explanations),
            audit_id=audit_id,
            timestamp=datetime.datetime.now(),
            metrics=metrics,
            payment_options=payment_options,
            risk_score=risk_score
        )

        return result.to_dict()

    async def _calculate_advanced_metrics(self, properties: List[Property]) -> PropertyMetrics:
        total_properties = len(properties)
        active_listings = sum(1 for p in properties if p.status == PropertyStatus.ACTIVE)
        leased_properties = sum(1 for p in properties if p.lease_status == 'leased')
        vacant_properties = total_properties - leased_properties
        total_rent = sum(p.monthly_rent for p in properties)
        average_rent = total_rent / total_properties if total_properties > 0 else Decimal('0')
        maintenance_costs = sum(p.maintenance_cost for p in properties)
        
        # Calculate revenue velocity (simplified)
        revenue_velocity = await self._calculate_revenue_velocity(properties)
        
        return PropertyMetrics(
            total_properties=total_properties,
            active_listings=active_listings,
            leased_properties=leased_properties,
            vacant_properties=vacant_properties,
            total_rental_value=total_rent,
            average_rent=average_rent,
            maintenance_costs=maintenance_costs,
            revenue_velocity=revenue_velocity
        )

    async def _calculate_revenue_velocity(self, properties: List[Property]) -> Decimal:
        """Calculate monthly revenue growth rate based on historical data"""
        # Simplified implementation - in production, use actual historical data
        if len(properties) == 0:
            return Decimal('0')
        
        current_revenue = sum(p.monthly_rent for p in properties)
        # Mock previous month's revenue with some variation
        previous_revenue = current_revenue * Decimal('0.95')
        
        if previous_revenue > 0:
            velocity = ((current_revenue - previous_revenue) / previous_revenue) * 100
            return velocity
        return Decimal('0')

    @async_cache(ttl=3600)
    async def calculate_property_management_fee(self, num_homes: int) -> Tuple[Decimal, str]:
        for tier, config in self.tiers.items():
            if config.max_properties is None or (num_homes >= config.min_properties and num_homes <= config.max_properties):
                if config.max_properties and config.max_properties > config.min_properties:
                    range_size = config.max_properties - config.min_properties
                    fee_range = config.max_fee - config.min_fee
                    base_fee = config.min_fee + (fee_range * (num_homes - config.min_properties) / range_size)
                else:
                    base_fee = config.min_fee
                
                # Apply tier discount
                discount = base_fee * config.discount_rate
                final_fee = base_fee - discount
                
                explanation = (
                    f"Property Management Fee: {num_homes} homes in {tier.value} "
                    f"({config.min_properties}-{config.max_properties or '∞'}). "
                    f"Base: Ksh{base_fee:.2f}, Discount: {config.discount_rate*100}% (Ksh{discount:.2f}), "
                    f"Final: Ksh{final_fee:.2f}. Features: {', '.join(config.features)}"
                )
                return final_fee, explanation
        return Decimal('0'), "No applicable tier found"

    async def calculate_multi_estate_fee(self, months: int) -> Tuple[Decimal, str]:
        if months not in [3, 6, 12]:
            return Decimal('0'), f"Invalid period: {months}. Must be 3, 6, or 12 months."
        
        base_fee = Decimal('1000000')
        if months == 6:
            base_fee *= Decimal('0.9')  # 10% discount for 6 months
        elif months == 12:
            base_fee *= Decimal('0.8')  # 20% discount for 12 months
            
        explanation = f"Multi-Estate Fee: Ksh{base_fee:.2f} for {months}-month plan."
        return base_fee, explanation

    async def calculate_leasing_fee(self, monthly_rent: Decimal) -> Tuple[Decimal, str]:
        fee = monthly_rent * self.leasing_fee_rate
        explanation = (
            f"Leasing Fee: {self.leasing_fee_rate*100}% of monthly rent (Ksh{monthly_rent:.2f}). "
            f"Calculated: Ksh{fee:.2f}"
        )
        return fee, explanation

    async def calculate_transaction_fee(self, transaction_amount: Decimal) -> Tuple[Decimal, str]:
        fee = transaction_amount * self.transaction_fee_rate
        explanation = (
            f"Transaction Fee: {self.transaction_fee_rate*100}% of transaction amount "
            f"(Ksh{transaction_amount:.2f}). Calculated: Ksh{fee:.2f}"
        )
        return fee, explanation

    async def calculate_maintenance_fee(self, properties: List[Property]) -> Tuple[Decimal, str]:
        total_maintenance = sum(p.maintenance_cost for p in properties)
        fee = total_maintenance * self.maintenance_fee_rate
        explanation = (
            f"Maintenance Management Fee: {self.maintenance_fee_rate*100}% of total maintenance costs "
            f"(Ksh{total_maintenance:.2f}). Calculated: Ksh{fee:.2f}"
        )
        return fee, explanation

    async def calculate_enhanced_roi(self, revenue: Decimal, expenses: Decimal, risk_score: float) -> Tuple[Decimal, str]:
        if expenses == 0:
            return Decimal('0'), "ROI: Cannot calculate, expenses are zero."
        
        base_roi = ((revenue - expenses) / expenses) * 100
        # Adjust ROI based on risk (higher risk = lower effective ROI)
        risk_adjustment = Decimal(str(1 - (risk_score / 10)))  # Simple risk adjustment
        adjusted_roi = base_roi * risk_adjustment
        
        explanation = (
            f"Enhanced ROI: Base {base_roi:.2f}%, Risk-adjusted {adjusted_roi:.2f}% "
            f"(Risk score: {risk_score:.1f}/10)"
        )
        return adjusted_roi, explanation

    async def assess_risk(self, metrics: PropertyMetrics, properties: List[Property]) -> float:
        """Assess portfolio risk on a scale of 0-10"""
        risk_factors = []
        
        # Occupancy risk
        if metrics.occupancy_rate < Decimal('0.7'):
            risk_factors.append(3.0)
        elif metrics.occupancy_rate < Decimal('0.85'):
            risk_factors.append(1.5)
        else:
            risk_factors.append(0.5)
            
        # Maintenance risk
        avg_maintenance = metrics.maintenance_costs / metrics.total_properties if metrics.total_properties > 0 else Decimal('0')
        if avg_maintenance > Decimal('5000'):
            risk_factors.append(2.0)
            
        # Revenue concentration risk
        rents = [p.monthly_rent for p in properties]
        if rents:
            cv = np.std(rents) / np.mean(rents) if np.mean(rents) > 0 else 0
            risk_factors.append(float(cv * 2))
            
        # Property age risk (simplified)
        old_properties = sum(1 for p in properties 
                           if p.last_renovation and 
                           (datetime.datetime.now() - p.last_renovation).days > 3650)  # >10 years
        if old_properties / len(properties) > 0.3:
            risk_factors.append(2.0)
            
        return min(10.0, sum(risk_factors))

    async def stream_billing_progress(self, tenant_id: str, num_homes: int) -> AsyncGenerator[str, None]:
        yield f"Progress: Calculating property management fee for tenant {tenant_id}..."
        fee, explanation = await self.calculate_property_management_fee(num_homes)
        yield f"Progress: {explanation}"
        yield f"Progress: Assessing portfolio risk..."
        yield f"Progress: Finalizing billing calculations for tenant {tenant_id}..."

class PaymentFeatures:
    @staticmethod
    @async_cache(ttl=600)
    async def generate_payment_options(total_amount: Decimal) -> Dict:
        options = {
            'single_payment': {
                'amount': float(total_amount),
                'processing_fee': 0.0,
                'total': float(total_amount),
                'recommended': total_amount < Decimal('50000')
            }
        }
        
        for installments in [3, 6, 12]:
            installment_amounts = await PaymentFeatures.calculate_installment_plan(total_amount, installments)
            processing_fee = sum(installment_amounts) - total_amount
            options[f'{installments}_installments'] = {
                'installments': [float(amt) for amt in installment_amounts],
                'total': float(sum(installment_amounts)),
                'processing_fee': float(processing_fee),
                'recommended': installments == 3 and total_amount > Decimal('50000')
            }
            
        return options

    @staticmethod
    async def calculate_installment_plan(total_amount: Decimal, installment_count: int) -> List[Decimal]:
        if installment_count == 1:
            return [total_amount]
            
        # Dynamic processing fee based on installment count
        fee_rates = {3: Decimal('0.015'), 6: Decimal('0.025'), 12: Decimal('0.035')}
        processing_fee_rate = fee_rates.get(installment_count, Decimal('0.02'))
        processing_fee = total_amount * processing_fee_rate
        
        total_with_fee = total_amount + processing_fee
        installment_amount = (total_with_fee / installment_count).quantize(Decimal('0.01'))
        
        installments = [installment_amount] * installment_count
        # Adjust for rounding
        installments[-1] += total_with_fee - sum(installments)
        return installments

    @staticmethod
    async def apply_loyalty_discount(total_amount: Decimal, tenant_since: datetime.datetime, 
                                   total_spent: Decimal, payment_history: List[dict]) -> Tuple[Decimal, Decimal]:
        tenure_years = (datetime.datetime.now() - tenant_since).days / 365
        discount_rate = Decimal('0.0')
        
        # Tenure-based discount
        if tenure_years >= 5:
            discount_rate += Decimal('0.08')
        elif tenure_years >= 3:
            discount_rate += Decimal('0.05')
        elif tenure_years >= 1:
            discount_rate += Decimal('0.02')
            
        # Volume-based discount
        if total_spent > Decimal('5000000'):
            discount_rate += Decimal('0.05')
        elif total_spent > Decimal('1000000'):
            discount_rate += Decimal('0.03')
        elif total_spent > Decimal('500000'):
            discount_rate += Decimal('0.015')
            
        # Payment history discount (good payment behavior)
        on_time_payments = sum(1 for payment in payment_history if payment.get('on_time', False))
        total_payments = len(payment_history)
        if total_payments > 0 and on_time_payments / total_payments > 0.9:
            discount_rate += Decimal('0.02')
            
        discount_amount = total_amount * discount_rate
        return total_amount - discount_amount, discount_amount

    @staticmethod
    async def optimize_payment_method(amount: Decimal, payment_method: str, tenant_risk: float) -> Dict:
        fee_rates = {
            'bank_transfer': Decimal('0.0'),
            'mobile_money': Decimal('0.015'),
            'credit_card': Decimal('0.025'),
            'debit_card': Decimal('0.015'),
            'crypto': Decimal('0.03')
        }
        
        # Adjust fees based on risk
        risk_multiplier = Decimal(str(1 + (tenant_risk / 20)))  # 5% increase per risk point
        
        fee_rate = fee_rates.get(payment_method, Decimal('0.02')) * risk_multiplier
        processing_fee = amount * fee_rate
        
        recommendations = []
        optimal_method = 'bank_transfer'
        
        if amount > Decimal('50000') and payment_method != 'bank_transfer':
            recommendations.append("Consider bank transfer for large amounts (no fees)")
        if tenant_risk > 7 and payment_method == 'crypto':
            recommendations.append("High-risk profile detected: consider secure payment methods")
            
        if amount < Decimal('10000'):
            optimal_method = 'mobile_money'
        elif tenant_risk > 5:
            optimal_method = 'bank_transfer'
            
        return {
            'processing_fee': processing_fee.quantize(Decimal('0.01')),
            'total_with_fee': (amount + processing_fee).quantize(Decimal('0.01')),
            'recommendations': recommendations,
            'optimal_method': optimal_method,
            'risk_adjusted_fee': float(fee_rate)
        }

class AnalyticsAgent(Agent):
    async def process(self, tenant_id: str, payload: dict) -> dict:
        properties = [Property(**prop) for prop in payload.get('properties', [])]
        metrics = await self._calculate_analytics(properties)
        return metrics
    
    async def validate_input(self, payload: dict) -> bool:
        return 'properties' in payload
    
    async def _calculate_analytics(self, properties: List[Property]) -> dict:
        if not properties:
            return {}
            
        rents = [float(p.monthly_rent) for p in properties]
        maintenance_costs = [float(p.maintenance_cost) for p in properties]
        
        analytics = {
            'rent_statistics': {
                'mean': np.mean(rents),
                'median': np.median(rents),
                'std_dev': np.std(rents),
                'cv': np.std(rents) / np.mean(rents) if np.mean(rents) > 0 else 0
            },
            'maintenance_analysis': {
                'total_maintenance': sum(maintenance_costs),
                'maintenance_per_property': np.mean(maintenance_costs)
            },
            'portfolio_health': await self._calculate_portfolio_health(properties)
        }
        
        return analytics
    
    async def _calculate_portfolio_health(self, properties: List[Property]) -> dict:
        active_count = sum(1 for p in properties if p.status == PropertyStatus.ACTIVE)
        leased_count = sum(1 for p in properties if p.lease_status == 'leased')
        vacancy_rate = (len(properties) - leased_count) / len(properties) if properties else 0
        
        return {
            'active_rate': active_count / len(properties) if properties else 0,
            'occupancy_rate': leased_count / len(properties) if properties else 0,
            'vacancy_rate': vacancy_rate,
            'health_score': max(0, 100 - (vacancy_rate * 100))
        }

class PaymentOrchestrator:
    def __init__(self):
        self.agents = {
            'billing': BillingAgent(),
            'analytics': AnalyticsAgent()
        }
        self.payment_features = PaymentFeatures()

    @audit_trail
    async def process_billing(self, tenant_id: str, payload: dict) -> dict:
        # Process billing
        billing_result = await self.agents['billing'].process(tenant_id, payload)
        
        # Get tenant info and apply loyalty discounts
        tenant_info = await self._get_tenant_info(tenant_id)
        if tenant_info:
            discounted_total, discount = await self.payment_features.apply_loyalty_discount(
                Decimal(str(billing_result['total_fee'])),
                tenant_info['join_date'],
                Decimal(str(tenant_info['total_spent'])),
                tenant_info.get('payment_history', [])
            )
            billing_result['loyalty_discount'] = float(discount)
            billing_result['discounted_total'] = float(discounted_total)
            billing_result['total_fee'] = float(discounted_total)
        
        # Generate analytics
        analytics_result = await self.agents['analytics'].process(tenant_id, payload)
        billing_result['analytics'] = analytics_result
        
        # Generate payment optimization
        payment_optimization = await self.payment_features.optimize_payment_method(
            Decimal(str(billing_result['total_fee'])),
            'bank_transfer',
            billing_result.get('risk_score', 0)
        )
        billing_result['payment_optimization'] = payment_optimization
        
        return billing_result

    async def _get_tenant_info(self, tenant_id: str) -> dict:
        # Mock tenant data - in production, fetch from database
        return {
            'join_date': datetime.datetime.now() - datetime.timedelta(days=400),
            'total_spent': Decimal('600000'),
            'payment_history': [
                {'amount': 50000, 'on_time': True, 'date': datetime.datetime.now() - datetime.timedelta(days=30)},
                {'amount': 45000, 'on_time': True, 'date': datetime.datetime.now() - datetime.timedelta(days=60)},
                {'amount': 48000, 'on_time': False, 'date': datetime.datetime.now() - datetime.timedelta(days=90)}
            ]
        }

class MwarokinSystem:
    def __init__(self):
        self.orchestrator = PaymentOrchestrator()

    @audit_trail
    async def process_property_billing(self, tenant_id: str, payload: dict) -> dict:
        result = await self.orchestrator.process_billing(tenant_id, payload)
        result['recommendations'] = await self._generate_recommendations(payload, result)
        result['formatted_output'] = display_object(result)
        return result

    async def _generate_recommendations(self, payload: dict, result: dict) -> List[str]:
        recommendations = []
        num_homes = payload.get('num_homes', 0)
        metrics = result.get('metrics', {})
        analytics = result.get('analytics', {})
        
        if metrics.get('vacant_properties', 0) > 0:
            recommendations.append(
                f"Reduce rent by 5-10% for {metrics['vacant_properties']} vacant properties to improve occupancy"
            )
        
        if metrics.get('average_rent', 0) < Decimal('20000'):
            recommendations.append("Consider gradual rent increases for renewals")
            
        if num_homes > 30:
            recommendations.append("Eligible for bulk transaction discounts")
            
        risk_score = result.get('risk_score', 0)
        if risk_score > 7:
            recommendations.append("High portfolio risk detected: consider diversifying property types")
            
        rent_stats = analytics.get('rent_statistics', {})
        if rent_stats.get('cv', 0) > 0.5:
            recommendations.append("High rent concentration risk: consider standardizing rental prices")
            
        return recommendations

    async def get_billing_progress(self, tenant_id: str, num_homes: int) -> AsyncGenerator[str, None]:
        async for progress in self.orchestrator.agents['billing'].stream_billing_progress(tenant_id, num_homes):
            yield progress

# Enhanced display function
def display_object(obj: Any, indent: int = 0, indent_str: str = "  ") -> str:
    """Display all properties of an object in a readable, indented format."""
    def _format_value(value: Any, current_indent: int) -> str:
        indent_space = indent_str * current_indent
        if isinstance(value, dict):
            items = []
            for k, v in value.items():
                if isinstance(v, (dict, list)):
                    items.append(f"{indent_space}{k}:\n{_format_value(v, current_indent + 1)}")
                else:
                    items.append(f"{indent_space}{k}: {v}")
            return "\n".join(items)
        elif isinstance(value, list):
            if not value:
                return f"{indent_space}[]"
            items = []
            for i, item in enumerate(value):
                if isinstance(item, (dict, list)):
                    items.append(f"{indent_space}[{i}]:\n{_format_value(item, current_indent + 1)}")
                else:
                    items.append(f"{indent_space}[{i}]: {item}")
            return "\n".join(items)
        else:
            return f"{indent_space}{value}"
    
    if isinstance(obj, dict):
        return _format_value(obj, indent)
    elif hasattr(obj, '__dict__'):
        return _format_value(obj.__dict__, indent)
    elif isinstance(obj, list):
        return _format_value(obj, indent)
    else:
        return f"{indent_str * indent}{str(obj)}"

# Example usage with enhanced features
async def main():
    system = MwarokinSystem()
    
    payload = {
        'num_homes': 50,
        'monthly_rent': '50000',
        'transaction_amount': '1000000',
        'is_multi_estate': False,
        'multi_estate_months': 0,
        'use_white_label': True,
        'properties': [
            {
                'id': '1', 
                'status': 'active', 
                'lease_status': 'leased', 
                'monthly_rent': 25000,
                'maintenance_cost': 2000,
                'last_renovation': datetime.datetime.now() - datetime.timedelta(days=365)
            },
            {
                'id': '2', 
                'status': 'active', 
                'lease_status': 'leased', 
                'monthly_rent': 35000,
                'maintenance_cost': 1500,
                'last_renovation': datetime.datetime.now() - datetime.timedelta(days=730)
            },
            {
                'id': '3', 
                'status': 'active', 
                'lease_status': 'vacant', 
                'monthly_rent': 20000,
                'maintenance_cost': 1000,
                'last_renovation': datetime.datetime.now() - datetime.timedelta(days=1825)
            }
        ]
    }
    
    print("Processing billing with enhanced features...")
    
    # Show progress
    async for progress in system.get_billing_progress("tenant_123", 50):
        print(progress)
    
    result = await system.process_property_billing("tenant_123", payload)
    
    print("\n" + "="*80)
    print("ENHANCED BILLING RESULT")
    print("="*80)
    print(result['formatted_output'])
    print("\nRECOMMENDATIONS:", result['recommendations'])
    
    # Display analytics
    if 'analytics' in result:
        print("\n" + "="*80)
        print("PORTFOLIO ANALYTICS")
        print("="*80)
        print(display_object(result['analytics']))

if __name__ == "__main__":
    asyncio.run(main())