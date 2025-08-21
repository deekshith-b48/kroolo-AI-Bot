import pytest
import asyncio
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.database.session import get_db_session
from src.core.agent_manager import AgentManager
from src.core.telegram_client import TelegramClient
from src.core.rag_service import RAGService
from src.core.content_scheduler import ContentScheduler
from src.core.metrics_collector import MetricsCollector

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=None
)

TestingSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
def mock_telegram_update() -> Dict[str, Any]:
    """Mock Telegram update data."""
    return {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "from": {
                "id": 987654321,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser"
            },
            "chat": {
                "id": -100123456789,
                "type": "group",
                "title": "Test Group"
            },
            "date": 1640995200,
            "text": "/start"
        }
    }

@pytest.fixture
def mock_agent_config() -> Dict[str, Any]:
    """Mock agent configuration."""
    return {
        "name": "Test Agent",
        "handle": "test_agent",
        "persona": "A helpful test agent",
        "capabilities": ["chat", "help"],
        "guardrails": ["no_harm", "be_helpful"],
        "rate_limits": {"messages_per_minute": 10},
        "is_active": True,
        "is_default": False
    }

@pytest.fixture
def mock_telegram_client() -> TelegramClient:
    """Mock Telegram client."""
    client = MagicMock(spec=TelegramClient)
    client.send_message = AsyncMock(return_value={"message_id": 1})
    client.send_poll = AsyncMock(return_value={"poll_id": 1})
    client.edit_message = AsyncMock(return_value=True)
    client.delete_message = AsyncMock(return_value=True)
    client.answer_callback_query = AsyncMock(return_value=True)
    client.get_chat = AsyncMock(return_value={"id": 1, "type": "group"})
    client.get_me = AsyncMock(return_value={"id": 123, "username": "test_bot"})
    client.set_webhook = AsyncMock(return_value=True)
    client.delete_webhook = AsyncMock(return_value=True)
    client.health_check = AsyncMock(return_value={"status": "healthy"})
    return client

@pytest.fixture
def mock_agent_manager() -> AgentManager:
    """Mock agent manager."""
    manager = MagicMock(spec=AgentManager)
    manager.get_agent = AsyncMock(return_value=MagicMock())
    manager.get_agents_by_type = AsyncMock(return_value=[])
    manager.get_agents_by_capability = AsyncMock(return_value=[])
    manager.get_agents_by_tag = AsyncMock(return_value=[])
    manager.reload_agents = AsyncMock(return_value=True)
    manager.health_check = AsyncMock(return_value={"status": "healthy"})
    return manager

@pytest.fixture
def mock_rag_service() -> RAGService:
    """Mock RAG service."""
    service = MagicMock(spec=RAGService)
    service.add_knowledge = AsyncMock(return_value="test_id")
    service.search_knowledge = AsyncMock(return_value=[])
    service.get_context_for_agent = AsyncMock(return_value="test context")
    service.health_check = AsyncMock(return_value={"status": "healthy"})
    return service

@pytest.fixture
def mock_content_scheduler() -> ContentScheduler:
    """Mock content scheduler."""
    scheduler = MagicMock(spec=ContentScheduler)
    scheduler.schedule_content = AsyncMock(return_value="task_id")
    scheduler.cancel_scheduled_content = AsyncMock(return_value=True)
    scheduler.get_scheduled_content = AsyncMock(return_value=[])
    scheduler.health_check = AsyncMock(return_value={"status": "healthy"})
    return scheduler

@pytest.fixture
def mock_metrics_collector() -> MetricsCollector:
    """Mock metrics collector."""
    collector = MagicMock(spec=MetricsCollector)
    collector.record_message = AsyncMock()
    collector.record_agent_response = AsyncMock()
    collector.record_error = AsyncMock()
    collector.get_metrics = AsyncMock(return_value={})
    collector.health_check = AsyncMock(return_value={"status": "healthy"})
    return collector

@pytest.fixture
async def override_dependencies(
    mock_telegram_client: TelegramClient,
    mock_agent_manager: AgentManager,
    mock_rag_service: RAGService,
    mock_content_scheduler: ContentScheduler,
    mock_metrics_collector: MetricsCollector
):
    """Override dependencies for testing."""
    app.dependency_overrides[TelegramClient] = lambda: mock_telegram_client
    app.dependency_overrides[AgentManager] = lambda: mock_agent_manager
    app.dependency_overrides[RAGService] = lambda: mock_rag_service
    app.dependency_overrides[ContentScheduler] = lambda: mock_content_scheduler
    app.dependency_overrides[MetricsCollector] = lambda: mock_metrics_collector
    
    yield
    
    app.dependency_overrides.clear()

@pytest.fixture
def sample_news_article() -> Dict[str, Any]:
    """Sample news article for testing."""
    return {
        "title": "Test News Article",
        "summary": "This is a test news article for testing purposes.",
        "source": "Test Source",
        "url": "https://example.com/test",
        "published_at": "2024-01-01T00:00:00Z",
        "category": "technology",
        "sentiment": "positive",
        "embedding": [0.1, 0.2, 0.3]
    }

@pytest.fixture
def sample_quiz() -> Dict[str, Any]:
    """Sample quiz for testing."""
    return {
        "question": "What is the capital of France?",
        "options": ["London", "Berlin", "Paris", "Madrid"],
        "correct_answer": 2,
        "explanation": "Paris is the capital of France.",
        "category": "geography",
        "difficulty": "easy"
    }

@pytest.fixture
def sample_debate() -> Dict[str, Any]:
    """Sample debate for testing."""
    return {
        "topic": "Should AI be regulated?",
        "description": "A debate about AI regulation",
        "participants": ["AlanTuring", "NewsReporter"],
        "max_turns": 5,
        "current_turn": 0,
        "status": "active"
    }

@pytest.fixture
def sample_fun_content() -> Dict[str, Any]:
    """Sample fun content for testing."""
    return {
        "content_type": "joke",
        "content": "Why don't scientists trust atoms? Because they make up everything!",
        "category": "science",
        "rating": 4.5,
        "usage_count": 10
    }
