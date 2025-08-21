#!/usr/bin/env python3
"""
Kroolo Agent Bot Runner
This script runs both the FastAPI server and Telegram bot polling
"""

import asyncio
import uvicorn
import threading
from app import app, bot, application, register_handlers, redis_cache

async def start_polling():
    """Start Telegram bot polling"""
    try:
        print("🤖 Starting Telegram bot polling...")
        
        # Register handlers
        await register_handlers()
        
        # Delete any existing webhook
        await bot.delete_webhook()
        
        # Initialize and start application
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        print("✅ Telegram bot polling started successfully!")
        print("📱 Bot is now listening for messages!")
        
        # Keep polling running
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        print(f"❌ Error starting polling: {e}")
        import traceback
        traceback.print_exc()

def start_fastapi():
    """Start FastAPI server in a separate thread"""
    try:
        print("🌐 Starting FastAPI server...")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    except Exception as e:
        print(f"❌ Error starting FastAPI: {e}")

async def main():
    """Main function"""
    try:
        print("🚀 Starting Kroolo Agent Bot...")
        
        # Initialize Redis
        await redis_cache._init_aioredis()
        print("✅ Redis initialized")
        
        # Start FastAPI in a separate thread
        fastapi_thread = threading.Thread(target=start_fastapi, daemon=True)
        fastapi_thread.start()
        
        # Wait a moment for FastAPI to start
        await asyncio.sleep(3)
        
        # Start polling
        await start_polling()
        
    except Exception as e:
        print(f"❌ Error in main: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        import traceback
        traceback.print_exc()
