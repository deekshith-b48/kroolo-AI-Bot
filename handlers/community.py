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
        
        # Check for bot mentions
        if context.bot.username and f"@{context.bot.username}" in text:
            await self._handle_bot_mention(update, context)
            return
        
        # Auto-moderation features
        await self._auto_moderation(update, context)
        
        # Auto-topic detection
        await self._auto_topic_detection(update, context)
        
        # Thread summarization for long conversations
        await self._check_thread_summarization(update, context)
    
    async def _handle_bot_mention(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle when bot is mentioned in chat"""
        message = update.message
        chat_id = message.chat.id
        user = message.from_user
        text = message.text or ""
        
        # Extract the query after bot mention
        bot_username = context.bot.username
        query = text.replace(f"@{bot_username}", "").strip()
        
        if not query:
            await context.bot.send_message(
                chat_id=chat_id,
                text="👋 Hi! I'm here to help. What would you like to know?",
                reply_to_message_id=message.message_id
            )
            return
        
        # Check if user is banned
        if user and self.auth_service.get_user_role(user.id) == "banned":
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ You are banned from using this bot. Contact an administrator.",
                reply_to_message_id=message.message_id
            )
            return
        
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        try:
            # Get AI response
            answer = await self.ai_service.ask_ai(query)
            
            # Send response
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🤖 **AI Response:**\n\n{answer}",
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=message.message_id
            )
            
            # Log action
            if user:
                log_user_action(user.id, chat_id, "bot_mention", query)
                
        except Exception as e:
            logger.error(f"Error handling bot mention: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Sorry, I encountered an error. Please try again later.",
                reply_to_message_id=message.message_id
            )
    
    async def _auto_moderation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Auto-moderation features"""
        message = update.message
        chat_id = message.chat.id
        user = message.from_user
        text = message.text or ""
        
        # Skip if message is too short for analysis
        if len(text) < 10:
            return
        
        try:
            # Check for potential spam
            spam_analysis = await self.ai_service.detect_spam(text)
            
            if spam_analysis.get("is_spam", False) and spam_analysis.get("confidence", 0) > 0.7:
                await self._handle_potential_spam(update, context, spam_analysis)
            
            # Check for inappropriate content
            if any(word in text.lower() for word in ["spam", "scam", "click here", "free money"]):
                await self._flag_suspicious_content(update, context, text)
                
        except Exception as e:
            logger.error(f"Error in auto-moderation: {e}")
    
    async def _handle_potential_spam(self, update: Update, context: ContextTypes.DEFAULT_TYPE, spam_analysis: Dict[str, Any]):
        """Handle potential spam messages"""
        message = update.message
        chat_id = message.chat.id
        user = message.from_user
        
        # Create moderation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"mod_approve_{message.message_id}"),
                InlineKeyboardButton("❌ Remove", callback_data=f"mod_remove_{message.message_id}")
            ],
            [
                InlineKeyboardButton("🚫 Ban User", callback_data=f"mod_ban_{user.id if user else 0}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send moderation alert to admins
        admin_message = (
            f"🚨 **Potential Spam Detected**\n\n"
            f"**User:** {user.first_name if user else 'Unknown'} (@{user.username if user else 'N/A'})\n"
            f"**Confidence:** {spam_analysis.get('confidence', 0):.2f}\n"
            f"**Reasons:** {', '.join(spam_analysis.get('reasons', []))}\n\n"
            f"**Message:** {message.text[:100]}{'...' if len(message.text) > 100 else ''}"
        )
        
        # Find admins in the chat and notify them
        await self._notify_admins(context, chat_id, admin_message, reply_markup)
        
        # Log moderation action
        if user:
            log_user_action(user.id, chat_id, "spam_detected", f"confidence: {spam_analysis.get('confidence', 0)}")
    
    async def _flag_suspicious_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Flag suspicious content for admin review"""
        message = update.message
        chat_id = message.chat.id
        user = message.from_user
        
        # Create moderation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Allow", callback_data=f"mod_allow_{message.message_id}"),
                InlineKeyboardButton("⚠️ Warn", callback_data=f"mod_warn_{user.id if user else 0}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send moderation alert
        admin_message = (
            f"⚠️ **Suspicious Content Flagged**\n\n"
            f"**User:** {user.first_name if user else 'Unknown'} (@{user.username if user else 'N/A'})\n"
            f"**Content:** {text[:100]}{'...' if len(text) > 100 else ''}\n\n"
            f"**Action Required:** Review and take appropriate action."
        )
        
        await self._notify_admins(context, chat_id, admin_message, reply_markup)
    
    async def _notify_admins(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, message: str, reply_markup: InlineKeyboardMarkup):
        """Notify admins about moderation issues"""
        try:
            # Get chat administrators
            chat_member = await context.bot.get_chat_administrators(chat_id)
            admin_ids = [member.user.id for member in chat_member]
            
            # Also check our bot's admin list
            bot_admins = self.auth_service.get_admin_list()
            bot_admin_ids = [admin["telegram_id"] for admin in bot_admins if admin["telegram_id"]]
            
            # Combine admin lists
            all_admin_ids = list(set(admin_ids + bot_admin_ids))
            
            # Send notification to each admin
            for admin_id in all_admin_ids:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=message,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error notifying admins: {e}")
    
    async def _auto_topic_detection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Auto-detect topics from messages"""
        message = update.message
        chat_id = message.chat.id
        text = message.text or ""
        
        # Skip if message is too short
        if len(text) < 20:
            return
        
        try:
            # Generate topic suggestions based on message content
            topics = await self.ai_service.generate_topic_suggestions(text)
            
            # Store topics for this chat (in production, save to database)
            if chat_id not in self.community_settings:
                self.community_settings[chat_id] = {"topics": []}
            
            # Add new topics
            for topic in topics:
                if topic not in self.community_settings[chat_id]["topics"]:
                    self.community_settings[chat_id]["topics"].append(topic)
            
            # Log topic detection
            log_user_action(
                message.from_user.id if message.from_user else 0,
                chat_id,
                "topic_detected",
                f"topics: {', '.join(topics)}"
            )
            
        except Exception as e:
            logger.error(f"Error in topic detection: {e}")
    
    async def _check_thread_summarization(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check if thread needs summarization"""
        message = update.message
        chat_id = message.chat.id
        
        # This is a simplified version - in production you'd track message counts
        # and thread lengths more sophisticatedly
        
        # For now, we'll just log that we're monitoring
        if message.from_user:
            log_user_action(
                message.from_user.id,
                chat_id,
                "message_monitored",
                "thread summarization check"
            )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from moderation keyboards"""
        query = update.callback_query
        data = query.data
        user = query.from_user
        
        # Check if user is admin
        if not self.auth_service.is_admin(user.id):
            await query.answer("❌ You don't have permission to perform this action.")
            return
        
        try:
            if data.startswith("mod_approve_"):
                await self._handle_moderation_approval(update, context, data)
            elif data.startswith("mod_remove_"):
                await self._handle_moderation_removal(update, context, data)
            elif data.startswith("mod_ban_"):
                await self._handle_moderation_ban(update, context, data)
            elif data.startswith("mod_allow_"):
                await self._handle_moderation_allow(update, context, data)
            elif data.startswith("mod_warn_"):
                await self._handle_moderation_warn(update, context, data)
            else:
                await query.answer("Unknown action")
                
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
            await query.answer("Error processing action")
    
    async def _handle_moderation_approval(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle moderation approval"""
        query = update.callback_query
        message_id = data.replace("mod_approve_", "")
        
        await query.answer("✅ Message approved")
        await query.edit_message_text("✅ **Approved by moderator**")
        
        # Log action
        log_admin_action(query.from_user.id, 0, "moderation_approve", f"message_id: {message_id}")
    
    async def _handle_moderation_removal(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle moderation removal"""
        query = update.callback_query
        message_id = data.replace("mod_remove_", "")
        
        try:
            # Try to delete the message
            await context.bot.delete_message(chat_id=query.message.chat.id, message_id=int(message_id))
            await query.answer("❌ Message removed")
            await query.edit_message_text("❌ **Message removed by moderator**")
            
            # Log action
            log_admin_action(query.from_user.id, 0, "moderation_remove", f"message_id: {message_id}")
            
        except Exception as e:
            logger.error(f"Error removing message: {e}")
            await query.answer("Error removing message")
    
    async def _handle_moderation_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle moderation ban"""
        query = update.callback_query
        user_id = data.replace("mod_ban_", "")
        
        try:
            # Ban the user
            result = self.auth_service.ban_user(query.from_user.id, f"user_{user_id}")
            
            if result["success"]:
                await query.answer("🚫 User banned")
                await query.edit_message_text("🚫 **User banned by moderator**")
                
                # Log action
                log_admin_action(query.from_user.id, 0, "moderation_ban", f"user_id: {user_id}")
            else:
                await query.answer(f"Error: {result['error']}")
                
        except Exception as e:
            logger.error(f"Error banning user: {e}")
            await query.answer("Error banning user")
    
    async def _handle_moderation_allow(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle moderation allow"""
        query = update.callback_query
        message_id = data.replace("mod_allow_", "")
        
        await query.answer("✅ Content allowed")
        await query.edit_message_text("✅ **Content allowed by moderator**")
        
        # Log action
        log_admin_action(query.from_user.id, 0, "moderation_allow", f"message_id: {message_id}")
    
    async def _handle_moderation_warn(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle moderation warn"""
        query = update.callback_query
        user_id = data.replace("mod_warn_", "")
        
        await query.answer("⚠️ Warning sent")
        await query.edit_message_text("⚠️ **Warning sent to user**")
        
        # Log action
        log_admin_action(query.from_user.id, 0, "moderation_warn", f"user_id: {user_id}")
    
    async def get_community_topics(self, chat_id: int) -> List[str]:
        """Get current topics for a community"""
        if chat_id in self.community_settings:
            return self.community_settings[chat_id].get("topics", [])
        return []
    
    async def set_community_topic(self, chat_id: int, topic: str) -> bool:
        """Set a topic for a community"""
        try:
            if chat_id not in self.community_settings:
                self.community_settings[chat_id] = {"topics": []}
            
            if topic not in self.community_settings[chat_id]["topics"]:
                self.community_settings[chat_id]["topics"].append(topic)
            
            return True
        except Exception as e:
            logger.error(f"Error setting community topic: {e}")
            return False
