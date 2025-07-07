# Docker Example for Open Stocks MCP

This directory contains a complete example of how to run the Open Stocks MCP server using Docker and Docker Compose.

## Architecture

This setup uses a two-stage approach:
1. **Dockerfile**: Creates a secure base image with the `open-stocks-mcp` library (v0.1.5) installed and verified
2. **docker-compose.yml**: Orchestrates the server deployment with proper configuration and security settings

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (version 20.10 or later)
- [Docker Compose](https://docs.docker.com/compose/install/) (version 2.0 or later)
- Valid Robinhood account credentials

## Quick Start

### 1. Build the Base Image

First, build the base image that contains the verified library installation:

```bash
docker build . -t open-stocks-mcp-base:latest
```

Or let Docker Compose build it automatically:

```bash
docker-compose build
```

### 2. Create Environment File

Copy the example environment file and add your credentials:

```bash
cp .env.example .env
```

Edit the `.env` file with your Robinhood credentials:

```env
# .env
ROBINHOOD_USERNAME=your_robinhood_username
ROBINHOOD_PASSWORD=your_robinhood_password
```

⚠️ **Security Note**: Never commit the `.env` file to version control. It's already included in `.gitignore`.

### 3. Start the Server

Run the server using Docker Compose:

```bash
# Foreground (see logs)
docker-compose up

# Background (detached mode)
docker-compose up -d
```

### 4. Verify Server Health

Check that the server is running properly:

```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs -f

# Check health status
docker inspect open-stocks-mcp-server --format='{{.State.Health.Status}}'
```

## Usage

### Connecting to the Server

The MCP server runs on port `3001` using Server-Sent Events (SSE) transport. You can connect with any MCP-compatible client:

```bash
# Using mcp CLI tool
mcp --transport sse --url http://localhost:3001

# Using curl to test connection
curl -N -H "Accept: text/event-stream" http://localhost:3001/sse
```

### Available Tools

The server provides 17 MCP tools across 5 categories:

- **Account Management**: `account_info`, `portfolio`, `account_details`, `positions`, `portfolio_history`
- **Market Data**: `stock_price`, `stock_info`, `search_stocks_tool`, `market_hours`, `price_history`
- **Order History**: `stock_orders`, `options_orders`
- **System Management**: `session_status`, `rate_limit_status`, `metrics_summary`, `health_check`
- **Utility**: `list_tools`

## Management

### Stop the Server

```bash
# Graceful shutdown
docker-compose down

# Force stop (if needed)
docker-compose down --timeout 10
```

### Update to Latest Version

```bash
# Pull latest version and rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### View Logs

```bash
# Follow logs in real-time
docker-compose logs -f

# View last 100 lines
docker-compose logs --tail=100

# View logs for specific timeframe
docker-compose logs --since="1h"
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ROBINHOOD_USERNAME` | Yes | Your Robinhood account username |
| `ROBINHOOD_PASSWORD` | Yes | Your Robinhood account password |

### Resource Limits

The Docker Compose configuration includes resource limits:
- **Memory**: 512MB limit, 256MB reservation
- **CPU**: 0.5 cores limit, 0.25 cores reservation

Adjust these in `docker-compose.yml` based on your needs.

## Security Features

- **Non-root user**: Container runs as user ID 1001 for security
- **Health checks**: Automatic container health monitoring
- **Environment isolation**: Credentials passed via environment variables
- **Resource limits**: Prevents resource exhaustion
- **Log rotation**: Automatic log file management

## Troubleshooting

### Common Issues

**Container won't start:**
```bash
# Check logs for errors
docker-compose logs

# Verify environment file exists and has correct format
cat .env
```

**Connection refused:**
```bash
# Verify container is running and healthy
docker-compose ps
docker inspect open-stocks-mcp-server --format='{{.State.Health.Status}}'

# Check if port is accessible
curl -v http://localhost:3001
```

**Authentication errors:**
```bash
# Verify credentials in .env file
# Check Robinhood account status
# Ensure no 2FA is enabled (not currently supported)
```

### Debug Mode

Run with debug logging:

```bash
# Add debug environment variable
echo "LOG_LEVEL=DEBUG" >> .env
docker-compose restart
docker-compose logs -f
```

## Production Considerations

For production deployments, consider:

1. **Secrets Management**: Use Docker Secrets or external secret management
2. **Reverse Proxy**: Add NGINX or Traefik for SSL termination
3. **Monitoring**: Integrate with Prometheus/Grafana
4. **Backup**: Implement session data backup if persistence is needed
5. **Network Security**: Use Docker networks and firewall rules

## Development

To modify the container for development:

```bash
# Mount local code for development
docker run -v $(pwd)/../../:/app open-stocks-mcp-base:latest bash

# Or create a development docker-compose override
cp docker-compose.yml docker-compose.override.yml
# Edit override file for development settings
```