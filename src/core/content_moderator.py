"""
Content moderation service for the Kroolo AI Bot.
Handles safety checks, toxicity detection, and content filtering.
"""

import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI not available. Content moderation will be limited.")

from config.settings import settings

logger = logging.getLogger(__name__)


class ContentModerator:
    """Service for content moderation and safety checks."""
    
    def __init__(self):
        self.moderation_levels = {
            'light': 0.7,      # More permissive
            'standard': 0.8,   # Default moderation
            'strict': 0.9      # Very strict
        }
        
        # Content categories to check
        self.safety_categories = [
            'hate', 'harassment', 'self_harm', 'sexual', 'violence', 'drugs'
        ]
        
        # Blocked patterns and keywords
        self.blocked_patterns = [
            r'\b(kill|murder|suicide|bomb|terrorist)\b',
            r'\b(hate|racist|sexist|homophobic)\b',
            r'\b(drugs|cocaine|heroin|meth)\b',
            r'\b(porn|sex|nude|explicit)\b'
        ]
        
        # Warning patterns (less severe)
        self.warning_patterns = [
            r'\b(damn|hell|shit|fuck)\b',
            r'\b(stupid|idiot|moron)\b',
            r'\b(fight|attack|hurt)\b'
        ]
        
        # OpenAI client for AI-powered moderation
        self.openai_client = None
        if OPENAI_AVAILABLE and settings.openai_api_key:
            openai.api_key = settings.openai_api_key
            self.openai_client = openai
        
        # Moderation cache
        self.moderation_cache = {}
        self.cache_size_limit = 1000
        
        # Moderation statistics
        self.moderation_stats = {
            'total_checked': 0,
            'blocked': 0,
            'warned': 0,
            'passed': 0,
            'errors': 0
        }
        
        logger.info("Content moderator initialized")
    
    async def moderate_content(self, content: str, content_type: str = "text",
                             user_id: Optional[int] = None, 
                             chat_id: Optional[int] = None,
                             moderation_level: str = "standard") -> Dict[str, Any]:
        """
        Moderate content for safety and compliance.
        
        Args:
            content: Content to moderate
            content_type: Type of content (text, image, etc.)
            user_id: ID of the user who created the content
            chat_id: ID of the chat where content was posted
            moderation_level: Moderation strictness level
            
        Returns:
            Moderation result with decision and details
        """
        try:
            # Check cache first
            content_hash = self._hash_content(content)
            if content_hash in self.moderation_cache:
                cached_result = self.moderation_cache[content_hash]
                # Update timestamp for cache management
                cached_result['cached'] = True
                cached_result['timestamp'] = datetime.now().isoformat()
                return cached_result
            
            # Update statistics
            self.moderation_stats['total_checked'] += 1
            
            # Perform moderation checks
            result = await self._perform_moderation_checks(
                content, content_type, user_id, chat_id, moderation_level
            )
            
            # Cache result
            if len(self.moderation_cache) < self.cache_size_limit:
                self.moderation_cache[content_hash] = result.copy()
            
            # Update statistics based on result
            if result['decision'] == 'blocked':
                self.moderation_stats['blocked'] += 1
            elif result['decision'] == 'warned':
                self.moderation_stats['warned'] += 1
            else:
                self.moderation_stats['passed'] += 1
            
            logger.info(f"Content moderation completed: {result['decision']} for {content_type}")
            return result
            
        except Exception as e:
            logger.error(f"Content moderation failed: {e}")
            self.moderation_stats['errors'] += 1
            
            # Return safe fallback
            return {
                'decision': 'error',
                'reason': 'Moderation system error',
                'details': str(e),
                'timestamp': datetime.now().isoformat(),
                'content_type': content_type,
                'user_id': user_id,
                'chat_id': chat_id
            }
    
    async def _perform_moderation_checks(self, content: str, content_type: str,
                                       user_id: Optional[int], chat_id: Optional[int],
                                       moderation_level: str) -> Dict[str, Any]:
        """Perform all moderation checks."""
        # Initialize result
        result = {
            'decision': 'passed',
            'reason': 'Content passed all checks',
            'details': [],
            'flags': [],
            'risk_score': 0.0,
            'timestamp': datetime.now().isoformat(),
            'content_type': content_type,
            'user_id': user_id,
            'chat_id': chat_id,
            'moderation_level': moderation_level
        }
        
        # 1. Pattern-based checks
        pattern_result = self._check_patterns(content)
        if pattern_result['blocked']:
            result['decision'] = 'blocked'
            result['reason'] = 'Content contains blocked patterns'
            result['details'].append(pattern_result['details'])
            result['flags'].extend(pattern_result['flags'])
            result['risk_score'] = 1.0
            return result
        
        if pattern_result['warned']:
            result['flags'].extend(pattern_result['flags'])
            result['risk_score'] += 0.3
        
        # 2. AI-powered moderation (if available)
        if self.openai_client:
            ai_result = await self._ai_moderation_check(content, moderation_level)
            if ai_result['decision'] == 'blocked':
                result['decision'] = 'blocked'
                result['reason'] = ai_result['reason']
                result['details'].append(ai_result['details'])
                result['flags'].extend(ai_result['flags'])
                result['risk_score'] = max(result['risk_score'], ai_result['risk_score'])
                return result
            
            result['flags'].extend(ai_result['flags'])
            result['risk_score'] = max(result['risk_score'], ai_result['risk_score'])
        
        # 3. Content-specific checks
        content_result = self._check_content_specific(content, content_type)
        result['flags'].extend(content_result['flags'])
        result['risk_score'] += content_result['risk_score']
        
        # 4. User history checks (if user_id provided)
        if user_id:
            user_result = await self._check_user_history(user_id, content)
            result['flags'].extend(user_result['flags'])
            result['risk_score'] += user_result['risk_score']
        
        # 5. Final decision based on risk score
        threshold = self.moderation_levels.get(moderation_level, 0.8)
        if result['risk_score'] >= threshold:
            if result['risk_score'] >= 0.9:
                result['decision'] = 'blocked'
                result['reason'] = 'Content exceeds safety threshold'
            else:
                result['decision'] = 'warned'
                result['reason'] = 'Content requires attention'
        
        return result
    
    def _check_patterns(self, content: str) -> Dict[str, Any]:
        """Check content against blocked and warning patterns."""
        result = {
            'blocked': False,
            'warned': False,
            'details': [],
            'flags': []
        }
        
        content_lower = content.lower()
        
        # Check blocked patterns
        for pattern in self.blocked_patterns:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            if matches:
                result['blocked'] = True
                result['details'].append(f"Blocked pattern detected: {pattern}")
                result['flags'].append(f"blocked_pattern_{pattern}")
        
        # Check warning patterns
        for pattern in self.warning_patterns:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            if matches:
                result['warned'] = True
                result['flags'].append(f"warning_pattern_{pattern}")
        
        return result
    
    async def _ai_moderation_check(self, content: str, moderation_level: str) -> Dict[str, Any]:
        """Use OpenAI's moderation API for AI-powered content checking."""
        try:
            if not self.openai_client:
                return {
                    'decision': 'passed',
                    'reason': 'AI moderation not available',
                    'details': [],
                    'flags': [],
                    'risk_score': 0.0
                }
            
            # Use OpenAI's moderation endpoint
            response = await openai.Moderation.acreate(input=content)
            
            result = {
                'decision': 'passed',
                'reason': 'AI moderation passed',
                'details': [],
                'flags': [],
                'risk_score': 0.0
            }
            
            # Check each category
            for category in self.safety_categories:
                if response.results[0].categories.get(category, False):
                    result['flags'].append(f"ai_{category}")
                    result['details'].append(f"AI detected {category} content")
                    
                    # Get category score
                    category_score = response.results[0].category_scores.get(category, 0.0)
                    result['risk_score'] = max(result['risk_score'], category_score)
            
            # Make decision based on risk score
            threshold = self.moderation_levels.get(moderation_level, 0.8)
            if result['risk_score'] >= threshold:
                result['decision'] = 'blocked'
                result['reason'] = 'AI moderation flagged content'
            
            return result
            
        except Exception as e:
            logger.error(f"AI moderation check failed: {e}")
            return {
                'decision': 'passed',
                'reason': 'AI moderation error',
                'details': [f"AI check failed: {str(e)}"],
                'flags': ['ai_error'],
                'risk_score': 0.0
            }
    
    def _check_content_specific(self, content: str, content_type: str) -> Dict[str, Any]:
        """Check content based on its specific type."""
        result = {
            'flags': [],
            'risk_score': 0.0
        }
        
        # Length checks
        if len(content) > 4096:
            result['flags'].append('content_too_long')
            result['risk_score'] += 0.1
        
        # URL checks
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, content)
        if len(urls) > 5:
            result['flags'].append('too_many_urls')
            result['risk_score'] += 0.2
        
        # Repetitive content
        words = content.split()
        if len(words) > 10:
            unique_words = set(words)
            repetition_ratio = len(unique_words) / len(words)
            if repetition_ratio < 0.3:
                result['flags'].append('repetitive_content')
                result['risk_score'] += 0.2
        
        # Content type specific checks
        if content_type == 'quiz':
            # Check for inappropriate quiz questions
            inappropriate_terms = ['kill', 'hurt', 'hate', 'racist']
            if any(term in content.lower() for term in inappropriate_terms):
                result['flags'].append('inappropriate_quiz')
                result['risk_score'] += 0.3
        
        elif content_type == 'debate':
            # Check for inflammatory debate topics
            inflammatory_terms = ['violence', 'hate', 'discrimination']
            if any(term in content.lower() for term in inflammatory_terms):
                result['flags'].append('inflammatory_debate')
                result['risk_score'] += 0.2
        
        return result
    
    async def _check_user_history(self, user_id: int, content: str) -> Dict[str, Any]:
        """Check user's moderation history."""
        result = {
            'flags': [],
            'risk_score': 0.0
        }
        
        # This would integrate with a database to check user history
        # For now, return basic result
        # In production, you'd check:
        # - Previous violations
        # - Warning count
        # - Time since last violation
        # - User reputation score
        
        return result
    
    def _hash_content(self, content: str) -> str:
        """Create a hash of content for caching."""
        import hashlib
        return hashlib.md5(content.encode()).hexdigest()
    
    async def moderate_user_message(self, message: str, user_id: int, 
                                  chat_id: int, chat_type: str = "group") -> Dict[str, Any]:
        """Moderate a user message with appropriate level based on chat type."""
        # Adjust moderation level based on chat type
        if chat_type == "private":
            moderation_level = "light"
        elif chat_type == "group":
            moderation_level = "standard"
        elif chat_type == "supergroup":
            moderation_level = "standard"
        elif chat_type == "channel":
            moderation_level = "strict"
        else:
            moderation_level = "standard"
        
        return await self.moderate_content(
            content=message,
            content_type="user_message",
            user_id=user_id,
            chat_id=chat_id,
            moderation_level=moderation_level
        )
    
    async def moderate_agent_response(self, response: str, agent_name: str,
                                    chat_id: int) -> Dict[str, Any]:
        """Moderate an AI agent's response."""
        return await self.moderate_content(
            content=response,
            content_type="agent_response",
            user_id=None,
            chat_id=chat_id,
            moderation_level="strict"  # Strict for AI responses
        )
    
    async def moderate_content_creation(self, content: str, content_type: str,
                                      creator_id: int, chat_id: int) -> Dict[str, Any]:
        """Moderate content being created by users."""
        return await self.moderate_content(
            content=content,
            content_type=content_type,
            user_id=creator_id,
            chat_id=chat_id,
            moderation_level="standard"
        )
    
    def get_moderation_stats(self) -> Dict[str, Any]:
        """Get moderation statistics."""
        return {
            'total_checked': self.moderation_stats['total_checked'],
            'blocked': self.moderation_stats['blocked'],
            'warned': self.moderation_stats['warned'],
            'passed': self.moderation_stats['passed'],
            'errors': self.moderation_stats['errors'],
            'block_rate': self.moderation_stats['blocked'] / max(self.moderation_stats['total_checked'], 1),
            'warning_rate': self.moderation_stats['warned'] / max(self.moderation_stats['total_checked'], 1),
            'cache_size': len(self.moderation_cache),
            'moderation_levels': self.moderation_levels
        }
    
    async def update_moderation_level(self, chat_id: int, new_level: str) -> bool:
        """Update moderation level for a specific chat."""
        if new_level not in self.moderation_levels:
            logger.warning(f"Invalid moderation level: {new_level}")
            return False
        
        # This would update the chat's moderation level in the database
        # For now, just log the change
        logger.info(f"Updated moderation level for chat {chat_id} to {new_level}")
        return True
    
    async def add_blocked_pattern(self, pattern: str, description: str = "") -> bool:
        """Add a new blocked pattern."""
        try:
            # Validate regex pattern
            re.compile(pattern)
            
            # Add to blocked patterns
            self.blocked_patterns.append(pattern)
            
            logger.info(f"Added blocked pattern: {pattern}")
            return True
            
        except re.error as e:
            logger.error(f"Invalid regex pattern: {pattern}, error: {e}")
            return False
    
    async def remove_blocked_pattern(self, pattern: str) -> bool:
        """Remove a blocked pattern."""
        if pattern in self.blocked_patterns:
            self.blocked_patterns.remove(pattern)
            logger.info(f"Removed blocked pattern: {pattern}")
            return True
        return False
    
    async def clear_moderation_cache(self):
        """Clear the moderation cache."""
        self.moderation_cache.clear()
        logger.info("Moderation cache cleared")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the content moderator."""
        try:
            # Test pattern compilation
            pattern_status = "healthy"
            pattern_error = None
            try:
                for pattern in self.blocked_patterns:
                    re.compile(pattern)
            except re.error as e:
                pattern_status = "unhealthy"
                pattern_error = str(e)
            
            # Test OpenAI connection if available
            openai_status = "not_available"
            openai_error = None
            if self.openai_client:
                try:
                    # Simple test with OpenAI
                    test_response = await openai.Moderation.acreate(input="test")
                    openai_status = "healthy"
                except Exception as e:
                    openai_status = "unhealthy"
                    openai_error = str(e)
            
            health_status = {
                'status': 'healthy' if pattern_status == 'healthy' else 'unhealthy',
                'pattern_checker': {
                    'status': pattern_status,
                    'error': pattern_error
                },
                'openai_moderation': {
                    'status': openai_status,
                    'error': openai_error
                },
                'cache_size': len(self.moderation_cache),
                'blocked_patterns_count': len(self.blocked_patterns),
                'warning_patterns_count': len(self.warning_patterns),
                'moderation_stats': self.get_moderation_stats()
            }
            
            return health_status
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    async def shutdown(self):
        """Shutdown the content moderator."""
        try:
            # Clear cache
            await self.clear_moderation_cache()
            logger.info("Content moderator shutdown")
        except Exception as e:
            logger.error(f"Error during content moderator shutdown: {e}")


# Global content moderator instance
content_moderator = ContentModerator()
