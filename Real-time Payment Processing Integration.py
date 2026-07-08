# payment_processor.py
import asyncio
from typing import Dict, Any, Optional
import aiohttp
from datetime import datetime

class RealTimePaymentProcessor:
    def __init__(self, os_instance):
        self.os = os_instance
        self.webhook_handlers = {}
        self.setup_webhook_handlers()
    
    def setup_webhook_handlers(self):
        """Setup handlers for different payment webhooks"""
        self.webhook_handlers = {
            "payment.succeeded": self.handle_payment_succeeded,
            "payment.failed": self.handle_payment_failed,
            "subscription.updated": self.handle_subscription_updated,
            "refund.processed": self.handle_refund_processed
        }
    
    async def handle_payment_webhook(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming payment webhooks"""
        if event_type in self.webhook_handlers:
            return await self.webhook_handlers[event_type](data)
        return {"status": "error", "message": f"Unknown event type: {event_type}"}
    
    async def handle_payment_succeeded(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful payment webhook"""
        tenant_id = data.get("metadata", {}).get("tenant_id")
        amount = data.get("amount", 0) / 100  # Convert from cents
        currency = data.get("currency", "usd")
        
        if not tenant_id:
            return {"status": "error", "message": "Missing tenant_id in metadata"}
        
        # Update tenant status and allocate properties
        payment_result = await self.os.handle_payment(
            tenant_id=tenant_id,
            amount=amount,
            currency=currency,
            payment_method={"type": "webhook", "data": data}
        )
        
        return payment_result
    
    async def handle_payment_failed(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed payment webhook"""
        tenant_id = data.get("metadata", {}).get("tenant_id")
        
        if not tenant_id:
            return {"status": "error", "message": "Missing tenant_id in metadata"}
        
        # Mark tenant as delinquent
        if tenant_id in self.os.tenants:
            tenant = self.os.tenants[tenant_id]
            tenant.status = TenantStatus.DELINQUENT
            
            # Send notification
            await self.send_payment_failure_notification(tenant_id, data)
            
            return {"status": "success", "message": "Tenant marked as delinquent"}
        
        return {"status": "error", "message": "Tenant not found"}
    
    async def send_payment_failure_notification(self, tenant_id: str, data: Dict[str, Any]):
        """Send payment failure notification to tenant"""
        # In real implementation, this would send email, SMS, or in-app notification
        print(f"Payment failed for tenant {tenant_id}. Data: {data}")
        
        # Example: Integrate with notification service
        # await notification_service.send(
        #     recipient=tenant_id,
        #     template="payment_failed",
        #     data=data
        # )