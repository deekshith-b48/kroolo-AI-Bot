"""
Basic tests for Kroolo AI Bot functionality.
These tests verify that the core components can be imported and initialized.
"""

import pytest
import os
import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBasicImports:
    """Test that all core modules can be imported."""
    
    def test_import_ai_service(self):
        """Test that AI service can be imported."""
        from services.ai_service import AIService
        assert AIService is not None
    
    def test_import_auth_service(self):
        """Test that auth service can be imported."""
        from services.auth import AuthService
        assert AuthService is not None
    
    def test_import_database(self):
        """Test that database module can be imported."""
        from db import Database
        assert Database is not None
    
    def test_import_handlers(self):
        """Test that handler modules can be imported."""
        from handlers.commands import CommandHandlers
        from handlers.inline import InlineQueryHandler
        from handlers.community import CommunityHandler
        assert CommandHandlers is not None
        assert InlineQueryHandler is not None
        assert CommunityHandler is not None


class TestAIService:
    """Test AI Service functionality."""
    
    @pytest.fixture
    def ai_service(self):
        """Create an AI service instance for testing."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test_key',
            'GEMINI_API_KEY': 'test_gemini_key'
        }):
            from services.ai_service import AIService
            return AIService()
    
    def test_ai_service_initialization(self, ai_service):
        """Test AI service can be initialized."""
        assert ai_service is not None
        assert hasattr(ai_service, 'ask_ai')
        assert hasattr(ai_service, 'ask_openai')
        assert hasattr(ai_service, 'ask_gemini')
    
    def test_service_health_tracking(self, ai_service):
        """Test service health tracking."""
        health = ai_service.get_service_health()
        assert isinstance(health, dict)
        assert 'openai' in health or 'gemini' in health


class TestDatabase:
    """Test Database functionality."""
    
    @pytest.fixture
    def database(self):
        """Create a database instance for testing."""
        from db import Database
        return Database("sqlite:///./test_kroolo_bot.db")
    
    def test_database_initialization(self, database):
        """Test database can be initialized."""
        assert database is not None
        assert hasattr(database, 'get_user')
        assert hasattr(database, 'create_user')


class TestCommandHandlers:
    """Test Command Handlers functionality."""
    
    @pytest.fixture
    def command_handlers(self):
        """Create command handlers instance for testing."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test_key',
            'GEMINI_API_KEY': 'test_gemini_key'
        }):
            from services.ai_service import AIService
            from services.auth import AuthService
            from db import Database
            from handlers.commands import CommandHandlers
            
            ai_service = AIService()
            database = Database("sqlite:///./test_kroolo_bot.db")
            auth_service = AuthService(database)
            return CommandHandlers(ai_service, auth_service)
    
    def test_command_handlers_initialization(self, command_handlers):
        """Test command handlers can be initialized."""
        assert command_handlers is not None
        assert hasattr(command_handlers, 'start_command')
        assert hasattr(command_handlers, 'help_command')
        assert hasattr(command_handlers, 'ask_command')


class TestEnvironmentVariables:
    """Test environment variable handling."""
    
    def test_required_env_vars_handled(self):
        """Test that missing environment variables are handled gracefully."""
        # This should not raise an exception even without env vars
        from services.ai_service import AIService
        ai_service = AIService()
        assert ai_service is not None
    
    def test_database_url_fallback(self):
        """Test database URL fallback to default."""
        from db import Database
        # Should use default SQLite if no DATABASE_URL is set
        db = Database()
        assert db is not None


class TestUtilities:
    """Test utility functions."""
    
    def test_cache_import(self):
        """Test cache utilities can be imported."""
        from utils.cache import RedisCache, RateLimiter, CacheManager
        assert RedisCache is not None
        assert RateLimiter is not None
        assert CacheManager is not None
    
    def test_logger_import(self):
        """Test logger utilities can be imported."""
        from utils.logger import logger, log_api_call, log_user_action
        assert logger is not None
        assert log_api_call is not None
        assert log_user_action is not None


@pytest.mark.asyncio
class TestAsyncFunctionality:
    """Test async functionality."""
    
    async def test_ai_service_async_methods(self):
        """Test AI service async methods."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test_key',
            'GEMINI_API_KEY': 'test_gemini_key'
        }):
            from services.ai_service import AIService
            ai_service = AIService()
            
            # Mock the actual API calls
            with patch.object(ai_service, 'ask_ai', new_callable=AsyncMock) as mock_ask:
                mock_ask.return_value = "Test response"
                result = await ai_service.ask_ai("Test question")
                assert result == "Test response"
                mock_ask.assert_called_once_with("Test question")


class TestConfiguration:
    """Test configuration and settings."""
    
    def test_basic_configuration(self):
        """Test basic configuration loading."""
        # Test that the app can handle missing configuration gracefully
        from services.ai_service import AIService
        ai_service = AIService()
        
        # Should have default values
        assert ai_service.max_retries >= 1
        assert ai_service.max_requests_per_minute > 0
    
    def test_service_health_structure(self):
        """Test service health structure."""
        from services.ai_service import AIService
        ai_service = AIService()
        health = ai_service.get_service_health()
        
        # Should be a dictionary with service information
        assert isinstance(health, dict)
        for service_name, service_info in health.items():
            assert isinstance(service_info, dict)
            assert 'status' in service_info
            assert 'last_check' in service_info


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
