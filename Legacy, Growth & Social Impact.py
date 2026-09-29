Here’s a complete **FastAPI** backend for the Legacy, Growth & Social Impact page with real, mutable functionality.

```python
"""
Mwarokin Estates – Legacy, Growth & Social Impact (Page 13)
Modern FastAPI backend with real functionality.

Run:
    pip install fastapi uvicorn[standard] pydantic
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Open: http://127.0.0.1:8000
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, computed_field

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mwarokin Estates – Legacy, Growth & Social Impact",
    description="Estate planning, crowdfunding, lease AI, wellness, tax opt, drones, impact fund.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Enums & models
# ---------------------------------------------------------------------------

class DocState(str, Enum):
    done = "done"
    progress = "progress"
    pending = "pending"


class CampaignStatus(str, Enum):
    active = "Active"
    closing = "Closing Soon"
    funded = "Funded"
    ended = "Ended"


class RiskSeverity(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class ProjectStatus(str, Enum):
    active = "Active"
    completed = "Completed"
    planned = "Planned"


class StatItem(BaseModel):
    label: str
    value: str
    sub: str = ""
    color: str = ""


class Beneficiary(BaseModel):
    id: str
    initials: str
    name: str
    relation: str
    share_pct: float = Field(..., ge=0, le=100)
    color: str

    @computed_field
    @property
    def share(self) -> str:
        return f"{int(self.share_pct)}%"


class LegalDocument(BaseModel):
    id: str
    name: str
    status: str
    state: DocState


class EstateOverview(BaseModel):
    plan_complete_pct: int
    stats: list[StatItem]
    beneficiaries: list[Beneficiary]
    documents: list[LegalDocument]


class Campaign(BaseModel):
    id: str
    banner: str
    icon: str
    name: str
    location: str
    raised: int
    target: int
    investors: int
    min_investment: int
    deadline: str
    status: CampaignStatus

    @computed_field
    @property
    def progress_pct(self) -> float:
        return round((self.raised / self.target) * 100, 1) if self.target else 0


class InvestRequest(BaseModel):
    amount: int = Field(..., gt=0)


class AnalysisItem(BaseModel):
    id: str
    severity: RiskSeverity
    title: str
    desc: str
    clause: str


class LeaseAnalysisResult(BaseModel):
    filename: str
    analyzed_at: str
    items: list[AnalysisItem]
    risk_summary: dict[str, int]


class WellnessService(BaseModel):
    id: str
    icon: str
    name: str
    desc: str
    enrolled: int = 0


class TaxRecommendation(BaseModel):
    id: str
    icon: str
    title: str
    desc: str
    savings_yearly: int
    applied: bool = False

    @computed_field
    @property
    def savings(self) -> str:
        return f"KSh {self.savings_yearly:,}/yr"


class DroneSurvey(BaseModel):
    id: str
    icon: str
    name: str
    date: str


class ImpactProject(BaseModel):
    id: str
    icon: str
    name: str
    desc: str
    funding: int
    goal: int
    status: ProjectStatus

    @computed_field
    @property
    def progress_pct(self) -> float:
        return round((self.funding / self.goal) * 100, 1) if self.goal else 0


class DonateRequest(BaseModel):
    amount: int = Field(..., gt=0)


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

PLAN_COMPLETE_PCT = 78

ESTATE_STATS = [
    StatItem(label="Portfolio Value", value="KSh 486M", sub="Total assets covered"),
    StatItem(label="Beneficiaries", value="4", sub="Named in will"),
    StatItem(label="Trust Assets", value="KSh 128M", sub="In family trust"),
    StatItem(label="Last Updated", value="Apr 2", sub="2025"),
]

BENEFICIARIES: dict[str, Beneficiary] = {
    "b1": Beneficiary(id="b1", initials="MW", name="Mary Wanjiku", relation="Spouse",
                      share_pct=45, color="#b5447a"),
    "b2": Beneficiary(id="b2", initials="JW", name="John Wanjiku", relation="Son",
                      share_pct=20, color="#2c6b9e"),
    "b3": Beneficiary(id="b3", initials="AW", name="Alice Wanjiku", relation="Daughter",
                      share_pct=20, color="#6b4c9a"),
    "b4": Beneficiary(id="b4", initials="CW", name="Charity Foundation", relation="Charity",
                      share_pct=15, color="#1e8e5c"),
}

DOCUMENTS: dict[str, LegalDocument] = {
    "d1": LegalDocument(id="d1", name="Last Will & Testament",
                        status="Signed & notarized", state=DocState.done),
    "d2": LegalDocument(id="d2", name="Family Trust Deed",
                        status="Registered with lands office", state=DocState.done),
    "d3": LegalDocument(id="d3", name="Power of Attorney",
                        status="Signed · pending witnesses", state=DocState.progress),
    "d4": LegalDocument(id="d4", name="Healthcare Directive",
                        status="Awaiting legal review", state=DocState.progress),
    "d5": LegalDocument(id="d5", name="Business Succession Plan",
                        status="Not started", state=DocState.pending),
}

CAMPAIGNS: dict[str, Campaign] = {
    "c1": Campaign(
        id="c1", banner="residential", icon="fa-building",
        name="Riverside Apartments Phase 2", location="Riverside, Nairobi",
        raised=42_000_000, target=60_000_000, investors=248,
        min_investment=50_000, deadline="May 30, 2025", status=CampaignStatus.active,
    ),
    "c2": Campaign(
        id="c2", banner="mixed", icon="fa-city",
        name="Thika Road Mixed-Use Complex", location="Thika Road, Nairobi",
        raised=128_000_000, target=180_000_000, investors=412,
        min_investment=100_000, deadline="Jun 15, 2025", status=CampaignStatus.active,
    ),
    "c3": Campaign(
        id="c3", banner="commercial", icon="fa-store",
        name="Karen Business Park Expansion", location="Karen, Nairobi",
        raised=215_000_000, target=250_000_000, investors=156,
        min_investment=250_000, deadline="May 20, 2025", status=CampaignStatus.closing,
    ),
    "c4": Campaign(
        id="c4", banner="hospitality", icon="fa-hotel",
        name="Diani Beach Resort Development", location="Diani, Mombasa",
        raised=48_000_000, target=120_000_000, investors=184,
        min_investment=75_000, deadline="Aug 10, 2025", status=CampaignStatus.active,
    ),
}

ANALYSIS_ITEMS: list[AnalysisItem] = [
    AnalysisItem(
        id="a1", severity=RiskSeverity.high,
        title="Unlimited Rent Escalation Clause",
        desc="The lease permits rent increase without cap or notice period. This is non-standard and highly unfavorable.",
        clause='Clause 4.2: "The Landlord may revise the rent at any time, at their sole discretion, without prior notice to the Tenant."',
    ),
    AnalysisItem(
        id="a2", severity=RiskSeverity.medium,
        title="Automatic Renewal Without Notice",
        desc="Lease auto-renews annually unless notice is given 90 days prior. Standard is 30–60 days.",
        clause='Clause 7.1: "This lease shall automatically renew for successive one-year terms unless either party provides written notice at least ninety (90) days prior to expiry."',
    ),
    AnalysisItem(
        id="a3", severity=RiskSeverity.low,
        title="Standard Deposit Protection",
        desc="Security deposit clause is compliant with Kenyan tenancy law. Deposit held in escrow.",
        clause='Clause 5.3: "The Security Deposit shall be held in a designated escrow account and refunded within 30 days of lease termination, less any documented deductions."',
    ),
    AnalysisItem(
        id="a4", severity=RiskSeverity.medium,
        title="Broad Maintenance Obligations",
        desc="Tenant is responsible for structural repairs, which is typically a landlord obligation.",
        clause='Clause 9.4: "The Tenant shall be responsible for all repairs, including structural repairs, plumbing, and electrical systems, at their own cost."',
    ),
]

LAST_ANALYSIS: LeaseAnalysisResult | None = None

WS_STATS = [
    StatItem(label="Enrolled Tenants", value="184", sub="Active in programs"),
    StatItem(label="Health Screenings", value="328", sub="YTD completed"),
    StatItem(label="Scholarships", value="12", sub="Children sponsored"),
    StatItem(label="Counselling Sessions", value="148", sub="Free & confidential"),
]

WS_SERVICES: dict[str, WellnessService] = {
    "w1": WellnessService(id="w1", icon="fa-stethoscope", name="Free Health Screenings",
                          desc="Quarterly BP, sugar & BMI checks", enrolled=42),
    "w2": WellnessService(id="w2", icon="fa-graduation-cap", name="Education Scholarships",
                          desc="School fees for children in need", enrolled=12),
    "w3": WellnessService(id="w3", icon="fa-brain", name="Mental Health Support",
                          desc="Counselling & wellness programs", enrolled=28),
    "w4": WellnessService(id="w4", icon="fa-dumbbell", name="Fitness & Sports",
                          desc="Weekly community sports events", enrolled=56),
    "w5": WellnessService(id="w5", icon="fa-book", name="Financial Literacy",
                          desc="Free courses on saving & budgeting", enrolled=34),
    "w6": WellnessService(id="w6", icon="fa-utensils", name="Nutrition Program",
                          desc="Meal plans & cooking classes", enrolled=19),
    "w7": WellnessService(id="w7", icon="fa-baby", name="Childcare Support",
                          desc="Subsidized daycare services", enrolled=15),
    "w8": WellnessService(id="w8", icon="fa-hands-helping", name="Elderly Care",
                          desc="Home visits & assistance", enrolled=8),
}

TAX_RECS: dict[str, TaxRecommendation] = {
    "t1": TaxRecommendation(
        id="t1", icon="fa-home",
        title="Claim Capital Allowances on Renovations",
        desc="Your recent KSh 2.8M renovation at Lavington Suites qualifies for capital allowance deductions over 5 years.",
        savings_yearly=168_000,
    ),
    "t2": TaxRecommendation(
        id="t2", icon="fa-hand-holding-usd",
        title="Maximize Mortgage Interest Deduction",
        desc="You can deduct up to KSh 30,000/month in mortgage interest on each rental property. You're currently under-claiming.",
        savings_yearly=96_000,
    ),
    "t3": TaxRecommendation(
        id="t3", icon="fa-shield-alt",
        title="Insurance Premium Deductions",
        desc="Property insurance premiums are fully tax-deductible. Your KSh 420,000 annual premium is not yet claimed.",
        savings_yearly=126_000,
    ),
    "t4": TaxRecommendation(
        id="t4", icon="fa-tools",
        title="Maintenance Expense Optimization",
        desc="Shift preventive maintenance to this FY. You have KSh 1.2M in maintenance scheduled for next FY.",
        savings_yearly=96_000,
    ),
}

DRONE_STATS = [
    StatItem(label="Total Area Surveyed", value="14.2 acres", sub=""),
    StatItem(label="Images Captured", value="8,420", sub="", color="gold"),
    StatItem(label="3D Models Generated", value="6", sub="", color="green"),
    StatItem(label="Last Survey", value="Apr 8, 2025", sub=""),
]

DRONE_SURVEYS: dict[str, DroneSurvey] = {
    "ds1": DroneSurvey(id="ds1", icon="fa-building", name="Kilimani Court · Roof Inspection",
                       date="Apr 8, 2025 · 4K orthomosaic"),
    "ds2": DroneSurvey(id="ds2", icon="fa-hard-hat", name="South B Expansion · Progress",
                       date="Apr 2, 2025 · Weekly survey"),
    "ds3": DroneSurvey(id="ds3", icon="fa-tree", name="Runda Gardens · Boundary Check",
                       date="Mar 28, 2025 · Title verification"),
    "ds4": DroneSurvey(id="ds4", icon="fa-map-marked-alt", name="Lavington Suites · Site Plan",
                       date="Mar 15, 2025 · 3D model"),
}

IMPACT_STATS = [
    StatItem(label="Total Fund Value", value="KSh 4.8M", sub="Contributions + match"),
    StatItem(label="Projects Funded", value="18", sub="Across 6 communities"),
    StatItem(label="Lives Impacted", value="1,240", sub="Direct beneficiaries"),
    StatItem(label="Your Contribution", value="KSh 384K", sub="8% of fund"),
]

IMPACT_PROJECTS: dict[str, ImpactProject] = {
    "ip1": ImpactProject(
        id="ip1", icon="fa-school", name="Kilimani Primary School Library",
        desc="Built a new library for 480 pupils with 2,000 books.",
        funding=1_850_000, goal=2_000_000, status=ProjectStatus.active,
    ),
    "ip2": ImpactProject(
        id="ip2", icon="fa-briefcase-medical", name="South B Community Clinic",
        desc="Free medical camp serving 800+ residents monthly.",
        funding=1_200_000, goal=1_200_000, status=ProjectStatus.completed,
    ),
    "ip3": ImpactProject(
        id="ip3", icon="fa-tree", name="Lavington Green Park",
        desc="Community park with 200 trees and playground.",
        funding=680_000, goal=1_000_000, status=ProjectStatus.active,
    ),
    "ip4": ImpactProject(
        id="ip4", icon="fa-female", name="Women Entrepreneur Fund",
        desc="Micro-grants for 40 women-owned businesses.",
        funding=820_000, goal=1_500_000, status=ProjectStatus.active,
    ),
}

# Mutable contribution tracker for impact fund
YOUR_CONTRIBUTION = 384_000
FUND_TOTAL = 4_800_000

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def recompute_plan_pct() -> int:
    done = sum(1 for d in DOCUMENTS.values() if d.state == DocState.done)
    progress = sum(1 for d in DOCUMENTS.values() if d.state == DocState.progress)
    total = len(DOCUMENTS)
    if total == 0:
        return 0
    return min(100, int((done * 100 + progress * 40) / total))


def total_tax_savings() -> int:
    return sum(r.savings_yearly for r in TAX_RECS.values() if r.applied)


def potential_tax_savings() -> int:
    return sum(r.savings_yearly for r in TAX_RECS.values() if not r.applied)


# ---------------------------------------------------------------------------
# API – Estate Planning
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Legacy, Growth & Social Impact"}


@app.get("/api/estate", response_model=EstateOverview, tags=["Estate"])
def get_estate():
    global PLAN_COMPLETE_PCT
    PLAN_COMPLETE_PCT = recompute_plan_pct()
    return EstateOverview(
        plan_complete_pct=PLAN_COMPLETE_PCT,
        stats=ESTATE_STATS,
        beneficiaries=list(BENEFICIARIES.values()),
        documents=list(DOCUMENTS.values()),
    )


@app.post("/api/estate/documents/{doc_id}/advance", response_model=LegalDocument, tags=["Estate"])
def advance_document(doc_id: str):
    """Move document: pending → progress → done."""
    doc = DOCUMENTS.get(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.state == DocState.pending:
        doc.state = DocState.progress
        doc.status = "In progress · legal drafting"
    elif doc.state == DocState.progress:
        doc.state = DocState.done
        doc.status = "Signed & complete"
    else:
        raise HTTPException(400, "Document already complete")
    return doc


# ---------------------------------------------------------------------------
# API – Crowdfunding
# ---------------------------------------------------------------------------

@app.get("/api/campaigns", response_model=list[Campaign], tags=["Crowdfunding"])
def list_campaigns():
    return list(CAMPAIGNS.values())


@app.get("/api/campaigns/{campaign_id}", response_model=Campaign, tags=["Crowdfunding"])
def get_campaign(campaign_id: str):
    c = CAMPAIGNS.get(campaign_id)
    if not c:
        raise HTTPException(404, "Campaign not found")
    return c


@app.post("/api/campaigns/{campaign_id}/invest", response_model=Campaign, tags=["Crowdfunding"])
def invest(campaign_id: str, body: InvestRequest):
    c = CAMPAIGNS.get(campaign_id)
    if not c:
        raise HTTPException(404, "Campaign not found")
    if c.status in (CampaignStatus.funded, CampaignStatus.ended):
        raise HTTPException(400, "Campaign is no longer accepting investments")
    if body.amount < c.min_investment:
        raise HTTPException(400, f"Minimum investment is KSh {c.min_investment:,}")
    remaining = c.target - c.raised
    if body.amount > remaining:
        raise HTTPException(400, f"Only KSh {remaining:,} remaining to target")

    c.raised += body.amount
    c.investors += 1
    if c.raised >= c.target:
        c.status = CampaignStatus.funded
        c.raised = c.target
    return c


# ---------------------------------------------------------------------------
# API – Lease Analyzer
# ---------------------------------------------------------------------------

@app.get("/api/lease/analysis", response_model=LeaseAnalysisResult | None, tags=["Lease AI"])
def get_last_analysis():
    return LAST_ANALYSIS


@app.post("/api/lease/analyze", response_model=LeaseAnalysisResult, tags=["Lease AI"])
def analyze_lease(filename: str = Query("Kilimani_Unit_3B_2025.pdf")):
    """Simulate AI lease analysis (returns seeded risk items)."""
    global LAST_ANALYSIS
    summary = {"high": 0, "medium": 0, "low": 0}
    for item in ANALYSIS_ITEMS:
        summary[item.severity.value] += 1
    LAST_ANALYSIS = LeaseAnalysisResult(
        filename=filename,
        analyzed_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        items=ANALYSIS_ITEMS,
        risk_summary=summary,
    )
    return LAST_ANALYSIS


# ---------------------------------------------------------------------------
# API – Wellness
# ---------------------------------------------------------------------------

@app.get("/api/wellness/stats", response_model=list[StatItem], tags=["Wellness"])
def wellness_stats():
    enrolled = sum(s.enrolled for s in WS_SERVICES.values())
    stats = list(WS_STATS)
    # live enrolled figure
    stats[0] = StatItem(label="Enrolled Tenants", value=str(enrolled), sub="Active in programs")
    return stats


@app.get("/api/wellness/services", response_model=list[WellnessService], tags=["Wellness"])
def list_wellness_services():
    return list(WS_SERVICES.values())


@app.post("/api/wellness/services/{service_id}/enroll", response_model=WellnessService, tags=["Wellness"])
def enroll_wellness(service_id: str):
    s = WS_SERVICES.get(service_id)
    if not s:
        raise HTTPException(404, "Service not found")
    s.enrolled += 1
    return s


# ---------------------------------------------------------------------------
# API – Tax Optimization
# ---------------------------------------------------------------------------

@app.get("/api/tax/recommendations", tags=["Tax"])
def list_tax_recs():
    applied = total_tax_savings()
    potential = potential_tax_savings()
    return {
        "potential_savings": potential,
        "applied_savings": applied,
        "potential_display": f"KSh {potential // 1000}K" if potential >= 1000 else f"KSh {potential}",
        "items": list(TAX_RECS.values()),
    }


@app.post("/api/tax/recommendations/{rec_id}/apply", response_model=TaxRecommendation, tags=["Tax"])
def apply_tax_rec(rec_id: str):
    rec = TAX_RECS.get(rec_id)
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    if rec.applied:
        raise HTTPException(400, "Already applied")
    rec.applied = True
    return rec


# ---------------------------------------------------------------------------
# API – Drone
# ---------------------------------------------------------------------------

@app.get("/api/drone/stats", response_model=list[StatItem], tags=["Drone"])
def drone_stats():
    return DRONE_STATS


@app.get("/api/drone/surveys", response_model=list[DroneSurvey], tags=["Drone"])
def list_drone_surveys():
    return list(DRONE_SURVEYS.values())


@app.get("/api/drone/surveys/{survey_id}", response_model=DroneSurvey, tags=["Drone"])
def get_drone_survey(survey_id: str):
    s = DRONE_SURVEYS.get(survey_id)
    if not s:
        raise HTTPException(404, "Survey not found")
    return s


# ---------------------------------------------------------------------------
# API – Impact Fund
# ---------------------------------------------------------------------------

@app.get("/api/impact/stats", tags=["Impact"])
def impact_stats():
    global YOUR_CONTRIBUTION, FUND_TOTAL
    pct = round((YOUR_CONTRIBUTION / FUND_TOTAL) * 100) if FUND_TOTAL else 0
    return [
        StatItem(label="Total Fund Value", value=f"KSh {FUND_TOTAL / 1_000_000:.1f}M", sub="Contributions + match"),
        StatItem(label="Projects Funded", value="18", sub="Across 6 communities"),
        StatItem(label="Lives Impacted", value="1,240", sub="Direct beneficiaries"),
        StatItem(label="Your Contribution", value=f"KSh {YOUR_CONTRIBUTION // 1000}K", sub=f"{pct}% of fund"),
    ]


@app.get("/api/impact/projects", response_model=list[ImpactProject], tags=["Impact"])
def list_impact_projects():
    return list(IMPACT_PROJECTS.values())


@app.post("/api/impact/projects/{project_id}/donate", response_model=ImpactProject, tags=["Impact"])
def donate(project_id: str, body: DonateRequest):
    global YOUR_CONTRIBUTION, FUND_TOTAL
    p = IMPACT_PROJECTS.get(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    if p.status == ProjectStatus.completed:
        raise HTTPException(400, "Project already fully funded")

    p.funding = min(p.goal, p.funding + body.amount)
    if p.funding >= p.goal:
        p.status = ProjectStatus.completed
        p.funding = p.goal

    YOUR_CONTRIBUTION += body.amount
    FUND_TOTAL += body.amount
    return p


# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

FRONTEND_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Mwarokin Estates · Legacy, Growth & Social Impact</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" />
  <style>
    :root {
      --primary: #1e8e5c; --gold: #c8972a; --purple: #6b4c9a; --blue: #2c6b9e;
      --pink: #b5447a; --red: #c0392b; --navy: #1e3a5f;
      --gray-50: #f8fafc; --gray-100: #f1f5f9; --gray-200: #e2e8f0;
      --gray-400: #94a3b8; --gray-500: #64748b; --gray-700: #334155; --gray-900: #0f172a;
      --radius: 12px; --shadow: 0 4px 20px rgba(0,0,0,.06);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', system-ui, sans-serif; background: var(--gray-100); color: var(--gray-900); line-height: 1.5; }
    .app-container { max-width: 1200px; margin: 0 auto; padding: 0 20px 40px; }

    .top-bar { display: flex; justify-content: space-between; align-items: center; padding: 16px 0; border-bottom: 1px solid var(--gray-200); margin-bottom: 24px; }
    .brand { display: flex; align-items: center; gap: 12px; }
    .brand-icon { width: 42px; height: 42px; background: linear-gradient(135deg, var(--primary), var(--blue)); color: white; border-radius: 10px; display: grid; place-items: center; font-size: 20px; }
    .brand-text h1 { font-size: 1.2rem; } .brand-text h1 span { color: var(--primary); }
    .tagline { font-size: 0.75rem; color: var(--gray-500); }
    .nav-actions { display: flex; align-items: center; gap: 12px; }
    .nav-link { text-decoration: none; color: var(--gray-500); font-size: 0.85rem; padding: 6px 10px; border-radius: 8px; }
    .nav-link.active, .nav-link:hover { background: var(--gray-200); color: var(--primary); }
    .avatar { width: 36px; height: 36px; border-radius: 50%; background: var(--primary); color: white; display: grid; place-items: center; font-weight: 600; font-size: 0.8rem; }

    .page-header { margin-bottom: 24px; }
    .page-header h2 { font-size: 1.4rem; margin-bottom: 4px; }
    .page-header p { color: var(--gray-500); font-size: 0.9rem; }

    .section-title { font-size: 0.95rem; font-weight: 600; margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }
    .fade-in { animation: fadeIn .35s ease; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }

    .estate-hero, .crowdfund-panel, .lease-analyzer-panel, .wellness-services-panel,
    .tax-optimizer-panel, .drone-panel, .impact-panel {
      background: white; border-radius: var(--radius); padding: 20px; box-shadow: var(--shadow); margin-bottom: 20px;
    }

    .estate-header, .ws-header, .impact-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }
    .estate-progress-ring { text-align: center; background: var(--gray-50); padding: 12px 18px; border-radius: 12px; }
    .epr-value { font-size: 1.6rem; font-weight: 700; color: var(--primary); }
    .epr-label { font-size: 0.7rem; color: var(--gray-500); }

    .estate-stats, .ws-stats, .impact-stats {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 16px;
    }
    .estate-stat, .ws-stat, .impact-stat { background: var(--gray-50); border-radius: 10px; padding: 12px; }
    .es-label, .wss-label, .is-label { font-size: 0.72rem; color: var(--gray-500); }
    .es-value, .wss-value, .is-value { font-size: 1.2rem; font-weight: 700; margin: 2px 0; }
    .es-sub, .is-sub { font-size: 0.7rem; color: var(--gray-400); }

    .estate-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
    @media (max-width: 800px) { .estate-grid { grid-template-columns: 1fr; } }
    .estate-card { background: white; border-radius: var(--radius); padding: 18px; box-shadow: var(--shadow); }

    .beneficiary { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--gray-100); }
    .beneficiary:last-child { border-bottom: none; }
    .beneficiary-avatar { width: 40px; height: 40px; border-radius: 50%; color: white; display: grid; place-items: center; font-weight: 600; font-size: 0.8rem; }
    .beneficiary-name { font-weight: 600; font-size: 0.9rem; }
    .beneficiary-relation { font-size: 0.75rem; color: var(--gray-500); }
    .beneficiary-share { margin-left: auto; text-align: right; }
    .bs-value { font-weight: 700; color: var(--primary); }
    .bs-label { font-size: 0.7rem; color: var(--gray-400); }

    .doc-item { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--gray-100); }
    .doc-item:last-child { border-bottom: none; }
    .doc-check { width: 32px; height: 32px; border-radius: 50%; display: grid; place-items: center; font-size: 0.8rem; color: white; }
    .doc-check.done { background: var(--primary); }
    .doc-check.progress { background: var(--gold); }
    .doc-check.pending { background: var(--gray-400); }
    .doc-name { font-weight: 600; font-size: 0.85rem; }
    .doc-status { font-size: 0.75rem; color: var(--gray-500); }
    .doc-advance { margin-left: auto; border: 1px solid var(--gray-200); background: white; border-radius: 6px; padding: 4px 10px; font-size: 0.72rem; cursor: pointer; }
    .doc-advance:hover { border-color: var(--primary); color: var(--primary); }

    .crowdfund-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; margin-top: 12px; }
    .campaign-card { border: 1px solid var(--gray-200); border-radius: var(--radius); overflow: hidden; transition: .2s; }
    .campaign-card:hover { border-color: var(--primary); box-shadow: var(--shadow); }
    .campaign-banner { height: 80px; display: flex; align-items: center; justify-content: center; position: relative; color: white; font-size: 1.8rem; }
    .campaign-banner.residential { background: linear-gradient(135deg, #2c6b9e, #1e8e5c); }
    .campaign-banner.mixed { background: linear-gradient(135deg, #6b4c9a, #2c6b9e); }
    .campaign-banner.commercial { background: linear-gradient(135deg, #c8972a, #c4622a); }
    .campaign-banner.hospitality { background: linear-gradient(135deg, #b5447a, #6b4c9a); }
    .campaign-status-badge { position: absolute; top: 8px; right: 8px; background: rgba(0,0,0,.35); padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; }
    .campaign-body { padding: 14px; }
    .campaign-name { font-weight: 600; font-size: 0.9rem; }
    .campaign-location { font-size: 0.75rem; color: var(--gray-500); margin: 4px 0 10px; }
    .campaign-progress-header { display: flex; justify-content: space-between; font-size: 0.75rem; margin-bottom: 4px; }
    .cph-raised { font-weight: 600; color: var(--primary); }
    .campaign-progress-bar { height: 6px; background: var(--gray-200); border-radius: 3px; overflow: hidden; margin-bottom: 10px; }
    .campaign-progress-fill { height: 100%; background: var(--primary); }
    .campaign-meta { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; margin-bottom: 12px; }
    .cmi-label { font-size: 0.65rem; color: var(--gray-400); }
    .cmi-value { font-size: 0.8rem; font-weight: 600; }
    .cmi-value.green { color: var(--primary); }
    .campaign-actions { display: flex; gap: 8px; }
    button { border: 1px solid var(--gray-200); background: white; border-radius: 8px; padding: 6px 12px; font-size: 0.8rem; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; }
    button.primary { background: var(--primary); color: white; border-color: var(--primary); }
    button:hover { opacity: .9; }

    .analyzer-layout { display: grid; grid-template-columns: 220px 1fr; gap: 16px; margin-top: 12px; }
    @media (max-width: 700px) { .analyzer-layout { grid-template-columns: 1fr; } }
    .upload-zone {
      border: 2px dashed var(--gray-200); border-radius: var(--radius); padding: 24px 16px;
      text-align: center; cursor: pointer; background: var(--gray-50);
    }
    .upload-zone:hover { border-color: var(--primary); }
    .upload-zone i { font-size: 2rem; color: var(--primary); margin-bottom: 8px; }
    .upload-zone h4 { font-size: 0.9rem; margin-bottom: 4px; }
    .upload-zone p { font-size: 0.75rem; color: var(--gray-500); margin-bottom: 12px; }
    .upload-btn { background: var(--primary); color: white; border: none; }

    .analysis-item { border-left: 3px solid var(--gray-300); padding: 12px; margin-bottom: 10px; background: var(--gray-50); border-radius: 0 8px 8px 0; }
    .analysis-item.risk-high { border-left-color: var(--red); }
    .analysis-item.risk-medium { border-left-color: var(--gold); }
    .analysis-item.risk-low { border-left-color: var(--primary); }
    .analysis-header { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 4px; }
    .analysis-title { font-weight: 600; font-size: 0.85rem; }
    .analysis-severity { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; text-transform: capitalize; }
    .analysis-severity.high { background: #fee2e2; color: #991b1b; }
    .analysis-severity.medium { background: #fef3c7; color: #92400e; }
    .analysis-severity.low { background: #d1fae5; color: #065f46; }
    .analysis-desc { font-size: 0.8rem; color: var(--gray-500); margin-bottom: 6px; }
    .analysis-clause { font-size: 0.75rem; font-family: monospace; background: white; padding: 8px; border-radius: 6px; color: var(--gray-700); }

    .ws-services-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; margin-top: 12px; }
    .ws-service {
      display: flex; align-items: center; gap: 12px; padding: 12px; background: var(--gray-50);
      border-radius: 10px; cursor: pointer; transition: .15s;
    }
    .ws-service:hover { background: #ecfdf5; }
    .ws-service-icon { width: 40px; height: 40px; border-radius: 10px; background: var(--primary); color: white; display: grid; place-items: center; flex-shrink: 0; }
    .ws-service-name { font-weight: 600; font-size: 0.85rem; }
    .ws-service-desc { font-size: 0.72rem; color: var(--gray-500); }

    .optimizer-hero {
      display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
      background: linear-gradient(135deg, #ecfdf5, #f0fdf4); border-radius: 10px; padding: 16px; margin: 12px 0;
    }
    .optimizer-hero-icon { width: 48px; height: 48px; border-radius: 12px; background: var(--primary); color: white; display: grid; place-items: center; font-size: 1.2rem; }
    .optimizer-hero-text { flex: 1; min-width: 180px; }
    .optimizer-hero-text h4 { font-size: 0.95rem; }
    .optimizer-hero-text p { font-size: 0.8rem; color: var(--gray-500); }
    .optimizer-savings { text-align: center; }
    .os-value { font-size: 1.4rem; font-weight: 700; color: var(--primary); }
    .os-label { font-size: 0.7rem; color: var(--gray-500); }

    .optimization-item {
      display: flex; align-items: center; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--gray-100); flex-wrap: wrap;
    }
    .optimization-item:last-child { border-bottom: none; }
    .optimization-icon { width: 40px; height: 40px; border-radius: 10px; background: var(--gray-100); display: grid; place-items: center; color: var(--primary); flex-shrink: 0; }
    .optimization-info { flex: 1; min-width: 180px; }
    .optimization-title { font-weight: 600; font-size: 0.85rem; }
    .optimization-desc { font-size: 0.75rem; color: var(--gray-500); }
    .optimization-savings-badge { background: #d1fae5; color: #065f46; padding: 4px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
    .optimization-apply { background: var(--primary); color: white; border: none; border-radius: 8px; padding: 6px 12px; font-size: 0.8rem; cursor: pointer; }
    .optimization-apply:disabled { background: var(--gray-400); cursor: default; }

    .drone-layout { display: grid; grid-template-columns: 1fr 220px; gap: 16px; margin-top: 12px; }
    @media (max-width: 700px) { .drone-layout { grid-template-columns: 1fr; } }
    .drone-map {
      height: 180px; background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 10px;
      position: relative; display: grid; place-items: center; color: white; margin-bottom: 12px;
    }
    .dmc-label { font-weight: 600; margin-top: 6px; }
    .dmc-sub { font-size: 0.75rem; opacity: .7; }
    .drone-pin { position: absolute; width: 10px; height: 10px; background: #ef4444; border-radius: 50%; box-shadow: 0 0 0 4px rgba(239,68,68,.3); animation: pulse 2s infinite; }
    @keyframes pulse { 50% { box-shadow: 0 0 0 8px rgba(239,68,68,.1); } }
    .survey-item { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--gray-100); }
    .survey-icon { width: 32px; height: 32px; border-radius: 8px; background: var(--gray-100); display: grid; place-items: center; color: var(--primary); }
    .survey-name { font-weight: 600; font-size: 0.8rem; }
    .survey-date { font-size: 0.7rem; color: var(--gray-500); }
    .survey-action { margin-left: auto; border: 1px solid var(--gray-200); background: white; border-radius: 6px; padding: 4px 10px; font-size: 0.72rem; cursor: pointer; }
    .drone-stat-row { display: flex; align-items: center; gap: 10px; padding: 10px 0; border-bottom: 1px solid var(--gray-100); }
    .drone-stat-icon { width: 36px; height: 36px; border-radius: 8px; background: var(--gray-100); display: grid; place-items: center; color: var(--primary); }
    .drone-stat-label { font-size: 0.75rem; color: var(--gray-500); }
    .drone-stat-value { font-weight: 700; font-size: 0.95rem; }
    .drone-stat-value.gold { color: var(--gold); }
    .drone-stat-value.green { color: var(--primary); }

    .impact-projects { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px; margin-top: 12px; }
    .impact-project { border: 1px solid var(--gray-200); border-radius: var(--radius); padding: 14px; }
    .impact-project-top { display: flex; justify-content: space-between; margin-bottom: 8px; }
    .impact-project-icon { width: 36px; height: 36px; border-radius: 8px; background: #fce7f3; color: var(--pink); display: grid; place-items: center; }
    .impact-project-status { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; background: var(--gray-100); color: var(--gray-500); }
    .impact-project-name { font-weight: 600; font-size: 0.9rem; margin-bottom: 4px; }
    .impact-project-desc { font-size: 0.78rem; color: var(--gray-500); margin-bottom: 12px; }
    .impact-project-footer { display: flex; justify-content: space-between; align-items: center; }
    .impact-funding { font-size: 0.75rem; color: var(--gray-500); }
    .impact-funding strong { color: var(--gray-900); }
    .impact-donate-btn { background: var(--pink); color: white; border: none; border-radius: 8px; padding: 6px 12px; font-size: 0.8rem; cursor: pointer; }

    .page-footer { text-align: center; padding: 24px 0; color: var(--gray-400); font-size: 0.8rem; }
    .page-footer a { color: var(--gray-500); }

    .toast {
      position: fixed; bottom: 24px; right: 24px; background: var(--gray-900); color: white;
      padding: 12px 18px; border-radius: 10px; font-size: 0.9rem; z-index: 100; max-width: 320px;
      animation: fadeIn .3s ease;
    }
  </style>
</head>
<body>
  <div class="app-container">
    <header class="top-bar">
      <div class="brand">
        <div class="brand-icon">⬡</div>
        <div class="brand-text">
          <h1>Mwarokin <span>Estates</span></h1>
          <div class="tagline">Advanced Payments · Page 13</div>
        </div>
      </div>
      <div class="nav-actions">
        <a href="#" class="nav-link"><i class="fas fa-chart-pie"></i> Dashboard</a>
        <a href="#" class="nav-link"><i class="fas fa-file-invoice"></i> Invoices</a>
        <a href="#" class="nav-link active"><i class="fas fa-seedling"></i> Growth & Legacy</a>
        <div class="avatar" title="Landlord Admin">AD</div>
      </div>
    </header>

    <div class="page-header">
      <h2><i class="fas fa-seedling"></i> Legacy, Growth & Social Impact</h2>
      <p>Estate planning, crowdfunding, AI lease analysis, tenant wellness, tax optimization, drone surveys, and community impact.</p>
    </div>

    <!-- Estate -->
    <div class="estate-hero fade-in">
      <div class="estate-header">
        <div>
          <h3><i class="fas fa-scroll"></i> Estate Planning & Will Manager</h3>
          <p style="font-size:13px;color:var(--gray-500)">Secure your legacy with legally-binding wills, trusts, and beneficiary management.</p>
        </div>
        <div class="estate-progress-ring">
          <div class="epr-value" id="planPct">—</div>
          <div class="epr-label">Plan Complete</div>
        </div>
      </div>
      <div class="estate-stats" id="estateStats"></div>
    </div>
    <div class="estate-grid">
      <div class="estate-card fade-in">
        <div class="section-title"><i class="fas fa-users"></i> Beneficiaries & Distribution</div>
        <div class="beneficiary-list" id="beneficiaryList"></div>
      </div>
      <div class="estate-card fade-in">
        <div class="section-title"><i class="fas fa-file-signature"></i> Legal Documents Progress</div>
        <div class="doc-progress" id="docProgress"></div>
      </div>
    </div>

    <!-- Crowdfunding -->
    <div class="crowdfund-panel fade-in">
      <div class="section-title"><i class="fas fa-rocket"></i> Property Crowdfunding Launchpad</div>
      <p style="font-size:13px;color:var(--gray-500);margin-bottom:4px">Launch and manage real estate crowdfunding campaigns.</p>
      <div class="crowdfund-grid" id="crowdfundGrid"></div>
    </div>

    <!-- Lease AI -->
    <div class="lease-analyzer-panel fade-in">
      <div class="section-title"><i class="fas fa-file-search"></i> AI Lease Abstraction & Clause Analyzer</div>
      <p style="font-size:13px;color:var(--gray-500)">Upload lease agreements and let AI extract key clauses and flag risks.</p>
      <div class="analyzer-layout">
        <div class="upload-zone" id="uploadZone">
          <i class="fas fa-cloud-upload-alt"></i>
          <h4>Upload Lease Agreement</h4>
          <p>PDF, DOCX, or scanned images</p>
          <button class="upload-btn" id="analyzeBtn"><i class="fas fa-upload"></i> Analyze Sample</button>
        </div>
        <div class="analysis-results" id="analysisResults">
          <p style="color:var(--gray-500);font-size:0.85rem;padding:20px 0">Run analysis to see clause risks.</p>
        </div>
      </div>
    </div>

    <!-- Wellness -->
    <div class="wellness-services-panel fade-in">
      <div class="ws-header">
        <div>
          <h3><i class="fas fa-heart-pulse"></i> Tenant Wellness & Social Services</h3>
          <p style="font-size:13px;color:var(--gray-500)">Connect tenants with health, education, and social support.</p>
        </div>
      </div>
      <div class="ws-stats" id="wsStats"></div>
      <div class="ws-services-grid" id="wsServicesGrid"></div>
    </div>

    <!-- Tax -->
    <div class="tax-optimizer-panel fade-in">
      <div class="section-title"><i class="fas fa-piggy-bank"></i> Landlord Tax Optimization Engine</div>
      <p style="font-size:13px;color:var(--gray-500)">AI-powered, KRA-compliant recommendations.</p>
      <div class="optimizer-hero">
        <div class="optimizer-hero-icon"><i class="fas fa-lightbulb"></i></div>
        <div class="optimizer-hero-text">
          <h4>Optimization Opportunity</h4>
          <p>Apply recommendations before June 30, 2025 for maximum savings.</p>
        </div>
        <div class="optimizer-savings">
          <div class="os-value" id="taxPotential">—</div>
          <div class="os-label">Potential Savings</div>
        </div>
      </div>
      <div class="optimization-list" id="optimizationList"></div>
    </div>

    <!-- Drone -->
    <div class="drone-panel fade-in">
      <div class="section-title"><i class="fas fa-satellite"></i> Property Drone Survey & Mapping</div>
      <p style="font-size:13px;color:var(--gray-500)">Aerial surveys for mapping and progress tracking.</p>
      <div class="drone-layout">
        <div>
          <div class="drone-map">
            <div class="drone-map-content">
              <i class="fas fa-map-marked-alt" style="font-size:2rem"></i>
              <div class="dmc-label">Kilimani Court · Aerial View</div>
              <div class="dmc-sub">Last survey: Apr 8, 2025 · 4K Orthomosaic</div>
            </div>
            <div class="drone-pin" style="top:30%;left:40%"></div>
            <div class="drone-pin" style="top:55%;left:65%;animation-delay:.5s"></div>
            <div class="drone-pin" style="top:70%;left:25%;animation-delay:1s"></div>
          </div>
          <div class="drone-surveys-list" id="droneSurveysList"></div>
        </div>
        <div class="drone-stats" id="droneStats"></div>
      </div>
    </div>

    <!-- Impact -->
    <div class="impact-panel fade-in">
      <div class="impact-header">
        <div>
          <h3><i class="fas fa-hand-holding-heart"></i> Mwarokin Impact & Community Fund</h3>
          <p style="font-size:13px;color:var(--gray-500)">A portion of management fees supports local impact projects.</p>
        </div>
      </div>
      <div class="impact-stats" id="impactStats"></div>
      <div class="impact-projects" id="impactProjects"></div>
    </div>

    <div class="page-footer">
      <p>Mwarokin Estates · Legacy, Growth & Social Impact · © 2025 · <a href="#">Privacy</a> · <a href="#">Terms</a></p>
    </div>
  </div>

  <script>
    const API = '';

    function toast(msg) {
      const el = document.createElement('div');
      el.className = 'toast';
      el.textContent = msg;
      document.body.appendChild(el);
      setTimeout(() => el.remove(), 3000);
    }

    async function api(path, opts = {}) {
      const res = await fetch(API + path, {
        headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
        ...opts,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const detail = err.detail;
        throw new Error(typeof detail === 'string' ? detail : (detail?.[0]?.msg || res.statusText));
      }
      return res.json();
    }

    function formatKsh(v) {
      return 'KSh ' + Number(v).toLocaleString('en-KE');
    }
    function formatMillions(v) {
      return 'KSh ' + (v / 1e6).toFixed(1) + 'M';
    }

    // ----- Estate -----
    async function renderEstate() {
      const data = await api('/api/estate');
      document.getElementById('planPct').textContent = data.plan_complete_pct + '%';
      document.getElementById('estateStats').innerHTML = data.stats.map(s => `
        <div class="estate-stat">
          <div class="es-label">${s.label}</div>
          <div class="es-value">${s.value}</div>
          <div class="es-sub">${s.sub}</div>
        </div>`).join('');
      document.getElementById('beneficiaryList').innerHTML = data.beneficiaries.map(b => `
        <div class="beneficiary">
          <div class="beneficiary-avatar" style="background:${b.color}">${b.initials}</div>
          <div class="beneficiary-info">
            <div class="beneficiary-name">${b.name}</div>
            <div class="beneficiary-relation">${b.relation}</div>
          </div>
          <div class="beneficiary-share">
            <div class="bs-value">${b.share}</div>
            <div class="bs-label">Share</div>
          </div>
        </div>`).join('');
      document.getElementById('docProgress').innerHTML = data.documents.map(d => {
        const icon = d.state === 'done' ? 'fa-check' : d.state === 'progress' ? 'fa-clock' : 'fa-circle';
        const btn = d.state !== 'done'
          ? `<button class="doc-advance" onclick="advanceDoc('${d.id}')">Advance</button>`
          : '';
        return `
          <div class="doc-item">
            <div class="doc-check ${d.state}"><i class="fas ${icon}"></i></div>
            <div class="doc-info">
              <div class="doc-name">${d.name}</div>
              <div class="doc-status">${d.status}</div>
            </div>
            ${btn}
          </div>`;
      }).join('');
    }

    async function advanceDoc(id) {
      try {
        await api(`/api/estate/documents/${id}/advance`, { method: 'POST' });
        toast('📄 Document progressed');
        await renderEstate();
      } catch (e) { toast('⚠️ ' + e.message); }
    }

    // ----- Crowdfunding -----
    async function renderCrowdfunding() {
      const campaigns = await api('/api/campaigns');
      document.getElementById('crowdfundGrid').innerHTML = campaigns.map(c => `
        <div class="campaign-card fade-in">
          <div class="campaign-banner ${c.banner}">
            <i class="fas ${c.icon}"></i>
            <span class="campaign-status-badge">${c.status}</span>
          </div>
          <div class="campaign-body">
            <div class="campaign-name">${c.name}</div>
            <div class="campaign-location"><i class="fas fa-map-marker-alt"></i> ${c.location}</div>
            <div class="campaign-progress">
              <div class="campaign-progress-header">
                <span class="cph-raised">${formatMillions(c.raised)} raised</span>
                <span class="cph-target">of ${formatMillions(c.target)}</span>
              </div>
              <div class="campaign-progress-bar">
                <div class="campaign-progress-fill" style="width:${c.progress_pct}%"></div>
              </div>
            </div>
            <div class="campaign-meta">
              <div class="campaign-meta-item"><div class="cmi-label">Investors</div><div class="cmi-value">${c.investors}</div></div>
              <div class="campaign-meta-item"><div class="cmi-label">Min. Invest</div><div class="cmi-value green">${formatKsh(c.min_investment)}</div></div>
              <div class="campaign-meta-item"><div class="cmi-label">Deadline</div><div class="cmi-value">${c.deadline}</div></div>
            </div>
            <div class="campaign-actions">
              <button onclick="toast('📊 ${c.name}')"><i class="fas fa-info-circle"></i> Details</button>
              <button class="primary" onclick="invest('${c.id}', ${c.min_investment}, '${c.name.replace(/'/g, "\\'")}')"><i class="fas fa-coins"></i> Invest</button>
            </div>
          </div>
        </div>`).join('');
    }

    async function invest(id, minAmt, name) {
      try {
        await api(`/api/campaigns/${id}/invest`, {
          method: 'POST',
          body: JSON.stringify({ amount: minAmt }),
        });
        toast(`💰 Invested ${formatKsh(minAmt)} in ${name}`);
        await renderCrowdfunding();
      } catch (e) { toast('⚠️ ' + e.message); }
    }

    // ----- Lease AI -----
    async function renderAnalysis() {
      const data = await api('/api/lease/analysis');
      const el = document.getElementById('analysisResults');
      if (!data) {
        el.innerHTML = '<p style="color:var(--gray-500);font-size:0.85rem;padding:20px 0">Run analysis to see clause risks.</p>';
        return;
      }
      el.innerHTML = `
        <p style="font-size:0.8rem;color:var(--gray-500);margin-bottom:10px">
          Analyzed: <strong>${data.filename}</strong> · ${data.analyzed_at}
          · High: ${data.risk_summary.high} · Medium: ${data.risk_summary.medium} · Low: ${data.risk_summary.low}
        </p>
        ${data.items.map(a => `
          <div class="analysis-item risk-${a.severity}">
            <div class="analysis-header">
              <div class="analysis-title">${a.title}</div>
              <span class="analysis-severity ${a.severity}">${a.severity} risk</span>
            </div>
            <div class="analysis-desc">${a.desc}</div>
            <div class="analysis-clause">${a.clause}</div>
          </div>`).join('')}`;
    }

    async function runAnalysis() {
      try {
        await api('/api/lease/analyze?filename=Kilimani_Unit_3B_2025.pdf', { method: 'POST' });
        toast('📄 Lease analyzed');
        await renderAnalysis();
      } catch (e) { toast('⚠️ ' + e.message); }
    }

    // ----- Wellness -----
    async function renderWellness() {
      const [stats, services] = await Promise.all([
        api('/api/wellness/stats'),
        api('/api/wellness/services'),
      ]);
      document.getElementById('wsStats').innerHTML = stats.map(s => `
        <div class="ws-stat">
          <div class="wss-label">${s.label}</div>
          <div class="wss-value">${s.value}</div>
        </div>`).join('');
      document.getElementById('wsServicesGrid').innerHTML = services.map(s => `
        <div class="ws-service" onclick="enrollWellness('${s.id}', '${s.name.replace(/'/g, "\\'")}')">
          <div class="ws-service-icon"><i class="fas ${s.icon}"></i></div>
          <div class="ws-service-info">
            <div class="ws-service-name">${s.name}</div>
            <div class="ws-service-desc">${s.desc} · ${s.enrolled} enrolled</div>
          </div>
        </div>`).join('');
    }

    async function enrollWellness(id, name) {
      try {
        await api(`/api/wellness/services/${id}/enroll`, { method: 'POST' });
        toast(`❤️ Enrolled in ${name}`);
        await renderWellness();
      } catch (e) { toast('⚠️ ' + e.message); }
    }

    // ----- Tax -----
    async function renderTax() {
      const data = await api('/api/tax/recommendations');
      document.getElementById('taxPotential').textContent = data.potential_display;
      document.getElementById('optimizationList').innerHTML = data.items.map(o => `
        <div class="optimization-item">
          <div class="optimization-icon"><i class="fas ${o.icon}"></i></div>
          <div class="optimization-info">
            <div class="optimization-title">${o.title}</div>
            <div class="optimization-desc">${o.desc}</div>
          </div>
          <span class="optimization-savings-badge">${o.savings}</span>
          <button class="optimization-apply" ${o.applied ? 'disabled' : ''} onclick="applyTax('${o.id}')">
            ${o.applied ? 'Applied' : 'Apply'}
          </button>
        </div>`).join('');
    }

    async function applyTax(id) {
      try {
        await api(`/api/tax/recommendations/${id}/apply`, { method: 'POST' });
        toast('✅ Recommendation applied');
        await renderTax();
      } catch (e) { toast('⚠️ ' + e.message); }
    }

    // ----- Drone -----
    async function renderDrone() {
      const [stats, surveys] = await Promise.all([
        api('/api/drone/stats'),
        api('/api/drone/surveys'),
      ]);
      document.getElementById('droneStats').innerHTML = stats.map(s => `
        <div class="drone-stat-row">
          <div class="drone-stat-icon"><i class="fas ${s.label.includes('Area') ? 'fa-map' : s.label.includes('Images') ? 'fa-camera' : s.label.includes('3D') ? 'fa-cube' : 'fa-clock'}"></i></div>
          <div class="drone-stat-info">
            <div class="drone-stat-label">${s.label}</div>
            <div class="drone-stat-value ${s.color || ''}">${s.value}</div>
          </div>
        </div>`).join('');
      document.getElementById('droneSurveysList').innerHTML = surveys.map(s => `
        <div class="survey-item">
          <div class="survey-icon"><i class="fas ${s.icon}"></i></div>
          <div class="survey-info">
            <div class="survey-name">${s.name}</div>
            <div class="survey-date">${s.date}</div>
          </div>
          <button class="survey-action" onclick="toast('🛰️ ${s.name}')">View</button>
        </div>`).join('');
    }

    // ----- Impact -----
    async function renderImpact() {
      const [stats, projects] = await Promise.all([
        api('/api/impact/stats'),
        api('/api/impact/projects'),
      ]);
      document.getElementById('impactStats').innerHTML = stats.map(s => `
        <div class="impact-stat">
          <div class="is-label">${s.label}</div>
          <div class="is-value">${s.value}</div>
          <div class="is-sub">${s.sub}</div>
        </div>`).join('');
      document.getElementById('impactProjects').innerHTML = projects.map(p => `
        <div class="impact-project">
          <div class="impact-project-top">
            <div class="impact-project-icon"><i class="fas ${p.icon}"></i></div>
            <span class="impact-project-status">${p.status}</span>
          </div>
          <div class="impact-project-name">${p.name}</div>
          <div class="impact-project-desc">${p.desc}</div>
          <div class="impact-project-footer">
            <div class="impact-funding">
              <strong>${formatKsh(p.funding)}</strong><br/>of ${formatKsh(p.goal)} goal
            </div>
            <button class="impact-donate-btn" ${p.status === 'Completed' ? 'disabled style="opacity:.5"' : ''}
              onclick="donate('${p.id}', '${p.name.replace(/'/g, "\\'")}')">Donate</button>
          </div>
        </div>`).join('');
    }

    async function donate(id, name) {
      try {
        await api(`/api/impact/projects/${id}/donate`, {
          method: 'POST',
          body: JSON.stringify({ amount: 25000 }),
        });
        toast(`❤️ Donated KSh 25,000 to ${name}`);
        await renderImpact();
      } catch (e) { toast('⚠️ ' + e.message); }
    }

    // ----- Init -----
    async function init() {
      document.getElementById('analyzeBtn').addEventListener('click', (e) => {
        e.stopPropagation();
        runAnalysis();
      });
      document.getElementById('uploadZone').addEventListener('click', runAnalysis);

      await Promise.all([
        renderEstate(),
        renderCrowdfunding(),
        renderAnalysis(),
        renderWellness(),
        renderTax(),
        renderDrone(),
        renderImpact(),
      ]);
      console.log('🌱 Mwarokin Estates · Legacy, Growth & Social Impact ready (real API)');
    }

    document.addEventListener('DOMContentLoaded', init);
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    return FRONTEND_HTML


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

### Real behaviour

| Feature | Real actions |
|---------|----------------|
| **Estate planning** | Plan % recomputed from document states; **Advance** moves pending → progress → done |
| **Crowdfunding** | **Invest** (min amount) increases raised + investors; marks Funded at target |
| **Lease AI** | **Analyze** returns risk clauses + summary; stores last analysis |
| **Wellness** | **Enroll** increments enrolled count per service; stats update |
| **Tax opt** | **Apply** marks recommendation applied; potential savings shrink |
| **Drone** | List surveys + stats (view logs toast) |
| **Impact fund** | **Donate** (KSh 25k) updates project funding, your contribution, fund total; completes when goal met |

### Run

```bash
pip install fastapi "uvicorn[standard]" pydantic
uvicorn main:app --reload --port 8000
```

Open **http://127.0.0.1:8000** — all buttons and filters talk to the Python backend.