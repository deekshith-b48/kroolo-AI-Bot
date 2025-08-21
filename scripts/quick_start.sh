#!/bin/bash

# Kroolo AI Bot - Quick Start Script
# This script automates the initial setup process

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check system requirements
check_requirements() {
    print_status "Checking system requirements..."
    
    # Check Python
    if ! command_exists python3; then
        print_error "Python 3.9+ is required but not installed."
        print_status "Please install Python 3.9+ and try again."
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_success "Python $PYTHON_VERSION found"
    
    # Check Docker
    if ! command_exists docker; then
        print_warning "Docker is not installed. Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        print_success "Docker installed. Please log out and back in for group changes to take effect."
    else
        print_success "Docker found"
    fi
    
    # Check Docker Compose
    if ! command_exists docker-compose; then
        print_warning "Docker Compose is not installed. Installing Docker Compose..."
        sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        print_success "Docker Compose installed"
    else
        print_success "Docker Compose found"
    fi
    
    # Check Git
    if ! command_exists git; then
        print_error "Git is required but not installed."
        print_status "Please install Git and try again."
        exit 1
    else
        print_success "Git found"
    fi
}

# Function to create project structure
create_project_structure() {
    print_status "Creating project structure..."
    
    # Create necessary directories
    mkdir -p src/{core,agents,engines,services,models,database,utils}
    mkdir -p config
    mkdir -p tests/{test_core,test_agents,test_engines,test_services,test_utils}
    mkdir -p docker/{nginx,postgres,prometheus,grafana}
    mkdir -p scripts
    mkdir -p docs
    mkdir -p logs
    mkdir -p data
    
    print_success "Project structure created"
}

# Function to install Python dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "Python dependencies installed"
    else
        print_warning "requirements.txt not found, skipping Python dependency installation"
    fi
    
    # Deactivate virtual environment
    deactivate
}

# Function to setup environment
setup_environment() {
    print_status "Setting up environment..."
    
    # Copy environment template if it doesn't exist
    if [ ! -f ".env" ] && [ -f "env.example" ]; then
        cp env.example .env
        print_success "Environment file created from template"
        print_warning "Please edit .env file with your actual configuration"
    elif [ ! -f ".env" ]; then
        print_warning "No environment template found, creating basic .env file"
        cat > .env << EOF
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/webhook
TELEGRAM_WEBHOOK_SECRET=your_webhook_secret_here

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=2000
OPENAI_TEMPERATURE=0.7

# Database Configuration
DATABASE_URL=postgresql://kroolo_user:kroolo_pass@localhost:5432/kroolo_bot
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333

# Development Settings
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=INFO
EOF
        print_success "Basic environment file created"
        print_warning "Please edit .env file with your actual configuration"
    fi
}

# Function to setup bot
setup_bot() {
    print_status "Setting up Telegram bot..."
    
    # Check if setup script exists
    if [ -f "scripts/setup_bot.py" ]; then
        print_status "Running bot setup script..."
        source venv/bin/activate
        python scripts/setup_bot.py
        deactivate
    else
        print_warning "Bot setup script not found, manual setup required"
        print_status "Please follow the manual setup instructions in the README"
    fi
}

# Function to start services
start_services() {
    print_status "Starting services with Docker Compose..."
    
    # Check if docker-compose.yml exists
    if [ -f "docker-compose.yml" ]; then
        # Start services in background
        docker-compose up -d
        
        # Wait for services to be ready
        print_status "Waiting for services to be ready..."
        sleep 30
        
        # Check service status
        docker-compose ps
        
        print_success "Services started successfully"
    else
        print_warning "docker-compose.yml not found, skipping service startup"
    fi
}

# Function to run health checks
run_health_checks() {
    print_status "Running health checks..."
    
    # Wait a bit more for services to fully initialize
    sleep 10
    
    # Check if main service is responding
    if command_exists curl; then
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            print_success "Main service is responding"
        else
            print_warning "Main service is not responding yet"
        fi
    fi
    
    # Check Docker services
    if [ -f "docker-compose.yml" ]; then
        if docker-compose ps | grep -q "Up"; then
            print_success "Docker services are running"
        else
            print_warning "Some Docker services may not be running properly"
        fi
    fi
}

# Function to show next steps
show_next_steps() {
    echo
    echo "=================================================="
    echo "🎉 Kroolo AI Bot setup completed!"
    echo "=================================================="
    echo
    echo "📋 Next steps:"
    echo "1. Edit .env file with your actual configuration:"
    echo "   - Telegram bot token"
    echo "   - OpenAI API key"
    echo "   - Database credentials"
    echo
    echo "2. Configure your bot with @BotFather:"
    echo "   - Set bot commands"
    echo "   - Configure webhook URL"
    echo
    echo "3. Start the bot:"
    echo "   docker-compose up -d"
    echo
    echo "4. Test the bot:"
    echo "   - Send /start to your bot"
    echo "   - Check health: http://localhost:8000/health"
    echo
    echo "5. Monitor logs:"
    echo "   docker-compose logs -f"
    echo
    echo "📚 Documentation:"
    echo "   - README.md: Project overview"
    echo "   - docs/deployment.md: Deployment guide"
    echo "   - PROJECT_STRUCTURE.md: Architecture details"
    echo
    echo "🆘 Support:"
    echo "   - Create an issue in the repository"
    echo "   - Check the troubleshooting section"
    echo
    echo "Happy botting! 🤖"
}

# Main execution
main() {
    echo "🚀 Kroolo AI Bot - Quick Start"
    echo "================================"
    echo
    
    # Check if we're in the right directory
    if [ ! -f "README.md" ] && [ ! -f "tasks.md" ]; then
        print_error "This script must be run from the Kroolo-Ai-Bot directory"
        exit 1
    fi
    
    # Run setup steps
    check_requirements
    create_project_structure
    install_dependencies
    setup_environment
    setup_bot
    start_services
    run_health_checks
    show_next_steps
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
