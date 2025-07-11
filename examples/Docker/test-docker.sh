#!/bin/bash
# Test script for Open Stocks MCP Docker setup
# This script validates the Docker configuration and basic functionality

set -e  # Exit on any error

echo "🧪 Testing Open Stocks MCP Docker Setup"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
echo
log_info "Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed or not in PATH"
    exit 1
fi
log_info "Docker: $(docker --version)"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose is not installed or not in PATH"
    exit 1
fi
log_info "Docker Compose: $(docker-compose --version)"

# Check if .env file exists
if [ ! -f ".env" ]; then
    log_warn ".env file not found. Creating from example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        log_warn "Please edit .env file with your Robinhood credentials before running the server"
    else
        log_error ".env.example not found"
        exit 1
    fi
fi

# Validate Docker configuration files
echo
log_info "Validating configuration files..."

# Check Dockerfile
if [ ! -f "Dockerfile" ]; then
    log_error "Dockerfile not found"
    exit 1
fi
log_info "Dockerfile found"

# Check docker-compose.yml
if [ ! -f "docker-compose.yml" ]; then
    log_error "docker-compose.yml not found"
    exit 1
fi

# Validate docker-compose.yml syntax
if ! docker-compose config &> /dev/null; then
    log_error "docker-compose.yml has syntax errors"
    docker-compose config
    exit 1
fi
log_info "docker-compose.yml syntax is valid"

# Build the Docker image
echo
log_info "Building Docker image..."
if docker build -t open-stocks-mcp-base:latest . ; then
    log_info "Docker image built successfully"
else
    log_error "Failed to build Docker image"
    exit 1
fi

# Test the image
echo
log_info "Testing Docker image..."

# Test that the package is installed
if docker run --rm open-stocks-mcp-base:latest python -c "import open_stocks_mcp; print('Package import successful')"; then
    log_info "Package import test passed"
else
    log_error "Package import test failed"
    exit 1
fi

# Test that the CLI commands are available
if docker run --rm open-stocks-mcp-base:latest open-stocks-mcp-server --help > /dev/null; then
    log_info "CLI command test passed"
else
    log_error "CLI command test failed"
    exit 1
fi

# Test health check
if docker run --rm open-stocks-mcp-base:latest python -c "import open_stocks_mcp; print('OK')"; then
    log_info "Health check test passed"
else
    log_error "Health check test failed"
    exit 1
fi

# Security tests
echo
log_info "Running security tests..."

# Check that container doesn't run as root
if docker run --rm open-stocks-mcp-base:latest whoami | grep -q "mcp"; then
    log_info "Non-root user test passed"
else
    log_error "Container is running as root (security risk)"
    exit 1
fi

# Summary
echo
echo "======================================"
log_info "All tests passed! ✅"
echo
echo "Next steps:"
echo "1. Edit .env file with your Robinhood credentials"
echo "2. Run: docker-compose up"
echo "3. Test endpoints:"
echo "   - Health check: curl http://localhost:3000/health"
echo "   - Server status: curl http://localhost:3000/status"
echo "   - Available tools: curl http://localhost:3000/tools"
echo "   - SSE events: curl -N -H 'Accept: text/event-stream' http://localhost:3000/sse"
echo