"""
Redis cache utility for Kroolo Agent Bot
Handles caching and rate limiting
"""

import json
import logging
import time
from typing import Optional, Any, Dict
import redis
import aioredis

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis_client = None
        self.aioredis_client = None
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    async def _init_aioredis(self):
        """Initialize async Redis connection"""
        try:
            self.aioredis_client = aioredis.from_url(self.redis_url, decode_responses=True)
            await self.aioredis_client.ping()
            logger.info("Async Redis connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to async Redis: {e}")
            self.aioredis_client = None
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Failed to get from cache: {e}")
            return None
    
    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set value in cache with expiration"""
        if not self.redis_client:
            return False
        
        try:
            serialized_value = json.dumps(value)
            self.redis_client.setex(key, expire, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Failed to set cache: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete from cache: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Failed to check cache existence: {e}")
            return False
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter in cache"""
        if not self.redis_client:
            return None
        
        try:
            return self.redis_client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Failed to increment cache: {e}")
            return None
    
    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for key"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.expire(key, seconds))
        except Exception as e:
            logger.error(f"Failed to set expiration: {e}")
            return False

class RateLimiter:
    """Rate limiter using Redis with token bucket algorithm"""
    
    def __init__(self, redis_cache: RedisCache):
        self.cache = redis_cache
        self.default_limits = {
            "user": 10,      # 10 requests per minute per user
            "chat": 50,      # 50 requests per minute per chat
            "global": 1000   # 1000 requests per minute globally
        }
    
    def check_rate_limit(self, key: str, limit: int, window: int = 60) -> bool:
        """
        Check if rate limit is exceeded
        Returns True if request is allowed, False if rate limited
        """
        current_time = int(time.time())
        bucket_key = f"rate_limit:{key}:{current_time // window}"
        
        try:
            # Get current count
            current_count = self.cache.get(bucket_key) or 0
            
            if current_count >= limit:
                return False
            
            # Increment counter
            self.cache.increment(bucket_key, 1)
            self.cache.expire(bucket_key, window)
            
            return True
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True  # Allow request if rate limiting fails
    
    def check_user_rate_limit(self, user_id: int) -> bool:
        """Check rate limit for specific user"""
        return self.check_rate_limit(f"user:{user_id}", self.default_limits["user"])
    
    def check_chat_rate_limit(self, chat_id: int) -> bool:
        """Check rate limit for specific chat"""
        return self.check_rate_limit(f"chat:{chat_id}", self.default_limits["chat"])
    
    def check_global_rate_limit(self) -> bool:
        """Check global rate limit"""
        return self.check_rate_limit("global", self.default_limits["global"])
    
    def is_rate_limited(self, user_id: int, chat_id: int) -> bool:
        """Check all applicable rate limits"""
        # Check global first
        if not self.check_global_rate_limit():
            return True
        
        # Check chat limit
        if not self.check_chat_rate_limit(chat_id):
            return True
        
        # Check user limit
        if not self.check_user_rate_limit(user_id):
            return True
        
        return False
    
    def get_rate_limit_info(self, user_id: int, chat_id: int) -> Dict[str, Any]:
        """Get current rate limit status"""
        current_time = int(time.time())
        window = 60
        
        user_key = f"rate_limit:user:{user_id}:{current_time // window}"
        chat_key = f"rate_limit:chat:{chat_id}:{current_time // window}"
        global_key = f"rate_limit:global:{current_time // window}"
        
        return {
            "user": {
                "current": self.cache.get(user_key) or 0,
                "limit": self.default_limits["user"],
                "remaining": max(0, self.default_limits["user"] - (self.cache.get(user_key) or 0))
            },
            "chat": {
                "current": self.cache.get(chat_key) or 0,
                "limit": self.default_limits["chat"],
                "remaining": max(0, self.default_limits["chat"] - (self.cache.get(chat_key) or 0))
            },
            "global": {
                "current": self.cache.get(global_key) or 0,
                "limit": self.default_limits["global"],
                "remaining": max(0, self.default_limits["global"] - (self.cache.get(global_key) or 0))
            }
        }

class CacheManager:
    """High-level cache manager for common bot operations"""
    
    def __init__(self, redis_cache: RedisCache):
        self.cache = redis_cache
        self.default_ttl = 3600  # 1 hour
    
    def cache_user_data(self, user_id: int, data: Dict[str, Any], ttl: int = None) -> bool:
        """Cache user data"""
        key = f"user:{user_id}"
        return self.cache.set(key, data, ttl or self.default_ttl)
    
    def get_cached_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get cached user data"""
        key = f"user:{user_id}"
        return self.cache.get(key)
    
    def cache_community_settings(self, chat_id: int, settings: Dict[str, Any], ttl: int = None) -> bool:
        """Cache community settings"""
        key = f"community:{chat_id}:settings"
        return self.cache.set(key, settings, ttl or self.default_ttl)
    
    def get_cached_community_settings(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get cached community settings"""
        key = f"community:{chat_id}:settings"
        return self.cache.get(key)
    
    def cache_ai_response(self, query_hash: str, response: str, ttl: int = 1800) -> bool:
        """Cache AI responses to avoid repeated API calls"""
        key = f"ai_response:{query_hash}"
        return self.cache.set(key, response, ttl)
    
    def get_cached_ai_response(self, query_hash: str) -> Optional[str]:
        """Get cached AI response"""
        key = f"ai_response:{query_hash}"
        return self.cache.get(key)
    
    def invalidate_user_cache(self, user_id: int) -> bool:
        """Invalidate user-related cache"""
        key = f"user:{user_id}"
        return self.cache.delete(key)
    
    def invalidate_community_cache(self, chat_id: int) -> bool:
        """Invalidate community-related cache"""
        pattern = f"community:{chat_id}:*"
        # Note: Redis doesn't support pattern deletion, so we'd need to implement this differently
        # For now, just delete the settings
        return self.cache.delete(f"community:{chat_id}:settings")
