I'll create modern Python code with real-time functionality that complements your elderly care HTML page. Here's a comprehensive backend system with real-time features:

## 1. Real-time Monitoring System

```python
# real_time_monitor.py
import asyncio
import websockets
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CareLevel(Enum):
    INDEPENDENT = "independent"
    ASSISTED = "assisted"
    MEMORY = "memory"
    SKILLED = "skilled"

@dataclass
class Resident:
    id: str
    name: str
    age: int
    care_level: CareLevel
    room: str
    emergency_contact: str
    medical_conditions: List[str]
    last_check_in: datetime

class RealTimeElderlyMonitor:
    def __init__(self, db_path: str = "elderly_care.db"):
        self.db_path = db_path
        self.connected_clients = set()
        self.residents: Dict[str, Resident] = {}
        self._init_database()
        self._load_residents()
    
    def _init_database(self):
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS residents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    care_level TEXT NOT NULL,
                    room TEXT NOT NULL,
                    emergency_contact TEXT,
                    medical_conditions TEXT,
                    last_check_in TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS health_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resident_id TEXT,
                    heart_rate INTEGER,
                    blood_pressure TEXT,
                    temperature REAL,
                    oxygen_saturation REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (resident_id) REFERENCES residents (id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resident_id TEXT,
                    alert_type TEXT,
                    severity TEXT,
                    message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (resident_id) REFERENCES residents (id)
                )
            ''')
    
    def _load_residents(self):
        """Load residents from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT * FROM residents')
            for row in cursor.fetchall():
                medical_conditions = json.loads(row[6]) if row[6] else []
                resident = Resident(
                    id=row[0],
                    name=row[1],
                    age=row[2],
                    care_level=CareLevel(row[3]),
                    room=row[4],
                    emergency_contact=row[5],
                    medical_conditions=medical_conditions,
                    last_check_in=datetime.fromisoformat(row[7]) if row[7] else datetime.now()
                )
                self.residents[resident.id] = resident
    
    async def add_health_metric(self, resident_id: str, metrics: Dict):
        """Add health metrics and check for alerts"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO health_metrics 
                (resident_id, heart_rate, blood_pressure, temperature, oxygen_saturation)
                VALUES (?, ?, ?, ?, ?)
            ''', (resident_id, metrics.get('heart_rate'), metrics.get('blood_pressure'),
                 metrics.get('temperature'), metrics.get('oxygen_saturation')))
            
            # Check for critical values
            await self._check_health_alerts(resident_id, metrics)
    
    async def _check_health_alerts(self, resident_id: str, metrics: Dict):
        """Check health metrics for critical values and create alerts"""
        alerts = []
        
        heart_rate = metrics.get('heart_rate')
        if heart_rate and (heart_rate < 50 or heart_rate > 120):
            alerts.append(("ABNORMAL_HEART_RATE", "HIGH", 
                          f"Heart rate critical: {heart_rate}"))
        
        temperature = metrics.get('temperature')
        if temperature and (temperature < 36.0 or temperature > 38.5):
            alerts.append(("ABNORMAL_TEMPERATURE", "MEDIUM",
                          f"Temperature abnormal: {temperature}°C"))
        
        oxygen = metrics.get('oxygen_saturation')
        if oxygen and oxygen < 92:
            alerts.append(("LOW_OXYGEN", "HIGH",
                          f"Oxygen saturation low: {oxygen}%"))
        
        # Add alerts to database and notify clients
        for alert_type, severity, message in alerts:
            await self._create_alert(resident_id, alert_type, severity, message)
    
    async def _create_alert(self, resident_id: str, alert_type: str, 
                           severity: str, message: str):
        """Create alert and notify connected clients"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO alerts (resident_id, alert_type, severity, message)
                VALUES (?, ?, ?, ?)
            ''', (resident_id, alert_type, severity, message))
            alert_id = cursor.lastrowid
        
        # Notify all connected clients
        alert_data = {
            "type": "ALERT",
            "alert_id": alert_id,
            "resident_id": resident_id,
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        await self._broadcast_to_clients(alert_data)
        logger.warning(f"Alert created: {message}")
    
    async def register_client(self, websocket):
        """Register a new WebSocket client"""
        self.connected_clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.connected_clients)}")
        
        # Send current status to new client
        await self._send_initial_data(websocket)
    
    async def unregister_client(self, websocket):
        """Unregister a WebSocket client"""
        self.connected_clients.remove(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.connected_clients)}")
    
    async def _send_initial_data(self, websocket):
        """Send initial data to newly connected client"""
        # Send residents data
        residents_data = {
            "type": "RESIDENTS_DATA",
            "residents": [
                {
                    "id": resident.id,
                    "name": resident.name,
                    "care_level": resident.care_level.value,
                    "room": resident.room,
                    "last_check_in": resident.last_check_in.isoformat()
                }
                for resident in self.residents.values()
            ]
        }
        await websocket.send(json.dumps(residents_data))
        
        # Send recent alerts
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT * FROM alerts 
                WHERE resolved = FALSE 
                ORDER BY timestamp DESC 
                LIMIT 10
            ''')
            alerts = cursor.fetchall()
            
            if alerts:
                alerts_data = {
                    "type": "RECENT_ALERTS",
                    "alerts": [
                        {
                            "id": alert[0],
                            "resident_id": alert[1],
                            "alert_type": alert[2],
                            "severity": alert[3],
                            "message": alert[4],
                            "timestamp": alert[5]
                        }
                        for alert in alerts
                    ]
                }
                await websocket.send(json.dumps(alerts_data))
    
    async def _broadcast_to_clients(self, data: Dict):
        """Broadcast data to all connected clients"""
        if self.connected_clients:
            message = json.dumps(data)
            await asyncio.gather(
                *[client.send(message) for client in self.connected_clients],
                return_exceptions=True
            )
    
    async def handle_health_data(self, data: Dict):
        """Handle incoming health data from IoT devices"""
        resident_id = data.get('resident_id')
        metrics = data.get('metrics', {})
        
        if resident_id in self.residents:
            await self.add_health_metric(resident_id, metrics)
            
            # Broadcast update to clients
            update_data = {
                "type": "HEALTH_UPDATE",
                "resident_id": resident_id,
                "metrics": metrics,
                "timestamp": datetime.now().isoformat()
            }
            await self._broadcast_to_clients(update_data)
    
    async def handle_check_in(self, resident_id: str):
        """Handle resident check-in"""
        if resident_id in self.residents:
            self.residents[resident_id].last_check_in = datetime.now()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE residents SET last_check_in = ? WHERE id = ?
                ''', (datetime.now().isoformat(), resident_id))
            
            # Notify clients
            check_in_data = {
                "type": "CHECK_IN",
                "resident_id": resident_id,
                "timestamp": datetime.now().isoformat()
            }
            await self._broadcast_to_clients(check_in_data)

# WebSocket server
monitor = RealTimeElderlyMonitor()

async def health_monitor_server(websocket, path):
    await monitor.register_client(websocket)
    try:
        async for message in websocket:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'HEALTH_DATA':
                await monitor.handle_health_data(data)
            elif message_type == 'CHECK_IN':
                await monitor.handle_check_in(data.get('resident_id'))
            elif message_type == 'RESOLVE_ALERT':
                # Handle alert resolution
                pass
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await monitor.unregister_client(websocket)

async def main():
    """Start the WebSocket server"""
    server = await websockets.serve(health_monitor_server, "localhost", 8765)
    logger.info("Real-time elderly care monitor started on ws://localhost:8765")
    
    # Simulate some health data for demonstration
    await simulate_health_data()
    
    await server.wait_closed()

async def simulate_health_data():
    """Simulate health data for demonstration purposes"""
    import random
    import time
    
    while True:
        if monitor.residents:
            resident_id = random.choice(list(monitor.residents.keys()))
            metrics = {
                'heart_rate': random.randint(60, 100),
                'blood_pressure': f"{random.randint(110, 130)}/{random.randint(70, 85)}",
                'temperature': round(random.uniform(36.2, 37.5), 1),
                'oxygen_saturation': random.randint(95, 99)
            }
            
            # Occasionally simulate abnormal readings
            if random.random() < 0.1:  # 10% chance
                if random.random() < 0.5:
                    metrics['heart_rate'] = random.randint(40, 50)  # Low heart rate
                else:
                    metrics['oxygen_saturation'] = random.randint(85, 91)  # Low oxygen
            
            await monitor.handle_health_data({
                'resident_id': resident_id,
                'metrics': metrics
            })
        
        await asyncio.sleep(30)  # Send data every 30 seconds

if __name__ == "__main__":
    asyncio.run(main())
```

## 2. Property Management API

```python
# property_api.py
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
import sqlite3
from datetime import datetime
import uvicorn

app = FastAPI(title="Mwarokin Estates Elderly Care API", version="1.0.0")

class CareLevel(str, Enum):
    INDEPENDENT = "independent"
    ASSISTED = "assisted"
    MEMORY = "memory"
    SKILLED = "skilled"

class PropertyBase(BaseModel):
    name: str
    location: str
    care_levels: List[CareLevel]
    monthly_cost: float
    capacity: int
    available_units: int
    amenities: List[str]
    medical_services: List[str]
    image_url: Optional[str] = None
    description: Optional[str] = None

class Property(PropertyBase):
    id: int
    created_at: datetime

class PropertyFilter(BaseModel):
    care_levels: Optional[List[CareLevel]] = None
    location: Optional[str] = None
    max_price: Optional[float] = None
    min_price: Optional[float] = None
    amenities: Optional[List[str]] = None
    has_medical: Optional[bool] = None

class BookingRequest(BaseModel):
    property_id: int
    resident_name: str
    resident_age: int
    care_level: CareLevel
    contact_email: str
    contact_phone: str
    preferred_move_in: datetime
    special_requirements: Optional[str] = None

def init_database():
    """Initialize the properties database"""
    with sqlite3.connect('properties.db') as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                care_levels TEXT NOT NULL,
                monthly_cost REAL NOT NULL,
                capacity INTEGER NOT NULL,
                available_units INTEGER NOT NULL,
                amenities TEXT NOT NULL,
                medical_services TEXT NOT NULL,
                image_url TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert sample data if empty
        cursor = conn.execute('SELECT COUNT(*) FROM properties')
        if cursor.fetchone()[0] == 0:
            sample_properties = [
                (
                    "Serene Gardens Retirement",
                    "Nairobi, Karen",
                    '["independent"]',
                    3200.0,
                    50,
                    12,
                    '["24/7 Emergency Response", "Restaurant-style Dining", "Fitness & Wellness Center"]',
                    '["On-site Clinic", "Regular Health Check-ups"]',
                    "https://images.unsplash.com/photo-1560448204-603b3fc33ddc",
                    "Upscale independent living community with golf course and swimming pool"
                ),
                (
                    "Ocean View Assisted Living",
                    "Mombasa, Nyali",
                    '["assisted"]',
                    4500.0,
                    35,
                    8,
                    '["Personalized Care Plans", "Therapy Services", "Medication Management"]',
                    '["Physical Therapy", "Occupational Therapy", "24/7 Nursing"]',
                    "https://images.unsplash.com/photo-1586023492125-27b2c045efd7",
                    "Beautiful coastal facility offering personalized care plans"
                )
            ]
            
            conn.executemany('''
                INSERT INTO properties 
                (name, location, care_levels, monthly_cost, capacity, available_units, 
                 amenities, medical_services, image_url, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', sample_properties)

@app.on_event("startup")
async def startup_event():
    init_database()

@app.get("/properties", response_model=List[Property])
async def get_properties(
    care_level: Optional[CareLevel] = Query(None),
    location: Optional[str] = Query(None),
    max_price: Optional[float] = Query(None),
    min_price: Optional[float] = Query(None),
    amenity: Optional[str] = Query(None)
):
    """Get properties with optional filtering"""
    query = "SELECT * FROM properties WHERE 1=1"
    params = []
    
    if care_level:
        query += " AND care_levels LIKE ?"
        params.append(f'%"{care_level}"%')
    
    if location:
        query += " AND location LIKE ?"
        params.append(f'%{location}%')
    
    if max_price:
        query += " AND monthly_cost <= ?"
        params.append(max_price)
    
    if min_price:
        query += " AND monthly_cost >= ?"
        params.append(min_price)
    
    if amenity:
        query += " AND amenities LIKE ?"
        params.append(f'%{amenity}%')
    
    with sqlite3.connect('properties.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query, params)
        properties = cursor.fetchall()
    
    result = []
    for prop in properties:
        result.append(Property(
            id=prop['id'],
            name=prop['name'],
            location=prop['location'],
            care_levels=json.loads(prop['care_levels']),
            monthly_cost=prop['monthly_cost'],
            capacity=prop['capacity'],
            available_units=prop['available_units'],
            amenities=json.loads(prop['amenities']),
            medical_services=json.loads(prop['medical_services']),
            image_url=prop['image_url'],
            description=prop['description'],
            created_at=prop['created_at']
        ))
    
    return result

@app.get("/properties/{property_id}", response_model=Property)
async def get_property(property_id: int):
    """Get a specific property by ID"""
    with sqlite3.connect('properties.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute('SELECT * FROM properties WHERE id = ?', (property_id,))
        property_data = cursor.fetchone()
    
    if not property_data:
        raise HTTPException(status_code=404, detail="Property not found")
    
    return Property(
        id=property_data['id'],
        name=property_data['name'],
        location=property_data['location'],
        care_levels=json.loads(property_data['care_levels']),
        monthly_cost=property_data['monthly_cost'],
        capacity=property_data['capacity'],
        available_units=property_data['available_units'],
        amenities=json.loads(property_data['amenities']),
        medical_services=json.loads(property_data['medical_services']),
        image_url=property_data['image_url'],
        description=property_data['description'],
        created_at=property_data['created_at']
    )

@app.post("/bookings")
async def create_booking(booking: BookingRequest):
    """Create a new booking request"""
    # Validate property exists and has availability
    with sqlite3.connect('properties.db') as conn:
        cursor = conn.execute(
            'SELECT available_units FROM properties WHERE id = ?',
            (booking.property_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Property not found")
        
        if result[0] <= 0:
            raise HTTPException(status_code=400, detail="No available units")
    
    # In a real application, you would:
    # 1. Save the booking to a database
    # 2. Send confirmation emails
    # 3. Notify staff
    
    return {
        "message": "Booking request received successfully",
        "booking_reference": f"BK{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "next_steps": "Our team will contact you within 24 hours to discuss your requirements"
    }

@app.get("/care-levels")
async def get_care_levels():
    """Get available care levels with descriptions"""
    return {
        "independent": {
            "name": "Independent Living",
            "description": "Active senior communities with maintenance-free living",
            "services": ["Private apartments", "Social activities", "Housekeeping"]
        },
        "assisted": {
            "name": "Assisted Living",
            "description": "Support with daily activities while maintaining independence",
            "services": ["Personal care assistance", "Medication management", "24/7 staff"]
        },
        "memory": {
            "name": "Memory Care",
            "description": "Specialized care for seniors with memory issues",
            "services": ["Secure environment", "Cognitive therapies", "Specialized staff"]
        },
        "skilled": {
            "name": "Skilled Nursing",
            "description": "24/7 medical care and rehabilitation services",
            "services": ["Registered nurses", "Rehabilitation services", "Medical monitoring"]
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 3. Real-time Dashboard

```python
# dashboard.py
import asyncio
import websockets
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta

class ElderlyCareDashboard:
    def __init__(self):
        self.health_data = {}
        self.alerts = []
    
    async def connect_to_monitor(self):
        """Connect to the real-time monitor"""
        uri = "ws://localhost:8765"
        async with websockets.connect(uri) as websocket:
            # Request initial data
            await websocket.send(json.dumps({"type": "GET_INITIAL_DATA"}))
            
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                await self.handle_message(data)
    
    async def handle_message(self, data):
        """Handle incoming WebSocket messages"""
        message_type = data.get('type')
        
        if message_type == "HEALTH_UPDATE":
            await self.update_health_data(data)
        elif message_type == "ALERT":
            await self.handle_alert(data)
        elif message_type == "CHECK_IN":
            await self.handle_check_in(data)
    
    async def update_health_data(self, data):
        """Update health data and refresh dashboard"""
        resident_id = data['resident_id']
        metrics = data['metrics']
        
        if resident_id not in self.health_data:
            self.health_data[resident_id] = []
        
        self.health_data[resident_id].append({
            **metrics,
            'timestamp': data['timestamp']
        })
        
        # Keep only last 24 hours of data
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.health_data[resident_id] = [
            point for point in self.health_data[resident_id]
            if datetime.fromisoformat(point['timestamp']) > cutoff_time
        ]
        
        # Update dashboard
        await self.refresh_dashboard()
    
    async def handle_alert(self, data):
        """Handle new alerts"""
        self.alerts.append(data)
        print(f"🚨 ALERT: {data['message']} (Severity: {data['severity']})")
        
        # In a real application, you might:
        # - Send SMS/email notifications
        # - Trigger emergency protocols
        # - Update UI in real-time
    
    async def handle_check_in(self, data):
        """Handle resident check-ins"""
        print(f"✅ Check-in: Resident {data['resident_id']} at {data['timestamp']}")
    
    async def refresh_dashboard(self):
        """Refresh the dashboard display"""
        # This would update a web dashboard in a real application
        # For now, we'll just print a summary
        print("\n" + "="*50)
        print("ELDERLY CARE DASHBOARD")
        print("="*50)
        
        for resident_id, data in self.health_data.items():
            if data:
                latest = data[-1]
                print(f"\nResident {resident_id}:")
                print(f"  Heart Rate: {latest.get('heart_rate', 'N/A')} bpm")
                print(f"  Temperature: {latest.get('temperature', 'N/A')}°C")
                print(f"  Oxygen: {latest.get('oxygen_saturation', 'N/A')}%")
        
        if self.alerts:
            print(f"\nActive Alerts: {len(self.alerts)}")
            for alert in self.alerts[-3:]:  # Show last 3 alerts
                print(f"  ⚠️  {alert['message']}")
    
    def generate_health_report(self, resident_id: str, days: int = 7):
        """Generate a health report for a resident"""
        if resident_id not in self.health_data:
            return None
        
        data = self.health_data[resident_id]
        cutoff_time = datetime.now() - timedelta(days=days)
        recent_data = [
            point for point in data
            if datetime.fromisoformat(point['timestamp']) > cutoff_time
        ]
        
        if not recent_data:
            return None
        
        df = pd.DataFrame(recent_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Create visualization
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Heart Rate', 'Temperature', 'Oxygen Saturation', 'Blood Pressure'),
            vertical_spacing=0.1
        )
        
        if 'heart_rate' in df.columns:
            fig.add_trace(
                go.Scatter(x=df['timestamp'], y=df['heart_rate'], name='Heart Rate'),
                row=1, col=1
            )
        
        if 'temperature' in df.columns:
            fig.add_trace(
                go.Scatter(x=df['timestamp'], y=df['temperature'], name='Temperature'),
                row=1, col=2
            )
        
        if 'oxygen_saturation' in df.columns:
            fig.add_trace(
                go.Scatter(x=df['timestamp'], y=df['oxygen_saturation'], name='Oxygen'),
                row=2, col=1
            )
        
        fig.update_layout(height=600, title_text=f"Health Report - Resident {resident_id}")
        return fig

async def main():
    dashboard = ElderlyCareDashboard()
    
    # Start dashboard and connect to monitor
    try:
        await dashboard.connect_to_monitor()
    except Exception as e:
        print(f"Failed to connect to monitor: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

 4. Requirements File

requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
websockets==12.0
pydantic==2.5.0
plotly==5.17.0
pandas==2.1.3
python-multipart==0.0.6
aiohttp==3.9.1
asyncio-mqtt==0.13.0
```

## 5. Installation and Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Start the property API (Terminal 1)
uvicorn property_api:app --reload --port 8000

# Start the real-time monitor (Terminal 2)
python real_time_monitor.py

# Start the dashboard (Terminal 3)
python dashboard.py
```

## Key Features:

1. **Real-time Health Monitoring**: WebSocket-based system for live health data
2. **Automated Alert System**: Detects abnormal health metrics and creates alerts
3. **Property Management API**: RESTful API for property listings and bookings
4. **Live Dashboard**: Real-time visualization of resident health data
5. **Database Integration**: SQLite with proper schema design
6. **Async/Await**: Modern Python async functionality for real-time features
7. **Type Hints**: Full type annotations for better code quality

This system provides a complete backend for your elderly care platform with real-time functionality that complements your HTML frontend.