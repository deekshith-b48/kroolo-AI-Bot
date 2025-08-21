#!/usr/bin/env python3
"""
Database initialization script for Kroolo AI Bot.
Creates all tables and inserts default data according to Phase 5 specifications.
"""

import asyncio
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from src.database.session import init_database, get_db_session
from src.models.base import BaseEntity
from src.models.phase5_schemas import (
    Agent, ChatConfig, MessageLog, Schedule, Quiz, QuizAttempt,
    NewsArticle, Debate, DebateMessage, FunContent, KnowledgeDocument, UserProfile
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_AGENTS = [
    {
        "handle": "alanturing",
        "name": "Alan Turing",
        "persona_prompt": """You are Alan Turing, the brilliant mathematician and computer scientist. 
        You are known for your work on computation, artificial intelligence, and breaking the Enigma code. 
        Respond with intellectual curiosity, mathematical precision, and thoughtful analysis. 
        You're passionate about the nature of intelligence and computation.""",
        "capabilities": ["mathematics", "computing", "philosophy", "logic", "artificial_intelligence"],
        "guardrails": ["no_harm", "academic", "respectful", "educational"],
        "agent_type": "persona",
        "temperature": 0.7,
        "model_name": "gpt-4"
    },
    {
        "handle": "newsreporter",
        "name": "News Reporter",
        "persona_prompt": """You are a professional news reporter with expertise in technology, science, and current events. 
        You provide accurate, timely, and well-sourced information. You present news objectively, 
        cite sources, and help users understand complex topics.""",
        "capabilities": ["news", "current_events", "research", "fact_checking", "summarization"],
        "guardrails": ["factual_accuracy", "source_citation", "objective_reporting"],
        "agent_type": "news",
        "temperature": 0.3,
        "model_name": "gpt-4"
    },
    {
        "handle": "quizmaster",
        "name": "Quiz Master",
        "persona_prompt": """You are an engaging quiz master who creates fun, educational quizzes. 
        You're enthusiastic about learning and make questions that are challenging but fair. 
        You provide helpful explanations and encourage participation.""",
        "capabilities": ["quiz_generation", "education", "scoring", "explanations"],
        "guardrails": ["educational_content", "fair_questions", "encouraging"],
        "agent_type": "quiz",
        "temperature": 0.6,
        "model_name": "gpt-4"
    },
    {
        "handle": "debatebot",
        "name": "Debate Moderator",
        "persona_prompt": """You are a skilled debate moderator who facilitates thoughtful discussions. 
        You present multiple perspectives, ask probing questions, and help participants 
        engage in constructive dialogue while maintaining civility.""",
        "capabilities": ["debate_moderation", "critical_thinking", "perspective_analysis"],
        "guardrails": ["civil_discourse", "balanced_perspectives", "constructive_dialogue"],
        "agent_type": "debate",
        "temperature": 0.5,
        "model_name": "gpt-4"
    },
    {
        "handle": "funagent",
        "name": "Fun Agent",
        "persona_prompt": """You are a fun-loving, entertaining bot that brings joy and humor to conversations. 
        You share jokes, interesting facts, riddles, and stories. You're upbeat, positive, 
        and always looking to brighten someone's day.""",
        "capabilities": ["humor", "entertainment", "storytelling", "fun_facts", "riddles"],
        "guardrails": ["family_friendly", "positive_content", "respectful_humor"],
        "agent_type": "fun",
        "temperature": 0.8,
        "model_name": "gpt-4"
    }
]

DEFAULT_CHAT_CONFIG = {
    "enabled_agents": ["alanturing", "newsreporter", "quizmaster", "debatebot", "funagent"],
    "default_agent": "alanturing",
    "schedules": {},
    "moderation_policy": {
        "level": "standard",
        "auto_moderate": True,
        "escalate_threshold": 3,
        "content_filters": ["toxicity", "spam", "inappropriate"]
    },
    "feature_flags": {
        "rag_enabled": True,
        "scheduling_enabled": True,
        "debates_enabled": True,
        "quizzes_enabled": True,
        "news_enabled": True,
        "fun_enabled": True
    },
    "chat_type": "group",
    "language": "en",
    "timezone": "UTC"
}

DEFAULT_FUN_CONTENT = [
    {
        "content_type": "joke",
        "content": "Why don't scientists trust atoms? Because they make up everything!",
        "category": "science",
        "rating": 4.5,
        "tags": ["science", "chemistry", "wordplay"]
    },
    {
        "content_type": "fact",
        "content": "The human brain contains approximately 86 billion neurons, each connected to thousands of others.",
        "category": "science",
        "rating": 4.8,
        "tags": ["neuroscience", "brain", "biology"]
    },
    {
        "content_type": "riddle",
        "content": "I speak without a mouth and hear without ears. I have no body, but come alive with wind. What am I? (Answer: An echo)",
        "category": "logic",
        "rating": 4.2,
        "tags": ["logic", "riddle", "thinking"]
    },
    {
        "content_type": "fact",
        "content": "A group of flamingos is called a 'flamboyance'. They get their pink color from the shrimp and algae they eat.",
        "category": "animals",
        "rating": 4.6,
        "tags": ["animals", "nature", "biology"]
    },
    {
        "content_type": "joke",
        "content": "Why do programmers prefer dark mode? Because light attracts bugs!",
        "category": "technology",
        "rating": 4.3,
        "tags": ["programming", "technology", "humor"]
    }
]

async def create_tables():
    """Create all database tables."""
    try:
        from sqlalchemy import create_engine
        from src.models.base import BaseEntity
        
        # Create tables
        engine = create_engine(settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", ""))
        BaseEntity.metadata.create_all(engine)
        
        logger.info("✅ Database tables created successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        raise

async def insert_default_agents():
    """Insert default agents into the database."""
    try:
        async with get_db_session() as session:
            # Check if agents already exist
            existing_agents = await session.execute("SELECT COUNT(*) FROM agents")
            count = existing_agents.scalar()
            
            if count > 0:
                logger.info("Agents already exist, skipping default agent creation")
                return
            
            # Insert default agents
            for agent_data in DEFAULT_AGENTS:
                agent = Agent(
                    id=uuid.uuid4(),
                    handle=agent_data["handle"],
                    name=agent_data["name"],
                    persona_prompt=agent_data["persona_prompt"],
                    capabilities=agent_data["capabilities"],
                    guardrails=agent_data["guardrails"],
                    agent_type=agent_data["agent_type"],
                    temperature=agent_data["temperature"],
                    model_name=agent_data["model_name"],
                    enabled=True
                )
                session.add(agent)
            
            await session.commit()
            logger.info(f"✅ Inserted {len(DEFAULT_AGENTS)} default agents")
            
    except Exception as e:
        logger.error(f"❌ Failed to insert default agents: {e}")
        raise

async def insert_default_fun_content():
    """Insert default fun content into the database."""
    try:
        async with get_db_session() as session:
            # Check if fun content already exists
            existing_content = await session.execute("SELECT COUNT(*) FROM fun_content")
            count = existing_content.scalar()
            
            if count > 0:
                logger.info("Fun content already exists, skipping default content creation")
                return
            
            # Insert default fun content
            for content_data in DEFAULT_FUN_CONTENT:
                content = FunContent(
                    id=uuid.uuid4(),
                    content_type=content_data["content_type"],
                    content=content_data["content"],
                    category=content_data["category"],
                    rating=content_data["rating"],
                    tags=content_data["tags"],
                    usage_count=0,
                    likes=0,
                    dislikes=0,
                    shares=0
                )
                session.add(content)
            
            await session.commit()
            logger.info(f"✅ Inserted {len(DEFAULT_FUN_CONTENT)} default fun content items")
            
    except Exception as e:
        logger.error(f"❌ Failed to insert default fun content: {e}")
        raise

async def create_default_chat_config(chat_id: int):
    """Create default configuration for a chat."""
    try:
        async with get_db_session() as session:
            # Check if chat config already exists
            existing_config = await session.execute(
                "SELECT COUNT(*) FROM chat_configs WHERE chat_id = :chat_id",
                {"chat_id": chat_id}
            )
            count = existing_config.scalar()
            
            if count > 0:
                logger.info(f"Chat config for {chat_id} already exists")
                return
            
            # Create default chat config
            chat_config = ChatConfig(
                id=uuid.uuid4(),
                chat_id=chat_id,
                enabled_agents=DEFAULT_CHAT_CONFIG["enabled_agents"],
                schedules=DEFAULT_CHAT_CONFIG["schedules"],
                moderation_policy=DEFAULT_CHAT_CONFIG["moderation_policy"],
                feature_flags=DEFAULT_CHAT_CONFIG["feature_flags"],
                chat_type=DEFAULT_CHAT_CONFIG["chat_type"],
                language=DEFAULT_CHAT_CONFIG["language"],
                timezone=DEFAULT_CHAT_CONFIG["timezone"]
            )
            
            session.add(chat_config)
            await session.commit()
            
            logger.info(f"✅ Created default chat config for {chat_id}")
            
    except Exception as e:
        logger.error(f"❌ Failed to create default chat config: {e}")
        raise

async def run_database_initialization():
    """Run complete database initialization."""
    try:
        logger.info("🚀 Starting database initialization...")
        
        # Initialize database connection
        await init_database()
        logger.info("✅ Database connection established")
        
        # Create tables (if using SQLAlchemy create_all)
        # await create_tables()
        
        # Insert default data
        await insert_default_agents()
        await insert_default_fun_content()
        
        # Create a sample chat config (for testing)
        await create_default_chat_config(-100123456789)  # Sample group chat ID
        
        logger.info("🎉 Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_database_initialization())
