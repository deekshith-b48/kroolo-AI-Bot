"""
Command handlers for Kroolo Agent Bot
Handles /start, /help, /ask, /admin commands
"""

import logging
from typing import Optional, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from services.ai_service import AIService
from services.auth import AuthService
from utils.logger import log_user_action, log_admin_action

logger = logging.getLogger(__name__)

class CommandHandlers:
    """Handles all bot commands"""
    
    def __init__(self, ai_service: AIService, auth_service: AuthService):
        self.ai_service = ai_service
        self.auth_service = auth_service
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        # Create user if not exists
        if user:
            self.auth_service.create_user_if_not_exists(user.id, user.username)
        
        text = (
            "👋 Hello — I am Kroolo Agent Bot (@krooloAgentBot).\n\n"
            "I'm here to help with:\n"
            "• AI-powered questions and answers\n"
            "• Community topic management\n"
            "• Automated moderation and insights\n\n"
            "Use /help to see all available commands.\n"
            "You can also mention me inline: `@krooloAgentBot <your query>`"
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Log action
        if user:
            log_user_action(user.id, chat_id, "start", "user started bot")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        text = (
            "🤖 **KrooloAgentBot Commands**\n\n"
            "**Basic Commands:**\n"
            "/start - Start & introduction\n"
            "/help - This help message\n"
            "/ask <question> - Ask the AI\n"
            "/topic <name> - Switch/query topic\n\n"
            "**Admin Commands:**\n"
            "/status - Bot status (admins only)\n"
            "/admin_help - Admin commands (admins only)\n"
            "/promote @user - Promote to moderator\n"
            "/demote @user - Demote user\n"
            "/ban @user - Ban user from bot\n"
            "/unban @user - Unban user\n\n"
            "**Inline Usage:**\n"
            "Type `@krooloAgentBot <query>` anywhere in chat for instant AI responses.\n\n"
            "**Community Features:**\n"
            "• Auto-topic detection\n"
            "• Spam detection\n"
            "• Thread summarization\n"
            "• Feature approval workflows"
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Log action
        if user:
            log_user_action(user.id, chat_id, "help", "viewed help")
    
    async def ask_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ask command"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        args = context.args
        
        if not args:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Usage:** `/ask <your question>`\n\nExample: `/ask What is artificial intelligence?`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        query = " ".join(args)
        
        # Check if user is banned
        if user and self.auth_service.get_user_role(user.id) == "banned":
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ You are banned from using this bot. Contact an administrator."
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
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log action
            if user:
                log_user_action(user.id, chat_id, "ask", query)
                
        except Exception as e:
            logger.error(f"Error in ask command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Sorry, I encountered an error while processing your question. Please try again later."
            )
    
    async def topic_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /topic command"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        args = context.args
        
        if not args:
            # Show current topics
            await self._show_current_topics(update, context)
            return
        
        topic_name = " ".join(args)
        
        # Check if user is banned
        if user and self.auth_service.get_user_role(user.id) == "banned":
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ You are banned from using this bot. Contact an administrator."
            )
            return
        
        try:
            # Update community topic
            # This would integrate with your community management system
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🎯 **Topic Updated:** {topic_name}\n\n"
                     f"Bot will now focus on this topic for future interactions.",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log action
            if user:
                log_user_action(user.id, chat_id, "topic", f"set to {topic_name}")
                
        except Exception as e:
            logger.error(f"Error in topic command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Error updating topic. Please try again."
            )
    
    async def _show_current_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current community topics"""
        chat_id = update.effective_chat.id
        
        # This would fetch from your community settings
        topics = ["General Discussion", "Questions & Answers", "Community Updates"]
        
        text = "📋 **Current Community Topics:**\n\n"
        for i, topic in enumerate(topics, 1):
            text += f"{i}. {topic}\n"
        
        text += "\nUse `/topic <name>` to switch to a specific topic."
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command (admin only)"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        if not user or not self.auth_service.is_admin(user.id):
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Access Denied:** This command is for administrators only."
            )
            return
        
        try:
            # Get bot status information
            ai_status = self.ai_service.is_service_available()
            
            text = (
                "📊 **Bot Status Report**\n\n"
                f"**AI Services:**\n"
                f"• OpenAI: {'✅ Available' if ai_status['openai'] else '❌ Unavailable'}\n"
                f"• HuggingFace: {'✅ Available' if ai_status['huggingface'] else '❌ Unavailable'}\n"
                f"• Overall: {'✅ Available' if ai_status['overall'] else '❌ Unavailable'}\n\n"
                f"**User Info:**\n"
                f"• Your Role: {self.auth_service.get_user_role(user.id)}\n"
                f"• Chat ID: {chat_id}\n"
                f"• User ID: {user.id}\n\n"
                f"**Bot Info:**\n"
                f"• Username: @{context.bot.username}\n"
                f"• Available Models: {', '.join(self.ai_service.get_available_models()[:3])}"
            )
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log action
            log_admin_action(user.id, "status", "viewed bot status")
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Error retrieving status. Please try again."
            )
    
    async def admin_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin_help command (admin only)"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        if not user or not self.auth_service.is_admin(user.id):
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Access Denied:** This command is for administrators only."
            )
            return
        
        permissions = self.auth_service.get_user_permissions(user.id)
        
        text = "🔐 **Admin Commands & Permissions**\n\n"
        
        if permissions["can_promote"]:
            text += "**User Management:**\n"
            text += "/promote @username - Promote to moderator\n"
            text += "/demote @username - Demote to user\n"
            text += "/ban @username - Ban from bot\n"
            text += "/unban @username - Unban user\n\n"
        
        if permissions["can_manage_settings"]:
            text += "**Community Management:**\n"
            text += "/settings - Manage bot settings\n"
            text += "/approve <task> - Approve feature/task\n"
            text += "/reject <task> - Reject feature/task\n\n"
        
        if permissions["can_backup"]:
            text += "**System Management:**\n"
            text += "/backup - Create system backup\n"
            text += "/restore - Restore from backup\n\n"
        
        text += "**General Admin:**\n"
        text += "/status - View bot status\n"
        text += "/admin_help - This help message\n\n"
        text += f"**Your Role:** {permissions['role'].title()}"
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Log action
        log_admin_action(user.id, "admin_help", "viewed admin help")
    
    async def promote_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /promote command (admin only)"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        args = context.args
        
        if not user or not self.auth_service.is_admin(user.id):
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Access Denied:** This command is for administrators only."
            )
            return
        
        if not args:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Usage:** `/promote @username`\n\nExample: `/promote @john_doe`"
            )
            return
        
        target_username = args[0]
        new_role = args[1] if len(args) > 1 else "moderator"
        
        try:
            result = self.auth_service.promote_user(user.id, target_username, new_role)
            
            if result["success"]:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ **Success:** {result['message']}"
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ **Error:** {result['error']}"
                )
                
        except Exception as e:
            logger.error(f"Error in promote command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Error promoting user. Please try again."
            )
    
    async def demote_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /demote command (admin only)"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        args = context.args
        
        if not user or not self.auth_service.is_admin(user.id):
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Access Denied:** This command is for administrators only."
            )
            return
        
        if not args:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Usage:** `/demote @username`\n\nExample: `/demote @john_doe`"
            )
            return
        
        target_username = args[0]
        
        try:
            result = self.auth_service.demote_user(user.id, target_username)
            
            if result["success"]:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ **Success:** {result['message']}"
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ **Error:** {result['error']}"
                )
                
        except Exception as e:
            logger.error(f"Error in demote command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Error demoting user. Please try again."
            )
    
    async def ban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ban command (admin only)"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        args = context.args
        
        if not user or not self.auth_service.is_admin(user.id):
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Access Denied:** This command is for administrators only."
            )
            return
        
        if not args:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Usage:** `/ban @username`\n\nExample: `/ban @spam_user`"
            )
            return
        
        target_username = args[0]
        
        try:
            result = self.auth_service.ban_user(user.id, target_username)
            
            if result["success"]:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ **Success:** {result['message']}"
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ **Error:** {result['error']}"
                )
                
        except Exception as e:
            logger.error(f"Error in ban command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Error banning user. Please try again."
            )
    
    async def unban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unban command (admin only)"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        args = context.args
        
        if not user or not self.auth_service.is_admin(user.id):
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Access Denied:** This command is for administrators only."
            )
            return
        
        if not args:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Usage:** `/unban @username`\n\nExample: `/unban @john_doe`"
            )
            return
        
        target_username = args[0]
        
        try:
            result = self.auth_service.unban_user(user.id, target_username)
            
            if result["success"]:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ **Success:** {result['message']}"
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ **Error:** {result['error']}"
                )
                
        except Exception as e:
            logger.error(f"Error in unban command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Error unbanning user. Please try again."
            )
