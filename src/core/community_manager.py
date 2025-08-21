"""
Community management system for the Kroolo AI Bot.
Handles community settings, topic management, and moderation features.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta

from src.core.admin_auth import admin_auth, AdminAuthError, InsufficientPermissionError
from src.models.admin import (
    CommunitySettings, Permissions, AuditAction
)
from src.database.session import get_db_session
from src.core.telegram_client import TelegramClient

logger = logging.getLogger(__name__)


class CommunityManager:
    """Manages community settings and features."""
    
    def __init__(self, telegram_client: TelegramClient):
        self.telegram_client = telegram_client
        self.settings_cache = {}  # Cache for community settings
        self.default_settings = {
            "auto_moderation": False,
            "auto_topic_creation": False,
            "manual_approval": False,
            "allowed_commands": [],
            "blocked_commands": [],
            "welcome_message": None,
            "community_rules": None,
            "default_topic_id": None,
            "admin_only_mode": False,
            "ai_assistant_enabled": True,
            "settings_data": {}
        }
    
    async def get_community_settings(self, chat_id: int, create_if_missing: bool = True) -> Optional[CommunitySettings]:
        """Get community settings for a chat."""
        # Check cache first
        if chat_id in self.settings_cache:
            return self.settings_cache[chat_id]
        
        async with get_db_session() as session:
            settings = session.query(CommunitySettings).filter(
                CommunitySettings.chat_id == chat_id
            ).first()
            
            if not settings and create_if_missing:
                # Get chat info from Telegram
                chat_info = await self.telegram_client.get_chat(chat_id)
                
                # Create default settings
                settings = CommunitySettings(
                    chat_id=chat_id,
                    chat_title=chat_info.get("title", "Unknown"),
                    chat_type=chat_info.get("type", "unknown"),
                    **self.default_settings
                )
                session.add(settings)
                session.commit()
                session.refresh(settings)
                
                logger.info(f"Created default settings for chat {chat_id}")
            
            # Cache settings
            if settings:
                self.settings_cache[chat_id] = settings
            
            return settings
    
    async def update_community_settings(self, admin_id: int, chat_id: int, 
                                      updates: Dict[str, Any]) -> CommunitySettings:
        """Update community settings."""
        if not await admin_auth.has_permission(admin_id, Permissions.MANAGE_COMMUNITY):
            raise InsufficientPermissionError("No permission to manage community settings")
        
        settings = await self.get_community_settings(chat_id)
        if not settings:
            raise ValueError("Community settings not found")
        
        async with get_db_session() as session:
            # Merge settings back into session
            settings = session.merge(settings)
            
            # Update fields
            for key, value in updates.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)
                else:
                    # Store in settings_data for custom fields
                    if not settings.settings_data:
                        settings.settings_data = {}
                    settings.settings_data[key] = value
            
            # Update managed_by
            admin_user = await admin_auth.get_admin_user(admin_id)
            if admin_user:
                settings.managed_by_id = admin_user.id
            
            session.commit()
            session.refresh(settings)
            
            # Update cache
            self.settings_cache[chat_id] = settings
            
            # Log action
            await admin_auth.log_admin_action(
                admin_id, AuditAction.SETTINGS_CHANGED, chat_id=chat_id,
                details={"updates": updates}
            )
            
            logger.info(f"Community settings updated for chat {chat_id} by admin {admin_id}")
            return settings
    
    async def set_welcome_message(self, admin_id: int, chat_id: int, message: str) -> bool:
        """Set welcome message for new members."""
        if not await admin_auth.has_permission(admin_id, Permissions.MANAGE_COMMUNITY):
            raise InsufficientPermissionError("No permission to set welcome message")
        
        await self.update_community_settings(admin_id, chat_id, {"welcome_message": message})
        return True
    
    async def set_community_rules(self, admin_id: int, chat_id: int, rules: str) -> bool:
        """Set community rules."""
        if not await admin_auth.has_permission(admin_id, Permissions.SET_RULES):
            raise InsufficientPermissionError("No permission to set community rules")
        
        await self.update_community_settings(admin_id, chat_id, {"community_rules": rules})
        return True
    
    async def toggle_auto_moderation(self, admin_id: int, chat_id: int) -> bool:
        """Toggle auto-moderation for the community."""
        if not await admin_auth.has_permission(admin_id, Permissions.MANAGE_COMMUNITY):
            raise InsufficientPermissionError("No permission to toggle auto-moderation")
        
        settings = await self.get_community_settings(chat_id)
        new_status = not settings.auto_moderation
        
        await self.update_community_settings(admin_id, chat_id, {"auto_moderation": new_status})
        
        logger.info(f"Auto-moderation {'enabled' if new_status else 'disabled'} for chat {chat_id}")
        return new_status
    
    async def toggle_auto_topic_creation(self, admin_id: int, chat_id: int) -> bool:
        """Toggle auto-topic creation for the community."""
        if not await admin_auth.has_permission(admin_id, Permissions.CREATE_TOPIC):
            raise InsufficientPermissionError("No permission to toggle auto-topic creation")
        
        settings = await self.get_community_settings(chat_id)
        new_status = not settings.auto_topic_creation
        
        await self.update_community_settings(admin_id, chat_id, {"auto_topic_creation": new_status})
        
        logger.info(f"Auto-topic creation {'enabled' if new_status else 'disabled'} for chat {chat_id}")
        return new_status
    
    async def toggle_manual_approval(self, admin_id: int, chat_id: int) -> bool:
        """Toggle manual approval mode for the community."""
        if not await admin_auth.has_permission(admin_id, Permissions.MANAGE_COMMUNITY):
            raise InsufficientPermissionError("No permission to toggle manual approval")
        
        settings = await self.get_community_settings(chat_id)
        new_status = not settings.manual_approval
        
        await self.update_community_settings(admin_id, chat_id, {"manual_approval": new_status})
        
        logger.info(f"Manual approval {'enabled' if new_status else 'disabled'} for chat {chat_id}")
        return new_status
    
    async def add_allowed_command(self, admin_id: int, chat_id: int, command: str) -> bool:
        """Add command to allowed list."""
        if not await admin_auth.has_permission(admin_id, Permissions.MANAGE_SETTINGS):
            raise InsufficientPermissionError("No permission to manage command settings")
        
        settings = await self.get_community_settings(chat_id)
        
        # Normalize command
        command = command.lstrip('/')
        
        if command not in settings.allowed_commands:
            allowed_commands = settings.allowed_commands.copy()
            allowed_commands.append(command)
            
            await self.update_community_settings(admin_id, chat_id, {"allowed_commands": allowed_commands})
            
            logger.info(f"Command '{command}' added to allowed list for chat {chat_id}")
            return True
        
        return False
    
    async def remove_allowed_command(self, admin_id: int, chat_id: int, command: str) -> bool:
        """Remove command from allowed list."""
        if not await admin_auth.has_permission(admin_id, Permissions.MANAGE_SETTINGS):
            raise InsufficientPermissionError("No permission to manage command settings")
        
        settings = await self.get_community_settings(chat_id)
        
        # Normalize command
        command = command.lstrip('/')
        
        if command in settings.allowed_commands:
            allowed_commands = settings.allowed_commands.copy()
            allowed_commands.remove(command)
            
            await self.update_community_settings(admin_id, chat_id, {"allowed_commands": allowed_commands})
            
            logger.info(f"Command '{command}' removed from allowed list for chat {chat_id}")
            return True
        
        return False
    
    async def add_blocked_command(self, admin_id: int, chat_id: int, command: str) -> bool:
        """Add command to blocked list."""
        if not await admin_auth.has_permission(admin_id, Permissions.MANAGE_SETTINGS):
            raise InsufficientPermissionError("No permission to manage command settings")
        
        settings = await self.get_community_settings(chat_id)
        
        # Normalize command
        command = command.lstrip('/')
        
        if command not in settings.blocked_commands:
            blocked_commands = settings.blocked_commands.copy()
            blocked_commands.append(command)
            
            await self.update_community_settings(admin_id, chat_id, {"blocked_commands": blocked_commands})
            
            logger.info(f"Command '{command}' added to blocked list for chat {chat_id}")
            return True
        
        return False
    
    async def remove_blocked_command(self, admin_id: int, chat_id: int, command: str) -> bool:
        """Remove command from blocked list."""
        if not await admin_auth.has_permission(admin_id, Permissions.MANAGE_SETTINGS):
            raise InsufficientPermissionError("No permission to manage command settings")
        
        settings = await self.get_community_settings(chat_id)
        
        # Normalize command
        command = command.lstrip('/')
        
        if command in settings.blocked_commands:
            blocked_commands = settings.blocked_commands.copy()
            blocked_commands.remove(command)
            
            await self.update_community_settings(admin_id, chat_id, {"blocked_commands": blocked_commands})
            
            logger.info(f"Command '{command}' removed from blocked list for chat {chat_id}")
            return True
        
        return False
    
    async def is_command_allowed(self, chat_id: int, command: str) -> bool:
        """Check if command is allowed in the community."""
        settings = await self.get_community_settings(chat_id, create_if_missing=False)
        if not settings:
            return True  # Allow by default if no settings
        
        # Normalize command
        command = command.lstrip('/')
        
        # Check if command is explicitly blocked
        if command in settings.blocked_commands:
            return False
        
        # If there are allowed commands specified, check if command is in the list
        if settings.allowed_commands:
            return command in settings.allowed_commands
        
        # Allow by default if no restrictions
        return True
    
    async def should_auto_approve(self, chat_id: int) -> bool:
        """Check if auto-approval is enabled for the community."""
        settings = await self.get_community_settings(chat_id, create_if_missing=False)
        return not (settings and settings.manual_approval)
    
    async def is_ai_assistant_enabled(self, chat_id: int) -> bool:
        """Check if AI assistant is enabled for the community."""
        settings = await self.get_community_settings(chat_id, create_if_missing=False)
        if not settings:
            return True  # Enabled by default
        return settings.ai_assistant_enabled
    
    async def toggle_ai_assistant(self, admin_id: int, chat_id: int) -> bool:
        """Toggle AI assistant for the community."""
        if not await admin_auth.has_permission(admin_id, Permissions.MANAGE_COMMUNITY):
            raise InsufficientPermissionError("No permission to toggle AI assistant")
        
        settings = await self.get_community_settings(chat_id)
        new_status = not settings.ai_assistant_enabled
        
        await self.update_community_settings(admin_id, chat_id, {"ai_assistant_enabled": new_status})
        
        logger.info(f"AI assistant {'enabled' if new_status else 'disabled'} for chat {chat_id}")
        return new_status
    
    async def set_default_topic(self, admin_id: int, chat_id: int, topic_id: Optional[int]) -> bool:
        """Set default topic for the community."""
        if not await admin_auth.has_permission(admin_id, Permissions.CREATE_TOPIC):
            raise InsufficientPermissionError("No permission to set default topic")
        
        await self.update_community_settings(admin_id, chat_id, {"default_topic_id": topic_id})
        
        logger.info(f"Default topic set to {topic_id} for chat {chat_id}")
        return True
    
    async def get_welcome_message(self, chat_id: int) -> Optional[str]:
        """Get welcome message for new members."""
        settings = await self.get_community_settings(chat_id, create_if_missing=False)
        return settings.welcome_message if settings else None
    
    async def get_community_rules(self, chat_id: int) -> Optional[str]:
        """Get community rules."""
        settings = await self.get_community_settings(chat_id, create_if_missing=False)
        return settings.community_rules if settings else None
    
    async def send_welcome_message(self, chat_id: int, user_id: int, user_name: Optional[str] = None) -> bool:
        """Send welcome message to new member."""
        welcome_message = await self.get_welcome_message(chat_id)
        if not welcome_message:
            return False
        
        try:
            # Format welcome message with user info
            formatted_message = welcome_message.format(
                user_id=user_id,
                user_name=user_name or f"User {user_id}",
                chat_id=chat_id
            )
            
            # Send welcome message
            await self.telegram_client.send_message(
                chat_id=chat_id,
                text=formatted_message,
                parse_mode="Markdown"
            )
            
            # Also send community rules if available
            rules = await self.get_community_rules(chat_id)
            if rules:
                rules_message = f"📋 **Community Rules:**\n\n{rules}"
                await self.telegram_client.send_message(
                    chat_id=chat_id,
                    text=rules_message,
                    parse_mode="Markdown"
                )
            
            logger.info(f"Welcome message sent to user {user_id} in chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send welcome message: {e}")
            return False
    
    async def get_community_stats(self, admin_id: int) -> Dict[str, Any]:
        """Get community management statistics."""
        if not await admin_auth.has_permission(admin_id, Permissions.VIEW_ANALYTICS):
            raise InsufficientPermissionError("No permission to view analytics")
        
        async with get_db_session() as session:
            total_communities = session.query(CommunitySettings).count()
            auto_moderation_enabled = session.query(CommunitySettings).filter(
                CommunitySettings.auto_moderation == True
            ).count()
            manual_approval_enabled = session.query(CommunitySettings).filter(
                CommunitySettings.manual_approval == True
            ).count()
            ai_assistant_enabled = session.query(CommunitySettings).filter(
                CommunitySettings.ai_assistant_enabled == True
            ).count()
            
            return {
                "total_communities": total_communities,
                "auto_moderation_enabled": auto_moderation_enabled,
                "manual_approval_enabled": manual_approval_enabled,
                "ai_assistant_enabled": ai_assistant_enabled,
                "cached_settings": len(self.settings_cache)
            }
    
    async def list_communities(self, admin_id: int) -> List[CommunitySettings]:
        """List all managed communities."""
        if not await admin_auth.has_permission(admin_id, Permissions.VIEW_ANALYTICS):
            raise InsufficientPermissionError("No permission to view communities")
        
        async with get_db_session() as session:
            communities = session.query(CommunitySettings).order_by(
                CommunitySettings.chat_title
            ).all()
            
            return communities
    
    def clear_settings_cache(self, chat_id: Optional[int] = None):
        """Clear settings cache for specific chat or all chats."""
        if chat_id:
            self.settings_cache.pop(chat_id, None)
        else:
            self.settings_cache.clear()
        
        logger.info(f"Settings cache cleared for {'chat ' + str(chat_id) if chat_id else 'all chats'}")


# Global community manager instance
community_manager = None


def get_community_manager(telegram_client: TelegramClient) -> CommunityManager:
    """Get global community manager instance."""
    global community_manager
    if community_manager is None:
        community_manager = CommunityManager(telegram_client)
    return community_manager
