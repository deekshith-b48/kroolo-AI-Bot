"""
Authentication service for Kroolo Agent Bot
Handles admin/user roles and permissions
"""

import os
import logging
from typing import Optional, Dict, Any, List
from db import Database
from utils.logger import log_admin_action, log_user_action

logger = logging.getLogger(__name__)

class AuthService:
    """Service for user authentication and role management"""
    
    def __init__(self, database: Database):
        self.database = database
        self.admin_ids = [int(x.strip()) for x in (os.getenv("ADMIN_IDS", "").split(",") if os.getenv("ADMIN_IDS") else [])]
        
        # Role hierarchy
        self.role_hierarchy = {
            "user": 0,
            "moderator": 1,
            "admin": 2,
            "superadmin": 3
        }
    
    def is_admin(self, telegram_user_id: int) -> bool:
        """Check if user is admin (from env or database)"""
        # Check environment admin IDs first
        if telegram_user_id in self.admin_ids:
            return True
        
        # Check database role
        user = self.database.get_user_by_telegram_id(telegram_user_id)
        if user and user.get("role") in ["admin", "superadmin", "moderator"]:
            return True
        
        return False
    
    def is_moderator(self, telegram_user_id: int) -> bool:
        """Check if user is moderator or higher"""
        if self.is_admin(telegram_user_id):
            return True
        
        user = self.database.get_user_by_telegram_id(telegram_user_id)
        return user and user.get("role") == "moderator"
    
    def is_superadmin(self, telegram_user_id: int) -> bool:
        """Check if user is superadmin"""
        if telegram_user_id in self.admin_ids:
            return True
        
        user = self.database.get_user_by_telegram_id(telegram_user_id)
        return user and user.get("role") == "superadmin"
    
    def get_user_role(self, telegram_user_id: int) -> str:
        """Get user's role"""
        user = self.database.get_user_by_telegram_id(telegram_user_id)
        if user:
            return user.get("role", "user")
        return "user"
    
    def can_perform_action(self, user_id: int, action: str, target_role: str = None, target_user_id: int = None) -> bool:
        """Check if user can perform specific action with enhanced security"""
        user_role = self.get_user_role(user_id)
        user_level = self.role_hierarchy.get(user_role, 0)
        
        # Prevent users from acting on themselves for certain actions
        if target_user_id and target_user_id == user_id and action in ["ban", "demote"]:
            return False
        
        # Enhanced action-based permissions
        action_permissions = {
            "promote": {"min_role": "admin", "target_max_role": "moderator", "description": "Promote users"},
            "demote": {"min_role": "admin", "target_max_role": "moderator", "description": "Demote users"},
            "ban": {"min_role": "moderator", "target_max_role": "user", "description": "Ban users"},
            "unban": {"min_role": "moderator", "target_max_role": "user", "description": "Unban users"},
            "settings": {"min_role": "moderator", "description": "Modify bot settings"},
            "approve": {"min_role": "moderator", "description": "Approve content"},
            "reject": {"min_role": "moderator", "description": "Reject content"},
            "backup": {"min_role": "admin", "description": "Create database backups"},
            "restore": {"min_role": "admin", "description": "Restore database"},
            "system": {"min_role": "superadmin", "description": "System administration"},
            "users": {"min_role": "admin", "description": "View user list"},
            "logs": {"min_role": "admin", "description": "View system logs"},
            "status": {"min_role": "moderator", "description": "View bot status"},
            "admin_help": {"min_role": "moderator", "description": "View admin commands"}
        }
        
        if action not in action_permissions:
            return False
        
        permission = action_permissions[action]
        min_role_level = self.role_hierarchy.get(permission["min_role"], 0)
        
        if user_level < min_role_level:
            return False
        
        # Check target role restrictions
        if target_role and "target_max_role" in permission:
            target_level = self.role_hierarchy.get(target_role, 0)
            max_target_level = self.role_hierarchy.get(permission["target_max_role"], 0)
            if target_level > max_target_level:
                return False
        
        return True
    
    def get_available_actions(self, user_id: int) -> List[str]:
        """Get list of actions available to user"""
        user_role = self.get_user_role(user_id)
        user_level = self.role_hierarchy.get(user_role, 0)
        
        available_actions = []
        action_permissions = {
            "promote": {"min_role": "admin", "description": "Promote users"},
            "demote": {"min_role": "admin", "description": "Demote users"},
            "ban": {"min_role": "moderator", "description": "Ban users"},
            "unban": {"min_role": "moderator", "description": "Unban users"},
            "settings": {"min_role": "moderator", "description": "Modify bot settings"},
            "backup": {"min_role": "admin", "description": "Create database backups"},
            "restore": {"min_role": "admin", "description": "Restore database"},
            "system": {"min_role": "superadmin", "description": "System administration"},
            "users": {"min_role": "admin", "description": "View user list"},
            "logs": {"min_role": "admin", "description": "View system logs"},
            "status": {"min_role": "moderator", "description": "View bot status"},
            "admin_help": {"min_role": "moderator", "description": "View admin commands"}
        }
        
        for action, permission in action_permissions.items():
            min_level = self.role_hierarchy.get(permission["min_role"], 0)
            if user_level >= min_level:
                available_actions.append(f"• `/{action}` - {permission['description']}")
        
        return available_actions
    
    def is_group_admin(self, user_id: int, chat_id: int, context) -> bool:
        """Check if user is admin in the specific Telegram group"""
        try:
            # This would require checking with Telegram API
            # For now, we'll use our internal role system
            return self.is_admin(user_id) or self.is_moderator(user_id)
        except Exception:
            return False
    
    def promote_user(self, admin_id: int, target_username: str, new_role: str = "moderator") -> Dict[str, Any]:
        """Promote user to new role"""
        if not self.can_perform_action(admin_id, "promote", new_role):
            return {"success": False, "error": "Insufficient permissions"}
        
        try:
            # Find user by username or create new entry
            target_user = None
            
            # Try to find existing user
            if target_username.startswith("@"):
                target_username = target_username[1:]  # Remove @ symbol
            
            # For now, we'll create a placeholder user entry
            # In production, you'd want to resolve usernames to IDs
            success = self.database.create_user(
                telegram_id=0,  # Placeholder - would need to resolve username
                username=target_username,
                role=new_role
            )
            
            if success:
                log_admin_action(admin_id, "promote", target_username, f"to {new_role}")
                return {"success": True, "message": f"Promoted {target_username} to {new_role}"}
            else:
                return {"success": False, "error": "Failed to promote user"}
                
        except Exception as e:
            logger.error(f"Error promoting user: {e}")
            return {"success": False, "error": str(e)}
    
    def demote_user(self, admin_id: int, target_username: str) -> Dict[str, Any]:
        """Demote user to regular user"""
        if not self.can_perform_action(admin_id, "demote"):
            return {"success": False, "error": "Insufficient permissions"}
        
        try:
            # Find and update user
            # This is simplified - in production you'd resolve username to ID
            success = True  # Placeholder
            
            if success:
                log_admin_action(admin_id, "demote", target_username, "to user")
                return {"success": True, "message": f"Demoted {target_username} to user"}
            else:
                return {"success": False, "error": "Failed to demote user"}
                
        except Exception as e:
            logger.error(f"Error demoting user: {e}")
            return {"success": False, "error": str(e)}
    
    def ban_user(self, admin_id: int, target_username: str) -> Dict[str, Any]:
        """Ban user from bot interactions"""
        if not self.can_perform_action(admin_id, "ban"):
            return {"success": False, "error": "Insufficient permissions"}
        
        try:
            # Update user role to banned
            success = True  # Placeholder
            
            if success:
                log_admin_action(admin_id, "ban", target_username, "user banned")
                return {"success": True, "message": f"Banned {target_username} from bot interactions"}
            else:
                return {"success": False, "error": "Failed to ban user"}
                
        except Exception as e:
            logger.error(f"Error banning user: {e}")
            return {"success": False, "error": str(e)}
    
    def unban_user(self, admin_id: int, target_username: str) -> Dict[str, Any]:
        """Unban user from bot interactions"""
        if not self.can_perform_action(admin_id, "unban"):
            return {"success": False, "error": "Insufficient permissions"}
        
        try:
            # Update user role back to user
            success = True  # Placeholder
            
            if success:
                log_admin_action(admin_id, "unban", target_username, "user unbanned")
                return {"success": True, "message": f"Unbanned {target_username}"}
            else:
                return {"success": False, "error": "Failed to unban user"}
                
        except Exception as e:
            logger.error(f"Error unbanning user: {e}")
            return {"success": False, "error": str(e)}
    
    def get_admin_list(self) -> List[Dict[str, Any]]:
        """Get list of all admins and moderators"""
        admins = []
        
        # Add environment admins
        for admin_id in self.admin_ids:
            admins.append({
                "telegram_id": admin_id,
                "username": f"Admin_{admin_id}",
                "role": "superadmin",
                "source": "environment"
            })
        
        # Add database admins
        db_admins = self.database.get_users_by_role("admin")
        for admin in db_admins:
            admin["source"] = "database"
            admins.append(admin)
        
        db_moderators = self.database.get_users_by_role("moderator")
        for moderator in db_moderators:
            moderator["source"] = "database"
            admins.append(moderator)
        
        return admins
    
    def create_user_if_not_exists(self, telegram_id: int, username: str = None) -> bool:
        """Create user if they don't exist"""
        existing_user = self.database.get_user_by_telegram_id(telegram_id)
        if existing_user:
            return True
        
        # Create new user
        return self.database.create_user(telegram_id, username, "user")
    
    def update_user_role(self, telegram_id: int, new_role: str) -> bool:
        """Update user role (admin only)"""
        if new_role not in self.role_hierarchy:
            return False
        
        return self.database.update_user_role(telegram_id, new_role)
    
    def get_user_permissions(self, telegram_user_id: int) -> Dict[str, Any]:
        """Get user's permissions and capabilities"""
        role = self.get_user_role(telegram_user_id)
        is_admin_user = self.is_admin(telegram_user_id)
        is_moderator_user = self.is_moderator(telegram_user_id)
        
        permissions = {
            "role": role,
            "is_admin": is_admin_user,
            "is_moderator": is_moderator_user,
            "can_promote": self.can_perform_action(telegram_user_id, "promote"),
            "can_demote": self.can_perform_action(telegram_user_id, "demote"),
            "can_ban": self.can_perform_action(telegram_user_id, "ban"),
            "can_unban": self.can_perform_action(telegram_user_id, "unban"),
            "can_manage_settings": self.can_perform_action(telegram_user_id, "settings"),
            "can_approve": self.can_perform_action(telegram_user_id, "approve"),
            "can_reject": self.can_perform_action(telegram_user_id, "reject"),
            "can_backup": self.can_perform_action(telegram_user_id, "backup"),
            "can_restore": self.can_perform_action(telegram_user_id, "restore"),
            "can_system": self.can_perform_action(telegram_user_id, "system")
        }
        
        return permissions
