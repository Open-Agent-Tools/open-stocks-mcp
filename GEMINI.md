# GEMINI.md

This file provides technical guidance for Gemini when working with the Open Stocks MCP server codebase.

## Project Status (v0.4.1)

- **61 MCP tools** providing complete read-only stock market functionality
- **HTTP transport** with Server-Sent Events (SSE) on port 3001
- **Docker deployment** with persistent volumes for sessions and logs
- **100% test coverage** with 148 tests across all tools
- **Zero MyPy errors** across 58 source files
- **Production-ready** with comprehensive error handling and monitoring

## Development Commands

This project uses UV for dependency management and virtual environments.

### Virtual Environment Setup
```bash
uv venv  # Creates .venv
source .venv/bin/activate  # Activate the environment
```

### Dependency Installation
```bash
uv pip install -e .  # Install project in editable mode
uv pip install -e ".[dev]"  # Install with dev dependencies
```

### Running Tests
```bash
uv run pytest                               # All tests (skips exception tests by default)
uv run pytest -m "not slow and not exception_test"  # Fast tests only (recommended)
uv run pytest -m integration               # Integration tests (needs credentials)
uv run pytest -m exception_test            # Exception/error state tests only
uv run pytest -m slow                      # Slow performance tests only
```

### Linting and Type Checking
```bash
uv run ruff check . --fix  # Linting with auto-fix
uv run ruff format .       # Formatting
uv run mypy .             # Type checking (should show 0 errors)
```

### Adding Dependencies
```bash
# Add to pyproject.toml dependencies section, then:
uv pip install -e .
```

### Docker Development
```bash
cd examples/open-stocks-mcp-docker
docker-compose up -d           # Start with persistent volumes
docker-compose logs -f          # Monitor logs
curl http://localhost:3001/health  # Test health endpoint
docker-compose down             # Stop server
```

## Architecture

### MCP Server Structure

The project uses FastMCP with HTTP transport, providing a high-level interface to the MCP protocol with Server-Sent Events (SSE):

```python
from mcp.server.fastmcp import FastMCP

# Create server instance
mcp = FastMCP("Open Stocks MCP")

# Tools are functions that can have side effects
@mcp.tool()
async def get_stock_price(symbol: str) -> dict:
    """Get current stock price."""
    quote = await execute_with_retry(rh.stocks.get_quote, symbol)
    return {
        "result": {
            "symbol": symbol, 
            "price": float(quote["last_trade_price"])
        }
    }

# Resources provide data without side effects  
@mcp.resource("portfolio://holdings")
def get_holdings() -> str:
    """Get portfolio holdings."""
    return json.dumps({"AAPL": 10, "GOOGL": 5})

# Prompts are reusable templates
@mcp.prompt(title="Stock Analysis")
def analyze_stock(symbol: str) -> str:
    return f"Analyze {symbol} stock performance"
```

### Key MCP Patterns

1. **JSON Output**: Tools should ALWAYS return JSON objects with data in a "result" field
2. **Structured Output**: Tools can return Pydantic models, TypedDicts, or regular dicts for structured data
3. **Context Access**: Tools can access MCP context for logging, progress reporting, and session data
4. **Async Support**: Use async functions for I/O operations
5. **Error Handling**: Return JSON objects with error information in the "result" field

### MCP Tool Best Practices

When implementing MCP tools, follow these best practices:

1. **Clear Naming**: Provide clear, descriptive names and descriptions
2. **Schema Definitions**: Use detailed JSON Schema definitions for parameters
3. **Examples**: Include examples in tool descriptions to demonstrate usage
4. **Error Handling**: Implement proper error handling and validation
5. **Progress Reporting**: Use progress reporting for long operations
6. **Atomic Operations**: Keep tool operations focused and atomic
7. **Documentation**: Document expected return value structures
8. **Timeouts**: Implement proper timeouts for operations
9. **Rate Limiting**: Consider rate limiting for resource-intensive operations
10. **Logging**: Log tool usage for debugging and monitoring
11. **Result Field**: Always return JSON with data in a "result" field

Example tool implementation:

```python
@mcp.tool()
async def get_stock_quote(symbol: str) -> dict:
    """Get detailed stock quote information.
    
    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "GOOGL")
    
    Returns:
        JSON object with stock quote data in "result" field:
        {
            "result": {
                "symbol": "AAPL",
                "price": 150.00,
                "change": 2.50,
                "change_percent": 1.69,
                "volume": 50000000
            }
        }
    """
    try:
        # Async wrapper for synchronous API
        loop = asyncio.get_event_loop()
        quote = await loop.run_in_executor(None, rh.stocks.get_quote, symbol)
        
        return {
            "result": {
                "symbol": symbol,
                "price": float(quote["last_trade_price"]),
                "change": float(quote["previous_close"]) - float(quote["last_trade_price"]),
                "volume": int(quote["volume"]),
                "status": "success"
            }
        }
    except Exception as e:
        logger.error(f"Failed to get quote for {symbol}: {e}")
        return {
            "result": {
                "error": str(e),
                "status": "error"
            }
        }
```

### Robin Stocks Integration

Use the project's async wrapper utilities for Robin Stocks integration:

```python
from open_stocks_mcp.tools.session_manager import execute_with_retry
from open_stocks_mcp.tools.error_handling import handle_robin_stocks_errors
import robin_stocks.robinhood as rh

@mcp.tool()
@handle_robin_stocks_errors
async def get_stock_quote(symbol: str) -> dict:
    """Get stock quote with proper error handling and retry logic."""
    quote = await execute_with_retry(rh.stocks.get_quote, symbol)
    return {
        "result": {
            "symbol": symbol,
            "price": float(quote["last_trade_price"]),
            "status": "success"
        }
    }
```

### Development Guidelines

1. **Tools vs Resources**: 
   - Tools: Functions that perform actions (place orders, fetch live data)
   - Resources: Static or cached data (portfolio snapshot, watchlists)

2. **Authentication**: Use the project's session manager:
   ```python
   from open_stocks_mcp.tools.session_manager import get_session_manager
   
   # Session manager handles authentication automatically
   session_manager = get_session_manager()
   await session_manager.ensure_authenticated()
   
   # Check session status
   session_info = session_manager.get_session_info()
   print(f"Authenticated: {session_info['is_authenticated']}")
   ```

3. **Error Handling**: Always handle API errors gracefully
4. **Rate Limiting**: Implement caching to avoid hitting API limits
5. **Security**: Never log or return sensitive data (passwords, full account numbers)

## Testing MCP Tools

Test tools with HTTP transport (recommended):
```bash
# Start HTTP server
uv run open-stocks-mcp-server --transport http --port 3001

# Test with curl
curl http://localhost:3001/health
curl http://localhost:3001/tools
```

Test tools with STDIO transport:
```bash
uv run mcp dev src/open_stocks_mcp/server/app.py
```

Docker testing:
```bash
cd examples/open-stocks-mcp-docker
docker-compose up -d
curl http://localhost:3001/health
```

Or write unit tests with pytest:
```python
def test_stock_tool():
    result = get_stock_price("AAPL")
    assert "symbol" in result
    assert "price" in result

@pytest.mark.integration
def test_live_stock_data():
    # Test requiring real API access
    pass

@pytest.mark.slow  
def test_performance():
    # Test that might take longer
    pass
```

Available test markers:
- `slow`: Tests that take longer to run (watchlist operations, multiple API calls)
- `integration`: Tests requiring credentials/live APIs  
- `exception_test`: Error state and exception handling tests (skipped by default)
- `agent_evaluation`: ADK evaluation tests

## Current Development Phase

### Next Priority: Phase 6 - Advanced Instrument Data (v0.4.2)
Implementing 4 new read-only tools:
1. `get_instruments_by_symbols()` - Metadata for multiple symbols
2. `find_instrument_data()` - Search instrument information  
3. `get_stock_quote_by_id()` - Quote by Robinhood instrument ID
4. `get_pricebook_by_symbol()` - Level II order book (Gold required)

### Implementation Guidelines for Phase 6:
- Use existing Robin Stocks functions: `rh.find_instrument_data()`, etc.
- Follow async wrapper pattern with `execute_with_retry`
- Add comprehensive error handling with `@handle_robin_stocks_errors`
- Include rate limiting via `get_rate_limiter()`
- Write unit tests following existing patterns
- Update tool registration in `server/app.py`

### Out of Scope:
- Crypto tools (`get_crypto_*()` functions)
- Banking tools (`get_bank_*()` functions)
- Any functions involving money movement
- Account modification tools

## Release Management

For complete GitHub CLI operations and release processes, see `CONTRIBUTING.md`.
