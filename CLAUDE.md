# CLAUDE.md

Project guidance for Claude Code when working with the Open Stocks MCP server.

## Project Overview

**Open Stocks MCP** - Model Context Protocol server providing stock market data through Robin Stocks API.
- **Current Version**: v0.5.4 with trading capabilities and 83 MCP tools
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
```bash
pytest                           # All tests (skips exception tests by default)
pytest tests/unit/               # Unit tests (fast)
pytest tests/integration/ -m integration  # Integration (needs auth)
pytest -m "not slow and not exception_test"  # Fast tests (recommended)
```

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

### Completed (v0.5.4)
- ✅ **Phases 1-7**: 83 MCP tools with complete trading functionality
- ✅ **HTTP Transport**: Server-Sent Events (SSE) on port 3001
- ✅ **Docker Infrastructure**: Persistent volumes for sessions and logs
- ✅ **Test Coverage**: Comprehensive test suite covering all tools
- ✅ **Type Safety**: Zero MyPy errors maintained across codebase
- ✅ **Trading Bug Fixes**: Fixed API method calls in trading functions

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
   docker-compose pull  # Get latest published version
   docker-compose up -d
   curl http://localhost:3001/health  # Verify version updated
   ```
3. **Important**: Docker containers pull from PyPI releases, not local codebase

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