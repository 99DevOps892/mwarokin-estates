

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import aiohttp
import redis
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import tensorflow as tf
from tensorflow import keras
import blockchain
from web3 import Web3
import qrcode
import bcrypt
import jwt
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn

# Configuration
class Config:
    DATABASE_URL = "sqlite:///mwarokin.db"
    REDIS_URL = "redis://localhost:6379"
    BLOCKCHAIN_NETWORK = "https://mainnet.infura.io/v3/YOUR_PROJECT_ID"
    JWT_SECRET = "your-super-secret-jwt-key"
    AI_MODEL_PATH = "models/property_predictor.h5"
    CRYPTO_PAYMENTS = True

# Database Setup
Base = declarative_base()
engine = create_engine(Config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis for caching and real-time features
redis_client = redis.Redis.from_url(Config.REDIS_URL)

# FastAPI App
app = FastAPI(title="Mwarokin Real Estate API", version="2.0.0")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Enums
class PropertyStatus(Enum):
    FOR_SALE = "for_sale"
    FOR_RENT = "for_rent"
    SOLD = "sold"
    RENTED = "rented"

class PaymentStatus(Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    FAILED = "failed"

class Currency(Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    KES = "KES"
    NGN = "NGN"
    GHS = "GHS"
    ZAR = "ZAR"

# Data Models
@dataclass
class Property:
    id: str
    title: str
    description: str
    type: str
    status: PropertyStatus
    location: str
    country: str
    continent: str
    price: float
    currency: Currency
    bedrooms: int
    bathrooms: int
    size_sqft: float
    amenities: List[str]
    images: List[str]
    coordinates: Dict[str, float]
    owner_id: str
    created_at: datetime
    updated_at: datetime
    ai_valuation: Optional[float] = None
    market_trend: Optional[float] = None

@dataclass
class Tenant:
    id: str
    property_id: str
    name: str
    email: str
    phone: str
    payment_account: str
    monthly_rent: float
    currency: Currency
    lease_start: datetime
    lease_end: datetime
    status: PaymentStatus

@dataclass
class User:
    id: str
    email: str
    name: str
    role: str
    phone: str
    avatar: Optional[str]
    preferences: Dict[str, Any]
    created_at: datetime
    last_login: datetime

@dataclass
class Transaction:
    id: str
    property_id: str
    tenant_id: str
    amount: float
    currency: Currency
    type: str
    status: PaymentStatus
    blockchain_hash: Optional[str]
    created_at: datetime

# Database Models
class DBProperty(Base):
    __tablename__ = "properties"
    
    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    type = Column(String)
    status = Column(String)
    location = Column(String)
    country = Column(String)
    continent = Column(String)
    price = Column(Float)
    currency = Column(String)
    bedrooms = Column(Integer)
    bathrooms = Column(Integer)
    size_sqft = Column(Float)
    amenities = Column(Text)  # JSON string
    images = Column(Text)  # JSON string
    coordinates = Column(Text)  # JSON string
    owner_id = Column(String)
    ai_valuation = Column(Float)
    market_trend = Column(Float)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

class DBTenant(Base):
    __tablename__ = "tenants"
    
    id = Column(String, primary_key=True, index=True)
    property_id = Column(String, index=True)
    name = Column(String)
    email = Column(String)
    phone = Column(String)
    payment_account = Column(String)
    monthly_rent = Column(Float)
    currency = Column(String)
    lease_start = Column(DateTime)
    lease_end = Column(DateTime)
    status = Column(String)

class DBUser(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    role = Column(String)
    phone = Column(String)
    avatar = Column(String)
    preferences = Column(Text)  # JSON string
    password_hash = Column(String)
    created_at = Column(DateTime)
    last_login = Column(DateTime)

class DBTransaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True, index=True)
    property_id = Column(String, index=True)
    tenant_id = Column(String, index=True)
    amount = Column(Float)
    currency = Column(String)
    type = Column(String)
    status = Column(String)
    blockchain_hash = Column(String)
    created_at = Column(DateTime)

# Create tables
Base.metadata.create_all(bind=engine)

# AI-Powered Property Valuation System
class PropertyValuationAI:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.features = ['bedrooms', 'bathrooms', 'size_sqft', 'location_score', 'amenities_count']
        self.load_model()
    
    def load_model(self):
        """Load pre-trained AI model"""
        try:
            self.model = keras.models.load_model(Config.AI_MODEL_PATH)
        except:
            # Create a simple model for demo
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
    
    async def predict_valuation(self, property_data: Dict) -> float:
        """Predict property valuation using AI"""
        try:
            # Feature engineering
            features = np.array([
                property_data['bedrooms'],
                property_data['bathrooms'],
                property_data['size_sqft'],
                self.calculate_location_score(property_data['location']),
                len(property_data.get('amenities', []))
            ]).reshape(1, -1)
            
            # Scale features
            features_scaled = self.scaler.fit_transform(features)
            
            # Predict
            if isinstance(self.model, RandomForestRegressor):
                prediction = self.model.predict(features_scaled)[0]
            else:
                prediction = self.model.predict(features_scaled)[0][0]
            
            return float(prediction)
        except Exception as e:
            logging.error(f"AI valuation error: {e}")
            return property_data['price'] * 0.9  # Fallback to 90% of asking price
    
    def calculate_location_score(self, location: str) -> float:
        """Calculate location desirability score"""
        # This would integrate with external APIs for real data
        location_factors = {
            'nairobi': 0.8, 'lagos': 0.7, 'cairo': 0.75,
            'accra': 0.7, 'johannesburg': 0.8, 'cape town': 0.85
        }
        return location_factors.get(location.lower(), 0.5)

# Blockchain Integration
class BlockchainManager:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(Config.BLOCKCHAIN_NETWORK))
        self.contract_address = "YOUR_CONTRACT_ADDRESS"
        self.contract_abi = []  # Your contract ABI here
    
    async def record_transaction(self, transaction_data: Dict) -> str:
        """Record transaction on blockchain"""
        try:
            # This would interact with your smart contract
            tx_hash = "0x" + uuid.uuid4().hex[:40]  # Mock hash
            return tx_hash
        except Exception as e:
            logging.error(f"Blockchain error: {e}")
            return None
    
    async def verify_transaction(self, tx_hash: str) -> bool:
        """Verify transaction on blockchain"""
        return True  # Mock verification

# Advanced Chatbot with AI
class MwarokinAssistant:
    def __init__(self):
        self.intents = self.load_intents()
        self.conversation_history = {}
    
    def load_intents(self) -> Dict:
        return {
            'greeting': {
                'patterns': ['hello', 'hi', 'hey', 'good morning', 'good afternoon'],
                'responses': [
                    "Hello! I'm Mwarokin Assistant. How can I help with your property needs?",
                    "Hi there! Ready to find your dream property?"
                ]
            },
            'property_search': {
                'patterns': ['search property', 'find house', 'looking for apartment', 'properties for sale'],
                'responses': [
                    "I can help you find properties. What type are you looking for?",
                    "Let me show you available properties. Any specific requirements?"
                ]
            },
            'price_inquiry': {
                'patterns': ['price', 'cost', 'how much', 'valuation'],
                'responses': [
                    "Property prices vary by location and type. I can provide market insights.",
                    "Let me check current market rates for you."
                ]
            },
            'location': {
                'patterns': ['where', 'location', 'area', 'neighborhood'],
                'responses': [
                    "We have properties across Africa and internationally. Any preferred location?",
                    "I can show you properties in specific areas. Where are you interested?"
                ]
            }
        }
    
    async def process_message(self, user_id: str, message: str) -> str:
        """Process user message and generate response"""
        # Store conversation history
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        self.conversation_history[user_id].append({"user": message, "timestamp": datetime.now()})
        
        # Simple intent recognition
        message_lower = message.lower()
        response = "I'm here to help with property-related questions. You can ask me about properties, prices, locations, or market trends."
        
        for intent, data in self.intents.items():
            for pattern in data['patterns']:
                if pattern in message_lower:
                    response = np.random.choice(data['responses'])
                    break
        
        self.conversation_history[user_id].append({"assistant": response, "timestamp": datetime.now()})
        
        # Keep only last 10 messages
        if len(self.conversation_history[user_id]) > 20:
            self.conversation_history[user_id] = self.conversation_history[user_id][-10:]
        
        return response

# Main Service Class
class MwarokinRealEstateService:
    def __init__(self):
        self.ai_valuator = PropertyValuationAI()
        self.blockchain = BlockchainManager()
        self.assistant = MwarokinAssistant()
        self.db = SessionLocal()
    
    # Property Management
    async def add_property(self, property_data: Dict) -> Property:
        """Add new property with AI valuation"""
        property_id = str(uuid.uuid4())
        
        # AI valuation
        ai_valuation = await self.ai_valuator.predict_valuation(property_data)
        
        property_obj = Property(
            id=property_id,
            title=property_data['title'],
            description=property_data['description'],
            type=property_data['type'],
            status=PropertyStatus(property_data['status']),
            location=property_data['location'],
            country=property_data['country'],
            continent=property_data['continent'],
            price=property_data['price'],
            currency=Currency(property_data['currency']),
            bedrooms=property_data['bedrooms'],
            bathrooms=property_data['bathrooms'],
            size_sqft=property_data['size_sqft'],
            amenities=property_data.get('amenities', []),
            images=property_data.get('images', []),
            coordinates=property_data.get('coordinates', {}),
            owner_id=property_data['owner_id'],
            ai_valuation=ai_valuation,
            market_trend=self.calculate_market_trend(property_data['location']),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Save to database
        db_property = DBProperty(**asdict(property_obj))
        db_property.amenities = json.dumps(property_obj.amenities)
        db_property.images = json.dumps(property_obj.images)
        db_property.coordinates = json.dumps(property_obj.coordinates)
        
        self.db.add(db_property)
        self.db.commit()
        
        # Cache in Redis
        redis_client.set(f"property:{property_id}", json.dumps(asdict(property_obj)), ex=3600)
        
        return property_obj
    
    async def search_properties(self, filters: Dict) -> List[Property]:
        """Advanced property search with multiple filters"""
        query = self.db.query(DBProperty)
        
        if filters.get('keyword'):
            query = query.filter(
                DBProperty.title.ilike(f"%{filters['keyword']}%") |
                DBProperty.description.ilike(f"%{filters['keyword']}%") |
                DBProperty.location.ilike(f"%{filters['keyword']}%")
            )
        
        if filters.get('type'):
            query = query.filter(DBProperty.type == filters['type'])
        
        if filters.get('continent'):
            query = query.filter(DBProperty.continent == filters['continent'])
        
        if filters.get('country'):
            query = query.filter(DBProperty.country == filters['country'])
        
        if filters.get('min_price'):
            query = query.filter(DBProperty.price >= filters['min_price'])
        
        if filters.get('max_price'):
            query = query.filter(DBProperty.price <= filters['max_price'])
        
        if filters.get('bedrooms'):
            query = query.filter(DBProperty.bedrooms >= filters['bedrooms'])
        
        properties = query.limit(100).all()
        
        return [self._db_to_property(p) for p in properties]
    
    async def get_property_recommendations(self, user_id: str) -> List[Property]:
        """AI-powered property recommendations based on user behavior"""
        # This would analyze user preferences and behavior
        user_preferences = await self.get_user_preferences(user_id)
        
        # Mock recommendations based on preferences
        recommendations = await self.search_properties({
            'type': user_preferences.get('preferred_type', 'apartment'),
            'max_price': user_preferences.get('max_budget', 500000),
            'bedrooms': user_preferences.get('min_bedrooms', 2)
        })
        
        return recommendations[:10]  # Return top 10 recommendations
    
    # Tenant Management
    async def add_tenant(self, tenant_data: Dict) -> Tenant:
        """Add new tenant"""
        tenant_id = str(uuid.uuid4())
        
        tenant_obj = Tenant(
            id=tenant_id,
            property_id=tenant_data['property_id'],
            name=tenant_data['name'],
            email=tenant_data['email'],
            phone=tenant_data['phone'],
            payment_account=tenant_data['payment_account'],
            monthly_rent=tenant_data['monthly_rent'],
            currency=Currency(tenant_data['currency']),
            lease_start=datetime.fromisoformat(tenant_data['lease_start']),
            lease_end=datetime.fromisoformat(tenant_data['lease_end']),
            status=PaymentStatus.PENDING
        )
        
        db_tenant = DBTenant(**asdict(tenant_obj))
        self.db.add(db_tenant)
        self.db.commit()
        
        return tenant_obj
    
    async def get_tenant_management_data(self) -> List[Dict]:
        """Get comprehensive tenant management data"""
        tenants = self.db.query(DBTenant).all()
        
        result = []
        for tenant in tenants:
            property_obj = self.db.query(DBProperty).filter(DBProperty.id == tenant.property_id).first()
            
            result.append({
                'tenant_id': tenant.id,
                'property_details': property_obj.title if property_obj else 'Unknown',
                'location': property_obj.location if property_obj else 'Unknown',
                'payment_account': tenant.payment_account,
                'tenant_name': tenant.name,
                'month': tenant.lease_start.strftime('%B'),
                'year': tenant.lease_start.year,
                'status': tenant.status
            })
        
        return result
    
    # Payment Processing
    async def process_payment(self, payment_data: Dict) -> Transaction:
        """Process property payment with blockchain recording"""
        transaction_id = str(uuid.uuid4())
        
        # Record on blockchain if enabled
        blockchain_hash = None
        if Config.CRYPTO_PAYMENTS:
            blockchain_hash = await self.blockchain.record_transaction(payment_data)
        
        transaction_obj = Transaction(
            id=transaction_id,
            property_id=payment_data['property_id'],
            tenant_id=payment_data['tenant_id'],
            amount=payment_data['amount'],
            currency=Currency(payment_data['currency']),
            type=payment_data['type'],
            status=PaymentStatus.PAID,
            blockchain_hash=blockchain_hash,
            created_at=datetime.now()
        )
        
        db_transaction = DBTransaction(**asdict(transaction_obj))
        self.db.add(db_transaction)
        self.db.commit()
        
        # Update tenant status
        tenant = self.db.query(DBTenant).filter(DBTenant.id == payment_data['tenant_id']).first()
        if tenant:
            tenant.status = PaymentStatus.PAID.value
            self.db.commit()
        
        return transaction_obj
    
    # Market Analytics
    async def get_market_analytics(self, location: str = None) -> Dict:
        """Get comprehensive market analytics"""
        query = self.db.query(DBProperty)
        if location:
            query = query.filter(DBProperty.location.ilike(f"%{location}%"))
        
        properties = query.all()
        
        if not properties:
            return {}
        
        prices = [p.price for p in properties]
        sizes = [p.size_sqft for p in properties]
        
        analytics = {
            'total_properties': len(properties),
            'average_price': np.mean(prices),
            'median_price': np.median(prices),
            'price_per_sqft': np.mean([p/s for p, s in zip(prices, sizes) if s > 0]),
            'market_trend': self.calculate_market_trend(location),
            'property_types': self.analyze_property_types(properties),
            'price_distribution': self.analyze_price_distribution(prices)
        }
        
        return analytics
    
    def calculate_market_trend(self, location: str) -> float:
        """Calculate market trend for location"""
        # This would integrate with real market data APIs
        trends = {
            'nairobi': 5.2, 'lagos': 3.8, 'cairo': 4.5,
            'accra': 2.9, 'johannesburg': 4.1, 'cape town': 6.2
        }
        return trends.get(location.lower(), 2.5)
    
    def analyze_property_types(self, properties: List[DBProperty]) -> Dict:
        """Analyze property type distribution"""
        types = {}
        for prop in properties:
            types[prop.type] = types.get(prop.type, 0) + 1
        return types
    
    def analyze_price_distribution(self, prices: List[float]) -> Dict:
        """Analyze price distribution"""
        return {
            'under_100k': len([p for p in prices if p < 100000]),
            '100k_500k': len([p for p in prices if 100000 <= p < 500000]),
            '500k_1m': len([p for p in prices if 500000 <= p < 1000000]),
            'over_1m': len([p for p in prices if p >= 1000000])
        }
    
    # Utility Methods
    def _db_to_property(self, db_property: DBProperty) -> Property:
        """Convert database property to Property object"""
        return Property(
            id=db_property.id,
            title=db_property.title,
            description=db_property.description,
            type=db_property.type,
            status=PropertyStatus(db_property.status),
            location=db_property.location,
            country=db_property.country,
            continent=db_property.continent,
            price=db_property.price,
            currency=Currency(db_property.currency),
            bedrooms=db_property.bedrooms,
            bathrooms=db_property.bathrooms,
            size_sqft=db_property.size_sqft,
            amenities=json.loads(db_property.amenities),
            images=json.loads(db_property.images),
            coordinates=json.loads(db_property.coordinates),
            owner_id=db_property.owner_id,
            ai_valuation=db_property.ai_valuation,
            market_trend=db_property.market_trend,
            created_at=db_property.created_at,
            updated_at=db_property.updated_at
        )
    
    async def get_user_preferences(self, user_id: str) -> Dict:
        """Get user preferences for recommendations"""
        user = self.db.query(DBUser).filter(DBUser.id == user_id).first()
        if user and user.preferences:
            return json.loads(user.preferences)
        return {}

# FastAPI Routes
service = MwarokinRealEstateService()

@app.get("/")
async def root():
    return {"message": "Mwarokin Real Estate API", "version": "2.0.0"}

@app.get("/api/properties")
async def get_properties(
    keyword: str = None,
    type: str = None,
    continent: str = None,
    country: str = None,
    min_price: float = None,
    max_price: float = None,
    bedrooms: int = None
):
    filters = {
        'keyword': keyword,
        'type': type,
        'continent': continent,
        'country': country,
        'min_price': min_price,
        'max_price': max_price,
        'bedrooms': bedrooms
    }
    
    properties = await service.search_properties(filters)
    return {"properties": [asdict(p) for p in properties]}

@app.post("/api/properties")
async def create_property(property_data: Dict):
    property_obj = await service.add_property(property_data)
    return {"property": asdict(property_obj), "message": "Property added successfully"}

@app.get("/api/tenants")
async def get_tenants():
    tenant_data = await service.get_tenant_management_data()
    return {"tenants": tenant_data}

@app.post("/api/tenants")
async def create_tenant(tenant_data: Dict):
    tenant_obj = await service.add_tenant(tenant_data)
    return {"tenant": asdict(tenant_obj), "message": "Tenant added successfully"}

@app.post("/api/payments")
async def process_payment(payment_data: Dict):
    transaction = await service.process_payment(payment_data)
    return {"transaction": asdict(transaction), "message": "Payment processed successfully"}

@app.get("/api/analytics")
async def get_analytics(location: str = None):
    analytics = await service.get_market_analytics(location)
    return {"analytics": analytics}

@app.get("/api/recommendations/{user_id}")
async def get_recommendations(user_id: str):
    recommendations = await service.get_property_recommendations(user_id)
    return {"recommendations": [asdict(p) for p in recommendations]}

# WebSocket for Real-time Chat
@app.websocket("/ws/chat/{user_id}")
async def websocket_chat(websocket: WebSocket, user_id: str):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            response = await service.assistant.process_message(user_id, message_data['message'])
            
            await websocket.send_text(json.dumps({
                "response": response,
                "timestamp": datetime.now().isoformat()
            }))
    except WebSocketDisconnect:
        logging.info(f"User {user_id} disconnected")

# Real-time Property Updates
@app.websocket("/ws/properties")
async def websocket_properties(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            # Send real-time property updates
            properties = await service.search_properties({})
            featured_properties = properties[:6]  # Top 6 properties
            
            await websocket.send_text(json.dumps({
                "type": "property_update",
                "properties": [asdict(p) for p in featured_properties],
                "timestamp": datetime.now().isoformat()
            }))
            
            await asyncio.sleep(30)  # Update every 30 seconds
    except WebSocketDisconnect:
        logging.info("Property updates disconnected")

# Currency Conversion
@app.get("/api/currency/convert")
async def convert_currency(amount: float, from_currency: str, to_currency: str):
    # This would integrate with real currency API
    rates = {
        'USD': 1.0, 'EUR': 0.85, 'GBP': 0.73,
        'KES': 115.5, 'NGN': 415.2, 'GHS': 6.1, 'ZAR': 15.3
    }
    
    if from_currency not in rates or to_currency not in rates:
        raise HTTPException(status_code=400, detail="Invalid currency")
    
    converted_amount = (amount / rates[from_currency]) * rates[to_currency]
    
    return {
        "original_amount": amount,
        "original_currency": from_currency,
        "converted_amount": round(converted_amount, 2),
        "converted_currency": to_currency,
        "exchange_rate": rates[to_currency] / rates[from_currency]
    }

# QR Code Generation for Properties
@app.get("/api/properties/{property_id}/qrcode")
async def generate_property_qrcode(property_id: str):
    property_obj = service.db.query(DBProperty).filter(DBProperty.id == property_id).first()
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")
    
    property_url = f"https://mwarokin.com/properties/{property_id}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(property_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(f"qrcodes/{property_id}.png")
    
    return {"qrcode_url": f"/qrcodes/{property_id}.png", "property_url": property_url}

# Advanced Search with AI
@app.post("/api/search/advanced")
async def advanced_search(search_criteria: Dict):
    """Advanced search with AI-powered ranking"""
    properties = await service.search_properties(search_criteria)
    
    # AI-powered ranking based on relevance
    ranked_properties = await service.rank_properties_by_relevance(properties, search_criteria)
    
    return {
        "total_results": len(ranked_properties),
        "properties": [asdict(p) for p in ranked_properties]
    }

async def rank_properties_by_relevance(self, properties: List[Property], criteria: Dict) -> List[Property]:
    """Rank properties by relevance to search criteria using AI"""
    # Simple ranking algorithm - in production, this would use ML
    ranked = []
    
    for prop in properties:
        score = 0
        
        # Location match
        if criteria.get('location') and criteria['location'].lower() in prop.location.lower():
            score += 3
        
        # Price proximity (closer to budget is better)
        if criteria.get('max_price'):
            price_ratio = prop.price / criteria['max_price']
            if price_ratio <= 1.0:
                score += (1.0 - price_ratio) * 2
        
        # Bedroom match
        if criteria.get('bedrooms') and prop.bedrooms >= criteria['bedrooms']:
            score += 1
        
        # Type match
        if criteria.get('type') and prop.type == criteria['type']:
            score += 2
        
        ranked.append((score, prop))
    
    # Sort by score descending
    ranked.sort(key=lambda x: x[0], reverse=True)
    
    return [prop for score, prop in ranked]

# Initialize with Sample Data
async def initialize_sample_data():
    """Initialize database with sample data"""
    db = SessionLocal()
    
    # Check if data already exists
    if db.query(DBProperty).count() > 0:
        return
    
    sample_properties = [
        {
            'title': 'Modern Apartment in Nairobi',
            'description': 'Beautiful modern apartment with city views',
            'type': 'apartment',
            'status': 'for_sale',
            'location': 'Nairobi, Kenya',
            'country': 'Kenya',
            'continent': 'Africa',
            'price': 85000,
            'currency': 'USD',
            'bedrooms': 2,
            'bathrooms': 2,
            'size_sqft': 1200,
            'amenities': ['parking', 'security', 'gym'],
            'images': ['img/property-1.jpg'],
            'coordinates': {'lat': -1.2921, 'lng': 36.8219},
            'owner_id': 'owner1'
        },
        {
            'title': 'Luxury Villa in Lagos',
            'description': 'Spacious villa with private pool',
            'type': 'villa',
            'status': 'for_rent',
            'location': 'Lagos, Nigeria',
            'country': 'Nigeria',
            'continent': 'Africa',
            'price': 2500,
            'currency': 'USD',
            'bedrooms': 4,
            'bathrooms': 3,
            'size_sqft': 3200,
            'amenities': ['pool', 'garden', 'security'],
            'images': ['img/property-2.jpg'],
            'coordinates': {'lat': 6.5244, 'lng': 3.3792},
            'owner_id': 'owner2'
        }
    ]
    
    for prop_data in sample_properties:
        await service.add_property(prop_data)
    
    logging.info("Sample data initialized")

# Main Execution
if __name__ == "__main__":
    # Initialize sample data
    asyncio.run(initialize_sample_data())
    
    # Start the server
    uvicorn.run(
        "mwarokin_backend:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )