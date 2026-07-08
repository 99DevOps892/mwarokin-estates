import uuid
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import logging
from dataclasses import dataclass, field
import aiohttp
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import redis
from sqlalchemy import create_engine, Column, String, JSON, DateTime, Float, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import bcrypt
from jose import JWTError, jwt
from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
import asyncpg

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mwarokin")

# Database setup
DATABASE_URL = "postgresql+asyncpg://user:password@localhost/mwarokin"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis for caching
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Security
SECRET_KEY = "your-secret-key-here"  # Change in production
ALGORITHM = "HS256"
security = HTTPBearer()

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)
    config = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user")  # admin, manager, agent, user
    permissions = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

class Listing(Base):
    __tablename__ = "listings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False)
    property_data = Column(JSON, nullable=False)
    status = Column(String, default="draft")  # draft, active, pending, sold, rented
    validation_report = Column(JSON, default={})
    enrichment_data = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Pydantic models for request/response
class TenantCreate(BaseModel):
    name: str
    config: Dict[str, Any] = {}

class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "user"
    permissions: List[str] = []

class ListingIntake(BaseModel):
    property_data: Dict[str, Any]
    tenant_id: str

class ValuationRequest(BaseModel):
    listing_id: Optional[str] = None
    address: Optional[str] = None
    tenant_id: str

class MatchmakingRequest(BaseModel):
    profile: Dict[str, Any]
    tenant_id: str

class LeaseCreate(BaseModel):
    listing_id: str
    applicant_id: str
    terms: Dict[str, Any]

# Agent Base Class
class BaseAgent:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.redis = redis_client
        self.db_session = SessionLocal()
    
    async def execute(self, *args, **kwargs):
        raise NotImplementedError("Subclasses must implement execute method")
    
    def get_tenant_config(self):
        """Get tenant-specific configuration"""
        tenant = self.db_session.query(Tenant).filter(Tenant.id == self.tenant_id).first()
        return tenant.config if tenant else {}
    
    def log_activity(self, action: str, details: Dict[str, Any]):
        """Log agent activity for audit trail"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": self.__class__.__name__,
            "tenant_id": self.tenant_id,
            "action": action,
            "details": details
        }
        # Store in Redis for quick access and in DB for persistence
        self.redis.rpush(f"activity:{self.tenant_id}", json.dumps(log_entry))

# Specialized Agents
class ListingAgent(BaseAgent):
    """Handles property listing intake, validation, and enrichment"""
    
    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process new listing intake"""
        try:
            # Validate required fields
            validation_result = self._validate_listing(payload)
            
            if not validation_result["is_valid"]:
                return {
                    "status": "rejected",
                    "warnings": validation_result["warnings"],
                    "normalized_fields": {},
                    "media_report": {}
                }
            
            # Normalize data
            normalized_data = self._normalize_listing_data(payload)
            
            # Enrich with external data
            enriched_data = await self._enrich_listing(normalized_data)
            
            # Generate media quality report
            media_report = self._analyze_media(payload.get("media", []))
            
            return {
                "status": "accepted",
                "warnings": validation_result["warnings"],
                "normalized_fields": normalized_data,
                "media_report": media_report,
                "enrichment_data": enriched_data
            }
            
        except Exception as e:
            logger.error(f"ListingAgent error: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _validate_listing(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate listing data against business rules"""
        warnings = []
        required_fields = ["address", "property_type", "price", "area"]
        
        for field in required_fields:
            if field not in listing_data or not listing_data[field]:
                warnings.append(f"Missing required field: {field}")
        
        # Price validation
        if "price" in listing_data and listing_data["price"]:
            try:
                price = float(listing_data["price"])
                if price <= 0:
                    warnings.append("Price must be positive")
            except (ValueError, TypeError):
                warnings.append("Invalid price format")
        
        return {
            "is_valid": len(warnings) == 0,
            "warnings": warnings
        }
    
    def _normalize_listing_data(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize listing data to standard format"""
        normalized = listing_data.copy()
        
        # Standardize property type
        property_type_map = {
            "apt": "apartment", "condo": "condominium",
            "house": "single_family", "townhome": "townhouse"
        }
        if normalized.get("property_type") in property_type_map:
            normalized["property_type"] = property_type_map[normalized["property_type"]]
        
        # Convert area to square meters if needed
        if "area" in normalized and "area_unit" in normalized:
            if normalized["area_unit"].lower() in ["sqft", "square feet"]:
                normalized["area"] = float(normalized["area"]) * 0.092903
                normalized["area_unit"] = "square_meters"
        
        return normalized
    
    async def _enrich_listing(self, listing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich listing with external data"""
        enriched = {}
        address = listing_data.get("address")
        
        if address:
            try:
                # Geocoding (simplified)
                enriched["geocoding"] = await self._geocode_address(address)
                
                # Get proximity data (simplified)
                enriched["proximity"] = {
                    "schools": await self._get_nearby_schools(address),
                    "transit": await self._get_transit_info(address),
                    "amenities": await self._get_nearby_amenities(address)
                }
                
                # Walk score (simplified)
                enriched["walk_score"] = await self._calculate_walk_score(address)
                
            except Exception as e:
                logger.warning(f"Enrichment failed: {str(e)}")
        
        return enriched
    
    async def _geocode_address(self, address: str) -> Dict[str, Any]:
        """Simulated geocoding"""
        await asyncio.sleep(0.1)  # Simulate API call
        return {
            "latitude": np.random.uniform(-90, 90),
            "longitude": np.random.uniform(-180, 180),
            "confidence": "high"
        }
    
    async def _get_nearby_schools(self, address: str) -> List[Dict[str, Any]]:
        """Simulated school data"""
        await asyncio.sleep(0.1)
        return [{"name": f"School {i}", "distance": np.random.uniform(0.5, 5.0), "rating": np.random.uniform(3, 5)} 
                for i in range(3)]
    
    async def _get_transit_info(self, address: str) -> Dict[str, Any]:
        """Simulated transit data"""
        await asyncio.sleep(0.1)
        return {
            "stops": [{"type": "bus", "distance": np.random.uniform(0.1, 1.0)} 
                     for _ in range(2)],
            "score": np.random.uniform(50, 100)
        }
    
    async def _get_nearby_amenities(self, address: str) -> Dict[str, Any]:
        """Simulated amenities data"""
        await asyncio.sleep(0.1)
        amenities = ["grocery", "restaurant", "park", "pharmacy", "gym"]
        return {amenity: np.random.uniform(0.1, 2.0) for amenity in amenities}
    
    async def _calculate_walk_score(self, address: str) -> float:
        """Simulated walk score"""
        await asyncio.sleep(0.1)
        return np.random.uniform(50, 100)
    
    def _analyze_media(self, media_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze media quality"""
        if not media_items:
            return {"quality_score": 0, "issues": ["No media provided"]}
        
        issues = []
        for i, media in enumerate(media_items):
            if media.get("size", 0) < 10240:  # 10KB minimum
                issues.append(f"Media {i+1}: File too small")
            if not media.get("url"):
                issues.append(f"Media {i+1}: Missing URL")
        
        quality_score = max(0, 100 - len(issues) * 20)
        return {"quality_score": quality_score, "issues": issues}

class ValuationAgent(BaseAgent):
    """Provides property valuation using comps and market data"""
    
    async def execute(self, listing_id: Optional[str] = None, address: Optional[str] = None) -> Dict[str, Any]:
        """Generate property valuation"""
        try:
            # Get property data
            property_data = await self._get_property_data(listing_id, address)
            if not property_data:
                return {"error": "Property not found"}
            
            # Find comparable properties
            comps = await self._find_comps(property_data)
            
            # Calculate valuation
            valuation = self._calculate_valuation(property_data, comps)
            
            # Generate reasoning
            reasoning = self._generate_valuation_reasoning(property_data, comps, valuation)
            
            return {
                "range_low": valuation["low"],
                "range_high": valuation["high"],
                "confidence": valuation["confidence"],
                "comp_ids": [comp.get("id") for comp in comps if comp.get("id")],
                "reasoning": reasoning,
                "sources": ["internal_comps", "market_trends"]
            }
            
        except Exception as e:
            logger.error(f"ValuationAgent error: {str(e)}")
            return {"error": str(e)}
    
    async def _get_property_data(self, listing_id: Optional[str], address: Optional[str]) -> Optional[Dict[str, Any]]:
        """Retrieve property data from database or external source"""
        if listing_id:
            # Get from database
            listing = self.db_session.query(Listing).filter(Listing.id == listing_id).first()
            if listing:
                return listing.property_data
        
        if address:
            # Simulate external data lookup
            await asyncio.sleep(0.2)
            return {
                "address": address,
                "property_type": "single_family",
                "bedrooms": 3,
                "bathrooms": 2,
                "area": 150,
                "year_built": 1990
            }
        
        return None
    
    async def _find_comps(self, property_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find comparable properties"""
        # In a real system, this would query a database of recent sales/listings
        await asyncio.sleep(0.3)
        
        comps = []
        for i in range(5):
            comps.append({
                "id": f"comp_{i}",
                "address": f"{i*100} Example St",
                "property_type": property_data["property_type"],
                "bedrooms": max(1, property_data.get("bedrooms", 3) + np.random.randint(-1, 2)),
                "bathrooms": max(1, property_data.get("bathrooms", 2) + np.random.randint(-1, 2)),
                "area": property_data.get("area", 150) * np.random.uniform(0.8, 1.2),
                "price": np.random.uniform(200000, 800000),
                "sale_date": (datetime.now() - timedelta(days=np.random.randint(1, 180))).isoformat(),
                "distance_km": np.random.uniform(0.1, 5.0)
            })
        
        return comps
    
    def _calculate_valuation(self, property_data: Dict[str, Any], comps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate valuation range based on comps"""
        if not comps:
            return {"low": 0, "high": 0, "confidence": "low"}
        
        # Simple valuation based on price per square meter/area
        comp_prices = []
        for comp in comps:
            if comp.get("area") and comp.get("price"):
                price_per_area = comp["price"] / comp["area"]
                comp_prices.append(price_per_area)
        
        if not comp_prices:
            return {"low": 0, "high": 0, "confidence": "low"}
        
        avg_price_per_area = np.mean(comp_prices)
        std_price_per_area = np.std(comp_prices)
        
        estimated_value = avg_price_per_area * property_data.get("area", 150)
        
        # Calculate confidence based on comp similarity and recency
        similarity_score = self._calculate_similarity_score(property_data, comps)
        confidence = "high" if similarity_score > 0.8 else "medium" if similarity_score > 0.5 else "low"
        
        return {
            "low": estimated_value * 0.9,
            "high": estimated_value * 1.1,
            "confidence": confidence
        }
    
    def _calculate_similarity_score(self, property_data: Dict[str, Any], comps: List[Dict[str, Any]]) -> float:
        """Calculate how similar comps are to the subject property"""
        if not comps:
            return 0.0
        
        scores = []
        for comp in comps:
            score = 0.0
            # Property type match
            if comp.get("property_type") == property_data.get("property_type"):
                score += 0.3
            
            # Size similarity
            if comp.get("area") and property_data.get("area"):
                size_ratio = min(comp["area"], property_data["area"]) / max(comp["area"], property_data["area"])
                score += size_ratio * 0.3
            
            # Bedroom/bathroom similarity
            bedroom_diff = abs(comp.get("bedrooms", 0) - property_data.get("bedrooms", 0))
            bathroom_diff = abs(comp.get("bathrooms", 0) - property_data.get("bathrooms", 0))
            score += max(0, 0.4 - (bedroom_diff * 0.1 + bathroom_diff * 0.1))
            
            scores.append(min(1.0, score))
        
        return np.mean(scores) if scores else 0.0
    
    def _generate_valuation_reasoning(self, property_data: Dict[str, Any], comps: List[Dict[str, Any]], valuation: Dict[str, Any]) -> str:
        """Generate human-readable valuation reasoning"""
        num_comps = len(comps)
        confidence = valuation["confidence"]
        
        reasoning = f"Valuation based on {num_comps} comparable properties with {confidence} confidence. "
        
        if comps:
            avg_comp_price = np.mean([comp.get("price", 0) for comp in comps])
            reasoning += f"Average comparable property price: ${avg_comp_price:,.0f}. "
        
        reasoning += f"Valuation range: ${valuation['low']:,.0f} - ${valuation['high']:,.0f}."
        
        return reasoning

class MatchmakingAgent(BaseAgent):
    """Matches buyers/tenants with properties using embeddings and rules"""
    
    def __init__(self, tenant_id: str):
        super().__init__(tenant_id)
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.property_embeddings = {}
    
    async def execute(self, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find property matches for a given profile"""
        try:
            # Get active listings
            active_listings = self._get_active_listings()
            
            if not active_listings:
                return []
            
            # Calculate match scores
            matches = []
            for listing in active_listings:
                score = self._calculate_match_score(profile, listing)
                if score > 0.3:  # Minimum threshold
                    explanation = self._generate_match_explanation(profile, listing, score)
                    matches.append({
                        "listing_id": listing["id"],
                        "score": score,
                        "explanation": explanation
                    })
            
            # Sort by score descending
            matches.sort(key=lambda x: x["score"], reverse=True)
            
            return matches[:10]  # Return top 10 matches
            
        except Exception as e:
            logger.error(f"MatchmakingAgent error: {str(e)}")
            return []
    
    def _get_active_listings(self) -> List[Dict[str, Any]]:
        """Get active listings from database"""
        listings = self.db_session.query(Listing).filter(
            Listing.tenant_id == self.tenant_id,
            Listing.status == "active"
        ).all()
        
        return [{
            "id": listing.id,
            "property_data": listing.property_data,
            "enrichment_data": listing.enrichment_data
        } for listing in listings]
    
    def _calculate_match_score(self, profile: Dict[str, Any], listing: Dict[str, Any]) -> float:
        """Calculate match score between profile and listing"""
        score = 0.0
        property_data = listing["property_data"]
        
        # Budget match (40% weight)
        budget_score = self._calculate_budget_match(profile, property_data)
        score += budget_score * 0.4
        
        # Property type preference (20% weight)
        type_score = self._calculate_type_match(profile, property_data)
        score += type_score * 0.2
        
        # Location preference (20% weight)
        location_score = self._calculate_location_match(profile, listing)
        score += location_score * 0.2
        
        # Amenities match (20% weight)
        amenities_score = self._calculate_amenities_match(profile, property_data)
        score += amenities_score * 0.2
        
        return min(1.0, score)
    
    def _calculate_budget_match(self, profile: Dict[str, Any], property_data: Dict[str, Any]) -> float:
        """Calculate budget compatibility score"""
        profile_budget = profile.get("max_budget")
        property_price = property_data.get("price")
        
        if not profile_budget or not property_price:
            return 0.5  # Neutral score if data missing
        
        if property_price <= profile_budget:
            # Within budget - higher score for closer to budget
            ratio = property_price / profile_budget
            return 0.5 + (0.5 * ratio)  # 0.5 to 1.0
        else:
            # Over budget - penalty based on how far over
            excess_ratio = (property_price - profile_budget) / profile_budget
            return max(0, 0.5 - excess_ratio)
    
    def _calculate_type_match(self, profile: Dict[str, Any], property_data: Dict[str, Any]) -> float:
        """Calculate property type preference match"""
        preferred_types = profile.get("preferred_property_types", [])
        actual_type = property_data.get("property_type")
        
        if not preferred_types or not actual_type:
            return 0.5
        
        if actual_type in preferred_types:
            return 1.0
        elif any(pt in actual_type for pt in preferred_types):
            return 0.7
        else:
            return 0.3
    
    def _calculate_location_match(self, profile: Dict[str, Any], listing: Dict[str, Any]) -> float:
        """Calculate location preference match"""
        preferred_locations = profile.get("preferred_locations", [])
        property_address = listing["property_data"].get("address", "")
        enrichment = listing.get("enrichment_data", {})
        
        if not preferred_locations:
            return 0.5
        
        # Check if address contains any preferred location keywords
        address_match = any(loc.lower() in property_address.lower() for loc in preferred_locations)
        if address_match:
            return 1.0
        
        # Check proximity to preferred amenities
        proximity_score = 0.0
        preferred_amenities = profile.get("preferred_amenities", [])
        if preferred_amenities and enrichment.get("proximity"):
            for amenity in preferred_amenities:
                if amenity in enrichment["proximity"].get("amenities", {}):
                    distance = enrichment["proximity"]["amenities"][amenity]
                    proximity_score += max(0, 1.0 - (distance / 5.0))  # 1.0 if very close, 0 if >5km
            
            proximity_score /= len(preferred_amenities)
        
        return max(0.3, proximity_score)
    
    def _calculate_amenities_match(self, profile: Dict[str, Any], property_data: Dict[str, Any]) -> float:
        """Calculate amenities match score"""
        required_amenities = profile.get("required_amenities", [])
        preferred_amenities = profile.get("preferred_amenities", [])
        property_amenities = property_data.get("amenities", [])
        
        if not required_amenities and not preferred_amenities:
            return 0.5
        
        # Check required amenities
        missing_required = [amenity for amenity in required_amenities if amenity not in property_amenities]
        if missing_required:
            return 0.0  # Fail if required amenities are missing
        
        # Score preferred amenities
        preferred_score = 0.0
        for amenity in preferred_amenities:
            if amenity in property_amenities:
                preferred_score += 1.0
        
        if preferred_amenities:
            preferred_score /= len(preferred_amenities)
        
        return 0.5 + (preferred_score * 0.5)  # 0.5 to 1.0
    
    def _generate_match_explanation(self, profile: Dict[str, Any], listing: Dict[str, Any], score: float) -> str:
        """Generate human-readable match explanation"""
        reasons = []
        property_data = listing["property_data"]
        
        # Budget explanation
        budget = profile.get("max_budget")
        price = property_data.get("price")
        if budget and price:
            if price <= budget:
                reasons.append(f"Within your budget (${price:,.0f} ≤ ${budget:,.0f})")
            else:
                reasons.append(f"Slightly above budget (${price:,.0f} > ${budget:,.0f})")
        
        # Property type explanation
        preferred_types = profile.get("preferred_property_types", [])
        actual_type = property_data.get("property_type")
        if preferred_types and actual_type:
            if actual_type in preferred_types:
                reasons.append(f"Matches your preferred property type ({actual_type})")
            else:
                reasons.append(f"Property type: {actual_type}")
        
        # Location explanation
        preferred_locations = profile.get("preferred_locations", [])
        if preferred_locations:
            address = property_data.get("address", "")
            if any(loc.lower() in address.lower() for loc in preferred_locations):
                reasons.append("In your preferred location")
        
        if not reasons:
            reasons.append("Good overall match based on your preferences")
        
        return ". ".join(reasons) + f". Match score: {score:.0%}"

class LeaseAgent(BaseAgent):
    """Handles lease document generation and management"""
    
    async def execute(self, listing_id: str, applicant_id: str, terms: Dict[str, Any]) -> Dict[str, Any]:
        """Create lease draft"""
        try:
            # Validate inputs
            validation_result = self._validate_lease_terms(terms)
            if not validation_result["is_valid"]:
                return {
                    "clauses": {},
                    "schedule": {},
                    "risks": validation_result["errors"]
                }
            
            # Get listing and applicant data
            listing = self._get_listing(listing_id)
            applicant = self._get_applicant(applicant_id)
            
            if not listing or not applicant:
                return {"error": "Listing or applicant not found"}
            
            # Generate lease clauses
            clauses = self._generate_lease_clauses(listing, applicant, terms)
            
            # Create payment schedule
            schedule = self._generate_payment_schedule(terms)
            
            # Risk assessment
            risks = self._assess_lease_risks(applicant, terms)
            
            return {
                "clauses": clauses,
                "schedule": schedule,
                "risks": risks
            }
            
        except Exception as e:
            logger.error(f"LeaseAgent error: {str(e)}")
            return {"error": str(e)}
    
    def _validate_lease_terms(self, terms: Dict[str, Any]) -> Dict[str, Any]:
        """Validate lease terms"""
        errors = []
        warnings = []
        
        required_fields = ["start_date", "duration_months", "monthly_rent", "security_deposit"]
        for field in required_fields:
            if field not in terms:
                errors.append(f"Missing required field: {field}")
        
        # Date validation
        if "start_date" in terms:
            try:
                start_date = datetime.fromisoformat(terms["start_date"].replace('Z', '+00:00'))
                if start_date < datetime.now():
                    warnings.append("Start date is in the past")
            except (ValueError, TypeError):
                errors.append("Invalid start date format")
        
        # Rent validation
        if "monthly_rent" in terms:
            try:
                rent = float(terms["monthly_rent"])
                if rent <= 0:
                    errors.append("Rent must be positive")
            except (ValueError, TypeError):
                errors.append("Invalid rent format")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _get_listing(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """Get listing from database"""
        listing = self.db_session.query(Listing).filter(Listing.id == listing_id).first()
        return listing.property_data if listing else None
    
    def _get_applicant(self, applicant_id: str) -> Optional[Dict[str, Any]]:
        """Get applicant data (simplified)"""
        # In real implementation, this would query user database
        return {
            "id": applicant_id,
            "credit_score": np.random.randint(600, 800),
            "employment_status": "employed",
            "income": np.random.uniform(3000, 10000)
        }
    
    def _generate_lease_clauses(self, listing: Dict[str, Any], applicant: Dict[str, Any], terms: Dict[str, Any]) -> Dict[str, Any]:
        """Generate lease agreement clauses"""
        clauses = {
            "parties": {
                "landlord": "Mwarokin Properties",
                "tenant": applicant.get("name", "Tenant")
            },
            "property": {
                "address": listing.get("address"),
                "description": f"{listing.get('bedrooms', 0)} bedroom {listing.get('property_type')}"
            },
            "term": {
                "start_date": terms["start_date"],
                "duration_months": terms["duration_months"]
            },
            "rent": {
                "monthly_amount": terms["monthly_rent"],
                "due_date": "1st of each month"
            },
            "deposit": {
                "amount": terms["security_deposit"],
                "return_terms": "Within 30 days of lease termination, less any deductions"
            },
            "utilities": "Tenant responsible for all utilities unless otherwise specified",
            "maintenance": "Landlord responsible for structural repairs, tenant for minor maintenance"
        }
        
        return clauses
    
    def _generate_payment_schedule(self, terms: Dict[str, Any]) -> Dict[str, Any]:
        """Generate payment schedule"""
        try:
            start_date = datetime.fromisoformat(terms["start_date"].replace('Z', '+00:00'))
            duration = int(terms["duration_months"])
            monthly_rent = float(terms["monthly_rent"])
            
            schedule = {}
            current_date = start_date
            
            for month in range(duration):
                due_date = current_date.replace(day=1)
                schedule[due_date.isoformat()] = {
                    "amount": monthly_rent,
                    "type": "rent",
                    "status": "pending"
                }
                current_date += timedelta(days=30)  # Approximate
            
            return schedule
            
        except (ValueError, TypeError):
            return {"error": "Invalid terms for payment schedule"}
    
    def _assess_lease_risks(self, applicant: Dict[str, Any], terms: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Assess potential risks in the lease agreement"""
        risks = []
        
        # Income to rent ratio check
        income = applicant.get("income", 0)
        monthly_rent = float(terms.get("monthly_rent", 0))
        
        if income > 0 and monthly_rent > 0:
            ratio = monthly_rent / income
            if ratio > 0.3:
                risks.append({
                    "type": "financial",
                    "severity": "high",
                    "description": f"Rent represents {ratio:.0%} of tenant's income (recommended ≤30%)"
                })
            elif ratio > 0.4:
                risks.append({
                    "type": "financial",
                    "severity": "critical",
                    "description": f"Rent represents {ratio:.0%} of tenant's income (high risk of default)"
                })
        
        # Credit score check
        credit_score = applicant.get("credit_score", 0)
        if credit_score < 600:
            risks.append({
                "type": "credit",
                "severity": "high",
                "description": f"Low credit score ({credit_score}) may indicate payment risk"
            })
        
        # Lease duration risk
        duration = int(terms.get("duration_months", 12))
        if duration < 6:
            risks.append({
                "type": "operational",
                "severity": "medium",
                "description": "Short lease duration may lead to frequent turnover"
            })
        
        return risks

# Additional agents would be implemented similarly...
# ComplianceAgent, WhiteLabelAgent, RAG_Agent, AnalyticsAgent, etc.

# Orchestrator / Supervisor
class MwarokinOrchestrator:
    """Main orchestrator that coordinates all agents"""
    
    def __init__(self):
        self.agents = {
            "listing": ListingAgent,
            "valuation": ValuationAgent,
            "matchmaking": MatchmakingAgent,
            "lease": LeaseAgent,
            # Add other agents here
        }
        self.redis = redis_client
        self.db_session = SessionLocal()
    
    async def process_request(self, agent_type: str, tenant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process request through appropriate agent"""
        # Validate tenant access
        if not self._validate_tenant_access(tenant_id):
            return {"error": "Tenant not authorized"}
        
        # Get agent class
        agent_class = self.agents.get(agent_type)
        if not agent_class:
            return {"error": f"Unknown agent type: {agent_type}"}
        
        # Create and execute agent
        agent = agent_class(tenant_id)
        result = await agent.execute(**payload)
        
        # Log the operation
        self._log_operation(tenant_id, agent_type, payload, result)
        
        return result
    
    def _validate_tenant_access(self, tenant_id: str) -> bool:
        """Validate that tenant exists and is active"""
        tenant = self.db_session.query(Tenant).filter(
            Tenant.id == tenant_id,
            Tenant.is_active == True
        ).first()
        return tenant is not None
    
    def _log_operation(self, tenant_id: str, agent_type: str, payload: Dict[str, Any], result: Dict[str, Any]):
        """Log operation for audit trail"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "agent_type": agent_type,
            "payload": payload,
            "result": result,
            "status": "success" if "error" not in result else "error"
        }
        
        self.redis.rpush(f"operations:{tenant_id}", json.dumps(log_entry))
        
        # Also store in database for long-term persistence
        # (implementation would depend on your database schema)

# FastAPI Application
app = FastAPI(title="Mwarokin Real Estate Agentic OS", version="1.0.0")

# Dependency to get current user from JWT token
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        user = SessionLocal().query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

# Dependency to get orchestrator
def get_orchestrator():
    return MwarokinOrchestrator()

# API Routes
@app.post("/api/{agent_type}")
async def process_agent_request(
    agent_type: str,
    payload: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    orchestrator: MwarokinOrchestrator = Depends(get_orchestrator)
):
    """Process request through specified agent"""
    result = await orchestrator.process_request(agent_type, current_user.tenant_id, payload)
    return JSONResponse(content=result)
