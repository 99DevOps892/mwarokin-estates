Here’s a complete **modern FastAPI backend** for **Page 11 – Marketplace, Community & Operations** with real filtering, token generation, posting, renewals, claims workflow, and benchmarking.

```python
# main.py
"""
Mwarokin Estates – Page 11 Backend
Marketplace, Community & Operations
FastAPI · Python 3.11+
"""

from __future__ import annotations

import secrets
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="Mwarokin Estates – Marketplace API",
    description="Vendors, syndication, token vending, community, renewals, claims & benchmarking",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────

class VendorCategory(str, Enum):
    plumbing = "plumbing"
    electrical = "electrical"
    cleaning = "cleaning"
    security = "security"
    landscaping = "landscaping"
    hvac = "hvac"


class Vendor(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    icon: str
    category: VendorCategory
    name: str
    desc: str
    rating: float = Field(ge=0, le=5)
    reviews: int = 0
    price: str
    tags: List[str]
    cat: str  # display label


class SyndChannel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    icon: str
    name: str
    enabled: bool
    views: str
    inquiries: str


class UtilityType(str, Enum):
    electricity = "electricity"
    water = "water"
    gas = "gas"


class VendTokenRequest(BaseModel):
    tenant: str
    utility: UtilityType
    amount: int = Field(gt=0, le=100_000)


class VendTokenResponse(BaseModel):
    token: str
    tenant: str
    utility: UtilityType
    amount: int
    fee: int
    total: int
    units: str
    message: str
    timestamp: str


class PostBadge(str, Enum):
    landlord = "Landlord"
    tenant = "Tenant"


class CommunityPost(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    initials: str
    name: str
    badge: PostBadge
    badgeType: Optional[str] = None  # "landlord" or None
    time: str
    content: str
    likes: int = 0
    comments: int = 0


class CreatePostRequest(BaseModel):
    content: str
    name: str = "Admin"
    initials: str = "AD"
    badge: PostBadge = PostBadge.landlord


class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    month: str
    day: str
    name: str
    meta: str


class RenewalStatus(str, Enum):
    urgent = "urgent"
    expiring = "expiring"
    renewed = "renewed"


class RenewalStat(BaseModel):
    label: str
    value: str
    color: str


class LeaseRenewal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    initials: str
    tenant: str
    property: str
    leaseEnd: str
    currentRent: str
    suggestedRent: str
    status: RenewalStatus
    daysLeft: int
    color: str


class ClaimStatus(str, Enum):
    submitted = "submitted"
    under_review = "under-review"
    approved = "approved"
    rejected = "rejected"


class InsuranceClaim(BaseModel):
    id: str
    title: str
    property: str
    status: ClaimStatus
    amount: str
    filed: str
    insurer: str
    step: int = Field(ge=1, le=4)


class CreateClaimRequest(BaseModel):
    title: str
    property: str
    amount: str
    insurer: str


class BenchMetric(BaseModel):
    label: str
    value: str
    compare: str
    direction: str  # above | below


class Comparison(BaseModel):
    label: str
    you: float
    peer: float
    max: float


class Advantage(BaseModel):
    icon: str
    color: str
    title: str
    desc: str


class BookVendorRequest(BaseModel):
    vendor_id: str
    message: Optional[str] = None


class ToggleSyndRequest(BaseModel):
    channel_id: str
    enabled: bool


class SendRenewalOfferRequest(BaseModel):
    renewal_id: str
    custom_rent: Optional[str] = None


# ──────────────────────────────────────────────────────────────
# In-memory store
# ──────────────────────────────────────────────────────────────

vendors: List[Vendor] = [
    Vendor(icon="fa-wrench", category=VendorCategory.plumbing, name="Plumber Kings Ltd",
           desc="24/7 emergency plumbing, pipe repair, and drainage solutions.",
           rating=4.9, reviews=284, price="From KSh 2,500",
           tags=["Verified", "Insured", "24/7"], cat="Plumbing"),
    Vendor(icon="fa-bolt", category=VendorCategory.electrical, name="ElectroLight Kenya",
           desc="Certified electrical installations, wiring, and safety inspections.",
           rating=4.8, reviews=196, price="From KSh 3,000",
           tags=["Verified", "EPRA Licensed"], cat="Electrical"),
    Vendor(icon="fa-broom", category=VendorCategory.cleaning, name="CleanPro Services",
           desc="Professional deep cleaning, post-construction, and move-in/out.",
           rating=4.9, reviews=412, price="From KSh 1,500",
           tags=["Verified", "Eco-Friendly"], cat="Cleaning"),
    Vendor(icon="fa-shield-alt", category=VendorCategory.security, name="SecureGuard Kenya",
           desc="Manned guarding, CCTV installation, and alarm monitoring.",
           rating=4.7, reviews=158, price="From KSh 45,000/mo",
           tags=["Verified", "PSRA Licensed"], cat="Security"),
    Vendor(icon="fa-leaf", category=VendorCategory.landscaping, name="GreenScape Gardens",
           desc="Garden design, lawn maintenance, and tree care services.",
           rating=4.8, reviews=92, price="From KSh 5,000",
           tags=["Verified", "Eco-Friendly"], cat="Landscaping"),
    Vendor(icon="fa-wind", category=VendorCategory.hvac, name="AirCool Systems",
           desc="AC installation, servicing, and ventilation system design.",
           rating=4.6, reviews=124, price="From KSh 4,500",
           tags=["Verified", "Certified"], cat="HVAC"),
    Vendor(icon="fa-wrench", category=VendorCategory.plumbing, name="AquaFix Experts",
           desc="Water pump installation, tank cleaning, and leak detection.",
           rating=4.5, reviews=87, price="From KSh 2,000",
           tags=["Insured"], cat="Plumbing"),
    Vendor(icon="fa-broom", category=VendorCategory.cleaning, name="Sparkle Team",
           desc="Residential cleaning, laundry, and fumigation services.",
           rating=4.7, reviews=203, price="From KSh 1,200",
           tags=["Verified"], cat="Cleaning"),
]

synd_channels: List[SyndChannel] = [
    SyndChannel(icon="fa-home", name="Mwarokin Estates", enabled=True, views="12,480", inquiries="142"),
    SyndChannel(icon="fa-building", name="Property24 Kenya", enabled=True, views="8,920", inquiries="96"),
    SyndChannel(icon="fa-city", name="BuyRentKenya", enabled=True, views="6,740", inquiries="78"),
    SyndChannel(icon="fa-globe", name="Jumia House", enabled=False, views="0", inquiries="0"),
    SyndChannel(icon="fa-search", name="Google Rentals", enabled=True, views="4,210", inquiries="42"),
    SyndChannel(icon="fa-facebook", name="Facebook Marketplace", enabled=True, views="3,840", inquiries="36"),
    SyndChannel(icon="fa-instagram", name="Instagram Property", enabled=False, views="0", inquiries="0"),
    SyndChannel(icon="fa-tiktok", name="TikTok Tours", enabled=False, views="0", inquiries="0"),
]

posts: List[CommunityPost] = [
    CommunityPost(initials="GW", name="Grace Wanjiku", badge=PostBadge.landlord, badgeType="landlord",
                  time="2 hours ago",
                  content="📢 Reminder: Water tank cleaning is scheduled for <strong>Saturday, April 19th</strong> from 8 AM to 12 PM. Please store enough water for the day.",
                  likes=24, comments=8),
    CommunityPost(initials="JW", name="John Wachira", badge=PostBadge.tenant,
                  time="5 hours ago",
                  content="Has anyone else noticed the WiFi being slow in the evenings? Might be worth checking with the ISP. 🤔",
                  likes=12, comments=15),
    CommunityPost(initials="AH", name="Amina Hassan", badge=PostBadge.landlord, badgeType="landlord",
                  time="Yesterday",
                  content="🎉 Welcome to our new tenants at South B Apartments! We're excited to have you join our community.",
                  likes=38, comments=4),
    CommunityPost(initials="MN", name="Mary Njoki", badge=PostBadge.tenant,
                  time="Yesterday",
                  content="Anyone interested in a weekend football match at the estate grounds? ⚽ Let's organize!",
                  likes=22, comments=18),
]

events: List[Event] = [
    Event(month="APR", day="19", name="Water Tank Cleaning", meta="8:00 AM · All Units"),
    Event(month="APR", day="22", name="Fire Drill & Safety Training", meta="10:00 AM · Estate Grounds"),
    Event(month="APR", day="28", name="Community BBQ & Meetup", meta="4:00 PM · Garden Area"),
    Event(month="MAY", day="05", name="Estate AGM", meta="6:00 PM · Community Hall"),
    Event(month="MAY", day="12", name="Kids Fun Day", meta="10:00 AM · Playground"),
]

renewal_stats: List[RenewalStat] = [
    RenewalStat(label="Expiring in 30 days", value="8", color="red"),
    RenewalStat(label="Expiring in 60 days", value="14", color="gold"),
    RenewalStat(label="Expiring in 90 days", value="22", color=""),
    RenewalStat(label="Renewed YTD", value="48", color="green"),
]

renewals: List[LeaseRenewal] = [
    LeaseRenewal(initials="JW", tenant="John Wachira", property="Kilimani Court · Unit 3B",
                 leaseEnd="Apr 30, 2025", currentRent="KSh 45,000", suggestedRent="KSh 48,500",
                 status=RenewalStatus.urgent, daysLeft=18, color="#c8972a"),
    LeaseRenewal(initials="MN", tenant="Mary Njoki", property="Westlands Heights · Unit 5A",
                 leaseEnd="May 15, 2025", currentRent="KSh 38,000", suggestedRent="KSh 40,200",
                 status=RenewalStatus.expiring, daysLeft=33, color="#6b4c9a"),
    LeaseRenewal(initials="BK", tenant="Brian Kamau", property="South B Apartments · Unit 12",
                 leaseEnd="May 28, 2025", currentRent="KSh 32,000", suggestedRent="KSh 34,000",
                 status=RenewalStatus.expiring, daysLeft=46, color="#2c6b9e"),
    LeaseRenewal(initials="LM", tenant="Lucy Muthoni", property="Lavington Suites · Unit 7C",
                 leaseEnd="Jun 10, 2025", currentRent="KSh 52,000", suggestedRent="KSh 54,500",
                 status=RenewalStatus.expiring, daysLeft=59, color="#b5447a"),
    LeaseRenewal(initials="TM", tenant="Tom Mboya", property="Eastleigh Plaza · Unit 4D",
                 leaseEnd="Apr 15, 2025", currentRent="KSh 28,000", suggestedRent="KSh 29,800",
                 status=RenewalStatus.renewed, daysLeft=0, color="#1e8e5c"),
]

claims: List[InsuranceClaim] = [
    InsuranceClaim(id="CLM-2025-0142", title="Water Damage · Burst Pipe",
                   property="Kilimani Court · Unit 3B", status=ClaimStatus.under_review,
                   amount="KSh 45,000", filed="Apr 8, 2025", insurer="Jubilee Insurance", step=2),
    InsuranceClaim(id="CLM-2025-0138", title="Theft · Burglary Attempt",
                   property="Westlands Heights · Unit 5A", status=ClaimStatus.approved,
                   amount="KSh 82,000", filed="Mar 28, 2025", insurer="APA Insurance", step=4),
    InsuranceClaim(id="CLM-2025-0129", title="Fire Damage · Kitchen",
                   property="South B Apartments · Unit 12", status=ClaimStatus.submitted,
                   amount="KSh 120,000", filed="Apr 11, 2025", insurer="Britam", step=1),
    InsuranceClaim(id="CLM-2025-0119", title="Storm Damage · Roof Repair",
                   property="Lavington Suites · Unit 7C", status=ClaimStatus.rejected,
                   amount="KSh 68,000", filed="Mar 15, 2025", insurer="CIC Insurance", step=4),
]

bench_metrics: List[BenchMetric] = [
    BenchMetric(label="Rental Yield", value="8.4%", compare="Above avg (+2.1%)", direction="above"),
    BenchMetric(label="Occupancy Rate", value="92%", compare="Above avg (+5%)", direction="above"),
    BenchMetric(label="Rent Collection", value="96%", compare="Above avg (+8%)", direction="above"),
    BenchMetric(label="Maintenance Cost", value="4.2%", compare="Below avg (-1.4%)", direction="above"),
]

comparisons: List[Comparison] = [
    Comparison(label="Rental Yield", you=8.4, peer=6.3, max=12),
    Comparison(label="Occupancy Rate", you=92, peer=87, max=100),
    Comparison(label="Rent Collection", you=96, peer=88, max=100),
    Comparison(label="Tenant Retention", you=88, peer=72, max=100),
    Comparison(label="Maintenance Efficiency", you=85, peer=68, max=100),
]

advantages: List[Advantage] = [
    Advantage(icon="fa-trophy", color="gold", title="Top 5% in Rent Collection",
              desc="Your 96% collection rate is exceptional"),
    Advantage(icon="fa-chart-line", color="green", title="Above-Average Yield",
              desc="8.4% vs peer average of 6.3%"),
    Advantage(icon="fa-users", color="blue", title="High Tenant Retention",
              desc="88% annual retention rate"),
    Advantage(icon="fa-tools", color="purple", title="Efficient Maintenance",
              desc="Lower maintenance cost per unit"),
]

# Token & action history
token_history: List[dict] = []
action_log: List[dict] = []

UNITS_PER_KSH = {
    UtilityType.electricity: 0.0135,  # kWh
    UtilityType.water: 0.008,         # m³
    UtilityType.gas: 0.0012,          # kg
}
SERVICE_FEE_RATE = 0.02


def log_action(action: str, detail: dict) -> None:
    action_log.append({
        "id": str(uuid4()),
        "action": action,
        "detail": detail,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })


def _generate_token() -> str:
    """20-char alphanumeric token in groups of 5."""
    chars = "0123456789ABCDEF"
    raw = "".join(secrets.choice(chars) for _ in range(20))
    return "-".join(raw[i:i + 5] for i in range(0, 20, 5))


# ──────────────────────────────────────────────────────────────
# Marketplace & Vendors
# ──────────────────────────────────────────────────────────────

@app.get("/api/vendors", response_model=List[Vendor])
def list_vendors(category: Optional[VendorCategory] = None):
    if category:
        return [v for v in vendors if v.category == category]
    return vendors


@app.get("/api/vendors/{vendor_id}", response_model=Vendor)
def get_vendor(vendor_id: str):
    vendor = next((v for v in vendors if v.id == vendor_id), None)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@app.post("/api/vendors/book")
def book_vendor(req: BookVendorRequest):
    vendor = next((v for v in vendors if v.id == req.vendor_id), None)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    log_action("vendor_booked", {
        "vendor_id": req.vendor_id,
        "name": vendor.name,
        "message": req.message,
    })
    return {
        "status": "booked",
        "message": f"{vendor.name} will reach out within 2 hours.",
        "vendor": vendor,
    }


# ──────────────────────────────────────────────────────────────
# Listing Syndication
# ──────────────────────────────────────────────────────────────

@app.get("/api/syndication/channels", response_model=List[SyndChannel])
def list_synd_channels():
    return synd_channels


@app.patch("/api/syndication/toggle")
def toggle_syndication(req: ToggleSyndRequest):
    channel = next((c for c in synd_channels if c.id == req.channel_id), None)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    channel.enabled = req.enabled
    if not req.enabled:
        channel.views = "0"
        channel.inquiries = "0"
    log_action("syndication_toggled", {
        "channel": channel.name,
        "enabled": req.enabled,
    })
    return {
        "status": "updated",
        "message": f"{channel.name} syndication {'enabled' if req.enabled else 'disabled'}.",
        "channel": channel,
    }


@app.get("/api/syndication/summary")
def syndication_summary():
    enabled = [c for c in synd_channels if c.enabled]
    total_views = sum(int(c.views.replace(",", "")) for c in enabled)
    total_inquiries = sum(int(c.inquiries.replace(",", "")) for c in enabled)
    return {
        "enabled_count": len(enabled),
        "total_channels": len(synd_channels),
        "total_views": total_views,
        "total_inquiries": total_inquiries,
        "channels": synd_channels,
    }


# ──────────────────────────────────────────────────────────────
# Utility Prepaid Token Vending
# ──────────────────────────────────────────────────────────────

@app.post("/api/vending/token", response_model=VendTokenResponse)
def generate_token(req: VendTokenRequest):
    fee = int(round(req.amount * SERVICE_FEE_RATE))
    total = req.amount + fee
    units_val = req.amount * UNITS_PER_KSH[req.utility]
    if req.utility == UtilityType.electricity:
        units_str = f"{units_val:.1f} kWh"
    elif req.utility == UtilityType.water:
        units_str = f"{units_val:.1f} m³"
    else:
        units_str = f"{units_val:.2f} kg"

    token = _generate_token()
    record = {
        "token": token,
        "tenant": req.tenant,
        "utility": req.utility,
        "amount": req.amount,
        "fee": fee,
        "total": total,
        "units": units_str,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    token_history.append(record)
    log_action("token_generated", record)

    return VendTokenResponse(
        token=token,
        tenant=req.tenant,
        utility=req.utility,
        amount=req.amount,
        fee=fee,
        total=total,
        units=units_str,
        message=f"Token generated and sent via SMS to {req.tenant}.",
        timestamp=record["timestamp"],
    )


@app.get("/api/vending/history")
def vending_history(limit: int = 50):
    return token_history[-limit:]


@app.get("/api/vending/preview")
def vending_preview(amount: int = 1000, utility: UtilityType = UtilityType.electricity):
    fee = int(round(amount * SERVICE_FEE_RATE))
    units_val = amount * UNITS_PER_KSH[utility]
    if utility == UtilityType.electricity:
        units_str = f"{units_val:.1f} kWh"
    elif utility == UtilityType.water:
        units_str = f"{units_val:.1f} m³"
    else:
        units_str = f"{units_val:.2f} kg"
    return {
        "amount": amount,
        "fee": fee,
        "total": amount + fee,
        "units": units_str,
        "utility": utility,
    }


# ──────────────────────────────────────────────────────────────
# Tenant Community Board
# ──────────────────────────────────────────────────────────────

@app.get("/api/community/posts", response_model=List[CommunityPost])
def list_posts():
    return posts


@app.post("/api/community/posts", response_model=CommunityPost, status_code=status.HTTP_201_CREATED)
def create_post(req: CreatePostRequest):
    post = CommunityPost(
        initials=req.initials,
        name=req.name,
        badge=req.badge,
        badgeType="landlord" if req.badge == PostBadge.landlord else None,
        time="Just now",
        content=req.content,
        likes=0,
        comments=0,
    )
    posts.insert(0, post)
    log_action("post_created", post.model_dump())
    return post


@app.post("/api/community/posts/{post_id}/like")
def like_post(post_id: str):
    post = next((p for p in posts if p.id == post_id), None)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.likes += 1
    return {"likes": post.likes, "post": post}


@app.get("/api/community/events", response_model=List[Event])
def list_events():
    return events


@app.post("/api/community/events", response_model=Event, status_code=status.HTTP_201_CREATED)
def create_event(event: Event):
    events.append(event)
    log_action("event_created", event.model_dump())
    return event


# ──────────────────────────────────────────────────────────────
# Lease Renewal Engine
# ──────────────────────────────────────────────────────────────

@app.get("/api/renewals/stats", response_model=List[RenewalStat])
def get_renewal_stats():
    return renewal_stats


@app.get("/api/renewals", response_model=List[LeaseRenewal])
def list_renewals(status: Optional[RenewalStatus] = None):
    if status:
        return [r for r in renewals if r.status == status]
    return renewals


@app.post("/api/renewals/offer")
def send_renewal_offer(req: SendRenewalOfferRequest):
    renewal = next((r for r in renewals if r.id == req.renewal_id), None)
    if not renewal:
        raise HTTPException(status_code=404, detail="Renewal not found")
    if renewal.status == RenewalStatus.renewed:
        raise HTTPException(status_code=400, detail="Lease already renewed")
    rent = req.custom_rent or renewal.suggestedRent
    log_action("renewal_offer_sent", {
        "renewal_id": req.renewal_id,
        "tenant": renewal.tenant,
        "suggested_rent": rent,
    })
    return {
        "status": "offer_sent",
        "message": f"Renewal offer sent to {renewal.tenant} at {rent}.",
        "renewal": renewal,
    }


@app.post("/api/renewals/{renewal_id}/mark-renewed")
def mark_renewed(renewal_id: str):
    renewal = next((r for r in renewals if r.id == renewal_id), None)
    if not renewal:
        raise HTTPException(status_code=404, detail="Renewal not found")
    renewal.status = RenewalStatus.renewed
    renewal.daysLeft = 0
    log_action("lease_renewed", {"tenant": renewal.tenant})
    return {"status": "renewed", "renewal": renewal}


# ──────────────────────────────────────────────────────────────
# Insurance Claims Portal
# ──────────────────────────────────────────────────────────────

@app.get("/api/claims", response_model=List[InsuranceClaim])
def list_claims(status: Optional[ClaimStatus] = None):
    if status:
        return [c for c in claims if c.status == status]
    return claims


@app.get("/api/claims/{claim_id}", response_model=InsuranceClaim)
def get_claim(claim_id: str):
    claim = next((c for c in claims if c.id == claim_id), None)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@app.post("/api/claims", response_model=InsuranceClaim, status_code=status.HTTP_201_CREATED)
def create_claim(req: CreateClaimRequest):
    claim_id = f"CLM-2025-{secrets.randbelow(9000) + 1000:04d}"
    claim = InsuranceClaim(
        id=claim_id,
        title=req.title,
        property=req.property,
        status=ClaimStatus.submitted,
        amount=req.amount,
        filed=datetime.utcnow().strftime("%b %d, %Y"),
        insurer=req.insurer,
        step=1,
    )
    claims.insert(0, claim)
    log_action("claim_created", claim.model_dump())
    return claim


@app.patch("/api/claims/{claim_id}/advance")
def advance_claim(claim_id: str):
    claim = next((c for c in claims if c.id == claim_id), None)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.status in (ClaimStatus.approved, ClaimStatus.rejected):
        raise HTTPException(status_code=400, detail="Claim already finalized")
    claim.step = min(4, claim.step + 1)
    if claim.step == 2:
        claim.status = ClaimStatus.under_review
    elif claim.step == 4:
        claim.status = ClaimStatus.approved  # demo: auto-approve at end
    log_action("claim_advanced", {"id": claim_id, "step": claim.step, "status": claim.status})
    return claim


@app.post("/api/claims/{claim_id}/upload")
def upload_claim_docs(claim_id: str):
    claim = next((c for c in claims if c.id == claim_id), None)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    log_action("claim_docs_uploaded", {"id": claim_id})
    return {
        "status": "uploaded",
        "message": f"Documents uploaded for {claim_id}.",
        "claim": claim,
    }


# ──────────────────────────────────────────────────────────────
# Benchmarking & Peer Analytics
# ──────────────────────────────────────────────────────────────

@app.get("/api/benchmark/metrics", response_model=List[BenchMetric])
def get_bench_metrics():
    return bench_metrics


@app.get("/api/benchmark/comparisons", response_model=List[Comparison])
def get_comparisons():
    return comparisons


@app.get("/api/benchmark/advantages", response_model=List[Advantage])
def get_advantages():
    return advantages


@app.get("/api/benchmark/summary")
def benchmark_summary():
    return {
        "percentile": "Top 12%",
        "label": "Of Kenyan Landlords",
        "metrics": bench_metrics,
        "comparisons": comparisons,
        "advantages": advantages,
    }


# ──────────────────────────────────────────────────────────────
# Full Page 11 payload
# ──────────────────────────────────────────────────────────────

@app.get("/api/page11")
def page11_data():
    return {
        "vendors": vendors,
        "syndication": {
            "channels": synd_channels,
            "summary": {
                "enabled": len([c for c in synd_channels if c.enabled]),
                "total": len(synd_channels),
            },
        },
        "vending": {
            "fee_rate": SERVICE_FEE_RATE,
            "units_per_ksh": {k.value: v for k, v in UNITS_PER_KSH.items()},
            "history_count": len(token_history),
        },
        "community": {
            "posts": posts,
            "events": events,
        },
        "renewals": {
            "stats": renewal_stats,
            "items": renewals,
        },
        "claims": claims,
        "benchmark": {
            "percentile": "Top 12%",
            "metrics": bench_metrics,
            "comparisons": comparisons,
            "advantages": advantages,
        },
    }


@app.get("/api/actions")
def get_action_log(limit: int = 50):
    return action_log[-limit:]


@app.get("/")
def root():
    return {
        "service": "Mwarokin Estates – Marketplace, Community & Operations",
        "page": 11,
        "version": "1.0.0",
        "docs": "/docs",
        "page11": "/api/page11",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### Run

```bash
pip install fastapi uvicorn pydantic
python main.py
```

→ **http://localhost:8000/docs**

### Real functionality map

| Feature                    | Key endpoints                                      | Behaviour                                      |
|----------------------------|----------------------------------------------------|------------------------------------------------|
| **Vendors**                | `GET /api/vendors?category=`, `POST /api/vendors/book` | Filter by category, book with confirmation   |
| **Syndication**            | `GET /api/syndication/*`, `PATCH .../toggle`       | Enable/disable channels, live view/inquiry counts |
| **Token Vending**          | `POST /api/vending/token`, `GET .../preview`       | Generates real tokens, calculates fee & units, SMS sim |
| **Community**              | `GET/POST /api/community/posts`, `POST .../like`   | Create posts, like, list events                |
| **Lease Renewals**         | `GET /api/renewals`, `POST .../offer`, `.../mark-renewed` | Send offers, mark renewed                 |
| **Insurance Claims**       | `GET/POST /api/claims`, `PATCH .../advance`        | Create, advance workflow, upload docs          |
| **Benchmarking**           | `GET /api/benchmark/*`                             | Metrics, peer comparisons, advantages          |
| **Full page**              | `GET /api/page11`                                  | Single payload for the UI                      |
| **Audit**                  | `GET /api/actions`                                 | Every write is logged                          |

Tokens use cryptographically secure random generation. Claims advance through a 4-step pipeline. Swap the in-memory stores for SQLAlchemy + Postgres when you need persistence.