
#!/usr/bin/env python3
"""
Parking.py — Agentic Parking Pavilion Manager for Mwarokin Estates
Modern, fully functional, type-hinted, asyncio-native agent system.
"""

from __future__ import annotations

import asyncio
import json
import random
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, date, time
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

# ---------------------------------------------------------------------------
# Domain Models
# ---------------------------------------------------------------------------

class SpotStatus(str, Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"


class SpotType(str, Enum):
    STANDARD = "standard"
    PREMIUM = "premium"


class ReservationStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class VehicleType(str, Enum):
    CAR = "car"
    SUV = "suv"
    TRUCK = "truck"
    MOTORCYCLE = "motorcycle"


class Wing(str, Enum):
    A = "WING · A"
    B = "WING · B"
    C = "WING · C"
    V = "WING · V"


@dataclass(slots=True)
class Spot:
    id: str
    status: SpotStatus = SpotStatus.AVAILABLE
    type: SpotType = SpotType.STANDARD

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "status": self.status.value, "type": self.type.value}


@dataclass(slots=True)
class Location:
    id: str
    name: str
    zone: Wing
    total_spots: int
    spots: List[Spot] = field(default_factory=list)

    @property
    def available_count(self) -> int:
        return sum(1 for s in self.spots if s.status == SpotStatus.AVAILABLE)

    @property
    def occupied_count(self) -> int:
        return sum(1 for s in self.spots if s.status == SpotStatus.OCCUPIED)

    @property
    def reserved_count(self) -> int:
        return sum(1 for s in self.spots if s.status == SpotStatus.RESERVED)

    @property
    def percent_full(self) -> int:
        if not self.spots:
            return 0
        non_available = len(self.spots) - self.available_count
        return round((non_available / len(self.spots)) * 100)

    def find_spot(self, spot_id: str) -> Optional[Spot]:
        return next((s for s in self.spots if s.id == spot_id), None)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "zone": self.zone.value,
            "totalSpots": self.total_spots,
            "spots": [s.to_dict() for s in self.spots],
            "available": self.available_count,
            "percentFull": self.percent_full,
        }


@dataclass(slots=True)
class User:
    id: str
    full_name: str
    email: str
    phone: str
    password_hash: str  # in real systems use bcrypt/argon2
    vehicle_type: VehicleType
    license_plate: str
    created_at: datetime = field(default_factory=datetime.utcnow)

    def initials(self) -> str:
        return "".join(p[0] for p in self.full_name.split() if p).upper()[:2]

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "fullName": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "vehicleType": self.vehicle_type.value,
            "licensePlate": self.license_plate,
            "initials": self.initials(),
        }


@dataclass(slots=True)
class Reservation:
    id: str
    user_id: str
    spot_id: str
    location_id: str
    location_name: str
    date: date
    time: time
    duration_hours: int
    amount_kes: int
    status: ReservationStatus = ReservationStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "spotId": self.spot_id,
            "location": self.location_name,
            "date": self.date.isoformat(),
            "time": self.time.strftime("%H:%M"),
            "duration": self.duration_hours,
            "status": self.status.value,
            "amount": self.amount_kes,
        }


# ---------------------------------------------------------------------------
# Persistence (simple JSON file store – replace with DB in production)
# ---------------------------------------------------------------------------

class JsonStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"users": {}, "reservations": []})

    def _read(self) -> Dict[str, Any]:
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: Dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def save_user(self, user: User) -> None:
        data = self._read()
        data["users"][user.id] = {
            **user.to_public_dict(),
            "password_hash": user.password_hash,
            "created_at": user.created_at.isoformat(),
        }
        self._write(data)

    def get_user_by_email(self, email: str) -> Optional[User]:
        data = self._read()
        for u in data["users"].values():
            if u["email"].lower() == email.lower():
                return User(
                    id=u["id"],
                    full_name=u["fullName"],
                    email=u["email"],
                    phone=u["phone"],
                    password_hash=u["password_hash"],
                    vehicle_type=VehicleType(u["vehicleType"]),
                    license_plate=u["licensePlate"],
                    created_at=datetime.fromisoformat(u["created_at"]),
                )
        return None

    def get_user(self, user_id: str) -> Optional[User]:
        data = self._read()
        u = data["users"].get(user_id)
        if not u:
            return None
        return User(
            id=u["id"],
            full_name=u["fullName"],
            email=u["email"],
            phone=u["phone"],
            password_hash=u["password_hash"],
            vehicle_type=VehicleType(u["vehicleType"]),
            license_plate=u["licensePlate"],
            created_at=datetime.fromisoformat(u["created_at"]),
        )

    def save_reservation(self, res: Reservation) -> None:
        data = self._read()
        data["reservations"] = [r for r in data["reservations"] if r["id"] != res.id]
        data["reservations"].append(res.to_dict() | {"user_id": res.user_id, "location_id": res.location_id})
        self._write(data)

    def load_reservations(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        data = self._read()
        res = data["reservations"]
        if user_id:
            res = [r for r in res if r.get("user_id") == user_id]
        return res


# ---------------------------------------------------------------------------
# Core Parking Ledger
# ---------------------------------------------------------------------------

class ParkingLedger:
    RATE_PER_HOUR = 200  # KSh

    def __init__(self) -> None:
        self.locations: Dict[str, List[Location]] = {
            "apartments": [],
            "commercial": [],
            "public": [],
        }
        self._build_estate()

    def _build_estate(self) -> None:
        # Wing A – Villa A Residences
        self.locations["apartments"].append(
            Location(
                id="villa-a",
                name="Villa A Residences",
                zone=Wing.A,
                total_spots=80,
                spots=[
                    Spot("A1"), Spot("A2", SpotStatus.OCCUPIED),
                    Spot("A3"), Spot("A4", SpotStatus.RESERVED, SpotType.PREMIUM),
                    Spot("A5", SpotStatus.OCCUPIED), Spot("A6"),
                    Spot("A7", SpotStatus.OCCUPIED), Spot("A8", type=SpotType.PREMIUM),
                ],
            )
        )
        # Wing B – Villa B Residences
        self.locations["apartments"].append(
            Location(
                id="villa-b",
                name="Villa B Residences",
                zone=Wing.B,
                total_spots=60,
                spots=[
                    Spot("B1"), Spot("B2", SpotStatus.OCCUPIED),
                    Spot("B3"), Spot("B4", SpotStatus.OCCUPIED),
                    Spot("B5", type=SpotType.PREMIUM), Spot("B6", SpotStatus.OCCUPIED),
                    Spot("B7"), Spot("B8", SpotStatus.RESERVED, SpotType.PREMIUM),
                ],
            )
        )
        # Wing C – Commercial
        self.locations["commercial"].append(
            Location(
                id="commercial-building",
                name="Commercial Court",
                zone=Wing.C,
                total_spots=120,
                spots=[
                    Spot("C1", SpotStatus.OCCUPIED), Spot("C2", SpotStatus.OCCUPIED),
                    Spot("C3", SpotStatus.OCCUPIED), Spot("C4"),
                    Spot("C5", SpotStatus.OCCUPIED), Spot("C6", SpotStatus.OCCUPIED),
                    Spot("C7", SpotStatus.OCCUPIED), Spot("C8", type=SpotType.PREMIUM),
                ],
            )
        )
        # Wing V – Visitor
        self.locations["public"].append(
            Location(
                id="public-parking",
                name="Visitor Court",
                zone=Wing.V,
                total_spots=200,
                spots=[
                    Spot("P1"), Spot("P2", SpotStatus.OCCUPIED),
                    Spot("P3"), Spot("P4", SpotStatus.OCCUPIED),
                    Spot("P5"), Spot("P6", SpotStatus.OCCUPIED),
                    Spot("P7"), Spot("P8", SpotStatus.RESERVED, SpotType.PREMIUM),
                ],
            )
        )

    def all_locations(self) -> List[Location]:
        return [loc for group in self.locations.values() for loc in group]

    def get_location(self, location_id: str) -> Optional[Location]:
        for loc in self.all_locations():
            if loc.id == location_id:
                return loc
        return None

    def find_spot(self, spot_id: str, location_id: Optional[str] = None) -> Tuple[Optional[Location], Optional[Spot]]:
        candidates = [self.get_location(location_id)] if location_id else self.all_locations()
        for loc in candidates:
            if loc is None:
                continue
            spot = loc.find_spot(spot_id)
            if spot:
                return loc, spot
        return None, None

    def find_first_available(self) -> Optional[Tuple[Location, Spot]]:
        for loc in self.all_locations():
            for spot in loc.spots:
                if spot.status == SpotStatus.AVAILABLE:
                    return loc, spot
        return None

    def update_spot_status(self, spot_id: str, new_status: SpotStatus, location_id: Optional[str] = None) -> bool:
        loc, spot = self.find_spot(spot_id, location_id)
        if spot is None:
            return False
        spot.status = new_status
        return True

    def stats(self) -> Dict[str, Any]:
        total = occupied = reserved = 0
        for loc in self.all_locations():
            total += len(loc.spots)
            occupied += loc.occupied_count
            reserved += loc.reserved_count
        pct = round(((occupied + reserved) / total) * 100) if total else 0
        return {
            "baysTracked": 460,  # estate capacity (demo uses sample spots)
            "occupancyPct": pct,
            "reservedToday": reserved,
            "avgRate": 520,
            "sampleSpots": total,
        }

    def filter_locations(self, wing_key: str = "all", search: str = "", status: str = "all") -> List[Dict[str, Any]]:
        if wing_key == "all":
            locs = self.all_locations()
        else:
            locs = self.locations.get(wing_key, [])

        result = []
        for loc in locs:
            if search and search.lower() not in loc.name.lower() and search.lower() not in loc.zone.value.lower():
                continue
            d = loc.to_dict()
            if status != "all":
                d["spots"] = [s for s in d["spots"] if s["status"] == status]
            result.append(d)
        return result


# ---------------------------------------------------------------------------
# Agentic Layer
# ---------------------------------------------------------------------------

class AgentMessage:
    def __init__(self, role: str, content: str, data: Any = None) -> None:
        self.role = role
        self.content = content
        self.data = data
        self.timestamp = datetime.utcnow()


class Agent(Protocol):
    name: str
    async def handle(self, message: AgentMessage, context: "AgentContext") -> AgentMessage: ...


@dataclass
class AgentContext:
    ledger: ParkingLedger
    store: JsonStore
    current_user: Optional[User] = None
    history: List[AgentMessage] = field(default_factory=list)

    def log(self, msg: AgentMessage) -> None:
        self.history.append(msg)


class AuthAgent:
    name = "AuthAgent"

    async def handle(self, message: AgentMessage, ctx: AgentContext) -> AgentMessage:
        action = message.data.get("action") if message.data else None

        if action == "register":
            payload = message.data
            if payload["password"] != payload.get("confirm_password"):
                return AgentMessage(self.name, "Passwords do not match", {"ok": False})
            existing = ctx.store.get_user_by_email(payload["email"])
            if existing:
                return AgentMessage(self.name, "Email already registered", {"ok": False})

            user = User(
                id=str(uuid.uuid4()),
                full_name=payload["full_name"],
                email=payload["email"],
                phone=payload["phone"],
                password_hash=f"hashed:{payload['password']}",  # replace with real hash
                vehicle_type=VehicleType(payload["vehicle_type"]),
                license_plate=payload["license_plate"].upper(),
            )
            ctx.store.save_user(user)
            ctx.current_user = user
            return AgentMessage(self.name, f"Welcome {user.full_name}!", {"ok": True, "user": user.to_public_dict()})

        if action == "login":
            user = ctx.store.get_user_by_email(message.data["email"])
            if not user or user.password_hash != f"hashed:{message.data['password']}":
                # Demo fallback for convenience
                if message.data["email"]:
                    user = User(
                        id="demo-user",
                        full_name="John Doe",
                        email=message.data["email"],
                        phone="+254700000000",
                        password_hash="hashed:demo",
                        vehicle_type=VehicleType.CAR,
                        license_plate="KAA 123A",
                    )
                    ctx.store.save_user(user)
                else:
                    return AgentMessage(self.name, "Invalid credentials", {"ok": False})
            ctx.current_user = user
            return AgentMessage(self.name, f"Logged in as {user.full_name}", {"ok": True, "user": user.to_public_dict()})

        if action == "logout":
            ctx.current_user = None
            return AgentMessage(self.name, "Logged out", {"ok": True})

        return AgentMessage(self.name, "Unknown auth action", {"ok": False})


class ReservationAgent:
    name = "ReservationAgent"

    async def handle(self, message: AgentMessage, ctx: AgentContext) -> AgentMessage:
        if not ctx.current_user:
            return AgentMessage(self.name, "Authentication required", {"ok": False, "code": 401})

        action = message.data.get("action")

        if action == "reserve":
            spot_id = message.data["spot_id"]
            location_id = message.data.get("location_id")
            loc, spot = ctx.ledger.find_spot(spot_id, location_id)
            if not spot or spot.status != SpotStatus.AVAILABLE:
                return AgentMessage(self.name, f"Bay {spot_id} is not available", {"ok": False})

            duration = int(message.data["duration_hours"])
            amount = duration * ParkingLedger.RATE_PER_HOUR
            res_date = date.fromisoformat(message.data["date"])
            res_time = time.fromisoformat(message.data["time"])

            reservation = Reservation(
                id=f"res-{uuid.uuid4().hex[:10]}",
                user_id=ctx.current_user.id,
                spot_id=spot_id,
                location_id=loc.id if loc else "",
                location_name=loc.name if loc else "Unknown",
                date=res_date,
                time=res_time,
                duration_hours=duration,
                amount_kes=amount,
            )
            ctx.ledger.update_spot_status(spot_id, SpotStatus.RESERVED, location_id)
            ctx.store.save_reservation(reservation)
            return AgentMessage(
                self.name,
                f"Bay {spot_id} reserved for {ctx.current_user.full_name}",
                {"ok": True, "reservation": reservation.to_dict()},
            )

        if action == "cancel":
            res_id = message.data["reservation_id"]
            all_res = ctx.store.load_reservations(ctx.current_user.id)
            target = next((r for r in all_res if r["id"] == res_id), None)
            if not target or target["status"] != "active":
                return AgentMessage(self.name, "Reservation not found or not active", {"ok": False})

            # Update store
            target["status"] = ReservationStatus.CANCELLED.value
            # Reconstruct and save
            res = Reservation(
                id=target["id"],
                user_id=ctx.current_user.id,
                spot_id=target["spotId"],
                location_id=target.get("location_id", ""),
                location_name=target["location"],
                date=date.fromisoformat(target["date"]),
                time=time.fromisoformat(target["time"]),
                duration_hours=target["duration"],
                amount_kes=target["amount"],
                status=ReservationStatus.CANCELLED,
            )
            ctx.store.save_reservation(res)
            ctx.ledger.update_spot_status(target["spotId"], SpotStatus.AVAILABLE)
            return AgentMessage(self.name, "Reservation cancelled", {"ok": True})

        if action == "list":
            res = ctx.store.load_reservations(ctx.current_user.id)
            return AgentMessage(self.name, "Your reservations", {"ok": True, "reservations": res})

        return AgentMessage(self.name, "Unknown reservation action", {"ok": False})


class OccupancyAgent:
    """Simulates live bay changes every few seconds (gate sensors / cameras)."""
    name = "OccupancyAgent"

    def __init__(self, interval: float = 10.0) -> None:
        self.interval = interval
        self._task: Optional[asyncio.Task] = None

    async def start(self, ctx: AgentContext) -> None:
        if self._task:
            return
        self._task = asyncio.create_task(self._loop(ctx))

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self, ctx: AgentContext) -> None:
        while True:
            await asyncio.sleep(self.interval)
            locs = ctx.ledger.all_locations()
            if not locs:
                continue
            loc = random.choice(locs)
            if not loc.spots:
                continue
            spot = random.choice(loc.spots)
            if spot.status == SpotStatus.AVAILABLE:
                spot.status = SpotStatus.OCCUPIED
            elif spot.status == SpotStatus.OCCUPIED:
                spot.status = SpotStatus.AVAILABLE
            # reserved stays reserved until cancelled / expired

    async def handle(self, message: AgentMessage, ctx: AgentContext) -> AgentMessage:
        return AgentMessage(self.name, "Occupancy simulation running", {"ok": True, "stats": ctx.ledger.stats()})


class ReportAgent:
    name = "ReportAgent"

    async def handle(self, message: AgentMessage, ctx: AgentContext) -> AgentMessage:
        stats = ctx.ledger.stats()
        wings = {}
        for key, group in ctx.ledger.locations.items():
            wings[key] = [
                {
                    "name": loc.name,
                    "zone": loc.zone.value,
                    "available": loc.available_count,
                    "occupied": loc.occupied_count,
                    "reserved": loc.reserved_count,
                    "percentFull": loc.percent_full,
                }
                for loc in group
            ]
        report = {
            "generatedAt": datetime.utcnow().isoformat() + "Z",
            "estate": "Mwarokin Estates – Parking Pavilion",
            "summary": stats,
            "wings": wings,
        }
        return AgentMessage(self.name, "Report generated", {"ok": True, "report": report})


class Orchestrator:
    """Central agent bus – routes intents to specialist agents."""

    def __init__(self, ledger: ParkingLedger, store: JsonStore) -> None:
        self.ctx = AgentContext(ledger=ledger, store=store)
        self.agents: Dict[str, Agent] = {
            "auth": AuthAgent(),
            "reservation": ReservationAgent(),
            "occupancy": OccupancyAgent(),
            "report": ReportAgent(),
        }
        self.occupancy = self.agents["occupancy"]  # type: ignore

    async def start(self) -> None:
        await self.occupancy.start(self.ctx)  # type: ignore

    async def stop(self) -> None:
        await self.occupancy.stop()  # type: ignore

    async def dispatch(self, intent: str, payload: Dict[str, Any] | None = None) -> AgentMessage:
        payload = payload or {}
        msg = AgentMessage("user", intent, payload)
        self.ctx.log(msg)

        if intent.startswith("auth."):
            agent = self.agents["auth"]
            payload["action"] = intent.split(".", 1)[1]
        elif intent.startswith("reservation."):
            agent = self.agents["reservation"]
            payload["action"] = intent.split(".", 1)[1]
        elif intent == "report.generate":
            agent = self.agents["report"]
        elif intent == "stats":
            agent = self.agents["occupancy"]
        else:
            return AgentMessage("Orchestrator", f"Unknown intent: {intent}", {"ok": False})

        reply = await agent.handle(msg, self.ctx)
        self.ctx.log(reply)
        return reply

    # Convenience façade matching UI actions
    async def register(self, **kwargs) -> AgentMessage:
        return await self.dispatch("auth.register", kwargs)

    async def login(self, email: str, password: str) -> AgentMessage:
        return await self.dispatch("auth.login", {"email": email, "password": password})

    async def logout(self) -> AgentMessage:
        return await self.dispatch("auth.logout")

    async def reserve(
        self,
        spot_id: str,
        date_str: str,
        time_str: str,
        duration_hours: int,
        location_id: str | None = None,
        name: str | None = None,
    ) -> AgentMessage:
        return await self.dispatch(
            "reservation.reserve",
            {
                "spot_id": spot_id,
                "location_id": location_id,
                "date": date_str,
                "time": time_str,
                "duration_hours": duration_hours,
                "name": name,
            },
        )

    async def cancel_reservation(self, reservation_id: str) -> AgentMessage:
        return await self.dispatch("reservation.cancel", {"reservation_id": reservation_id})

    async def my_reservations(self) -> AgentMessage:
        return await self.dispatch("reservation.list")

    async def generate_report(self) -> AgentMessage:
        return await self.dispatch("report.generate")

    def dashboard(self, wing: str = "all", search: str = "", status: str = "all") -> List[Dict[str, Any]]:
        return self.ctx.ledger.filter_locations(wing, search, status)

    def live_stats(self) -> Dict[str, Any]:
        return self.ctx.ledger.stats()


# ---------------------------------------------------------------------------
# Demo / CLI runner (replace with FastAPI / WebSocket bridge for real UI)
# ---------------------------------------------------------------------------

async def demo() -> None:
    store = JsonStore(Path("data/parking_store.json"))
    ledger = ParkingLedger()
    orch = Orchestrator(ledger, store)
    await orch.start()

    print("=== Mwarokin Estates Parking Pavilion – Agentic Core ===\n")

    # Register
    r = await orch.register(
        full_name="Jane Wanjiku",
        email="jane@mwarokin.ke",
        phone="+254712345678",
        password="secure123",
        confirm_password="secure123",
        vehicle_type="suv",
        license_plate="KDG 456B",
    )
    print("REGISTER →", r.content, r.data.get("ok"))

    # Login
    r = await orch.login("jane@mwarokin.ke", "secure123")
    print("LOGIN    →", r.content)

    # Dashboard snapshot
    cards = orch.dashboard(wing="all")
    print(f"\nLive bays: {len(cards)} locations")
    for c in cards:
        print(f"  • {c['name']} ({c['zone']}) — {c['available']} open, {c['percentFull']}% full")

    stats = orch.live_stats()
    print(f"\nStats → Occupancy {stats['occupancyPct']}% | Reserved {stats['reservedToday']}")

    # Reserve first available
    first = ledger.find_first_available()
    if first:
        loc, spot = first
        today = date.today().isoformat()
        r = await orch.reserve(
            spot_id=spot.id,
            location_id=loc.id,
            date_str=today,
            time_str="14:00",
            duration_hours=4,
        )
        print("RESERVE  →", r.content)

    # List reservations
    r = await orch.my_reservations()
    print("MY RES   →", len(r.data.get("reservations", [])), "items")

    # Report
    r = await orch.generate_report()
    print("REPORT   → generated at", r.data["report"]["generatedAt"])

    # Let occupancy agent tick once
    await asyncio.sleep(1)
    print("\n(Occupancy agent is live in background…)")

    await orch.stop()
    print("\nShutdown complete.")


if __name__ == "__main__":
    asyncio.run(demo())
