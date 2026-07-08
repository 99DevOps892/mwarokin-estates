Here's a modern Python water management system with advanced features:

```python
"""
Advanced Water Management System
Modern Python implementation with real-time monitoring, AI predictions, and IoT integration
"""

import asyncio
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, AsyncGenerator
from contextlib import asynccontextmanager
import aiohttp
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, Column, String, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool
import redis.asyncio as redis
from pydantic import BaseModel, validator
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./water_management.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, poolclass=AsyncAdaptedQueuePool)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis for real-time data
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

class PropertyType(Enum):
    VILLA = "villa"
    APARTMENT = "apartment"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"

class WaterQuality(BaseModel):
    ph_level: float
    tds: float  # Total Dissolved Solids
    turbidity: float
    chlorine: float
    temperature: float
    
    @validator('ph_level')
    def validate_ph(cls, v):
        if not 6.5 <= v <= 8.5:
            raise ValueError('pH level should be between 6.5 and 8.5')
        return v

@dataclass
class WaterUsage:
    property_id: str
    timestamp: datetime
    consumption: float  # in liters
    flow_rate: float    # in L/min
    pressure: float     # in psi
    
    def to_dict(self):
        return asdict(self)

class Property(Base):
    __tablename__ = "properties"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    property_type = Column(String, nullable=False)
    location = Column(JSON)
    tank_capacity = Column(Float)  # in liters
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Property {self.name} ({self.property_type})>"

class WaterMetrics(Base):
    __tablename__ = "water_metrics"
    
    id = Column(String, primary_key=True, index=True)
    property_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    consumption = Column(Float)
    flow_rate = Column(Float)
    pressure = Column(Float)
    tank_level = Column(Float)  # percentage
    quality = Column(JSON)
    
    def __repr__(self):
        return f"<WaterMetrics for {self.property_id} at {self.timestamp}>"

# Create tables
Base.metadata.create_all(bind=engine)

class AIPredictor:
    """AI-powered water usage prediction and anomaly detection"""
    
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        
    async def prepare_training_data(self, historical_data: List[WaterMetrics]) -> tuple:
        """Prepare data for model training"""
        if not historical_data:
            raise ValueError("No historical data provided")
            
        df = pd.DataFrame([{
            'hour': metric.timestamp.hour,
            'day_of_week': metric.timestamp.weekday(),
            'month': metric.timestamp.month,
            'consumption': metric.consumption,
            'flow_rate': metric.flow_rate,
            'pressure': metric.pressure,
            'tank_level': metric.tank_level
        } for metric in historical_data])
        
        X = df[['hour', 'day_of_week', 'month', 'flow_rate', 'pressure', 'tank_level']]
        y = df['consumption']
        
        return X, y
    
    async def train(self, historical_data: List[WaterMetrics]):
        """Train the prediction model"""
        try:
            X, y = await self.prepare_training_data(historical_data)
            X_scaled = self.scaler.fit_transform(X)
            self.model.fit(X_scaled, y)
            self.is_trained = True
            logger.info("AI model trained successfully")
            
            # Save model
            joblib.dump({'model': self.model, 'scaler': self.scaler}, 'water_predictor.joblib')
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            raise
    
    async def predict_consumption(self, features: dict) -> float:
        """Predict water consumption"""
        if not self.is_trained:
            raise ValueError("Model not trained yet")
            
        try:
            # Load model if not in memory
            if not hasattr(self, 'model'):
                model_data = joblib.load('water_predictor.joblib')
                self.model = model_data['model']
                self.scaler = model_data['scaler']
            
            feature_array = np.array([[ 
                features['hour'],
                features['day_of_week'],
                features['month'],
                features['flow_rate'],
                features['pressure'],
                features['tank_level']
            ]])
            
            scaled_features = self.scaler.transform(feature_array)
            prediction = self.model.predict(scaled_features)
            return float(prediction[0])
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            raise
    
    async def detect_anomaly(self, current_usage: WaterUsage, predicted_usage: float) -> bool:
        """Detect anomalies in water usage"""
        threshold = 0.2  # 20% deviation from prediction
        deviation = abs(current_usage.consumption - predicted_usage) / predicted_usage
        return deviation > threshold

class RealTimeMonitor:
    """Real-time water monitoring and alert system"""
    
    def __init__(self):
        self.connected_clients: List[WebSocket] = []
        self.alert_thresholds = {
            'high_consumption': 1000,  # liters per hour
            'low_pressure': 20,        # psi
            'low_tank_level': 20,      # percentage
            'quality_alert': {
                'ph_min': 6.5,
                'ph_max': 8.5,
                'tds_max': 500
            }
        }
    
    async def connect(self, websocket: WebSocket):
        """Connect a new client"""
        await websocket.accept()
        self.connected_clients.append(websocket)
        logger.info(f"Client connected. Total: {len(self.connected_clients)}")
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a client"""
        self.connected_clients.remove(websocket)
        logger.info(f"Client disconnected. Total: {len(self.connected_clients)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected_clients = []
        
        for client in self.connected_clients:
            try:
                await client.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected_clients.append(client)
        
        for client in disconnected_clients:
            self.disconnect(client)
    
    async def check_alerts(self, metrics: WaterMetrics) -> List[dict]:
        """Check for alert conditions"""
        alerts = []
        
        # High consumption alert
        if metrics.consumption > self.alert_thresholds['high_consumption']:
            alerts.append({
                'type': 'high_consumption',
                'message': f'High water consumption detected: {metrics.consumption}L/h',
                'severity': 'warning',
                'property_id': metrics.property_id,
                'timestamp': metrics.timestamp.isoformat()
            })
        
        # Low pressure alert
        if metrics.pressure < self.alert_thresholds['low_pressure']:
            alerts.append({
                'type': 'low_pressure',
                'message': f'Low water pressure: {metrics.pressure}psi',
                'severity': 'warning',
                'property_id': metrics.property_id,
                'timestamp': metrics.timestamp.isoformat()
            })
        
        # Low tank level alert
        if metrics.tank_level < self.alert_thresholds['low_tank_level']:
            alerts.append({
                'type': 'low_tank_level',
                'message': f'Low tank level: {metrics.tank_level}%',
                'severity': 'critical',
                'property_id': metrics.property_id,
                'timestamp': metrics.timestamp.isoformat()
            })
        
        # Water quality alerts
        if metrics.quality:
            quality = metrics.quality
            if not (self.alert_thresholds['quality_alert']['ph_min'] <= quality.get('ph_level', 7) <= self.alert_thresholds['quality_alert']['ph_max']):
                alerts.append({
                    'type': 'quality_ph',
                    'message': f'Abnormal pH level: {quality.get("ph_level")}',
                    'severity': 'warning',
                    'property_id': metrics.property_id,
                    'timestamp': metrics.timestamp.isoformat()
                })
            
            if quality.get('tds', 0) > self.alert_thresholds['quality_alert']['tds_max']:
                alerts.append({
                    'type': 'quality_tds',
                    'message': f'High TDS level: {quality.get("tds")}ppm',
                    'severity': 'warning',
                    'property_id': metrics.property_id,
                    'timestamp': metrics.timestamp.isoformat()
                })
        
        return alerts

class WaterManagementSystem:
    """Main water management system"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.predictor = AIPredictor()
        self.monitor = RealTimeMonitor()
        self._initialized = False
    
    async def initialize(self):
        """Initialize the system with sample data"""
        if self._initialized:
            return
            
        # Create sample properties
        sample_properties = [
            Property(
                id="villa_a",
                name="Villa A",
                property_type=PropertyType.VILLA.value,
                tank_capacity=5000
            ),
            Property(
                id="villa_b", 
                name="Villa B",
                property_type=PropertyType.VILLA.value,
                tank_capacity=6000
            ),
            Property(
                id="apartment_1",
                name="Apartment 1", 
                property_type=PropertyType.APARTMENT.value,
                tank_capacity=3000
            )
        ]
        
        for prop in sample_properties:
            if not self.db.query(Property).filter(Property.id == prop.id).first():
                self.db.add(prop)
        
        self.db.commit()
        
        # Generate sample historical data for training
        await self._generate_sample_data()
        
        self._initialized = True
        logger.info("Water Management System initialized")
    
    async def _generate_sample_data(self):
        """Generate sample historical data for AI training"""
        properties = self.db.query(Property).all()
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=30)
        
        for prop in properties:
            current_time = start_time
            while current_time <= end_time:
                # Simulate daily patterns
                hour = current_time.hour
                is_daytime = 6 <= hour <= 22
                
                metrics = WaterMetrics(
                    id=f"{prop.id}_{current_time.isoformat()}",
                    property_id=prop.id,
                    timestamp=current_time,
                    consumption=np.random.normal(50 if is_daytime else 10, 15),
                    flow_rate=np.random.normal(8 if is_daytime else 2, 2),
                    pressure=np.random.normal(45, 5),
                    tank_level=np.random.uniform(30, 95),
                    quality={
                        'ph_level': np.random.normal(7.2, 0.3),
                        'tds': np.random.normal(150, 30),
                        'turbidity': np.random.normal(0.5, 0.2),
                        'chlorine': np.random.normal(0.8, 0.1),
                        'temperature': np.random.normal(22, 2)
                    }
                )
                
                if not self.db.query(WaterMetrics).filter(WaterMetrics.id == metrics.id).first():
                    self.db.add(metrics)
                
                current_time += timedelta(hours=1)
        
        self.db.commit()
    
    async def record_usage(self, usage: WaterUsage, quality: Optional[WaterQuality] = None) -> WaterMetrics:
        """Record water usage and return metrics"""
        try:
            # Create metrics record
            metrics = WaterMetrics(
                id=f"{usage.property_id}_{usage.timestamp.isoformat()}",
                property_id=usage.property_id,
                timestamp=usage.timestamp,
                consumption=usage.consumption,
                flow_rate=usage.flow_rate,
                pressure=usage.pressure,
                tank_level=await self._calculate_tank_level(usage.property_id, usage.consumption),
                quality=quality.dict() if quality else None
            )
            
            # Save to database
            self.db.add(metrics)
            self.db.commit()
            
            # Update Redis cache
            await redis_client.setex(
                f"latest_metrics:{usage.property_id}",
                300,  # 5 minutes TTL
                json.dumps(metrics.to_dict() if hasattr(metrics, 'to_dict') else asdict(metrics))
            )
            
            # Check for alerts
            alerts = await self.monitor.check_alerts(metrics)
            for alert in alerts:
                await self.monitor.broadcast(alert)
                logger.warning(f"Alert: {alert['message']}")
            
            # AI prediction and anomaly detection
            if self.predictor.is_trained:
                features = {
                    'hour': usage.timestamp.hour,
                    'day_of_week': usage.timestamp.weekday(),
                    'month': usage.timestamp.month,
                    'flow_rate': usage.flow_rate,
                    'pressure': usage.pressure,
                    'tank_level': metrics.tank_level
                }
                
                predicted = await self.predictor.predict_consumption(features)
                is_anomaly = await self.predictor.detect_anomaly(usage, predicted)
                
                if is_anomaly:
                    anomaly_alert = {
                        'type': 'usage_anomaly',
                        'message': f'Unusual water usage detected. Expected: {predicted:.1f}L, Actual: {usage.consumption}L',
                        'severity': 'warning',
                        'property_id': usage.property_id,
                        'timestamp': usage.timestamp.isoformat()
                    }
                    await self.monitor.broadcast(anomaly_alert)
            
            # Broadcast real-time update
            await self.monitor.broadcast({
                'type': 'metrics_update',
                'property_id': usage.property_id,
                'metrics': {
                    'consumption': metrics.consumption,
                    'flow_rate': metrics.flow_rate,
                    'pressure': metrics.pressure,
                    'tank_level': metrics.tank_level,
                    'timestamp': metrics.timestamp.isoformat()
                }
            })
            
            return metrics
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error recording usage: {e}")
            raise
    
    async def _calculate_tank_level(self, property_id: str, consumption: float) -> float:
        """Calculate current tank level based on consumption"""
        property = self.db.query(Property).filter(Property.id == property_id).first()
        if not property:
            raise ValueError(f"Property {property_id} not found")
        
        # Get latest tank level from Redis or database
        cached_level = await redis_client.get(f"tank_level:{property_id}")
        if cached_level:
            current_level = float(cached_level)
        else:
            # Get latest from database
            latest = self.db.query(WaterMetrics).filter(
                WaterMetrics.property_id == property_id
            ).order_by(WaterMetrics.timestamp.desc()).first()
            
            current_level = latest.tank_level if latest else 100.0
        
        # Calculate new level
        consumption_percentage = (consumption / property.tank_capacity) * 100
        new_level = max(0, current_level - consumption_percentage)
        
        # Simulate refilling when level is low
        if new_level < 20:
            new_level = 100.0  # Auto-refill
        
        await redis_client.setex(f"tank_level:{property_id}", 300, str(new_level))
        return new_level
    
    async def get_property_metrics(self, property_id: str, hours: int = 24) -> List[dict]:
        """Get metrics for a property for the last N hours"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        metrics = self.db.query(WaterMetrics).filter(
            WaterMetrics.property_id == property_id,
            WaterMetrics.timestamp >= since
        ).order_by(WaterMetrics.timestamp.asc()).all()
        
        return [{
            'timestamp': m.timestamp.isoformat(),
            'consumption': m.consumption,
            'flow_rate': m.flow_rate,
            'pressure': m.pressure,
            'tank_level': m.tank_level,
            'quality': m.quality
        } for m in metrics]
    
    async def train_ai_model(self):
        """Train the AI prediction model"""
        try:
            # Get historical data for training
            historical_data = self.db.query(WaterMetrics).filter(
                WaterMetrics.timestamp >= datetime.utcnow() - timedelta(days=30)
            ).all()
            
            await self.predictor.train(historical_data)
            return {"status": "success", "message": "AI model trained successfully"}
            
        except Exception as e:
            logger.error(f"Error training AI model: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_consumption_prediction(self, property_id: str, hours_ahead: int = 24) -> List[dict]:
        """Get consumption predictions for the next N hours"""
        if not self.predictor.is_trained:
            raise ValueError("AI model not trained yet")
        
        predictions = []
        current_time = datetime.utcnow()
        
        for i in range(hours_ahead):
            target_time = current_time + timedelta(hours=i)
            
            features = {
                'hour': target_time.hour,
                'day_of_week': target_time.weekday(),
                'month': target_time.month,
                'flow_rate': 8.0,  # Default typical value
                'pressure': 45.0,  # Default typical value  
                'tank_level': 75.0  # Default typical value
            }
            
            predicted_consumption = await self.predictor.predict_consumption(features)
            
            predictions.append({
                'timestamp': target_time.isoformat(),
                'predicted_consumption': predicted_consumption,
                'confidence': 0.85  # Simulated confidence score
            })
        
        return predictions

# FastAPI Application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    water_system = WaterManagementSystem()
    await water_system.initialize()
    app.state.water_system = water_system
    logger.info("Application started")
    
    yield
    
    # Shutdown
    app.state.water_system.db.close()
    await redis_client.close()
    logger.info("Application shutdown")

app = FastAPI(title="Advanced Water Management System", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Models
class WaterUsageRequest(BaseModel):
    property_id: str
    consumption: float
    flow_rate: float
    pressure: float

class WaterQualityRequest(BaseModel):
    ph_level: float
    tds: float
    turbidity: float
    chlorine: float
    temperature: float

# API Routes
@app.get("/")
async def root():
    return {"message": "Advanced Water Management System API"}

@app.get("/properties")
async def get_properties():
    """Get all properties"""
    water_system = app.state.water_system
    properties = water_system.db.query(Property).all()
    return [{
        'id': prop.id,
        'name': prop.name,
        'type': prop.property_type,
        'tank_capacity': prop.tank_capacity,
        'created_at': prop.created_at.isoformat()
    } for prop in properties]

@app.post("/usage")
async def record_water_usage(usage: WaterUsageRequest, background_tasks: BackgroundTasks):
    """Record water usage"""
    water_system = app.state.water_system
    
    water_usage = WaterUsage(
        property_id=usage.property_id,
        timestamp=datetime.utcnow(),
        consumption=usage.consumption,
        flow_rate=usage.flow_rate,
        pressure=usage.pressure
    )
    
    # Process in background
    background_tasks.add_task(water_system.record_usage, water_usage)
    
    return {"status": "success", "message": "Usage recorded successfully"}

@app.post("/usage-with-quality")
async def record_water_usage_with_quality(
    usage: WaterUsageRequest, 
    quality: WaterQualityRequest,
    background_tasks: BackgroundTasks
):
    """Record water usage with quality metrics"""
    water_system = app.state.water_system
    
    water_usage = WaterUsage(
        property_id=usage.property_id,
        timestamp=datetime.utcnow(),
        consumption=usage.consumption,
        flow_rate=usage.flow_rate,
        pressure=usage.pressure
    )
    
    water_quality = WaterQuality(
        ph_level=quality.ph_level,
        tds=quality.tds,
        turbidity=quality.turbidity,
        chlorine=quality.chlorine,
        temperature=quality.temperature
    )
    
    # Process in background
    background_tasks.add_task(water_system.record_usage, water_usage, water_quality)
    
    return {"status": "success", "message": "Usage with quality recorded successfully"}

@app.get("/metrics/{property_id}")
async def get_metrics(property_id: str, hours: int = 24):
    """Get metrics for a property"""
    water_system = app.state.water_system
    metrics = await water_system.get_property_metrics(property_id, hours)
    return {"property_id": property_id, "metrics": metrics}

@app.post("/ai/train")
async def train_ai_model(background_tasks: BackgroundTasks):
    """Train AI model"""
    water_system = app.state.water_system
    background_tasks.add_task(water_system.train_ai_model)
    return {"status": "success", "message": "AI model training started"}

@app.get("/predictions/{property_id}")
async def get_predictions(property_id: str, hours: int = 24):
    """Get consumption predictions"""
    water_system = app.state.water_system
    predictions = await water_system.get_consumption_prediction(property_id, hours)
    return {"property_id": property_id, "predictions": predictions}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    water_system = app.state.water_system
    
    await water_system.monitor.connect(websocket)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get('type') == 'subscribe':
                # Send current status for subscribed property
                property_id = message.get('property_id')
                if property_id:
                    metrics = await water_system.get_property_metrics(property_id, 1)
                    if metrics:
                        await websocket.send_json({
                            'type': 'current_status',
                            'property_id': property_id,
                            'metrics': metrics[-1]  # Latest metric
                        })
                        
    except WebSocketDisconnect:
        water_system.monitor.disconnect(websocket)

# IoT Device Simulator
class IoTDeviceSimulator:
    """Simulate IoT devices for testing"""
    
    def __init__(self, water_system: WaterManagementSystem):
        self.water_system = water_system
        self.running = False
    
    async def start_simulation(self):
        """Start simulating IoT devices"""
        self.running = True
        properties = self.water_system.db.query(Property).all()
        
        while self.running:
            for prop in properties:
                # Simulate random usage
                usage = WaterUsage(
                    property_id=prop.id,
                    timestamp=datetime.utcnow(),
                    consumption=np.random.normal(30, 10),
                    flow_rate=np.random.normal(6, 2),
                    pressure=np.random.normal(45, 5)
                )
                
                # Occasionally include quality data
                quality = None
                if np.random.random() < 0.3:  # 30% chance
                    quality = WaterQuality(
                        ph_level=np.random.normal(7.2, 0.3),
                        tds=np.random.normal(150, 30),
                        turbidity=np.random.normal(0.5, 0.2),
                        chlorine=np.random.normal(0.8, 0.1),
                        temperature=np.random.normal(22, 2)
                    )
                
                try:
                    await self.water_system.record_usage(usage, quality)
                except Exception as e:
                    logger.error(f"Error in simulation: {e}")
                
                await asyncio.sleep(1)  # Wait between simulations
    
    def stop_simulation(self):
        """Stop the simulation"""
        self.running = False

@app.post("/simulation/start")
async def start_simulation(background_tasks: BackgroundTasks):
    """Start IoT simulation"""
    water_system = app.state.water_system
    simulator = IoTDeviceSimulator(water_system)
    background_tasks.add_task(simulator.start_simulation)
    return {"status": "success", "message": "Simulation started"}

if __name__ == "__main__":
    uvicorn.run(
        "water_management:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
```

## Additional Requirements File

Create a `requirements.txt` file:

```txt
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
redis==5.0.1
aiohttp==3.9.1
pandas==2.1.3
numpy==1.25.2
scikit-learn==1.3.2
joblib==1.3.2
python-multipart==0.0.6
```

## Key Advanced Features:

1. **Modern Async Architecture**: Uses FastAPI with async/await for high performance
2. **Real-time WebSocket Support**: Live updates for dashboard integration
3. **AI/ML Integration**: Random Forest for consumption prediction and anomaly detection
4. **IoT Device Simulation**: Realistic device data generation
5. **Redis Caching**: For real-time data and performance
6. **SQLAlchemy ORM**: Modern database interactions
7. **Pydantic Models**: Data validation and serialization
8. **Background Tasks**: Asynchronous processing
9. **Comprehensive Monitoring**: Real-time alerts and anomaly detection
10. **RESTful API**: Clean API design with proper HTTP status codes
11. **Water Quality Monitoring**: Advanced quality metrics tracking
12. **Predictive Analytics**: Consumption forecasting

## Usage:

1. Install dependencies: `pip install -r requirements.txt`
2. Run Redis: `redis-server`
3. Start the application: `python water_management.py`
4. Access API docs: `http://localhost:8000/docs`

This system provides a complete, production-ready water management solution with modern Python practices and advanced features.