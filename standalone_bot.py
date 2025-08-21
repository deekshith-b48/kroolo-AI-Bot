#!/usr/bin/env python3
"""
Standalone Kroolo Bot Runner
This bot runs independently without FastAPI to avoid Python 3.13 compatibility issues
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Get bot token
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN not found in .env file")
    exit(1)

# Create bot and application
bot = Bot(token=TOKEN)
application = Application.builder().token(TOKEN).build()

# Command handlers
async def start_command(update, context):
    """Handle /start command"""
    user = update.effective_user
    welcome_message = f"""
🤖 Welcome to Kroolo Agent Bot, {user.first_name}!

I'm your AI-powered assistant. Here's what I can do:

📚 **Commands:**
• /start - Show this welcome message
• /help - Show all available commands
• /ask <question> - Ask me anything
• /topic - Get topic suggestions
• /status - Check bot status

💡 **Examples:**
• /ask What is artificial intelligence?
• /topic technology
• /status

Ready to get started? Just send me a message or use one of the commands above!
    """
    await update.message.reply_text(welcome_message.strip())

async def help_command(update, context):
    """Handle /help command"""
    help_text = """
📚 **Kroolo Agent Bot Commands:**

🔹 **Basic Commands:**
• /start - Welcome message and introduction
• /help - Show this help message
• /status - Check bot status

🔹 **AI Features:**
• /ask <question> - Ask me anything using AI
• /topic <category> - Get topic suggestions

🔹 **Examples:**
• /ask How does machine learning work?
• /topic science
• /status

💡 **Tips:**
• You can also just send me a message and I'll respond
• I'm powered by advanced AI to help with any questions
• Feel free to ask about any topic!
    """
    await update.message.reply_text(help_text.strip())

async def ask_command(update, context):
    """Handle /ask command"""
    if not context.args:
        await update.message.reply_text("❌ Please provide a question after /ask\n\nExample: /ask What is quantum computing?")
        return
    
    question = " ".join(context.args)
    await update.message.reply_text(f"🤔 Processing your question: {question}\n\n⏳ This feature requires AI integration. For now, I can confirm I received: '{question}'")

async def topic_command(update, context):
    """Handle /topic command"""
    topics = [
        "🚀 Technology & Innovation",
        "🧠 Artificial Intelligence",
        "🌍 Science & Nature", 
        "📚 Education & Learning",
        "💼 Business & Finance",
        "🎨 Arts & Creativity",
        "🏥 Health & Wellness",
        "🌱 Environment & Sustainability"
    ]
    
    topic_text = "🎯 **Topic Suggestions:**\n\n" + "\n".join(topics)
    topic_text += "\n\n💡 Send me a message about any of these topics or ask me anything!"
    
    await update.message.reply_text(topic_text)

async def status_command(update, context):
    """Handle /status command"""
    status_text = """
📊 **Bot Status:**

✅ **Bot:** Online and running
✅ **Connection:** Connected to Telegram
✅ **Commands:** All handlers active
✅ **Environment:** Local development mode

🔄 **Mode:** Polling (actively listening for messages)
🌐 **API:** FastAPI server available at localhost:8000

💡 **Next Steps:**
• Send me a message to test
• Use /help to see all commands
• Try /ask with a question
    """
    await update.message.reply_text(status_text.strip())

async def handle_message(update, context):
    """Handle regular messages"""
    message_text = update.message.text
    user = update.effective_user
    
    # Simple response for now
    response = f"👋 Hi {user.first_name}! I received your message: '{message_text}'\n\n💡 Try using /help to see what I can do, or /ask to ask me a question!"
    await update.message.reply_text(response)

async def main():
    """Main function to start the standalone bot"""
    try:
        print("🚀 Starting Standalone Kroolo Bot...")
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("ask", ask_command))
        application.add_handler(CommandHandler("topic", topic_command))
        application.add_handler(CommandHandler("status", status_command))
        
        # Add message handler for regular messages
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("✅ All handlers registered")
        
        # Delete webhook
        await bot.delete_webhook()
        print("✅ Webhook deleted")
        
        # Start polling
        print("🤖 Starting polling...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        print("✅ Bot polling started successfully!")
        print("📱 Bot is now listening and processing messages!")
        
        # Get bot info
        bot_info = await bot.get_me()
        print(f"🤖 Bot username: @{bot_info.username}")
        
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
