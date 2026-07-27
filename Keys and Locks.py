"""
Mwarokin Estates - Keys & Access Control System
Modern Python backend with functional programming patterns
Agentic UI management for key registry, lock control, and access management
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from enum import Enum
import json
import os
from functools import reduce, partial
from itertools import groupby
from operator import attrgetter
import random
import uuid
import hashlib
import base64
from typing import Protocol

# ============================================================================
# CORE TYPES & ENUMS
# ============================================================================

class KeyType(Enum):
    PHYSICAL = "physical"
    DIGITAL = "digital"
    FOB = "fob"
    SPARE = "spare"

class KeyStatus(Enum):
    ACTIVE = "Active"
    ISSUED = "Issued"
    REPORTED_LOST = "Reported Lost"
    SPARE = "Spare"
    REVOKED = "Revoked"

class LockState(Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"

class AccessChipType(Enum):
    PERMANENT = "perm"
    TEMPORARY = "temp"
    MAINTENANCE = "maint"

class ActivityType(Enum):
    KEY_ISSUED = "key_issued"
    KEY_LOST = "key_lost"
    KEY_REVOKED = "key_revoked"
    LOCK_LOCKED = "lock_locked"
    LOCK_UNLOCKED = "lock_unlocked"
    ACCESS_GRANTED = "access_granted"
    QR_GENERATED = "qr_generated"
    KEY_MATCHED = "key_matched"

@dataclass
class AccessChip:
    """Access permission chip for a key"""
    chip_type: AccessChipType
    icon: str
    description: str
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "type": self.chip_type.value,
            "icon": self.icon,
            "description": self.description
        }

@dataclass
class Key:
    """Key entity with access control data"""
    id: str
    key_type: KeyType
    name: str
    property_name: str
    unit: str
    block: str
    building: str
    status: KeyStatus
    holder: str
    chips: List[AccessChip]
    teeth_pattern: List[int]
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def type_icon(self) -> str:
        """Get icon for key type"""
        return {
            KeyType.PHYSICAL: "ti-key",
            KeyType.DIGITAL: "ti-device-mobile",
            KeyType.FOB: "ti-radio",
            KeyType.SPARE: "ti-key"
        }[self.key_type]
    
    @property
    def status_class(self) -> str:
        """Get CSS class for status"""
        return {
            KeyStatus.ACTIVE: "dot-active",
            KeyStatus.ISSUED: "dot-issued",
            KeyStatus.REPORTED_LOST: "dot-lost",
            KeyStatus.SPARE: "dot-spare",
            KeyStatus.REVOKED: "dot-lost"
        }[self.status]
    
    @property
    def status_color(self) -> str:
        """Get color for status"""
        return {
            KeyStatus.ACTIVE: "#5dcc8a",
            KeyStatus.ISSUED: "#e8c96a",
            KeyStatus.REPORTED_LOST: "#f07070",
            KeyStatus.SPARE: "rgba(184,143,60,0.6)",
            KeyStatus.REVOKED: "#f07070"
        }[self.status]
    
    def is_physical(self) -> bool:
        return self.key_type in [KeyType.PHYSICAL, KeyType.SPARE]
    
    def is_active(self) -> bool:
        return self.status in [KeyStatus.ACTIVE, KeyStatus.ISSUED]
    
    def matches_teeth(self, pattern: List[int], threshold: float = 0.6) -> float:
        """Calculate similarity with another teeth pattern"""
        if len(pattern) != len(self.teeth_pattern):
            return 0.0
        
        differences = sum(abs(a - b) for a, b in zip(pattern, self.teeth_pattern))
        max_diff = len(pattern) * 7  # Each tooth can differ by up to 7
        return max(0.0, 1.0 - (differences / max_diff))

@dataclass
class Lock:
    """Smart lock entity"""
    id: str
    name: str
    property_name: str
    state: LockState
    last_activity: datetime = field(default_factory=datetime.now)
    
    @property
    def is_locked(self) -> bool:
        return self.state == LockState.LOCKED
    
    def toggle_state(self) -> LockState:
        """Toggle lock state and return new state"""
        self.state = LockState.UNLOCKED if self.is_locked else LockState.LOCKED
        self.last_activity = datetime.now()
        return self.state

@dataclass
class AccessCode:
    """Temporary access code with QR data"""
    code: str
    key_id: str
    payload: Dict[str, Any]
    generated_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(seconds=120))
    is_active: bool = True
    
    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at or not self.is_active
    
    @property
    def seconds_remaining(self) -> int:
        if self.is_expired:
            return 0
        return max(0, int((self.expires_at - datetime.now()).total_seconds()))
    
    def to_qr_data(self) -> str:
        """Convert to QR code data string"""
        return json.dumps({
            "code": self.code,
            **self.payload,
            "expires": self.expires_at.isoformat()
        })

@dataclass
class ActivityLog:
    """Activity log entry"""
    id: str
    activity_type: ActivityType
    actor: str
    description: str
    key_id: Optional[str]
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def time_ago(self) -> str:
        """Get human-readable time difference"""
        delta = datetime.now() - self.timestamp
        if delta.total_seconds() < 60:
            return "Just now"
        if delta.total_seconds() < 3600:
            return f"{int(delta.total_seconds() / 60)} minutes ago"
        if delta.total_seconds() < 86400:
            return f"{int(delta.total_seconds() / 3600)} hours ago"
        return f"{int(delta.total_seconds() / 86400)} days ago"

# ============================================================================
# REPOSITORY (Functional Data Management)
# ============================================================================

class KeyRepository:
    """Functional repository for key and lock data"""
    
    STORE_KEY = "mwarokin_keys_v2"
    
    @staticmethod
    def generate_key_id(prefix: str) -> str:
        """Generate a unique key ID"""
        return f"{prefix}-{random.randint(1000, 9999)}"
    
    @staticmethod
    def default_keys() -> List[Key]:
        """Create default key data"""
        return [
            Key(
                id="KY-0011",
                key_type=KeyType.PHYSICAL,
                name="Master Key — Block A",
                property_name="Mwarokin Heights, Westlands",
                unit="Common Area",
                block="Block A",
                building="Building A",
                status=KeyStatus.ISSUED,
                holder="Caretaker · James M.",
                chips=[
                    AccessChip(AccessChipType.PERMANENT, "ti-shield-check", "Full access"),
                    AccessChip(AccessChipType.MAINTENANCE, "ti-tools", "Maintenance")
                ],
                teeth_pattern=[3, 7, 2, 6, 4, 8, 3]
            ),
            Key(
                id="DK-0047",
                key_type=KeyType.DIGITAL,
                name="Digital PIN — Unit 4B",
                property_name="Mwarokin Suites, Kilimani",
                unit="Unit 4B",
                block="Block C",
                building="Suites Tower",
                status=KeyStatus.ACTIVE,
                holder="Tenant · Amina K.",
                chips=[
                    AccessChip(AccessChipType.TEMPORARY, "ti-clock", "Expires 30 Jul")
                ],
                teeth_pattern=[5, 5, 5, 5, 5, 5, 5]
            ),
            Key(
                id="FB-0089",
                key_type=KeyType.FOB,
                name="RFID Fob — Parking Level 2",
                property_name="Mwarokin Plaza, CBD",
                unit="Parking P2",
                block="Block P",
                building="Plaza Tower",
                status=KeyStatus.ACTIVE,
                holder="Tenant · Brian O.",
                chips=[
                    AccessChip(AccessChipType.PERMANENT, "ti-car", "Parking only")
                ],
                teeth_pattern=[6, 6, 6, 6, 6, 6, 6]
            ),
            Key(
                id="KY-0023",
                key_type=KeyType.PHYSICAL,
                name="Unit Key — 7C Front Door",
                property_name="Mwarokin Gardens, Lavington",
                unit="Unit 7C",
                block="Block D",
                building="Garden Wing",
                status=KeyStatus.REPORTED_LOST,
                holder="Ex-tenant · Grace N.",
                chips=[
                    AccessChip(AccessChipType.TEMPORARY, "ti-clock", "Temp — 7 days")
                ],
                teeth_pattern=[2, 8, 5, 3, 7, 1, 6]
            ),
            Key(
                id="QR-0018",
                key_type=KeyType.DIGITAL,
                name="QR Access — Gym & Amenities",
                property_name="Mwarokin Heights, Westlands",
                unit="Amenities",
                block="Block A",
                building="Building A",
                status=KeyStatus.ACTIVE,
                holder="Resident · Fatuma A.",
                chips=[
                    AccessChip(AccessChipType.PERMANENT, "ti-swimming", "Amenities")
                ],
                teeth_pattern=[4, 4, 4, 4, 4, 4, 4]
            ),
            Key(
                id="KY-0031-S",
                key_type=KeyType.SPARE,
                name="Spare Key — Unit 2A",
                property_name="Mwarokin Suites, Kilimani",
                unit="Unit 2A",
                block="Block C",
                building="Suites Tower",
                status=KeyStatus.SPARE,
                holder="Office · Secure storage",
                chips=[
                    AccessChip(AccessChipType.MAINTENANCE, "ti-archive", "In safe")
                ],
                teeth_pattern=[7, 3, 7, 3, 7, 3, 7]
            ),
            Key(
                id="KY-0052",
                key_type=KeyType.PHYSICAL,
                name="Unit Key — 5D Front Door",
                property_name="Mwarokin Gardens, Lavington",
                unit="Unit 5D",
                block="Block D",
                building="Garden Wing",
                status=KeyStatus.ISSUED,
                holder="Tenant · Peter K.",
                chips=[
                    AccessChip(AccessChipType.PERMANENT, "ti-home", "Full access")
                ],
                teeth_pattern=[8, 2, 4, 6, 3, 5, 7]
            )
        ]
    
    @staticmethod
    def default_locks() -> List[Lock]:
        """Create default lock data"""
        return [
            Lock("ZL-400", "Block A — Main Entrance", "Mwarokin Heights, Westlands", LockState.LOCKED),
            Lock("ZL-221", "Block B — Main Gate", "Mwarokin Plaza, CBD", LockState.LOCKED),
            Lock("ZL-118", "Gym Entrance", "Mwarokin Heights, Westlands", LockState.UNLOCKED),
            Lock("ZL-305", "Parking Gate P2", "Mwarokin Plaza, CBD", LockState.LOCKED),
            Lock("ZL-090", "Rooftop Terrace", "Mwarokin Suites, Kilimani", LockState.UNLOCKED),
            Lock("ZL-410", "Garden Wing — Main Door", "Mwarokin Gardens, Lavington", LockState.LOCKED)
        ]
    
    @staticmethod
    def default_activities() -> List[ActivityLog]:
        """Create default activity data"""
        now = datetime.now()
        return [
            ActivityLog(str(uuid.uuid4())[:8], ActivityType.LOCK_UNLOCKED, "James M.", 
                       "unlocked Block A main door", "KY-0011", now - timedelta(minutes=2)),
            ActivityLog(str(uuid.uuid4())[:8], ActivityType.KEY_ISSUED, "Admin",
                       "issued digital PIN to Amina K. — Unit 4B", "DK-0047", now - timedelta(hours=1)),
            ActivityLog(str(uuid.uuid4())[:8], ActivityType.KEY_LOST, "Grace N.",
                       "reported key lost — Unit 7C", "KY-0023", now - timedelta(hours=3)),
            ActivityLog(str(uuid.uuid4())[:8], ActivityType.ACCESS_GRANTED, "Brian O.",
                       "fob access — Parking Level 2", "FB-0089", now - timedelta(hours=5)),
            ActivityLog(str(uuid.uuid4())[:8], ActivityType.KEY_ISSUED, "Admin",
                       "spare key logged to secure storage — 2A", "KY-0031-S", now - timedelta(days=1))
        ]
    
    @staticmethod
    def load() -> Dict[str, Any]:
        """Load data from storage"""
        try:
            if os.path.exists(f"_storage_{KeyRepository.STORE_KEY}.json"):
                with open(f"_storage_{KeyRepository.STORE_KEY}.json", "r") as f:
                    return json.loads(f.read())
        except:
            pass
        return {
            "keys": [k.__dict__ for k in KeyRepository.default_keys()],
            "locks": [l.__dict__ for l in KeyRepository.default_locks()],
            "activities": [a.__dict__ for a in KeyRepository.default_activities()]
        }
    
    @staticmethod
    def save(data: Dict[str, Any]) -> None:
        """Save data to storage"""
        try:
            with open(f"_storage_{KeyRepository.STORE_KEY}.json", "w") as f:
                f.write(json.dumps(data, default=str, indent=2))
        except:
            pass

# ============================================================================
# FUNCTIONAL OPERATIONS (Pure Functions)
# ============================================================================

# Type aliases
KeyTransformer = Callable[[List[Key]], List[Key]]
LockTransformer = Callable[[List[Lock]], List[Lock]]
ActivityTransformer = Callable[[List[ActivityLog]], List[ActivityLog]]

def compose(*functions: Callable) -> Callable:
    """Compose multiple functions"""
    def apply(x):
        return reduce(lambda acc, f: f(acc), functions, x)
    return apply

def filter_keys(predicate: Callable[[Key], bool]) -> KeyTransformer:
    """Filter keys by predicate"""
    def transform(keys: List[Key]) -> List[Key]:
        return list(filter(predicate, keys))
    return transform

def sort_keys(key_func: Callable[[Key], Any], reverse: bool = False) -> KeyTransformer:
    """Sort keys by key function"""
    def transform(keys: List[Key]) -> List[Key]:
        return sorted(keys, key=key_func, reverse=reverse)
    return transform

def search_keys(search_term: str) -> KeyTransformer:
    """Search keys by term"""
    def predicate(key: Key) -> bool:
        haystack = f"{key.name}{key.unit}{key.holder}{key.id}{key.block}{key.property_name}".lower()
        return search_term.lower() in haystack
    return filter_keys(predicate)

def filter_by_type(key_type: Optional[KeyType]) -> KeyTransformer:
    """Filter keys by type"""
    if key_type is None:
        return lambda x: x
    return filter_keys(lambda k: k.key_type == key_type)

def filter_by_status(statuses: List[KeyStatus]) -> KeyTransformer:
    """Filter keys by status"""
    return filter_keys(lambda k: k.status in statuses)

def update_key_status(key_id: str, new_status: KeyStatus) -> KeyTransformer:
    """Update a key's status"""
    def transform(keys: List[Key]) -> List[Key]:
        updated_keys = []
        for key in keys:
            if key.id == key_id:
                updated_keys.append(Key(
                    id=key.id,
                    key_type=key.key_type,
                    name=key.name,
                    property_name=key.property_name,
                    unit=key.unit,
                    block=key.block,
                    building=key.building,
                    status=new_status,
                    holder=key.holder,
                    chips=key.chips,
                    teeth_pattern=key.teeth_pattern,
                    created_at=key.created_at,
                    updated_at=datetime.now()
                ))
            else:
                updated_keys.append(key)
        return updated_keys
    return transform

def add_key(new_key: Key) -> KeyTransformer:
    """Add a new key to the list"""
    def transform(keys: List[Key]) -> List[Key]:
        return [new_key] + keys
    return transform

def find_best_teeth_match(teeth_pattern: List[int], threshold: float = 0.6) -> Callable[[List[Key]], Optional[Tuple[Key, float]]]:
    """Find the best matching key by teeth pattern"""
    def find_match(keys: List[Key]) -> Optional[Tuple[Key, float]]:
        physical_keys = [k for k in keys if k.is_physical()]
        if not physical_keys:
            return None
        
        best_match = None
        best_score = -1
        
        for key in physical_keys:
            score = key.matches_teeth(teeth_pattern)
            if score > best_score:
                best_score = score
                best_match = key
        
        if best_match and best_score >= threshold:
            return (best_match, best_score * 100)  # Return as percentage
        return None
    return find_match

# ============================================================================
# ACCESS CODE MANAGEMENT
# ============================================================================

class AccessCodeManager:
    """Functional access code management"""
    
    @staticmethod
    def generate_code(key: Key) -> AccessCode:
        """Generate a new access code for a key"""
        code = f"ME-QR-{key.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        payload = {
            "keyId": key.id,
            "tenant": key.holder.split('·')[-1].strip(),
            "unit": key.unit,
            "block": key.block,
            "building": key.building,
            "property": key.property_name
        }
        return AccessCode(code, key.id, payload)
    
    @staticmethod
    def verify_code(code_data: str) -> Optional[Dict[str, Any]]:
        """Verify and parse an access code"""
        try:
            data = json.loads(code_data)
            if "code" not in data:
                return None
            return data
        except:
            return None
    
    @staticmethod
    def is_code_valid(code: AccessCode) -> bool:
        """Check if access code is still valid"""
        return not code.is_expired

# ============================================================================
# ANALYTICS ENGINE
# ============================================================================

class KeyAnalytics:
    """Analytics for key management"""
    
    @staticmethod
    def get_key_statistics(keys: List[Key]) -> Dict[str, Any]:
        """Calculate key statistics"""
        return {
            "total_keys": len(keys),
            "by_type": {
                t.value: len([k for k in keys if k.key_type == t])
                for t in KeyType
            },
            "by_status": {
                s.value: len([k for k in keys if k.status == s])
                for s in KeyStatus
            },
            "active_keys": len([k for k in keys if k.is_active()]),
            "lost_keys": len([k for k in keys if k.status == KeyStatus.REPORTED_LOST]),
            "issued_keys": len([k for k in keys if k.status == KeyStatus.ISSUED]),
            "spare_keys": len([k for k in keys if k.status == KeyStatus.SPARE])
        }
    
    @staticmethod
    def get_lock_statistics(locks: List[Lock]) -> Dict[str, Any]:
        """Calculate lock statistics"""
        return {
            "total_locks": len(locks),
            "locked": len([l for l in locks if l.state == LockState.LOCKED]),
            "unlocked": len([l for l in locks if l.state == LockState.UNLOCKED])
        }
    
    @staticmethod
    def get_activity_summary(activities: List[ActivityLog]) -> Dict[str, Any]:
        """Get activity summary"""
        return {
            "total_activities": len(activities),
            "by_type": {
                t.value: len([a for a in activities if a.activity_type == t])
                for t in ActivityType
            },
            "recent": activities[:6]
        }

# ============================================================================
# COMMAND PATTERN
# ============================================================================

class Command(Protocol):
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        ...
    
    def undo(self, state: Dict[str, Any]) -> Dict[str, Any]:
        ...

class IssueKeyCommand(Command):
    """Command to issue a new key"""
    
    def __init__(self, key: Key):
        self.key = key
        self._key_id = key.id
    
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        keys = state.get("keys", [])
        activities = state.get("activities", [])
        
        # Add the new key
        transformer = add_key(self.key)
        new_keys = transformer(keys)
        
        # Add activity log
        activity = ActivityLog(
            str(uuid.uuid4())[:8],
            ActivityType.KEY_ISSUED,
            "Admin",
            f"issued new {self.key.key_type.value} key — {self.key.name}",
            self.key.id
        )
        new_activities = [activity] + activities
        
        return {
            **state,
            "keys": new_keys,
            "activities": new_activities
        }
    
    def undo(self, state: Dict[str, Any]) -> Dict[str, Any]:
        keys = state.get("keys", [])
        activities = state.get("activities", [])
        
        # Remove the key
        new_keys = [k for k in keys if k.id != self._key_id]
        
        # Remove the activity
        new_activities = [
            a for a in activities 
            if not (a.activity_type == ActivityType.KEY_ISSUED and a.key_id == self._key_id)
        ]
        
        return {
            **state,
            "keys": new_keys,
            "activities": new_activities
        }

class UpdateKeyStatusCommand(Command):
    """Command to update key status"""
    
    def __init__(self, key_id: str, new_status: KeyStatus):
        self.key_id = key_id
        self.new_status = new_status
        self._old_status = None
    
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        keys = state.get("keys", [])
        activities = state.get("activities", [])
        
        # Find old status
        for key in keys:
            if key.id == self.key_id:
                self._old_status = key.status
                break
        
        # Update status
        transformer = update_key_status(self.key_id, self.new_status)
        new_keys = transformer(keys)
        
        # Add activity
        activity_type = {
            KeyStatus.REPORTED_LOST: ActivityType.KEY_LOST,
            KeyStatus.REVOKED: ActivityType.KEY_REVOKED
        }.get(self.new_status, ActivityType.KEY_ISSUED)
        
        activity = ActivityLog(
            str(uuid.uuid4())[:8],
            activity_type,
            "Admin",
            f"updated {self.key_id} status to {self.new_status.value}",
            self.key_id
        )
        new_activities = [activity] + activities
        
        return {
            **state,
            "keys": new_keys,
            "activities": new_activities
        }
    
    def undo(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if self._old_status is None:
            return state
        
        keys = state.get("keys", [])
        activities = state.get("activities", [])
        
        # Revert status
        transformer = update_key_status(self.key_id, self._old_status)
        new_keys = transformer(keys)
        
        # Remove the activity
        new_activities = [
            a for a in activities 
            if not (a.key_id == self.key_id and 
                   a.activity_type in [ActivityType.KEY_LOST, ActivityType.KEY_REVOKED])
        ]
        
        return {
            **state,
            "keys": new_keys,
            "activities": new_activities
        }

class ToggleLockCommand(Command):
    """Command to toggle lock state"""
    
    def __init__(self, lock_id: str):
        self.lock_id = lock_id
        self._old_state = None
    
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        locks = state.get("locks", [])
        activities = state.get("activities", [])
        
        new_locks = []
        for lock in locks:
            if lock.id == self.lock_id:
                self._old_state = lock.state
                new_state = lock.toggle_state()
                new_locks.append(lock)
                
                # Add activity
                activity_type = ActivityType.LOCK_LOCKED if new_state == LockState.LOCKED else ActivityType.LOCK_UNLOCKED
                activity = ActivityLog(
                    str(uuid.uuid4())[:8],
                    activity_type,
                    "You",
                    f"{'locked' if new_state == LockState.LOCKED else 'unlocked'} {lock.name}",
                    None
                )
                new_activities = [activity] + activities
            else:
                new_locks.append(lock)
        
        return {
            **state,
            "locks": new_locks,
            "activities": new_activities
        }
    
    def undo(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if self._old_state is None:
            return state
        
        locks = state.get("locks", [])
        activities = state.get("activities", [])
        
        # Revert lock state
        new_locks = []
        for lock in locks:
            if lock.id == self.lock_id:
                lock.state = self._old_state
                lock.last_activity = datetime.now()
                new_locks.append(lock)
            else:
                new_locks.append(lock)
        
        # Remove last activity
        new_activities = activities[1:] if activities else activities
        
        return {
            **state,
            "locks": new_locks,
            "activities": new_activities
        }

# ============================================================================
# COMMAND MANAGER
# ============================================================================

class CommandManager:
    """Manager for executing commands with history"""
    
    def __init__(self):
        self._history: List[Command] = []
        self._redo_stack: List[Command] = []
    
    def execute(self, command: Command, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a command and add to history"""
        result = command.execute(state)
        self._history.append(command)
        self._redo_stack.clear()
        return result
    
    def undo(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Undo the last command"""
        if not self._history:
            return state
        
        command = self._history.pop()
        self._redo_stack.append(command)
        return command.undo(state)
    
    def redo(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Redo the last undone command"""
        if not self._redo_stack:
            return state
        
        command = self._redo_stack.pop()
        self._history.append(command)
        return command.execute(state)

# ============================================================================
# SERVICE LAYER
# ============================================================================

class KeyService:
    """Main service for key management"""
    
    def __init__(self):
        self.repository = KeyRepository()
        self.command_manager = CommandManager()
        self._state = self.repository.load()
        self._state["keys"] = self._deserialize_keys(self._state.get("keys", []))
        self._state["locks"] = self._deserialize_locks(self._state.get("locks", []))
        self._state["activities"] = self._deserialize_activities(self._state.get("activities", []))
        self._analytics = KeyAnalytics()
        self._access_manager = AccessCodeManager()
        self._current_access_code: Optional[AccessCode] = None
    
    @property
    def keys(self) -> List[Key]:
        return self._state.get("keys", [])
    
    @property
    def locks(self) -> List[Lock]:
        return self._state.get("locks", [])
    
    @property
    def activities(self) -> List[ActivityLog]:
        return self._state.get("activities", [])
    
    def _deserialize_keys(self, data: List[Dict]) -> List[Key]:
        """Deserialize key data"""
        keys = []
        for d in data:
            try:
                keys.append(Key(
                    id=d["id"],
                    key_type=KeyType(d["key_type"]),
                    name=d["name"],
                    property_name=d["property_name"],
                    unit=d["unit"],
                    block=d["block"],
                    building=d["building"],
                    status=KeyStatus(d["status"]),
                    holder=d["holder"],
                    chips=[AccessChip(
                        AccessChipType(c["chip_type"]),
                        c["icon"],
                        c["description"]
                    ) for c in d.get("chips", [])],
                    teeth_pattern=d.get("teeth_pattern", [1] * 7),
                    created_at=datetime.fromisoformat(d["created_at"]) if "created_at" in d else datetime.now(),
                    updated_at=datetime.fromisoformat(d["updated_at"]) if "updated_at" in d else datetime.now()
                ))
            except Exception as e:
                print(f"Error deserializing key: {e}")
                continue
        return keys
    
    def _deserialize_locks(self, data: List[Dict]) -> List[Lock]:
        """Deserialize lock data"""
        locks = []
        for d in data:
            try:
                locks.append(Lock(
                    id=d["id"],
                    name=d["name"],
                    property_name=d["property_name"],
                    state=LockState(d["state"]),
                    last_activity=datetime.fromisoformat(d["last_activity"]) if "last_activity" in d else datetime.now()
                ))
            except:
                continue
        return locks
    
    def _deserialize_activities(self, data: List[Dict]) -> List[ActivityLog]:
        """Deserialize activity data"""
        activities = []
        for d in data:
            try:
                activities.append(ActivityLog(
                    id=d["id"],
                    activity_type=ActivityType(d["activity_type"]),
                    actor=d["actor"],
                    description=d["description"],
                    key_id=d.get("key_id"),
                    timestamp=datetime.fromisoformat(d["timestamp"]) if "timestamp" in d else datetime.now()
                ))
            except:
                continue
        return activities
    
    def _save_state(self) -> None:
        """Save current state"""
        data = {
            "keys": [
                {
                    "id": k.id,
                    "key_type": k.key_type.value,
                    "name": k.name,
                    "property_name": k.property_name,
                    "unit": k.unit,
                    "block": k.block,
                    "building": k.building,
                    "status": k.status.value,
                    "holder": k.holder,
                    "chips": [{"chip_type": c.chip_type.value, "icon": c.icon, "description": c.description} for c in k.chips],
                    "teeth_pattern": k.teeth_pattern,
                    "created_at": k.created_at.isoformat(),
                    "updated_at": k.updated_at.isoformat()
                }
                for k in self.keys
            ],
            "locks": [
                {
                    "id": l.id,
                    "name": l.name,
                    "property_name": l.property_name,
                    "state": l.state.value,
                    "last_activity": l.last_activity.isoformat()
                }
                for l in self.locks
            ],
            "activities": [
                {
                    "id": a.id,
                    "activity_type": a.activity_type.value,
                    "actor": a.actor,
                    "description": a.description,
                    "key_id": a.key_id,
                    "timestamp": a.timestamp.isoformat()
                }
                for a in self.activities
            ]
        }
        self.repository.save(data)
    
    def issue_key(self, key_type: KeyType, name: str, property_name: str, 
                  unit: str, block: str, building: str, holder: str) -> Optional[Key]:
        """Issue a new key"""
        prefix = {
            KeyType.PHYSICAL: "KY",
            KeyType.DIGITAL: "DK",
            KeyType.FOB: "FB",
            KeyType.SPARE: "SP"
        }[key_type]
        
        key_id = KeyRepository.generate_key_id(prefix)
        teeth = [random.randint(1, 8) for _ in range(7)]
        
        new_key = Key(
            id=key_id,
            key_type=key_type,
            name=name or f"New {key_type.value} Key",
            property_name=property_name or "Mwarokin Estates",
            unit=unit or "Unassigned",
            block=block or "Block —",
            building=building or "Building —",
            status=KeyStatus.ISSUED,
            holder=holder or "Unassigned",
            chips=[AccessChip(AccessChipType.TEMPORARY, "ti-clock", "New issue")],
            teeth_pattern=teeth
        )
        
        command = IssueKeyCommand(new_key)
        self._state = self.command_manager.execute(command, self._state)
        self._save_state()
        return new_key
    
    def update_key_status(self, key_id: str, status: KeyStatus) -> bool:
        """Update a key's status"""
        command = UpdateKeyStatusCommand(key_id, status)
        self._state = self.command_manager.execute(command, self._state)
        self._save_state()
        return True
    
    def toggle_lock(self, lock_id: str) -> Optional[LockState]:
        """Toggle a lock state"""
        command = ToggleLockCommand(lock_id)
        self._state = self.command_manager.execute(command, self._state)
        self._save_state()
        
        # Find and return the updated lock
        for lock in self.locks:
            if lock.id == lock_id:
                return lock.state
        return None
    
    def get_filtered_keys(self, search_term: str = "", key_type: Optional[str] = None, 
                          status_filter: Optional[str] = None) -> List[Key]:
        """Get filtered keys"""
        keys = self.keys
        
        if search_term:
            transformer = search_keys(search_term)
            keys = transformer(keys)
        
        if key_type and key_type != "all":
            transformer = filter_by_type(KeyType(key_type))
            keys = transformer(keys)
        
        if status_filter and status_filter != "all":
            if status_filter.startswith("status:"):
                statuses = [KeyStatus(s.strip()) for s in status_filter.replace("status:", "").split(",")]
                transformer = filter_by_status(statuses)
                keys = transformer(keys)
        
        return keys
    
    def find_key_by_teeth(self, teeth_pattern: List[int]) -> Optional[Tuple[Key, float]]:
        """Find a key by teeth pattern"""
        matcher = find_best_teeth_match(teeth_pattern)
        return matcher(self.keys)
    
    def generate_access_code(self, key_id: str) -> Optional[AccessCode]:
        """Generate an access code for a key"""
        key = next((k for k in self.keys if k.id == key_id), None)
        if not key:
            return None
        
        code = self._access_manager.generate_code(key)
        self._current_access_code = code
        
        # Log activity
        activity = ActivityLog(
            str(uuid.uuid4())[:8],
            ActivityType.QR_GENERATED,
            "System",
            f"generated access code for {key.name}",
            key_id
        )
        self._state["activities"] = [activity] + self.activities
        self._save_state()
        
        return code
    
    def verify_access_code(self, code_data: str) -> Optional[Dict[str, Any]]:
        """Verify an access code"""
        return self._access_manager.verify_code(code_data)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics"""
        return {
            "keys": self._analytics.get_key_statistics(self.keys),
            "locks": self._analytics.get_lock_statistics(self.locks),
            "activities": self._analytics.get_activity_summary(self.activities)
        }
    
    def undo_last_action(self) -> None:
        """Undo the last action"""
        self._state = self.command_manager.undo(self._state)
        self._save_state()
    
    def redo_last_action(self) -> None:
        """Redo the last undone action"""
        self._state = self.command_manager.redo(self._state)
        self._save_state()

# ============================================================================
# UI VIEW MODELS
# ============================================================================

class KeyViewModel:
    """View model for keys"""
    
    @staticmethod
    def to_dict(key: Key) -> Dict[str, Any]:
        """Convert key to dictionary for UI rendering"""
        return {
            "id": key.id,
            "type": key.key_type.value,
            "type_icon": key.type_icon,
            "name": key.name,
            "property": key.property_name,
            "unit": key.unit,
            "block": key.block,
            "building": key.building,
            "status": key.status.value,
            "status_class": key.status_class,
            "status_color": key.status_color,
            "holder": key.holder,
            "chips": [{"type": c.chip_type.value, "icon": c.icon, "description": c.description} for c in key.chips],
            "teeth": key.teeth_pattern
        }
    
    @staticmethod
    def to_dict_list(keys: List[Key]) -> List[Dict[str, Any]]:
        """Convert list of keys to dictionary list"""
        return [KeyViewModel.to_dict(k) for k in keys]

class LockViewModel:
    """View model for locks"""
    
    @staticmethod
    def to_dict(lock: Lock) -> Dict[str, Any]:
        """Convert lock to dictionary for UI rendering"""
        return {
            "id": lock.id,
            "name": lock.name,
            "property": lock.property_name,
            "state": lock.state.value,
            "is_locked": lock.is_locked,
            "last_activity": lock.last_activity.isoformat()
        }
    
    @staticmethod
    def to_dict_list(locks: List[Lock]) -> List[Dict[str, Any]]:
        """Convert list of locks to dictionary list"""
        return [LockViewModel.to_dict(l) for l in locks]

class ActivityViewModel:
    """View model for activities"""
    
    @staticmethod
    def to_dict(activity: ActivityLog) -> Dict[str, Any]:
        """Convert activity to dictionary for UI rendering"""
        return {
            "id": activity.id,
            "type": activity.activity_type.value,
            "actor": activity.actor,
            "description": activity.description,
            "key_id": activity.key_id,
            "timestamp": activity.timestamp.isoformat(),
            "time_ago": activity.time_ago
        }
    
    @staticmethod
    def to_dict_list(activities: List[ActivityLog]) -> List[Dict[str, Any]]:
        """Convert list of activities to dictionary list"""
        return [ActivityViewModel.to_dict(a) for a in activities]

# ============================================================================
# AGENTIC UI MANAGEMENT
# ============================================================================

class UIState:
    """UI state management with reactive updates"""
    
    def __init__(self, service: KeyService):
        self.service = service
        self._observers: List[Callable[[Dict[str, Any]], None]] = []
        self._state = {
            "selected_key_id": None,
            "active_type": "all",
            "search_term": "",
            "status_filter": "all",
            "active_lock_idx": 0
        }
    
    @property
    def selected_key(self) -> Optional[Key]:
        if not self._state["selected_key_id"]:
            return None
        return next((k for k in self.service.keys if k.id == self._state["selected_key_id"]), None)
    
    def set_selected_key(self, key_id: str) -> None:
        self._state["selected_key_id"] = key_id
        self._notify()
    
    def set_filter(self, filter_type: str, value: str) -> None:
        self._state[filter_type] = value
        self._notify()
    
    def add_observer(self, observer: Callable[[Dict[str, Any]], None]) -> None:
        self._observers.append(observer)
    
    def _notify(self) -> None:
        """Notify observers of state change"""
        for observer in self._observers:
            observer(self._state)

# ============================================================================
# MAIN APPLICATION
# ============================================================================

class KeysAndLocksApp:
    """Main application for keys and locks management"""
    
    def __init__(self):
        self.service = KeyService()
        self.ui_state = UIState(self.service)
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize the application"""
        if self._initialized:
            return
        
        # Set initial selected key
        if self.service.keys:
            self.ui_state.set_selected_key(self.service.keys[0].id)
        
        self._initialized = True
        print("Keys & Locks system initialized successfully")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for dashboard display"""
        stats = self.service.get_statistics()
        keys = self.service.get_filtered_keys(
            self.ui_state._state["search_term"],
            self.ui_state._state["active_type"],
            self.ui_state._state["status_filter"]
        )
        
        return {
            "statistics": stats,
            "keys": KeyViewModel.to_dict_list(keys),
            "all_keys_count": len(self.service.keys),
            "locks": LockViewModel.to_dict_list(self.service.locks),
            "activities": ActivityViewModel.to_dict_list(self.service.activities[:8]),
            "selected_key": KeyViewModel.to_dict(self.ui_state.selected_key) if self.ui_state.selected_key else None,
            "active_lock": LockViewModel.to_dict(self.service.locks[self.ui_state._state["active_lock_idx"]]) 
                          if self.service.locks else None
        }
    
    def issue_key(self, key_type: str, name: str, property_name: str,
                  unit: str, block: str, building: str, holder: str) -> Optional[Dict[str, Any]]:
        """Issue a new key"""
        key = self.service.issue_key(
            KeyType(key_type),
            name,
            property_name,
            unit,
            block,
            building,
            holder
        )
        
        if key:
            self.ui_state.set_selected_key(key.id)
            return KeyViewModel.to_dict(key)
        return None
    
    def update_key_status(self, key_id: str, status: str) -> bool:
        """Update key status"""
        return self.service.update_key_status(key_id, KeyStatus(status))
    
    def toggle_lock(self, lock_id: str) -> Optional[Dict[str, Any]]:
        """Toggle a lock state"""
        new_state = self.service.toggle_lock(lock_id)
        if new_state:
            lock = next((l for l in self.service.locks if l.id == lock_id), None)
            return LockViewModel.to_dict(lock) if lock else None
        return None
    
    def scan_key_teeth(self, teeth_pattern: List[int]) -> Optional[Dict[str, Any]]:
        """Scan a key by teeth pattern"""
        match = self.service.find_key_by_teeth(teeth_pattern)
        if match:
            key, confidence = match
            return {
                "key": KeyViewModel.to_dict(key),
                "confidence": confidence,
                "matched": True
            }
        return {"matched": False, "confidence": 0}
    
    def generate_access_code(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Generate an access code for a key"""
        code = self.service.generate_access_code(key_id)
        if code:
            return {
                "code": code.code,
                "qr_data": code.to_qr_data(),
                "seconds_remaining": code.seconds_remaining,
                "is_expired": code.is_expired,
                "payload": code.payload
            }
        return None
    
    def get_access_code_status(self) -> Dict[str, Any]:
        """Get current access code status"""
        if not self.service._current_access_code:
            return {"has_code": False}
        
        code = self.service._current_access_code
        return {
            "has_code": True,
            "code": code.code,
            "seconds_remaining": code.seconds_remaining,
            "is_expired": code.is_expired
        }
    
    def get_teeth_visualization(self, teeth_pattern: List[int]) -> str:
        """Get HTML for teeth visualization"""
        bars = []
        for t in teeth_pattern:
            height = t * 4
            bars.append(f'<div class="tooth-bar" style="height:{height}px;"></div>')
        return ''.join(bars)
    
    def export_report(self) -> str:
        """Export a key registry report"""
        stats = self.service.get_statistics()
        lines = [
            "MWAROKIN ESTATES — KEY REGISTRY REPORT",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "KEY STATISTICS",
            f"Total Keys: {stats['keys']['total_keys']}",
            f"Active Keys: {stats['keys']['active_keys']}",
            f"Lost Keys: {stats['keys']['lost_keys']}",
            f"Issued Keys: {stats['keys']['issued_keys']}",
            f"Spare Keys: {stats['keys']['spare_keys']}",
            "",
            "KEYS BY TYPE",
        ]
        
        for key_type, count in stats['keys']['by_type'].items():
            lines.append(f"  {key_type}: {count}")
        
        lines.append("")
        lines.append("LOCK STATISTICS")
        lines.append(f"Total Locks: {stats['locks']['total_locks']}")
        lines.append(f"Locked: {stats['locks']['locked']}")
        lines.append(f"Unlocked: {stats['locks']['unlocked']}")
        
        lines.append("")
        lines.append("KEY REGISTRY DETAIL")
        for key in self.service.keys:
            lines.append(f"  {key.id}: {key.name} — {key.status.value} — {key.holder}")
        
        return "\n".join(lines)

# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Main entry point"""
    app = KeysAndLocksApp()
    app.initialize()
    
    print("\n" + "="*60)
    print("MWAROKIN ESTATES — KEYS & LOCKS SYSTEM")
    print("="*60)
    
    # Display dashboard
    dashboard = app.get_dashboard_data()
    stats = dashboard["statistics"]
    
    print(f"\n🔑 KEY STATISTICS")
    print(f"  Total Keys: {stats['keys']['total_keys']}")
    print(f"  Active: {stats['keys']['active_keys']} | Lost: {stats['keys']['lost_keys']} | Issued: {stats['keys']['issued_keys']}")
    
    print(f"\n🔒 LOCK STATISTICS")
    print(f"  Total Locks: {stats['locks']['total_locks']}")
    print(f"  Locked: {stats['locks']['locked']} | Unlocked: {stats['locks']['unlocked']}")
    
    print("\n📋 RECENT ACTIVITY")
    for activity in dashboard["activities"][:5]:
        print(f"  • {activity['actor']}: {activity['description']} ({activity['time_ago']})")
    
    print("\n🔑 KEY REGISTRY")
    for key in dashboard["keys"][:5]:
        print(f"  • {key['id']}: {key['name']} — {key['status']} — {key['holder']}")
    
    # Test: Find key by teeth pattern
    print("\n🔍 TESTING: Find key by teeth pattern")
    test_pattern = [3, 7, 2, 6, 4, 8, 3]
    result = app.scan_key_teeth(test_pattern)
    if result["matched"]:
        print(f"  ✓ Found match: {result['key']['name']} (Confidence: {result['confidence']:.1f}%)")
    else:
        print("  ✗ No match found")
    
    # Test: Generate access code
    print("\n📱 TESTING: Generate access code")
    if dashboard["selected_key"]:
        code_data = app.generate_access_code(dashboard["selected_key"]["id"])
        if code_data:
            print(f"  ✓ Generated code: {code_data['code']}")
            print(f"  ✓ Expires in: {code_data['seconds_remaining']}s")
    
    # Test: Toggle lock
    print("\n🔓 TESTING: Toggle first lock")
    if app.service.locks:
        lock_id = app.service.locks[0].id
        new_state = app.toggle_lock(lock_id)
        if new_state:
            print(f"  ✓ Lock {lock_id} is now {new_state['state']}")
    
    # Export report
    print(f"\n📄 Report saved to 'key_registry_report.txt'")
    with open("key_registry_report.txt", "w") as f:
        f.write(app.export_report())
    
    print("\n✅ Keys & Locks system ready!")

if __name__ == "__main__":
    main()