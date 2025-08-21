"""
Admin authentication and authorization system for the Kroolo AI Bot.
Handles role-based access control, permission checking, and admin validation.
"""

import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
from functools import wraps
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from config.settings import settings
from src.database.session import get_db_session
from src.models.admin import (
    AdminUser, AdminRole, Permissions, DEFAULT_PERMISSIONS,
    BannedUser, MutedUser, AuditLog, AuditAction
)

logger = logging.getLogger(__name__)


class AdminAuthError(Exception):
    """Custom exception for admin authentication errors."""
    pass


class InsufficientPermissionError(AdminAuthError):
    """Raised when user lacks required permissions."""
    pass


class AdminAuthenticator:
    """Handles admin authentication and authorization."""
    
    def __init__(self):
        self.super_admin_ids = self._load_super_admin_ids()
        self._permission_cache = {}  # Cache for performance
        self._cache_expiry = {}
    
    def _load_super_admin_ids(self) -> List[int]:
        """Load super admin IDs from environment."""
        admin_ids_str = getattr(settings, 'bot_admin_ids', None) or getattr(settings, 'telegram_admin_ids', '123456789')
        
        try:
            if isinstance(admin_ids_str, str):
                admin_ids = [int(id_str.strip()) for id_str in admin_ids_str.split(',') if id_str.strip()]
            elif isinstance(admin_ids_str, (list, tuple)):
                admin_ids = [int(id_) for id_ in admin_ids_str]
            else:
                admin_ids = [int(admin_ids_str)]
            
            logger.info(f"Loaded {len(admin_ids)} super admin IDs")
            return admin_ids
            
        except (ValueError, TypeError) as e:
            logger.error(f"Error loading admin IDs: {e}")
            return [123456789]  # Fallback default
    
    async def is_super_admin(self, user_id: int) -> bool:
        """Check if user is a super admin."""
        return user_id in self.super_admin_ids
    
    async def get_admin_user(self, user_id: int) -> Optional[AdminUser]:
        """Get admin user from database."""
        async with get_db_session() as session:
            admin_user = session.query(AdminUser).filter(
                AdminUser.telegram_user_id == user_id,
                AdminUser.is_active == True
            ).first()
            
            # Auto-create super admin if not exists
            if not admin_user and await self.is_super_admin(user_id):
                admin_user = AdminUser(
                    telegram_user_id=user_id,
                    role=AdminRole.SUPER_ADMIN,
                    permissions=DEFAULT_PERMISSIONS[AdminRole.SUPER_ADMIN],
                    is_active=True
                )
                session.add(admin_user)
                session.commit()
                session.refresh(admin_user)
                logger.info(f"Auto-created super admin user: {user_id}")
            
            return admin_user
    
    async def get_user_permissions(self, user_id: int) -> List[str]:
        """Get user permissions with caching."""
        cache_key = f"perms_{user_id}"
        
        # Check cache
        if cache_key in self._permission_cache:
            if datetime.now() < self._cache_expiry.get(cache_key, datetime.min):
                return self._permission_cache[cache_key]
        
        # Get from database
        admin_user = await self.get_admin_user(user_id)
        if not admin_user:
            permissions = []
        else:
            # Combine role-based and custom permissions
            role_permissions = DEFAULT_PERMISSIONS.get(admin_user.role, [])
            custom_permissions = admin_user.permissions or []
            permissions = list(set(role_permissions + custom_permissions))
        
        # Cache for 5 minutes
        self._permission_cache[cache_key] = permissions
        self._cache_expiry[cache_key] = datetime.now() + timedelta(minutes=5)
        
        return permissions
    
    async def has_permission(self, user_id: int, permission: str) -> bool:
        """Check if user has specific permission."""
        permissions = await self.get_user_permissions(user_id)
        return permission in permissions
    
    async def has_any_permission(self, user_id: int, permissions: List[str]) -> bool:
        """Check if user has any of the specified permissions."""
        user_permissions = await self.get_user_permissions(user_id)
        return any(perm in user_permissions for perm in permissions)
    
    async def has_all_permissions(self, user_id: int, permissions: List[str]) -> bool:
        """Check if user has all specified permissions."""
        user_permissions = await self.get_user_permissions(user_id)
        return all(perm in user_permissions for perm in permissions)
    
    async def is_admin(self, user_id: int) -> bool:
        """Check if user is any type of admin."""
        admin_user = await self.get_admin_user(user_id)
        return admin_user is not None
    
    async def get_admin_role(self, user_id: int) -> Optional[AdminRole]:
        """Get user's admin role."""
        admin_user = await self.get_admin_user(user_id)
        return admin_user.role if admin_user else None
    
    async def is_user_banned(self, user_id: int) -> bool:
        """Check if user is banned."""
        async with get_db_session() as session:
            ban = session.query(BannedUser).filter(
                BannedUser.telegram_user_id == user_id,
                BannedUser.is_active == True,
                or_(
                    BannedUser.banned_until.is_(None),
                    BannedUser.banned_until > datetime.now()
                )
            ).first()
            return ban is not None
    
    async def is_user_muted(self, user_id: int, chat_id: int) -> bool:
        """Check if user is muted in specific chat."""
        async with get_db_session() as session:
            mute = session.query(MutedUser).filter(
                MutedUser.telegram_user_id == user_id,
                MutedUser.chat_id == chat_id,
                MutedUser.is_active == True,
                or_(
                    MutedUser.muted_until.is_(None),
                    MutedUser.muted_until > datetime.now()
                )
            ).first()
            return mute is not None
    
    async def promote_user(self, admin_id: int, target_user_id: int, role: AdminRole, 
                          permissions: Optional[List[str]] = None) -> AdminUser:
        """Promote user to admin role."""
        # Check permissions
        if not await self.has_permission(admin_id, Permissions.PROMOTE_USER):
            raise InsufficientPermissionError("No permission to promote users")
        
        async with get_db_session() as session:
            # Check if user is already admin
            existing_admin = session.query(AdminUser).filter(
                AdminUser.telegram_user_id == target_user_id
            ).first()
            
            if existing_admin:
                # Update existing admin
                existing_admin.role = role
                existing_admin.permissions = permissions or DEFAULT_PERMISSIONS.get(role, [])
                existing_admin.is_active = True
                admin_user = existing_admin
            else:
                # Create new admin
                admin_user = AdminUser(
                    telegram_user_id=target_user_id,
                    role=role,
                    permissions=permissions or DEFAULT_PERMISSIONS.get(role, []),
                    created_by_id=(await self.get_admin_user(admin_id)).id,
                    is_active=True
                )
                session.add(admin_user)
            
            session.commit()
            session.refresh(admin_user)
            
            # Log action
            await self.log_admin_action(
                admin_id, AuditAction.USER_PROMOTED, target_user_id,
                details={"role": role.value, "permissions": permissions}
            )
            
            # Clear cache
            self._clear_user_cache(target_user_id)
            
            return admin_user
    
    async def demote_user(self, admin_id: int, target_user_id: int) -> bool:
        """Demote user from admin role."""
        if not await self.has_permission(admin_id, Permissions.DEMOTE_USER):
            raise InsufficientPermissionError("No permission to demote users")
        
        async with get_db_session() as session:
            admin_user = session.query(AdminUser).filter(
                AdminUser.telegram_user_id == target_user_id,
                AdminUser.is_active == True
            ).first()
            
            if admin_user:
                admin_user.is_active = False
                session.commit()
                
                await self.log_admin_action(
                    admin_id, AuditAction.USER_DEMOTED, target_user_id
                )
                
                self._clear_user_cache(target_user_id)
                return True
            
            return False
    
    async def ban_user(self, admin_id: int, target_user_id: int, reason: Optional[str] = None,
                      duration: Optional[timedelta] = None) -> BannedUser:
        """Ban user from using the bot."""
        if not await self.has_permission(admin_id, Permissions.BAN_USER):
            raise InsufficientPermissionError("No permission to ban users")
        
        async with get_db_session() as session:
            # Check if already banned
            existing_ban = session.query(BannedUser).filter(
                BannedUser.telegram_user_id == target_user_id,
                BannedUser.is_active == True
            ).first()
            
            if existing_ban:
                # Update existing ban
                existing_ban.reason = reason or existing_ban.reason
                existing_ban.banned_until = (datetime.now() + duration) if duration else None
                existing_ban.banned_by_id = (await self.get_admin_user(admin_id)).id
                banned_user = existing_ban
            else:
                # Create new ban
                banned_user = BannedUser(
                    telegram_user_id=target_user_id,
                    reason=reason,
                    banned_by_id=(await self.get_admin_user(admin_id)).id,
                    banned_until=(datetime.now() + duration) if duration else None,
                    is_active=True
                )
                session.add(banned_user)
            
            session.commit()
            session.refresh(banned_user)
            
            await self.log_admin_action(
                admin_id, AuditAction.USER_BANNED, target_user_id,
                details={"reason": reason, "duration": str(duration) if duration else "permanent"}
            )
            
            return banned_user
    
    async def unban_user(self, admin_id: int, target_user_id: int) -> bool:
        """Unban user."""
        if not await self.has_permission(admin_id, Permissions.UNBAN_USER):
            raise InsufficientPermissionError("No permission to unban users")
        
        async with get_db_session() as session:
            banned_user = session.query(BannedUser).filter(
                BannedUser.telegram_user_id == target_user_id,
                BannedUser.is_active == True
            ).first()
            
            if banned_user:
                banned_user.is_active = False
                session.commit()
                
                await self.log_admin_action(
                    admin_id, AuditAction.USER_UNBANNED, target_user_id
                )
                return True
            
            return False
    
    async def mute_user(self, admin_id: int, target_user_id: int, chat_id: int,
                       reason: Optional[str] = None, duration: Optional[timedelta] = None) -> MutedUser:
        """Mute user in specific chat."""
        if not await self.has_permission(admin_id, Permissions.MUTE_USER):
            raise InsufficientPermissionError("No permission to mute users")
        
        async with get_db_session() as session:
            # Check if already muted
            existing_mute = session.query(MutedUser).filter(
                MutedUser.telegram_user_id == target_user_id,
                MutedUser.chat_id == chat_id,
                MutedUser.is_active == True
            ).first()
            
            if existing_mute:
                # Update existing mute
                existing_mute.reason = reason or existing_mute.reason
                existing_mute.muted_until = (datetime.now() + duration) if duration else None
                existing_mute.muted_by_id = (await self.get_admin_user(admin_id)).id
                muted_user = existing_mute
            else:
                # Create new mute
                muted_user = MutedUser(
                    telegram_user_id=target_user_id,
                    chat_id=chat_id,
                    reason=reason,
                    muted_by_id=(await self.get_admin_user(admin_id)).id,
                    muted_until=(datetime.now() + duration) if duration else None,
                    is_active=True
                )
                session.add(muted_user)
            
            session.commit()
            session.refresh(muted_user)
            
            await self.log_admin_action(
                admin_id, AuditAction.USER_MUTED, target_user_id, chat_id,
                details={"reason": reason, "duration": str(duration) if duration else "permanent"}
            )
            
            return muted_user
    
    async def unmute_user(self, admin_id: int, target_user_id: int, chat_id: int) -> bool:
        """Unmute user in specific chat."""
        if not await self.has_permission(admin_id, Permissions.UNMUTE_USER):
            raise InsufficientPermissionError("No permission to unmute users")
        
        async with get_db_session() as session:
            muted_user = session.query(MutedUser).filter(
                MutedUser.telegram_user_id == target_user_id,
                MutedUser.chat_id == chat_id,
                MutedUser.is_active == True
            ).first()
            
            if muted_user:
                muted_user.is_active = False
                session.commit()
                
                await self.log_admin_action(
                    admin_id, AuditAction.USER_UNMUTED, target_user_id, chat_id
                )
                return True
            
            return False
    
    async def log_admin_action(self, admin_id: int, action: AuditAction, 
                              target_user_id: Optional[int] = None, chat_id: Optional[int] = None,
                              details: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None,
                              user_agent: Optional[str] = None):
        """Log admin action for audit purposes."""
        async with get_db_session() as session:
            admin_user = await self.get_admin_user(admin_id)
            if not admin_user:
                logger.error(f"Cannot log action for non-admin user: {admin_id}")
                return
            
            audit_log = AuditLog(
                admin_id=admin_user.id,
                action=action,
                target_user_id=target_user_id,
                chat_id=chat_id,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent
            )
            session.add(audit_log)
            session.commit()
    
    async def get_audit_logs(self, admin_id: int, limit: int = 50, offset: int = 0) -> List[AuditLog]:
        """Get audit logs (requires view_logs permission)."""
        if not await self.has_permission(admin_id, Permissions.VIEW_LOGS):
            raise InsufficientPermissionError("No permission to view logs")
        
        async with get_db_session() as session:
            logs = session.query(AuditLog).order_by(
                AuditLog.created_at.desc()
            ).offset(offset).limit(limit).all()
            return logs
    
    def _clear_user_cache(self, user_id: int):
        """Clear cached permissions for user."""
        cache_key = f"perms_{user_id}"
        if cache_key in self._permission_cache:
            del self._permission_cache[cache_key]
        if cache_key in self._cache_expiry:
            del self._cache_expiry[cache_key]
    
    async def update_admin_activity(self, user_id: int):
        """Update last activity timestamp for admin."""
        async with get_db_session() as session:
            admin_user = session.query(AdminUser).filter(
                AdminUser.telegram_user_id == user_id,
                AdminUser.is_active == True
            ).first()
            
            if admin_user:
                admin_user.last_activity = datetime.now()
                session.commit()


# Global authenticator instance
admin_auth = AdminAuthenticator()


# Decorators for permission checking

def require_admin(func):
    """Decorator to require admin privileges."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract user_id from args/kwargs
        user_id = kwargs.get('user_id') or (args[0] if args else None)
        if not user_id:
            raise AdminAuthError("User ID not provided")
        
        if not await admin_auth.is_admin(user_id):
            raise AdminAuthError("Admin privileges required")
        
        await admin_auth.update_admin_activity(user_id)
        return await func(*args, **kwargs)
    return wrapper


def require_permission(permission: str):
    """Decorator to require specific permission."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get('user_id') or (args[0] if args else None)
            if not user_id:
                raise AdminAuthError("User ID not provided")
            
            if not await admin_auth.has_permission(user_id, permission):
                raise InsufficientPermissionError(f"Permission '{permission}' required")
            
            await admin_auth.update_admin_activity(user_id)
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(*permissions: str):
    """Decorator to require any of the specified permissions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get('user_id') or (args[0] if args else None)
            if not user_id:
                raise AdminAuthError("User ID not provided")
            
            if not await admin_auth.has_any_permission(user_id, list(permissions)):
                raise InsufficientPermissionError(f"One of these permissions required: {', '.join(permissions)}")
            
            await admin_auth.update_admin_activity(user_id)
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_super_admin(func):
    """Decorator to require super admin privileges."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        user_id = kwargs.get('user_id') or (args[0] if args else None)
        if not user_id:
            raise AdminAuthError("User ID not provided")
        
        if not await admin_auth.is_super_admin(user_id):
            raise AdminAuthError("Super admin privileges required")
        
        await admin_auth.update_admin_activity(user_id)
        return await func(*args, **kwargs)
    return wrapper
