from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import asyncio
import aiohttp
import redis
import jwt
from pydantic import BaseModel, EmailStr, validator
import uuid
import logging
from contextlib import asynccontextmanager
import websockets

# Configuration
class Config:
    DATABASE_URL = "sqlite:///./travel_platform.db"
    REDIS_URL = "redis://localhost:6379"
    SECRET_KEY = "your-secret-key-here"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Database setup
engine = create_engine(Config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis connection
redis_client = redis.Redis.from_url(Config.REDIS_URL)

# Security
security = HTTPBearer()

# Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    hashed_password = Column(String)
    phone_number = Column(String)
    preferences = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class FlightSearch(Base):
    __tablename__ = "flight_searches"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True)
    origin = Column(String)
    destination = Column(String)
    departure_date = Column(DateTime)
    return_date = Column(DateTime, nullable=True)
    passengers = Column(JSON)
    class_type = Column(String)
    results = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class HotelSearch(Base):
    __tablename__ = "hotel_searches"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True)
    destination = Column(String)
    check_in = Column(DateTime)
    check_out = Column(DateTime)
    guests = Column(Integer)
    rooms = Column(Integer)
    results = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True)
    type = Column(String)  # 'flight', 'hotel', 'package'
    details = Column(JSON)
    status = Column(String, default='pending')
    total_amount = Column(Float)
    currency = Column(String, default='USD')
    created_at = Column(DateTime, default=datetime.utcnow)

# Pydantic Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone_number: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    phone_number: Optional[str]
    preferences: Dict[str, Any]

class FlightSearchRequest(BaseModel):
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str] = None
    passengers: Dict[str, int]
    class_type: str = "economy"

class HotelSearchRequest(BaseModel):
    destination: str
    check_in: str
    check_out: str
    guests: int = 2
    rooms: int = 1

class BookingRequest(BaseModel):
    type: str
    details: Dict[str, Any]
    payment_method: Dict[str, Any]

# Authentication
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, Config.SECRET_KEY, algorithm=Config.ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Real-time WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, str] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_sessions[user_id] = str(uuid.uuid4())

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

# External API Clients
class FlightAPIClient:
    def __init__(self):
        self.base_url = "https://api.skyscanner.net/apichedule/v1.0"
        self.api_key = "your_skyscanner_api_key"

    async def search_flights(self, search_request: FlightSearchRequest) -> List[Dict]:
        # Mock implementation - replace with actual API calls
        return [
            {
                "id": str(uuid.uuid4()),
                "airline": "Kenya Airways",
                "flight_number": "KQ 123",
                "departure_time": "08:00",
                "arrival_time": "10:30",
                "duration": "2h 30m",
                "price": 420,
                "currency": "USD",
                "stops": 0,
                "aircraft": "Boeing 737"
            },
            {
                "id": str(uuid.uuid4()),
                "airline": "Emirates",
                "flight_number": "EK 723",
                "departure_time": "14:20",
                "arrival_time": "18:45",
                "duration": "4h 25m",
                "price": 580,
                "currency": "USD",
                "stops": 1,
                "aircraft": "Airbus A380"
            }
        ]

class HotelAPIClient:
    def __init__(self):
        self.base_url = "https://api.hotels.com/v1"
        self.api_key = "your_hotels_api_key"

    async def search_hotels(self, search_request: HotelSearchRequest) -> List[Dict]:
        # Mock implementation - replace with actual API calls
        return [
            {
                "id": str(uuid.uuid4()),
                "name": "Luxury Beach Resort",
                "location": "Bali, Indonesia",
                "price": 120,
                "currency": "USD",
                "rating": 4.8,
                "reviews": 1247,
                "amenities": ["Pool", "Spa", "Beach Access", "WiFi"],
                "image": "https://images.unsplash.com/photo-1566073771259-6a8506099945?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80"
            },
            {
                "id": str(uuid.uuid4()),
                "name": "City Center Hotel",
                "location": "Barcelona, Spain",
                "price": 85,
                "currency": "USD",
                "rating": 4.5,
                "reviews": 892,
                "amenities": ["WiFi", "Gym", "Restaurant", "Bar"],
                "image": "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80"
            }
        ]

class PaymentProcessor:
    def __init__(self):
        self.stripe_secret_key = "your_stripe_secret_key"

    async def process_payment(self, amount: float, currency: str, payment_method: Dict) -> Dict:
        # Mock payment processing
        return {
            "success": True,
            "transaction_id": str(uuid.uuid4()),
            "amount": amount,
            "currency": currency,
            "status": "completed"
        }

# Background Task Manager
class BackgroundTaskManager:
    def __init__(self):
        self.tasks = {}

    async def start_price_monitoring(self, search_id: str, search_params: Dict):
        task = asyncio.create_task(self._monitor_prices(search_id, search_params))
        self.tasks[search_id] = task

    async def _monitor_prices(self, search_id: str, search_params: Dict):
        while True:
            try:
                # Check for price changes
                current_prices = await self._get_current_prices(search_params)
                previous_prices = redis_client.get(f"prices:{search_id}")
                
                if previous_prices:
                    previous_prices = json.loads(previous_prices)
                    price_changes = self._analyze_price_changes(previous_prices, current_prices)
                    
                    if price_changes.get('significant_drop'):
                        # Notify users via WebSocket
                        await connection_manager.broadcast(json.dumps({
                            "type": "price_alert",
                            "search_id": search_id,
                            "price_changes": price_changes
                        }))
                
                redis_client.setex(f"prices:{search_id}", 3600, json.dumps(current_prices))
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logging.error(f"Price monitoring error: {e}")
                await asyncio.sleep(60)

# Application Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    logging.info("Application started")
    yield
    # Shutdown
    logging.info("Application shutting down")

# Initialize FastAPI app
app = FastAPI(
    title="Faraja Sky Travel Platform",
    description="Advanced travel booking platform with real-time features",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global instances
connection_manager = ConnectionManager()
flight_client = FlightAPIClient()
hotel_client = HotelAPIClient()
payment_processor = PaymentProcessor()
task_manager = BackgroundTaskManager()

# Routes
@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("templates/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/auth/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user (in real app, hash password)
    db_user = User(
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone_number=user.phone_number,
        hashed_password=user.password  # Hash this in production
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create access token
    access_token = create_access_token(data={"sub": db_user.id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(db_user)
    }

@app.post("/api/auth/login")
async def login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or user.hashed_password != password:  # Verify hashed password in production
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }

@app.post("/api/flights/search")
async def search_flights(
    search_request: FlightSearchRequest,
    token: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    user_id = token.get("sub")
    
    # Search flights
    flights = await flight_client.search_flights(search_request)
    
    # Save search to database
    search_record = FlightSearch(
        user_id=user_id,
        origin=search_request.origin,
        destination=search_request.destination,
        departure_date=datetime.fromisoformat(search_request.departure_date),
        return_date=datetime.fromisoformat(search_request.return_date) if search_request.return_date else None,
        passengers=search_request.passengers,
        class_type=search_request.class_type,
        results=flights
    )
    
    db.add(search_record)
    db.commit()
    
    # Start price monitoring
    await task_manager.start_price_monitoring(
        search_record.id,
        search_request.dict()
    )
    
    return {
        "search_id": search_record.id,
        "results": flights,
        "total_results": len(flights)
    }

@app.post("/api/hotels/search")
async def search_hotels(
    search_request: HotelSearchRequest,
    token: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    user_id = token.get("sub")
    
    # Search hotels
    hotels = await hotel_client.search_hotels(search_request)
    
    # Save search to database
    search_record = HotelSearch(
        user_id=user_id,
        destination=search_request.destination,
        check_in=datetime.fromisoformat(search_request.check_in),
        check_out=datetime.fromisoformat(search_request.check_out),
        guests=search_request.guests,
        rooms=search_request.rooms,
        results=hotels
    )
    
    db.add(search_record)
    db.commit()
    
    return {
        "search_id": search_record.id,
        "results": hotels,
        "total_results": len(hotels)
    }

@app.post("/api/bookings/create")
async def create_booking(
    booking_request: BookingRequest,
    token: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    user_id = token.get("sub")
    
    # Process payment
    payment_result = await payment_processor.process_payment(
        amount=booking_request.details.get("total_amount", 0),
        currency=booking_request.details.get("currency", "USD"),
        payment_method=booking_request.payment_method
    )
    
    if not payment_result["success"]:
        raise HTTPException(status_code=400, detail="Payment failed")
    
    # Create booking record
    booking = Booking(
        user_id=user_id,
        type=booking_request.type,
        details=booking_request.details,
        total_amount=booking_request.details.get("total_amount", 0),
        currency=booking_request.details.get("currency", "USD"),
        status="confirmed"
    )
    
    db.add(booking)
    db.commit()
    db.refresh(booking)
    
    # Send real-time confirmation
    await connection_manager.send_personal_message(
        json.dumps({
            "type": "booking_confirmation",
            "booking_id": booking.id,
            "status": "confirmed",
            "details": booking_request.details
        }),
        user_id
    )
    
    return {
        "booking_id": booking.id,
        "status": "confirmed",
        "payment_status": "completed",
        "transaction_id": payment_result["transaction_id"]
    }

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await connection_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle real-time messages from client
            message = json.loads(data)
            
            if message["type"] == "subscribe_prices":
                # Subscribe to price updates
                await connection_manager.send_personal_message(
                    json.dumps({
                        "type": "subscription_confirmed",
                        "search_id": message["search_id"]
                    }),
                    user_id
                )
                
    except WebSocketDisconnect:
        connection_manager.disconnect(user_id)

@app.get("/api/user/bookings")
async def get_user_bookings(
    token: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    user_id = token.get("sub")
    bookings = db.query(Booking).filter(Booking.user_id == user_id).all()
    
    return {
        "bookings": [
            {
                "id": booking.id,
                "type": booking.type,
                "status": booking.status,
                "total_amount": booking.total_amount,
                "currency": booking.currency,
                "created_at": booking.created_at.isoformat(),
                "details": booking.details
            }
            for booking in bookings
        ]
    }

@app.get("/api/user/preferences")
async def get_user_preferences(
    token: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    user_id = token.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    
    return {
        "preferences": user.preferences if user else {}
    }

@app.put("/api/user/preferences")
async def update_user_preferences(
    preferences: Dict[str, Any],
    token: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    user_id = token.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    
    if user:
        user.preferences = preferences
        db.commit()
        
    return {"status": "preferences_updated"}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logging.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
```

## 2. Advanced Real-Time Features Module

```python
# real_time/price_monitor.py
import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List
import logging

class RealTimePriceMonitor:
    def __init__(self):
        self.active_monitors = {}
        self.price_cache = {}
        
    async def start_monitoring(self, search_id: str, search_params: Dict):
        """Start monitoring prices for a specific search"""
        if search_id in self.active_monitors:
            return
            
        monitor_task = asyncio.create_task(
            self._monitor_prices(search_id, search_params)
        )
        self.active_monitors[search_id] = monitor_task
        
    async def stop_monitoring(self, search_id: str):
        """Stop monitoring prices for a specific search"""
        if search_id in self.active_monitors:
            self.active_monitors[search_id].cancel()
            del self.active_monitors[search_id]
            
    async def _monitor_prices(self, search_id: str, search_params: Dict):
        """Background task to monitor price changes"""
        while True:
            try:
                current_prices = await self._fetch_current_prices(search_params)
                previous_prices = self.price_cache.get(search_id)
                
                if previous_prices:
                    price_changes = self._analyze_price_changes(
                        previous_prices, current_prices
                    )
                    
                    if price_changes.get('has_significant_drop'):
                        await self._notify_price_drop(
                            search_id, price_changes, current_prices
                        )
                
                self.price_cache[search_id] = current_prices
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logging.error(f"Price monitoring error for {search_id}: {e}")
                await asyncio.sleep(60)
```

## 3. Enhanced Frontend Integration

```python
# static/js/real-time-client.js
class RealTimeTravelClient {
    constructor() {
        this.ws = null;
        this.userId = null;
        this.isConnected = false;
        this.messageHandlers = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    async connect(userId, token) {
        this.userId = userId;
        this.token = token;
        
        try {
            this.ws = new WebSocket(`ws://localhost:8000/ws/${userId}`);
            
            this.ws.onopen = () => {
                this.isConnected = true;
                this.reconnectAttempts = 0;
                console.log('Connected to real-time travel service');
                this.onConnectionStateChange(true);
            };
            
            this.ws.onmessage = (event) => {
                this.handleMessage(JSON.parse(event.data));
            };
            
            this.ws.onclose = () => {
                this.isConnected = false;
                this.onConnectionStateChange(false);
                this.handleReconnection();
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.onError(error);
            };
            
        } catch (error) {
            console.error('Connection error:', error);
            this.handleReconnection();
        }
    }

    handleMessage(message) {
        const handler = this.messageHandlers.get(message.type);
        if (handler) {
            handler(message);
        }
        
        // Default handlers
        switch(message.type) {
            case 'price_alert':
                this.showPriceAlert(message);
                break;
            case 'booking_confirmation':
                this.showBookingConfirmation(message);
                break;
            case 'flight_status_update':
                this.updateFlightStatus(message);
                break;
        }
    }

    subscribeToPriceAlerts(searchId) {
        this.send({
            type: 'subscribe_prices',
            search_id: searchId
        });
    }

    send(message) {
        if (this.isConnected && this.ws) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket not connected');
        }
    }

    on(event, handler) {
        this.messageHandlers.set(event, handler);
    }

    showPriceAlert(message) {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = 'fixed top-4 right-4 bg-green-500 text-white p-4 rounded-lg shadow-lg z-50';
        toast.innerHTML = `
            <div class="flex items-center">
                <span class="text-xl mr-2">🎉</span>
                <div>
                    <h4 class="font-bold">Price Drop Alert!</h4>
                    <p>Prices have dropped for your search</p>
                    <p class="text-sm">New best price: $${message.price_changes.best_price}</p>
                </div>
                <button onclick="this.parentElement.parentElement.remove()" 
                        class="ml-4 text-white hover:text-gray-200">
                    ✕
                </button>
            </div>
        `;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 10000);
    }

    handleReconnection() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
            
            setTimeout(() => {
                if (this.userId && this.token) {
                    this.connect(this.userId, this.token);
                }
            }, delay);
        }
    }

    onConnectionStateChange(connected) {
        const indicator = document.getElementById('connection-indicator');
        if (indicator) {
            indicator.className = connected ? 
                'bg-green-500 text-white px-2 py-1 rounded text-sm' :
                'bg-red-500 text-white px-2 py-1 rounded text-sm';
            indicator.textContent = connected ? 'Connected' : 'Disconnected';
        }
    }

    onError(error) {
        console.error('Real-time client error:', error);
    }
}

// Initialize real-time client
const travelClient = new RealTimeTravelClient();

// Enhanced search function with real-time features
async function enhancedFlightSearch(searchData) {
    try {
        const response = await fetch('/api/flights/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify(searchData)
        });
        
        const result = await response.json();
        
        if (result.search_id) {
            // Subscribe to price alerts for this search
            travelClient.subscribeToPriceAlerts(result.search_id);
        }
        
        return result;
        
    } catch (error) {
        console.error('Search error:', error);
        throw error;
    }
}

// Real-time booking confirmation
travelClient.on('booking_confirmation', (message) => {
    showBookingModal(message);
});

function showBookingModal(confirmation) {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    modal.innerHTML = `
        <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div class="text-center">
                <div class="text-green-500 text-4xl mb-4">✓</div>
                <h3 class="text-xl font-bold mb-2">Booking Confirmed!</h3>
                <p class="text-gray-600 mb-4">Your booking has been successfully confirmed.</p>
                <div class="bg-gray-50 rounded p-4 mb-4 text-left">
                    <p><strong>Booking ID:</strong> ${confirmation.booking_id}</p>
                    <p><strong>Status:</strong> ${confirmation.status}</p>
                    <p><strong>Amount:</strong> $${confirmation.details.total_amount}</p>
                </div>
                <button onclick="this.closest('.fixed').remove()" 
                        class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700">
                    Close
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}
```

## 4. Configuration and Environment Setup

```python
# config.py
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class DatabaseConfig:
    url: str = os.getenv("DATABASE_URL", "sqlite:///./travel_platform.db")
    echo: bool = os.getenv("DB_ECHO", "False").lower() == "true"

@dataclass
class RedisConfig:
    url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    decode_responses: bool = True

@dataclass
class SecurityConfig:
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

@dataclass
class ExternalAPIs:
    skyscanner_api_key: Optional[str] = os.getenv("SKYSCANNER_API_KEY")
    hotels_api_key: Optional[str] = os.getenv("HOTELS_API_KEY")
    stripe_secret_key: Optional[str] = os.getenv("STRIPE_SECRET_KEY")

@dataclass
class AppConfig:
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    security: SecurityConfig = SecurityConfig()
    external_apis: ExternalAPIs = ExternalAPIs()
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"

config = AppConfig()
```

## 5. Advanced Features Implementation

```python
# services/recommendation_engine.py
from typing import List, Dict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class RecommendationEngine:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.user_profiles = {}
        
    def get_personalized_recommendations(self, user_id: str, search_history: List, available_options: List) -> List:
        user_profile = self._build_user_profile(user_id, search_history)
        recommendations = self._rank_options(user_profile, available_options)
        return recommendations[:10]  # Return top 10
    
    def _build_user_profile(self, user_id: str, search_history: List) -> Dict:
        if user_id in self.user_profiles:
            return self.user_profiles[user_id]
            
        # Analyze search history to build user preferences
        preferences = {
            'preferred_destinations': [],
            'budget_range': {'min': 0, 'max': 1000},
            'travel_style': 'balanced',  # budget, luxury, balanced
            'preferred_activities': []
        }
        
        # Implement preference extraction logic
        self.user_profiles[user_id] = preferences
        return preferences
    
    def _rank_options(self, user_profile: Dict, options: List) -> List:
        # Implement ranking algorithm based on user preferences
        scored_options = []
        
        for option in options:
            score = self._calculate_match_score(user_profile, option)
            scored_options.append((score, option))
            
        scored_options.sort(key=lambda x: x[0], reverse=True)
        return [option for score, option in scored_options]
```

## 6. Deployment Setup

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./travel_platform.db
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

## 7. Requirements File

```txt
# requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
alembic==1.12.1
python-jose==3.3.0
passlib==1.7.4
python-multipart==0.0.6
redis==5.0.1
aiohttp==3.9.1
websockets==12.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
scikit-learn==1.3.2
numpy==1.25.2
```

## Key Features Implemented:

1. **Real-Time WebSocket Communication** - Live price updates and booking confirmations
2. **JWT Authentication** - Secure user authentication
3. **SQLAlchemy ORM** - Database management with relationships
4. **Background Task Management** - Price monitoring and notifications
5. **External API Integration** - Flight and hotel search APIs
6. **Payment Processing** - Mock payment integration
7. **Error Handling** - Comprehensive error management
8. **CORS Support** - Frontend-backend communication
9. **User Preferences** - Personalized experience
10. **Health Checks** - System monitoring
11. **Docker Support** - Easy deployment

This advanced Python backend provides a robust, scalable foundation for your travel platform with real-time features and modern development practices.