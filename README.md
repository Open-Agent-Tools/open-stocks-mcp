# Open Stocks MCP

An MCP (Model Context Protocol) server providing access to stock market data and trading capabilities through Robin Stocks API.

## Features

**🚀 Current Status: v0.5.0 - Complete BETA Trading Capabilities**
- ✅ **84 MCP tools** across 9 categories
- ✅ **Complete trading functionality** - stocks, options, order management  
- ✅ **Production-ready** - HTTP transport, Docker support, comprehensive testing
- ✅ **Phases 1-7 complete** - Foundation → Analytics → Trading

## Installation

```bash
pip install open-stocks-mcp
```

For development:
```bash
git clone https://github.com/Open-Agent-Tools/open-stocks-mcp.git
cd open-stocks-mcp
uv pip install -e .
```

## Quick Start

### 1. Set Up Credentials

Create a `.env` file:
```bash
ROBINHOOD_USERNAME=your_email@example.com
ROBINHOOD_PASSWORD=your_password
```

### 2. Start the Server

**HTTP Transport (Recommended)**
```bash
open-stocks-mcp-server --transport http --port 3001
```

**STDIO Transport**
```bash
open-stocks-mcp-server --transport stdio
```

### 3. Test the Server

```bash
# Health check (HTTP transport)
curl http://localhost:3001/health

# Interactive testing
uv run mcp dev src/open_stocks_mcp/server/app.py
```

## Docker Deployment

**Production Docker Setup:**
```bash
cd examples/open-stocks-mcp-docker
docker-compose up -d
```

**Features:**
- Persistent session storage
- Automatic log rotation
- Health monitoring
- Security headers and CORS

## MCP Client Integration

### Claude Desktop
Add to your MCP settings (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "open-stocks": {
      "command": "open-stocks-mcp-server",
      "args": ["--transport", "stdio"]
    }
  }
}
```

### HTTP Transport Integration
```json
{
  "mcpServers": {
    "open-stocks": {
      "command": "python",
      "args": ["-m", "mcp_http_client", "http://localhost:3001/mcp"]
    }
  }
}
```

## Available Tools

### Account & Portfolio (15 tools)
- Account information and details
- Portfolio positions and holdings
- Day trading metrics and history
- Stock and options order history

### Market Data (12 tools)
- Real-time stock quotes and fundamentals
- Market movers and top performers
- Sector analysis and market trends
- Historical price data

### Options Trading (15 tools)
- Options chains and market data
- Position aggregation and analysis
- Historical options data
- Options instrument search

### Watchlists & Profiles (8 tools)
- Watchlist management
- User profile and settings
- Investment preferences
- Account features

### Market Research (10 tools)
- Earnings data and analysis
- Stock ratings and news
- Dividend information
- Corporate actions and splits

### Analytics & Monitoring (5 tools)
- Portfolio analytics
- Performance metrics
- Server health monitoring
- Interest and loan payments

### Notifications (12 tools)
- Account notifications
- Margin calls and interest
- Subscription management
- Referral tracking

### Advanced Instruments (4 tools)
- Multi-symbol instrument lookup
- Enhanced search capabilities
- Level II market data (Gold required)
- Direct instrument access

### Trading Capabilities (19 tools)
**Stock Orders:**
- Market, limit, stop-loss, trailing stop orders
- Fractional share purchases
- Buy/sell order placement

**Options Orders:**
- Options limit orders (buy/sell)
- Credit and debit spread strategies

**Order Management:**
- Cancel individual or all orders
- View open positions
- Order status tracking

## Authentication

The server handles Robinhood's authentication requirements:
- **Device Verification**: Automatic handling of new device approval
- **Multi-Factor Authentication**: Support for SMS and app-based MFA
- **Session Persistence**: Cached authentication to reduce re-verification

## Development

### Testing
```bash
pytest                           # All tests
pytest tests/unit/               # Unit tests (fast)
pytest -m "not slow and not exception_test"  # Recommended for development
```

### Code Quality
```bash
ruff check . --fix              # Lint and fix
ruff format .                   # Format code
mypy .                          # Type check
```

### Google ADK Evaluation
```bash
# Set environment variables
export GOOGLE_API_KEY="your-google-api-key"
export ROBINHOOD_USERNAME="email@example.com"
export ROBINHOOD_PASSWORD="password"

# Start Docker server
cd examples/open-stocks-mcp-docker && docker-compose up -d

# Run evaluation
MCP_HTTP_URL="http://localhost:3001/mcp" adk eval examples/google_adk_agent tests/evals/list_available_tools_test.json --config_file_path tests/evals/test_config.json
```

## Project Scope

**Phase 8 (v0.6.0) - Final Phase:**
- Quality & reliability improvements
- Enhanced monitoring and observability
- Performance optimization

**Out of Scope:**
- Crypto trading tools
- Banking/ACH transfers
- Account modifications
- Deposit/withdrawal functionality

## Contributing

See [CONTRIBUTING.md](contributing/README.md) for development guidelines.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Security

**Important Security Notes:**
- This is a read-only API with trading capabilities - use with caution
- Never commit credentials to version control
- Use proper file permissions for `.env` files
- Trading tools are provided for educational/development purposes
- Always verify trades before execution in production

For security concerns, please see our [security policy](SECURITY.md).

---

**Disclaimer:** This software is for educational and development purposes. Trading stocks and options involves substantial risk. Always verify trades and understand the risks before executing any financial transactions.