# requirements.txt
"""
fastapi==0.104.1
uvicorn==0.24.0
websockets==12.0
pydantic==2.4.2
python-multipart==0.0.6
sqlalchemy==2.0.23
aiosqlite==0.19.0
pandas==2.1.3
numpy==1.25.2
scikit-learn==1.3.2
asyncio
"""

# main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import json
import uuid
from datetime import datetime, date
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import aiosqlite
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mwarokin Relocation API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class UserPreferences(BaseModel):
    relocation_type: str = Field(..., description="upgrade or downgrade")
    budget_min: float = Field(..., ge=0)
    budget_max: float = Field(..., ge=0)
    location: str
    bedrooms: int = Field(..., ge=1)
    amenities: List[str] = []
    commute: int = Field(..., ge=0)
    move_date: date

class PropertyRecommendation(BaseModel):
    listing_id: str
    score: float = Field(..., ge=0, le=1)
    valuation_range: List[float]
    fit_reason: str
    upgrade_downgrade_fit: str
    relocation_type: str
    location: str
    bedrooms: int
    price: float
    sq_ft: int
    bathrooms: int
    year_built: int
    property_type: str
    features: List[str]

class ComplianceReport(BaseModel):
    status: str
    kyc_passed: bool
    aml_flags: List[str]
    fair_housing_compliance: bool
    regulatory_notes: List[str]

class RelocationResponse(BaseModel):
    recommendations: List[PropertyRecommendation]
    compliance_report: ComplianceReport
    search_id: str
    timestamp: datetime

# Real-time connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_sessions: Dict[str, Any] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.user_sessions[user_id] = {
            "websocket": websocket,
            "preferences": None,
            "last_search": None
        }
        logger.info(f"User {user_id} connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        logger.info(f"User {user_id} disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.user_sessions:
            websocket = self.user_sessions[user_id]["websocket"]
            await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    async def send_real_time_update(self, user_id: str, update_type: str, data: Dict):
        if user_id in self.user_sessions:
            message = {
                "type": update_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
            await self.send_personal_message(json.dumps(message), user_id)

manager = ConnectionManager()

# Property valuation engine
class PropertyValuationEngine:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        
    async def train_model(self, training_data: pd.DataFrame):
        """Train the property valuation model"""
        try:
            # Feature columns
            features = ['bedrooms', 'bathrooms', 'sq_ft', 'year_built', 'location_score']
            X = training_data[features]
            y = training_data['price']
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train model
            self.model.fit(X_scaled, y)
            self.is_trained = True
            logger.info("Property valuation model trained successfully")
        except Exception as e:
            logger.error(f"Error training model: {e}")

    def predict_valuation(self, property_features: Dict) -> List[float]:
        """Predict property valuation range"""
        if not self.is_trained:
            # Return default valuation based on simple rules
            base_price = property_features.get('bedrooms', 2) * 150000
            location_multiplier = property_features.get('location_score', 0.8)
            predicted_price = base_price * location_multiplier
            
            # Add some variance for range
            low_range = predicted_price * 0.85
            high_range = predicted_price * 1.15
            
            return [low_range, high_range]
        
        try:
            features = np.array([[
                property_features.get('bedrooms', 2),
                property_features.get('bathrooms', 2),
                property_features.get('sq_ft', 1500),
                property_features.get('year_built', 1990),
                property_features.get('location_score', 0.8)
            ]])
            
            features_scaled = self.scaler.transform(features)
            predicted_price = self.model.predict(features_scaled)[0]
            
            # Add confidence interval
            low_range = predicted_price * 0.9
            high_range = predicted_price * 1.1
            
            return [float(low_range), float(high_range)]
        except Exception as e:
            logger.error(f"Error predicting valuation: {e}")
            return [300000, 500000]  # Fallback range

valuation_engine = PropertyValuationEngine()

# Compliance checker
class ComplianceChecker:
    @staticmethod
    async def check_compliance(preferences: UserPreferences, property_price: float) -> ComplianceReport:
        """Check regulatory compliance for the relocation"""
        aml_flags = []
        regulatory_notes = []
        
        # Anti-money laundering checks
        if property_price > 1000000:
            aml_flags.append("High-value transaction requiring additional verification")
        
        if preferences.budget_max - preferences.budget_min > 500000:
            aml_flags.append("Unusually wide budget range")
        
        # Fair housing compliance
        fair_housing_compliance = True
        if any(discriminatory_term in preferences.location.lower() for discriminatory_term in ["exclusive", "restricted"]):
            fair_housing_compliance = False
            regulatory_notes.append("Location preferences may violate fair housing laws")
        
        # KYC verification (simplified)
        kyc_passed = preferences.budget_max <= 2000000  # Simplified check
        
        status = "compliant" if not aml_flags and fair_housing_compliance and kyc_passed else "non-compliant"
        
        return ComplianceReport(
            status=status,
            kyc_passed=kyc_passed,
            aml_flags=aml_flags,
            fair_housing_compliance=fair_housing_compliance,
            regulatory_notes=regulatory_notes
        )

# Property matching engine
class PropertyMatchingEngine:
    def __init__(self):
        self.property_db = []
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """Initialize with sample property data"""
        locations = ["San Francisco, CA", "Oakland, CA", "San Jose, CA", "Berkeley, CA"]
        property_types = ["Single Family", "Condo", "Townhouse", "Apartment"]
        
        for i in range(50):
            bedrooms = np.random.choice([2, 3, 4, 5])
            bathrooms = bedrooms - np.random.choice([0, 1])
            sq_ft = 1000 + (bedrooms * 300) + np.random.randint(0, 500)
            year_built = np.random.randint(1950, 2023)
            
            self.property_db.append({
                "listing_id": f"prop_{uuid.uuid4().hex[:8]}",
                "location": np.random.choice(locations),
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "sq_ft": sq_ft,
                "year_built": year_built,
                "property_type": np.random.choice(property_types),
                "features": np.random.choice(["parking", "gym", "pool", "garden", "garage"], 
                                           size=np.random.randint(1, 4), replace=False).tolist(),
                "location_score": np.random.uniform(0.7, 1.0)
            })
    
    async def find_matches(self, preferences: UserPreferences) -> List[PropertyRecommendation]:
        """Find property matches based on user preferences"""
        matches = []
        
        for prop in self.property_db:
            score = await self._calculate_match_score(prop, preferences)
            
            if score >= 0.6:  # Minimum match threshold
                valuation_range = valuation_engine.predict_valuation(prop)
                price = np.mean(valuation_range)
                
                match = PropertyRecommendation(
                    listing_id=prop["listing_id"],
                    score=score,
                    valuation_range=valuation_range,
                    fit_reason=await self._generate_fit_reason(prop, preferences, score),
                    upgrade_downgrade_fit=await self._generate_upgrade_fit(price, preferences),
                    relocation_type=preferences.relocation_type,
                    location=prop["location"],
                    bedrooms=prop["bedrooms"],
                    price=price,
                    sq_ft=prop["sq_ft"],
                    bathrooms=prop["bathrooms"],
                    year_built=prop["year_built"],
                    property_type=prop["property_type"],
                    features=prop["features"]
                )
                matches.append(match)
        
        # Sort by match score
        matches.sort(key=lambda x: x.score, reverse=True)
        return matches[:12]  # Return top 12 matches
    
    async def _calculate_match_score(self, property_data: Dict, preferences: UserPreferences) -> float:
        """Calculate match score between property and preferences"""
        score = 0.0
        max_score = 0.0
        
        # Bedroom match
        if property_data["bedrooms"] >= preferences.bedrooms:
            score += 0.3
        max_score += 0.3
        
        # Location match (simplified)
        if preferences.location.lower() in property_data["location"].lower():
            score += 0.3
        max_score += 0.3
        
        # Amenities match
        amenity_match = len(set(property_data["features"]) & set(preferences.amenities))
        if preferences.amenities:
            score += (amenity_match / len(preferences.amenities)) * 0.2
        max_score += 0.2
        
        # Budget consideration (indirect)
        valuation_range = valuation_engine.predict_valuation(property_data)
        avg_price = np.mean(valuation_range)
        if preferences.budget_min <= avg_price <= preferences.budget_max:
            score += 0.2
        max_score += 0.2
        
        return score / max_score if max_score > 0 else 0
    
    async def _generate_fit_reason(self, property_data: Dict, preferences: UserPreferences, score: float) -> str:
        """Generate human-readable fit reason"""
        reasons = []
        
        if property_data["bedrooms"] >= preferences.bedrooms:
            reasons.append(f"meets {preferences.bedrooms}+ bedroom requirement")
        
        if any(amenity in property_data["features"] for amenity in preferences.amenities):
            reasons.append("includes desired amenities")
        
        if preferences.location.lower() in property_data["location"].lower():
            reasons.append("in preferred location")
        
        return f"Matches {int(score * 100)}% of preferences: {', '.join(reasons)}."
    
    async def _generate_upgrade_fit(self, price: float, preferences: UserPreferences) -> str:
        """Generate upgrade/downgrade fit description"""
        budget_mid = (preferences.budget_min + preferences.budget_max) / 2
        
        if preferences.relocation_type == "upgrade":
            if price > budget_mid:
                return f"Upgrade: Higher value (${price/1000:.0f}K vs budget ${budget_mid/1000:.0f}K)"
            else:
                return "Not an upgrade: Valuation within or below budget"
        else:  # downgrade
            if price < budget_mid:
                return f"Downgrade: Lower value (${price/1000:.0f}K vs budget ${budget_mid/1000:.0f}K)"
            else:
                return "Not a downgrade: Valuation within or above budget"

matching_engine = PropertyMatchingEngine()

# Real-time property updates
class RealTimeUpdateService:
    def __init__(self):
        self.active = True
    
    async def start_property_updates(self):
        """Start broadcasting real-time property updates"""
        while self.active:
            await asyncio.sleep(15)  # Update every 15 seconds
            
            # Generate new property listing
            new_property = await self._generate_new_property()
            
            # Broadcast to all connected clients
            update_message = {
                "type": "new_property",
                "data": new_property,
                "timestamp": datetime.now().isoformat()
            }
            
            await manager.broadcast(json.dumps(update_message))
            logger.info("Broadcasted new property update")
    
    async def _generate_new_property(self) -> Dict:
        """Generate a new property listing"""
        locations = ["San Francisco, CA", "Oakland, CA", "San Jose, CA", "Berkeley, CA"]
        
        return {
            "listing_id": f"new_prop_{uuid.uuid4().hex[:8]}",
            "title": "New Listing Available",
            "location": np.random.choice(locations),
            "bedrooms": np.random.choice([2, 3, 4]),
            "bathrooms": 2,
            "price": np.random.randint(400000, 800000),
            "sq_ft": 1500,
            "match_score": 0.92,
            "description": "Just listed! Hot new property matching current searches."
        }

real_time_service = RealTimeUpdateService()

# Database initialization
async def init_db():
    """Initialize SQLite database"""
    async with aiosqlite.connect("mwarokin.db") as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id TEXT UNIQUE,
                user_id TEXT,
                preferences TEXT,
                results TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                listing_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, listing_id)
            )
        ''')
        await db.commit()

# API Routes
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await init_db()
    
    # Train valuation model with sample data
    sample_data = pd.DataFrame([
        [3, 2, 1500, 1990, 0.9, 750000],
        [4, 3, 2000, 2005, 0.95, 950000],
        [2, 1, 1000, 1985, 0.8, 550000],
        [5, 4, 2500, 2010, 1.0, 1200000],
    ], columns=['bedrooms', 'bathrooms', 'sq_ft', 'year_built', 'location_score', 'price'])
    
    await valuation_engine.train_model(sample_data)
    
    # Start real-time updates
    asyncio.create_task(real_time_service.start_property_updates())
    
    logger.info("Mwarokin Relocation API started successfully")

@app.post("/api/search", response_model=RelocationResponse)
async def search_properties(preferences: UserPreferences, background_tasks: BackgroundTasks):
    """Search for property matches"""
    try:
        # Generate search ID
        search_id = str(uuid.uuid4())
        
        # Find property matches
        recommendations = await matching_engine.find_matches(preferences)
        
        # Check compliance
        avg_price = np.mean([np.mean(rec.valuation_range) for rec in recommendations]) if recommendations else 0
        compliance_report = await ComplianceChecker.check_compliance(preferences, avg_price)
        
        response = RelocationResponse(
            recommendations=recommendations,
            compliance_report=compliance_report,
            search_id=search_id,
            timestamp=datetime.now()
        )
        
        # Store search in database (background task)
        background_tasks.add_task(store_search_results, search_id, "user_123", preferences, response)
        
        logger.info(f"Search completed: {search_id}, found {len(recommendations)} matches")
        
        return response
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "heartbeat":
                # Respond to heartbeat
                await manager.send_personal_message(
                    json.dumps({"type": "heartbeat_ack", "timestamp": datetime.now().isoformat()}),
                    user_id
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)

@app.get("/api/favorites/{user_id}")
async def get_user_favorites(user_id: str):
    """Get user's favorite properties"""
    async with aiosqlite.connect("mwarokin.db") as db:
        cursor = await db.execute(
            "SELECT listing_id FROM user_favorites WHERE user_id = ? ORDER BY timestamp DESC",
            (user_id,)
        )
        favorites = await cursor.fetchall()
        
    return {"favorites": [fav[0] for fav in favorites]}

@app.post("/api/favorites/{user_id}/{listing_id}")
async def add_favorite(user_id: str, listing_id: str):
    """Add property to user's favorites"""
    async with aiosqlite.connect("mwarokin.db") as db:
        try:
            await db.execute(
                "INSERT OR IGNORE INTO user_favorites (user_id, listing_id) VALUES (?, ?)",
                (user_id, listing_id)
            )
            await db.commit()
            return {"status": "added", "listing_id": listing_id}
        except Exception as e:
            logger.error(f"Error adding favorite: {e}")
            raise HTTPException(status_code=500, detail="Failed to add favorite")

@app.delete("/api/favorites/{user_id}/{listing_id}")
async def remove_favorite(user_id: str, listing_id: str):
    """Remove property from user's favorites"""
    async with aiosqlite.connect("mwarokin.db") as db:
        await db.execute(
            "DELETE FROM user_favorites WHERE user_id = ? AND listing_id = ?",
            (user_id, listing_id)
        )
        await db.commit()
    
    return {"status": "removed", "listing_id": listing_id}

# Background tasks
async def store_search_results(search_id: str, user_id: str, preferences: UserPreferences, response: RelocationResponse):
    """Store search results in database"""
    async with aiosqlite.connect("mwarokin.db") as db:
        await db.execute(
            "INSERT INTO searches (search_id, user_id, preferences, results) VALUES (?, ?, ?, ?)",
            (search_id, user_id, preferences.json(), response.json())
        )
        await db.commit()

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_connections": len(manager.active_connections),
        "model_trained": valuation_engine.is_trained
    }

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Mwarokin Relocation API",
        "version": "1.0.0",
        "endpoints": {
            "search": "/api/search (POST)",
            "websocket": "/ws/{user_id}",
            "favorites": "/api/favorites/{user_id}",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)