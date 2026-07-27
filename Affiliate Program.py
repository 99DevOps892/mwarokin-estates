
# AffiliatedPrograms.py
# Modern Python Code with Functional Upgrades and Agentic UI Management

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps, reduce
from itertools import chain, groupby
from operator import attrgetter, itemgetter
import json
import random
import string
from dataclasses import field
import inspect
import hashlib

# =================== Functional Core ===================
# Pure functions with no side effects - the heart of functional programming

class Status(Enum):
    PENDING = "pending"
    QUALIFIED = "qualified"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ACTIVE = "active"

@dataclass(frozen=True)
class Referral:
    """Immutable referral data structure"""
    id: str
    name: str
    joined: datetime
    property_type: str
    status: Status
    commission: float
    is_new: bool = False
    
    def qualify(self) -> 'Referral':
        """Pure function: returns new Referral with qualified status"""
        if self.status == Status.QUALIFIED:
            return self
        commission = random.randint(150, 450)
        return Referral(
            id=self.id,
            name=self.name,
            joined=self.joined,
            property_type=self.property_type,
            status=Status.QUALIFIED,
            commission=commission,
            is_new=True
        )
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'joined': self.joined.isoformat(),
            'property_type': self.property_type,
            'status': self.status.value,
            'commission': self.commission,
            'is_new': self.is_new
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Referral':
        return cls(
            id=data['id'],
            name=data['name'],
            joined=datetime.fromisoformat(data['joined']),
            property_type=data['property_type'],
            status=Status(data['status']),
            commission=data['commission'],
            is_new=data.get('is_new', False)
        )

@dataclass(frozen=True)
class Payout:
    """Immutable payout data structure"""
    id: str
    date: datetime
    method: str
    reference: str
    amount: float
    status: Status
    
    def complete(self) -> 'Payout':
        """Pure function: returns new Payout with completed status"""
        if self.status == Status.COMPLETED:
            return self
        return Payout(
            id=self.id,
            date=self.date,
            method=self.method,
            reference=self.reference,
            amount=self.amount,
            status=Status.COMPLETED
        )
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'method': self.method,
            'reference': self.reference,
            'amount': self.amount,
            'status': self.status.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Payout':
        return cls(
            id=data['id'],
            date=datetime.fromisoformat(data['date']),
            method=data['method'],
            reference=data['reference'],
            amount=data['amount'],
            status=Status(data['status'])
        )

@dataclass(frozen=True)
class FeedItem:
    """Immutable feed data"""
    text: str
    amount: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            'text': self.text,
            'amount': self.amount,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FeedItem':
        return cls(
            text=data['text'],
            amount=data.get('amount'),
            timestamp=datetime.fromisoformat(data['timestamp'])
        )

@dataclass(frozen=True)
class AffiliateState:
    """Immutable application state"""
    balance: float
    referrals: List[Referral]
    payouts: List[Payout]
    feed: List[FeedItem]
    threshold: float = 5000.0
    max_withdrawal: float = 50000.0
    
    def update_balance(self, amount: float) -> 'AffiliateState':
        """Pure function: returns new state with updated balance"""
        return AffiliateState(
            balance=self.balance + amount,
            referrals=self.referrals,
            payouts=self.payouts,
            feed=self.feed,
            threshold=self.threshold,
            max_withdrawal=self.max_withdrawal
        )
    
    def add_referral(self, referral: Referral) -> 'AffiliateState':
        """Pure function: returns new state with added referral"""
        return AffiliateState(
            balance=self.balance,
            referrals=[referral] + self.referrals,
            payouts=self.payouts,
            feed=self.feed,
            threshold=self.threshold,
            max_withdrawal=self.max_withdrawal
        )
    
    def add_payout(self, payout: Payout) -> 'AffiliateState':
        """Pure function: returns new state with added payout"""
        return AffiliateState(
            balance=self.balance - payout.amount,
            referrals=self.referrals,
            payouts=[payout] + self.payouts,
            feed=self.feed,
            threshold=self.threshold,
            max_withdrawal=self.max_withdrawal
        )
    
    def add_feed_item(self, item: FeedItem) -> 'AffiliateState':
        """Pure function: returns new state with added feed item"""
        feed = [item] + self.feed[:19]  # Keep last 20 items
        return AffiliateState(
            balance=self.balance,
            referrals=self.referrals,
            payouts=self.payouts,
            feed=feed,
            threshold=self.threshold,
            max_withdrawal=self.max_withdrawal
        )
    
    def qualify_pending_referral(self, referral_id: str) -> tuple['AffiliateState', Optional[Referral]]:
        """Pure function: qualifies a pending referral and returns (new_state, qualified_referral)"""
        for i, ref in enumerate(self.referrals):
            if ref.id == referral_id and ref.status == Status.PENDING:
                qualified_ref = ref.qualify()
                new_referrals = self.referrals.copy()
                new_referrals[i] = qualified_ref
                new_state = AffiliateState(
                    balance=self.balance + qualified_ref.commission,
                    referrals=new_referrals,
                    payouts=self.payouts,
                    feed=self.feed,
                    threshold=self.threshold,
                    max_withdrawal=self.max_withdrawal
                )
                return new_state, qualified_ref
        return self, None
    
    def to_dict(self) -> Dict:
        return {
            'balance': self.balance,
            'referrals': [r.to_dict() for r in self.referrals],
            'payouts': [p.to_dict() for p in self.payouts],
            'feed': [f.to_dict() for f in self.feed],
            'threshold': self.threshold,
            'max_withdrawal': self.max_withdrawal
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AffiliateState':
        return cls(
            balance=data['balance'],
            referrals=[Referral.from_dict(r) for r in data['referrals']],
            payouts=[Payout.from_dict(p) for p in data['payouts']],
            feed=[FeedItem.from_dict(f) for f in data['feed']],
            threshold=data.get('threshold', 5000.0),
            max_withdrawal=data.get('max_withdrawal', 50000.0)
        )

# =================== State Management with Functional Patterns ===================

class AffiliateProgram:
    """Functional state management with immutable updates and pure transformations"""
    
    def __init__(self, storage: Optional[Callable[[], Dict]] = None):
        self._storage = storage or self._default_storage
        self._state = self._load_state()
    
    def _default_storage(self) -> Dict:
        """Default storage using in-memory dict"""
        return {}
    
    def _load_state(self) -> AffiliateState:
        """Load state from storage, creating default if needed"""
        data = self._storage()
        if data:
            try:
                return AffiliateState.from_dict(data)
            except Exception:
                pass
        return self._create_default_state()
    
    def _create_default_state(self) -> AffiliateState:
        """Create default state with sample data"""
        now = datetime.now()
        referrals = []
        for i in range(12):
            qualified = i < 7
            status = Status.QUALIFIED if qualified else Status.PENDING
            referrals.append(Referral(
                id=f"r{i}",
                name=f"{self._random_name()}",
                joined=now - timedelta(days=random.randint(1, 45)),
                property_type=self._random_property_type(),
                status=status,
                commission=random.randint(150, 450) if qualified else 0
            ))
        
        payouts = [
            Payout(
                id="p1",
                date=now - timedelta(days=30),
                method="M-Pesa",
                reference="MWK-PX88214",
                amount=6200,
                status=Status.COMPLETED
            ),
            Payout(
                id="p2",
                date=now - timedelta(days=58),
                method="Bank transfer",
                reference="MWK-BT77035",
                amount=9500,
                status=Status.COMPLETED
            ),
            Payout(
                id="p3",
                date=now - timedelta(days=90),
                method="M-Pesa",
                reference="MWK-PX65120",
                amount=5000,
                status=Status.COMPLETED
            ),
            Payout(
                id="p4",
                date=now - timedelta(days=4),
                method="M-Pesa",
                reference="MWK-PX90944",
                amount=5800,
                status=Status.PROCESSING
            )
        ]
        
        return AffiliateState(
            balance=1140.0,
            referrals=referrals,
            payouts=payouts,
            feed=[],
            threshold=5000.0,
            max_withdrawal=50000.0
        )
    
    def _random_name(self) -> str:
        first_names = ["Wanjiru", "Otieno", "Achieng", "Kiptoo", "Mwangi", "Njeri", "Kamau", "Adhiambo", "Kilonzo", "Nyambura", "Cheruiyot", "Wafula", "Amina", "Juma", "Naliaka"]
        last_names = ["M.", "K.", "O.", "W.", "N.", "A."]
        return f"{random.choice(first_names)} {random.choice(last_names)}"
    
    def _random_property_type(self) -> str:
        types = ["2BR Apartment", "Studio Unit", "3BR Townhouse", "Commercial Lot", "1BR Apartment", "Gated Villa"]
        return random.choice(types)
    
    def get_state(self) -> AffiliateState:
        """Pure getter - returns immutable state"""
        return self._state
    
    def save_state(self) -> None:
        """Save current state to storage"""
        self._storage(self._state.to_dict())
    
    # ============ Pure State Transformations ============
    
    def create_referral(self, name: str, property_type: str) -> tuple[AffiliateState, Referral]:
        """Pure transformation: create new referral and return (new_state, referral)"""
        referral = Referral(
            id=f"r{int(datetime.now().timestamp())}",
            name=name,
            joined=datetime.now(),
            property_type=property_type,
            status=Status.PENDING,
            commission=0,
            is_new=True
        )
        new_state = self._state.add_referral(referral)
        feed_item = FeedItem(text=f"<b>{name}</b> signed up using your link")
        return new_state.add_feed_item(feed_item), referral
    
    def qualify_referral(self, referral_id: str) -> tuple[AffiliateState, Optional[Referral]]:
        """Pure transformation: qualify a pending referral"""
        new_state, qualified_ref = self._state.qualify_pending_referral(referral_id)
        if qualified_ref:
            feed_item = FeedItem(
                text=f"<b>{qualified_ref.name}</b> qualified — commission credited",
                amount=qualified_ref.commission
            )
            return new_state.add_feed_item(feed_item), qualified_ref
        return self._state, None
    
    def request_payout(self, amount: float, method: str) -> tuple[AffiliateState, Optional[Payout]]:
        """Pure transformation: request a payout"""
        if amount <= 0 or amount > self._state.balance or amount > self._state.max_withdrawal:
            return self._state, None
        
        if self._state.balance < self._state.threshold:
            return self._state, None
        
        payout = Payout(
            id=f"p{int(datetime.now().timestamp())}",
            date=datetime.now(),
            method=method,
            reference=f"MWK-{method[:2].upper()}{random.randint(10000, 99999)}",
            amount=amount,
            status=Status.PROCESSING
        )
        new_state = self._state.add_payout(payout)
        feed_item = FeedItem(
            text=f"Withdrawal of <b>KSh {payout.amount:,.0f}</b> requested via {method}",
            amount=-amount
        )
        return new_state.add_feed_item(feed_item), payout
    
    def complete_payout(self, payout_id: str) -> tuple[AffiliateState, Optional[Payout]]:
        """Pure transformation: complete a processing payout"""
        for i, p in enumerate(self._state.payouts):
            if p.id == payout_id and p.status == Status.PROCESSING:
                completed = p.complete()
                new_payouts = self._state.payouts.copy()
                new_payouts[i] = completed
                new_state = AffiliateState(
                    balance=self._state.balance,
                    referrals=self._state.referrals,
                    payouts=new_payouts,
                    feed=self._state.feed,
                    threshold=self._state.threshold,
                    max_withdrawal=self._state.max_withdrawal
                )
                return new_state, completed
        return self._state, None
    
    def generate_referral_link(self, user_id: str = "RBM-7284") -> str:
        """Pure function: generate referral link"""
        return f"https://home.mwarokinestates.co.ke/join?ref={user_id}"
    
    def simulate_live_event(self) -> AffiliateState:
        """Pure transformation: simulate a live event"""
        roll = random.random()
        
        if roll < 0.55:
            # New referral signs up
            name = self._random_name()
            new_state, _ = self.create_referral(name, self._random_property_type())
            return new_state
        
        elif roll < 0.85:
            # Qualify a pending referral
            pending = [r for r in self._state.referrals if r.status == Status.PENDING]
            if pending:
                referral = random.choice(pending)
                new_state, _ = self.qualify_referral(referral.id)
                return new_state
            else:
                # No pending referrals, add bonus
                bonus = random.randint(80, 200)
                new_state = self._state.update_balance(bonus)
                feed_item = FeedItem(text="Referral bonus credited to your balance", amount=bonus)
                return new_state.add_feed_item(feed_item)
        
        else:
            # Loyalty top-up
            bonus = random.randint(50, 120)
            new_state = self._state.update_balance(bonus)
            feed_item = FeedItem(text="Loyalty top-up credited to your balance", amount=bonus)
            return new_state.add_feed_item(feed_item)
    
    def apply_state(self, new_state: AffiliateState) -> None:
        """Apply a new state (for functional updates)"""
        self._state = new_state
        self.save_state()

# =================== Agentic UI Management ===================

class UIAgent:
    """Agentic class that manages UI interactions and state synchronization"""
    
    def __init__(self, program: AffiliateProgram):
        self.program = program
        self._listeners: List[Callable[[AffiliateState], None]] = []
        self._broadcast_channel = None
        
        try:
            # This would use BroadcastChannel in a browser environment
            pass
        except:
            pass
    
    def subscribe(self, callback: Callable[[AffiliateState], None]) -> None:
        """Subscribe to state changes"""
        self._listeners.append(callback)
    
    def notify_listeners(self) -> None:
        """Notify all listeners of state change"""
        state = self.program.get_state()
        for listener in self._listeners:
            listener(state)
    
    def handle_copy_referral_link(self) -> str:
        """Agent action: copy referral link"""
        state = self.program.get_state()
        link = self.program.generate_referral_link()
        return link
    
    def handle_share(self, platform: str) -> str:
        """Agent action: share via platform"""
        state = self.program.get_state()
        link = self.program.generate_referral_link()
        messages = {
            'whatsapp': f"Check out Mwarokin Estates! Use my referral link: {link}",
            'sms': f"Mwarokin Estates referral: {link}",
            'email': f"Hi,\n\nI wanted to share Mwarokin Estates with you. Use my referral link to sign up: {link}",
            'x': f"Check out Mwarokin Estates! 🏠 Use my referral link: {link}"
        }
        return messages.get(platform, link)
    
    def handle_invite(self, email: str, note: str = "") -> tuple[bool, str]:
        """Agent action: send invitation"""
        if not email or '@' not in email:
            return False, "Invalid email address"
        
        state = self.program.get_state()
        return True, f"Invitation sent to {email}"
    
    def handle_withdraw(self, amount: float, method: str) -> tuple[bool, str, Optional[Payout]]:
        """Agent action: process withdrawal"""
        state = self.program.get_state()
        
        if amount <= 0:
            return False, "Enter a valid amount", None
        
        if amount > state.balance:
            return False, "Amount exceeds available balance", None
        
        if amount > state.max_withdrawal:
            return False, f"Maximum withdrawal is KSh {state.max_withdrawal:,.0f}", None
        
        if state.balance < state.threshold:
            return False, f"Minimum withdrawal is KSh {state.threshold:,.0f}", None
        
        new_state, payout = self.program.request_payout(amount, method)
        if payout:
            self.program.apply_state(new_state)
            self.notify_listeners()
            return True, "Withdrawal request submitted", payout
        
        return False, "Withdrawal failed", None
    
    def handle_simulate_event(self) -> Dict:
        """Agent action: simulate a live event"""
        new_state = self.program.simulate_live_event()
        self.program.apply_state(new_state)
        self.notify_listeners()
        return {
            'balance': new_state.balance,
            'referrals_count': len(new_state.referrals),
            'feed': [f.text for f in new_state.feed[:3]]
        }
    
    def get_ui_data(self) -> Dict:
        """Agent action: get data for UI rendering"""
        state = self.program.get_state()
        
        qualified = len([r for r in state.referrals if r.status == Status.QUALIFIED])
        pending = len([r for r in state.referrals if r.status == Status.PENDING])
        total = len(state.referrals)
        
        return {
            'balance': state.balance,
            'threshold': state.threshold,
            'max_withdrawal': state.max_withdrawal,
            'referrals': {
                'total': total,
                'qualified': qualified,
                'pending': pending,
                'conversion': f"{round((qualified/total)*100) if total else 0}%",
                'list': [r.to_dict() for r in state.referrals]
            },
            'payouts': {
                'total': len(state.payouts),
                'list': [p.to_dict() for p in state.payouts]
            },
            'feed': [f.to_dict() for f in state.feed[:8]],
            'referral_link': self.program.generate_referral_link()
        }

# =================== Functional Compositions ===================

def compose(*functions: Callable) -> Callable:
    """Functional composition helper"""
    def composed(data):
        result = data
        for fn in reversed(functions):
            result = fn(result)
        return result
    return composed

def with_state_update(update_fn: Callable) -> Callable:
    """Decorator for state update functions"""
    def decorator(agent_method: Callable):
        @wraps(agent_method)
        def wrapper(self, *args, **kwargs):
            result = agent_method(self, *args, **kwargs)
            self.notify_listeners()
            return result
        return wrapper
    return decorator

# =================== Analytics and Statistics (Pure Functions) ===================

def calculate_stats(state: AffiliateState) -> Dict:
    """Pure function: calculate analytics from state"""
    referrals = state.referrals
    payouts = state.payouts
    
    total_referrals = len(referrals)
    qualified = len([r for r in referrals if r.status == Status.QUALIFIED])
    pending = total_referrals - qualified
    
    total_commission = sum(r.commission for r in referrals if r.status == Status.QUALIFIED)
    total_payout = sum(p.amount for p in payouts if p.status == Status.COMPLETED)
    
    return {
        'total_referrals': total_referrals,
        'qualified': qualified,
        'pending': pending,
        'conversion_rate': (qualified / total_referrals * 100) if total_referrals else 0,
        'total_commission': total_commission,
        'total_payout': total_payout,
        'current_balance': state.balance,
        'progress_to_threshold': min(state.balance / state.threshold * 100, 100)
    }

def get_trend_data(state: AffiliateState) -> Dict:
    """Pure function: calculate trend data"""
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    
    recent_referrals = [r for r in state.referrals if r.joined > week_ago]
    recent_payouts = [p for p in state.payouts if p.date > week_ago]
    
    return {
        'new_referrals': len(recent_referrals),
        'new_payouts': len(recent_payouts),
        'status': 'live' if recent_referrals or recent_payouts else 'inactive'
    }

# =================== Main Program Setup ===================

class Program:
    """Main program with functional and agentic features"""
    
    def __init__(self, storage: Optional[Callable] = None):
        self.affiliate = AffiliateProgram(storage)
        self.agent = UIAgent(self.affiliate)
        self.agent.subscribe(self._on_state_change)
        self._running = True
    
    def _on_state_change(self, state: AffiliateState) -> None:
        """Callback for state changes"""
        stats = calculate_stats(state)
        self._debug_log(f"State updated: Balance KSh {state.balance:,.0f}, Referrals {len(state.referrals)}")
    
    def _debug_log(self, message: str) -> None:
        """Debug logging"""
        print(f"[AffiliateProgram] {message}")
    
    def run(self) -> None:
        """Main program loop"""
        print("Mwarokin Estates Affiliate Program")
        print("=" * 40)
        
        # Initial UI data
        ui_data = self.agent.get_ui_data()
        print(f"Balance: KSh {ui_data['balance']:,.0f}")
        print(f"Referrals: {ui_data['referrals']['total']}")
        print(f"Qualified: {ui_data['referrals']['qualified']}")
        print(f"Conversion: {ui_data['referrals']['conversion']}")
        print(f"Referral Link: {ui_data['referral_link']}")
        print("-" * 40)
    
    def simulate_live(self) -> None:
        """Simulate live events"""
        print("Simulating live events...")
        for _ in range(5):
            event = self.agent.handle_simulate_event()
            print(f"  Event: Balance KSh {event['balance']:,.0f}, Referrals: {event['referrals_count']}")

# =================== Example Usage ===================

if __name__ == "__main__":
    # Example storage that persists in memory
    storage_data = {}
    
    def storage(storage=storage_data):
        if callable(storage):
            storage = storage()
        return storage
    
    # Initialize program
    program = Program()
    program.run()
    
    # Demo: simulate live events
    print("\n" + "=" * 40)
    program.simulate_live()
    
    # Demo: withdrawal flow
    print("\n" + "=" * 40)
    print("Withdrawal Demo:")
    success, message, payout = program.agent.handle_withdraw(1000, "M-Pesa")
    print(f"  {message}")
    
    if success and payout:
        print(f"  Payout: {payout.reference} - KSh {payout.amount:,.0f}")
    
    # Demo: referral creation
    print("\n" + "=" * 40)
    print("Creating Referral:")
    ui_data = program.agent.get_ui_data()
    
    # Show final state
    print(f"Final Balance: KSh {ui_data['balance']:,.0f}")
    print(f"Final Referrals: {ui_data['referrals']['total']}")
    print(f"Pending Referrals: {ui_data['referrals']['pending']}")
