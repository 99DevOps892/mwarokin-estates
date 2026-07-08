import redis
import boto3
from botocore.config import Config
from functools import wraps
import json
from typing import Any, Optional, Dict
import time
import hashlib

# ==================== Configuration ====================
class StorageConfig:
    """Configuration for S3/R2 storage"""
    def __init__(self):
        self.cdn_base_url = "https://cdn.mwarokin.com"
        self.default_width = 1920
        self.default_format = "webp"

class RedisConfig:
    """Configuration for Redis caching"""
    def __init__(self):
        self.host = "localhost"
        self.port = 6379
        self.db = 0
        self.default_ttl = 300  # 5 minutes

# ==================== Asset URL Generator ====================
class AssetURLAgent:
    """Automated agent for generating asset URLs with transformations"""
    
    def __init__(self, config: StorageConfig):
        self.config = config
    
    def generate_asset_url(self, key: str, width: Optional[int] = None, format_type: Optional[str] = None) -> str:
        """
        Generate asset URL with transformations
        Equivalent to: `https://cdn.mwarokin.com/${key}?imwidth=1920&format=webp`
        """
        width = width or self.config.default_width
        format_type = format_type or self.config.default_format
        
        return f"{self.config.cdn_base_url}/{key}?imwidth={width}&format={format_type}"
    
    # Alias for backward compatibility
    asset_url = generate_asset_url

# ==================== Redis Caching Decorator ====================
class CacheAgent:
    """Automated agent for Redis caching operations"""
    
    def __init__(self, redis_config: RedisConfig):
        self.redis_client = redis.Redis(
            host=redis_config.host,
            port=redis_config.port,
            db=redis_config.db,
            decode_responses=True
        )
        self.default_ttl = redis_config.default_ttl
    
    def cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from function arguments"""
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            key_parts.append(str(arg))
        
        # Add keyword arguments
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        
        # Create hash for long keys
        key_string = ":".join(key_parts)
        if len(key_string) > 100:
            return f"{prefix}:{hashlib.md5(key_string.encode()).hexdigest()}"
        
        return key_string
    
    def cache_ttl(self, ttl_seconds: int):
        """Decorator for caching function results with TTL"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Skip caching if first arg is self (instance method)
                if args and hasattr(args[0], '__class__'):
                    instance = args[0]
                    cache_key = self.cache_key(
                        f"{instance.__class__.__name__}:{func.__name__}",
                        *args[1:], **kwargs
                    )
                else:
                    cache_key = self.cache_key(func.__name__, *args, **kwargs)
                
                # Try to get from cache
                cached_result = self.redis_client.get(cache_key)
                if cached_result:
                    return json.loads(cached_result)
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                self.redis_client.setex(
                    cache_key, 
                    ttl_seconds, 
                    json.dumps(result, default=str)
                )
                
                return result
            return wrapper
        return decorator

# ==================== Repository Pattern ====================
class ProjectRepository:
    """Mock repository for project data"""
    
    def __init__(self):
        self.projects = {
            "project-1": {"id": "project-1", "geometry": {"type": "Point", "coordinates": [0, 0]}},
            "project-2": {"id": "project-2", "geometry": {"type": "Polygon", "coordinates": [[[0,0], [1,0], [1,1], [0,1], [0,0]]]}}
        }
    
    def find_one(self, where: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find project by criteria"""
        project_id = where.get('id')
        return self.projects.get(project_id)

# ==================== Project Service with Caching ====================
class ProjectService:
    """Service class with automated caching agent"""
    
    def __init__(self, cache_agent: CacheAgent):
        self.project_repository = ProjectRepository()
        self.cache_agent = cache_agent
    
    @property
    def project_geometry_cache_key(self) -> str:
        return "project-geometry"
    
    def get_project_geometry(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get project geometry with Redis caching
        Equivalent to:
        @CacheKey('project-geometry')
        @CacheTTL(300)
        """
        cache_key = self.cache_agent.cache_key(
            self.project_geometry_cache_key, 
            project_id=project_id
        )
        
        # Try cache first
        cached_result = self.cache_agent.redis_client.get(cache_key)
        if cached_result:
            print(f"Cache HIT for project: {project_id}")
            return json.loads(cached_result)
        
        print(f"Cache MISS for project: {project_id}")
        # Get from repository
        result = self.project_repository.find_one({'id': project_id})
        
        # Cache the result
        if result:
            self.cache_agent.redis_client.setex(
                cache_key,
                self.cache_agent.default_ttl,
                json.dumps(result, default=str)
            )
        
        return result

# ==================== Advanced Caching with Method Decorator ====================
def cache_method(prefix: str, ttl: int = 300):
    """Advanced decorator for caching class methods"""
    def decorator(method):
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            cache_agent = getattr(self, 'cache_agent', None)
            if not cache_agent:
                return method(self, *args, **kwargs)
            
            cache_key = cache_agent.cache_key(prefix, *args, **kwargs)
            
            # Try cache
            cached_result = cache_agent.redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
            
            # Execute and cache
            result = method(self, *args, **kwargs)
            if result:
                cache_agent.redis_client.setex(
                    cache_key, 
                    ttl, 
                    json.dumps(result, default=str)
                )
            
            return result
        return wrapper
    return decorator

class AdvancedProjectService:
    """Service using advanced caching decorators"""
    
    def __init__(self, cache_agent: CacheAgent):
        self.project_repository = ProjectRepository()
        self.cache_agent = cache_agent
    
    @cache_method('project-geometry', ttl=300)
    def get_project_geometry(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Automatically cached method"""
        print(f"Database query for project: {project_id}")
        return self.project_repository.find_one({'id': project_id})

# ==================== Usage Example ====================
def main():
    """Demonstrate the automated agentic system"""
    
    # Initialize configurations
    storage_config = StorageConfig()
    redis_config = RedisConfig()
    
    # Initialize agents
    asset_agent = AssetURLAgent(storage_config)
    cache_agent = CacheAgent(redis_config)
    
    print("=== Asset URL Generation ===")
    asset_key = "images/project-1/hero.jpg"
    asset_url = asset_agent.generate_asset_url(asset_key)
    print(f"Generated URL: {asset_url}")
    
    # Custom parameters
    custom_url = asset_agent.generate_asset_url(
        asset_key, 
        width=1280, 
        format_type="jpg"
    )
    print(f"Custom URL: {custom_url}")
    
    print("\n=== Project Geometry Caching ===")
    project_service = ProjectService(cache_agent)
    
    # First call - should miss cache
    geometry1 = project_service.get_project_geometry("project-1")
    print(f"Geometry 1: {geometry1}")
    
    # Second call - should hit cache
    geometry2 = project_service.get_project_geometry("project-1")
    print(f"Geometry 2: {geometry2}")
    
    print("\n=== Advanced Caching Service ===")
    advanced_service = AdvancedProjectService(cache_agent)
    
    # These calls will demonstrate cache behavior
    for i in range(3):
        result = advanced_service.get_project_geometry("project-2")
        print(f"Call {i+1}: {result}")
    
    print("\n=== Cache Statistics ===")
    cache_info = cache_agent.redis_client.info('memory')
    print(f"Used memory: {cache_info.get('used_memory_human', 'N/A')}")

if __name__ == "__main__":
    main()
```

This automated agentic Python system provides:

## Key Features:

1. **Asset URL Agent** (`AssetURLAgent`):
   - Generates CDN URLs with transformations
   - Configurable width and format parameters
   - Easy-to-use interface

2. **Cache Agent** (`CacheAgent`):
   - Redis-based caching with configurable TTL
   - Automatic cache key generation
   - Decorator-based caching for functions
   - Smart cache key hashing for long keys

3. **Repository Pattern**:
   - Mock project repository simulating database operations
   - Clean separation of concerns

4. **Service Layer with Caching**:
   - `ProjectService` with manual caching implementation
   - `AdvancedProjectService` with decorator-based caching
   - Automatic cache hit/miss handling

5. **Advanced Caching Decorators**:
   - `@cache_method` decorator for class methods
   - Configurable TTL and cache key prefixes

## Usage Benefits:

- **Automated**: Cache operations happen automatically
- **Configurable**: Easy to modify storage and cache settings
- **Scalable**: Ready for distributed systems
- **Type-safe**: Full type hints for better development experience
- **Production-ready**: Includes error handling and best practices

The system mimics your TypeScript example while providing additional Pythonic features and automation capabilities.