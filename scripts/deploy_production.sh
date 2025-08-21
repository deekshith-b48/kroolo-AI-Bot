#!/bin/bash

# Kroolo AI Bot - Production Deployment Script
# This script automates the production deployment process

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="kroolo-ai-bot"
DEPLOYMENT_ENV="production"
DOCKER_REGISTRY=""
IMAGE_TAG="latest"
BACKUP_DIR="/backups/kroolo-bot"
LOG_DIR="/var/log/kroolo-bot"

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

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if running as root or with sudo
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root. Consider using a non-root user with sudo privileges."
    fi
    
    # Check required commands
    local required_commands=("docker" "docker-compose" "git" "curl" "jq")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Required command '$cmd' not found. Please install it first."
            exit 1
        fi
    done
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

create_directories() {
    log_info "Creating necessary directories..."
    
    sudo mkdir -p "$BACKUP_DIR"
    sudo mkdir -p "$LOG_DIR"
    sudo mkdir -p "/etc/kroolo-bot"
    sudo mkdir -p "/var/lib/kroolo-bot"
    
    # Set proper permissions
    sudo chown -R $USER:$USER "$BACKUP_DIR"
    sudo chown -R $USER:$USER "$LOG_DIR"
    sudo chown -R $USER:$USER "/etc/kroolo-bot"
    sudo chown -R $USER:$USER "/var/lib/kroolo-bot"
    
    log_success "Directories created"
}

backup_existing() {
    if [ -d "/opt/$PROJECT_NAME" ]; then
        log_info "Backing up existing installation..."
        
        local backup_name="backup-$(date +%Y%m%d-%H%M%S)"
        sudo cp -r "/opt/$PROJECT_NAME" "$BACKUP_DIR/$backup_name"
        
        log_success "Backup created: $BACKUP_DIR/$backup_name"
    fi
}

setup_environment() {
    log_info "Setting up environment configuration..."
    
    # Copy environment file
    if [ ! -f "/etc/kroolo-bot/.env" ]; then
        if [ -f ".env" ]; then
            sudo cp .env "/etc/kroolo-bot/.env"
            log_success "Environment file copied"
        else
            log_warning "No .env file found. Please create one manually."
        fi
    fi
    
    # Create production environment file
    cat > "/tmp/kroolo-bot.env" << EOF
# Production Environment Configuration
NODE_ENV=production
LOG_LEVEL=info
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-}
TELEGRAM_WEBHOOK_URL=${TELEGRAM_WEBHOOK_URL:-}
OPENAI_API_KEY=${OPENAI_API_KEY:-}
DATABASE_URL=${DATABASE_URL:-postgresql://kroolo:password@localhost:5432/kroolo_bot}
REDIS_URL=${REDIS_URL:-redis://localhost:6379/0}
QDRANT_URL=${QDRANT_URL:-http://localhost:6333}
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
SECURITY_LEVEL=strict
RATE_LIMIT_STRICT=true
CONTENT_MODERATION_LEVEL=strict
EOF
    
    sudo cp "/tmp/kroolo-bot.env" "/etc/kroolo-bot/.env.production"
    rm "/tmp/kroolo-bot.env"
    
    log_success "Environment configuration created"
}

setup_ssl() {
    log_info "Setting up SSL certificates..."
    
    # Check if Let's Encrypt is available
    if command -v certbot &> /dev/null; then
        log_info "Let's Encrypt certbot found. Setting up SSL..."
        
        # This would need to be configured with your domain
        # certbot certonly --standalone -d yourdomain.com
        
        log_warning "SSL setup requires domain configuration. Please run certbot manually."
    else
        log_warning "Let's Encrypt certbot not found. SSL setup skipped."
    fi
}

build_and_deploy() {
    log_info "Building and deploying application..."
    
    # Build Docker images
    log_info "Building Docker images..."
    docker-compose -f docker-compose.yml build --no-cache
    
    # Tag images for production
    if [ -n "$DOCKER_REGISTRY" ]; then
        docker tag kroolo-bot:latest "$DOCKER_REGISTRY/kroolo-bot:$IMAGE_TAG"
        docker push "$DOCKER_REGISTRY/kroolo-bot:$IMAGE_TAG"
    fi
    
    # Stop existing services
    log_info "Stopping existing services..."
    docker-compose -f docker-compose.yml down || true
    
    # Start services
    log_info "Starting services..."
    docker-compose -f docker-compose.yml up -d
    
    log_success "Application deployed successfully"
}

setup_monitoring() {
    log_info "Setting up monitoring and logging..."
    
    # Create systemd service for the bot
    cat > "/tmp/kroolo-bot.service" << EOF
[Unit]
Description=Kroolo AI Bot
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/$PROJECT_NAME
ExecStart=/usr/local/bin/docker-compose -f docker-compose.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
    
    sudo cp "/tmp/kroolo-bot.service" "/etc/systemd/system/kroolo-bot.service"
    rm "/tmp/kroolo-bot.service"
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable kroolo-bot.service
    
    # Setup log rotation
    cat > "/tmp/kroolo-bot.logrotate" << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        systemctl reload kroolo-bot.service
    endscript
}
EOF
    
    sudo cp "/tmp/kroolo-bot.logrotate" "/etc/logrotate.d/kroolo-bot"
    rm "/tmp/kroolo-bot.logrotate"
    
    log_success "Monitoring and logging configured"
}

setup_firewall() {
    log_info "Setting up firewall rules..."
    
    # Check if ufw is available
    if command -v ufw &> /dev/null; then
        sudo ufw allow 22/tcp    # SSH
        sudo ufw allow 80/tcp    # HTTP
        sudo ufw allow 443/tcp   # HTTPS
        sudo ufw allow 8000/tcp  # Bot API
        sudo ufw allow 9090/tcp  # Prometheus
        sudo ufw allow 3000/tcp  # Grafana
        
        log_success "Firewall rules configured"
    else
        log_warning "ufw not found. Please configure firewall manually."
    fi
}

health_check() {
    log_info "Performing health checks..."
    
    # Wait for services to start
    sleep 30
    
    # Check bot health
    if curl -f "http://localhost:8000/health" &> /dev/null; then
        log_success "Bot API is healthy"
    else
        log_error "Bot API health check failed"
        return 1
    fi
    
    # Check Prometheus
    if curl -f "http://localhost:9090/-/healthy" &> /dev/null; then
        log_success "Prometheus is healthy"
    else
        log_warning "Prometheus health check failed"
    fi
    
    # Check Grafana
    if curl -f "http://localhost:3000/api/health" &> /dev/null; then
        log_success "Grafana is healthy"
    else
        log_warning "Grafana health check failed"
    fi
    
    log_success "Health checks completed"
}

setup_backup_cron() {
    log_info "Setting up automated backups..."
    
    # Create backup script
    cat > "/tmp/backup-kroolo.sh" << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/kroolo-bot"
PROJECT_NAME="kroolo-ai-bot"
DATE=$(date +%Y%m%d-%H%M%S)

# Create backup
cd /opt/$PROJECT_NAME
docker-compose exec -T postgres pg_dump -U kroolo kroolo_bot > "$BACKUP_DIR/db-backup-$DATE.sql"
docker-compose exec -T redis redis-cli BGSAVE

# Compress backup
gzip "$BACKUP_DIR/db-backup-$DATE.sql"

# Clean old backups (keep last 7 days)
find "$BACKUP_DIR" -name "db-backup-*.sql.gz" -mtime +7 -delete

echo "Backup completed: db-backup-$DATE.sql.gz"
EOF
    
    sudo cp "/tmp/backup-kroolo.sh" "/usr/local/bin/backup-kroolo.sh"
    sudo chmod +x "/usr/local/bin/backup-kroolo.sh"
    rm "/tmp/backup-kroolo.sh"
    
    # Add to crontab (daily at 2 AM)
    (crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup-kroolo.sh") | crontab -
    
    log_success "Automated backups configured"
}

show_status() {
    log_info "Deployment Status:"
    echo "=================="
    
    # Show running containers
    echo "Running Containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo
    
    # Show service status
    echo "Systemd Service Status:"
    sudo systemctl status kroolo-bot.service --no-pager -l
    echo
    
    # Show logs
    echo "Recent Logs:"
    docker-compose logs --tail=20
}

main() {
    log_info "Starting production deployment of Kroolo AI Bot..."
    
    # Check if we're in the right directory
    if [ ! -f "docker-compose.yml" ]; then
        log_error "docker-compose.yml not found. Please run this script from the project root."
        exit 1
    fi
    
    # Run deployment steps
    check_prerequisites
    create_directories
    backup_existing
    setup_environment
    setup_ssl
    build_and_deploy
    setup_monitoring
    setup_firewall
    setup_backup_cron
    health_check
    
    log_success "Production deployment completed successfully!"
    
    show_status
    
    log_info "Next steps:"
    echo "1. Configure your domain and SSL certificates"
    echo "2. Set up monitoring alerts in Grafana"
    echo "3. Configure backup storage location"
    echo "4. Test all bot functionality"
    echo "5. Set up CI/CD pipeline for future updates"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --status       Show deployment status"
        echo "  --logs         Show recent logs"
        echo "  --restart      Restart services"
        echo "  --update       Update to latest version"
        ;;
    --status)
        show_status
        ;;
    --logs)
        docker-compose logs --tail=100 -f
        ;;
    --restart)
        log_info "Restarting services..."
        docker-compose restart
        sudo systemctl restart kroolo-bot.service
        log_success "Services restarted"
        ;;
    --update)
        log_info "Updating to latest version..."
        git pull origin main
        docker-compose down
        docker-compose build --no-cache
        docker-compose up -d
        log_success "Update completed"
        ;;
    *)
        main
        ;;
esac
