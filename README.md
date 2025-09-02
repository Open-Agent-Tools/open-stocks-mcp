# Open Stocks MCP

An MCP (Model Context Protocol) server providing access to stock market data and trading capabilities through Robin Stocks API.

## Features

**🚀 Current Status: v0.6.1 - Enhanced Options Tools**
- ✅ **80 MCP tools** across 9 categories (4 deprecated)
- ✅ **Complete trading functionality** - stocks, options, order management  
- ✅ **Live trading validated** - Stock and options trading tested with real orders
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

### Watchlists & Profiles (8 tools) ✅ Watchlist Management Tested
- **Watchlist management** - All 5 tools working (add/remove symbols tested with AMC)
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

### Trading Capabilities (15 tools)
**Stock Orders (✅ Live Tested):**
- ✅ Market orders - Buy/sell tested with XOM and AMC
- ✅ Limit orders - Buy/sell tested with XOM ($106) and AMC ($3)
- ✅ Stop-loss orders - Sell tested with AMC (25 shares at $2.50)
- Individual and bulk order cancellation
- ❌ **Deprecated**: Trailing stop orders, fractional shares (uncommon use cases)

**Options Orders (✅ Live Tested):**
- ✅ Options limit orders (buy/sell) - **API bugs fixed**
- ✅ Options discovery and contract search
- ✅ Credit and debit spread strategies - **API bugs fixed, ready for testing**
- Live validation: F $9 put sell order placed successfully

**Order Management:**
- Cancel individual or all orders (stock and options)
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
pytest -m "journey_account"      # Fast account tests (~1.8s)
pytest -m "journey_market_data"  # Market data tests (~3.8s) 
pytest -m "not slow and not exception_test"  # Recommended for development

# See CLAUDE.md for complete journey testing guide
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

**Completed in v0.6.1:**
- ✅ **Enhanced Options Tools** - New `open_option_positions_with_details()` enriches positions with call/put type
- ✅ **Stock trading API fixes** - Market, limit, and stop-loss buy/sell functions now working correctly
- ✅ **Live stock trading validation** - XOM and AMC orders successfully placed (market, limit, stop-loss)
- ✅ **Tool deprecation** - Removed 4 uncommon trading functions (buy_stock_stop_loss, trailing stops, fractional shares)
- ✅ **Options trading API fixes** - `buy_option_limit`, `sell_option_limit`, and spread strategies now working
- ✅ **Live options validation** - F $9 put successfully traded
- ✅ **Options discovery** - `find_options` function working correctly
- ✅ **Options spreads fixed** - Credit and debit spread functions corrected (API signature, data structure, symbol extraction)
- ✅ **Watchlist management complete** - All 5 watchlist tools working with live testing
- ✅ **Watchlist API fixes** - Fixed response format changes and parameter binding issues
- ✅ **All trading functions ready** - Phase 7 complete, ready for Phase 8

**Phase 8 (v0.6.1) - Final Phase (Ready to Begin):**
- Quality & reliability improvements
- Enhanced monitoring and observability  
- Performance optimization
- All trading functions validated and ready for production

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
- **Live trading capabilities** - Real orders are placed with actual money
- Never commit credentials to version control
- Use proper file permissions for `.env` files
- **Trading validation complete** - Both stock and options trading tested
- Always verify trades before execution in production
- **Options trading note**: Selling options (like puts) can result in assignment and stock ownership

For security concerns, please see our [security policy](SECURITY.md).

---

**Disclaimer:** This software is for educational and development purposes. Trading stocks and options involves substantial risk. Always verify trades and understand the risks before executing any financial transactions.