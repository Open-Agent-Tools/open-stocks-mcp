# GEMINI.md

Technical guidance for Gemini when working with the Open Stocks MCP server codebase.

## Project Status (v0.5.0)

- **84 MCP tools** with complete trading functionality
- **HTTP transport** with Server-Sent Events (SSE) on port 3001
- **Docker deployment** with persistent volumes
- **Comprehensive test coverage** with performance optimization
- **Zero MyPy errors** maintained across codebase
- **Production-ready** with comprehensive error handling

## Development Commands

### Virtual Environment & Dependencies
```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Testing
```bash
uv run pytest                               # All tests (skips exception tests)
uv run pytest -m "not slow and not exception_test"  # Fast tests (recommended)
uv run pytest -m integration               # Integration tests (needs credentials)
uv run pytest -m exception_test            # Exception/error state tests
uv run pytest -m slow                      # Slow performance tests
```

### Code Quality
```bash
uv run ruff check . --fix  # Linting with auto-fix
uv run ruff format .       # Formatting
uv run mypy .             # Type checking (should show 0 errors)
```

### MCP Server Testing
```bash
# HTTP transport (recommended)
uv run open-stocks-mcp-server --transport http --port 3001

# STDIO transport
uv run mcp dev src/open_stocks_mcp/server/app.py

# Docker development
cd examples/open-stocks-mcp-docker && docker-compose up -d
```

## Test Markers

**Performance & Scope:**
- `slow` - Long-running performance tests (watchlist operations, multiple API calls)
- `integration` - Requires credentials
- `agent_evaluation` - ADK evaluation tests
- `exception_test` - Error state and exception handling tests (skipped by default)

**Recommended for development:**
```bash
pytest -m "not slow and not exception_test"
```

## Current Development Phase

### Current Status: Phase 7 Complete - Trading Capabilities (v0.5.0)
✅ **84 MCP tools implemented** including full trading functionality:
- Stock order placement (9 tools): market, limit, stop-loss, trailing stop orders
- Options order placement (4 tools): buy/sell options, credit/debit spreads  
- Order management (6 tools): cancel orders, view open positions

### Next Priority: Phase 8 - Quality & Reliability (v0.6.0)
Implementing enhanced reliability and monitoring features

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

## Common Patterns

### MCP Tool Structure
```python
@mcp.tool()
async def tool_name(param: str) -> dict[str, Any]:
    """Tool description."""
    try:
        result = await execute_with_retry(rh.some_function, param)
        return {"result": result}
    except Exception as e:
        return {"result": {"error": str(e), "status": "error"}}
```

### Key Conventions
- **Async wrappers** for Robin Stocks (synchronous API)
- **Retry logic** via `execute_with_retry`
- **Error handling** via `@handle_robin_stocks_errors`
- **Rate limiting** via `get_rate_limiter()`
- **Session management** for authentication
- **JSON responses** with `{"result": data}` format

## Testing Guidelines

### Unit Tests
- Mock external API calls
- Test error conditions
- Validate return formats
- Use pytest fixtures for common setups

### Integration Tests
- Require valid credentials
- Test against live API
- Mark with `@pytest.mark.integration`
- Handle rate limiting appropriately

### Performance Tests
- Mark with `@pytest.mark.slow`
- Test with realistic data volumes
- Monitor execution times
- Validate memory usage

## Authentication Handling

The server includes robust authentication for Robinhood:
- **Device verification** - Automatic handling of new device approval
- **Multi-factor authentication** - Support for SMS and app-based MFA
- **Session persistence** - Cached authentication to reduce re-verification
- **Error recovery** - Graceful handling of authentication failures

## Important Notes

- **UV package manager** - All commands use UV for dependency management
- **HTTP transport default** - Server runs on port 3001 (not 3000)
- **Docker persistent volumes** - Session tokens and logs survive container restarts
- **Type safety critical** - Maintain zero MyPy errors
- **Rate limiting active** - Automatic rate limiting respects Robin Stocks API limits
- **Testing isolation** - Unit tests use mocks to avoid real API calls