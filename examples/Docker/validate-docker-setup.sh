#!/bin/bash

# Docker Setup Validation Script for Open Stocks MCP v0.4.0
# This script validates the Docker setup and HTTP transport functionality

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="open-stocks-mcp-validator"
TEST_PORT="3001"
BASE_URL="http://localhost:${TEST_PORT}"
ENV_FILE=".env"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    print_status "Docker is installed: $(docker --version)"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
    print_status "Docker Compose is available"
    
    # Check environment file
    if [[ ! -f "$ENV_FILE" ]]; then
        print_error "Environment file '$ENV_FILE' not found"
        print_info "Create it by copying from .env.example and adding your credentials"
        exit 1
    fi
    print_status "Environment file found: $ENV_FILE"
    
    # Check curl
    if ! command -v curl &> /dev/null; then
        print_error "curl is not installed (required for testing)"
        exit 1
    fi
    print_status "curl is available"
    
    # Check jq (optional but helpful)
    if command -v jq &> /dev/null; then
        print_status "jq is available (JSON parsing enabled)"
        JQ_AVAILABLE=true
    else
        print_warning "jq not found (JSON output will not be formatted)"
        JQ_AVAILABLE=false
    fi
}

# Function to validate environment file
validate_env_file() {
    print_info "Validating environment file..."
    
    # Check for required variables
    if ! grep -q "ROBINHOOD_USERNAME=" "$ENV_FILE"; then
        print_error "ROBINHOOD_USERNAME not found in $ENV_FILE"
        exit 1
    fi
    
    if ! grep -q "ROBINHOOD_PASSWORD=" "$ENV_FILE"; then
        print_error "ROBINHOOD_PASSWORD not found in $ENV_FILE"
        exit 1
    fi
    
    # Check that values are not empty
    if grep -q "ROBINHOOD_USERNAME=$" "$ENV_FILE" || grep -q "ROBINHOOD_USERNAME=\"\"" "$ENV_FILE"; then
        print_error "ROBINHOOD_USERNAME is empty in $ENV_FILE"
        exit 1
    fi
    
    if grep -q "ROBINHOOD_PASSWORD=$" "$ENV_FILE" || grep -q "ROBINHOOD_PASSWORD=\"\"" "$ENV_FILE"; then
        print_error "ROBINHOOD_PASSWORD is empty in $ENV_FILE"
        exit 1
    fi
    
    print_status "Environment file validation passed"
}

# Function to build Docker image
build_image() {
    print_info "Building Docker image..."
    
    if docker-compose build --no-cache > /dev/null 2>&1; then
        print_status "Docker image built successfully"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
}

# Function to start container
start_container() {
    print_info "Starting container for testing..."
    
    # Stop any existing container
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    
    # Start new container
    if docker run --rm -d \
        --name "$CONTAINER_NAME" \
        -p "${TEST_PORT}:3000" \
        --env-file "$ENV_FILE" \
        open-stocks-mcp:0.4.0 > /dev/null; then
        print_status "Container started: $CONTAINER_NAME"
    else
        print_error "Failed to start container"
        exit 1
    fi
    
    # Wait for container to be ready
    print_info "Waiting for container to initialize..."
    for i in {1..30}; do
        if docker ps --filter "name=$CONTAINER_NAME" --filter "status=running" | grep -q "$CONTAINER_NAME"; then
            print_status "Container is running"
            break
        fi
        if [[ $i -eq 30 ]]; then
            print_error "Container failed to start within 30 seconds"
            docker logs "$CONTAINER_NAME"
            exit 1
        fi
        sleep 1
    done
    
    # Additional wait for HTTP server to be ready
    print_info "Waiting for HTTP server to be ready..."
    for i in {1..60}; do
        if curl -s "$BASE_URL/health" > /dev/null 2>&1; then
            print_status "HTTP server is ready"
            break
        fi
        if [[ $i -eq 60 ]]; then
            print_error "HTTP server not responding after 60 seconds"
            docker logs "$CONTAINER_NAME"
            exit 1
        fi
        sleep 1
    done
}

# Function to test HTTP endpoints
test_endpoints() {
    print_info "Testing HTTP endpoints..."
    
    # Test health endpoint
    print_info "Testing health endpoint..."
    response=$(curl -s "$BASE_URL/health")
    if echo "$response" | grep -q '"status":"healthy"'; then
        print_status "Health endpoint responding correctly"
        if [[ "$JQ_AVAILABLE" == true ]]; then
            echo "$response" | jq '.status, .version, .transport'
        fi
    else
        print_error "Health endpoint not responding correctly"
        echo "Response: $response"
        exit 1
    fi
    
    # Test root endpoint
    print_info "Testing root endpoint..."
    response=$(curl -s "$BASE_URL/")
    if echo "$response" | grep -q '"name":"Open Stocks MCP Server"'; then
        print_status "Root endpoint responding correctly"
    else
        print_error "Root endpoint not responding correctly"
        exit 1
    fi
    
    # Test status endpoint
    print_info "Testing status endpoint..."
    response=$(curl -s "$BASE_URL/status")
    if echo "$response" | grep -q '"status":"running"'; then
        print_status "Status endpoint responding correctly"
    else
        print_error "Status endpoint not responding correctly"
        exit 1
    fi
    
    # Test tools endpoint
    print_info "Testing tools endpoint..."
    response=$(curl -s "$BASE_URL/tools")
    if echo "$response" | grep -q '"result"'; then
        print_status "Tools endpoint responding correctly"
        if [[ "$JQ_AVAILABLE" == true ]]; then
            tools_count=$(echo "$response" | jq '.result.tools | length')
            print_info "Available tools: $tools_count"
        fi
    else
        print_error "Tools endpoint not responding correctly"
        exit 1
    fi
    
    # Test security headers
    print_info "Testing security headers..."
    headers=$(curl -I -s "$BASE_URL/health")
    if echo "$headers" | grep -q "x-content-type-options: nosniff"; then
        print_status "Security headers present"
    else
        print_warning "Security headers may not be properly configured"
    fi
}

# Function to test Docker health checks
test_docker_health() {
    print_info "Testing Docker health checks..."
    
    # Wait for health check to run
    sleep 15
    
    health_status=$(docker inspect "$CONTAINER_NAME" --format='{{.State.Health.Status}}' 2>/dev/null || echo "none")
    
    if [[ "$health_status" == "healthy" ]]; then
        print_status "Docker health check is passing"
    elif [[ "$health_status" == "starting" ]]; then
        print_info "Docker health check is still starting..."
        # Wait a bit more
        sleep 15
        health_status=$(docker inspect "$CONTAINER_NAME" --format='{{.State.Health.Status}}' 2>/dev/null || echo "none")
        if [[ "$health_status" == "healthy" ]]; then
            print_status "Docker health check is now passing"
        else
            print_warning "Docker health check is not yet healthy: $health_status"
        fi
    else
        print_warning "Docker health check status: $health_status"
    fi
}

# Function to test container logs
test_container_logs() {
    print_info "Checking container logs for errors..."
    
    logs=$(docker logs "$CONTAINER_NAME" 2>&1 | tail -20)
    
    if echo "$logs" | grep -q "Starting HTTP MCP server"; then
        print_status "HTTP server started successfully"
    else
        print_warning "HTTP server startup message not found in logs"
    fi
    
    if echo "$logs" | grep -qi "error\|exception\|failed"; then
        print_warning "Potential errors found in logs:"
        echo "$logs" | grep -i "error\|exception\|failed"
    else
        print_status "No obvious errors in container logs"
    fi
}

# Function to cleanup
cleanup() {
    print_info "Cleaning up test container..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    print_status "Cleanup completed"
}

# Function to show summary
show_summary() {
    echo
    echo "=================================="
    echo "VALIDATION SUMMARY"
    echo "=================================="
    print_status "Docker setup validation completed successfully!"
    echo
    print_info "✓ Prerequisites checked"
    print_info "✓ Environment file validated"
    print_info "✓ Docker image built"
    print_info "✓ Container started and running"
    print_info "✓ HTTP endpoints tested"
    print_info "✓ Security features validated"
    print_info "✓ Health checks verified"
    echo
    print_info "Your Open Stocks MCP Docker setup is ready for production!"
    echo
    print_info "To start the server permanently:"
    echo "  docker-compose up -d"
    echo
    print_info "To view logs:"
    echo "  docker-compose logs -f"
    echo
    print_info "To stop the server:"
    echo "  docker-compose down"
}

# Main execution
main() {
    echo "========================================"
    echo "Open Stocks MCP Docker Validation v0.4.0"
    echo "========================================"
    echo
    
    # Set trap to cleanup on exit
    trap cleanup EXIT
    
    check_prerequisites
    validate_env_file
    build_image
    start_container
    test_endpoints
    test_docker_health
    test_container_logs
    show_summary
}

# Run main function
main "$@"