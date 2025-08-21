"""
Agent models for managing AI personas and their capabilities.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import Column, String, Text, JSON, Boolean, Integer
from pydantic import BaseModel, Field

from .base import BaseEntity, BasePydanticModel, PydanticTimestampMixin


class Agent(BaseEntity):
    """Database model for AI agents/personas."""
    __tablename__ = "agents"
    
    name = Column(String(100), nullable=False, index=True)
    handle = Column(String(50), unique=True, nullable=False, index=True)
    persona = Column(Text, nullable=False)
    tone = Column(String(50), nullable=False)  # formal, witty, skeptical, etc.
    era = Column(String(50), nullable=True)  # historical period if applicable
    domain_focus = Column(String(100), nullable=True)
    
    # Capabilities and permissions
    capabilities = Column(JSON, default=list)  # list of allowed tools
    guardrails = Column(JSON, default=list)  # topics to avoid
    compliance_notes = Column(Text, nullable=True)
    
    # Context and memory
    context_policy = Column(JSON, default=dict)
    memory_depth = Column(Integer, default=10)
    summarization_cadence = Column(String(50), default="daily")
    
    # Routing and classification
    routing_tags = Column(JSON, default=list)  # old-AI, new-AI, research, etc.
    
    # Rate limiting
    rate_limits = Column(JSON, default=dict)
    max_tokens_per_response = Column(Integer, default=2000)
    
    # Safety and moderation
    safety_level = Column(String(20), default="standard")  # standard, strict, experimental
    requires_moderation = Column(Boolean, default=False)
    
    # Status
    is_enabled = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<Agent(name='{self.name}', handle='{self.handle}')>"


class AgentCreate(BasePydanticModel):
    """Model for creating new agents."""
    name: str = Field(..., min_length=1, max_length=100)
    handle: str = Field(..., min_length=1, max_length=50)
    persona: str = Field(..., min_length=10)
    tone: str = Field(..., min_length=1, max_length=50)
    era: Optional[str] = Field(None, max_length=50)
    domain_focus: Optional[str] = Field(None, max_length=100)
    capabilities: List[str] = Field(default_factory=list)
    guardrails: List[str] = Field(default_factory=list)
    compliance_notes: Optional[str] = None
    context_policy: Dict[str, Any] = Field(default_factory=dict)
    memory_depth: int = Field(default=10, ge=1, le=100)
    summarization_cadence: str = Field(default="daily")
    routing_tags: List[str] = Field(default_factory=list)
    rate_limits: Dict[str, Any] = Field(default_factory=dict)
    max_tokens_per_response: int = Field(default=2000, ge=100, le=8000)
    safety_level: str = Field(default="standard")
    requires_moderation: bool = False
    is_default: bool = False


class AgentUpdate(BasePydanticModel):
    """Model for updating existing agents."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    persona: Optional[str] = Field(None, min_length=10)
    tone: Optional[str] = Field(None, min_length=1, max_length=50)
    era: Optional[str] = Field(None, max_length=50)
    domain_focus: Optional[str] = Field(None, max_length=100)
    capabilities: Optional[List[str]] = None
    guardrails: Optional[List[str]] = None
    compliance_notes: Optional[str] = None
    context_policy: Optional[Dict[str, Any]] = None
    memory_depth: Optional[int] = Field(None, ge=1, le=100)
    summarization_cadence: Optional[str] = None
    routing_tags: Optional[List[str]] = None
    rate_limits: Optional[Dict[str, Any]] = None
    max_tokens_per_response: Optional[int] = Field(None, ge=100, le=8000)
    safety_level: Optional[str] = None
    requires_moderation: Optional[bool] = None
    is_enabled: Optional[bool] = None
    is_default: Optional[bool] = None


class AgentResponse(BasePydanticModel, PydanticTimestampMixin):
    """Model for agent responses."""
    id: int
    name: str
    handle: str
    persona: str
    tone: str
    era: Optional[str]
    domain_focus: Optional[str]
    capabilities: List[str]
    guardrails: List[str]
    routing_tags: List[str]
    safety_level: str
    is_enabled: bool
    is_default: bool


# Default agent configurations
DEFAULT_AGENTS = [
    {
        "name": "Alan Turing",
        "handle": "AlanTuring",
        "persona": "I am Alan Turing, a British mathematician, logician, and computer scientist. I'm known for my work on computability theory, the Turing test, and breaking the Enigma code during WWII. I speak with precision and mathematical rigor, often referencing theoretical concepts in computer science.",
        "tone": "precise",
        "era": "early-20th-century",
        "domain_focus": "theoretical computer science, cryptography, artificial intelligence",
        "capabilities": ["rag.retrieve", "math.compute", "explain.concept"],
        "guardrails": ["modern_tech", "current_events"],
        "routing_tags": ["old-AI", "research", "theoretical"],
        "safety_level": "standard"
    },
    {
        "name": "Old AI Advocate",
        "handle": "OldAI",
        "persona": "I represent the classical, symbolic approach to artificial intelligence. I believe in rule-based systems, expert systems, and symbolic reasoning. I'm skeptical of deep learning's black-box nature and advocate for interpretable, explainable AI systems.",
        "tone": "skeptical",
        "era": "modern",
        "domain_focus": "symbolic AI, expert systems, knowledge representation",
        "capabilities": ["rag.retrieve", "explain.concept", "debate.argue"],
        "guardrails": ["harmful_content", "personal_advice"],
        "routing_tags": ["old-AI", "debate", "research"],
        "safety_level": "standard"
    },
    {
        "name": "New AI Advocate",
        "handle": "NewAI",
        "persona": "I champion modern deep learning approaches to artificial intelligence. I'm excited about transformers, large language models, and neural networks. I believe in the power of data-driven approaches and the potential for AGI through scaling and architecture improvements.",
        "tone": "enthusiastic",
        "era": "modern",
        "domain_focus": "deep learning, neural networks, transformers",
        "capabilities": ["rag.retrieve", "explain.concept", "debate.argue"],
        "guardrails": ["harmful_content", "personal_advice"],
        "routing_tags": ["new-AI", "debate", "research"],
        "safety_level": "standard"
    }
]
