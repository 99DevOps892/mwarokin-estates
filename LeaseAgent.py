import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, EmailStr
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Integer, DateTime, JSON, Text, select, Boolean
from transformers import pipeline
import httpx
import logging
from contextlib import asynccontextmanager
from functools import wraps
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import websockets
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Mwarokin")

# Database Setup
DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/mwarokin"
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

# SQLAlchemy Models
class Base(DeclarativeBase):
    pass

class ListingDB(Base):
    __tablename__ = "listings"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    address: Mapped[str] = mapped_column(String)
    property_type: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bedrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    square_feet: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    images: Mapped[List[str]] = mapped_column(JSON, default=list)
    amenities: Mapped[List[str]] = mapped_column(JSON, default=list)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BuyerProfileDB(Base):
    __tablename__ = "buyer_profiles"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    preferences: Mapped[Dict] = mapped_column(JSON)
    credit_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    employment_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class LeaseDB(Base):
    __tablename__ = "leases"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    listing_id: Mapped[str] = mapped_column(String)
    applicant_id: Mapped[str] = mapped_column(String)
    clauses: Mapped[Dict] = mapped_column(JSON)
    payment_schedule: Mapped[Dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default="draft")  # draft, signed, active, expired
    risks: Mapped[List[str]] = mapped_column(JSON, default=[])
    signed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class TenantConfigDB(Base):
    __tablename__ = "tenant_configs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    role: Mapped[str] = mapped_column(String)
    white_label: Mapped[Dict] = mapped_column(JSON)
    locale: Mapped[str] = mapped_column(String, default="en_US")
    currency: Mapped[str] = mapped_column(String, default="USD")
    email_config: Mapped[Dict] = mapped_column(JSON, default=dict)
    whatsapp_config: Mapped[Dict] = mapped_column(JSON, default=dict)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    action: Mapped[str] = mapped_column(String)
    details: Mapped[Dict] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ViewingScheduleDB(Base):
    __tablename__ = "viewing_schedules"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    listing_id: Mapped[str] = mapped_column(String)
    viewer_name: Mapped[str] = mapped_column(String)
    viewer_email: Mapped[str] = mapped_column(String)
    viewer_phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    scheduled_date: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String, default="scheduled")  # scheduled, confirmed, completed, cancelled
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class NotificationDB(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String)  # email, whatsapp, push, system
    status: Mapped[str] = mapped_column(String, default="pending")  # pending, sent, failed
    metadata: Mapped[Dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

# Pydantic Models
class Role(str, Enum):
    ADMIN = "admin"
    AGENT = "agent"
    USER = "user"

class TenantConfig(BaseModel):
    tenant_id: str
    role: Role
    white_label: Dict[str, str] = {}
    locale: str = "en_US"
    currency: str = "USD"

class KycPayload(BaseModel):
    tenant_id: str
    user_id: str
    name: str
    dob: str  # ISO format, e.g., "1990-01-01"
    address: str
    document_id: str
    document_image: str  # Base64-encoded image

class KycResult(BaseModel):
    status: str  # "approved", "rejected", "pending"
    details: Dict
    risks: List[str]

class ComplianceReport(BaseModel):
    status: str  # "compliant", "non_compliant"
    violations: List[str]
    suggestions: List[str]

class LeaseDraftPayload(BaseModel):
    tenant_id: str
    listing_id: str
    applicant_id: str
    terms: Dict  # e.g., {"duration_months": 12, "monthly_rent": 2000, "renewal_option": true}

class LeaseDraft(BaseModel):
    clauses: Dict
    schedule: Dict
    risks: List[str]
    lease_id: str

class ViewingSchedulePayload(BaseModel):
    tenant_id: str
    listing_id: str
    viewer_name: str
    viewer_email: EmailStr
    viewer_phone: Optional[str] = None
    scheduled_date: datetime
    notes: Optional[str] = None

class NotificationPayload(BaseModel):
    tenant_id: str
    user_id: Optional[str] = None
    title: str
    message: str
    type: str = "system"
    metadata: Dict = {}

class PropertySearchPayload(BaseModel):
    tenant_id: str
    location: Optional[str] = None
    property_type: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None

# Notification Service
class NotificationService:
    def __init__(self):
        self.email_config = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "noreply@mwarokin.com",
            "sender_password": "your_password"
        }
        self.whatsapp_config = {
            "api_url": "https://api.whatsapp.com/send",
            "business_id": "your_business_id"
        }

    async def send_email(self, to_email: str, subject: str, body: str, html_body: Optional[str] = None):
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.email_config["sender_email"]
            message["To"] = to_email

            # Add both plain text and HTML versions
            part1 = MIMEText(body, "plain")
            message.attach(part1)
            
            if html_body:
                part2 = MIMEText(html_body, "html")
                message.attach(part2)

            with smtplib.SMTP(self.email_config["smtp_server"], self.email_config["smtp_port"]) as server:
                server.starttls()
                server.login(self.email_config["sender_email"], self.email_config["sender_password"])
                server.send_message(message)
            
            logger.info(f"Email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False

    async def send_whatsapp(self, to_phone: str, message: str):
        try:
            # This would integrate with WhatsApp Business API
            # For demo purposes, we'll log the message
            logger.info(f"WhatsApp message to {to_phone}: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to send WhatsApp: {str(e)}")
            return False

    async def send_push_notification(self, user_id: str, title: str, message: str, data: Dict = None):
        # This would integrate with Firebase Cloud Messaging or similar
        logger.info(f"Push notification to {user_id}: {title} - {message}")
        return True

    async def create_notification(self, db: AsyncSession, payload: NotificationPayload):
        notification = NotificationDB(
            tenant_id=payload.tenant_id,
            user_id=payload.user_id,
            title=payload.title,
            message=payload.message,
            type=payload.type,
            metadata=payload.metadata
        )
        db.add(notification)
        await db.commit()
        return notification

# WebSocket Manager for Real-time Updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, tenant_id: str):
        await websocket.accept()
        if tenant_id not in self.active_connections:
            self.active_connections[tenant_id] = []
        self.active_connections[tenant_id].append(websocket)

    def disconnect(self, websocket: WebSocket, tenant_id: str):
        if tenant_id in self.active_connections:
            self.active_connections[tenant_id].remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_tenant(self, tenant_id: str, message: Dict):
        if tenant_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[tenant_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
            
            # Remove disconnected clients
            for connection in disconnected:
                self.active_connections[tenant_id].remove(connection)

manager = ConnectionManager()
notification_service = NotificationService()

# Security and RBAC
api_key_header = APIKeyHeader(name="X-API-Key")

def require_role(min_role: Role):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, tenant_config: TenantConfig = Depends(get_tenant_config), **kwargs):
            role_hierarchy = {Role.USER: 1, Role.AGENT: 2, Role.ADMIN: 3}
            if role_hierarchy[tenant_config.role] < role_hierarchy[min_role]:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return await func(*args, tenant_config=tenant_config, **kwargs)
        return wrapper
    return decorator

async def get_tenant_config(api_key: str = Depends(api_key_header)) -> TenantConfig:
    async with async_session() as db:
        result = await db.execute(select(TenantConfigDB).where(TenantConfigDB.tenant_id == api_key))
        tenant = result.scalars().first()
        if not tenant:
            raise HTTPException(status_code=403, detail="Invalid tenant")
        return TenantConfig(
            tenant_id=tenant.tenant_id,
            role=Role(tenant.role),
            white_label=tenant.white_label,
            locale=tenant.locale,
            currency=tenant.currency
        )

# Database Dependency
async def get_db():
    async with async_session() as session:
        yield session

# NLP Model for Fair-Housing
try:
    nlp_classifier = pipeline("text-classification", model="distilbert-base-uncased-finetuned-sst-2-english")
except:
    logger.warning("NLP model not available, using mock classifier")
    nlp_classifier = None

# ComplianceAgent
class ComplianceAgent:
    async def execute(self, task: str, payload: Dict, tenant_config: TenantConfig, db: AsyncSession) -> Dict:
        if task == "check_kyc":
            return await self.check_kyc(KycPayload(**payload), tenant_config, db)
        elif task == "check_listing":
            return await self.check_listing(payload, tenant_config, db)
        else:
            raise HTTPException(status_code=400, detail="Invalid compliance task")

    async def check_kyc(self, payload: KycPayload, tenant_config: TenantConfig, db: AsyncSession) -> KycResult:
        if payload.tenant_id != tenant_config.tenant_id:
            raise HTTPException(status_code=403, detail="Tenant ID mismatch")

        # ComplyAdvantage AML screening (mocked)
        kyc_result = await self.comply_advantage_aml_check(payload)
        
        # Send notification based on result
        if kyc_result.status == "approved":
            await notification_service.create_notification(
                db,
                NotificationPayload(
                    tenant_id=tenant_config.tenant_id,
                    user_id=payload.user_id,
                    title="KYC Verification Approved",
                    message=f"KYC verification for {payload.name} has been approved.",
                    type="system",
                    metadata={"kyc_result": kyc_result.dict()}
                )
            )
        
        # Log action with PII redaction
        await self.log_action(
            db,
            tenant_config.tenant_id,
            "kyc_check",
            {"user_id": payload.user_id, "status": kyc_result.status, "risks": kyc_result.risks}
        )
        
        return kyc_result

    async def comply_advantage_aml_check(self, payload: KycPayload) -> KycResult:
        # Mock ComplyAdvantage API call (replace with real implementation)
        async with httpx.AsyncClient() as client:
            try:
                # Mock response based on name (for demo)
                if "test" in payload.name.lower() or "demo" in payload.name.lower():
                    status = "approved"
                    risks = []
                else:
                    # Simulate random risk assessment
                    import random
                    status = "approved" if random.random() > 0.2 else "rejected"
                    risks = ["Potential match in sanctions list"] if status == "rejected" else []
                
                return KycResult(
                    status=status,
                    details={
                        "name_verified": True, 
                        "aml_check": status == "approved",
                        "document_verified": True
                    },
                    risks=risks
                )
            except Exception as e:
                logger.error(f"AML API error: {str(e)}")
                return KycResult(
                    status="pending",
                    details={"error": "Service temporarily unavailable"},
                    risks=[]
                )

    async def check_listing(self, payload: Dict, tenant_config: TenantConfig, db: AsyncSession) -> ComplianceReport:
        listing_id = payload.get("listing_id")
        description = payload.get("description", "")
        
        if not listing_id and not description:
            raise HTTPException(status_code=400, detail="Listing ID or description required")

        # If listing_id provided, fetch from database
        if listing_id:
            result = await db.execute(select(ListingDB).where(ListingDB.id == listing_id, ListingDB.tenant_id == tenant_config.tenant_id))
            listing = result.scalars().first()
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            description = listing.description or ""

        # Check for fair-housing violations (US + EU rules)
        violations, suggestions = await self.check_fair_housing(description, tenant_config.locale)
        
        # Log action
        await self.log_action(
            db,
            tenant_config.tenant_id,
            "listing_compliance_check",
            {"listing_id": listing_id, "violations": violations, "description_preview": description[:100]}
        )
        
        return ComplianceReport(
            status="non_compliant" if violations else "compliant",
            violations=violations,
            suggestions=suggestions
        )

    async def check_fair_housing(self, description: str, locale: str) -> tuple[List[str], List[str]]:
        if not description:
            return [], []

        violations = []
        suggestions = []

        # US fair-housing rules
        us_discriminatory_terms = [
            "exclusive neighborhood", "family-friendly only", "no families", "specific group",
            "perfect for singles", "no children", "adults only", "christian community",
            "muslim family", "jewish neighborhood", "white neighborhood", "black community"
        ]
        
        for term in us_discriminatory_terms:
            if term.lower() in description.lower():
                violations.append(f"US Fair Housing violation: '{term}'")
                suggestions.append(f"Remove '{term}' and use neutral language")

        # EU-specific rules
        eu_discriminatory_terms = ["only locals", "christian preferred", "no immigrants", "specific nationality"]
        if locale.startswith("en_EU") or locale.startswith("fr") or locale.startswith("de"):
            for term in eu_discriminatory_terms:
                if term.lower() in description.lower():
                    violations.append(f"EU Anti-Discrimination violation: '{term}'")
                    suggestions.append(f"Remove '{term}' to comply with EU regulations")

        # NLP-based check for sentiment if available
        if nlp_classifier:
            try:
                result = nlp_classifier(description[:512])  # Limit input length
                score = result[0]["score"]
                label = result[0]["label"]
                
                if label == "NEGATIVE" and score > 0.7:
                    violations.append("Potentially biased or negative language detected")
                    suggestions.append("Rewrite description to use inclusive, neutral language")
            except Exception as e:
                logger.warning(f"NLP analysis failed: {str(e)}")

        return violations, suggestions

    async def log_action(self, db: AsyncSession, tenant_id: str, action: str, details: Dict):
        redacted_details = {k: "REDACTED" if k in ["name", "address", "dob", "document_id"] else v for k, v in details.items()}
        audit_log = AuditLog(tenant_id=tenant_id, action=action, details=redacted_details)
        db.add(audit_log)
        await db.commit()

# LeaseAgent
class LeaseAgent:
    async def execute(self, payload: Dict, tenant_config: TenantConfig, db: AsyncSession) -> LeaseDraft:
        payload = LeaseDraftPayload(**payload)
        if payload.tenant_id != tenant_config.tenant_id:
            raise HTTPException(status_code=403, detail="Tenant ID mismatch")

        # Validate listing and applicant
        listing_result = await db.execute(select(ListingDB).where(ListingDB.id == payload.listing_id, ListingDB.tenant_id == tenant_config.tenant_id))
        listing = listing_result.scalars().first()
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")

        profile_result = await db.execute(select(BuyerProfileDB).where(BuyerProfileDB.id == payload.applicant_id, BuyerProfileDB.tenant_id == tenant_config.tenant_id))
        profile = profile_result.scalars().first()
        if not profile:
            raise HTTPException(status_code=404, detail="Applicant not found")

        # Generate detailed lease clauses
        clauses = {
            "duration_months": payload.terms.get("duration_months", 12),
            "monthly_rent": payload.terms.get("monthly_rent", listing.price or 2000),
            "renewal_option": payload.terms.get("renewal_option", False),
            "renewal_terms": {"extension_months": 12, "rent_increase_percent": 5} if payload.terms.get("renewal_option") else None,
            "late_payment_penalty": {"amount": 50, "grace_period_days": 5},
            "security_deposit": payload.terms.get("monthly_rent", 2000),
            "maintenance_responsibility": "Tenant responsible for minor repairs under $100",
            "property_address": listing.address,
            "tenant_name": profile.name
        }
        
        start_date = datetime.utcnow() + timedelta(days=7)
        schedule = {
            "start_date": start_date.isoformat(),
            "end_date": (start_date + timedelta(days=30 * clauses["duration_months"])).isoformat(),
            "payments": [
                {
                    "due_date": (start_date + timedelta(days=30 * i)).isoformat(),
                    "amount": clauses["monthly_rent"],
                    "type": "rent"
                } for i in range(1, clauses["duration_months"] + 1)
            ]
        }
        
        risks = []
        if clauses["renewal_option"] and not profile.credit_score:
            risks.append("Credit check recommended for renewal option")
        if clauses["monthly_rent"] > profile.preferences.get("max_price", float("inf")):
            risks.append("Rent exceeds applicant's stated budget")
        if not profile.employment_status:
            risks.append("Employment verification recommended")

        # Save to database
        lease = LeaseDB(
            tenant_id=tenant_config.tenant_id,
            listing_id=payload.listing_id,
            applicant_id=payload.applicant_id,
            clauses=clauses,
            payment_schedule=schedule,
            risks=risks
        )
        db.add(lease)
        await db.commit()
        await db.refresh(lease)

        # Send notification
        await notification_service.create_notification(
            db,
            NotificationPayload(
                tenant_id=tenant_config.tenant_id,
                user_id=payload.applicant_id,
                title="Lease Draft Created",
                message=f"Lease draft has been created for {listing.address}",
                type="system",
                metadata={"lease_id": lease.id, "listing_address": listing.address}
            )
        )

        # Log action
        await self.log_action(db, tenant_config.tenant_id, "lease_draft_created", {"lease_id": lease.id})

        return LeaseDraft(clauses=clauses, schedule=schedule, risks=risks, lease_id=lease.id)

    async def log_action(self, db: AsyncSession, tenant_id: str, action: str, details: Dict):
        redacted_details = {k: "REDACTED" if k in ["name", "address", "dob"] else v for k, v in details.items()}
        audit_log = AuditLog(tenant_id=tenant_id, action=action, details=redacted_details)
        db.add(audit_log)
        await db.commit()

# Property Search Agent
class PropertySearchAgent:
    async def execute(self, payload: Dict, tenant_config: TenantConfig, db: AsyncSession) -> Dict:
        search_payload = PropertySearchPayload(**payload)
        
        # Build query
        query = select(ListingDB).where(ListingDB.tenant_id == tenant_config.tenant_id, ListingDB.is_available == True)
        
        if search_payload.location:
            query = query.where(ListingDB.address.ilike(f"%{search_payload.location}%"))
        if search_payload.property_type:
            query = query.where(ListingDB.property_type == search_payload.property_type)
        if search_payload.min_price:
            query = query.where(ListingDB.price >= search_payload.min_price)
        if search_payload.max_price:
            query = query.where(ListingDB.price <= search_payload.max_price)
        if search_payload.bedrooms:
            query = query.where(ListingDB.bedrooms >= search_payload.bedrooms)
        if search_payload.bathrooms:
            query = query.where(ListingDB.bathrooms >= search_payload.bathrooms)
        
        result = await db.execute(query)
        listings = result.scalars().all()
        
        return {
            "count": len(listings),
            "results": [
                {
                    "id": listing.id,
                    "address": listing.address,
                    "property_type": listing.property_type,
                    "bedrooms": listing.bedrooms,
                    "bathrooms": listing.bathrooms,
                    "square_feet": listing.square_feet,
                    "price": listing.price,
                    "description": listing.description,
                    "images": listing.images,
                    "amenities": listing.amenities
                } for listing in listings
            ]
        }

# Viewing Schedule Agent
class ViewingScheduleAgent:
    async def execute(self, payload: Dict, tenant_config: TenantConfig, db: AsyncSession) -> Dict:
        schedule_payload = ViewingSchedulePayload(**payload)
        
        # Check if listing exists
        result = await db.execute(select(ListingDB).where(ListingDB.id == schedule_payload.listing_id, ListingDB.tenant_id == tenant_config.tenant_id))
        listing = result.scalars().first()
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        # Create viewing schedule
        viewing = ViewingScheduleDB(
            tenant_id=tenant_config.tenant_id,
            listing_id=schedule_payload.listing_id,
            viewer_name=schedule_payload.viewer_name,
            viewer_email=schedule_payload.viewer_email,
            viewer_phone=schedule_payload.viewer_phone,
            scheduled_date=schedule_payload.scheduled_date,
            notes=schedule_payload.notes
        )
        db.add(viewing)
        await db.commit()
        await db.refresh(viewing)
        
        # Send email confirmation
        email_body = f"""
        Dear {schedule_payload.viewer_name},
        
        Your property viewing has been scheduled:
        
        Property: {listing.address}
        Date: {schedule_payload.scheduled_date.strftime('%B %d, %Y at %I:%M %p')}
        
        We look forward to showing you the property!
        
        Best regards,
        Mwarokin Team
        """
        
        html_body = f"""
        <html>
        <body>
            <h2>Viewing Scheduled</h2>
            <p>Dear {schedule_payload.viewer_name},</p>
            <p>Your property viewing has been scheduled:</p>
            <ul>
                <li><strong>Property:</strong> {listing.address}</li>
                <li><strong>Date:</strong> {schedule_payload.scheduled_date.strftime('%B %d, %Y at %I:%M %p')}</li>
            </ul>
            <p>We look forward to showing you the property!</p>
            <p>Best regards,<br>Mwarokin Team</p>
        </body>
        </html>
        """
        
        await notification_service.send_email(
            schedule_payload.viewer_email,
            f"Viewing Scheduled - {listing.address}",
            email_body,
            html_body
        )
        
        # Send WhatsApp reminder if phone provided
        if schedule_payload.viewer_phone:
            whatsapp_msg = f"Reminder: Your viewing for {listing.address} is scheduled for {schedule_payload.scheduled_date.strftime('%B %d, %Y at %I:%M %p')}"
            await notification_service.send_whatsapp(schedule_payload.viewer_phone, whatsapp_msg)
        
        # Broadcast real-time notification
        await manager.broadcast_to_tenant(tenant_config.tenant_id, {
            "type": "viewing_scheduled",
            "data": {
                "viewing_id": viewing.id,
                "property_address": listing.address,
                "viewer_name": schedule_payload.viewer_name,
                "scheduled_date": schedule_payload.scheduled_date.isoformat()
            }
        })
        
        return {
            "viewing_id": viewing.id,
            "status": "scheduled",
            "message": "Viewing scheduled successfully. Confirmation email sent."
        }

# Analytics Agent
class AnalyticsAgent:
    async def execute(self, payload: Dict, tenant_config: TenantConfig, db: AsyncSession) -> Dict:
        # Get basic analytics
        listings_result = await db.execute(
            select(ListingDB).where(ListingDB.tenant_id == tenant_config.tenant_id)
        )
        listings = listings_result.scalars().all()
        
        leases_result = await db.execute(
            select(LeaseDB).where(LeaseDB.tenant_id == tenant_config.tenant_id)
        )
        leases = leases_result.scalars().all()
        
        viewings_result = await db.execute(
            select(ViewingScheduleDB).where(ViewingScheduleDB.tenant_id == tenant_config.tenant_id)
        )
        viewings = viewings_result.scalars().all()
        
        available_listings = [l for l in listings if l.is_available]
        active_leases = [l for l in leases if l.status == "active"]
        
        return {
            "metrics": {
                "total_listings": len(listings),
                "available_listings": len(available_listings),
                "occupancy_rate": (len(listings) - len(available_listings)) / len(listings) * 100 if listings else 0,
                "total_leases": len(leases),
                "active_leases": len(active_leases),
                "scheduled_viewings": len([v for v in viewings if v.status == "scheduled"]),
                "monthly_revenue": sum([lease.clauses.get("monthly_rent", 0) for lease in active_leases])
            },
            "compliance_status": {
                "compliant_listings": len(listings),  # This would be calculated based on actual compliance checks
                "needs_review": 0
            }
        }

# Orchestrator
class Orchestrator:
    def __init__(self):
        self.agents = {
            "compliance": ComplianceAgent(),
            "lease": LeaseAgent(),
            "property_search": PropertySearchAgent(),
            "viewing_schedule": ViewingScheduleAgent(),
            "analytics": AnalyticsAgent(),
        }

    async def process_task(self, task_type: str, payload: Dict, tenant_config: TenantConfig, db: AsyncSession) -> Dict:
        agent = self.agents.get(task_type)
        if not agent:
            raise HTTPException(status_code=400, detail="Invalid task type")

        logger.info(f"Executing {task_type} for tenant {tenant_config.tenant_id}")
        try:
            result = await agent.execute(payload, tenant_config, db)
            logger.info(f"Completed {task_type} successfully")
            return result
        except Exception as e:
            logger.error(f"Error in {task_type}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

# FastAPI App
app = FastAPI(
    title="Mwarokin Real Estate OS",
    description="Advanced real estate management platform with AI-powered compliance and leasing",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app.router.lifespan = lifespan

# API Endpoints
orchestrator = Orchestrator()

@app.get("/")
async def root():
    return {"message": "Mwarokin Real Estate OS API", "version": "2.0.0"}

@app.post("/compliance/kyc")
@require_role(Role.AGENT)
async def check_kyc(payload: KycPayload, tenant_config: TenantConfig = Depends(get_tenant_config), db: AsyncSession = Depends(get_db)):
    return await orchestrator.process_task("compliance", {"task": "check_kyc", **payload.dict()}, tenant_config, db)

@app.post("/compliance/listing")
@require_role(Role.AGENT)
async def check_listing(payload: Dict, tenant_config: TenantConfig = Depends(get_tenant_config), db: AsyncSession = Depends(get_db)):
    return await orchestrator.process_task("compliance", {"task": "check_listing", **payload}, tenant_config, db)

@app.post("/lease/draft")
@require_role(Role.AGENT)
async def create_lease_draft(payload: LeaseDraftPayload, tenant_config: TenantConfig = Depends(get_tenant_config), db: AsyncSession = Depends(get_db)):
    return await orchestrator.process_task("lease", payload.dict(), tenant_config, db)

@app.post("/properties/search")
@require_role(Role.USER)
async def search_properties(payload: PropertySearchPayload, tenant_config: TenantConfig = Depends(get_tenant_config), db: AsyncSession = Depends(get_db)):
    return await orchestrator.process_task("property_search", payload.dict(), tenant_config, db)

@app.post("/viewings/schedule")
@require_role(Role.USER)
async def schedule_viewing(payload: ViewingSchedulePayload, tenant_config: TenantConfig = Depends(get_tenant_config), db: AsyncSession = Depends(get_db)):
    return await orchestrator.process_task("viewing_schedule", payload.dict(), tenant_config, db)

@app.get("/analytics/dashboard")
@require_role(Role.AGENT)
async def get_dashboard_analytics(tenant_config: TenantConfig = Depends(get_tenant_config), db: AsyncSession = Depends(get_db)):
    return await orchestrator.process_task("analytics", {}, tenant_config, db)

@app.get("/notifications")
@require_role(Role.USER)
async def get_notifications(tenant_config: TenantConfig = Depends(get_tenant_config), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NotificationDB).where(NotificationDB.tenant_id == tenant_config.tenant_id).order_by(NotificationDB.created_at.desc()).limit(50)
    )
    notifications = result.scalars().all()
    return {
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "type": n.type,
                "created_at": n.created_at.isoformat(),
                "metadata": n.metadata
            } for n in notifications
        ]
    }

# WebSocket endpoint for real-time updates
@app.websocket("/ws/{tenant_id}")
async def websocket_endpoint(websocket: WebSocket, tenant_id: str):
    await manager.connect(websocket, tenant_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
            await websocket.send_json({"type": "ack", "message": "Message received"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, tenant_id)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Run the app (for development)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)