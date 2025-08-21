#!/bin/bash

# Kroolo AI Bot - Complete Startup Script
# Starts all services and the bot with proper configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_banner() {
    echo -e "${PURPLE}"
    echo "🤖================================================================🤖"
    echo "🚀                KROOLO AI BOT STARTUP                        🚀"
    echo "🤖================================================================🤖"
    echo -e "${NC}"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Python
    if ! command -v python &> /dev/null; then
        log_error "Python not found. Please install Python 3.11+"
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install Docker"
        exit 1
    fi
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        log_info "Creating virtual environment..."
        python -m venv venv
    fi
    
    log_success "Prerequisites OK"
}

start_services() {
    log_info "Starting Docker services..."
    
    # Start PostgreSQL, Redis, and Qdrant
    if command -v docker-compose &> /dev/null; then
        sudo docker-compose up -d postgres redis qdrant
    else
        sudo docker compose up -d postgres redis qdrant
    fi
    
    # Wait for services to be ready
    log_info "Waiting for services to initialize..."
    sleep 10
    
    # Check service health
    if curl -f http://localhost:6379 &> /dev/null; then
        log_success "Redis is running"
    else
        log_warning "Redis may not be fully ready"
    fi
    
    log_success "Docker services started"
}

start_bot() {
    log_info "Starting Kroolo AI Bot..."
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        log_warning ".env file not found. Creating from template..."
        cp env.example .env
    fi
    
    # Start the bot server
    log_info "🌐 Starting web server on http://localhost:8000"
    log_info "📡 Webhook endpoint: http://localhost:8000/v1/telegram/webhook/krooloAgentBot"
    log_info "📊 Health check: http://localhost:8000/health"
    log_info "📚 API docs: http://localhost:8000/docs"
    
    # Use nohup to run in background
    nohup venv/bin/python scripts/test_server.py > kroolo_bot.log 2>&1 &
    BOT_PID=$!
    
    # Wait for server to start
    sleep 5
    
    # Test if server is running
    if curl -f http://localhost:8000/health &> /dev/null; then
        log_success "🎉 Kroolo AI Bot is running successfully!"
        log_info "Process ID: $BOT_PID"
        log_info "Logs: tail -f kroolo_bot.log"
    else
        log_error "❌ Bot failed to start. Check kroolo_bot.log for details"
        exit 1
    fi
}

show_status() {
    log_info "🔍 System Status Check..."
    
    echo -e "\n${CYAN}📊 SERVICE STATUS:${NC}"
    echo "===================="
    
    # Check bot health
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        echo "✅ Kroolo AI Bot: HEALTHY"
    else
        echo "❌ Kroolo AI Bot: UNHEALTHY"
    fi
    
    # Check Docker services
    echo -e "\n${CYAN}🐳 DOCKER SERVICES:${NC}"
    sudo docker-compose ps
    
    echo -e "\n${CYAN}🌐 ENDPOINTS:${NC}"
    echo "Health Check: http://localhost:8000/health"
    echo "API Docs: http://localhost:8000/docs"
    echo "Webhook: http://localhost:8000/v1/telegram/webhook/krooloAgentBot"
    
    echo -e "\n${CYAN}📝 LOGS:${NC}"
    echo "Bot logs: tail -f kroolo_bot.log"
    echo "Docker logs: sudo docker-compose logs -f"
}

show_next_steps() {
    echo -e "\n${GREEN}🎯 NEXT STEPS:${NC}"
    echo "=============="
    echo "1. 🔑 Set up credentials:"
    echo "   python scripts/setup_credentials.py"
    echo ""
    echo "2. 🧪 Test functionality:"
    echo "   python scripts/test_all_functionality.py"
    echo ""
    echo "3. 📱 Configure your Telegram bot:"
    echo "   - Add bot to a group"
    echo "   - Send: @YourBot /start"
    echo "   - Try: @AlanTuring Hello!"
    echo ""
    echo "4. 🚀 For production deployment:"
    echo "   ./scripts/deploy_production.sh"
    echo ""
    echo "🎊 Your Kroolo AI Bot is ready to go!"
}

main() {
    print_banner
    
    log_info "Starting Kroolo AI Bot setup..."
    
    check_prerequisites
    start_services
    start_bot
    show_status
    show_next_steps
    
    log_success "🎉 Kroolo AI Bot startup completed!"
    log_info "🛑 To stop: pkill -f test_server.py && sudo docker-compose down"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --status       Show current status"
        echo "  --stop         Stop all services"
        echo "  --restart      Restart all services"
        echo "  --logs         Show logs"
        ;;
    --status)
        show_status
        ;;
    --stop)
        log_info "Stopping Kroolo AI Bot..."
        pkill -f test_server.py || true
        sudo docker-compose down
        log_success "All services stopped"
        ;;
    --restart)
        log_info "Restarting Kroolo AI Bot..."
        pkill -f test_server.py || true
        sudo docker-compose restart
        sleep 5
        nohup venv/bin/python scripts/test_server.py > kroolo_bot.log 2>&1 &
        sleep 3
        show_status
        log_success "Services restarted"
        ;;
    --logs)
        echo "🔍 Recent bot logs:"
        tail -50 kroolo_bot.log
        echo -e "\n🔍 Docker logs:"
        sudo docker-compose logs --tail=20
        ;;
    *)
        main
        ;;
esac
