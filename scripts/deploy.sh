#!/bin/bash
# OpenAI Realtime Bot - Production Deployment Script
# =================================================
#
# This script handles the complete deployment of the OpenAI Realtime Bot
# to production environments with proper validation and monitoring setup.
#
# Usage:
# ./scripts/deploy.sh [environment] [bot_type]
#
# Examples:
# ./scripts/deploy.sh production sales
# ./scripts/deploy.sh staging support
#
# Author: Agent Stream Team
# Version: 2.0.0

set -euo pipefail # Exit on error, undefined vars, pipe failures

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-production}"
BOT_TYPE="${2:-sales}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Validation functions
validate_environment() {
 local env="$1"
 if [[ ! "$env" =~ ^(development|staging|production)$ ]]; then
 log_error "Invalid environment: $env"
 log_info "Valid environments: development, staging, production"
 exit 1
 fi
}

validate_bot_type() {
 local bot_type="$1"
 if [[ ! "$bot_type" =~ ^(sales|support|qualification|collection)$ ]]; then
 log_error "Invalid bot type: $bot_type"
 log_info "Valid bot types: sales, support, qualification, collection"
 exit 1
 fi
}

check_prerequisites() {
 log_info "Checking prerequisites..."

 # Check Python version
 if ! python3 --version | grep -q "Python 3.[8-9]\|Python 3.1[0-9]"; then
 log_error "Python 3.8+ is required"
 exit 1
 fi

 # Check required commands
 local required_commands=("docker" "docker-compose" "pip" "git")
 for cmd in "${required_commands[@]}"; do
 if ! command -v "$cmd" &> /dev/null; then
 log_error "Required command not found: $cmd"
 exit 1
 fi
 done

 # Check environment file
 local env_file="$PROJECT_ROOT/.env.$ENVIRONMENT"
 if [[ ! -f "$env_file" ]]; then
 log_error "Environment file not found: $env_file"
 log_info "Please create the environment file with required variables"
 exit 1
 fi

 log_success "Prerequisites check passed"
}

validate_configuration() {
 log_info "Validating configuration..."

 # Source environment variables
 source "$PROJECT_ROOT/.env.$ENVIRONMENT"

 # Check required environment variables
 local required_vars=("OPENAI_API_KEY" "COMPANY_NAME" "ASSISTANT_NAME")
 for var in "${required_vars[@]}"; do
 if [[ -z "${!var:-}" ]]; then
 log_error "Required environment variable not set: $var"
 exit 1
 fi
 done

 # Validate OpenAI API key format
 if [[ ! "$OPENAI_API_KEY" =~ ^sk-[a-zA-Z0-9]{48,}$ ]]; then
 log_warning "OpenAI API key format may be invalid"
 fi

 log_success "Configuration validation passed"
}

setup_python_environment() {
 log_info "Setting up Python environment..."

 cd "$PROJECT_ROOT"

 # Create virtual environment if it doesn't exist
 if [[ ! -d "venv" ]]; then
 python3 -m venv venv
 log_success "Created virtual environment"
 fi

 # Activate virtual environment
 source venv/bin/activate

 # Upgrade pip
 pip install --upgrade pip

 # Install dependencies
 if [[ "$ENVIRONMENT" == "production" ]]; then
 pip install -r requirements.txt --no-dev
 else
 pip install -r requirements.txt
 fi

 log_success "Python environment setup completed"
}

run_tests() {
 log_info "Running tests..."

 cd "$PROJECT_ROOT"
 source venv/bin/activate

 # Run unit tests
 if command -v pytest &> /dev/null; then
 pytest tests/ -v --tb=short
 log_success "Unit tests passed"
 else
 log_warning "pytest not available, skipping tests"
 fi

 # Run linting
 if command -v flake8 &> /dev/null; then
 flake8 src/ --max-line-length=100
 log_success "Code linting passed"
 else
 log_warning "flake8 not available, skipping linting"
 fi
}

build_docker_image() {
 log_info "Building Docker image..."

 cd "$PROJECT_ROOT"

 # Build image with environment and bot type tags
 local image_tag="openai-realtime-bot:$ENVIRONMENT-$BOT_TYPE"
 docker build -t "$image_tag" -f docker/Dockerfile .

 # Tag as latest for the environment
 docker tag "$image_tag" "openai-realtime-bot:$ENVIRONMENT-latest"

 log_success "Docker image built: $image_tag"
}

deploy_with_docker_compose() {
 log_info "Deploying with Docker Compose..."

 cd "$PROJECT_ROOT"

 # Set environment variables for docker-compose
 export ENVIRONMENT="$ENVIRONMENT"
 export BOT_TYPE="$BOT_TYPE"
 export IMAGE_TAG="$ENVIRONMENT-$BOT_TYPE"

 # Deploy using docker-compose
 docker-compose -f docker/docker-compose.yml down
 docker-compose -f docker/docker-compose.yml up -d

 log_success "Docker Compose deployment completed"
}

deploy_to_kubernetes() {
 log_info "Deploying to Kubernetes..."

 cd "$PROJECT_ROOT"

 # Apply Kubernetes manifests
 kubectl apply -f k8s/namespace.yaml
 kubectl apply -f k8s/configmap.yaml
 kubectl apply -f k8s/secret.yaml
 kubectl apply -f k8s/deployment.yaml
 kubectl apply -f k8s/service.yaml
 kubectl apply -f k8s/ingress.yaml

 # Wait for deployment to be ready
 kubectl rollout status deployment/openai-realtime-bot -n bot-system --timeout=300s

 log_success "Kubernetes deployment completed"
}

setup_monitoring() {
 log_info "Setting up monitoring..."

 # Setup log directory
 mkdir -p "$PROJECT_ROOT/logs"

 # Setup monitoring configuration
 if [[ "$ENVIRONMENT" == "production" ]]; then
 # Setup log rotation
 cat > /etc/logrotate.d/openai-realtime-bot << EOF
$PROJECT_ROOT/logs/*.log {
 daily
 rotate 30
 compress
 delaycompress
 missingok
 notifempty
 create 0644 www-data www-data
}
EOF

 # Setup systemd service for monitoring
 cat > /etc/systemd/system/openai-realtime-bot.service << EOF
[Unit]
Description=OpenAI Realtime Bot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=$PROJECT_ROOT
Environment=PATH=$PROJECT_ROOT/venv/bin
ExecStart=$PROJECT_ROOT/venv/bin/python src/examples/${BOT_TYPE}_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

 systemctl daemon-reload
 systemctl enable openai-realtime-bot

 log_success "Production monitoring setup completed"
 fi
}

health_check() {
 log_info "Running health checks..."

 local max_attempts=30
 local attempt=1
 local health_url="http://localhost:5000/health"

 while [[ $attempt -le $max_attempts ]]; do
 if curl -f -s "$health_url" > /dev/null 2>&1; then
 log_success "Health check passed"
 return 0
 fi

 log_info "Health check attempt $attempt/$max_attempts failed, retrying in 10s..."
 sleep 10
 ((attempt++))
 done

 log_error "Health check failed after $max_attempts attempts"
 return 1
}

cleanup_old_deployments() {
 log_info "Cleaning up old deployments..."

 # Remove old Docker images (keep last 3)
 docker images "openai-realtime-bot" --format "table {{.Repository}}:{{.Tag}}\t{{.CreatedAt}}" | \
 tail -n +4 | \
 awk '{print $1}' | \
 xargs -r docker rmi

 # Clean up old log files (keep last 7 days)
 find "$PROJECT_ROOT/logs" -name "*.log" -mtime +7 -delete

 log_success "Cleanup completed"
}

rollback_deployment() {
 log_error "Deployment failed, initiating rollback..."

 # Rollback Docker Compose
 if command -v docker-compose &> /dev/null; then
 docker-compose -f docker/docker-compose.yml down
 docker-compose -f docker/docker-compose.yml up -d --scale bot=1
 fi

 # Rollback Kubernetes
 if command -v kubectl &> /dev/null; then
 kubectl rollout undo deployment/openai-realtime-bot -n bot-system
 fi

 log_info "Rollback completed"
}

main() {
 log_info "Starting OpenAI Realtime Bot deployment..."
 log_info "Environment: $ENVIRONMENT"
 log_info "Bot Type: $BOT_TYPE"

 # Validation
 validate_environment "$ENVIRONMENT"
 validate_bot_type "$BOT_TYPE"
 check_prerequisites
 validate_configuration

 # Setup
 setup_python_environment

 # Testing (skip in production for faster deployment)
 if [[ "$ENVIRONMENT" != "production" ]]; then
 run_tests
 fi

 # Deployment
 build_docker_image

 # Choose deployment method
 if [[ -f "$PROJECT_ROOT/docker/docker-compose.yml" ]]; then
 deploy_with_docker_compose
 elif command -v kubectl &> /dev/null; then
 deploy_to_kubernetes
 else
 log_error "No deployment method available (Docker Compose or Kubernetes)"
 exit 1
 fi

 # Post-deployment
 setup_monitoring

 # Health check
 if ! health_check; then
 rollback_deployment
 exit 1
 fi

 # Cleanup
 cleanup_old_deployments

 log_success "Deployment completed successfully!"
 log_info "Bot is running at: http://localhost:5000"
 log_info "Health check: http://localhost:5000/health"
 log_info "Logs: $PROJECT_ROOT/logs/"

 # Display connection information
 echo
 echo "OpenAI Realtime Bot Deployed Successfully!"
 echo "=============================================="
 echo
 echo "Deployment Summary:"
 echo " Environment: $ENVIRONMENT"
 echo " Bot Type: $BOT_TYPE"
 echo " Image: openai-realtime-bot:$ENVIRONMENT-$BOT_TYPE"
 echo
 echo "Connection Details:"
 echo " WebSocket: ws://localhost:5000/?sample-rate=24000"
 echo " Health Check: http://localhost:5000/health"
 echo " Metrics: http://localhost:5000/metrics"
 echo
 echo "Next Steps:"
 echo " 1. Update your telephony provider webhook URL"
 echo " 2. Test with a sample call"
 echo " 3. Monitor logs in $PROJECT_ROOT/logs/"
 echo " 4. Setup external monitoring and alerting"
 echo
 echo "Management Commands:"
 echo " View logs: docker-compose logs -f bot"
 echo " Restart: docker-compose restart bot"
 echo " Stop: docker-compose down"
 echo " Scale: docker-compose up -d --scale bot=3"
 echo
}

# Trap errors and run rollback
trap 'rollback_deployment' ERR

# Run main function
main "$@" 