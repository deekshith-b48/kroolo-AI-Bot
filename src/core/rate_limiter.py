"""
Rate limiter service for managing request rates.
Implements token bucket algorithm for per-user, per-chat, and global rate limiting.
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    tokens_per_second: float
    bucket_size: int
    refill_time: float  # seconds


class TokenBucket:
    """Token bucket implementation for rate limiting."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens = config.bucket_size
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """Consume tokens from the bucket."""
        now = time.time()
        
        # Refill tokens based on time passed
        time_passed = now - self.last_refill
        tokens_to_add = time_passed * self.config.tokens_per_second
        
        self.tokens = min(self.config.bucket_size, self.tokens + tokens_to_add)
        self.last_refill = now
        
        # Check if we have enough tokens
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        
        return False
    
    def get_wait_time(self) -> float:
        """Get time to wait before next request."""
        if self.tokens >= 1:
            return 0.0
        
        tokens_needed = 1 - self.tokens
        return tokens_needed / self.config.tokens_per_second


class RateLimiter:
    """Rate limiter service for managing request rates."""
    
    def __init__(self):
        # Rate limit configurations
        self.user_config = RateLimitConfig(
            tokens_per_second=1.0 / (60.0 / settings.rate_limit_per_user),
            bucket_size=settings.rate_limit_per_user,
            refill_time=60.0
        )
        
        self.chat_config = RateLimitConfig(
            tokens_per_second=1.0 / (3600.0 / settings.rate_limit_per_chat),
            bucket_size=settings.rate_limit_per_chat,
            refill_time=3600.0
        )
        
        self.global_config = RateLimitConfig(
            tokens_per_second=1.0 / (3600.0 / settings.rate_limit_global),
            bucket_size=settings.rate_limit_global,
            refill_time=3600.0
        )
        
        # Bucket storage
        self.user_buckets: Dict[int, TokenBucket] = {}
        self.chat_buckets: Dict[int, TokenBucket] = {}
        self.global_bucket = TokenBucket(self.global_config)
        
        # Cleanup task
        self.cleanup_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """Initialize the rate limiter."""
        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Rate limiter initialized")
    
    async def shutdown(self):
        """Shutdown the rate limiter."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Rate limiter shutdown")
    
    async def check_rate_limit(self, message_info: Dict[str, Any]) -> bool:
        """Check if a message is within rate limits."""
        try:
            user_id = message_info.get('user_id')
            chat_id = message_info.get('chat_id')
            
            if not user_id or not chat_id:
                logger.warning("Missing user_id or chat_id for rate limiting")
                return True  # Allow if we can't identify
            
            # Check global rate limit
            if not self.global_bucket.consume():
                logger.warning("Global rate limit exceeded")
                return False
            
            # Check user rate limit
            if not await self._check_user_limit(user_id):
                logger.warning(f"User {user_id} rate limit exceeded")
                return False
            
            # Check chat rate limit
            if not await self._check_chat_limit(chat_id):
                logger.warning(f"Chat {chat_id} rate limit exceeded")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow on error
    
    async def _check_user_limit(self, user_id: int) -> bool:
        """Check user-specific rate limit."""
        if user_id not in self.user_buckets:
            self.user_buckets[user_id] = TokenBucket(self.user_config)
        
        bucket = self.user_buckets[user_id]
        return bucket.consume()
    
    async def _check_chat_limit(self, chat_id: int) -> bool:
        """Check chat-specific rate limit."""
        if chat_id not in self.chat_buckets:
            self.chat_buckets[chat_id] = TokenBucket(self.chat_config)
        
        bucket = self.chat_buckets[chat_id]
        return bucket.consume()
    
    async def get_wait_time(self, user_id: int, chat_id: int) -> Dict[str, float]:
        """Get wait times for different rate limit buckets."""
        wait_times = {}
        
        # Global wait time
        wait_times['global'] = self.global_bucket.get_wait_time()
        
        # User wait time
        if user_id in self.user_buckets:
            wait_times['user'] = self.user_buckets[user_id].get_wait_time()
        else:
            wait_times['user'] = 0.0
        
        # Chat wait time
        if chat_id in self.chat_buckets:
            wait_times['chat'] = self.chat_buckets[chat_id].get_wait_time()
        else:
            wait_times['chat'] = 0.0
        
        return wait_times
    
    async def reset_limits(self, user_id: Optional[int] = None, chat_id: Optional[int] = None):
        """Reset rate limits for specific user or chat."""
        if user_id and user_id in self.user_buckets:
            self.user_buckets[user_id] = TokenBucket(self.user_config)
            logger.info(f"Reset rate limits for user {user_id}")
        
        if chat_id and chat_id in self.chat_buckets:
            self.chat_buckets[chat_id] = TokenBucket(self.chat_config)
            logger.info(f"Reset rate limits for chat {chat_id}")
        
        if not user_id and not chat_id:
            # Reset all
            self.user_buckets.clear()
            self.chat_buckets.clear()
            self.global_bucket = TokenBucket(self.global_config)
            logger.info("Reset all rate limits")
    
    async def _cleanup_loop(self):
        """Cleanup loop to remove old buckets."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Clean up inactive user buckets (older than 24 hours)
                current_time = time.time()
                inactive_users = []
                
                for user_id, bucket in self.user_buckets.items():
                    if current_time - bucket.last_refill > 86400:  # 24 hours
                        inactive_users.append(user_id)
                
                for user_id in inactive_users:
                    del self.user_buckets[user_id]
                
                if inactive_users:
                    logger.info(f"Cleaned up {len(inactive_users)} inactive user buckets")
                
                # Clean up inactive chat buckets (older than 24 hours)
                inactive_chats = []
                
                for chat_id, bucket in self.chat_buckets.items():
                    if current_time - bucket.last_refill > 86400:  # 24 hours
                        inactive_chats.append(chat_id)
                
                for chat_id in inactive_chats:
                    del self.chat_buckets[chat_id]
                
                if inactive_chats:
                    logger.info(f"Cleaned up {len(inactive_chats)} inactive chat buckets")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        return {
            "active_user_buckets": len(self.user_buckets),
            "active_chat_buckets": len(self.chat_buckets),
            "global_tokens_remaining": self.global_bucket.tokens,
            "config": {
                "user_limit_per_minute": settings.rate_limit_per_user,
                "chat_limit_per_hour": settings.rate_limit_per_chat,
                "global_limit_per_hour": settings.rate_limit_global
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for the rate limiter."""
        try:
            stats = self.get_stats()
            return {
                "status": "healthy",
                "stats": stats,
                "cleanup_task_running": self.cleanup_task is not None and not self.cleanup_task.done()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__
            }
