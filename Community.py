
"""
Community Suggestions Module - Functional Python Implementation
A modern, functional approach to managing community suggestions with real-time updates,
voting, comments, and progress tracking.

This module demonstrates:
- Pure functional programming patterns
- Immutable data structures
- Type hints and validation
- Functional reactive programming concepts
- Modern Python features (dataclasses, pattern matching, etc.)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Callable, Any, Union, Tuple
from enum import Enum
from functools import reduce, partial
from collections.abc import Sequence
import json
import uuid
from operator import attrgetter, itemgetter

# ============================================================================
# Domain Models - Immutable Data Structures
# ============================================================================

class Status(Enum):
    """Suggestion status lifecycle"""
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    IMPLEMENTED = "implemented"
    REJECTED = "rejected"

    @property
    def display(self) -> str:
        return self.value.replace("_", " ").title()

    @property
    def progress(self) -> int:
        """Progress percentage for each status"""
        return {
            Status.SUBMITTED: 0,
            Status.UNDER_REVIEW: 25,
            Status.IN_PROGRESS: 50,
            Status.APPROVED: 75,
            Status.IMPLEMENTED: 100,
            Status.REJECTED: 0,
        }[self]


class Category(Enum):
    """Suggestion categories"""
    AMENITY = "amenity"
    SECURITY = "security"
    COMMUNITY = "community"
    MAINTENANCE = "maintenance"
    INFRASTRUCTURE = "infrastructure"
    OTHER = "other"

    @property
    def display(self) -> str:
        return self.value.title()

    @property
    def color(self) -> str:
        return {
            Category.AMENITY: "#c9a227",
            Category.SECURITY: "#e74c3c",
            Category.COMMUNITY: "#2ecc71",
            Category.MAINTENANCE: "#f39c12",
            Category.INFRASTRUCTURE: "#3498db",
            Category.OTHER: "#95a5a6",
        }[self]


@dataclass(frozen=True)
class Reaction:
    """Immutable reaction to a comment"""
    type: str
    count: int = 0
    users: Set[str] = field(default_factory=set)

    def add_user(self, user_id: str) -> 'Reaction':
        if user_id in self.users:
            return self
        return Reaction(
            type=self.type,
            count=self.count + 1,
            users=self.users | {user_id}
        )

    def remove_user(self, user_id: str) -> 'Reaction':
        if user_id not in self.users:
            return self
        return Reaction(
            type=self.type,
            count=self.count - 1,
            users=self.users - {user_id}
        )


@dataclass(frozen=True)
class Comment:
    """Immutable comment on a suggestion"""
    id: str
    author_id: str
    author_name: str
    author_role: str
    text: str
    created_at: datetime
    reactions: Dict[str, Reaction] = field(default_factory=dict)
    reply_to: Optional[str] = None

    def with_reaction(self, reaction_type: str, user_id: str) -> 'Comment':
        current = self.reactions.get(reaction_type)
        if current:
            new_reaction = current.add_user(user_id)
        else:
            new_reaction = Reaction(type=reaction_type, count=1, users={user_id})
        return Comment(
            id=self.id,
            author_id=self.author_id,
            author_name=self.author_name,
            author_role=self.author_role,
            text=self.text,
            created_at=self.created_at,
            reactions={**self.reactions, reaction_type: new_reaction},
            reply_to=self.reply_to
        )

    def without_reaction(self, reaction_type: str, user_id: str) -> 'Comment':
        current = self.reactions.get(reaction_type)
        if not current:
            return self
        new_reaction = current.remove_user(user_id)
        if new_reaction.count == 0:
            reactions = {k: v for k, v in self.reactions.items() if k != reaction_type}
        else:
            reactions = {**self.reactions, reaction_type: new_reaction}
        return Comment(
            id=self.id,
            author_id=self.author_id,
            author_name=self.author_name,
            author_role=self.author_role,
            text=self.text,
            created_at=self.created_at,
            reactions=reactions,
            reply_to=self.reply_to
        )


@dataclass(frozen=True)
class Suggestion:
    """Immutable community suggestion"""
    id: str
    title: str
    description: str
    category: Category
    status: Status
    author_id: str
    author_name: str
    property: Optional[str]
    created_at: datetime
    updated_at: datetime
    upvotes: Set[str] = field(default_factory=set)
    downvotes: Set[str] = field(default_factory=set)
    comments: List[Comment] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    @property
    def vote_count(self) -> int:
        return len(self.upvotes) - len(self.downvotes)

    @property
    def upvote_count(self) -> int:
        return len(self.upvotes)

    @property
    def downvote_count(self) -> int:
        return len(self.downvotes)

    @property
    def comment_count(self) -> int:
        return len(self.comments)

    @property
    def total_votes(self) -> int:
        return len(self.upvotes) + len(self.downvotes)

    def with_upvote(self, user_id: str) -> 'Suggestion':
        if user_id in self.upvotes:
            return self
        new_upvotes = self.upvotes | {user_id}
        new_downvotes = self.downvotes - {user_id}
        return Suggestion(
            id=self.id,
            title=self.title,
            description=self.description,
            category=self.category,
            status=self.status,
            author_id=self.author_id,
            author_name=self.author_name,
            property=self.property,
            created_at=self.created_at,
            updated_at=datetime.now(),
            upvotes=new_upvotes,
            downvotes=new_downvotes,
            comments=self.comments,
            tags=self.tags
        )

    def with_downvote(self, user_id: str) -> 'Suggestion':
        if user_id in self.downvotes:
            return self
        new_downvotes = self.downvotes | {user_id}
        new_upvotes = self.upvotes - {user_id}
        return Suggestion(
            id=self.id,
            title=self.title,
            description=self.description,
            category=self.category,
            status=self.status,
            author_id=self.author_id,
            author_name=self.author_name,
            property=self.property,
            created_at=self.created_at,
            updated_at=datetime.now(),
            upvotes=new_upvotes,
            downvotes=new_downvotes,
            comments=self.comments,
            tags=self.tags
        )

    def with_comment(self, comment: Comment) -> 'Suggestion':
        return Suggestion(
            id=self.id,
            title=self.title,
            description=self.description,
            category=self.category,
            status=self.status,
            author_id=self.author_id,
            author_name=self.author_name,
            property=self.property,
            created_at=self.created_at,
            updated_at=datetime.now(),
            upvotes=self.upvotes,
            downvotes=self.downvotes,
            comments=self.comments + [comment],
            tags=self.tags
        )

    def with_status(self, new_status: Status) -> 'Suggestion':
        return Suggestion(
            id=self.id,
            title=self.title,
            description=self.description,
            category=self.category,
            status=new_status,
            author_id=self.author_id,
            author_name=self.author_name,
            property=self.property,
            created_at=self.created_at,
            updated_at=datetime.now(),
            upvotes=self.upvotes,
            downvotes=self.downvotes,
            comments=self.comments,
            tags=self.tags
        )

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category.value,
            'category_display': self.category.display,
            'status': self.status.value,
            'status_display': self.status.display,
            'status_progress': self.status.progress,
            'author_id': self.author_id,
            'author_name': self.author_name,
            'property': self.property,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'upvotes': len(self.upvotes),
            'downvotes': len(self.downvotes),
            'vote_count': self.vote_count,
            'comment_count': self.comment_count,
            'total_votes': self.total_votes,
            'tags': self.tags
        }


# ============================================================================
# Functional Core - Pure Functions
# ============================================================================

def create_suggestion(
    title: str,
    description: str,
    category: Category,
    author_id: str,
    author_name: str,
    property: Optional[str] = None,
    tags: List[str] = None
) -> Suggestion:
    """Create a new suggestion with validation"""
    if not title or len(title.strip()) < 3:
        raise ValueError("Title must be at least 3 characters")
    if not description or len(description.strip()) < 10:
        raise ValueError("Description must be at least 10 characters")
    
    return Suggestion(
        id=str(uuid.uuid4()),
        title=title.strip(),
        description=description.strip(),
        category=category,
        status=Status.SUBMITTED,
        author_id=author_id,
        author_name=author_name,
        property=property,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        tags=tags or []
    )


def filter_suggestions(
    suggestions: Sequence[Suggestion],
    *,
    category: Optional[Category] = None,
    status: Optional[Status] = None,
    author_id: Optional[str] = None,
    search: Optional[str] = None,
    min_votes: Optional[int] = None,
    property: Optional[str] = None
) -> List[Suggestion]:
    """Filter suggestions by various criteria - pure function"""
    result = list(suggestions)
    
    if category:
        result = [s for s in result if s.category == category]
    if status:
        result = [s for s in result if s.status == status]
    if author_id:
        result = [s for s in result if s.author_id == author_id]
    if property:
        result = [s for s in result if s.property == property]
    if min_votes is not None:
        result = [s for s in result if s.vote_count >= min_votes]
    if search:
        search_lower = search.lower()
        result = [
            s for s in result
            if search_lower in s.title.lower()
            or search_lower in s.description.lower()
        ]
    
    return result


def sort_suggestions(
    suggestions: Sequence[Suggestion],
    by: str = 'vote_count',
    reverse: bool = True
) -> List[Suggestion]:
    """Sort suggestions by various criteria - pure function"""
    sort_map = {
        'vote_count': attrgetter('vote_count'),
        'created_at': attrgetter('created_at'),
        'updated_at': attrgetter('updated_at'),
        'comment_count': attrgetter('comment_count'),
        'title': attrgetter('title'),
        'status': lambda s: s.status.value,
    }
    
    key = sort_map.get(by, sort_map['vote_count'])
    return sorted(suggestions, key=key, reverse=reverse)


def aggregate_suggestions(
    suggestions: Sequence[Suggestion]
) -> Dict:
    """Aggregate statistics about suggestions - pure function"""
    total = len(suggestions)
    if total == 0:
        return {
            'total': 0,
            'by_status': {},
            'by_category': {},
            'total_votes': 0,
            'implemented': 0,
            'satisfaction': 0
        }
    
    by_status = reduce(
        lambda acc, s: {**acc, s.status: acc.get(s.status, 0) + 1},
        suggestions,
        {}
    )
    
    by_category = reduce(
        lambda acc, s: {**acc, s.category: acc.get(s.category, 0) + 1},
        suggestions,
        {}
    )
    
    total_votes = sum(s.total_votes for s in suggestions)
    implemented = sum(1 for s in suggestions if s.status == Status.IMPLEMENTED)
    
    return {
        'total': total,
        'by_status': {k.value: v for k, v in by_status.items()},
        'by_category': {k.value: v for k, v in by_category.items()},
        'total_votes': total_votes,
        'implemented': implemented,
        'satisfaction': round((implemented / total * 100) if total > 0 else 0, 1)
    }


def comment_reaction_state(
    comment: Comment,
    user_id: str
) -> Dict[str, bool]:
    """Get reaction state for a comment - pure function"""
    return {
        reaction_type: user_id in reaction.users
        for reaction_type, reaction in comment.reactions.items()
    }


# ============================================================================
# Functional Reactive Store
# ============================================================================

class CommunityStore:
    """
    Functional reactive store for community suggestions.
    Uses immutable updates with event streaming.
    """
    
    def __init__(self):
        self._suggestions: Dict[str, Suggestion] = {}
        self._observers: List[Callable] = []
        self._events: List[Dict] = []
    
    # ===== Query Operations (Pure Reads) =====
    
    def get_suggestion(self, suggestion_id: str) -> Optional[Suggestion]:
        return self._suggestions.get(suggestion_id)
    
    def get_all_suggestions(self) -> List[Suggestion]:
        return list(self._suggestions.values())
    
    def get_suggestions_by_status(self, status: Status) -> List[Suggestion]:
        return [s for s in self._suggestions.values() if s.status == status]
    
    def get_trending(self, limit: int = 10) -> List[Suggestion]:
        """Get trending suggestions sorted by vote count and recency"""
        sorted_by_votes = sort_suggestions(
            self._suggestions.values(),
            by='vote_count'
        )[:limit]
        
        # Re-sort by recency for trending mix
        return sorted(sorted_by_votes, key=attrgetter('created_at'), reverse=True)
    
    # ===== Command Operations (Immutable Updates) =====
    
    def add_suggestion(self, suggestion: Suggestion) -> 'CommunityStore':
        new_store = CommunityStore()
        new_store._suggestions = {**self._suggestions, suggestion.id: suggestion}
        new_store._observers = self._observers
        new_store._events = self._events + [{
            'type': 'suggestion_created',
            'data': suggestion.to_dict(),
            'timestamp': datetime.now()
        }]
        new_store._notify_observers('suggestion_created', suggestion)
        return new_store
    
    def vote_suggestion(
        self,
        suggestion_id: str,
        user_id: str,
        vote_type: str
    ) -> 'CommunityStore':
        suggestion = self.get_suggestion(suggestion_id)
        if not suggestion:
            raise ValueError(f"Suggestion {suggestion_id} not found")
        
        if vote_type == 'up':
            updated = suggestion.with_upvote(user_id)
        elif vote_type == 'down':
            updated = suggestion.with_downvote(user_id)
        else:
            raise ValueError(f"Invalid vote_type: {vote_type}")
        
        new_store = CommunityStore()
        new_store._suggestions = {**self._suggestions, suggestion_id: updated}
        new_store._observers = self._observers
        new_store._events = self._events + [{
            'type': 'vote_cast',
            'suggestion_id': suggestion_id,
            'user_id': user_id,
            'vote_type': vote_type,
            'timestamp': datetime.now()
        }]
        new_store._notify_observers('vote_cast', updated)
        return new_store
    
    def add_comment(
        self,
        suggestion_id: str,
        comment: Comment
    ) -> 'CommunityStore':
        suggestion = self.get_suggestion(suggestion_id)
        if not suggestion:
            raise ValueError(f"Suggestion {suggestion_id} not found")
        
        updated = suggestion.with_comment(comment)
        new_store = CommunityStore()
        new_store._suggestions = {**self._suggestions, suggestion_id: updated}
        new_store._observers = self._observers
        new_store._events = self._events + [{
            'type': 'comment_added',
            'suggestion_id': suggestion_id,
            'comment_id': comment.id,
            'timestamp': datetime.now()
        }]
        new_store._notify_observers('comment_added', updated)
        return new_store
    
    def update_status(
        self,
        suggestion_id: str,
        new_status: Status
    ) -> 'CommunityStore':
        suggestion = self.get_suggestion(suggestion_id)
        if not suggestion:
            raise ValueError(f"Suggestion {suggestion_id} not found")
        
        if suggestion.status == new_status:
            return self
        
        updated = suggestion.with_status(new_status)
        new_store = CommunityStore()
        new_store._suggestions = {**self._suggestions, suggestion_id: updated}
        new_store._observers = self._observers
        new_store._events = self._events + [{
            'type': 'status_updated',
            'suggestion_id': suggestion_id,
            'new_status': new_status.value,
            'timestamp': datetime.now()
        }]
        new_store._notify_observers('status_updated', updated)
        return new_store
    
    def react_to_comment(
        self,
        suggestion_id: str,
        comment_id: str,
        user_id: str,
        reaction_type: str,
        add: bool = True
    ) -> 'CommunityStore':
        suggestion = self.get_suggestion(suggestion_id)
        if not suggestion:
            raise ValueError(f"Suggestion {suggestion_id} not found")
        
        # Find and update comment
        updated_comments = []
        comment_found = False
        
        for comment in suggestion.comments:
            if comment.id == comment_id:
                comment_found = True
                if add:
                    updated = comment.with_reaction(reaction_type, user_id)
                else:
                    updated = comment.without_reaction(reaction_type, user_id)
                updated_comments.append(updated)
            else:
                updated_comments.append(comment)
        
        if not comment_found:
            raise ValueError(f"Comment {comment_id} not found")
        
        updated_suggestion = Suggestion(
            id=suggestion.id,
            title=suggestion.title,
            description=suggestion.description,
            category=suggestion.category,
            status=suggestion.status,
            author_id=suggestion.author_id,
            author_name=suggestion.author_name,
            property=suggestion.property,
            created_at=suggestion.created_at,
            updated_at=datetime.now(),
            upvotes=suggestion.upvotes,
            downvotes=suggestion.downvotes,
            comments=updated_comments,
            tags=suggestion.tags
        )
        
        new_store = CommunityStore()
        new_store._suggestions = {**self._suggestions, suggestion_id: updated_suggestion}
        new_store._observers = self._observers
        new_store._events = self._events + [{
            'type': 'reaction_updated',
            'suggestion_id': suggestion_id,
            'comment_id': comment_id,
            'user_id': user_id,
            'reaction_type': reaction_type,
            'add': add,
            'timestamp': datetime.now()
        }]
        new_store._notify_observers('reaction_updated', updated_suggestion)
        return new_store
    
    # ===== Observer Pattern =====
    
    def subscribe(self, observer: Callable) -> 'CommunityStore':
        new_store = CommunityStore()
        new_store._suggestions = self._suggestions
        new_store._observers = self._observers + [observer]
        new_store._events = self._events
        return new_store
    
    def _notify_observers(self, event_type: str, data: Any):
        for observer in self._observers:
            try:
                observer(event_type, data)
            except Exception as e:
                print(f"Observer error: {e}")
    
    # ===== Query Helpers =====
    
    def get_aggregates(self) -> Dict:
        return aggregate_suggestions(self.get_all_suggestions())
    
    def get_status_counts(self) -> Dict[Status, int]:
        return reduce(
            lambda acc, s: {**acc, s.status: acc.get(s.status, 0) + 1},
            self._suggestions.values(),
            {}
        )
    
    def to_json(self) -> str:
        return json.dumps({
            'suggestions': [s.to_dict() for s in self._suggestions.values()],
            'aggregates': self.get_aggregates(),
            'events': self._events[-50:]  # Last 50 events
        }, indent=2)


# ============================================================================
# UI Integration - Functional Adapters
# ============================================================================

def format_suggestion_for_ui(suggestion: Suggestion) -> Dict:
    """Format suggestion for UI display - pure function"""
    return {
        'id': suggestion.id,
        'title': suggestion.title,
        'description': suggestion.description[:150] + ('...' if len(suggestion.description) > 150 else ''),
        'category': suggestion.category.value,
        'category_label': suggestion.category.display,
        'status': suggestion.status.value,
        'status_label': suggestion.status.display,
        'progress': suggestion.status.progress,
        'author': suggestion.author_name,
        'property': suggestion.property or 'All Properties',
        'date': suggestion.created_at.strftime('%b %d, %Y'),
        'votes': suggestion.vote_count,
        'upvotes': suggestion.upvote_count,
        'downvotes': suggestion.downvote_count,
        'comments': suggestion.comment_count,
        'total_votes': suggestion.total_votes,
        'tags': suggestion.tags,
        'online_users': []  # Would come from presence system
    }


def format_comments_for_ui(
    suggestion: Suggestion,
    current_user_id: str
) -> List[Dict]:
    """Format comments for UI - pure function"""
    return [
        {
            'id': c.id,
            'author': c.author_name,
            'role': c.author_role,
            'text': c.text,
            'time': c.created_at.strftime('%b %d, %Y · %I:%M %p'),
            'reactions': {
                rt: {
                    'count': r.count,
                    'active': current_user_id in r.users
                }
                for rt, r in c.reactions.items()
            }
        }
        for c in suggestion.comments
    ]


# ============================================================================
# Example Usage & Test Data
# ============================================================================

def create_sample_suggestions() -> List[Suggestion]:
    """Create sample suggestions for demonstration - pure function"""
    now = datetime.now()
    
    return [
        create_suggestion(
            title="Install Solar Panels on Common Areas",
            description="Reduce electricity costs and promote sustainability by installing solar panels on rooftops of common buildings and parking structures. Preliminary estimates suggest a payback period of under four years.",
            category=Category.AMENITY,
            author_id="user1",
            author_name="Sarah K.",
            property="Villa A",
            tags=["sustainability", "energy"]
        ).with_upvote("user1").with_upvote("user2").with_upvote("user3"),
        
        create_suggestion(
            title="Enhance Night Lighting in Parking",
            description="Improve safety by adding more LED lights in the parking areas. Some corners are too dark during nighttime.",
            category=Category.SECURITY,
            author_id="user2",
            author_name="Michael T.",
            property="Apartment 2",
            tags=["safety", "lighting"]
        ),
        
        create_suggestion(
            title="Weekly Community Cleanup Events",
            description="Organize weekly cleanup drives where residents can volunteer to maintain our beautiful community spaces together.",
            category=Category.COMMUNITY,
            author_id="user3",
            author_name="James R.",
            property="All Properties",
            tags=["community", "volunteer"]
        ),
    ]


def run_demo():
    """Run a demonstration of the functional community system"""
    print("=" * 60)
    print("COMMUNITY SUGGESTIONS - Functional Python Demo")
    print("=" * 60)
    
    # Initialize store
    store = CommunityStore()
    
    # Add sample suggestions
    for suggestion in create_sample_suggestions():
        store = store.add_suggestion(suggestion)
        print(f"✓ Added: {suggestion.title}")
    
    print("\n" + "-" * 60)
    print("AGGREGATED STATISTICS")
    print("-" * 60)
    aggregates = store.get_aggregates()
    for key, value in aggregates.items():
        print(f"  {key}: {value}")
    
    print("\n" + "-" * 60)
    print("SUGGESTIONS BY CATEGORY")
    print("-" * 60)
    for category in Category:
        filtered = filter_suggestions(
            store.get_all_suggestions(),
            category=category
        )
        if filtered:
            print(f"\n  {category.display}:")
            for s in filtered:
                print(f"    • {s.title} ({s.vote_count} votes)")
    
    print("\n" + "-" * 60)
    print("TRENDING SUGGESTIONS")
    print("-" * 60)
    trending = store.get_trending(limit=3)
    for s in trending:
        print(f"  • {s.title} - {s.vote_count} votes")
    
    print("\n" + "-" * 60)
    print("IMMUTABILITY DEMONSTRATION")
    print("-" * 60)
    
    first_suggestion = store.get_all_suggestions()[0]
    original_votes = first_suggestion.vote_count
    print(f"Original suggestion: {first_suggestion.title}")
    print(f"  Vote count: {original_votes}")
    
    # Vote on it (creates new instance)
    store2 = store.vote_suggestion(first_suggestion.id, "new_user", "up")
    updated_suggestion = store2.get_suggestion(first_suggestion.id)
    print(f"After voting (new store): {updated_suggestion.vote_count}")
    print(f"Original store unchanged: {store.get_suggestion(first_suggestion.id).vote_count}")
    
    print("\n" + "=" * 60)
    print("Demo complete! All operations were pure and immutable.")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()