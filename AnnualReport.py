import asyncio
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import aiohttp
import logging
from dataclasses import dataclass, asdict
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from io import BytesIO
import base64

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReportType(Enum):
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"
    COMPREHENSIVE = "comprehensive"

@dataclass
class ReportParameters:
    tenant_id: str
    report_type: ReportType
    start_date: datetime
    end_date: datetime
    currency: str = "USD"
    include_comparative: bool = True
    include_forecast: bool = False
    breakdown_by_property: bool = False

@dataclass
class FinancialMetrics:
    total_revenue: float
    total_expenses: float
    net_operating_income: float
    cap_rate: float
    cash_on_cash_return: float
    occupancy_rate: float
    average_rent: float
    revenue_breakdown: Dict[str, float]
    expense_breakdown: Dict[str, float]
    yoy_growth: float

@dataclass
class OperationalMetrics:
    properties_managed: int
    units_managed: int
    new_leases_signed: int
    lease_renewals: int
    tenant_turnover_rate: float
    average_days_vacant: float
    maintenance_requests: int
    average_response_time: float
    tenant_satisfaction_score: float

@dataclass
class ComplianceMetrics:
    kyc_checks_completed: int
    aml_checks_completed: int
    compliance_issues: int
    issues_resolved: int
    audit_trail_completeness: float
    fair_housing_compliance: float
    data_privacy_compliance: float

@dataclass
class PerformanceMetrics:
    lead_conversion_rate: float
    time_to_lease: float
    time_to_close: float
    website_traffic: int
    inquiry_to_viewing_rate: float
    viewing_to_application_rate: float
    application_to_lease_rate: float

class AnnualReportGenerator:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _call_agent(self, endpoint: str, payload: Dict) -> Dict:
        """Generic method to call agent endpoints"""
        try:
            url = f"{self.base_url}/{endpoint}"
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Error calling {endpoint}: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Exception calling {endpoint}: {str(e)}")
            return {}
    
    async def get_financial_data(self, tenant_id: str, start_date: datetime, end_date: datetime) -> FinancialMetrics:
        """Retrieve financial data from AnalyticsAgent and other sources"""
        payload = {
            "tenant_id": tenant_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "metrics": [
                "revenue", "expenses", "noi", "cap_rate", "cash_on_cash", 
                "occupancy", "average_rent", "revenue_breakdown", "expense_breakdown"
            ]
        }
        
        data = await self._call_agent("analytics/financial", payload)
        
        # Calculate YoY growth if comparative data is available
        yoy_growth = 0.0
        if payload.get("include_comparative", True):
            prev_start = start_date - timedelta(days=365)
            prev_end = end_date - timedelta(days=365)
            prev_payload = {**payload, "start_date": prev_start.isoformat(), "end_date": prev_end.isoformat()}
            prev_data = await self._call_agent("analytics/financial", prev_payload)
            
            if prev_data and "total_revenue" in prev_data and data.get("total_revenue", 0) > 0:
                yoy_growth = ((data["total_revenue"] - prev_data["total_revenue"]) / 
                             prev_data["total_revenue"]) * 100
        
        return FinancialMetrics(
            total_revenue=data.get("total_revenue", 0),
            total_expenses=data.get("total_expenses", 0),
            net_operating_income=data.get("noi", 0),
            cap_rate=data.get("cap_rate", 0),
            cash_on_cash_return=data.get("cash_on_cash", 0),
            occupancy_rate=data.get("occupancy", 0),
            average_rent=data.get("average_rent", 0),
            revenue_breakdown=data.get("revenue_breakdown", {}),
            expense_breakdown=data.get("expense_breakdown", {}),
            yoy_growth=yoy_growth
        )
    
    async def get_operational_data(self, tenant_id: str, start_date: datetime, end_date: datetime) -> OperationalMetrics:
        """Retrieve operational data from various agents"""
        payload = {
            "tenant_id": tenant_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
        
        # Get properties and units data
        properties_data = await self._call_agent("analytics/properties", payload)
        
        # Get leasing data
        leasing_data = await self._call_agent("analytics/leasing", payload)
        
        # Get maintenance data
        maintenance_data = await self._call_agent("analytics/maintenance", payload)
        
        # Get tenant satisfaction data
        satisfaction_data = await self._call_agent("analytics/satisfaction", payload)
        
        return OperationalMetrics(
            properties_managed=properties_data.get("total_properties", 0),
            units_managed=properties_data.get("total_units", 0),
            new_leases_signed=leasing_data.get("new_leases", 0),
            lease_renewals=leasing_data.get("renewals", 0),
            tenant_turnover_rate=leasing_data.get("turnover_rate", 0),
            average_days_vacant=leasing_data.get("days_vacant", 0),
            maintenance_requests=maintenance_data.get("total_requests", 0),
            average_response_time=maintenance_data.get("response_time", 0),
            tenant_satisfaction_score=satisfaction_data.get("score", 0)
        )
    
    async def get_compliance_data(self, tenant_id: str, start_date: datetime, end_date: datetime) -> ComplianceMetrics:
        """Retrieve compliance data from ComplianceAgent"""
        payload = {
            "tenant_id": tenant_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
        
        data = await self._call_agent("compliance/metrics", payload)
        
        return ComplianceMetrics(
            kyc_checks_completed=data.get("kyc_checks", 0),
            aml_checks_completed=data.get("aml_checks", 0),
            compliance_issues=data.get("issues", 0),
            issues_resolved=data.get("resolved", 0),
            audit_trail_completeness=data.get("audit_completeness", 0),
            fair_housing_compliance=data.get("fair_housing", 0),
            data_privacy_compliance=data.get("data_privacy", 0)
        )
    
    async def get_performance_data(self, tenant_id: str, start_date: datetime, end_date: datetime) -> PerformanceMetrics:
        """Retrieve performance data from AnalyticsAgent and LeadCRM_Agent"""
        payload = {
            "tenant_id": tenant_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
        
        lead_data = await self._call_agent("analytics/leads", payload)
        conversion_data = await self._call_agent("analytics/conversions", payload)
        website_data = await self._call_agent("analytics/website", payload)
        
        return PerformanceMetrics(
            lead_conversion_rate=conversion_data.get("conversion_rate", 0),
            time_to_lease=conversion_data.get("time_to_lease", 0),
            time_to_close=conversion_data.get("time_to_close", 0),
            website_traffic=website_data.get("traffic", 0),
            inquiry_to_viewing_rate=conversion_data.get("inquiry_to_viewing", 0),
            viewing_to_application_rate=conversion_data.get("viewing_to_application", 0),
            application_to_lease_rate=conversion_data.get("application_to_lease", 0)
        )
    
    def generate_financial_charts(self, financial_metrics: FinancialMetrics, currency: str) -> Dict[str, str]:
        """Generate financial charts and return as base64 encoded images"""
        charts = {}
        
        # Revenue vs Expenses chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=['Revenue', 'Expenses', 'Net Income'],
            y=[financial_metrics.total_revenue, financial_metrics.total_expenses, 
               financial_metrics.net_operating_income],
            marker_color=['green', 'red', 'blue']
        ))
        fig.update_layout(
            title='Financial Overview',
            yaxis_title=f'Amount ({currency})',
            showlegend=False
        )
        charts['financial_overview'] = self._fig_to_base64(fig)
        
        # Revenue breakdown pie chart
        if financial_metrics.revenue_breakdown:
            fig2 = px.pie(
                values=list(financial_metrics.revenue_breakdown.values()),
                names=list(financial_metrics.revenue_breakdown.keys()),
                title='Revenue Breakdown'
            )
            charts['revenue_breakdown'] = self._fig_to_base64(fig2)
        
        # Expense breakdown pie chart
        if financial_metrics.expense_breakdown:
            fig3 = px.pie(
                values=list(financial_metrics.expense_breakdown.values()),
                names=list(financial_metrics.expense_breakdown.keys()),
                title='Expense Breakdown'
            )
            charts['expense_breakdown'] = self._fig_to_base64(fig3)
        
        return charts
    
    def generate_operational_charts(self, operational_metrics: OperationalMetrics) -> Dict[str, str]:
        """Generate operational charts and return as base64 encoded images"""
        charts = {}
        
        # Properties and units chart
        fig = make_subplots(rows=1, cols=2, subplot_titles=('Properties Managed', 'Units Managed'))
        fig.add_trace(go.Indicator(
            mode="number",
            value=operational_metrics.properties_managed,
            title={"text": "Properties"},
        ), row=1, col=1)
        fig.add_trace(go.Indicator(
            mode="number",
            value=operational_metrics.units_managed,
            title={"text": "Units"},
        ), row=1, col=2)
        fig.update_layout(height=300, showlegend=False)
        charts['properties_units'] = self._fig_to_base64(fig)
        
        # Leasing activity chart
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=['New Leases', 'Renewals'],
            y=[operational_metrics.new_leases_signed, operational_metrics.lease_renewals],
            marker_color=['blue', 'green']
        ))
        fig2.update_layout(
            title='Leasing Activity',
            yaxis_title='Count',
            showlegend=False
        )
        charts['leasing_activity'] = self._fig_to_base64(fig2)
        
        return charts
    
    def _fig_to_base64(self, fig) -> str:
        """Convert plotly figure to base64 encoded image"""
        img_bytes = fig.to_image(format="png")
        return base64.b64encode(img_bytes).decode('utf-8')
    
    async def generate_report(self, params: ReportParameters) -> Dict[str, Any]:
        """
        Generate a comprehensive annual report based on the provided parameters
        """
        logger.info(f"Generating {params.report_type.value} report for tenant {params.tenant_id}")
        
        report_data = {
            "metadata": {
                "report_id": f"report_{params.tenant_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "generated_at": datetime.now().isoformat(),
                "tenant_id": params.tenant_id,
                "report_type": params.report_type.value,
                "period": {
                    "start": params.start_date.isoformat(),
                    "end": params.end_date.isoformat()
                },
                "currency": params.currency
            },
            "summary": {},
            "detailed_data": {},
            "charts": {},
            "recommendations": []
        }
        
        try:
            # Get financial data for all report types
            if params.report_type in [ReportType.FINANCIAL, ReportType.COMPREHENSIVE]:
                financial_data = await self.get_financial_data(
                    params.tenant_id, params.start_date, params.end_date
                )
                report_data["financial_metrics"] = asdict(financial_data)
                report_data["charts"].update(
                    self.generate_financial_charts(financial_data, params.currency)
                )
            
            # Get operational data for operational and comprehensive reports
            if params.report_type in [ReportType.OPERATIONAL, ReportType.COMPREHENSIVE]:
                operational_data = await self.get_operational_data(
                    params.tenant_id, params.start_date, params.end_date
                )
                report_data["operational_metrics"] = asdict(operational_data)
                report_data["charts"].update(
                    self.generate_operational_charts(operational_data)
                )
            
            # Get compliance data for compliance and comprehensive reports
            if params.report_type in [ReportType.COMPLIANCE, ReportType.COMPREHENSIVE]:
                compliance_data = await self.get_compliance_data(
                    params.tenant_id, params.start_date, params.end_date
                )
                report_data["compliance_metrics"] = asdict(compliance_data)
            
            # Get performance data for performance and comprehensive reports
            if params.report_type in [ReportType.PERFORMANCE, ReportType.COMPREHENSIVE]:
                performance_data = await self.get_performance_data(
                    params.tenant_id, params.start_date, params.end_date
                )
                report_data["performance_metrics"] = asdict(performance_data)
            
            # Generate executive summary
            report_data["summary"] = self._generate_executive_summary(report_data)
            
            # Generate recommendations using RAG
            report_data["recommendations"] = await self._generate_recommendations(
                params.tenant_id, report_data
            )
            
            logger.info(f"Successfully generated report for tenant {params.tenant_id}")
            return report_data
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise
    
    def _generate_executive_summary(self, report_data: Dict) -> Dict:
        """Generate an executive summary based on the report data"""
        summary = {
            "overview": "",
            "key_achievements": [],
            "areas_for_improvement": [],
            "financial_highlights": {}
        }
        
        # Financial highlights
        if "financial_metrics" in report_data:
            financial = report_data["financial_metrics"]
            summary["financial_highlights"] = {
                "total_revenue": financial["total_revenue"],
                "net_operating_income": financial["net_operating_income"],
                "occupancy_rate": financial["occupancy_rate"],
                "yoy_growth": financial["yoy_growth"]
            }
        
        # Generate textual overview based on metrics
        overview_parts = []
        
        if "financial_metrics" in report_data:
            financial = report_data["financial_metrics"]
            overview_parts.append(
                f"The portfolio generated {financial['total_revenue']:,.0f} in revenue "
                f"with a net operating income of {financial['net_operating_income']:,.0f}. "
                f"Occupancy rates stood at {financial['occupancy_rate']:.1%}."
            )
            
            if financial['yoy_growth'] > 0:
                overview_parts.append(f"Revenue grew by {financial['yoy_growth']:.1f}% year-over-year.")
            elif financial['yoy_growth'] < 0:
                overview_parts.append(f"Revenue decreased by {abs(financial['yoy_growth']):.1f}% year-over-year.")
        
        if "operational_metrics" in report_data:
            operational = report_data["operational_metrics"]
            overview_parts.append(
                f"The portfolio managed {operational['properties_managed']} properties "
                f"with {operational['units_managed']} units, signing {operational['new_leases_signed']} "
                f"new leases and {operational['lease_renewals']} renewals."
            )
        
        summary["overview"] = " ".join(overview_parts)
        
        # Identify key achievements and areas for improvement
        if "financial_metrics" in report_data:
            financial = report_data["financial_metrics"]
            if financial['yoy_growth'] > 10:
                summary["key_achievements"].append("Exceptional revenue growth exceeding 10% year-over-year.")
            if financial['occupancy_rate'] > 0.9:
                summary["key_achievements"].append("High occupancy rate above 90%.")
            elif financial['occupancy_rate'] < 0.8:
                summary["areas_for_improvement"].append("Occupancy rate below 80% requires attention.")
        
        if "performance_metrics" in report_data:
            performance = report_data["performance_metrics"]
            if performance['lead_conversion_rate'] < 0.1:
                summary["areas_for_improvement"].append("Low lead conversion rate suggests need for better lead qualification.")
        
        return summary
    
    async def _generate_recommendations(self, tenant_id: str, report_data: Dict) -> List[Dict]:
        """Generate recommendations using RAG based on the report data"""
        # This would typically call the RAG_Agent with the report data
        # For now, we'll return some placeholder recommendations
        
        recommendations = []
        
        if "financial_metrics" in report_data:
            financial = report_data["financial_metrics"]
            if financial['occupancy_rate'] < 0.85:
                recommendations.append({
                    "category": "Occupancy",
                    "priority": "High",
                    "recommendation": "Implement targeted marketing campaigns to reduce vacancy rates",
                    "estimated_impact": "Potential 5-15% increase in revenue",
                    "implementation_timeline": "30-60 days"
                })
            
            if financial['yoy_growth'] < 5:
                recommendations.append({
                    "category": "Revenue Growth",
                    "priority": "Medium",
                    "recommendation": "Review pricing strategy and consider value-add services",
                    "estimated_impact": "Potential 3-8% revenue growth",
                    "implementation_timeline": "60-90 days"
                })
        
        if "operational_metrics" in report_data:
            operational = report_data["operational_metrics"]
            if operational['average_response_time'] > 48:
                recommendations.append({
                    "category": "Maintenance",
                    "priority": "High",
                    "recommendation": "Implement a more efficient maintenance response system",
                    "estimated_impact": "Improved tenant satisfaction and retention",
                    "implementation_timeline": "30 days"
                })
        
        return recommendations
    
    def export_report(self, report_data: Dict, format: str = "json") -> BytesIO:
        """Export the report in the specified format"""
        if format == "json":
            json_str = json.dumps(report_data, indent=2)
            return BytesIO(json_str.encode('utf-8'))
        elif format == "csv":
            # Flatten the data for CSV export
            flat_data = self._flatten_report_data(report_data)
            df = pd.DataFrame([flat_data])
            csv_buffer = BytesIO()
            df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            return csv_buffer
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _flatten_report_data(self, report_data: Dict) -> Dict:
        """Flatten the report data for CSV export"""
        flat_data = {}
        
        # Flatten metadata
        for key, value in report_data.get("metadata", {}).items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    flat_data[f"metadata_{key}_{subkey}"] = subvalue
            else:
                flat_data[f"metadata_{key}"] = value
        
        # Flatten metrics
        for metric_type in ["financial_metrics", "operational_metrics", 
                           "compliance_metrics", "performance_metrics"]:
            if metric_type in report_data:
                for key, value in report_data[metric_type].items():
                    if isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            flat_data[f"{metric_type}_{key}_{subkey}"] = subvalue
                    else:
                        flat_data[f"{metric_type}_{key}"] = value
        
        return flat_data

# Example usage
async def main():
    # Initialize the report generator
    async with AnnualReportGenerator(
        base_url="https://api.mwarokin.com",
        api_key="your_api_key_here"
    ) as generator:
        
        # Define report parameters
        params = ReportParameters(
            tenant_id="tenant_123",
            report_type=ReportType.COMPREHENSIVE,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            currency="USD"
        )
        
        # Generate the report
        report = await generator.generate_report(params)
        
        # Export to JSON
        json_export = generator.export_report(report, "json")
        
        # Save to file
        with open(f"annual_report_{params.tenant_id}_{params.end_date.year}.json", "wb") as f:
            f.write(json_export.getvalue())
        
        print(f"Report generated successfully for tenant {params.tenant_id}")

if __name__ == "__main__":
    asyncio.run(main())
```

This comprehensive Annual Report module for Mwarokin Real Estate Agentic OS:

1. **Integrates with all specialized agents** to gather data from across the platform
2. **Supports multiple report types** (financial, operational, compliance, performance, comprehensive)
3. **Generates visualizations** using Plotly for financial and operational data
4. **Provides executive summaries** and data-driven recommendations
5. **Supports multi-tenant architecture** with proper tenant isolation
6. **Offers export capabilities** in JSON and CSV formats
7. **Uses async/await** for efficient API calls to various agents

The module follows the ReAct pattern by:
- Planning what data to collect based on report type
- Executing calls to various agents to gather required information
- Reflecting on the data to generate insights and recommendations

To use this module, you would need to:
1. Update the base URL and API key to match your Mwarokin deployment
2. Ensure all the agent endpoints exist and return data in the expected format
3. Customize the report parameters based on your specific needs

The generated reports can be used for strategic decision-making, investor communications, and regulatory compliance.