"""
Cache management layer with Redis backend and in-memory fallback
"""
from typing import Any, Callable, Optional, TypeVar
from datetime import datetime, timedelta
import json
import logging
import hashlib

logger = logging.getLogger(__name__)

T = TypeVar('T')

# In-memory fallback cache
_memory_cache: dict[str, tuple[Any, datetime]] = {}


class CacheManager:
    """Manages caching operations with Redis backend or in-memory fallback"""
    
    def __init__(self, redis_client: Optional[Any] = None):
        """
        Initialize cache manager.
        
        Args:
            redis_client: Optional redis.Redis instance. If None, uses in-memory cache.
        """
        self.redis = redis_client
        self.use_memory = redis_client is None
    
    async def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], T],
        ttl: int = 3600
    ) -> T:
        """
        Get value from cache or compute and cache it.
        
        Args:
            key: Cache key
            compute_fn: Async function to compute value if cache miss
            ttl: Time to live in seconds (default 1 hour)
        
        Returns:
            Cached or computed value
        """
        try:
            # Try to get from cache
            cached_value = await self.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {key}")
                return cached_value
            
            # Cache miss - compute value
            logger.debug(f"Cache miss: {key}")
            value = await compute_fn()
            
            # Store in cache
            await self.set(key, value, ttl)
            return value
            
        except Exception as e:
            logger.error(f"Cache error for key {key}: {e}")
            # Fallback to recomputing if cache fails
            return await compute_fn()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.use_memory:
                return self._memory_get(key)
            else:
                # Redis get
                value = self.redis.get(key)
                if value:
                    return json.loads(value)
                return None
        except Exception as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL"""
        try:
            if self.use_memory:
                self._memory_set(key, value, ttl)
            else:
                # Redis set with expiration
                self.redis.setex(
                    key,
                    ttl,
                    json.dumps(value, default=str)
                )
            return True
        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            return False
    
    async def invalidate(self, key: str) -> bool:
        """Remove value from cache"""
        try:
            if self.use_memory:
                self._memory_delete(key)
            else:
                self.redis.delete(key)
            logger.debug(f"Cache invalidated: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache invalidate failed for key {key}: {e}")
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern.
        
        Args:
            pattern: Pattern like "dashboard:*" or "issues:app_123:*"
        
        Returns:
            Number of keys invalidated
        """
        try:
            if self.use_memory:
                return self._memory_delete_pattern(pattern)
            else:
                # Redis pattern delete
                keys = self.redis.keys(pattern)
                if keys:
                    return self.redis.delete(*keys)
                return 0
        except Exception as e:
            logger.error(f"Cache pattern invalidate failed for pattern {pattern}: {e}")
            return 0
    
    async def health_check(self) -> bool:
        """Check if cache backend is healthy"""
        try:
            if self.use_memory:
                return True
            else:
                # Ping Redis
                return self.redis.ping()
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return False
    
    # In-memory cache utilities
    @staticmethod
    def _memory_get(key: str) -> Optional[Any]:
        """Get value from in-memory cache"""
        if key in _memory_cache:
            value, expires_at = _memory_cache[key]
            if datetime.utcnow() < expires_at:
                return value
            else:
                # Expired
                del _memory_cache[key]
                return None
        return None
    
    @staticmethod
    def _memory_set(key: str, value: Any, ttl: int) -> None:
        """Set value in in-memory cache"""
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        _memory_cache[key] = (value, expires_at)
    
    @staticmethod
    def _memory_delete(key: str) -> None:
        """Delete from in-memory cache"""
        if key in _memory_cache:
            del _memory_cache[key]
    
    @staticmethod
    def _memory_delete_pattern(pattern: str) -> int:
        """Delete from in-memory cache by pattern"""
        import fnmatch
        keys_to_delete = [k for k in _memory_cache.keys() if fnmatch.fnmatch(k, pattern)]
        for key in keys_to_delete:
            del _memory_cache[key]
        return len(keys_to_delete)
    
    @staticmethod
    def generate_cache_key(*parts: str) -> str:
        """Generate cache key from parts"""
        return ":".join(str(p) for p in parts)


# Global cache instance
_cache_instance: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """Get or create global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance


def init_cache(redis_client: Optional[Any] = None) -> CacheManager:
    """Initialize cache with optional Redis client"""
    global _cache_instance
    _cache_instance = CacheManager(redis_client)
    return _cache_instance
