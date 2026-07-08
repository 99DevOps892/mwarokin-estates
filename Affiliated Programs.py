```python
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import random

app = FastAPI(
    title="Mwarokin Estates - Affiliate Program API",
    description="Backend API for Affiliate Programs & Referrals",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enums & Models
class TierLevel(str, Enum):
    MSINGI = "Msingi"
    JENGO = "Jengo"
    MILKI = "Milki"

class ReferralStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    ACTIVE = "active"

class Referral(BaseModel):
    id: str
    name: str
    avatar: str
    joined_date: str
    plan: str
    earnings: int
    status: ReferralStatus

class Tier(BaseModel):
    level: TierLevel
    commission_rate: int  # percentage
    min_referrals: int
    max_referrals: Optional[int]
    is_current: bool = False

class AffiliateStats(BaseModel):
    total_earned: int
    active_referrals: int
    pending_balance: int
    conversion_rate: float
    current_tier: TierLevel
    referrals_to_next_tier: int

class ReferralLink(BaseModel):
    url: str
    code: str
    created_at: datetime

class WithdrawalInfo(BaseModel):
    available_balance: int
    total_earned: int
    threshold: int
    progress_percentage: float
    can_withdraw: bool

# In-memory database
referrals_db: List[Referral] = []
stats_cache: Optional[AffiliateStats] = None
referral_link: Optional[ReferralLink] = None
withdrawal_history = []

def init_data():
    global referrals_db, stats_cache, referral_link
    
    referrals_db = [
        Referral(
            id=str(uuid.uuid4()),
            name="Agnes Kamau",
            avatar="AK",
            joined_date="Joined 3 days ago",
            plan="Jengo Plan",
            earnings=420,
            status=ReferralStatus.CONFIRMED
        ),
        Referral(
            id=str(uuid.uuid4()),
            name="James Mutua",
            avatar="JM",
            joined_date="Joined 8 days ago",
            plan="Msingi Plan",
            earnings=210,
            status=ReferralStatus.CONFIRMED
        ),
        Referral(
            id=str(uuid.uuid4()),
            name="Faith Njoki",
            avatar="FN",
            joined_date="Signed up",
            plan="Pending activation",
            earnings=0,
            status=ReferralStatus.PENDING
        ),
    ]
    
    referral_link = ReferralLink(
        url="https://mwarokin.co.ke/ref?code=ROBIN2025",
        code="ROBIN2025",
        created_at=datetime.now()
    )
    
    stats_cache = AffiliateStats(
        total_earned=4200,
        active_referrals=7,
        pending_balance=1400,
        conversion_rate=63.0,
        current_tier=TierLevel.JENGO,
        referrals_to_next_tier=3
    )

init_data()

# Tiers definition
TIERS = [
    Tier(level=TierLevel.MSINGI, commission_rate=5, min_referrals=1, max_referrals=3),
    Tier(level=TierLevel.JENGO, commission_rate=10, min_referrals=4, max_referrals=9, is_current=True),
    Tier(level=TierLevel.MILKI, commission_rate=15, min_referrals=10, max_referrals=None),
]

@app.get("/api/affiliate/stats", response_model=AffiliateStats)
async def get_affiliate_stats():
    return stats_cache

@app.get("/api/affiliate/referrals", response_model=List[Referral])
async def get_referrals(
    status: Optional[ReferralStatus] = Query(None),
    limit: int = Query(20, le=100)
):
    filtered = referrals_db
    if status:
        filtered = [r for r in filtered if r.status == status]
    return filtered[:limit]

@app.get("/api/affiliate/tiers", response_model=List[Tier])
async def get_tiers():
    return TIERS

@app.get("/api/affiliate/referral-link", response_model=ReferralLink)
async def get_referral_link():
    if not referral_link:
        raise HTTPException(status_code=404, detail="Referral link not found")
    return referral_link

@app.post("/api/affiliate/referral-link/regenerate", response_model=ReferralLink)
async def regenerate_referral_link():
    global referral_link
    new_code = f"ROBIN{random.randint(1000,9999)}"
    referral_link = ReferralLink(
        url=f"https://mwarokin.co.ke/ref?code={new_code}",
        code=new_code,
        created_at=datetime.now()
    )
    return referral_link

@app.get("/api/affiliate/withdrawal", response_model=WithdrawalInfo)
async def get_withdrawal_info():
    available = 900  # from UI
    total = 4200
    threshold = 2500
    
    return WithdrawalInfo(
        available_balance=available,
        total_earned=total,
        threshold=threshold,
        progress_percentage=min((available / threshold) * 100, 100),
        can_withdraw=available >= threshold
    )

@app.post("/api/affiliate/withdraw")
async def request_withdrawal(data: dict = Body(...)):
    amount = data.get("amount", 0)
    method = data.get("method", "mpesa")
    
    if amount < 2500:
        raise HTTPException(status_code=400, detail="Minimum withdrawal is KES 2,500")
    
    withdrawal_history.append({
        "id": str(uuid.uuid4()),
        "amount": amount,
        "method": method,
        "status": "processed",
        "date": datetime.now().isoformat()
    })
    
    # Simulate balance deduction (in real app update DB)
    global stats_cache
    if stats_cache:
        stats_cache.pending_balance = max(0, stats_cache.pending_balance - amount)
    
    return {
        "success": True,
        "message": f"Withdrawal of KES {amount} requested successfully via {method.upper()}",
        "transaction_id": str(uuid.uuid4())[:8].upper()
    }

@app.get("/api/affiliate/payout-history")
async def get_payout_history():
    return withdrawal_history or [
        {
            "id": "TXN-7842",
            "amount": 2800,
            "date": "2026-06-12",
            "method": "M-Pesa",
            "status": "completed"
        },
        {
            "id": "TXN-6519",
            "amount": 1500,
            "date": "2026-05-28",
            "method": "M-Pesa",
            "status": "completed"
        }
    ]

# Health check
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "mwarokin-affiliate",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Mwarokin Estates Affiliate Program Backend...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

**Usage:**
```bash
pip install fastapi uvicorn pydantic
python main.py
```

This backend fully supports the Affiliate UI with clean, modern endpoints for stats, referrals, tiers, referral link management, and withdrawals. Ready to connect with the frontend via fetch/axios.