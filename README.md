# Open Stocks MCP

An MCP (Model Context Protocol) server providing access to stock market data and trading capabilities through multiple broker APIs.

## Features

**🚀 Current Status: v0.7.0-dev - Multi-Broker Support (Robinhood + Schwab)**
- ✅ **122 MCP tools** total - 87 Robinhood + 35 Schwab (4 deprecated)
- ✅ **Multi-broker architecture** - Support for Robinhood and Charles Schwab
- ✅ **Complete trading functionality** - stocks, options, order management
- ✅ **Live trading validated** - Robinhood stock and options trading tested with real orders
- ✅ **Production-ready** - HTTP transport, Docker support, comprehensive testing
- ✅ **Schwab integration complete** - OAuth authentication, 35 tools ready for testing
- 🔧 **Account details fixed** - Real financial data instead of N/A values

## Installation

```bash
pip install open-stocks-mcp
```

For development:
```bash
git clone https://github.com/Open-Agent-Tools/open-stocks-mcp.git
cd open-stocks-mcp
uv sync   # installs all deps including dev group
```

## Quick Start

### 1. Set Up Credentials

Create a `.env` file:

**For Robinhood:**
```bash
ROBINHOOD_USERNAME=your_email@example.com
ROBINHOOD_PASSWORD=your_password
```

**For Schwab (optional):**
```bash
SCHWAB_API_KEY=your_api_key
SCHWAB_APP_SECRET=your_app_secret
SCHWAB_CALLBACK_URL=https://127.0.0.1:8182/
SCHWAB_TOKEN_PATH=~/.tokens/schwab_token.json

# Enable both brokers
ENABLED_BROKERS=robinhood,schwab
```

**Note:** Schwab requires a developer account and API approval (several days). See `docs/SCHWAB_INTEGRATION_PLAN.md` for details.

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

# Prometheus metrics (no auth required)
curl http://localhost:3001/metrics

# Interactive testing
uv run mcp dev src/open_stocks_mcp/server/app.py
```

The `/metrics` endpoint exposes:
- `open_stocks_mcp_tool_calls_total` (counter by tool)
- `open_stocks_mcp_tool_calls_per_minute` (gauge by tool)
- `open_stocks_mcp_tool_latency_ms` (gauge by tool and quantile: `0.50`, `0.95`, `0.99`)

Distributed tracing setup (OpenTelemetry, Jaeger, Tempo):
- [docs/OPENTELEMETRY_TRACING.md](docs/OPENTELEMETRY_TRACING.md)

### Operational Circuit Breaker Defaults

Broker call protection is enabled by default and reports state in MCP `health_check`,
MCP `rate_limit_status`, HTTP `/health`, and HTTP `/status`.

- `OPEN_STOCKS_MCP_CIRCUIT_BREAKER_ENABLED` (default: `true`)
- `OPEN_STOCKS_MCP_CIRCUIT_BREAKER_FAILURE_THRESHOLD` (default: `5`)
- `OPEN_STOCKS_MCP_CIRCUIT_BREAKER_COOLDOWN_SECONDS` (default: `60`)

State meanings:
- `closed`: requests flow normally.
- `open`: broker calls fail fast until cooldown expires.
- `half_open`: one probe call is allowed; success resets to `closed`, failure returns to `open`.

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

**Kubernetes / Orchestrated Deployment:**
See [examples/kubernetes/README.md](examples/kubernetes/README.md) for Kustomize manifests covering HTTP transport, non-root security context, PVC-backed token/log persistence, and health probes.

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

Reference docs and runnable examples:
- [API docs and notebook guide](docs/api/README.md), including the generated
  [tool reference](docs/api/tools.md)

### 🏦 Multi-Broker Support

**Robinhood Tools (87 tools)**:
- All existing Robinhood functionality maintained
- No breaking changes to existing API

**Schwab Tools (35 tools)**:
- Account & Portfolio (11 tools) - account numbers, balances, positions
- Market Data (5 tools) - quotes, price history, instrument search
- Trading (11 tools) - market/limit buy/sell, order management, transactions
- Options (8 tools) - chains, expirations, positions, buy/sell

All Schwab tools use `schwab_` prefix (e.g., `schwab_get_portfolio`, `schwab_buy_stock_market`).

---

### Robinhood Tools by Category

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
- **App-Push Approval**: Automatic handling of app-based device approval (approve via Robinhood mobile app).
- **SMS/Email MFA Code**: Set `ROBINHOOD_MFA_CODE` before login attempts to complete code-based verification (time-sensitive, typically 5-10 minutes).
- **Session Persistence**: Cached and encrypted authentication to reduce re-verification.

## Development

### Testing
```bash
uv run pytest                           # All tests (works after uv sync)
uv run pytest -m "journey_account"      # Fast account tests (~1.8s)
uv run pytest -m "journey_market_data"  # Market data tests (~3.8s)
uv run pytest -m "not slow and not exception_test"  # Recommended for development
uv run pytest -m rate_limited           # Opt-in live API tests that may hit broker rate limits
RUN_RATE_LIMITED=1 uv run pytest        # Include rate-limited tests in a full run
uv run pytest -m performance tests/performance -v  # Mocked, CI-safe benchmarks
RUN_PERFORMANCE=1 uv run pytest         # Include performance tests in a full run

# See CLAUDE.md for complete journey testing guide
```

### Code Quality
```bash
ruff check . --fix              # Lint and fix
ruff format .                   # Format code
mypy .                          # Type check
```

### YAML Configuration
Open Stocks MCP can load configuration from `open-stocks-mcp.yaml` or `config.yaml` in the current working directory.
You can also set an explicit path with `OPEN_STOCKS_CONFIG=/path/to/config.yaml` or `OPEN_STOCKS_CONFIG_FILE=/path/to/config.yaml` (`OPEN_STOCKS_MCP_CONFIG` remains supported for backward compatibility).

Environment variables always win over YAML values, including:
- `MCP_SERVER_NAME`, `LOG_LEVEL`
- `RATE_LIMIT_CALLS_PER_MINUTE`, `RATE_LIMIT_CALLS_PER_HOUR`, `RATE_LIMIT_BURST_SIZE`
- `CACHE_TTL_MARKET_SECONDS`, `CACHE_TTL_ACCOUNT_SECONDS`, `CACHE_MAX_SIZE`
- `ENABLE_CACHE`
- `OPEN_STOCKS_MCP_BATCH_SIZE`, `OPEN_STOCKS_MCP_QUEUE_MAX_WAIT`

Feature flags support safe defaults plus per-environment overrides:

```yaml
environment: production
feature_flags:
  brokers.robinhood:
    default: true
  brokers.schwab:
    default: false
    environments:
      production: true
```

Unknown feature flags resolve to disabled (`false`).

See `config.yaml.example` for the supported schema.

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

**Completed in v0.7.0-dev:**
- ✅ **Multi-broker architecture** - Abstract broker layer supporting multiple brokers
- ✅ **Schwab integration** - 35 tools across account, market data, trading, and options
- ✅ **OAuth authentication** - Schwab OAuth 2.0 flow with automatic token refresh
- ✅ **Graceful degradation** - Server starts even if broker authentication fails
- ✅ **Backward compatibility** - All Robinhood tools unchanged, no breaking changes

**Completed in v0.6.4:**
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

**Next Priority (Schwab Testing):**
- ⏳ Schwab journey tests (blocked by API credentials)
- ⏳ Live Schwab trading validation
- ⏳ Multi-broker integration tests
- ⏳ Schwab-specific documentation

**Out of Scope:**
- Crypto trading tools
- Banking/ACH transfers
- Account modifications
- Deposit/withdrawal functionality

## Contributing

See [CONTRIBUTING.md](contributing/README.md) for development guidelines.
See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and debugging recipes.

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
