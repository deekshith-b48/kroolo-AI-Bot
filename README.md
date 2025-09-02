# 🤖 Kroolo AI Bot - Advanced Telegram Assistant

A production-grade, AI-powered Telegram bot with **enhanced response formatting**, community management, and intelligent conversation capabilities. Built with modern Python architecture and optimized for both private chats and group interactions.

## ✨ Key Features

### 🧠 **Advanced AI Integration**
- **Multi-Model Support**: OpenAI GPT, Google Gemini, and HuggingFace models
- **Intelligent Response Formatting**: Structured responses with proper line breaks and Telegram markdown
- **Concise & Clear**: AI responses optimized for readability with bullet points and headers
- **Context-Aware**: Smart conversation handling with memory and context retention
- **Rate Limiting**: Built-in protection against API abuse and quota management

### 📱 **Enhanced User Experience**
- **Structured Responses**: AI responses formatted with:
  - **Bold headers** for key sections
  - • Bullet points for lists and information
  - Proper line breaks for readability
  - Maximum 200-word responses for conciseness
- **Inline Mode**: Quick responses with `@kroolobot <query>` in any chat
- **Group Optimized**: Seamless operation in Telegram groups and supergroups
- **Private Admin Commands**: Sensitive commands sent privately to prevent data leakage

### 🛡️ **Community Management**
- **Role-Based Access Control**: Admin, moderator, and user permissions
- **Topic Management**: Dynamic community topic setting and tracking
- **Auto-Moderation**: Spam detection and content filtering
- **User Management**: Ban, unban, promote, and demote users
- **Comprehensive Logging**: All actions tracked with detailed logs

### ⚡ **Performance & Reliability**
- **Long-Polling Architecture**: No webhook dependencies for maximum reliability
- **Async Processing**: Non-blocking operations for optimal performance
- **Redis Caching**: Fast response caching and session management
- **Database Integration**: SQLite/PostgreSQL with migration support
- **Health Monitoring**: Real-time system health checks and monitoring

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.10+** (recommended)
- **Telegram Bot Token** from [@BotFather](https://t.me/botfather)
- **AI API Keys**: OpenAI or Google Gemini (optional but recommended)
- **Redis Server** (optional, for caching and rate limiting)

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/deekshith-b48/kroolo-AI-Bot.git
cd kroolo-AI-Bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp env.example .env

# Edit with your actual values
nano .env
```

**Required Environment Variables:**
```env
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_IDS=your_telegram_user_id,another_admin_id

# AI Services (choose one or more)
OPENAI_API_KEY=your_openai_key_here
GEMINI_API_KEY=your_gemini_key_here
HUGGINGFACE_API_KEY=your_hf_key_here

# Database (optional)
DATABASE_URL=sqlite:///./kroolo_bot.db

# Redis (optional)
REDIS_URL=redis://localhost:6379/0
```

### 3. Start the Bot

```bash
# Recommended: Use the main bot file
python kroolo_bot.py

# Alternative: Use startup script
python start_kroolo_bot.py

# For development with auto-reload
python -m uvicorn app:app --reload --port 8000
```

## 📱 Bot Commands & Usage

### 🔤 **User Commands**
| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Initialize bot and show welcome message | `/start` |
| `/help` | Display available commands and usage | `/help` |
| `/ask <question>` | Ask AI any question with formatted response | `/ask What is Python?` |
| `/topic <name>` | Set or view community topic | `/topic Python Development` |

### 🔐 **Admin Commands** (Sent Privately in Groups)
| Command | Description | Permission Level |
|---------|-------------|------------------|
| `/status` | View bot health and statistics | Admin |
| `/admin_help` | Show admin commands for your role | Admin |
| `/promote @user [role]` | Promote user to moderator/admin | Admin |
| `/demote @user` | Demote user to regular user | Admin |
| `/ban @user` | Ban user from using the bot | Admin |
| `/unban @user` | Remove user ban | Admin |
| `/users` | List all users and their roles | Admin |
| `/backup` | Create database backup | Super Admin |

### 🔍 **Inline Mode Usage**
Type `@your_bot_username <query>` anywhere in Telegram for instant AI responses:
- `@kroolobot What is machine learning?`
- `@kroolobot Explain quantum computing`
- `@kroolobot Generate a Python function`

## 🏗️ Architecture Overview

```
kroolo-AI-Bot/
├── 📁 Core Files
│   ├── kroolo_bot.py              # Main bot with long-polling
│   ├── app.py                     # FastAPI web server (optional)
│   ├── db.py                      # Database models and operations
│   └── requirements.txt           # Python dependencies
│
├── 📁 Handlers (Bot Logic)
│   ├── commands.py                # User command implementations
│   ├── inline.py                  # Inline query handling
│   ├── community.py               # Community management
│   └── community_commands.py      # Community engagement features
│
├── 📁 Services (Business Logic)
│   ├── ai_service.py              # 🔥 Enhanced AI with formatting
│   ├── ai_service_gemini.py       # Google Gemini integration
│   ├── auth.py                    # Authentication & permissions
│   ├── scheduler.py               # Task scheduling
│   └── community_engagement.py    # Community features
│
├── 📁 Utils (Helper Functions)
│   ├── cache.py                   # Redis caching & rate limiting
│   └── logger.py                  # Structured logging
│
├── 📁 Configuration
│   ├── config/settings.py         # App configuration
│   ├── env.example               # Environment template
│   └── .env                      # Your environment variables
│
├── 📁 Documentation
│   ├── README.md                 # This file
│   ├── SETUP_GUIDE.md           # Detailed setup instructions
│   └── REFACTORING_COMPLETE.md  # Recent improvements log
│
└── 📁 Deployment
    ├── Dockerfile                # Docker configuration
    ├── docker-compose.yml       # Multi-container setup
    └── scripts/                 # Deployment scripts
```

## 🎯 **Recent Major Improvements (v3.1.0)**

### ✨ **Enhanced AI Response Formatting**
- **Structured Output**: AI responses now include proper headers, bullet points, and line breaks
- **Telegram Optimized**: Responses formatted specifically for Telegram's markdown
- **Concise Responses**: Limited to 200 words with 300 token limits for clarity
- **Better Readability**: Clear section separation and visual hierarchy

**Before:**
```
Hi there! Im Kroolo AI Bot, your friendly Telegram assistant. • Im here to help your community with information and tasks. • I can answer questions, provide summaries, and assist with various requests. • Think of me as a helpful, concise, and always-available community member.
```

**After:**
```
**About Me:**
• I'm Kroolo AI Bot, your friendly Telegram assistant
• I help communities with information and tasks

**What I Can Do:**
• Answer questions and provide summaries
• Assist with various requests
• Be a helpful, always-available community member
```

### 🔧 **AI Service Improvements**
- **Multi-Model Fallback**: OpenAI → Gemini → HuggingFace automatic fallback
- **Enhanced Prompts**: AI models trained with specific formatting instructions
- **Better Error Handling**: Graceful degradation when services are unavailable
- **Response Caching**: Intelligent caching to reduce API calls and costs

### 🏗️ **Architecture Enhancements**
- **Modular Design**: Clean separation of concerns across services
- **Async Operations**: Non-blocking I/O for better performance
- **Health Monitoring**: Comprehensive system health checks
- **Logging Improvements**: Structured JSON logging with action tracking

## 🔧 Configuration & Customization

### 🤖 **AI Service Configuration**

```python
# AI Service Settings (in services/ai_service.py)
MAX_TOKENS = 300                    # Response length limit
MAX_REQUESTS_PER_MINUTE = 15       # Rate limiting
TEMPERATURE = 0.7                  # Response creativity (0-1)
PRIMARY_SERVICE = "gemini"         # Primary AI service
```

### 📊 **Response Formatting Settings**

The AI responses are configured to be:
- **Concise**: Maximum 200 words
- **Structured**: Headers with `**bold**` formatting
- **Listed**: Bullet points with `•` for easy reading
- **Spaced**: Proper line breaks between sections
- **Telegram-Optimized**: Uses Telegram's markdown formatting

### 🗄️ **Database Configuration**

```env
# SQLite (Development)
DATABASE_URL=sqlite:///./kroolo_bot.db

# PostgreSQL (Production)
DATABASE_URL=postgresql://user:password@localhost/kroolo_bot

# MySQL (Alternative)
DATABASE_URL=mysql+pymysql://user:password@localhost/kroolo_bot
```

### ⚡ **Redis Configuration**

```env
# Local Redis
REDIS_URL=redis://localhost:6379/0

# Redis Cloud
REDIS_URL=redis://username:password@host:port/0

# Redis with SSL
REDIS_URL=rediss://username:password@host:port/0
```

## 🚀 Deployment Options

### 🐳 **Docker Deployment (Recommended)**

```bash
# Using Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**docker-compose.yml features:**
- Multi-container setup with Redis
- Automatic restart policies
- Volume persistence for data
- Environment variable management

### ☁️ **Cloud Deployment**

#### **Railway**
1. Connect GitHub repository
2. Set environment variables
3. Deploy automatically

#### **Render**
1. Connect repository
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `python kroolo_bot.py`

#### **Heroku**
```bash
# Install Heroku CLI and login
heroku create your-bot-name
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set OPENAI_API_KEY=your_key
git push heroku main
```

### 🖥️ **VPS/Server Deployment**

```bash
# Clone and setup
git clone https://github.com/deekshith-b48/kroolo-AI-Bot.git
cd kroolo-AI-Bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create systemd service
sudo nano /etc/systemd/system/kroolo-bot.service

# Start service
sudo systemctl enable kroolo-bot
sudo systemctl start kroolo-bot
```

## 📊 Monitoring & Analytics

### 🔍 **Health Monitoring**

```bash
# Check bot status
curl http://localhost:8000/health

# Detailed system status
curl http://localhost:8000/admin/status

# View logs
tail -f bot_errors.log
```

### 📈 **Performance Metrics**

The bot tracks:
- **Response Times**: AI service response times
- **Success Rates**: API call success percentages
- **User Activity**: Command usage statistics
- **Error Rates**: Failed requests and error types
- **Rate Limiting**: Request patterns and limits

### 🔔 **Logging Features**

- **Structured Logging**: JSON-formatted logs for easy parsing
- **Action Tracking**: All user and admin actions logged
- **Error Monitoring**: Comprehensive error tracking with stack traces
- **Performance Logging**: Response times and resource usage

## 🧪 Testing

### 🔬 **Running Tests**

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-asyncio

# Run all tests
pytest

# Run with coverage
pytest --cov=services --cov=handlers tests/

# Run specific test categories
pytest tests/test_ai_service.py -v
pytest tests/test_commands.py -v
pytest tests/test_auth.py -v
```

### 🎯 **Test Categories**

- **Unit Tests**: Individual component testing
- **Integration Tests**: Service interaction testing
- **API Tests**: Telegram API interaction testing
- **Performance Tests**: Load and stress testing

## 🔒 Security Features

### 🛡️ **Built-in Security**

- **Input Sanitization**: Prevents injection attacks and malicious input
- **Rate Limiting**: Protects against abuse and spam
- **Role-Based Access**: Hierarchical permission system
- **Content Filtering**: AI-powered inappropriate content detection
- **Secure Token Storage**: Environment-based sensitive data storage

### 🔐 **Authentication & Authorization**

```python
# Permission levels
USER = 0           # Basic user permissions
MODERATOR = 1      # Community moderation
ADMIN = 2          # Full bot administration
SUPER_ADMIN = 3    # System-level access
```

### 🚫 **Content Moderation**

- **Spam Detection**: AI-powered spam identification
- **Content Filtering**: Inappropriate content blocking
- **User Reporting**: Community-based reporting system
- **Automatic Actions**: Configurable responses to violations

## 🤝 Contributing

### 🔄 **Development Workflow**

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Make** your changes with proper formatting
4. **Add** tests for new functionality
5. **Commit** changes (`git commit -m 'Add amazing feature'`)
6. **Push** to branch (`git push origin feature/amazing-feature`)
7. **Create** a Pull Request

### 📝 **Contribution Guidelines**

- **Code Style**: Follow PEP 8 Python style guidelines
- **Documentation**: Update README and docstrings for new features
- **Testing**: Add tests for all new functionality
- **Commits**: Use clear, descriptive commit messages
- **Issues**: Check existing issues before creating new ones

### 🐛 **Bug Reports**

When reporting bugs, please include:
- **Environment**: Python version, OS, dependencies
- **Steps to Reproduce**: Clear reproduction steps
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Logs**: Relevant error messages and logs

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

## 🆘 Support & Help

### 📞 **Getting Help**

- **Bot Commands**: Use `/help` in the bot for command reference
- **Admin Help**: Use `/admin_help` for administrator assistance
- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check this README and setup guides

### 🔧 **Troubleshooting**

**Common Issues:**

1. **Bot not responding**: Check token and network connectivity
2. **AI not working**: Verify API keys and quotas
3. **Database errors**: Check database URL and permissions
4. **Redis connection failed**: Ensure Redis server is running

**Debug Commands:**
```bash
# Check bot status
python -c "from services.ai_service import AIService; print(AIService().get_service_health())"

# Test database connection
python -c "from db import Database; db = Database(); print('DB OK')"

# Validate environment
python -c "import os; print('Token:', bool(os.getenv('TELEGRAM_BOT_TOKEN')))"
```

## 🔄 Changelog

### 🚀 **v3.1.0 - Enhanced AI Responses (Current)**
- ✨ **Structured AI Responses**: Proper formatting with headers and bullet points
- 🎯 **Concise Output**: Limited to 200 words for better readability
- 📱 **Telegram Optimized**: Better markdown formatting for mobile users
- 🔧 **Improved Prompts**: AI models trained with specific formatting instructions
- ⚡ **Performance**: Reduced token limits (300) for faster responses
- 🎨 **Visual Structure**: Clear section separation and hierarchy

### 🔄 **v3.0.0 - Complete Refactor**
- 🚀 **Long-Polling Architecture**: Removed webhook dependencies
- 🎯 **Group Optimized**: Enhanced inline mode for Telegram groups
- 🔐 **Private Admin Commands**: Secure admin command handling
- 🛡️ **Enhanced Permissions**: Robust role-based access control
- 🧹 **Clean Codebase**: Removed redundant files and deprecated code
- ⚡ **Improved Performance**: Streamlined architecture
- 🧪 **Testing Framework**: Comprehensive test suite
- 📋 **Better Documentation**: Complete setup and usage guides

### 📈 **v2.0.0 - Major Improvements**
- ✅ Command-based interaction (`/ask` instead of @mentions)
- ✅ Input validation and sanitization
- ✅ Robust scheduling system
- ✅ AI service reliability improvements
- ✅ Enhanced error handling
- ✅ Health monitoring and maintenance
- ✅ Codebase optimization

### 🎯 **v1.0.0 - Initial Release**
- Basic AI integration with OpenAI
- Community management features
- User role system
- Webhook support

---

## 🌟 **Why Choose Kroolo AI Bot?**

### 🏆 **Production Ready**
- **Reliable**: Long-polling architecture with robust error handling
- **Scalable**: Modular design supports growth and customization
- **Secure**: Comprehensive security features and access control
- **Monitored**: Built-in health checks and performance monitoring

### 🎨 **User-Friendly**
- **Clear Responses**: Structured AI output with proper formatting
- **Fast Performance**: Optimized for quick response times
- **Group Optimized**: Seamless operation in Telegram communities
- **Easy Setup**: Simple configuration and deployment process

### 🔧 **Developer Friendly**
- **Well Documented**: Comprehensive guides and code documentation
- **Modular Design**: Easy to extend and customize
- **Test Coverage**: Robust testing framework included
- **Open Source**: MIT license with active community support

---

**🤖 Built with ❤️ for the Telegram community | 🚀 Ready for production deployment**

**⭐ Star this repository if you find it helpful! | 🐛 Report issues on GitHub**