
import uuid
import json
import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from flask import Flask, request, jsonify, g
import threading
import logging
from functools import wraps

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Mwarokin")

# Database setup
Base = declarative_base()

class Tenant(Base):
    __tablename__ = 'tenants'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    config = Column(JSON, default={})  # White-label settings, feature flags, etc.
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey('tenants.id'), nullable=False)
    email = Column(String, nullable=False)
    role = Column(String, nullable=False)  # admin, agent, viewer, etc.
    permissions = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class PropertyListing(Base):
    __tablename__ = 'property_listings'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey('tenants.id'), nullable=False)
    raw_data = Column(JSON, nullable=False)
    normalized_data = Column(JSON, nullable=False)
    status = Column(String, default="pending")  # pending, validated, rejected, sold, etc.
    validation_warnings = Column(JSON, default=[])
    enrichment_data = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class Valuation(Base):
    __tablename__ = 'valuations'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey('tenants.id'), nullable=False)
    listing_id = Column(String, ForeignKey('property_listings.id'), nullable=False)
    range_low = Column(Float, nullable=False)
    range_high = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    comp_ids = Column(JSON, default=[])
    reasoning = Column(String, nullable=False)
    sources = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Lead(Base):
    __tablename__ = 'leads'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey('tenants.id'), nullable=False)
    contact_info = Column(JSON, nullable=False)
    bant_score = Column(JSON, default={})  # Budget, Authority, Need, Timeline
    status = Column(String, default="new")
    assigned_to = Column(String, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

# Create database engine
engine = create_engine('sqlite:///mwarokin.db', pool_size=20, max_overflow=0)
Base.metadata.create_all(engine)
Session = scoped_session(sessionmaker(bind=engine))

# Flask app setup
app = Flask(__name__)

# Tenant context management
def with_tenant(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        tenant_id = request.headers.get('X-Tenant-ID') or request.args.get('tenant_id')
        if not tenant_id:
            return jsonify({"error": "Tenant ID required"}), 400
        
        session = Session()
        tenant = session.query(Tenant).filter(Tenant.id == tenant_id, Tenant.is_active == True).first()
        if not tenant:
            Session.remove()
            return jsonify({"error": "Invalid tenant ID"}), 404
        
        g.tenant_id = tenant_id
        g.tenant_config = tenant.config
        result = f(*args, **kwargs)
        Session.remove()
        return result
    return decorated_function

# Base Agent class
class Agent:
    def __init__(self, name):
        self.name = name
        self.session = Session()
    
    def __del__(self):
        self.session.close()

# Specialized Agents
class ListingAgent(Agent):
    def __init__(self):
        super().__init__("ListingAgent")
    
    def intake(self, payload: Dict) -> Dict:
        """Intake, normalize, and validate property listings"""
        try:
            # Basic validation
            required_fields = ['address', 'property_type', 'price', 'square_footage']
            missing_fields = [field for field in required_fields if field not in payload]
            
            if missing_fields:
                return {
                    "status": "rejected",
                    "warnings": [f"Missing required field: {field}" for field in missing_fields]
                }
            
            # Normalize data
            normalized_data = self._normalize_listing_data(payload)
            
            # Validate data
            validation_warnings = self._validate_listing_data(normalized_data)
            
            # Create listing record
            listing = PropertyListing(
                tenant_id=g.tenant_id,
                raw_data=payload,
                normalized_data=normalized_data,
                validation_warnings=validation_warnings,
                status="pending" if not validation_warnings else "needs_review"
            )
            
            self.session.add(listing)
            self.session.commit()
            
            # Start enrichment process in background
            threading.Thread(target=self._enrich_listing, args=(listing.id,)).start()
            
            return {
                "status": "success",
                "listing_id": listing.id,
                "warnings": validation_warnings,
                "normalized_fields": normalized_data
            }
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Listing intake error: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _normalize_listing_data(self, data: Dict) -> Dict:
        """Normalize listing data to standard format"""
        normalized = data.copy()
        
        # Standardize property type
        prop_type_map = {
            'house': 'residential', 'apartment': 'residential', 'condo': 'residential',
            'commercial': 'commercial', 'office': 'commercial', 'retail': 'commercial',
            'land': 'land', 'plot': 'land'
        }
        
        if 'property_type' in normalized:
            normalized['property_type'] = prop_type_map.get(
                normalized['property_type'].lower(), 
                normalized['property_type']
            )
        
        # Standardize price to float
        if 'price' in normalized:
            if isinstance(normalized['price'], str):
                normalized['price'] = float(normalized['price'].replace('$', '').replace(',', ''))
        
        return normalized
    
    def _validate_listing_data(self, data: Dict) -> List[str]:
        """Validate listing data and return warnings"""
        warnings = []
        
        # Price validation
        if 'price' in data:
            if data['price'] <= 0:
                warnings.append("Price must be positive")
            elif data['property_type'] == 'residential' and data['price'] > 10000000:  # $10M threshold
                warnings.append("Price seems unusually high for residential property")
        
        # Square footage validation
        if 'square_footage' in data:
            if data['square_footage'] <= 0:
                warnings.append("Square footage must be positive")
            elif data['square_footage'] > 100000:  # 100k sqft threshold
                warnings.append("Square footage seems unusually large")
        
        return warnings
    
    def _enrich_listing(self, listing_id: str):
        """Enrich listing with external data (geocoding, walkscore, etc.)"""
        try:
            listing = self.session.query(PropertyListing).filter(PropertyListing.id == listing_id).first()
            if not listing:
                return
            
            # Simulate external API calls for enrichment
            enrichment_data = {
                "geocoding": {"lat": 40.7128, "lng": -74.0060},  # Simulated coordinates
                "walkscore": 75,
                "transit_score": 65,
                "schools": [{"name": "Nearby School", "rating": 8, "distance_km": 1.2}],
                "amenities": ["park", "grocery", "public_transport"],
                "enriched_at": datetime.datetime.utcnow().isoformat()
            }
            
            listing.enrichment_data = enrichment_data
            self.session.commit()
            
        except Exception as e:
            logger.error(f"Enrichment error for listing {listing_id}: {str(e)}")

class ValuationAgent(Agent):
    def __init__(self):
        super().__init__("ValuationAgent")
    
    def request_valuation(self, listing_id: str = None, address: str = None) -> Dict:
        """Generate property valuation using CMA/AVM approach"""
        try:
            if not listing_id and not address:
                return {"error": "Either listing_id or address must be provided"}
            
            # Get listing data
            if listing_id:
                listing = self.session.query(PropertyListing).filter(
                    PropertyListing.id == listing_id, 
                    PropertyListing.tenant_id == g.tenant_id
                ).first()
            else:
                # In a real implementation, we'd look up by address
                listing = None
            
            if not listing:
                return {"error": "Listing not found"}
            
            # Get comparable properties (simulated)
            comps = self._find_comps(listing.normalized_data)
            
            # Calculate valuation (simulated algorithm)
            valuation = self._calculate_valuation(listing.normalized_data, comps)
            
            # Create valuation record
            valuation_record = Valuation(
                tenant_id=g.tenant_id,
                listing_id=listing.id,
                range_low=valuation["range_low"],
                range_high=valuation["range_high"],
                confidence=valuation["confidence"],
                comp_ids=valuation["comp_ids"],
                reasoning=valuation["reasoning"],
                sources=valuation["sources"]
            )
            
            self.session.add(valuation_record)
            self.session.commit()
            
            return {
                "range_low": valuation["range_low"],
                "range_high": valuation["range_high"],
                "confidence": valuation["confidence"],
                "comp_ids": valuation["comp_ids"],
                "reasoning": valuation["reasoning"],
                "sources": valuation["sources"]
            }
            
        except Exception as e:
            logger.error(f"Valuation error: {str(e)}")
            return {"error": str(e)}
    
    def _find_comps(self, listing_data: Dict) -> List[Dict]:
        """Find comparable properties (simulated)"""
        # In a real implementation, this would query a database of recent sales
        # and similar properties based on location, features, etc.
        
        comps = [
            {
                "id": str(uuid.uuid4()),
                "address": "123 Comp St",
                "price": listing_data.get("price", 500000) * 0.9,
                "square_footage": listing_data.get("square_footage", 2000) * 0.95,
                "sold_date": (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "address": "456 Comp Ave",
                "price": listing_data.get("price", 500000) * 1.1,
                "square_footage": listing_data.get("square_footage", 2000) * 1.05,
                "sold_date": (datetime.datetime.now() - datetime.timedelta(days=45)).isoformat()
            }
        ]
        
        return comps
    
    def _calculate_valuation(self, listing_data: Dict, comps: List[Dict]) -> Dict:
        """Calculate property valuation based on comps"""
        # Simple averaging algorithm for demonstration
        # Real implementation would use more sophisticated modeling
        
        comp_prices = [comp["price"] for comp in comps]
        avg_price = sum(comp_prices) / len(comp_prices)
        
        # Adjust based on property features
        adjustment_factors = {
            "square_footage": 0.0005,  # $ per sqft
            "bedrooms": 0.05,  # 5% per bedroom
            "bathrooms": 0.03,  # 3% per bathroom
        }
        
        adjusted_price = avg_price
        
        for feature, factor in adjustment_factors.items():
            if feature in listing_data:
                comp_avg = sum(comp.get(feature, 0) for comp in comps) / len(comps)
                diff = listing_data[feature] - comp_avg
                adjusted_price += adjusted_price * factor * diff
        
        # Apply market conditions (simulated)
        market_factor = 1.05  # 5% appreciation
        
        # Calculate range and confidence
        range_percent = 0.1  # 10% range
        range_low = adjusted_price * market_factor * (1 - range_percent/2)
        range_high = adjusted_price * market_factor * (1 + range_percent/2)
        
        # Confidence based on number and recency of comps
        confidence = min(0.95, 0.7 + (len(comps) * 0.1))
        
        return {
            "range_low": round(range_low, 2),
            "range_high": round(range_high, 2),
            "confidence": confidence,
            "comp_ids": [comp["id"] for comp in comps],
            "reasoning": f"Based on {len(comps)} comparable properties with adjustments for property features",
            "sources": ["internal_comps_db", "market_trends_api"]
        }

class MatchmakingAgent(Agent):
    def __init__(self):
        super().__init__("MatchmakingAgent")
    
    def find_matches(self, profile: Dict) -> Dict:
        """Find property matches for a buyer/tenant profile"""
        try:
            # Get active listings for tenant
            listings = self.session.query(PropertyListing).filter(
                PropertyListing.tenant_id == g.tenant_id,
                PropertyListing.status.in_(["validated", "active"])
            ).all()
            
            # Calculate match scores
            matches = []
            for listing in listings:
                score = self._calculate_match_score(profile, listing.normalized_data)
                if score > 0.5:  # Threshold for matches
                    matches.append({
                        "listing_id": listing.id,
                        "score": score,
                        "explanation": self._generate_explanation(profile, listing.normalized_data, score)
                    })
            
            # Sort by score descending
            matches.sort(key=lambda x: x["score"], reverse=True)
            
            return {"matches": matches}
            
        except Exception as e:
            logger.error(f"Matchmaking error: {str(e)}")
            return {"error": str(e)}
    
    def _calculate_match_score(self, profile: Dict, listing: Dict) -> float:
        """Calculate match score between profile and listing"""
        score = 0.0
        max_score = 0.0
        
        # Budget match
        if "max_budget" in profile and "price" in listing:
            max_score += 1.0
            if listing["price"] <= profile["max_budget"]:
                budget_ratio = listing["price"] / profile["max_budget"]
                score += 1.0 - (0.5 * budget_ratio)  # Prefer properties well under budget
        
        # Property type match
        if "preferred_property_types" in profile and "property_type" in listing:
            max_score += 1.0
            if listing["property_type"] in profile["preferred_property_types"]:
                score += 1.0
        
        # Size match
        if "min_size" in profile and "square_footage" in listing:
            max_score += 1.0
            if listing["square_footage"] >= profile["min_size"]:
                size_ratio = profile["min_size"] / listing["square_footage"]
                score += size_ratio  # Closer to minimum is better
        
        # Location match (simplified)
        if "preferred_locations" in profile and "address" in listing:
            max_score += 1.0
            # In real implementation, we'd do geographic proximity calculation
            # For demo, we'll just check if any preferred location is in address
            for loc in profile["preferred_locations"]:
                if loc.lower() in listing["address"].lower():
                    score += 1.0
                    break
        
        return score / max_score if max_score > 0 else 0.0
    
    def _generate_explanation(self, profile: Dict, listing: Dict, score: float) -> str:
        """Generate human-readable explanation for match"""
        reasons = []
        
        if "max_budget" in profile and "price" in listing:
            if listing["price"] <= profile["max_budget"]:
                reasons.append(f"Within budget (${listing['price']:,.0f} ≤ ${profile['max_budget']:,.0f})")
            else:
                reasons.append(f"Over budget (${listing['price']:,.0f} > ${profile['max_budget']:,.0f})")
        
        if "preferred_property_types" in profile and "property_type" in listing:
            if listing["property_type"] in profile["preferred_property_types"]:
                reasons.append(f"Matches preferred type: {listing['property_type']}")
        
        if "min_size" in profile and "square_footage" in listing:
            if listing["square_footage"] >= profile["min_size"]:
                reasons.append(f"Meets size requirement: {listing['square_footage']} ≥ {profile['min_size']} sqft")
        
        return f"Score: {score:.2f}. " + "; ".join(reasons)

class LeadCRM_Agent(Agent):
    def __init__(self):
        super().__init__("LeadCRM_Agent")
    
    def capture_lead(self, contact_info: Dict, source: str = "web") -> Dict:
        """Capture a new lead and calculate BANT score"""
        try:
            # Calculate BANT score
            bant_score = self._calculate_bant_score(contact_info)
            
            # Create lead record
            lead = Lead(
                tenant_id=g.tenant_id,
                contact_info=contact_info,
                bant_score=bant_score,
                status="new"
            )
            
            self.session.add(lead)
            self.session.commit()
            
            # Auto-assign based on rules
            self._auto_assign_lead(lead)
            
            return {
                "lead_id": lead.id,
                "bant_score": bant_score,
                "status": lead.status
            }
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Lead capture error: {str(e)}")
            return {"error": str(e)}
    
    def _calculate_bant_score(self, contact_info: Dict) -> Dict:
        """Calculate BANT (Budget, Authority, Need, Timeline) score"""
        # Simplified scoring for demonstration
        score = {
            "budget": 0.0,
            "authority": 0.0,
            "need": 0.0,
            "timeline": 0.0,
            "overall": 0.0
        }
        
        # Budget score based on provided information
        if "budget" in contact_info:
            score["budget"] = 0.8 if contact_info["budget"] > 0 else 0.2
        elif "income" in contact_info:
            score["budget"] = 0.6 if contact_info["income"] > 0 else 0.2
        else:
            score["budget"] = 0.1
        
        # Authority score (simplified)
        score["authority"] = 0.7  # Assume most leads have some authority
        
        # Need score based on urgency indicators
        need_keywords = ["urgent", "asap", "immediately", "soon"]
        message = contact_info.get("message", "").lower()
        score["need"] = 0.9 if any(keyword in message for keyword in need_keywords) else 0.5
        
        # Timeline score
        timeline = contact_info.get("timeline", "").lower()
        if "month" in timeline:
            score["timeline"] = 0.8
        elif "week" in timeline:
            score["timeline"] = 0.9
        elif "day" in timeline:
            score["timeline"] = 1.0
        else:
            score["timeline"] = 0.3
        
        # Overall score (weighted average)
        weights = {"budget": 0.3, "authority": 0.2, "need": 0.3, "timeline": 0.2}
        score["overall"] = sum(score[component] * weights[component] for component in weights)
        
        return score
    
    def _auto_assign_lead(self, lead: Lead):
        """Auto-assign lead based on rules and availability"""
        # In a real implementation, this would use round-robin, skills-based,
        # or load-based assignment logic
        
        # For demo, just assign to first available user
        users = self.session.query(User).filter(
            User.tenant_id == g.tenant_id,
            User.role.in_(["agent", "broker"])
        ).all()
        
        if users:
            lead.assigned_to = users[0].id
            lead.status = "assigned"
            self.session.commit()

# Flask API endpoints
@app.route('/api/listings/intake', methods=['POST'])
@with_tenant
def intake_listing():
    """Endpoint for listing intake"""
    data = request.get_json()
    agent = ListingAgent()
    result = agent.intake(data)
    return jsonify(result)

@app.route('/api/valuation/request', methods=['POST'])
@with_tenant
def request_valuation():
    """Endpoint for valuation requests"""
    data = request.get_json()
    agent = ValuationAgent()
    result = agent.request_valuation(
        listing_id=data.get('listing_id'),
        address=data.get('address')
    )
    return jsonify(result)

@app.route('/api/matchmaking/find', methods=['POST'])
@with_tenant
def find_matches():
    """Endpoint for matchmaking"""
    data = request.get_json()
    agent = MatchmakingAgent()
    result = agent.find_matches(data.get('profile', {}))
    return jsonify(result)

@app.route('/api/leads/capture', methods=['POST'])
@with_tenant
def capture_lead():
    """Endpoint for lead capture"""
    data = request.get_json()
    agent = LeadCRM_Agent()
    result = agent.capture_lead(
        contact_info=data.get('contact_info', {}),
        source=data.get('source', 'web')
    )
    return jsonify(result)

# System initialization
def initialize_system():
    """Initialize the system with a default tenant"""
    session = Session()
    
    # Check if default tenant exists
    default_tenant = session.query(Tenant).filter(Tenant.name == "Default Tenant").first()
    
    if not default_tenant:
        # Create default tenant
        default_tenant = Tenant(
            name="Default Tenant",
            config={
                "theme": {
                    "primary_color": "#3498db",
                    "secondary_color": "#2ecc71",
                    "logo_url": "/static/logo.png"
                },
                "features": {
                    "valuation": True,
                    "matchmaking": True,
                    "lead_management": True
                },
                "locale": "en_US",
                "currency": "USD"
            }
        )
        session.add(default_tenant)
        session.commit()
        
        # Create default admin user
        admin_user = User(
            tenant_id=default_tenant.id,
            email="admin@example.com",
            role="admin",
            permissions={"all": True}
        )
        session.add(admin_user)
        session.commit()
        
        logger.info("Default tenant and admin user created")
    
    session.close()

# Main execution
if __name__ == '__main__':
    # Initialize the system
    initialize_system()
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
```

This implementation provides:

1. **Multi-tenancy Support**: Each request is tenant-scoped with proper isolation
2. **Specialized Agents**: 
   - ListingAgent for property intake and validation
   - ValuationAgent for property valuation using comps
   - MatchmakingAgent for matching buyers/tenants with properties
   - LeadCRM_Agent for lead capture and scoring

3. **Database Models**: For tenants, users, listings, valuations, and leads
4. **API Endpoints**: For all major operations
5. **Security**: Tenant isolation and basic validation
6. **Extensibility**: Easy to add more agents and functionality

To use this system:

1. Run the script to initialize the database and start the server
2. Use the API endpoints with the `X-Tenant-ID` header or `tenant_id` parameter
3. Extend with additional agents as needed (LeaseAgent, ComplianceAgent, etc.)

The implementation follows modern Python practices and includes proper error handling, logging, and documentation. You can extend it with the other agents mentioned in your requirements following the same pattern.