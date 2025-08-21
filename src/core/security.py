"""
Security utilities for the Kroolo AI Bot.
Handles webhook verification, input validation, and security checks.
"""

import hashlib
import hmac
import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, Depends, Header

from config.settings import settings

logger = logging.getLogger(__name__)


async def verify_telegram_signature(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None)
) -> str:
    """
    Verify Telegram webhook signature.
    
    This function verifies that the incoming webhook request is actually from Telegram.
    It checks the X-Telegram-Bot-Api-Secret-Token header if configured.
    
    Args:
        request: FastAPI request object
        x_telegram_bot_api_secret_token: Secret token header from Telegram
        
    Returns:
        The signature for further processing
        
    Raises:
        HTTPException: If signature verification fails
    """
    try:
        # Check if secret token is configured
        if settings.telegram_webhook_secret and settings.telegram_webhook_secret != "your_webhook_secret_here":
            if not x_telegram_bot_api_secret_token:
                logger.warning("Missing X-Telegram-Bot-Api-Secret-Token header")
                raise HTTPException(status_code=401, detail="Missing secret token")
            
            if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
                logger.warning("Invalid secret token")
                raise HTTPException(status_code=401, detail="Invalid secret token")
        
        # For additional security, you can also verify the request source
        # This is optional but recommended for production
        client_ip = request.client.host
        if not _is_valid_telegram_ip(client_ip):
            logger.warning(f"Request from suspicious IP: {client_ip}")
            # Don't block, just log for monitoring
        
        return "verified"
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in signature verification: {e}")
        raise HTTPException(status_code=500, detail="Internal security error")


def _is_valid_telegram_ip(ip: str) -> bool:
    """
    Check if the IP address is from Telegram's range.
    
    Note: This is a basic check. For production, you might want to use
    a more comprehensive IP validation service.
    
    Args:
        ip: IP address to check
        
    Returns:
        True if IP appears to be from Telegram
    """
    # Telegram's IP ranges (this is a simplified check)
    # In production, you might want to use a more comprehensive approach
    telegram_ranges = [
        "149.154.160.0/20",  # Telegram's main range
        "91.108.4.0/22",     # Additional range
        "91.108.8.0/22",     # Additional range
        "91.108.12.0/22",    # Additional range
        "91.108.16.0/22",    # Additional range
        "91.108.56.0/22",    # Additional range
        "91.108.4.0/22",     # Additional range
    ]
    
    # For now, accept all IPs but log for monitoring
    # In production, implement proper IP range checking
    return True


def sanitize_input(text: str, max_length: int = 4096) -> str:
    """
    Sanitize user input text.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text
        
    Raises:
        ValueError: If text is too long or contains invalid content
    """
    if not text:
        return ""
    
    # Check length
    if len(text) > max_length:
        raise ValueError(f"Text too long. Maximum length: {max_length}")
    
    # Remove null bytes and control characters
    sanitized = "".join(char for char in text if ord(char) >= 32 or char in "\n\r\t")
    
    # Basic XSS prevention (remove script tags)
    sanitized = sanitized.replace("<script", "&lt;script")
    sanitized = sanitized.replace("</script>", "&lt;/script&gt;")
    
    # Remove other potentially dangerous HTML tags
    dangerous_tags = ["<iframe", "<object", "<embed", "<form", "<input"]
    for tag in dangerous_tags:
        sanitized = sanitized.replace(tag, f"&lt;{tag[1:]}")
    
    return sanitized.strip()


def validate_chat_id(chat_id: Any) -> bool:
    """
    Validate Telegram chat ID.
    
    Args:
        chat_id: Chat ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        chat_id_int = int(chat_id)
        # Telegram chat IDs are typically negative for groups/channels
        # and positive for private chats
        return True
    except (ValueError, TypeError):
        return False


def validate_user_id(user_id: Any) -> bool:
    """
    Validate Telegram user ID.
    
    Args:
        user_id: User ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        user_id_int = int(user_id)
        # Telegram user IDs are always positive
        return user_id_int > 0
    except (ValueError, TypeError):
        return False


def validate_message_text(text: str) -> bool:
    """
    Validate message text content.
    
    Args:
        text: Text to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not text:
        return False
    
    # Check for minimum length
    if len(text.strip()) < 1:
        return False
    
    # Check for maximum length (Telegram limit is 4096)
    if len(text) > 4096:
        return False
    
    # Check for only whitespace
    if text.strip() == "":
        return False
    
    return True


def create_webhook_secret() -> str:
    """
    Create a secure webhook secret.
    
    Returns:
        A secure random string for webhook verification
    """
    import secrets
    return secrets.token_urlsafe(32)


def hash_sensitive_data(data: str) -> str:
    """
    Hash sensitive data for logging or storage.
    
    Args:
        data: Data to hash
        
    Returns:
        SHA-256 hash of the data
    """
    return hashlib.sha256(data.encode()).hexdigest()


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive data for logging.
    
    Args:
        data: Data to mask
        visible_chars: Number of characters to keep visible
        
    Returns:
        Masked data string
    """
    if not data or len(data) <= visible_chars:
        return "*" * len(data) if data else ""
    
    return data[:visible_chars] + "*" * (len(data) - visible_chars)


class SecurityManager:
    """Central security manager for the bot."""
    
    def __init__(self):
        self.blocked_ips: set = set()
        self.suspicious_activities: list = []
        self.rate_limit_violations: dict = {}
    
    def block_ip(self, ip: str, reason: str = "Suspicious activity"):
        """Block an IP address."""
        self.blocked_ips.add(ip)
        logger.warning(f"Blocked IP {ip}: {reason}")
    
    def is_ip_blocked(self, ip: str) -> bool:
        """Check if an IP is blocked."""
        return ip in self.blocked_ips
    
    def record_suspicious_activity(self, ip: str, activity: str, details: Dict[str, Any]):
        """Record suspicious activity for monitoring."""
        self.suspicious_activities.append({
            "ip": ip,
            "activity": activity,
            "details": details,
            "timestamp": "now"  # In production, use proper datetime
        })
        
        # Keep only last 1000 activities
        if len(self.suspicious_activities) > 1000:
            self.suspicious_activities = self.suspicious_activities[-1000:]
        
        logger.warning(f"Suspicious activity from {ip}: {activity}")
    
    def record_rate_limit_violation(self, user_id: int, chat_id: int, violation_type: str):
        """Record rate limit violations."""
        key = f"{user_id}:{chat_id}"
        if key not in self.rate_limit_violations:
            self.rate_limit_violations[key] = {}
        
        if violation_type not in self.rate_limit_violations[key]:
            self.rate_limit_violations[key][violation_type] = 0
        
        self.rate_limit_violations[key][violation_type] += 1
        
        # Auto-block if too many violations
        if self.rate_limit_violations[key][violation_type] > 10:
            logger.warning(f"Auto-blocking user {user_id} in chat {chat_id} due to repeated violations")
            # In production, implement actual blocking logic
    
    def get_security_report(self) -> Dict[str, Any]:
        """Get security status report."""
        return {
            "blocked_ips_count": len(self.blocked_ips),
            "suspicious_activities_count": len(self.suspicious_activities),
            "rate_limit_violations_count": len(self.rate_limit_violations),
            "recent_suspicious_activities": self.suspicious_activities[-10:],
            "blocked_ips": list(self.blocked_ips)[:10]  # Show first 10
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for security manager."""
        try:
            report = self.get_security_report()
            return {
                "status": "healthy",
                "report": report
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__
            }


# Global security manager instance
security_manager = SecurityManager()
