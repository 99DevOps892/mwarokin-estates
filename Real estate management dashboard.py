
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import json
import uuid
from datetime import datetime, date
import asyncio
from enum import Enum
import aiohttp
from dataclasses import dataclass
from contextlib import asynccontextmanager

# Data Models
class PaymentStatus(str, Enum):
    PAID = "paid"
    PENDING = "pending"
    OVERDUE = "overdue"

class PropertyType(str, Enum):
    ONE_BEDROOM = "One-Bed-Room"
    TWO_BEDROOM = "Two-Bed-Room"
    THREE_BEDROOM = "Three-Bed-Room"
    BEDSITTER = "Bed-Sitter"
    COMPOUND_HOME = "Compound Home"

class Continent(str, Enum):
    AFRICA = "Africa"
    ASIA = "Asia"
    EUROPE = "Europe"
    ANTARCTICA = "Antarctica"
    NORTH_AMERICA = "North America"
    AUSTRALIA = "Australia"
    SOUTH_AMERICA = "South America"

class AfricanCountry(str, Enum):
    KENYA = "Kenya"
    NIGERIA = "Nigeria"
    SOUTH_AFRICA = "South Africa"
    GHANA = "Ghana"
    EGYPT = "Egypt"
    TANZANIA = "Tanzania"
    UGANDA = "Uganda"
    ETHIOPIA = "Ethiopia"
    RWANDA = "Rwanda"

# Pydantic Models
class TenantCreate(BaseModel):
    property_details: PropertyType
    location: str
    payment_amount: float
    tenant_name: str
    month: str
    year: int

class TenantResponse(TenantCreate):
    id: str
    status: PaymentStatus
    created_at: datetime

class ChatMessage(BaseModel):
    message: str
    is_user: bool
    timestamp: datetime

class LocationData(BaseModel):
    latitude: float
    longitude: float
    address: Optional[str] = None

# Service Classes
class CurrencyService:
    _rates = {
        "Kenya": {"rate": 1, "symbol": "KSh"},
        "Nigeria": {"rate": 21.5, "symbol": "₦"},
        "South Africa": {"rate": 0.075, "symbol": "R"},
        "Ghana": {"rate": 0.064, "symbol": "₵"},
        "Egypt": {"rate": 0.18, "symbol": "E£"},
        "Tanzania": {"rate": 0.039, "symbol": "TSh"},
        "Uganda": {"rate": 0.026, "symbol": "USh"},
        "Ethiopia": {"rate": 0.17, "symbol": "Br"},
        "Rwanda": {"rate": 0.0085, "symbol": "FRw"}
    }
    
    @classmethod
    def get_currency_info(cls, country: AfricanCountry) -> Dict[str, Any]:
        return cls._rates.get(country.value, {"rate": 1, "symbol": "KSh"})

class ChatbotService:
    def __init__(self):
        self.responses = {
            "rent": "I can help you with rent payments. You can make payments through M-Pesa, bank transfer, or credit card. Would you like to proceed with a payment?",
            "property": "We have several properties available. You can view available properties, schedule a viewing, or list your property for rent/sale. What would you like to do?",
            "issue": "I'm sorry to hear you're experiencing an issue. Please describe the problem in detail, and I'll create a maintenance ticket for you.",
            "greeting": "Hello! How can I assist you with your real estate needs today?",
            "default": "I'm here to help with your real estate management needs. You can ask me about payments, properties, maintenance issues, or general inquiries."
        }
    
    async def generate_response(self, user_input: str) -> str:
        user_input = user_input.lower()
        
        if any(word in user_input for word in ["hello", "hi", "hey"]):
            return self.responses["greeting"]
        elif any(word in user_input for word in ["rent", "payment"]):
            return self.responses["rent"]
        elif any(word in user_input for word in ["property", "house", "apartment"]):
            return self.responses["property"]
        elif any(word in user_input for word in ["issue", "problem", "maintenance"]):
            return self.responses["issue"]
        else:
            return self.responses["default"]

class TenantService:
    def __init__(self):
        self.tenants: Dict[str, TenantResponse] = {}
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        sample_tenants = [
            {
                "id": "111", "property_details": PropertyType.TWO_BEDROOM, 
                "location": "Kangemi", "payment_amount": 22064.0, 
                "tenant_name": "Mwarema", "month": "January", "year": 2023,
                "status": PaymentStatus.PAID
            },
            {
                "id": "22", "property_details": PropertyType.THREE_BEDROOM,
                "location": "Taveta", "payment_amount": 35000.0,
                "tenant_name": "Kisha", "month": "March", "year": 2019,
                "status": PaymentStatus.OVERDUE
            }
        ]
        
        for tenant_data in sample_tenants:
            self.tenants[tenant_data["id"]] = TenantResponse(
                **tenant_data, created_at=datetime.now()
            )
    
    def get_all_tenants(self) -> List[TenantResponse]:
        return list(self.tenants.values())
    
    def get_tenant(self, tenant_id: str) -> Optional[TenantResponse]:
        return self.tenants.get(tenant_id)
    
    def create_tenant(self, tenant_data: TenantCreate) -> TenantResponse:
        tenant_id = str(uuid.uuid4())[:8]
        tenant = TenantResponse(
            id=tenant_id,
            **tenant_data.dict(),
            status=PaymentStatus.PENDING,
            created_at=datetime.now()
        )
        self.tenants[tenant_id] = tenant
        return tenant
    
    def update_tenant_status(self, tenant_id: str, status: PaymentStatus) -> Optional[TenantResponse]:
        if tenant_id in self.tenants:
            self.tenants[tenant_id].status = status
            return self.tenants[tenant_id]
        return None

# Application State
@dataclass
class AppState:
    tenant_service: TenantService
    chatbot_service: ChatbotService
    currency_service: CurrencyService

# Lifespan Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.services = AppState(
        tenant_service=TenantService(),
        chatbot_service=ChatbotService(),
        currency_service=CurrencyService()
    )
    yield
    # Shutdown
    # Cleanup resources if needed

# FastAPI Application
app = FastAPI(
    title="Mwarokin Real Estate Management",
    description="Modern real estate management system with advanced features",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Dependency Injection
def get_tenant_service(request: Request) -> TenantService:
    return request.app.state.services.tenant_service

def get_chatbot_service(request: Request) -> ChatbotService:
    return request.app.state.services.chatbot_service

def get_currency_service(request: Request) -> CurrencyService:
    return request.app.state.services.currency_service

# API Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """Render the main dashboard with real-time statistics"""
    tenants = tenant_service.get_all_tenants()
    
    # Calculate real-time statistics
    total_properties = len(tenants)
    active_tenants = len([t for t in tenants if t.status == PaymentStatus.PAID])
    monthly_revenue = sum(t.payment_amount for t in tenants if t.status == PaymentStatus.PAID)
    pending_issues = len([t for t in tenants if t.status == PaymentStatus.OVERDUE])
    
    dashboard_stats = {
        "total_properties": total_properties,
        "active_tenants": active_tenants,
        "monthly_revenue": f"Ksh {monthly_revenue:,.2f}",
        "pending_issues": pending_issues
    }
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "dashboard_stats": dashboard_stats,
            "tenants": tenants,
            "continents": [c.value for c in Continent],
            "countries": [c.value for c in AfricanCountry]
        }
    )

@app.get("/api/tenants", response_model=List[TenantResponse])
async def get_tenants(
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """API endpoint to get all tenants"""
    return tenant_service.get_all_tenants()

@app.post("/api/tenants", response_model=TenantResponse)
async def create_tenant(
    tenant_data: TenantCreate,
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """API endpoint to create a new tenant"""
    return tenant_service.create_tenant(tenant_data)

@app.get("/api/currency/{country}")
async def get_currency_rate(
    country: AfricanCountry,
    currency_service: CurrencyService = Depends(get_currency_service)
):
    """API endpoint to get currency conversion rates"""
    currency_info = currency_service.get_currency_info(country)
    return {
        "country": country.value,
        "symbol": currency_info["symbol"],
        "rate": currency_info["rate"],
        "message": f"{currency_info['symbol']}1 = KSh{currency_info['rate']:.3f}"
    }

@app.post("/api/chat")
async def chat_with_assistant(
    message: str = Form(...),
    chatbot_service: ChatbotService = Depends(get_chatbot_service)
):
    """API endpoint for chatbot interactions"""
    response = await chatbot_service.generate_response(message)
    return {
        "user_message": message,
        "bot_response": response,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/location")
async def process_location(location_data: LocationData):
    """API endpoint to process location data"""
    # In a real application, you would integrate with a geocoding service
    # like Google Maps API or OpenStreetMap
    
    simulated_address = f"Approximate Location: Nairobi, Kenya"
    
    return {
        "latitude": location_data.latitude,
        "longitude": location_data.longitude,
        "address": simulated_address,
        "message": f"Location pinned: {simulated_address}"
    }

# Advanced Features
class AnalyticsService:
    @staticmethod
    def calculate_rent_trends(tenants: List[TenantResponse]) -> Dict[str, Any]:
        """Calculate rental trends and analytics"""
        paid_tenants = [t for t in tenants if t.status == PaymentStatus.PAID]
        overdue_tenants = [t for t in tenants if t.status == PaymentStatus.OVERDUE]
        
        return {
            "collection_rate": len(paid_tenants) / len(tenants) * 100 if tenants else 0,
            "average_rent": sum(t.payment_amount for t in paid_tenants) / len(paid_tenants) if paid_tenants else 0,
            "overdue_amount": sum(t.payment_amount for t in overdue_tenants),
            "total_revenue": sum(t.payment_amount for t in paid_tenants)
        }

@app.get("/api/analytics")
async def get_analytics(
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """API endpoint for advanced analytics"""
    tenants = tenant_service.get_all_tenants()
    analytics = AnalyticsService.calculate_rent_trends(tenants)
    
    return {
        "analytics": analytics,
        "generated_at": datetime.now().isoformat()
    }

# Error Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred"}
    )

# Health Check
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Mwarokin Real Estate API"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        reload=True  # Enable auto-reload for development
    )