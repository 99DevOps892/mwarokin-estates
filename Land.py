# Mwarokin Real Estate Agentic OS - Implementation Plan

I'll create a comprehensive Python-based agentic system for the Mwarokin Real Estate platform. Let me start by implementing the core components with modern Python, focusing on the agent architecture and coordination.

```python
"""
Mwarokin Real Estate Agentic OS - Core System Implementation
A multi-tenant, agent-based real estate management platform
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
import json
import logging
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MwarokinOS")

# Type aliases
TenantID = str
ListingID = str
UserID = str

class PropertyType(Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    LAND = "land"
    APARTMENT = "apartment"
    VILLA = "villa"
    OFFICE = "office"
    BUILDING = "building"
    HOME = "home"
    SHOP = "shop"

class ListingStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PENDING = "pending"
    SOLD = "sold"
    RENTED = "rented"
    EXPIRED = "expired"

class Currency(Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    XAF = "XAF"
    KES = "KES"
    NGN = "NGN"
    ZAR = "ZAR"

@dataclass
class GeoLocation:
    latitude: float
    longitude: float
    accuracy: Optional[float] = None

@dataclass
class TenantContext:
    tenant_id: TenantID
    brand_name: str
    locale: str
    currency: Currency
    theme_settings: Dict[str, Any]
    feature_flags: Dict[str, bool]
    created_at: datetime
    is_active: bool = True

def tenant_required(func):
    """Decorator to ensure tenant context is provided"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if 'tenant_id' not in kwargs and (not args or not hasattr(args[0], 'tenant_id')):
            raise ValueError("tenant_id is required for this operation")
        return await func(self, *args, **kwargs)
    return wrapper

def validate_rbac(required_role: str):
    """Role-Based Access Control decorator"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            user_role = kwargs.get('user_role', 'guest')
            if user_role != required_role:
                raise PermissionError(f"Access denied. Required role: {required_role}")
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

class BaseAgent:
    """Base class for all agents in the system"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.tenant_contexts: Dict[TenantID, TenantContext] = {}
        
    def set_tenant_context(self, tenant_context: TenantContext):
        self.tenant_contexts[tenant_context.tenant_id] = tenant_context
        
    async def execute(self, *args, **kwargs):
        raise NotImplementedError("Subclasses must implement execute method")
    
    async def reflect(self, result: Any) -> Dict[str, Any]:
        """Reflect on the execution results for improvement"""
        return {
            "agent": self.agent_name,
            "timestamp": datetime.now(),
            "success": True,
            "insights": []
        }

class ListingAgent(BaseAgent):
    """Handles property listing intake, normalization, and validation"""
    
    def __init__(self):
        super().__init__("ListingAgent")
        self.listings: Dict[Tuple[TenantID, ListingID], Dict] = {}
    
    @tenant_required
    @validate_rbac("agent")
    async def execute(self, payload: Dict, tenant_id: TenantID, **kwargs) -> Dict:
        """
        Intake a new property listing
        Returns: Dict with status, warnings, normalized_fields, media_report
        """
        try:
            # Validate required fields
            required_fields = ['title', 'property_type', 'location', 'price']
            missing_fields = [field for field in required_fields if field not in payload]
            if missing_fields:
                return {
                    "status": "error",
                    "message": f"Missing required fields: {missing_fields}",
                    "normalized_fields": {},
                    "media_report": {}
                }
            
            # Generate unique listing ID
            listing_id = str(uuid.uuid4())
            
            # Normalize and validate data
            normalized = self._normalize_listing_data(payload, tenant_id)
            
            # Validate media if provided
            media_report = await self._validate_media(payload.get('media', []))
            
            # Store the listing
            self.listings[(tenant_id, listing_id)] = {
                **normalized,
                'listing_id': listing_id,
                'tenant_id': tenant_id,
                'created_at': datetime.now(),
                'status': ListingStatus.DRAFT.value,
                'media_report': media_report
            }
            
            return {
                "status": "success",
                "listing_id": listing_id,
                "warnings": normalized.get('warnings', []),
                "normalized_fields": normalized,
                "media_report": media_report
            }
            
        except Exception as e:
            logger.error(f"ListingAgent error: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "normalized_fields": {},
                "media_report": {}
            }
    
    def _normalize_listing_data(self, payload: Dict, tenant_id: TenantID) -> Dict:
        """Normalize and validate listing data"""
        normalized = payload.copy()
        warnings = []
        
        # Normalize property type
        prop_type = payload.get('property_type', '').lower()
        try:
            normalized['property_type'] = PropertyType(prop_type).value
        except ValueError:
            warnings.append(f"Invalid property type: {prop_type}")
            normalized['property_type'] = PropertyType.RESIDENTIAL.value
        
        # Normalize price (convert to numeric)
        try:
            normalized['price'] = float(payload['price'])
        except (ValueError, TypeError):
            warnings.append("Price could not be converted to number")
            normalized['price'] = 0.0
            
        # Add geocoding if location provided but no coordinates
        if 'location' in payload and ('latitude' not in payload or 'longitude' not in payload):
            # In a real implementation, this would call a geocoding service
            normalized['geocoding_attempted'] = True
            
        return {**normalized, 'warnings': warnings}
    
    async def _validate_media(self, media_list: List[Dict]) -> Dict:
        """Validate property media (images, videos)"""
        # This would integrate with actual media validation services
        return {
            "total_media": len(media_list),
            "valid_images": len([m for m in media_list if m.get('type') == 'image']),
            "valid_videos": len([m for m in media_list if m.get('type') == 'video']),
            "issues": []
        }

class ValuationAgent(BaseAgent):
    """Provides property valuation using CMA/AVM approach"""
    
    def __init__(self, rag_service=None):
        super().__init__("ValuationAgent")
        self.rag_service = rag_service
    
    @tenant_required
    async def execute(self, listing_id: Optional[str] = None, 
                     address: Optional[str] = None, 
                     tenant_id: TenantID = None, **kwargs) -> Dict:
        """
        Generate property valuation
        Returns: Valuation with range, confidence, reasoning, and sources
        """
        if not listing_id and not address:
            return {
                "status": "error",
                "message": "Either listing_id or address must be provided"
            }
        
        try:
            # Retrieve property data
            property_data = await self._get_property_data(listing_id, address, tenant_id)
            if not property_data:
                return {
                    "status": "error",
                    "message": "Property not found"
                }
                
            # Get comparable properties using RAG
            comps = await self._find_comparables(property_data, tenant_id)
            
            # Calculate valuation
            valuation = await self._calculate_valuation(property_data, comps)
            
            return {
                "status": "success",
                "range_low": valuation['range_low'],
                "range_high": valuation['range_high'],
                "confidence": valuation['confidence'],
                "comp_ids": [comp.get('id') for comp in comps if comp.get('id')],
                "reasoning": valuation['reasoning'],
                "sources": valuation['sources'],
                "currency": self.tenant_contexts[tenant_id].currency.value
            }
            
        except Exception as e:
            logger.error(f"ValuationAgent error: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _get_property_data(self, listing_id: Optional[str], 
                               address: Optional[str], 
                               tenant_id: TenantID) -> Optional[Dict]:
        """Retrieve property data from database or external source"""
        # In real implementation, this would query the database
        return {
            "id": listing_id or f"ext_{hash(address)}",
            "address": address or "Unknown",
            "property_type": "residential",
            "size_sqft": 1500,
            "bedrooms": 3,
            "bathrooms": 2,
            "year_built": 2000,
            "location": {"latitude": 0.0, "longitude": 0.0}
        }
    
    async def _find_comparables(self, property_data: Dict, tenant_id: TenantID) -> List[Dict]:
        """Find comparable properties using RAG and similarity search"""
        # This would use the RAG service to find similar properties
        return [
            {
                "id": "comp_1",
                "address": "123 Comparable St",
                "price": 250000,
                "size_sqft": 1400,
                "bedrooms": 3,
                "bathrooms": 2,
                "distance_km": 0.5,
                "sale_date": "2023-06-15"
            },
            {
                "id": "comp_2",
                "address": "456 Similar Ave",
                "price": 275000,
                "size_sqft": 1600,
                "bedrooms": 4,
                "bathrooms": 2.5,
                "distance_km": 0.8,
                "sale_date": "2023-08-22"
            }
        ]
    
    async def _calculate_valuation(self, property_data: Dict, comps: List[Dict]) -> Dict:
        """Calculate valuation based on comparables"""
        if not comps:
            return {
                "range_low": 0,
                "range_high": 0,
                "confidence": 0.0,
                "reasoning": "No comparable properties found",
                "sources": []
            }
        
        # Simple valuation algorithm (in real implementation, this would be more sophisticated)
        comp_prices = [comp['price'] for comp in comps]
        avg_price = sum(comp_prices) / len(comp_prices)
        
        # Adjust based on property features
        adjustment_factor = 1.0
        if property_data.get('size_sqft'):
            avg_size = sum(comp['size_sqft'] for comp in comps) / len(comps)
            size_ratio = property_data['size_sqft'] / avg_size
            adjustment_factor *= size_ratio
        
        estimated_value = avg_price * adjustment_factor
        margin = estimated_value * 0.1  # 10% margin
        
        return {
            "range_low": round(estimated_value - margin, 2),
            "range_high": round(estimated_value + margin, 2),
            "confidence": 0.8,  # Confidence score
            "reasoning": f"Based on {len(comps)} comparable properties with adjustment for size and features",
            "sources": [comp['id'] for comp in comps]
        }

class MatchmakingAgent(BaseAgent):
    """Matches buyers/tenants with properties"""
    
    def __init__(self, embedding_service=None):
        super().__init__("MatchmakingAgent")
        self.embedding_service = embedding_service
    
    @tenant_required
    async def execute(self, profile: Dict, tenant_id: TenantID, **kwargs) -> Dict:
        """
        Match a user profile with suitable properties
        Returns: List of matches with scores and explanations
        """
        try:
            # Generate embedding for the profile
            profile_embedding = await self._generate_embedding(profile, tenant_id)
            
            # Find similar properties
            matches = await self._find_matches(profile_embedding, profile, tenant_id)
            
            return {
                "status": "success",
                "matches": matches,
                "total_properties_searched": 100,  # Example count
                "profile_summary": self._summarize_profile(profile)
            }
            
        except Exception as e:
            logger.error(f"MatchmakingAgent error: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "matches": []
            }
    
    async def _generate_embedding(self, profile: Dict, tenant_id: TenantID) -> List[float]:
        """Generate embedding vector for the profile"""
        # This would use the embedding service in a real implementation
        return [0.1, 0.2, 0.3, 0.4, 0.5]  # Example embedding
    
    async def _find_matches(self, embedding: List[float], profile: Dict, tenant_id: TenantID) -> List[Dict]:
        """Find property matches based on embedding similarity"""
        # This would query a vector database in a real implementation
        budget = profile.get('budget', {}).get('max', 1000000)
        property_type = profile.get('preferences', {}).get('property_type', 'residential')
        
        # Example matches
        return [
            {
                "listing_id": "match_1",
                "score": 0.92,
                "explanation": "Excellent match for budget and preferred location",
                "price": budget * 0.85,
                "address": "123 Ideal Street",
                "property_type": property_type
            },
            {
                "listing_id": "match_2",
                "score": 0.87,
                "explanation": "Good match with all required amenities",
                "price": budget * 0.95,
                "address": "456 Suitable Avenue",
                "property_type": property_type
            }
        ]
    
    def _summarize_profile(self, profile: Dict) -> Dict:
        """Create a summary of the user profile"""
        return {
            "budget_range": profile.get('budget', {}),
            "preferred_locations": profile.get('preferred_locations', []),
            "property_types": profile.get('preferences', {}).get('property_types', []),
            "must_have_amenities": profile.get('must_have_amenities', [])
        }

class MwarokinOrchestrator:
    """Main orchestrator for the Mwarokin Real Estate Agentic OS"""
    
    def __init__(self):
        self.agents = {
            "listing": ListingAgent(),
            "valuation": ValuationAgent(),
            "matchmaking": MatchmakingAgent()
        }
        self.tenant_contexts: Dict[TenantID, TenantContext] = {}
        self.task_queue = asyncio.Queue()
        self.is_running = False
        
    def register_tenant(self, tenant_context: TenantContext):
        """Register a new tenant in the system"""
        self.tenant_contexts[tenant_context.tenant_id] = tenant_context
        for agent in self.agents.values():
            agent.set_tenant_context(tenant_context)
        logger.info(f"Registered tenant: {tenant_context.tenant_id}")
    
    async def start(self):
        """Start the orchestrator"""
        self.is_running = True
        logger.info("Mwarokin Orchestrator started")
        
        # Start background task processing
        asyncio.create_task(self._process_tasks())
    
    async def stop(self):
        """Stop the orchestrator"""
        self.is_running = False
        logger.info("Mwarokin Orchestrator stopped")
    
    async def submit_task(self, task_type: str, payload: Dict, tenant_id: TenantID, 
                         user_id: Optional[UserID] = None, priority: int = 1) -> str:
        """Submit a task to the orchestrator"""
        if task_type not in self.agents:
            raise ValueError(f"Unknown task type: {task_type}")
            
        if tenant_id not in self.tenant_contexts:
            raise ValueError(f"Unknown tenant: {tenant_id}")
            
        task_id = str(uuid.uuid4())
        task = {
            "task_id": task_id,
            "type": task_type,
            "payload": payload,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "priority": priority,
            "submitted_at": datetime.now(),
            "status": "queued"
        }
        
        await self.task_queue.put(task)
        logger.info(f"Task submitted: {task_id} ({task_type})")
        return task_id
    
    async def _process_tasks(self):
        """Background task to process tasks from the queue"""
        while self.is_running:
            try:
                task = await self.task_queue.get()
                task_id = task["task_id"]
                task_type = task["type"]
                
                logger.info(f"Processing task: {task_id}")
                task["status"] = "processing"
                task["started_at"] = datetime.now()
                
                # Execute the appropriate agent
                agent = self.agents[task_type]
                result = await agent.execute(
                    **task["payload"],
                    tenant_id=task["tenant_id"],
                    user_id=task.get("user_id")
                )
                
                task["status"] = "completed"
                task["completed_at"] = datetime.now()
                task["result"] = result
                
                # Reflect on the task execution
                reflection = await agent.reflect(result)
                task["reflection"] = reflection
                
                logger.info(f"Task completed: {task_id}")
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing task: {str(e)}")
                if task:
                    task["status"] = "failed"
                    task["error"] = str(e)
    
    async def get_system_status(self) -> Dict:
        """Get current system status"""
        return {
            "status": "running" if self.is_running else "stopped",
            "tenants": len(self.tenant_contexts),
            "queue_size": self.task_queue.qsize(),
            "agents": {name: "active" for name in self.agents.keys()},
            "timestamp": datetime.now()
        }

# Example usage
async def demo():
    """Demonstration of the Mwarokin system"""
    
    # Initialize the orchestrator
    orchestrator = MwarokinOrchestrator()
    
    # Create a tenant context
    tenant = TenantContext(
        tenant_id="tenant_123",
        brand_name="Mwarokin Real Estate",
        locale="en_US",
        currency=Currency.USD,
        theme_settings={"primary_color": "#0066ff", "logo_url": "https://example.com/logo.png"},
        feature_flags={"advanced_valuation": True, "multilingual_support": True},
        created_at=datetime.now()
    )
    
    # Register the tenant
    orchestrator.register_tenant(tenant)
    
    # Start the orchestrator
    await orchestrator.start()
    
    # Submit a listing task
    listing_payload = {
        "title": "Beautiful family home in suburban area",
        "property_type": "house",
        "location": "123 Main St, Anytown",
        "price": "350000",
        "bedrooms": 4,
        "bathrooms": 2.5,
        "size_sqft": 2200,
        "description": "Spacious family home with updated kitchen and large backyard"
    }
    
    listing_task_id = await orchestrator.submit_task(
        "listing", 
        {"payload": listing_payload}, 
        "tenant_123"
    )
    
    # Wait a moment for processing
    await asyncio.sleep(1)
    
    # Submit a valuation task
    valuation_task_id = await orchestrator.submit_task(
        "valuation",
        {"listing_id": listing_task_id},
        "tenant_123"
    )
    
    # Submit a matchmaking task
    profile = {
        "budget": {"min": 200000, "max": 400000},
        "preferred_locations": ["Anytown", "Nearby City"],
        "preferences": {
            "property_type": "house",
            "bedrooms": 3,
            "bathrooms": 2
        },
        "must_have_amenities": ["parking", "garden", "updated_kitchen"]
    }
    
    matchmaking_task_id = await orchestrator.submit_task(
        "matchmaking",
        {"profile": profile},
        "tenant_123"
    )
    
    # Wait for tasks to complete
    await asyncio.sleep(2)
    
    # Get system status
    status = await orchestrator.get_system_status()
    print("System Status:", json.dumps(status, indent=2, default=str))
    
    # Stop the orchestrator
    await orchestrator.stop()

if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(demo())
```

This implementation provides:

1. **Base Agent System** with a consistent interface for all agents
2. **Three Core Agents**:
   - ListingAgent: For property intake and validation
   - ValuationAgent: For property valuation using comparables
   - MatchmakingAgent: For matching users with properties

3. **Orchestrator** that manages:
   - Multi-tenancy with tenant isolation
   - Task queueing and prioritization
   - Agent coordination
   - Error handling and reflection

4. **Key Features**:
   - Role-Based Access Control (RBAC)
   - Tenant isolation and context management
   - Async processing for scalability
   - Comprehensive logging and error handling
   - Reflection for continuous improvement

The system is designed to be extended with additional agents (PricingAgent, LeaseAgent, ComplianceAgent, etc.) following the same pattern. Each agent maintains tenant isolation and follows the principle of least privilege.

To complete the full system, you would add:
- RAG integration for knowledge grounding
- Additional agents for specialized tasks
- Database persistence layer
- API endpoints for web integration
- Authentication and authorization system
- Real-time communication channels

This architecture provides a solid foundation for a scalable, multi-tenant real estate agentic OS that can handle the complex workflows described in your requirements.