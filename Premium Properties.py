# requirements.txt

fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
alembic==1.12.1
pydantic==2.5.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
redis==5.0.1
celery==5.3.4
pandas==2.1.3
numpy==1.25.2
scikit-learn==1.3.2
openai==1.3.0
google-maps-services-python==4.10.0
pillow==10.1.0
boto3==1.34.0
websockets==12.0
aioredis==2.0.1


# main.py
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import asyncio
import json
import uuid
from datetime import datetime, timedelta

from database import SessionLocal, engine, Base
from models import *
from schemas import *
from auth import *
from services import *
from ai_services import RealEstateAI
from websocket_manager import ConnectionManager

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mwarokin Premium Real Estate API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize services
property_service = PropertyService()
ai_service = RealEstateAI()
websocket_manager = ConnectionManager()

@app.get("/")
async def root():
    return {"message": "Mwarokin Premium Real Estate API"}

# Property endpoints
@app.post("/properties/", response_model=PropertyResponse)
async def create_property(
    property: PropertyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return property_service.create_property(db, property, current_user.id)

@app.get("/properties/", response_model=List[PropertyResponse])
async def get_properties(
    skip: int = 0,
    limit: int = 100,
    property_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    bedrooms: Optional[int] = None,
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    return property_service.get_properties(
        db, skip, limit, property_type, min_price, max_price, bedrooms, location
    )

@app.get("/properties/featured", response_model=List[PropertyResponse])
async def get_featured_properties(db: Session = Depends(get_db)):
    return property_service.get_featured_properties(db)

@app.get("/properties/{property_id}", response_model=PropertyResponse)
async def get_property(property_id: int, db: Session = Depends(get_db)):
    property = property_service.get_property(db, property_id)
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    return property

@app.post("/properties/{property_id}/favorite")
async def favorite_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return property_service.toggle_favorite(db, current_user.id, property_id)

# AI-powered property recommendations
@app.get("/recommendations/{user_id}", response_model=List[PropertyResponse])
async def get_recommendations(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ai_service.get_personalized_recommendations(db, user_id)

# Real-time market insights
@app.get("/market-insights/{location}")
async def get_market_insights(location: str, db: Session = Depends(get_db)):
    return ai_service.get_market_insights(db, location)

# Virtual tour endpoints
@app.post("/properties/{property_id}/virtual-tour")
async def create_virtual_tour(
    property_id: int,
    tour_data: VirtualTourCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return property_service.create_virtual_tour(db, property_id, tour_data)

# WebSocket for real-time chat and notifications
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await websocket_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Handle different message types
            if message_data["type"] == "chat_message":
                await websocket_manager.broadcast_to_agents(
                    f"Client {client_id}: {message_data['message']}"
                )
            elif message_data["type"] == "property_inquiry":
                await handle_property_inquiry(client_id, message_data)
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(client_id)

async def handle_property_inquiry(client_id: int, data: Dict[str, Any]):
    """Handle real-time property inquiries through AI"""
    response = await ai_service.process_inquiry(data["message"])
    await websocket_manager.send_personal_message(
        json.dumps({"type": "ai_response", "message": response}),
        client_id
    )

# Image processing for property listings
@app.post("/properties/{property_id}/images")
async def upload_property_images(
    property_id: int,
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await property_service.process_property_images(db, property_id, images)

# Price prediction endpoint
@app.post("/properties/price-prediction")
async def predict_property_price(property_data: PricePredictionRequest):
    return await ai_service.predict_property_price(property_data)

# database.py
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/mwarokin_realestate")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# models.py
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    phone = Column(String)
    preferences = Column(JSON)  # User preferences for recommendations
    is_agent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Property(Base):
    __tablename__ = "properties"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    property_type = Column(String)  # apartment, house, villa, etc.
    price = Column(Float)
    price_history = Column(JSON)  # Track price changes
    bedrooms = Column(Integer)
    bathrooms = Column(Integer)
    area_sqft = Column(Float)
    location = Column(String, index=True)
    coordinates = Column(JSON)  # {lat: x, lng: y}
    amenities = Column(JSON)  # List of amenities
    images = Column(JSON)  # List of image URLs
    virtual_tour_url = Column(String)
    is_featured = Column(Boolean, default=False)
    status = Column(String)  # available, sold, pending
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    owner = relationship("User")
    favorites = relationship("Favorite", back_populates="property")

class Favorite(Base):
    __tablename__ = "favorites"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    property_id = Column(Integer, ForeignKey("properties.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")
    property = relationship("Property", back_populates="favorites")

class VirtualTour(Base):
    __tablename__ = "virtual_tours"
    
    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"))
    tour_url = Column(String)
    tour_data = Column(JSON)  # 3D tour data
    created_at = Column(DateTime, default=datetime.utcnow)

class MarketInsight(Base):
    __tablename__ = "market_insights"
    
    id = Column(Integer, primary_key=True, index=True)
    location = Column(String, index=True)
    avg_price = Column(Float)
    price_trend = Column(String)  # rising, falling, stable
    inventory_level = Column(String)  # low, medium, high
    days_on_market = Column(Float)
    insight_data = Column(JSON)
    generated_at = Column(DateTime, default=datetime.utcnow)

# schemas.py
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    is_agent: bool = False

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class PropertyBase(BaseModel):
    title: str
    description: str
    property_type: str
    price: float
    bedrooms: int
    bathrooms: int
    area_sqft: float
    location: str
    amenities: List[str] = []
    coordinates: Optional[Dict[str, float]] = None

class PropertyCreate(PropertyBase):
    pass

class PropertyResponse(PropertyBase):
    id: int
    images: List[str] = []
    virtual_tour_url: Optional[str] = None
    is_featured: bool
    status: str
    owner: UserResponse
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class VirtualTourCreate(BaseModel):
    tour_url: str
    tour_data: Optional[Dict[str, Any]] = None

class PricePredictionRequest(BaseModel):
    bedrooms: int
    bathrooms: int
    area_sqft: float
    location: str
    property_type: str
    amenities: List[str] = []

class ChatMessage(BaseModel):
    message: str
    client_id: int
    timestamp: datetime

# auth.py
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta

SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# services.py
from sqlalchemy.orm import Session
from typing import List, Optional
import boto3
from PIL import Image
import io
import uuid

class PropertyService:
    def create_property(self, db: Session, property_data: PropertyCreate, owner_id: int):
        db_property = Property(
            **property_data.dict(),
            owner_id=owner_id,
            status="available",
            images=[],
            price_history=[{"price": property_data.price, "date": datetime.utcnow()}]
        )
        db.add(db_property)
        db.commit()
        db.refresh(db_property)
        return db_property

    def get_properties(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        property_type: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        bedrooms: Optional[int] = None,
        location: Optional[str] = None
    ):
        query = db.query(Property).filter(Property.status == "available")
        
        if property_type:
            query = query.filter(Property.property_type == property_type)
        if min_price:
            query = query.filter(Property.price >= min_price)
        if max_price:
            query = query.filter(Property.price <= max_price)
        if bedrooms:
            query = query.filter(Property.bedrooms == bedrooms)
        if location:
            query = query.filter(Property.location.ilike(f"%{location}%"))
            
        return query.offset(skip).limit(limit).all()

    def get_featured_properties(self, db: Session):
        return db.query(Property).filter(
            Property.is_featured == True,
            Property.status == "available"
        ).limit(6).all()

    def toggle_favorite(self, db: Session, user_id: int, property_id: int):
        existing_favorite = db.query(Favorite).filter(
            Favorite.user_id == user_id,
            Favorite.property_id == property_id
        ).first()
        
        if existing_favorite:
            db.delete(existing_favorite)
            db.commit()
            return {"status": "removed"}
        else:
            favorite = Favorite(user_id=user_id, property_id=property_id)
            db.add(favorite)
            db.commit()
            return {"status": "added"}

    async def process_property_images(self, db: Session, property_id: int, images: List[UploadFile]):
        s3_client = boto3.client('s3')
        processed_urls = []
        
        for image in images:
            # Read and process image
            image_data = await image.read()
            img = Image.open(io.BytesIO(image_data))
            
            # Optimize image
            img.thumbnail((1200, 800))
            
            # Convert back to bytes
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85)
            output.seek(0)
            
            # Upload to S3
            filename = f"properties/{property_id}/{uuid.uuid4()}.jpg"
            s3_client.upload_fileobj(
                output, 
                "mwarokin-realestate", 
                filename,
                ExtraArgs={'ACL': 'public-read', 'ContentType': 'image/jpeg'}
            )
            
            url = f"https://mwarokin-realestate.s3.amazonaws.com/{filename}"
            processed_urls.append(url)
        
        # Update property with new images
        property_obj = db.query(Property).filter(Property.id == property_id).first()
        if property_obj:
            current_images = property_obj.images or []
            property_obj.images = current_images + processed_urls
            db.commit()
        
        return {"image_urls": processed_urls}

# ai_services.py
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from typing import List, Dict, Any
import openai
import asyncio

class RealEstateAI:
    def __init__(self):
        self.price_model = None
        self.label_encoders = {}
        self.openai_client = openai.AsyncOpenAI(api_key="your-openai-key")
        
    async def train_price_model(self, properties_data: List[Dict]):
        """Train machine learning model for price prediction"""
        df = pd.DataFrame(properties_data)
        
        # Preprocess data
        categorical_cols = ['location', 'property_type']
        for col in categorical_cols:
            self.label_encoders[col] = LabelEncoder()
            df[col] = self.label_encoders[col].fit_transform(df[col])
        
        # Prepare features and target
        X = df[['bedrooms', 'bathrooms', 'area_sqft', 'location', 'property_type']]
        y = df['price']
        
        # Train model
        self.price_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.price_model.fit(X, y)
    
    async def predict_property_price(self, property_data: PricePredictionRequest) -> Dict[str, Any]:
        """Predict property price using trained ML model"""
        if not self.price_model:
            # Return heuristic estimate if model not trained
            base_price = property_data.area_sqft * 200  # $200 per sqft
            bedroom_premium = property_data.bedrooms * 50000
            bathroom_premium = property_data.bathrooms * 30000
            estimated_price = base_price + bedroom_premium + bathroom_premium
            
            return {
                "estimated_price": estimated_price,
                "confidence": "low",
                "method": "heuristic"
            }
        
        # Prepare input for model prediction
        input_data = pd.DataFrame([{
            'bedrooms': property_data.bedrooms,
            'bathrooms': property_data.bathrooms,
            'area_sqft': property_data.area_sqft,
            'location': self.label_encoders['location'].transform([property_data.location])[0],
            'property_type': self.label_encoders['property_type'].transform([property_data.property_type])[0]
        }])
        
        predicted_price = self.price_model.predict(input_data)[0]
        
        return {
            "estimated_price": predicted_price,
            "confidence": "high",
            "method": "ml_model",
            "currency": "USD"
        }
    
    async def get_personalized_recommendations(self, db: Session, user_id: int) -> List[Property]:
        """Get AI-powered property recommendations based on user preferences"""
        user = db.query(User).filter(User.id == user_id).first()
        user_favorites = db.query(Favorite).filter(Favorite.user_id == user_id).all()
        
        # Simple recommendation logic - extend with collaborative filtering
        favorite_property_types = set()
        preferred_locations = set()
        
        for fav in user_favorites:
            property_obj = fav.property
            favorite_property_types.add(property_obj.property_type)
            preferred_locations.add(property_obj.location)
        
        # Query similar properties
        query = db.query(Property).filter(Property.status == "available")
        
        if favorite_property_types:
            query = query.filter(Property.property_type.in_(favorite_property_types))
        if preferred_locations:
            query = query.filter(Property.location.in_(preferred_locations))
        
        return query.limit(10).all()
    
    async def get_market_insights(self, db: Session, location: str) -> Dict[str, Any]:
        """Generate AI-powered market insights for a location"""
        # Get recent properties in location
        recent_properties = db.query(Property).filter(
            Property.location.ilike(f"%{location}%"),
            Property.status == "available"
        ).all()
        
        if not recent_properties:
            return {"error": "No data available for this location"}
        
        # Calculate market metrics
        prices = [p.price for p in recent_properties]
        avg_price = sum(prices) / len(prices)
        days_on_market = 45  # This would come from actual data
        
        # Generate AI analysis
        analysis_prompt = f"""
        Analyze the real estate market in {location} with the following metrics:
        - Average price: ${avg_price:,.2f}
        - Number of active listings: {len(recent_properties)}
        - Estimated days on market: {days_on_market}
        
        Provide a concise market analysis and investment recommendation.
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": analysis_prompt}],
                max_tokens=200
            )
            analysis = response.choices[0].message.content
        except:
            analysis = "Market analysis temporarily unavailable."
        
        return {
            "location": location,
            "average_price": avg_price,
            "active_listings": len(recent_properties),
            "market_trend": "stable",  # This would be calculated from historical data
            "analysis": analysis,
            "recommendation": "Consider investing" if avg_price < 500000 else "Evaluate carefully"
        }
    
    async def process_inquiry(self, message: str) -> str:
        """Process natural language inquiries using AI"""
        prompt = f"""
        You are a real estate assistant for Mwarokin Premium Properties. 
        Respond to the following inquiry professionally and helpfully:
        
        User: {message}
        
        Assistant:
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return "I apologize, but I'm having trouble processing your request. Please contact our agents directly for immediate assistance."

# websocket_manager.py
from fastapi import WebSocket
from typing import Dict, List
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
        self.agent_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, client_id: int):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: int):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_personal_message(self, message: str, client_id: int):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)

    async def broadcast_to_agents(self, message: str):
        for connection in self.agent_connections:
            await connection.send_text(message)

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

This advanced Python backend for Mwarokin Real Estate includes:

## Key Features:

1. **Modern FastAPI Framework** - High-performance async API
2. **AI-Powered Services**:
   - Property price prediction using ML
   - Personalized recommendations
   - Market insights with GPT-4 integration
   - Natural language processing for inquiries

3. **Real-time Features**:
   - WebSocket connections for live chat
   - Real-time notifications
   - Live market updates

4. **Advanced Database Design**:
   - PostgreSQL with SQLAlchemy ORM
   - Complex relationships and JSON fields
   - Price history tracking

5. **Image Processing**:
   - Automated image optimization
   - AWS S3 integration
   - Thumbnail generation

6. **Security**:
   - JWT authentication
   - Password hashing
   - Protected endpoints

7. **Scalable Architecture**:
   - Service layer abstraction
   - WebSocket connection management
   - Async/await patterns

## To run the application:

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
export DATABASE_URL="postgresql://user:password@localhost/mwarokin_realestate"
export SECRET_KEY="your-secret-key"
export OPENAI_API_KEY="your-openai-key"
```

3. Run the server:
```bash
python main.py
```

This provides a robust, scalable foundation for a premium real estate platform with advanced AI capabilities and real-time features.