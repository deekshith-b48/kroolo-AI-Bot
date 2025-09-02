"""
Simple tests for Kroolo AI Bot that don't require complex dependencies.
These tests verify basic functionality without external services.
"""

import pytest
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBasicFunctionality:
    """Test basic functionality without complex dependencies."""
    
    def test_python_version(self):
        """Test that we're running a supported Python version."""
        assert sys.version_info >= (3, 8), "Python 3.8+ required"
    
    def test_project_structure(self):
        """Test that required project files exist."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Check for main files
        assert os.path.exists(os.path.join(project_root, "kroolo_bot.py"))
        assert os.path.exists(os.path.join(project_root, "requirements.txt"))
        assert os.path.exists(os.path.join(project_root, "README.md"))
        
        # Check for directories
        assert os.path.isdir(os.path.join(project_root, "services"))
        assert os.path.isdir(os.path.join(project_root, "handlers"))
        assert os.path.exists(os.path.join(project_root, "utils"))


class TestEnvironmentHandling:
    """Test environment variable handling."""
    
    def test_env_vars_not_required_for_import(self):
        """Test that modules can be imported without env vars."""
        # This should not raise an exception even without env vars
        try:
            from services.ai_service import AIService
            assert AIService is not None
        except ImportError as e:
            pytest.fail(f"Failed to import AIService: {e}")
    
    def test_database_module_import(self):
        """Test database module import."""
        try:
            from db import Database
            assert Database is not None
        except ImportError as e:
            pytest.fail(f"Failed to import Database: {e}")


class TestUtilityModules:
    """Test utility modules can be imported."""
    
    def test_logger_import(self):
        """Test logger utilities import."""
        try:
            from utils.logger import logger
            assert logger is not None
        except ImportError as e:
            pytest.fail(f"Failed to import logger: {e}")
    
    def test_cache_import(self):
        """Test cache utilities import."""
        try:
            from utils.cache import RedisCache
            assert RedisCache is not None
        except ImportError as e:
            pytest.fail(f"Failed to import RedisCache: {e}")


class TestHandlerModules:
    """Test handler modules can be imported."""
    
    def test_commands_import(self):
        """Test commands handler import."""
        try:
            from handlers.commands import CommandHandlers
            assert CommandHandlers is not None
        except ImportError as e:
            pytest.fail(f"Failed to import CommandHandlers: {e}")
    
    def test_inline_import(self):
        """Test inline handler import."""
        try:
            from handlers.inline import InlineQueryHandler
            assert InlineQueryHandler is not None
        except ImportError as e:
            pytest.fail(f"Failed to import InlineQueryHandler: {e}")


class TestServiceModules:
    """Test service modules can be imported."""
    
    def test_ai_service_import(self):
        """Test AI service import."""
        try:
            from services.ai_service import AIService
            assert AIService is not None
        except ImportError as e:
            pytest.fail(f"Failed to import AIService: {e}")
    
    def test_auth_service_import(self):
        """Test auth service import."""
        try:
            from services.auth import AuthService
            assert AuthService is not None
        except ImportError as e:
            pytest.fail(f"Failed to import AuthService: {e}")


class TestConfigurationLoading:
    """Test configuration loading with fallbacks."""
    
    def test_ai_service_initialization_without_keys(self):
        """Test AI service can be initialized without API keys."""
        # Temporarily remove any API keys
        old_openai_key = os.environ.get('OPENAI_API_KEY')
        old_gemini_key = os.environ.get('GEMINI_API_KEY')
        
        # Remove keys if they exist
        if 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']
        if 'GEMINI_API_KEY' in os.environ:
            del os.environ['GEMINI_API_KEY']
        
        try:
            from services.ai_service import AIService
            ai_service = AIService()
            assert ai_service is not None
            assert hasattr(ai_service, 'ask_ai')
        except Exception as e:
            pytest.fail(f"AI service should initialize without API keys: {e}")
        finally:
            # Restore keys
            if old_openai_key:
                os.environ['OPENAI_API_KEY'] = old_openai_key
            if old_gemini_key:
                os.environ['GEMINI_API_KEY'] = old_gemini_key
    
    def test_database_initialization_with_default_url(self):
        """Test database can be initialized with default URL."""
        try:
            from db import Database
            # Should work with test SQLite URL
            db = Database("sqlite:///./test_kroolo_bot.db")
            assert db is not None
        except Exception as e:
            pytest.fail(f"Database should initialize with test URL: {e}")


class TestBasicMethods:
    """Test basic method existence without execution."""
    
    def test_ai_service_methods_exist(self):
        """Test AI service has expected methods."""
        from services.ai_service import AIService
        ai_service = AIService()
        
        # Check methods exist
        assert hasattr(ai_service, 'ask_ai')
        assert hasattr(ai_service, 'ask_openai')
        assert hasattr(ai_service, 'ask_gemini')
        assert hasattr(ai_service, 'get_service_health')
        assert callable(ai_service.ask_ai)
    
    def test_command_handlers_methods_exist(self):
        """Test command handlers have expected methods."""
        from services.ai_service import AIService
        from services.auth import AuthService
        from db import Database
        from handlers.commands import CommandHandlers
        
        # Create minimal instances
        ai_service = AIService()
        database = Database("sqlite:///./test_kroolo_bot.db")
        auth_service = AuthService(database)
        command_handlers = CommandHandlers(ai_service, auth_service)
        
        # Check methods exist
        assert hasattr(command_handlers, 'start_command')
        assert hasattr(command_handlers, 'help_command')
        assert hasattr(command_handlers, 'ask_command')
        assert callable(command_handlers.start_command)


class TestHealthChecks:
    """Test basic health check functionality."""
    
    def test_ai_service_health_structure(self):
        """Test AI service health check returns proper structure."""
        from services.ai_service import AIService
        ai_service = AIService()
        
        health = ai_service.get_service_health()
        assert isinstance(health, dict)
        
        # Should have service information
        for service_name, service_info in health.items():
            assert isinstance(service_info, dict)
            assert 'status' in service_info
            assert 'last_check' in service_info


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
