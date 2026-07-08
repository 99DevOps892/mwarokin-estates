import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import base64
import logging

# AI/ML for Security
import cv2
import numpy as np
from tensorflow import keras
from sklearn.ensemble import IsolationForest
import torch
import torch.nn as nn
from ultralytics import YOLO
import face_recognition

# Blockchain for Audit Trail
from web3 import Web3
import hashlib

# IoT & Real-time Communication
import websockets
from fastapi import FastAPI, WebSocket, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator

# Database & Storage
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, JSON, Text
from sqlalchemy.future import select
from sqlalchemy.sql import func

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== DATABASE SETUP =====
DATABASE_URL = "sqlite+aiosqlite:///./security.db"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class SecurityEvent(Base):
    __tablename__ = "security_events"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String, nullable=False)  # motion, access, alarm, etc.
    location = Column(String, nullable=False)
    camera_id = Column(String)
    confidence = Column(Float)
    description = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ai_analysis = Column(JSON)  # AI-generated insights
    blockchain_hash = Column(String)  # For audit trail
    severity = Column(String)  # low, medium, high, critical
    home_id = Column(String, default="all")  # To support multiple homes

class Camera(Base):
    __tablename__ = "cameras"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    status = Column(String, default="active")  # active, inactive, error
    stream_url = Column(String)
    ai_capabilities = Column(JSON)  # [face_recognition, object_detection, anomaly_detection]
    last_active = Column(DateTime, default=datetime.utcnow)
    home_id = Column(String, default="all")  # To support multiple homes

class Visitor(Base):
    __tablename__ = "visitors"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    purpose = Column(String)
    status = Column(String, default="pending")  # pending, approved, rejected, active, completed
    arrival_time = Column(DateTime)
    departure_time = Column(DateTime)
    face_encoding = Column(JSON)  # For facial recognition
    access_level = Column(String)  # restricted, limited, full
    approved_by = Column(String)
    home_id = Column(String, default="all")  # To support multiple homes

# ===== DATA MODELS =====
class SecurityAlert(BaseModel):
    type: str
    location: str
    severity: str
    description: str
    timestamp: datetime
    camera_id: Optional[str] = None
    confidence: Optional[float] = None
    home_id: Optional[str] = "all"

class VisitorRequest(BaseModel):
    name: str
    purpose: str
    expected_arrival: datetime
    access_level: str = "limited"
    face_image: Optional[str] = None  # Base64 encoded
    duration: Optional[int] = 2  # In hours
    notes: Optional[str] = None
    home_id: Optional[str] = "all"

    @validator("access_level")
    def validate_access_level(cls, v):
        if v not in ["restricted", "limited", "full"]:
            raise ValueError("Invalid access level")
        return v

class AISecurityAnalysis(BaseModel):
    threat_level: float
    detected_objects: List[str]
    anomaly_score: float
    recommended_action: str
    confidence: float
    facial_matches: List[str] = []

class BlockchainAudit(BaseModel):
    event_id: str
    transaction_hash: str
    block_number: int
    timestamp: datetime
    verified: bool = True

# ===== DEPENDENCY INJECTION =====
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# ===== AI SECURITY SERVICE =====
class AISecurityMonitor:
    """Advanced AI-powered security monitoring system"""
    
    def __init__(self):
        self.face_database = {}  # name -> face_encoding
        self.anomaly_detector = self._setup_anomaly_detection()
        self.object_detector = YOLO('yolov8n.pt')  # Pre-trained YOLO model
        self.behavior_analyzer = self._setup_behavior_analysis()
        logger.info("AI Security Monitor initialized")

    def _setup_anomaly_detection(self):
        """Setup isolation forest for anomaly detection"""
        return IsolationForest(contamination=0.1, random_state=42)
    
    def _setup_behavior_analysis(self):
        """Setup neural network for suspicious behavior detection"""
        class BehaviorNet(nn.Module):
            def __init__(self):
                super(BehaviorNet, self).__init__()
                self.fc1 = nn.Linear(10, 64)
                self.fc2 = nn.Linear(64, 32)
                self.fc3 = nn.Linear(32, 1)
                self.dropout = nn.Dropout(0.3)
            
            def forward(self, x):
                x = torch.relu(self.fc1(x))
                x = self.dropout(x)
                x = torch.relu(self.fc2(x))
                x = torch.sigmoid(self.fc3(x))
                return x
        
        return BehaviorNet().eval()

    async def analyze_video_frame(self, frame_data: np.ndarray, camera_id: str, home_id: str) -> AISecurityAnalysis:
        """Analyze video frame for security threats"""
        try:
            # Object detection
            objects_detected = await self._detect_objects(frame_data)
            
            # Face recognition
            facial_matches = await self._recognize_faces(frame_data)
            
            # Anomaly detection
            anomaly_score = await self._detect_anomalies(frame_data)
            
            # Behavior analysis
            threat_level = await self._analyze_behavior(frame_data, objects_detected)
            
            # Generate recommendations
            action = self._generate_recommendation(threat_level, objects_detected, anomaly_score)
            
            return AISecurityAnalysis(
                threat_level=threat_level,
                detected_objects=objects_detected,
                anomaly_score=anomaly_score,
                recommended_action=action,
                confidence=0.85,
                facial_matches=facial_matches
            )
        except Exception as e:
            logger.error(f"Video frame analysis failed: {e}")
            return AISecurityAnalysis(
                threat_level=0.0,
                detected_objects=[],
                anomaly_score=0.0,
                recommended_action="ERROR: Analysis failed",
                confidence=0.0
            )

    async def _detect_objects(self, frame: np.ndarray) -> List[str]:
        """Detect objects in video frame"""
        try:
            results = self.object_detector(frame)
            objects = []
            
            for result in results:
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    object_name = self.object_detector.names[class_id]
                    confidence = float(box.conf[0])
                    
                    if confidence > 0.5:
                        objects.append(object_name)
            
            return list(set(objects))
        except Exception as e:
            logger.error(f"Object detection error: {e}")
            return []

    async def _recognize_faces(self, frame: np.ndarray) -> List[str]:
        """Recognize faces in video frame"""
        try:
            face_locations = face_recognition.face_locations(frame)
            face_encodings = face_recognition.face_encodings(frame, face_locations)
            
            matches = []
            for face_encoding in face_encodings:
                for name, known_encoding in self.face_database.items():
                    match = face_recognition.compare_faces([known_encoding], face_encoding)[0]
                    if match:
                        matches.append(name)
            
            return matches
        except Exception as e:
            logger.error(f"Face recognition error: {e}")
            return []

    async def _detect_anomalies(self, frame: np.ndarray) -> float:
        """Detect anomalies in video frame"""
        try:
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            resized_frame = cv2.resize(gray_frame, (64, 64))
            features = resized_frame.flatten() / 255.0
            
            # Simulate anomaly score (in production, use trained model)
            anomaly_score = float(self.anomaly_detector.fit_predict([features])[0])
            return max(0.0, min(1.0, anomaly_score))
        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
            return 0.0

    async def _analyze_behavior(self, frame: np.ndarray, objects: List[str]) -> float:
        """Analyze behavior for threat assessment"""
        threat_indicators = 0
        
        suspicious_objects = {'knife', 'gun', 'mask', 'crowbar'}
        if any(obj in suspicious_objects for obj in objects):
            threat_indicators += 1
        
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 22:
            threat_indicators += 0.5
        
        if 'person' in objects and objects.count('person') > 3:
            threat_indicators += 0.5
        
        return min(threat_indicators / 3, 1.0)

    def _generate_recommendation(self, threat_level: float, objects: List[str], anomaly_score: float) -> str:
        """Generate security recommendations based on analysis"""
        if threat_level > 0.8 or anomaly_score > 0.8:
            return "IMMEDIATE_ALERT: Notify security personnel"
        elif threat_level > 0.6:
            return "HIGH_RISK: Monitor closely and prepare alert"
        elif threat_level > 0.4:
            return "MEDIUM_RISK: Increase surveillance frequency"
        else:
            return "LOW_RISK: Normal monitoring"

    async def register_face(self, name: str, image_data: np.ndarray):
        """Register a new face in the database"""
        try:
            face_encodings = face_recognition.face_encodings(image_data)
            if face_encodings:
                self.face_database[name] = face_encodings[0].tolist()
                logger.info(f"Face registered for {name}")
                return True
            logger.warning(f"No face detected for {name}")
            return False
        except Exception as e:
            logger.error(f"Face registration error: {e}")
            return False

# ===== BLOCKCHAIN AUDIT SERVICE =====
class BlockchainAuditService:
    """Blockchain-based audit trail for security events"""
    
    def __init__(self):
        # Replace with actual blockchain provider in production
        self.w3 = Web3(Web3.HTTPProvider('https://rinkeby.infura.io/v3/YOUR_PROJECT_ID'))
        logger.info("Blockchain Audit Service initialized")

    async def log_security_event(self, event_data: Dict) -> BlockchainAudit:
        """Log security event to blockchain"""
        try:
            event_hash = hashlib.sha256(
                json.dumps(event_data, sort_keys=True, default=str).encode()
            ).hexdigest()
            
            # Simulate blockchain transaction
            tx_hash = f"0x{hashlib.sha256(event_hash.encode()).hexdigest()[:40]}"
            block_number = 15432108 + np.random.randint(1, 1000)
            
            return BlockchainAudit(
                event_id=event_data.get('id', str(uuid.uuid4())),
                transaction_hash=tx_hash,
                block_number=block_number,
                timestamp=datetime.utcnow(),
                verified=True
            )
        except Exception as e:
            logger.error(f"Blockchain logging error: {e}")
            raise HTTPException(status_code=500, detail="Failed to log to blockchain")

# ===== IOT DEVICE MANAGEMENT =====
class IoTDeviceManager:
    """Manage IoT security devices"""
    
    def __init__(self):
        self.connected_devices = {}
        self.device_status = {}
        logger.info("IoT Device Manager initialized")

    async def register_device(self, device_id: str, device_type: str, capabilities: List[str]):
        """Register a new IoT device"""
        try:
            self.connected_devices[device_id] = {
                'type': device_type,
                'capabilities': capabilities,
                'last_heartbeat': datetime.utcnow(),
                'status': 'online'
            }
            logger.info(f"Device registered: {device_id}")
        except Exception as e:
            logger.error(f"Device registration error: {e}")
            raise HTTPException(status_code=500, detail="Failed to register device")

    async def send_device_command(self, device_id: str, command: str, payload: Dict = None):
        """Send command to IoT device"""
        try:
            if device_id in self.connected_devices:
                logger.info(f"Command sent to {device_id}: {command} - {payload}")
                return True
            logger.warning(f"Device not found: {device_id}")
            return False
        except Exception as e:
            logger.error(f"Device command error: {e}")
            return False

    async def check_device_health(self):
        """Check health of all connected devices"""
        try:
            current_time = datetime.utcnow()
            offline_devices = []
            
            for device_id, device_info in self.connected_devices.items():
                time_diff = current_time - device_info['last_heartbeat']
                if time_diff.total_seconds() > 300:
                    device_info['status'] = 'offline'
                    offline_devices.append(device_id)
            
            return offline_devices
        except Exception as e:
            logger.error(f"Device health check error: {e}")
            return []

# ===== REAL-TIME NOTIFICATION SERVICE =====
class RealTimeSecurityService:
    """Real-time security monitoring and notifications"""
    
    def __init__(self):
        self.connected_clients = {}
        self.alert_rules = self._setup_alert_rules()
        logger.info("Real-time Security Service initialized")

    def _setup_alert_rules(self):
        """Setup AI-powered alert rules"""
        return {
            'motion_after_hours': {'enabled': True, 'severity': 'high'},
            'multiple_unknown_faces': {'enabled': True, 'severity': 'medium'},
            'suspicious_objects': {'enabled': True, 'severity': 'critical'},
            'door_forced': {'enabled': True, 'severity': 'critical'},
            'camera_offline': {'enabled': True, 'severity': 'medium'}
        }

    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect WebSocket client"""
        try:
            await websocket.accept()
            self.connected_clients[client_id] = websocket
            logger.info(f"Client connected: {client_id}")
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")

    def disconnect(self, client_id: str):
        """Disconnect WebSocket client"""
        self.connected_clients.pop(client_id, None)
        logger.info(f"Client disconnected: {client_id}")

    async def send_alert(self, alert: SecurityAlert):
        """Send security alert to all connected clients"""
        try:
            disconnected = []
            for client_id, websocket in self.connected_clients.items():
                try:
                    await websocket.send_text(json.dumps({
                        'type': 'security_alert',
                        'alert': alert.dict(),
                        'timestamp': datetime.utcnow().isoformat()
                    }, default=str))
                except Exception as e:
                    logger.error(f"Failed to send alert to {client_id}: {e}")
                    disconnected.append(client_id)
            
            for client_id in disconnected:
                self.disconnect(client_id)
        except Exception as e:
            logger.error(f"Alert sending error: {e}")

    async def evaluate_alert_rules(self, event_data: Dict):
        """Evaluate event against alert rules"""
        try:
            triggered_rules = []
            
            if (event_data.get('event_type') == 'motion' and 
                self.alert_rules['motion_after_hours']['enabled']):
                current_hour = datetime.now().hour
                if current_hour < 6 or current_hour > 22:
                    triggered_rules.append('motion_after_hours')
            
            if (event_data.get('ai_analysis', {}).get('facial_matches') and 
                len(event_data['ai_analysis']['facial_matches']) == 0 and
                self.alert_rules['multiple_unknown_faces']['enabled']):
                triggered_rules.append('multiple_unknown_faces')
            
            return triggered_rules
        except Exception as e:
            logger.error(f"Alert rule evaluation error: {e}")
            return []

# ===== MAIN APPLICATION =====
app = FastAPI(title="Mwarokin Security Management API", version="2.1.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
ai_security = AISecurityMonitor()
blockchain_audit = BlockchainAuditService()
iot_manager = IoTDeviceManager()
real_time_service = RealTimeSecurityService()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await _initialize_sample_data()
        logger.info("Application startup completed")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise

async def _initialize_sample_data():
    """Initialize sample security data"""
    try:
        async with AsyncSessionLocal() as session:
            # Register sample cameras
            sample_cameras = [
                {"id": "front-gate", "name": "Front Gate", "location": "villa_a", "stream_url": "rtsp://front_gate", "ai_capabilities": ["face_recognition", "object_detection"], "home_id": "villa_a"},
                {"id": "back-yard", "name": "Back Yard", "location": "villa_a", "stream_url": "rtsp://back_yard", "ai_capabilities": ["object_detection"], "home_id": "villa_a"},
                {"id": "parking", "name": "Parking", "location": "villa_a", "stream_url": "rtsp://parking", "ai_capabilities": ["object_detection"], "home_id": "villa_a"},
                {"id": "main-door", "name": "Main Door", "location": "villa_a", "stream_url": "rtsp://main_door", "ai_capabilities": ["face_recognition"], "home_id": "villa_a"},
            ]
            
            for cam_data in sample_cameras:
                existing = await session.execute(select(Camera).filter_by(id=cam_data["id"]))
                if not existing.scalars().first():
                    camera = Camera(**cam_data)
                    session.add(camera)
            
            # Register sample visitors
            sample_visitors = [
                {"id": str(uuid.uuid4()), "name": "John Delivery", "purpose": "Package Delivery", "status": "approved", "arrival_time": datetime.utcnow() - timedelta(hours=2), "home_id": "villa_a"},
                {"id": str(uuid.uuid4()), "name": "Sarah Maintenance", "purpose": "Plumbing Work", "status": "approved", "arrival_time": datetime.utcnow() - timedelta(hours=3), "home_id": "villa_a"},
                {"id": str(uuid.uuid4()), "name": "Mike Guest", "purpose": "Personal Visit", "status": "approved", "arrival_time": datetime.utcnow() - timedelta(hours=5), "home_id": "villa_a"},
            ]
            
            for vis_data in sample_visitors:
                existing = await session.execute(select(Visitor).filter_by(id=vis_data["id"]))
                if not existing.scalars().first():
                    visitor = Visitor(**vis_data)
                    session.add(visitor)
            
            await session.commit()
            logger.info("Sample data initialized")
    except Exception as e:
        logger.error(f"Sample data initialization error: {e}")
        raise

@app.websocket("/ws/security/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time security updates"""
    try:
        await real_time_service.connect(websocket, client_id)
        while True:
            data = await websocket.receive_text()
            await _handle_security_message(json.loads(data), client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        real_time_service.disconnect(client_id)

async def _handle_security_message(message: Dict, client_id: str):
    """Handle incoming security messages"""
    try:
        message_type = message.get('type')
        
        if message_type == 'camera_control':
            await _handle_camera_control(message, client_id)
        elif message_type == 'security_command':
            await _handle_security_command(message, client_id)
        elif message_type == 'visitor_approval':
            await _handle_visitor_approval(message, client_id)
    except Exception as e:
        logger.error(f"Security message handling error: {e}")

async def _handle_camera_control(message: Dict, client_id: str):
    """Handle camera control commands"""
    try:
        camera_id = message.get('camera_id')
        action = message.get('action')
        
        if action == "view_feed":
            # Simulate streaming URL response
            async with AsyncSessionLocal() as session:
                camera = (await session.execute(select(Camera).filter_by(id=camera_id))).scalars().first()
                if camera:
                    await real_time_service.send_alert(SecurityAlert(
                        type="camera_access",
                        location=camera.location,
                        severity="low",
                        description=f"Camera feed accessed: {camera.name}",
                        timestamp=datetime.utcnow(),
                        camera_id=camera_id
                    ))
    except Exception as e:
        logger.error(f"Camera control error: {e}")

async def _handle_security_command(message: Dict, client_id: str):
    """Handle security commands"""
    try:
        command = message.get('command')
        if command == "lock_all_doors":
            success = await iot_manager.send_device_command("doors_001", "lock_all")
            if success:
                await real_time_service.send_alert(SecurityAlert(
                    type="security_action",
                    location="all",
                    severity="medium",
                    description="All doors locked",
                    timestamp=datetime.utcnow()
                ))
    except Exception as e:
        logger.error(f"Security command error: {e}")

async def _handle_visitor_approval(message: Dict, client_id: str):
    """Handle visitor approval"""
    try:
        visitor_id = message.get('visitor_id')
        status = message.get('status')
        
        async with AsyncSessionLocal() as session:
            visitor = (await session.execute(select(Visitor).filter_by(id=visitor_id))).scalars().first()
            if visitor:
                visitor.status = status
                await session.commit()
                await real_time_service.send_alert(SecurityAlert(
                    type="visitor_update",
                    location=visitor.home_id,
                    severity="low",
                    description=f"Visitor {visitor.name} status updated to {status}",
                    timestamp=datetime.utcnow()
                ))
    except Exception as e:
        logger.error(f"Visitor approval error: {e}")

@app.post("/api/security/analyze-frame")
async def analyze_security_frame(file: UploadFile = File(...), camera_id: str = "unknown", home_id: str = "all", db: AsyncSession = Depends(get_db)):
    """Analyze security camera frame with AI"""
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        analysis = await ai_security.analyze_video_frame(frame, camera_id, home_id)
        
        event_data = {
            'id': str(uuid.uuid4()),
            'event_type': 'ai_analysis',
            'location': home_id,
            'camera_id': camera_id,
            'description': f'AI analysis: {analysis.detected_objects}',
            'ai_analysis': analysis.dict(),
            'severity': 'high' if analysis.threat_level > 0.7 else 'medium',
            'home_id': home_id
        }
        
        audit = await blockchain_audit.log_security_event(event_data)
        
        event = SecurityEvent(**event_data, blockchain_hash=audit.transaction_hash)
        db.add(event)
        await db.commit()
        
        triggered_rules = await real_time_service.evaluate_alert_rules(event_data)
        if triggered_rules:
            alert = SecurityAlert(
                type="ai_analysis_alert",
                location=home_id,
                severity=event_data['severity'],
                description=f"AI detected potential threat: {analysis.detected_objects}",
                timestamp=datetime.utcnow(),
                camera_id=camera_id,
                home_id=home_id
            )
            await real_time_service.send_alert(alert)
        
        return {
            "analysis": analysis.dict(),
            "blockchain_audit": audit.dict(),
            "triggered_alerts": triggered_rules
        }
    except Exception as e:
        logger.error(f"Frame analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/api/security/visitors")
async def register_visitor(visitor_request: VisitorRequest, db: AsyncSession = Depends(get_db)):
    """Register a new visitor with facial recognition"""
    try:
        visitor = Visitor(
            id=str(uuid.uuid4()),
            name=visitor_request.name,
            purpose=visitor_request.purpose,
            status="pending",
            arrival_time=visitor_request.expected_arrival,
            departure_time=visitor_request.expected_arrival + timedelta(hours=visitor_request.duration),
            access_level=visitor_request.access_level,
            home_id=visitor_request.home_id
        )
        
        if visitor_request.face_image:
            image_data = base64.b64decode(visitor_request.face_image)
            nparr = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            success = await ai_security.register_face(visitor_request.name, frame)
            if success:
                visitor.status = "pre_approved"
        
        db.add(visitor)
        await db.commit()
        
        await real_time_service.send_alert(SecurityAlert(
            type="new_visitor",
            location=visitor_request.home_id,
            severity="low",
            description=f"New visitor registered: {visitor_request.name}",
            timestamp=datetime.utcnow(),
            home_id=visitor_request.home_id
        ))
        
        return {"visitor_id": visitor.id, "status": visitor.status}
    except Exception as e:
        logger.error(f"Visitor registration error: {e}")
        raise HTTPException(status_code=500, detail=f"Visitor registration failed: {str(e)}")

@app.get("/api/security/events")
async def get_security_events(hours: int = 24, severity: str = None, home_id: str = "all", db: AsyncSession = Depends(get_db)):
    """Get security events with filtering"""
    try:
        query = select(SecurityEvent).filter(
            SecurityEvent.timestamp >= datetime.utcnow() - timedelta(hours=hours),
            SecurityEvent.home_id == home_id
        )
        if severity:
            query = query.filter(SecurityEvent.severity == severity)
        
        events = (await db.execute(query)).scalars().all()
        
        return {
            "events": [
                {
                    "id": event.id,
                    "event_type": event.event_type,
                    "location": event.location,
                    "description": event.description,
                    "timestamp": event.timestamp,
                    "severity": event.severity,
                    "home_id": event.home_id
                } for event in events
            ]
        }
    except Exception as e:
        logger.error(f"Event retrieval error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve events: {str(e)}")

@app.get("/api/security/visitors")
async def get_visitors(home_id: str = "all", db: AsyncSession = Depends(get_db)):
    """Get current visitors"""
    try:
        query = select(Visitor).filter(
            Visitor.status.in_(["pending", "approved", "active"]),
            Visitor.home_id == home_id
        )
        visitors = (await db.execute(query)).scalars().all()
        
        return {
            "visitors": [
                {
                    "id": visitor.id,
                    "name": visitor.name,
                    "purpose": visitor.purpose,
                    "status": visitor.status,
                    "arrival_time": visitor.arrival_time,
                    "home_id": visitor.home_id
                } for visitor in visitors
            ],
            "count": len(visitors)
        }
    except Exception as e:
        logger.error(f"Visitor retrieval error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve visitors: {str(e)}")

@app.post("/api/security/control")
async def security_control(command: str, payload: Dict = None, db: AsyncSession = Depends(get_db)):
    """Execute security control commands"""
    try:
        valid_commands = {
            "arm_system": lambda: iot_manager.send_device_command("alarm_001", "arm"),
            "disarm_system": lambda: iot_manager.send_device_command("alarm_001", "disarm"),
            "lock_all_doors": lambda: iot_manager.send_device_command("doors_001", "lock_all"),
            "emergency_alert": lambda: real_time_service.send_alert(SecurityAlert(
                type="emergency",
                location=payload.get("home_id", "all") if payload else "all",
                severity="critical",
                description="Emergency alert activated",
                timestamp=datetime.utcnow(),
                home_id=payload.get("home_id", "all") if payload else "all"
            ))
        }
        
        if command in valid_commands:
            success = await valid_commands[command]()
            if success:
                event = SecurityEvent(
                    id=str(uuid.uuid4()),
                    event_type=command,
                    location=payload.get("home_id", "all") if payload else "all",
                    description=f"Security command executed: {command}",
                    severity="medium",
                    home_id=payload.get("home_id", "all") if payload else "all"
                )
                db.add(event)
                await db.commit()
            return {"success": success, "command": command}
        else:
            raise HTTPException(status_code=400, detail="Invalid command")
    except Exception as e:
        logger.error(f"Security control error: {e}")
        raise HTTPException(status_code=500, detail=f"Control command failed: {str(e)}")

@app.get("/api/security/cameras")
async def get_cameras(home_id: str = "all", db: AsyncSession = Depends(get_db)):
    """Get camera status and feeds"""
    try:
        query = select(Camera).filter(Camera.home_id == home_id)
        cameras = (await db.execute(query)).scalars().all()
        
        return {
            "cameras": [
                {
                    "id": cam.id,
                    "name": cam.name,
                    "status": cam.status,
                    "stream_url": cam.stream_url,
                    "home_id": cam.home_id
                } for cam in cameras
            ],
            "active_count": len([cam for cam in cameras if cam.status == "active"])
        }
    except Exception as e:
        logger.error(f"Camera retrieval error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cameras: {str(e)}")

@app.get("/api/security/analytics/dashboard")
async def get_security_analytics(home_id: str = "all", db: AsyncSession = Depends(get_db)):
    """Get security analytics for dashboard"""
    try:
        # Camera stats
        camera_query = select(func.count()).filter(Camera.status == "active", Camera.home_id == home_id)
        camera_count = (await db.execute(camera_query)).scalar()
        
        # Event stats
        event_query = select(func.count()).filter(
            SecurityEvent.timestamp >= datetime.utcnow() - timedelta(hours=24),
            SecurityEvent.home_id == home_id
        )
        event_count = (await db.execute(event_query)).scalar()
        
        # Active sensors and guards (simulated)
        sensor_count = 8  # In production, query from IoT manager
        guard_count = 3   # In production, query from guard management system
        
        analytics = {
            "total_cameras": camera_count,
            "active_sensors": sensor_count,
            "security_guards": guard_count,
            "today_events": event_count,
            "threat_level": "low" if event_count < 10 else "medium",
            "system_status": "operational",
            "recent_alerts": [
                {
                    "type": "motion",
                    "location": "back_yard",
                    "time": "2 min ago",
                    "severity": "low",
                    "home_id": home_id
                },
                {
                    "type": "access",
                    "location": "front_gate",
                    "time": "15 min ago",
                    "severity": "low",
                    "home_id": home_id
                }
            ],
            "ai_insights": {
                "suspicious_activity_trend": "decreasing",
                "peak_security_hours": "18:00-22:00",
                "common_anomalies": ["night_motion", "multiple_visitors"]
            }
        }
        
        return analytics
    except Exception as e:
        logger.error(f"Analytics retrieval error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve analytics: {str(e)}")

@app.get("/api/security/ai/predictive-threats")
async def get_predictive_threats(home_id: str = "all", db: AsyncSession = Depends(get_db)):
    """Get AI-predicted security threats"""
    try:
        # Simulate predictive analytics (in production, use trained ML model)
        predictions = {
            "high_risk_periods": [
                {"day": "Friday", "time": "20:00-23:00", "risk_level": 0.75},
                {"day": "Saturday", "time": "14:00-18:00", "risk_level": 0.65}
            ],
            "vulnerability_assessment": {
                "front_gate": 0.3,
                "back_yard": 0.6,
                "parking": 0.4,
                "main_door": 0.2
            },
            "recommended_actions": [
                "Increase patrols during Friday evenings",
                "Install additional lighting in back yard",
                "Review access logs for parking area"
            ]
        }
        
        return predictions
    except Exception as e:
        logger.error(f"Predictive threats error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve predictive threats: {str(e)}")

@app.post("/api/security/iot/register")
async def register_iot_device(device_data: Dict, db: AsyncSession = Depends(get_db)):
    """Register a new IoT security device"""
    try:
        await iot_manager.register_device(
            device_data['device_id'],
            device_data['device_type'],
            device_data.get('capabilities', [])
        )
        
        return {"status": "registered", "device_id": device_data['device_id']}
    except Exception as e:
        logger.error(f"IoT device registration error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register IoT device: {str(e)}")

# Simulate real-time updates
async def simulate_real_time_updates():
    """Simulate real-time security updates"""
    try:
        while True:
            if np.random.random() > 0.7:
                async with AsyncSessionLocal() as session:
                    random_events = [
                        {
                            "event_type": "motion",
                            "location": "front_yard",
                            "description": "Motion detected at front yard",
                            "severity": "medium",
                            "home_id": "villa_a"
                        },
                        {
                            "event_type": "vehicle",
                            "location": "parking",
                            "description": "Vehicle detected in parking area",
                            "severity": "low",
                            "home_id": "villa_a"
                        }
                    ]
                    
                    event_data = random_events[np.random.randint(0, len(random_events))]
                    event_data['id'] = str(uuid.uuid4())
                    event_data['timestamp'] = datetime.utcnow()
                    
                    audit = await blockchain_audit.log_security_event(event_data)
                    event = SecurityEvent(**event_data, blockchain_hash=audit.transaction_hash)
                    session.add(event)
                    await session.commit()
                    
                    await real_time_service.send_alert(SecurityAlert(
                        type=event_data['event_type'],
                        location=event_data['location'],
                        severity=event_data['severity'],
                        description=event_data['description'],
                        timestamp=event_data['timestamp'],
                        home_id=event_data['home_id']
                    ))
            
            await asyncio.sleep(10)
    except Exception as e:
        logger.error(f"Real-time update simulation error: {e}")

@app.on_event("startup")
async def start_background_tasks():
    """Start background tasks"""
    asyncio.create_task(simulate_real_time_updates())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)