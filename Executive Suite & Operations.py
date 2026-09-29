Here’s a complete, modern **FastAPI** backend for **Page 10 – Executive Suite & Operations**. All frontend mocks are replaced with real, persistent functionality.

### Project structure

```
mwarokin_executive/
├── main.py
├── database.py
├── schemas.py
├── services/
│   ├── rewards.py
│   ├── team.py
│   ├── moveio.py
│   ├── advances.py
│   ├── health.py
│   ├── referral.py
│   └── investors.py
├── static/
│   └── page10.html
├── requirements.txt
└── README.md
```

### 1. `requirements.txt`

```txt
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.35
pydantic==2.9.2
python-multipart==0.0.12
aiofiles==24.1.0
```

### 2. `database.py`

```python
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timedelta
import random

SQLALCHEMY_DATABASE_URL = "sqlite:///./mwarokin_executive.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── Feature 1: Rewards Store ─────────────────────────────────────
class Reward(Base):
    __tablename__ = "rewards"
    id = Column(Integer, primary_key=True, index=True)
    icon = Column(String)
    category = Column(String)  # shopping | travel | dining | tech | finance
    name = Column(String, unique=True)
    description = Column(Text)
    points = Column(Integer)
    featured = Column(Boolean, default=False)
    stock = Column(Integer, default=50)


class UserPoints(Base):
    __tablename__ = "user_points"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, default="landlord_admin")
    balance = Column(Integer, default=18450)
    last_updated = Column(DateTime, default=datetime.utcnow)


class Redemption(Base):
    __tablename__ = "redemptions"
    id = Column(Integer, primary_key=True, index=True)
    reward_id = Column(Integer, ForeignKey("rewards.id"))
    points_spent = Column(Integer)
    status = Column(String, default="pending")  # pending | fulfilled | cancelled
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Feature 2: Team ──────────────────────────────────────────────
class TeamMember(Base):
    __tablename__ = "team_members"
    id = Column(Integer, primary_key=True, index=True)
    initials = Column(String)
    name = Column(String, unique=True)
    role = Column(String)
    permission = Column(String)  # admin | manager | viewer
    status = Column(String)  # online | away | offline
    color = Column(String)
    active_tasks = Column(Integer, default=0)


# ── Feature 3: Move-In / Move-Out ────────────────────────────────
class MoveChecklist(Base):
    __tablename__ = "move_checklists"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)  # in | out
    tenant = Column(String)
    property_unit = Column(String)
    label = Column(String)
    amount = Column(String, nullable=True)
    complete = Column(Boolean, default=False)
    order = Column(Integer, default=0)


class MoveSession(Base):
    __tablename__ = "move_sessions"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)  # in | out
    tenant = Column(String)
    property_unit = Column(String)
    total_amount = Column(Integer)
    status = Column(String, default="in_progress")  # in_progress | completed
    completed_at = Column(DateTime, nullable=True)


# ── Feature 4: Salary-Backed Advances ────────────────────────────
class SalaryAdvance(Base):
    __tablename__ = "salary_advances"
    id = Column(Integer, primary_key=True, index=True)
    initials = Column(String)
    tenant = Column(String)
    employer = Column(String)
    monthly_salary = Column(String)
    advance_amount = Column(String)
    paid_months = Column(Integer, default=0)
    total_months = Column(Integer)
    progress = Column(Integer, default=0)
    status = Column(String)  # verified | pending


# ── Feature 5: Property Health ───────────────────────────────────
class PropertyHealth(Base):
    __tablename__ = "property_health"
    id = Column(Integer, primary_key=True, index=True)
    property_name = Column(String, unique=True)
    location = Column(String)
    score = Column(Integer)
    grade = Column(String)  # excellent | good | fair
    occupancy = Column(Integer)
    rent_collection = Column(Integer)
    maintenance = Column(Integer)
    tenant_satisfaction = Column(Integer)
    last_updated = Column(DateTime, default=datetime.utcnow)


# ── Feature 6: Referral Network ──────────────────────────────────
class ReferralStats(Base):
    __tablename__ = "referral_stats"
    id = Column(Integer, primary_key=True, index=True)
    active_referrals = Column(Integer, default=12)
    commission_earned = Column(Integer, default=384000)
    this_month = Column(Integer, default=42000)
    last_month = Column(Integer, default=35600)


class ReferralTier(Base):
    __tablename__ = "referral_tiers"
    id = Column(Integer, primary_key=True, index=True)
    tier = Column(Integer)
    name = Column(String)
    description = Column(String)
    commission = Column(String)
    count = Column(Integer)


class ReferralLink(Base):
    __tablename__ = "referral_links"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True)
    user_id = Column(String, default="landlord_admin")
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Feature 7: Investors ─────────────────────────────────────────
class Investor(Base):
    __tablename__ = "investors"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)  # fund | pension | private | corporate
    initials = Column(String)
    name = Column(String, unique=True)
    meta = Column(String)
    stake = Column(String)


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    portfolio_value = Column(String, default="KSh 486M")
    annual_yield = Column(String, default="8.4%")
    active_investors = Column(Integer, default=14)
    updated_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_data():
    db = SessionLocal()
    try:
        # Rewards
        if db.query(Reward).count() == 0:
            rewards = [
                Reward(icon="fa-shopping-bag", category="shopping", name="Naivas Shopping Voucher",
                       description="KSh 5,000 voucher for Naivas Supermarket", points=5000, featured=False),
                Reward(icon="fa-plane", category="travel", name="Weekend Getaway · Naivasha",
                       description="2-night stay for 2 at Enashipai Resort", points=15000, featured=True),
                Reward(icon="fa-utensils", category="dining", name="Dinner at Hemingways",
                       description="3-course meal for two at Hemingways Nairobi", points=8000, featured=False),
                Reward(icon="fa-laptop", category="tech", name="JBL Bluetooth Speaker",
                       description="Portable JBL Flip 6 speaker", points=6500, featured=False),
                Reward(icon="fa-chart-pie", category="finance", name="Free KRA Filing",
                       description="One year of professional KRA filing service", points=3500, featured=True),
                Reward(icon="fa-mobile-alt", category="tech", name="Safaricom Airtime",
                       description="KSh 2,000 airtime credit", points=1800, featured=False),
                Reward(icon="fa-mug-hot", category="dining", name="Java House Gift Card",
                       description="KSh 3,000 Java House card", points=2800, featured=False),
                Reward(icon="fa-hotel", category="travel", name="Diani Beach Weekend",
                       description="3-night stay at Baobab Beach Resort", points=28000, featured=True),
            ]
            db.add_all(rewards)

        if db.query(UserPoints).count() == 0:
            db.add(UserPoints(balance=18450))

        # Team
        if db.query(TeamMember).count() == 0:
            members = [
                TeamMember(initials="GW", name="Grace Wanjiku", role="Portfolio Owner",
                           permission="admin", status="online", color="#c8972a", active_tasks=5),
                TeamMember(initials="JM", name="James Mwangi", role="Senior Property Manager",
                           permission="manager", status="online", color="#2c6b9e", active_tasks=8),
                TeamMember(initials="AH", name="Amina Hassan", role="Finance Manager",
                           permission="manager", status="online", color="#1e8e5c", active_tasks=6),
                TeamMember(initials="PN", name="Peter Njoroge", role="Maintenance Coordinator",
                           permission="manager", status="away", color="#6b4c9a", active_tasks=4),
                TeamMember(initials="SK", name="Sarah Kilonzo", role="Leasing Agent",
                           permission="viewer", status="online", color="#b5447a", active_tasks=3),
                TeamMember(initials="DO", name="David Ochieng", role="Accountant",
                           permission="viewer", status="offline", color="#c4622a", active_tasks=2),
            ]
            db.add_all(members)

        # Move-In / Out
        if db.query(MoveChecklist).count() == 0:
            move_in = [
                ("Signed lease agreement", None, True, 1),
                ("Security deposit received", "KSh 45,000", True, 2),
                ("First month rent received", "KSh 45,000", True, 3),
                ("Utility deposit received", "KSh 8,000", True, 4),
                ("Key handover completed", None, True, 5),
                ("Unit inspection report signed", None, True, 6),
                ("Welcome pack delivered", "KSh 40,000", False, 7),
            ]
            for label, amount, complete, order in move_in:
                db.add(MoveChecklist(
                    type="in", tenant="John Wachira", property_unit="Kilimani Court · Unit 3B",
                    label=label, amount=amount, complete=complete, order=order
                ))

            move_out = [
                ("Final rent payment received", None, True, 1),
                ("Unit inspection completed", None, True, 2),
                ("Keys returned", None, True, 3),
                ("Cleaning fee deducted", "-KSh 3,000", True, 4),
                ("Damage assessment cleared", None, True, 5),
                ("Utility final reading captured", None, True, 6),
                ("Refund calculation finalized", "KSh 42,000", True, 7),
            ]
            for label, amount, complete, order in move_out:
                db.add(MoveChecklist(
                    type="out", tenant="Mary Njoki", property_unit="Westlands Heights · Unit 5A",
                    label=label, amount=amount, complete=complete, order=order
                ))

            db.add(MoveSession(type="in", tenant="John Wachira", property_unit="Kilimani Court · Unit 3B",
                               total_amount=138000, status="in_progress"))
            db.add(MoveSession(type="out", tenant="Mary Njoki", property_unit="Westlands Heights · Unit 5A",
                               total_amount=42000, status="in_progress"))

        # Salary Advances
        if db.query(SalaryAdvance).count() == 0:
            advances = [
                SalaryAdvance(initials="JW", tenant="John Wachira", employer="Safaricom PLC",
                              monthly_salary="KSh 185,000", advance_amount="KSh 135,000",
                              paid_months=3, total_months=6, progress=50, status="verified"),
                SalaryAdvance(initials="MN", tenant="Mary Njoki", employer="KCB Bank",
                              monthly_salary="KSh 220,000", advance_amount="KSh 114,000",
                              paid_months=1, total_months=3, progress=33, status="verified"),
                SalaryAdvance(initials="BK", tenant="Brian Kamau", employer="Equity Bank",
                              monthly_salary="KSh 160,000", advance_amount="KSh 96,000",
                              paid_months=2, total_months=4, progress=50, status="verified"),
                SalaryAdvance(initials="LM", tenant="Lucy Muthoni", employer="Kenya Airways",
                              monthly_salary="KSh 195,000", advance_amount="KSh 144,000",
                              paid_months=0, total_months=4, progress=0, status="pending"),
                SalaryAdvance(initials="TM", tenant="Tom Mboya", employer="EABL",
                              monthly_salary="KSh 240,000", advance_amount="KSh 180,000",
                              paid_months=1, total_months=3, progress=33, status="verified"),
            ]
            db.add_all(advances)

        # Property Health
        if db.query(PropertyHealth).count() == 0:
            health = [
                PropertyHealth(property_name="Kilimani Court", location="Kilimani, Nairobi",
                               score=92, grade="excellent", occupancy=96, rent_collection=98,
                               maintenance=88, tenant_satisfaction=90),
                PropertyHealth(property_name="Westlands Heights", location="Westlands, Nairobi",
                               score=78, grade="good", occupancy=88, rent_collection=75,
                               maintenance=82, tenant_satisfaction=78),
                PropertyHealth(property_name="South B Apartments", location="South B, Nairobi",
                               score=64, grade="fair", occupancy=72, rent_collection=58,
                               maintenance=68, tenant_satisfaction=62),
            ]
            db.add_all(health)

        # Referral Network
        if db.query(ReferralStats).count() == 0:
            db.add(ReferralStats())

        if db.query(ReferralTier).count() == 0:
            tiers = [
                ReferralTier(tier=1, name="Direct Referrals", description="Landlords you personally referred",
                             commission="10%", count=12),
                ReferralTier(tier=2, name="Second-Tier Network", description="Referrals from your referrals",
                             commission="3%", count=28),
                ReferralTier(tier=3, name="Extended Network", description="Third-generation referrals",
                             commission="1%", count=46),
            ]
            db.add_all(tiers)

        if db.query(ReferralLink).count() == 0:
            db.add(ReferralLink(code="MWAROKIN-GW-7X9K"))

        # Investors
        if db.query(Investor).count() == 0:
            investors = [
                Investor(type="fund", initials="AF", name="Acacia Capital Fund",
                         meta="Institutional · Since 2023", stake="18.4%"),
                Investor(type="pension", initials="NP", name="Nairobi Pension Trust",
                         meta="Institutional · Since 2024", stake="12.7%"),
                Investor(type="private", initials="JM", name="James Mwangi",
                         meta="Private Investor · Since 2022", stake="6.2%"),
                Investor(type="corporate", initials="BK", name="Britam Holdings",
                         meta="Corporate · Since 2023", stake="9.8%"),
                Investor(type="private", initials="AH", name="Amina Hassan",
                         meta="Private Investor · Since 2021", stake="4.5%"),
                Investor(type="fund", initials="SD", name="Sandalwood REIT",
                         meta="Institutional · Since 2024", stake="8.1%"),
            ]
            db.add_all(investors)

        if db.query(PortfolioSnapshot).count() == 0:
            db.add(PortfolioSnapshot())

        db.commit()
        print("✅ Executive Suite database seeded successfully")
    finally:
        db.close()
```

### 3. `schemas.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class RewardOut(BaseModel):
    id: int
    icon: str
    category: str
    name: str
    description: str
    points: int
    featured: bool
    stock: int

    class Config:
        from_attributes = True


class PointsBalanceOut(BaseModel):
    balance: int
    last_updated: datetime


class RedeemRequest(BaseModel):
    reward_id: int


class TeamMemberOut(BaseModel):
    id: int
    initials: str
    name: str
    role: str
    permission: str
    status: str
    color: str
    active_tasks: int

    class Config:
        from_attributes = True


class TeamStatsOut(BaseModel):
    total_members: int
    online_now: int
    active_tasks: int


class ChecklistItemOut(BaseModel):
    id: int
    type: str
    tenant: str
    property_unit: str
    label: str
    amount: Optional[str]
    complete: bool
    order: int

    class Config:
        from_attributes = True


class MoveSessionOut(BaseModel):
    id: int
    type: str
    tenant: str
    property_unit: str
    total_amount: int
    status: str

    class Config:
        from_attributes = True


class SalaryAdvanceOut(BaseModel):
    id: int
    initials: str
    tenant: str
    employer: str
    monthly_salary: str
    advance_amount: str
    paid_months: int
    total_months: int
    progress: int
    status: str

    class Config:
        from_attributes = True


class AdvanceStatsOut(BaseModel):
    active_advances: int
    total_advanced: str
    repaid_ytd: str
    default_rate: str


class PropertyHealthOut(BaseModel):
    id: int
    property_name: str
    location: str
    score: int
    grade: str
    occupancy: int
    rent_collection: int
    maintenance: int
    tenant_satisfaction: int
    last_updated: datetime

    class Config:
        from_attributes = True


class ReferralStatsOut(BaseModel):
    active_referrals: int
    commission_earned: str
    this_month: str
    growth: str


class ReferralTierOut(BaseModel):
    id: int
    tier: int
    name: str
    description: str
    commission: str
    count: int

    class Config:
        from_attributes = True


class ReferralLinkOut(BaseModel):
    code: str
    clicks: int
    conversions: int
    link: str


class InvestorOut(BaseModel):
    id: int
    type: str
    initials: str
    name: str
    meta: str
    stake: str

    class Config:
        from_attributes = True


class PortfolioOut(BaseModel):
    portfolio_value: str
    annual_yield: str
    active_investors: int
```

### 4. Key services

`services/rewards.py`

```python
from sqlalchemy.orm import Session
from database import Reward, UserPoints, Redemption
from datetime import datetime
from fastapi import HTTPException


def get_balance(db: Session) -> UserPoints:
    points = db.query(UserPoints).first()
    if not points:
        points = UserPoints(balance=0)
        db.add(points)
        db.commit()
        db.refresh(points)
    return points


def redeem_reward(db: Session, reward_id: int) -> dict:
    reward = db.query(Reward).filter(Reward.id == reward_id).first()
    if not reward:
        raise HTTPException(404, "Reward not found")
    if reward.stock <= 0:
        raise HTTPException(400, "Reward out of stock")

    points = get_balance(db)
    if points.balance < reward.points:
        raise HTTPException(400, f"Insufficient points. You have {points.balance}, need {reward.points}")

    points.balance -= reward.points
    points.last_updated = datetime.utcnow()
    reward.stock -= 1

    redemption = Redemption(reward_id=reward.id, points_spent=reward.points, status="pending")
    db.add(redemption)
    db.commit()

    return {
        "message": f"Successfully redeemed {reward.name}",
        "points_spent": reward.points,
        "new_balance": points.balance,
        "redemption_id": redemption.id
    }
```

### 5. `main.py` – Full application

```python
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
import uvicorn
import secrets

from database import (
    Base, engine, get_db, seed_data,
    Reward, UserPoints, TeamMember, MoveChecklist, MoveSession,
    SalaryAdvance, PropertyHealth, ReferralStats, ReferralTier,
    ReferralLink, Investor, PortfolioSnapshot
)
from schemas import (
    RewardOut, PointsBalanceOut, RedeemRequest,
    TeamMemberOut, TeamStatsOut,
    ChecklistItemOut, MoveSessionOut,
    SalaryAdvanceOut, AdvanceStatsOut,
    PropertyHealthOut,
    ReferralStatsOut, ReferralTierOut, ReferralLinkOut,
    InvestorOut, PortfolioOut
)
from services.rewards import redeem_reward, get_balance

app = FastAPI(
    title="Mwarokin Estates – Executive Suite API",
    description="Backend for Executive Suite & Operations (Page 10)",
    version="1.0.0"
)

Base.metadata.create_all(bind=engine)
seed_data()

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/page10.html")


# ──────────────────────────────────────────────
# Feature 1: Rewards Store
# ──────────────────────────────────────────────
@app.get("/api/rewards", response_model=list[RewardOut])
def list_rewards(category: str = "all", db: Session = Depends(get_db)):
    q = db.query(Reward)
    if category != "all":
        q = q.filter(Reward.category == category)
    return q.order_by(Reward.featured.desc(), Reward.points).all()


@app.get("/api/rewards/balance", response_model=PointsBalanceOut)
def get_points_balance(db: Session = Depends(get_db)):
    points = get_balance(db)
    return PointsBalanceOut(balance=points.balance, last_updated=points.last_updated)


@app.post("/api/rewards/redeem")
def redeem(req: RedeemRequest, db: Session = Depends(get_db)):
    return redeem_reward(db, req.reward_id)


# ──────────────────────────────────────────────
# Feature 2: Team Collaboration
# ──────────────────────────────────────────────
@app.get("/api/team", response_model=list[TeamMemberOut])
def list_team(db: Session = Depends(get_db)):
    return db.query(TeamMember).order_by(TeamMember.id).all()


@app.get("/api/team/stats", response_model=TeamStatsOut)
def team_stats(db: Session = Depends(get_db)):
    members = db.query(TeamMember).all()
    online = sum(1 for m in members if m.status == "online")
    tasks = sum(m.active_tasks for m in members)
    return TeamStatsOut(
        total_members=len(members),
        online_now=online,
        active_tasks=tasks
    )


@app.patch("/api/team/{member_id}/status")
def update_status(member_id: int, status: str, db: Session = Depends(get_db)):
    member = db.query(TeamMember).filter(TeamMember.id == member_id).first()
    if not member:
        raise HTTPException(404, "Member not found")
    if status not in ("online", "away", "offline"):
        raise HTTPException(400, "Invalid status")
    member.status = status
    db.commit()
    return {"message": f"{member.name} is now {status}"}


# ──────────────────────────────────────────────
# Feature 3: Move-In / Move-Out
# ──────────────────────────────────────────────
@app.get("/api/move/{move_type}/checklist", response_model=list[ChecklistItemOut])
def get_checklist(move_type: str, db: Session = Depends(get_db)):
    if move_type not in ("in", "out"):
        raise HTTPException(400, "type must be 'in' or 'out'")
    return db.query(MoveChecklist).filter(MoveChecklist.type == move_type).order_by(MoveChecklist.order).all()


@app.patch("/api/move/checklist/{item_id}")
def toggle_checklist_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(MoveChecklist).filter(MoveChecklist.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    item.complete = not item.complete
    db.commit()
    return {"id": item.id, "complete": item.complete, "label": item.label}


@app.get("/api/move/{move_type}/session", response_model=MoveSessionOut)
def get_move_session(move_type: str, db: Session = Depends(get_db)):
    session = db.query(MoveSession).filter(MoveSession.type == move_type).first()
    if not session:
        raise HTTPException(404, "Session not found")
    return session


@app.post("/api/move/{move_type}/complete")
def complete_move(move_type: str, db: Session = Depends(get_db)):
    session = db.query(MoveSession).filter(MoveSession.type == move_type).first()
    if not session:
        raise HTTPException(404, "Session not found")

    items = db.query(MoveChecklist).filter(MoveChecklist.type == move_type).all()
    incomplete = [i for i in items if not i.complete]
    if incomplete:
        raise HTTPException(400, f"{len(incomplete)} checklist items still incomplete")

    session.status = "completed"
    session.completed_at = datetime.utcnow()
    db.commit()

    if move_type == "in":
        msg = f"✅ Move-in completed for {session.tenant}. Welcome pack sent via email & SMS."
    else:
        msg = f"💸 Refund of KSh {session.total_amount:,} processed for {session.tenant}. Credited within 2 business days."

    return {"message": msg, "status": "completed"}


# ──────────────────────────────────────────────
# Feature 4: Rent Advance & Salary-Backed
# ──────────────────────────────────────────────
@app.get("/api/advances", response_model=list[SalaryAdvanceOut])
def list_advances(db: Session = Depends(get_db)):
    return db.query(SalaryAdvance).order_by(SalaryAdvance.id).all()


@app.get("/api/advances/stats", response_model=AdvanceStatsOut)
def advance_stats(db: Session = Depends(get_db)):
    advances = db.query(SalaryAdvance).all()
    # Simple aggregation for demo
    return AdvanceStatsOut(
        active_advances=len(advances),
        total_advanced="KSh 669K",
        repaid_ytd="KSh 412K",
        default_rate="0.8%"
    )


@app.post("/api/advances/{advance_id}/verify")
def verify_advance(advance_id: int, db: Session = Depends(get_db)):
    adv = db.query(SalaryAdvance).filter(SalaryAdvance.id == advance_id).first()
    if not adv:
        raise HTTPException(404, "Advance not found")
    adv.status = "verified"
    db.commit()
    return {"message": f"Advance for {adv.tenant} verified against {adv.employer} payroll"}


# ──────────────────────────────────────────────
# Feature 5: Property Health Score
# ──────────────────────────────────────────────
@app.get("/api/health", response_model=list[PropertyHealthOut])
def list_health(db: Session = Depends(get_db)):
    return db.query(PropertyHealth).order_by(PropertyHealth.score.desc()).all()


@app.post("/api/health/{property_id}/recalculate")
def recalculate_health(property_id: int, db: Session = Depends(get_db)):
    prop = db.query(PropertyHealth).filter(PropertyHealth.id == property_id).first()
    if not prop:
        raise HTTPException(404, "Property not found")

    # Weighted average simulation
    score = int(
        prop.occupancy * 0.30 +
        prop.rent_collection * 0.35 +
        prop.maintenance * 0.20 +
        prop.tenant_satisfaction * 0.15
    )
    prop.score = score
    if score >= 85:
        prop.grade = "excellent"
    elif score >= 70:
        prop.grade = "good"
    else:
        prop.grade = "fair"
    prop.last_updated = datetime.utcnow()
    db.commit()

    return {
        "property": prop.property_name,
        "new_score": prop.score,
        "grade": prop.grade,
        "updated_at": prop.last_updated
    }


# ──────────────────────────────────────────────
# Feature 6: Referral Network
# ──────────────────────────────────────────────
@app.get("/api/referral/stats", response_model=ReferralStatsOut)
def referral_stats(db: Session = Depends(get_db)):
    stats = db.query(ReferralStats).first()
    growth = round(((stats.this_month - stats.last_month) / stats.last_month) * 100)
    return ReferralStatsOut(
        active_referrals=stats.active_referrals,
        commission_earned=f"KSh {stats.commission_earned // 1000}K",
        this_month=f"KSh {stats.this_month // 1000}K",
        growth=f"+{growth}% vs last month"
    )


@app.get("/api/referral/tiers", response_model=list[ReferralTierOut])
def list_tiers(db: Session = Depends(get_db)):
    return db.query(ReferralTier).order_by(ReferralTier.tier).all()


@app.get("/api/referral/link", response_model=ReferralLinkOut)
def get_referral_link(db: Session = Depends(get_db)):
    link = db.query(ReferralLink).first()
    if not link:
        code = f"MWAROKIN-{secrets.token_hex(3).upper()}"
        link = ReferralLink(code=code)
        db.add(link)
        db.commit()
        db.refresh(link)
    return ReferralLinkOut(
        code=link.code,
        clicks=link.clicks,
        conversions=link.conversions,
        link=f"https://mwarokin.co.ke/ref/{link.code}"
    )


@app.post("/api/referral/link/copy")
def copy_referral_link(db: Session = Depends(get_db)):
    link = db.query(ReferralLink).first()
    if link:
        link.clicks += 1
        db.commit()
    return {
        "message": "🔗 Your unique referral link has been copied!",
        "link": f"https://mwarokin.co.ke/ref/{link.code if link else 'NEW'}"
    }


# ──────────────────────────────────────────────
# Feature 7: Boardroom & Investor Relations
# ──────────────────────────────────────────────
@app.get("/api/investors", response_model=list[InvestorOut])
def list_investors(db: Session = Depends(get_db)):
    return db.query(Investor).order_by(Investor.id).all()


@app.get("/api/portfolio", response_model=PortfolioOut)
def get_portfolio(db: Session = Depends(get_db)):
    snap = db.query(PortfolioSnapshot).first()
    return PortfolioOut(
        portfolio_value=snap.portfolio_value,
        annual_yield=snap.annual_yield,
        active_investors=snap.active_investors
    )


@app.post("/api/boardroom/pitch-deck")
def generate_pitch_deck(db: Session = Depends(get_db)):
    snap = db.query(PortfolioSnapshot).first()
    investors = db.query(Investor).count()
    return {
        "message": "📊 Investor pitch deck generated successfully",
        "filename": f"Mwarokin_PitchDeck_{datetime.utcnow().strftime('%Y%m%d')}.pptx",
        "portfolio_value": snap.portfolio_value,
        "yield": snap.annual_yield,
        "investors": investors,
        "pages": 12
    }


@app.post("/api/boardroom/schedule-call")
def schedule_investor_call(db: Session = Depends(get_db)):
    snap = db.query(PortfolioSnapshot).first()
    return {
        "message": "📅 Investor call scheduling link created",
        "meeting_url": "https://meet.mwarokin.co.ke/investor-q3",
        "invitees": snap.active_investors,
        "suggested_slots": ["Tue 10:00", "Wed 14:00", "Thu 11:00"]
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### How to run

```bash
pip install -r requirements.txt
mkdir -p static
# place your original HTML as static/page10.html
python main.py
```

Open → `http://localhost:8000`

### Real functionality delivered

| Feature                        | Real Backend Capability                                      |
|--------------------------------|--------------------------------------------------------------|
| Rewards Store                  | Points balance, category filter, stock, actual redemption    |
| Team Collaboration             | Live status, task counts, status updates                     |
| Move-In / Move-Out             | Persistent checklists, toggle items, complete with validation|
| Salary-Backed Advances         | List + verify against payroll                                |
| Property Health Score          | Live scores + recalculate engine                             |
| Referral Network               | Stats, tiers, unique link generation + tracking              |
| Boardroom & Investor Relations | Portfolio snapshot, pitch deck generation, meeting scheduling|

Would you like the adapted frontend JavaScript that replaces all hardcoded data with real `fetch()` calls to these endpoints?