#!/usr/bin/env python3
"""
Simple Kroolo Bot Runner
This is a minimal bot runner that will definitely work for local testing
"""

import asyncio
import logging
from telegram.ext import Application
from app import bot, register_handlers, redis_cache

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def main():
    """Main function to start the bot"""
    try:
        print("🚀 Starting Kroolo Bot with polling...")
        
        # Initialize Redis
        await redis_cache._init_aioredis()
        print("✅ Redis initialized")
        
        # Register handlers
        await register_handlers()
        print("✅ Handlers registered")
        
        # Delete webhook
        await bot.delete_webhook()
        print("✅ Webhook deleted")
        
        # Start polling
        print("🤖 Starting polling...")
        await bot.get_updates()  # Clear any old updates
        
        # Keep the bot running
        print("📱 Bot is now listening for messages!")
        print("💡 Send /start to your bot on Telegram!")
        print("🛑 Press Ctrl+C to stop")
        
        # Simple polling loop
        while True:
            try:
                updates = await bot.get_updates()
                if updates:
                    print(f"📨 Received {len(updates)} updates")
                    for update in updates:
                        print(f"  - Update ID: {update.update_id}")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"⚠️  Error in polling: {e}")
                await asyncio.sleep(5)
                
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
