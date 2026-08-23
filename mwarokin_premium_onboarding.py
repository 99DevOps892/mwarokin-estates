"""
MWAROKIN ESTATES - PREMIUM ONBOARDING SYSTEM
Modern Python Backend for the UI Onboarding Flow
Agentic-ready code with role-based configuration, validation, and session management
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import re
import json
import hashlib
import secrets
from abc import ABC, abstractmethod


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class Role(str, Enum):
    TENANT = "tenant"
    LANDLORD = "landlord"
    CARETAKER = "caretaker"
    MANAGEMENT = "management"


class PaymentMethod(str, Enum):
    MPESA = "mpesa"
    AIRTEL = "airtel"
    SYLLOPAY = "syllopay"
    BANK = "bank"
    MULTIPLE = "multiple"


class AccessLevel(str, Enum):
    VIEW_ONLY = "view_only"
    LIMITED = "limited"
    FULL = "full"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    OTP_SENT = "otp_sent"
    OTP_VERIFIED = "otp_verified"
    EMAIL_VERIFIED = "email_verified"
    COMPLETED = "completed"


# ============================================================================
# DATA CLASSES - Models
# ============================================================================

@dataclass
class Address:
    street: str
    city: str
    state: str
    country: str
    postal_code: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "Address":
        return cls(**data)


@dataclass
class BaseProfile:
    full_name: str
    email: str
    phone: str
    national_id: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def validate_email(self) -> bool:
        pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        return bool(re.match(pattern, self.email))

    def validate_phone(self) -> bool:
        pattern = r'^\+?[0-9\s\-\(\)]{8,15}$'
        return bool(re.match(pattern, self.phone))


@dataclass
class TenantProfile(BaseProfile):
    current_address: str
    move_in_date: datetime
    occupants: int
    desired_property_id: Optional[str] = None
    emergency_contact: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "move_in_date": self.move_in_date.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class LandlordProfile(BaseProfile):
    company_name: Optional[str] = None
    property_count: str  # "1", "2-5", "6-10", "10+"
    primary_address: str
    business_registration: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class CaretakerProfile(BaseProfile):
    assigned_property: str
    experience_years: str  # "0-2", "2-5", "5-10", "10+"
    primary_skill: str  # "electrical", "plumbing", "general", "mixed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class ManagementProfile(BaseProfile):
    department: str  # "operations", "finance", "admin", "support", "super_admin"
    staff_id: str
    access_level: AccessLevel = AccessLevel.LIMITED

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "access_level": self.access_level.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class TenantConfiguration:
    preferred_payment: PaymentMethod = PaymentMethod.MPESA
    sms_notifications: bool = True
    email_notifications: bool = True
    push_notifications: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preferred_payment": self.preferred_payment.value,
            "sms_notifications": self.sms_notifications,
            "email_notifications": self.email_notifications,
            "push_notifications": self.push_notifications,
        }


@dataclass
class LandlordConfiguration:
    payment_methods: List[PaymentMethod] = field(default_factory=lambda: [PaymentMethod.MPESA])
    paybill_number: Optional[str] = None
    late_reminders: bool = True
    auto_notify_caretakers: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payment_methods": [m.value for m in self.payment_methods],
            "paybill_number": self.paybill_number,
            "late_reminders": self.late_reminders,
            "auto_notify_caretakers": self.auto_notify_caretakers,
        }


@dataclass
class CaretakerConfiguration:
    handle_repairs: bool = True
    manage_waste: bool = True
    monitor_water: bool = True
    manage_security: bool = True
    communication_channel: str = "sms"  # "sms", "email", "app"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ManagementConfiguration:
    access_level: AccessLevel = AccessLevel.LIMITED
    tenant_management: bool = True
    landlord_management: bool = True
    finance_payments: bool = True
    reports_analytics: bool = True
    user_management: bool = False
    system_settings: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_level": self.access_level.value,
            "tenant_management": self.tenant_management,
            "landlord_management": self.landlord_management,
            "finance_payments": self.finance_payments,
            "reports_analytics": self.reports_analytics,
            "user_management": self.user_management,
            "system_settings": self.system_settings,
        }


@dataclass
class VerificationData:
    phone_verified: bool = False
    email_verified: bool = False
    otp_code: Optional[str] = None
    otp_expiry: Optional[datetime] = None
    terms_agreed: bool = False
    policies_agreed: bool = False
    data_processing_consent: bool = False
    status: VerificationStatus = VerificationStatus.PENDING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phone_verified": self.phone_verified,
            "email_verified": self.email_verified,
            "otp_code": self.otp_code,
            "otp_expiry": self.otp_expiry.isoformat() if self.otp_expiry else None,
            "terms_agreed": self.terms_agreed,
            "policies_agreed": self.policies_agreed,
            "data_processing_consent": self.data_processing_consent,
            "status": self.status.value,
        }


@dataclass
class OnboardingSession:
    session_id: str
    role: Role
    step: int = 0
    profile: Optional[BaseProfile] = None
    config: Any = None
    verification: VerificationData = field(default_factory=VerificationData)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_completed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "role": self.role.value,
            "step": self.step,
            "profile": self.profile.to_dict() if self.profile else None,
            "config": self.config.to_dict() if self.config else None,
            "verification": self.verification.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_completed": self.is_completed,
        }


# ============================================================================
# REPOSITORY / STORAGE INTERFACE
# ============================================================================

class SessionRepository(ABC):
    """Abstract repository for session storage"""
    
    @abstractmethod
    def save(self, session: OnboardingSession) -> str:
        """Save session and return session_id"""
        pass
    
    @abstractmethod
    def get(self, session_id: str) -> Optional[OnboardingSession]:
        """Retrieve session by ID"""
        pass
    
    @abstractmethod
    def update(self, session: OnboardingSession) -> bool:
        """Update existing session"""
        pass
    
    @abstractmethod
    def delete(self, session_id: str) -> bool:
        """Delete session"""
        pass


class InMemorySessionRepository(SessionRepository):
    """In-memory storage for development/testing"""
    
    def __init__(self):
        self._sessions: Dict[str, OnboardingSession] = {}
    
    def save(self, session: OnboardingSession) -> str:
        self._sessions[session.session_id] = session
        return session.session_id
    
    def get(self, session_id: str) -> Optional[OnboardingSession]:
        return self._sessions.get(session_id)
    
    def update(self, session: OnboardingSession) -> bool:
        if session.session_id in self._sessions:
            self._sessions[session.session_id] = session
            return True
        return False
    
    def delete(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False


# ============================================================================
# PROFILE FACTORY - Role-based profile creation
# ============================================================================

class ProfileFactory:
    """Factory for creating role-specific profiles from form data"""
    
    @staticmethod
    def create_profile(role: Role, data: Dict[str, Any]) -> BaseProfile:
        """Create a profile instance based on role and data"""
        
        if role == Role.TENANT:
            return TenantProfile(
                full_name=data.get("full_name", ""),
                email=data.get("email", ""),
                phone=data.get("phone", ""),
                national_id=data.get("national_id", ""),
                current_address=data.get("current_address", ""),
                move_in_date=datetime.fromisoformat(data.get("move_in_date", datetime.now().isoformat())),
                occupants=int(data.get("occupants", 1)),
                desired_property_id=data.get("desired_property_id"),
                emergency_contact=data.get("emergency_contact"),
            )
        
        elif role == Role.LANDLORD:
            return LandlordProfile(
                full_name=data.get("full_name", ""),
                email=data.get("email", ""),
                phone=data.get("phone", ""),
                national_id=data.get("national_id", ""),
                company_name=data.get("company_name"),
                property_count=data.get("property_count", "1"),
                primary_address=data.get("primary_address", ""),
                business_registration=data.get("business_registration"),
            )
        
        elif role == Role.CARETAKER:
            return CaretakerProfile(
                full_name=data.get("full_name", ""),
                email=data.get("email", ""),
                phone=data.get("phone", ""),
                national_id=data.get("national_id", ""),
                assigned_property=data.get("assigned_property", ""),
                experience_years=data.get("experience_years", "0-2"),
                primary_skill=data.get("primary_skill", "general"),
            )
        
        elif role == Role.MANAGEMENT:
            return ManagementProfile(
                full_name=data.get("full_name", ""),
                email=data.get("email", ""),
                phone=data.get("phone", ""),
                national_id=data.get("national_id", ""),
                department=data.get("department", "admin"),
                staff_id=data.get("staff_id", ""),
                access_level=AccessLevel(data.get("access_level", "limited")),
            )
        
        raise ValueError(f"Unsupported role: {role}")


# ============================================================================
# CONFIGURATION FACTORY
# ============================================================================

class ConfigurationFactory:
    """Factory for creating role-specific configurations"""
    
    @staticmethod
    def create_config(role: Role, data: Dict[str, Any]) -> Any:
        """Create configuration based on role and data"""
        
        if role == Role.TENANT:
            return TenantConfiguration(
                preferred_payment=PaymentMethod(data.get("preferred_payment", "mpesa")),
                sms_notifications=data.get("sms_notifications", True),
                email_notifications=data.get("email_notifications", True),
                push_notifications=data.get("push_notifications", True),
            )
        
        elif role == Role.LANDLORD:
            payment_methods = data.get("payment_methods", ["mpesa"])
            if isinstance(payment_methods, list):
                payment_methods = [PaymentMethod(m) for m in payment_methods]
            elif isinstance(payment_methods, str):
                payment_methods = [PaymentMethod(payment_methods)]
            
            return LandlordConfiguration(
                payment_methods=payment_methods,
                paybill_number=data.get("paybill_number"),
                late_reminders=data.get("late_reminders", True),
                auto_notify_caretakers=data.get("auto_notify_caretakers", True),
            )
        
        elif role == Role.CARETAKER:
            return CaretakerConfiguration(
                handle_repairs=data.get("handle_repairs", True),
                manage_waste=data.get("manage_waste", True),
                monitor_water=data.get("monitor_water", True),
                manage_security=data.get("manage_security", True),
                communication_channel=data.get("communication_channel", "sms"),
            )
        
        elif role == Role.MANAGEMENT:
            return ManagementConfiguration(
                access_level=AccessLevel(data.get("access_level", "limited")),
                tenant_management=data.get("tenant_management", True),
                landlord_management=data.get("landlord_management", True),
                finance_payments=data.get("finance_payments", True),
                reports_analytics=data.get("reports_analytics", True),
                user_management=data.get("user_management", False),
                system_settings=data.get("system_settings", False),
            )
        
        raise ValueError(f"Unsupported role: {role}")


# ============================================================================
# VALIDATORS
# ============================================================================

class OnboardingValidator:
    """Validator for onboarding data"""
    
    @staticmethod
    def validate_role_selection(role: str) -> bool:
        """Validate that the selected role is valid"""
        try:
            Role(role)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_profile_data(role: Role, data: Dict[str, Any]) -> List[str]:
        """Validate profile data and return list of validation errors"""
        errors = []
        
        # Common required fields
        required_common = ["full_name", "email", "phone", "national_id"]
        for field in required_common:
            if not data.get(field, "").strip():
                errors.append(f"{field} is required")
        
        # Email validation
        email = data.get("email", "")
        if email and not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            errors.append("Invalid email address")
        
        # Phone validation
        phone = data.get("phone", "")
        if phone and not re.match(r'^\+?[0-9\s\-\(\)]{8,15}$', phone):
            errors.append("Invalid phone number")
        
        # Role-specific validations
        if role == Role.TENANT:
            if not data.get("current_address", "").strip():
                errors.append("current_address is required")
            if not data.get("move_in_date"):
                errors.append("move_in_date is required")
            if not data.get("occupants"):
                errors.append("occupants is required")
            elif not str(data.get("occupants", "")).isdigit():
                errors.append("occupants must be a number")
        
        elif role == Role.LANDLORD:
            if not data.get("property_count", "").strip():
                errors.append("property_count is required")
            if not data.get("primary_address", "").strip():
                errors.append("primary_address is required")
        
        elif role == Role.CARETAKER:
            if not data.get("assigned_property", "").strip():
                errors.append("assigned_property is required")
            if not data.get("experience_years", "").strip():
                errors.append("experience_years is required")
            if not data.get("primary_skill", "").strip():
                errors.append("primary_skill is required")
        
        elif role == Role.MANAGEMENT:
            if not data.get("department", "").strip():
                errors.append("department is required")
            if not data.get("staff_id", "").strip():
                errors.append("staff_id is required")
        
        return errors
    
    @staticmethod
    def validate_otp(otp_code: str) -> bool:
        """Validate OTP code format (6 digits)"""
        return bool(re.match(r'^\d{6}$', otp_code))
    
    @staticmethod
    def validate_verification(verification: VerificationData) -> List[str]:
        """Validate verification data"""
        errors = []
        
        if not verification.terms_agreed:
            errors.append("Terms of Service must be agreed")
        if not verification.policies_agreed:
            errors.append("Privacy Policy must be agreed")
        if not verification.data_processing_consent:
            errors.append("Data processing consent is required")
        
        if verification.status != VerificationStatus.OTP_VERIFIED:
            errors.append("Phone verification is required")
        
        if not verification.email_verified:
            errors.append("Email verification is required")
        
        return errors


# ============================================================================
# AGENTIC ONBOARDING SERVICE - Core Business Logic
# ============================================================================

class OnboardingService:
    """
    Agentic onboarding service that orchestrates the complete onboarding flow.
    Designed to be called by AI agents or API endpoints.
    """
    
    def __init__(self, repository: Optional[SessionRepository] = None):
        self.repository = repository or InMemorySessionRepository()
        self.validator = OnboardingValidator()
        self.profile_factory = ProfileFactory()
        self.config_factory = ConfigurationFactory()
    
    def start_onboarding(self, role: str, initial_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Start a new onboarding session
        
        Args:
            role: The selected role ('tenant', 'landlord', 'caretaker', 'management')
            initial_data: Optional initial data to pre-populate
            
        Returns:
            Session data including session_id and initial state
        """
        # Validate role
        if not self.validator.validate_role_selection(role):
            return {"error": f"Invalid role: {role}", "success": False}
        
        role_enum = Role(role)
        session_id = self._generate_session_id()
        
        session = OnboardingSession(
            session_id=session_id,
            role=role_enum,
            step=0,
            verification=VerificationData(),
        )
        
        # Pre-populate if data provided
        if initial_data:
            # We don't set profile yet, just store in session for later
            pass
        
        self.repository.save(session)
        
        return {
            "success": True,
            "session_id": session_id,
            "role": role,
            "step": 0,
            "message": "Onboarding session started. Please complete step 1: Role Selection",
        }
    
    def submit_profile(self, session_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit profile information for the current session
        
        Args:
            session_id: The session identifier
            profile_data: Dictionary containing profile fields
            
        Returns:
            Validation result and next step information
        """
        session = self.repository.get(session_id)
        if not session:
            return {"error": "Session not found", "success": False}
        
        # Validate profile data
        errors = self.validator.validate_profile_data(session.role, profile_data)
        if errors:
            return {
                "success": False,
                "errors": errors,
                "message": "Profile validation failed",
            }
        
        # Create profile
        profile = self.profile_factory.create_profile(session.role, profile_data)
        session.profile = profile
        session.step = 2  # Move to configuration step
        session.updated_at = datetime.now()
        
        self.repository.update(session)
        
        return {
            "success": True,
            "session_id": session_id,
            "step": 2,
            "role": session.role.value,
            "message": "Profile saved. Please proceed to configuration.",
        }
    
    def submit_configuration(self, session_id: str, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit role-specific configuration
        
        Args:
            session_id: The session identifier
            config_data: Configuration data
            
        Returns:
            Result with next step information
        """
        session = self.repository.get(session_id)
        if not session:
            return {"error": "Session not found", "success": False}
        
        if not session.profile:
            return {"error": "Profile must be completed before configuration", "success": False}
        
        # Create configuration
        config = self.config_factory.create_config(session.role, config_data)
        session.config = config
        session.step = 3  # Move to verification step
        session.updated_at = datetime.now()
        
        self.repository.update(session)
        
        return {
            "success": True,
            "session_id": session_id,
            "step": 3,
            "role": session.role.value,
            "message": "Configuration saved. Please complete verification.",
        }
    
    def send_otp(self, session_id: str) -> Dict[str, Any]:
        """
        Send OTP to the user's phone
        
        Args:
            session_id: The session identifier
            
        Returns:
            Result with OTP sent status
        """
        session = self.repository.get(session_id)
        if not session:
            return {"error": "Session not found", "success": False}
        
        if not session.profile:
            return {"error": "Profile must be completed before OTP", "success": False}
        
        # Generate OTP
        otp_code = self._generate_otp()
        otp_expiry = datetime.now().replace(hour=datetime.now().hour + 1)  # 1 hour expiry
        
        session.verification.otp_code = otp_code
        session.verification.otp_expiry = otp_expiry
        session.verification.status = VerificationStatus.OTP_SENT
        session.updated_at = datetime.now()
        
        self.repository.update(session)
        
        # In a real implementation, this would send an SMS
        print(f"[OTP] Sent {otp_code} to {session.profile.phone}")
        
        return {
            "success": True,
            "session_id": session_id,
            "message": f"OTP sent to {session.profile.phone}",
            "otp_sent": True,
            # For development only - never expose OTP in production
            "_dev_otp": otp_code,
        }
    
    def verify_otp(self, session_id: str, otp_code: str) -> Dict[str, Any]:
        """
        Verify the OTP code
        
        Args:
            session_id: The session identifier
            otp_code: The 6-digit OTP code
            
        Returns:
            Verification result
        """
        session = self.repository.get(session_id)
        if not session:
            return {"error": "Session not found", "success": False}
        
        if not self.validator.validate_otp(otp_code):
            return {"error": "Invalid OTP format. Must be 6 digits.", "success": False}
        
        if session.verification.status != VerificationStatus.OTP_SENT:
            return {"error": "OTP has not been sent yet", "success": False}
        
        if session.verification.otp_code != otp_code:
            return {"error": "Invalid OTP code", "success": False}
        
        if session.verification.otp_expiry and datetime.now() > session.verification.otp_expiry:
            return {"error": "OTP has expired. Please request a new one.", "success": False}
        
        session.verification.status = VerificationStatus.OTP_VERIFIED
        session.verification.phone_verified = True
        session.updated_at = datetime.now()
        
        self.repository.update(session)
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Phone verified successfully",
            "phone_verified": True,
        }
    
    def verify_email(self, session_id: str, token: str) -> Dict[str, Any]:
        """
        Verify email using a verification token
        
        Args:
            session_id: The session identifier
            token: Email verification token
            
        Returns:
            Verification result
        """
        session = self.repository.get(session_id)
        if not session:
            return {"error": "Session not found", "success": False}
        
        # In a real implementation, validate the token
        # For now, we'll assume the token is valid
        session.verification.email_verified = True
        session.updated_at = datetime.now()
        
        self.repository.update(session)
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Email verified successfully",
            "email_verified": True,
        }
    
    def submit_verification(self, session_id: str, verification_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit final verification data (terms, policies, etc.)
        
        Args:
            session_id: The session identifier
            verification_data: Verification data
            
        Returns:
            Result with completion status
        """
        session = self.repository.get(session_id)
        if not session:
            return {"error": "Session not found", "success": False}
        
        # Update verification data
        verification = session.verification
        verification.terms_agreed = verification_data.get("terms_agreed", False)
        verification.policies_agreed = verification_data.get("policies_agreed", False)
        verification.data_processing_consent = verification_data.get("data_processing_consent", False)
        session.updated_at = datetime.now()
        
        # Validate
        errors = self.validator.validate_verification(verification)
        if errors:
            return {"success": False, "errors": errors}
        
        # Complete onboarding
        verification.status = VerificationStatus.COMPLETED
        session.is_completed = True
        session.step = 4  # Complete step
        session.updated_at = datetime.now()
        
        self.repository.update(session)
        
        # Determine dashboard URL based on role
        dashboard_map = {
            Role.TENANT: "Tenants.html",
            Role.LANDLORD: "Landlord.html",
            Role.CARETAKER: "CareTakers.html",
            Role.MANAGEMENT: "Mwarokin Dashboard Agents.html",
        }
        
        return {
            "success": True,
            "session_id": session_id,
            "step": 4,
            "role": session.role.value,
            "message": "Onboarding complete!",
            "is_completed": True,
            "dashboard_url": dashboard_map.get(session.role, "dashboard.html"),
            "session_data": session.to_dict(),
        }
    
    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """
        Get the current state of an onboarding session
        
        Args:
            session_id: The session identifier
            
        Returns:
            Current session state
        """
        session = self.repository.get(session_id)
        if not session:
            return {"error": "Session not found", "success": False}
        
        return {
            "success": True,
            "session_id": session_id,
            "role": session.role.value,
            "step": session.step,
            "is_completed": session.is_completed,
            "profile": session.profile.to_dict() if session.profile else None,
            "config": session.config.to_dict() if session.config else None,
            "verification": session.verification.to_dict(),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }
    
    def cancel_onboarding(self, session_id: str) -> Dict[str, Any]:
        """
        Cancel an onboarding session
        
        Args:
            session_id: The session identifier
            
        Returns:
            Cancellation result
        """
        self.repository.delete(session_id)
        return {
            "success": True,
            "session_id": session_id,
            "message": "Onboarding session cancelled",
        }
    
    # ========== PRIVATE HELPERS ==========
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        return secrets.token_hex(16)
    
    def _generate_otp(self) -> str:
        """Generate a 6-digit OTP"""
        return ''.join(secrets.choice('0123456789') for _ in range(6))


# ============================================================================
# AGENTIC ONBOARDING AGENT - AI Agent Interface
# ============================================================================

class OnboardingAgent:
    """
    AI Agent interface for the onboarding system.
    Provides a natural language-friendly API for agentic interactions.
    """
    
    def __init__(self, service: Optional[OnboardingService] = None):
        self.service = service or OnboardingService()
        self._session_context: Dict[str, Dict[str, Any]] = {}
    
    def process_intent(self, intent: str, session_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Process a natural language intent for onboarding
        
        Args:
            intent: The user intent ('start', 'select_role', 'profile', 'config', 'verify', 'complete')
            session_id: Optional session ID
            **kwargs: Additional parameters
            
        Returns:
            Action result with appropriate response
        """
        
        intents = {
            "start": self._handle_start,
            "select_role": self._handle_select_role,
            "profile": self._handle_profile,
            "config": self._handle_config,
            "send_otp": self._handle_send_otp,
            "verify_otp": self._handle_verify_otp,
            "verify_email": self._handle_verify_email,
            "verify_terms": self._handle_verify_terms,
            "complete": self._handle_complete,
            "status": self._handle_status,
            "cancel": self._handle_cancel,
        }
        
        handler = intents.get(intent)
        if not handler:
            return {"error": f"Unknown intent: {intent}", "success": False}
        
        return handler(session_id, **kwargs)
    
    def _handle_start(self, session_id: Optional[str], **kwargs) -> Dict[str, Any]:
        """Handle start intent - begins onboarding"""
        role = kwargs.get("role", "tenant")
        return self.service.start_onboarding(role, kwargs.get("data"))
    
    def _handle_select_role(self, session_id: Optional[str], **kwargs) -> Dict[str, Any]:
        """Handle role selection - (same as start for simplicity)"""
        if not session_id:
            return self.service.start_onboarding(kwargs.get("role", "tenant"), kwargs.get("data"))
        return {"success": True, "session_id": session_id, "message": "Role selected", "step": 1}
    
    def _handle_profile(self, session_id: Optional[str], **kwargs) -> Dict[str, Any]:
        """Handle profile submission"""
        if not session_id:
            return {"error": "Session ID required", "success": False}
        return self.service.submit_profile(session_id, kwargs.get("data", {}))
    
    def _handle_config(self, session_id: Optional[str], **kwargs) -> Dict[str, Any]:
        """Handle configuration submission"""
        if not session_id:
            return {"error": "Session ID required", "success": False}
        return self.service.submit_configuration(session_id, kwargs.get("data", {}))
    
    def _handle_send_otp(self, session_id: Optional[str], **kwargs) -> Dict[str, Any]:
        """Handle OTP sending"""
        if not session_id:
            return {"error": "Session ID required", "success": False}
        return self.service.send_otp(session_id)
    
    def _handle_verify_otp(self, session_id: Optional[str], **kwargs) -> Dict[str, Any]:
        """Handle OTP verification"""
        if not session_id:
            return {"error": "Session ID required", "success": False}
        otp_code = kwargs.get("otp_code", "")
        return self.service.verify_otp(session_id, otp_code)
    
    def _handle_verify_email(self, session_id: Optional[str], **kwargs) -> Dict[str, Any]:
        """Handle email verification"""
        if not session_id:
            return {"error": "Session ID required", "success": False}
        token = kwargs.get("token", "")
        return self.service.verify_email(session_id, token)
    
    def _handle_verify_terms(self, session_id: Optional[str], **kwargs) -> Dict[str, Any]:
        """Handle terms and policies agreement"""
        if not session_id:
            return {"error": "Session ID required", "success": False}
        data = {
            "terms_agreed": kwargs.get("terms_agreed", False),
            "policies_agreed": kwargs.get("policies_agreed", False),
            "data_processing_consent": kwargs.get("data_processing_consent", False),
        }
        # This is part of the verification step
        session = self.service.repository.get(session_id)
        if not session:
            return {"error": "Session not found", "success": False}
        
        session.verification.terms_agreed = data["terms_agreed"]
        session.verification.policies_agreed = data["policies_agreed"]
        session.verification.data_processing_consent = data["data_processing_consent"]
        self.service.repository.update(session)
        
        return {"success": True, "session_id": session_id, "message": "Terms agreed"}
    
    def _handle_complete(self, session_id: Optional[str], **kwargs) -> Dict[str, Any]:
        """Handle completion of onboarding"""
        if not session_id:
            return {"error": "Session ID required", "success": False}
        
        # Get session and submit final verification
        session = self.service.repository.get(session_id)
        if not session:
            return {"error": "Session not found", "success": False}
        
        verification_data = {
            "terms_agreed": session.verification.terms_agreed,
            "policies_agreed": session.verification.policies_agreed,
            "data_processing_consent": session.verification.data_processing_consent,
        }
        return self.service.submit_verification(session_id, verification_data)
    
    def _handle_status(self, session_id: Optional[str], **kwargs) -> Dict[str, Any]:
        """Handle status check"""
        if not session_id:
            return {"error": "Session ID required", "success": False}
        return self.service.get_session_state(session_id)
    
    def _handle_cancel(self, session_id: Optional[str], **kwargs) -> Dict[str, Any]:
        """Handle cancellation"""
        if not session_id:
            return {"error": "Session ID required", "success": False}
        return self.service.cancel_onboarding(session_id)


# ============================================================================
# DASHBOARD REDIRECT SERVICE
# ============================================================================

class DashboardRedirectService:
    """Service for determining dashboard redirects based on role"""
    
    DASHBOARD_URLS = {
        Role.TENANT: "Tenants.html",
        Role.LANDLORD: "Landlord.html",
        Role.CARETAKER: "CareTakers.html",
        Role.MANAGEMENT: "Mwarokin Dashboard Agents.html",
    }
    
    @classmethod
    def get_dashboard_url(cls, role: Role) -> str:
        """Get the dashboard URL for a given role"""
        return cls.DASHBOARD_URLS.get(role, "dashboard.html")
    
    @classmethod
    def get_redirect_response(cls, session_id: str, session: OnboardingSession) -> Dict[str, Any]:
        """Get a redirect response for a completed session"""
        if not session.is_completed:
            return {"error": "Onboarding not completed", "success": False}
        
        dashboard_url = cls.get_dashboard_url(session.role)
        
        return {
            "success": True,
            "session_id": session_id,
            "redirect_url": dashboard_url,
            "message": f"Redirecting to {dashboard_url}",
            "role": session.role.value,
            "session_data": session.to_dict(),
        }


# ============================================================================
# USAGE EXAMPLES / TESTING
# ============================================================================

def run_onboarding_flow():
    """Example of a complete onboarding flow using the service"""
    
    # Initialize service
    service = OnboardingService()
    
    # Start onboarding
    print("=" * 60)
    print("STARTING ONBOARDING FLOW")
    print("=" * 60)
    
    result = service.start_onboarding("tenant")
    session_id = result["session_id"]
    print(f"Session started: {session_id}")
    
    # Step 1: Profile
    print("\n--- STEP 1: PROFILE ---")
    profile_data = {
        "full_name": "John Mwangi",
        "email": "john@example.com",
        "phone": "+254 712 345 678",
        "national_id": "12345678",
        "current_address": "123 Main Street, Nairobi",
        "move_in_date": "2025-01-15",
        "occupants": "3",
    }
    result = service.submit_profile(session_id, profile_data)
    print(f"Profile submitted: {result.get('message')}")
    
    # Step 2: Configuration
    print("\n--- STEP 2: CONFIGURATION ---")
    config_data = {
        "preferred_payment": "mpesa",
        "sms_notifications": True,
        "email_notifications": True,
        "push_notifications": True,
    }
    result = service.submit_configuration(session_id, config_data)
    print(f"Configuration saved: {result.get('message')}")
    
    # Step 3: Verification
    print("\n--- STEP 3: VERIFICATION ---")
    
    # Send OTP
    result = service.send_otp(session_id)
    print(f"OTP sent: {result.get('message')}")
    otp_code = result.get("_dev_otp", "123456")
    
    # Verify OTP
    result = service.verify_otp(session_id, otp_code)
    print(f"OTP verified: {result.get('message')}")
    
    # Verify Email (simulated)
    result = service.verify_email(session_id, "mock_token")
    print(f"Email verified: {result.get('message')}")
    
    # Agree to Terms
    session = service.repository.get(session_id)
    session.verification.terms_agreed = True
    session.verification.policies_agreed = True
    session.verification.data_processing_consent = True
    service.repository.update(session)
    print("Terms and policies agreed")
    
    # Complete
    result = service.submit_verification(session_id, {
        "terms_agreed": True,
        "policies_agreed": True,
        "data_processing_consent": True,
    })
    print(f"\n--- COMPLETION ---")
    print(f"Onboarding complete: {result.get('message')}")
    print(f"Dashboard URL: {result.get('dashboard_url')}")
    
    # Get final state
    state = service.get_session_state(session_id)
    print(f"\n--- FINAL STATE ---")
    print(f"Role: {state.get('role')}")
    print(f"Step: {state.get('step')}")
    print(f"Completed: {state.get('is_completed')}")
    
    return session_id


def agentic_onboarding_example():
    """Example of agentic onboarding using the OnboardingAgent"""
    
    agent = OnboardingAgent()
    
    print("\n" + "=" * 60)
    print("AGENTIC ONBOARDING EXAMPLE")
    print("=" * 60)
    
    # Agent starts onboarding
    result = agent.process_intent("start", role="landlord")
    session_id = result["session_id"]
    print(f"Agent: {result.get('message')}")
    
    # Agent handles profile
    profile_data = {
        "full_name": "Jane Kipchoge",
        "email": "jane@example.com",
        "phone": "+254 722 345 678",
        "national_id": "87654321",
        "company_name": "Kipchoge Properties",
        "property_count": "2-5",
        "primary_address": "456 Business Park, Nairobi",
        "business_registration": "REG123456",
    }
    result = agent.process_intent("profile", session_id, data=profile_data)
    print(f"Agent: {result.get('message')}")
    
    # Agent handles config
    config_data = {
        "payment_methods": ["mpesa", "bank"],
        "paybill_number": "123456",
        "late_reminders": True,
        "auto_notify_caretakers": True,
    }
    result = agent.process_intent("config", session_id, data=config_data)
    print(f"Agent: {result.get('message')}")
    
    # Agent handles verification
    result = agent.process_intent("send_otp", session_id)
    print(f"Agent: {result.get('message')}")
    
    otp = result.get("_dev_otp", "654321")
    result = agent.process_intent("verify_otp", session_id, otp_code=otp)
    print(f"Agent: {result.get('message')}")
    
    result = agent.process_intent("verify_email", session_id, token="mock_token")
    print(f"Agent: {result.get('message')}")
    
    result = agent.process_intent("verify_terms", session_id, 
                                   terms_agreed=True, policies_agreed=True, data_processing_consent=True)
    print(f"Agent: {result.get('message')}")
    
    # Agent completes onboarding
    result = agent.process_intent("complete", session_id)
    print(f"Agent: {result.get('message')}")
    print(f"Dashboard: {result.get('dashboard_url')}")
    
    return session_id


# ============================================================================
# MAIN - RUN DEMO
# ============================================================================

if __name__ == "__main__":
    # Run the demo flows
    print("\n" + "=" * 60)
    print("MWAROKIN ESTATES - ONBOARDING SYSTEM DEMO")
    print("=" * 60)
    print("\nPython version: Modern, Agentic, Premium")
    print("Designed for the Mwarokin Estates UI Onboarding Flow")
    print("\n--- Running Demo Flows ---\n")
    
    # Standard flow
    session_id1 = run_onboarding_flow()
    
    # Agentic flow
    session_id2 = agentic_onboarding_example()
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print(f"Session 1: {session_id1}")
    print(f"Session 2: {session_id2}")
    print("=" * 60)
