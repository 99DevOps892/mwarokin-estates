
"""
Mwarokin Estates - House Manager Portal
Modern Python backend with real-world features
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Set
from enum import Enum
import json
import asyncio
from collections import defaultdict

# ============================================================================
# Core Domain Models
# ============================================================================

class VettingStage(str, Enum):
    APPLICATION_REVIEW = "application_review"
    BACKGROUND_CHECK = "background_check"
    SKILLS_ASSESSMENT = "skills_assessment"
    TRIAL_SHIFT = "trial_shift"

class CandidateStatus(str, Enum):
    AVAILABLE = "available"
    TRAINING = "training"
    HIRED = "hired"

class ContractType(str, Enum):
    ONE_MONTH = "1 Month"
    THREE_MONTHS = "3 Months"
    SIX_MONTHS = "6 Months"
    TWELVE_MONTHS = "12 Months"
    OPEN_ENDED = "Open-ended"

class WorkType(str, Enum):
    LIVE_IN = "Live-in"
    LIVE_OUT_DAILY = "Live-out, daily"
    PART_TIME = "Part-time"

class PaymentStatus(str, Enum):
    PAID = "paid"
    PENDING = "pending"
    OVERDUE = "overdue"

@dataclass
class VettingProgress:
    """Tracks candidate vetting progress through four stages"""
    background_check: bool = False
    reference_verification: bool = False
    skills_assessment: bool = False
    trial_shift: bool = False

    @property
    def score(self) -> int:
        return sum([
            self.background_check,
            self.reference_verification,
            self.skills_assessment,
            self.trial_shift
        ])

    @property
    def is_complete(self) -> bool:
        return self.score == 4

    def advance_to_next(self) -> Optional[VettingStage]:
        """Advance to next vetting stage, return None if complete"""
        if not self.background_check:
            return VettingStage.BACKGROUND_CHECK
        if not self.reference_verification:
            return VettingStage.SKILLS_ASSESSMENT
        if not self.skills_assessment:
            return VettingStage.TRIAL_SHIFT
        if not self.trial_shift:
            return None  # Complete, but still tracked
        return None

@dataclass
class Candidate:
    """House manager candidate with full profile"""
    id: int
    name: str
    age: int
    years_experience: int
    specialties: Set[str]
    expected_rate: int  # KES per month
    status: CandidateStatus
    vetting: VettingProgress
    bio: str
    colors: List[str] = field(default_factory=lambda: ["#2f5943", "#c9a24b"])
    is_gold: bool = False  # Gold-star candidates

    def __post_init__(self):
        self.specialties = set(self.specialties) if not isinstance(self.specialties, set) else self.specialties

    @property
    def display_rate(self) -> str:
        return f"{self.expected_rate:,}"

    @property
    def initials(self) -> str:
        parts = self.name.split()
        return "".join(p[0] for p in parts[:2]).upper()

    @classmethod
    def from_dict(cls, data: dict) -> "Candidate":
        return cls(
            id=data["id"],
            name=data["name"],
            age=data["age"],
            years_experience=data["exp"],
            specialties=set(data.get("specialties", [])),
            expected_rate=int(data.get("rate", "0").replace(",", "")),
            status=CandidateStatus(data.get("status", "available")),
            vetting=VettingProgress(**data.get("vet", {})),
            bio=data.get("bio", ""),
            colors=data.get("colors", ["#2f5943", "#c9a24b"]),
            is_gold=data.get("gold", 0) == 1
        )

@dataclass
class SchedulePlacement:
    """Confirmed schedule for a candidate"""
    candidate_id: int
    candidate_name: str
    property_name: str
    role: str
    start_date: date
    contract_length: ContractType
    is_active: bool = True

    @property
    def status_display(self) -> str:
        return "Active" if self.is_active else "Upcoming"

    @property
    def status_class(self) -> str:
        return "available" if self.is_active else "training"

@dataclass
class PaymentRecord:
    """Monthly payment record for a staff member"""
    staff_id: int
    staff_name: str
    property_name: str
    period: str  # e.g., "July 2026"
    amount: int
    method: str
    status: PaymentStatus

@dataclass
class Message:
    """Chat message in a thread"""
    sender: str  # "me" or "them"
    text: str
    timestamp: datetime

    def to_dict(self) -> dict:
        return {
            "from": self.sender,
            "text": self.text,
            "time": self.timestamp.strftime("%I:%M%p").lstrip("0").lower()
        }

@dataclass
class MessageThread:
    """Chat thread between estate owner and a staff member"""
    id: int
    staff_name: str
    messages: List[Message]

    @property
    def last_message(self) -> Optional[str]:
        if not self.messages:
            return None
        return self.messages[-1].text[:60]

    def add_message(self, sender: str, text: str) -> None:
        self.messages.append(Message(sender=sender, text=text, timestamp=datetime.now()))

# ============================================================================
# Repository Layer (in-memory with query capabilities)
# ============================================================================

class CandidateRepository:
    """Repository for managing candidates with filtering capabilities"""

    def __init__(self, candidates: List[Candidate]):
        self._candidates = {c.id: c for c in candidates}
        self._available_specialties = self._compute_specialties()

    def _compute_specialties(self) -> Set[str]:
        result = set()
        for c in self._candidates.values():
            result.update(c.specialties)
        return result

    @property
    def all_specialties(self) -> List[str]:
        return sorted(self._available_specialties)

    def get_by_id(self, candidate_id: int) -> Optional[Candidate]:
        return self._candidates.get(candidate_id)

    def get_all(self) -> List[Candidate]:
        return list(self._candidates.values())

    def get_by_ids(self, ids: List[int]) -> List[Candidate]:
        return [self._candidates[i] for i in ids if i in self._candidates]

    def filter_by_specialty(self, specialty: Optional[str] = None) -> List[Candidate]:
        if not specialty:
            return self.get_all()
        return [c for c in self._candidates.values() if specialty in c.specialties]

    def search(self, query: str, specialty: Optional[str] = None) -> List[Candidate]:
        """Search candidates by name or specialty, optionally filtered by specialty"""
        q = query.lower()
        candidates = self.filter_by_specialty(specialty)
        if not q:
            return candidates
        return [
            c for c in candidates
            if q in c.name.lower() or any(q in s.lower() for s in c.specialties)
        ]

    def get_by_status(self, status: CandidateStatus) -> List[Candidate]:
        return [c for c in self._candidates.values() if c.status == status]

    def add_candidate(self, candidate: Candidate) -> None:
        self._candidates[candidate.id] = candidate

    def update_status(self, candidate_id: int, status: CandidateStatus) -> Optional[Candidate]:
        if candidate_id not in self._candidates:
            return None
        self._candidates[candidate_id].status = status
        return self._candidates[candidate_id]


# ============================================================================
# Service Layer (business logic)
# ============================================================================

class VettingService:
    """Business logic for candidate vetting pipeline"""

    @staticmethod
    def get_vetting_stage(candidate: Candidate) -> Optional[VettingStage]:
        """Determine which vetting stage a candidate is currently in"""
        v = candidate.vetting
        if not v.background_check:
            return VettingStage.APPLICATION_REVIEW
        if not v.reference_verification:
            return VettingStage.BACKGROUND_CHECK
        if not v.skills_assessment:
            return VettingStage.SKILLS_ASSESSMENT
        if not v.trial_shift:
            return VettingStage.TRIAL_SHIFT
        return None  # Complete

    @staticmethod
    def get_pipeline_counts(candidates: List[Candidate]) -> Dict[VettingStage, int]:
        """Get count of candidates in each vetting stage"""
        counts = defaultdict(int)
        for c in candidates:
            stage = VettingService.get_vetting_stage(c)
            if stage is not None:
                counts[stage] += 1
        return dict(counts)

    @staticmethod
    def advance_candidate(candidate: Candidate) -> Optional[VettingStage]:
        """Advance a candidate to the next vetting stage if possible"""
        v = candidate.vetting
        if not v.background_check:
            v.background_check = True
            return VettingStage.BACKGROUND_CHECK
        if not v.reference_verification:
            v.reference_verification = True
            return VettingStage.SKILLS_ASSESSMENT
        if not v.skills_assessment:
            v.skills_assessment = True
            return VettingStage.TRIAL_SHIFT
        if not v.trial_shift:
            v.trial_shift = True
            return None  # Complete
        return None


class HireService:
    """Business logic for hiring and scheduling"""

    def __init__(self):
        self._placements: List[SchedulePlacement] = []

    @property
    def active_placements(self) -> List[SchedulePlacement]:
        return [p for p in self._placements if p.is_active]

    @property
    def upcoming_placements(self) -> List[SchedulePlacement]:
        return [p for p in self._placements if not p.is_active]

    def hire_candidate(
        self,
        candidate: Candidate,
        property_name: str,
        role: str,
        start_date: date,
        contract_length: ContractType
    ) -> SchedulePlacement:
        """Create a new schedule placement for a candidate"""
        placement = SchedulePlacement(
            candidate_id=candidate.id,
            candidate_name=candidate.name,
            property_name=property_name,
            role=role,
            start_date=start_date,
            contract_length=contract_length,
            is_active=True
        )
        candidate.status = CandidateStatus.HIRED
        self._placements.append(placement)
        return placement

    def get_placement_count(self) -> int:
        return len(self.active_placements)


class PaymentService:
    """Business logic for payroll management"""

    @staticmethod
    def calculate_monthly_payroll(placements: List[SchedulePlacement]) -> int:
        """Calculate total monthly payroll for active staff"""
        # In a real system, this would fetch salary data from staff records
        return sum(18000 for _ in placements)  # Placeholder

    @staticmethod
    def generate_payment_record(
        staff_name: str,
        property_name: str,
        amount: int,
        period: str
    ) -> PaymentRecord:
        return PaymentRecord(
            staff_id=0,  # Would be real ID in production
            staff_name=staff_name,
            property_name=property_name,
            period=period,
            amount=amount,
            method="M-Pesa",
            status=PaymentStatus.PENDING
        )


# ============================================================================
# Data Seeding
# ============================================================================

def seed_candidates() -> List[Candidate]:
    """Seed initial candidate data"""
    return [
        Candidate(
            id=1,
            name="Faith Wanjiru",
            age=29,
            years_experience=6,
            specialties={"Infant Care", "Cooking", "Cleaning"},
            expected_rate=18000,
            status=CandidateStatus.AVAILABLE,
            vetting=VettingProgress(True, True, True, True),
            bio=(
                "Faith has spent six years caring for infants and toddlers across three Nairobi households, "
                "including twins from birth to age two. Certified in infant first aid, she also runs a "
                "tight kitchen and keeps a spotless home."
            ),
            colors=["#2f5943", "#c9a24b"],
            is_gold=True
        ),
        Candidate(
            id=2,
            name="Daniel Kiptoo",
            age=34,
            years_experience=9,
            specialties={"Pet Care", "Car Cleaning", "Cleaning"},
            expected_rate=22000,
            status=CandidateStatus.AVAILABLE,
            vetting=VettingProgress(True, True, True, False),
            bio=(
                "Daniel has managed multi-pet households — dogs, cats and even a small aviary — "
                "while keeping vehicles showroom-clean. Nine years of experience with high-net-worth "
                "families across Karen and Runda."
            ),
            colors=["#1e3a2c", "#8fa692"]
        ),
        Candidate(
            id=3,
            name="Mercy Chebet",
            age=26,
            years_experience=4,
            specialties={"Laundry", "School Run", "Cleaning"},
            expected_rate=15500,
            status=CandidateStatus.TRAINING,
            vetting=VettingProgress(True, True, False, False),
            bio=(
                "Mercy is meticulous with garment care and fabric handling, and has a spotless driving "
                "record for school pick-ups. Currently completing her skills assessment."
            ),
            colors=["#2f5943", "#e7cd86"]
        ),
        Candidate(
            id=4,
            name="Samuel Mwangi",
            age=38,
            years_experience=11,
            specialties={"Cooking", "Infant Care", "Cleaning"},
            expected_rate=25000,
            status=CandidateStatus.AVAILABLE,
            vetting=VettingProgress(True, True, True, True),
            bio=(
                "Samuel trained as a chef before moving into private household management. "
                "Eleven years of experience, including three years caring for newborn twins "
                "alongside full home management."
            ),
            colors=["#a8452e", "#c9a24b"]
        ),
        Candidate(
            id=5,
            name="Grace Achieng",
            age=24,
            years_experience=2,
            specialties={"Infant Care", "Cleaning"},
            expected_rate=13000,
            status=CandidateStatus.TRAINING,
            vetting=VettingProgress(False, False, False, False),
            bio=(
                "Grace is early in her career but comes highly recommended for her gentle patience "
                "with babies. Currently in application review."
            ),
            colors=["#1e3a2c", "#8fa692"]
        ),
        Candidate(
            id=6,
            name="Esther Adhiambo",
            age=31,
            years_experience=7,
            specialties={"Cooking", "Laundry", "Pet Care"},
            expected_rate=19500,
            status=CandidateStatus.TRAINING,
            vetting=VettingProgress(True, True, True, False),
            bio=(
                "Esther is on trial shift this week at Runda Residence, managing meals, laundry "
                "and two dogs simultaneously. Early feedback has been excellent."
            ),
            colors=["#2f5943", "#c9a24b"]
        ),
        Candidate(
            id=7,
            name="Peter Otieno",
            age=41,
            years_experience=13,
            specialties={"Car Cleaning", "School Run", "Pet Care"},
            expected_rate=21000,
            status=CandidateStatus.AVAILABLE,
            vetting=VettingProgress(True, True, True, True),
            bio=(
                "Peter has thirteen years managing vehicles, security-conscious school runs, "
                "and household pets for diplomatic families in Nairobi."
            ),
            colors=["#1e3a2c", "#e7cd86"]
        ),
        Candidate(
            id=8,
            name="Joyce Wambui",
            age=27,
            years_experience=5,
            specialties={"Infant Care", "Cooking", "Cleaning"},
            expected_rate=17000,
            status=CandidateStatus.TRAINING,
            vetting=VettingProgress(True, True, False, False),
            bio=(
                "Joyce specialises in newborn care and is scheduled for her infant CPR and safety "
                "certification this week."
            ),
            colors=["#2f5943", "#8fa692"]
        ),
        Candidate(
            id=9,
            name="Alice Nyambura",
            age=33,
            years_experience=8,
            specialties={"Cleaning", "Laundry", "Car Cleaning"},
            expected_rate=18500,
            status=CandidateStatus.TRAINING,
            vetting=VettingProgress(False, False, False, False),
            bio=(
                "Alice brings eight years of full-home management experience and is currently "
                "undergoing background verification."
            ),
            colors=["#a8452e", "#8fa692"]
        ),
    ]


def seed_schedule_placements() -> List[SchedulePlacement]:
    """Seed initial schedule placements"""
    return [
        SchedulePlacement(
            candidate_id=1,
            candidate_name="Faith Wanjiru",
            property_name="Karen Residence",
            role="Infant Care & Cooking",
            start_date=date(2026, 8, 1),
            contract_length=ContractType.TWELVE_MONTHS,
            is_active=True
        ),
        SchedulePlacement(
            candidate_id=4,
            candidate_name="Samuel Mwangi",
            property_name="Runda Residence",
            role="Cooking & Home Management",
            start_date=date(2026, 8, 15),
            contract_length=ContractType.SIX_MONTHS,
            is_active=True
        ),
        SchedulePlacement(
            candidate_id=6,
            candidate_name="Esther Adhiambo",
            property_name="Runda Residence",
            role="Cooking & Pet Care",
            start_date=date(2026, 8, 12),
            contract_length=ContractType.THREE_MONTHS,
            is_active=False
        ),
        SchedulePlacement(
            candidate_id=7,
            candidate_name="Peter Otieno",
            property_name="Lavington Home",
            role="Car Cleaning & School Run",
            start_date=date(2026, 9, 1),
            contract_length=ContractType.OPEN_ENDED,
            is_active=False
        ),
    ]


def seed_payment_records() -> List[PaymentRecord]:
    """Seed initial payment records"""
    return [
        PaymentRecord(
            staff_id=1,
            staff_name="Faith Wanjiru",
            property_name="Karen Residence",
            period="July 2026",
            amount=18000,
            method="M-Pesa",
            status=PaymentStatus.PAID
        ),
        PaymentRecord(
            staff_id=4,
            staff_name="Samuel Mwangi",
            property_name="Runda Residence",
            period="July 2026",
            amount=25000,
            method="Bank Transfer",
            status=PaymentStatus.PAID
        ),
        PaymentRecord(
            staff_id=2,
            staff_name="Daniel Kiptoo",
            property_name="Lavington Home",
            period="July 2026",
            amount=22000,
            method="M-Pesa",
            status=PaymentStatus.PENDING
        ),
        PaymentRecord(
            staff_id=7,
            staff_name="Peter Otieno",
            property_name="Lavington Home",
            period="June 2026",
            amount=21000,
            method="M-Pesa",
            status=PaymentStatus.OVERDUE
        ),
    ]


def seed_message_threads() -> List[MessageThread]:
    """Seed initial message threads"""
    return [
        MessageThread(
            id=1,
            staff_name="Faith Wanjiru",
            messages=[
                Message(
                    sender="them",
                    text="Good morning! Just checked in at the nursery.",
                    timestamp=datetime(2026, 8, 3, 7, 3)
                ),
                Message(
                    sender="me",
                    text="Morning Faith, thank you. How did the night feed go?",
                    timestamp=datetime(2026, 8, 3, 7, 10)
                ),
                Message(
                    sender="them",
                    text="Smoothly — both slept through until 5am.",
                    timestamp=datetime(2026, 8, 3, 7, 12)
                ),
                Message(
                    sender="them",
                    text="The twins are down for their nap now.",
                    timestamp=datetime(2026, 8, 3, 14, 11)
                ),
            ]
        ),
        MessageThread(
            id=2,
            staff_name="Samuel Mwangi",
            messages=[
                Message(
                    sender="them",
                    text="Good afternoon, checked in and starting on lunch.",
                    timestamp=datetime(2026, 8, 3, 7, 46)
                ),
                Message(
                    sender="them",
                    text="Shall I prep the lunch menu for Friday's guests?",
                    timestamp=datetime(2026, 8, 3, 12, 20)
                ),
            ]
        ),
        MessageThread(
            id=3,
            staff_name="Esther Adhiambo",
            messages=[
                Message(
                    sender="them",
                    text="Trial shift went well today, thank you for the opportunity.",
                    timestamp=datetime(2026, 8, 3, 17, 40)
                ),
            ]
        ),
    ]


# ============================================================================
# Application Container (DI-like setup)
# ============================================================================

class Application:
    """Main application container managing all services"""

    def __init__(self):
        # Repositories
        self.candidate_repo = CandidateRepository(seed_candidates())

        # Services
        self.vetting_service = VettingService()
        self.hire_service = HireService()
        self.payment_service = PaymentService()

        # Seed data
        for placement in seed_schedule_placements():
            self.hire_service._placements.append(placement)

        self.payment_records = seed_payment_records()
        self.message_threads = seed_message_threads()

    @property
    def active_staff_count(self) -> int:
        return len(self.hire_service.active_placements)

    @property
    def pending_applications_count(self) -> int:
        return len(self.candidate_repo.filter_by_specialty(None))  # Simplified

    @property
    def in_vetting_count(self) -> int:
        return len([c for c in self.candidate_repo.get_all() if c.status == CandidateStatus.TRAINING])

    def get_dashboard_summary(self) -> dict:
        """Get summary data for the dashboard"""
        return {
            "active_staff": self.active_staff_count,
            "pending_applications": self.pending_applications_count,
            "in_vetting": self.in_vetting_count,
            "starting_this_month": len([p for p in self.hire_service._placements if p.start_date.month == 8 and p.start_date.year == 2026])
        }

    def get_activity_timeline(self) -> List[Dict[str, Any]]:
        """Generate activity timeline for the monitor view"""
        return [
            {"time": "7:02am", "type": "in", "text": "Faith Wanjiru checked in", "sub": "Karen Residence — Nursery"},
            {"time": "7:45am", "type": "in", "text": "Samuel Mwangi checked in", "sub": "Runda Residence — Kitchen"},
            {"time": "9:15am", "type": "out", "text": "Peter Otieno departed for school run", "sub": "Lavington Home"},
            {"time": "11:30am", "type": "alert", "text": "Gate sensor triggered — resolved", "sub": "Karen Residence — verified by Faith"},
            {"time": "1:00pm", "type": "in", "text": "Peter Otieno returned from school run", "sub": "Lavington Home"},
            {"time": "2:10pm", "type": "out", "text": "Nursery marked quiet — nap time", "sub": "Karen Residence"},
        ]


# ============================================================================
# API Layer (FastAPI-style endpoints)
# ============================================================================

# This would be the FastAPI router in a real application

app = Application()


# Example API endpoints:
def get_candidates(specialty: Optional[str] = None, search: Optional[str] = None) -> List[dict]:
    """Get candidates with optional filtering"""
    if search:
        candidates = app.candidate_repo.search(search, specialty)
    else:
        candidates = app.candidate_repo.filter_by_specialty(specialty)
    # Convert to dictionaries for JSON serialization
    return [
        {
            "id": c.id,
            "name": c.name,
            "age": c.age,
            "exp": c.years_experience,
            "specialties": list(c.specialties),
            "rate": c.display_rate,
            "status": c.status.value,
            "vet": {
                "background": c.vetting.background_check,
                "refs": c.vetting.reference_verification,
                "skills": c.vetting.skills_assessment,
                "trial": c.vetting.trial_shift
            },
            "bio": c.bio,
            "colors": c.colors,
            "gold": 1 if c.is_gold else 0
        }
        for c in candidates
    ]


def get_dashboard_data() -> dict:
    """Get all dashboard data"""
    return {
        "summary": app.get_dashboard_summary(),
        "overview_ids": [1, 4, 7],  # Recommended for Karen Residence
        "candidates": get_candidates(),
        "schedule": [
            {
                "name": p.candidate_name,
                "property": p.property_name,
                "role": p.role,
                "date": p.start_date.strftime("%d %b %Y"),
                "length": p.contract_length.value,
                "status": p.status_display
            }
            for p in app.hire_service._placements
        ],
        "payments": [
            {
                "name": p.staff_name,
                "property": p.property_name,
                "period": p.period,
                "amount": f"{p.amount:,}",
                "method": p.method,
                "status": p.status.value
            }
            for p in app.payment_records
        ],
        "timeline": app.get_activity_timeline(),
        "threads": [
            {
                "id": t.id,
                "name": t.staff_name,
                "last": t.last_message,
                "messages": [m.to_dict() for m in t.messages]
            }
            for t in app.message_threads
        ]
    }


# ============================================================================
# Entry point
# ============================================================================

if __name__ == "__main__":
    # Demonstrate the system
    print("=== Mwarokin Estates - House Manager Portal ===")
    print(f"Active Staff: {app.active_staff_count}")
    print(f"Pending Applications: {app.pending_applications_count}")
    print(f"In Vetting: {app.in_vetting_count}")

    print("\n=== Available Candidates ===")
    for c in app.candidate_repo.get_by_status(CandidateStatus.AVAILABLE):
        print(f"  {c.name} ({c.age}) - {', '.join(c.specialties)} - KES {c.display_rate}")

    print("\n=== Pipeline Counts ===")
    counts = app.vetting_service.get_pipeline_counts(app.candidate_repo.get_all())
    for stage, count in counts.items():
        print(f"  {stage.value}: {count}")

    print("\n=== Active Placements ===")
    for p in app.hire_service.active_placements:
        print(f"  {p.candidate_name} at {p.property_name} - {p.role} - starts {p.start_date}")

    print("\n=== System Ready ===")
