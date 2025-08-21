"""
Main FastAPI application for Kroolo Agent Bot
Integrates all handlers, services, and webhook functionality
"""

import os
import asyncio
import logging
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, Request, Header, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, InlineQueryHandler, CallbackQueryHandler, filters

# Import our modules
from db import Database
from services.ai_service import AIService
from services.auth import AuthService
from utils.cache import RedisCache, RateLimiter, CacheManager
from utils.logger import logger, log_bot_action
from handlers.commands import CommandHandlers
from handlers.inline import InlineQueryHandler as BotInlineQueryHandler
from handlers.community import CommunityHandler

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")
TELEGRAM_WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kroolo.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Validation
if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not set in environment")

if not WEBHOOK_SECRET:
    raise RuntimeError("TELEGRAM_WEBHOOK_SECRET not set in environment")

# Initialize services
database = Database(DATABASE_URL)
redis_cache = RedisCache(REDIS_URL)
rate_limiter = RateLimiter(redis_cache)
cache_manager = CacheManager(redis_cache)
ai_service = AIService()
auth_service = AuthService(database)

# Initialize handlers
command_handlers = CommandHandlers(ai_service, auth_service)
inline_handler = BotInlineQueryHandler(ai_service)
community_handler = CommunityHandler(ai_service, auth_service)

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# FastAPI app
app = FastAPI(
    title="Kroolo Agent Bot API",
    description="AI-powered Telegram bot with community management and moderation",
    version="1.0.0"
)

# Webhook model
class WebhookModel(BaseModel):
    update: dict

# Register command handlers
async def register_handlers():
    """Register all command and message handlers"""
    
    # Command handlers
    application.add_handler(CommandHandler("start", command_handlers.start_command))
    application.add_handler(CommandHandler("help", command_handlers.help_command))
    application.add_handler(CommandHandler("ask", command_handlers.ask_command))
    application.add_handler(CommandHandler("topic", command_handlers.topic_command))
    application.add_handler(CommandHandler("status", command_handlers.status_command))
    application.add_handler(CommandHandler("admin_help", command_handlers.admin_help_command))
    application.add_handler(CommandHandler("promote", command_handlers.promote_command))
    application.add_handler(CommandHandler("demote", command_handlers.demote_command))
    application.add_handler(CommandHandler("ban", command_handlers.ban_command))
    application.add_handler(CommandHandler("unban", command_handlers.unban_command))
    
    # Inline query handler
    from telegram.ext import InlineQueryHandler
    application.add_handler(InlineQueryHandler(inline_handler.handle_inline_query))
    
    # Message handler for community features
    application.add_handler(MessageHandler(
        filters.TEXT & (~filters.COMMAND), 
        community_handler.handle_message
    ))
    
    # Callback query handler for moderation
    application.add_handler(CallbackQueryHandler(community_handler.handle_callback_query))
    
    logger.info("All handlers registered successfully")

# Webhook endpoint
@app.post("/webhook")
async def webhook(
    request: Request, 
    x_telegram_bot_api_secret_token: Optional[str] = Header(None)
):
    """Telegram webhook endpoint"""
    
    # Verify webhook secret
    if x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        logger.warning("Invalid webhook secret")
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    
    try:
        # Parse update
        update_json = await request.json()
        update = Update.de_json(update_json, bot)
        
        # Process update
        await application.process_update(update)
        
        # Log successful processing
        log_bot_action("webhook_processed", f"update_id: {update.update_id}")
        
        return JSONResponse({"ok": True})
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        # Check bot status
        bot_info = await bot.get_me()
        
        # Check database
        db_status = "healthy"
        try:
            # Simple database check
            database.get_session()
        except Exception:
            db_status = "unhealthy"
        
        # Check Redis
        redis_status = "healthy"
        try:
            redis_cache.ping()
        except Exception:
            redis_status = "unhealthy"
        
        # Check AI services
        ai_status = ai_service.is_service_available()
        
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "bot": {
                "username": bot_info.username,
                "first_name": bot_info.first_name,
                "is_bot": bot_info.is_bot
            },
            "services": {
                "database": db_status,
                "redis": redis_status,
                "ai": ai_status
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e)}
        )

# Admin API endpoints
@app.get("/admin/logs")
async def get_logs(limit: int = 100, user_id: Optional[int] = None, chat_id: Optional[int] = None):
    """Get bot logs (admin only)"""
    try:
        logs = database.get_logs(limit=limit, user_id=user_id, chat_id=chat_id)
        return {"logs": logs, "count": len(logs)}
    except Exception as e:
        logger.error(f"Error retrieving logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve logs")

@app.get("/admin/users")
async def get_users(role: Optional[str] = None):
    """Get users (admin only)"""
    try:
        if role:
            users = database.get_users_by_role(role)
        else:
            # Get all users (simplified)
            users = []
            for role_name in ["user", "moderator", "admin", "superadmin"]:
                role_users = database.get_users_by_role(role_name)
                users.extend(role_users)
        
        return {"users": users, "count": len(users)}
    except Exception as e:
        logger.error(f"Error retrieving users: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve users")

@app.get("/admin/backup")
async def create_backup():
    """Create system backup (admin only)"""
    try:
        backup_data = database.backup_database()
        return backup_data
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        raise HTTPException(status_code=500, detail="Failed to create backup")

@app.get("/admin/status")
async def admin_status():
    """Get detailed system status (admin only)"""
    try:
        # Get rate limit info
        rate_limit_info = rate_limiter.get_rate_limit_info(0, 0)  # Global status
        
        # Get cache stats
        cache_stats = {
            "redis_connected": redis_cache.redis_client is not None,
            "cache_manager_ready": cache_manager is not None
        }
        
        # Get AI service status
        ai_status = ai_service.is_service_available()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "rate_limits": rate_limit_info,
            "cache": cache_stats,
            "ai_services": ai_status,
            "database": {
                "url": DATABASE_URL,
                "type": "sqlite" if "sqlite" in DATABASE_URL else "postgres"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting admin status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get status")

# Community management endpoints
@app.get("/community/{chat_id}/topics")
async def get_community_topics(chat_id: int):
    """Get topics for a community"""
    try:
        topics = await community_handler.get_community_topics(chat_id)
        return {"chat_id": chat_id, "topics": topics}
    except Exception as e:
        logger.error(f"Error getting community topics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get topics")

@app.post("/community/{chat_id}/topics")
async def set_community_topic(chat_id: int, topic: str):
    """Set a topic for a community"""
    try:
        success = await community_handler.set_community_topic(chat_id, topic)
        if success:
            return {"success": True, "message": f"Topic '{topic}' set for chat {chat_id}"}
        else:
            raise HTTPException(status_code=400, detail="Failed to set topic")
    except Exception as e:
        logger.error(f"Error setting community topic: {e}")
        raise HTTPException(status_code=500, detail="Failed to set topic")

# Rate limit info endpoint
@app.get("/rate-limit/{user_id}/{chat_id}")
async def get_rate_limit_info(user_id: int, chat_id: int):
    """Get rate limit information for user and chat"""
    try:
        info = rate_limiter.get_rate_limit_info(user_id, chat_id)
        return {
            "user_id": user_id,
            "chat_id": chat_id,
            "rate_limits": info
        }
    except Exception as e:
        logger.error(f"Error getting rate limit info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get rate limit info")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize bot on startup"""
    try:
        # Register handlers
        await register_handlers()
        
        # Set webhook if URL is configured and not localhost (Telegram requires HTTPS)
        if TELEGRAM_WEBHOOK_URL and not TELEGRAM_WEBHOOK_URL.startswith("http://localhost"):
            webhook_url = f"{TELEGRAM_WEBHOOK_URL}/webhook"
            
            # Remove existing webhook first
            await bot.delete_webhook()
            
            # Set new webhook
            await bot.set_webhook(
                url=webhook_url,
                secret_token=WEBHOOK_SECRET,
                allowed_updates=["message", "inline_query", "callback_query"]
            )
            
            logger.info(f"Webhook set successfully: {webhook_url}")
        else:
            # For local development, don't set webhook (Telegram requires HTTPS)
            await bot.delete_webhook()
            logger.info("Running in local development mode - webhook not set (use polling for testing)")
            
            # Start polling in background for local development
            import asyncio
            asyncio.create_task(start_polling())
        
        # Initialize Redis async connection
        await redis_cache._init_aioredis()
        
        logger.info("Kroolo Agent Bot started successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

async def start_polling():
    """Start polling for updates in local development mode"""
    try:
        logger.info("Starting polling for updates...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        logger.info("Polling started successfully - bot is now listening for messages!")
    except Exception as e:
        logger.error(f"Failed to start polling: {e}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        # Remove webhook
        await bot.delete_webhook()
        
        # Stop polling if running
        try:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
        except:
            pass
            
        logger.info("Webhook removed and polling stopped on shutdown")
        
        # Close Redis connections
        if redis_cache.aioredis_client:
            await redis_cache.aioredis_client.close()
        
        logger.info("Kroolo Agent Bot shutdown complete")
        
    except Exception as e:
        logger.error(f"Shutdown error: {e}")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with bot information"""
    try:
        bot_info = await bot.get_me()
        return {
            "message": "Kroolo Agent Bot API",
            "bot": {
                "username": bot_info.username,
                "first_name": bot_info.first_name,
                "is_bot": bot_info.is_bot
            },
            "endpoints": {
                "webhook": "/webhook",
                "health": "/health",
                "admin": "/admin/*",
                "community": "/community/*"
            },
            "documentation": "/docs"
        }
    except Exception as e:
        logger.error(f"Error getting root info: {e}")
        return {"message": "Kroolo Agent Bot API", "error": "Bot info unavailable"}

if __name__ == "__main__":
    import uvicorn
    import asyncio
    
    async def start_bot():
        """Start the bot with polling"""
        try:
            # Register handlers
            await register_handlers()
            
            # For local development, start polling
            await bot.delete_webhook()
            logger.info("Starting polling for updates...")
            
            # Initialize and start application
            await application.initialize()
            await application.start()
            await application.updater.start_polling()
            logger.info("Polling started successfully - bot is now listening for messages!")
            
            # Start uvicorn server
            config = uvicorn.Config(
                app=app,
                host="0.0.0.0",
                port=8000,
                log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            raise
    
    # Run the application with polling
    asyncio.run(start_bot())
