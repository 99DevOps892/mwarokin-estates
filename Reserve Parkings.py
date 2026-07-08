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
The main entry point for the FastAPI application.
pythonfrom fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, parking, reservation, analytics
from app.dependencies.database import engine, Base
from app.dependencies.rate_limit import setup_rate_limiter
import uvicorn

app = FastAPI(
    title="Mwarokin Parking System",
    description="A futuristic parking management system with AI-driven analytics",
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

@app.on_event("startup")
async def startup_event():
    print("Starting Mwarokin Parking System...")

@app.get("/")
async def root():
    return {"message": "Welcome to Mwarokin Parking System"}

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
    hashed_password = Column(String, nullable=False)
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
    latitude = Column(Float)
    longitude = Column(Float)
    total_spots = Column(Integer, nullable=False)
    spots = relationship("ParkingSpot", back_populates="location")

class ParkingSpot(Base):
    __tablename__ = "parking_spots"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("parking_locations.id"))
    spot_number = Column(String, nullable=False)
    is_occupied = Column(Boolean, default=False)
    is_reserved = Column(Boolean, default=False)
    is_ev_charging = Column(Boolean, default=False)
    location = relationship("ParkingLocation", back_populates="spots")
4. app/models/reservation.py
SQLAlchemy model for reservations.
pythonfrom sqlalchemy import Column, Integer, String, DateTime, ForeignKey
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
    duration = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")
    location = relationship("ParkingLocation")
    spot = relationship("ParkingSpot")
5. app/schemas/user.py
Pydantic schemas for user-related operations.
pythonfrom pydantic import BaseModel, EmailStr
from datetime import datetime

class UserBase(BaseModel):
    full_name: str
    email: EmailStr

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

class ParkingLocationBase(BaseModel):
    name: str
    address: str
    latitude: float
    longitude: float
    total_spots: int

class ParkingLocationResponse(ParkingLocationBase):
    id: int

    class Config:
        orm_mode = True

class ParkingSpotBase(BaseModel):
    spot_number: str
    is_occupied: bool
    is_reserved: bool
    is_ev_charging: bool

class ParkingSpotResponse(ParkingSpotBase):
    id: int
    location_id: int

    class Config:
        orm_mode = True
7. app/schemas/reservation.py
Pydantic schemas for reservation-related operations.
pythonfrom pydantic import BaseModel
from datetime import datetime

class ReservationBase(BaseModel):
    location_id: int
    start_time: datetime
    duration: str

class ReservationCreate(ReservationBase):
    pass

class ReservationResponse(ReservationBase):
    id: int
    user_id: int
    spot_id: int
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

SECRET_KEY = "your-secret-key"
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
Rate limiting using Redis.
pythonfrom fastapi import FastAPI
from fastapi_limiter import FastAPILimiter
from redis.asyncio import Redis

async def setup_rate_limiter(app: FastAPI):
    redis = Redis.from_url("redis://localhost:6379")
    await FastAPILimiter.init(redis)
11. app/routes/auth.py
Authentication routes.
pythonfrom fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.dependencies.database import get_db
from app.dependencies.auth import verify_password, get_password_hash, create_access_token
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    db_user = User(full_name=user.full_name, email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/token")
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
Parking location and spot management.
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
    return spots
13. app/routes/reservation.py
Reservation management.
pythonfrom fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.models.reservation import Reservation
from app.models.parking import ParkingSpot
from app.schemas.reservation import ReservationCreate, ReservationResponse
from datetime import datetime
from app.services.ai_service import predict_available_spot

router = APIRouter()

@router.post("/reserve", response_model=ReservationResponse)
async def create_reservation(reservation: ReservationCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # AI-driven spot selection
    spot = predict_available_spot(db, reservation.location_id, reservation.start_time)
    if not spot:
        raise HTTPException(status_code=400, detail="No available spots")
    
    db_reservation = Reservation(
        user_id=current_user.id,
        location_id=reservation.location_id,
        spot_id=spot.id,
        start_time=reservation.start_time,
        duration=reservation.duration
    )
    db.add(db_reservation)
    spot.is_reserved = True
    db.commit()
    db.refresh(db_reservation)
    return db_reservation
14. app/routes/analytics.py
Analytics and real-time data.
pythonfrom fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from datetime import datetime, timedelta
from redis.asyncio import Redis
import json

router = APIRouter()

@router.get("/analytics")
async def get_analytics(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    redis = Redis.from_url("redis://localhost:6379")
    cached_data = await redis.get("analytics_data")
    if cached_data:
        return json.loads(cached_data)

    # Mock analytics data
    data = {
        "labels": [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)],
        "occupancy": [78, 80, 75, 82, 79, 77, 81],
        "revenue": [12847, 11500, 13000, 12500, 12000, 11800, 12900]
    }
    await redis.set("analytics_data", json.dumps(data), ex=3600)  # Cache for 1 hour
    return data
15. app/services/ai_service.py
AI-driven parking spot prediction (simplified).
pythonfrom sqlalchemy.orm import Session
from app.models.parking import ParkingSpot
from datetime import datetime
import random  # Replace with ML model in production

def predict_available_spot(db: Session, location_id: int, start_time: datetime):
    # Simplified logic: select random available spot
    # In production, use ML model (e.g., scikit-learn) with historical data
    available_spots = db.query(ParkingSpot).filter(
        ParkingSpot.location_id == location_id,
        ParkingSpot.is_occupied == False,
        ParkingSpot.is_reserved == False
    ).all()
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
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = WebSocketManager()

async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast({"message": data})
    except:
        await manager.disconnect(websocket)
17. app/dependencies/rate_limit.py
Rate limiting setup.
pythonfrom fastapi import FastAPI
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from redis.asyncio import Redis

async def setup_rate_limiter(app: FastAPI):
    redis = Redis.from_url("redis://localhost:6379")
    await FastAPILimiter.init(redis)
18. requirements.txt
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
19. Dockerfile
For containerized deployment.
dockerfileFROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
20. docker-compose.yml
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

Static Files: The provided HTML is placed in app/templates/index.html. The CSS is in app/static/css/styles.css, and the JavaScript is in app/static/js/main.js.
WebSocket: The frontend JavaScript connects to the /ws endpoint for real-time updates.
API Endpoints: The frontend interacts with the API endpoints (/auth, /parking, /reservation, /analytics).
Jinja2 Templating: The index.html uses Jinja2 for dynamic rendering of user data and locations.

How to Run

Install Dependencies:
bashpip install -r requirements.txt

Set Up Environment:

Update SQLALCHEMY_DATABASE_URL in app/dependencies/database.py with your PostgreSQL credentials.
Update SECRET_KEY in app/dependencies/auth.py.


Run PostgreSQL and Redis:
Use docker-compose.yml to start the services:
bashdocker-compose up -d

Run the Application:
bashuvicorn app.main:app --host 0.0.0.0 --port 8000

Access the Frontend:
Open http://localhost:8000 in a browser.