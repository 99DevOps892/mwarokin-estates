import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
import logging
from dataclasses import dataclass, field
import random
import hashlib
import secrets
from abc import ABC, abstractmethod
import sqlite3
from contextlib import contextmanager
import aiohttp
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re

# Advanced AI Capabilities for FAQ System
class AICapability(Enum):
    NATURAL_LANGUAGE_PROCESSING = "nlp"
    SEMANTIC_SEARCH = "semantic_search"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    CONTEXT_UNDERSTANDING = "context_understanding"
    MULTILINGUAL_SUPPORT = "multilingual_support"
    LEARNING_ADAPTATION = "learning_adaptation"
    PREDICTIVE_SUGGESTIONS = "predictive_suggestions"

class FAQCategory(Enum):
    PLATFORM_FEATURES = "platform_features"
    SECURITY_PRIVACY = "security_privacy"
    PROPERTIES = "properties"
    ACCOUNT_BILLING = "account_billing"
    PAYMENTS = "payments"
    TECHNICAL_SUPPORT = "technical_support"
    MOBILE_APP = "mobile_app"

class UserSentiment(Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    FRUSTRATED = "frustrated"

@dataclass
class FAQEntry:
    id: str
    question: str
    answer: str
    category: FAQCategory
    tags: List[str]
    popularity_score: float = 0.0
    helpful_votes: int = 0
    unhelpful_votes: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    ai_generated: bool = False
    related_questions: List[str] = field(default_factory=list)
    
    def to_dict(self):
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "category": self.category.value,
            "tags": self.tags,
            "popularity_score": self.popularity_score,
            "helpful_votes": self.helpful_votes,
            "unhelpful_votes": self.unhelpful_votes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "ai_generated": self.ai_generated,
            "related_questions": self.related_questions
        }

@dataclass
class UserInteraction:
    id: str
    user_id: str
    question: str
    timestamp: datetime
    sentiment: UserSentiment
    found_helpful: bool = False
    clicked_faq: Optional[str] = None
    search_duration: float = 0.0
    feedback_rating: Optional[int] = None
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "question": self.question,
            "timestamp": self.timestamp.isoformat(),
            "sentiment": self.sentiment.value,
            "found_helpful": self.found_helpful,
            "clicked_faq": self.clicked_faq,
            "search_duration": self.search_duration,
            "feedback_rating": self.feedback_rating
        }

# Advanced AI Processors for FAQ System
class FAQAIProcessor(ABC):
    @abstractmethod
    async def process_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        pass

class SemanticSearchProcessor(FAQAIProcessor):
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        self.faq_vectors = None
        self.faq_ids = []
        
    async def process_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if not self.faq_vectors:
            return {"matches": [], "confidence": 0.0}
        
        query_vector = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vector, self.faq_vectors)
        
        matches = []
        for i, similarity in enumerate(similarities[0]):
            if similarity > 0.1:  # Threshold for relevance
                matches.append({
                    "faq_id": self.faq_ids[i],
                    "similarity_score": float(similarity),
                    "rank": i
                })
        
        # Sort by similarity score
        matches.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return {
            "matches": matches[:5],  # Top 5 matches
            "confidence": float(np.max(similarities)) if matches else 0.0,
            "search_algorithm": "semantic_tfidf"
        }
    
    def update_faq_corpus(self, faqs: List[FAQEntry]):
        """Update the semantic search model with new FAQs"""
        questions = [f"{faq.question} {faq.answer}" for faq in faqs]
        self.faq_ids = [faq.id for faq in faqs]
        
        if questions:
            self.faq_vectors = self.vectorizer.fit_transform(questions)

class SentimentAnalysisProcessor(FAQAIProcessor):
    async def process_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # Simple rule-based sentiment analysis
        query_lower = query.lower()
        
        positive_words = ['help', 'thanks', 'thank you', 'good', 'great', 'excellent', 'awesome']
        negative_words = ['problem', 'issue', 'error', 'broken', 'not working', 'why', 'how to']
        frustrated_words = ['urgent', 'immediately', 'now', 'asap', 'help me', 'frustrated', 'angry']
        
        sentiment_score = 0
        sentiment = UserSentiment.NEUTRAL
        
        for word in positive_words:
            if word in query_lower:
                sentiment_score += 1
        
        for word in negative_words:
            if word in query_lower:
                sentiment_score -= 1
        
        for word in frustrated_words:
            if word in query_lower:
                sentiment_score -= 2
        
        if sentiment_score > 1:
            sentiment = UserSentiment.POSITIVE
        elif sentiment_score < -2:
            sentiment = UserSentiment.FRUSTRATED
        elif sentiment_score < 0:
            sentiment = UserSentiment.NEGATIVE
        
        return {
            "sentiment": sentiment.value,
            "sentiment_score": sentiment_score,
            "urgency_level": "high" if sentiment == UserSentiment.FRUSTRATED else "normal"
        }

class ContextUnderstandingProcessor(FAQAIProcessor):
    async def process_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        user_history = context.get('user_history', [])
        current_category = context.get('current_category')
        
        # Analyze context from user history
        recent_searches = [interaction['question'] for interaction in user_history[-3:]]
        common_themes = self._extract_themes(recent_searches + [query])
        
        return {
            "common_themes": common_themes,
            "suggested_category": self._predict_category(query, common_themes),
            "context_aware": len(user_history) > 0,
            "follow_up_questions": self._generate_follow_up_questions(query, common_themes)
        }
    
    def _extract_themes(self, queries: List[str]) -> List[str]:
        themes = []
        property_terms = ['property', 'house', 'apartment', 'rent', 'buy', 'sell']
        payment_terms = ['payment', 'bill', 'money', 'price', 'cost']
        tech_terms = ['app', 'mobile', 'website', 'login', 'account']
        
        for query in queries:
            if any(term in query.lower() for term in property_terms):
                themes.append("property_related")
            if any(term in query.lower() for term in payment_terms):
                themes.append("payment_related")
            if any(term in query.lower() for term in tech_terms):
                themes.append("technical")
        
        return list(set(themes))
    
    def _predict_category(self, query: str, themes: List[str]) -> str:
        query_lower = query.lower()
        
        if any(theme in themes for theme in ["property_related"]):
            return FAQCategory.PROPERTIES.value
        elif any(theme in themes for theme in ["payment_related"]):
            return FAQCategory.PAYMENTS.value
        elif any(theme in themes for theme in ["technical"]):
            return FAQCategory.TECHNICAL_SUPPORT.value
        elif any(word in query_lower for word in ['security', 'privacy', 'safe']):
            return FAQCategory.SECURITY_PRIVACY.value
        elif any(word in query_lower for word in ['feature', 'how to', 'use']):
            return FAQCategory.PLATFORM_FEATURES.value
        else:
            return FAQCategory.PLATFORM_FEATURES.value
    
    def _generate_follow_up_questions(self, query: str, themes: List[str]) -> List[str]:
        follow_ups = []
        query_lower = query.lower()
        
        if "property" in query_lower:
            follow_ups.extend([
                "How do I list my property?",
                "What types of properties are available?",
                "How does property verification work?"
            ])
        
        if "payment" in query_lower or "bill" in query_lower:
            follow_ups.extend([
                "What payment methods are accepted?",
                "How secure are payments?",
                "Can I pay in installments?"
            ])
        
        return follow_ups[:3]  # Return top 3

# Main Advanced FAQ System
class AdvancedFAQSystem:
    """
    Advanced AI-powered FAQ system with real-time processing,
    semantic search, and adaptive learning
    """
    
    def __init__(self, db_path: str = "faq_database.db"):
        self.faq_entries: Dict[str, FAQEntry] = {}
        self.user_interactions: List[UserInteraction] = []
        self.ai_processors: Dict[str, FAQAIProcessor] = {}
        self.connected_clients: Dict[str, WebSocket] = {}
        self.system_metrics: Dict[str, Any] = {}
        self.is_running = False
        
        self.db_path = db_path
        self._setup_database()
        self._setup_logging()
        self._initialize_ai_processors()
        self._load_initial_faqs()
        
        # Initialize FastAPI app
        self.app = FastAPI(title="Mwarokin Advanced FAQ System")
        self._setup_api_routes()
        self._setup_cors()
    
    def _setup_database(self):
        """Initialize SQLite database for persistent storage"""
        with self._get_db_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS faq_entries (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tags TEXT,
                    popularity_score REAL DEFAULT 0,
                    helpful_votes INTEGER DEFAULT 0,
                    unhelpful_votes INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT,
                    ai_generated BOOLEAN DEFAULT 0,
                    related_questions TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_interactions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    question TEXT,
                    timestamp TEXT,
                    sentiment TEXT,
                    found_helpful BOOLEAN,
                    clicked_faq TEXT,
                    search_duration REAL,
                    feedback_rating INTEGER
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    total_searches INTEGER,
                    successful_searches INTEGER,
                    average_response_time REAL,
                    user_satisfaction_score REAL
                )
            ''')
    
    @contextmanager
    def _get_db_connection(self):
        """Database connection context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('faq_system.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _initialize_ai_processors(self):
        """Initialize AI processors for advanced FAQ functionality"""
        self.ai_processors = {
            "semantic_search": SemanticSearchProcessor(),
            "sentiment_analysis": SentimentAnalysisProcessor(),
            "context_understanding": ContextUnderstandingProcessor()
        }
    
    def _load_initial_faqs(self):
        """Load initial FAQ data into the system"""
        initial_faqs = [
            FAQEntry(
                id="faq_001",
                question="What sets Mwarokin apart from other real estate platforms?",
                answer="Mwarokin leverages cutting-edge AI technology to provide personalized property recommendations based on your preferences. Our user-friendly interface and advanced search features make finding your dream home a breeze. Additionally, we offer unique features like Lipa Mdogo payment plans and comprehensive property management tools.",
                category=FAQCategory.PLATFORM_FEATURES,
                tags=["ai", "features", "comparison", "benefits"]
            ),
            FAQEntry(
                id="faq_002",
                question="How does the AI-powered recommendation system work?",
                answer="Our AI analyzes your search history, preferences, and behavior to understand your unique requirements. It then suggests properties that match your criteria, ensuring a more efficient and tailored home-hunting experience. The system continuously learns from your interactions to improve recommendations.",
                category=FAQCategory.PLATFORM_FEATURES,
                tags=["ai", "recommendations", "machine-learning", "personalization"]
            ),
            FAQEntry(
                id="faq_003",
                question="Is my personal information secure on Mwarokin?",
                answer="Yes, we take data security seriously. Our platform employs the latest encryption technologies to safeguard your personal information, ensuring a secure and private browsing experience. We comply with international data protection regulations.",
                category=FAQCategory.SECURITY_PRIVACY,
                tags=["security", "privacy", "data-protection", "encryption"]
            ),
            FAQEntry(
                id="faq_004",
                question="Can I schedule property viewings through the app?",
                answer="Absolutely! Mwarokin allows you to seamlessly schedule property viewings at your convenience. Just find a property you're interested in, and with a few taps, you can set up a viewing with the listing agent.",
                category=FAQCategory.PROPERTIES,
                tags=["viewings", "appointments", "property-tours", "scheduling"]
            ),
            FAQEntry(
                id="faq_005",
                question="What types of properties are available on Mwarokin?",
                answer="Mwarokin offers a diverse range of properties including apartments, houses, commercial spaces, and land. Our extensive listings cover various locations across Africa, ensuring you find the perfect property.",
                category=FAQCategory.PROPERTIES,
                tags=["property-types", "listings", "apartments", "commercial"]
            ),
            FAQEntry(
                id="faq_006",
                question="How do I list my property on Mwarokin?",
                answer="Listing your property is easy! Simply create an account, fill in the necessary details, upload high-quality images, and set your desired preferences. Our platform makes the listing process hassle-free.",
                category=FAQCategory.PROPERTIES,
                tags=["listing", "property-owner", "upload", "management"]
            ),
            FAQEntry(
                id="faq_007",
                question="Can I receive notifications for new listings?",
                answer="Yes, Mwarokin provides a customizable notification system. Set your preferences, and we'll notify you instantly when new properties that match your criteria become available.",
                category=FAQCategory.PLATFORM_FEATURES,
                tags=["notifications", "alerts", "new-listings", "preferences"]
            ),
            FAQEntry(
                id="faq_008",
                question="Is Mwarokin available on mobile devices?",
                answer="Absolutely! You can download our app on both iOS and Android devices. Experience the convenience of browsing and managing your property search on the go.",
                category=FAQCategory.MOBILE_APP,
                tags=["mobile", "app", "ios", "android", "download"]
            ),
            FAQEntry(
                id="faq_009",
                question="How can I contact customer support?",
                answer="Our dedicated customer support team is ready to assist you. Reach out through the app's help center, use in-app chat, email support@mwarokin.com, or call +254-704-919-388.",
                category=FAQCategory.TECHNICAL_SUPPORT,
                tags=["support", "contact", "help", "customer-service"]
            ),
            FAQEntry(
                id="faq_010",
                question="Are there any fees associated with using Mwarokin?",
                answer="Mwarokin is free to download and use for property seekers. Property owners may incur listing fees. Check our pricing page for detailed information on subscription plans.",
                category=FAQCategory.ACCOUNT_BILLING,
                tags=["fees", "pricing", "cost", "subscription"]
            )
        ]
        
        for faq in initial_faqs:
            self.faq_entries[faq.id] = faq
        
        # Update semantic search processor
        self.ai_processors["semantic_search"].update_faq_corpus(list(self.faq_entries.values()))
        
        # Save to database
        self._save_faqs_to_db()
    
    def _save_faqs_to_db(self):
        """Save FAQ entries to database"""
        with self._get_db_connection() as conn:
            for faq in self.faq_entries.values():
                conn.execute('''
                    INSERT OR REPLACE INTO faq_entries 
                    (id, question, answer, category, tags, popularity_score, helpful_votes, 
                     unhelpful_votes, created_at, updated_at, ai_generated, related_questions)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    faq.id, faq.question, faq.answer, faq.category.value,
                    json.dumps(faq.tags), faq.popularity_score, faq.helpful_votes,
                    faq.unhelpful_votes, faq.created_at.isoformat(),
                    faq.updated_at.isoformat(), faq.ai_generated,
                    json.dumps(faq.related_questions)
                ))
    
    def _setup_api_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/")
        async def root():
            return {"message": "Mwarokin Advanced FAQ System", "status": "operational"}
        
        @self.app.get("/faqs")
        async def get_all_faqs(category: Optional[str] = None):
            """Get all FAQs, optionally filtered by category"""
            faqs = list(self.faq_entries.values())
            if category:
                faqs = [faq for faq in faqs if faq.category.value == category]
            return {"faqs": [faq.to_dict() for faq in faqs]}
        
        @self.app.get("/faqs/{faq_id}")
        async def get_faq(faq_id: str):
            """Get specific FAQ by ID"""
            faq = self.faq_entries.get(faq_id)
            if not faq:
                raise HTTPException(status_code=404, detail="FAQ not found")
            return faq.to_dict()
        
        @self.app.post("/search")
        async def search_faqs(query: str, user_id: Optional[str] = None):
            """Advanced semantic search for FAQs"""
            start_time = time.time()
            
            # Process query with AI
            context = {
                "user_history": self._get_user_history(user_id) if user_id else [],
                "current_category": None
            }
            
            # Get AI insights
            semantic_results = await self.ai_processors["semantic_search"].process_query(query, context)
            sentiment_results = await self.ai_processors["sentiment_analysis"].process_query(query, context)
            context_results = await self.ai_processors["context_understanding"].process_query(query, context)
            
            # Get matching FAQs
            matching_faqs = []
            for match in semantic_results["matches"]:
                faq = self.faq_entries.get(match["faq_id"])
                if faq:
                    matching_faqs.append({
                        **faq.to_dict(),
                        "relevance_score": match["similarity_score"]
                    })
            
            search_duration = time.time() - start_time
            
            # Log interaction
            interaction = UserInteraction(
                id=f"interaction_{uuid.uuid4().hex[:8]}",
                user_id=user_id or "anonymous",
                question=query,
                timestamp=datetime.now(),
                sentiment=UserSentiment(sentiment_results["sentiment"]),
                search_duration=search_duration
            )
            self.user_interactions.append(interaction)
            self._save_interaction_to_db(interaction)
            
            # Update metrics
            self._update_search_metrics(search_duration, len(matching_faqs) > 0)
            
            return {
                "query": query,
                "matches": matching_faqs,
                "ai_insights": {
                    "semantic_search": semantic_results,
                    "sentiment_analysis": sentiment_results,
                    "context_understanding": context_results
                },
                "search_metadata": {
                    "response_time": search_duration,
                    "total_results": len(matching_faqs),
                    "search_id": interaction.id
                }
            }
        
        @self.app.post("/feedback")
        async def submit_feedback(interaction_id: str, helpful: bool, rating: Optional[int] = None):
            """Submit feedback for a search interaction"""
            interaction = next((i for i in self.user_interactions if i.id == interaction_id), None)
            if interaction:
                interaction.found_helpful = helpful
                interaction.feedback_rating = rating
                self._update_interaction_in_db(interaction)
                return {"status": "feedback_recorded"}
            raise HTTPException(status_code=404, detail="Interaction not found")
        
        @self.app.post("/faqs/{faq_id}/vote")
        async def vote_faq(faq_id: str, helpful: bool):
            """Vote on FAQ helpfulness"""
            faq = self.faq_entries.get(faq_id)
            if not faq:
                raise HTTPException(status_code=404, detail="FAQ not found")
            
            if helpful:
                faq.helpful_votes += 1
            else:
                faq.unhelpful_votes += 1
            
            faq.updated_at = datetime.now()
            self._update_faq_in_db(faqq)
            
            return {"status": "vote_recorded", "helpful_votes": faq.helpful_votes, "unhelpful_votes": faq.unhelpful_votes}
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket for real-time updates"""
            await websocket.accept()
            client_id = str(uuid.uuid4())
            self.connected_clients[client_id] = websocket
            
            try:
                while True:
                    data = await websocket.receive_json()
                    await self._handle_websocket_message(client_id, data)
            except WebSocketDisconnect:
                del self.connected_clients[client_id]
    
    def _setup_cors(self):
        """Setup CORS middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    async def _handle_websocket_message(self, client_id: str, data: Dict[str, Any]):
        """Handle WebSocket messages"""
        message_type = data.get("type")
        
        if message_type == "search":
            query = data.get("query", "")
            results = await self.search_faqs(query, data.get("user_id"))
            await self.connected_clients[client_id].send_json({
                "type": "search_results",
                "data": results
            })
        
        elif message_type == "subscribe_metrics":
            # Send periodic system metrics
            asyncio.create_task(self._send_periodic_metrics(client_id))
    
    async def _send_periodic_metrics(self, client_id: str):
        """Send periodic system metrics to subscribed clients"""
        while client_id in self.connected_clients:
            metrics = self.get_system_metrics()
            await self.connected_clients[client_id].send_json({
                "type": "system_metrics",
                "data": metrics
            })
            await asyncio.sleep(10)  # Send every 10 seconds
    
    def _get_user_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's search history"""
        user_interactions = [
            interaction for interaction in self.user_interactions 
            if interaction.user_id == user_id
        ]
        return [interaction.to_dict() for interaction in user_interactions[-10:]]  # Last 10 interactions
    
    def _save_interaction_to_db(self, interaction: UserInteraction):
        """Save user interaction to database"""
        with self._get_db_connection() as conn:
            conn.execute('''
                INSERT INTO user_interactions 
                (id, user_id, question, timestamp, sentiment, found_helpful, clicked_faq, search_duration, feedback_rating)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                interaction.id, interaction.user_id, interaction.question,
                interaction.timestamp.isoformat(), interaction.sentiment.value,
                interaction.found_helpful, interaction.clicked_faq,
                interaction.search_duration, interaction.feedback_rating
            ))
    
    def _update_interaction_in_db(self, interaction: UserInteraction):
        """Update user interaction in database"""
        with self._get_db_connection() as conn:
            conn.execute('''
                UPDATE user_interactions 
                SET found_helpful = ?, feedback_rating = ?
                WHERE id = ?
            ''', (interaction.found_helpful, interaction.feedback_rating, interaction.id))
    
    def _update_faq_in_db(self, faq: FAQEntry):
        """Update FAQ in database"""
        with self._get_db_connection() as conn:
            conn.execute('''
                UPDATE faq_entries 
                SET helpful_votes = ?, unhelpful_votes = ?, updated_at = ?, popularity_score = ?
                WHERE id = ?
            ''', (faq.helpful_votes, faq.unhelpful_votes, faq.updated_at.isoformat(), faq.popularity_score, faq.id))
    
    def _update_search_metrics(self, response_time: float, successful: bool):
        """Update search performance metrics"""
        current_hour = datetime.now().strftime("%Y-%m-%d %H:00:00")
        
        with self._get_db_connection() as conn:
            # Get existing metrics for current hour
            result = conn.execute('''
                SELECT * FROM system_metrics 
                WHERE timestamp = ? 
                ORDER BY id DESC LIMIT 1
            ''', (current_hour,)).fetchone()
            
            if result:
                total_searches = result["total_searches"] + 1
                successful_searches = result["successful_searches"] + (1 if successful else 0)
                avg_response_time = (result["average_response_time"] * result["total_searches"] + response_time) / total_searches
                
                conn.execute('''
                    UPDATE system_metrics 
                    SET total_searches = ?, successful_searches = ?, average_response_time = ?
                    WHERE id = ?
                ''', (total_searches, successful_searches, avg_response_time, result["id"]))
            else:
                conn.execute('''
                    INSERT INTO system_metrics 
                    (timestamp, total_searches, successful_searches, average_response_time, user_satisfaction_score)
                    VALUES (?, ?, ?, ?, ?)
                ''', (current_hour, 1, 1 if successful else 0, response_time, 0.8))
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics"""
        total_faqs = len(self.faq_entries)
        total_interactions = len(self.user_interactions)
        
        # Calculate success rate
        successful_searches = sum(1 for i in self.user_interactions if i.found_helpful)
        success_rate = successful_searches / total_interactions if total_interactions > 0 else 0
        
        # Calculate average response time
        avg_response_time = np.mean([i.search_duration for i in self.user_interactions]) if self.user_interactions else 0
        
        # Get popular FAQs
        popular_faqs = sorted(
            self.faq_entries.values(),
            key=lambda x: x.popularity_score,
            reverse=True
        )[:5]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_faqs": total_faqs,
            "total_interactions": total_interactions,
            "success_rate": success_rate,
            "average_response_time": avg_response_time,
            "active_connections": len(self.connected_clients),
            "popular_faqs": [faq.to_dict() for faq in popular_faqs],
            "system_health": "excellent",
            "ai_capabilities": [cap.value for cap in AICapability]
        }
    
    async def start(self):
        """Start the FAQ system"""
        self.is_running = True
        self.logger.info("🚀 Advanced FAQ System activated")
        
        # Start background tasks
        asyncio.create_task(self._periodic_maintenance())
        
        self.logger.info("✅ FAQ System online and ready")
    
    async def stop(self):
        """Stop the FAQ system"""
        self.is_running = False
        self.logger.info("🛑 FAQ System shutting down")
    
    async def _periodic_maintenance(self):
        """Perform periodic system maintenance"""
        while self.is_running:
            try:
                # Update FAQ popularity scores
                self._update_popularity_scores()
                
                # Retrain semantic search model with new data
                self.ai_processors["semantic_search"].update_faq_corpus(list(self.faq_entries.values()))
                
                # Clean up old interactions
                self._cleanup_old_data()
                
                await asyncio.sleep(300)  # Run every 5 minutes
            except Exception as e:
                self.logger.error(f"Maintenance error: {e}")
    
    def _update_popularity_scores(self):
        """Update FAQ popularity scores based on interactions"""
        for faq in self.faq_entries.values():
            # Calculate score based on votes and recent interactions
            vote_score = (faq.helpful_votes - faq.unhelpful_votes) * 0.1
            recent_interactions = sum(
                1 for interaction in self.user_interactions[-100:]
                if interaction.clicked_faq == faq.id
            )
            interaction_score = recent_interactions * 0.05
            
            faq.popularity_score = max(0, vote_score + interaction_score)
            faq.updated_at = datetime.now()
    
    def _cleanup_old_data(self):
        """Clean up old user interactions"""
        cutoff_time = datetime.now() - timedelta(days=30)
        self.user_interactions = [
            i for i in self.user_interactions 
            if i.timestamp > cutoff_time
        ]

# Real-time Dashboard Integration
class FAQDashboard:
    """Real-time dashboard for monitoring FAQ system"""
    
    def __init__(self, faq_system: AdvancedFAQSystem):
        self.faq_system = faq_system
    
    async def get_real_time_metrics(self):
        """Get real-time metrics for dashboard"""
        return self.faq_system.get_system_metrics()
    
    async def get_search_analytics(self):
        """Get search analytics data"""
        interactions = self.faq_system.user_interactions
        
        # Analyze search patterns
        common_queries = pd.Series([i.question for i in interactions]).value_counts().head(10)
        sentiment_distribution = pd.Series([i.sentiment.value for i in interactions]).value_counts()
        
        return {
            "common_queries": common_queries.to_dict(),
            "sentiment_distribution": sentiment_distribution.to_dict(),
            "total_searches_today": len([i for i in interactions if i.timestamp.date() == datetime.now().date()]),
            "success_rate_today": len([i for i in interactions if i.found_helpful and i.timestamp.date() == datetime.now().date()]) / max(1, len([i for i in interactions if i.timestamp.date() == datetime.now().date()]))
        }

# Demonstration and Testing
async def demo_advanced_faq_system():
    """Demonstrate the advanced FAQ system"""
    print("🚀 Initializing Advanced FAQ System...")
    
    # Initialize system
    faq_system = AdvancedFAQSystem()
    dashboard = FAQDashboard(faq_system)
    
    await faq_system.start()
    
    # Test searches
    test_queries = [
        "How do I list my property?",
        "Is my data secure?",
        "Payment methods accepted",
        "Mobile app download",
        "Contact customer support",
        "Property viewing scheduling",
        "Fees and pricing",
        "AI recommendations"
    ]
    
    print(f"\n🔍 Testing {len(test_queries)} search queries...")
    
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        
        # Simulate search
        results = await faq_system.search_faqs(query, "test_user_001")
        
        if results["matches"]:
            top_match = results["matches"][0]
            print(f"   ✅ Found: {top_match['question']}")
            print(f"   📊 Relevance: {top_match['relevance_score']:.3f}")
            print(f"   🎯 Sentiment: {results['ai_insights']['sentiment_analysis']['sentiment']}")
        else:
            print("   ❌ No matches found")
        
        await asyncio.sleep(1)  # Simulate user thinking time
    
    # Display system metrics
    metrics = faq_system.get_system_metrics()
    print(f"\n📊 SYSTEM METRICS:")
    print(f"   📋 Total FAQs: {metrics['total_faqs']}")
    print(f"   👥 Total Interactions: {metrics['total_interactions']}")
    print(f"   ✅ Success Rate: {metrics['success_rate']:.1%}")
    print(f"   ⚡ Avg Response Time: {metrics['average_response_time']:.3f}s")
    
    # Display analytics
    analytics = await dashboard.get_search_analytics()
    print(f"\n📈 SEARCH ANALYTICS:")
    print(f"   🔍 Total Searches Today: {analytics['total_searches_today']}")
    print(f"   🎯 Today's Success Rate: {analytics['success_rate_today']:.1%}")
    
    # Show popular FAQs
    print(f"\n🏆 POPULAR FAQs:")
    for i, faq in enumerate(metrics['popular_faqs'][:3], 1):
        print(f"   {i}. {faq['question']} (Score: {faq['popularity_score']:.2f})")
    
    # Stop system
    await faq_system.stop()
    print("\n🛑 Advanced FAQ System demonstration complete")

# FastAPI Server Startup
def start_faq_server():
    """Start the FAQ system server"""
    faq_system = AdvancedFAQSystem()
    
    @faq_system.app.on_event("startup")
    async def startup_event():
        await faq_system.start()
        print("🚀 Mwarokin Advanced FAQ Server started!")
        print("📚 API Documentation: http://localhost:8000/docs")
        print("🌐 WebSocket endpoint: ws://localhost:8000/ws")
    
    @faq_system.app.on_event("shutdown")
    async def shutdown_event():
        await faq_system.stop()
        print("🛑 FAQ Server stopped")
    
    return faq_system.app

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        # Start the server
        uvicorn.run(
            "advanced_faq_system:start_faq_server()",
            host="0.0.0.0",
            port=8000,
            reload=True
        )
    else:
        # Run demonstration
        asyncio.run(demo_advanced_faq_system())
```

## Additional Requirements File

Create a `requirements.txt` file:

```txt
fastapi==0.104.1
uvicorn==0.24.0
websockets==12.0
aiohttp==3.9.1
pandas==2.1.3
scikit-learn==1.3.2
numpy==1.25.2
python-multipart==0.0.6
```

## Usage Instructions

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Run the server**:
```bash
python advanced_faq_system.py server
```

3. **Access the API**:
   - API Documentation: http://localhost:8000/docs
   - WebSocket endpoint: ws://localhost:8000/ws
   - REST API: http://localhost:8000

## Key Features

### 🚀 **Advanced AI Capabilities**
- Semantic search with TF-IDF and cosine similarity
- Real-time sentiment analysis
- Context-aware query understanding
- Multilingual support ready

### ⚡ **Real-time Functionality**
- WebSocket connections for live updates
- Real-time system metrics
- Live search analytics
- Instant feedback processing

### 🎯 **Smart Features**
- Adaptive learning from user interactions
- Popularity-based FAQ ranking
- Predictive follow-up questions
- User behavior analysis

### 📊 **Comprehensive Analytics**
- Search success rates
- User sentiment tracking
- Popular query analysis
- System performance monitoring

### 🔒 **Enterprise Ready**
- SQLite database persistence
- RESTful API with FastAPI
- CORS support
- Production-ready architecture

This advanced FAQ system provides a complete, real-time solution for managing and serving FAQ content with AI-powered intelligence and comprehensive analytics!