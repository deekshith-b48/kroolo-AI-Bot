# 🤖 Kroolo Agent Bot

A powerful, AI-powered Telegram bot built with FastAPI, featuring community management, auto-moderation, and intelligent responses.

## ✨ Features

- **AI-Powered Responses**: OpenAI and HuggingFace integration for intelligent conversations
- **Community Management**: Auto-topic detection and community settings
- **Auto-Moderation**: Spam detection and content filtering with admin controls
- **Inline Queries**: Quick responses with `@krooloAgentBot <query>`
- **Role-Based Access**: Admin, moderator, and user role management
- **Rate Limiting**: Redis-based rate limiting to prevent abuse
- **Comprehensive Logging**: Structured logging for monitoring and debugging
- **RESTful API**: Full API for external integrations and admin management

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram      │    │   FastAPI       │    │   Redis         │
│   Bot API       │◄──►│   Webhook       │◄──►│   Cache &       │
│                 │    │   Handler       │    │   Rate Limiting │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   SQLite        │
                       │   Database      │
                       │   (Users, Logs) │
                       └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Docker and Docker Compose
- Telegram Bot Token (from @BotFather)
- OpenAI API Key (optional, for AI features)

### 1. Clone and Setup

```bash
git clone <your-repo>
cd krooloAgentBot

# Copy environment file
cp env.example .env

# Edit .env with your tokens
nano .env
```

### 2. Configure Environment

Edit `.env` file with your configuration:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook
TELEGRAM_WEBHOOK_SECRET=your_webhook_secret_here
OPENAI_API_KEY=your_openai_api_key_here
ADMIN_IDS=123456789,987654321
DATABASE_URL=sqlite:///./kroolo.db
REDIS_URL=redis://localhost:6379/0
```

### 3. Deploy with Docker

```bash
# Make deploy script executable
chmod +x deploy.sh

# Deploy locally
./deploy.sh local

# Or deploy with ngrok tunnel (for testing)
./deploy.sh ngrok

# Check status
./deploy.sh status
```

### 4. Set Webhook (if not using ngrok)

```bash
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d "url=https://yourdomain.com/webhook" \
  -d "secret_token=${TELEGRAM_WEBHOOK_SECRET}"
```

## 📱 Bot Commands

### Basic Commands

- `/start` - Start the bot and see introduction
- `/help` - Show available commands
- `/ask <question>` - Ask AI a question
- `/topic <name>` - Set or view community topics

### Admin Commands

- `/status` - View bot status and health
- `/admin_help` - Show admin commands
- `/promote @username` - Promote user to moderator
- `/demote @username` - Demote user
- `/ban @username` - Ban user from bot
- `/unban @username` - Unban user

### Inline Usage

Type `@krooloAgentBot <query>` anywhere in chat for instant responses.

## 🔧 API Endpoints

### Health & Status

- `GET /health` - Bot health check
- `GET /` - Bot information and API docs

### Admin API

- `GET /admin/logs` - Get bot logs
- `GET /admin/users` - Get user list
- `GET /admin/backup` - Create system backup
- `GET /admin/status` - Detailed system status

### Community Management

- `GET /community/{chat_id}/topics` - Get community topics
- `POST /community/{chat_id}/topics` - Set community topic

### Rate Limiting

- `GET /rate-limit/{user_id}/{chat_id}` - Get rate limit info

## 🏠 Local Development

### Without Docker

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start Redis (if not running)
redis-server

# Run the bot
uvicorn app:app --reload --port 8000
```

### With Docker

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 🔒 Security Features

- **Webhook Secret Verification**: All webhook requests are verified
- **Rate Limiting**: Per-user and per-chat rate limiting
- **Role-Based Access**: Admin-only commands and API endpoints
- **Input Sanitization**: Safe handling of user inputs
- **Content Moderation**: AI-powered spam detection

## 📊 Monitoring

### Health Checks

- Bot status: `/health` endpoint
- Service monitoring: Docker health checks
- Rate limiting: Real-time rate limit information

### Logging

- Structured JSON logging
- User action tracking
- Admin action logging
- Error tracking and reporting

## 🚀 Production Deployment

### Render.com

1. Connect your GitHub repository
2. Set environment variables
3. Deploy with build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`

### Railway

1. Connect your GitHub repository
2. Set environment variables
3. Deploy automatically

### VPS/Cloud

1. Clone repository to server
2. Install dependencies
3. Set up systemd service
4. Configure nginx reverse proxy
5. Set up SSL certificates

## 🔧 Configuration

### Bot Settings

Configure bot behavior through environment variables:

- `TELEGRAM_BOT_TOKEN`: Your bot token from @BotFather
- `TELEGRAM_WEBHOOK_SECRET`: Secret for webhook verification
- `OPENAI_API_KEY`: OpenAI API key for AI features
- `ADMIN_IDS`: Comma-separated list of admin Telegram IDs
- `DATABASE_URL`: Database connection string
- `REDIS_URL`: Redis connection string

### Rate Limiting

Default rate limits (configurable):

- **Per User**: 10 requests per minute
- **Per Chat**: 50 requests per minute
- **Global**: 1000 requests per minute

## 🧪 Testing

### Manual Testing

1. Start the bot locally
2. Send commands in Telegram
3. Test inline queries
4. Verify admin functions

### API Testing

```bash
# Health check
curl http://localhost:8000/health

# Get logs
curl http://localhost:8000/admin/logs

# Check rate limits
curl http://localhost:8000/rate-limit/123/456
```

## 📈 Scaling

### Horizontal Scaling

- Multiple bot instances behind load balancer
- Redis for shared state and caching
- Database connection pooling

### Performance Optimization

- Redis caching for frequent queries
- Async processing for webhook handling
- Rate limiting to prevent abuse
- Efficient database queries

## 🔮 Future Enhancements

- **LangChain Integration**: Advanced AI workflows
- **Vector Database**: Document Q&A capabilities
- **Multi-Language Support**: Internationalization
- **Advanced Analytics**: User behavior insights
- **Plugin System**: Extensible bot functionality

## 🐛 Troubleshooting

### Common Issues

1. **Webhook not working**: Check webhook URL and secret
2. **Redis connection failed**: Ensure Redis is running
3. **Database errors**: Check database connection and permissions
4. **Rate limiting**: Check Redis connection and configuration

### Debug Mode

Enable debug logging by setting log level in the code:

```python
logging.basicConfig(level=logging.DEBUG)
```

### Support

- Check logs: `docker-compose logs -f`
- Health check: `curl http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For support and questions:

- Create an issue in the repository
- Check the documentation
- Review the troubleshooting section

---

**Built with ❤️ using FastAPI, Python, and Telegram Bot API**
# kroolo-AI-Bot
# kroolo-AI-Bot
# kroolo-AI-Bot
# kroolo-AI-Bot
