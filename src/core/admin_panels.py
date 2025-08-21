"""
Inline keyboard admin control panels for the Kroolo AI Bot.
Provides interactive admin interfaces with buttons and menus.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from src.core.admin_auth import admin_auth, AdminAuthError, InsufficientPermissionError
from src.models.admin import (
    AdminRole, Permissions, WorkflowStatus, AuditAction,
    BotWorkflow, CommunitySettings, PendingApproval
)
from src.database.session import get_db_session
from src.core.telegram_client import TelegramClient

logger = logging.getLogger(__name__)


class AdminPanelHandler:
    """Handles inline keyboard admin panels and callback queries."""
    
    def __init__(self, telegram_client: TelegramClient):
        self.telegram_client = telegram_client
        self.callback_handlers = self._build_callback_handlers()
    
    def _build_callback_handlers(self) -> Dict[str, callable]:
        """Build mapping of callback data to handler methods."""
        return {
            # Main panels
            'admin:user_panel': self.handle_user_panel,
            'admin:workflow_panel': self.handle_workflow_panel,
            'admin:community_panel': self.handle_community_panel,
            'admin:system_panel': self.handle_system_panel,
            'admin:analytics': self.handle_analytics_panel,
            'admin:logs': self.handle_logs_panel,
            
            # User management actions
            'admin:promote_menu': self.handle_promote_menu,
            'admin:ban_menu': self.handle_ban_menu,
            'admin:mute_menu': self.handle_mute_menu,
            'admin:list_admins': self.handle_list_admins_panel,
            
            # Workflow actions
            'admin:add_workflow': self.handle_add_workflow_panel,
            'admin:list_workflows': self.handle_list_workflows_panel,
            'admin:pending_workflows': self.handle_pending_workflows_panel,
            'admin:workflow_toggle': self.handle_workflow_toggle_panel,
            
            # Community actions
            'admin:community_settings': self.handle_community_settings_panel,
            'admin:topic_management': self.handle_topic_management_panel,
            'admin:moderation_settings': self.handle_moderation_settings_panel,
            
            # System actions
            'admin:reload_bot': self.handle_reload_bot_panel,
            'admin:health_check': self.handle_health_check_panel,
            'admin:maintenance': self.handle_maintenance_panel,
            
            # Navigation
            'admin:back': self.handle_back,
            'admin:main_menu': self.handle_main_menu,
        }
    
    async def handle_callback(self, user_id: int, chat_id: int, callback_data: str, 
                            message_id: int, callback_query_id: str) -> Dict[str, Any]:
        """Handle callback query from inline keyboard."""
        try:
            # Check if user is admin
            if not await admin_auth.is_admin(user_id):
                await self.telegram_client.answer_callback_query(
                    callback_query_id, "❌ Admin privileges required", show_alert=True
                )
                return {"success": False, "error": "Not admin"}
            
            # Check if user is banned
            if await admin_auth.is_user_banned(user_id):
                await self.telegram_client.answer_callback_query(
                    callback_query_id, "❌ You are banned", show_alert=True
                )
                return {"success": False, "error": "User banned"}
            
            # Parse callback data
            if ':' not in callback_data:
                callback_data = f"admin:{callback_data}"
            
            # Get handler
            handler = self.callback_handlers.get(callback_data)
            if not handler:
                await self.telegram_client.answer_callback_query(
                    callback_query_id, "❌ Unknown action"
                )
                return {"success": False, "error": "Unknown callback"}
            
            # Execute handler
            result = await handler(user_id, chat_id, message_id, callback_query_id)
            
            # Answer callback query
            if result.get("success"):
                await self.telegram_client.answer_callback_query(callback_query_id)
            else:
                await self.telegram_client.answer_callback_query(
                    callback_query_id, 
                    result.get("error", "Action failed"), 
                    show_alert=True
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling callback '{callback_data}': {e}")
            await self.telegram_client.answer_callback_query(
                callback_query_id, "❌ Internal error", show_alert=True
            )
            return {"success": False, "error": str(e)}
    
    # Main Panel Handlers
    
    async def handle_main_menu(self, user_id: int, chat_id: int, message_id: int, callback_query_id: str) -> Dict[str, Any]:
        """Show main admin menu."""
        role = await admin_auth.get_admin_role(user_id)
        
        keyboard = [
            [
                {"text": "👥 User Management", "callback_data": "admin:user_panel"},
                {"text": "🤖 Workflows", "callback_data": "admin:workflow_panel"}
            ],
            [
                {"text": "🏘️ Community", "callback_data": "admin:community_panel"},
                {"text": "📊 Analytics", "callback_data": "admin:analytics"}
            ],
            [
                {"text": "⚙️ System", "callback_data": "admin:system_panel"},
                {"text": "📋 Logs", "callback_data": "admin:logs"}
            ]
        ]
        
        text = f"🔧 **Admin Control Panel**\nRole: `{role.value if role else 'None'}`\n\nSelect an option:"
        
        try:
            await self.telegram_client.edit_message(
                chat_id, message_id, text,
                parse_mode="Markdown",
                reply_markup={"inline_keyboard": keyboard}
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_user_panel(self, user_id: int, chat_id: int, message_id: int, callback_query_id: str) -> Dict[str, Any]:
        """Show user management panel."""
        permissions = await admin_auth.get_user_permissions(user_id)
        
        keyboard = []
        
        if Permissions.PROMOTE_USER in permissions:
            keyboard.append([{"text": "⬆️ Promote User", "callback_data": "admin:promote_menu"}])
        
        if Permissions.DEMOTE_USER in permissions:
            keyboard.append([{"text": "⬇️ Demote User", "callback_data": "admin:demote_menu"}])
        
        keyboard.extend([
            [
                {"text": "🚫 Ban User", "callback_data": "admin:ban_menu"} if Permissions.BAN_USER in permissions else None,
                {"text": "🔇 Mute User", "callback_data": "admin:mute_menu"} if Permissions.MUTE_USER in permissions else None
            ],
            [{"text": "📋 List Admins", "callback_data": "admin:list_admins"}],
            [{"text": "🔙 Back", "callback_data": "admin:main_menu"}]
        ])
        
        # Filter out None buttons
        keyboard = [[btn for btn in row if btn] for row in keyboard]
        keyboard = [row for row in keyboard if row]
        
        text = "👥 **User Management Panel**\n\nSelect an action:"
        
        try:
            await self.telegram_client.edit_message(
                chat_id, message_id, text,
                parse_mode="Markdown",
                reply_markup={"inline_keyboard": keyboard}
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_workflow_panel(self, user_id: int, chat_id: int, message_id: int, callback_query_id: str) -> Dict[str, Any]:
        """Show workflow management panel."""
        permissions = await admin_auth.get_user_permissions(user_id)
        
        keyboard = []
        
        if Permissions.ADD_WORKFLOW in permissions:
            keyboard.append([{"text": "➕ Add Workflow", "callback_data": "admin:add_workflow"}])
        
        keyboard.extend([
            [{"text": "📋 List Workflows", "callback_data": "admin:list_workflows"}],
            [{"text": "⏳ Pending Approvals", "callback_data": "admin:pending_workflows"}],
        ])
        
        if Permissions.TOGGLE_WORKFLOW in permissions:
            keyboard.append([{"text": "🔄 Toggle Workflow", "callback_data": "admin:workflow_toggle"}])
        
        keyboard.append([{"text": "🔙 Back", "callback_data": "admin:main_menu"}])
        
        text = "🤖 **Workflow Management Panel**\n\nSelect an action:"
        
        try:
            await self.telegram_client.edit_message(
                chat_id, message_id, text,
                parse_mode="Markdown",
                reply_markup={"inline_keyboard": keyboard}
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_community_panel(self, user_id: int, chat_id: int, message_id: int, callback_query_id: str) -> Dict[str, Any]:
        """Show community management panel."""
        permissions = await admin_auth.get_user_permissions(user_id)
        
        keyboard = []
        
        if Permissions.MANAGE_COMMUNITY in permissions:
            keyboard.extend([
                [{"text": "⚙️ Community Settings", "callback_data": "admin:community_settings"}],
                [{"text": "📝 Topic Management", "callback_data": "admin:topic_management"}],
                [{"text": "🛡️ Moderation Settings", "callback_data": "admin:moderation_settings"}]
            ])
        
        keyboard.append([{"text": "🔙 Back", "callback_data": "admin:main_menu"}])
        
        text = "🏘️ **Community Management Panel**\n\nSelect an action:"
        
        try:
            await self.telegram_client.edit_message(
                chat_id, message_id, text,
                parse_mode="Markdown",
                reply_markup={"inline_keyboard": keyboard}
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_system_panel(self, user_id: int, chat_id: int, message_id: int, callback_query_id: str) -> Dict[str, Any]:
        """Show system control panel."""
        permissions = await admin_auth.get_user_permissions(user_id)
        
        keyboard = [
            [{"text": "🔄 Health Check", "callback_data": "admin:health_check"}]
        ]
        
        if Permissions.RELOAD_BOT in permissions:
            keyboard.append([{"text": "🔄 Reload Bot", "callback_data": "admin:reload_bot"}])
        
        if Permissions.SYSTEM_CONTROL in permissions:
            keyboard.append([{"text": "🚧 Maintenance Mode", "callback_data": "admin:maintenance"}])
        
        keyboard.append([{"text": "🔙 Back", "callback_data": "admin:main_menu"}])
        
        text = "⚙️ **System Control Panel**\n\nSelect an action:"
        
        try:
            await self.telegram_client.edit_message(
                chat_id, message_id, text,
                parse_mode="Markdown",
                reply_markup={"inline_keyboard": keyboard}
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Specific Action Handlers
    
    async def handle_list_admins_panel(self, user_id: int, chat_id: int, message_id: int, callback_query_id: str) -> Dict[str, Any]:
        """Show list of admin users."""
        try:
            async with get_db_session() as session:
                from src.models.admin import AdminUser
                admins = session.query(AdminUser).filter(
                    AdminUser.is_active == True
                ).order_by(AdminUser.role, AdminUser.created_at).all()
            
            if not admins:
                text = "👥 **Admin Users**\n\nNo admin users found."
            else:
                text = "👥 **Admin Users:**\n\n"
                role_emoji = {
                    AdminRole.SUPER_ADMIN: "👑",
                    AdminRole.ADMIN: "🛡️",
                    AdminRole.MODERATOR: "🎯"
                }
                
                for admin in admins[:10]:  # Limit to 10 to avoid message length issues
                    emoji = role_emoji.get(admin.role, "👤")
                    text += f"{emoji} `{admin.telegram_user_id}` - {admin.role.value.title()}\n"
                    if admin.username:
                        text += f"   @{admin.username}\n"
                    text += f"   Last active: {admin.last_activity.strftime('%m-%d %H:%M') if admin.last_activity else 'Never'}\n\n"
                
                if len(admins) > 10:
                    text += f"... and {len(admins) - 10} more"
            
            keyboard = [[{"text": "🔙 Back", "callback_data": "admin:user_panel"}]]
            
            await self.telegram_client.edit_message(
                chat_id, message_id, text,
                parse_mode="Markdown",
                reply_markup={"inline_keyboard": keyboard}
            )
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_list_workflows_panel(self, user_id: int, chat_id: int, message_id: int, callback_query_id: str) -> Dict[str, Any]:
        """Show list of workflows."""
        try:
            async with get_db_session() as session:
                workflows = session.query(BotWorkflow).order_by(
                    BotWorkflow.status, BotWorkflow.name
                ).limit(10).all()
            
            if not workflows:
                text = "🤖 **Bot Workflows**\n\nNo workflows found."
            else:
                text = "🤖 **Bot Workflows:**\n\n"
                status_emoji = {
                    WorkflowStatus.PENDING: "⏳",
                    WorkflowStatus.APPROVED: "✅",
                    WorkflowStatus.REJECTED: "❌",
                    WorkflowStatus.ACTIVE: "🟢",
                    WorkflowStatus.INACTIVE: "🔴"
                }
                
                for workflow in workflows:
                    emoji = status_emoji.get(workflow.status, "❓")
                    text += f"{emoji} **{workflow.name}**\n"
                    text += f"   Status: {workflow.status.value}\n"
                    text += f"   Executions: {workflow.execution_count}\n\n"
            
            keyboard = [
                [{"text": "🔄 Refresh", "callback_data": "admin:list_workflows"}],
                [{"text": "🔙 Back", "callback_data": "admin:workflow_panel"}]
            ]
            
            await self.telegram_client.edit_message(
                chat_id, message_id, text,
                parse_mode="Markdown",
                reply_markup={"inline_keyboard": keyboard}
            )
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_pending_workflows_panel(self, user_id: int, chat_id: int, message_id: int, callback_query_id: str) -> Dict[str, Any]:
        """Show pending workflow approvals."""
        try:
            async with get_db_session() as session:
                pending_workflows = session.query(BotWorkflow).filter(
                    BotWorkflow.status == WorkflowStatus.PENDING
                ).order_by(BotWorkflow.created_at).limit(5).all()
            
            if not pending_workflows:
                text = "⏳ **Pending Workflow Approvals**\n\nNo pending workflows."
                keyboard = [[{"text": "🔙 Back", "callback_data": "admin:workflow_panel"}]]
            else:
                text = "⏳ **Pending Workflow Approvals:**\n\n"
                keyboard = []
                
                for workflow in pending_workflows:
                    text += f"📝 **{workflow.name}**\n"
                    text += f"   URL: {workflow.endpoint_url}\n"
                    text += f"   Trigger: {workflow.trigger_command or 'Manual'}\n"
                    text += f"   Created: {workflow.created_at.strftime('%m-%d %H:%M')}\n\n"
                    
                    # Add approve/reject buttons if user has permission
                    if await admin_auth.has_permission(user_id, Permissions.APPROVE_WORKFLOW):
                        keyboard.append([
                            {"text": f"✅ Approve {workflow.name}", "callback_data": f"workflow:approve:{workflow.id}"},
                            {"text": f"❌ Reject {workflow.name}", "callback_data": f"workflow:reject:{workflow.id}"}
                        ])
                
                keyboard.append([{"text": "🔙 Back", "callback_data": "admin:workflow_panel"}])
            
            await self.telegram_client.edit_message(
                chat_id, message_id, text,
                parse_mode="Markdown",
                reply_markup={"inline_keyboard": keyboard}
            )
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_health_check_panel(self, user_id: int, chat_id: int, message_id: int, callback_query_id: str) -> Dict[str, Any]:
        """Show system health check."""
        try:
            health_data = await self.telegram_client.health_check()
            
            status = health_data.get('status', 'unknown')
            status_emoji = "✅" if status == 'healthy' else "❌"
            
            text = f"🔄 **System Health Check**\n\n"
            text += f"{status_emoji} **Status:** {status.title()}\n"
            text += f"🕒 **Check Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            if health_data.get('bot_info'):
                bot_info = health_data['bot_info']
                text += f"🤖 **Bot Info:**\n"
                text += f"   Username: @{bot_info.get('username', 'N/A')}\n"
                text += f"   Can Join Groups: {'✅' if bot_info.get('can_join_groups') else '❌'}\n"
                text += f"   Can Read Messages: {'✅' if bot_info.get('can_read_all_group_messages') else '❌'}\n\n"
            
            if health_data.get('webhook_info'):
                webhook_info = health_data['webhook_info']
                text += f"🔗 **Webhook Info:**\n"
                text += f"   URL: {webhook_info.get('url', 'Not set')}\n"
                text += f"   Pending Updates: {webhook_info.get('pending_update_count', 0)}\n"
            
            keyboard = [
                [{"text": "🔄 Refresh", "callback_data": "admin:health_check"}],
                [{"text": "🔙 Back", "callback_data": "admin:system_panel"}]
            ]
            
            await self.telegram_client.edit_message(
                chat_id, message_id, text,
                parse_mode="Markdown",
                reply_markup={"inline_keyboard": keyboard}
            )
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_analytics_panel(self, user_id: int, chat_id: int, message_id: int, callback_query_id: str) -> Dict[str, Any]:
        """Show analytics dashboard."""
        if not await admin_auth.has_permission(user_id, Permissions.VIEW_ANALYTICS):
            return {"success": False, "error": "No permission to view analytics"}
        
        try:
            # Get basic statistics
            async with get_db_session() as session:
                from src.models.admin import AdminUser, BotWorkflow, AuditLog
                
                admin_count = session.query(AdminUser).filter(AdminUser.is_active == True).count()
                active_workflows = session.query(BotWorkflow).filter(BotWorkflow.is_active == True).count()
                total_workflows = session.query(BotWorkflow).count()
                recent_actions = session.query(AuditLog).filter(
                    AuditLog.created_at >= datetime.now().replace(hour=0, minute=0, second=0)
                ).count()
            
            text = f"📊 **Analytics Dashboard**\n\n"
            text += f"👥 **Admin Users:** {admin_count}\n"
            text += f"🤖 **Workflows:** {active_workflows}/{total_workflows} active\n"
            text += f"⚡ **Today's Actions:** {recent_actions}\n"
            text += f"🕒 **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            
            keyboard = [
                [{"text": "🔄 Refresh", "callback_data": "admin:analytics"}],
                [{"text": "🔙 Back", "callback_data": "admin:main_menu"}]
            ]
            
            await self.telegram_client.edit_message(
                chat_id, message_id, text,
                parse_mode="Markdown",
                reply_markup={"inline_keyboard": keyboard}
            )
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_logs_panel(self, user_id: int, chat_id: int, message_id: int, callback_query_id: str) -> Dict[str, Any]:
        """Show recent audit logs."""
        if not await admin_auth.has_permission(user_id, Permissions.VIEW_LOGS):
            return {"success": False, "error": "No permission to view logs"}
        
        try:
            logs = await admin_auth.get_audit_logs(user_id, limit=5)
            
            if not logs:
                text = "📋 **Recent Audit Logs**\n\nNo logs found."
            else:
                text = "📋 **Recent Audit Logs:**\n\n"
                
                for log in logs:
                    text += f"🕒 {log.created_at.strftime('%m-%d %H:%M')}\n"
                    text += f"⚡ {log.action.value.replace('_', ' ').title()}\n"
                    if log.target_user_id:
                        text += f"🎯 Target: {log.target_user_id}\n"
                    text += "---\n"
            
            keyboard = [
                [{"text": "🔄 Refresh", "callback_data": "admin:logs"}],
                [{"text": "🔙 Back", "callback_data": "admin:main_menu"}]
            ]
            
            await self.telegram_client.edit_message(
                chat_id, message_id, text,
                parse_mode="Markdown",
                reply_markup={"inline_keyboard": keyboard}
            )
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_reload_bot_panel(self, user_id: int, chat_id: int, message_id: int, callback_query_id: str) -> Dict[str, Any]:
        """Handle bot reload with confirmation."""
        if not await admin_auth.has_permission(user_id, Permissions.RELOAD_BOT):
            return {"success": False, "error": "No permission to reload bot"}
        
        try:
            # Clear permission cache
            admin_auth._permission_cache.clear()
            admin_auth._cache_expiry.clear()
            
            # Log action
            await admin_auth.log_admin_action(user_id, AuditAction.BOT_RELOADED)
            
            text = "✅ **Bot Reloaded Successfully**\n\nConfiguration has been reloaded."
            
            keyboard = [[{"text": "🔙 Back", "callback_data": "admin:system_panel"}]]
            
            await self.telegram_client.edit_message(
                chat_id, message_id, text,
                parse_mode="Markdown",
                reply_markup={"inline_keyboard": keyboard}
            )
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_back(self, user_id: int, chat_id: int, message_id: int, callback_query_id: str) -> Dict[str, Any]:
        """Handle back navigation."""
        return await self.handle_main_menu(user_id, chat_id, message_id, callback_query_id)


# Global admin panel handler instance
admin_panels = None


def get_admin_panels(telegram_client: TelegramClient) -> AdminPanelHandler:
    """Get global admin panel handler instance."""
    global admin_panels
    if admin_panels is None:
        admin_panels = AdminPanelHandler(telegram_client)
    return admin_panels
