Mwarokin - Real Estate Agentic OS
Complete Python Backend Implementation

import uuid
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
import aiohttp
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MwarokinOS")

# Constants
DEFAULT_CURRENCY = "KES"
DEFAULT_LOCALE = "en-KE"

class AgentStatus(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class PropertyType(Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    LAND = "land"
    INDUSTRIAL = "industrial"

@dataclass
class Tenant:
    id: str
    name: str
    branding: Dict[str, Any]
    features: List[str]
    locale: str = DEFAULT_LOCALE
    currency: str = DEFAULT_CURRENCY
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True

@dataclass
class Task:
    id: str
    agent_type: str
    payload: Dict[str, Any]
    tenant_id: str
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: AgentStatus = AgentStatus.IDLE
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@dataclass
class PropertyListing:
    id: str
    title: str
    description: str
    property_type: PropertyType
    price: float
    currency: str
    location: Dict[str, Any]
    features: List[str]
    amenities: List[str]
    images: List[str]
    created_by: str
    tenant_id: str
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class ValuationResult:
    range_low: float
    range_high: float
    confidence: float
    comp_ids: List[str]
    reasoning: str
    sources: List[Dict[str, Any]]

class BaseAgent(ABC):
    """Base class for all specialized agents"""
    
    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.status = AgentStatus.IDLE
        self.current_task = None
        self.tasks_processed = 0
    
    async def execute(self, task: Task) -> Dict[str, Any]:
        """Execute a task"""
        self.status = AgentStatus.PROCESSING
        self.current_task = task
        
        try:
            # Validate tenant access
            if not await self._validate_tenant_access(task.tenant_id):
                raise PermissionError(f"Tenant {task.tenant_id} access denied for agent {self.agent_type}")
            
            # Process the task
            result = await self._process(task)
            self.status = AgentStatus.COMPLETED
            self.tasks_processed += 1
            return result
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"Agent {self.agent_id} error: {str(e)}")
            raise
    
    @abstractmethod
    async def _process(self, task: Task) -> Dict[str, Any]:
        """Process implementation for specialized agents"""
        pass
    
    async def _validate_tenant_access(self, tenant_id: str) -> bool:
        """Validate tenant access - to be implemented with actual tenant management"""
        # In a real implementation, this would check tenant permissions
        return True
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status.value,
            "current_task": self.current_task.id if self.current_task else None,
            "tasks_processed": self.tasks_processed
        }

class ListingAgent(BaseAgent):
    """Handles property listing intake, normalization, and validation"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, "ListingAgent")
    
    async def _process(self, task: Task) -> Dict[str, Any]:
        listing_data = task.payload.get("listing_data", {})
        
        # Perform validation and enrichment
        validated_data = await self._validate_listing(listing_data)
        enriched_data = await self._enrich_listing(validated_data)
        media_report = await self._validate_media(listing_data.get("images", []))
        
        # Create a property listing ID
        listing_id = f"list_{uuid.uuid4().hex[:10]}"
        
        return {
            "status": "success",
            "listing_id": listing_id,
            "normalized_fields": enriched_data,
            "warnings": validated_data.get("warnings", []),
            "media_report": media_report
        }
    
    async def _validate_listing(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate property listing data"""
        warnings = []
        
        # Check required fields
        required_fields = ["title", "property_type", "location", "price"]
        for field in required_fields:
            if field not in listing_data:
                warnings.append(f"Missing required field: {field}")
        
        # Validate property type
        if "property_type" in listing_data:
            try:
                PropertyType(listing_data["property_type"])
            except ValueError:
                warnings.append(f"Invalid property type: {listing_data['property_type']}")
        
        # Validate price
        if "price" in listing_data and listing_data["price"] <= 0:
            warnings.append("Price must be greater than zero")
        
        return {**listing_data, "warnings": warnings}
    
    async def _enrich_listing(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich listing data with additional information"""
        enriched = listing_data.copy()
        
        # Add timestamps
        enriched["processed_at"] = datetime.utcnow().isoformat()
        
        # Simulate geocoding if address is provided
        if "address" in listing_data:
            # In a real implementation, this would call a geocoding service
            enriched["geocode"] = {
                "lat": -1.2920659,  # Example coordinates for Nairobi
                "lng": 36.8219462,
                "accuracy": "ROOFTOP"
            }
        
        # Calculate amenity score
        enriched["amenity_score"] = self._calculate_amenity_score(listing_data)
        
        # Add energy/green score if not provided
        if "energy_score" not in enriched:
            enriched["energy_score"] = 0.7  # Default value
        
        return enriched
    
    async def _validate_media(self, media_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate media items"""
        # In a real implementation, this would validate images
        return {
            "total_count": len(media_items),
            "valid_count": len(media_items),
            "issues": []
        }
    
    def _calculate_amenity_score(self, listing_data: Dict[str, Any]) -> float:
        """Calculate amenity score based on available amenities"""
        base_score = 0.7
        amenities = listing_data.get("amenities", [])
        
        # Score based on number of amenities
        score = min(1.0, base_score + (0.05 * len(amenities)))
        
        # Bonus for premium amenities
        premium_amenities = ["pool", "gym", "security", "parking"]
        for amenity in premium_amenities:
            if amenity in amenities:
                score = min(1.0, score + 0.05)
        
        return round(score, 2)

class ValuationAgent(BaseAgent):
    """Handles property valuation using CMA/AVM approach with RAG"""
    
    def __init__(self, agent_id: str, rag_service):
        super().__init__(agent_id, "ValuationAgent")
        self.rag_service = rag_service
    
    async def _process(self, task: Task) -> Dict[str, Any]:
        property_data = task.payload.get("property_data", {})
        
        # Retrieve comparable properties using RAG
        comps = await self.rag_service.retrieve_comps(
            property_data, 
            task.tenant_id,
            limit=10
        )
        
        # Calculate valuation
        valuation = await self._calculate_valuation(property_data, comps)
        
        return {
            "range_low": valuation.range_low,
            "range_high": valuation.range_high,
            "confidence": valuation.confidence,
            "comp_ids": valuation.comp_ids,
            "reasoning": valuation.reasoning,
            "sources": valuation.sources
        }
    
    async def _calculate_valuation(self, property_data: Dict[str, Any], 
                                 comps: List[Dict[str, Any]]) -> ValuationResult:
        """Calculate property valuation based on comparables"""
        
        if not comps:
            # Fallback valuation when no comps available
            price = property_data.get("price", 0)
            return ValuationResult(
                range_low=price * 0.8,
                range_high=price * 1.2,
                confidence=0.5,
                comp_ids=[],
                reasoning="No comparable properties found, using broad estimate",
                sources=[]
            )
        
        # Calculate average price from comparables
        comp_prices = [comp.get("price", 0) for comp in comps if comp.get("price", 0) > 0]
        avg_price = sum(comp_prices) / len(comp_prices) if comp_prices else 0
        
        # Adjust based on property features
        adjustment_factor = self._calculate_adjustment_factor(property_data, comps[0] if comps else {})
        adjusted_price = avg_price * adjustment_factor
        
        # Calculate confidence based on number and quality of comps
        confidence = min(0.95, 0.7 + (0.05 * len(comps)))
        
        # Generate reasoning
        reasoning = f"Based on {len(comps)} comparable properties with adjustment for property features"
        
        return ValuationResult(
            range_low=adjusted_price * 0.9,
            range_high=adjusted_price * 1.1,
            confidence=round(confidence, 2),
            comp_ids=[comp.get("id", f"comp_{i}") for i, comp in enumerate(comps)],
            reasoning=reasoning,
            sources=comps[:3]  # Top 3 comps as sources
        )
    
    def _calculate_adjustment_factor(self, subject_property: Dict[str, Any], 
                                   comp_property: Dict[str, Any]) -> float:
        """Calculate adjustment factor based on property differences"""
        factor = 1.0
        
        # Adjust for size difference
        subj_size = subject_property.get("area", 0)
        comp_size = comp_property.get("area", 0)
        
        if subj_size > 0 and comp_size > 0:
            size_ratio = subj_size / comp_size
            if size_ratio > 1.1:
                factor *= 1.05
            elif size_ratio < 0.9:
                factor *= 0.95
        
        # Adjust for bedroom count
        subj_beds = subject_property.get("bedrooms", 0)
        comp_beds = comp_property.get("bedrooms", 0)
        
        if subj_beds != comp_beds:
            factor *= 1.0 + (0.03 * (subj_beds - comp_beds))
        
        # Adjust for amenities
        subj_amenities = subject_property.get("amenities", [])
        comp_amenities = comp_property.get("amenities", [])
        amenity_diff = len(subj_amenities) - len(comp_amenities)
        factor *= 1.0 + (0.02 * amenity_diff)
        
        return round(factor, 2)

class PricingAgent(BaseAgent):
    """Handles dynamic pricing and market analysis"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, "PricingAgent")
    
    async def _process(self, task: Task) -> Dict[str, Any]:
        property_data = task.payload.get("property_data", {})
        market_data = task.payload.get("market_data", {})
        
        # Calculate optimal price
        price_analysis = await self._analyze_pricing(property_data, market_data)
        
        return {
            "recommended_price": price_analysis["recommended_price"],
            "price_range": price_analysis["price_range"],
            "confidence": price_analysis["confidence"],
            "market_trend": price_analysis["market_trend"],
            "seasonal_adjustment": price_analysis["seasonal_adjustment"],
            "explanation": price_analysis["explanation"]
        }
    
    async def _analyze_pricing(self, property_data: Dict[str, Any], 
                             market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze optimal pricing based on property and market data"""
        base_price = property_data.get("price", 0)
        
        # Apply market trends
        market_trend = market_data.get("trend", "stable")
        trend_factor = self._get_trend_factor(market_trend)
        
        # Apply seasonal adjustments
        seasonal_factor = self._get_seasonal_factor()
        
        # Calculate recommended price
        recommended_price = base_price * trend_factor * seasonal_factor
        
        # Calculate price range (±10%)
        price_range = {
            "low": recommended_price * 0.9,
            "high": recommended_price * 1.1
        }
        
        # Generate explanation
        explanation = f"Base price: {base_price:.2f}. "
        explanation += f"Market trend: {market_trend} ({trend_factor}x). "
        explanation += f"Seasonal adjustment: {seasonal_factor}x."
        
        return {
            "recommended_price": round(recommended_price, 2),
            "price_range": {k: round(v, 2) for k, v in price_range.items()},
            "confidence": 0.8,  # Confidence score
            "market_trend": market_trend,
            "seasonal_adjustment": seasonal_factor,
            "explanation": explanation
        }
    
    def _get_trend_factor(self, trend: str) -> float:
        """Get pricing factor based on market trend"""
        factors = {
            "rising": 1.05,
            "stable": 1.0,
            "declining": 0.95
        }
        return factors.get(trend, 1.0)
    
    def _get_seasonal_factor(self) -> float:
        """Get seasonal adjustment factor"""
        month = datetime.now().month
        
        # Simple seasonal model (could be more sophisticated)
        if month in [3, 4, 5]:  # Spring - higher demand
            return 1.05
        elif month in [6, 7, 8]:  # Summer - peak demand
            return 1.1
        elif month in [9, 10, 11]:  # Fall - moderate demand
            return 1.0
        else:  # Winter - lower demand
            return 0.95

class MatchmakingAgent(BaseAgent):
    """Matches buyers/tenants with properties"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, "MatchmakingAgent")
    
    async def _process(self, task: Task) -> Dict[str, Any]:
        profile = task.payload.get("profile", {})
        preferences = task.payload.get("preferences", {})
        
        # Find matching properties
        matches = await self._find_matches(profile, preferences)
        
        return {
            "matches": matches,
            "total_matches": len(matches),
            "profile_summary": self._generate_profile_summary(profile)
        }
    
    async def _find_matches(self, profile: Dict[str, Any], 
                          preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find property matches based on profile and preferences"""
        # In a real implementation, this would query a database
        # For now, return mock matches
        
        budget = preferences.get("budget", {})
        min_price = budget.get("min", 0)
        max_price = budget.get("max", 1000000)
        
        property_type = preferences.get("property_type", "residential")
        location = preferences.get("location", "")
        
        # Generate mock matches based on preferences
        matches = []
        for i in range(5):
            price = min_price + (i * (max_price - min_price) / 5)
            score = 0.8 - (i * 0.1)  # Decreasing score for demo
            
            match = {
                "property_id": f"prop_{uuid.uuid4().hex[:8]}",
                "score": round(score, 2),
                "price": round(price, 2),
                "property_type": property_type,
                "location": location or "Nairobi",
                "explanation": f"Matches your budget and preferred property type",
                "features": ["3 bedrooms", "2 bathrooms", "parking"]
            }
            matches.append(match)
        
        # Sort by score (highest first)
        matches.sort(key=lambda x: x["score"], reverse=True)
        
        return matches
    
    def _generate_profile_summary(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the user profile"""
        return {
            "budget_range": f"{profile.get('min_budget', 0)}-{profile.get('max_budget', 0)}",
            "preferred_locations": profile.get("locations", []),
            "property_types": profile.get("property_types", []),
            "bedrooms": profile.get("bedrooms", {}),
            "amenities_priority": profile.get("amenities_priority", [])
        }

class RAGService:
    """Retrieval-Augmented Generation service for market data"""
    
    def __init__(self, knowledge_base_url: str):
        self.knowledge_base_url = knowledge_base_url
        self.session = aiohttp.ClientSession()
    
    async def retrieve_comps(self, property_data: Dict[str, Any], 
                           tenant_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve comparable properties"""
        # In a real implementation, this would query a knowledge base
        # For now, return mock data
        
        property_type = property_data.get("property_type", "residential")
        price = property_data.get("price", 100000)
        area = property_data.get("area", 100)
        bedrooms = property_data.get("bedrooms", 2)
        
        comps = []
        for i in range(limit):
            comp_price = price * (0.8 + 0.4 * (i/10))
            comp_area = area * (0.9 + 0.2 * (i/10))
            comp_beds = bedrooms + (i % 3 - 1)
            
            comp = {
                "id": f"comp_{uuid.uuid4().hex[:8]}",
                "price": round(comp_price, 2),
                "area": round(comp_area, 2),
                "bedrooms": comp_beds,
                "property_type": property_type,
                "location": property_data.get("location", "Nairobi"),
                "distance_km": round(i * 0.5, 1),
                "transaction_date": (datetime.now() - timedelta(days=30*i)).strftime("%Y-%m-%d")
            }
            comps.append(comp)
        
        return comps
    
    async def retrieve_market_intel(self, query: str, tenant_id: str, 
                                  limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve market intelligence documents"""
        # In a real implementation, this would query a knowledge base
        # For now, return mock data
        
        docs = []
        for i in range(limit):
            doc = {
                "id": f"doc_{uuid.uuid4().hex[:8]}",
                "title": f"Market Report {i+1} for {query}",
                "content": f"Market intelligence content for {query}. This includes trends, analysis, and forecasts.",
                "source": "Internal Database",
                "date": (datetime.now() - timedelta(days=7*i)).strftime("%Y-%m-%d"),
                "relevance": round(0.9 - (i * 0.1), 2)
            }
            docs.append(doc)
        
        return docs
    
    async def close(self):
        """Close the HTTP session"""
        await self.session.close()

class Orchestrator:
    """Main orchestrator that manages agents and tasks"""
    
    def __init__(self, knowledge_base_url: str = "https://api.knowledgebase.example.com"):
        self.agents = {}
        self.tasks = {}
        self.rag_service = RAGService(knowledge_base_url)
        self.tenants = {}  # Would be populated from database
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize all agents"""
        self.agents["listing"] = ListingAgent("listing_agent_1")
        self.agents["valuation"] = ValuationAgent("valuation_agent_1", self.rag_service)
        self.agents["pricing"] = PricingAgent("pricing_agent_1")
        self.agents["matchmaking"] = MatchmakingAgent("matchmaking_agent_1")
        # Additional agents would be initialized here
    
    async def submit_task(self, agent_type: str, payload: Dict[str, Any], 
                         tenant_id: str, priority: TaskPriority = TaskPriority.MEDIUM) -> str:
        """Submit a task to the appropriate agent"""
        if agent_type not in self.agents:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = Task(
            id=task_id,
            agent_type=agent_type,
            payload=payload,
            tenant_id=tenant_id,
            priority=priority
        )
        
        self.tasks[task_id] = task
        
        # Execute task asynchronously
        asyncio.create_task(self._execute_task(task))
        
        return task_id
    
    async def _execute_task(self, task: Task):
        """Execute a task with the appropriate agent"""
        agent = self.agents[task.agent_type]
        
        try:
            result = await agent.execute(task)
            task.result = result
            task.status = AgentStatus.COMPLETED
            logger.info(f"Task {task.id} completed successfully")
        except Exception as e:
            task.status = AgentStatus.ERROR
            task.error = str(e)
            logger.error(f"Task {task.id} failed: {str(e)}")
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a task"""
        if task_id not in self.tasks:
            raise ValueError(f"Task not found: {task_id}")
        
        task = self.tasks[task_id]
        return {
            "task_id": task.id,
            "agent_type": task.agent_type,
            "status": task.status.value,
            "created_at": task.created_at.isoformat(),
            "result": task.result,
            "error": task.error
        }
    
    def get_agent_statuses(self) -> Dict[str, Any]:
        """Get status of all agents"""
        return {agent_id: agent.get_status() for agent_id, agent in self.agents.items()}
    
    async def close(self):
        """Clean up resources"""
        await self.rag_service.close()

# FastAPI implementation for REST API
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Mwarokin Real Estate API", version="1.0.0")
security = HTTPBearer()

# Pydantic models for request/response
class ListingRequest(BaseModel):
    listing_data: dict
    tenant_id: str

class ValuationRequest(BaseModel):
    property_data: dict
    tenant_id: str

class PricingRequest(BaseModel):
    property_data: dict
    market_data: dict
    tenant_id: str

class MatchmakingRequest(BaseModel):
    profile: dict
    preferences: dict
    tenant_id: str

class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None

# Global orchestrator instance
orchestrator = Orchestrator()

def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate authentication token"""
    # In a real implementation, this would verify JWT tokens
    # For demo purposes, we'll just extract tenant_id from token
    try:
        # Simple mock validation - in reality, use proper JWT validation
        token = credentials.credentials
        # Extract tenant_id from token (mock implementation)
        if token.startswith("tenant_"):
            return {"tenant_id": token, "user_id": f"user_{token.split('_')[1]}"}
        else:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication")

@app.post("/api/listings/intake", response_model=TaskResponse)
async def intake_listing(request: ListingRequest, auth: dict = Depends(validate_token)):
    """Endpoint for listing intake"""
    try:
        task_id = await orchestrator.submit_task(
            agent_type="listing",
            payload={"listing_data": request.listing_data},
            tenant_id=request.tenant_id
        )
        return {"task_id": task_id, "status": "submitted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/valuation/request", response_model=TaskResponse)
async def request_valuation(request: ValuationRequest, auth: dict = Depends(validate_token)):
    """Endpoint for valuation requests"""
    try:
        task_id = await orchestrator.submit_task(
            agent_type="valuation",
            payload={"property_data": request.property_data},
            tenant_id=request.tenant_id
        )
        return {"task_id": task_id, "status": "submitted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pricing/analyze", response_model=TaskResponse)
async def analyze_pricing(request: PricingRequest, auth: dict = Depends(validate_token)):
    """Endpoint for pricing analysis"""
    try:
        task_id = await orchestrator.submit_task(
            agent_type="pricing",
            payload={
                "property_data": request.property_data,
                "market_data": request.market_data
            },
            tenant_id=request.tenant_id
        )
        return {"task_id": task_id, "status": "submitted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/matchmaking/find", response_model=TaskResponse)
async def find_matches(request: MatchmakingRequest, auth: dict = Depends(validate_token)):
    """Endpoint for matchmaking"""
    try:
        task_id = await orchestrator.submit_task(
            agent_type="matchmaking",
            payload={
                "profile": request.profile,
                "preferences": request.preferences
            },
            tenant_id=request.tenant_id
        )
        return {"task_id": task_id, "status": "submitted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str, auth: dict = Depends(validate_token)):
    """Get task status"""
    try:
        return orchestrator.get_task_status(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")

@app.get("/api/agents/status")
async def get_agents_status(auth: dict = Depends(validate_token)):
    """Get status of all agents"""
    return orchestrator.get_agent_statuses()

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Example usage
async def main():
    """Example usage of the orchestrator"""
    # Initialize the orchestrator
    orchestrator = Orchestrator()
    
    # Example: Submit a listing intake task
    listing_data = {
        "title": "Beautiful apartment in Nairobi",
        "property_type": "residential",
        "address": "123 Main St, Nairobi, Kenya",
        "price": 150000,
        "area": 85,
        "bedrooms": 2,
        "bathrooms": 1,
        "amenities": ["parking", "security", "gym"],
        "images": ["img1.jpg", "img2.jpg"]
    }
    
    task_id = await orchestrator.submit_task(
        agent_type="listing",
        payload={"listing_data": listing_data},
        tenant_id="tenant_123",
        priority=TaskPriority.HIGH
    )
    
    print(f"Submitted task: {task_id}")
    
    # Wait a moment for processing
    await asyncio.sleep(2)
    
    # Check task status
    status = orchestrator.get_task_status(task_id)
    print(f"Task status: {status['status']}")
    if status["status"] == "completed":
        print(f"Result: {json.dumps(status['result'], indent=2)}")
    
    # Check all agent statuses
    agent_statuses = orchestrator.get_agent_statuses()
    print(f"Agent statuses: {json.dumps(agent_statuses, indent=2)}")
    
    # Clean up
    await orchestrator.close()

if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
```

This Python implementation provides:

1. **Core Agent System**: Base class and specialized agents (Listing, Valuation, Pricing, Matchmaking)
2. **RAG Integration**: For retrieving market data and comparable properties
3. **Multi-tenancy Support**: Tenant isolation and validation
4. **REST API**: FastAPI endpoints for frontend integration
5. **Error Handling**: Comprehensive error handling and logging
6. **Type Safety**: Using Python type hints and Pydantic models

To complete the system, you would need to:

1. Set up a database for persistent storage
2. Implement the remaining agents (LeadCRM, Lease, Transaction, Compliance, etc.)
3. Add authentication and authorization with JWT tokens
4. Deploy the FastAPI application with a production ASGI server
5. Set up the RAG knowledge base with real estate data

The frontend JavaScript code would make API calls to these endpoints to integrate with the agentic system.