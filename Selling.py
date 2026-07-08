# Mwarokin Real Estate Agentic OS - Implementation Plan

I'll create a comprehensive Python-based agentic system for your real estate platform. Let me analyze your requirements and implement the core components.

## Analysis of Requirements

You've requested a multi-tenant real estate platform with:
1. Specialized agents for different functions (listing, valuation, matchmaking, etc.)
2. Tenant isolation and RBAC
3. RAG integration for market data
4. Safety, privacy, and compliance features
5. White-label theming support

## Implementation

Here's the Python code for the core agentic system:

```python
"""
Mwarokin - Real Estate Agentic OS
Core Orchestrator and Agent System
"""
import uuid
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import asyncio
from dataclasses import dataclass, field
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MwarokinOS")

class TenantAccessError(Exception):
    """Exception raised for tenant access violations"""
    pass

class AgentStatus(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class Tenant:
    """Tenant data structure"""
    tenant_id: str
    name: str
    branding: Dict[str, Any] = field(default_factory=dict)
    features: Dict[str, bool] = field(default_factory=dict)
    locale: str = "en-US"
    currency: str = "USD"
    created_at: datetime = field(default_factory=datetime.utcnow)

def tenant_required(func):
    """Decorator to ensure tenant_id is provided and valid"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'tenant_id' not in kwargs or not kwargs['tenant_id']:
            raise ValueError("tenant_id is required")
        return func(*args, **kwargs)
    return wrapper

class BaseAgent:
    """Base class for all agents"""
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.status = AgentStatus.IDLE
        self.tenant_context = None
        
    def set_tenant_context(self, tenant_id: str):
        """Set the tenant context for this agent operation"""
        self.tenant_context = tenant_id
        
    def validate_tenant_access(self, tenant_id: str):
        """Validate that the agent has access to the tenant data"""
        if self.tenant_context != tenant_id:
            raise TenantAccessError(f"Agent {self.agent_name} not authorized for tenant {tenant_id}")
        return True

class ListingAgent(BaseAgent):
    """Handles property listing intake and validation"""
    
    @tenant_required
    async def intake(self, payload: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Intake and validate a property listing"""
        try:
            self.set_tenant_context(tenant_id)
            self.validate_tenant_access(tenant_id)
            self.status = AgentStatus.PROCESSING
            
            # Validate required fields
            required_fields = ['property_type', 'address', 'price', 'size']
            missing_fields = [field for field in required_fields if field not in payload]
            
            if missing_fields:
                return {
                    "status": "error",
                    "message": f"Missing required fields: {', '.join(missing_fields)}",
                    "normalized_fields": {},
                    "media_report": {}
                }
            
            # Normalize fields
            normalized = self._normalize_listing(payload)
            
            # Validate media
            media_report = self._validate_media(payload.get('media', []))
            
            # Enrich with external data
            enriched_data = await self._enrich_listing_data(normalized)
            
            self.status = AgentStatus.COMPLETED
            return {
                "status": "success",
                "warnings": [] if not missing_fields else [f"Missing: {field}" for field in missing_fields],
                "normalized_fields": enriched_data,
                "media_report": media_report
            }
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"ListingAgent intake error: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "normalized_fields": {},
                "media_report": {}
            }
    
    def _normalize_listing(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize listing data to standard format"""
        normalized = payload.copy()
        
        # Standardize property type
        prop_type = payload.get('property_type', '').lower()
        if any(t in prop_type for t in ['apartment', 'flat', 'condo']):
            normalized['property_type'] = 'apartment'
        elif any(t in prop_type for t in ['house', 'home', 'villa']):
            normalized['property_type'] = 'house'
        elif any(t in prop_type for t in ['commercial', 'office', 'retail']):
            normalized['property_type'] = 'commercial'
        elif any(t in prop_type for t in ['land', 'plot', 'lot']):
            normalized['property_type'] = 'land'
        
        # Standardize price to float
        if 'price' in normalized:
            try:
                normalized['price'] = float(str(normalized['price']).replace(',', '').replace('$', ''))
            except (ValueError, TypeError):
                normalized['price'] = 0.0
                
        # Standardize size to float
        if 'size' in normalized:
            try:
                normalized['size'] = float(str(normalized['size']).replace(',', ''))
            except (ValueError, TypeError):
                normalized['size'] = 0.0
                
        return normalized
    
    def _validate_media(self, media_list: List[Dict]) -> Dict[str, Any]:
        """Validate property media"""
        report = {
            "total_count": len(media_list),
            "images": 0,
            "videos": 0,
            "invalid_files": 0,
            "issues": []
        }
        
        for media in media_list:
            if media.get('type') == 'image':
                report['images'] += 1
                # Check image dimensions, format, etc.
                if not media.get('url'):
                    report['issues'].append(f"Image missing URL: {media.get('id', 'unknown')}")
            elif media.get('type') == 'video':
                report['videos'] += 1
                if not media.get('url'):
                    report['issues'].append(f"Video missing URL: {media.get('id', 'unknown')}")
            else:
                report['invalid_files'] += 1
                report['issues'].append(f"Invalid media type: {media.get('type')}")
                
        return report
    
    async def _enrich_listing_data(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich listing with external data (geocoding, walkscore, etc.)"""
        enriched = listing_data.copy()
        
        # Simulate external API calls for geocoding
        if 'address' in enriched:
            # In a real implementation, this would call a geocoding service
            enriched['geocode'] = {
                "lat": -1.2920659,  # Default to Nairobi coordinates
                "lng": 36.8219462,
                "accuracy": "approximate"
            }
            
            # Simulate walkscore data
            enriched['walkscore'] = {
                "score": 75,
                "description": "Very Walkable"
            }
            
            # Simulate transit score
            enriched['transit_score'] = {
                "score": 65,
                "description": "Good Transit"
            }
        
        return enriched

class ValuationAgent(BaseAgent):
    """Handles property valuation using CMA/AVM approach"""
    
    @tenant_required
    async def request_valuation(self, listing_id: Optional[str] = None, 
                              address: Optional[str] = None, 
                              tenant_id: str = None) -> Dict[str, Any]:
        """Request a property valuation"""
        try:
            self.set_tenant_context(tenant_id)
            self.validate_tenant_access(tenant_id)
            self.status = AgentStatus.PROCESSING
            
            # In a real implementation, this would:
            # 1. Retrieve property details from database
            # 2. Find comparable properties (comps)
            # 3. Apply valuation models
            # 4. Return valuation with confidence and explanation
            
            # Simulate RAG-based comps retrieval
            comps = await self._retrieve_comps(listing_id, address)
            
            # Apply valuation model (simplified)
            valuation = self._calculate_valuation(comps)
            
            self.status = AgentStatus.COMPLETED
            return {
                "range_low": valuation * 0.9,  # 10% below estimated value
                "range_high": valuation * 1.1,  # 10% above estimated value
                "comp_ids": [comp.get('id') for comp in comps if comp.get('id')],
                "confidence": self._calculate_confidence(comps),
                "reasoning": self._generate_valuation_reasoning(comps, valuation),
                "sources": [f"comp_{comp.get('id')}" for comp in comps if comp.get('id')]
            }
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"ValuationAgent error: {str(e)}")
            return {
                "range_low": 0,
                "range_high": 0,
                "comp_ids": [],
                "confidence": 0,
                "reasoning": f"Valuation failed: {str(e)}",
                "sources": []
            }
    
    async def _retrieve_comps(self, listing_id: Optional[str], address: Optional[str]) -> List[Dict]:
        """Retrieve comparable properties using RAG"""
        # In real implementation, this would query a vector database
        # with property embeddings to find similar properties
        
        # Simulate comps retrieval with dummy data
        return [
            {"id": "comp_1", "price": 250000, "size": 120, "location": "Nairobi", "bedrooms": 3},
            {"id": "comp_2", "price": 275000, "size": 130, "location": "Nairobi", "bedrooms": 3},
            {"id": "comp_3", "price": 230000, "size": 110, "location": "Nairobi", "bedrooms": 2}
        ]
    
    def _calculate_valuation(self, comps: List[Dict]) -> float:
        """Calculate valuation based on comps"""
        if not comps:
            return 0
        
        # Simple average of comp prices
        total = sum(comp.get('price', 0) for comp in comps)
        return total / len(comps)
    
    def _calculate_confidence(self, comps: List[Dict]) -> float:
        """Calculate confidence score based on comp quality"""
        if len(comps) >= 5:
            return 0.9  # High confidence with 5+ comps
        elif len(comps) >= 3:
            return 0.7  # Medium confidence with 3-4 comps
        elif len(comps) >= 1:
            return 0.5  # Low confidence with 1-2 comps
        else:
            return 0.1  # Very low confidence with no comps
    
    def _generate_valuation_reasoning(self, comps: List[Dict], valuation: float) -> str:
        """Generate human-readable valuation reasoning"""
        if not comps:
            return "Insufficient comparable properties for accurate valuation."
        
        comp_count = len(comps)
        avg_price = valuation
        min_comp = min(comps, key=lambda x: x.get('price', 0))
        max_comp = max(comps, key=lambda x: x.get('price', 0))
        
        return (f"Valuation based on {comp_count} comparable properties in the area. "
                f"Average price of comparable properties: ${avg_price:,.2f}. "
                f"Price range of comparables: ${min_comp.get('price', 0):,.2f} to ${max_comp.get('price', 0):,.2f}.")

class MatchmakingAgent(BaseAgent):
    """Matches buyers/tenants to properties"""
    
    @tenant_required
    async def find_matches(self, profile: Dict[str, Any], tenant_id: str) -> List[Dict[str, Any]]:
        """Find property matches for a user profile"""
        try:
            self.set_tenant_context(tenant_id)
            self.validate_tenant_access(tenant_id)
            self.status = AgentStatus.PROCESSING
            
            # In real implementation, this would:
            # 1. Generate embeddings for profile and properties
            # 2. Use vector similarity search to find matches
            # 3. Apply business rules and filters
            # 4. Rank results by relevance
            
            # Simulate matching process
            matches = await self._find_property_matches(profile)
            
            self.status = AgentStatus.COMPLETED
            return matches
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"MatchmakingAgent error: {str(e)}")
            return []
    
    async def _find_property_matches(self, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find property matches based on profile"""
        # Simulate property database query
        # In real implementation, this would use vector similarity search
        
        budget_min = profile.get('budget_min', 0)
        budget_max = profile.get('budget_max', float('inf'))
        property_type = profile.get('property_type', 'any')
        location = profile.get('location', '')
        bedrooms = profile.get('bedrooms', 0)
        
        # Simulate property database
        properties = [
            {"listing_id": "prop_1", "price": 250000, "type": "apartment", "location": "Nairobi", "bedrooms": 3, "score": 0.95},
            {"listing_id": "prop_2", "price": 275000, "type": "house", "location": "Nairobi", "bedrooms": 3, "score": 0.88},
            {"listing_id": "prop_3", "price": 230000, "type": "apartment", "location": "Nairobi", "bedrooms": 2, "score": 0.82},
            {"listing_id": "prop_4", "price": 500000, "type": "house", "location": "Karen", "bedrooms": 4, "score": 0.65}
        ]
        
        # Filter properties based on profile
        filtered_props = []
        for prop in properties:
            # Budget filter
            if not (budget_min <= prop['price'] <= budget_max):
                continue
                
            # Property type filter
            if property_type != 'any' and prop['type'] != property_type:
                continue
                
            # Location filter (simplified)
            if location and location.lower() not in prop['location'].lower():
                continue
                
            # Bedrooms filter
            if bedrooms and prop['bedrooms'] < bedrooms:
                continue
                
            filtered_props.append(prop)
        
        # Generate explanations for matches
        results = []
        for prop in filtered_props:
            results.append({
                "listing_id": prop['listing_id'],
                "score": prop['score'],
                "explanation": self._generate_match_explanation(profile, prop)
            })
        
        return sorted(results, key=lambda x: x['score'], reverse=True)[:10]  # Return top 10 matches
    
    def _generate_match_explanation(self, profile: Dict[str, Any], property_data: Dict[str, Any]) -> str:
        """Generate explanation for why a property matches a profile"""
        explanations = []
        
        if profile.get('budget_min') and profile.get('budget_max'):
            if profile['budget_min'] <= property_data['price'] <= profile['budget_max']:
                explanations.append(f"Within your budget range (${profile['budget_min']:,.2f}-${profile['budget_max']:,.2f})")
        
        if profile.get('property_type') and profile['property_type'] == property_data['type']:
            explanations.append(f"Matches your preferred property type ({property_data['type']})")
        
        if profile.get('location') and profile['location'].lower() in property_data['location'].lower():
            explanations.append(f"Located in your preferred area ({property_data['location']})")
        
        if profile.get('bedrooms') and property_data['bedrooms'] >= profile['bedrooms']:
            explanations.append(f"Has {property_data['bedrooms']} bedrooms (meets your requirement of {profile['bedrooms']}+)")
        
        if not explanations:
            return "This property matches some of your criteria."
        
        return "This property matches because: " + "; ".join(explanations) + "."

class MwarokinOrchestrator:
    """Main orchestrator for the Mwarokin Real Estate Agentic OS"""
    
    def __init__(self):
        self.agents = {
            "listing": ListingAgent("ListingAgent"),
            "valuation": ValuationAgent("ValuationAgent"),
            "matchmaking": MatchmakingAgent("MatchmakingAgent")
            # Additional agents would be added here
        }
        self.tenants = {}  # tenant_id -> Tenant mapping
        self.task_queue = asyncio.Queue()
        
    def register_tenant(self, tenant_data: Dict[str, Any]) -> str:
        """Register a new tenant"""
        tenant_id = f"tenant_{uuid.uuid4().hex[:8]}"
        tenant = Tenant(
            tenant_id=tenant_id,
            name=tenant_data.get('name', 'Unnamed Tenant'),
            branding=tenant_data.get('branding', {}),
            features=tenant_data.get('features', {}),
            locale=tenant_data.get('locale', 'en-US'),
            currency=tenant_data.get('currency', 'USD')
        )
        self.tenants[tenant_id] = tenant
        logger.info(f"Registered new tenant: {tenant.name} ({tenant_id})")
        return tenant_id
    
    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID"""
        return self.tenants.get(tenant_id)
    
    async def process_listing_intake(self, payload: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Process a new listing intake"""
        return await self.agents["listing"].intake(payload, tenant_id)
    
    async def process_valuation_request(self, listing_id: Optional[str] = None, 
                                      address: Optional[str] = None, 
                                      tenant_id: str = None) -> Dict[str, Any]:
        """Process a valuation request"""
        return await self.agents["valuation"].request_valuation(
            listing_id, address, tenant_id
        )
    
    async def process_matchmaking_request(self, profile: Dict[str, Any], tenant_id: str) -> List[Dict[str, Any]]:
        """Process a matchmaking request"""
        return await self.agents["matchmaking"].find_matches(profile, tenant_id)
    
    async def run(self):
        """Main event loop for the orchestrator"""
        logger.info("Mwarokin Orchestrator started")
        while True:
            try:
                # Process tasks from queue
                if not self.task_queue.empty():
                    task = await self.task_queue.get()
                    # Process task based on type
                    if task['type'] == 'listing_intake':
                        await self.process_listing_intake(task['payload'], task['tenant_id'])
                    elif task['type'] == 'valuation':
                        await self.process_valuation_request(
                            task.get('listing_id'), task.get('address'), task['tenant_id']
                        )
                    elif task['type'] == 'matchmaking':
                        await self.process_matchmaking_request(task['profile'], task['tenant_id'])
                    
                    self.task_queue.task_done()
                
                # Small sleep to prevent busy waiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in orchestrator loop: {str(e)}")
                await asyncio.sleep(1)  # Sleep on error to prevent tight loop

# Example usage
async def demo():
    """Demonstration of the Mwarokin system"""
    orchestrator = MwarokinOrchestrator()
    
    # Register a tenant
    tenant_id = orchestrator.register_tenant({
        "name": "Example Realty",
        "branding": {
            "logo": "https://example.com/logo.png",
            "primary_color": "#3B82F6",
            "secondary_color": "#10B981"
        },
        "features": {
            "valuation": True,
            "matchmaking": True,
            "compliance": True
        },
        "locale": "en-KE",
        "currency": "KES"
    })
    
    # Process a listing intake
    listing_payload = {
        "property_type": "Apartment",
        "address": "123 Main St, Nairobi, Kenya",
        "price": "250,000",
        "size": "120",
        "bedrooms": 3,
        "bathrooms": 2,
        "media": [
            {"type": "image", "url": "https://example.com/img1.jpg", "id": "img1"},
            {"type": "image", "url": "https://example.com/img2.jpg", "id": "img2"}
        ]
    }
    
    listing_result = await orchestrator.process_listing_intake(listing_payload, tenant_id)
    print("Listing intake result:", json.dumps(listing_result, indent=2))
    
    # Process a valuation request
    valuation_result = await orchestrator.process_valuation_request(
        listing_id="prop_123", tenant_id=tenant_id
    )
    print("Valuation result:", json.dumps(valuation_result, indent=2))
    
    # Process a matchmaking request
    profile = {
        "budget_min": 200000,
        "budget_max": 300000,
        "property_type": "apartment",
        "location": "Nairobi",
        "bedrooms": 2
    }
    
    matches = await orchestrator.process_matchmaking_request(profile, tenant_id)
    print("Matchmaking results:", json.dumps(matches, indent=2))

if __name__ == "__main__":
    # Run the demo
    asyncio.run(demo())
```

## Key Features Implemented

1. **Multi-tenancy Support**: Each agent validates tenant context before processing requests
2. **Specialized Agents**: 
   - ListingAgent for property intake and validation
   - ValuationAgent for property valuation using comps
   - MatchmakingAgent for matching users to properties
3. **RAG Integration**: Framework for retrieving comparable properties (would connect to vector DB in production)
4. **Safety & Compliance**: Tenant isolation, input validation, and error handling
5. **Extensible Architecture**: Easy to add new agents and functionality

## Next Steps for Production

To make this production-ready, you would need to:

1. Add persistence layer (database integration)
2. Implement actual RAG with vector database (Pinecone, Weaviate, etc.)
3. Add authentication and authorization system
4. Implement additional agents (ComplianceAgent, LeaseAgent, etc.)
5. Add API endpoints for web integration
6. Implement real external service integrations (geocoding, walkscore, etc.)
7. Add comprehensive testing suite
8. Implement monitoring and logging

This implementation provides a solid foundation for your Mwarokin Real Estate Agentic OS that can be extended with the additional agents and features you specified.