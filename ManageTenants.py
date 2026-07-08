# mwarokin_os.py
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import json
from dataclasses import dataclass, field
import hashlib

# Enums for system constants
class TenantStatus(Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELINQUENT = "delinquent"
    GRACE_PERIOD = "grace_period"

class PropertyType(Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    LAND = "land"

class PaymentStatus(Enum):
    PAID = "paid"
    PENDING = "pending"
    OVERDUE = "overdue"
    FAILED = "failed"

# Data models
@dataclass
class Tenant:
    tenant_id: str
    name: str
    status: TenantStatus
    subscription_tier: str
    payment_account: Dict[str, Any]
    white_label_settings: Dict[str, Any]
    feature_flags: Dict[str, bool]
    created_at: datetime = field(default_factory=datetime.now)
    last_payment_date: Optional[datetime] = None
    next_payment_due: datetime = field(default_factory=lambda: datetime.now() + timedelta(days=30))

@dataclass
class Property:
    property_id: str
    tenant_id: str
    address: str
    property_type: PropertyType
    details: Dict[str, Any]
    status: str
    assigned_homes: int
    max_homes: int
    location: Dict[str, float]  # lat, long

@dataclass
class PaymentRecord:
    payment_id: str
    tenant_id: str
    amount: float
    currency: str
    status: PaymentStatus
    timestamp: datetime
    properties_allocated: List[str]
    description: str

class MwarokinRealEstateOS:
    def __init__(self):
        self.tenants: Dict[str, Tenant] = {}
        self.properties: Dict[str, Property] = {}
        self.payment_records: Dict[str, PaymentRecord] = {}
        self.agent_registry = {}
        self.initialize_agents()
    
    def initialize_agents(self):
        """Initialize all specialized agents"""
        self.agent_registry = {
            "listing_agent": ListingAgent(self),
            "valuation_agent": ValuationAgent(self),
            "pricing_agent": PricingAgent(self),
            "matchmaking_agent": MatchmakingAgent(self),
            "lead_crm_agent": LeadCRMAgent(self),
            "lease_agent": LeaseAgent(self),
            "transaction_agent": TransactionAgent(self),
            "compliance_agent": ComplianceAgent(self),
            "white_label_agent": WhiteLabelAgent(self),
            "rag_agent": RAGAgent(self),
            "analytics_agent": AnalyticsAgent(self),
        }
    
    async def handle_payment(self, tenant_id: str, amount: float, currency: str, 
                           payment_method: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment and allocate properties based on payment tier"""
        # Verify tenant exists
        if tenant_id not in self.tenants:
            return {"status": "error", "message": "Tenant not found"}
        
        tenant = self.tenants[tenant_id]
        
        # Process payment (in real implementation, integrate with payment gateway)
        payment_status = await self.process_payment_via_gateway(amount, currency, payment_method)
        
        if payment_status["status"] == "success":
            # Create payment record
            payment_id = f"pay_{uuid.uuid4().hex[:12]}"
            payment_record = PaymentRecord(
                payment_id=payment_id,
                tenant_id=tenant_id,
                amount=amount,
                currency=currency,
                status=PaymentStatus.PAID,
                timestamp=datetime.now(),
                properties_allocated=[],
                description=f"Subscription payment for {tenant.subscription_tier} tier"
            )
            
            # Determine properties to allocate based on payment amount
            properties_to_allocate = self.calculate_properties_allocation(amount, tenant.subscription_tier)
            
            # Update tenant status and properties
            tenant.status = TenantStatus.ACTIVE
            tenant.last_payment_date = datetime.now()
            tenant.next_payment_due = datetime.now() + timedelta(days=30)
            
            # Allocate properties
            allocated_properties = []
            for prop_id in properties_to_allocate:
                if prop_id in self.properties:
                    self.properties[prop_id].tenant_id = tenant_id
                    allocated_properties.append(prop_id)
            
            payment_record.properties_allocated = allocated_properties
            
            # Store payment record
            self.payment_records[payment_id] = payment_record
            
            return {
                "status": "success",
                "payment_id": payment_id,
                "allocated_properties": allocated_properties,
                "next_payment_due": tenant.next_payment_due.isoformat()
            }
        else:
            return {"status": "error", "message": "Payment processing failed"}
    
    async def process_payment_via_gateway(self, amount: float, currency: str, 
                                        payment_method: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate payment processing with a gateway"""
        # In a real implementation, this would integrate with Stripe, PayPal, etc.
        await asyncio.sleep(1)  # Simulate network delay
        
        # Simulate payment success (90% success rate)
        import random
        if random.random() > 0.1:  # 90% success rate
            return {"status": "success", "transaction_id": f"txn_{uuid.uuid4().hex[:12]}"}
        else:
            return {"status": "failed", "reason": "Insufficient funds"}
    
    def calculate_properties_allocation(self, amount: float, subscription_tier: str) -> List[str]:
        """Calculate how many properties to allocate based on payment amount and tier"""
        # This is a simplified calculation - real implementation would use tier-based pricing
        properties_to_allocate = []
        
        # Find available properties
        available_properties = [
            prop_id for prop_id, prop in self.properties.items() 
            if prop.tenant_id is None or prop.tenant_id == ""
        ]
        
        # Determine how many properties to allocate based on payment
        if subscription_tier == "basic":
            max_properties = min(5, len(available_properties))
        elif subscription_tier == "professional":
            max_properties = min(20, len(available_properties))
        else:  # enterprise
            max_properties = len(available_properties)
        
        # Allocate properties
        for i in range(max_properties):
            if i < len(available_properties):
                properties_to_allocate.append(available_properties[i])
        
        return properties_to_allocate
    
    def check_tenant_status(self, tenant_id: str) -> Dict[str, Any]:
        """Check tenant status and property allocations"""
        if tenant_id not in self.tenants:
            return {"status": "error", "message": "Tenant not found"}
        
        tenant = self.tenants[tenant_id]
        tenant_properties = [
            prop for prop in self.properties.values() if prop.tenant_id == tenant_id
        ]
        
        return {
            "tenant_id": tenant_id,
            "status": tenant.status.value,
            "subscription_tier": tenant.subscription_tier,
            "properties_allocated": len(tenant_properties),
            "properties": [{
                "property_id": prop.property_id,
                "address": prop.address,
                "type": prop.property_type.value
            } for prop in tenant_properties],
            "last_payment_date": tenant.last_payment_date.isoformat() if tenant.last_payment_date else None,
            "next_payment_due": tenant.next_payment_due.isoformat()
        }
    
    def suspend_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """Suspend tenant for non-payment"""
        if tenant_id not in self.tenants:
            return {"status": "error", "message": "Tenant not found"}
        
        tenant = self.tenants[tenant_id]
        tenant.status = TenantStatus.SUSPENDED
        
        # Free up properties for other tenants
        for prop in self.properties.values():
            if prop.tenant_id == tenant_id:
                prop.tenant_id = None
        
        return {"status": "success", "message": f"Tenant {tenant_id} suspended"}
    
    async def run_agentic_workflow(self, workflow_type: str, payload: Dict[str, Any], 
                                 tenant_id: str) -> Dict[str, Any]:
        """Execute an agentic workflow with tenant context"""
        # Add tenant context to payload
        payload_with_tenant = {**payload, "tenant_id": tenant_id}
        
        if workflow_type == "listing_intake":
            return await self.agent_registry["listing_agent"].process_listing(payload_with_tenant)
        elif workflow_type == "valuation":
            return await self.agent_registry["valuation_agent"].valuate_property(payload_with_tenant)
        elif workflow_type == "matchmaking":
            return await self.agent_registry["matchmaking_agent"].find_matches(payload_with_tenant)
        # Additional workflows would be handled here
        
        return {"status": "error", "message": f"Unknown workflow type: {workflow_type}"}

# Example agent implementation (simplified)
class ListingAgent:
    def __init__(self, os: MwarokinRealEstateOS):
        self.os = os
    
    async def process_listing(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process a new property listing"""
        tenant_id = payload.get("tenant_id")
        # Validate tenant has available properties
        tenant_status = self.os.check_tenant_status(tenant_id)
        if tenant_status["status"] == "error":
            return tenant_status
        
        tenant_properties_count = tenant_status["properties_allocated"]
        tenant = self.os.tenants[tenant_id]
        
        if tenant_properties_count >= tenant.max_homes:
            return {
                "status": "error", 
                "message": "Tenant has reached maximum property limit"
            }
        
        # Process listing (in real implementation, this would include validation, enrichment, etc.)
        property_id = f"prop_{uuid.uuid4().hex[:12]}"
        new_property = Property(
            property_id=property_id,
            tenant_id=tenant_id,
            address=payload.get("address", ""),
            property_type=PropertyType(payload.get("property_type", "residential")),
            details=payload.get("details", {}),
            status="active",
            assigned_homes=0,
            max_homes=10,  # Default value
            location=payload.get("location", {"lat": 0, "long": 0})
        )
        
        self.os.properties[property_id] = new_property
        tenant.assigned_homes += 1
        
        return {
            "status": "success",
            "property_id": property_id,
            "message": "Listing processed successfully"
        }

# Other agents would be implemented similarly...

# Initialize the OS
mwarokin_os = MwarokinRealEstateOS()

# Example usage
async def demo():
    # Create a tenant
    tenant_id = "tenant_123"
    mwarokin_os.tenants[tenant_id] = Tenant(
        tenant_id=tenant_id,
        name="Demo Tenant",
        status=TenantStatus.ACTIVE,
        subscription_tier="professional",
        payment_account={"type": "bank", "last4": "1234"},
        white_label_settings={"logo": "demo.png", "primary_color": "#3366CC"},
        feature_flags={"advanced_analytics": True, "ai_pricing": True}
    )
    
    # Process a payment
    payment_result = await mwarokin_os.handle_payment(
        tenant_id=tenant_id,
        amount=299.99,
        currency="USD",
        payment_method={"type": "credit_card", "token": "card_123"}
    )
    
    print("Payment result:", payment_result)
    
    # Check tenant status
    status = mwarokin_os.check_tenant_status(tenant_id)
    print("Tenant status:", status)
    
    # Process a listing
    listing_result = await mwarokin_os.run_agentic_workflow(
        workflow_type="listing_intake",
        payload={
            "address": "123 Main St, Nairobi, Kenya",
            "property_type": "residential",
            "details": {"bedrooms": 3, "bathrooms": 2, "area_sqft": 1500},
            "location": {"lat": -1.286389, "long": 36.817223}
        },
        tenant_id=tenant_id
    )
    
    print("Listing result:", listing_result)

# Run the demo
if __name__ == "__main__":
    asyncio.run(demo())

    ##Tenant Management Dashboard

    # tenant_dashboard.py
from typing import Dict, List, Any
import pandas as pd
from datetime import datetime, timedelta

class TenantDashboard:
    def __init__(self, os_instance):
        self.os = os_instance
    
    def get_tenant_overview(self, tenant_id: str) -> Dict[str, Any]:
        """Get comprehensive overview of a tenant"""
        tenant_status = self.os.check_tenant_status(tenant_id)
        if tenant_status["status"] == "error":
            return tenant_status
        
        # Get payment history
        payment_history = [
            {
                "payment_id": record.payment_id,
                "amount": record.amount,
                "currency": record.currency,
                "date": record.timestamp.isoformat(),
                "status": record.status.value
            }
            for record in self.os.payment_records.values() 
            if record.tenant_id == tenant_id
        ]
        
        # Get recent activity
        recent_activity = self.get_recent_activity(tenant_id)
        
        # Get utilization metrics
        utilization = self.calculate_utilization(tenant_id)
        
        return {
            **tenant_status,
            "payment_history": payment_history,
            "recent_activity": recent_activity,
            "utilization_metrics": utilization
        }
    
    def get_recent_activity(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Get recent activity for a tenant"""
        # In real implementation, this would query an activity log
        return [
            {
                "timestamp": (datetime.now() - timedelta(hours=i)).isoformat(),
                "action": f"action_{i}",
                "details": f"Details for action {i}"
            }
            for i in range(5)
        ]
    
    def calculate_utilization(self, tenant_id: str) -> Dict[str, Any]:
        """Calculate utilization metrics for a tenant"""
        tenant_properties = [
            prop for prop in self.os.properties.values() 
            if prop.tenant_id == tenant_id
        ]
        
        if not tenant_properties:
            return {
                "property_utilization": 0,
                "lead_conversion": 0,
                "revenue_per_property": 0
            }
        
        # Simplified calculations - real implementation would use actual business metrics
        active_properties = len([p for p in tenant_properties if p.status == "active"])
        total_properties = len(tenant_properties)
        
        return {
            "property_utilization": (active_properties / total_properties) * 100 if total_properties > 0 else 0,
            "lead_conversion": 25.5,  # Example value
            "revenue_per_property": 1500,  # Example value
            "total_properties": total_properties,
            "active_properties": active_properties
        }
    
    def generate_utilization_report(self, tenant_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate a detailed utilization report for a tenant"""
        # This would generate a comprehensive report with charts and metrics
        overview = self.get_tenant_overview(tenant_id)
        
        return {
            "tenant_id": tenant_id,
            "report_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": overview,
            "recommendations": self.generate_recommendations(overview)
        }
    
    def generate_recommendations(self, overview: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on tenant utilization"""
        recommendations = []
        utilization = overview.get("utilization_metrics", {})
        
        if utilization.get("property_utilization", 0) < 60:
            recommendations.append("Consider adding more properties to your portfolio to increase utilization")
        
        if utilization.get("lead_conversion", 0) < 20:
            recommendations.append("Improve lead qualification process to increase conversion rates")
        
        if utilization.get("revenue_per_property", 0) < 1000:
            recommendations.append("Evaluate pricing strategy to increase revenue per property")
        
        return recommendations