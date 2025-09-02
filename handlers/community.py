"""
Community handler for Kroolo Agent Bot
Handles group/community moderation and auto-functions
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from services.ai_service import AIService
from services.auth import AuthService
from utils.logger import log_user_action, log_admin_action
from datetime import datetime

logger = logging.getLogger(__name__)

class CommunityHandler:
    """Handles community-specific functionality and moderation"""
    
    def __init__(self, ai_service: AIService, auth_service: AuthService):
        self.ai_service = ai_service
        self.auth_service = auth_service
        
        # Community settings cache
        self.community_settings = {}
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages for community features"""
        if not update.message:
            return
        
        message = update.message
        chat_id = message.chat.id
        user = message.from_user
        text = message.text or ""
        
        # Skip if not a group chat
        if chat_id > 0:  # Private chat
            return
        
        # Create user if not exists
        if user:
            self.auth_service.create_user_if_not_exists(user.id, user.username)
        
        # Auto-moderation features
        await self._auto_moderation(update, context)
        
        # Auto-topic detection
        await self._auto_topic_detection(update, context)
        
        # Thread summarization for long conversations
        await self._check_thread_summarization(update, context)
    
    async def _auto_moderation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Auto-moderation for community messages"""
        message = update.message
        chat_id = message.chat.id
        user = message.from_user
        text = message.text or ""
        
        if not text or not user:
            return
        
        try:
            # Check for spam content
            spam_result = await self.ai_service.detect_spam(text)
            
            if spam_result.get("is_spam", False) and spam_result.get("confidence", 0) > 0.7:
                # High confidence spam detected
                await self._handle_spam_detection(update, context, spam_result)
                return
            
            # Check for inappropriate content (basic keyword filtering)
            inappropriate_words = ["spam", "scam", "buy now", "click here", "free money"]
            if any(word in text.lower() for word in inappropriate_words):
                await self._handle_inappropriate_content(update, context, text)
                return
                
        except Exception as e:
            logger.error(f"Error in auto-moderation: {e}")
    
    async def _handle_spam_detection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, spam_result: Dict):
        """Handle detected spam content"""
        message = update.message
        chat_id = message.chat.id
        user = message.from_user
        
        # Log the spam detection
        log_admin_action(
            user_id=user.id if user else 0,
            action="spam_detected",
            target_id=chat_id,
            details=f"Confidence: {spam_result.get('confidence', 0)}, Reasons: {spam_result.get('reasons', [])}"
        )
        
        # Send warning to user
        warning_text = (
            "⚠️ **Spam Detection Warning**\n\n"
            "Your message appears to contain spam content. "
            "Please ensure your messages are relevant to the community.\n\n"
            "If this is a false positive, contact a moderator."
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=warning_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_to_message_id=message.message_id
        )
        
        # If user has multiple warnings, consider temporary restriction
        # This would be implemented with a warning counter system
    
    async def _handle_inappropriate_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Handle inappropriate content"""
        message = update.message
        chat_id = message.chat.id
        user = message.from_user
        
        # Log the inappropriate content
        log_admin_action(
            user_id=user.id if user else 0,
            action="inappropriate_content",
            target_id=chat_id,
            details=f"Content: {text[:100]}..."
        )
        
        # Send gentle reminder
        reminder_text = (
            "💡 **Community Guidelines Reminder**\n\n"
            "Please ensure your messages follow community guidelines. "
            "If you need help, use `/help` to see available commands."
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=reminder_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_to_message_id=message.message_id
        )
    
    async def _auto_topic_detection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Auto-detect and suggest topics based on conversation"""
        message = update.message
        chat_id = message.chat.id
        text = message.text or ""
        
        if not text:
            return
        
        # Only run topic detection occasionally to avoid spam
        if hasattr(self, '_last_topic_check') and \
           (datetime.utcnow() - self._last_topic_check).seconds < 300:  # 5 minutes
            return
        
        try:
            # Get recent messages for context (simplified)
            context_text = text[:200]  # Use current message as context
            
            # Generate topic suggestions
            topics = await self.ai_service.generate_topic_suggestions(context_text)
            
            if topics and len(topics) > 0:
                # Store suggested topics for this chat
                if chat_id not in self.community_settings:
                    self.community_settings[chat_id] = {}
                
                self.community_settings[chat_id]['suggested_topics'] = topics
                self._last_topic_check = datetime.utcnow()
                
        except Exception as e:
            logger.error(f"Error in auto-topic detection: {e}")
    
    async def _check_thread_summarization(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check if thread needs summarization"""
        message = update.message
        chat_id = message.chat.id
        
        # This would check thread length and suggest summarization
        # For now, it's a placeholder for future implementation
        pass
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries for moderation actions"""
        if not update.callback_query:
            return
        
        callback_query = update.callback_query
        data = callback_query.data
        user = callback_query.from_user
        chat_id = callback_query.message.chat.id if callback_query.message else 0
        
        # Check if user has permission to moderate
        if not self.auth_service.is_moderator(user.id):
            await callback_query.answer("❌ You don't have permission to moderate.", show_alert=True)
            return
        
        try:
            if data.startswith("moderate_"):
                await self._handle_moderation_callback(update, context, data)
            elif data.startswith("topic_"):
                await self._handle_topic_callback(update, context, data)
            else:
                await callback_query.answer("Unknown action")
                
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
            await callback_query.answer("❌ Error processing action", show_alert=True)
    
    async def _handle_moderation_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle moderation-related callback queries"""
        callback_query = update.callback_query
        action = data.split("_")[1]
        target_id = data.split("_")[2] if len(data.split("_")) > 2 else None
        
        if action == "warn":
            await callback_query.answer("⚠️ Warning sent to user")
            # Implement warning logic
        elif action == "delete":
            await callback_query.answer("🗑️ Message deleted")
            # Implement message deletion logic
        elif action == "restrict":
            await callback_query.answer("🚫 User restricted")
            # Implement user restriction logic
    
    async def _handle_topic_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle topic-related callback queries"""
        callback_query = update.callback_query
        action = data.split("_")[1]
        topic = data.split("_")[2] if len(data.split("_")) > 2 else None
        
        if action == "set":
            await callback_query.answer(f"🎯 Topic set to: {topic}")
            # Implement topic setting logic
        elif action == "suggest":
            await callback_query.answer(f"💡 Topic suggestion: {topic}")
            # Implement topic suggestion logic
    
    async def get_community_topics(self, chat_id: int) -> List[str]:
        """Get current topics for a community"""
        if chat_id in self.community_settings:
            return self.community_settings[chat_id].get('suggested_topics', [])
        return []
    
    async def set_community_topic(self, chat_id: int, topic: str) -> bool:
        """Set a topic for a community"""
        try:
            if chat_id not in self.community_settings:
                self.community_settings[chat_id] = {}
            
            self.community_settings[chat_id]['current_topic'] = topic
            return True
        except Exception as e:
            logger.error(f"Error setting community topic: {e}")
            return False
    
    async def get_community_stats(self, chat_id: int) -> Dict[str, Any]:
        """Get community statistics"""
        try:
            # This would fetch real statistics from the database
            # For now, return placeholder data
            return {
                "chat_id": chat_id,
                "member_count": 0,  # Would be fetched from Telegram API
                "message_count": 0,  # Would be fetched from database
                "active_topics": self.community_settings.get(chat_id, {}).get('suggested_topics', []),
                "current_topic": self.community_settings.get(chat_id, {}).get('current_topic', "General Discussion")
            }
        except Exception as e:
            logger.error(f"Error getting community stats: {e}")
            return {"error": str(e)}
