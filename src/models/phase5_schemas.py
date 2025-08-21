"""
Phase 5 Database Schemas
Complete database models implementing your Phase 5 specifications.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import (
    Column, String, Text, JSON, Boolean, Integer, 
    ForeignKey, BigInteger, TIMESTAMP, Float
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from src.models.base import BaseEntity, BasePydanticModel, PydanticTimestampMixin

# SQLAlchemy Models (Database Schema)

class Agent(BaseEntity):
    """
    Agents Table - Stores AI agent configurations and personas.
    
    Corresponds to your specification:
    CREATE TABLE agents (
      id UUID PRIMARY KEY,
      handle TEXT UNIQUE,
      name TEXT,
      persona_prompt TEXT,
      capabilities JSONB,
      guardrails JSONB,
      enabled BOOLEAN DEFAULT TRUE,
      created_at TIMESTAMPTZ DEFAULT now()
    );
    """
    __tablename__ = "agents"
    
    # Use UUID as primary key (inherited from BaseEntity as 'id')
    handle = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    persona_prompt = Column(Text, nullable=False)
    capabilities = Column(JSONB, nullable=False, default=list)
    guardrails = Column(JSONB, nullable=False, default=list)
    enabled = Column(Boolean, default=True, nullable=False)
    
    # Additional fields for enhanced functionality
    agent_type = Column(String(50), default="persona")
    version = Column(String(20), default="1.0.0")
    max_tokens_per_response = Column(Integer, default=2000)
    temperature = Column(Float, default=0.7)
    model_name = Column(String(100), default="gpt-4")
    rate_limits = Column(JSONB, default=dict)
    
    # Relationships
    chat_configs = relationship("ChatConfig", back_populates="default_agent_rel")

class ChatConfig(BaseEntity):
    """
    Chat Config Table - Stores per-chat configuration settings.
    
    Corresponds to your specification:
    CREATE TABLE chat_configs (
      chat_id BIGINT PRIMARY KEY,
      enabled_agents UUID[],
      default_agent UUID,
      schedules JSONB,
      moderation_policy JSONB
    );
    """
    __tablename__ = "chat_configs"
    
    chat_id = Column(BigInteger, unique=True, nullable=False, index=True)
    enabled_agents = Column(ARRAY(UUID(as_uuid=True)), default=list)
    default_agent = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    schedules = Column(JSONB, default=dict)
    moderation_policy = Column(JSONB, default=dict)
    
    # Additional configuration fields
    feature_flags = Column(JSONB, default=dict)
    chat_type = Column(String(20), default="group")  # private, group, supergroup, channel
    language = Column(String(10), default="en")
    timezone = Column(String(50), default="UTC")
    welcome_message = Column(Text, nullable=True)
    admin_users = Column(ARRAY(BigInteger), default=list)
    
    # Relationships
    default_agent_rel = relationship("Agent", back_populates="chat_configs")
    messages = relationship("MessageLog", back_populates="chat")
    schedules_rel = relationship("Schedule", back_populates="chat")

class MessageLog(BaseEntity):
    """
    Message Logs Table - Stores processed message history and results.
    
    Corresponds to your specification:
    CREATE TABLE message_logs (
      update_id BIGINT,
      chat_id BIGINT,
      user_id BIGINT,
      normalized_json JSONB,
      handled_by TEXT,
      result_msg_id BIGINT,
      latency_ms INT,
      status TEXT,
      PRIMARY KEY (update_id, chat_id)
    );
    """
    __tablename__ = "message_logs"
    
    update_id = Column(BigInteger, nullable=False, index=True)
    chat_id = Column(BigInteger, ForeignKey("chat_configs.chat_id"), nullable=False, index=True)
    user_id = Column(BigInteger, nullable=True, index=True)
    normalized_json = Column(JSONB, nullable=False)
    handled_by = Column(String(100), nullable=True)  # Agent handle or service name
    result_msg_id = Column(BigInteger, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    
    # Additional fields for comprehensive logging
    message_type = Column(String(50), default="text")
    intent_detected = Column(String(50), nullable=True)
    route_reason = Column(String(200), nullable=True)
    error_message = Column(Text, nullable=True)
    agent_response_time = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    cost_cents = Column(Integer, nullable=True)
    
    # Relationships
    chat = relationship("ChatConfig", back_populates="messages")
    
    # Composite primary key
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )

class Schedule(BaseEntity):
    """
    Schedule Table - Stores scheduled task configurations.
    
    Corresponds to your specification:
    CREATE TABLE schedules (
      id UUID PRIMARY KEY,
      task_type TEXT,
      cron_expr TEXT,
      chat_id BIGINT,
      params JSONB,
      enabled BOOLEAN DEFAULT TRUE
    );
    """
    __tablename__ = "schedules"
    
    task_type = Column(String(100), nullable=False)
    cron_expr = Column(String(100), nullable=True)
    chat_id = Column(BigInteger, ForeignKey("chat_configs.chat_id"), nullable=False, index=True)
    params = Column(JSONB, default=dict)
    enabled = Column(Boolean, default=True, nullable=False)
    
    # Additional scheduling fields
    schedule_type = Column(String(50), default="cron")  # cron, interval, recurring, one_time
    schedule_config = Column(JSONB, default=dict)
    content_data = Column(JSONB, default=dict)
    next_run = Column(TIMESTAMP, nullable=True)
    last_run = Column(TIMESTAMP, nullable=True)
    run_count = Column(Integer, default=0)
    max_runs = Column(Integer, nullable=True)
    failure_count = Column(Integer, default=0)
    max_failures = Column(Integer, default=3)
    
    # Relationships
    chat = relationship("ChatConfig", back_populates="schedules_rel")

class Quiz(BaseEntity):
    """
    Quiz Table - Stores quiz questions and configurations.
    
    Corresponds to your specification:
    CREATE TABLE quizzes (
      id UUID PRIMARY KEY,
      chat_id BIGINT,
      question TEXT,
      options JSONB,
      answer_idx INT,
      start_ts TIMESTAMPTZ,
      end_ts TIMESTAMPTZ,
      results JSONB
    );
    """
    __tablename__ = "quizzes"
    
    chat_id = Column(BigInteger, nullable=False, index=True)
    question = Column(Text, nullable=False)
    options = Column(JSONB, nullable=False)
    answer_idx = Column(Integer, nullable=False)
    start_ts = Column(TIMESTAMP, nullable=True)
    end_ts = Column(TIMESTAMP, nullable=True)
    results = Column(JSONB, default=dict)
    
    # Additional quiz fields
    category = Column(String(100), default="general")
    difficulty = Column(String(20), default="medium")
    explanation = Column(Text, nullable=True)
    time_limit_seconds = Column(Integer, default=60)
    max_participants = Column(Integer, default=100)
    created_by_user = Column(BigInteger, nullable=True)
    source = Column(String(100), default="generated")
    tags = Column(ARRAY(String), default=list)
    
    # Relationships
    attempts = relationship("QuizAttempt", back_populates="quiz")

class QuizAttempt(BaseEntity):
    """Quiz Attempt Table - Stores individual quiz attempts and scores."""
    __tablename__ = "quiz_attempts"
    
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id"), nullable=False)
    user_id = Column(BigInteger, nullable=False, index=True)
    chat_id = Column(BigInteger, nullable=False, index=True)
    selected_answer = Column(Integer, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    score = Column(Integer, default=0)
    
    # Additional attempt tracking
    attempt_number = Column(Integer, default=1)
    hints_used = Column(Integer, default=0)
    submitted_at = Column(TIMESTAMP, nullable=True)
    
    # Relationships
    quiz = relationship("Quiz", back_populates="attempts")

class NewsArticle(BaseEntity):
    """News Article Table - Stores news articles and metadata."""
    __tablename__ = "news_articles"
    
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    url = Column(String(1000), nullable=True)
    source = Column(String(200), nullable=False)
    author = Column(String(200), nullable=True)
    published_at = Column(TIMESTAMP, nullable=True)
    category = Column(String(100), default="general")
    
    # AI processing fields
    sentiment = Column(String(20), nullable=True)  # positive, negative, neutral
    keywords = Column(ARRAY(String), default=list)
    embedding = Column(ARRAY(Float), nullable=True)  # Vector embedding
    ai_summary = Column(Text, nullable=True)
    relevance_score = Column(Float, nullable=True)
    
    # Metadata
    language = Column(String(10), default="en")
    word_count = Column(Integer, nullable=True)
    reading_time_minutes = Column(Integer, nullable=True)
    image_urls = Column(ARRAY(String), default=list)

class Debate(BaseEntity):
    """Debate Table - Stores debate topics and configurations."""
    __tablename__ = "debates"
    
    chat_id = Column(BigInteger, nullable=False, index=True)
    topic = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    participants = Column(ARRAY(String), default=list)  # Agent handles
    max_turns = Column(Integer, default=6)
    current_turn = Column(Integer, default=0)
    status = Column(String(50), default="pending")  # pending, active, completed, cancelled
    
    # Debate configuration
    category = Column(String(100), default="general")
    time_limit_minutes = Column(Integer, default=30)
    audience_voting = Column(Boolean, default=True)
    moderated = Column(Boolean, default=True)
    
    # Results
    winner = Column(String(100), nullable=True)
    audience_votes = Column(JSONB, default=dict)
    final_scores = Column(JSONB, default=dict)
    
    # Relationships
    messages = relationship("DebateMessage", back_populates="debate")

class DebateMessage(BaseEntity):
    """Debate Message Table - Stores individual debate messages."""
    __tablename__ = "debate_messages"
    
    debate_id = Column(UUID(as_uuid=True), ForeignKey("debates.id"), nullable=False)
    participant = Column(String(100), nullable=False)  # Agent handle
    turn_number = Column(Integer, nullable=False)
    message = Column(Text, nullable=False)
    position = Column(String(20), nullable=True)  # for, against, neutral
    
    # Message analysis
    argument_strength = Column(Float, nullable=True)
    sentiment = Column(String(20), nullable=True)
    word_count = Column(Integer, nullable=True)
    response_to_message_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Relationships
    debate = relationship("Debate", back_populates="messages")

class FunContent(BaseEntity):
    """Fun Content Table - Stores jokes, facts, riddles, and entertainment content."""
    __tablename__ = "fun_content"
    
    content_type = Column(String(50), nullable=False)  # joke, fact, riddle, story, meme
    content = Column(Text, nullable=False)
    category = Column(String(100), default="general")
    rating = Column(Float, default=0.0)
    usage_count = Column(Integer, default=0)
    
    # Content metadata
    language = Column(String(10), default="en")
    difficulty = Column(String(20), default="easy")
    tags = Column(ARRAY(String), default=list)
    source = Column(String(200), nullable=True)
    author = Column(String(200), nullable=True)
    
    # Engagement metrics
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    last_used = Column(TIMESTAMP, nullable=True)

class KnowledgeDocument(BaseEntity):
    """Knowledge Document Table - Stores RAG documents and metadata."""
    __tablename__ = "knowledge_documents"
    
    doc_id = Column(String(200), unique=True, nullable=False, index=True)
    chat_id = Column(BigInteger, nullable=False, index=True)
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    source_url = Column(String(1000), nullable=True)
    content_type = Column(String(50), default="text")
    
    # Processing metadata
    chunk_count = Column(Integer, default=0)
    embedding_model = Column(String(100), default="sentence-transformers")
    processing_status = Column(String(50), default="pending")
    
    # Access control
    access_level = Column(String(20), default="chat")  # public, chat, private
    owner_user_id = Column(BigInteger, nullable=True)
    
    # File metadata (if uploaded)
    filename = Column(String(500), nullable=True)
    file_size = Column(BigInteger, nullable=True)
    mime_type = Column(String(100), nullable=True)

class UserProfile(BaseEntity):
    """User Profile Table - Stores user preferences and history."""
    __tablename__ = "user_profiles"
    
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(200), nullable=True)
    last_name = Column(String(200), nullable=True)
    language_code = Column(String(10), default="en")
    
    # Preferences
    preferred_agents = Column(ARRAY(String), default=list)
    notification_settings = Column(JSONB, default=dict)
    privacy_settings = Column(JSONB, default=dict)
    
    # Usage statistics
    total_messages = Column(Integer, default=0)
    total_quiz_attempts = Column(Integer, default=0)
    total_debates_participated = Column(Integer, default=0)
    favorite_content_types = Column(ARRAY(String), default=list)
    
    # Engagement metrics
    last_active = Column(TIMESTAMP, nullable=True)
    streak_days = Column(Integer, default=0)
    points = Column(Integer, default=0)
    level = Column(Integer, default=1)

# Pydantic Models (API Schema)

class AgentSchema(BasePydanticModel, PydanticTimestampMixin):
    """Pydantic schema for Agent model."""
    id: uuid.UUID
    handle: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    persona_prompt: str
    capabilities: List[str] = []
    guardrails: List[str] = []
    enabled: bool = True
    agent_type: str = "persona"
    version: str = "1.0.0"
    max_tokens_per_response: int = 2000
    temperature: float = 0.7
    model_name: str = "gpt-4"
    rate_limits: Dict[str, Any] = {}

class ChatConfigSchema(BasePydanticModel, PydanticTimestampMixin):
    """Pydantic schema for ChatConfig model."""
    id: uuid.UUID
    chat_id: int
    enabled_agents: List[uuid.UUID] = []
    default_agent: Optional[uuid.UUID] = None
    schedules: Dict[str, Any] = {}
    moderation_policy: Dict[str, Any] = {}
    feature_flags: Dict[str, bool] = {}
    chat_type: str = "group"
    language: str = "en"
    timezone: str = "UTC"
    welcome_message: Optional[str] = None
    admin_users: List[int] = []

class MessageLogSchema(BasePydanticModel, PydanticTimestampMixin):
    """Pydantic schema for MessageLog model."""
    id: uuid.UUID
    update_id: int
    chat_id: int
    user_id: Optional[int] = None
    normalized_json: Dict[str, Any]
    handled_by: Optional[str] = None
    result_msg_id: Optional[int] = None
    latency_ms: Optional[int] = None
    status: str = "pending"
    message_type: str = "text"
    intent_detected: Optional[str] = None
    route_reason: Optional[str] = None
    error_message: Optional[str] = None

class ScheduleSchema(BasePydanticModel, PydanticTimestampMixin):
    """Pydantic schema for Schedule model."""
    id: uuid.UUID
    task_type: str
    cron_expr: Optional[str] = None
    chat_id: int
    params: Dict[str, Any] = {}
    enabled: bool = True
    schedule_type: str = "cron"
    schedule_config: Dict[str, Any] = {}
    content_data: Dict[str, Any] = {}
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    run_count: int = 0
    max_runs: Optional[int] = None

class QuizSchema(BasePydanticModel, PydanticTimestampMixin):
    """Pydantic schema for Quiz model."""
    id: uuid.UUID
    chat_id: int
    question: str
    options: List[str]
    answer_idx: int
    start_ts: Optional[datetime] = None
    end_ts: Optional[datetime] = None
    results: Dict[str, Any] = {}
    category: str = "general"
    difficulty: str = "medium"
    explanation: Optional[str] = None
    time_limit_seconds: int = 60
    max_participants: int = 100

class NewsArticleSchema(BasePydanticModel, PydanticTimestampMixin):
    """Pydantic schema for NewsArticle model."""
    id: uuid.UUID
    title: str = Field(..., max_length=500)
    summary: Optional[str] = None
    content: Optional[str] = None
    url: Optional[str] = None
    source: str = Field(..., max_length=200)
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    category: str = "general"
    sentiment: Optional[str] = None
    keywords: List[str] = []
    ai_summary: Optional[str] = None
    relevance_score: Optional[float] = None

class DebateSchema(BasePydanticModel, PydanticTimestampMixin):
    """Pydantic schema for Debate model."""
    id: uuid.UUID
    chat_id: int
    topic: str = Field(..., max_length=500)
    description: Optional[str] = None
    participants: List[str] = []
    max_turns: int = 6
    current_turn: int = 0
    status: str = "pending"
    category: str = "general"
    time_limit_minutes: int = 30
    audience_voting: bool = True
    moderated: bool = True
    winner: Optional[str] = None
    audience_votes: Dict[str, Any] = {}
    final_scores: Dict[str, Any] = {}

class FunContentSchema(BasePydanticModel, PydanticTimestampMixin):
    """Pydantic schema for FunContent model."""
    id: uuid.UUID
    content_type: str = Field(..., max_length=50)
    content: str
    category: str = "general"
    rating: float = 0.0
    usage_count: int = 0
    language: str = "en"
    difficulty: str = "easy"
    tags: List[str] = []
    source: Optional[str] = None
    author: Optional[str] = None
    likes: int = 0
    dislikes: int = 0
    shares: int = 0
    last_used: Optional[datetime] = None

class UserProfileSchema(BasePydanticModel, PydanticTimestampMixin):
    """Pydantic schema for UserProfile model."""
    id: uuid.UUID
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: str = "en"
    preferred_agents: List[str] = []
    notification_settings: Dict[str, Any] = {}
    privacy_settings: Dict[str, Any] = {}
    total_messages: int = 0
    total_quiz_attempts: int = 0
    total_debates_participated: int = 0
    favorite_content_types: List[str] = []
    last_active: Optional[datetime] = None
    streak_days: int = 0
    points: int = 0
    level: int = 1
