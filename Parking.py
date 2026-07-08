Directory Structure
textmwarokin/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── parking.py
│   │   ├── reservation.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── parking.py
│   │   ├── reservation.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── parking.py
│   │   ├── reservation.py
│   │   ├── analytics.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_service.py
│   │   ├── websocket_service.py
│   │   ├── payment_service.py
│   ├── dependencies/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── auth.py
│   │   ├── rate_limit.py
│   ├── static/
│   │   ├── css/
│   │   │   ├── styles.css
│   │   ├── js/
│   │   │   ├── main.js
│   ├── templates/
│   │   ├── index.html
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
Python Code Implementation
1. app/main.py
Main entry point for the FastAPI application.
pythonfrom fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from app.routes import auth, parking, reservation, analytics
from app.dependencies.database import engine, Base
from app.dependencies.rate_limit import setup_rate_limiter
import uvicorn

app = FastAPI(
    title="Mwarokin Smart Parking System",
    description="Advanced parking management with AI-driven analytics and real-time updates",
    version="1.0.0"
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(parking.router, prefix="/parking", tags=["parking"])
app.include_router(reservation.router, prefix="/reservation", tags=["reservation"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

# Initialize database
Base.metadata.create_all(bind=engine)

# Setup rate limiter
setup_rate_limiter(app)

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return app.templates.TemplateResponse("index.html", {"request": request})

@app.on_event("startup")
async def startup_event():
    print("Starting Mwarokin Smart Parking System...")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
2. app/models/user.py
SQLAlchemy model for users.
pythonfrom sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    vehicle_type = Column(String, nullable=True)
    license_plate = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
3. app/models/parking.py
SQLAlchemy model for parking locations and spots.
pythonfrom sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .user import Base

class ParkingLocation(Base):
    __tablename__ = "parking_locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    type = Column(String, nullable=False)  # apartments, commercial, public
    latitude = Column(Float)
    longitude = Column(Float)
    total_spots = Column(Integer, nullable=False)
    spots = relationship("ParkingSpot", back_populates="location")

class ParkingSpot(Base):
    __tablename__ = "parking_spots"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("parking_locations.id"))
    spot_number = Column(String, nullable=False)
    status = Column(String, default="available")  # available, occupied, reserved
    type = Column(String, default="standard")  # standard, premium
    location = relationship("ParkingLocation", back_populates="spots")
4. app/models/reservation.py
SQLAlchemy model for reservations.
pythonfrom sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from .user import Base
from datetime import datetime

class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    location_id = Column(Integer, ForeignKey("parking_locations.id"))
    spot_id = Column(Integer, ForeignKey("parking_spots.id"))
    start_time = Column(DateTime, nullable=False)
    duration_hours = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String, default="active")  # active, completed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")
    location = relationship("ParkingLocation")
    spot = relationship("ParkingSpot")
5. app/schemas/user.py
Pydantic schemas for user-related operations.
pythonfrom pydantic import BaseModel, EmailStr, constr
from datetime import datetime

class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    phone: constr(pattern=r"^\+?\d{10,15}$")
    vehicle_type: str | None
    license_plate: str | None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    is_active: bool

    class Config:
        orm_mode = True
6. app/schemas/parking.py
Pydantic schemas for parking-related operations.
pythonfrom pydantic import BaseModel
from typing import List

class ParkingSpotBase(BaseModel):
    spot_number: str
    status: str
    type: str

class ParkingSpotResponse(ParkingSpotBase):
    id: int
    location_id: int

    class Config:
        orm_mode = True

class ParkingLocationBase(BaseModel):
    name: str
    address: str
    type: str
    latitude: float
    longitude: float
    total_spots: int

class ParkingLocationResponse(ParkingLocationBase):
    id: int
    spots: List[ParkingSpotResponse]

    class Config:
        orm_mode = True
7. app/schemas/reservation.py
Pydantic schemas for reservation-related operations.
pythonfrom pydantic import BaseModel
from datetime import datetime

class ReservationBase(BaseModel):
    location_id: int
    spot_id: int
    start_time: datetime
    duration_hours: int

class ReservationCreate(ReservationBase):
    pass

class ReservationResponse(ReservationBase):
    id: int
    user_id: int
    amount: float
    status: str
    created_at: datetime

    class Config:
        orm_mode = True
8. app/dependencies/database.py
Database dependency setup.
pythonfrom sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi import Depends
from typing import Generator

SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost:5432/mwarokin"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
9. app/dependencies/auth.py
JWT-based authentication.
pythonfrom fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .database import get_db
from app.models.user import User
from app.schemas.user import UserResponse
from passlib.context import CryptContext

SECRET_KEY = "your-secret-key-here-secure-32-char"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user
10. app/dependencies/rate_limit.py
Rate limiting with Redis.
pythonfrom fastapi import FastAPI
from fastapi_limiter import FastAPILimiter
from redis.asyncio import Redis

async def setup_rate_limiter(app: FastAPI):
    redis = Redis.from_url("redis://localhost:6379")
    await FastAPILimiter.init(redis)
11. app/routes/auth.py
Authentication routes for login and registration.
pythonfrom fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.dependencies.database import get_db
from app.dependencies.auth import verify_password, get_password_hash, create_access_token
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from fastapi_limiter.depends import RateLimiter

router = APIRouter()

@router.post("/register", response_model=UserResponse, dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    db_user = User(
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        hashed_password=hashed_password,
        vehicle_type=user.vehicle_type,
        license_plate=user.license_plate
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/token", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}
12. app/routes/parking.py
Routes for managing parking locations and spots.
pythonfrom fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.models.parking import ParkingLocation, ParkingSpot
from app.schemas.parking import ParkingLocationResponse, ParkingSpotResponse
from typing import List

router = APIRouter()

@router.get("/locations", response_model=List[ParkingLocationResponse])
async def get_locations(db: Session = Depends(get_db)):
    locations = db.query(ParkingLocation).all()
    return locations

@router.get("/spots/{location_id}", response_model=List[ParkingSpotResponse])
async def get_spots(location_id: int, db: Session = Depends(get_db)):
    spots = db.query(ParkingSpot).filter(ParkingSpot.location_id == location_id).all()
    if not spots:
        raise HTTPException(status_code=404, detail="No spots found for this location")
    return spots
13. app/routes/reservation.py
Routes for reservation management.
pythonfrom fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.models.reservation import Reservation
from app.models.parking import ParkingSpot
from app.schemas.reservation import ReservationCreate, ReservationResponse
from app.services.ai_service import predict_available_spot
from app.services.payment_service import process_payment
from app.services.websocket_service import manager
from datetime import datetime
from typing import List

router = APIRouter()

@router.post("/reserve", response_model=ReservationResponse)
async def create_reservation(reservation: ReservationCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    spot = db.query(ParkingSpot).filter(
        ParkingSpot.id == reservation.spot_id,
        ParkingSpot.status == "available"
    ).first()
    if not spot:
        raise HTTPException(status_code=400, detail="Spot not available")

    # Calculate cost ($4 per hour, premium spots 1.5x)
    rate = 6.0 if spot.type == "premium" else 4.0
    amount = reservation.duration_hours * rate

    # Process payment (simulated)
    payment_success = await process_payment(current_user.id, amount)
    if not payment_success:
        raise HTTPException(status_code=400, detail="Payment failed")

    db_reservation = Reservation(
        user_id=current_user.id,
        location_id=reservation.location_id,
        spot_id=reservation.spot_id,
        start_time=reservation.start_time,
        duration_hours=reservation.duration_hours,
        amount=amount,
        status="active"
    )
    db.add(db_reservation)
    spot.status = "reserved"
    db.commit()
    db.refresh(db_reservation)

    # Broadcast update via WebSocket
    await manager.broadcast({
        "spot_id": spot.id,
        "status": spot.status,
        "location_id": spot.location_id
    })

    return db_reservation

@router.get("/user-reservations", response_model=List[ReservationResponse])
async def get_user_reservations(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    reservations = db.query(Reservation).filter(Reservation.user_id == current_user.id).all()
    return reservations

@router.post("/cancel/{reservation_id}")
async def cancel_reservation(reservation_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    reservation = db.query(Reservation).filter(
        Reservation.id == reservation_id,
        Reservation.user_id == current_user.id
    ).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if reservation.status != "active":
        raise HTTPException(status_code=400, detail="Reservation cannot be cancelled")

    reservation.status = "cancelled"
    spot = db.query(ParkingSpot).filter(ParkingSpot.id == reservation.spot_id).first()
    spot.status = "available"
    db.commit()

    # Broadcast update via WebSocket
    await manager.broadcast({
        "spot_id": spot.id,
        "status": spot.status,
        "location_id": spot.location_id
    })

    return {"message": "Reservation cancelled successfully"}
14. app/routes/analytics.py
Analytics for parking data.
pythonfrom fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from datetime import datetime, timedelta
from redis.asyncio import Redis
import json

router = APIRouter()

@router.get("/analytics")
async def get_analytics(location_id: int | None = None, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    redis = Redis.from_url("redis://localhost:6379")
    cache_key = f"analytics_{location_id or 'all'}"
    cached_data = await redis.get(cache_key)
    if cached_data:
        return json.loads(cached_data)

    # Generate analytics data
    query = db.query(Reservation)
    if location_id:
        query = query.filter(Reservation.location_id == location_id)
    
    total_revenue = sum(r.amount for r in query.all())
    total_spots = db.query(ParkingSpot).count()
    occupied_spots = db.query(ParkingSpot).filter(ParkingSpot.status.in_(["occupied", "reserved"])).count()
    occupancy_rate = (occupied_spots / total_spots * 100) if total_spots > 0 else 0

    data = {
        "labels": [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)],
        "revenue": [total_revenue / 7] * 7,  # Simplified for demo
        "occupancy": [occupancy_rate] * 7,  # Simplified for demo
        "total_revenue": total_revenue,
        "occupancy_rate": occupancy_rate
    }

    await redis.set(cache_key, json.dumps(data), ex=3600)  # Cache for 1 hour
    return data
15. app/services/ai_service.py
AI-driven parking spot prediction (simplified).
pythonfrom sqlalchemy.orm import Session
from app.models.parking import ParkingSpot
from datetime import datetime
import random  # Replace with ML model in production

def predict_available_spot(db: Session, location_id: int, start_time: datetime):
    available_spots = db.query(ParkingSpot).filter(
        ParkingSpot.location_id == location_id,
        ParkingSpot.status == "available"
    ).all()
    # In production, use ML model to predict based on time, location, historical data
    return random.choice(available_spots) if available_spots else None
16. app/services/websocket_service.py
WebSocket service for real-time updates.
pythonfrom fastapi import WebSocket
from typing import Set

class WebSocketManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = WebSocketManager()

async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        await manager.disconnect(websocket)
17. app/services/payment_service.py
Simulated payment processing.
pythonasync def process_payment(user_id: int, amount: float) -> bool:
    # Simulate Stripe payment processing
    # In production, integrate with Stripe SDK
    try:
        # Mock payment logic
        print(f"Processing payment of ${amount} for user {user_id}")
        return True
    except Exception as e:
        print(f"Payment failed: {str(e)}")
        return False
18. app/dependencies/rate_limit.py
Rate limiting setup.
pythonfrom fastapi import FastAPI
from fastapi_limiter import FastAPILimiter
from redis.asyncio import Redis

async def setup_rate_limiter(app: FastAPI):
    redis = Redis.from_url("redis://localhost:6379")
    await FastAPILimiter.init(redis)
19. requirements.txt
List of dependencies.
textfastapi==0.115.0
uvicorn==0.30.6
sqlalchemy==2.0.31
pydantic==2.8.2
passlib[bcrypt]==1.7.4
pyjwt==2.8.0
redis==5.0.8
aiohttp==3.10.5
scikit-learn==1.5.1
python-jose==3.3.0
fastapi-limiter==0.1.6
psycopg2-binary==2.9.9
20. Dockerfile
For containerized deployment.
dockerfileFROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
21. docker-compose.yml
For running the app with PostgreSQL and Redis.
yamlversion: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/mwarokin
      - REDIS_URL=redis://redis:6379

  db:
    image: postgres:14
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: mwarokin
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
Integration with Frontend

Static Files and Templates: The provided HTML is placed in app/templates/index.html. The embedded CSS is extracted to app/static/css/styles.css, and the JavaScript is moved to app/static/js/main.js (modified to work with the backend API).
API Endpoints:

/auth/register: Register a new user.
/auth/token: Login and obtain JWT token.
/parking/locations: Fetch all parking locations.
/parking/spots/{location_id}: Fetch spots for a location.
/reservation/reserve: Create a new reservation.
/reservation/user-reservations: Fetch user reservations.
/reservation/cancel/{reservation_id}: Cancel a reservation.
/analytics: Fetch analytics data.


WebSocket: The frontend connects to /ws for real-time updates on spot status.
Jinja2 Templating: The index.html can be updated to use Jinja2 for dynamic data (e.g., {{ current_user.full_name }}).

Modified Frontend JavaScript (app/static/js/main.js)
The frontend JavaScript is updated to interact with the backend API and WebSocket.
javascript// Initialize WebSocket
const ws = new WebSocket(`wss://${window.location.host}/ws`);

// User data and token
let userData = null;
let token = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    checkLoginStatus();
    renderParkingDashboard();
    setupEventListeners();
    setupWebSocket();
});

// Check login status
async function checkLoginStatus() {
    token = localStorage.getItem('parkingToken');
    if (token) {
        try {
            const response = await fetch('/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                userData = await response.json();
                showUserDashboard();
            } else {
                logoutUser();
            }
        } catch (error) {
            console.error('Error checking login status:', error);
            logoutUser();
        }
    } else {
        showAuthButtons();
    }
}

// Show user dashboard
function showUserDashboard() {
    document.getElementById('authButtons').style.display = 'none';
    document.getElementById('userDashboard').classList.add('active');
    document.getElementById('userName').textContent = userData.full_name;
    document.getElementById('userAvatar').textContent = getInitials(userData.full_name);
    loadUserReservations();
}

// Show auth buttons
function showAuthButtons() {
    document.getElementById('authButtons').style.display = 'flex';
    document.getElementById('userDashboard').classList.remove('active');
}

// Get initials for avatar
function getInitials(name) {
    return name.split(' ').map(n => n[0]).join('').toUpperCase();
}

// Render parking dashboard
async function renderParkingDashboard() {
    const parkingGrid = document.getElementById('parkingGrid');
    parkingGrid.innerHTML = '';
    const activeLocation = document.querySelector('.location-tab.active').dataset.location;

    try {
        const response = await fetch('/parking/locations', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const locations = await response.json();

        locations
            .filter(loc => activeLocation === 'all' || loc.type === activeLocation)
            .forEach(location => {
                parkingGrid.appendChild(createParkingCard(location));
            });
    } catch (error) {
        console.error('Error fetching locations:', error);
        showNotification('Failed to load parking data', 'error');
    }
}

// Create parking card
function createParkingCard(location) {
    const card = document.createElement('div');
    card.className = 'parking-card';
    card.dataset.locationId = location.id;

    const availableCount = location.spots.filter(spot => spot.status === 'available').length;
    const occupiedCount = location.spots.filter(spot => spot.status === 'occupied').length;
    const reservedCount = location.spots.filter(spot => spot.status === 'reserved').length;
    
    let statusBadge = '';
    if (availableCount === 0) {
        statusBadge = `<span class="status-badge status-occupied">Full</span>`;
    } else if (availableCount <= location.total_spots * 0.2) {
        statusBadge = `<span class="status-badge status-occupied">Almost Full</span>`;
    } else {
        statusBadge = `<span class="status-badge status-available">${availableCount} Available</span>`;
    }

    let spotsHTML = '';
    location.spots.forEach(spot => {
        let icon = '🚗';
        if (spot.status === 'occupied') icon = '🚙';
        if (spot.status === 'reserved') icon = '🔒';
        if (spot.type === 'premium') icon = '⭐';

        spotsHTML += `
            <div class="parking-spot ${spot.status}" data-spot="${spot.id}" data-location="${location.id}">
                <div class="spot-icon">${icon}</div>
                <div class="spot-number">${spot.spot_number}</div>
            </div>
        `;
    });

    const percentage = ((location.total_spots - availableCount) / location.total_spots) * 100;

    card.innerHTML = `
        <div class="card-header">
            <h3 class="card-title">${location.name}</h3>
            ${statusBadge}
        </div>
        <div class="spots-grid">
            ${spotsHTML}
        </div>
        <div class="progress-section">
            <div class="progress-label">
                <span>Capacity</span>
                <span>${location.total_spots - availableCount}/${location.total_spots}</span>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar-fill" style="width: ${percentage}%;"></div>
            </div>
        </div>
    `;

    return card;
}

// Setup WebSocket
function setupWebSocket() {
    ws.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        if (data.spot_id && data.status && data.location_id) {
            renderParkingDashboard(); // Refresh dashboard on spot status update
        }
    };
    ws.onopen = () => console.log('WebSocket connected');
    ws.onerror = () => console.error('WebSocket error');
    ws.onclose = () => console.log('WebSocket disconnected');
}

// Setup event listeners
function setupEventListeners() {
    // Registration/Login modal
    document.getElementById('registerBtn').addEventListener('click', () => {
        document.getElementById('registrationModal').classList.add('active');
        switchFormTab('register');
    });

    document.getElementById('loginBtn').addEventListener('click', () => {
        document.getElementById('registrationModal').classList.add('active');
        switchFormTab('login');
    });

    // Hero buttons
    document.getElementById('heroRegisterBtn').addEventListener('click', () => {
        document.getElementById('registrationModal').classList.add('active');
        switchFormTab('register');
    });

    // Form tabs
    document.querySelectorAll('.form-tab').forEach(tab => {
        tab.addEventListener('click', () => switchFormTab(tab.dataset.tab));
    });

    // Registration form
    document.getElementById('registrationForm').addEventListener('submit', registerUser);

    // Login form
    document.getElementById('loginFormElement').addEventListener('submit', loginUser);

    // Location tabs
    document.querySelectorAll('.location-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.location-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            renderParkingDashboard();
        });
    });

    // Parking spot clicks
    document.addEventListener('click', (e) => {
        if (e.target.closest('.parking-spot')) {
            const spotElement = e.target.closest('.parking-spot');
            handleSpotClick(spotElement.dataset.spot, spotElement.dataset.location);
        }
    });

    // Reserve spot button
    document.getElementById('reserveSpotBtn').addEventListener('click', async () => {
        if (!userData) {
            showNotification('Please log in to reserve a spot', 'error');
            document.getElementById('registrationModal').classList.add('active');
            return;
        }

        // Fetch available spot using AI prediction
        const activeLocation = document.querySelector('.location-tab.active').dataset.location;
        const response = await fetch('/parking/locations', { headers: { 'Authorization': `Bearer ${token}` } });
        const locations = await response.json();
        const location = locations.find(loc => activeLocation === 'all' || loc.type === activeLocation);
        if (location) {
            const spot = location.spots.find(s => s.status === 'available');
            if (spot) {
                openReservationModal(spot.id, location.id);
            } else {
                showNotification('No available spots found. Please try another location.', 'error');
            }
        }
    });

    // User menu
    document.getElementById('userMenu').addEventListener('click', function() {
        this.classList.toggle('active');
    });

    // User menu items
    document.getElementById('reservationsBtn').addEventListener('click', showUserReservations);
    document.getElementById('logoutBtn').addEventListener('click', logoutUser);

    // Close modals
    document.querySelectorAll('.close-modal').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.modal-overlay, .registration-modal, .payment-modal').forEach(modal => {
                modal.classList.remove('active');
            });
        });
    });

    // Click outside modals to close
    document.querySelectorAll('.modal-overlay, .registration-modal, .payment-modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.classList.remove('active');
        });
    });

    // Search functionality
    document.getElementById('searchInput').addEventListener('input', function() {
        filterParkingLocations(this.value);
    });

    // Status filter
    document.getElementById('statusFilter').addEventListener('change', function() {
        filterParkingSpots(this.value);
    });

    // Payment method selection
    document.querySelectorAll('.payment-method').forEach(method => {
        method.addEventListener('click', function() {
            document.querySelectorAll('.payment-method').forEach(m => m.classList.remove('active'));
            this.classList.add('active');
        });
    });

    // Reservation form submission
    document.getElementById('reservationForm').addEventListener('submit', submitReservation);

    // Payment form submission
    document.getElementById('paymentForm').addEventListener('submit', submitPayment);
}

// Switch form tabs
function switchFormTab(tabName) {
    document.querySelectorAll('.form-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });
    document.querySelectorAll('.form-content').forEach(form => {
        form.classList.toggle('active', form.id === `${tabName}Form`);
    });
}

// Register user
async function registerUser(e) {
    e.preventDefault();
    const submitBtn = document.getElementById('registerSubmitBtn');
    const btnText = submitBtn.querySelector('.btn-text');
    const spinner = submitBtn.querySelector('.loading-spinner');

    btnText.style.display = 'none';
    spinner.style.display = 'inline-block';

    const formData = {
        full_name: document.getElementById('fullName').value,
        email: document.getElementById('email').value,
        phone: document.getElementById('phone').value,
        password: document.getElementById('password').value,
        vehicle_type: document.getElementById('vehicleType').value,
        license_plate: document.getElementById('licensePlate').value
    };

    if (formData.password !== document.getElementById('confirmPassword').value) {
        showNotification('Passwords do not match', 'error');
        btnText.style.display = 'inline-block';
        spinner.style.display = 'none';
        return;
    }

    try {
        const response = await fetch('/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        if (response.ok) {
            const user = await response.json();
            showNotification('Account created successfully!', 'success');
            document.getElementById('registrationModal').classList.remove('active');
            document.getElementById('registrationForm').reset();
        } else {
            const error = await response.json();
            showNotification(error.detail, 'error');
        }
    } catch (error) {
        showNotification('Registration failed. Please try again.', 'error');
    } finally {
        btnText.style.display = 'inline-block';
        spinner.style.display = 'none';
    }
}

// Login user
async function loginUser(e) {
    e.preventDefault();
    const submitBtn = document.getElementById('loginSubmitBtn');
    const btnText = submitBtn.querySelector('.btn-text');
    const spinner = submitBtn.querySelector('.loading-spinner');

    btnText.style.display = 'none';
    spinner.style.display = 'inline-block';

    const formData = new FormData();
    formData.append('username', document.getElementById('loginEmail').value);
    formData.append('password', document.getElementById('loginPassword').value);

    try {
        const response = await fetch('/auth/token', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            token = data.access_token;
            localStorage.setItem('parkingToken', token);
            const userResponse = await fetch('/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            userData = await userResponse.json();
            showUserDashboard();
            document.getElementById('registrationModal').classList.remove('active');
            showNotification('Logged in successfully!', 'success');
            document.getElementById('loginFormElement').reset();
        } else {
            const error = await response.json();
            showNotification(error.detail, 'error');
        }
    } catch (error) {
        showNotification('Login failed. Please try again.', 'error');
    } finally {
        btnText.style.display = 'inline-block';
        spinner.style.display = 'none';
    }
}

// Logout user
function logoutUser() {
    userData = null;
    token = null;
    localStorage.removeItem('parkingToken');
    showAuthButtons();
    showNotification('Logged out successfully', 'success');
}

// Handle spot click
async function handleSpotClick(spotId, locationId) {
    if (!userData) {
        showNotification('Please log in to reserve a spot', 'error');
        document.getElementById('registrationModal').classList.add('active');
        return;
    }

    try {
        const response = await fetch(`/parking/spots/${locationId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const spots = await response.json();
        const spot = spots.find(s => s.id == spotId);

        if (spot.status === 'available') {
            openReservationModal(spotId, locationId);
        } else if (spot.status === 'reserved') {
            showNotification(`Spot ${spot.spot_number} is reserved.`, 'warning');
        } else {
            showNotification(`Spot ${spot.spot_number} is occupied.`, 'error');
        }
    } catch (error) {
        showNotification('Error fetching spot details', 'error');
    }
}

// Open reservation modal
function openReservationModal(spotId, locationId) {
    document.getElementById('spotNumber').value = spotId;
    document.getElementById('reservationModal').dataset.locationId = locationId;
    document.getElementById('reservationModal').classList.add('active');
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('reservationDate').setAttribute('min', today);
}

// Submit reservation
async function submitReservation(e) {
    e.preventDefault();
    const spotId = document.getElementById('spotNumber').value;
    const locationId = document.getElementById('reservationModal').dataset.locationId;
    const date = document.getElementById('reservationDate').value;
    const time = document.getElementById('reservationTime').value;
    const duration = parseInt(document.getElementById('reservationDuration').value);

    const startTime = new Date(`${date}T${time}`).toISOString();
    const amount = duration * 4; // $4 per hour

    try {
        const response = await fetch('/reservation/reserve', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                location_id: parseInt(locationId),
                spot_id: parseInt(spotId),
                start_time: startTime,
                duration_hours: duration
            })
        });

        if (response.ok) {
            const reservation = await response.json();
            document.getElementById('paymentSpotNumber').textContent = spotId;
            document.getElementById('paymentDuration').textContent = `${duration} hours`;
            document.getElementById('paymentAmount').textContent = `$${amount.toFixed(2)}`;
            document.getElementById('reservationModal').classList.remove('active');
            document.getElementById('paymentModal').classList.add('active');
        } else {
            const error = await response.json();
            showNotification(error.detail, 'error');
        }
    } catch (error) {
        showNotification('Error creating reservation', 'error');
    }
}

// Submit payment
async function submitPayment(e) {
    e.preventDefault();
    const submitBtn = document.getElementById('paymentSubmitBtn');
    const btnText = submitBtn.querySelector('.btn-text');
    const spinner = submitBtn.querySelector('.loading-spinner');

    btnText.style.display = 'none';
    spinner.style.display = 'inline-block';

    try {
        // Simulate payment processing
        await new Promise(resolve => setTimeout(resolve, 1500));
        document.getElementById('paymentModal').classList.remove('active');
        showNotification('Payment successful! Reservation confirmed.', 'success');
        document.getElementById('paymentForm').reset();
        renderParkingDashboard();
    } catch (error) {
        showNotification('Payment failed. Please try again.', 'error');
    } finally {
        btnText.style.display = 'inline-block';
        spinner.style.display = 'none';
    }
}

// Show user reservations
async function showUserReservations() {
    document.getElementById('dashboard').style.display = 'none';
    document.getElementById('userReservations').style.display = 'block';
    document.getElementById('userMenu').classList.remove('active');
    await renderUserReservations();
}

// Render user reservations
async function renderUserReservations() {
    const reservationsList = document.getElementById('reservationsList');
    reservationsList.innerHTML = '';

    try {
        const response = await fetch('/reservation/user-reservations', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const reservations = await response.json();

        if (reservations.length === 0) {
            reservationsList.innerHTML = '<p style="text-align: center; color: var(--gray-light);">No reservations found.</p>';
            return;
        }

        reservations.forEach(reservation => {
            const reservationCard = document.createElement('div');
            reservationCard.className = 'reservation-card';

            let statusBadge = '';
            if (reservation.status === 'active') {
                statusBadge = '<span class="status-badge status-available">Active</span>';
            } else if (reservation.status === 'completed') {
                statusBadge = '<span class="status-badge" style="background: rgba(100, 116, 139, 0.2); color: var(--gray); border: 1px solid rgba(100, 116, 139, 0.3);">Completed</span>';
            } else if (reservation.status === 'cancelled') {
                statusBadge = '<span class="status-badge status-occupied">Cancelled</span>';
            }

            reservationCard.innerHTML = `
                <div class="reservation-info">
                    <h4>Spot ${reservation.spot_id} - ${reservation.location_id}</h4>
                    <p>${new Date(reservation.start_time).toLocaleString()} | ${reservation.duration_hours} hours | $${reservation.amount.toFixed(2)}</p>
                </div>
                <div class="reservation-actions">
                    ${statusBadge}
                    ${reservation.status === 'active' ? `<button class="btn btn-outline cancel-reservation" data-id="${reservation.id}">Cancel</button>` : ''}
                </div>
            `;
            reservationsList.appendChild(reservationCard);
        });

        document.querySelectorAll('.cancel-reservation').forEach(button => {
            button.addEventListener('click', async () => {
                const reservationId = button.dataset.id;
                try {
                    const response = await fetch(`/reservation/cancel/${reservationId}`, {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    if (response.ok) {
                        showNotification('Reservation cancelled successfully', 'success');
                        renderUserReservations();
                    } else {
                        const error = await response.json();
                        showNotification(error.detail, 'error');
                    }
                } catch (error) {
                    showNotification('Error cancelling reservation', 'error');
                }
            });
        });
    } catch (error) {
        showNotification('Error loading reservations', 'error');
    }
}

// Filter parking locations
function filterParkingLocations(searchTerm) {
    const parkingCards = document.querySelectorAll('.parking-card');
    const term = searchTerm.toLowerCase();

    parkingCards.forEach(card => {
        const title = card.querySelector('.card-title').textContent.toLowerCase();
        card.style.display = title.includes(term) ? 'block' : 'none';
    });
}

// Filter parking spots
function filterParkingSpots(status) {
    const parkingSpots = document.querySelectorAll('.parking-spot');
    parkingSpots.forEach(spot => {
        spot.style.display = (status === 'all' || spot.classList.contains(status)) ? 'flex' : 'none';
    });
}

// Show notification
function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    const notificationText = notification.querySelector('.notification-text');
    
    notificationText.innerHTML = `<strong>${type.charAt(0).toUpperCase() + type.slice(1)}!</strong> ${message}`;
    notification.className = `notification ${type} active`;
    
    setTimeout(() => {
        notification.classList.remove('active');
    }, 5000);
}
Database Initialization
To populate the database with initial data (locations and spots), you can run the following script:
python# app/init_db.py
from sqlalchemy.orm import Session
from app.dependencies.database import SessionLocal, Base, engine
from app.models.parking import ParkingLocation, ParkingSpot

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Add sample locations and spots
    locations = [
        {"name": "Villa A Parking", "address": "123 Villa St", "type": "apartments", "latitude": 40.7128, "longitude": -74.0060, "total_spots": 80},
        {"name": "Villa B Parking", "address": "456 Villa St", "type": "apartments", "latitude": 40.7129, "longitude": -74.0061, "total_spots": 60},
        {"name": "Commercial Building", "address": "789 Commerce Rd", "type": "commercial", "latitude": 40.7130, "longitude": -74.0062, "total_spots": 120},
        {"name": "Public Parking Area", "address": "101 Public Ave", "type": "public", "latitude": 40.7131, "longitude": -74.0063, "total_spots": 200}
    ]

    for loc in locations:
        db_location = db.query(ParkingLocation).filter(ParkingLocation.name == loc["name"]).first()
        if not db_location:
            db_location = ParkingLocation(**loc)
            db.add(db_location)
            db.commit()
            db.refresh(db_location)

            # Add spots
            for i in range(1, min(9, loc["total_spots"] + 1)):
                spot_number = f"{loc['name'][0]}{i}"
                spot_type = "premium" if i % 4 == 0 else "standard"
                db_spot = ParkingSpot(
                    location_id=db_location.id,
                    spot_number=spot_number,
                    status="available",
                    type=spot_type
                )
                db.add(db_spot)
            db.commit()

    db.close()

if __name__ == "__main__":
    init_db()
Run the script:
bashpython app/init_db.py
How to Run

Install Dependencies:
bashpip install -r requirements.txt

Set Up Environment:

Update SQLALCHEMY_DATABASE_URL in app/dependencies/database.py with your PostgreSQL credentials.
Update SECRET_KEY in app/dependencies/auth.py with a secure key.


Run PostgreSQL and Redis:
bashdocker-compose up -d

Initialize Database:
bashpython app/init_db.py

Run the Application:
bashuvicorn app.main:app --host 0.0.0.0 --port 8000

Access the Frontend:
Open http://localhost:8000 in a browser.

Future Enhancements

Advanced AI: Replace predict_available_spot with a machine learning model trained on historical parking data (e.g., using scikit-learn or TensorFlow).
Payment Integration: Fully integrate with Stripe or PayPal for real payment processing.
WebGL Map: Add an interactive WebGL-based parking map for visualization.
Push Notifications: Implement WebPush for real-time reservation updates.
Analytics Dashboard: Expand analytics with detailed charts using Chart.js or Plotly.

This implementation provides a robust, scalable, and futuristic backend that integrates seamlessly with the provided frontend, handling user authentication, parking management, reservations, payments, and real-time updates. Let me know if you need further customization or specific feature implementations!