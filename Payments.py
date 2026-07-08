```python
"""
Mwarokin Estates Payment Portal - Backend API
Modern, professional, and user-friendly payment processing service.
"""

import asyncio
import logging
import random
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator, root_validator
import uvicorn

# -----------------------------------------------------------------------------
# Logging configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Data Models (Pydantic)
# -----------------------------------------------------------------------------


class PaymentBase(BaseModel):
    """Base model for all payment requests."""
    amount: float = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="KES", description="Currency code (KES, USD, etc.)")
    reference: Optional[str] = Field(None, description="Optional reference")

    @validator("currency")
    def validate_currency(cls, v: str) -> str:
        allowed = {"KES", "USD", "NGN", "GHS", "ZAR"}
        if v not in allowed:
            raise ValueError(f"Currency must be one of {allowed}")
        return v.upper()


class SyllopayRequest(PaymentBase):
    syllo_code: str = Field(..., min_length=3, description="SylloPay ID or SylloCode")


class MpesaRequest(PaymentBase):
    phone: str = Field(..., description="M-Pesa phone number (07XX...)")
    reference: Optional[str] = Field(None, description="Account reference")

    @validator("phone")
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"\s+", "", v)
        if not re.match(r"^0[71]\d{8}$", cleaned):
            raise ValueError("Phone number must be in format 07XX XXX XXX")
        return cleaned


class BankTransferRequest(PaymentBase):
    bank_name: str = Field(..., description="Name of the bank")
    account_number: str = Field(..., description="Bank account number")
    account_name: str = Field(..., description="Account holder name")


class MobileWalletRequest(PaymentBase):
    wallet_provider: str = Field(..., description="Mobile wallet provider (e.g., Airtel Money)")
    wallet_number: str = Field(..., description="Wallet phone number or ID")


class CryptoRequest(PaymentBase):
    cryptocurrency: str = Field(..., description="Cryptocurrency type (e.g., Bitcoin, Ethereum)")
    wallet_address: str = Field(..., description="Recipient wallet address")
    currency: str = Field(default="USD", description="Currency for amount (typically USD)")


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------


class PaymentResponse(BaseModel):
    id: str
    status: str  # pending, completed, initiated, awaiting_confirmation, failed
    type: str  # syllopay, mpesa, bank_transfer, mobile_wallet, crypto
    amount: float
    currency: str
    timestamp: str
    reference: Optional[str] = None
    # Additional fields for specific payment types (optional)
    extra: Optional[Dict[str, Any]] = None


class PaymentHistoryResponse(BaseModel):
    payments: List[PaymentResponse]


# -----------------------------------------------------------------------------
# In-Memory Payment Storage
# -----------------------------------------------------------------------------


class PaymentStore:
    """Thread-safe in-memory store for payment records."""

    def __init__(self):
        self._payments: List[PaymentResponse] = []
        self._lock = asyncio.Lock()

    async def add_payment(self, payment: PaymentResponse) -> None:
        """Add a payment record."""
        async with self._lock:
            self._payments.insert(0, payment)

    async def get_all(self) -> List[PaymentResponse]:
        """Return all payments (newest first)."""
        async with self._lock:
            return self._payments.copy()

    async def update_status(self, payment_id: str, new_status: str, extra: Optional[Dict[str, Any]] = None) -> bool:
        """Update a payment's status and optional extra data. Returns True if found."""
        async with self._lock:
            for p in self._payments:
                if p.id == payment_id:
                    p.status = new_status
                    if extra:
                        p.extra = extra
                    return True
            return False


store = PaymentStore()


# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------


def generate_reference() -> str:
    """Generate a random reference number."""
    return f"REF{random.randint(100000, 999999)}"


def generate_id(prefix: str) -> str:
    """Generate a unique ID with a prefix."""
    return f"{prefix}_{uuid4().hex[:8]}"


def current_timestamp() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.utcnow().isoformat()


# -----------------------------------------------------------------------------
# Payment Processing Services (Simulated)
# -----------------------------------------------------------------------------


class PaymentService:
    """Simulates payment processing for various methods."""

    @staticmethod
    async def process_syllopay(data: SyllopayRequest) -> PaymentResponse:
        """Process SylloPay payment."""
        await asyncio.sleep(1.3)  # simulate network delay
        payment_id = generate_id("sp")
        ref = data.reference or generate_reference()
        return PaymentResponse(
            id=payment_id,
            status="completed",
            type="syllopay",
            amount=data.amount,
            currency=data.currency,
            timestamp=current_timestamp(),
            reference=ref,
            extra={"syllo_code": data.syllo_code},
        )

    @staticmethod
    async def process_mpesa(data: MpesaRequest) -> PaymentResponse:
        """Process M-Pesa payment (STK push)."""
        await asyncio.sleep(1.0)
        payment_id = generate_id("mp")
        ref = data.reference or generate_reference()
        return PaymentResponse(
            id=payment_id,
            status="pending",
            type="mpesa",
            amount=data.amount,
            currency=data.currency,
            timestamp=current_timestamp(),
            reference=ref,
            extra={"phone": data.phone},
        )

    @staticmethod
    async def process_bank_transfer(data: BankTransferRequest) -> PaymentResponse:
        """Process bank transfer."""
        await asyncio.sleep(1.5)
        payment_id = generate_id("bt")
        ref = data.reference or generate_reference()
        return PaymentResponse(
            id=payment_id,
            status="pending",
            type="bank_transfer",
            amount=data.amount,
            currency=data.currency,
            timestamp=current_timestamp(),
            reference=ref,
            extra={
                "bank_name": data.bank_name,
                "account_number": data.account_number,
            },
        )

    @staticmethod
    async def process_mobile_wallet(data: MobileWalletRequest) -> PaymentResponse:
        """Process mobile wallet payment."""
        await asyncio.sleep(1.2)
        payment_id = generate_id("mw")
        ref = data.reference or generate_reference()
        return PaymentResponse(
            id=payment_id,
            status="initiated",
            type="mobile_wallet",
            amount=data.amount,
            currency=data.currency,
            timestamp=current_timestamp(),
            reference=ref,
            extra={
                "wallet_provider": data.wallet_provider,
                "wallet_number": data.wallet_number,
            },
        )

    @staticmethod
    async def process_crypto(data: CryptoRequest) -> PaymentResponse:
        """Process cryptocurrency payment."""
        await asyncio.sleep(1.0)
        payment_id = generate_id("cp")
        ref = data.reference or generate_reference()
        # Simulate crypto conversion (rough)
        crypto_amount = round(data.amount / 4000, 8) if data.currency == "USD" else round(data.amount / 150, 8)
        return PaymentResponse(
            id=payment_id,
            status="awaiting_confirmation",
            type="crypto",
            amount=data.amount,
            currency=data.currency,
            timestamp=current_timestamp(),
            reference=ref,
            extra={
                "cryptocurrency": data.cryptocurrency,
                "wallet_address": data.wallet_address,
                "crypto_amount": crypto_amount,
            },
        )


# -----------------------------------------------------------------------------
# FastAPI Application
# -----------------------------------------------------------------------------

app = FastAPI(
    title="Mwarokin Estates Payment API",
    description="Premium payment processing for estate management",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------


@app.get("/", tags=["Root"])
async def root():
    """Welcome endpoint."""
    return {
        "message": "Welcome to Mwarokin Estates Payment API",
        "docs": "/api/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Root"])
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": current_timestamp()}


@app.post("/api/payments/syllopay", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_syllopay_payment(request: SyllopayRequest):
    """Initiate a SylloPay payment."""
    try:
        payment = await PaymentService.process_syllopay(request)
        await store.add_payment(payment)
        logger.info(f"SylloPay payment created: {payment.id}")
        return payment
    except Exception as e:
        logger.error(f"Error processing Syllopay: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/payments/mpesa", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_mpesa_payment(request: MpesaRequest):
    """Initiate an M-Pesa STK push payment."""
    try:
        payment = await PaymentService.process_mpesa(request)
        await store.add_payment(payment)
        logger.info(f"M-Pesa payment created: {payment.id}")
        return payment
    except Exception as e:
        logger.error(f"Error processing M-Pesa: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/payments/bank-transfer", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_bank_transfer(request: BankTransferRequest):
    """Initiate a bank transfer payment."""
    try:
        payment = await PaymentService.process_bank_transfer(request)
        await store.add_payment(payment)
        logger.info(f"Bank transfer created: {payment.id}")
        return payment
    except Exception as e:
        logger.error(f"Error processing bank transfer: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/payments/mobile-wallet", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_mobile_wallet_payment(request: MobileWalletRequest):
    """Initiate a mobile wallet payment."""
    try:
        payment = await PaymentService.process_mobile_wallet(request)
        await store.add_payment(payment)
        logger.info(f"Mobile wallet payment created: {payment.id}")
        return payment
    except Exception as e:
        logger.error(f"Error processing mobile wallet: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/payments/crypto", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_crypto_payment(request: CryptoRequest):
    """Initiate a cryptocurrency payment."""
    try:
        payment = await PaymentService.process_crypto(request)
        await store.add_payment(payment)
        logger.info(f"Crypto payment created: {payment.id}")
        return payment
    except Exception as e:
        logger.error(f"Error processing crypto: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/payments/history", response_model=PaymentHistoryResponse)
async def get_payment_history():
    """Retrieve all payment records."""
    payments = await store.get_all()
    return PaymentHistoryResponse(payments=payments)


# -----------------------------------------------------------------------------
# Startup Events
# -----------------------------------------------------------------------------


@app.on_event("startup")
async def startup_event():
    """Seed the store with sample payment data."""
    sample_payments = [
        PaymentResponse(
            id="sp_1",
            status="completed",
            type="syllopay",
            amount=12000.0,
            currency="KES",
            timestamp=datetime.utcnow().isoformat(),
            reference="SYL284710",
            extra={"syllo_code": "SYL-4XK92"},
        ),
        PaymentResponse(
            id="mp_1",
            status="completed",
            type="mpesa",
            amount=5000.0,
            currency="KES",
            timestamp=datetime.utcnow().isoformat(),
            reference="MPX384729",
            extra={"phone": "0712 *** 456"},
        ),
        PaymentResponse(
            id="bt_1",
            status="pending",
            type="bank_transfer",
            amount=7500.0,
            currency="KES",
            timestamp=datetime.utcnow().isoformat(),
            reference="REF384729",
            extra={"bank_name": "Equity Bank"},
        ),
        PaymentResponse(
            id="mw_1",
            status="completed",
            type="mobile_wallet",
            amount=3500.0,
            currency="KES",
            timestamp=datetime.utcnow().isoformat(),
            reference=None,
            extra={"wallet_provider": "Airtel Money"},
        ),
        PaymentResponse(
            id="cp_1",
            status="awaiting_confirmation",
            type="crypto",
            amount=100.0,
            currency="USD",
            timestamp=datetime.utcnow().isoformat(),
            reference=None,
            extra={"cryptocurrency": "Ethereum", "wallet_address": "0x742d..."},
        ),
    ]
    for p in sample_payments:
        await store.add_payment(p)
    logger.info("Seeded sample payment history")


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
```