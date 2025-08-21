import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.core.rate_limiter import RateLimiter, RateLimitConfig, TokenBucket
from src.core.security import SecurityManager, sanitize_input, validate_telegram_id
from src.core.intent_classifier import IntentClassifier, Intent
from src.core.rag_service import RAGService

class TestRateLimiter:
    """Test rate limiter functionality."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter instance."""
        return RateLimiter()
    
    @pytest.fixture
    def token_bucket(self):
        """Create a token bucket instance."""
        config = RateLimitConfig(
            tokens_per_second=1.0,
            bucket_size=10,
            refill_time=1.0
        )
        return TokenBucket(config)
    
    def test_token_bucket_initialization(self, token_bucket):
        """Test token bucket initialization."""
        assert token_bucket.tokens == 10
        assert token_bucket.config.bucket_size == 10
        assert token_bucket.config.tokens_per_second == 1.0
    
    def test_token_bucket_consume(self, token_bucket):
        """Test token consumption."""
        # Should be able to consume tokens initially
        assert token_bucket.consume(5) == True
        assert token_bucket.tokens == 5
        
        # Should be able to consume more
        assert token_bucket.consume(3) == True
        assert token_bucket.tokens == 2
        
        # Should not be able to consume more than available
        assert token_bucket.consume(5) == False
        assert token_bucket.tokens == 2
    
    def test_token_bucket_refill(self, token_bucket):
        """Test token bucket refill."""
        # Consume all tokens
        token_bucket.consume(10)
        assert token_bucket.tokens == 0
        
        # Wait for refill
        time.sleep(1.1)
        
        # Should have refilled
        assert token_bucket.tokens > 0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_initialization(self, rate_limiter):
        """Test rate limiter initialization."""
        await rate_limiter.initialize()
        
        # Should have default configs
        assert "user" in rate_limiter.user_buckets
        assert "chat" in rate_limiter.chat_buckets
        assert "global" in rate_limiter.global_buckets
    
    @pytest.mark.asyncio
    async def test_rate_limiter_check_rate_limit(self, rate_limiter):
        """Test rate limit checking."""
        await rate_limiter.initialize()
        
        message_info = {
            "user_id": 123,
            "chat_id": 456,
            "message_type": "text"
        }
        
        # First message should pass
        assert await rate_limiter.check_rate_limit(message_info) == True
        
        # Rapid messages should be rate limited
        for _ in range(20):
            await rate_limiter.check_rate_limit(message_info)
        
        # Should be rate limited now
        assert await rate_limiter.check_rate_limit(message_info) == False
    
    @pytest.mark.asyncio
    async def test_rate_limiter_health_check(self, rate_limiter):
        """Test rate limiter health check."""
        await rate_limiter.initialize()
        
        health = await rate_limiter.health_check()
        
        assert health["status"] == "healthy"
        assert "user_buckets" in health
        assert "chat_buckets" in health
        assert "global_buckets" in health

class TestSecurityManager:
    """Test security manager functionality."""
    
    @pytest.fixture
    def security_manager(self):
        """Create a security manager instance."""
        return SecurityManager()
    
    def test_security_manager_initialization(self, security_manager):
        """Test security manager initialization."""
        assert len(security_manager.blocked_ips) == 0
        assert len(security_manager.suspicious_activities) == 0
        assert len(security_manager.rate_limit_violations) == 0
    
    def test_ip_blocking(self, security_manager):
        """Test IP blocking functionality."""
        ip = "192.168.1.1"
        reason = "Suspicious activity"
        
        security_manager.block_ip(ip, reason)
        
        assert ip in security_manager.blocked_ips
        assert security_manager.blocked_ips[ip]["reason"] == reason
        assert "timestamp" in security_manager.blocked_ips[ip]
    
    def test_suspicious_activity_tracking(self, security_manager):
        """Test suspicious activity tracking."""
        ip = "192.168.1.2"
        activity = "Multiple failed login attempts"
        
        security_manager.record_suspicious_activity(ip, activity)
        
        assert len(security_manager.suspicious_activities) == 1
        assert security_manager.suspicious_activities[0]["ip"] == ip
        assert security_manager.suspicious_activities[0]["activity"] == activity
    
    def test_rate_limit_violation_tracking(self, security_manager):
        """Test rate limit violation tracking."""
        ip = "192.168.1.3"
        violation_type = "message_spam"
        
        security_manager.record_rate_limit_violation(ip, violation_type)
        
        assert ip in security_manager.rate_limit_violations
        assert security_manager.rate_limit_violations[ip]["type"] == violation_type
        assert "count" in security_manager.rate_limit_violations[ip]
    
    @pytest.mark.asyncio
    async def test_security_manager_health_check(self, security_manager):
        """Test security manager health check."""
        health = await security_manager.health_check()
        
        assert health["status"] == "healthy"
        assert "blocked_ips_count" in health
        assert "suspicious_activities_count" in health
        assert "rate_limit_violations_count" in health

class TestSecurityFunctions:
    """Test security utility functions."""
    
    def test_sanitize_input(self):
        """Test input sanitization."""
        from src.core.security import sanitize_input
        
        # Test normal text
        normal_text = "Hello, world!"
        assert sanitize_input(normal_text) == normal_text
        
        # Test text with HTML
        html_text = "<script>alert('xss')</script>Hello"
        sanitized = sanitize_input(html_text)
        assert "<script>" not in sanitized
        assert "Hello" in sanitized
        
        # Test text with special characters
        special_text = "Hello\n\t\r\b\f"
        sanitized = sanitize_input(special_text)
        assert "\n" not in sanitized
        assert "\t" not in sanitized
        
        # Test text length limit
        long_text = "x" * 5000
        sanitized = sanitize_input(long_text, max_length=1000)
        assert len(sanitized) <= 1000
    
    def test_validate_telegram_id(self):
        """Test Telegram ID validation."""
        from src.core.security import validate_telegram_id
        
        # Valid IDs
        assert validate_telegram_id(123456789) == True
        assert validate_telegram_id(-100123456789) == True  # Group ID
        
        # Invalid IDs
        assert validate_telegram_id("invalid") == False
        assert validate_telegram_id(0) == False
        assert validate_telegram_id(None) == False

class TestIntentClassifier:
    """Test intent classifier functionality."""
    
    @pytest.fixture
    def intent_classifier(self):
        """Create an intent classifier instance."""
        return IntentClassifier()
    
    def test_intent_classifier_initialization(self, intent_classifier):
        """Test intent classifier initialization."""
        assert len(intent_classifier.patterns) > 0
        assert len(intent_classifier.keyword_weights) > 0
        assert len(intent_classifier.context_patterns) > 0
    
    @pytest.mark.asyncio
    async def test_news_intent_classification(self, intent_classifier):
        """Test news intent classification."""
        text = "Show me the latest news"
        intent = await intent_classifier.classify_intent(text)
        
        assert intent == Intent.NEWS
    
    @pytest.mark.asyncio
    async def test_quiz_intent_classification(self, intent_classifier):
        """Test quiz intent classification."""
        text = "I want to take a quiz"
        intent = await intent_classifier.classify_intent(text)
        
        assert intent == Intent.QUIZ
    
    @pytest.mark.asyncio
    async def test_debate_intent_classification(self, intent_classifier):
        """Test debate intent classification."""
        text = "Let's have a debate about AI"
        intent = await intent_classifier.classify_intent(text)
        
        assert intent == Intent.DEBATE
    
    @pytest.mark.asyncio
    async def test_fun_intent_classification(self, intent_classifier):
        """Test fun intent classification."""
        text = "Tell me a joke"
        intent = await intent_classifier.classify_intent(text)
        
        assert intent == Intent.FUN
    
    @pytest.mark.asyncio
    async def test_help_intent_classification(self, intent_classifier):
        """Test help intent classification."""
        text = "Help me understand how to use this bot"
        intent = await intent_classifier.classify_intent(text)
        
        assert intent == Intent.HELP
    
    @pytest.mark.asyncio
    async def test_unknown_intent_classification(self, intent_classifier):
        """Test unknown intent classification."""
        text = "Random text without clear intent"
        intent = await intent_classifier.classify_intent(text)
        
        assert intent == Intent.UNKNOWN
    
    def test_rule_based_scoring(self, intent_classifier):
        """Test rule-based scoring."""
        text = "What's the latest news about technology?"
        
        scores = intent_classifier._calculate_rule_based_scores(text)
        
        assert Intent.NEWS in scores
        assert scores[Intent.NEWS] > 0
    
    @pytest.mark.asyncio
    async def test_intent_classifier_health_check(self, intent_classifier):
        """Test intent classifier health check."""
        health = await intent_classifier.health_check()
        
        assert health["status"] == "healthy"
        assert "patterns_compiled" in health
        assert "total_classifications" in health

class TestRAGService:
    """Test RAG service functionality."""
    
    @pytest.fixture
    def rag_service(self):
        """Create a RAG service instance."""
        return RAGService()
    
    @pytest.mark.asyncio
    async def test_rag_service_initialization(self, rag_service):
        """Test RAG service initialization."""
        with patch('src.core.rag_service.QDRANT_AVAILABLE', True):
            await rag_service.initialize()
            
            assert rag_service.is_initialized == True
            assert rag_service.client is not None
    
    @pytest.mark.asyncio
    async def test_add_knowledge(self, rag_service):
        """Test adding knowledge to RAG service."""
        with patch('src.core.rag_service.QDRANT_AVAILABLE', True):
            await rag_service.initialize()
            
            content = "This is a test knowledge item"
            metadata = {"type": "test", "source": "test"}
            
            knowledge_id = await rag_service.add_knowledge(content, metadata)
            
            assert knowledge_id is not None
            assert isinstance(knowledge_id, str)
    
    @pytest.mark.asyncio
    async def test_search_knowledge(self, rag_service):
        """Test searching knowledge in RAG service."""
        with patch('src.core.rag_service.QDRANT_AVAILABLE', True):
            await rag_service.initialize()
            
            query = "test knowledge"
            results = await rag_service.search_knowledge(query, limit=5)
            
            assert isinstance(results, list)
            assert len(results) <= 5
    
    @pytest.mark.asyncio
    async def test_get_context_for_agent(self, rag_service):
        """Test getting context for agent."""
        with patch('src.core.rag_service.QDRANT_AVAILABLE', True):
            await rag_service.initialize()
            
            query = "test query"
            agent_context = {"agent_type": "persona", "capabilities": ["chat"]}
            
            context = await rag_service.get_context_for_agent(query, agent_context)
            
            assert isinstance(context, str)
            assert len(context) > 0
    
    @pytest.mark.asyncio
    async def test_rag_service_health_check(self, rag_service):
        """Test RAG service health check."""
        with patch('src.core.rag_service.QDRANT_AVAILABLE', True):
            await rag_service.initialize()
            
            health = await rag_service.health_check()
            
            assert health["status"] == "healthy"
            assert "qdrant_status" in health
            assert "embedding_model_status" in health
    
    @pytest.mark.asyncio
    async def test_rag_service_without_qdrant(self, rag_service):
        """Test RAG service without Qdrant available."""
        with patch('src.core.rag_service.QDRANT_AVAILABLE', False):
            await rag_service.initialize()
            
            # Should still initialize but with limited functionality
            assert rag_service.is_initialized == True
            assert rag_service.client is None

class TestIntegration:
    """Test integration between core services."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_with_security(self):
        """Test rate limiter integration with security manager."""
        rate_limiter = RateLimiter()
        security_manager = SecurityManager()
        
        await rate_limiter.initialize()
        
        # Simulate rate limit violations
        message_info = {"user_id": 123, "chat_id": 456}
        
        for _ in range(25):  # Exceed rate limit
            await rate_limiter.check_rate_limit(message_info)
        
        # Security manager should track violations
        assert len(security_manager.rate_limit_violations) > 0
    
    @pytest.mark.asyncio
    async def test_intent_classifier_with_rag(self):
        """Test intent classifier integration with RAG service."""
        intent_classifier = IntentClassifier()
        rag_service = RAGService()
        
        with patch('src.core.rag_service.QDRANT_AVAILABLE', True):
            await rag_service.initialize()
            
            # Classify intent
            text = "What's the latest news about AI?"
            intent = await intent_classifier.classify_intent(text)
            
            # Get context from RAG
            agent_context = {"agent_type": "news", "capabilities": ["news"]}
            context = await rag_service.get_context_for_agent(text, agent_context)
            
            assert intent == Intent.NEWS
            assert isinstance(context, str)

class TestPerformance:
    """Test performance characteristics of core services."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_performance(self):
        """Test rate limiter performance."""
        rate_limiter = RateLimiter()
        await rate_limiter.initialize()
        
        import time
        
        start_time = time.time()
        
        # Process many messages quickly
        message_info = {"user_id": 123, "chat_id": 456}
        for _ in range(100):
            await rate_limiter.check_rate_limit(message_info)
        
        end_time = time.time()
        
        # Should process 100 messages quickly
        assert end_time - start_time < 1.0
    
    @pytest.mark.asyncio
    async def test_intent_classifier_performance(self):
        """Test intent classifier performance."""
        intent_classifier = IntentClassifier()
        
        import time
        
        start_time = time.time()
        
        # Classify many intents
        texts = [
            "Show me the news",
            "I want a quiz",
            "Let's debate",
            "Tell me a joke",
            "Help me"
        ] * 20  # 100 total
        
        for text in texts:
            await intent_classifier.classify_intent(text)
        
        end_time = time.time()
        
        # Should classify 100 intents quickly
        assert end_time - start_time < 2.0
