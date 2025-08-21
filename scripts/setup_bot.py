#!/usr/bin/env python3
"""
Setup script for Kroolo AI Bot.
Helps users configure their bot with BotFather and set up initial configuration.
"""

import os
import sys
import json
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from config.settings import settings


class BotSetup:
    """Bot setup and configuration helper."""
    
    def __init__(self):
        self.base_url = "https://api.telegram.org/bot"
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self):
        """Initialize the HTTP session."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def shutdown(self):
        """Shutdown the HTTP session."""
        if self.session:
            await self.session.close()
    
    async def create_bot(self, bot_name: str, username: str, description: str = "") -> Dict[str, Any]:
        """Create a new bot using BotFather."""
        print(f"\n🤖 Creating bot: {bot_name} (@{username})")
        print("=" * 50)
        
        print("\n📋 Steps to create your bot:")
        print("1. Open Telegram and search for @BotFather")
        print("2. Send /newbot command")
        print("3. Follow the prompts to set:")
        print(f"   - Bot name: {bot_name}")
        print(f"   - Bot username: {username}")
        print("4. Copy the bot token provided by BotFather")
        
        token = input("\n🔑 Enter your bot token: ").strip()
        
        if not token:
            print("❌ No token provided. Please get a token from @BotFather first.")
            return {}
        
        # Test the token
        bot_info = await self.test_token(token)
        if not bot_info:
            print("❌ Invalid token. Please check and try again.")
            return {}
        
        print(f"✅ Bot token verified! Bot: {bot_info.get('first_name', 'Unknown')}")
        
        # Configure bot settings
        await self.configure_bot(token, bot_info, description)
        
        return {
            "token": token,
            "bot_info": bot_info,
            "username": username
        }
    
    async def test_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Test if a bot token is valid."""
        try:
            url = f"{self.base_url}{token}/getMe"
            async with self.session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('ok'):
                        return result.get('result', {})
                return None
        except Exception as e:
            print(f"Error testing token: {e}")
            return None
    
    async def configure_bot(self, token: str, bot_info: Dict[str, Any], description: str):
        """Configure bot settings with BotFather."""
        print(f"\n⚙️  Configuring bot settings...")
        
        # Set bot description
        if description:
            await self.set_bot_description(token, description)
        
        # Set bot commands
        await self.set_bot_commands(token)
        
        # Set privacy mode
        await self.set_privacy_mode(token)
        
        print("✅ Bot configuration completed!")
    
    async def set_bot_description(self, token: str, description: str):
        """Set bot description."""
        try:
            url = f"{self.base_url}{token}/setDescription"
            data = {"description": description}
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('ok'):
                        print("✅ Bot description set")
                    else:
                        print(f"⚠️  Could not set description: {result.get('description')}")
        except Exception as e:
            print(f"⚠️  Error setting description: {e}")
    
    async def set_bot_commands(self, token: str):
        """Set bot commands."""
        commands = [
            {"command": "start", "description": "Start the bot"},
            {"command": "help", "description": "Show help and available commands"},
            {"command": "agents", "description": "List available AI agents"},
            {"command": "news", "description": "Get AI news and updates"},
            {"command": "quiz", "description": "Take an AI quiz"},
            {"command": "debate", "description": "Start an AI debate"},
            {"command": "fun", "description": "Get fun AI facts and jokes"},
            {"command": "config", "description": "Configure bot settings (admin only)"}
        ]
        
        try:
            url = f"{self.base_url}{token}/setMyCommands"
            data = {"commands": json.dumps(commands)}
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('ok'):
                        print("✅ Bot commands set")
                    else:
                        print(f"⚠️  Could not set commands: {result.get('description')}")
        except Exception as e:
            print(f"⚠️  Error setting commands: {e}")
    
    async def set_privacy_mode(self, token: str):
        """Set bot privacy mode (disabled to see all messages)."""
        try:
            url = f"{self.base_url}{token}/setChatMenuButton"
            data = {"menu_button": {"type": "commands"}}
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    print("✅ Bot menu button configured")
        except Exception as e:
            print(f"⚠️  Error configuring menu button: {e}")
    
    async def setup_webhook(self, token: str, webhook_url: str) -> bool:
        """Set up webhook for the bot."""
        print(f"\n🔗 Setting up webhook...")
        print(f"Webhook URL: {webhook_url}")
        
        try:
            url = f"{self.base_url}{token}/setWebhook"
            data = {
                "url": webhook_url,
                "allowed_updates": [
                    "message", "edited_message", "channel_post", "edited_channel_post",
                    "inline_query", "chosen_inline_result", "callback_query",
                    "shipping_query", "pre_checkout_query", "poll", "poll_answer",
                    "my_chat_member", "chat_member", "chat_join_request"
                ]
            }
            
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('ok'):
                        print("✅ Webhook set successfully!")
                        return True
                    else:
                        print(f"❌ Failed to set webhook: {result.get('description')}")
                        return False
                else:
                    print(f"❌ HTTP error: {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error setting webhook: {e}")
            return False
    
    def create_env_file(self, bot_data: Dict[str, Any], webhook_url: str):
        """Create .env file with bot configuration."""
        env_content = f"""# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN={bot_data.get('token')}
TELEGRAM_WEBHOOK_URL={webhook_url}
TELEGRAM_WEBHOOK_SECRET=your_webhook_secret_here

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=2000
OPENAI_TEMPERATURE=0.7

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/kroolo_bot
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333

# External APIs
NEWS_API_KEY=your_news_api_key_here
RSS_FEEDS=https://example.com/feed1,https://example.com/feed2

# Security & Rate Limiting
RATE_LIMIT_PER_USER=10
RATE_LIMIT_PER_CHAT=50
RATE_LIMIT_GLOBAL=1000

# Content & Scheduling
DEFAULT_TIMEZONE=Asia/Kolkata
NEWS_DIGEST_TIME=09:00
QUIZ_TIME=19:00
FUN_FACT_TIME=21:00

# Monitoring & Logging
LOG_LEVEL=INFO
ENVIRONMENT=development
DEBUG=true
"""
        
        env_file = Path(".env")
        with open(env_file, "w") as f:
            f.write(env_content)
        
        print(f"✅ Environment file created: {env_file}")
        print("⚠️  Please edit .env file with your actual API keys and configuration")
    
    def print_next_steps(self):
        """Print next steps for the user."""
        print("\n" + "=" * 60)
        print("🎉 Bot setup completed! Next steps:")
        print("=" * 60)
        print("\n1. 📝 Edit .env file with your API keys:")
        print("   - OpenAI API key")
        print("   - News API key (optional)")
        print("   - Database credentials")
        print("\n2. 🐳 Start the bot with Docker:")
        print("   docker-compose up -d")
        print("\n3. 🔍 Test the bot:")
        print("   - Send /start to your bot")
        print("   - Try /help to see available commands")
        print("\n4. 📊 Monitor the bot:")
        print("   - Health check: http://localhost:8000/health")
        print("   - Status: http://localhost:8000/status")
        print("\n5. 🚀 Deploy to production:")
        print("   - Update webhook URL in .env")
        print("   - Set ENVIRONMENT=production")
        print("   - Configure SSL certificates")
        print("\n📚 Documentation: Check the README.md file")
        print("🆘 Support: Create an issue in the repository")


async def main():
    """Main setup function."""
    print("🚀 Kroolo AI Bot Setup")
    print("=" * 50)
    
    setup = BotSetup()
    await setup.initialize()
    
    try:
        # Get bot details
        bot_name = input("Enter bot name (e.g., 'Kroolo AI Bot'): ").strip()
        if not bot_name:
            bot_name = "Kroolo AI Bot"
        
        username = input("Enter bot username (e.g., 'kroolo_ai_bot'): ").strip()
        if not username:
            username = "kroolo_ai_bot"
        
        description = input("Enter bot description (optional): ").strip()
        if not description:
            description = "Multi-agent AI bot with news, quizzes, debates, and fun content!"
        
        # Create bot
        bot_data = await setup.create_bot(bot_name, username, description)
        if not bot_data:
            print("❌ Bot setup failed. Please try again.")
            return
        
        # Get webhook URL
        print(f"\n🌐 Webhook Configuration")
        print("=" * 50)
        print("Your bot needs a webhook URL to receive updates.")
        print("For development, you can use ngrok or similar service.")
        
        webhook_url = input("Enter webhook URL (e.g., https://yourdomain.com/webhook): ").strip()
        if not webhook_url:
            print("⚠️  No webhook URL provided. You can set it later.")
            webhook_url = "https://yourdomain.com/webhook"
        
        # Set webhook if URL provided
        if webhook_url and webhook_url != "https://yourdomain.com/webhook":
            await setup.setup_webhook(bot_data['token'], webhook_url)
        
        # Create environment file
        setup.create_env_file(bot_data, webhook_url)
        
        # Print next steps
        setup.print_next_steps()
        
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
    finally:
        await setup.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
