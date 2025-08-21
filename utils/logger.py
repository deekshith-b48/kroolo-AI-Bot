"""
Logging utilities for Kroolo Agent Bot
Structured logging with different levels
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

class BotLogger:
    """Centralized logger for the bot"""
    
    def __init__(self, name: str = "krooloAgentBot", level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup console and file handlers"""
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = StructuredFormatter()
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler for errors
        try:
            file_handler = logging.FileHandler("bot_errors.log")
            file_handler.setLevel(logging.ERROR)
            file_formatter = StructuredFormatter()
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            # If file logging fails, just log to console
            self.logger.warning(f"Failed to setup file logging: {e}")
    
    def info(self, message: str, extra_fields: Optional[Dict[str, Any]] = None):
        """Log info message with optional extra fields"""
        if extra_fields:
            self.logger.info(message, extra={"extra_fields": extra_fields})
        else:
            self.logger.info(message)
    
    def warning(self, message: str, extra_fields: Optional[Dict[str, Any]] = None):
        """Log warning message with optional extra fields"""
        if extra_fields:
            self.logger.warning(message, extra={"extra_fields": extra_fields})
        else:
            self.logger.warning(message)
    
    def error(self, message: str, extra_fields: Optional[Dict[str, Any]] = None):
        """Log error message with optional extra fields"""
        if extra_fields:
            self.logger.error(message, extra={"extra_fields": extra_fields})
        else:
            self.logger.error(message)
    
    def critical(self, message: str, extra_fields: Optional[Dict[str, Any]] = None):
        """Log critical message with optional extra fields"""
        if extra_fields:
            self.logger.critical(message, extra={"extra_fields": extra_fields})
        else:
            self.logger.critical(message)
    
    def exception(self, message: str, extra_fields: Optional[Dict[str, Any]] = None):
        """Log exception with traceback"""
        if extra_fields:
            self.logger.exception(message, extra={"extra_fields": extra_fields})
        else:
            self.logger.exception(message)

# Global logger instance
logger = BotLogger()

def log_user_action(user_id: int, chat_id: int, action: str, details: str = "", level: str = "info"):
    """Log user actions with structured data"""
    extra_fields = {
        "user_id": user_id,
        "chat_id": chat_id,
        "action": action,
        "details": details,
        "log_type": "user_action"
    }
    
    getattr(logger, level)(f"User action: {action}", extra_fields)

def log_bot_action(action: str, details: str = "", level: str = "info"):
    """Log bot actions with structured data"""
    extra_fields = {
        "action": action,
        "details": details,
        "log_type": "bot_action"
    }
    
    getattr(logger, level)(f"Bot action: {action}", extra_fields)

def log_admin_action(admin_id: int, action: str, target: str = "", details: str = "", level: str = "info"):
    """Log admin actions with structured data"""
    extra_fields = {
        "admin_id": admin_id,
        "action": action,
        "target": target,
        "details": details,
        "log_type": "admin_action"
    }
    
    getattr(logger, level)(f"Admin action: {action} on {target}", extra_fields)

def log_error(error: Exception, context: str = "", extra_fields: Optional[Dict[str, Any]] = None):
    """Log errors with context and optional extra fields"""
    error_fields = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context,
        "log_type": "error"
    }
    
    if extra_fields:
        error_fields.update(extra_fields)
    
    logger.error(f"Error in {context}: {str(error)}", error_fields)

def log_rate_limit(user_id: int, chat_id: int, action: str):
    """Log rate limit events"""
    extra_fields = {
        "user_id": user_id,
        "chat_id": chat_id,
        "action": action,
        "log_type": "rate_limit"
    }
    
    logger.warning(f"Rate limit exceeded for user {user_id} in chat {chat_id}", extra_fields)

def log_api_call(api_name: str, endpoint: str, status: str, response_time: float, extra_fields: Optional[Dict[str, Any]] = None):
    """Log API calls with performance metrics"""
    api_fields = {
        "api_name": api_name,
        "endpoint": endpoint,
        "status": status,
        "response_time": response_time,
        "log_type": "api_call"
    }
    
    if extra_fields:
        api_fields.update(extra_fields)
    
    logger.info(f"API call to {api_name}: {endpoint} - {status} ({response_time:.2f}s)", api_fields)
