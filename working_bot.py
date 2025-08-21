#!/usr/bin/env python3
"""
Working Kroolo Bot Runner
This bot will actually process and respond to Telegram messages
"""

import asyncio
import logging
from telegram.ext import Application
from app import bot, application, register_handlers, redis_cache

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def main():
    """Main function to start the working bot"""
    try:
        print("🚀 Starting Kroolo Bot with message processing...")
        
        # Initialize Redis
        await redis_cache._init_aioredis()
        print("✅ Redis initialized")
        
        # Register handlers
        await register_handlers()
        print("✅ Message handlers registered")
        
        # Delete webhook
        await bot.delete_webhook()
        print("✅ Webhook deleted")
        
        # Initialize and start application
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        print("✅ Bot polling started successfully!")
        print("📱 Bot is now listening and processing messages!")
        print("💡 Send /start to your bot on Telegram - it will respond now!")
        print("🛑 Press Ctrl+C to stop")
        
        # Keep the bot running
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
