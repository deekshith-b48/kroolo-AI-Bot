# 🚀 Kroolo Bot Setup Guide

This guide will help you set up and run the refactored Kroolo AI Bot.

## 📋 Prerequisites

1. **Python 3.8+** installed on your system
2. **Telegram Bot Token** from [@BotFather](https://t.me/botfather)
3. **OpenAI API Key** for AI features
4. **Your Telegram User ID** (you can get this from [@userinfobot](https://t.me/userinfobot))

## 🔧 Setup Steps

### 1. Environment Configuration

Create a `.env` file in the project root:

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here
OPENAI_API_KEY=your_openai_key_here  
ADMIN_IDS=your_telegram_user_id

# Optional (defaults provided)
DATABASE_URL=sqlite:///./kroolo_bot.db
REDIS_URL=redis://localhost:6379/0
```

### 2. Install Dependencies

```bash
# Using virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run the Bot

```bash
# Start the bot
python start_kroolo_bot.py
```

## 🤖 Bot Features

### For Regular Users:
- `/start` - Initialize the bot
- `/help` - Show available commands  
- `/ask <question>` - Ask AI anything
- `/topic <name>` - Set community topic
- **Inline Mode**: Type `@your_bot_name query` in any chat

### For Admins:
- `/status` - View bot status (sent privately in groups)
- `/admin_help` - Show admin commands based on your role
- `/promote @user` - Promote user to moderator/admin
- `/users` - List all users and their roles
- `/backup` - Create database backup

## 🔐 Permission System

- **👤 User**: Regular user (default)
- **🛡️ Moderator**: Can ban/unban users, moderate content
- **⚡ Admin**: Can promote/demote users, manage settings  
- **👑 Superadmin**: Full system access

## 🎯 Group Usage

1. **Add the bot to your Telegram group**
2. **Make it an admin** (optional, for better functionality)
3. **Use inline mode**: Type `@your_bot_name your question`
4. **Admin commands are sent privately** to prevent data leakage

## 🛠️ Troubleshooting

### Common Issues:

1. **"TELEGRAM_BOT_TOKEN not set"**
   - Make sure your `.env` file exists and contains the bot token

2. **"Module not found"**  
   - Activate your virtual environment: `source venv/bin/activate`
   - Install dependencies: `pip install -r requirements.txt`

3. **Bot doesn't respond to commands**
   - Check if the bot is running: look for "✅ Bot started successfully"
   - Verify your bot token is correct
   - Make sure the bot isn't already running elsewhere

4. **Admin commands don't work**
   - Ensure your Telegram user ID is in the `ADMIN_IDS` environment variable
   - Start a private chat with the bot first (for private admin responses)

### Logs and Debugging:

- Check the console output for error messages
- Bot logs are displayed in the terminal when running
- Database file: `kroolo_bot.db` (SQLite)

## 🎉 Success!

If everything is set up correctly, you should see:

```
🚀 Starting Kroolo AI Bot...
✅ Environment validated
🤖 Starting bot with long-polling...
✅ Bot started successfully with long-polling
```

Your bot is now ready to use in Telegram groups and private chats!

## 📞 Support

If you encounter issues:
1. Check this guide first
2. Verify your environment variables
3. Look at the console output for error messages
4. Make sure all dependencies are installed correctly
