```python
"""
Marketing Hub - Modern Python Code with Agentic UI Capabilities
Real functional code for managing marketing operations, integrations, and analytics.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Callable, Union
from enum import Enum
import json
import logging
from functools import wraps, reduce
from collections import defaultdict
import asyncio
from decimal import Decimal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====================================================
# DECORATORS & FUNCTIONAL HELPERS
# ====================================================

def log_operation(func: Callable) -> Callable:
    """Decorator to log operations with timestamps."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = datetime.now()
        logger.info(f"Starting {func.__name__} at {start}")
        result = func(*args, **kwargs)
        end = datetime.now()
        logger.info(f"Completed {func.__name__} in {(end - start).total_seconds():.2f}s")
        return result
    return wrapper

def validate_data(func: Callable) -> Callable:
    """Decorator to validate input data before processing."""
    @wraps(func)
    def wrapper(self, data: Dict, *args, **kwargs):
        if not data or not isinstance(data, dict):
            raise ValueError("Invalid data: must be a non-empty dictionary")
        return func(self, data, *args, **kwargs)
    return wrapper

def retry_on_failure(max_retries: int = 3):
    """Decorator to retry failed operations."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        raise
            return None
        return wrapper
    return decorator

# ====================================================
# ENUMS & CONSTANTS
# ====================================================

class ChannelType(Enum):
    FACEBOOK = "facebook_lead_ads"
    MAILCHIMP = "mailchimp"
    LEADCONNECTOR = "leadconnector"
    GOOGLE_ADS = "google_ads"
    ACTIVECAMPAIGN = "activecampaign"
    BREVO = "brevo"
    FACEBOOK_CONVERSIONS = "facebook_conversions"

class LeadStage(Enum):
    NEW = "new"
    QUALIFIED = "qualified"
    NURTURING = "nurturing"
    CONVERTED = "converted"
    LOST = "lost"

class IntegrationStatus(Enum):
    CONNECTED = "connected"
    AVAILABLE = "available"
    ERROR = "error"
    DISCONNECTED = "disconnected"

class Brand(Enum):
    MWAROKIN_ESTATES = "mwarokin_estates"
    SYLLOPAY = "syllopay"
    MALI_ACCESS_UNION = "mali_access_union"
    GRILL_MASTERS = "grill_masters"

# ====================================================
# DATA CLASSES
# ====================================================

@dataclass
class Lead:
    """Represents a lead in the marketing system."""
    id: str
    name: str
    email: str
    phone: str
    source: ChannelType
    stage: LeadStage
    brand: Brand
    created_at: datetime
    updated_at: datetime
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert lead to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "source": self.source.value,
            "stage": self.stage.value,
            "brand": self.brand.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "score": self.score,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Lead':
        """Create lead from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            email=data["email"],
            phone=data["phone"],
            source=ChannelType(data["source"]),
            stage=LeadStage(data["stage"]),
            brand=Brand(data["brand"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            score=data.get("score", 0.0),
            metadata=data.get("metadata", {})
        )

@dataclass
class Integration:
    """Represents a marketing integration."""
    id: str
    name: str
    channel: ChannelType
    status: IntegrationStatus
    brand: Brand
    metrics: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    connected_at: Optional[datetime] = None
    last_sync: Optional[datetime] = None

@dataclass
class Campaign:
    """Represents a marketing campaign."""
    id: str
    name: str
    brand: Brand
    channels: List[ChannelType]
    budget: float
    spent: float
    leads_generated: int
    conversions: int
    start_date: datetime
    end_date: Optional[datetime] = None
    active: bool = True

@dataclass
class AnalyticsMetric:
    """Represents an analytics metric with historical data."""
    name: str
    current_value: Union[int, float]
    historical_values: List[Union[int, float]]
    unit: str = ""
    trend: str = "stable"  # "up", "down", "stable"

# ====================================================
# CORE MARKETING SYSTEM
# ====================================================

class MarketingHub:
    """Core marketing system with agentic capabilities."""
    
    def __init__(self):
        self._leads: Dict[str, Lead] = {}
        self._integrations: Dict[str, Integration] = {}
        self._campaigns: Dict[str, Campaign] = {}
        self._pipeline_stages: Dict[LeadStage, List[str]] = defaultdict(list)
        self._analytics_cache: Dict[str, List[AnalyticsMetric]] = defaultdict(list)
        self._listeners: List[Callable] = []
        
    # ================================================
    # LEAD MANAGEMENT
    # ================================================
    
    @log_operation
    def create_lead(self, lead_data: Dict) -> Lead:
        """Create a new lead in the system."""
        lead = Lead(
            id=f"lead_{datetime.now().timestamp()}",
            name=lead_data["name"],
            email=lead_data["email"],
            phone=lead_data["phone"],
            source=ChannelType(lead_data["source"]),
            stage=LeadStage.NEW,
            brand=Brand(lead_data["brand"]),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            score=lead_data.get("score", 0.0),
            metadata=lead_data.get("metadata", {})
        )
        self._leads[lead.id] = lead
        self._pipeline_stages[lead.stage].append(lead.id)
        self._notify_listeners("lead_created", lead)
        return lead
    
    @validate_data
    def update_lead_stage(self, lead_id: str, new_stage: LeadStage) -> Lead:
        """Update a lead's stage in the pipeline."""
        lead = self._leads.get(lead_id)
        if not lead:
            raise KeyError(f"Lead {lead_id} not found")
        
        # Remove from old stage
        old_stage = lead.stage
        if lead_id in self._pipeline_stages[old_stage]:
            self._pipeline_stages[old_stage].remove(lead_id)
        
        # Add to new stage
        lead.stage = new_stage
        lead.updated_at = datetime.now()
        self._pipeline_stages[new_stage].append(lead_id)
        
        self._notify_listeners("lead_stage_changed", lead, old_stage, new_stage)
        return lead
    
    def get_leads_by_stage(self, stage: LeadStage) -> List[Lead]:
        """Get all leads at a specific stage."""
        lead_ids = self._pipeline_stages[stage]
        return [self._leads[lead_id] for lead_id in lead_ids if lead_id in self._leads]
    
    def get_leads_by_brand(self, brand: Brand) -> List[Lead]:
        """Get all leads for a specific brand."""
        return [lead for lead in self._leads.values() if lead.brand == brand]
    
    @log_operation
    def calculate_lead_score(self, lead: Lead) -> float:
        """Calculate lead score based on engagement and metadata."""
        score = 0.0
        
        # Base score from metadata
        score += lead.metadata.get("engagement_score", 0.0)
        
        # Bonus for multiple touchpoints
        if "touchpoints" in lead.metadata:
            touchpoints = lead.metadata["touchpoints"]
            score += min(len(touchpoints) * 5, 20)
        
        # Bonus for high-value actions
        if lead.metadata.get("high_value_action", False):
            score += 15
        
        # Time decay (newer leads get higher scores)
        days_old = (datetime.now() - lead.created_at).days
        score += max(0, 10 - days_old)
        
        return min(score, 100)
    
    # ================================================
    # INTEGRATION MANAGEMENT
    # ================================================
    
    def add_integration(self, integration_data: Dict) -> Integration:
        """Add a new integration to the hub."""
        integration = Integration(
            id=integration_data["id"],
            name=integration_data["name"],
            channel=ChannelType(integration_data["channel"]),
            status=IntegrationStatus(integration_data["status"]),
            brand=Brand(integration_data["brand"]),
            metrics=integration_data.get("metrics", {}),
            config=integration_data.get("config", {}),
            connected_at=datetime.now(),
            last_sync=datetime.now()
        )
        self._integrations[integration.id] = integration
        self._notify_listeners("integration_added", integration)
        return integration
    
    def update_integration_status(self, integration_id: str, status: IntegrationStatus) -> Integration:
        """Update the status of an integration."""
        integration = self._integrations.get(integration_id)
        if not integration:
            raise KeyError(f"Integration {integration_id} not found")
        
        integration.status = status
        integration.last_sync = datetime.now()
        return integration
    
    def get_active_integrations(self) -> List[Integration]:
        """Get all active (connected) integrations."""
        return [i for i in self._integrations.values() 
                if i.status == IntegrationStatus.CONNECTED]
    
    # ================================================
    # CAMPAIGN MANAGEMENT
    # ================================================
    
    def create_campaign(self, campaign_data: Dict) -> Campaign:
        """Create a new marketing campaign."""
        campaign = Campaign(
            id=campaign_data["id"],
            name=campaign_data["name"],
            brand=Brand(campaign_data["brand"]),
            channels=[ChannelType(c) for c in campaign_data["channels"]],
            budget=campaign_data["budget"],
            spent=0.0,
            leads_generated=0,
            conversions=0,
            start_date=datetime.fromisoformat(campaign_data["start_date"]),
            end_date=datetime.fromisoformat(campaign_data["end_date"]) if "end_date" in campaign_data else None,
            active=True
        )
        self._campaigns[campaign.id] = campaign
        return campaign
    
    def track_campaign_metrics(self, campaign_id: str, metrics: Dict) -> Campaign:
        """Track campaign performance metrics."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            raise KeyError(f"Campaign {campaign_id} not found")
        
        campaign.spent += metrics.get("spent", 0)
        campaign.leads_generated += metrics.get("leads_generated", 0)
        campaign.conversions += metrics.get("conversions", 0)
        
        return campaign
    
    def get_campaign_roi(self, campaign_id: str) -> float:
        """Calculate ROI for a campaign."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign or campaign.spent == 0:
            return 0.0
        
        # Assuming each conversion has a value of 1000 (could be configurable)
        conversion_value = 1000
        revenue = campaign.conversions * conversion_value
        roi = (revenue - campaign.spent) / campaign.spent * 100
        return roi
    
    # ================================================
    # ANALYTICS
    # ================================================
    
    def compute_blended_cpl(self, brand: Brand, period_days: int = 30) -> float:
        """Compute blended Cost Per Lead for a brand over a period."""
        leads = self.get_leads_by_brand(brand)
        recent_leads = [l for l in leads 
                       if (datetime.now() - l.created_at).days <= period_days]
        
        if not recent_leads:
            return 0.0
        
        # Sum all campaign spends for this brand
        total_spend = sum(c.spent for c in self._campaigns.values() 
                         if c.brand == brand and c.active)
        
        return total_spend / len(recent_leads) if recent_leads else 0.0
    
    def compute_conversion_rate(self, brand: Brand) -> float:
        """Compute conversion rate for a brand."""
        leads = self.get_leads_by_brand(brand)
        if not leads:
            return 0.0
        
        converted = [l for l in leads if l.stage == LeadStage.CONVERTED]
        return (len(converted) / len(leads)) * 100
    
    def get_channel_performance(self, brand: Brand) -> Dict[ChannelType, Dict]:
        """Get performance metrics by channel for a brand."""
        leads = self.get_leads_by_brand(brand)
        channel_metrics = defaultdict(lambda: {"leads": 0, "conversions": 0})
        
        for lead in leads:
            channel_metrics[lead.source]["leads"] += 1
            if lead.stage == LeadStage.CONVERTED:
                channel_metrics[lead.source]["conversions"] += 1
        
        # Calculate conversion rates
        for channel in channel_metrics:
            total = channel_metrics[channel]["leads"]
            conversions = channel_metrics[channel]["conversions"]
            channel_metrics[channel]["conversion_rate"] = (conversions / total * 100) if total > 0 else 0
        
        return dict(channel_metrics)
    
    @log_operation
    def generate_dashboard_data(self, brand: Brand) -> Dict:
        """Generate comprehensive dashboard data for a brand."""
        leads = self.get_leads_by_brand(brand)
        active_integrations = [i for i in self._integrations.values() 
                              if i.brand == brand and i.status == IntegrationStatus.CONNECTED]
        
        return {
            "brand": brand.value,
            "leads_this_month": len([l for l in leads if l.created_at.month == datetime.now().month]),
            "total_leads": len(leads),
            "blended_cpl": self.compute_blended_cpl(brand),
            "conversion_rate": self.compute_conversion_rate(brand),
            "ad_spend": sum(c.spent for c in self._campaigns.values() if c.brand == brand),
            "stage_distribution": {
                stage.value: len(self.get_leads_by_stage(stage))
                for stage in LeadStage
            },
            "channel_performance": self.get_channel_performance(brand),
            "integrations": [
                {
                    "name": i.name,
                    "status": i.status.value,
                    "metrics": i.metrics
                }
                for i in active_integrations
            ]
        }
    
    # ================================================
    # PIPELINE & WORKFLOW
    # ================================================
    
    @retry_on_failure(max_retries=3)
    def process_incoming_lead(self, lead_data: Dict) -> Lead:
        """Process an incoming lead through the entire pipeline."""
        # Create the lead
        lead = self.create_lead(lead_data)
        
        # Auto-qualify based on score
        score = self.calculate_lead_score(lead)
        if score > 70:
            self.update_lead_stage(lead.id, LeadStage.QUALIFIED)
        elif score > 40:
            self.update_lead_stage(lead.id, LeadStage.NURTURING)
        
        # Route to appropriate brand's workflow
        self._route_lead_to_workflow(lead)
        
        return lead
    
    def _route_lead_to_workflow(self, lead: Lead):
        """Route lead to appropriate brand workflow."""
        if lead.brand == Brand.MWAROKIN_ESTATES:
            self._mwarokin_workflow(lead)
        elif lead.brand == Brand.SYLLOPAY:
            self._syllopay_workflow(lead)
        elif lead.brand == Brand.MALI_ACCESS_UNION:
            self._mali_access_workflow(lead)
        elif lead.brand == Brand.GRILL_MASTERS:
            self._grill_masters_workflow(lead)
    
    def _mwarokin_workflow(self, lead: Lead):
        """Mwarokin Estates specific workflow."""
        logger.info(f"Processing Mwarokin Estates lead: {lead.name}")
        # Assign to appropriate agent based on location
        location = lead.metadata.get("location", "Nairobi")
        if location in ["Nairobi", "Diaspora"]:
            lead.metadata["assigned_agent"] = "Njeri"
        else:
            lead.metadata["assigned_agent"] = "Otieno"
    
    def _syllopay_workflow(self, lead: Lead):
        """SylloPay specific workflow."""
        logger.info(f"Processing Syllopay lead: {lead.name}")
        # Check if lead qualifies for Lipa Mdogo Mdogo
        if lead.score > 60:
            lead.metadata["lmm_eligible"] = True
    
    def _mali_access_workflow(self, lead: Lead):
        """Mali Access Union specific workflow."""
        logger.info(f"Processing Mali Access Union lead: {lead.name}")
        # Add to savings program flow
        lead.metadata["savings_program"] = "automatic"
    
    def _grill_masters_workflow(self, lead: Lead):
        """Grill Masters specific workflow."""
        logger.info(f"Processing Grill Masters lead: {lead.name}")
        # Send welcome offer
        lead.metadata["welcome_offer"] = "15% off first order"
    
    # ================================================
    # EVENT SYSTEM
    # ================================================
    
    def subscribe(self, callback: Callable) -> None:
        """Subscribe to system events."""
        self._listeners.append(callback)
    
    def unsubscribe(self, callback: Callable) -> None:
        """Unsubscribe from system events."""
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self, event_type: str, *args, **kwargs) -> None:
        """Notify all listeners of an event."""
        for listener in self._listeners:
            try:
                listener(event_type, *args, **kwargs)
            except Exception as e:
                logger.error(f"Listener error: {e}")
    
    # ================================================
    # DATA PERSISTENCE
    # ================================================
    
    def export_state(self) -> Dict:
        """Export the entire system state."""
        return {
            "leads": {lead_id: lead.to_dict() for lead_id, lead in self._leads.items()},
            "integrations": [
                {
                    "id": i.id,
                    "name": i.name,
                    "channel": i.channel.value,
                    "status": i.status.value,
                    "brand": i.brand.value,
                    "metrics": i.metrics,
                    "config": i.config
                }
                for i in self._integrations.values()
            ],
            "campaigns": [
                {
                    "id": c.id,
                    "name": c.name,
                    "brand": c.brand.value,
                    "channels": [ch.value for ch in c.channels],
                    "budget": c.budget,
                    "spent": c.spent,
                    "leads_generated": c.leads_generated,
                    "conversions": c.conversions,
                    "active": c.active
                }
                for c in self._campaigns.values()
            ]
        }
    
    def import_state(self, state: Dict) -> None:
        """Import system state."""
        # Clear existing data
        self._leads.clear()
        self._integrations.clear()
        self._campaigns.clear()
        self._pipeline_stages.clear()
        
        # Import leads
        for lead_id, lead_data in state.get("leads", {}).items():
            lead = Lead.from_dict(lead_data)
            self._leads[lead_id] = lead
            self._pipeline_stages[lead.stage].append(lead_id)
        
        # Import integrations
        for int_data in state.get("integrations", []):
            integration = Integration(
                id=int_data["id"],
                name=int_data["name"],
                channel=ChannelType(int_data["channel"]),
                status=IntegrationStatus(int_data["status"]),
                brand=Brand(int_data["brand"]),
                metrics=int_data["metrics"],
                config=int_data["config"]
            )
            self._integrations[integration.id] = integration
        
        # Import campaigns
        for camp_data in state.get("campaigns", []):
            campaign = Campaign(
                id=camp_data["id"],
                name=camp_data["name"],
                brand=Brand(camp_data["brand"]),
                channels=[ChannelType(ch) for ch in camp_data["channels"]],
                budget=camp_data["budget"],
                spent=camp_data["spent"],
                leads_generated=camp_data["leads_generated"],
                conversions=camp_data["conversions"],
                start_date=datetime.now(),
                active=camp_data["active"]
            )
            self._campaigns[campaign.id] = campaign

# ====================================================
# AGENTIC UI MANAGER
# ====================================================

class AgenticUIManager:
    """Manages agentic UI operations and state updates."""
    
    def __init__(self, marketing_hub: MarketingHub):
        self.hub = marketing_hub
        self.ui_state = {
            "sidebar": {"active": "Overview", "brands": []},
            "topbar": {"user": "Robin", "brand": "Mwarokin Estates"},
            "stats": {},
            "confluence": {},
            "integrations": [],
            "pipeline": {}
        }
        self._pending_updates = []
        
    def update_dashboard(self, brand: Brand) -> Dict:
        """Update the dashboard UI state for a brand."""
        dashboard_data = self.hub.generate_dashboard_data(brand)
        
        self.ui_state["stats"] = {
            "leads_this_month": dashboard_data["leads_this_month"],
            "blended_cpl": dashboard_data["blended_cpl"],
            "conversion_rate": dashboard_data["conversion_rate"],
            "ad_spend": dashboard_data["ad_spend"]
        }
        
        self.ui_state["confluence"] = {
            "unified_leads": dashboard_data["total_leads"],
            "channels": [
                {"name": channel.value, "lead_count": metrics["leads"]}
                for channel, metrics in dashboard_data["channel_performance"].items()
            ]
        }
        
        self.ui_state["integrations"] = dashboard_data["integrations"]
        self.ui_state["pipeline"] = dashboard_data["stage_distribution"]
        
        return self.ui_state
    
    def render_component(self, component: str, data: Dict) -> str:
        """Render a UI component with provided data."""
        if component == "stat_card":
            return self._render_stat_card(data)
        elif component == "integration_card":
            return self._render_integration_card(data)
        elif component == "pipeline_column":
            return self._render_pipeline_column(data)
        elif component == "feed_item":
            return self._render_feed_item(data)
        else:
            return f"<!-- Unknown component: {component} -->"
    
    def _render_stat_card(self, data: Dict) -> str:
        """Render a stat card component."""
        return f"""
        <div class="stat-card">
            <div class="lbl">{data['label']} <i class="fas {data['icon']}"></i></div>
            <div class="val">{data['value']}</div>
            <div class="delta {data['trend']}"><i class="fas fa-arrow-{data['trend']}"></i> {data['change']}</div>
        </div>
        """
    
    def _render_integration_card(self, data: Dict) -> str:
        """Render an integration card component."""
        return f"""
        <div class="int-card">
            <div class="int-top">
                <div class="int-logo" style="background:{data['color']};">
                    <i class="fab {data['icon']}"></i>
                </div>
                <div>
                    <div class="int-name">{data['name']}</div>
                    <div class="int-cat">{data['category']}</div>
                </div>
                <div class="int-status status-{data['status']}">{data['status'].capitalize()}</div>
            </div>
            <div class="int-desc">{data['description']}</div>
            <div class="int-metrics">
                {' '.join(f'<div><b>{m["value"]}</b>{m["label"]}</div>' for m in data['metrics'])}
            </div>
            <div class="int-actions">
                <div class="int-btn">Configure</div>
                {'<div class="int-btn">View Data</div>' if data['status'] == 'connected' else ''}
            </div>
        </div>
        """
    
    def _render_pipeline_column(self, data: Dict) -> str:
        """Render a pipeline column component."""
        leads_html = ''.join(
            f"""
            <div class="pipe-card">
                <div class="n">{lead['name']}</div>
                <div class="src"><i class="fas fa-{lead['source_icon']}"></i>{lead['source']}</div>
            </div>
            """
            for lead in data['leads']
        )
        return f"""
        <div>
            <div class="pipe-col-head">{data['stage']} <b>{data['count']}</b></div>
            {leads_html}
        </div>
        """
    
    def _render_feed_item(self, data: Dict) -> str:
        """Render a feed item component."""
        return f"""
        <div class="feed-item">
            <div class="feed-ic" style="background:{data['color']};">
                <i class="fas {data['icon']}"></i>
            </div>
            <div>
                <div class="feed-txt">{data['description']}</div>
                <div class="feed-time">{data['time']}</div>
            </div>
        </div>
        """
    
    def live_update(self, update_type: str, data: Dict) -> Dict:
        """Process a live update to the UI state."""
        if update_type == "new_lead":
            self._handle_new_lead_update(data)
        elif update_type == "stage_change":
            self._handle_stage_change_update(data)
        elif update_type == "metric_update":
            self._handle_metric_update(data)
        elif update_type == "integration_update":
            self._handle_integration_update(data)
        
        return self.ui_state
    
    def _handle_new_lead_update(self, data: Dict):
        """Handle new lead update."""
        feed_item = {
            "color": data.get("color", "var(--fb)"),
            "icon": data.get("icon", "fa-user-plus"),
            "description": f"<b>New lead</b> from {data['source']} — {data['name']}",
            "time": "Just now"
        }
        # Add to feed (keep last 5)
        if "feed" not in self.ui_state:
            self.ui_state["feed"] = []
        self.ui_state["feed"].insert(0, self._render_feed_item(feed_item))
        self.ui_state["feed"] = self.ui_state["feed"][:5]
    
    def _handle_stage_change_update(self, data: Dict):
        """Handle stage change update."""
        feed_item = {
            "color": data.get("color", "var(--lc)"),
            "icon": data.get("icon", "fa-diagram-project"),
            "description": f"<b>Lead moved</b> to {data['new_stage']} — {data['name']}",
            "time": "Just now"
        }
        if "feed" not in self.ui_state:
            self.ui_state["feed"] = []
        self.ui_state["feed"].insert(0, self._render_feed_item(feed_item))
        self.ui_state["feed"] = self.ui_state["feed"][:5]
    
    def _handle_metric_update(self, data: Dict):
        """Handle metric update."""
        if "stats" in self.ui_state and data["metric"] in self.ui_state["stats"]:
            self.ui_state["stats"][data["metric"]] = data["value"]
    
    def _handle_integration_update(self, data: Dict):
        """Handle integration status update."""
        for integration in self.ui_state["integrations"]:
            if integration["name"] == data["name"]:
                integration["status"] = data["status"]
                break

# ====================================================
# TEST DATA GENERATOR
# ====================================================

def generate_test_data():
    """Generate test data for the marketing system."""
    hub = MarketingHub()
    
    # Add some integrations
    hub.add_integration({
        "id": "int_fb_lead",
        "name": "Facebook Lead Ads",
        "channel": "facebook_lead_ads",
        "status": "connected",
        "brand": "mwarokin_estates",
        "metrics": {"leads_30d": 612, "avg_cpl": 72}
    })
    
    hub.add_integration({
        "id": "int_mailchimp",
        "name": "Mailchimp",
        "channel": "mailchimp",
        "status": "connected",
        "brand": "mwarokin_estates",
        "metrics": {"open_rate": 44.2, "live_flows": 9}
    })
    
    hub.add_integration({
        "id": "int_google",
        "name": "Google Ads",
        "channel": "google_ads",
        "status": "connected",
        "brand": "mwarokin_estates",
        "metrics": {"roas": 4.6, "spend_mtd": 61000}
    })
    
    # Add some campaigns
    hub.create_campaign({
        "id": "camp_estates_q3",
        "name": "Mwarokin Estates Q3 Campaign",
        "brand": "mwarokin_estates",
        "channels": ["facebook_lead_ads", "google_ads"],
        "budget": 500000,
        "start_date": "2026-07-01T00:00:00"
    })
    
    # Add some leads
    test_leads = [
        {
            "id": "lead_1",
            "name": "Wanjiru K.",
            "email": "wanjiru@example.com",
            "phone": "+254700000001",
            "source": "facebook_lead_ads",
            "stage": "new",
            "brand": "mwarokin_estates",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "score": 45,
            "metadata": {"location": "Nairobi"}
        },
        {
            "id": "lead_2",
            "name": "David N.",
            "email": "david@example.com",
            "phone": "+254700000002",
            "source": "leadconnector",
            "stage": "qualified",
            "brand": "mwarokin_estates",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "score": 78,
            "metadata": {"location": "Mombasa"}
        },
        {
            "id": "lead_3",
            "name": "Brian O.",
            "email": "brian@example.com",
            "phone": "+254700000003",
            "source": "facebook_lead_ads",
            "stage": "converted",
            "brand": "mwarokin_estates",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "score": 92,
            "metadata": {"location": "Nairobi", "high_value_action": True}
        }
    ]
    
    for lead_data in test_leads:
        hub.create_lead(lead_data)
    
    return hub

# ====================================================
# MAIN EXECUTION
# ====================================================

def main():
    """Main function to demonstrate the marketing system."""
    print("=" * 60)
    print("CONFLUENCE MARKETING HUB")
    print("=" * 60)
    
    # Initialize system
    hub = MarketingHub()
    ui_manager = AgenticUIManager(hub)
    
    # Generate test data
    hub = generate_test_data()
    ui_manager.hub = hub
    
    # Subscribe to events
    def event_listener(event_type, *args, **kwargs):
        print(f"[Event] {event_type}: {args}")
    
    hub.subscribe(event_listener)
    
    print("\n📊 DASHBOARD DATA")
    print("-" * 40)
    dashboard = ui_manager.update_dashboard(Brand.MWAROKIN_ESTATES)
    
    # Display stats
    print(f"Leads This Month: {dashboard['stats']['leads_this_month']}")
    print(f"Blended CPL: KSh {dashboard['stats']['blended_cpl']:.0f}")
    print(f"Conversion Rate: {dashboard['stats']['conversion_rate']:.1f}%")
    print(f"Ad Spend (MTD): KSh {dashboard['stats']['ad_spend']:,.0f}")
    
    # Display pipeline
    print("\n📋 PIPELINE DISTRIBUTION")
    print("-" * 40)
    for stage, count in dashboard['pipeline'].items():
        print(f"{stage.capitalize()}: {count}")
    
    # Display integrations
    print("\n🔌 INTEGRATIONS")
    print("-" * 40)
    for integration in dashboard['integrations']:
        print(f"{integration['name']}: {integration['status'].upper()}")
    
    # Simulate a new lead coming in
    print("\n🔄 PROCESSING NEW LEAD")
    print("-" * 40)
    new_lead = hub.process_incoming_lead({
        "name": "Grace W.",
        "email": "grace@example.com",
        "phone": "+254700000004",
        "source": "facebook_lead_ads",
        "brand": "mwarokin_estates",
        "metadata": {"location": "Nairobi"}
    })
    
    print(f"Created lead: {new_lead.name} (Score: {new_lead.score:.1f}, Stage: {new_lead.stage.value})")
    
    # Simulate UI update
    ui_manager.live_update("new_lead", {
        "source": "Facebook Lead Ads",
        "name": "Grace W.",
        "color": "var(--fb)",
        "icon": "fa-user-plus"
    })
    
    # Get channel performance
    print("\n📈 CHANNEL PERFORMANCE")
    print("-" * 40)
    performance = hub.get_channel_performance(Brand.MWAROKIN_ESTATES)
    for channel, metrics in performance.items():
        print(f"{channel.value.replace('_', ' ').title()}: {metrics['leads']} leads, {metrics['conversion_rate']:.1f}% CR")
    
    print("\n" + "=" * 60)
    print("✅ Marketing Hub operational")
    print("=" * 60)

if __name__ == "__main__":
    main()
```