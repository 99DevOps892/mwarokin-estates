import os
import json
import logging
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from enum import Enum
from functools import wraps
import re
import hashlib

from flask import Flask, request, jsonify, render_template, session, Response
from flask_cors import CORS
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
import numpy as np
from pydantic import BaseModel, Field, validator
import redis

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('mwarokin')

# Initialize Flask application
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'mwarokin-secure-key-2024')
CORS(app)

# Redis for caching and session management
redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    db=0,
    decode_responses=True
)

# Database simulation (in production, use PostgreSQL/MongoDB)
class Database:
    def __init__(self):
        self.users = {}
        self.properties = {}
        self.listings = {}
        self.tenants = {}
        self.leads = {}
        self.leases = {}
        self.transactions = {}
        self.audit_logs = []
        
    def log_audit(self, action: str, user_id: str, tenant_id: str, details: Dict):
        log_entry = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'user_id': user_id,
            'tenant_id': tenant_id,
            'details': details
        }
        self.audit_logs.append(log_entry)
        return log_entry

db = Database()

# Pydantic models for type validation
class ListingData(BaseModel):
    title: str
    description: str
    property_type: str
    location: str
    price: float
    currency: str = "USD"
    status: str  # "for rent", "for sale", "for buy"
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    area: Optional[float] = None
    features: List[str] = []
    images: List[str] = []
    coordinates: Optional[Dict[str, float]] = None

class ValuationRequest(BaseModel):
    listing_id: Optional[str] = None
    address: Optional[str] = None
    property_type: str
    location: str
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    area: Optional[float] = None
    features: List[str] = []

class MatchmakingProfile(BaseModel):
    budget_min: float
    budget_max: float
    preferred_locations: List[str]
    property_types: List[str]
    min_bedrooms: Optional[int] = None
    min_bathrooms: Optional[int] = None
    min_area: Optional[float] = None
    must_have_features: List[str] = []
    preferred_features: List[str] = []

class LeaseTerms(BaseModel):
    start_date: str
    duration_months: int
    monthly_rent: float
    security_deposit: float
    utilities_included: bool
    special_terms: List[str] = []

# Authentication and authorization decorators
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'message': 'Bearer token is missing'}), 401
        
        try:
            token = token.split(' ')[1]
            payload = jwt.decode(token, app.secret_key, algorithms=['HS256'])
            current_user = db.users.get(payload['user_id'])
            if not current_user:
                return jsonify({'message': 'User not found'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

def tenant_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        tenant_id = request.headers.get('X-Tenant-ID') or request.args.get('tenant_id')
        if not tenant_id or tenant_id not in db.tenants:
            return jsonify({'message': 'Valid tenant ID required'}), 400
        return f(tenant_id, *args, **kwargs)
    return decorated

def role_required(required_roles: List[str]):
    def decorator(f):
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            if current_user.get('role') not in required_roles:
                return jsonify({'message': 'Insufficient permissions'}), 403
            return f(current_user, *args, **kwargs)
        return decorated
    return decorator

# Utility functions
def validate_listing_data(data: Dict) -> Tuple[bool, List[str]]:
    errors = []
    required_fields = ['title', 'property_type', 'location', 'price', 'status']
    
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"Missing required field: {field}")
    
    valid_property_types = ['apartment', 'villa', 'house', 'office', 'building', 
                           'townhouse', 'shop', 'flat', 'land', 'estate', 'garage']
    if data.get('property_type') not in valid_property_types:
        errors.append(f"Invalid property type. Must be one of: {', '.join(valid_property_types)}")
    
    valid_statuses = ['for rent', 'for sale', 'for buy']
    if data.get('status') not in valid_statuses:
        errors.append(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    return len(errors) == 0, errors

def get_tenant_context(tenant_id: str) -> Dict:
    tenant = db.tenants.get(tenant_id, {})
    return {
        'tenant_id': tenant_id,
        'branding': tenant.get('settings', {}),
        'features': tenant.get('features', []),
        'locale': tenant.get('settings', {}).get('locale', 'en-US'),
        'currency': tenant.get('settings', {}).get('currency', 'USD'),
        'compliance_rules': tenant.get('compliance_rules', {})
    }

def redact_pii(data: Dict) -> Dict:
    """Redact personally identifiable information for logging"""
    redacted = data.copy()
    pii_fields = ['email', 'phone', 'ssn', 'password', 'credit_card', 'address']
    
    for field in pii_fields:
        if field in redacted:
            redacted[field] = '***REDACTED***'
    
    return redacted

# Agent Base Class
class BaseAgent:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.redis = redis_client
    
    def log_activity(self, action: str, tenant_id: str, details: Dict):
        """Log agent activity for audit purposes"""
        log_entry = {
            'agent': self.agent_name,
            'action': action,
            'timestamp': datetime.utcnow().isoformat(),
            'tenant_id': tenant_id,
            'details': redact_pii(details)
        }
        self.redis.rpush(f'agent_logs:{tenant_id}', json.dumps(log_entry))
    
    def plan_execute_reflect(self, task: str, tenant_context: Dict, *args, **kwargs):
        """ReAct-style planning and execution loop"""
        # Plan phase
        plan = self._create_plan(task, tenant_context, *args, **kwargs)
        self.log_activity('plan_created', tenant_context['tenant_id'], {'plan': plan})
        
        # Execute phase
        result = self._execute_plan(plan, tenant_context, *args, **kwargs)
        
        # Reflect phase
        reflection = self._reflect_on_execution(plan, result, tenant_context)
        self.log_activity('execution_reflection', tenant_context['tenant_id'], {'reflection': reflection})
        
        return result
    
    def _create_plan(self, task: str, tenant_context: Dict, *args, **kwargs) -> List[Dict]:
        """Create execution plan for a task"""
        # This would be implemented with LLM planning in a real system
        return [{'step': 1, 'action': 'process_task', 'parameters': kwargs}]
    
    def _execute_plan(self, plan: List[Dict], tenant_context: Dict, *args, **kwargs) -> Any:
        """Execute the planned steps"""
        # Simplified implementation - real system would execute each step
        try:
            return self.process_task(tenant_context, *args, **kwargs)
        except Exception as e:
            logger.error(f"Execution failed: {str(e)}")
            raise
    
    def _reflect_on_execution(self, plan: List[Dict], result: Any, tenant_context: Dict) -> Dict:
        """Reflect on execution results and improve future plans"""
        return {
            'success': True,
            'improvements': [],
            'lessons_learned': []
        }
    
    def process_task(self, tenant_context: Dict, *args, **kwargs):
        """To be implemented by specific agents"""
        raise NotImplementedError("Subclasses must implement process_task")

# Specialized Agents
class ListingAgent(BaseAgent):
    def __init__(self):
        super().__init__('ListingAgent')
    
    def intake(self, payload: Dict, tenant_context: Dict) -> Dict:
        """Process property listing intake"""
        self.log_activity('listing_intake_start', tenant_context['tenant_id'], {'payload': payload})
        
        # Validate input
        is_valid, errors = validate_listing_data(payload)
        if not is_valid:
            return {'status': 'error', 'errors': errors}
        
        # Normalize and enrich data
        normalized = self._normalize_listing_data(payload, tenant_context)
        enriched = self._enrich_listing_data(normalized, tenant_context)
        
        # Validate media
        media_report = self._validate_media(enriched.get('images', []))
        
        result = {
            'status': 'success',
            'warnings': media_report.get('warnings', []),
            'normalized_fields': enriched,
            'media_report': media_report
        }
        
        self.log_activity('listing_intake_complete', tenant_context['tenant_id'], {'result': result})
        return result
    
    def _normalize_listing_data(self, data: Dict, tenant_context: Dict) -> Dict:
        """Normalize listing data to standard format"""
        normalized = data.copy()
        
        # Standardize property type
        property_type_map = {
            'apt': 'apartment', 'flat': 'apartment', 'condo': 'apartment',
            'villa': 'villa', 'house': 'house', 'home': 'house',
            'office': 'office', 'commercial': 'office',
            'land': 'land', 'plot': 'land'
        }
        normalized['property_type'] = property_type_map.get(
            data['property_type'].lower(), data['property_type']
        )
        
        # Standardize currency
        normalized['currency'] = tenant_context['currency']
        
        return normalized
    
    def _enrich_listing_data(self, data: Dict, tenant_context: Dict) -> Dict:
        """Enrich listing data with additional information"""
        enriched = data.copy()
        
        # Geocoding (simplified)
        if 'location' in data and not data.get('coordinates'):
            enriched['coordinates'] = self._geocode_address(data['location'])
        
        # Add proximity scores (simplified)
        enriched['proximity_scores'] = {
            'transit': self._calculate_transit_score(data['location']),
            'schools': self._calculate_school_score(data['location']),
            'amenities': self._calculate_amenities_score(data['location'])
        }
        
        # Energy/green score if available
        if data.get('features'):
            enriched['energy_score'] = self._calculate_energy_score(data['features'])
        
        return enriched
    
    def _validate_media(self, images: List[str]) -> Dict:
        """Validate listing images"""
        # Simplified implementation - real system would analyze image quality
        return {
            'total_images': len(images),
            'valid_images': len(images),
            'warnings': [] if len(images) >= 3 else ['Recommend adding more images'],
            'quality_score': 0.8  # Placeholder
        }
    
    def _geocode_address(self, address: str) -> Dict[str, float]:
        """Simulated geocoding"""
        return {'lat': 40.7128, 'lng': -74.0060}  # Default to NYC
    
    def _calculate_transit_score(self, location: str) -> float:
        """Calculate transit accessibility score"""
        return round(np.random.uniform(0.5, 1.0), 2)
    
    def _calculate_school_score(self, location: str) -> float:
        """Calculate school proximity score"""
        return round(np.random.uniform(0.5, 1.0), 2)
    
    def _calculate_amenities_score(self, location: str) -> float:
        """Calculate amenities proximity score"""
        return round(np.random.uniform(0.5, 1.0), 2)
    
    def _calculate_energy_score(self, features: List[str]) -> float:
        """Calculate energy efficiency score"""
        green_features = ['solar_panels', 'energy_star', 'double_pane_windows', 'smart_thermostat']
        green_count = sum(1 for feature in features if feature in green_features)
        return round(green_count / len(green_features), 2) if green_features else 0.5

class ValuationAgent(BaseAgent):
    def __init__(self):
        super().__init__('ValuationAgent')
        self.comps_cache = {}
    
    def request(self, listing_id: Optional[str] = None, address: Optional[str] = None, 
                tenant_context: Dict = None) -> Dict:
        """Generate property valuation"""
        self.log_activity('valuation_request', tenant_context['tenant_id'], 
                         {'listing_id': listing_id, 'address': address})
        
        # Get property data
        property_data = self._get_property_data(listing_id, address, tenant_context)
        
        # Find comparable properties
        comps = self._find_comparables(property_data, tenant_context)
        
        # Calculate valuation
        valuation = self._calculate_valuation(property_data, comps, tenant_context)
        
        result = {
            'range_low': valuation['low'],
            'range_high': valuation['high'],
            'confidence': valuation['confidence'],
            'comp_ids': [comp['id'] for comp in comps],
            'reasoning': valuation['reasoning'],
            'sources': valuation['sources']
        }
        
        self.log_activity('valuation_complete', tenant_context['tenant_id'], {'result': result})
        return result
    
    def _get_property_data(self, listing_id: Optional[str], address: Optional[str], 
                          tenant_context: Dict) -> Dict:
        """Retrieve property data from database or external sources"""
        if listing_id and listing_id in db.listings:
            return db.listings[listing_id]
        elif address:
            # Simulate property data lookup by address
            return {
                'property_type': 'apartment',
                'location': address,
                'bedrooms': 2,
                'bathrooms': 1,
                'area': 1000,
                'features': ['parking', 'laundry']
            }
        else:
            raise ValueError("Either listing_id or address must be provided")
    
    def _find_comparables(self, property_data: Dict, tenant_context: Dict) -> List[Dict]:
        """Find comparable properties using RAG and similarity search"""
        cache_key = f"comps:{hashlib.md5(json.dumps(property_data).encode()).hexdigest()}"
        
        if cache_key in self.comps_cache:
            return self.comps_cache[cache_key]
        
        # Simulated comparable search
        comps = []
        for i in range(3):
            comps.append({
                'id': f"comp_{i}",
                'price': property_data.get('price', 100000) * (0.8 + 0.4 * np.random.random()),
                'location': property_data['location'],
                'property_type': property_data['property_type'],
                'bedrooms': property_data.get('bedrooms', 2),
                'bathrooms': property_data.get('bathrooms', 1),
                'area': property_data.get('area', 1000) * (0.9 + 0.2 * np.random.random()),
                'similarity_score': round(0.7 + 0.3 * np.random.random(), 2)
            })
        
        self.comps_cache[cache_key] = comps
        return comps
    
    def _calculate_valuation(self, property_data: Dict, comps: List[Dict], 
                           tenant_context: Dict) -> Dict:
        """Calculate property valuation based on comparables"""
        if not comps:
            return {
                'low': property_data.get('price', 100000) * 0.8,
                'high': property_data.get('price', 100000) * 1.2,
                'confidence': 0.5,
                'reasoning': 'Limited comparable data available',
                'sources': ['internal_estimation']
            }
        
        prices = [comp['price'] for comp in comps]
        avg_price = sum(prices) / len(prices)
        
        # Adjust based on property features
        adjustment = self._calculate_feature_adjustment(property_data, comps)
        adjusted_price = avg_price * adjustment
        
        confidence = min(0.9, 0.5 + 0.1 * len(comps))  # Higher confidence with more comps
        
        return {
            'low': adjusted_price * 0.9,
            'high': adjusted_price * 1.1,
            'confidence': confidence,
            'reasoning': f'Based on {len(comps)} comparable properties with adjustment for features',
            'sources': [f'comp_{i}' for i in range(len(comps))]
        }
    
    def _calculate_feature_adjustment(self, property_data: Dict, comps: List[Dict]) -> float:
        """Calculate price adjustment based on features"""
        base_adjustment = 1.0
        feature_values = {
            'parking': 1.05,
            'laundry': 1.02,
            'garden': 1.08,
            'pool': 1.15,
            'gym': 1.07
        }
        
        for feature in property_data.get('features', []):
            if feature in feature_values:
                base_adjustment *= feature_values[feature]
        
        return base_adjustment

class MatchmakingAgent(BaseAgent):
    def __init__(self):
        super().__init__('MatchmakingAgent')
    
    def request(self, profile: Dict, tenant_context: Dict) -> List[Dict]:
        """Match properties to user profile"""
        self.log_activity('matchmaking_request', tenant_context['tenant_id'], {'profile': profile})
        
        # Get available listings
        available_listings = [
            listing for listing in db.listings.values() 
            if listing.get('tenant_id') == tenant_context['tenant_id'] 
            and listing.get('status') in ['for rent', 'for sale']
        ]
        
        # Calculate matches
        matches = []
        for listing in available_listings:
            score = self._calculate_match_score(profile, listing)
            if score > 0.5:  # Minimum threshold
                matches.append({
                    'listing_id': listing['id'],
                    'score': score,
                    'explanation': self._generate_explanation(profile, listing, score)
                })
        
        # Sort by score and deduplicate
        matches.sort(key=lambda x: x['score'], reverse=True)
        matches = self._deduplicate_matches(matches)
        
        self.log_activity('matchmaking_complete', tenant_context['tenant_id'], 
                         {'matches_count': len(matches)})
        return matches
    
    def _calculate_match_score(self, profile: Dict, listing: Dict) -> float:
        """Calculate match score between profile and listing"""
        score = 0.0
        total_weight = 0
        
        # Budget match
        if 'budget_min' in profile and 'budget_max' in profile:
            price = listing.get('price', 0)
            if profile['budget_min'] <= price <= profile['budget_max']:
                score += 0.4
            total_weight += 0.4
        
        # Location match
        if 'preferred_locations' in profile and listing.get('location'):
            if listing['location'] in profile['preferred_locations']:
                score += 0.3
            total_weight += 0.3
        
        # Property type match
        if 'property_types' in profile and listing.get('property_type'):
            if listing['property_type'] in profile['property_types']:
                score += 0.2
            total_weight += 0.2
        
        # Features match
        if 'must_have_features' in profile and listing.get('features'):
            must_have_matches = sum(1 for feature in profile['must_have_features'] 
                                  if feature in listing['features'])
            if must_have_matches == len(profile['must_have_features']):
                score += 0.1
            total_weight += 0.1
        
        return score / total_weight if total_weight > 0 else 0
    
    def _generate_explanation(self, profile: Dict, listing: Dict, score: float) -> str:
        """Generate human-readable explanation for the match"""
        explanations = []
        
        if 'budget_min' in profile and 'budget_max' in profile:
            price = listing.get('price', 0)
            if profile['budget_min'] <= price <= profile['budget_max']:
                explanations.append("Within your budget range")
        
        if 'preferred_locations' in profile and listing.get('location'):
            if listing['location'] in profile['preferred_locations']:
                explanations.append("In your preferred location")
        
        return "; ".join(explanations) if explanations else "Basic match based on available criteria"
    
    def _deduplicate_matches(self, matches: List[Dict]) -> List[Dict]:
        """Remove duplicate matches for the same property"""
        seen = set()
        deduped = []
        for match in matches:
            if match['listing_id'] not in seen:
                seen.add(match['listing_id'])
                deduped.append(match)
        return deduped

class LeadCRMAgent(BaseAgent):
    def __init__(self):
        super().__init__('LeadCRMAgent')
    
    def capture_lead(self, lead_data: Dict, tenant_context: Dict) -> Dict:
        """Capture and process new lead"""
        self.log_activity('lead_capture', tenant_context['tenant_id'], {'lead_data': lead_data})
        
        # Validate lead data
        validation_result = self._validate_lead_data(lead_data, tenant_context)
        if not validation_result['valid']:
            return {'status': 'error', 'errors': validation_result['errors']}
        
        # Score lead (BANT-like methodology)
        score = self._score_lead(lead_data, tenant_context)
        
        # Route lead to appropriate agent/broker
        routing = self._route_lead(lead_data, score, tenant_context)
        
        # Handle GDPR compliance if applicable
        compliance = self._handle_compliance(lead_data, tenant_context)
        
        result = {
            'lead_id': str(uuid.uuid4()),
            'score': score,
            'routing': routing,
            'compliance_status': compliance,
            'next_steps': self._generate_next_steps(score, routing)
        }
        
        # Store lead
        db.leads[result['lead_id']] = {
            **lead_data,
            **result,
            'tenant_id': tenant_context['tenant_id'],
            'created_at': datetime.utcnow().isoformat()
        }
        
        self.log_activity('lead_processed', tenant_context['tenant_id'], {'result': result})
        return result
    
    def _validate_lead_data(self, lead_data: Dict, tenant_context: Dict) -> Dict:
        """Validate lead information"""
        errors = []
        required_fields = ['contact_info', 'name']
        
        for field in required_fields:
            if field not in lead_data or not lead_data[field]:
                errors.append(f"Missing required field: {field}")
        
        return {'valid': len(errors) == 0, 'errors': errors}
    
    def _score_lead(self, lead_data: Dict, tenant_context: Dict) -> float:
        """Score lead using BANT-like methodology"""
        score = 0.0
        
        # Budget (30%)
        if lead_data.get('budget'):
            score += 0.3
        
        # Authority (25%)
        if lead_data.get('decision_maker', False):
            score += 0.25
        
        # Need (25%)
        if lead_data.get('urgency') == 'high':
            score += 0.25
        
        # Timeline (20%)
        if lead_data.get('timeline') == 'immediate':
            score += 0.2
        
        return round(score, 2)
    
    def _route_lead(self, lead_data: Dict, score: float, tenant_context: Dict) -> Dict:
        """Route lead to appropriate agent or broker"""
        # Simplified routing logic
        if score >= 0.7:
            route_to = 'top_agent'
        elif score >= 0.4:
            route_to = 'regular_agent'
        else:
            route_to = 'automated_followup'
        
        return {
            'assigned_to': route_to,
            'priority': 'high' if score >= 0.7 else 'medium' if score >= 0.4 else 'low',
            'sla_hours': 4 if score >= 0.7 else 24 if score >= 0.4 else 72
        }
    
    def _handle_compliance(self, lead_data: Dict, tenant_context: Dict) -> Dict:
        """Handle GDPR and other compliance requirements"""
        compliance_rules = tenant_context.get('compliance_rules', {})
        status = {'gdpr_compliant': False, 'opt_in_verified': False}
        
        if compliance_rules.get('gdpr_enabled', False):
            status['gdpr_compliant'] = lead_data.get('gdpr_consent', False)
        
        if compliance_rules.get('require_opt_in', False):
            status['opt_in_verified'] = lead_data.get('opt_in', False)
        
        return status
    
    def _generate_next_steps(self, score: float, routing: Dict) -> List[str]:
        """Generate recommended next steps"""
        steps = []
        
        if score >= 0.7:
            steps.extend(['Immediate phone call', 'Schedule viewing within 24 hours'])
        elif score >= 0.4:
            steps.extend(['Email follow-up', 'Send property recommendations'])
        else:
            steps.extend(['Add to newsletter', 'Nurture campaign'])
        
        steps.append(f"SLA: {routing['sla_hours']} hours")
        return steps

class LeaseAgent(BaseAgent):
    def __init__(self):
        super().__init__('LeaseAgent')
    
    def create_draft(self, listing_id: str, applicant_id: str, terms: Dict, 
                    tenant_context: Dict) -> Dict:
        """Create lease draft document"""
        self.log_activity('lease_draft_start', tenant_context['tenant_id'], 
                         {'listing_id': listing_id, 'applicant_id': applicant_id})
        
        # Validate inputs
        if listing_id not in db.listings:
            return {'status': 'error', 'message': 'Listing not found'}
        
        # Generate lease clauses
        clauses = self._generate_lease_clauses(terms, tenant_context)
        
        # Create payment schedule
        schedule = self._create_payment_schedule(terms, tenant_context)
        
        # Assess risks
        risks = self._assess_lease_risks(applicant_id, terms, tenant_context)
        
        result = {
            'clauses': clauses,
            'schedule': schedule,
            'risks': risks,
            'document_id': str(uuid.uuid4()),
            'status': 'draft'
        }
        
        # Store lease draft
        db.leases[result['document_id']] = {
            **result,
            'listing_id': listing_id,
            'applicant_id': applicant_id,
            'tenant_id': tenant_context['tenant_id'],
            'created_at': datetime.utcnow().isoformat()
        }
        
        self.log_activity('lease_draft_complete', tenant_context['tenant_id'], {'result': result})
        return result
    
    def _generate_lease_clauses(self, terms: Dict, tenant_context: Dict) -> List[Dict]:
        """Generate standard and custom lease clauses"""
        clauses = []
        
        # Standard clauses
        standard_clauses = [
            {'type': 'rent', 'content': f'Monthly rent: {terms.get("monthly_rent", 0)}'},
            {'type': 'duration', 'content': f'Lease term: {terms.get("duration_months", 12)} months'},
            {'type': 'security_deposit', 'content': f'Security deposit: {terms.get("security_deposit", 0)}'},
            {'type': 'utilities', 'content': 'Utilities included: ' + 
             ('Yes' if terms.get('utilities_included', False) else 'No')}
        ]
        
        clauses.extend(standard_clauses)
        
        # Custom clauses based on special terms
        for special_term in terms.get('special_terms', []):
            clauses.append({'type': 'custom', 'content': special_term})
        
        return clauses
    
    def _create_payment_schedule(self, terms: Dict, tenant_context: Dict) -> List[Dict]:
        """Create payment schedule for the lease"""
        schedule = []
        start_date = datetime.strptime(terms['start_date'], '%Y-%m-%d')
        monthly_rent = terms.get('monthly_rent', 0)
        
        for month in range(terms.get('duration_months', 12)):
            due_date = start_date + timedelta(days=30 * month)
            schedule.append({
                'due_date': due_date.strftime('%Y-%m-%d'),
                'amount': monthly_rent,
                'type': 'rent',
                'status': 'pending'
            })
        
        # Add security deposit as first payment
        schedule.insert(0, {
            'due_date': start_date.strftime('%Y-%m-%d'),
            'amount': terms.get('security_deposit', 0),
            'type': 'security_deposit',
            'status': 'pending'
        })
        
        return schedule
    
    def _assess_lease_risks(self, applicant_id: str, terms: Dict, tenant_context: Dict) -> List[Dict]:
        """Assess potential risks for the lease agreement"""
        risks = []
        
        # Financial risk assessment
        if terms.get('monthly_rent', 0) > 0.3 * 50000:  # Simplified income assumption
            risks.append({
                'type': 'financial',
                'severity': 'medium',
                'description': 'Rent may be high relative to typical income levels',
                'mitigation': 'Request income verification'
            })
        
        # Lease term risk
        if terms.get('duration_months', 12) < 6:
            risks.append({
                'type': 'term',
                'severity': 'low',
                'description': 'Short lease term may lead to quick turnover',
                'mitigation': 'Consider longer term or renewal incentives'
            })
        
        return risks

# Initialize agent instances
agents = {
    'listing': ListingAgent(),
    'valuation': ValuationAgent(),
    'matchmaking': MatchmakingAgent(),
    'lead_crm': LeadCRMAgent(),
    'lease': LeaseAgent()
}

# API Routes
@app.route('/')
def index():
    """Serve the main landing page"""
    return render_template('index.html')

@app.route('/api/auth/register', methods=['POST'])
def register():
    """User registration endpoint"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'message': 'Email and password required'}), 400
        
        if data['email'] in db.users:
            return jsonify({'message': 'User already exists'}), 409
        
        # Create new user
        user_id = str(uuid.uuid4())
        db.users[data['email']] = {
            'id': user_id,
            'email': data['email'],
            'password': generate_password_hash(data['password']),
            'role': data.get('role', 'user'),
            'tenant_id': data.get('tenant_id', 'default'),
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Generate JWT token
        token = jwt.encode({
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.secret_key, algorithm='HS256')
        
        # Log audit event
        db.log_audit('user_registration', user_id, data.get('tenant_id', 'default'), 
                    {'action': 'new_user_created'})
        
        return jsonify({
            'message': 'User created successfully',
            'token': token,
            'user_id': user_id
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500

@app.route('/api/auth/login', methods['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'message': 'Email and password required'}), 400
        
        user = db.users.get(data['email'])
        if not user or not check_password_hash(user['password'], data['password']):
            return jsonify({'message': 'Invalid credentials'}), 401
        
        # Generate JWT token
        token = jwt.encode({
            'user_id': user['id'],
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.secret_key, algorithm='HS256')
        
        # Log audit event
        db.log_audit('user_login', user['id'], user.get('tenant_id', 'default'), 
                    {'action': 'user_logged_in'})
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user_id': user['id'],
            'role': user['role']
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500

@app.route('/api/listings', methods=['POST'])
@token_required
@tenant_required
def create_listing(current_user, tenant_id):
    """Create a new property listing"""
    try:
        data = request.get_json()
        
        # Validate listing data
        is_valid, errors = validate_listing_data(data)
        if not is_valid:
            return jsonify({'message': 'Validation failed', 'errors': errors}), 400
        
        # Create listing with ListingAgent
        tenant_context = get_tenant_context(tenant_id)
        listing_result = agents['listing'].intake(data, tenant_context)
        
        if listing_result['status'] != 'success':
            return jsonify({
                'message': 'Listing creation failed',
                'warnings': listing_result.get('warnings', [])
            }), 400
        
        # Store the listing
        listing_id = str(uuid.uuid4())
        listing_data = {
            'id': listing_id,
            'tenant_id': tenant_id,
            'created_by': current_user['id'],
            'created_at': datetime.utcnow().isoformat(),
            **listing_result['normalized_fields']
        }
        db.listings[listing_id] = listing_data
        db.log_audit('listing_created', current_user['id'], tenant_id, 
                    {'listing_id': listing_id})
        return jsonify({'message': 'Listing created successfully', 'listing_id': listing_id}), 201  
    except Exception as e:
        logger.error(f"Create listing error: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500
@app.route('/api/valuation', methods=['POST'])
@token_required
