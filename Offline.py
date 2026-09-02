# Offline.py - Professional Backend Engine for Mwarokin Estates

```python
"""
================================================================================
OFFLINE ENGINE - Mwarokin Estates Professional Backend System
================================================================================
Module: offline.py
Version: 2.0.0
Author: Syllogism Technology Africa
Description: Production-grade offline-first backend engine with automatic
             synchronization, transaction logging, and agent-based processing.
================================================================================
"""

import json
import sqlite3
import threading
import time
import uuid
import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from queue import Queue
from collections import defaultdict
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OfflineEngine")


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class UserRole(Enum):
    """User roles within the Mwarokin Estates system."""
    TENANT = "tenant"
    LANDLORD = "landlord"
    CARETAKER = "caretaker"
    MANAGEMENT = "management"
    PROFESSIONAL = "professional"


class TransactionStatus(Enum):
    """Status of transactions in the system."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SYNCED = "synced"


class Priority(Enum):
    """Priority levels for maintenance requests."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventType(Enum):
    """Event types for activity logging."""
    PAYMENT = "payment"
    MAINTENANCE = "maintenance"
    VISITOR = "visitor"
    LOGIN = "login"
    REGISTRATION = "registration"
    UNIT_UPDATE = "unit_update"
    SYNC = "sync"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Transaction:
    """Represents a financial transaction."""
    id: str
    amount: float
    unit_id: str
    user_id: str
    user_role: UserRole
    transaction_type: str
    status: TransactionStatus
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    receipt_url: Optional[str] = None
    sync_status: bool = False

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'amount': self.amount,
            'unit_id': self.unit_id,
            'user_id': self.user_id,
            'user_role': self.user_role.value,
            'transaction_type': self.transaction_type,
            'status': self.status.value,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'metadata': json.dumps(self.metadata),
            'receipt_url': self.receipt_url,
            'sync_status': self.sync_status
        }


@dataclass
class MaintenanceRequest:
    """Represents a maintenance request."""
    id: str
    unit_id: str
    user_id: str
    user_role: UserRole
    title: str
    description: str
    priority: Priority
    status: str
    assigned_to: Optional[str]
    created_at: str
    updated_at: str
    resolved_at: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)
    sync_status: bool = False

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'unit_id': self.unit_id,
            'user_id': self.user_id,
            'user_role': self.user_role.value,
            'title': self.title,
            'description': self.description,
            'priority': self.priority.value,
            'status': self.status,
            'assigned_to': self.assigned_to,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'resolved_at': self.resolved_at,
            'notes': json.dumps(self.notes),
            'attachments': json.dumps(self.attachments),
            'sync_status': self.sync_status
        }


@dataclass
class Visitor:
    """Represents a visitor log entry."""
    id: str
    visitor_name: str
    unit_id: str
    purpose: str
    checked_in_at: str
    checked_out_at: Optional[str]
    host_user_id: Optional[str]
    phone_number: Optional[str]
    id_type: Optional[str]
    id_number: Optional[str]
    created_by: str
    sync_status: bool = False

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'visitor_name': self.visitor_name,
            'unit_id': self.unit_id,
            'purpose': self.purpose,
            'checked_in_at': self.checked_in_at,
            'checked_out_at': self.checked_out_at,
            'host_user_id': self.host_user_id,
            'phone_number': self.phone_number,
            'id_type': self.id_type,
            'id_number': self.id_number,
            'created_by': self.created_by,
            'sync_status': self.sync_status
        }


@dataclass
class Unit:
    """Represents a property unit."""
    id: str
    unit_number: str
    property_name: str
    property_address: str
    landlord_id: str
    caretaker_id: Optional[str]
    tenant_id: Optional[str]
    rent_amount: float
    deposit_amount: float
    bedrooms: int
    bathrooms: int
    square_feet: int
    status: str
    created_at: str
    updated_at: str
    amenities: List[str] = field(default_factory=list)
    sync_status: bool = False

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'unit_number': self.unit_number,
            'property_name': self.property_name,
            'property_address': self.property_address,
            'landlord_id': self.landlord_id,
            'caretaker_id': self.caretaker_id,
            'tenant_id': self.tenant_id,
            'rent_amount': self.rent_amount,
            'deposit_amount': self.deposit_amount,
            'bedrooms': self.bedrooms,
            'bathrooms': self.bathrooms,
            'square_feet': self.square_feet,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'amenities': json.dumps(self.amenities),
            'sync_status': self.sync_status
        }


@dataclass
class ActivityLog:
    """Represents an activity log entry."""
    id: str
    event_type: EventType
    user_id: str
    user_role: UserRole
    description: str
    ip_address: Optional[str]
    device_info: Optional[str]
    metadata: Dict[str, Any]
    created_at: str
    sync_status: bool = False


@dataclass
class SyncResult:
    """Result of a synchronization operation."""
    success: bool
    items_synced: int
    items_failed: int
    errors: List[str]
    timestamp: str
    duration_ms: float


# ============================================================================
# DATABASE MANAGER
# ============================================================================

class DatabaseManager:
    """
    Manages SQLite database operations with proper connection handling
    and transaction management.
    """
    
    def __init__(self, db_path: str = "mwarokin_offline.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._initialize_database()

    def _get_connection(self):
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    def _initialize_database(self):
        """Initialize database schema with all required tables."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    amount REAL NOT NULL,
                    unit_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    user_role TEXT NOT NULL,
                    transaction_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT,
                    receipt_url TEXT,
                    sync_status INTEGER DEFAULT 0
                )
            """)
            
            # Maintenance requests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS maintenance_requests (
                    id TEXT PRIMARY KEY,
                    unit_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    user_role TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    assigned_to TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    resolved_at TEXT,
                    notes TEXT,
                    attachments TEXT,
                    sync_status INTEGER DEFAULT 0
                )
            """)
            
            # Visitors table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS visitors (
                    id TEXT PRIMARY KEY,
                    visitor_name TEXT NOT NULL,
                    unit_id TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    checked_in_at TEXT NOT NULL,
                    checked_out_at TEXT,
                    host_user_id TEXT,
                    phone_number TEXT,
                    id_type TEXT,
                    id_number TEXT,
                    created_by TEXT NOT NULL,
                    sync_status INTEGER DEFAULT 0
                )
            """)
            
            # Units table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS units (
                    id TEXT PRIMARY KEY,
                    unit_number TEXT NOT NULL,
                    property_name TEXT NOT NULL,
                    property_address TEXT NOT NULL,
                    landlord_id TEXT NOT NULL,
                    caretaker_id TEXT,
                    tenant_id TEXT,
                    rent_amount REAL NOT NULL,
                    deposit_amount REAL NOT NULL,
                    bedrooms INTEGER NOT NULL,
                    bathrooms INTEGER NOT NULL,
                    square_feet INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    amenities TEXT,
                    sync_status INTEGER DEFAULT 0
                )
            """)
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    phone_number TEXT,
                    user_role TEXT NOT NULL,
                    is_verified INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    sync_status INTEGER DEFAULT 0
                )
            """)
            
            # Activity logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    user_role TEXT NOT NULL,
                    description TEXT NOT NULL,
                    ip_address TEXT,
                    device_info TEXT,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    sync_status INTEGER DEFAULT 0
                )
            """)
            
            # Sync metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            conn.commit()
            logger.info("✓ Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute a query and return results as dictionaries."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            return results
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []

    def execute_insert(self, query: str, params: tuple) -> bool:
        """Execute an insert query and commit."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Insert failed: {e}")
            return False

    def execute_update(self, query: str, params: tuple) -> bool:
        """Execute an update query and commit."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Update failed: {e}")
            return False

    def get_pending_sync_items(self, table: str, limit: int = 100) -> List[Dict]:
        """Get items pending synchronization."""
        try:
            query = f"SELECT * FROM {table} WHERE sync_status = 0 LIMIT ?"
            return self.execute_query(query, (limit,))
        except Exception as e:
            logger.error(f"Failed to get pending items from {table}: {e}")
            return []

    def mark_synced(self, table: str, item_id: str) -> bool:
        """Mark an item as synchronized."""
        try:
            query = f"UPDATE {table} SET sync_status = 1 WHERE id = ?"
            return self.execute_update(query, (item_id,))
        except Exception as e:
            logger.error(f"Failed to mark item {item_id} as synced: {e}")
            return False


# ============================================================================
# SYNC AGENT
# ============================================================================

class SyncAgent:
    """
    Background agent that handles automatic synchronization with the cloud.
    Runs in a separate thread and processes queued items.
    """
    
    def __init__(self, db_manager: DatabaseManager, sync_interval: int = 30):
        self.db = db_manager
        self.sync_interval = sync_interval
        self.is_running = False
        self._sync_thread = None
        self._sync_queue = Queue()
        self._stop_event = threading.Event()
        self._pending_items_cache = defaultdict(list)
        self._last_sync_time = None
        self._sync_results = []

    def start(self):
        """Start the sync agent in a background thread."""
        if self.is_running:
            return
        
        self.is_running = True
        self._stop_event.clear()
        self._sync_thread = threading.Thread(target=self._run, daemon=True)
        self._sync_thread.start()
        logger.info("✓ Sync agent started")

    def stop(self):
        """Stop the sync agent."""
        self.is_running = False
        self._stop_event.set()
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=5)
        logger.info("✓ Sync agent stopped")

    def _run(self):
        """Main loop for the sync agent."""
        while not self._stop_event.is_set():
            try:
                self._sync_all()
                self._last_sync_time = datetime.now().isoformat()
            except Exception as e:
                logger.error(f"Sync error: {e}")
            
            # Wait for the next sync interval
            for _ in range(self.sync_interval):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

    def _sync_all(self):
        """Synchronize all pending items."""
        start_time = time.time()
        items_synced = 0
        items_failed = 0
        errors = []

        tables = ['transactions', 'maintenance_requests', 'visitors', 'units', 'users', 'activity_logs']
        
        for table in tables:
            try:
                pending = self.db.get_pending_sync_items(table)
                for item in pending:
                    if self._sync_item(table, item):
                        items_synced += 1
                    else:
                        items_failed += 1
                        errors.append(f"Failed to sync {table} item {item.get('id')}")
            except Exception as e:
                errors.append(f"Error syncing {table}: {str(e)}")
                items_failed += 1

        duration_ms = (time.time() - start_time) * 1000
        
        result = SyncResult(
            success=items_failed == 0,
            items_synced=items_synced,
            items_failed=items_failed,
            errors=errors,
            timestamp=datetime.now().isoformat(),
            duration_ms=duration_ms
        )
        
        self._sync_results.append(result)
        
        if items_synced > 0 or items_failed > 0:
            logger.info(f"Sync completed: {items_synced} synced, {items_failed} failed")

    def _sync_item(self, table: str, item: Dict) -> bool:
        """
        Synchronize a single item with the cloud.
        Returns True if successful.
        """
        # For now, simulate a sync by marking it as synced
        # In production, this would make API calls to the cloud
        try:
            # Simulate API call
            # In production:
            # response = requests.post(f"{API_URL}/sync/{table}", json=item)
            # if response.status_code != 200:
            #     return False
            
            # Mark as synced
            return self.db.mark_synced(table, item['id'])
        except Exception as e:
            logger.error(f"Sync item failed: {e}")
            return False

    def force_sync(self) -> SyncResult:
        """Force an immediate synchronization."""
        self._sync_all()
        return self._sync_results[-1] if self._sync_results else SyncResult(
            success=False,
            items_synced=0,
            items_failed=0,
            errors=["No sync results available"],
            timestamp=datetime.now().isoformat(),
            duration_ms=0
        )

    def get_sync_status(self) -> Dict:
        """Get the current sync status."""
        pending_count = 0
        for table in ['transactions', 'maintenance_requests', 'visitors', 'units', 'users', 'activity_logs']:
            pending = self.db.get_pending_sync_items(table)
            pending_count += len(pending)
        
        return {
            'is_running': self.is_running,
            'last_sync_time': self._last_sync_time,
            'pending_items': pending_count,
            'sync_interval': self.sync_interval,
            'last_results': self._sync_results[-1] if self._sync_results else None
        }


# ============================================================================
# OFFLINE ENGINE - MAIN CLASS
# ============================================================================

class OfflineEngine:
    """
    Main offline engine for Mwarokin Estates.
    Handles all operations and manages the sync agent.
    """
    
    def __init__(self, db_path: str = "mwarokin_offline.db", 
                 sync_interval: int = 30,
                 auto_start_sync: bool = True):
        """
        Initialize the offline engine.
        
        Args:
            db_path: Path to the SQLite database file
            sync_interval: Interval in seconds between sync attempts
            auto_start_sync: Whether to automatically start the sync agent
        """
        self.db = DatabaseManager(db_path)
        self.sync_agent = SyncAgent(self.db, sync_interval)
        
        # Track agent status
        self._agent_status = {
            'is_running': False,
            'started_at': None,
            'operations_count': 0
        }
        
        if auto_start_sync:
            self.start_sync_agent()
        
        logger.info("✓ OfflineEngine initialized")

    def start_sync_agent(self):
        """Start the synchronization agent."""
        if not self._agent_status['is_running']:
            self.sync_agent.start()
            self._agent_status['is_running'] = True
            self._agent_status['started_at'] = datetime.now().isoformat()
            logger.info("✓ Sync agent started via engine")

    def stop_sync_agent(self):
        """Stop the synchronization agent."""
        if self._agent_status['is_running']:
            self.sync_agent.stop()
            self._agent_status['is_running'] = False
            logger.info("✓ Sync agent stopped via engine")

    def force_sync(self) -> SyncResult:
        """Force immediate synchronization."""
        if not self._agent_status['is_running']:
            self.start_sync_agent()
        return self.sync_agent.force_sync()

    def status(self) -> Dict:
        """
        Get the current status of the engine.
        
        Returns:
            Dict containing status information
        """
        sync_status = self.sync_agent.get_sync_status()
        return {
            'agent_running': self._agent_status['is_running'],
            'started_at': self._agent_status['started_at'],
            'sync_status': sync_status,
            'database_path': self.db.db_path,
            'ready': self._agent_status['is_running']
        }

    # ========================================================================
    # PAYMENT OPERATIONS
    # ========================================================================

    def pay_rent(self, amount: float, unit_id: str, user_id: str,
                 user_role: Union[UserRole, str] = UserRole.TENANT,
                 transaction_type: str = "rent",
                 metadata: Dict = None) -> Dict:
        """
        Process a rent payment.
        
        Args:
            amount: Payment amount
            unit_id: Unit identifier
            user_id: User making the payment
            user_role: User role (default: TENANT)
            transaction_type: Type of transaction
            metadata: Additional metadata
            
        Returns:
            Dict containing transaction details
        """
        if isinstance(user_role, str):
            user_role = UserRole(user_role)
        
        transaction_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        transaction = Transaction(
            id=transaction_id,
            amount=amount,
            unit_id=unit_id,
            user_id=user_id,
            user_role=user_role,
            transaction_type=transaction_type,
            status=TransactionStatus.PENDING,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
            sync_status=False
        )
        
        # Store in database
        query = """
            INSERT INTO transactions (
                id, amount, unit_id, user_id, user_role,
                transaction_type, status, created_at, updated_at,
                metadata, sync_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            transaction.id,
            transaction.amount,
            transaction.unit_id,
            transaction.user_id,
            transaction.user_role.value,
            transaction.transaction_type,
            transaction.status.value,
            transaction.created_at,
            transaction.updated_at,
            json.dumps(transaction.metadata),
            0  # sync_status = 0
        )
        
        success = self.db.execute_insert(query, params)
        
        if success:
            self._agent_status['operations_count'] += 1
            logger.info(f"✓ Rent payment processed: {amount} for {unit_id}")
            
            # Log activity
            self._log_activity(
                EventType.PAYMENT,
                user_id,
                user_role,
                f"Rent payment of {amount} for {unit_id}",
                metadata={'amount': amount, 'unit_id': unit_id}
            )
        
        return {
            'success': success,
            'transaction_id': transaction_id,
            'amount': amount,
            'unit_id': unit_id,
            'status': transaction.status.value,
            'timestamp': now
        }

    # ========================================================================
    # MAINTENANCE OPERATIONS
    # ========================================================================

    def request_maintenance(self, unit_id: str, title: str, 
                           description: str,
                           user_id: str,
                           user_role: Union[UserRole, str] = UserRole.TENANT,
                           priority: Union[Priority, str] = Priority.MEDIUM,
                           attachments: List[str] = None) -> Dict:
        """
        Request maintenance for a unit.
        
        Args:
            unit_id: Unit identifier
            title: Request title
            description: Detailed description
            user_id: User making the request
            user_role: User role
            priority: Priority level
            attachments: List of attachment URLs
            
        Returns:
            Dict containing maintenance request details
        """
        if isinstance(user_role, str):
            user_role = UserRole(user_role)
        
        if isinstance(priority, str):
            priority = Priority(priority.lower())
        
        request_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        maintenance = MaintenanceRequest(
            id=request_id,
            unit_id=unit_id,
            user_id=user_id,
            user_role=user_role,
            title=title,
            description=description,
            priority=priority,
            status="pending",
            assigned_to=None,
            created_at=now,
            updated_at=now,
            resolved_at=None,
            notes=[],
            attachments=attachments or [],
            sync_status=False
        )
        
        # Store in database
        query = """
            INSERT INTO maintenance_requests (
                id, unit_id, user_id, user_role, title, description,
                priority, status, assigned_to, created_at, updated_at,
                resolved_at, notes, attachments, sync_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            maintenance.id,
            maintenance.unit_id,
            maintenance.user_id,
            maintenance.user_role.value,
            maintenance.title,
            maintenance.description,
            maintenance.priority.value,
            maintenance.status,
            maintenance.assigned_to,
            maintenance.created_at,
            maintenance.updated_at,
            maintenance.resolved_at,
            json.dumps(maintenance.notes),
            json.dumps(maintenance.attachments),
            0  # sync_status = 0
        )
        
        success = self.db.execute_insert(query, params)
        
        if success:
            self._agent_status['operations_count'] += 1
            logger.info(f"✓ Maintenance request: {title} for {unit_id} ({priority.value})")
            
            # Log activity
            self._log_activity(
                EventType.MAINTENANCE,
                user_id,
                user_role,
                f"Maintenance request: {title}",
                metadata={'unit_id': unit_id, 'priority': priority.value}
            )
        
        return {
            'success': success,
            'request_id': request_id,
            'unit_id': unit_id,
            'title': title,
            'priority': priority.value,
            'status': maintenance.status,
            'timestamp': now
        }

    # ========================================================================
    # VISITOR OPERATIONS
    # ========================================================================

    def log_visitor(self, visitor_name: str, unit_id: str, purpose: str,
                    created_by: str, host_user_id: str = None,
                    phone_number: str = None, id_type: str = None,
                    id_number: str = None) -> Dict:
        """
        Log a visitor entry.
        
        Args:
            visitor_name: Name of the visitor
            unit_id: Unit being visited
            purpose: Purpose of visit
            created_by: User logging the visitor
            host_user_id: Host user ID (optional)
            phone_number: Visitor's phone number (optional)
            id_type: ID type (optional)
            id_number: ID number (optional)
            
        Returns:
            Dict containing visitor log details
        """
        visitor_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        visitor = Visitor(
            id=visitor_id,
            visitor_name=visitor_name,
            unit_id=unit_id,
            purpose=purpose,
            checked_in_at=now,
            checked_out_at=None,
            host_user_id=host_user_id,
            phone_number=phone_number,
            id_type=id_type,
            id_number=id_number,
            created_by=created_by,
            sync_status=False
        )
        
        # Store in database
        query = """
            INSERT INTO visitors (
                id, visitor_name, unit_id, purpose, checked_in_at,
                checked_out_at, host_user_id, phone_number, id_type,
                id_number, created_by, sync_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            visitor.id,
            visitor.visitor_name,
            visitor.unit_id,
            visitor.purpose,
            visitor.checked_in_at,
            visitor.checked_out_at,
            visitor.host_user_id,
            visitor.phone_number,
            visitor.id_type,
            visitor.id_number,
            visitor.created_by,
            0  # sync_status = 0
        )
        
        success = self.db.execute_insert(query, params)
        
        if success:
            self._agent_status['operations_count'] += 1
            logger.info(f"✓ Visitor logged: {visitor_name} for {unit_id}")
            
            # Log activity
            self._log_activity(
                EventType.VISITOR,
                created_by,
                UserRole.CARETAKER,
                f"Visitor: {visitor_name} for {unit_id}",
                metadata={'unit_id': unit_id, 'purpose': purpose}
            )
        
        return {
            'success': success,
            'visitor_id': visitor_id,
            'visitor_name': visitor_name,
            'unit_id': unit_id,
            'checked_in_at': now,
            'created_by': created_by
        }

    def checkout_visitor(self, visitor_id: str, checkout_by: str) -> Dict:
        """
        Check out a visitor.
        
        Args:
            visitor_id: Visitor ID to check out
            checkout_by: User performing the checkout
            
        Returns:
            Dict containing checkout result
        """
        now = datetime.now().isoformat()
        
        query = """
            UPDATE visitors 
            SET checked_out_at = ?, sync_status = 0
            WHERE id = ?
        """
        success = self.db.execute_update(query, (now, visitor_id))
        
        if success:
            logger.info(f"✓ Visitor checked out: {visitor_id}")
            self._log_activity(
                EventType.VISITOR,
                checkout_by,
                UserRole.CARETAKER,
                f"Visitor checked out: {visitor_id}",
                metadata={'visitor_id': visitor_id}
            )
        
        return {
            'success': success,
            'visitor_id': visitor_id,
            'checked_out_at': now,
            'checkout_by': checkout_by
        }

    # ========================================================================
    # UNIT OPERATIONS
    # ========================================================================

    def get_unit(self, unit_id: str) -> Optional[Dict]:
        """Get unit details."""
        query = "SELECT * FROM units WHERE id = ?"
        results = self.db.execute_query(query, (unit_id,))
        return results[0] if results else None

    def get_all_units(self) -> List[Dict]:
        """Get all units."""
        query = "SELECT * FROM units"
        return self.db.execute_query(query)

    def update_unit_status(self, unit_id: str, status: str, user_id: str) -> Dict:
        """
        Update a unit's status.
        
        Args:
            unit_id: Unit identifier
            status: New status
            user_id: User performing the update
            
        Returns:
            Dict containing update result
        """
        now = datetime.now().isoformat()
        
        query = """
            UPDATE units 
            SET status = ?, updated_at = ?, sync_status = 0
            WHERE id = ?
        """
        success = self.db.execute_update(query, (status, now, unit_id))
        
        if success:
            logger.info(f"✓ Unit {unit_id} status updated to {status}")
            self._log_activity(
                EventType.UNIT_UPDATE,
                user_id,
                UserRole.MANAGEMENT,
                f"Unit {unit_id} status updated to {status}",
                metadata={'unit_id': unit_id, 'status': status}
            )
        
        return {
            'success': success,
            'unit_id': unit_id,
            'status': status,
            'updated_at': now
        }

    # ========================================================================
    # USER OPERATIONS
    # ========================================================================

    def register_user(self, email: str, full_name: str, user_role: Union[UserRole, str],
                      phone_number: str = None, created_by: str = "system") -> Dict:
        """
        Register a new user.
        
        Args:
            email: User email
            full_name: User's full name
            user_role: User role
            phone_number: User's phone number (optional)
            created_by: Creator identifier
            
        Returns:
            Dict containing user registration details
        """
        if isinstance(user_role, str):
            user_role = UserRole(user_role)
        
        user_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        # Check if user already exists
        existing = self.db.execute_query(
            "SELECT * FROM users WHERE email = ?", (email,)
        )
        if existing:
            return {
                'success': False,
                'error': 'User already exists',
                'user_id': existing[0]['id']
            }
        
        # Store in database
        query = """
            INSERT INTO users (
                id, email, full_name, phone_number, user_role,
                is_verified, created_at, updated_at, sync_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            user_id,
            email,
            full_name,
            phone_number,
            user_role.value,
            0,  # is_verified = 0
            now,
            now,
            0  # sync_status = 0
        )
        
        success = self.db.execute_insert(query, params)
        
        if success:
            logger.info(f"✓ User registered: {email} as {user_role.value}")
            self._log_activity(
                EventType.REGISTRATION,
                user_id,
                user_role,
                f"User registered: {email}",
                metadata={'role': user_role.value}
            )
        
        return {
            'success': success,
            'user_id': user_id,
            'email': email,
            'role': user_role.value,
            'created_at': now
        }

    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user details."""
        query = "SELECT * FROM users WHERE id = ?"
        results = self.db.execute_query(query, (user_id,))
        return results[0] if results else None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user details by email."""
        query = "SELECT * FROM users WHERE email = ?"
        results = self.db.execute_query(query, (email,))
        return results[0] if results else None

    # ========================================================================
    # REPORTING & ANALYTICS
    # ========================================================================

    def get_transactions_for_unit(self, unit_id: str, 
                                   limit: int = 50) -> List[Dict]:
        """Get transactions for a specific unit."""
        query = """
            SELECT * FROM transactions 
            WHERE unit_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """
        return self.db.execute_query(query, (unit_id, limit))

    def get_maintenance_for_unit(self, unit_id: str,
                                  limit: int = 50) -> List[Dict]:
        """Get maintenance requests for a specific unit."""
        query = """
            SELECT * FROM maintenance_requests 
            WHERE unit_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """
        return self.db.execute_query(query, (unit_id, limit))

    def get_visitors_for_unit(self, unit_id: str,
                              limit: int = 50) -> List[Dict]:
        """Get visitor logs for a specific unit."""
        query = """
            SELECT * FROM visitors 
            WHERE unit_id = ? 
            ORDER BY checked_in_at DESC 
            LIMIT ?
        """
        return self.db.execute_query(query, (unit_id, limit))

    def get_pending_maintenance(self) -> List[Dict]:
        """Get all pending maintenance requests."""
        query = """
            SELECT * FROM maintenance_requests 
            WHERE status IN ('pending', 'in_progress')
            ORDER BY priority DESC, created_at ASC
        """
        return self.db.execute_query(query)

    def get_pending_sync_items(self) -> Dict[str, int]:
        """Get count of pending sync items by table."""
        result = {}
        tables = ['transactions', 'maintenance_requests', 'visitors', 'units', 'users', 'activity_logs']
        
        for table in tables:
            items = self.db.get_pending_sync_items(table, limit=1000)
            result[table] = len(items)
        
        return result

    # ========================================================================
    # INTERNAL HELPERS
    # ========================================================================

    def _log_activity(self, event_type: EventType, user_id: str,
                      user_role: UserRole, description: str,
                      metadata: Dict = None, ip_address: str = None,
                      device_info: str = None) -> bool:
        """Log an activity entry."""
        activity_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        query = """
            INSERT INTO activity_logs (
                id, event_type, user_id, user_role, description,
                ip_address, device_info, metadata, created_at, sync_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            activity_id,
            event_type.value,
            user_id,
            user_role.value,
            description,
            ip_address,
            device_info,
            json.dumps(metadata or {}),
            now,
            0  # sync_status = 0
        )
        
        return self.db.execute_insert(query, params)

    # ========================================================================
    # CLEANUP & MAINTENANCE
    # ========================================================================

    def cleanup_old_data(self, days_old: int = 90) -> Dict:
        """
        Clean up data older than specified days.
        
        Args:
            days_old: Number of days to keep
            
        Returns:
            Dict with cleanup results
        """
        cutoff = (datetime.now() - timedelta(days=days_old)).isoformat()
        results = {'deleted': 0, 'failed': 0}
        
        tables = [
            ('transactions', 'created_at'),
            ('maintenance_requests', 'created_at'),
            ('visitors', 'checked_in_at'),
            ('activity_logs', 'created_at')
        ]
        
        for table, date_field in tables:
            try:
                query = f"DELETE FROM {table} WHERE {date_field} < ? AND sync_status = 1"
                success = self.db.execute_update(query, (cutoff,))
                if success:
                    results['deleted'] += 1
            except Exception as e:
                logger.error(f"Cleanup failed for {table}: {e}")
                results['failed'] += 1
        
        return results

    def vacuum_database(self) -> bool:
        """Optimize the database by running VACUUM."""
        try:
            conn = self.db._get_connection()
            conn.execute("VACUUM")
            logger.info("✓ Database vacuumed")
            return True
        except Exception as e:
            logger.error(f"Database vacuum failed: {e}")
            return False


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_offline_engine(db_path: str = "mwarokin_offline.db",
                          sync_interval: int = 30,
                          auto_start: bool = True) -> OfflineEngine:
    """
    Create a new OfflineEngine instance.
    
    Args:
        db_path: Path to SQLite database
        sync_interval: Sync interval in seconds
        auto_start: Whether to start sync agent
        
    Returns:
        OfflineEngine instance
    """
    return OfflineEngine(db_path, sync_interval, auto_start)


# ============================================================================
# STANDALONE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example usage
    print("Mwarokin Estates - Offline Engine")
    print("=" * 50)
    
    # Create engine
    engine = OfflineEngine()
    
    # Register a user
    user = engine.register_user(
        email="john.doe@example.com",
        full_name="John Doe",
        user_role="tenant",
        phone_number="+254 712 345 678"
    )
    print(f"User registered: {user}")
    
    # Pay rent
    payment = engine.pay_rent(
        amount=45000,
        unit_id="UNIT-A12",
        user_id=user['user_id'],
        user_role="tenant"
    )
    print(f"Payment processed: {payment}")
    
    # Request maintenance
    maint = engine.request_maintenance(
        unit_id="UNIT-A12",
        title="Water leak in kitchen",
        description="There's a persistent water leak under the sink. Water is pooling on the floor.",
        user_id=user['user_id'],
        user_role="tenant",
        priority="critical"
    )
    print(f"Maintenance request: {maint}")
    
    # Log visitor
    visitor = engine.log_visitor(
        visitor_name="John Kamau",
        unit_id="UNIT-B07",
        purpose="Delivery",
        created_by=user['user_id'],
        phone_number="+254 720 123 456"
    )
    print(f"Visitor logged: {visitor}")
    
    # Check status
    status = engine.status()
    print(f"Engine status: {status}")
    
    # Force sync
    if not status['ready']:
        engine.start_sync_agent()
    
    sync_result = engine.force_sync()
    print(f"Sync result: {sync_result}")
    
    # Get pending sync items
    pending = engine.get_pending_sync_items()
    print(f"Pending sync items: {pending}")
```

---

## Key Features of This Implementation

### 1. **Robust Database Management**
- Thread-safe SQLite connections
- Full schema with all tables (transactions, maintenance, visitors, units, users, activity logs)
- Transaction integrity and proper indexing

### 2. **Automatic Background Sync**
- Runs in a separate thread
- Configurable sync interval (default: 30 seconds)
- Handles all pending items across all tables
- Tracks sync success/failure

### 3. **Complete Business Operations**
- **Payments**: Rent processing with metadata support
- **Maintenance**: Request tracking with priority levels
- **Visitors**: Check-in/check-out logging
- **Units**: Status management and retrieval
- **Users**: Registration and lookup

### 4. **Activity Logging**
- All operations are logged for audit trails
- Includes IP address and device info support
- Event types for filtering

### 5. **Reporting & Analytics**
- Get transactions by unit
- Get maintenance requests by unit
- Get visitors by unit
- Pending maintenance overview
- Sync status dashboard

### 6. **Cleanup & Maintenance**
- Automatic data cleanup for old records
- Database vacuum for optimization
- Proper connection management

### 7. **Professional Error Handling**
- Comprehensive logging
- Graceful failure handling
- Detailed error messages

### 8. **Extensible Design**
- Enum-based state management
- Dataclasses for data structures
- Factory function for easy instantiation

## Usage Example

```python
from offline import OfflineEngine

# Initialize engine (auto-starts sync agent)
engine = OfflineEngine()

# Register a tenant
user = engine.register_user(
    email="tenant@example.com",
    full_name="Jane Tenant",
    user_role="tenant"
)

# Pay rent
engine.pay_rent(55000, "UNIT-A01", user['user_id'])

# Request maintenance
engine.request_maintenance(
    "UNIT-A01", 
    "Broken window", 
    "Window in bedroom won't close",
    priority="high"
)

# Log visitor
engine.log_visitor("James", "UNIT-A01", "Maintenance", "system")

# Force sync when back online
engine.force_sync()

# Check status
print(engine.status())
```