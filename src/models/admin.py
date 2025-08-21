"""
Admin system models for the Kroolo AI Bot.
Handles admin roles, permissions, audit logs, and workflow management.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, BigInteger, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, TimestampMixin, PydanticTimestampMixin


class AdminRole(str, Enum):
    """Admin role enumeration."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"


class WorkflowStatus(str, Enum):
    """Workflow status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    INACTIVE = "inactive"


class AuditAction(str, Enum):
    """Audit action enumeration."""
    USER_PROMOTED = "user_promoted"
    USER_DEMOTED = "user_demoted"
    USER_BANNED = "user_banned"
    USER_UNBANNED = "user_unbanned"
    USER_MUTED = "user_muted"
    USER_UNMUTED = "user_unmuted"
    WORKFLOW_ADDED = "workflow_added"
    WORKFLOW_REMOVED = "workflow_removed"
    WORKFLOW_ENABLED = "workflow_enabled"
    WORKFLOW_DISABLED = "workflow_disabled"
    COMMAND_ENABLED = "command_enabled"
    COMMAND_DISABLED = "command_disabled"
    TOPIC_CREATED = "topic_created"
    TOPIC_CLOSED = "topic_closed"
    BOT_RELOADED = "bot_reloaded"
    SETTINGS_CHANGED = "settings_changed"


# SQLAlchemy Models

class AdminUser(Base, TimestampMixin):
    """Admin user model."""
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    role = Column(SQLEnum(AdminRole), nullable=False, default=AdminRole.MODERATOR)
    permissions = Column(JSON, default=list)  # List of specific permissions
    is_active = Column(Boolean, default=True)
    created_by_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    last_activity = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    created_by = relationship("AdminUser", remote_side=[id])
    audit_logs = relationship("AuditLog", back_populates="admin", cascade="all, delete-orphan")


class BannedUser(Base, TimestampMixin):
    """Banned user model."""
    __tablename__ = "banned_users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    reason = Column(Text, nullable=True)
    banned_by_id = Column(Integer, ForeignKey("admin_users.id"), nullable=False)
    banned_until = Column(DateTime(timezone=True), nullable=True)  # None for permanent
    is_active = Column(Boolean, default=True)
    
    # Relationships
    banned_by = relationship("AdminUser")


class MutedUser(Base, TimestampMixin):
    """Muted user model."""
    __tablename__ = "muted_users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(BigInteger, index=True, nullable=False)
    chat_id = Column(BigInteger, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    reason = Column(Text, nullable=True)
    muted_by_id = Column(Integer, ForeignKey("admin_users.id"), nullable=False)
    muted_until = Column(DateTime(timezone=True), nullable=True)  # None for permanent
    is_active = Column(Boolean, default=True)
    
    # Relationships
    muted_by = relationship("AdminUser")


class BotWorkflow(Base, TimestampMixin):
    """Bot workflow model."""
    __tablename__ = "bot_workflows"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    trigger_command = Column(String(255), nullable=True)  # e.g., "/salesreport"
    endpoint_url = Column(String(1000), nullable=False)
    method = Column(String(10), default="POST")
    headers = Column(JSON, default=dict)
    payload_template = Column(JSON, default=dict)
    status = Column(SQLEnum(WorkflowStatus), default=WorkflowStatus.PENDING)
    created_by_id = Column(Integer, ForeignKey("admin_users.id"), nullable=False)
    approved_by_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    is_active = Column(Boolean, default=False)
    execution_count = Column(Integer, default=0)
    last_executed = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    created_by = relationship("AdminUser", foreign_keys=[created_by_id])
    approved_by = relationship("AdminUser", foreign_keys=[approved_by_id])


class CommunitySettings(Base, TimestampMixin):
    """Community-specific bot settings."""
    __tablename__ = "community_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger, unique=True, index=True, nullable=False)
    chat_title = Column(String(255), nullable=True)
    chat_type = Column(String(50), nullable=False)  # group, supergroup, channel
    auto_moderation = Column(Boolean, default=False)
    auto_topic_creation = Column(Boolean, default=False)
    manual_approval = Column(Boolean, default=False)
    allowed_commands = Column(JSON, default=list)  # List of allowed commands
    blocked_commands = Column(JSON, default=list)  # List of blocked commands
    welcome_message = Column(Text, nullable=True)
    community_rules = Column(Text, nullable=True)
    default_topic_id = Column(Integer, nullable=True)
    admin_only_mode = Column(Boolean, default=False)
    ai_assistant_enabled = Column(Boolean, default=True)
    managed_by_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    settings_data = Column(JSON, default=dict)  # Additional settings
    
    # Relationships
    managed_by = relationship("AdminUser")


class PendingApproval(Base, TimestampMixin):
    """Pending approval requests."""
    __tablename__ = "pending_approvals"
    
    id = Column(Integer, primary_key=True, index=True)
    request_type = Column(String(100), nullable=False)  # workflow, user_action, content, etc.
    request_data = Column(JSON, nullable=False)
    requested_by_id = Column(BigInteger, nullable=False)  # Telegram user ID
    chat_id = Column(BigInteger, nullable=True)
    status = Column(String(50), default="pending")  # pending, approved, rejected
    reviewed_by_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
    review_message = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    reviewed_by = relationship("AdminUser")


class AuditLog(Base, TimestampMixin):
    """Audit log for admin actions."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admin_users.id"), nullable=False)
    action = Column(SQLEnum(AuditAction), nullable=False)
    target_user_id = Column(BigInteger, nullable=True)
    chat_id = Column(BigInteger, nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Relationships
    admin = relationship("AdminUser", back_populates="audit_logs")


# Pydantic Models for API

class AdminUserCreate(BaseModel):
    """Admin user creation model."""
    telegram_user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: AdminRole = AdminRole.MODERATOR
    permissions: List[str] = Field(default_factory=list)


class AdminUserUpdate(BaseModel):
    """Admin user update model."""
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[AdminRole] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None


class AdminUserResponse(PydanticTimestampMixin):
    """Admin user response model."""
    id: int
    telegram_user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: AdminRole
    permissions: List[str]
    is_active: bool
    last_activity: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class BotWorkflowCreate(BaseModel):
    """Bot workflow creation model."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_command: Optional[str] = Field(None, regex=r'^/[a-zA-Z][a-zA-Z0-9_]*$')
    endpoint_url: str = Field(..., regex=r'^https?://.+')
    method: str = Field(default="POST", regex=r'^(GET|POST|PUT|DELETE)$')
    headers: Dict[str, str] = Field(default_factory=dict)
    payload_template: Dict[str, Any] = Field(default_factory=dict)


class BotWorkflowUpdate(BaseModel):
    """Bot workflow update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_command: Optional[str] = Field(None, regex=r'^/[a-zA-Z][a-zA-Z0-9_]*$')
    endpoint_url: Optional[str] = Field(None, regex=r'^https?://.+')
    method: Optional[str] = Field(None, regex=r'^(GET|POST|PUT|DELETE)$')
    headers: Optional[Dict[str, str]] = None
    payload_template: Optional[Dict[str, Any]] = None
    status: Optional[WorkflowStatus] = None
    is_active: Optional[bool] = None


class BotWorkflowResponse(PydanticTimestampMixin):
    """Bot workflow response model."""
    id: int
    name: str
    description: Optional[str] = None
    trigger_command: Optional[str] = None
    endpoint_url: str
    method: str
    status: WorkflowStatus
    is_active: bool
    execution_count: int
    last_executed: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CommunitySettingsUpdate(BaseModel):
    """Community settings update model."""
    auto_moderation: Optional[bool] = None
    auto_topic_creation: Optional[bool] = None
    manual_approval: Optional[bool] = None
    allowed_commands: Optional[List[str]] = None
    blocked_commands: Optional[List[str]] = None
    welcome_message: Optional[str] = None
    community_rules: Optional[str] = None
    default_topic_id: Optional[int] = None
    admin_only_mode: Optional[bool] = None
    ai_assistant_enabled: Optional[bool] = None
    settings_data: Optional[Dict[str, Any]] = None


class CommunitySettingsResponse(PydanticTimestampMixin):
    """Community settings response model."""
    id: int
    chat_id: int
    chat_title: Optional[str] = None
    chat_type: str
    auto_moderation: bool
    auto_topic_creation: bool
    manual_approval: bool
    allowed_commands: List[str]
    blocked_commands: List[str]
    welcome_message: Optional[str] = None
    community_rules: Optional[str] = None
    admin_only_mode: bool
    ai_assistant_enabled: bool
    settings_data: Dict[str, Any]
    
    class Config:
        from_attributes = True


class PendingApprovalResponse(PydanticTimestampMixin):
    """Pending approval response model."""
    id: int
    request_type: str
    request_data: Dict[str, Any]
    requested_by_id: int
    chat_id: Optional[int] = None
    status: str
    review_message: Optional[str] = None
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AuditLogResponse(PydanticTimestampMixin):
    """Audit log response model."""
    id: int
    action: AuditAction
    target_user_id: Optional[int] = None
    chat_id: Optional[int] = None
    details: Dict[str, Any]
    admin: AdminUserResponse
    
    class Config:
        from_attributes = True


# Permission Constants

class Permissions:
    """Permission constants for admin roles."""
    
    # User management
    PROMOTE_USER = "promote_user"
    DEMOTE_USER = "demote_user"
    BAN_USER = "ban_user"
    UNBAN_USER = "unban_user"
    MUTE_USER = "mute_user"
    UNMUTE_USER = "unmute_user"
    
    # Workflow management
    ADD_WORKFLOW = "add_workflow"
    REMOVE_WORKFLOW = "remove_workflow"
    APPROVE_WORKFLOW = "approve_workflow"
    TOGGLE_WORKFLOW = "toggle_workflow"
    
    # Community management
    MANAGE_COMMUNITY = "manage_community"
    CREATE_TOPIC = "create_topic"
    CLOSE_TOPIC = "close_topic"
    SET_RULES = "set_rules"
    MANAGE_SETTINGS = "manage_settings"
    
    # Bot control
    RELOAD_BOT = "reload_bot"
    VIEW_LOGS = "view_logs"
    VIEW_ANALYTICS = "view_analytics"
    SYSTEM_CONTROL = "system_control"


# Default permissions by role
DEFAULT_PERMISSIONS = {
    AdminRole.SUPER_ADMIN: [
        Permissions.PROMOTE_USER,
        Permissions.DEMOTE_USER,
        Permissions.BAN_USER,
        Permissions.UNBAN_USER,
        Permissions.MUTE_USER,
        Permissions.UNMUTE_USER,
        Permissions.ADD_WORKFLOW,
        Permissions.REMOVE_WORKFLOW,
        Permissions.APPROVE_WORKFLOW,
        Permissions.TOGGLE_WORKFLOW,
        Permissions.MANAGE_COMMUNITY,
        Permissions.CREATE_TOPIC,
        Permissions.CLOSE_TOPIC,
        Permissions.SET_RULES,
        Permissions.MANAGE_SETTINGS,
        Permissions.RELOAD_BOT,
        Permissions.VIEW_LOGS,
        Permissions.VIEW_ANALYTICS,
        Permissions.SYSTEM_CONTROL,
    ],
    AdminRole.ADMIN: [
        Permissions.BAN_USER,
        Permissions.UNBAN_USER,
        Permissions.MUTE_USER,
        Permissions.UNMUTE_USER,
        Permissions.ADD_WORKFLOW,
        Permissions.TOGGLE_WORKFLOW,
        Permissions.MANAGE_COMMUNITY,
        Permissions.CREATE_TOPIC,
        Permissions.CLOSE_TOPIC,
        Permissions.SET_RULES,
        Permissions.MANAGE_SETTINGS,
        Permissions.VIEW_LOGS,
        Permissions.VIEW_ANALYTICS,
    ],
    AdminRole.MODERATOR: [
        Permissions.MUTE_USER,
        Permissions.UNMUTE_USER,
        Permissions.CREATE_TOPIC,
        Permissions.CLOSE_TOPIC,
        Permissions.MANAGE_COMMUNITY,
    ],
}
