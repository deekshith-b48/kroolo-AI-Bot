#!/bin/bash

# Kroolo Agent Bot Deployment Script
# This script helps you deploy the bot locally or to production

set -e

echo "🚀 Kroolo Agent Bot Deployment Script"
echo "====================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create one based on env.example"
    exit 1
fi

# Load environment variables
source .env

# Check required environment variables
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ TELEGRAM_BOT_TOKEN not set in .env"
    exit 1
fi

if [ -z "$TELEGRAM_WEBHOOK_SECRET" ]; then
    echo "❌ TELEGRAM_WEBHOOK_SECRET not set in .env"
    exit 1
fi

echo "✅ Environment variables loaded"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
echo "🔍 Checking dependencies..."

if ! command_exists docker; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command_exists docker-compose; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

echo "✅ Dependencies check passed"

# Function to deploy locally
deploy_local() {
    echo "🏠 Deploying locally..."
    
    # Build and start services
    docker-compose up -d --build
    
    echo "✅ Local deployment started!"
    echo "📱 Bot should be available at: http://localhost:8000"
    echo "🔍 Health check: http://localhost:8000/health"
    echo "📚 API docs: http://localhost:8000/docs"
}

# Function to deploy with ngrok
deploy_with_ngrok() {
    echo "🌐 Deploying with ngrok..."
    
    # Check if ngrok is installed
    if ! command_exists ngrok; then
        echo "❌ ngrok not found. Please install ngrok first:"
        echo "   https://ngrok.com/download"
        exit 1
    fi
    
    # Start local services
    docker-compose up -d --build
    
    echo "⏳ Waiting for services to start..."
    sleep 10
    
    # Start ngrok
    echo "🚀 Starting ngrok tunnel..."
    ngrok http 8000 &
    NGROK_PID=$!
    
    # Wait for ngrok to start
    sleep 5
    
    # Get ngrok URL
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"[^"]*' | cut -d'"' -f4 | head -1)
    
    if [ -z "$NGROK_URL" ]; then
        echo "❌ Failed to get ngrok URL"
        kill $NGROK_PID 2>/dev/null || true
        exit 1
    fi
    
    echo "✅ ngrok tunnel started: $NGROK_URL"
    
    # Set webhook
    WEBHOOK_URL="$NGROK_URL/webhook"
    echo "🔗 Setting webhook to: $WEBHOOK_URL"
    
    # Update .env with ngrok URL
    sed -i.bak "s|TELEGRAM_WEBHOOK_URL=.*|TELEGRAM_WEBHOOK_URL=$WEBHOOK_URL|" .env
    
    # Restart bot with new webhook URL
    docker-compose restart kroolo-bot
    
    echo "✅ Webhook set successfully!"
    echo "📱 Bot is now accessible via Telegram"
    echo "🌐 Public URL: $NGROK_URL"
    echo "🔍 Health check: $NGROK_URL/health"
    
    echo ""
    echo "💡 To stop ngrok, run: kill $NGROK_PID"
    echo "💡 To stop all services, run: docker-compose down"
}

# Function to deploy to production
deploy_production() {
    echo "🚀 Deploying to production..."
    
    if [ -z "$TELEGRAM_WEBHOOK_URL" ]; then
        echo "❌ TELEGRAM_WEBHOOK_URL not set for production deployment"
        exit 1
    fi
    
    # Start production services
    docker-compose --profile production up -d --build
    
    echo "✅ Production deployment started!"
    echo "🌐 Bot accessible at: $TELEGRAM_WEBHOOK_URL"
    echo "🔍 Health check: $TELEGRAM_WEBHOOK_URL/health"
}

# Function to stop services
stop_services() {
    echo "🛑 Stopping services..."
    docker-compose down
    echo "✅ Services stopped"
}

# Function to view logs
view_logs() {
    echo "📋 Viewing logs..."
    docker-compose logs -f
}

# Function to check status
check_status() {
    echo "📊 Checking service status..."
    docker-compose ps
    
    echo ""
    echo "🔍 Health check:"
    curl -s http://localhost:8000/health | jq . 2>/dev/null || curl -s http://localhost:8000/health
}

# Function to show help
show_help() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  local     - Deploy locally with Docker Compose"
    echo "  ngrok     - Deploy locally with ngrok tunnel"
    echo "  prod      - Deploy to production"
    echo "  stop      - Stop all services"
    echo "  logs      - View service logs"
    echo "  status    - Check service status"
    echo "  help      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 local     # Deploy locally"
    echo "  $0 ngrok     # Deploy with ngrok tunnel"
    echo "  $0 stop      # Stop services"
}

# Main script logic
case "${1:-help}" in
    "local")
        deploy_local
        ;;
    "ngrok")
        deploy_with_ngrok
        ;;
    "prod")
        deploy_production
        ;;
    "stop")
        stop_services
        ;;
    "logs")
        view_logs
        ;;
    "status")
        check_status
        ;;
    "help"|*)
        show_help
        ;;
esac
