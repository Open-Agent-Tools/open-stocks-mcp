# Makefile for Open Stocks MCP Docker Example
# 
# This Makefile provides convenient commands for managing the Docker deployment

.PHONY: help build up down logs shell test clean setup

# Default target
help: ## Show this help message
	@echo "Open Stocks MCP Docker Commands:"
	@echo "================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Setup environment file from example
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file from example"; \
		echo "Please edit .env with your Robinhood credentials"; \
	else \
		echo ".env file already exists"; \
	fi

build: ## Build the Docker image
	docker build -t open-stocks-mcp-base:latest .

up: ## Start the services in foreground
	docker-compose up

up-d: ## Start the services in background
	docker-compose up -d

down: ## Stop the services
	docker-compose down

logs: ## View logs from the running container
	docker-compose logs -f

status: ## Show status of running containers
	docker-compose ps

health: ## Check container health status
	@if docker inspect open-stocks-mcp-server --format='{{.State.Health.Status}}' 2>/dev/null; then \
		echo "Container health status checked"; \
	else \
		echo "Container not running or no health check configured"; \
	fi

shell: ## Open a shell in the running container
	docker-compose exec open-stocks-mcp bash

test: ## Run the test script to validate setup
	@if [ -f test-docker.sh ]; then \
		./test-docker.sh; \
	else \
		echo "test-docker.sh not found"; \
		exit 1; \
	fi

clean: ## Clean up containers, images, and volumes
	docker-compose down -v
	docker rmi open-stocks-mcp-base:latest 2>/dev/null || true
	docker system prune -f

rebuild: ## Clean build and restart
	$(MAKE) down
	$(MAKE) clean
	$(MAKE) build
	$(MAKE) up-d

# Development targets
dev-build: ## Build image with no cache (for development)
	docker build --no-cache -t open-stocks-mcp-base:latest .

dev-logs: ## View logs with timestamps
	docker-compose logs -f --timestamps

dev-inspect: ## Inspect the running container
	docker inspect open-stocks-mcp-server

# Debugging targets
debug: ## Start container with debug logging
	@echo "LOG_LEVEL=DEBUG" >> .env
	$(MAKE) down
	$(MAKE) up

debug-shell: ## Start a debug shell with the image
	docker run --rm -it --env-file .env open-stocks-mcp-base:latest bash

# Quick commands
start: up-d ## Alias for up-d
stop: down ## Alias for down
restart: down up-d ## Restart the services