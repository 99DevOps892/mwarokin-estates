Here’s a **modern FastAPI backend** that powers the Mwarokin Estates “Legacy, Wellness & Galactic Rewards” page with real endpoints, Pydantic models, in-memory state (easy to swap for SQLite/Postgres later), and interactive actions.

```python
# main.py
"""
Mwarokin Estates – Page 14 Backend
Legacy, Wellness & Galactic Rewards
Modern FastAPI · Python 3.11+
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="Mwarokin Estates API",
    description="Backend for Legacy, Wellness & Galactic Rewards (Page 14)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────

class HealthStat(BaseModel):
    label: str
    value: str
    sub: str


class WellnessCategory(BaseModel):
    label: str
    score: int = Field(ge=0, le=100)
    color: str


class ScreeningStatus(str, Enum):
    upcoming = "upcoming"
    due = "due"
    complete = "complete"


class Screening(BaseModel):
    icon: str
    type: str
    name: str
    meta: str
    status: ScreeningStatus


class CapsuleMoment(BaseModel):
    year: str
    title: str
    desc: str
    icon: str


class CallType(str, Enum):
    incoming = "incoming"
    outgoing = "outgoing"
    missed = "missed"


class CallLogEntry(BaseModel):
    type: CallType
    name: str
    meta: str
    duration: str


class SkillType(str, Enum):
    offer = "offer"
    wanted = "wanted"


class SkillListing(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    initials: str
    name: str
    property: str
    type: SkillType
    title: str
    desc: str
    tags: List[str]


class BarterStat(BaseModel):
    label: str
    value: str
    sub: str


class Trade(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    initials: str
    name: str
    property: str
    color: str
    give: str
    get: str
    match: str
    value: str
    status: str = "open"  # open | proposed | accepted | completed


class Readiness(str, Enum):
    ready = "ready"
    training = "training"


class LegacyCandidate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    initials: str
    name: str
    relation: str
    color: str
    readiness: Readiness
    progress: int = Field(ge=0, le=100)
    skills: List[str]


class Galaxy(BaseModel):
    icon: str
    color: str
    name: str
    desc: str
    progress: int = Field(ge=0, le=100)
    unlocked: bool
    status: str


class VoiceSettings(BaseModel):
    auto_answer: bool = True
    bilingual: bool = True
    record_transcripts: bool = True
    voice: str = "Amina (F)"


class ProposeTradeRequest(BaseModel):
    trade_id: str
    message: Optional[str] = None


class ContactSkillRequest(BaseModel):
    skill_id: str
    message: Optional[str] = None


class LegacyActionRequest(BaseModel):
    candidate_id: str
    action: str  # "begin_handover" | "continue_training"


# ──────────────────────────────────────────────────────────────
# In-memory store (replace with DB later)
# ──────────────────────────────────────────────────────────────

hp_stats: List[HealthStat] = [
    HealthStat(label="Wellness Score", value="78/100", sub="Top 24% of landlords"),
    HealthStat(label="Steps This Week", value="48,240", sub="Daily avg: 6,891"),
    HealthStat(label="Sleep Quality", value="7.2 hrs", sub="Avg. nightly"),
    HealthStat(label="Health Checks", value="92%", sub="Up to date"),
]

wellness_categories: List[WellnessCategory] = [
    WellnessCategory(label="Physical Activity", score=82, color="green"),
    WellnessCategory(label="Nutrition", score=74, color="teal"),
    WellnessCategory(label="Sleep Quality", score=68, color="gold"),
    WellnessCategory(label="Stress Management", score=65, color="gold"),
    WellnessCategory(label="Preventive Care", score=92, color="green"),
    WellnessCategory(label="Mental Wellbeing", score=78, color="blue"),
]

screenings: List[Screening] = [
    Screening(
        icon="fa-heartbeat", type="heart", name="Cardiovascular Screening",
        meta="Nairobi Hospital · Free for members", status=ScreeningStatus.upcoming
    ),
    Screening(
        icon="fa-lungs", type="lungs", name="Lung Function Test",
        meta="Due in 45 days", status=ScreeningStatus.due
    ),
    Screening(
        icon="fa-eye", type="eye", name="Comprehensive Eye Exam",
        meta="Completed 3 months ago", status=ScreeningStatus.complete
    ),
    Screening(
        icon="fa-tooth", type="dental", name="Dental Checkup & Cleaning",
        meta="Scheduled Apr 22, 2025", status=ScreeningStatus.upcoming
    ),
]

capsules: List[CapsuleMoment] = [
    CapsuleMoment(year="2019", title="First Property Acquired",
                  desc="Purchased Kilimani Court with a KSh 12M mortgage.", icon="fa-home"),
    CapsuleMoment(year="2021", title="Portfolio Doubled",
                  desc="Added Westlands Heights and South B Apartments to the portfolio.", icon="fa-chart-line"),
    CapsuleMoment(year="2023", title="KSh 100M Milestone",
                  desc="Portfolio valuation crossed the 100M mark for the first time.", icon="fa-trophy"),
    CapsuleMoment(year="2024", title="Family Legacy Begins",
                  desc="Onboarded daughter Alice as co-manager in training.", icon="fa-users"),
    CapsuleMoment(year="2025", title="KSh 486M Portfolio",
                  desc="Peak portfolio value reached with 12 properties and 248 tenants.", icon="fa-crown"),
]

calls: List[CallLogEntry] = [
    CallLogEntry(type=CallType.incoming, name="John Wachira",
                 meta="Tenant · Kilimani Court · Lease renewal query", duration="4:32"),
    CallLogEntry(type=CallType.outgoing, name="Plumber Kings Ltd",
                 meta="Vendor · Confirming repair appointment", duration="1:48"),
    CallLogEntry(type=CallType.incoming, name="Mary Njoki",
                 meta="Tenant · Payment confirmation", duration="2:15"),
    CallLogEntry(type=CallType.missed, name="New Prospect",
                 meta="Inquiry about Unit 5C availability", duration="—"),
    CallLogEntry(type=CallType.incoming, name="Amina Hassan",
                 meta="Co-landlord · Discussing maintenance budget", duration="8:42"),
]

skills: List[SkillListing] = [
    SkillListing(initials="JW", name="John Wachira", property="Kilimani Court · 3B",
                 type=SkillType.offer, title="Coding & Web Development",
                 desc="Full-stack developer offering free weekend coding lessons for teens.",
                 tags=["JavaScript", "Python", "Teens"]),
    SkillListing(initials="MN", name="Mary Njoki", property="Westlands Heights · 5A",
                 type=SkillType.wanted, title="Kiswahili Tutoring for Kids",
                 desc="Looking for a patient tutor to teach my two children Kiswahili on weekends.",
                 tags=["Education", "Weekends"]),
    SkillListing(initials="BK", name="Brian Kamau", property="South B Apartments · 12",
                 type=SkillType.offer, title="Car Repair & Maintenance",
                 desc="Certified mechanic offering discounted car diagnostics and basic repairs.",
                 tags=["Automotive", "Discount"]),
    SkillListing(initials="LM", name="Lucy Muthoni", property="Lavington Suites · 7C",
                 type=SkillType.offer, title="Baking & Pastry Classes",
                 desc="Professional baker offering small-group pastry classes twice a month.",
                 tags=["Cooking", "Classes"]),
    SkillListing(initials="TM", name="Tom Mboya", property="Eastleigh Plaza · 4D",
                 type=SkillType.wanted, title="Yoga Instructor",
                 desc="Seeking a certified yoga instructor for weekly morning sessions at the estate.",
                 tags=["Wellness", "Fitness"]),
    SkillListing(initials="SK", name="Sarah Kilonzo", property="Runda Gardens · 2A",
                 type=SkillType.offer, title="Photography Services",
                 desc="Event and portrait photographer offering tenant discounts on family shoots.",
                 tags=["Photography", "Events"]),
]

barter_stats: List[BarterStat] = [
    BarterStat(label="Active Trades", value="24", sub="Across 12 landlords"),
    BarterStat(label="Trade Value YTD", value="KSh 8.4M", sub="Total bartered value"),
    BarterStat(label="Match Rate", value="72%", sub="Successful matches"),
    BarterStat(label="Your Trades", value="6", sub="3 completed · 3 pending"),
]

trades: List[Trade] = [
    Trade(initials="GW", name="Grace Wanjiku", property="Kilimani Court", color="#c8972a",
          give="2 months rent · Unit 3B (KSh 90,000 value)",
          get="Professional repainting of 3 units (KSh 90,000 value)",
          match="Perfect Match", value="KSh 90,000"),
    Trade(initials="AH", name="Amina Hassan", property="South B Apartments", color="#6b4c9a",
          give="Legal consultation on tenant disputes (20 hrs)",
          get="Plumbing overhaul for 2 buildings (KSh 180,000 value)",
          match="Good Match", value="KSh 180,000"),
    Trade(initials="DO", name="David Ochieng", property="Eastleigh Plaza", color="#2c6b9e",
          give="Accounting services for Q2 2025",
          get="Security camera installation (8 units)",
          match="Perfect Match", value="KSh 240,000"),
    Trade(initials="SK", name="Sarah Kilonzo", property="Runda Gardens", color="#b5447a",
          give="Interior design consultation for office space",
          get="Landscaping work for garden and driveway",
          match="Good Match", value="KSh 120,000"),
]

legacy_candidates: List[LegacyCandidate] = [
    LegacyCandidate(initials="AW", name="Alice Wanjiku", relation="Daughter · Age 28",
                    color="#b5447a", readiness=Readiness.ready, progress=88,
                    skills=["Property Management", "Accounting", "Tenant Relations", "Legal Basics"]),
    LegacyCandidate(initials="JW", name="John Wanjiku", relation="Son · Age 24",
                    color="#2c6b9e", readiness=Readiness.training, progress=54,
                    skills=["Maintenance", "Vendor Management", "Construction"]),
    LegacyCandidate(initials="NW", name="Nancy Wanjiku", relation="Niece · Age 32",
                    color="#6b4c9a", readiness=Readiness.training, progress=42,
                    skills=["Finance", "Investment Analysis", "KRA Compliance"]),
    LegacyCandidate(initials="CW", name="Charity Foundation", relation="Trusted Partner Organization",
                    color="#1e8e5c", readiness=Readiness.ready, progress=92,
                    skills=["Asset Management", "Governance", "Non-Profit Leadership"]),
]

galaxies: List[Galaxy] = [
    Galaxy(icon="fa-seedling", color="green", name="Genesis Galaxy",
           desc="Your first property and the beginning of your journey.",
           progress=100, unlocked=True, status="Completed"),
    Galaxy(icon="fa-mountain", color="blue", name="Horizon Galaxy",
           desc="Grow your portfolio to 5 properties and 50 tenants.",
           progress=100, unlocked=True, status="Completed"),
    Galaxy(icon="fa-globe-africa", color="gold", name="Terra Nova",
           desc="Current galaxy · 12 properties, 248 tenants, KSh 486M value.",
           progress=74, unlocked=True, status="Current · 74%"),
    Galaxy(icon="fa-crown", color="purple", name="Sovereign Galaxy",
           desc="Reach KSh 1B portfolio value and 500+ tenants.",
           progress=48, unlocked=False, status="48% to unlock"),
    Galaxy(icon="fa-gem", color="pink", name="Eternal Galaxy",
           desc="Legacy tier · Multi-generational wealth and impact.",
           progress=22, unlocked=False, status="22% to unlock"),
    Galaxy(icon="fa-infinity", color="locked", name="Infinity Galaxy",
           desc="The highest tier · Reserved for legends of Mwarokin.",
           progress=0, unlocked=False, status="Locked"),
]

voice_settings = VoiceSettings()

# Action logs (real side-effects)
action_log: List[dict] = []


def log_action(action: str, detail: dict) -> None:
    action_log.append({
        "id": str(uuid4()),
        "action": action,
        "detail": detail,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })


# ──────────────────────────────────────────────────────────────
# Health & Longevity
# ──────────────────────────────────────────────────────────────

@app.get("/api/health/stats", response_model=List[HealthStat])
def get_health_stats():
    return hp_stats


@app.get("/api/health/wellness-categories", response_model=List[WellnessCategory])
def get_wellness_categories():
    return wellness_categories


@app.get("/api/health/screenings", response_model=List[Screening])
def get_screenings():
    return screenings


@app.get("/api/health/summary")
def health_summary():
    return {
        "heart_rate": 72,
        "wellness_score": 78,
        "status": "Good Standing",
        "percentile": "top 24%",
        "stats": hp_stats,
        "categories": wellness_categories,
        "screenings": screenings,
    }


# ──────────────────────────────────────────────────────────────
# Time Capsule
# ──────────────────────────────────────────────────────────────

@app.get("/api/capsule/timeline", response_model=List[CapsuleMoment])
def get_capsule_timeline():
    return capsules


@app.post("/api/capsule/moments", response_model=CapsuleMoment, status_code=status.HTTP_201_CREATED)
def add_capsule_moment(moment: CapsuleMoment):
    capsules.append(moment)
    log_action("capsule_added", moment.model_dump())
    return moment


# ──────────────────────────────────────────────────────────────
# AI Voice Assistant
# ──────────────────────────────────────────────────────────────

@app.get("/api/voice/settings", response_model=VoiceSettings)
def get_voice_settings():
    return voice_settings


@app.patch("/api/voice/settings", response_model=VoiceSettings)
def update_voice_settings(settings: VoiceSettings):
    global voice_settings
    voice_settings = settings
    log_action("voice_settings_updated", settings.model_dump())
    return voice_settings


@app.get("/api/voice/calls", response_model=List[CallLogEntry])
def get_call_log():
    return calls


@app.post("/api/voice/calls", response_model=CallLogEntry, status_code=status.HTTP_201_CREATED)
def log_call(entry: CallLogEntry):
    calls.insert(0, entry)
    log_action("call_logged", entry.model_dump())
    return entry


# ──────────────────────────────────────────────────────────────
# Skills Exchange
# ──────────────────────────────────────────────────────────────

@app.get("/api/skills", response_model=List[SkillListing])
def list_skills(type: Optional[SkillType] = None):
    if type:
        return [s for s in skills if s.type == type]
    return skills


@app.post("/api/skills", response_model=SkillListing, status_code=status.HTTP_201_CREATED)
def create_skill(listing: SkillListing):
    skills.append(listing)
    log_action("skill_created", listing.model_dump())
    return listing


@app.post("/api/skills/contact")
def contact_skill(req: ContactSkillRequest):
    skill = next((s for s in skills if s.id == req.skill_id), None)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill listing not found")
    log_action("skill_contacted", {
        "skill_id": req.skill_id,
        "name": skill.name,
        "type": skill.type,
        "message": req.message,
    })
    return {
        "status": "connected",
        "message": f"You will be connected with {skill.name} to "
                   f"{'learn' if skill.type == 'offer' else 'offer'} this skill.",
        "skill": skill,
    }


# ──────────────────────────────────────────────────────────────
# Barter Network
# ──────────────────────────────────────────────────────────────

@app.get("/api/barter/stats", response_model=List[BarterStat])
def get_barter_stats():
    return barter_stats


@app.get("/api/barter/trades", response_model=List[Trade])
def list_trades(status: Optional[str] = None):
    if status:
        return [t for t in trades if t.status == status]
    return trades


@app.post("/api/barter/propose")
def propose_trade(req: ProposeTradeRequest):
    trade = next((t for t in trades if t.id == req.trade_id), None)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    if trade.status != "open":
        raise HTTPException(status_code=400, detail=f"Trade already {trade.status}")
    trade.status = "proposed"
    log_action("trade_proposed", {
        "trade_id": req.trade_id,
        "partner": trade.name,
        "message": req.message,
    })
    return {
        "status": "proposed",
        "message": f"Barter trade proposed to {trade.name}",
        "trade": trade,
    }


# ──────────────────────────────────────────────────────────────
# Legacy Handover
# ──────────────────────────────────────────────────────────────

@app.get("/api/legacy/candidates", response_model=List[LegacyCandidate])
def list_legacy_candidates():
    return legacy_candidates


@app.post("/api/legacy/action")
def legacy_action(req: LegacyActionRequest):
    candidate = next((c for c in legacy_candidates if c.id == req.candidate_id), None)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if req.action == "begin_handover":
        if candidate.readiness != Readiness.ready:
            raise HTTPException(status_code=400, detail="Candidate is not ready for handover")
        log_action("handover_started", {"candidate": candidate.name})
        return {
            "status": "handover_initiated",
            "message": f"Legacy handover ceremony started for {candidate.name}",
            "candidate": candidate,
        }
    elif req.action == "continue_training":
        # Simulate progress bump
        candidate.progress = min(100, candidate.progress + 5)
        if candidate.progress >= 85:
            candidate.readiness = Readiness.ready
        log_action("training_continued", {
            "candidate": candidate.name,
            "new_progress": candidate.progress,
        })
        return {
            "status": "training_updated",
            "message": f"Training continued for {candidate.name}. Progress: {candidate.progress}%",
            "candidate": candidate,
        }
    else:
        raise HTTPException(status_code=400, detail="Invalid action")


# ──────────────────────────────────────────────────────────────
# Constellation / Galaxies
# ──────────────────────────────────────────────────────────────

@app.get("/api/constellation/galaxies", response_model=List[Galaxy])
def list_galaxies():
    return galaxies


@app.get("/api/constellation/current")
def current_galaxy():
    current = next((g for g in galaxies if "Current" in g.status), None)
    return {
        "level": "Galaxy 3",
        "name": "Terra Nova",
        "current": current,
        "galaxies": galaxies,
    }


# ──────────────────────────────────────────────────────────────
# Full page payload (single request for the frontend)
# ──────────────────────────────────────────────────────────────

@app.get("/api/page14")
def page14_data():
    return {
        "health": {
            "heart_rate": 72,
            "wellness_score": 78,
            "stats": hp_stats,
            "categories": wellness_categories,
            "screenings": screenings,
        },
        "capsule": capsules,
        "voice": {
            "settings": voice_settings,
            "calls": calls,
        },
        "skills": skills,
        "barter": {
            "stats": barter_stats,
            "trades": trades,
        },
        "legacy": legacy_candidates,
        "constellation": {
            "level": "Galaxy 3",
            "label": "Terra Nova",
            "galaxies": galaxies,
        },
    }


# ──────────────────────────────────────────────────────────────
# Audit / Action log
# ──────────────────────────────────────────────────────────────

@app.get("/api/actions")
def get_action_log(limit: int = 50):
    return action_log[-limit:]


@app.get("/")
def root():
    return {
        "service": "Mwarokin Estates – Legacy, Wellness & Galactic Rewards",
        "version": "1.0.0",
        "docs": "/docs",
        "page14": "/api/page14",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### How to run

```bash
pip install fastapi uvicorn pydantic
python main.py
# or: uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for interactive Swagger UI.

### Key real functionality

| Feature              | Endpoints                                      | Real behaviour                          |
|----------------------|------------------------------------------------|-----------------------------------------|
| Health               | `GET /api/health/*`                            | Live data + summary                     |
| Time Capsule         | `GET/POST /api/capsule/*`                      | Add new moments                         |
| Voice Assistant      | `GET/PATCH /api/voice/*`                       | Toggle settings, log calls              |
| Skills Exchange      | `GET/POST /api/skills`, `POST /api/skills/contact` | Contact listings, create new ones   |
| Barter               | `GET /api/barter/*`, `POST /api/barter/propose` | Propose trades → status changes         |
| Legacy Handover      | `GET /api/legacy/*`, `POST /api/legacy/action`  | Start handover or advance training      |
| Constellation        | `GET /api/constellation/*`                     | Current galaxy + progress               |
| Full page            | `GET /api/page14`                              | Everything in one call                  |
| Audit                | `GET /api/actions`                             | Every write action is logged            |

Replace the in-memory lists with SQLAlchemy + SQLite/Postgres when you’re ready for persistence. The models and endpoints stay the same.