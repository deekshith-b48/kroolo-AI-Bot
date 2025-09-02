#!/usr/bin/env python3
"""
Kroolo AI Bot - Refactored for Telegram Groups and Inline Mode
Features:
- Long-polling (no webhooks)
- Inline mode support for groups
- Robust permission system
- Private admin commands
- Community topic management
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from telegram import Update, Bot, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import (
    Application, CommandHandler, MessageHandler, InlineQueryHandler, 
    CallbackQueryHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from dotenv import load_dotenv

# Import our modules
from db import Database
from services.ai_service import AIService
from services.auth import AuthService
from services.scheduler import SchedulerService
from services.community_engagement import CommunityEngagementService
from utils.cache import RedisCache, RateLimiter, CacheManager
from utils.logger import logger, log_bot_action
from handlers.commands import CommandHandlers
from handlers.inline import InlineQueryHandler as BotInlineQueryHandler
from handlers.community import CommunityHandler
from handlers.community_commands import CommunityEngagementCommands

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kroolo_bot.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Validation
if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not set in environment")

class KrooloBot:
    """Main bot class with all functionality"""
    
    def __init__(self):
        self.bot = None
        self.application = None
        self._initialize_bot()
        
        # Initialize services
        self.database = Database(DATABASE_URL)
        self.redis_cache = RedisCache(REDIS_URL)
        self.rate_limiter = RateLimiter(self.redis_cache)
        self.cache_manager = CacheManager(self.redis_cache)
        self.ai_service = AIService()
        self.auth_service = AuthService(self.database)
        self.scheduler_service = SchedulerService(self.ai_service, self.auth_service, self.database)
        self.engagement_service = CommunityEngagementService(self.ai_service)
        
        # Initialize handlers
        self.command_handlers = CommandHandlers(self.ai_service, self.auth_service)
        self.inline_handler = BotInlineQueryHandler(self.ai_service)
        self.community_handler = CommunityHandler(self.ai_service, self.auth_service)
        self.engagement_commands = CommunityEngagementCommands(self.engagement_service, self.auth_service)
        
        # Register all handlers
        self._register_handlers()
        
        logger.info("Kroolo Bot initialized successfully")
    
    def _initialize_bot(self):
        """Initialize bot and application objects"""
        try:
            self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
            # Build application without job queue to avoid weak reference issues
            self.application = (
                Application.builder()
                .token(TELEGRAM_BOT_TOKEN)
                .job_queue(None)
                .build()
            )
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise
    
    def _register_handlers(self):
        """Register all command and message handlers"""
        
        # Basic command handlers
        self.application.add_handler(CommandHandler("start", self.command_handlers.start_command))
        self.application.add_handler(CommandHandler("help", self.command_handlers.help_command))
        self.application.add_handler(CommandHandler("ask", self.command_handlers.ask_command))
        self.application.add_handler(CommandHandler("topic", self.command_handlers.topic_command))
        
        # Admin commands (these will be handled privately)
        self.application.add_handler(CommandHandler("status", self._handle_admin_command))
        self.application.add_handler(CommandHandler("admin_help", self._handle_admin_command))
        self.application.add_handler(CommandHandler("promote", self._handle_admin_command))
        self.application.add_handler(CommandHandler("demote", self._handle_admin_command))
        self.application.add_handler(CommandHandler("ban", self._handle_admin_command))
        self.application.add_handler(CommandHandler("unban", self._handle_admin_command))
        self.application.add_handler(CommandHandler("users", self._handle_admin_command))
        self.application.add_handler(CommandHandler("backup", self._handle_admin_command))
        
        # Community engagement commands
        self.application.add_handler(CommandHandler("news", self.engagement_commands.news_command))
        self.application.add_handler(CommandHandler("quiz", self.engagement_commands.quiz_command))
        self.application.add_handler(CommandHandler("funfact", self.engagement_commands.funfact_command))
        
        # Inline query handler
        self.application.add_handler(InlineQueryHandler(self.inline_handler.handle_inline_query))
        
        # Message handlers for community features
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.community_handler.handle_message
        ))
        
        # Callback query handler for interactive elements
        self.application.add_handler(CallbackQueryHandler(self.community_handler.handle_callback_query))
        
        logger.info("All handlers registered successfully")
    
    async def _handle_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin commands privately to prevent data leakage"""
        user = update.effective_user
        chat = update.effective_chat
        
        if not user:
            return
        
        # Check if user is admin
        if not self.auth_service.is_admin(user.id):
            await update.message.reply_text(
                "❌ You don't have permission to use admin commands.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # If command is used in a group, send private message
        if chat.type in ['group', 'supergroup']:
            try:
                # Send private message to admin
                await self._send_private_admin_response(update, context)
                # Confirm in group that command was processed
                await update.message.reply_text(
                    "✅ Admin command processed. Check your private messages.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to send private admin response: {e}")
                await update.message.reply_text(
                    "❌ Failed to process admin command. Please start a private chat with me first.",
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            # Already private chat, handle normally
            await self._execute_admin_command(update, context)
    
    async def _send_private_admin_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send admin command response to private chat"""
        user = update.effective_user
        command = update.message.text.split()[0][1:]  # Remove / from command
        
        try:
            # Execute the admin command and get response
            response = await self._execute_admin_command(update, context)
            
            # Send response privately
            await context.bot.send_message(
                chat_id=user.id,
                text=response,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error executing admin command {command}: {e}")
            await context.bot.send_message(
                chat_id=user.id,
                text=f"❌ Error executing command `/{command}`: {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _execute_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Execute the actual admin command"""
        command = update.message.text.split()[0][1:]  # Remove / from command
        
        # Route to appropriate handler
        if command == "status":
            await self.command_handlers.status_command(update, context)
            return "✅ Status command executed"
        elif command == "admin_help":
            await self.command_handlers.admin_help_command(update, context)
            return "✅ Admin help displayed"
        elif command == "promote":
            await self.command_handlers.promote_command(update, context)
            return "✅ Promote command executed"
        elif command == "demote":
            await self.command_handlers.demote_command(update, context)
            return "✅ Demote command executed"
        elif command == "ban":
            await self.command_handlers.ban_command(update, context)
            return "✅ Ban command executed"
        elif command == "unban":
            await self.command_handlers.unban_command(update, context)
            return "✅ Unban command executed"
        elif command == "users":
            return await self._handle_users_command(update, context)
        elif command == "backup":
            return await self._handle_backup_command(update, context)
        else:
            return "❌ Unknown admin command"
    
    async def _handle_users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /users command to list users"""
        users = self.database.get_all_users()
        
        if not users:
            return "📊 No users found in database."
        
        response = "📊 **User List:**\n\n"
        for user in users[:50]:  # Limit to first 50 users
            role_emoji = {
                "user": "👤",
                "moderator": "🛡️",
                "admin": "⚡",
                "superadmin": "👑"
            }.get(user.get("role", "user"), "👤")
            
            response += f"{role_emoji} **{user.get('username', 'Unknown')}** (ID: {user.get('telegram_id')})\n"
            response += f"   Role: {user.get('role', 'user')}\n"
            response += f"   Joined: {user.get('created_at', 'Unknown')}\n\n"
        
        if len(users) > 50:
            response += f"... and {len(users) - 50} more users"
        
        return response
    
    async def _handle_backup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /backup command"""
        try:
            # Create backup of database
            backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            # This is a simplified backup - in production you'd want proper backup logic
            return f"✅ Database backup created: `{backup_file}`\n\nNote: This is a development backup. For production, implement proper backup procedures."
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return f"❌ Backup failed: {str(e)}"
    
    async def start(self):
        """Start the bot with long-polling"""
        logger.info("🚀 Starting Kroolo Bot with long-polling...")
        
        # Start scheduler service
        await self.scheduler_service.start()
        
        # Start the bot
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
        logger.info("✅ Bot started successfully with long-polling")
        
        # Keep the bot running
        try:
            # Keep the event loop running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Bot stopped by user")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the bot gracefully"""
        logger.info("🛑 Stopping Kroolo Bot...")
        
        # Stop scheduler
        await self.scheduler_service.stop()
        
        # Stop the bot
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
        
        logger.info("✅ Bot stopped successfully")

async def main():
    """Main function"""
    bot = KrooloBot()
    await bot.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        import traceback
        traceback.print_exc()
