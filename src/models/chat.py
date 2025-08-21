"""
Chat and message models for the Kroolo AI Bot.
Stores conversation data, message history, and chat configurations.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from .base import BaseEntity, BasePydanticModel, PydanticTimestampMixin


class Chat(BaseEntity):
    """Database model for Telegram chats."""
    __tablename__ = "chats"
    
    chat_id = Column(BigInteger, unique=True, nullable=False, index=True)
    chat_type = Column(String(20), nullable=False)  # private, group, supergroup, channel
    title = Column(String(255), nullable=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    
    # Chat configuration
    enabled_agents = Column(JSON, default=list)  # List of enabled agent handles
    default_agent = Column(String(50), nullable=True)
    content_plan = Column(JSON, default=dict)  # Scheduling configuration
    moderation_policies = Column(JSON, default=dict)  # Moderation settings
    format_preferences = Column(JSON, default=dict)  # Formatting preferences
    
    # Status and settings
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    language_code = Column(String(10), default="en")
    timezone = Column(String(50), default="UTC")
    
    # Relationships
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    chat_members = relationship("ChatMember", back_populates="chat", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Chat(chat_id={self.chat_id}, type='{self.chat_type}', title='{self.title}')>"


class ChatMember(BaseEntity):
    """Database model for chat members."""
    __tablename__ = "chat_members"
    
    chat_id = Column(BigInteger, ForeignKey("chats.chat_id"), nullable=False)
    user_id = Column(BigInteger, nullable=False, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    
    # Member roles and permissions
    role = Column(String(20), default="member")  # owner, administrator, member
    permissions = Column(JSON, default=dict)  # Member permissions
    is_bot = Column(Boolean, default=False)
    
    # Activity tracking
    last_activity = Column(String(50), nullable=True)  # ISO timestamp
    message_count = Column(Integer, default=0)
    
    # Relationships
    chat = relationship("Chat", back_populates="chat_members")
    
    def __repr__(self):
        return f"<ChatMember(chat_id={self.chat_id}, user_id={self.user_id}, role='{self.role}')>"


class Message(BaseEntity):
    """Database model for Telegram messages."""
    __tablename__ = "messages"
    
    message_id = Column(BigInteger, nullable=False, index=True)
    chat_id = Column(BigInteger, ForeignKey("chats.chat_id"), nullable=False)
    user_id = Column(BigInteger, nullable=False, index=True)
    
    # Message content
    text = Column(Text, nullable=True)
    message_type = Column(String(20), nullable=False)  # text, photo, video, etc.
    content = Column(JSON, default=dict)  # Additional message content
    
    # Message context
    reply_to_message_id = Column(BigInteger, nullable=True)
    forward_from_chat_id = Column(BigInteger, nullable=True)
    forward_from_message_id = Column(BigInteger, nullable=True)
    
    # Processing information
    handled_by = Column(String(50), nullable=True)  # Agent that handled the message
    intent = Column(String(50), nullable=True)  # Detected user intent
    processing_time = Column(Integer, nullable=True)  # Processing time in milliseconds
    
    # Message status
    is_processed = Column(Boolean, default=False)
    is_flagged = Column(Boolean, default=False)
    flag_reason = Column(String(100), nullable=True)
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(message_id={self.message_id}, chat_id={self.chat_id}, user_id={self.user_id})>"


class Conversation(BaseEntity):
    """Database model for conversation threads."""
    __tablename__ = "conversations"
    
    chat_id = Column(BigInteger, ForeignKey("chats.chat_id"), nullable=False)
    thread_id = Column(BigInteger, nullable=True)  # For forum topics
    
    # Conversation state
    active_agents = Column(JSON, default=list)  # Currently active agents
    context_pointer = Column(String(100), nullable=True)  # Vector store reference
    conversation_summary = Column(Text, nullable=True)  # AI-generated summary
    
    # Conversation metadata
    topic = Column(String(255), nullable=True)
    mood = Column(String(50), nullable=True)  # friendly, formal, casual, etc.
    language = Column(String(10), default="en")
    
    # Activity tracking
    last_activity = Column(String(50), nullable=True)  # ISO timestamp
    message_count = Column(Integer, default=0)
    participant_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<Conversation(chat_id={self.chat_id}, thread_id={self.thread_id})>"


# Pydantic models for API responses
class ChatCreate(BasePydanticModel):
    """Model for creating new chats."""
    chat_id: int = Field(..., description="Telegram chat ID")
    chat_type: str = Field(..., description="Type of chat")
    title: Optional[str] = Field(None, max_length=255)
    username: Optional[str] = Field(None, max_length=100)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    enabled_agents: List[str] = Field(default_factory=list)
    default_agent: Optional[str] = Field(None, max_length=50)
    language_code: str = Field(default="en", max_length=10)
    timezone: str = Field(default="UTC", max_length=50)


class ChatUpdate(BasePydanticModel):
    """Model for updating existing chats."""
    title: Optional[str] = Field(None, max_length=255)
    enabled_agents: Optional[List[str]] = None
    default_agent: Optional[str] = Field(None, max_length=50)
    content_plan: Optional[Dict[str, Any]] = None
    moderation_policies: Optional[Dict[str, Any]] = None
    format_preferences: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    language_code: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)


class ChatResponse(BasePydanticModel, PydanticTimestampMixin):
    """Model for chat responses."""
    id: int
    chat_id: int
    chat_type: str
    title: Optional[str]
    username: Optional[str]
    enabled_agents: List[str]
    default_agent: Optional[str]
    is_active: bool
    language_code: str
    timezone: str


class MessageCreate(BasePydanticModel):
    """Model for creating new messages."""
    message_id: int = Field(..., description="Telegram message ID")
    chat_id: int = Field(..., description="Chat ID")
    user_id: int = Field(..., description="User ID")
    text: Optional[str] = Field(None, description="Message text")
    message_type: str = Field(..., description="Type of message")
    content: Dict[str, Any] = Field(default_factory=dict)
    reply_to_message_id: Optional[int] = None
    intent: Optional[str] = Field(None, max_length=50)


class MessageResponse(BasePydanticModel, PydanticTimestampMixin):
    """Model for message responses."""
    id: int
    message_id: int
    chat_id: int
    user_id: int
    text: Optional[str]
    message_type: str
    handled_by: Optional[str]
    intent: Optional[str]
    is_processed: bool
    is_flagged: bool


class ConversationCreate(BasePydanticModel):
    """Model for creating new conversations."""
    chat_id: int = Field(..., description="Chat ID")
    thread_id: Optional[int] = Field(None, description="Thread ID for forum topics")
    topic: Optional[str] = Field(None, max_length=255)
    active_agents: List[str] = Field(default_factory=list)
    language: str = Field(default="en", max_length=10)


class ConversationResponse(BasePydanticModel, PydanticTimestampMixin):
    """Model for conversation responses."""
    id: int
    chat_id: int
    thread_id: Optional[int]
    active_agents: List[str]
    topic: Optional[str]
    mood: Optional[str]
    language: str
    message_count: int
    participant_count: int
    last_activity: Optional[str]
