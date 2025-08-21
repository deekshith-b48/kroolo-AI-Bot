"""
Admin API endpoints for the Kroolo AI Bot.
Provides REST API access to admin functionality for external tools and dashboards.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from src.core.admin_auth import admin_auth, AdminAuthError, InsufficientPermissionError
from src.core.admin_commands import get_admin_commands
from src.core.workflow_manager import get_workflow_manager
from src.core.community_manager import get_community_manager
from src.core.telegram_client import TelegramClient
from src.models.admin import (
    AdminUserCreate, AdminUserUpdate, AdminUserResponse,
    BotWorkflowCreate, BotWorkflowUpdate, BotWorkflowResponse,
    CommunitySettingsUpdate, CommunitySettingsResponse,
    PendingApprovalResponse, AuditLogResponse,
    AdminRole, WorkflowStatus, Permissions
)
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/admin", tags=["admin"])
security = HTTPBearer()


# Request/Response Models

class AdminTokenRequest(BaseModel):
    """Admin token request model."""
    telegram_user_id: int
    username: Optional[str] = None


class AdminTokenResponse(BaseModel):
    """Admin token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    admin_role: str
    permissions: List[str]


class CommandRequest(BaseModel):
    """Command execution request model."""
    command: str
    args: List[str] = Field(default_factory=list)
    chat_id: int
    message_id: Optional[int] = None


class CommandResponse(BaseModel):
    """Command execution response model."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    inline_keyboard: Optional[List[List[Dict[str, str]]]] = None


class WorkflowExecutionRequest(BaseModel):
    """Workflow execution request model."""
    workflow_name: str
    input_data: Dict[str, Any]
    user_id: Optional[int] = None
    chat_id: Optional[int] = None


class BanUserRequest(BaseModel):
    """Ban user request model."""
    user_id: int
    reason: Optional[str] = None
    duration_hours: Optional[int] = None


class MuteUserRequest(BaseModel):
    """Mute user request model."""
    user_id: int
    chat_id: int
    reason: Optional[str] = None
    duration_hours: Optional[int] = None


# Authentication Dependencies

async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """Get current admin user from token."""
    token = credentials.credentials
    
    # Simple token validation - in production, use proper JWT
    # For now, expect format: "admin_user_id"
    try:
        user_id = int(token.replace("admin_", ""))
        
        # Verify user is admin
        if not await admin_auth.is_admin(user_id):
            raise HTTPException(status_code=401, detail="Invalid admin token")
        
        return user_id
        
    except (ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="Invalid token format")


async def require_permission(permission: str):
    """Dependency to require specific permission."""
    async def check_permission(admin_id: int = Depends(get_current_admin)) -> int:
        if not await admin_auth.has_permission(admin_id, permission):
            raise HTTPException(
                status_code=403, 
                detail=f"Permission '{permission}' required"
            )
        return admin_id
    return check_permission


# Authentication Endpoints

@router.post("/auth/token", response_model=AdminTokenResponse)
async def get_admin_token(request: AdminTokenRequest):
    """Get admin access token."""
    try:
        admin_user = await admin_auth.get_admin_user(request.telegram_user_id)
        if not admin_user:
            raise HTTPException(status_code=401, detail="User is not an admin")
        
        # Generate simple token (in production, use proper JWT)
        token = f"admin_{request.telegram_user_id}"
        
        permissions = await admin_auth.get_user_permissions(request.telegram_user_id)
        
        return AdminTokenResponse(
            access_token=token,
            expires_in=3600,  # 1 hour
            admin_role=admin_user.role.value,
            permissions=permissions
        )
        
    except Exception as e:
        logger.error(f"Token generation error: {e}")
        raise HTTPException(status_code=500, detail="Token generation failed")


@router.get("/auth/me", response_model=AdminUserResponse)
async def get_current_admin_info(admin_id: int = Depends(get_current_admin)):
    """Get current admin user information."""
    try:
        admin_user = await admin_auth.get_admin_user(admin_id)
        if not admin_user:
            raise HTTPException(status_code=404, detail="Admin user not found")
        
        return AdminUserResponse.from_orm(admin_user)
        
    except Exception as e:
        logger.error(f"Get admin info error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get admin info")


# User Management Endpoints

@router.get("/users", response_model=List[AdminUserResponse])
async def list_admin_users(admin_id: int = Depends(get_current_admin)):
    """List all admin users."""
    try:
        from src.database.session import get_db_session
        from src.models.admin import AdminUser
        
        async with get_db_session() as session:
            admins = session.query(AdminUser).filter(
                AdminUser.is_active == True
            ).order_by(AdminUser.role, AdminUser.created_at).all()
        
        return [AdminUserResponse.from_orm(admin) for admin in admins]
        
    except Exception as e:
        logger.error(f"List admins error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list admin users")


@router.post("/users", response_model=AdminUserResponse)
async def create_admin_user(
    user_data: AdminUserCreate,
    admin_id: int = Depends(require_permission(Permissions.PROMOTE_USER))
):
    """Create/promote admin user."""
    try:
        admin_user = await admin_auth.promote_user(
            admin_id=admin_id,
            target_user_id=user_data.telegram_user_id,
            role=user_data.role,
            permissions=user_data.permissions
        )
        
        return AdminUserResponse.from_orm(admin_user)
        
    except Exception as e:
        logger.error(f"Create admin error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{user_id}")
async def demote_admin_user(
    user_id: int,
    admin_id: int = Depends(require_permission(Permissions.DEMOTE_USER))
):
    """Demote admin user."""
    try:
        success = await admin_auth.demote_user(admin_id, user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="User not found or not admin")
        
        return {"success": True, "message": f"User {user_id} demoted"}
        
    except Exception as e:
        logger.error(f"Demote admin error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/ban")
async def ban_user(
    request: BanUserRequest,
    admin_id: int = Depends(require_permission(Permissions.BAN_USER))
):
    """Ban user from using the bot."""
    try:
        duration = timedelta(hours=request.duration_hours) if request.duration_hours else None
        
        banned_user = await admin_auth.ban_user(
            admin_id=admin_id,
            target_user_id=request.user_id,
            reason=request.reason,
            duration=duration
        )
        
        return {
            "success": True,
            "message": f"User {request.user_id} banned",
            "banned_until": banned_user.banned_until.isoformat() if banned_user.banned_until else None
        }
        
    except Exception as e:
        logger.error(f"Ban user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/unban")
async def unban_user(
    user_id: int,
    admin_id: int = Depends(require_permission(Permissions.UNBAN_USER))
):
    """Unban user."""
    try:
        success = await admin_auth.unban_user(admin_id, user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="User not banned")
        
        return {"success": True, "message": f"User {user_id} unbanned"}
        
    except Exception as e:
        logger.error(f"Unban user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/mute")
async def mute_user(
    request: MuteUserRequest,
    admin_id: int = Depends(require_permission(Permissions.MUTE_USER))
):
    """Mute user in specific chat."""
    try:
        duration = timedelta(hours=request.duration_hours) if request.duration_hours else None
        
        muted_user = await admin_auth.mute_user(
            admin_id=admin_id,
            target_user_id=request.user_id,
            chat_id=request.chat_id,
            reason=request.reason,
            duration=duration
        )
        
        return {
            "success": True,
            "message": f"User {request.user_id} muted in chat {request.chat_id}",
            "muted_until": muted_user.muted_until.isoformat() if muted_user.muted_until else None
        }
        
    except Exception as e:
        logger.error(f"Mute user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/unmute")
async def unmute_user(
    user_id: int,
    chat_id: int,
    admin_id: int = Depends(require_permission(Permissions.UNMUTE_USER))
):
    """Unmute user in specific chat."""
    try:
        success = await admin_auth.unmute_user(admin_id, user_id, chat_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="User not muted in this chat")
        
        return {"success": True, "message": f"User {user_id} unmuted in chat {chat_id}"}
        
    except Exception as e:
        logger.error(f"Unmute user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Workflow Management Endpoints

@router.get("/workflows", response_model=List[BotWorkflowResponse])
async def list_workflows(
    include_inactive: bool = Query(False),
    admin_id: int = Depends(get_current_admin)
):
    """List all workflows."""
    try:
        telegram_client = TelegramClient()
        workflow_manager = get_workflow_manager(telegram_client)
        
        workflows = await workflow_manager.list_workflows(admin_id, include_inactive)
        
        return [BotWorkflowResponse.from_orm(workflow) for workflow in workflows]
        
    except Exception as e:
        logger.error(f"List workflows error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows", response_model=BotWorkflowResponse)
async def create_workflow(
    workflow_data: BotWorkflowCreate,
    admin_id: int = Depends(require_permission(Permissions.ADD_WORKFLOW))
):
    """Create new workflow."""
    try:
        telegram_client = TelegramClient()
        workflow_manager = get_workflow_manager(telegram_client)
        
        workflow = await workflow_manager.add_workflow(
            admin_id=admin_id,
            name=workflow_data.name,
            endpoint_url=workflow_data.endpoint_url,
            description=workflow_data.description,
            trigger_command=workflow_data.trigger_command,
            method=workflow_data.method,
            headers=workflow_data.headers,
            payload_template=workflow_data.payload_template
        )
        
        return BotWorkflowResponse.from_orm(workflow)
        
    except Exception as e:
        logger.error(f"Create workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/{workflow_id}/approve")
async def approve_workflow(
    workflow_id: int,
    admin_id: int = Depends(require_permission(Permissions.APPROVE_WORKFLOW))
):
    """Approve pending workflow."""
    try:
        telegram_client = TelegramClient()
        workflow_manager = get_workflow_manager(telegram_client)
        
        success = await workflow_manager.approve_workflow(admin_id, workflow_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Workflow not found or not pending")
        
        return {"success": True, "message": f"Workflow {workflow_id} approved"}
        
    except Exception as e:
        logger.error(f"Approve workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/{workflow_id}/reject")
async def reject_workflow(
    workflow_id: int,
    reason: Optional[str] = Body(None),
    admin_id: int = Depends(require_permission(Permissions.APPROVE_WORKFLOW))
):
    """Reject pending workflow."""
    try:
        telegram_client = TelegramClient()
        workflow_manager = get_workflow_manager(telegram_client)
        
        success = await workflow_manager.reject_workflow(admin_id, workflow_id, reason)
        
        if not success:
            raise HTTPException(status_code=404, detail="Workflow not found or not pending")
        
        return {"success": True, "message": f"Workflow {workflow_id} rejected"}
        
    except Exception as e:
        logger.error(f"Reject workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/{workflow_name}/toggle")
async def toggle_workflow(
    workflow_name: str,
    admin_id: int = Depends(require_permission(Permissions.TOGGLE_WORKFLOW))
):
    """Toggle workflow active status."""
    try:
        telegram_client = TelegramClient()
        workflow_manager = get_workflow_manager(telegram_client)
        
        success = await workflow_manager.toggle_workflow(admin_id, workflow_name)
        
        if not success:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return {"success": True, "message": f"Workflow {workflow_name} toggled"}
        
    except Exception as e:
        logger.error(f"Toggle workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/execute")
async def execute_workflow(
    request: WorkflowExecutionRequest,
    admin_id: int = Depends(get_current_admin)
):
    """Execute workflow manually."""
    try:
        telegram_client = TelegramClient()
        workflow_manager = get_workflow_manager(telegram_client)
        
        result = await workflow_manager.execute_workflow(
            workflow_name=request.workflow_name,
            input_data=request.input_data,
            user_id=request.user_id,
            chat_id=request.chat_id
        )
        
        return {
            "success": result.success,
            "response_data": result.response_data,
            "error_message": result.error_message,
            "execution_time": result.execution_time,
            "status_code": result.status_code
        }
        
    except Exception as e:
        logger.error(f"Execute workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Community Management Endpoints

@router.get("/communities")
async def list_communities(admin_id: int = Depends(get_current_admin)):
    """List all managed communities."""
    try:
        telegram_client = TelegramClient()
        community_manager = get_community_manager(telegram_client)
        
        communities = await community_manager.list_communities(admin_id)
        
        return [CommunitySettingsResponse.from_orm(community) for community in communities]
        
    except Exception as e:
        logger.error(f"List communities error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/communities/{chat_id}", response_model=CommunitySettingsResponse)
async def get_community_settings(
    chat_id: int,
    admin_id: int = Depends(get_current_admin)
):
    """Get community settings."""
    try:
        telegram_client = TelegramClient()
        community_manager = get_community_manager(telegram_client)
        
        settings = await community_manager.get_community_settings(chat_id)
        
        if not settings:
            raise HTTPException(status_code=404, detail="Community not found")
        
        return CommunitySettingsResponse.from_orm(settings)
        
    except Exception as e:
        logger.error(f"Get community settings error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/communities/{chat_id}", response_model=CommunitySettingsResponse)
async def update_community_settings(
    chat_id: int,
    updates: CommunitySettingsUpdate,
    admin_id: int = Depends(require_permission(Permissions.MANAGE_COMMUNITY))
):
    """Update community settings."""
    try:
        telegram_client = TelegramClient()
        community_manager = get_community_manager(telegram_client)
        
        # Convert Pydantic model to dict, excluding None values
        update_data = updates.dict(exclude_unset=True)
        
        settings = await community_manager.update_community_settings(
            admin_id=admin_id,
            chat_id=chat_id,
            updates=update_data
        )
        
        return CommunitySettingsResponse.from_orm(settings)
        
    except Exception as e:
        logger.error(f"Update community settings error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# System Control Endpoints

@router.post("/system/reload")
async def reload_system(admin_id: int = Depends(require_permission(Permissions.RELOAD_BOT))):
    """Reload system configuration."""
    try:
        # Clear permission cache
        admin_auth._permission_cache.clear()
        admin_auth._cache_expiry.clear()
        
        # Clear community settings cache
        telegram_client = TelegramClient()
        community_manager = get_community_manager(telegram_client)
        community_manager.clear_settings_cache()
        
        # Log action
        from src.models.admin import AuditAction
        await admin_auth.log_admin_action(admin_id, AuditAction.BOT_RELOADED)
        
        return {"success": True, "message": "System configuration reloaded"}
        
    except Exception as e:
        logger.error(f"Reload system error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/health")
async def system_health_check(admin_id: int = Depends(get_current_admin)):
    """Get system health status."""
    try:
        telegram_client = TelegramClient()
        health_data = await telegram_client.health_check()
        
        # Get additional stats
        workflow_manager = get_workflow_manager(telegram_client)
        workflow_stats = await workflow_manager.get_workflow_stats(admin_id)
        
        community_manager = get_community_manager(telegram_client)
        community_stats = await community_manager.get_community_stats(admin_id)
        
        return {
            "telegram": health_data,
            "workflows": workflow_stats,
            "communities": community_stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    admin_id: int = Depends(require_permission(Permissions.VIEW_LOGS))
):
    """Get audit logs."""
    try:
        logs = await admin_auth.get_audit_logs(admin_id, limit=limit, offset=offset)
        
        return [AuditLogResponse.from_orm(log) for log in logs]
        
    except Exception as e:
        logger.error(f"Get logs error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics")
async def get_analytics(admin_id: int = Depends(require_permission(Permissions.VIEW_ANALYTICS))):
    """Get system analytics."""
    try:
        telegram_client = TelegramClient()
        
        # Get workflow stats
        workflow_manager = get_workflow_manager(telegram_client)
        workflow_stats = await workflow_manager.get_workflow_stats(admin_id)
        
        # Get community stats
        community_manager = get_community_manager(telegram_client)
        community_stats = await community_manager.get_community_stats(admin_id)
        
        # Get admin stats
        from src.database.session import get_db_session
        from src.models.admin import AdminUser, AuditLog
        
        async with get_db_session() as session:
            total_admins = session.query(AdminUser).filter(AdminUser.is_active == True).count()
            today_actions = session.query(AuditLog).filter(
                AuditLog.created_at >= datetime.now().replace(hour=0, minute=0, second=0)
            ).count()
        
        return {
            "admins": {
                "total_admins": total_admins,
                "today_actions": today_actions
            },
            "workflows": workflow_stats,
            "communities": community_stats,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Command Execution Endpoint

@router.post("/commands/execute", response_model=CommandResponse)
async def execute_command(
    request: CommandRequest,
    admin_id: int = Depends(get_current_admin)
):
    """Execute admin command."""
    try:
        telegram_client = TelegramClient()
        admin_commands = get_admin_commands(telegram_client)
        
        result = await admin_commands.handle_command(
            user_id=admin_id,
            chat_id=request.chat_id,
            command=request.command,
            args=request.args,
            message_id=request.message_id
        )
        
        return CommandResponse(
            success=result.success,
            message=result.message,
            data=result.data,
            inline_keyboard=result.inline_keyboard
        )
        
    except Exception as e:
        logger.error(f"Execute command error: {e}")
        raise HTTPException(status_code=500, detail=str(e))