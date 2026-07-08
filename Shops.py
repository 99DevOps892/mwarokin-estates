
# mwarokin_os.py
import uuid
import json
import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
import asyncio
from abc import ABC, abstractmethod

# Security and compliance imports
import bcrypt
from cryptography.fernet import Fernet
import re

# Data processing imports
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

# ==================== CORE DATA MODELS ====================

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

class Tenant:
    def __init__(self, tenant_id: str, name: str, config: Dict):
        self.tenant_id = tenant_id
        self.name = name
        self.config = config  # Includes white-label settings, feature flags, etc.
        self.created_at = datetime.datetime.now()
        self.is_active = True

@dataclass
class PropertyListing:
    listing_id: str
    tenant_id: str
    property_type: PropertyType
    status: ListingStatus
    address: str
    price: float
    currency: str
    size_sqft: int
    bedrooms: int
    bathrooms: int
    amenities: List[str]
    location: Dict[str, float]  # lat, long
    images: List[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime
    enriched_data: Optional[Dict] = None

@dataclass
class Valuation:
    range_low: float
    range_high: float
    confidence: float  # 0.0 to 1.0
    comp_ids: List[str]
    reasoning: str
    sources: List[str]
    generated_at: datetime.datetime

@dataclass
class MatchResult:
    listing_id: str
    score: float
    explanation: str
    match_factors: List[str]

@dataclass
class LeadProfile:
    lead_id: str
    tenant_id: str
    name: str
    contact_info: Dict[str, str]
    budget: float
    preferences: Dict[str, Any]
    bant_score: float  # Budget, Authority, Need, Timeline
    status: str

# ==================== BASE AGENT CLASS ====================

class BaseAgent(ABC):
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.agent_id = f"{self.__class__.__name__}_{uuid.uuid4().hex[:8]}"
        
    @abstractmethod
    async def execute(self, task_data: Dict, context: Dict) -> Dict:
        pass
    
    def _validate_tenant_access(self, target_tenant_id: str):
        if target_tenant_id != self.tenant_id:
            raise PermissionError(f"Agent {self.agent_id} cannot access data for tenant {target_tenant_id}")
    
    def _log_activity(self, action: str, details: Dict):
        # Implementation would connect to audit logging system
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "action": action,
            "details": details
        }
        print(f"ACTIVITY LOG: {json.dumps(log_entry)}")  # Replace with actual logging

# ==================== SPECIFIC AGENT IMPLEMENTATIONS ====================

class ListingAgent(BaseAgent):
    def __init__(self, tenant_id: str):
        super().__init__(tenant_id)
        self.geocoding_service = None  # Would be initialized with API key
        
    async def execute(self, task_data: Dict, context: Dict) -> Dict:
        self._validate_tenant_access(task_data.get("tenant_id"))
        
        # Validate required fields
        required_fields = ["address", "property_type", "price", "currency"]
        for field in required_fields:
            if field not in task_data:
                return {"status": "error", "message": f"Missing required field: {field}"}
        
        # Create listing ID
        listing_id = f"list_{uuid.uuid4().hex[:10]}"
        
        # Normalize data
        normalized_data = self._normalize_listing_data(task_data)
        
        # Validate data
        validation_results = self._validate_listing_data(normalized_data)
        
        # Enrich with additional data
        enriched_data = await self._enrich_listing_data(normalized_data)
        
        # Create listing object
        listing = PropertyListing(
            listing_id=listing_id,
            tenant_id=self.tenant_id,
            property_type=PropertyType(normalized_data["property_type"]),
            status=ListingStatus.DRAFT,
            address=normalized_data["address"],
            price=normalized_data["price"],
            currency=normalized_data["currency"],
            size_sqft=normalized_data.get("size_sqft", 0),
            bedrooms=normalized_data.get("bedrooms", 0),
            bathrooms=normalized_data.get("bathrooms", 0),
            amenities=normalized_data.get("amenities", []),
            location=normalized_data.get("location", {"lat": 0, "lng": 0}),
            images=normalized_data.get("images", []),
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            enriched_data=enriched_data
        )
        
        # Save to database (pseudo-code)
        # db.save_listing(listing)
        
        self._log_activity("listing_intake", {"listing_id": listing_id, "status": "success"})
        
        return {
            "status": "success",
            "listing_id": listing_id,
            "warnings": validation_results.get("warnings", []),
            "normalized_fields": normalized_data,
            "media_report": self._generate_media_report(normalized_data.get("images", []))
        }
    
    def _normalize_listing_data(self, data: Dict) -> Dict:
        normalized = data.copy()
        
        # Standardize property type
        if "property_type" in normalized:
            pt = normalized["property_type"].lower()
            if "apartment" in pt:
                normalized["property_type"] = PropertyType.APARTMENT.value
            elif "villa" in pt:
                normalized["property_type"] = PropertyType.VILLA.value
            elif "office" in pt:
                normalized["property_type"] = PropertyType.OFFICE.value
            elif "shop" in pt:
                normalized["property_type"] = PropertyType.SHOP.value
            elif "home" in pt or "house" in pt:
                normalized["property_type"] = PropertyType.HOME.value
            elif "land" in pt:
                normalized["property_type"] = PropertyType.LAND.value
            elif "commercial" in pt:
                normalized["property_type"] = PropertyType.COMMERCIAL.value
            else:
                normalized["property_type"] = PropertyType.RESIDENTIAL.value
        
        # Ensure price is float
        if "price" in normalized:
            try:
                normalized["price"] = float(normalized["price"])
            except (ValueError, TypeError):
                normalized["price"] = 0.0
        
        return normalized
    
    def _validate_listing_data(self, data: Dict) -> Dict:
        warnings = []
        
        # Price validation
        if data.get("price", 0) <= 0:
            warnings.append("Price should be greater than zero")
        
        # Address validation
        if not data.get("address", "").strip():
            warnings.append("Address is required")
        
        # Image validation
        if not data.get("images"):
            warnings.append("At least one image is recommended")
        
        return {"warnings": warnings, "is_valid": len(warnings) == 0}
    
    async def _enrich_listing_data(self, data: Dict) -> Dict:
        enriched = {}
        
        # Geocoding
        try:
            # This would call a real geocoding service
            # location = await self.geocoding_service.geocode(data["address"])
            # enriched["location"] = {"lat": location.lat, "lng": location.lng}
            enriched["location"] = {"lat": 0.0, "lng": 0.0}  # Placeholder
        except Exception as e:
            print(f"Geocoding error: {e}")
        
        # Additional enrichment would go here (walkscore, schools, etc.)
        
        return enriched
    
    def _generate_media_report(self, images: List[str]) -> Dict:
        # This would analyze images for quality, content, etc.
        return {
            "image_count": len(images),
            "quality_score": 0.8,  # Placeholder
            "issues": []  # Placeholder
        }

class ValuationAgent(BaseAgent):
    def __init__(self, tenant_id: str):
        super().__init__(tenant_id)
        self.comps_db = {}  # Would be a real database connection
        
    async def execute(self, task_data: Dict, context: Dict) -> Dict:
        self._validate_tenant_access(task_data.get("tenant_id"))
        
        listing_id = task_data.get("listing_id")
        address = task_data.get("address")
        
        if not listing_id and not address:
            return {"status": "error", "message": "Either listing_id or address is required"}
        
        # Get property details (pseudo-code)
        # if listing_id:
        #     property_details = db.get_listing(listing_id, self.tenant_id)
        # else:
        #     property_details = db.find_listing_by_address(address, self.tenant_id)
        
        # For demo purposes, creating a mock property
        property_details = {
            "property_type": "apartment",
            "address": "123 Main St, Nairobi, Kenya",
            "size_sqft": 1200,
            "bedrooms": 3,
            "bathrooms": 2,
            "amenities": ["parking", "security", "garden"]
        }
        
        # Find comparable properties
        comps = self._find_comps(property_details)
        
        # Calculate valuation
        valuation = self._calculate_valuation(property_details, comps)
        
        self._log_activity("valuation_request", {
            "listing_id": listing_id, 
            "address": address,
            "valuation": valuation.range_low
        })
        
        return {
            "range_low": valuation.range_low,
            "range_high": valuation.range_high,
            "confidence": valuation.confidence,
            "comp_ids": valuation.comp_ids,
            "reasoning": valuation.reasoning,
            "sources": valuation.sources
        }
    
    def _find_comps(self, property_details: Dict) -> List[Dict]:
        # This would query a database of recent sales and listings
        # For demo, returning mock data
        return [
            {
                "comp_id": "comp_1",
                "address": "124 Main St, Nairobi, Kenya",
                "price": 250000,
                "size_sqft": 1100,
                "bedrooms": 3,
                "bathrooms": 2,
                "sold_date": "2023-10-15",
                "similarity_score": 0.85
            },
            {
                "comp_id": "comp_2",
                "address": "125 Main St, Nairobi, Kenya",
                "price": 270000,
                "size_sqft": 1300,
                "bedrooms": 3,
                "bathrooms": 2,
                "sold_date": "2023-09-20",
                "similarity_score": 0.78
            }
        ]
    
    def _calculate_valuation(self, property_details: Dict, comps: List[Dict]) -> Valuation:
        if not comps:
            # Fallback valuation if no comps found
            return Valuation(
                range_low=property_details.get("price", 0) * 0.8,
                range_high=property_details.get("price", 0) * 1.2,
                confidence=0.3,
                comp_ids=[],
                reasoning="Limited comparable data available",
                sources=[],
                generated_at=datetime.datetime.now()
            )
        
        # Simple valuation based on comps (would be more sophisticated IRL)
        comp_prices = [comp["price"] for comp in comps]
        avg_price = sum(comp_prices) / len(comp_prices)
        
        # Adjust for property differences
        adjustment_factors = self._calculate_adjustment_factors(property_details, comps)
        adjusted_price = avg_price * adjustment_factors
        
        # Calculate confidence based on comp quality and quantity
        confidence = min(0.9, 0.5 + (len(comps) * 0.1))
        
        comp_ids = [comp["comp_id"] for comp in comps]
        
        return Valuation(
            range_low=adjusted_price * 0.9,
            range_high=adjusted_price * 1.1,
            confidence=confidence,
            comp_ids=comp_ids,
            reasoning=f"Based on {len(comps)} comparable properties with adjustment for size and features",
            sources=["internal_comps_db", "market_trends"],
            generated_at=datetime.datetime.now()
        )
    
    def _calculate_adjustment_factors(self, property_details: Dict, comps: List[Dict]) -> float:
        # Simple adjustment based on size difference
        prop_size = property_details.get("size_sqft", 1000)
        comp_sizes = [comp.get("size_sqft", 1000) for comp in comps]
        avg_comp_size = sum(comp_sizes) / len(comp_sizes)
        
        size_ratio = prop_size / avg_comp_size if avg_comp_size else 1
        return min(1.5, max(0.7, size_ratio))  # Cap adjustments

class MatchmakingAgent(BaseAgent):
    def __init__(self, tenant_id: str):
        super().__init__(tenant_id)
        self.vectorizer = TfidfVectorizer(max_features=1000)
        
    async def execute(self, task_data: Dict, context: Dict) -> Dict:
        self._validate_tenant_access(task_data.get("tenant_id"))
        
        profile = task_data.get("profile", {})
        if not profile:
            return {"status": "error", "message": "Profile data is required"}
        
        # Get active listings (pseudo-code)
        # active_listings = db.get_active_listings(self.tenant_id)
        active_listings = self._get_mock_listings()
        
        # Calculate matches
        matches = []
        for listing in active_listings:
            score = self._calculate_match_score(profile, listing)
            if score > 0.5:  # Threshold
                explanation = self._generate_explanation(profile, listing, score)
                match_factors = self._identify_match_factors(profile, listing)
                
                matches.append(MatchResult(
                    listing_id=listing["listing_id"],
                    score=score,
                    explanation=explanation,
                    match_factors=match_factors
                ))
        
        # Sort by score descending
        matches.sort(key=lambda x: x.score, reverse=True)
        
        self._log_activity("matchmaking_request", {
            "profile_id": profile.get("profile_id", "unknown"),
            "matches_found": len(matches)
        })
        
        return {
            "matches": [
                {
                    "listing_id": m.listing_id,
                    "score": m.score,
                    "explanation": m.explanation,
                    "match_factors": m.match_factors
                } for m in matches
            ]
        }
    
    def _get_mock_listings(self) -> List[Dict]:
        return [
            {
                "listing_id": "list_1",
                "property_type": "apartment",
                "address": "123 Main St, Nairobi, Kenya",
                "price": 250000,
                "size_sqft": 1200,
                "bedrooms": 3,
                "bathrooms": 2,
                "amenities": ["parking", "security", "garden"],
                "location": {"lat": -1.2921, "lng": 36.8219}
            },
            {
                "listing_id": "list_2",
                "property_type": "villa",
                "address": "456 Luxury Ave, Nairobi, Kenya",
                "price": 850000,
                "size_sqft": 3500,
                "bedrooms": 5,
                "bathrooms": 4,
                "amenities": ["pool", "gym", "security", "garden"],
                "location": {"lat": -1.2921, "lng": 36.8219}
            }
        ]
    
    def _calculate_match_score(self, profile: Dict, listing: Dict) -> float:
        score = 0.0
        factors = []
        
        # Budget match
        budget = profile.get("budget", 0)
        price = listing.get("price", 0)
        if budget > 0 and price > 0:
            budget_ratio = min(budget, price) / max(budget, price)
            budget_score = budget_ratio * 0.3
            score += budget_score
            factors.append(f"budget_match:{budget_score:.2f}")
        
        # Property type match
        pref_type = profile.get("preferred_property_type", "")
        actual_type = listing.get("property_type", "")
        if pref_type and actual_type and pref_type.lower() == actual_type.lower():
            score += 0.2
            factors.append("property_type_match")
        
        # Bedroom match
        pref_bedrooms = profile.get("preferred_bedrooms", 0)
        actual_bedrooms = listing.get("bedrooms", 0)
        if pref_bedrooms > 0 and actual_bedrooms > 0:
            if actual_bedrooms >= pref_bedrooms:
                score += 0.2
                factors.append("bedroom_match")
            elif actual_bedrooms >= pref_bedrooms - 1:
                score += 0.1
                factors.append("bedroom_near_match")
        
        # Location match (simplified)
        pref_location = profile.get("preferred_location", "")
        if pref_location and listing.get("address", ""):
            # This would use proper geocoding in a real implementation
            if pref_location.lower() in listing.get("address", "").lower():
                score += 0.3
                factors.append("location_match")
        
        return min(1.0, score)  # Cap at 1.0
    
    def _generate_explanation(self, profile: Dict, listing: Dict, score: float) -> str:
        explanations = []
        
        if score > 0.7:
            explanations.append("Excellent match based on your preferences")
        elif score > 0.5:
            explanations.append("Good match considering your criteria")
        else:
            explanations.append("Reasonable match worth considering")
        
        # Add specific factors
        budget = profile.get("budget", 0)
        price = listing.get("price", 0)
        if budget > 0 and price > 0 and price <= budget * 1.2:
            explanations.append(f"Within your budget range (${price:,.0f})")
        
        pref_type = profile.get("preferred_property_type", "")
        actual_type = listing.get("property_type", "")
        if pref_type and actual_type and pref_type.lower() == actual_type.lower():
            explanations.append(f"Matches your preferred property type ({pref_type})")
        
        return ". ".join(explanations)
    
    def _identify_match_factors(self, profile: Dict, listing: Dict) -> List[str]:
        factors = []
        
        # Budget factor
        budget = profile.get("budget", 0)
        price = listing.get("price", 0)
        if budget > 0 and price > 0 and price <= budget:
            factors.append("within_budget")
        elif budget > 0 and price > 0 and price <= budget * 1.2:
            factors.append("near_budget")
        
        # Property type factor
        pref_type = profile.get("preferred_property_type", "")
        actual_type = listing.get("property_type", "")
        if pref_type and actual_type and pref_type.lower() == actual_type.lower():
            factors.append("property_type_match")
        
        # Bedroom factor
        pref_bedrooms = profile.get("preferred_bedrooms", 0)
        actual_bedrooms = listing.get("bedrooms", 0)
        if pref_bedrooms > 0 and actual_bedrooms >= pref_bedrooms:
            factors.append("sufficient_bedrooms")
        
        # Location factor
        pref_location = profile.get("preferred_location", "")
        if pref_location and listing.get("address", ""):
            if pref_location.lower() in listing.get("address", "").lower():
                factors.append("preferred_location")
        
        return factors

# ==================== ORCHESTRATOR / SUPERVISOR ====================

class MwarokinOrchestrator:
    def __init__(self):
        self.agents = {}
        self.tenant_agents = {}  # tenant_id -> agent mapping
        self.task_queue = asyncio.Queue()
        self.active_tasks = {}
        
    def register_agent(self, agent_type: str, agent_class):
        self.agents[agent_type] = agent_class
        
    async def process_task(self, task_type: str, task_data: Dict, context: Dict) -> Dict:
        tenant_id = task_data.get("tenant_id")
        if not tenant_id:
            return {"status": "error", "message": "tenant_id is required"}
        
        # Get or create agent for this tenant
        agent_key = f"{task_type}_{tenant_id}"
        if agent_key not in self.tenant_agents:
            if task_type not in self.agents:
                return {"status": "error", "message": f"Unknown agent type: {task_type}"}
            
            agent_class = self.agents[task_type]
            self.tenant_agents[agent_key] = agent_class(tenant_id)
        
        agent = self.tenant_agents[agent_key]
        
        try:
            # Execute the task with the agent
            result = await agent.execute(task_data, context)
            return result
        except Exception as e:
            return {"status": "error", "message": f"Agent execution failed: {str(e)}"}
    
    async def start_processing(self):
        """Start processing tasks from the queue"""
        while True:
            task_id, task_type, task_data, context = await self.task_queue.get()
            try:
                result = await self.process_task(task_type, task_data, context)
                self.active_tasks[task_id] = {
                    "status": "completed",
                    "result": result,
                    "completed_at": datetime.datetime.now()
                }
            except Exception as e:
                self.active_tasks[task_id] = {
                    "status": "failed",
                    "error": str(e),
                    "failed_at": datetime.datetime.now()
                }
            finally:
                self.task_queue.task_done()
    
    async def submit_task(self, task_type: str, task_data: Dict, context: Dict = None) -> str:
        """Submit a task for processing and return task ID"""
        task_id = f"task_{uuid.uuid4().hex[:10]}"
        context = context or {}
        
        self.active_tasks[task_id] = {
            "status": "queued",
            "submitted_at": datetime.datetime.now(),
            "task_type": task_type,
            "task_data": task_data
        }
        
        await self.task_queue.put((task_id, task_type, task_data, context))
        return task_id
    
    def get_task_status(self, task_id: str) -> Dict:
        """Get the status of a task"""
        return self.active_tasks.get(task_id, {"status": "not_found"})

# ==================== SECURITY & COMPLIANCE ====================

class SecurityManager:
    def __init__(self):
        self.encryption_key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
    def encrypt_pii(self, data: str) -> str:
        """Encrypt personally identifiable information"""
        if not data:
            return ""
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt_pii(self, encrypted_data: str) -> str:
        """Decrypt personally identifiable information"""
        if not encrypted_data:
            return ""
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
    
    def hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data for secure storage"""
        if not data:
            return ""
        return bcrypt.hashpw(data.encode(), bcrypt.gensalt()).decode()
    
    def verify_hash(self, data: str, hashed_data: str) -> bool:
        """Verify hashed data"""
        if not data or not hashed_data:
            return False
        return bcrypt.checkpw(data.encode(), hashed_data.encode())
    
    def redact_pii(self, text: str) -> str:
        """Redact PII from text for logging"""
        # Redact email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', text)
        # Redact phone numbers (international format)
        text = re.sub(r'\b\+?[0-9][0-9\s\-\(\)]{7,20}\b', '[PHONE_REDACTED]', text)
        return text

class ComplianceAgent(BaseAgent):
    def __init__(self, tenant_id: str):
        super().__init__(tenant_id)
        self.kyc_providers = {}  # Would be initialized with actual KYC service connections
        
    async def execute(self, task_data: Dict, context: Dict) -> Dict:
        self._validate_tenant_access(task_data.get("tenant_id"))
        
        check_type = task_data.get("check_type", "kyc")
        user_data = task_data.get("user_data", {})
        
        if check_type == "kyc":
            result = await self._perform_kyc_check(user_data)
        elif check_type == "aml":
            result = await self._perform_aml_check(user_data)
        elif check_type == "pep":
            result = await self._perform_pep_check(user_data)
        else:
            return {"status": "error", "message": f"Unknown check type: {check_type}"}
        
        self._log_activity("compliance_check", {
            "check_type": check_type,
            "user_id": user_data.get("user_id", "unknown"),
            "result": result.get("status", "unknown")
        })
        
        return result
    
    async def _perform_kyc_check(self, user_data: Dict) -> Dict:
        # This would integrate with a real KYC service
        # For demo purposes, returning a mock response
        return {
            "status": "verified",
            "score": 0.85,
            "details": {
                "identity_verified": True,
                "document_valid": True,
                "biometric_match": True
            },
            "timestamp": datetime.datetime.now().isoformat()
        }
    
    async def _perform_aml_check(self, user_data: Dict) -> Dict:
        # This would integrate with an AML screening service
        return {
            "status": "clear",
            "risk_score": 0.1,
            "sanctions_match": False,
            "adverse_media": False,
            "timestamp": datetime.datetime.now().isoformat()
        }
    
    async def _perform_pep_check(self, user_data: Dict) -> Dict:
        # This would check for Politically Exposed Person status
        return {
            "status": "clear",
            "is_pep": False,
            "pep_relations": [],
            "timestamp": datetime.datetime.now().isoformat()
        }

# ==================== MAIN APPLICATION ====================

async def main():
    # Initialize the orchestrator
    orchestrator = MwarokinOrchestrator()
    
    # Register agent types
    orchestrator.register_agent("listing", ListingAgent)
    orchestrator.register_agent("valuation", ValuationAgent)
    orchestrator.register_agent("matchmaking", MatchmakingAgent)
    orchestrator.register_agent("compliance", ComplianceAgent)
    
    # Start processing tasks in the background
    processing_task = asyncio.create_task(orchestrator.start_processing())
    
    # Example usage
    try:
        # Example 1: Submit a listing intake task
        listing_task_id = await orchestrator.submit_task(
            "listing",
            {
                "tenant_id": "tenant_123",
                "address": "123 Main Street, Nairobi, Kenya",
                "property_type": "apartment",
                "price": 250000,
                "currency": "USD",
                "size_sqft": 1200,
                "bedrooms": 3,
                "bathrooms": 2,
                "amenities": ["parking", "security", "garden"],
                "images": ["img1.jpg", "img2.jpg"]
            }
        )
        print(f"Submitted listing task: {listing_task_id}")
        
        # Example 2: Submit a valuation task
        valuation_task_id = await orchestrator.submit_task(
            "valuation",
            {
                "tenant_id": "tenant_123",
                "address": "123 Main Street, Nairobi, Kenya"
            }
        )
        print(f"Submitted valuation task: {valuation_task_id}")
        
        # Example 3: Submit a matchmaking task
        matchmaking_task_id = await orchestrator.submit_task(
            "matchmaking",
            {
                "tenant_id": "tenant_123",
                "profile": {
                    "profile_id": "user_456",
                    "budget": 300000,
                    "preferred_property_type": "apartment",
                    "preferred_bedrooms": 3,
                    "preferred_location": "Nairobi"
                }
            }
        )
        print(f"Submitted matchmaking task: {matchmaking_task_id}")
        
        # Wait a bit for processing
        await asyncio.sleep(2)
        
        # Check task status
        print("Listing task status:", orchestrator.get_task_status(listing_task_id))
        print("Valuation task status:", orchestrator.get_task_status(valuation_task_id))
        print("Matchmaking task status:", orchestrator.get_task_status(matchmaking_task_id))
        
    finally:
        # Clean up
        processing_task.cancel()
        try:
            await processing_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    asyncio.run(main())
```

## HTML/JavaScript Integration

For the frontend integration, here's how you would connect your HTML interface to the Python backend:

```javascript
// frontend-integration.js
class MwarokinClient {
    constructor(apiBaseUrl, tenantId) {
        this.apiBaseUrl = apiBaseUrl;
        this.tenantId = tenantId;
    }

    async submitTask(agentType, taskData) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/task`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Tenant-ID': this.tenantId
                },
                body: JSON.stringify({
                    agent_type: agentType,
                    task_data: taskData
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error submitting task:', error);
            throw error;
        }
    }

    async getTaskStatus(taskId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/task/${taskId}`, {
                headers: {
                    'X-Tenant-ID': this.tenantId
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error getting task status:', error);
            throw error;
        }
    }

    // Property-related methods
    async intakeListing(listingData) {
        return this.submitTask('listing', {
            ...listingData,
            tenant_id: this.tenantId
        });
    }

    async requestValuation(listingIdOrAddress) {
        const taskData = { tenant_id: this.tenantId };
        
        if (listingIdOrAddress.startsWith('list_')) {
            taskData.listing_id = listingIdOrAddress;
        } else {
            taskData.address = listingIdOrAddress;
        }

        return this.submitTask('valuation', taskData);
    }

    async findMatches(profileData) {
        return this.submitTask('matchmaking', {
            profile: profileData,
            tenant_id: this.tenantId
        });
    }

    async performComplianceCheck(checkType, userData) {
        return this.submitTask('compliance', {
            check_type: checkType,
            user_data: userData,
            tenant_id: this.tenantId
        });
    }
}

// Initialize client
const mwarokinClient = new MwarokinClient('https://api.mwarokin.com', 'tenant_123');

// Example usage with your HTML form
document.getElementById('propertyForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const listingData = {
        address: formData.get('address'),
        property_type: formData.get('propertyType'),
        price: parseFloat(formData.get('price')),
        currency: formData.get('currency'),
        size_sqft: parseInt(formData.get('size')),
        bedrooms: parseInt(formData.get('bedrooms')),
        bathrooms: parseInt(formData.get('bathrooms')),
        amenities: formData.get('amenities').split(',').map(a => a.trim()),
        images: Array.from(formData.getAll('images')).filter(img => img)
    };

    try {
        const result = await mwarokinClient.intakeListing(listingData);
        console.log('Listing created:', result);
        alert('Property listed successfully!');
    } catch (error) {
        console.error('Error creating listing:', error);
        alert('Error creating listing. Please try again.');
    }
});
```

## Deployment and Scaling

For production deployment, you would want to:

1. Containerize the application using Docker
2. Use a message queue (Redis, RabbitMQ) for task processing
3. Implement proper database connections (PostgreSQL recommended)
4. Set up monitoring and logging (Prometheus, Grafana, ELK stack)
5. Implement API rate limiting and authentication
6. Use a cloud provider with auto-scaling capabilities

This implementation provides a solid foundation for your Mwarokin Real Estate Agentic OS that can be extended with the other agents you mentioned (PricingAgent, LeadCRM_Agent, LeaseAgent, etc.). The architecture ensures tenant isolation, security, and compliance while maintaining flexibility for future enhancements.