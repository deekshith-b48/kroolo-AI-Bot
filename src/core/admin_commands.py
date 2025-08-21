"""
Admin command handlers for the Kroolo AI Bot.
Provides comprehensive admin control functionality including user management,
workflow control, community settings, and system administration.
"""

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.core.admin_auth import admin_auth, AdminAuthError, InsufficientPermissionError
from src.core.admin_auth import require_admin, require_permission, require_super_admin
from src.models.admin import (
    AdminRole, Permissions, WorkflowStatus, AuditAction,
    BotWorkflow, CommunitySettings, PendingApproval
)
from src.database.session import get_db_session
from src.core.telegram_client import TelegramClient
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class CommandResponse:
    """Standard response format for admin commands."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    inline_keyboard: Optional[List[List[Dict[str, str]]]] = None


class AdminCommandHandler:
    """Handles all admin commands for the bot."""
    
    def __init__(self, telegram_client: TelegramClient):
        self.telegram_client = telegram_client
        self.command_map = self._build_command_map()
    
    def _build_command_map(self) -> Dict[str, callable]:
        """Build mapping of command names to handler methods."""
        return {
            # Help and status
            'admin_help': self.handle_admin_help,
            'status': self.handle_status,
            'health': self.handle_health,
            
            # User management
            'promote': self.handle_promote_user,
            'demote': self.handle_demote_user,
            'ban': self.handle_ban_user,
            'unban': self.handle_unban_user,
            'mute': self.handle_mute_user,
            'unmute': self.handle_unmute_user,
            'listadmins': self.handle_list_admins,
            
            # Workflow management
            'addworkflow': self.handle_add_workflow,
            'removeworkflow': self.handle_remove_workflow,
            'listworkflows': self.handle_list_workflows,
            'toggleworkflow': self.handle_toggle_workflow,
            'approvals': self.handle_pending_approvals,
            'approve': self.handle_approve_request,
            'reject': self.handle_reject_request,
            
            # Community management
            'settopic': self.handle_set_topic,
            'allowcommand': self.handle_allow_command,
            'blockcommand': self.handle_block_command,
            'toggleautoresponse': self.handle_toggle_auto_response,
            'setwelcome': self.handle_set_welcome,
            'setrules': self.handle_set_rules,
            'communitysettings': self.handle_community_settings,
            
            # System control
            'reload': self.handle_reload_bot,
            'logs': self.handle_get_logs,
            'analytics': self.handle_analytics,
            'errors': self.handle_get_errors,
            'backup': self.handle_backup,
            'maintenance': self.handle_maintenance_mode,
            
            # Inline panel handlers
            'admin_panel': self.handle_admin_panel,
            'workflow_panel': self.handle_workflow_panel,
            'user_panel': self.handle_user_panel,
        }
    
    async def handle_command(self, user_id: int, chat_id: int, command: str, 
                           args: List[str], message_id: Optional[int] = None) -> CommandResponse:
        """Main command handler dispatcher."""
        try:
            # Check if user is banned
            if await admin_auth.is_user_banned(user_id):
                return CommandResponse(
                    success=False,
                    message="❌ You are banned from using this bot."
                )
            
            # Check if user is muted in this chat
            if await admin_auth.is_user_muted(user_id, chat_id):
                return CommandResponse(
                    success=False,
                    message="❌ You are muted in this chat."
                )
            
            # Get command handler
            handler = self.command_map.get(command.lower())
            if not handler:
                return CommandResponse(
                    success=False,
                    message=f"❌ Unknown admin command: `{command}`\nUse `/admin_help` to see available commands."
                )
            
            # Execute command
            return await handler(user_id, chat_id, args, message_id)
            
        except AdminAuthError as e:
            return CommandResponse(
                success=False,
                message=f"❌ Authentication error: {str(e)}"
            )
        except InsufficientPermissionError as e:
            return CommandResponse(
                success=False,
                message=f"❌ Access denied: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error handling admin command '{command}': {e}")
            return CommandResponse(
                success=False,
                message=f"❌ Command failed: {str(e)}"
            )
    
    # Help and Status Commands
    
    @require_admin
    async def handle_admin_help(self, user_id: int, chat_id: int, args: List[str], message_id: Optional[int]) -> CommandResponse:
        """Show admin help menu."""
        user_permissions = await admin_auth.get_user_permissions(user_id)
        role = await admin_auth.get_admin_role(user_id)
        
        help_text = f"""
🔧 **Admin Control Panel** - Role: `{role.value if role else 'None'}`

**👥 User Management:**
• `/promote @username [role]` - Promote user to admin
• `/demote @username` - Remove admin privileges
• `/ban @username [reason]` - Ban user from bot
• `/unban @username` - Unban user
• `/mute @username [duration]` - Mute user in chat
• `/unmute @username` - Unmute user
• `/listadmins` - List all admins

**🤖 Workflow Management:**
• `/addworkflow <name> <url>` - Add automation workflow
• `/removeworkflow <name>` - Remove workflow
• `/listworkflows` - List all workflows
• `/toggleworkflow <name>` - Enable/disable workflow
• `/approvals` - Show pending approvals
• `/approve <id>` - Approve request
• `/reject <id>` - Reject request

**🏘️ Community Management:**
• `/settopic <topic_name>` - Set default topic
• `/allowcommand <command>` - Allow command in chat
• `/blockcommand <command>` - Block command in chat
• `/toggleautoresponse` - Toggle auto responses
• `/setwelcome <message>` - Set welcome message
• `/setrules <rules>` - Set community rules
• `/communitysettings` - View community settings

**⚙️ System Control:**
• `/status` - Show bot status
• `/reload` - Reload bot configuration
• `/logs` - View recent logs
• `/analytics` - Show usage analytics
• `/errors` - Show recent errors
• `/backup` - Create system backup

**📱 Quick Access:**
• `/admin_panel` - Show inline admin panel
        """
        
        inline_keyboard = [
            [
                {"text": "👥 User Panel", "callback_data": "admin:user_panel"},
                {"text": "🤖 Workflow Panel", "callback_data": "admin:workflow_panel"}
            ],
            [
                {"text": "🏘️ Community Panel", "callback_data": "admin:community_panel"},
                {"text": "⚙️ System Panel", "callback_data": "admin:system_panel"}
            ]
        ]
        
        return CommandResponse(
            success=True,
            message=help_text,
            inline_keyboard=inline_keyboard
        )
    
    @require_admin
    async def handle_status(self, user_id: int, chat_id: int, args: List[str], message_id: Optional[int]) -> CommandResponse:
        """Show comprehensive bot status."""
        try:
            # Get system health
            health_data = await self.telegram_client.health_check()
            
            # Get admin stats
            async with get_db_session() as session:
                from src.models.admin import AdminUser, BotWorkflow
                admin_count = session.query(AdminUser).filter(AdminUser.is_active == True).count()
                workflow_count = session.query(BotWorkflow).filter(BotWorkflow.is_active == True).count()
            
            status_text = f"""
🤖 **Bot Status Report**

**System Health:** {'✅ Healthy' if health_data.get('status') == 'healthy' else '❌ Unhealthy'}
**Uptime:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Version:** {settings.app_version}
**Environment:** {settings.environment}

**Admin System:**
• Active Admins: {admin_count}
• Active Workflows: {workflow_count}
• Webhook Status: {'✅ Active' if health_data.get('webhook_info') else '❌ Inactive'}

**Bot Information:**
• Bot Username: @{health_data.get('bot_info', {}).get('username', 'N/A')}
• Can Join Groups: {'✅ Yes' if health_data.get('bot_info', {}).get('can_join_groups') else '❌ No'}
• Can Read Messages: {'✅ Yes' if health_data.get('bot_info', {}).get('can_read_all_group_messages') else '❌ No'}
            """
            
            return CommandResponse(
                success=True,
                message=status_text,
                data=health_data
            )
            
        except Exception as e:
            return CommandResponse(
                success=False,
                message=f"❌ Failed to get status: {str(e)}"
            )
    
    # User Management Commands
    
    @require_permission(Permissions.PROMOTE_USER)
    async def handle_promote_user(self, user_id: int, chat_id: int, args: List[str], message_id: Optional[int]) -> CommandResponse:
        """Promote user to admin role."""
        if len(args) < 1:
            return CommandResponse(
                success=False,
                message="❌ Usage: `/promote @username [role]`\nRoles: admin, moderator"
            )
        
        username_or_id = args[0].replace('@', '')
        role_str = args[1].lower() if len(args) > 1 else 'moderator'
        
        # Parse role
        role_map = {
            'admin': AdminRole.ADMIN,
            'moderator': AdminRole.MODERATOR,
            'mod': AdminRole.MODERATOR
        }
        
        role = role_map.get(role_str)
        if not role:
            return CommandResponse(
                success=False,
                message="❌ Invalid role. Available roles: admin, moderator"
            )
        
        try:
            # Try to parse as user ID first, then as username
            try:
                target_user_id = int(username_or_id)
            except ValueError:
                # TODO: Implement username to user_id resolution
                return CommandResponse(
                    success=False,
                    message="❌ Please provide user ID for now. Username lookup not yet implemented."
                )
            
            # Promote user
            admin_user = await admin_auth.promote_user(user_id, target_user_id, role)
            
            return CommandResponse(
                success=True,
                message=f"✅ User {target_user_id} promoted to {role.value}"
            )
            
        except Exception as e:
            return CommandResponse(
                success=False,
                message=f"❌ Failed to promote user: {str(e)}"
            )
    
    @require_permission(Permissions.DEMOTE_USER)
    async def handle_demote_user(self, user_id: int, chat_id: int, args: List[str], message_id: Optional[int]) -> CommandResponse:
        """Demote user from admin role."""
        if len(args) < 1:
            return CommandResponse(
                success=False,
                message="❌ Usage: `/demote @username`"
            )
        
        username_or_id = args[0].replace('@', '')
        
        try:
            try:
                target_user_id = int(username_or_id)
            except ValueError:
                return CommandResponse(
                    success=False,
                    message="❌ Please provide user ID for now."
                )
            
            success = await admin_auth.demote_user(user_id, target_user_id)
            
            if success:
                return CommandResponse(
                    success=True,
                    message=f"✅ User {target_user_id} demoted from admin role"
                )
            else:
                return CommandResponse(
                    success=False,
                    message="❌ User is not an admin or already demoted"
                )
                
        except Exception as e:
            return CommandResponse(
                success=False,
                message=f"❌ Failed to demote user: {str(e)}"
            )
    
    @require_permission(Permissions.BAN_USER)
    async def handle_ban_user(self, user_id: int, chat_id: int, args: List[str], message_id: Optional[int]) -> CommandResponse:
        """Ban user from using the bot."""
        if len(args) < 1:
            return CommandResponse(
                success=False,
                message="❌ Usage: `/ban @username [reason]`"
            )
        
        username_or_id = args[0].replace('@', '')
        reason = ' '.join(args[1:]) if len(args) > 1 else "No reason provided"
        
        try:
            try:
                target_user_id = int(username_or_id)
            except ValueError:
                return CommandResponse(
                    success=False,
                    message="❌ Please provide user ID for now."
                )
            
            banned_user = await admin_auth.ban_user(user_id, target_user_id, reason)
            
            return CommandResponse(
                success=True,
                message=f"✅ User {target_user_id} banned\nReason: {reason}"
            )
            
        except Exception as e:
            return CommandResponse(
                success=False,
                message=f"❌ Failed to ban user: {str(e)}"
            )
    
    @require_permission(Permissions.UNBAN_USER)
    async def handle_unban_user(self, user_id: int, chat_id: int, args: List[str], message_id: Optional[int]) -> CommandResponse:
        """Unban user."""
        if len(args) < 1:
            return CommandResponse(
                success=False,
                message="❌ Usage: `/unban @username`"
            )
        
        username_or_id = args[0].replace('@', '')
        
        try:
            try:
                target_user_id = int(username_or_id)
            except ValueError:
                return CommandResponse(
                    success=False,
                    message="❌ Please provide user ID for now."
                )
            
            success = await admin_auth.unban_user(user_id, target_user_id)
            
            if success:
                return CommandResponse(
                    success=True,
                    message=f"✅ User {target_user_id} unbanned"
                )
            else:
                return CommandResponse(
                    success=False,
                    message="❌ User is not banned"
                )
                
        except Exception as e:
            return CommandResponse(
                success=False,
                message=f"❌ Failed to unban user: {str(e)}"
            )
    
    @require_admin
    async def handle_list_admins(self, user_id: int, chat_id: int, args: List[str], message_id: Optional[int]) -> CommandResponse:
        """List all admin users."""
        try:
            async with get_db_session() as session:
                from src.models.admin import AdminUser
                admins = session.query(AdminUser).filter(
                    AdminUser.is_active == True
                ).order_by(AdminUser.role, AdminUser.created_at).all()
            
            if not admins:
                return CommandResponse(
                    success=True,
                    message="📋 No admin users found."
                )
            
            admin_list = "👥 **Admin Users:**\n\n"
            for admin in admins:
                role_emoji = {
                    AdminRole.SUPER_ADMIN: "👑",
                    AdminRole.ADMIN: "🛡️",
                    AdminRole.MODERATOR: "🎯"
                }
                
                admin_list += f"{role_emoji.get(admin.role, '👤')} **{admin.role.value.title()}**\n"
                admin_list += f"   ID: `{admin.telegram_user_id}`\n"
                admin_list += f"   Name: {admin.first_name or 'N/A'} {admin.last_name or ''}\n"
                admin_list += f"   Username: @{admin.username or 'N/A'}\n"
                admin_list += f"   Last Active: {admin.last_activity.strftime('%Y-%m-%d %H:%M') if admin.last_activity else 'Never'}\n\n"
            
            return CommandResponse(
                success=True,
                message=admin_list
            )
            
        except Exception as e:
            return CommandResponse(
                success=False,
                message=f"❌ Failed to list admins: {str(e)}"
            )
    
    # Workflow Management Commands
    
    @require_permission(Permissions.ADD_WORKFLOW)
    async def handle_add_workflow(self, user_id: int, chat_id: int, args: List[str], message_id: Optional[int]) -> CommandResponse:
        """Add new automation workflow."""
        if len(args) < 2:
            return CommandResponse(
                success=False,
                message="❌ Usage: `/addworkflow <name> <url> [trigger_command]`"
            )
        
        name = args[0]
        url = args[1]
        trigger_command = args[2] if len(args) > 2 else None
        
        # Validate URL
        if not (url.startswith('http://') or url.startswith('https://')):
            return CommandResponse(
                success=False,
                message="❌ Invalid URL. Must start with http:// or https://"
            )
        
        try:
            async with get_db_session() as session:
                admin_user = await admin_auth.get_admin_user(user_id)
                
                # Check if workflow already exists
                existing = session.query(BotWorkflow).filter(
                    BotWorkflow.name == name
                ).first()
                
                if existing:
                    return CommandResponse(
                        success=False,
                        message=f"❌ Workflow '{name}' already exists"
                    )
                
                # Create workflow
                workflow = BotWorkflow(
                    name=name,
                    endpoint_url=url,
                    trigger_command=trigger_command,
                    created_by_id=admin_user.id,
                    status=WorkflowStatus.PENDING
                )
                
                session.add(workflow)
                session.commit()
                session.refresh(workflow)
                
                await admin_auth.log_admin_action(
                    user_id, AuditAction.WORKFLOW_ADDED,
                    details={"name": name, "url": url, "trigger": trigger_command}
                )
                
                return CommandResponse(
                    success=True,
                    message=f"✅ Workflow '{name}' added and pending approval\nURL: {url}"
                )
                
        except Exception as e:
            return CommandResponse(
                success=False,
                message=f"❌ Failed to add workflow: {str(e)}"
            )
    
    @require_permission(Permissions.REMOVE_WORKFLOW)
    async def handle_remove_workflow(self, user_id: int, chat_id: int, args: List[str], message_id: Optional[int]) -> CommandResponse:
        """Remove automation workflow."""
        if len(args) < 1:
            return CommandResponse(
                success=False,
                message="❌ Usage: `/removeworkflow <name>`"
            )
        
        name = args[0]
        
        try:
            async with get_db_session() as session:
                workflow = session.query(BotWorkflow).filter(
                    BotWorkflow.name == name
                ).first()
                
                if not workflow:
                    return CommandResponse(
                        success=False,
                        message=f"❌ Workflow '{name}' not found"
                    )
                
                session.delete(workflow)
                session.commit()
                
                await admin_auth.log_admin_action(
                    user_id, AuditAction.WORKFLOW_REMOVED,
                    details={"name": name}
                )
                
                return CommandResponse(
                    success=True,
                    message=f"✅ Workflow '{name}' removed"
                )
                
        except Exception as e:
            return CommandResponse(
                success=False,
                message=f"❌ Failed to remove workflow: {str(e)}"
            )
    
    @require_admin
    async def handle_list_workflows(self, user_id: int, chat_id: int, args: List[str], message_id: Optional[int]) -> CommandResponse:
        """List all workflows."""
        try:
            async with get_db_session() as session:
                workflows = session.query(BotWorkflow).order_by(
                    BotWorkflow.status, BotWorkflow.name
                ).all()
            
            if not workflows:
                return CommandResponse(
                    success=True,
                    message="🤖 No workflows found."
                )
            
            workflow_list = "🤖 **Bot Workflows:**\n\n"
            
            status_emoji = {
                WorkflowStatus.PENDING: "⏳",
                WorkflowStatus.APPROVED: "✅",
                WorkflowStatus.REJECTED: "❌",
                WorkflowStatus.ACTIVE: "🟢",
                WorkflowStatus.INACTIVE: "🔴"
            }
            
            for workflow in workflows:
                emoji = status_emoji.get(workflow.status, "❓")
                workflow_list += f"{emoji} **{workflow.name}**\n"
                workflow_list += f"   Status: {workflow.status.value}\n"
                workflow_list += f"   Trigger: {workflow.trigger_command or 'Manual'}\n"
                workflow_list += f"   Executions: {workflow.execution_count}\n"
                workflow_list += f"   Last Run: {workflow.last_executed.strftime('%Y-%m-%d %H:%M') if workflow.last_executed else 'Never'}\n\n"
            
            return CommandResponse(
                success=True,
                message=workflow_list
            )
            
        except Exception as e:
            return CommandResponse(
                success=False,
                message=f"❌ Failed to list workflows: {str(e)}"
            )
    
    @require_permission(Permissions.TOGGLE_WORKFLOW)
    async def handle_toggle_workflow(self, user_id: int, chat_id: int, args: List[str], message_id: Optional[int]) -> CommandResponse:
        """Toggle workflow active status."""
        if len(args) < 1:
            return CommandResponse(
                success=False,
                message="❌ Usage: `/toggleworkflow <name>`"
            )
        
        name = args[0]
        
        try:
            async with get_db_session() as session:
                workflow = session.query(BotWorkflow).filter(
                    BotWorkflow.name == name
                ).first()
                
                if not workflow:
                    return CommandResponse(
                        success=False,
                        message=f"❌ Workflow '{name}' not found"
                    )
                
                # Toggle status
                workflow.is_active = not workflow.is_active
                workflow.status = WorkflowStatus.ACTIVE if workflow.is_active else WorkflowStatus.INACTIVE
                session.commit()
                
                action = AuditAction.WORKFLOW_ENABLED if workflow.is_active else AuditAction.WORKFLOW_DISABLED
                await admin_auth.log_admin_action(
                    user_id, action,
                    details={"name": name, "active": workflow.is_active}
                )
                
                status = "enabled" if workflow.is_active else "disabled"
                return CommandResponse(
                    success=True,
                    message=f"✅ Workflow '{name}' {status}"
                )
                
        except Exception as e:
            return CommandResponse(
                success=False,
                message=f"❌ Failed to toggle workflow: {str(e)}"
            )
    
    # System Control Commands
    
    @require_permission(Permissions.RELOAD_BOT)
    async def handle_reload_bot(self, user_id: int, chat_id: int, args: List[str], message_id: Optional[int]) -> CommandResponse:
        """Reload bot configuration."""
        try:
            # Clear permission cache
            admin_auth._permission_cache.clear()
            admin_auth._cache_expiry.clear()
            
            # Log action
            await admin_auth.log_admin_action(
                user_id, AuditAction.BOT_RELOADED
            )
            
            return CommandResponse(
                success=True,
                message="✅ Bot configuration reloaded successfully"
            )
            
        except Exception as e:
            return CommandResponse(
                success=False,
                message=f"❌ Failed to reload bot: {str(e)}"
            )
    
    @require_permission(Permissions.VIEW_LOGS)
    async def handle_get_logs(self, user_id: int, chat_id: int, args: List[str], message_id: Optional[int]) -> CommandResponse:
        """Get recent audit logs."""
        try:
            limit = int(args[0]) if args and args[0].isdigit() else 10
            limit = min(limit, 50)  # Max 50 logs
            
            logs = await admin_auth.get_audit_logs(user_id, limit=limit)
            
            if not logs:
                return CommandResponse(
                    success=True,
                    message="📋 No audit logs found."
                )
            
            log_text = f"📋 **Recent Audit Logs (Last {len(logs)}):**\n\n"
            
            for log in logs:
                log_text += f"🕒 {log.created_at.strftime('%m-%d %H:%M')}\n"
                log_text += f"👤 Admin ID: {log.admin.telegram_user_id}\n"
                log_text += f"⚡ Action: {log.action.value.replace('_', ' ').title()}\n"
                if log.target_user_id:
                    log_text += f"🎯 Target: {log.target_user_id}\n"
                if log.details:
                    log_text += f"📝 Details: {json.dumps(log.details, indent=2)}\n"
                log_text += "---\n"
            
            return CommandResponse(
                success=True,
                message=log_text
            )
            
        except Exception as e:
            return CommandResponse(
                success=False,
                message=f"❌ Failed to get logs: {str(e)}"
            )
    
    # Inline Panel Handlers
    
    @require_admin
    async def handle_admin_panel(self, user_id: int, chat_id: int, args: List[str], message_id: Optional[int]) -> CommandResponse:
        """Show main admin control panel."""
        role = await admin_auth.get_admin_role(user_id)
        
        inline_keyboard = [
            [
                {"text": "👥 User Management", "callback_data": "admin:user_panel"},
                {"text": "🤖 Workflows", "callback_data": "admin:workflow_panel"}
            ],
            [
                {"text": "🏘️ Community Settings", "callback_data": "admin:community_panel"},
                {"text": "📊 Analytics", "callback_data": "admin:analytics"}
            ],
            [
                {"text": "⚙️ System Control", "callback_data": "admin:system_panel"},
                {"text": "📋 Audit Logs", "callback_data": "admin:logs"}
            ]
        ]
        
        return CommandResponse(
            success=True,
            message=f"🔧 **Admin Control Panel**\nRole: `{role.value if role else 'None'}`\n\nSelect an option:",
            inline_keyboard=inline_keyboard
        )


# Global admin command handler instance
admin_commands = None


def get_admin_commands(telegram_client: TelegramClient) -> AdminCommandHandler:
    """Get global admin command handler instance."""
    global admin_commands
    if admin_commands is None:
        admin_commands = AdminCommandHandler(telegram_client)
    return admin_commands
