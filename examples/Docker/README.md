# Docker Example for Open Stocks MCP

This directory contains a complete example of how to run the Open Stocks MCP server using Docker and Docker Compose.

## Architecture

This setup uses a production-ready approach:
1. **Dockerfile**: Creates a secure base image with the `open-stocks-mcp` library installed and verified
2. **docker-compose.yml**: Orchestrates the server deployment with HTTP transport and proper configuration
3. **Enhanced Authentication**: Automatic device verification and MFA support for seamless Robinhood integration
4. **HTTP Transport**: Uses HTTP transport (port 3000) for better reliability and session management

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (version 20.10 or later)
- [Docker Compose](https://docs.docker.com/compose/install/) (version 2.0 or later)
- Valid Robinhood account credentials

## Quick Start

### 1. Choose Your Setup

**Production (Stable):**
Uses the published PyPI package (v0.3.0 - STDIO transport only):
```bash
docker-compose up
```

**Development (Latest):**
Builds from source with HTTP transport support (v0.4.0+):
```bash
docker-compose -f docker-compose.dev.yml up
```

### 2. Build the Image

**Production:**
```bash
docker-compose build
```

**Development:**
```bash
docker-compose -f docker-compose.dev.yml build
```

### 3. Create Environment File

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

### 4. Device Verification Setup

**IMPORTANT**: The first time you start the container, Robinhood may require device verification:

1. **Have your mobile app ready**: Keep the Robinhood mobile app accessible on your phone
2. **Watch the logs**: Monitor container logs for verification prompts
3. **Approve the device**: When prompted, approve the new device in your mobile app
4. **Wait for completion**: The server will automatically handle the verification workflow

```bash
# Monitor logs during first startup
docker-compose logs -f
```

Look for messages like:
```
INFO - Device verification prompt: Check robinhood app for device approvals method...
INFO - Login successful with device verification
INFO - Successfully authenticated user: your_username
INFO - ✅ Successfully logged into Robinhood for user: your_username
INFO - Starting HTTP MCP server on 0.0.0.0:3000
INFO - Available endpoints:
INFO -   - MCP JSON-RPC: http://0.0.0.0:3000/mcp
INFO -   - SSE Events: http://0.0.0.0:3000/sse
INFO -   - Health Check: http://0.0.0.0:3000/health
```

**Success Indicators:**
- ✅ Container status shows `healthy`
- ✅ Logs show "Login successful with device verification"
- ✅ Logs show "Starting HTTP MCP server on 0.0.0.0:3000"
- ✅ Session file created at `/home/mcp/.tokens/robinhood.pickle`
- ✅ Health check responds: `curl http://localhost:3000/health`

### 5. Start the Server

Run the server using Docker Compose:

**Production (Stable):**
```bash
# Foreground (see logs)
docker-compose up

# Background (detached mode)
docker-compose up -d
```

**Development (Latest with HTTP transport):**
```bash
# Foreground (see logs)
docker-compose -f docker-compose.dev.yml up

# Background (detached mode)
docker-compose -f docker-compose.dev.yml up -d
```

### 6. Verify Server Health

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

The MCP server runs on port `3000` using **HTTP transport with Server-Sent Events (SSE)**. You can connect with any MCP-compatible client:

```bash
# Test health endpoint
curl http://localhost:3000/health

# Test server status
curl http://localhost:3000/status

# Test available tools
curl http://localhost:3000/tools

# MCP JSON-RPC endpoint
curl -X POST http://localhost:3000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# SSE endpoint for real-time events
curl -N -H "Accept: text/event-stream" http://localhost:3000/sse
```

### Available Tools

The server provides **61 MCP tools** across **10 categories**:

- **Account Management**: `account_info`, `portfolio`, `account_details`, `positions`
- **Market Data**: `stock_price`, `stock_info`, `search_stocks_tool`, `market_hours`, `price_history`
- **Options Trading**: `options_chains`, `find_options`, `option_market_data`, `option_historicals`
- **Watchlist Management**: `all_watchlists`, `watchlist_by_name`, `add_to_watchlist`, `remove_from_watchlist`
- **Advanced Analytics**: `build_holdings`, `build_user_profile`, `day_trades`
- **Market Research**: `top_movers_sp500`, `stock_ratings`, `stock_earnings`, `stock_news`
- **Account Features**: `notifications`, `margin_calls`, `subscription_fees`, `referrals`
- **User Profiles**: `account_profile`, `basic_profile`, `investment_profile`, `security_profile`
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
# Stop current container
docker-compose down

# Pull latest version from PyPI and rebuild
docker-compose build --no-cache

# Start with latest version
docker-compose up -d

# Verify update
docker-compose logs | grep "open-stocks-mcp"
```

**Note**: Device verification may be required again after major updates if the session cache is cleared.

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

**Authentication Issues:**

*Device Verification Required:*
```bash
# Check logs for device verification prompts
docker-compose logs | grep -i "verification\|device"

# Look for these messages:
# "Device verification prompt: Check robinhood app..."
# "Waiting for device approval..."

# Solution:
# 1. Open Robinhood mobile app
# 2. Look for device approval notifications
# 3. Approve the new device
# 4. Wait for "Login successful with device verification"
```

*Authentication Failed:*
```bash
# Verify credentials are correct
cat .env

# Check for common .env formatting issues:
# ✓ ROBINHOOD_USERNAME=your_email@example.com
# ✓ ROBINHOOD_PASSWORD=your_password
# ✗ ROBINHOOD_USERNAME="your_email@example.com" (avoid quotes)

# Restart after fixing credentials
docker-compose restart
```

*MFA/2FA Issues:*
```bash
# The server now supports MFA via mobile app notifications
# If you see MFA prompts, check your mobile app for:
# - Push notifications
# - SMS verification codes (if applicable)
# - Email verification codes (if applicable)
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