#!/bin/bash

# Bluesky Crypto Agent Deployment Script
# This script handles the complete deployment of the Bluesky Crypto Agent

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
CONTAINER_NAME="bluesky-crypto-agent"

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

check_dependencies() {
    log_info "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    log_success "All dependencies are installed"
}

setup_environment() {
    log_info "Setting up environment..."
    
    if [ ! -f "$ENV_FILE" ]; then
        log_warning ".env file not found. Creating from template..."
        cp "$PROJECT_DIR/.env.example" "$ENV_FILE"
        log_warning "Please edit .env file with your actual API keys and configuration"
        log_warning "Required variables: PERPLEXITY_API_KEY, BLUESKY_USERNAME, BLUESKY_PASSWORD"
        return 1
    fi
    
    # Validate required environment variables
    source "$ENV_FILE"
    
    if [ -z "$PERPLEXITY_API_KEY" ] || [ "$PERPLEXITY_API_KEY" = "your_perplexity_api_key_here" ]; then
        log_error "PERPLEXITY_API_KEY is not set in .env file"
        return 1
    fi
    
    if [ -z "$BLUESKY_USERNAME" ] || [ "$BLUESKY_USERNAME" = "your_bluesky_username_here" ]; then
        log_error "BLUESKY_USERNAME is not set in .env file"
        return 1
    fi
    
    if [ -z "$BLUESKY_PASSWORD" ] || [ "$BLUESKY_PASSWORD" = "your_bluesky_password_here" ]; then
        log_error "BLUESKY_PASSWORD is not set in .env file"
        return 1
    fi
    
    log_success "Environment configuration is valid"
    return 0
}

create_directories() {
    log_info "Creating necessary directories..."
    
    mkdir -p "$PROJECT_DIR/logs"
    mkdir -p "$PROJECT_DIR/config"
    
    log_success "Directories created"
}

build_image() {
    log_info "Building Docker image..."
    
    cd "$PROJECT_DIR"
    docker-compose build --no-cache
    
    log_success "Docker image built successfully"
}

deploy_container() {
    log_info "Deploying container..."
    
    cd "$PROJECT_DIR"
    
    # Stop existing container if running
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        log_info "Stopping existing container..."
        docker-compose down
    fi
    
    # Start the container
    docker-compose up -d
    
    log_success "Container deployed successfully"
}

verify_deployment() {
    log_info "Verifying deployment..."
    
    # Wait for container to start
    sleep 10
    
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        log_success "Container is running"
        
        # Check container health
        health_status=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "unknown")
        log_info "Container health status: $health_status"
        
        # Show container logs
        log_info "Recent container logs:"
        docker-compose logs --tail=20 "$CONTAINER_NAME"
        
    else
        log_error "Container is not running"
        log_info "Container logs:"
        docker-compose logs "$CONTAINER_NAME"
        return 1
    fi
}

show_status() {
    log_info "Deployment Status:"
    echo "===================="
    docker-compose ps
    echo ""
    log_info "To view logs: docker-compose logs -f $CONTAINER_NAME"
    log_info "To stop: docker-compose down"
    log_info "To restart: docker-compose restart"
}

# Main deployment flow
main() {
    log_info "Starting Bluesky Crypto Agent deployment..."
    
    check_dependencies
    
    if ! setup_environment; then
        log_error "Environment setup failed. Please configure .env file and run again."
        exit 1
    fi
    
    create_directories
    build_image
    deploy_container
    
    if verify_deployment; then
        show_status
        log_success "Deployment completed successfully!"
    else
        log_error "Deployment verification failed"
        exit 1
    fi
}

# Handle command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "stop")
        log_info "Stopping Bluesky Crypto Agent..."
        cd "$PROJECT_DIR"
        docker-compose down
        log_success "Agent stopped"
        ;;
    "restart")
        log_info "Restarting Bluesky Crypto Agent..."
        cd "$PROJECT_DIR"
        docker-compose restart
        log_success "Agent restarted"
        ;;
    "logs")
        cd "$PROJECT_DIR"
        docker-compose logs -f "$CONTAINER_NAME"
        ;;
    "status")
        cd "$PROJECT_DIR"
        show_status
        ;;
    "help")
        echo "Usage: $0 [command]"
        echo "Commands:"
        echo "  deploy  - Deploy the agent (default)"
        echo "  stop    - Stop the agent"
        echo "  restart - Restart the agent"
        echo "  logs    - Show agent logs"
        echo "  status  - Show deployment status"
        echo "  help    - Show this help message"
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac