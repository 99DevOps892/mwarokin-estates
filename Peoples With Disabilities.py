import timestamp
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import re
from typing import List, Dict
import asyncio
from contextlib import asynccontextmanager
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data models
class TextSimplificationRequest(BaseModel):
    text: str
    simplification_level: str = "moderate"  # mild, moderate, extensive

class SimplifiedTextResponse(BaseModel):
    original: str
    simplified: str
    changes_made: List[Dict[str, str]]
    readability_score: float

class CommunityPost(BaseModel):
    user_id: str
    content: str
    post_type: str = "discussion"

class PostResponse(BaseModel):
    post_id: str
    user_id: str
    content: str
    timestamp: str
    likes: int = 0
    comments: int = 0

# In-memory storage for demo purposes
posts_db = defaultdict(dict)
simplification_cache = {}

# Complex word replacements at different levels
SIMPLIFICATION_RULES = {
    "mild": {
        r'\butilize\b': 'use',
        r'\bemploy\b': 'use',
        r'\bapproximately\b': 'about',
        r'\bcommence\b': 'start',
        r'\bterminate\b': 'end',
        r'\bdemonstrate\b': 'show',
        r'\bobtain\b': 'get',
    },
    "moderate": {
        r'\bcomplicated\b': 'complex',
        r'\bcomplex\b': 'not simple',
        r'\bdifficult\b': 'hard',
        r'\bassistance\b': 'help',
        r'\badditional\b': 'more',
        r'\brequire\b': 'need',
        r'\bfacilitate\b': 'help',
        r'\binitiate\b': 'start',
        r'\bconclude\b': 'end',
        r'\bapproximately\b': 'about',
        r'\bsubstantial\b': 'large',
    },
    "extensive": {
        r'\bcomplicated\b': 'simple',
        r'\bcomplex\b': 'simple',
        r'\bdifficult\b': 'easy',
        r'\bchallenging\b': 'easy',
        r'\bcomplicated\b': 'not hard',
        r'\butilize\b': 'use',
        r'\bemploy\b': 'use',
        r'\bapproximately\b': 'about',
        r'\bassistance\b': 'help',
        r'\bcommence\b': 'start',
        r'\bterminate\b': 'end',
        r'\badditional\b': 'more',
        r'\bdemonstrate\b': 'show',
        r'\brequire\b': 'need',
        r'\bobtain\b': 'get',
        r'\bfacilitate\b': 'help',
        r'\binitiate\b': 'start',
        r'\bconclude\b': 'end',
        r'\bsubstantial\b': 'large',
        r'\bnumerous\b': 'many',
        r'\bacquire\b': 'get',
        r'\bendeavor\b': 'try',
    }
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Accessibility Hub API")
    yield
    # Shutdown
    logger.info("Shutting down Accessibility Hub API")

app = FastAPI(
    title="Accessibility Hub API",
    description="API for accessibility tools and community features",
    version="1.0.0",
    lifespan=lifespan
)

def calculate_readability_score(text: str) -> float:
    """Calculate a simple readability score (0-1, higher is better)"""
    words = text.split()
    if not words:
        return 1.0
    
    # Simple metrics for demonstration
    avg_word_length = sum(len(word) for word in words) / len(words)
    sentence_count = text.count('.') + text.count('!') + text.count('?')
    word_count = len(words)
    
    # Normalize scores (these are simplified calculations)
    word_score = max(0, 1 - (avg_word_length - 4) / 10)  # Prefer shorter words
    sentence_score = max(0, 1 - (word_count / max(1, sentence_count) - 15) / 20)  # Prefer shorter sentences
    
    return (word_score + sentence_score) / 2

async def simplify_text_coroutine(text: str, level: str) -> SimplifiedTextResponse:
    """Async function to simplify text"""
    # Simulate some processing time
    await asyncio.sleep(0.1)
    
    original_text = text
    changes = []
    simplified = text
    
    # Apply simplification rules
    rules = SIMPLIFICATION_RULES.get(level, SIMPLIFICATION_RULES["moderate"])
    
    for pattern, replacement in rules.items():
        original_simplified = simplified
        simplified = re.sub(pattern, replacement, simplified, flags=re.IGNORECASE)
        
        # Check if any changes were made
        if simplified != original_simplified:
            matches = re.findall(pattern, original_simplified, flags=re.IGNORECASE)
            for match in matches:
                changes.append({
                    "original": match,
                    "simplified": replacement,
                    "type": "word_replacement"
                })
    
    # Additional simplification: break long sentences
    if level in ["moderate", "extensive"]:
        sentences = re.split(r'[.!?]+', simplified)
        if len(sentences) > 1:
            new_sentences = []
            for sentence in sentences:
                words = sentence.strip().split()
                if len(words) > 15 and level == "extensive":  # Very long sentence
                    # Split into two sentences (simplified approach)
                    mid_point = len(words) // 2
                    new_sentences.append(' '.join(words[:mid_point]) + '.')
                    new_sentences.append(' '.join(words[mid_point:]))
                else:
                    new_sentences.append(sentence.strip())
            simplified = '. '.join(filter(None, new_sentences))
    
    readability_before = calculate_readability_score(original_text)
    readability_after = calculate_readability_score(simplified)
    
    return SimplifiedTextResponse(
        original=original_text,
        simplified=simplified,
        changes_made=changes,
        readability_score=readability_after
    )

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Accessibility Hub API",
        "version": "1.0.0",
        "endpoints": {
            "text_simplification": "/api/simplify-text",
            "community_posts": "/api/posts",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": asyncio.get_event_loop().time()}

@app.post("/api/simplify-text", response_model=SimplifiedTextResponse)
async def simplify_text(request: TextSimplificationRequest):
    """
    Simplify complex text for better accessibility
    
    - **text**: The text to simplify
    - **simplification_level**: Level of simplification (mild, moderate, extensive)
    """
    try:
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        # Check cache first
        cache_key = f"{request.text}:{request.simplification_level}"
        if cache_key in simplification_cache:
            logger.info("Returning cached simplification result")
            return simplification_cache[cache_key]
        
        # Process text
        result = await simplify_text_coroutine(request.text, request.simplification_level)
        
        # Cache the result
        simplification_cache[cache_key] = result
        
        logger.info(f"Simplified text from {len(request.text)} to {len(result.simplified)} characters")
        return result
        
    except Exception as e:
        logger.error(f"Error simplifying text: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing text")

@app.get("/api/posts", response_model=List[PostResponse])
async def get_community_posts(limit: int = 10, offset: int = 0):
    """Get community posts with pagination"""
    try:
        # Convert to list and sort by timestamp (simplified)
        posts_list = list(posts_db.values())
        sorted_posts = sorted(posts_list, key=lambda x: x.get('timestamp', ''), reverse=True)
        
        paginated_posts = sorted_posts[offset:offset + limit]
        
        return [
            PostResponse(
                post_id=post.get('post_id', ''),
                user_id=post.get('user_id', ''),
                content=post.get('content', ''),
                timestamp=post.get('timestamp', ''),
                likes=post.get('likes', 0),
                comments=post.get('comments', 0)
            )
            for post in paginated_posts
        ]
    except Exception as e:
        logger.error(f"Error retrieving posts: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving posts")

@app.post("/api/posts", response_model=PostResponse)
async def create_community_post(post: CommunityPost):
    """Create a new community post"""
    try:
        if not post.content.strip():
            raise HTTPException(status_code=400, detail="Post content cannot be empty")
        
        post_id = f"post_{len(posts_db) + 1}"
        timestamp = asyncio.get_event_loop().time()
        
        new_post = {
            'post_id': post_id,
            'user_id': post.user_id,
            'content': post.content,
            'post_type': post.post_type,
            'timestamp': str(timestamp),
            'likes': 0,
            'comments': 0
        }
        
        posts_db[post_id] = new_post
        
        logger.info(f"Created new post {post_id} by user {post.user_id}")
        
        return PostResponse(**new_post)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating post: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating post")

@app.post("/api/posts/{post_id}/like")
async def like_post(post_id: str):
    """Like a community post"""
    try:
        if post_id not in posts_db:
            raise HTTPException(status_code=404, detail="Post not found")
        
        posts_db[post_id]['likes'] += 1
        
        return {"message": "Post liked successfully", "likes": posts_db[post_id]['likes']}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error liking post: {str(e)}")
        raise HTTPException(status_code=500, detail="Error liking post")

# Utility endpoints for text analysis
@app.get("/api/analyze-text")
async def analyze_text(text: str):
    """Analyze text complexity and provide metrics"""
    try:
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        
        metrics = {
            "word_count": len(words),
            "sentence_count": len([s for s in sentences if s.strip()]),
            "avg_sentence_length": len(words) / max(1, len(sentences)),
            "avg_word_length": sum(len(word) for word in words) / max(1, len(words)),
            "readability_score": calculate_readability_score(text),
            "complex_words": [
                word for word in words 
                if len(word) > 8 and not any(char.isdigit() for char in word)
            ]
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error analyzing text: {str(e)}")
        raise HTTPException(status_code=500, detail="Error analyzing text")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

And here's a modern Python client to interact with the API:

```python
import httpx
import asyncio
from typing import List, Optional
from dataclasses import dataclass
import json

@dataclass
class SimplifiedText:
    original: str
    simplified: str
    changes_made: List[dict]
    readability_score: float

@dataclass
class CommunityPost:
    post_id: str
    user_id: str
    content: str
    timestamp: str
    likes: int
    comments: int

class AccessibilityHubClient:
    """Modern async client for the Accessibility Hub API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def simplify_text(
        self, 
        text: str, 
        level: str = "moderate"
    ) -> SimplifiedText:
        """Simplify text using the API"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/simplify-text",
                json={"text": text, "simplification_level": level}
            )
            response.raise_for_status()
            
            data = response.json()
            return SimplifiedText(
                original=data["original"],
                simplified=data["simplified"],
                changes_made=data["changes_made"],
                readability_score=data["readability_score"]
            )
            
        except httpx.HTTPStatusError as e:
            print(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            print(f"Error simplifying text: {e}")
            raise
    
    async def analyze_text_complexity(self, text: str) -> dict:
        """Analyze text complexity"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/analyze-text",
                params={"text": text}
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            print(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
    
    async def create_post(self, user_id: str, content: str) -> CommunityPost:
        """Create a new community post"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/posts",
                json={"user_id": user_id, "content": content}
            )
            response.raise_for_status()
            
            data = response.json()
            return CommunityPost(**data)
            
        except httpx.HTTPStatusError as e:
            print(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
    
    async def get_posts(self, limit: int = 10, offset: int = 0) -> List[CommunityPost]:
        """Get community posts"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/posts",
                params={"limit": limit, "offset": offset}
            )
            response.raise_for_status()
            
            data = response.json()
            return [CommunityPost(**post) for post in data]
            
        except httpx.HTTPStatusError as e:
            print(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
    
    async def like_post(self, post_id: str) -> dict:
        """Like a community post"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/posts/{post_id}/like"
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            print(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
    
    async def health_check(self) -> bool:
        """Check if API is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False

# Example usage with modern Python features
async def demonstrate_functionality():
    """Demonstrate the API functionality"""
    async with AccessibilityHubClient() as client:
        # Check health
        is_healthy = await client.health_check()
        print(f"API healthy: {is_healthy}")
        
        if not is_healthy:
            print("API is not available")
            return
        
        # Example text simplification
        complex_text = """
        The utilization of complicated technological apparatus necessitates 
        substantial cognitive effort and may prove challenging for individuals 
        with cognitive disabilities. We should endeavor to facilitate more 
        accessible user experiences.
        """
        
        print("Original text:", complex_text)
        
        # Simplify with different levels
        for level in ["mild", "moderate", "extensive"]:
            simplified = await client.simplify_text(complex_text, level)
            print(f"\n--- {level.upper()} SIMPLIFICATION ---")
            print(f"Simplified: {simplified.simplified}")
            print(f"Readability score: {simplified.readability_score:.2f}")
            print(f"Changes made: {len(simplified.changes_made)}")
        
        # Analyze text complexity
        analysis = await client.analyze_text_complexity(complex_text)
        print(f"\n--- TEXT ANALYSIS ---")
        print(f"Word count: {analysis['word_count']}")
        print(f"Sentence count: {analysis['sentence_count']}")
        print(f"Complex words: {analysis['complex_words']}")
        
        # Community features
        post = await client.create_post(
            user_id="user123",
            content="Has anyone tried the new text simplification feature? It's amazing!"
        )
        print(f"\n--- COMMUNITY POST ---")
        print(f"Created post: {post.content}")
        
        # Get recent posts
        posts = await client.get_posts(limit=3)
        print(f"\n--- RECENT POSTS ---")
        for p in posts:
            print(f"- {p.content} (Likes: {p.likes})")

# Functional programming utilities
def process_text_batch(
    texts: List[str], 
    simplification_level: str = "moderate"
) -> List[SimplifiedText]:
    """Process multiple texts in batch (functional style)"""
    
    async def process_batch():
        async with AccessibilityHubClient() as client:
            # Create tasks for all texts
            tasks = [
                client.simplify_text(text, simplification_level) 
                for text in texts
            ]
            # Execute concurrently
            return await asyncio.gather(*tasks, return_exceptions=True)
    
    # Run the async function
    results = asyncio.run(process_batch())
    
    # Filter out exceptions and return successful results
    return [
        result for result in results 
        if not isinstance(result, Exception)
    ]

def create_simplification_pipeline(level: str = "moderate"):
    """Create a text simplification pipeline (functional composition)"""
    
    async def pipeline(texts: List[str]) -> List[SimplifiedText]:
        return process_text_batch(texts, level)
    
    return pipeline

# Modern usage with type hints and async context
if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(demonstrate_functionality())
    
    # Example of batch processing
    sample_texts = [
        "The utilization of complex apparatus is challenging.",
        "We need to facilitate better user experiences.",
        "The implementation necessitates substantial effort."
    ]
    
    print("\n--- BATCH PROCESSING ---")
    results = process_text_batch(sample_texts, "moderate")
    for i, result in enumerate(results):
        print(f"Text {i+1}: {result.simplified}")
```

This modern Python code demonstrates:

1. **FastAPI** for modern, async web API
2. **Type hints** throughout for better code clarity
3. **Async/await** for non-blocking operations
4. **Pydantic models** for data validation
5. **Functional programming** patterns with pure functions
6. **Context managers** for resource management
7. **Comprehensive error handling**
8. **Modern dataclasses** for data structures
9. **Async client** with httpx
10. **Batch processing** capabilities

The code provides a complete backend for the text simplification feature and community functionality from your HTML, using modern Python best practices.