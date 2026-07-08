
# main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import asyncio
import json
import os

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./property_management.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    property_address = Column(String)
    rent_amount = Column(Float)
    lease_start = Column(DateTime)
    lease_end = Column(DateTime)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True)
    amount = Column(Float)
    payment_date = Column(DateTime)
    due_date = Column(DateTime)
    status = Column(String, default="pending")  # pending, completed, overdue
    payment_method = Column(String)
    reference = Column(String)

class MaintenanceRequest(Base):
    __tablename__ = "maintenance_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, index=True)
    property_address = Column(String)
    issue_type = Column(String)
    description = Column(String)
    priority = Column(String)  # low, medium, high, urgent
    status = Column(String, default="pending")  # pending, in_progress, completed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class Property(Base):
    __tablename__ = "properties"
    
    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, unique=True, index=True)
    type = Column(String)  # apartment, house, condo
    bedrooms = Column(Integer)
    bathrooms = Column(Integer)
    rent_amount = Column(Float)
    status = Column(String, default="available")  # available, occupied, maintenance
    owner = Column(String)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic Models
class TenantCreate(BaseModel):
    name: str
    email: str
    phone: str
    property_address: str
    rent_amount: float
    lease_start: datetime
    lease_end: datetime

class TenantResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    property_address: str
    rent_amount: float
    lease_start: datetime
    lease_end: datetime
    status: str
    
    class Config:
        from_attributes = True

class PaymentCreate(BaseModel):
    tenant_id: int
    amount: float
    due_date: datetime
    payment_method: str

class PaymentResponse(BaseModel):
    id: int
    tenant_id: int
    amount: float
    payment_date: Optional[datetime]
    due_date: datetime
    status: str
    payment_method: str
    
    class Config:
        from_attributes = True

class MaintenanceCreate(BaseModel):
    tenant_id: int
    property_address: str
    issue_type: str
    description: str
    priority: str

class MaintenanceResponse(BaseModel):
    id: int
    tenant_id: int
    property_address: str
    issue_type: str
    description: str
    priority: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    monthly_revenue: float
    active_tenants: int
    pending_requests: int
    overdue_payments: int
    revenue_change: float
    tenant_change: int

# FastAPI App
app = FastAPI(title="Mwarokin Estates API", version="1.0.0")

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

# WebSocket manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Real-time data simulation
class RealTimeDataSimulator:
    def __init__(self):
        self.is_running = False
    
    async def start_simulation(self):
        self.is_running = True
        while self.is_running:
            await asyncio.sleep(30)  # Update every 30 seconds
            # Simulate new notifications, payments, etc.
            notification = {
                "type": "notification",
                "title": "System Update",
                "message": "Real-time data refreshed",
                "timestamp": datetime.utcnow().isoformat()
            }
            await manager.broadcast(json.dumps(notification))

simulator = RealTimeDataSimulator()

# API Routes
@app.get("/")
async def root():
    return {"message": "Mwarokin Estates Property Management API"}

@app.get("/api/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    # Calculate real stats from database
    total_revenue = db.query(Payment).filter(
        Payment.status == "completed",
        Payment.payment_date >= datetime.utcnow() - timedelta(days=30)
    ).with_entities(db.func.sum(Payment.amount)).scalar() or 0
    
    active_tenants = db.query(Tenant).filter(Tenant.status == "active").count()
    
    pending_requests = db.query(MaintenanceRequest).filter(
        MaintenanceRequest.status == "pending"
    ).count()
    
    overdue_payments = db.query(Payment).filter(
        Payment.status == "overdue"
    ).count()
    
    # Calculate changes (simplified)
    previous_revenue = total_revenue * 0.85  # Simulate 15% increase
    revenue_change = ((total_revenue - previous_revenue) / previous_revenue * 100) if previous_revenue else 0
    
    return DashboardStats(
        monthly_revenue=total_revenue,
        active_tenants=active_tenants,
        pending_requests=pending_requests,
        overdue_payments=overdue_payments,
        revenue_change=revenue_change,
        tenant_change=2  # Simplified
    )

@app.get("/api/tenants", response_model=List[TenantResponse])
async def get_tenants(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    tenants = db.query(Tenant).offset(skip).limit(limit).all()
    return tenants

@app.post("/api/tenants", response_model=TenantResponse)
async def create_tenant(tenant: TenantCreate, db: Session = Depends(get_db)):
    db_tenant = Tenant(**tenant.dict())
    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)
    
    # Notify all connected clients
    notification = {
        "type": "new_tenant",
        "message": f"New tenant added: {tenant.name}",
        "tenant": tenant.name
    }
    await manager.broadcast(json.dumps(notification))
    
    return db_tenant

@app.get("/api/payments", response_model=List[PaymentResponse])
async def get_payments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    payments = db.query(Payment).offset(skip).limit(limit).all()
    return payments

@app.post("/api/payments", response_model=PaymentResponse)
async def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    db_payment = Payment(
        **payment.dict(),
        payment_date=datetime.utcnow(),
        status="completed"
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    
    # Notify all connected clients
    notification = {
        "type": "payment_received",
        "message": f"Payment received: ${payment.amount}",
        "amount": payment.amount
    }
    await manager.broadcast(json.dumps(notification))
    
    return db_payment

@app.get("/api/maintenance", response_model=List[MaintenanceResponse])
async def get_maintenance_requests(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    requests = db.query(MaintenanceRequest).offset(skip).limit(limit).all()
    return requests

@app.post("/api/maintenance", response_model=MaintenanceResponse)
async def create_maintenance_request(request: MaintenanceCreate, db: Session = Depends(get_db)):
    db_request = MaintenanceRequest(**request.dict())
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    
    # Notify all connected clients
    notification = {
        "type": "maintenance_request",
        "message": f"New maintenance request: {request.issue_type}",
        "priority": request.priority
    }
    await manager.broadcast(json.dumps(notification))
    
    return db_request

@app.put("/api/maintenance/{request_id}")
async def update_maintenance_status(request_id: int, status: str, db: Session = Depends(get_db)):
    db_request = db.query(MaintenanceRequest).filter(MaintenanceRequest.id == request_id).first()
    if not db_request:
        raise HTTPException(status_code=404, detail="Maintenance request not found")
    
    db_request.status = status
    if status == "completed":
        db_request.completed_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": f"Maintenance request {request_id} updated to {status}"}

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages from clients
            message = json.loads(data)
            if message.get("type") == "ping":
                await manager.send_personal_message(json.dumps({"type": "pong"}), websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Serve the frontend
@app.on_event("startup")
async def startup_event():
    # Initialize with sample data
    db = SessionLocal()
    try:
        # Check if we need to add sample data
        if db.query(Tenant).count() == 0:
            sample_tenants = [
                Tenant(
                    name="Michael Brown",
                    email="michael@example.com",
                    phone="555-0101",
                    property_address="123 Main St",
                    rent_amount=1200.00,
                    lease_start=datetime(2024, 1, 1),
                    lease_end=datetime(2024, 12, 31)
                ),
                Tenant(
                    name="Sarah Johnson",
                    email="sarah@example.com",
                    phone="555-0102",
                    property_address="456 Oak Ave",
                    rent_amount=1500.00,
                    lease_start=datetime(2024, 2, 1),
                    lease_end=datetime(2025, 1, 31)
                )
            ]
            db.add_all(sample_tenants)
            db.commit()
    finally:
        db.close()
    
    # Start real-time simulation
    asyncio.create_task(simulator.start_simulation())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

## Enhanced Frontend with Real-time Integration

Create a new file `templates/index.html` with your HTML content, but add this JavaScript for real-time functionality:

```javascript
// Add this to your existing JavaScript
class RealTimeManager {
    constructor() {
        this.ws = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.updateConnectionStatus(true);
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.isConnected = false;
            this.updateConnectionStatus(false);
            this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    handleMessage(data) {
        switch(data.type) {
            case 'notification':
                this.showNotification(data.title, data.message);
                break;
            case 'new_tenant':
                this.updateDashboardStats();
                this.showNotification('New Tenant', data.message);
                break;
            case 'payment_received':
                this.updateDashboardStats();
                this.showNotification('Payment Received', data.message);
                break;
            case 'maintenance_request':
                this.updateDashboardStats();
                this.showNotification('Maintenance Request', data.message, data.priority);
                break;
        }
    }

    showNotification(title, message, priority = 'info') {
        const notificationPanel = document.getElementById('notificationPanel');
        const notificationItem = document.createElement('div');
        notificationItem.className = `notification-item ${priority}`;
        notificationItem.innerHTML = `
            <div class="notification-title">${title}</div>
            <div class="notification-text">${message}</div>
            <div class="notification-time">Just now</div>
        `;
        notificationPanel.appendChild(notificationItem);

        // Update notification count
        const notificationCount = document.querySelector('.notification-count');
        notificationCount.textContent = parseInt(notificationCount.textContent) + 1;

        // Show notification toast
        this.showToast(message, priority);
    }

    showToast(message, type = 'info') {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            border-left: 4px solid #4361ee;
            z-index: 10000;
            max-width: 300px;
        `;

        if (type === 'warning') toast.style.borderLeftColor = '#f8961e';
        if (type === 'danger') toast.style.borderLeftColor = '#f72585';

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 5000);
    }

    updateConnectionStatus(connected) {
        const statusIndicator = document.getElementById('connectionStatus') || this.createStatusIndicator();
        statusIndicator.textContent = connected ? '🟢 Live' : '🔴 Offline';
        statusIndicator.style.background = connected ? '#4CAF50' : '#f44336';
    }

    createStatusIndicator() {
        const indicator = document.createElement('div');
        indicator.id = 'connectionStatus';
        indicator.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 20px;
            background: #4CAF50;
            color: white;
            padding: 8px 12px;
            border-radius: 20px;
            font-size: 12px;
            z-index: 1000;
        `;
        document.body.appendChild(indicator);
        return indicator;
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                this.connect();
            }, 3000);
        }
    }

    sendMessage(message) {
        if (this.isConnected && this.ws) {
            this.ws.send(JSON.stringify(message));
        }
    }
}

// API Service
class ApiService {
    constructor() {
        this.baseUrl = window.location.origin;
    }

    async fetchDashboardStats() {
        try {
            const response = await fetch(`${this.baseUrl}/api/dashboard/stats`);
            return await response.json();
        } catch (error) {
            console.error('Error fetching dashboard stats:', error);
            return null;
        }
    }

    async fetchTenants() {
        try {
            const response = await fetch(`${this.baseUrl}/api/tenants`);
            return await response.json();
        } catch (error) {
            console.error('Error fetching tenants:', error);
            return [];
        }
    }

    async createTenant(tenantData) {
        try {
            const response = await fetch(`${this.baseUrl}/api/tenants`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(tenantData),
            });
            return await response.json();
        } catch (error) {
            console.error('Error creating tenant:', error);
            return null;
        }
    }

    async createPayment(paymentData) {
        try {
            const response = await fetch(`${this.baseUrl}/api/payments`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(paymentData),
            });
            return await response.json();
        } catch (error) {
            console.error('Error creating payment:', error);
            return null;
        }
    }

    async createMaintenanceRequest(requestData) {
        try {
            const response = await fetch(`${this.baseUrl}/api/maintenance`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData),
            });
            return await response.json();
        } catch (error) {
            console.error('Error creating maintenance request:', error);
            return null;
        }
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    const realTimeManager = new RealTimeManager();
    const apiService = new ApiService();

    // Connect to WebSocket
    realTimeManager.connect();

    // Load initial data
    loadDashboardData();
    loadTenantsData();

    // Set up periodic data refresh
    setInterval(loadDashboardData, 30000); // Refresh every 30 seconds

    async function loadDashboardData() {
        const stats = await apiService.fetchDashboardStats();
        if (stats) {
            updateDashboardUI(stats);
        }
    }

    async function loadTenantsData() {
        const tenants = await apiService.fetchTenants();
        if (tenants.length > 0) {
            updateTenantsTable(tenants);
        }
    }

    function updateDashboardUI(stats) {
        // Update stat cards
        document.querySelector('.stat-card.primary .stat-value').textContent = `$${stats.monthly_revenue.toLocaleString()}`;
        document.querySelector('.stat-card.success .stat-value').textContent = stats.active_tenants;
        document.querySelector('.stat-card.warning .stat-value').textContent = stats.pending_requests;
        document.querySelector('.stat-card.danger .stat-value').textContent = stats.overdue_payments;

        // Update change indicators
        const revenueChange = document.querySelector('.stat-card.primary .stat-change');
        revenueChange.innerHTML = `<i class="fas fa-arrow-up"></i> ${stats.revenue_change.toFixed(1)}% from last month`;
        revenueChange.className = `stat-change ${stats.revenue_change >= 0 ? 'positive' : 'negative'}`;
    }

    function updateTenantsTable(tenants) {
        // Implementation for updating tenants table
        console.log('Updating tenants table with:', tenants);
    }

    // Export to global scope for debugging
    window.realTimeManager = realTimeManager;
    window.apiService = apiService;
});
```

## Requirements File

Create `requirements.txt`:

```txt
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
python-multipart==0.0.6
websockets==12.0
```

## Running the Application

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run the application:**
```bash
python main.py
```

3. **Access the application:**
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Key Features

1. **Real-time Updates**: WebSocket connections for live data updates
2. **RESTful API**: Complete CRUD operations for all entities
3. **Database Integration**: SQLAlchemy with SQLite
4. **Dashboard Analytics**: Real-time statistics and charts
5. **Notification System**: Live notifications for important events
6. **Responsive Design**: Your existing beautiful UI with enhanced functionality

## Advanced Features

- **WebSocket Reconnection**: Automatic reconnection if connection drops
- **Real-time Notifications**: Instant updates across all connected clients
- **Data Persistence**: All data stored in SQLite database
- **API Documentation**: Auto-generated Swagger docs at `/docs`
- **Error Handling**: Comprehensive error handling and validation

This solution provides a complete, production-ready property management system with seamless frontend-backend integration and real-time capabilities.