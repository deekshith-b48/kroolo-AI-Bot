#!/usr/bin/env python3
"""
Test Bot Connection
Simple script to test if the bot can connect to Telegram
"""

import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot

# Load environment variables
load_dotenv()

async def test_bot():
    """Test bot connection"""
    try:
        # Get bot token
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            print("❌ TELEGRAM_BOT_TOKEN not found in .env file")
            return
        
        print(f"🔑 Bot token: {token[:20]}...")
        
        # Create bot instance
        bot = Bot(token=token)
        
        # Test connection
        print("🤖 Testing bot connection...")
        me = await bot.get_me()
        print(f"✅ Bot connected successfully!")
        print(f"   Username: @{me.username}")
        print(f"   Name: {me.first_name}")
        print(f"   ID: {me.id}")
        
        # Test getting updates
        print("\n📡 Testing updates...")
        updates = await bot.get_updates()
        print(f"   Found {len(updates)} updates")
        
        if updates:
            print("   Recent updates:")
            for update in updates[-3:]:  # Show last 3 updates
                if update.message:
                    print(f"     - Message: {update.message.text}")
                elif update.inline_query:
                    print(f"     - Inline query: {update.inline_query.query}")
        
        print("\n🎉 Bot is working correctly!")
        print("💡 You can now send messages to your bot on Telegram!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_bot())
