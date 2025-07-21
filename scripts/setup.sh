#!/bin/bash

# Bluesky Crypto Agent Setup Script
# This script handles initial setup and configuration

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

check_system() {
    log_info "Checking system requirements..."
    
    # Check OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log_info "Detected Linux system"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        log_info "Detected macOS system"
    else
        log_warning "Unsupported OS: $OSTYPE"
    fi
    
    # Check Docker
    if command -v docker &> /dev/null; then
        docker_version=$(docker --version)
        log_success "Docker found: $docker_version"
    else
        log_error "Docker not found. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check Docker Compose
    if command -v docker-compose &> /dev/null; then
        compose_version=$(docker-compose --version)
        log_success "Docker Compose found: $compose_version"
    elif docker compose version &> /dev/null; then
        compose_version=$(docker compose version)
        log_success "Docker Compose (plugin) found: $compose_version"
    else
        log_error "Docker Compose not found. Please install Docker Compose."
        echo "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
}

setup_directories() {
    log_info "Setting up project directories..."
    
    cd "$PROJECT_DIR"
    
    # Create necessary directories
    mkdir -p logs
    mkdir -p config
    mkdir -p data
    
    # Set permissions
    chmod 755 logs config data
    
    log_success "Directories created and configured"
}

setup_environment() {
    log_info "Setting up environment configuration..."
    
    cd "$PROJECT_DIR"
    
    if [ ! -f ".env" ]; then
        log_info "Creating .env file from template..."
        cp .env.example .env
        log_success ".env file created"
        
        echo ""
        log_warning "IMPORTANT: Please edit the .env file with your actual configuration:"
        echo "  1. Set your Perplexity API key (PERPLEXITY_API_KEY)"
        echo "  2. Set your Bluesky username (BLUESKY_USERNAME)"
        echo "  3. Set your Bluesky password (BLUESKY_PASSWORD)"
        echo "  4. Adjust other settings as needed"
        echo ""
        
        read -p "Press Enter to open .env file for editing (or Ctrl+C to exit)..."
        
        # Try to open with common editors
        if command -v nano &> /dev/null; then
            nano .env
        elif command -v vim &> /dev/null; then
            vim .env
        elif command -v vi &> /dev/null; then
            vi .env
        else
            log_warning "No text editor found. Please manually edit .env file"
        fi
    else
        log_info ".env file already exists"
    fi
}

validate_configuration() {
    log_info "Validating configuration..."
    
    cd "$PROJECT_DIR"
    
    if [ ! -f ".env" ]; then
        log_error ".env file not found"
        return 1
    fi
    
    # Source the environment file
    source .env
    
    # Check required variables
    errors=0
    
    if [ -z "$PERPLEXITY_API_KEY" ] || [ "$PERPLEXITY_API_KEY" = "your_perplexity_api_key_here" ]; then
        log_error "PERPLEXITY_API_KEY is not configured"
        errors=$((errors + 1))
    fi
    
    if [ -z "$BLUESKY_USERNAME" ] || [ "$BLUESKY_USERNAME" = "your_bluesky_username_here" ]; then
        log_error "BLUESKY_USERNAME is not configured"
        errors=$((errors + 1))
    fi
    
    if [ -z "$BLUESKY_PASSWORD" ] || [ "$BLUESKY_PASSWORD" = "your_bluesky_password_here" ]; then
        log_error "BLUESKY_PASSWORD is not configured"
        errors=$((errors + 1))
    fi
    
    if [ $errors -gt 0 ]; then
        log_error "Configuration validation failed. Please update .env file."
        return 1
    fi
    
    log_success "Configuration is valid"
    return 0
}

test_docker() {
    log_info "Testing Docker setup..."
    
    cd "$PROJECT_DIR"
    
    # Test Docker build
    log_info "Building Docker image (this may take a few minutes)..."
    if docker-compose build --quiet; then
        log_success "Docker image built successfully"
    else
        log_error "Docker build failed"
        return 1
    fi
    
    # Test container creation (without starting)
    log_info "Testing container creation..."
    if docker-compose create; then
        log_success "Container created successfully"
        # Clean up test container
        docker-compose down --remove-orphans
    else
        log_error "Container creation failed"
        return 1
    fi
}

show_next_steps() {
    log_success "Setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "==========="
    echo "1. Review your configuration in .env file"
    echo "2. Deploy the agent: ./scripts/deploy.sh"
    echo "3. Monitor logs: ./scripts/deploy.sh logs"
    echo "4. Check status: ./scripts/deploy.sh status"
    echo ""
    echo "For help: ./scripts/deploy.sh help"
}

# Main setup flow
main() {
    log_info "Starting Bluesky Crypto Agent setup..."
    echo ""
    
    check_system
    setup_directories
    setup_environment
    
    if validate_configuration; then
        if test_docker; then
            show_next_steps
        else
            log_error "Docker testing failed. Please check your Docker installation."
            exit 1
        fi
    else
        log_warning "Setup completed but configuration needs attention."
        echo "Please update .env file and run setup again to validate."
    fi
}

# Handle command line arguments
case "${1:-setup}" in
    "setup")
        main
        ;;
    "validate")
        validate_configuration
        ;;
    "test-docker")
        test_docker
        ;;
    "help")
        echo "Usage: $0 [command]"
        echo "Commands:"
        echo "  setup       - Run complete setup (default)"
        echo "  validate    - Validate configuration only"
        echo "  test-docker - Test Docker build only"
        echo "  help        - Show this help message"
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac