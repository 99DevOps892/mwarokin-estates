```python
from fastapi import FastAPI, HTTPException, Query, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime, timedelta
import uuid
import random
from enum import Enum

app = FastAPI(
    title="Mwarokin Estates - Keys & Locks API",
    description="Backend for Keys and Access Control Management",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enums
class KeyType(str, Enum):
    PHYSICAL = "physical"
    DIGITAL = "digital"
    FOB = "fob"
    QR = "qr"
    SPARE = "spare"

class KeyStatus(str, Enum):
    ACTIVE = "active"
    ISSUED = "issued"
    LOST = "lost"
    SPARE = "spare"
    EXPIRED = "expired"

class LockStatus(str, Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"

# Models
class AccessChip(BaseModel):
    type: str
    label: str
    icon: str

class Key(BaseModel):
    id: str
    key_id: str
    name: str
    type: KeyType
    unit: str
    property: str
    status: KeyStatus
    holder: str
    chips: List[AccessChip]
    last_activity: Optional[datetime] = None

class Lock(BaseModel):
    id: str
    name: str
    type: str = "Smart Lock"
    model: str
    status: LockStatus
    last_activity: str
    location: str

class Activity(BaseModel):
    id: str
    who: str
    what: str
    time: str
    key_id: str

class Stats(BaseModel):
    total_keys: int
    smart_locks: int
    keys_issued: int
    lost_flagged: int

class QRCode(BaseModel):
    code: str
    expires: datetime
    unit: str
    property: str

# In-memory data store (replace with DB in production)
keys_db: List[Key] = []
locks_db: List[Lock] = []
activities_db: List[Activity] = []
qr_codes: List[QRCode] = []

def init_data():
    global keys_db, locks_db, activities_db, qr_codes
    
    # Sample Keys
    keys_db = [
        Key(
            id=str(uuid.uuid4()),
            key_id="KY-0011",
            name="Master Key — Block A",
            type=KeyType.PHYSICAL,
            unit="Mwarokin Heights, Westlands",
            property="Mwarokin Heights",
            status=KeyStatus.ISSUED,
            holder="Caretaker · James M.",
            chips=[
                AccessChip(type="perm", label="Full access", icon="shield-check"),
                AccessChip(type="maint", label="Maintenance", icon="tools")
            ],
            last_activity=datetime.now() - timedelta(minutes=2)
        ),
        Key(
            id=str(uuid.uuid4()),
            key_id="DK-0047",
            name="Digital PIN — Unit 4B",
            type=KeyType.DIGITAL,
            unit="Mwarokin Suites, Kilimani",
            property="Mwarokin Suites",
            status=KeyStatus.ACTIVE,
            holder="Tenant · Amina K.",
            chips=[AccessChip(type="temp", label="Expires 30 Jul", icon="clock")],
            last_activity=datetime.now() - timedelta(hours=1)
        ),
        Key(
            id=str(uuid.uuid4()),
            key_id="FB-0089",
            name="RFID Fob — Parking Level 2",
            type=KeyType.FOB,
            unit="Mwarokin Plaza, CBD",
            property="Mwarokin Plaza",
            status=KeyStatus.ACTIVE,
            holder="Tenant · Brian O.",
            chips=[AccessChip(type="perm", label="Parking only", icon="car")],
            last_activity=datetime.now() - timedelta(hours=5)
        ),
        Key(
            id=str(uuid.uuid4()),
            key_id="KY-0023",
            name="Unit Key — 7C Front Door",
            type=KeyType.PHYSICAL,
            unit="Mwarokin Gardens, Lavington",
            property="Mwarokin Gardens",
            status=KeyStatus.LOST,
            holder="Ex-tenant · Grace N.",
            chips=[AccessChip(type="temp", label="Temp — 7 days", icon="clock")],
            last_activity=datetime.now() - timedelta(hours=3)
        ),
        Key(
            id=str(uuid.uuid4()),
            key_id="QR-0018",
            name="QR Access — Gym & Amenities",
            type=KeyType.QR,
            unit="Mwarokin Heights, Westlands",
            property="Mwarokin Heights",
            status=KeyStatus.ACTIVE,
            holder="Resident · Fatuma A.",
            chips=[AccessChip(type="perm", label="Amenities", icon="swimming")],
            last_activity=datetime.now() - timedelta(hours=10)
        ),
        Key(
            id=str(uuid.uuid4()),
            key_id="KY-0031-S",
            name="Spare Key — Unit 2A",
            type=KeyType.SPARE,
            unit="Mwarokin Suites, Kilimani",
            property="Mwarokin Suites",
            status=KeyStatus.SPARE,
            holder="Office · Secure storage",
            chips=[AccessChip(type="maint", label="In safe", icon="archive")],
            last_activity=datetime.now() - timedelta(days=1)
        ),
    ]

    # Sample Locks
    locks_db = [
        Lock(
            id="LK-BA-001",
            name="Block A — Main Entrance",
            model="ZL-400",
            status=LockStatus.LOCKED,
            last_activity="2 mins ago",
            location="Mwarokin Heights, Westlands"
        ),
        Lock(
            id="LK-BB-001",
            name="Block B — Main Gate",
            model="ZL-400",
            status=LockStatus.LOCKED,
            last_activity="Yesterday",
            location="Mwarokin Heights"
        ),
        Lock(
            id="LK-GYM-001",
            name="Gym Entrance",
            model="ZL-300",
            status=LockStatus.UNLOCKED,
            last_activity="15 mins ago",
            location="Mwarokin Suites"
        ),
        Lock(
            id="LK-P2-001",
            name="Parking Gate P2",
            model="ZL-500",
            status=LockStatus.LOCKED,
            last_activity="4 hours ago",
            location="Mwarokin Plaza"
        ),
    ]

    # Sample Activities
    activities_db = [
        Activity(
            id=str(uuid.uuid4()),
            who="James M.",
            what="unlocked Block A main door",
            time="2 minutes ago",
            key_id="KY-0011"
        ),
        Activity(
            id=str(uuid.uuid4()),
            who="Admin",
            what="issued digital PIN to Amina K. — Unit 4B",
            time="1 hour ago",
            key_id="DK-0047"
        ),
        Activity(
            id=str(uuid.uuid4()),
            who="Grace N.",
            what="reported key lost — Unit 7C",
            time="3 hours ago",
            key_id="KY-0023"
        ),
        Activity(
            id=str(uuid.uuid4()),
            who="Brian O.",
            what="fob access — Parking Level 2",
            time="5 hours ago",
            key_id="FB-0089"
        ),
    ]

    # Sample QR
    qr_codes.append(QRCode(
        code="ME-QR-4B-2025-A7",
        expires=datetime.now() + timedelta(hours=24),
        unit="Unit 4B",
        property="Mwarokin Suites"
    ))

init_data()

# Dependency for stats
def get_stats() -> Stats:
    total = len(keys_db)
    issued = len([k for k in keys_db if k.status == KeyStatus.ISSUED])
    lost = len([k for k in keys_db if k.status == KeyStatus.LOST])
    smart_locks = len(locks_db)
    return Stats(
        total_keys=total,
        smart_locks=smart_locks,
        keys_issued=issued,
        lost_flagged=lost
    )

# Routes
@app.get("/api/stats", response_model=Stats)
async def get_system_stats():
    return get_stats()

@app.get("/api/keys", response_model=List[Key])
async def get_keys(
    search: Optional[str] = Query(None, description="Search by unit, holder, or key ID"),
    key_type: Optional[KeyType] = Query(None),
    status: Optional[KeyStatus] = Query(None)
):
    filtered = keys_db.copy()
    
    if search:
        search_lower = search.lower()
        filtered = [
            k for k in filtered 
            if search_lower in k.name.lower() or 
               search_lower in k.unit.lower() or 
               search_lower in k.key_id.lower() or 
               search_lower in k.holder.lower()
        ]
    
    if key_type:
        filtered = [k for k in filtered if k.type == key_type]
    
    if status:
        filtered = [k for k in filtered if k.status == status]
    
    return filtered

@app.post("/api/keys", response_model=Key)
async def issue_key(key_data: dict = Body(...)):
    new_key = Key(
        id=str(uuid.uuid4()),
        key_id=f"KY-{random.randint(1000,9999)}",
        name=key_data.get("name", "New Key"),
        type=KeyType(key_data.get("type", "physical")),
        unit=key_data.get("unit", ""),
        property=key_data.get("property", ""),
        status=KeyStatus.ISSUED,
        holder=key_data.get("holder", "New Holder"),
        chips=key_data.get("chips", []),
        last_activity=datetime.now()
    )
    keys_db.append(new_key)
    
    # Log activity
    activities_db.insert(0, Activity(
        id=str(uuid.uuid4()),
        who="Admin",
        what=f"issued {new_key.name} to {new_key.holder}",
        time="Just now",
        key_id=new_key.key_id
    ))
    
    return new_key

@app.get("/api/locks", response_model=List[Lock])
async def get_locks():
    return locks_db

@app.post("/api/locks/{lock_id}/toggle")
async def toggle_lock(lock_id: str, locked: bool = Body(...)):
    lock = next((l for l in locks_db if l.id == lock_id), None)
    if not lock:
        raise HTTPException(status_code=404, detail="Lock not found")
    
    lock.status = LockStatus.LOCKED if locked else LockStatus.UNLOCKED
    lock.last_activity = "Just now"
    
    # Log activity
    action = "locked" if locked else "unlocked"
    activities_db.insert(0, Activity(
        id=str(uuid.uuid4()),
        who="System",
        what=f"{action} {lock.name}",
        time="Just now",
        key_id=lock.id
    ))
    
    return {"status": lock.status, "message": f"Lock {action} successfully"}

@app.get("/api/activities", response_model=List[Activity])
async def get_recent_activities(limit: int = 10):
    return activities_db[:limit]

@app.get("/api/qr", response_model=QRCode)
async def get_current_qr():
    if not qr_codes:
        return QRCode(
            code="ME-QR-GEN-2025",
            expires=datetime.now() + timedelta(hours=24),
            unit="Unit 4B",
            property="Mwarokin Suites"
        )
    return qr_codes[-1]

@app.post("/api/qr/regenerate", response_model=QRCode)
async def regenerate_qr():
    new_qr = QRCode(
        code=f"ME-QR-{random.randint(1000,9999)}-2025-{random.randint(10,99)}",
        expires=datetime.now() + timedelta(hours=24),
        unit="Unit 4B",
        property="Mwarokin Suites"
    )
    qr_codes.append(new_qr)
    return new_qr

# Health check
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "mwarokin-keys-locks", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Mwarokin Estates Keys & Locks Backend...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

**To run:**
```bash
pip install fastapi uvicorn pydantic
python main.py
```

The backend provides all endpoints needed by the UI:
- Stats, Keys list with filters/search
- Issue new keys
- Lock control (toggle)
- Activities feed
- QR generation

Modern, type-safe, ready for production with a real database (SQLAlchemy + Alembic) and authentication.