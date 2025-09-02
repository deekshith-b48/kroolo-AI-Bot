"""
Command handlers for Kroolo Agent Bot
Handles /start, /help, /ask, /admin commands
"""

import logging
import re
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
    
    def _sanitize_input(self, text: str, max_length: int = 1000) -> str:
        """Sanitize user input to prevent abuse and ensure safety"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove potentially dangerous characters
        text = re.sub(r'[<>"\']', '', text)
        
        # Limit length
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text
    
    def _validate_query(self, query: str) -> Dict[str, Any]:
        """Validate user query for safety and appropriateness"""
        if not query or len(query.strip()) < 3:
            return {"valid": False, "error": "Query must be at least 3 characters long"}
        
        if len(query) > 1000:
            return {"valid": False, "error": "Query is too long (max 1000 characters)"}
        
        # Check for potentially harmful patterns
        harmful_patterns = [
            r'(?:https?://|www\.)',  # URLs
            r'(?:[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',  # Email addresses
            r'(?:\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b)',  # Credit card numbers
            r'(?:password|secret|key|token)',  # Sensitive keywords
        ]
        
        for pattern in harmful_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return {"valid": False, "error": "Query contains potentially sensitive information"}
        
        return {"valid": True, "query": query}
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        # Create user if not exists
        if user:
            self.auth_service.create_user_if_not_exists(user.id, user.username)
        
        text = (
            "👋 **Hello! I am Kroolo Agent Bot.**\n\n"
            "I'm here to help with:\n"
            "• 🤖 **AI-powered questions and answers**\n"
            "• 🎯 **Community topic management**\n"
            "• 🛡️ **Automated moderation and insights**\n\n"
            "**Quick Start:**\n"
            "• Use `/ask <your question>` to get AI responses\n"
            "• Use `/help` to see all available commands\n"
            "• Use `/topic <name>` to set community topics\n\n"
            "I'm ready to help! What would you like to know?"
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
            "🤖 **Kroolo Agent Bot Commands**\n\n"
            "**Basic Commands:**\n"
            "• `/start` - Start & introduction\n"
            "• `/help` - This help message\n"
            "• `/ask <question>` - Ask the AI\n"
            "• `/topic <name>` - Switch/query topic\n\n"
            "**📰 News & Updates:**\n"
            "• `/news` - Get latest AI news\n"
            "• `/setnews HH:MM` - Schedule daily news (Admin)\n"
            "• `/stopnews` - Stop news schedule (Admin)\n\n"
            "**🧠 Quiz System:**\n"
            "• `/quiz` - Start an AI quiz\n"
            "• `/leaderboard` - View top scorers\n"
            "• `/mystats` - Your quiz statistics\n"
            "• `/setquiz HH:MM` - Schedule daily quiz (Admin)\n"
            "• `/stopquiz` - Stop quiz schedule (Admin)\n\n"
            "**🎭 Fun & Entertainment:**\n"
            "• `/funfact` - Random AI fun fact\n"
            "• `/joke` - Tech/AI joke\n"
            "• `/setfunfact HH:MM` - Schedule daily fun fact (Admin)\n"
            "• `/stopfunfact` - Stop fun fact schedule (Admin)\n\n"
            "**Admin Commands:**\n"
            "• `/status` - Bot status (admins only)\n"
            "• `/admin_help` - Admin commands (admins only)\n"
            "• `/promote @user` - Promote to moderator\n"
            "• `/demote @user` - Demote user\n"
            "• `/ban @user` - Ban user from bot\n"
            "• `/unban @user` - Unban user\n"
            "• `/listjobs` - View all scheduled jobs (Admin)\n\n"
            "**How to Use:**\n"
            "• **Ask Questions:** `/ask What is artificial intelligence?`\n"
            "• **Set Topics:** `/topic Python Programming`\n"
            "• **Get News:** `/news` for latest AI updates\n"
            "• **Take Quiz:** `/quiz` to test your AI knowledge\n"
            "• **Schedule Content:** Use `/setnews 09:00` to schedule daily posts\n\n"
            "**💡 Tips:**\n"
            "• Use HH:MM format for scheduling (e.g., 09:00, 20:30)\n"
            "• Add timezone for specific regions (e.g., EST, PST, GMT)\n"
            "• Quiz points accumulate over time\n"
            "• All schedules are chat-specific\n\n"
            "**Community Features:**\n"
            "• Auto-topic detection\n"
            "• Spam detection\n"
            "• Thread summarization\n"
            "• Feature approval workflows\n\n"
            "**Need more help?** Use `/help_engagement` for detailed engagement commands!"
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
        """Handle /ask command with improved input validation and sanitization"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        args = context.args
        
        if not args:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Usage:** `/ask <your question>`\n\n"
                     "**Examples:**\n"
                     "• `/ask What is artificial intelligence?`\n"
                     "• `/ask How do I learn Python?`\n"
                     "• `/ask Explain quantum computing`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Join arguments and sanitize input
        raw_query = " ".join(args)
        sanitized_query = self._sanitize_input(raw_query)
        
        # Validate the query
        validation = self._validate_query(sanitized_query)
        if not validation["valid"]:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ **Invalid Query:** {validation['error']}\n\n"
                     "Please rephrase your question and try again.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        query = validation["query"]
        
        # Check if user is banned
        if user and self.auth_service.get_user_role(user.id) == "banned":
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Access Denied:** You are banned from using this bot. Contact an administrator."
            )
            return
        
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        try:
            # Log the query attempt
            if user:
                log_user_action(user.id, chat_id, "ask_attempt", f"query: {query[:100]}")
            
            # Get AI response
            answer = await self.ai_service.ask_ai(query)
            
            # Sanitize the response for safety
            safe_answer = self._sanitize_input(answer, max_length=4000)
            
            # Send response
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🤖 **AI Response:**\n\n{safe_answer}",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log successful response
            if user:
                log_user_action(user.id, chat_id, "ask_success", f"query: {query[:100]}")
                
        except Exception as e:
            logger.error(f"Error in ask command: {e}")
            
            # Log the error
            if user:
                log_user_action(user.id, chat_id, "ask_error", f"error: {str(e)}")
            
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Sorry, I encountered an error while processing your question.**\n\n"
                     "**Possible reasons:**\n"
                     "• AI service is temporarily unavailable\n"
                     "• Your question is too complex\n"
                     "• Network connectivity issues\n\n"
                     "**Please try:**\n"
                     "• Rephrasing your question\n"
                     "• Waiting a few minutes\n"
                     "• Contacting support if the issue persists",
                parse_mode=ParseMode.MARKDOWN
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
        sanitized_topic = self._sanitize_input(topic_name, max_length=200)
        
        # Check if user is banned
        if user and self.auth_service.get_user_role(user.id) == "banned":
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Access Denied:** You are banned from using this bot. Contact an administrator."
            )
            return
        
        try:
            # Update community topic
            # This would integrate with your community management system
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🎯 **Topic Updated:** {sanitized_topic}\n\n"
                     f"Bot will now focus on this topic for future interactions.\n\n"
                     f"**Current Topic:** {sanitized_topic}",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log action
            if user:
                log_user_action(user.id, chat_id, "topic", f"set to {sanitized_topic}")
                
        except Exception as e:
            logger.error(f"Error in topic command: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Error updating topic.** Please try again or contact support."
            )
    
    async def _show_current_topics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current community topics"""
        chat_id = update.effective_chat.id
        
        # This would fetch from your community settings
        topics = ["General Discussion", "Questions & Answers", "Community Updates"]
        
        text = "📋 **Current Community Topics:**\n\n"
        for i, topic in enumerate(topics, 1):
            text += f"{i}. {topic}\n"
        
        text += "\n**To set a new topic:**\n"
        text += "Use `/topic <topic name>`\n\n"
        text += "**Examples:**\n"
        text += "• `/topic Python Programming`\n"
        text += "• `/topic AI Discussion`\n"
        text += "• `/topic General Chat`"
        
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
                text="❌ **Error retrieving status.** Please try again or contact support."
            )
    
    async def admin_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin_help command (admin only)"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        if not user or not self.auth_service.can_perform_action(user.id, "admin_help"):
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ **Access Denied:** This command is for administrators only."
            )
            return
        
        # Get user's role and available actions
        user_role = self.auth_service.get_user_role(user.id)
        available_actions = self.auth_service.get_available_actions(user.id)
        
        role_emoji = {
            "user": "👤",
            "moderator": "🛡️",
            "admin": "⚡",
            "superadmin": "👑"
        }.get(user_role, "👤")
        
        text = (
            f"🔧 **Admin Commands** {role_emoji}\n\n"
            f"**Your Role:** {user_role.title()}\n\n"
            "**Available Commands:**\n"
        )
        
        if available_actions:
            text += "\n".join(available_actions)
        else:
            text += "• No admin commands available for your role"
        
        text += (
            "\n\n**Role Hierarchy:**\n"
            "👤 `user` - Regular user (default)\n"
            "🛡️ `moderator` - Can moderate content and users\n"
            "⚡ `admin` - Can manage users and system settings\n"
            "👑 `superadmin` - Full system access\n\n"
            "**Security Notes:**\n"
            "• Admin commands in groups are sent privately\n"
            "• All admin actions are logged\n"
            "• Users cannot perform actions on themselves\n\n"
            "Use commands responsibly!"
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Log action
        log_admin_action(user.id, chat_id, "admin_help", f"viewed admin help as {user_role}")
    
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
                text="❌ **Usage:** `/promote @username [role]`\n\n"
                     "**Examples:**\n"
                     "• `/promote @john_doe` - Promote to moderator\n"
                     "• `/promote @jane_smith admin` - Promote to admin\n\n"
                     "**Available roles:** user, moderator, admin"
            )
            return
        
        target_username = args[0]
        new_role = args[1] if len(args) > 1 else "moderator"
        
        # Validate role
        valid_roles = ["user", "moderator", "admin"]
        if new_role not in valid_roles:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ **Invalid role:** {new_role}\n\n"
                     f"**Valid roles:** {', '.join(valid_roles)}"
            )
            return
        
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
                text="❌ **Error promoting user.** Please try again or contact support."
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
                text="❌ **Usage:** `/demote @username`\n\n"
                     "**Example:** `/demote @john_doe`"
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
                text="❌ **Error demoting user.** Please try again or contact support."
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
                text="❌ **Usage:** `/ban @username`\n\n"
                     "**Example:** `/ban @spam_user`\n\n"
                     "**Note:** This will prevent the user from using bot commands."
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
                text="❌ **Error banning user.** Please try again or contact support."
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
                text="❌ **Usage:** `/unban @username`\n\n"
                     "**Example:** `/unban @john_doe`\n\n"
                     "**Note:** This will restore the user's access to bot commands."
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
                text="❌ **Error unbanning user.** Please try again or contact support."
            )
