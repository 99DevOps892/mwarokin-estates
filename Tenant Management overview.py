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