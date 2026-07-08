import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import json
import logging
from dataclasses import dataclass, field
from functools import wraps
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MwarokinOS")

# Type aliases
TenantID = str
UserID = str
ListingID = str
AgentID = str

class ListingStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PENDING = "pending"
    SOLD = "sold"
    RENTED = "rented"
    EXPIRED = "expired"

class PropertyType(Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    LAND = "land"
    APARTMENT = "apartment"
    VILLA = "villa"
    OFFICE = "office"

class AgentType(Enum):
    LISTING = "listing_agent"
    VALUATION = "valuation_agent"
    PRICING = "pricing_agent"
    MATCHMAKING = "matchmaking_agent"
    LEAD_CRM = "lead_crm_agent"
    LEASE = "lease_agent"
    TRANSACTION = "transaction_agent"
    COMPLIANCE = "compliance_agent"
    WHITELABEL = "white_label_agent"
    RAG = "rag_agent"
    ANALYTICS = "analytics_agent"

@dataclass
class TenantConfig:
    """Configuration for a tenant"""
    tenant_id: TenantID
    name: str
    branding: Dict[str, Any]
    feature_flags: Dict[str, bool]
    locale: str = "en-US"
    currency: str = "USD"
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True

@dataclass
class User:
    """User model with role-based access"""
    user_id: UserID
    tenant_id: TenantID
    email: str
    roles: List[str]
    permissions: List[str] = field(default_factory=list)
    is_active: bool = True

@dataclass
class PropertyListing:
    """Property listing data structure"""
    listing_id: ListingID
    tenant_id: TenantID
    property_type: PropertyType
    status: ListingStatus
    address: Dict[str, Any]
    price: float
    currency: str
    features: Dict[str, Any]
    media: List[str]
    created_by: UserID
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValuationResult:
    """Valuation agent output"""
    range_low: float
    range_high: float
    confidence: float  # 0.0 to 1.0
    comp_ids: List[str]
    reasoning: str
    sources: List[str]
    generated_at: datetime = field(default_factory=datetime.now)

@dataclass
class MatchResult:
    """Matchmaking agent output"""
    listing_id: ListingID
    score: float  # 0.0 to 1.0
    explanation: str
    factors: Dict[str, float]

def tenant_required(func):
    """Decorator to ensure tenant_id is provided"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'tenant_id' not in kwargs or not kwargs['tenant_id']:
            raise ValueError("tenant_id is required")
        return func(*args, **kwargs)
    return wrapper

def role_required(required_roles: List[str]):
    """Decorator to check user roles"""
    def decorator(func):
        @wraps(func)
        def wrapper(user: User, *args, **kwargs):
            if not any(role in user.roles for role in required_roles):
                raise PermissionError(f"User lacks required roles: {required_roles}")
            return func(user, *args, **kwargs)
        return wrapper
    return decorator

class BaseAgent:
    """Base class for all agents"""
    def __init__(self, agent_id: AgentID, agent_type: AgentType):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.is_available = True
        
    async def initialize(self):
        """Initialize the agent"""
        logger.info(f"Initializing {self.agent_type.value} agent: {self.agent_id}")
        
    async def execute(self, task: Dict[str, Any], tenant_id: TenantID) -> Dict[str, Any]:
        """Execute a task - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement execute method")
    
    async def health_check(self) -> bool:
        """Check if agent is healthy"""
        return self.is_available

class ListingAgent(BaseAgent):
    """Handles property listing intake and validation"""
    def __init__(self, agent_id: AgentID):
        super().__init__(agent_id, AgentType.LISTING)
        self.geocoding_service = None  # Would be initialized with actual service
        
    async def initialize(self):
        await super().initialize()
        # Initialize geocoding and other services here
        logger.info(f"ListingAgent {self.agent_id} initialized")
    
    @tenant_required
    async def intake_listing(self, payload: Dict[str, Any], tenant_id: TenantID) -> Dict[str, Any]:
        """Process new property listing"""
        try:
            # Validate required fields
            required_fields = ['property_type', 'address', 'price', 'currency']
            for field in required_fields:
                if field not in payload:
                    return {"status": "error", "message": f"Missing required field: {field}"}
            
            # Generate listing ID
            listing_id = f"lst_{uuid.uuid4().hex[:12]}"
            
            # Normalize data
            normalized_data = self._normalize_listing_data(payload)
            
            # Validate data
            validation_result = self._validate_listing_data(normalized_data)
            
            if not validation_result["is_valid"]:
                return {
                    "status": "validation_failed", 
                    "warnings": validation_result["warnings"],
                    "normalized_fields": normalized_data
                }
            
            # Enrich with additional data
            enriched_data = await self._enrich_listing_data(normalized_data, tenant_id)
            
            # Create listing object
            listing = PropertyListing(
                listing_id=listing_id,
                tenant_id=tenant_id,
                property_type=PropertyType(payload['property_type']),
                status=ListingStatus.DRAFT,
                address=payload['address'],
                price=payload['price'],
                currency=payload['currency'],
                features=enriched_data.get('features', {}),
                media=payload.get('media', []),
                created_by=payload.get('created_by', 'system'),
                metadata=enriched_data
            )
            
            # Store listing (in a real implementation, this would be a database operation)
            logger.info(f"Created listing {listing_id} for tenant {tenant_id}")
            
            return {
                "status": "success",
                "listing_id": listing_id,
                "warnings": validation_result["warnings"],
                "normalized_fields": normalized_data,
                "media_report": self._generate_media_report(payload.get('media', []))
            }
            
        except Exception as e:
            logger.error(f"Error in listing intake: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _normalize_listing_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize listing data to standard format"""
        normalized = data.copy()
        
        # Standardize property type
        if 'property_type' in normalized:
            prop_type = normalized['property_type'].lower()
            if 'apartment' in prop_type:
                normalized['property_type'] = 'apartment'
            elif 'house' in prop_type or 'villa' in prop_type:
                normalized['property_type'] = 'villa'
            elif 'commercial' in prop_type or 'office' in prop_type:
                normalized['property_type'] = 'office'
            elif 'land' in prop_type:
                normalized['property_type'] = 'land'
            else:
                normalized['property_type'] = 'residential'
        
        # Standardize price format
        if 'price' in normalized and isinstance(normalized['price'], str):
            # Remove currency symbols and commas
            price_str = normalized['price'].replace('$', '').replace(',', '').strip()
            try:
                normalized['price'] = float(price_str)
            except ValueError:
                pass  # Keep as string if not convertible
                
        return normalized
    
    def _validate_listing_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate listing data and return warnings"""
        warnings = []
        is_valid = True
        
        # Price validation
        if 'price' in data:
            if not isinstance(data['price'], (int, float)) or data['price'] <= 0:
                warnings.append("Price should be a positive number")
                is_valid = False
                
        # Address validation
        if 'address' not in data or not data['address'].get('street'):
            warnings.append("Address is incomplete")
            is_valid = False
            
        return {"is_valid": is_valid, "warnings": warnings}
    
    async def _enrich_listing_data(self, data: Dict[str, Any], tenant_id: TenantID) -> Dict[str, Any]:
        """Enrich listing data with external information"""
        enriched = {}
        
        # In a real implementation, this would call geocoding, walkscore, etc.
        try:
            # Simulate geocoding
            if 'address' in data:
                enriched['geocode'] = {
                    "lat": 40.7128,  # Example coordinates
                    "lng": -74.0060,
                    "accuracy": "high"
                }
                
            # Simulate walkscore
            enriched['walkscore'] = {
                "score": 75,
                "description": "Very Walkable"
            }
            
            # Simulate school data
            enriched['schools'] = [
                {"name": "Local Elementary", "distance": "0.5 miles", "rating": 8},
                {"name": "Local High School", "distance": "1.2 miles", "rating": 7}
            ]
            
        except Exception as e:
            logger.warning(f"Enrichment failed: {str(e)}")
            
        return enriched
    
    def _generate_media_report(self, media_list: List[str]) -> Dict[str, Any]:
        """Generate a report on listing media"""
        # In a real implementation, this would analyze images
        return {
            "total_media": len(media_list),
            "quality_check": "pending",
            "recommendations": ["Add more interior photos" if len(media_list) < 3 else "Sufficient media"]
        }

class ValuationAgent(BaseAgent):
    """Handles property valuation using CMA/AVM approach"""
    def __init__(self, agent_id: AgentID):
        super().__init__(agent_id, AgentType.VALUATION)
        self.comps_db = {}  # In real implementation, this would be a proper database
        
    async def initialize(self):
        await super().initialize()
        # Load comps data or connect to services
        logger.info(f"ValuationAgent {self.agent_id} initialized")
    
    @tenant_required
    async def request_valuation(self, listing_id: Optional[str] = None, 
                              address: Optional[Dict[str, Any]] = None, 
                              tenant_id: TenantID = None) -> ValuationResult:
        """Generate property valuation"""
        try:
            # In a real implementation, this would fetch the listing or property details
            # For now, we'll simulate the process
            
            # Get comparable properties (in real implementation, from database)
            comps = self._find_comparable_properties(listing_id, address, tenant_id)
            
            # Calculate valuation range
            valuation = self._calculate_valuation(comps)
            
            # Generate reasoning
            reasoning = self._generate_valuation_reasoning(valuation, comps)
            
            return ValuationResult(
                range_low=valuation['low'],
                range_high=valuation['high'],
                confidence=valuation['confidence'],
                comp_ids=[comp.get('id', '') for comp in comps],
                reasoning=reasoning,
                sources=["internal_comps_db", "market_trends"]
            )
            
        except Exception as e:
            logger.error(f"Valuation error: {str(e)}")
            # Return a conservative estimate with low confidence
            return ValuationResult(
                range_low=0,
                range_high=0,
                confidence=0.1,
                comp_ids=[],
                reasoning=f"Valuation failed: {str(e)}",
                sources=[]
            )
    
    def _find_comparable_properties(self, listing_id: Optional[str], 
                                  address: Optional[Dict[str, Any]], 
                                  tenant_id: TenantID) -> List[Dict[str, Any]]:
        """Find comparable properties for valuation"""
        # In a real implementation, this would query a database
        # For simulation, return some example comps
        return [
            {
                "id": "comp_1",
                "price": 250000,
                "sqft": 1500,
                "bedrooms": 3,
                "bathrooms": 2,
                "distance": 0.5,  # miles
                "sold_date": "2023-06-15"
            },
            {
                "id": "comp_2",
                "price": 275000,
                "sqft": 1600,
                "bedrooms": 3,
                "bathrooms": 2.5,
                "distance": 0.3,
                "sold_date": "2023-07-20"
            },
            {
                "id": "comp_3",
                "price": 240000,
                "sqft": 1450,
                "bedrooms": 3,
                "bathrooms": 1.5,
                "distance": 0.7,
                "sold_date": "2023-05-10"
            }
        ]
    
    def _calculate_valuation(self, comps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate valuation based on comparables"""
        if not comps:
            return {"low": 0, "high": 0, "confidence": 0.1}
            
        prices = [comp['price'] for comp in comps]
        avg_price = sum(prices) / len(prices)
        
        # Simple adjustment based on comp quality
        # In real implementation, this would be more sophisticated
        confidence = min(0.95, 0.5 + (len(comps) * 0.15))
        
        # Calculate range based on standard deviation
        if len(prices) > 1:
            variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
            std_dev = variance ** 0.5
            low = avg_price - std_dev
            high = avg_price + std_dev
        else:
            low = avg_price * 0.9
            high = avg_price * 1.1
            
        return {"low": low, "high": high, "confidence": confidence}
    
    def _generate_valuation_reasoning(self, valuation: Dict[str, Any], 
                                    comps: List[Dict[str, Any]]) -> str:
        """Generate human-readable reasoning for valuation"""
        comp_count = len(comps)
        confidence_percent = valuation['confidence'] * 100
        
        reasoning = f"Valuation based on {comp_count} comparable properties. "
        reasoning += f"Price range: ${valuation['low']:,.0f} - ${valuation['high']:,.0f} "
        reasoning += f"with {confidence_percent:.1f}% confidence. "
        
        if comp_count > 0:
            avg_price = sum(comp['price'] for comp in comps) / comp_count
            reasoning += f"Average comparable price: ${avg_price:,.0f}. "
            
        if valuation['confidence'] < 0.7:
            reasoning += "Lower confidence due to limited comparable data. "
            
        return reasoning

class MatchmakingAgent(BaseAgent):
    """Matches buyers/tenants with properties"""
    def __init__(self, agent_id: AgentID):
        super().__init__(agent_id, AgentType.MATCHMAKING)
        self.profile_embeddings = {}  # In real implementation, use proper vector database
    
    @tenant_required
    async def find_matches(self, profile: Dict[str, Any], tenant_id: TenantID) -> List[MatchResult]:
        """Find property matches for a user profile"""
        try:
            # In a real implementation, this would:
            # 1. Generate embedding for the profile
            # 2. Query similar listings from vector database
            # 3. Apply business rules
            # 4. Rank results
            
            # For simulation, return some example matches
            mock_listings = [
                {
                    "listing_id": "lst_abc123",
                    "score": 0.92,
                    "explanation": "Excellent match based on budget, location preferences, and desired amenities",
                    "factors": {
                        "budget": 0.95,
                        "location": 0.88,
                        "amenities": 0.91,
                        "property_type": 1.0
                    }
                },
                {
                    "listing_id": "lst_def456",
                    "score": 0.78,
                    "explanation": "Good match with slightly higher price but better location",
                    "factors": {
                        "budget": 0.65,
                        "location": 0.95,
                        "amenities": 0.82,
                        "property_type": 0.9
                    }
                }
            ]
            
            return [
                MatchResult(
                    listing_id=match["listing_id"],
                    score=match["score"],
                    explanation=match["explanation"],
                    factors=match["factors"]
                ) for match in mock_listings
            ]
            
        except Exception as e:
            logger.error(f"Matchmaking error: {str(e)}")
            return []

class MwarokinOrchestrator:
    """Main orchestrator for the Mwarokin Real Estate Agentic OS"""
    def __init__(self):
        self.agents: Dict[AgentType, BaseAgent] = {}
        self.tenants: Dict[TenantID, TenantConfig] = {}
        self.users: Dict[UserID, User] = {}
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize the orchestrator and all agents"""
        if self.is_initialized:
            return
            
        logger.info("Initializing Mwarokin Orchestrator")
        
        # Initialize agents
        self.agents[AgentType.LISTING] = ListingAgent("listing_agent_001")
        self.agents[AgentType.VALUATION] = ValuationAgent("valuation_agent_001")
        self.agents[AgentType.MATCHMAKING] = MatchmakingAgent("matchmaking_agent_001")
        
        # Initialize all agents
        for agent in self.agents.values():
            await agent.initialize()
            
        self.is_initialized = True
        logger.info("Mwarokin Orchestrator initialized successfully")
    
    def register_tenant(self, tenant_config: TenantConfig):
        """Register a new tenant"""
        self.tenants[tenant_config.tenant_id] = tenant_config
        logger.info(f"Registered tenant: {tenant_config.name} ({tenant_config.tenant_id})")
    
    def register_user(self, user: User):
        """Register a new user"""
        # Verify tenant exists
        if user.tenant_id not in self.tenants:
            raise ValueError(f"Tenant {user.tenant_id} does not exist")
            
        self.users[user.user_id] = user
        logger.info(f"Registered user: {user.email} for tenant {user.tenant_id}")
    
    @role_required(["admin", "agent"])
    async def process_listing_intake(self, user: User, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process a new property listing"""
        if not self.is_initialized:
            await self.initialize()
            
        listing_agent = self.agents[AgentType.LISTING]
        result = await listing_agent.intake_listing(payload, user.tenant_id)
        
        # If listing is valid, trigger valuation
        if result.get("status") == "success":
            valuation_agent = self.agents[AgentType.VALUATION]
            valuation = await valuation_agent.request_valuation(
                listing_id=result["listing_id"], 
                tenant_id=user.tenant_id
            )
            
            result["valuation"] = {
                "range_low": valuation.range_low,
                "range_high": valuation.range_high,
                "confidence": valuation.confidence
            }
        
        return result
    
    @role_required(["admin", "agent", "user"])
    async def get_property_valuation(self, user: User, listing_id: Optional[str] = None, 
                                   address: Optional[Dict[str, Any]] = None) -> ValuationResult:
        """Get valuation for a property"""
        if not self.is_initialized:
            await self.initialize()
            
        valuation_agent = self.agents[AgentType.VALUATION]
        return await valuation_agent.request_valuation(listing_id, address, user.tenant_id)
    
    @role_required(["admin", "agent", "user"])
    async def find_property_matches(self, user: User, profile: Dict[str, Any]) -> List[MatchResult]:
        """Find property matches for a user profile"""
        if not self.is_initialized:
            await self.initialize()
            
        matchmaking_agent = self.agents[AgentType.MATCHMAKING]
        return await matchmaking_agent.find_matches(profile, user.tenant_id)
    
    async def health_check(self) -> Dict[AgentType, bool]:
        """Check health of all agents"""
        results = {}
        for agent_type, agent in self.agents.items():
            results[agent_type] = await agent.health_check()
        return results

# Example usage
async def main():
    """Example demonstration of the Mwarokin system"""
    # Create orchestrator
    orchestrator = MwarokinOrchestrator()
    
    # Create a tenant
    tenant_config = TenantConfig(
        tenant_id="tenant_001",
        name="Premium Realty Group",
        branding={
            "logo": "premium-logo.png",
            "primary_color": "#3498db",
            "secondary_color": "#2ecc71"
        },
        feature_flags={
            "advanced_analytics": True,
            "multilingual_support": True,
            "ai_pricing": True
        },
        locale="en-US",
        currency="USD"
    )
    
    # Register tenant
    orchestrator.register_tenant(tenant_config)
    
    # Create a user
    user = User(
        user_id="user_001",
        tenant_id="tenant_001",
        email="agent@premiumrealty.com",
        roles=["admin", "agent"]
    )
    
    # Register user
    orchestrator.register_user(user)
    
    # Initialize the system
    await orchestrator.initialize()
    
    # Example: Process a new listing
    listing_payload = {
        "property_type": "apartment",
        "address": {
            "street": "123 Main St",
            "city": "New York",
            "state": "NY",
            "zipcode": "10001",
            "country": "USA"
        },
        "price": 350000,
        "currency": "USD",
        "bedrooms": 2,
        "bathrooms": 1,
        "sqft": 950,
        "media": ["img1.jpg", "img2.jpg"],
        "created_by": "user_001"
    }
    
    print("Processing new listing...")
    listing_result = await orchestrator.process_listing_intake(user, listing_payload)
    print(f"Listing result: {json.dumps(listing_result, indent=2)}")
    
    # Example: Get valuation
    print("\nGetting valuation...")
    valuation = await orchestrator.get_property_valuation(user, listing_id=listing_result.get("listing_id"))
    print(f"Valuation range: ${valuation.range_low:,.0f} - ${valuation.range_high:,.0f}")
    print(f"Confidence: {valuation.confidence:.0%}")
    print(f"Reasoning: {valuation.reasoning}")
    
    # Example: Find matches
    print("\nFinding property matches...")
    user_profile = {
        "budget": 300000,
        "preferred_locations": ["New York", "Brooklyn"],
        "property_types": ["apartment", "condo"],
        "bedrooms": 2,
        "bathrooms": 1,
        "amenities": ["laundry", "parking", "pet_friendly"]
    }
    
    matches = await orchestrator.find_property_matches(user, user_profile)
    for match in matches:
        print(f"Match: {match.listing_id} (Score: {match.score:.2f})")
        print(f"Explanation: {match.explanation}")
    
    # Health check
    print("\nSystem health check:")
    health = await orchestrator.health_check()
    for agent_type, status in health.items():
        print(f"{agent_type.value}: {'Healthy' if status else 'Unhealthy'}")

if __name__ == "__main__":
    asyncio.run(main())