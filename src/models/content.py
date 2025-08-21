"""
Content models for the Kroolo AI Bot.
Stores news articles, quizzes, debates, and other content types.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, ForeignKey, BigInteger, Float
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
from datetime import datetime

from .base import BaseEntity, BasePydanticModel, PydanticTimestampMixin


class NewsArticle(BaseEntity):
    """Database model for news articles."""
    __tablename__ = "news_articles"
    
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    source_url = Column(String(1000), nullable=True)
    source_name = Column(String(200), nullable=False)
    
    # Content metadata
    category = Column(String(100), nullable=True)  # AI, technology, research, etc.
    tags = Column(JSON, default=list)  # List of tags
    language = Column(String(10), default="en")
    
    # AI processing
    ai_generated_summary = Column(Text, nullable=True)
    sentiment_score = Column(Float, nullable=True)  # -1 to 1
    relevance_score = Column(Float, nullable=True)  # 0 to 1
    embedding_vector = Column(JSON, nullable=True)  # Vector representation
    
    # Publishing
    published_at = Column(String(50), nullable=True)  # ISO timestamp
    is_published = Column(Boolean, default=False)
    published_to_chats = Column(JSON, default=list)  # List of chat IDs
    
    def __repr__(self):
        return f"<NewsArticle(title='{self.title[:50]}...', source='{self.source_name}')>"


class Quiz(BaseEntity):
    """Database model for quizzes."""
    __tablename__ = "quizzes"
    
    question = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)  # List of answer options
    correct_answer_index = Column(Integer, nullable=False)
    explanation = Column(Text, nullable=True)
    
    # Quiz metadata
    category = Column(String(100), nullable=True)  # AI, technology, general, etc.
    difficulty = Column(String(20), default="medium")  # easy, medium, hard
    tags = Column(JSON, default=list)
    language = Column(String(10), default="en")
    
    # Quiz settings
    time_limit = Column(Integer, default=60)  # Time limit in seconds
    is_active = Column(Boolean, default=True)
    max_attempts = Column(Integer, default=1)
    
    # Statistics
    total_attempts = Column(Integer, default=0)
    correct_attempts = Column(Integer, default=0)
    average_time = Column(Float, nullable=True)  # Average completion time
    
    # Publishing
    published_to_chats = Column(JSON, default=list)  # List of chat IDs
    scheduled_publish_time = Column(String(50), nullable=True)  # ISO timestamp
    
    def __repr__(self):
        return f"<Quiz(question='{self.question[:50]}...', difficulty='{self.difficulty}')>"


class QuizAttempt(BaseEntity):
    """Database model for quiz attempts."""
    __tablename__ = "quiz_attempts"
    
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    user_id = Column(BigInteger, nullable=False, index=True)
    chat_id = Column(BigInteger, nullable=False, index=True)
    
    # Attempt details
    selected_answer_index = Column(Integer, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    time_taken = Column(Integer, nullable=True)  # Time taken in seconds
    score = Column(Float, nullable=True)  # Score based on time and correctness
    
    # User feedback
    user_rating = Column(Integer, nullable=True)  # 1-5 rating
    feedback_comment = Column(Text, nullable=True)
    
    # Relationships
    quiz = relationship("Quiz")
    
    def __repr__(self):
        return f"<QuizAttempt(quiz_id={self.quiz_id}, user_id={self.user_id}, correct={self.is_correct})>"


class Debate(BaseEntity):
    """Database model for debates."""
    __tablename__ = "debates"
    
    topic = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    participants = Column(JSON, default=list)  # List of agent handles
    
    # Debate structure
    max_turns = Column(Integer, default=10)
    turn_duration = Column(Integer, default=300)  # Duration per turn in seconds
    current_turn = Column(Integer, default=0)
    current_speaker = Column(String(50), nullable=True)
    
    # Debate state
    status = Column(String(20), default="pending")  # pending, active, completed, cancelled
    start_time = Column(String(50), nullable=True)  # ISO timestamp
    end_time = Column(String(50), nullable=True)  # ISO timestamp
    
    # Debate settings
    is_public = Column(Boolean, default=True)
    allow_audience_participation = Column(Boolean, default=True)
    moderation_level = Column(String(20), default="standard")  # light, standard, strict
    
    # Statistics
    total_messages = Column(Integer, default=0)
    participant_count = Column(Integer, default=0)
    audience_participation = Column(Integer, default=0)
    
    # Publishing
    published_to_chats = Column(JSON, default=list)  # List of chat IDs
    scheduled_start_time = Column(String(50), nullable=True)  # ISO timestamp
    
    def __repr__(self):
        return f"<Debate(topic='{self.topic[:50]}...', status='{self.status}')>"


class DebateMessage(BaseEntity):
    """Database model for debate messages."""
    __tablename__ = "debate_messages"
    
    debate_id = Column(Integer, ForeignKey("debates.id"), nullable=False)
    speaker_handle = Column(String(50), nullable=False)
    message_text = Column(Text, nullable=False)
    turn_number = Column(Integer, nullable=False)
    
    # Message metadata
    message_type = Column(String(20), default="speech")  # speech, question, rebuttal, etc.
    target_speaker = Column(String(50), nullable=True)  # Who the message is directed to
    response_to_message_id = Column(Integer, nullable=True)  # Response to specific message
    
    # AI processing
    sentiment_score = Column(Float, nullable=True)  # -1 to 1
    relevance_score = Column(Float, nullable=True)  # 0 to 1
    is_moderated = Column(Boolean, default=False)
    moderation_notes = Column(Text, nullable=True)
    
    # Timing
    turn_start_time = Column(String(50), nullable=True)  # ISO timestamp
    turn_end_time = Column(String(50), nullable=True)  # ISO timestamp
    
    # Relationships
    debate = relationship("Debate")
    
    def __repr__(self):
        return f"<DebateMessage(debate_id={self.debate_id}, speaker='{self.speaker_handle}', turn={self.turn_number})>"


class FunContent(BaseEntity):
    """Database model for fun content (jokes, facts, memes)."""
    __tablename__ = "fun_content"
    
    content_type = Column(String(50), nullable=False)  # joke, fact, meme, story
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)
    
    # Content metadata
    category = Column(String(100), nullable=True)  # humor, science, history, etc.
    tags = Column(JSON, default=list)
    language = Column(String(10), default="en")
    age_rating = Column(String(20), default="general")  # general, teen, adult
    
    # AI processing
    ai_generated = Column(Boolean, default=False)
    sentiment_score = Column(Float, nullable=True)  # -1 to 1
    humor_score = Column(Float, nullable=True)  # 0 to 1
    embedding_vector = Column(JSON, nullable=True)  # Vector representation
    
    # Content settings
    is_active = Column(Boolean, default=True)
    max_daily_usage = Column(Integer, default=5)  # Maximum times per day
    cooldown_hours = Column(Integer, default=24)  # Hours between uses in same chat
    
    # Statistics
    total_uses = Column(Integer, default=0)
    user_ratings = Column(JSON, default=list)  # List of user ratings
    average_rating = Column(Float, nullable=True)
    
    # Publishing
    published_to_chats = Column(JSON, default=list)  # List of chat IDs
    scheduled_publish_time = Column(String(50), nullable=True)  # ISO timestamp
    
    def __repr__(self):
        return f"<FunContent(type='{self.content_type}', title='{self.title}')>"


class ContentSchedule(BaseEntity):
    """Database model for content scheduling."""
    __tablename__ = "content_schedules"
    
    content_type = Column(String(50), nullable=False)  # news, quiz, debate, fun
    content_id = Column(Integer, nullable=True)  # ID of the specific content item
    chat_id = Column(BigInteger, nullable=False, index=True)
    
    # Schedule details
    schedule_type = Column(String(20), nullable=False)  # one_time, recurring, interval
    cron_expression = Column(String(100), nullable=True)  # Cron expression for recurring
    scheduled_time = Column(String(50), nullable=True)  # ISO timestamp for one-time
    interval_minutes = Column(Integer, nullable=True)  # Interval in minutes
    
    # Schedule state
    status = Column(String(20), default="pending")  # pending, active, completed, cancelled
    last_run = Column(String(50), nullable=True)  # ISO timestamp
    next_run = Column(String(50), nullable=True)  # ISO timestamp
    run_count = Column(Integer, default=0)
    
    # Schedule settings
    is_active = Column(Boolean, default=True)
    max_runs = Column(Integer, nullable=True)  # Maximum number of runs
    timezone = Column(String(50), default="UTC")
    
    def __repr__(self):
        return f"<ContentSchedule(type='{self.content_type}', chat_id={self.chat_id}, status='{self.status}')>"


# Pydantic models for API responses
class NewsArticleCreate(BasePydanticModel):
    """Model for creating news articles."""
    title: str = Field(..., max_length=500)
    summary: Optional[str] = None
    content: Optional[str] = None
    source_url: Optional[str] = Field(None, max_length=1000)
    source_name: str = Field(..., max_length=200)
    category: Optional[str] = Field(None, max_length=100)
    tags: List[str] = Field(default_factory=list)
    language: str = Field(default="en", max_length=10)


class NewsArticleResponse(BasePydanticModel, PydanticTimestampMixin):
    """Model for news article responses."""
    id: int
    title: str
    summary: Optional[str]
    source_name: str
    category: Optional[str]
    tags: List[str]
    is_published: bool
    published_at: Optional[str]


class QuizCreate(BasePydanticModel):
    """Model for creating quizzes."""
    question: str
    options: List[str]
    correct_answer_index: int = Field(..., ge=0)
    explanation: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    difficulty: str = Field(default="medium")
    tags: List[str] = Field(default_factory=list)
    time_limit: int = Field(default=60, ge=10, le=600)


class QuizResponse(BasePydanticModel, PydanticTimestampMixin):
    """Model for quiz responses."""
    id: int
    question: str
    options: List[str]
    category: Optional[str]
    difficulty: str
    is_active: bool
    total_attempts: int
    correct_attempts: int


class DebateCreate(BasePydanticModel):
    """Model for creating debates."""
    topic: str = Field(..., max_length=500)
    description: Optional[str] = None
    participants: List[str] = Field(..., min_items=2)
    max_turns: int = Field(default=10, ge=2, le=50)
    turn_duration: int = Field(default=300, ge=60, le=1800)
    is_public: bool = Field(default=True)
    allow_audience_participation: bool = Field(default=True)


class DebateResponse(BasePydanticModel, PydanticTimestampMixin):
    """Model for debate responses."""
    id: int
    topic: str
    status: str
    participants: List[str]
    current_turn: int
    max_turns: int
    total_messages: int
    start_time: Optional[str]


class FunContentCreate(BasePydanticModel):
    """Model for creating fun content."""
    content_type: str = Field(..., max_length=50)
    title: Optional[str] = Field(None, max_length=200)
    content: str
    category: Optional[str] = Field(None, max_length=100)
    tags: List[str] = Field(default_factory=list)
    age_rating: str = Field(default="general")
    ai_generated: bool = Field(default=False)


class FunContentResponse(BasePydanticModel, PydanticTimestampMixin):
    """Model for fun content responses."""
    id: int
    content_type: str
    title: Optional[str]
    content: str
    category: Optional[str]
    tags: List[str]
    is_active: bool
    total_uses: int
    average_rating: Optional[float]


class ContentScheduleCreate(BasePydanticModel):
    """Model for creating content schedules."""
    content_type: str = Field(..., max_length=50)
    content_id: Optional[int] = None
    chat_id: int
    schedule_type: str = Field(..., max_length=20)
    cron_expression: Optional[str] = Field(None, max_length=100)
    scheduled_time: Optional[str] = None
    interval_minutes: Optional[int] = Field(None, ge=1, le=10080)  # Max 1 week
    timezone: str = Field(default="UTC", max_length=50)


class ContentScheduleResponse(BasePydanticModel, PydanticTimestampMixin):
    """Model for content schedule responses."""
    id: int
    content_type: str
    chat_id: int
    schedule_type: str
    status: str
    last_run: Optional[str]
    next_run: Optional[str]
    run_count: int
    is_active: bool
