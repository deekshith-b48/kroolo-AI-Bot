import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.agents.base_agent import BaseAgent
from src.agents.persona_agent import PersonaAgent
from src.agents.news_agent import NewsAgent
from src.agents.quiz_agent import QuizAgent
from src.agents.debate_agent import DebateAgent
from src.agents.fun_agent import FunAgent

class TestBaseAgent:
    """Test base agent functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock agent configuration."""
        return MagicMock(
            name="Test Agent",
            handle="test_agent",
            persona="A helpful test agent",
            capabilities=["chat", "help"],
            guardrails=["no_harm", "be_helpful"],
            rate_limits={"messages_per_minute": 10},
            is_active=True
        )
    
    @pytest.fixture
    def mock_telegram_client(self):
        """Mock Telegram client."""
        client = MagicMock()
        client.send_message = AsyncMock(return_value={"message_id": 1})
        return client
    
    def test_base_agent_initialization(self, mock_config):
        """Test base agent initialization."""
        agent = BaseAgent(mock_config)
        assert agent.config == mock_config
        assert agent.agent_type == "base"
        assert agent.is_active == True
    
    @pytest.mark.asyncio
    async def test_base_agent_process_message(self, mock_config, mock_telegram_client):
        """Test base agent message processing."""
        agent = BaseAgent(mock_config)
        
        message_info = {
            "message_id": 1,
            "chat_id": 123,
            "user_id": 456,
            "text": "Hello",
            "chat_type": "private"
        }
        
        agent_context = {
            "user_history": [],
            "chat_context": [],
            "agent_memory": {}
        }
        
        # Mock the abstract method
        with patch.object(agent, '_generate_response', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "Hello! How can I help you?"
            
            result = await agent.process_message(message_info, agent_context)
            
            assert result["success"] == True
            assert "response" in result
    
    @pytest.mark.asyncio
    async def test_base_agent_safety_checks(self, mock_config, mock_telegram_client):
        """Test base agent safety checks."""
        agent = BaseAgent(mock_config)
        
        # Test with safe message
        safe_message = "Hello, how are you?"
        assert await agent._check_safety(safe_message) == True
        
        # Test with potentially unsafe message
        unsafe_message = "How to harm someone?"
        assert await agent._check_safety(unsafe_message) == False
    
    @pytest.mark.asyncio
    async def test_base_agent_health_check(self, mock_config):
        """Test base agent health check."""
        agent = BaseAgent(mock_config)
        health = await agent.health_check()
        
        assert health["status"] == "healthy"
        assert health["agent_type"] == "base"
        assert health["is_active"] == True

class TestPersonaAgent:
    """Test persona agent functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock persona agent configuration."""
        return MagicMock(
            name="Alan Turing",
            handle="alanturing",
            persona="A brilliant mathematician and computer scientist",
            capabilities=["chat", "math", "computing"],
            guardrails=["no_harm", "be_helpful", "academic"],
            openai_temperature=0.7,
            openai_model="gpt-4",
            max_tokens_per_response=2000
        )
    
    @pytest.mark.asyncio
    async def test_persona_agent_initialization(self, mock_config):
        """Test persona agent initialization."""
        with patch('src.agents.persona_agent.openai') as mock_openai:
            agent = PersonaAgent(mock_config)
            
            assert agent.config == mock_config
            assert agent.agent_type == "persona"
            assert agent.temperature == 0.7
            assert agent.model == "gpt-4"
    
    @pytest.mark.asyncio
    async def test_persona_agent_response_generation(self, mock_config):
        """Test persona agent response generation."""
        with patch('src.agents.persona_agent.openai') as mock_openai:
            agent = PersonaAgent(mock_config)
            
            message_info = {
                "text": "What is the Turing Test?",
                "user_id": 123,
                "chat_id": 456
            }
            
            agent_context = {
                "user_history": [],
                "chat_context": [],
                "agent_memory": {}
            }
            
            # Mock OpenAI response
            mock_openai.ChatCompletion.acreate.return_value = {
                "choices": [{"message": {"content": "The Turing Test is a method..."}}]
            }
            
            response = await agent._generate_response(message_info, agent_context)
            
            assert "Turing Test" in response
            assert mock_openai.ChatCompletion.acreate.called
    
    @pytest.mark.asyncio
    async def test_persona_agent_prompt_building(self, mock_config):
        """Test persona agent prompt building."""
        with patch('src.agents.persona_agent.openai'):
            agent = PersonaAgent(mock_config)
            
            user_message = "Tell me about computers"
            agent_context = {
                "user_history": ["Previous message"],
                "chat_context": ["Chat context"],
                "agent_memory": {"key": "value"}
            }
            
            prompt = agent._build_prompt(user_message, agent_context)
            
            assert "Alan Turing" in prompt
            assert "computers" in prompt
            assert "Previous message" in prompt

class TestNewsAgent:
    """Test news agent functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock news agent configuration."""
        return MagicMock(
            name="News Reporter",
            handle="newsreporter",
            persona="A professional news reporter",
            capabilities=["news", "updates", "summaries"],
            rss_feeds=["https://example.com/feed1", "https://example.com/feed2"],
            cache_duration=1800
        )
    
    @pytest.mark.asyncio
    async def test_news_agent_initialization(self, mock_config):
        """Test news agent initialization."""
        agent = NewsAgent(mock_config)
        
        assert agent.agent_type == "news"
        assert len(agent.rss_feeds) == 2
        assert agent.cache_duration.total_seconds() == 1800
    
    @pytest.mark.asyncio
    async def test_news_agent_fetch_news(self, mock_config):
        """Test news agent news fetching."""
        with patch('src.agents.news_agent.aiohttp.ClientSession') as mock_session, \
             patch('src.agents.news_agent.feedparser') as mock_feedparser:
            
            agent = NewsAgent(mock_config)
            
            # Mock RSS feed response
            mock_feedparser.parse.return_value = {
                "entries": [
                    {
                        "title": "Test News",
                        "summary": "Test summary",
                        "link": "https://example.com/news1",
                        "published": "2024-01-01T00:00:00Z"
                    }
                ]
            }
            
            news = await agent._fetch_news()
            
            assert len(news) == 2  # 2 feeds
            assert "Test News" in [item["title"] for item in news[0]]
    
    @pytest.mark.asyncio
    async def test_news_agent_response_generation(self, mock_config):
        """Test news agent response generation."""
        agent = NewsAgent(mock_config)
        
        message_info = {
            "text": "Show me the latest news",
            "user_id": 123,
            "chat_id": 456
        }
        
        agent_context = {
            "user_history": [],
            "chat_context": [],
            "agent_memory": {}
        }
        
        with patch.object(agent, '_fetch_news', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [
                [{"title": "Test News", "summary": "Test summary", "source": "Test Source"}]
            ]
            
            response = await agent._generate_response(message_info, agent_context)
            
            assert "Test News" in response
            assert "Test summary" in response

class TestQuizAgent:
    """Test quiz agent functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock quiz agent configuration."""
        return MagicMock(
            name="Quiz Master",
            handle="quizmaster",
            persona="An engaging quiz master",
            capabilities=["quiz", "questions", "scoring"],
            question_bank_size=100,
            max_quiz_duration=300
        )
    
    @pytest.mark.asyncio
    async def test_quiz_agent_initialization(self, mock_config):
        """Test quiz agent initialization."""
        agent = QuizAgent(mock_config)
        
        assert agent.agent_type == "quiz"
        assert len(agent.question_bank) > 0
        assert len(agent.active_quizzes) == 0
    
    @pytest.mark.asyncio
    async def test_quiz_agent_start_quiz(self, mock_config):
        """Test quiz agent starting a new quiz."""
        agent = QuizAgent(mock_config)
        
        chat_id = 123
        user_id = 456
        
        response = await agent._start_new_quiz(chat_id, user_id)
        
        assert "quiz" in response.lower()
        assert chat_id in agent.active_quizzes
        assert agent.active_quizzes[chat_id]["user_id"] == user_id
    
    @pytest.mark.asyncio
    async def test_quiz_agent_process_answer(self, mock_config):
        """Test quiz agent processing answers."""
        agent = QuizAgent(mock_config)
        
        # Start a quiz first
        chat_id = 123
        user_id = 456
        await agent._start_new_quiz(chat_id, user_id)
        
        # Process answer
        response = await agent._process_answer(chat_id, user_id, "Paris")
        
        assert "answer" in response.lower() or "correct" in response.lower() or "incorrect" in response.lower()

class TestDebateAgent:
    """Test debate agent functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock debate agent configuration."""
        return MagicMock(
            name="Debate Bot",
            handle="debatebot",
            persona="A skilled debate moderator",
            capabilities=["debate", "moderation", "discussion"],
            debate_topics=["AI Ethics", "Climate Change", "Education"],
            max_debate_duration=1800
        )
    
    @pytest.mark.asyncio
    async def test_debate_agent_initialization(self, mock_config):
        """Test debate agent initialization."""
        agent = DebateAgent(mock_config)
        
        assert agent.agent_type == "debate"
        assert len(agent.debate_topics) == 3
        assert len(agent.active_debates) == 0
    
    @pytest.mark.asyncio
    async def test_debate_agent_start_debate(self, mock_config):
        """Test debate agent starting a new debate."""
        agent = DebateAgent(mock_config)
        
        chat_id = 123
        user_id = 456
        
        response = await agent._start_new_debate(chat_id, user_id)
        
        assert "debate" in response.lower()
        assert chat_id in agent.active_debates
        assert agent.active_debates[chat_id]["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_debate_agent_run_debate(self, mock_config):
        """Test debate agent running a debate."""
        agent = DebateAgent(mock_config)
        
        # Start a debate first
        chat_id = 123
        user_id = 456
        await agent._start_new_debate(chat_id, user_id)
        
        # Run debate
        with patch.object(agent, '_send_debate_message', new_callable=AsyncMock) as mock_send:
            await agent._run_debate(chat_id)
            
            # Should send at least one message
            assert mock_send.called

class TestFunAgent:
    """Test fun agent functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock fun agent configuration."""
        return MagicMock(
            name="Fun Agent",
            handle="funagent",
            persona="An entertaining and fun-loving bot",
            capabilities=["jokes", "facts", "riddles", "stories"],
            content_types=["joke", "fact", "riddle", "story"],
            daily_usage_limit=10
        )
    
    @pytest.mark.asyncio
    async def test_fun_agent_initialization(self, mock_config):
        """Test fun agent initialization."""
        agent = FunAgent(mock_config)
        
        assert agent.agent_type == "fun"
        assert len(agent.content_types) == 4
        assert len(agent.content_database) > 0
    
    @pytest.mark.asyncio
    async def test_fun_agent_content_generation(self, mock_config):
        """Test fun agent content generation."""
        agent = FunAgent(mock_config)
        
        message_info = {
            "text": "Tell me a joke",
            "user_id": 123,
            "chat_id": 456
        }
        
        agent_context = {
            "user_history": [],
            "chat_context": [],
            "agent_memory": {}
        }
        
        response = await agent._generate_response(message_info, agent_context)
        
        assert "joke" in response.lower() or "funny" in response.lower()
    
    @pytest.mark.asyncio
    async def test_fun_agent_rate_limiting(self, mock_config):
        """Test fun agent rate limiting."""
        agent = FunAgent(mock_config)
        
        chat_id = 123
        
        # Should be able to use content initially
        assert await agent._can_use_content(chat_id) == True
        
        # Simulate multiple uses
        for i in range(15):  # Exceed daily limit
            agent.daily_usage[chat_id] = i
        
        # Should be rate limited
        assert await agent._can_use_content(chat_id) == False

class TestAgentIntegration:
    """Test agent integration and interaction."""
    
    @pytest.mark.asyncio
    async def test_agent_chain_processing(self):
        """Test multiple agents working together."""
        # This would test how agents can work together
        # For example, news agent providing context to persona agent
        pass
    
    @pytest.mark.asyncio
    async def test_agent_context_sharing(self):
        """Test agents sharing context and memory."""
        # This would test context sharing between agents
        pass
    
    @pytest.mark.asyncio
    async def test_agent_fallback_mechanism(self):
        """Test agent fallback when primary agent fails."""
        # This would test fallback mechanisms
        pass

class TestAgentPerformance:
    """Test agent performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_agent_response_time(self):
        """Test agent response time performance."""
        # This would test response time performance
        pass
    
    @pytest.mark.asyncio
    async def test_agent_memory_usage(self):
        """Test agent memory usage."""
        # This would test memory usage
        pass
    
    @pytest.mark.asyncio
    async def test_agent_concurrent_processing(self):
        """Test agent concurrent processing capability."""
        # This would test concurrent processing
        pass
