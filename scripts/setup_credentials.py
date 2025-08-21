#!/usr/bin/env python3
"""
Interactive credential setup for Kroolo AI Bot.
Helps users configure their bot tokens and API keys.
"""

import os
import sys
import re
from pathlib import Path

def print_banner():
    """Print setup banner."""
    print("🤖" + "=" * 58 + "🤖")
    print("🚀           KROOLO AI BOT CREDENTIAL SETUP           🚀")
    print("🤖" + "=" * 58 + "🤖")
    print()

def validate_telegram_token(token):
    """Validate Telegram bot token format."""
    pattern = r'^\d+:[A-Za-z0-9_-]{35}$'
    return bool(re.match(pattern, token))

def validate_openai_key(key):
    """Validate OpenAI API key format."""
    return key.startswith('sk-') and len(key) > 20

def get_telegram_credentials():
    """Get Telegram bot credentials."""
    print("📱 TELEGRAM BOT SETUP")
    print("-" * 40)
    print("1. Open Telegram and message @BotFather")
    print("2. Send /newbot")
    print("3. Choose a name: Kroolo AI Bot")
    print("4. Choose a username: krooloAgentBot (must end with 'bot')")
    print("5. Copy the bot token from BotFather")
    print()
    
    while True:
        token = input("🔑 Enter your Telegram bot token: ").strip()
        if not token:
            print("❌ Token cannot be empty")
            continue
        
        if token.lower() in ['skip', 'later', 'none']:
            print("⏭️  Skipping Telegram setup - you can add this later")
            return None, None
        
        if validate_telegram_token(token):
            print("✅ Valid Telegram bot token!")
            break
        else:
            print("❌ Invalid token format. Should be like: 123456789:ABCdefGHIjklMNOpqrSTUvwxyz")
            print("💡 Type 'skip' to skip this step")
    
    username = input("🏷️  Enter your bot username (optional): ").strip()
    if not username:
        username = "krooloAgentBot"
    
    return token, username

def get_openai_credentials():
    """Get OpenAI API credentials."""
    print("\n🧠 OPENAI API SETUP")
    print("-" * 40)
    print("1. Go to https://platform.openai.com/api-keys")
    print("2. Click 'Create new secret key'")
    print("3. Copy the API key (starts with 'sk-')")
    print()
    
    while True:
        key = input("🔑 Enter your OpenAI API key: ").strip()
        if not key:
            print("❌ API key cannot be empty")
            continue
        
        if key.lower() in ['skip', 'later', 'none']:
            print("⏭️  Skipping OpenAI setup - you can add this later")
            return None
        
        if validate_openai_key(key):
            print("✅ Valid OpenAI API key!")
            break
        else:
            print("❌ Invalid key format. Should start with 'sk-'")
            print("💡 Type 'skip' to skip this step")
    
    return key

def get_webhook_url():
    """Get webhook URL configuration."""
    print("\n🌐 WEBHOOK URL SETUP")
    print("-" * 40)
    print("For production, you'll need a public HTTPS URL")
    print("For local testing, you can use ngrok or similar")
    print()
    
    webhook_url = input("🔗 Enter your webhook URL (or press Enter for localhost): ").strip()
    
    if not webhook_url:
        webhook_url = "https://your-domain.com/v1/telegram/webhook/krooloAgentBot"
        print(f"📝 Using placeholder: {webhook_url}")
    
    return webhook_url

def update_env_file(telegram_token, telegram_username, openai_key, webhook_url):
    """Update the .env file with credentials."""
    env_path = Path(".env")
    
    if not env_path.exists():
        print("❌ .env file not found!")
        return False
    
    # Read current .env file
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Update credentials
    updated_lines = []
    for line in lines:
        if line.startswith('TELEGRAM_BOT_TOKEN=') and telegram_token:
            updated_lines.append(f'TELEGRAM_BOT_TOKEN={telegram_token}\n')
        elif line.startswith('TELEGRAM_BOT_USERNAME=') and telegram_username:
            updated_lines.append(f'TELEGRAM_BOT_USERNAME={telegram_username}\n')
        elif line.startswith('OPENAI_API_KEY=') and openai_key:
            updated_lines.append(f'OPENAI_API_KEY={openai_key}\n')
        elif line.startswith('TELEGRAM_WEBHOOK_URL=') and webhook_url:
            updated_lines.append(f'TELEGRAM_WEBHOOK_URL={webhook_url}\n')
        else:
            updated_lines.append(line)
    
    # Write updated .env file
    with open(env_path, 'w') as f:
        f.writelines(updated_lines)
    
    print("✅ .env file updated successfully!")
    return True

def show_next_steps():
    """Show next steps after credential setup."""
    print("\n🎉 SETUP COMPLETE!")
    print("=" * 50)
    print("🚀 Your Kroolo AI Bot is ready to launch!")
    print()
    print("📋 NEXT STEPS:")
    print("1. Start the bot:")
    print("   ./scripts/quick_start.sh")
    print()
    print("2. Test the bot:")
    print("   - Add your bot to a Telegram group")
    print("   - Send: @YourBot /start")
    print("   - Try: @AlanTuring What is computation?")
    print()
    print("3. Monitor the bot:")
    print("   - Health: http://localhost:8000/health")
    print("   - API docs: http://localhost:8000/docs")
    print("   - Logs: docker-compose logs -f")
    print()
    print("4. For production:")
    print("   ./scripts/deploy_production.sh")
    print()
    print("🎊 Enjoy your AI-powered Telegram bot!")

def main():
    """Main setup function."""
    print_banner()
    
    print("This script will help you set up credentials for your Kroolo AI Bot.")
    print("You can skip any step and configure manually later.")
    print()
    
    # Get credentials
    telegram_token, telegram_username = get_telegram_credentials()
    openai_key = get_openai_credentials()
    webhook_url = get_webhook_url()
    
    # Update .env file
    print("\n💾 UPDATING CONFIGURATION")
    print("-" * 40)
    
    if any([telegram_token, openai_key, webhook_url]):
        if update_env_file(telegram_token, telegram_username, openai_key, webhook_url):
            print("✅ Configuration updated successfully!")
        else:
            print("❌ Failed to update configuration")
            return 1
    else:
        print("⏭️  No credentials provided - you can add them manually to .env file")
    
    # Show next steps
    show_next_steps()
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n🛑 Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)
