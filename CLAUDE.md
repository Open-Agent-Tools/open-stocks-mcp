# CLAUDE.md

Project guidance for Claude Code when working with the Open Stocks MCP server.

## Project Overview

**Open Stocks MCP** - Model Context Protocol server providing stock market data through Robin Stocks API.
- **Current Version**: v0.5.5 with trading capabilities and 83 MCP tools
- **Framework**: FastMCP for simplified MCP development
- **API**: Robin Stocks for market data and trading
- **Transport**: HTTP with Server-Sent Events (SSE) on port 3001
- **Docker**: Production-ready with persistent session/log storage

## Quick Reference

### Development Setup
```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Testing

**Journey-Based Testing** - 11 user journey categories for focused testing:

```bash
# All tests (skips exception tests by default)
pytest                           

# Fast journey testing (<30s each)
pytest -m "journey_account"      # Account management (16 tests, ~1.8s)
pytest -m "journey_portfolio"    # Portfolio & holdings (3 tests, ~1.7s)  
pytest -m "journey_market_data"  # Stock quotes & market info (19 tests, ~3.8s)
pytest -m "journey_research"     # Earnings, ratings, news (23 tests, ~3.0s)
pytest -m "journey_watchlists"   # Watchlist management (20 tests, ~16.7s)
pytest -m "journey_options"      # Options analysis (13 tests, ~9.7s)
pytest -m "journey_notifications" # Alerts & notifications (15 tests, ~1.6s)
pytest -m "journey_system"       # Health & monitoring (11 tests, ~1.9s)
pytest -m "journey_trading"      # Trading operations (1 test, ~1.6s)

# Combined journeys
pytest -m "journey_account or journey_portfolio"          # User account flows
pytest -m "journey_market_data or journey_research"       # Market intelligence
pytest -m "journey_options or journey_trading"            # Trading related

# Development workflows
pytest -m "not slow and not exception_test"               # Fast tests (recommended)
pytest -m "unit and journey_account"                      # Quick unit feedback
pytest tests/unit/                                        # Unit tests (fast)
pytest tests/integration/ -m integration                  # Integration (needs auth)

# READ ONLY journeys (perfect for ADK evaluations)
pytest -m "journey_account or journey_portfolio or journey_market_data or journey_research or journey_notifications or journey_system"
```

**Journey Categories:**
- `journey_account` - Account info, profiles, settings, day trades
- `journey_portfolio` - Portfolio overview, positions, holdings
- `journey_market_data` - Stock prices, quotes, instruments, search
- `journey_research` - Earnings, ratings, news, dividends, splits
- `journey_watchlists` - Watchlist CRUD, performance tracking
- `journey_options` - Options chains, positions, market data
- `journey_notifications` - Alerts, margin calls, subscription fees
- `journey_system` - Health checks, metrics, session status
- `journey_trading` - Buy/sell orders, cancellation, order management

### Code Quality
```bash
ruff check . --fix              # Lint and fix
ruff format .                   # Format code  
mypy .                          # Type check
```

### MCP Development
```bash
# Test server locally (HTTP transport)
uv run open-stocks-mcp-server --transport http --port 3001

# Docker development
cd examples/open-stocks-mcp-docker && docker-compose up -d
curl http://localhost:3001/health  # Test health endpoint
```

## MCP Architecture

### Tool Structure
All tools return JSON with `result` field:
```python
@mcp.tool()
async def get_stock_quote(symbol: str) -> dict:
    try:
        quote = await execute_with_retry(rh.stocks.get_quote, symbol)
        return {"result": {"symbol": symbol, "price": float(quote["last_trade_price"])}}
    except Exception as e:
        return {"result": {"error": str(e), "status": "error"}}
```

### Key Patterns
- **Async wrappers** for Robin Stocks (synchronous API)
- **Retry logic** via `execute_with_retry`
- **Error handling** via `@handle_robin_stocks_errors` 
- **Rate limiting** via `get_rate_limiter()`
- **Session management** for authentication

## Environment Variables

### Required for Live Testing
```bash
ROBINHOOD_USERNAME="email@example.com"
ROBINHOOD_PASSWORD="password"
```

### Required for ADK Evaluation  
```bash
GOOGLE_API_KEY="your-google-api-key"
ROBINHOOD_USERNAME="email@example.com" 
ROBINHOOD_PASSWORD="password"
```

## Current Development Status

### Completed (v0.5.7)
- ✅ **Phases 0-7**: 79 MCP tools with complete trading functionality (4 deprecated)
- ✅ **Journey Testing**: 11 user journey categories for organized testing
- ✅ **HTTP Transport**: Server-Sent Events (SSE) on port 3001
- ✅ **Docker Infrastructure**: Persistent volumes for sessions and logs
- ✅ **Test Coverage**: Comprehensive test suite with journey-based markers
- ✅ **Type Safety**: Zero MyPy errors maintained across codebase
- ✅ **Trading Validation**: All functions live-tested or API-corrected

### Next Phase Priority
**Phase 8: Quality & Reliability (v0.6.0)** - Final phase:
- Advanced error handling and recovery mechanisms
- Performance optimization and caching strategies
- Enhanced monitoring and observability features

## Common Tasks

### Adding New MCP Tool
1. Create tool function in appropriate `tools/robinhood_*.py` file
2. Use `@mcp.tool()` decorator
3. Follow async pattern with error handling
4. Add to server registration in `server/app.py`
5. Write unit tests in `tests/unit/`

### Creating New Release and Updating Docker
1. **Create GitHub Release**: 
   ```bash
   git tag v0.x.x && git push origin v0.x.x
   gh release create v0.x.x --generate-notes
   ```
2. **Update Docker Container** (Docker uses PyPI, not local code):
   ```bash
   cd examples/open-stocks-mcp-docker
   docker-compose down
   docker-compose build --no-cache  # Rebuilds with latest PyPI version
   docker-compose up -d
   curl http://localhost:3001/health  # Verify version updated
   ```
3. **Important**: Docker containers install from PyPI during build, not local codebase. Use `build --no-cache` to ensure latest version is fetched.

### Running ADK Evaluations
1. Install: `pip install google-agent-developer-kit`
2. Set environment variables (see above)
3. Start Docker server: `cd examples/open-stocks-mcp-docker && docker-compose up -d`
4. From project root: `MCP_HTTP_URL="http://localhost:3001/mcp" adk eval examples/google_adk_agent tests/evals/list_available_tools_test.json --config_file_path tests/evals/test_config.json`

## Important Notes

- **Use UV for dependencies** - Project uses UV package manager  
- **HTTP transport default** - Server runs on port 3001 (not 3000)
- **Docker persistent volumes** - Session tokens and logs survive restarts
- **Async patterns required** - Robin Stocks is sync, tools are async
- **JSON responses mandatory** - All tools return `{"result": data}` format
- **Rate limiting active** - Automatic rate limiting for Robin Stocks API
- **Type safety maintained** - Zero MyPy errors maintained across codebase