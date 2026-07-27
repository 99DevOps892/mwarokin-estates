python
"""
Mwarokin Estates - Trash Management System
Modern Python backend for waste collection and tenant portal
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import random
import threading
import time
from pathlib import Path

# For web framework - using Flask for simplicity, but can be replaced with FastAPI/Django
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mwarokin-secret-key-change-in-production'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ============================================================================
# DATA MODELS
# ============================================================================

class WasteType(str, Enum):
    GENERAL = "general"
    RECYCLABLE = "recycle"
    ORGANIC = "organic"
    HAZARDOUS = "hazardous"

class ActivityType(str, Enum):
    COLLECTION = "collection"
    PICKUP = "pickup"
    ISSUE = "issue"
    ALERT = "alert"
    REPLACE = "replace"

class ActivityStatus(str, Enum):
    DONE = "done"
    PENDING = "pending"
    ALERT = "alert"

class BinStatus(str, Enum):
    EMPTY = "empty"
    LOW = "low"
    MEDIUM = "med"
    HIGH = "high"
    OVERFLOW = "overflow"

@dataclass
class Bin:
    """Smart bin model with sensor data"""
    name: str
    emoji: str
    capacity: int  # kg
    current_level: float  # percentage 0-100
    last_updated: datetime
    status: BinStatus = BinStatus.LOW
    property_id: Optional[str] = None

    def __post_init__(self):
        self._update_status()

    def _update_status(self):
        if self.current_level < 20:
            self.status = BinStatus.EMPTY
        elif self.current_level < 50:
            self.status = BinStatus.LOW
        elif self.current_level < 80:
            self.status = BinStatus.MEDIUM
        else:
            self.status = BinStatus.OVERFLOW

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'emoji': self.emoji,
            'pct': round(self.current_level),
            'updated': int(self.last_updated.timestamp() * 1000),
            'status': self.status.value,
            'capacity': self.capacity
        }

@dataclass
class CollectionSchedule:
    """Waste collection schedule"""
    waste_type: WasteType
    label: str
    icon: str
    emoji: str
    days: List[int]  # 0=Sunday, 6=Saturday
    time: str
    property_id: Optional[str] = None

@dataclass
class Activity:
    """User activity log"""
    timestamp: datetime
    type: ActivityType
    title: str
    description: str
    status: ActivityStatus
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict:
        return {
            'ts': int(self.timestamp.timestamp() * 1000),
            'type': self.type.value,
            'title': self.title,
            'desc': self.description,
            'status': self.status.value,
            'metadata': self.metadata or {}
        }

@dataclass
class Notification:
    """User notification"""
    timestamp: datetime
    text: str
    read: bool = False

    def to_dict(self) -> Dict:
        return {
            'ts': int(self.timestamp.timestamp() * 1000),
            'text': self.text,
            'read': self.read
        }

@dataclass
class PickupRequest:
    """Special pickup request"""
    id: str
    waste_type: WasteType
    preferred_date: datetime
    time_slot: str
    instructions: str
    status: str = "pending"
    created_at: datetime = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now()

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'waste_type': self.waste_type.value,
            'preferred_date': self.preferred_date.isoformat(),
            'time_slot': self.time_slot,
            'instructions': self.instructions,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }

@dataclass
class IssueReport:
    """Issue report from tenant"""
    id: str
    issue_type: str
    description: str
    photo_attachments: List[str]
    status: str = "pending"
    created_at: datetime = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now()

@dataclass
class UserSettings:
    """User preferences"""
    reminders_enabled: bool = True
    alerts_enabled: bool = True
    reports_enabled: bool = False
    lead_time_hours: int = 6
    notification_preferences: Dict[str, bool] = None

    def __post_init__(self):
        if self.notification_preferences is None:
            self.notification_preferences = {
                'general': True,
                'recycle': True,
                'organic': False
            }

# ============================================================================
# DATA STORE
# ============================================================================

class DataStore:
    """In-memory data store with persistence"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._data_file = Path("data_store.json")
        self._load()
    
    def _load(self):
        """Load data from file or initialize defaults"""
        if self._data_file.exists():
            try:
                with open(self._data_file, 'r') as f:
                    data = json.load(f)
                self._from_dict(data)
                logger.info("Data loaded from file")
            except Exception as e:
                logger.error(f"Error loading data: {e}")
                self._init_defaults()
        else:
            self._init_defaults()
            self._save()
    
    def _init_defaults(self):
        """Initialize with default data"""
        now = datetime.now()
        
        self.bins = {
            'general': Bin(
                name="General Waste",
                emoji="🗑️",
                capacity=240,
                current_level=65,
                last_updated=now
            ),
            'recycle': Bin(
                name="Recyclables",
                emoji="♻️",
                capacity=240,
                current_level=85,
                last_updated=now
            ),
            'organic': Bin(
                name="Organic Waste",
                emoji="🌿",
                capacity=120,
                current_level=20,
                last_updated=now
            )
        }
        
        self.schedule = [
            CollectionSchedule(
                waste_type=WasteType.GENERAL,
                label="General Waste",
                icon="general",
                emoji="fa-trash",
                days=[1, 4],  # Monday, Thursday
                time="7:00 – 9:00 AM"
            ),
            CollectionSchedule(
                waste_type=WasteType.RECYCLABLE,
                label="Recyclables",
                icon="recycle",
                emoji="fa-recycle",
                days=[3],  # Wednesday
                time="8:00 – 10:00 AM"
            ),
            CollectionSchedule(
                waste_type=WasteType.ORGANIC,
                label="Organic Waste",
                icon="organic",
                emoji="fa-leaf",
                days=[6],  # Saturday
                time="6:00 – 8:00 AM"
            )
        ]
        
        self.activities = [
            Activity(
                timestamp=now - timedelta(minutes=30),
                type=ActivityType.COLLECTION,
                title="Organic Waste Collected",
                description="Your organic bin was emptied as scheduled.",
                status=ActivityStatus.DONE
            ),
            Activity(
                timestamp=now - timedelta(hours=22),
                type=ActivityType.PICKUP,
                title="Special Pickup Requested",
                description="Additional pickup for general waste — confirmed.",
                status=ActivityStatus.DONE
            ),
            Activity(
                timestamp=now - timedelta(hours=46),
                type=ActivityType.ALERT,
                title="Recycling Bin Alert",
                description="Recyclables bin reached 85% capacity.",
                status=ActivityStatus.ALERT
            )
        ]
        
        self.notifications = [
            Notification(
                timestamp=now - timedelta(minutes=20),
                text="Recyclables bin is at 85% — request a pickup soon."
            ),
            Notification(
                timestamp=now - timedelta(hours=20),
                text="Reminder: General waste collection tomorrow at 7:00 AM."
            )
        ]
        
        self.settings = UserSettings()
        self.pickup_requests: List[PickupRequest] = []
        self.issue_reports: List[IssueReport] = []
        self.eco_score = 75
        
        self._last_activity_id = 0
        self._last_pickup_id = 0
    
    def _from_dict(self, data: Dict):
        """Load state from dictionary"""
        now = datetime.now()
        
        # Load bins
        self.bins = {}
        for key, bin_data in data.get('bins', {}).items():
            self.bins[key] = Bin(
                name=bin_data.get('name', key),
                emoji=bin_data.get('emoji', '🗑️'),
                capacity=bin_data.get('capacity', 240),
                current_level=bin_data.get('current_level', 50),
                last_updated=datetime.fromtimestamp(bin_data.get('last_updated', now.timestamp()))
            )
        
        # Load schedule
        self.schedule = []
        for sched_data in data.get('schedule', []):
            self.schedule.append(CollectionSchedule(
                waste_type=WasteType(sched_data.get('waste_type', 'general')),
                label=sched_data.get('label', ''),
                icon=sched_data.get('icon', ''),
                emoji=sched_data.get('emoji', ''),
                days=sched_data.get('days', []),
                time=sched_data.get('time', '')
            ))
        
        # Load activities
        self.activities = []
        for act_data in data.get('activities', []):
            self.activities.append(Activity(
                timestamp=datetime.fromtimestamp(act_data.get('ts', now.timestamp())),
                type=ActivityType(act_data.get('type', 'collection')),
                title=act_data.get('title', ''),
                description=act_data.get('desc', ''),
                status=ActivityStatus(act_data.get('status', 'done'))
            ))
        
        # Load notifications
        self.notifications = []
        for notif_data in data.get('notifications', []):
            self.notifications.append(Notification(
                timestamp=datetime.fromtimestamp(notif_data.get('ts', now.timestamp())),
                text=notif_data.get('text', ''),
                read=notif_data.get('read', False)
            ))
        
        # Load settings
        settings_data = data.get('settings', {})
        self.settings = UserSettings(
            reminders_enabled=settings_data.get('reminders_enabled', True),
            alerts_enabled=settings_data.get('alerts_enabled', True),
            reports_enabled=settings_data.get('reports_enabled', False),
            lead_time_hours=settings_data.get('lead_time_hours', 6),
            notification_preferences=settings_data.get('notification_preferences', {})
        )
        
        self.pickup_requests = []
        for req_data in data.get('pickup_requests', []):
            self.pickup_requests.append(PickupRequest(
                id=req_data.get('id', ''),
                waste_type=WasteType(req_data.get('waste_type', 'general')),
                preferred_date=datetime.fromisoformat(req_data.get('preferred_date')),
                time_slot=req_data.get('time_slot', ''),
                instructions=req_data.get('instructions', ''),
                status=req_data.get('status', 'pending'),
                created_at=datetime.fromisoformat(req_data.get('created_at'))
            ))
        
        self.issue_reports = []
        for issue_data in data.get('issue_reports', []):
            self.issue_reports.append(IssueReport(
                id=issue_data.get('id', ''),
                issue_type=issue_data.get('issue_type', ''),
                description=issue_data.get('description', ''),
                photo_attachments=issue_data.get('photo_attachments', []),
                status=issue_data.get('status', 'pending'),
                created_at=datetime.fromisoformat(issue_data.get('created_at'))
            ))
        
        self.eco_score = data.get('eco_score', 75)
        self._last_activity_id = data.get('_last_activity_id', 0)
        self._last_pickup_id = data.get('_last_pickup_id', 0)
    
    def _to_dict(self) -> Dict:
        """Convert state to dictionary for persistence"""
        return {
            'bins': {
                key: {
                    'name': bin_data.name,
                    'emoji': bin_data.emoji,
                    'capacity': bin_data.capacity,
                    'current_level': bin_data.current_level,
                    'last_updated': bin_data.last_updated.timestamp()
                }
                for key, bin_data in self.bins.items()
            },
            'schedule': [
                {
                    'waste_type': s.waste_type.value,
                    'label': s.label,
                    'icon': s.icon,
                    'emoji': s.emoji,
                    'days': s.days,
                    'time': s.time
                }
                for s in self.schedule
            ],
            'activities': [a.to_dict() for a in self.activities],
            'notifications': [n.to_dict() for n in self.notifications],
            'settings': {
                'reminders_enabled': self.settings.reminders_enabled,
                'alerts_enabled': self.settings.alerts_enabled,
                'reports_enabled': self.settings.reports_enabled,
                'lead_time_hours': self.settings.lead_time_hours,
                'notification_preferences': self.settings.notification_preferences
            },
            'pickup_requests': [r.to_dict() for r in self.pickup_requests],
            'issue_reports': [
                {
                    'id': i.id,
                    'issue_type': i.issue_type,
                    'description': i.description,
                    'photo_attachments': i.photo_attachments,
                    'status': i.status,
                    'created_at': i.created_at.isoformat()
                }
                for i in self.issue_reports
            ],
            'eco_score': self.eco_score,
            '_last_activity_id': self._last_activity_id,
            '_last_pickup_id': self._last_pickup_id
        }
    
    def _save(self):
        """Save data to file"""
        try:
            with open(self._data_file, 'w') as f:
                json.dump(self._to_dict(), f, indent=2)
            logger.debug("Data saved to file")
        except Exception as e:
            logger.error(f"Error saving data: {e}")
    
    def save(self):
        """Public save method"""
        self._save()
    
    def add_activity(self, activity: Activity):
        """Add a new activity and maintain limit"""
        self.activities.insert(0, activity)
        self.activities = self.activities[:60]  # Keep last 60
        self._last_activity_id += 1
        self._save()
    
    def add_notification(self, notification: Notification):
        """Add a new notification and maintain limit"""
        self.notifications.insert(0, notification)
        self.notifications = self.notifications[:20]  # Keep last 20
        self._save()
    
    def get_next_collection(self) -> Optional[tuple]:
        """Get the next collection date and schedule"""
        now = datetime.now()
        best = None
        
        for sched in self.schedule:
            for day_offset in range(14):  # Look ahead 2 weeks
                dt = now + timedelta(days=day_offset)
                if dt.weekday() in sched.days:
                    # Parse time
                    try:
                        hour = int(sched.time.split(':')[0])
                        if 'PM' in sched.time and hour < 12:
                            hour += 12
                    except:
                        hour = 7  # Default
                    
                    dt = dt.replace(hour=hour, minute=0, second=0, microsecond=0)
                    if dt > now:
                        if not best or dt < best[0]:
                            best = (dt, sched)
                        break
        
        return best

# ============================================================================
# SERVICE LAYER
# ============================================================================

class WasteManagementService:
    """Core business logic for waste management"""
    
    def __init__(self):
        self.store = DataStore()
    
    def get_dashboard_data(self) -> Dict:
        """Get complete dashboard data"""
        next_collection = self.store.get_next_collection()
        
        return {
            'eco_score': self.store.eco_score,
            'bins': {key: bin_data.to_dict() for key, bin_data in self.store.bins.items()},
            'schedule': [
                {
                    'key': s.waste_type.value,
                    'label': s.label,
                    'icon': s.icon,
                    'emoji': s.emoji,
                    'days': s.days,
                    'time': s.time,
                    'day_names': [['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][d] for d in s.days]
                }
                for s in self.store.schedule
            ],
            'activities': [a.to_dict() for a in self.store.activities[:10]],
            'notifications': [n.to_dict() for n in self.store.notifications],
            'next_collection': {
                'label': next_collection[1].label if next_collection else None,
                'timestamp': int(next_collection[0].timestamp() * 1000) if next_collection else None,
                'time': next_collection[1].time if next_collection else None
            },
            'settings': {
                'reminders_enabled': self.store.settings.reminders_enabled,
                'alerts_enabled': self.store.settings.alerts_enabled,
                'reports_enabled': self.store.settings.reports_enabled,
                'lead_time_hours': self.store.settings.lead_time_hours,
                'notification_preferences': self.store.settings.notification_preferences
            }
        }
    
    def update_bin_level(self, bin_key: str, level: float) -> Dict:
        """Update a bin's fill level"""
        if bin_key not in self.store.bins:
            raise ValueError(f"Bin '{bin_key}' not found")
        
        bin_data = self.store.bins[bin_key]
        old_level = bin_data.current_level
        bin_data.current_level = max(0, min(100, level))
        bin_data.last_updated = datetime.now()
        bin_data._update_status()
        
        # Check for overflow alert
        if old_level < 80 and bin_data.current_level >= 80 and self.store.settings.alerts_enabled:
            self.store.add_activity(Activity(
                timestamp=datetime.now(),
                type=ActivityType.ALERT,
                title=f"{bin_data.name} Bin Alert",
                description=f"{bin_data.name} bin reached {bin_data.current_level:.0f}% capacity.",
                status=ActivityStatus.ALERT
            ))
            self.store.add_notification(Notification(
                timestamp=datetime.now(),
                text=f"{bin_data.name} bin is at {bin_data.current_level:.0f}% — request a pickup soon."
            ))
        
        self.store._save()
        return bin_data.to_dict()
    
    def schedule_pickup(self, waste_type: str, preferred_date: str, 
                        time_slot: str, instructions: str) -> PickupRequest:
        """Schedule a special pickup"""
        try:
            waste_enum = WasteType(waste_type.lower())
            date_obj = datetime.fromisoformat(preferred_date)
        except ValueError as e:
            raise ValueError(f"Invalid input: {e}")
        
        if date_obj < datetime.now():
            raise ValueError("Preferred date must be in the future")
        
        pickup = PickupRequest(
            id=f"P-{self.store._last_pickup_id + 1:06d}",
            waste_type=waste_enum,
            preferred_date=date_obj,
            time_slot=time_slot,
            instructions=instructions
        )
        
        self.store.pickup_requests.append(pickup)
        self.store._last_pickup_id += 1
        
        self.store.add_activity(Activity(
            timestamp=datetime.now(),
            type=ActivityType.PICKUP,
            title="Special Pickup Scheduled",
            description=f"{waste_type} on {date_obj.date()} · {time_slot}",
            status=ActivityStatus.PENDING
        ))
        
        self.store.add_notification(Notification(
            timestamp=datetime.now(),
            text=f"Your {waste_type.lower()} pickup is scheduled for {date_obj.date()}."
        ))
        
        self.store._save()
        return pickup
    
    def report_issue(self, issue_type: str, description: str, 
                     photo_attachments: List[str] = None) -> IssueReport:
        """Report an issue"""
        if not issue_type or not description:
            raise ValueError("Issue type and description are required")
        
        issue = IssueReport(
            id=f"I-{len(self.store.issue_reports) + 1:06d}",
            issue_type=issue_type,
            description=description,
            photo_attachments=photo_attachments or []
        )
        
        self.store.issue_reports.append(issue)
        
        self.store.add_activity(Activity(
            timestamp=datetime.now(),
            type=ActivityType.ISSUE,
            title=issue_type,
            description=f"{description} (photos: {len(issue.photo_attachments)})",
            status=ActivityStatus.PENDING,
            metadata={'issue_id': issue.id}
        ))
        
        self.store.add_notification(Notification(
            timestamp=datetime.now(),
            text=f"Issue reported: {issue_type}. Our team will follow up."
        ))
        
        self.store._save()
        return issue
    
    def request_bin_replacement(self, bin_type: str, reason: str) -> Dict:
        """Request a bin replacement"""
        valid_bins = ['General Waste', 'Recyclables', 'Organic Waste']
        if bin_type not in valid_bins:
            raise ValueError(f"Invalid bin type. Must be one of: {valid_bins}")
        
        self.store.add_activity(Activity(
            timestamp=datetime.now(),
            type=ActivityType.REPLACE,
            title="Bin Replacement Requested",
            description=f"{bin_type} — {reason}",
            status=ActivityStatus.PENDING
        ))
        
        self.store.add_notification(Notification(
            timestamp=datetime.now(),
            text=f"Replacement requested for {bin_type}."
        ))
        
        self.store._save()
        return {'bin_type': bin_type, 'reason': reason, 'status': 'pending'}
    
    def update_settings(self, settings: Dict) -> UserSettings:
        """Update user settings"""
        if 'reminders_enabled' in settings:
            self.store.settings.reminders_enabled = settings['reminders_enabled']
        if 'alerts_enabled' in settings:
            self.store.settings.alerts_enabled = settings['alerts_enabled']
        if 'reports_enabled' in settings:
            self.store.settings.reports_enabled = settings['reports_enabled']
        if 'lead_time_hours' in settings:
            self.store.settings.lead_time_hours = max(1, min(24, settings['lead_time_hours']))
        if 'notification_preferences' in settings:
            self.store.settings.notification_preferences.update(settings['notification_preferences'])
        
        self.store._save()
        return self.store.settings
    
    def get_statistics(self) -> Dict:
        """Get waste statistics"""
        total_waste = sum(b.current_level * b.capacity / 100 for b in self.store.bins.values())
        recycled_waste = self.store.bins['recycle'].current_level * self.store.bins['recycle'].capacity / 100
        organic_waste = self.store.bins['organic'].current_level * self.store.bins['organic'].capacity / 100
        general_waste = self.store.bins['general'].current_level * self.store.bins['general'].capacity / 100
        
        return {
            'total_waste': round(total_waste, 1),
            'recycled_waste': round(recycled_waste, 1),
            'organic_waste': round(organic_waste, 1),
            'general_waste': round(general_waste, 1),
            'recycling_rate': round((recycled_waste / total_waste * 100) if total_waste > 0 else 0, 1),
            'pickup_count': len([a for a in self.store.activities if a.type == ActivityType.COLLECTION]),
            'eco_score': self.store.eco_score,
            'monthly_trend': self._get_monthly_trend()
        }
    
    def _get_monthly_trend(self) -> List[Dict]:
        """Get monthly waste trend data"""
        months = 6
        now = datetime.now()
        trend = []
        
        # Generate synthetic trend data based on current levels
        for i in range(months - 1, -1, -1):
            month = now - timedelta(days=30 * i)
            base_total = sum(b.current_level * b.capacity / 100 for b in self.store.bins.values())
            variation = random.uniform(-0.15, 0.15)
            recycled = self.store.bins['recycle'].current_level * self.store.bins['recycle'].capacity / 100
            
            trend.append({
                'month': month.strftime('%b'),
                'total': round(base_total * (1 + variation), 1),
                'recycled': round(recycled * (1 + variation), 1)
            })
        
        return trend
    
    def clear_notifications(self):
        """Clear all notifications"""
        self.store.notifications = []
        self.store._save()
    
    def mark_notification_read(self, index: int):
        """Mark a notification as read"""
        if 0 <= index < len(self.store.notifications):
            self.store.notifications[index].read = True
            self.store._save()

# ============================================================================
# BACKEND TASKS / SIMULATION
# ============================================================================

class SensorSimulator:
    """Simulate sensor data for demonstration"""
    
    def __init__(self, service: WasteManagementService):
        self.service = service
        self.running = False
        self._thread = None
    
    def start(self):
        """Start the sensor simulation"""
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Sensor simulation started")
    
    def stop(self):
        """Stop the sensor simulation"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("Sensor simulation stopped")
    
    def _run(self):
        """Main simulation loop"""
        while self.running:
            try:
                # Randomly update bin levels
                for bin_key in self.service.store.bins.keys():
                    if random.random() < 0.3:  # 30% chance of update
                        current = self.service.store.bins[bin_key].current_level
                        # Simulate waste generation (gradual increase)
                        delta = random.uniform(0, 3)
                        new_level = min(100, current + delta)
                        self.service.update_bin_level(bin_key, new_level)
                
                # Randomly add notifications for testing
                if random.random() < 0.05:  # 5% chance
                    self.service.store.add_notification(Notification(
                        timestamp=datetime.now(),
                        text=f"Sensor update: Bin levels refreshed"
                    ))
                
            except Exception as e:
                logger.error(f"Error in sensor simulation: {e}")
            
            time.sleep(15)  # Run every 15 seconds

# ============================================================================
# API ROUTES
# ============================================================================

service = WasteManagementService()
sensor_sim = SensorSimulator(service)

# Start sensor simulation
sensor_sim.start()

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    """Get dashboard data"""
    try:
        data = service.get_dashboard_data()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bins', methods=['GET'])
def get_bins():
    """Get all bin statuses"""
    try:
        bins = {key: bin_data.to_dict() for key, bin_data in service.store.bins.items()}
        return jsonify({'success': True, 'data': bins})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bins/<bin_key>', methods=['POST'])
def update_bin(bin_key):
    """Update bin level"""
    try:
        data = request.get_json()
        if 'level' not in data:
            return jsonify({'success': False, 'error': 'Level is required'}), 400
        
        level = float(data['level'])
        bin_data = service.update_bin_level(bin_key, level)
        return jsonify({'success': True, 'data': bin_data})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/pickup', methods=['POST'])
def schedule_pickup():
    """Schedule a special pickup"""
    try:
        data = request.get_json()
        required = ['waste_type', 'preferred_date', 'time_slot']
        for field in required:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400
        
        pickup = service.schedule_pickup(
            waste_type=data['waste_type'],
            preferred_date=data['preferred_date'],
            time_slot=data['time_slot'],
            instructions=data.get('instructions', '')
        )
        
        return jsonify({'success': True, 'data': pickup.to_dict()})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/issue', methods=['POST'])
def report_issue():
    """Report an issue"""
    try:
        data = request.get_json()
        required = ['issue_type', 'description']
        for field in required:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400
        
        issue = service.report_issue(
            issue_type=data['issue_type'],
            description=data['description'],
            photo_attachments=data.get('photo_attachments', [])
        )
        
        return jsonify({'success': True, 'data': {
            'id': issue.id,
            'issue_type': issue.issue_type,
            'description': issue.description,
            'status': issue.status,
            'created_at': issue.created_at.isoformat()
        }})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/replace', methods=['POST'])
def request_replacement():
    """Request bin replacement"""
    try:
        data = request.get_json()
        if 'bin_type' not in data or 'reason' not in data:
            return jsonify({'success': False, 'error': 'bin_type and reason are required'}), 400
        
        result = service.request_bin_replacement(
            bin_type=data['bin_type'],
            reason=data['reason']
        )
        
        return jsonify({'success': True, 'data': result})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    """Get or update settings"""
    if request.method == 'GET':
        return jsonify({'success': True, 'data': {
            'reminders_enabled': service.store.settings.reminders_enabled,
            'alerts_enabled': service.store.settings.alerts_enabled,
            'reports_enabled': service.store.settings.reports_enabled,
            'lead_time_hours': service.store.settings.lead_time_hours,
            'notification_preferences': service.store.settings.notification_preferences
        }})
    
    try:
        data = request.get_json()
        settings = service.update_settings(data)
        return jsonify({'success': True, 'data': {
            'reminders_enabled': settings.reminders_enabled,
            'alerts_enabled': settings.alerts_enabled,
            'reports_enabled': settings.reports_enabled,
            'lead_time_hours': settings.lead_time_hours,
            'notification_preferences': settings.notification_preferences
        }})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Get waste statistics"""
    try:
        stats = service.get_statistics()
        return jsonify({'success': True, 'data': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/activity', methods=['GET'])
def get_activity():
    """Get activity history"""
    try:
        filter_type = request.args.get('type', 'all')
        activities = service.store.activities
        
        if filter_type != 'all':
            activities = [a for a in activities if a.type.value == filter_type]
        
        return jsonify({'success': True, 'data': [a.to_dict() for a in activities]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notifications', methods=['GET', 'DELETE'])
def handle_notifications():
    """Get or clear notifications"""
    if request.method == 'GET':
        return jsonify({'success': True, 'data': [n.to_dict() for n in service.store.notifications]})
    
    try:
        service.clear_notifications()
        return jsonify({'success': True, 'message': 'All notifications cleared'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/schedule', methods=['GET'])
def get_schedule():
    """Get collection schedule"""
    try:
        schedule = [
            {
                'key': s.waste_type.value,
                'label': s.label,
                'icon': s.icon,
                'emoji': s.emoji,
                'days': s.days,
                'day_names': [['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][d] for d in s.days],
                'time': s.time
            }
            for s in service.store.schedule
        ]
        return jsonify({'success': True, 'data': schedule})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export', methods=['GET'])
def export_history():
    """Export activity history as text"""
    try:
        lines = []
        for a in service.store.activities:
            date = a.timestamp.strftime('%d %b %Y, %H:%M')
            lines.append(f"{date} | {a.type.value} | {a.title} — {a.description} | {a.status.value}")
        
        text = "\n".join(lines)
        return text, 200, {'Content-Type': 'text/plain', 'Content-Disposition': 'attachment; filename=mwarokin-waste-history.txt'}
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# WEBSOCKET EVENTS (for real-time updates)
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'status': 'ok'})

@socketio.on('subscribe')
def handle_subscribe(data):
    """Handle subscription to updates"""
    room = data.get('room', 'dashboard')
    join_room(room)
    emit('subscribed', {'room': room})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

def emit_bin_update(bin_key: str, bin_data: Dict):
    """Emit bin update via WebSocket"""
    socketio.emit('bin_update', {'key': bin_key, 'data': bin_data})

def emit_notification(notification: Dict):
    """Emit notification via WebSocket"""
    socketio.emit('new_notification', notification)

# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

def create_app():
    """Create and configure the Flask application"""
    return app

if __name__ == '__main__':
    try:
        logger.info("Starting Mwarokin Estates Waste Management System")
        logger.info(f"Data store: {DataStore._instance._data_file}")
        
        # Run the app with SocketIO support
        socketio.run(
            app,
            host='0.0.0.0',
            port=5000,
            debug=True,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sensor_sim.stop()
    finally:
        logger.info("Application stopped")
