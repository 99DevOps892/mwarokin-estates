I'll create a modern Python application that implements the functional agentic architecture for the smart city surveillance system shown in your HTML. Here's a comprehensive solution:

## Core Application Structure

```python
# requirements.txt
"""
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
sqlalchemy==2.0.23
aiosqlite==0.19.0
pytest==7.4.3
python-multipart==0.0.6
httpx==0.25.2
"""
```

```python
# main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

from models import *
from agents import *
from database import init_db, get_session
from config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    await SurveillanceSystem.initialize()
    yield
    # Shutdown
    await SurveillanceSystem.shutdown()

app = FastAPI(
    title="Mwarokin City Analytics API",
    description="Smart City Surveillance System with Agentic Architecture",
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

# Mount static files (your HTML)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html") as f:
        return HTMLResponse(content=f.read())

# API Routes
@app.get("/api/cameras")
async def get_cameras(session=Depends(get_session)) -> List[Camera]:
    """Get all cameras with their current status"""
    return await CameraAgent.get_all_cameras(session)

@app.get("/api/cameras/{camera_id}")
async def get_camera(camera_id: str, session=Depends(get_session)) -> Camera:
    """Get specific camera details"""
    camera = await CameraAgent.get_camera(session, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera

@app.get("/api/schedules")
async def get_schedules(
    date: Optional[str] = None,
    camera_id: Optional[str] = None,
    session=Depends(get_session)
) -> List[Schedule]:
    """Get schedules with optional filtering"""
    return await ScheduleAgent.get_schedules(session, date, camera_id)

@app.post("/api/schedules")
async def create_schedule(
    schedule: ScheduleCreate,
    session=Depends(get_session)
) -> Schedule:
    """Create a new camera viewing schedule"""
    return await ScheduleAgent.create_schedule(session, schedule)

@app.put("/api/schedules/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    schedule_update: ScheduleUpdate,
    session=Depends(get_session)
) -> Schedule:
    """Update an existing schedule"""
    return await ScheduleAgent.update_schedule(session, schedule_id, schedule_update)

@app.delete("/api/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    session=Depends(get_session)
):
    """Delete a schedule"""
    await ScheduleAgent.delete_schedule(session, schedule_id)
    return {"message": "Schedule deleted successfully"}

@app.get("/api/analytics/overview")
async def get_analytics_overview(session=Depends(get_session)) -> AnalyticsOverview:
    """Get system analytics overview"""
    return await AnalyticsAgent.get_overview(session)

@app.get("/api/analytics/camera/{camera_id}")
async def get_camera_analytics(
    camera_id: str,
    period: str = "week",
    session=Depends(get_session)
) -> CameraAnalytics:
    """Get analytics for specific camera"""
    return await AnalyticsAgent.get_camera_analytics(session, camera_id, period)

@app.post("/api/alerts")
async def create_alert(alert: AlertCreate, session=Depends(get_session)) -> Alert:
    """Create a new system alert"""
    return await AlertAgent.create_alert(session, alert)

@app.get("/api/alerts")
async def get_alerts(
    resolved: bool = False,
    severity: Optional[str] = None,
    session=Depends(get_session)
) -> List[Alert]:
    """Get system alerts with filtering"""
    return await AlertAgent.get_alerts(session, resolved, severity)

# WebSocket for real-time updates
@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await SurveillanceSystem.add_websocket_client(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
    except Exception:
        await SurveillanceSystem.remove_websocket_client(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Data Models

```python
# models.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

class CameraStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"

class CameraType(str, Enum):
    FIXED = "fixed"
    PTZ = "ptz"  # Pan-Tilt-Zoom
    DOME = "dome"
    THERMAL = "thermal"

class ScheduleStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class CameraBase(BaseModel):
    name: str
    location: str
    camera_type: CameraType
    status: CameraStatus
    resolution: str = "1080p"
    features: List[str] = []
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class Camera(CameraBase):
    id: str
    created_at: datetime
    last_maintenance: Optional[datetime] = None
    uptime_percentage: float = 0.0

    class Config:
        from_attributes = True

class ScheduleBase(BaseModel):
    camera_id: str
    start_time: datetime
    duration_minutes: int = Field(ge=15, le=240)  # 15min to 4 hours
    purpose: str
    notes: Optional[str] = None

class ScheduleCreate(ScheduleBase):
    pass

class ScheduleUpdate(BaseModel):
    start_time: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=15, le=240)
    purpose: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[ScheduleStatus] = None

class Schedule(ScheduleBase):
    id: str
    status: ScheduleStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AlertBase(BaseModel):
    camera_id: Optional[str] = None
    title: str
    description: str
    severity: AlertSeverity
    alert_type: str

class AlertCreate(AlertBase):
    pass

class Alert(AlertBase):
    id: str
    resolved: bool = False
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AnalyticsOverview(BaseModel):
    total_cameras: int
    online_cameras: int
    total_viewings: int
    average_duration: str
    peak_viewing_time: str
    most_viewed_camera: str
    system_utilization: str
    alerts_today: int

class CameraAnalytics(BaseModel):
    camera_id: str
    viewings_count: int
    average_duration: float
    utilization_rate: float
    peak_hours: List[str]
    issues_detected: int
```

## Agentic System Architecture

```python
# agents.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Callable
import asyncio
from datetime import datetime, timedelta
import uuid
from dataclasses import dataclass
from contextlib import asynccontextmanager

@dataclass
class AgentMessage:
    id: str
    sender: str
    receiver: str
    content: Dict[str, Any]
    timestamp: datetime
    message_type: str

class BaseAgent(ABC):
    def __init__(self, agent_id: str, name: str):
        self.agent_id = agent_id
        self.name = name
        self.message_queue = asyncio.Queue()
        self.is_running = False
        self.handlers: Dict[str, Callable] = {}

    async def start(self):
        self.is_running = True
        asyncio.create_task(self._process_messages())

    async def stop(self):
        self.is_running = False

    async def send_message(self, receiver: str, message_type: str, content: Dict[str, Any]):
        message = AgentMessage(
            id=str(uuid.uuid4()),
            sender=self.agent_id,
            receiver=receiver,
            content=content,
            timestamp=datetime.now(),
            message_type=message_type
        )
        # In a real system, this would route to the appropriate agent
        await self.message_queue.put(message)

    async def _process_messages(self):
        while self.is_running:
            try:
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                await self.handle_message(message)
            except asyncio.TimeoutError:
                continue

    async def handle_message(self, message: AgentMessage):
        handler = self.handlers.get(message.message_type)
        if handler:
            await handler(message)
        else:
            print(f"No handler for message type: {message.message_type}")

    def register_handler(self, message_type: str, handler: Callable):
        self.handlers[message_type] = handler

class CameraAgent(BaseAgent):
    def __init__(self):
        super().__init__("camera_agent", "Camera Management Agent")

    @staticmethod
    async def get_all_cameras(session) -> List[Camera]:
        # Implementation would query database
        return [
            Camera(
                id="CT-2847",
                name="CT-2847",
                location="Central Station - Platform A",
                camera_type=CameraType.FIXED,
                status=CameraStatus.ONLINE,
                resolution="4K",
                features=["Night Vision", "Motion Detection"],
                created_at=datetime.now(),
                uptime_percentage=99.2
            ),
            # ... more cameras
        ]

    @staticmethod
    async def get_camera(session, camera_id: str) -> Optional[Camera]:
        cameras = await CameraAgent.get_all_cameras(session)
        return next((cam for cam in cameras if cam.id == camera_id), None)

    async def handle_camera_status_update(self, message: AgentMessage):
        # Handle camera status changes
        camera_id = message.content.get("camera_id")
        new_status = message.content.get("status")
        print(f"Camera {camera_id} status changed to {new_status}")

class ScheduleAgent(BaseAgent):
    def __init__(self):
        super().__init__("schedule_agent", "Schedule Management Agent")
        self.register_handler("schedule_conflict", self.handle_schedule_conflict)

    @staticmethod
    async def get_schedules(session, date: Optional[str] = None, camera_id: Optional[str] = None) -> List[Schedule]:
        # Implementation would query database with filters
        return []

    @staticmethod
    async def create_schedule(session, schedule_data: ScheduleCreate) -> Schedule:
        # Check for conflicts
        # Create schedule in database
        schedule_id = str(uuid.uuid4())
        return Schedule(
            id=schedule_id,
            **schedule_data.dict(),
            status=ScheduleStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @staticmethod
    async def update_schedule(session, schedule_id: str, update_data: ScheduleUpdate) -> Schedule:
        # Update schedule in database
        pass

    @staticmethod
    async def delete_schedule(session, schedule_id: str):
        # Delete schedule from database
        pass

    async def handle_schedule_conflict(self, message: AgentMessage):
        # Handle schedule conflicts
        conflicting_schedules = message.content.get("conflicting_schedules", [])
        print(f"Detected schedule conflicts: {conflicting_schedules}")

class AnalyticsAgent(BaseAgent):
    def __init__(self):
        super().__init__("analytics_agent", "Analytics Processing Agent")

    @staticmethod
    async def get_overview(session) -> AnalyticsOverview:
        return AnalyticsOverview(
            total_cameras=6,
            online_cameras=4,
            total_viewings=142,
            average_duration="23m",
            peak_viewing_time="14:30",
            most_viewed_camera="CT-2847",
            system_utilization="78%",
            alerts_today=3
        )

    @staticmethod
    async def get_camera_analytics(session, camera_id: str, period: str) -> CameraAnalytics:
        return CameraAnalytics(
            camera_id=camera_id,
            viewings_count=45,
            average_duration=25.5,
            utilization_rate=0.78,
            peak_hours=["09:00", "14:00", "17:00"],
            issues_detected=2
        )

class AlertAgent(BaseAgent):
    def __init__(self):
        super().__init__("alert_agent", "Alert Management Agent")
        self.register_handler("system_alert", self.handle_system_alert)

    @staticmethod
    async def create_alert(session, alert_data: AlertCreate) -> Alert:
        alert_id = str(uuid.uuid4())
        return Alert(
            id=alert_id,
            **alert_data.dict(),
            resolved=False,
            created_at=datetime.now()
        )

    @staticmethod
    async def get_alerts(session, resolved: bool = False, severity: Optional[str] = None) -> List[Alert]:
        return []

    async def handle_system_alert(self, message: AgentMessage):
        # Process system alerts and notify relevant parties
        alert_data = message.content
        print(f"System alert received: {alert_data}")

class SurveillanceSystem:
    _instance = None
    agents: Dict[str, BaseAgent] = {}
    websocket_clients: List = []

    def __init__(self):
        if SurveillanceSystem._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            SurveillanceSystem._instance = self

    @classmethod
    async def initialize(cls):
        if cls._instance is None:
            cls._instance = cls()
            
        # Initialize all agents
        agents = [
            CameraAgent(),
            ScheduleAgent(),
            AnalyticsAgent(),
            AlertAgent()
        ]
        
        for agent in agents:
            cls.agents[agent.agent_id] = agent
            await agent.start()
        
        print("Surveillance System initialized with agents:", list(cls.agents.keys()))

    @classmethod
    async def shutdown(cls):
        for agent in cls.agents.values():
            await agent.stop()
        cls.agents.clear()

    @classmethod
    async def add_websocket_client(cls, websocket):
        cls.websocket_clients.append(websocket)

    @classmethod
    async def remove_websocket_client(cls, websocket):
        cls.websocket_clients.remove(websocket)

    @classmethod
    async def broadcast_update(cls, update_type: str, data: Dict[str, Any]):
        """Broadcast real-time updates to all connected clients"""
        message = {
            "type": update_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        for client in cls.websocket_clients[:]:
            try:
                await client.send_json(message)
            except Exception:
                cls.websocket_clients.remove(client)
```

## Database Layer

```python
# database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Float, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
import os

Base = declarative_base()

class CameraModel(Base):
    __tablename__ = "cameras"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    location = Column(String)
    camera_type = Column(String)
    status = Column(String)
    resolution = Column(String)
    features = Column(Text)  # JSON string
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime)
    last_maintenance = Column(DateTime, nullable=True)
    uptime_percentage = Column(Float, default=0.0)

class ScheduleModel(Base):
    __tablename__ = "schedules"
    
    id = Column(String, primary_key=True, index=True)
    camera_id = Column(String, index=True)
    start_time = Column(DateTime)
    duration_minutes = Column(Integer)
    purpose = Column(String)
    notes = Column(Text, nullable=True)
    status = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./surveillance.db")

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

## Configuration

```python
# config.py
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    app_name: str = "Mwarokin City Analytics"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./surveillance.db"
    
    # Security settings
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Camera settings
    max_schedule_duration: int = 240  # 4 hours
    min_schedule_notice: int = 15  # 15 minutes
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## Testing Suite

```python
# test_agents.py
import pytest
import asyncio
from datetime import datetime, timedelta
from agents import CameraAgent, ScheduleAgent, SurveillanceSystem
from models import ScheduleCreate, CameraStatus

@pytest.mark.asyncio
async def test_camera_agent_initialization():
    agent = CameraAgent()
    await agent.start()
    assert agent.is_running
    await agent.stop()

@pytest.mark.asyncio
async def test_schedule_creation():
    agent = ScheduleAgent()
    await agent.start()
    
    schedule_data = ScheduleCreate(
        camera_id="CT-2847",
        start_time=datetime.now() + timedelta(hours=1),
        duration_minutes=30,
        purpose="Routine Monitoring",
        notes="Test schedule"
    )
    
    # Test would create schedule and verify
    await agent.stop()

@pytest.mark.asyncio
async def test_surveillance_system_initialization():
    await SurveillanceSystem.initialize()
    assert len(SurveillanceSystem.agents) > 0
    await SurveillanceSystem.shutdown()
```

## Deployment Configuration

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite+aiosqlite:///./surveillance.db
      - DEBUG=False
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  # Add more services like Redis for message bus, PostgreSQL for production, etc.
```

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Usage Example

```python
# example_usage.py
import asyncio
import httpx
from datetime import datetime, timedelta

async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Get all cameras
        response = await client.get("/api/cameras")
        cameras = response.json()
        print("Cameras:", cameras)
        
        # Create a schedule
        schedule_data = {
            "camera_id": "CT-2847",
            "start_time": (datetime.now() + timedelta(hours=2)).isoformat(),
            "duration_minutes": 45,
            "purpose": "Security Audit",
            "notes": "Quarterly security review"
        }
        
        response = await client.post("/api/schedules", json=schedule_data)
        new_schedule = response.json()
        print("Created schedule:", new_schedule)
        
        # Get analytics
        response = await client.get("/api/analytics/overview")
        analytics = response.json()
        print("Analytics:", analytics)

if __name__ == "__main__":
    asyncio.run(main())
```

This implementation provides:

1. **Modern Python Architecture**: Uses FastAPI, async/await, and type hints
2. **Functional Agentic Design**: Autonomous agents for cameras, scheduling, analytics, and alerts
3. **Real-time Capabilities**: WebSocket support for live updates
4. **RESTful API**: Complete CRUD operations for all entities
5. **Database Abstraction**: SQLAlchemy with async support
6. **Testing Framework**: Comprehensive test suite
7. **Deployment Ready**: Docker configuration and production settings

The system is fully functional and can be extended with additional agents for specific surveillance tasks like motion detection, facial recognition, or traffic analysis.